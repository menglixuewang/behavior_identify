from ultralytics import YOLO
import numpy as np
import os, cv2, time, torch, random, warnings, argparse, math
import threading
import queue
import contextlib

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
warnings.filterwarnings("ignore", category=UserWarning)

# 添加环境变量控制GUI显示，用于服务器环境
# Windows组员可以忽略这个，默认启用GUI显示
ENABLE_GUI = os.environ.get('ENABLE_GUI', 'true').lower() in ('true', '1', 'yes')

from pytorchvideo.transforms.functional import (
    uniform_temporal_subsample,
    short_side_scale_with_boxes,
    clip_boxes_to_image, )
from torchvision.transforms._functional_video import normalize
from pytorchvideo.data.ava import AvaLabeledVideoFramePaths
from pytorchvideo.models.hub import slowfast_r50_detection
from deep_sort.deep_sort import DeepSort


class MyVideoCapture:

    def __init__(self, source):
        # 区分摄像头和视频文件
        if isinstance(source, int):
            # 添加CAP_DSHOW后端以解决Windows摄像头访问问题
            self.cap = cv2.VideoCapture(source)
            err_msg = f"无法打开摄像头: {source}，请检查摄像头是否被占用或权限是否允许"
        else:
            # 打开视频文件
            self.cap = cv2.VideoCapture(source)
            err_msg = f"无法打开视频文件: {source}，请检查文件路径是否正确或文件是否损坏"

        if not self.cap.isOpened():
            raise RuntimeError(err_msg)
        # 移除显式分辨率设置，使用摄像头默认分辨率
        # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        # 验证实际分辨率
        actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"视频源分辨率: {actual_width}x{actual_height}")
        self.idx = -1
        self.end = False
        self.stack = []

    def read(self):
        self.idx += 1
        ret, img = self.cap.read()
        if not ret:
            print(f"警告: 无法读取视频帧 {self.idx}，可能是摄像头断开连接")
            self.end = True
            return ret, None
        if img is None or img.size == 0:
            print(f"警告: 读取到空图像 {self.idx}")
            self.stack.append(np.zeros((480, 640, 3), dtype=np.uint8))  # 返回黑色占位图像
            return ret, img
        # 显示原始摄像头帧用于调试 (仅在GUI模式下)
        if ENABLE_GUI:
            try:
                cv2.imshow("原始摄像头画面", img)
                cv2.waitKey(1)
            except cv2.error as e:
                print(f"GUI显示失败 (这在服务器环境中是正常的): {e}")
        print(f"原始图像尺寸: {img.shape}, 数据类型: {img.dtype}, 数据范围: [{img.min()}, {img.max()}]")
        self.stack.append(img)
        return ret, img

    def to_tensor(self, img):
        img = torch.from_numpy(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        return img.unsqueeze(0)

    def get_video_clip(self):
        assert len(self.stack) > 0, "clip length must large than 0 !"
        self.stack = [self.to_tensor(img) for img in self.stack]
        clip = torch.cat(self.stack).permute(-1, 0, 1, 2)
        del self.stack
        self.stack = []
        return clip

    def release(self):
        """释放摄像头资源，确保完全关闭"""
        try:
            if hasattr(self, 'cap') and self.cap is not None:
                print("🎥 MyVideoCapture: 正在释放摄像头...")
                self.cap.release()
                print("🎥 MyVideoCapture: 摄像头已释放")

                # 强制等待确保资源完全释放
                import time
                time.sleep(0.1)

                # 设置为None，避免重复释放
                self.cap = None
                print("🎥 MyVideoCapture: 摄像头对象已清空")
            else:
                print("🎥 MyVideoCapture: 摄像头对象不存在或已释放")
        except Exception as e:
            print(f"🎥 MyVideoCapture: 释放摄像头时出错: {e}")
        finally:
            # 确保对象被标记为已释放
            self.end = True


def tensor_to_numpy(tensor):
    img = tensor.cpu().numpy().transpose((1, 2, 0))
    return img


def ava_inference_transform(
        clip,
        boxes,
        num_frames=32,  # if using slowfast_r50_detection, change this to 32, 4 for slow
        crop_size=640,
        data_mean=[0.45, 0.45, 0.45],
        data_std=[0.225, 0.225, 0.225],
        slow_fast_alpha=4,  # if using slowfast_r50_detection, change this to 4, None for slow
):
    boxes = np.array(boxes)
    roi_boxes = boxes.copy()
    clip = uniform_temporal_subsample(clip, num_frames)
    clip = clip.float()
    clip = clip / 255.0
    height, width = clip.shape[2], clip.shape[3]
    boxes = clip_boxes_to_image(boxes, height, width)
    clip, boxes = short_side_scale_with_boxes(clip, size=crop_size, boxes=boxes, )
    clip = normalize(clip,
                     np.array(data_mean, dtype=np.float32),
                     np.array(data_std, dtype=np.float32), )
    boxes = clip_boxes_to_image(boxes, clip.shape[2], clip.shape[3])
    if slow_fast_alpha is not None:
        fast_pathway = clip
        slow_pathway = torch.index_select(clip, 1,
                                          torch.linspace(0, clip.shape[1] - 1, clip.shape[1] // slow_fast_alpha).long())
        clip = [slow_pathway, fast_pathway]

    return clip, torch.from_numpy(boxes), roi_boxes


def plot_one_box(x, img, color=[100, 100, 100], text_info="None",
                 velocity=None, thickness=1, fontsize=0.5, fontthickness=1):
    # Plots one bounding box on image img
    c1, c2 = (int(x[0]), int(x[1])), (int(x[2]), int(x[3]))
    cv2.rectangle(img, c1, c2, color, thickness, lineType=cv2.LINE_AA)
    t_size = cv2.getTextSize(text_info, cv2.FONT_HERSHEY_TRIPLEX, fontsize, fontthickness + 2)[0]
    cv2.rectangle(img, c1, (c1[0] + int(t_size[0]), c1[1] + int(t_size[1] * 1.45)), color, -1)
    cv2.putText(img, text_info, (c1[0], c1[1] + t_size[1] + 2),
                cv2.FONT_HERSHEY_TRIPLEX, fontsize, [255, 255, 255], fontthickness)
    return img


def deepsort_update(Tracker, pred, xywh, np_img):
    outputs = Tracker.update(xywh, pred[:, 4:5], pred[:, 5].tolist(), cv2.cvtColor(np_img, cv2.COLOR_BGR2RGB))
    # 修正后的跟踪信息打印
    print(f"\n跟踪结果 - 目标数: {len(outputs)}")
    for i, output in enumerate(outputs):
        # 检查输出长度并相应处理
        if len(output) >= 7:  # 至少有位置、类别、ID和置信度
            track_info = f"目标 {i + 1}: ID:{int(output[5])} | 类别:{int(output[4])} | 置信度:{output[6]:.2f} | "
            track_info += f"位置:[{output[0]:.0f},{output[1]:.0f},{output[2]:.0f},{output[3]:.0f}]"
            # 检查是否有速度信息
            if len(output) >= 8:
                track_info += f" | 速度(vx,vy):[{output[6]:.2f},{output[7]:.2f}]"
            print(track_info)
    return outputs


def save_yolopreds_tovideo(yolo_preds, id_to_ava_labels, color_map, output_video, vis=False):
    for i, (im, pred) in enumerate(zip(yolo_preds.ims, yolo_preds.pred)):
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        if pred.shape[0]:
            for j, (*box, cls, trackid, vx, vy) in enumerate(pred):
                if int(cls) != 0:
                    ava_label = ''
                elif trackid in id_to_ava_labels.keys():
                    ava_label = id_to_ava_labels[trackid].split(' ')[0]
                else:
                    ava_label = 'Unknow'
                text = '{} {} {}'.format(int(trackid), yolo_preds.names[int(cls)], ava_label)
                color = color_map[int(cls)]
                im = plot_one_box(box, im, color, text)
        im = im.astype(np.uint8)
        # 强制图像数据类型为uint8并裁剪范围，解决黑屏问题
        im = np.clip(im, 0, 255).astype(np.uint8)
        # 添加图像调试信息
        print(f"显示图像尺寸: {im.shape}, 数据类型: {im.dtype}, 数据范围: [{im.min()}, {im.max()}]")
        if im.size == 0:
            print("警告: 空图像，跳过显示")
            return
        if output_video is not None:
            output_video.write(im)
        if vis:
            # 恢复正确的颜色空间转换 (RGB转BGR)
            im_bgr = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
            # 添加详细调试信息
            print(
                f"显示前图像尺寸: {im_bgr.shape}, 数据类型: {im_bgr.dtype}, 数据范围: [{im_bgr.min()}, {im_bgr.max()}]")
            if ENABLE_GUI:
                try:
                    cv2.imshow("实时检测", im_bgr)
                    key = cv2.waitKey(1)
                    if key & 0xFF == ord('q'):
                        cv2.destroyAllWindows()
                        exit()
                except cv2.error as e:
                    print(f"GUI显示失败 (这在服务器环境中是正常的): {e}")


def main(config):
    device = config.device
    imsize = config.imsize

    # 判断是否为实时摄像头模式
    is_camera = isinstance(config.input, int)

    model = YOLO("yolov8n.pt")  # yolov8l, s, m, x

    # 修改 SlowFast 模型加载方式
    SLOWFAST_WEIGHTS_PATH = "SLOWFAST_8x8_R50_DETECTION.pyth"
    if not os.path.exists(SLOWFAST_WEIGHTS_PATH):
        raise RuntimeError(f"SlowFast 权重文件不存在: {SLOWFAST_WEIGHTS_PATH}")
    
    # 创建模型并加载权重
    video_model = slowfast_r50_detection(False)  # False表示不自动下载权重
    checkpoint = torch.load(SLOWFAST_WEIGHTS_PATH)
    video_model.load_state_dict(checkpoint['model_state'])
    video_model = video_model.eval().to(device)

    deepsort_tracker = DeepSort("ckpt.t7")
    ava_labelnames, _ = AvaLabeledVideoFramePaths.read_label_map("temp.pbtxt")

    coco_color_map = [[random.randint(0, 255) for _ in range(3)] for _ in range(80)]

    vide_save_path = config.output
    if not vide_save_path and not is_camera:
        # 如果是视频文件但没有指定输出路径，则自动生成
        input_name = os.path.splitext(os.path.basename(config.input))[0]
        vide_save_path = f"{input_name}_output.mp4"
        print(f"未指定输出路径，将保存到: {vide_save_path}")

    outputvideo = None
    if vide_save_path:
        video = cv2.VideoCapture(config.input)
        width, height = int(video.get(3)), int(video.get(4))
        video.release()
        outputvideo = cv2.VideoWriter(vide_save_path, cv2.VideoWriter_fourcc(*"mp4v"), 25, (width, height))
        print(f"视频将保存到: {os.path.abspath(vide_save_path)}")
    else:
        # Get camera resolution
        cap = cv2.VideoCapture(config.input)
        width = int(cap.get(3))
        height = int(cap.get(4))
        cap.release()

    print("开始处理...")
    cap = MyVideoCapture(config.input)
    id_to_ava_labels = {}
    a = time.time()

    # 新增：clip 队列和动作识别线程
    clip_queue = queue.Queue()
    result_queue = queue.Queue()

    def slowfast_worker():
        # 仅当使用GPU时才创建独立的CUDA流
        stream = torch.cuda.Stream() if 'cuda' in str(device) else None
        
        # 使用 contextlib.nullcontext() 来优雅地处理 CPU 情况
        context_manager = torch.cuda.stream(stream) if stream else contextlib.nullcontext()

        while True:
            item = clip_queue.get()
            if item is None:
                break
            idx, clip, pred_result = item
            
            # 所有在这个 'with' 块内的CUDA操作都将在我们创建的独立流上执行
            with context_manager:
                if pred_result.pred[0].shape[0]:
                    inputs, inp_boxes, _ = ava_inference_transform(clip, pred_result.pred[0][:, 0:4], crop_size=imsize)
                    inp_boxes = torch.cat([torch.zeros(inp_boxes.shape[0], 1), inp_boxes], dim=1)
                    if isinstance(inputs, list):
                        # non_blocking=True 允许主机(CPU)代码继续执行，而不会等待数据复制完成
                        inputs = [inp.unsqueeze(0).to(device, non_blocking=True) for inp in inputs]
                    else:
                        inputs = inputs.unsqueeze(0).to(device, non_blocking=True)
                    
                    inp_boxes_gpu = inp_boxes.to(device, non_blocking=True)

                    with torch.no_grad():
                        # SlowFast模型推理被提交到独立的流
                        slowfaster_preds = video_model(inputs, inp_boxes_gpu)
                    
                    # 修复数据类型转换问题 - 确保正确的数据类型转换
                    slowfaster_preds_cpu = slowfaster_preds.cpu().float()  # 确保为float类型
                    pred_labels = torch.argmax(slowfaster_preds_cpu, dim=1).numpy().astype(np.int32)
                    track_ids = pred_result.pred[0][:, 5].astype(np.int32)

                    result_queue.put((idx, track_ids.tolist(), pred_labels.tolist()))
            clip_queue.task_done()

    threading.Thread(target=slowfast_worker, daemon=True).start()

    frame_count = 0
    total_frames = int(cap.cap.get(cv2.CAP_PROP_FRAME_COUNT)) if not is_camera else 0

    while not cap.end:
        ret, img = cap.read()
        if not ret:
            continue

        frame_count += 1
        if not is_camera and frame_count % 25 == 0:
            # 每25帧显示一次进度（仅在处理视频文件时）
            progress = (frame_count / total_frames) * 100 if total_frames > 0 else 0
            print(f"\r处理进度: {progress:.1f}% ({frame_count}/{total_frames})", end="", flush=True)

        results = model.predict(source=img, imgsz=imsize, device=device, verbose=False)
        boxes = results[0].boxes  # YOLOv8 Results object

        # 仅在调试模式或使用摄像头时打印详细信息
        if is_camera:
            print(f"\n帧 {cap.idx} - 检测结果:")
            print(f"检测到 {len(boxes)} 个目标:")
            cls_counts = {}
            for i, box in enumerate(boxes):
                cls_name = model.names[int(box.cls)]
                cls_counts[cls_name] = cls_counts.get(cls_name, 0) + 1
                print(f"目标 {i + 1}: 类别:{cls_name} | 置信度:{box.conf.item():.2f} | "
                      f"位置:[{box.xyxy.cpu().numpy()[0][0]:.0f},{box.xyxy.cpu().numpy()[0][1]:.0f},"
                      f"{box.xyxy.cpu().numpy()[0][2]:.0f},{box.xyxy.cpu().numpy()[0][3]:.0f}]")
            print("类别统计:", ", ".join([f"{k}:{v}" for k, v in cls_counts.items()]))

        pred_xyxy = boxes.xyxy.cpu().numpy()
        pred_conf = boxes.conf.cpu().numpy().reshape(-1, 1)
        pred_cls = boxes.cls.cpu().numpy().reshape(-1, 1)

        pred = np.hstack((pred_xyxy, pred_conf, pred_cls))
        xywh = np.hstack(((pred[:, 0:2] + pred[:, 2:4]) / 2, pred[:, 2:4] - pred[:, 0:2]))
        temp = deepsort_update(deepsort_tracker, pred, xywh, img)
        temp = temp if len(temp) else np.ones((0, 8)).astype(np.float32)

        pred_result = type("YoloPred", (), {})()
        pred_result.ims = [img]
        pred_result.pred = [temp.astype(np.float32)]
        pred_result.names = model.names

        if len(cap.stack) == 25:
            if is_camera:
                print(f"processing {cap.idx // 25}th second clips (异步)")
            clip = cap.get_video_clip()
            clip_queue.put((cap.idx, clip, pred_result))

        while not result_queue.empty():
            idx, tids, avalabels = result_queue.get()
            for tid, avalabel in zip(tids, avalabels):
                id_to_ava_labels[tid] = ava_labelnames[avalabel + 1]
            if is_camera:
                print(f"动作识别结果: 更新了 {len(avalabels)} 个目标的动作标签 (帧 {idx})")
            result_queue.task_done()

        # 仅在使用摄像头时显示实时画面
        show_frame = is_camera and config.show
        save_yolopreds_tovideo(pred_result, id_to_ava_labels, coco_color_map, outputvideo, show_frame)

    if not is_camera:
        print("\n")  # 为进度条添加换行

    print("\n处理完成!")
    process_time = time.time() - a
    print("总耗时: {:.3f} 秒, 视频长度: {:.1f} 秒, 平均帧率: {:.1f} FPS".format(
        process_time, cap.idx / 25, frame_count / process_time))
    
    cap.release()
    if outputvideo is not None:
        outputvideo.release()
        print('视频已保存到:', os.path.abspath(vide_save_path))
    cv2.destroyAllWindows()
    clip_queue.put(None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, default='0')
    parser.add_argument('--output', type=str, default='')
    parser.add_argument('--imsize', type=int, default=640)
    parser.add_argument('--conf', type=float, default=0.4)
    parser.add_argument('--iou', type=float, default=0.4)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--classes', nargs='+', type=int)
    parser.add_argument('--show', action='store_false', default=True, help='Show real-time video')
    config = parser.parse_args()

    if config.input.isdigit():
        print("using local camera.")
        config.input = int(config.input)

    print(config)
    main(config)
