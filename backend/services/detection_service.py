"""
检测服务模块 - 封装YOLOv8+SlowFast算法
"""
import os
import sys
import cv2
import time
import json
import threading
import queue
from datetime import datetime
import base64
from typing import Dict, List, Optional, Tuple, Any

# 添加算法模块路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
yolo_slowfast_path = os.path.join(project_root, 'yolo_slowfast-master')
sys.path.append(yolo_slowfast_path)

# 导入现有算法模块
try:
    from yolo_slowfast import *
    import torch
    import numpy as np
    from ultralytics import YOLO
    from pytorchvideo.data.ava import AvaLabeledVideoFramePaths
    from pytorchvideo.models.hub import slowfast_r50_detection
    from deep_sort.deep_sort import DeepSort
except ImportError as e:
    print(f"警告: 无法导入算法模块: {e}")


class BehaviorDetectionService:
    """行为检测服务类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化检测服务
        
        Args:
            config: 配置字典，包含设备、输入尺寸、置信度阈值等参数
        """
        # 设备配置 - GPU检测
        if config.get('device', 'cpu').lower() == 'cuda':
            if torch.cuda.is_available():
                self.device = 'cuda'
                print(f"✓ 使用GPU: {torch.cuda.get_device_name()}")
            else:
                self.device = 'cpu'
                print("⚠ CUDA不可用，回退到CPU")
        else:
            self.device = 'cpu'
            print("✓ 使用CPU")
        
        # 加载COCO类别名称
        coco_names_path = os.path.join(yolo_slowfast_path, 'selfutils', 'coco_names.txt')
        self.coco_names = []
        if os.path.exists(coco_names_path):
            with open(coco_names_path, 'r') as f:
                self.coco_names = [line.strip() for line in f.readlines()]
            print(f"✓ 加载COCO类别名称: {len(self.coco_names)}个类别")
        else:
            print("⚠ COCO类别名称文件不存在")
            # 使用默认类别
            self.coco_names = ['person', 'bicycle', 'car', 'motorbike', 'aeroplane']
        
        self.input_size = config.get('input_size', 640)
        self.confidence_threshold = config.get('confidence_threshold', 0.5)
        
        # 初始化标志
        self.models_initialized = False
        self.task_lock = threading.Lock()
        self.stopped_tasks = set()
        self.current_tasks = {}
        self.should_stop_realtime = False  # 添加停止实时监控的标志
        
        # 模型相关路径
        self.yolo_model_path = 'yolov8n.pt'
        self.slowfast_weights_path = 'SLOWFAST_8x8_R50_DETECTION.pyth'
        self.deepsort_weights_path = 'ckpt.t7'
        self.ava_labels_path = 'temp.pbtxt'
        
        # 模型对象
        self.yolo_model = None
        self.video_model = None
        self.deepsort_tracker = None
        self.ava_labelnames = None
        
        # 报警配置
        self.alert_behaviors = config.get('alert_behaviors', ['fall down', 'fight', 'enter', 'exit'])
        
    def initialize_models(self) -> bool:
        """
        初始化所有模型
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            print("正在初始化算法模型...")
            
            # 切换到算法目录
            original_cwd = os.getcwd()
            os.chdir(yolo_slowfast_path)
            
            # 初始化YOLO模型
            self.yolo_model = YOLO(self.yolo_model_path)
            print(f"✓ YOLO模型已加载: {self.yolo_model_path}")
            
            # 初始化SlowFast模型
            if os.path.exists(self.slowfast_weights_path):
                self.video_model = slowfast_r50_detection(False)
                checkpoint = torch.load(self.slowfast_weights_path, map_location=self.device)
                self.video_model.load_state_dict(checkpoint['model_state'])
                self.video_model = self.video_model.eval().to(self.device)
                print(f"✓ SlowFast模型已加载: {self.slowfast_weights_path}")
            else:
                print(f"⚠ SlowFast权重文件不存在，使用预训练模型: {self.slowfast_weights_path}")
                self.video_model = slowfast_r50_detection(True).eval().to(self.device)
            
            # 初始化DeepSort跟踪器
            if os.path.exists(self.deepsort_weights_path):
                self.deepsort_tracker = DeepSort(self.deepsort_weights_path)
                print(f"✓ DeepSort跟踪器已加载: {self.deepsort_weights_path}")
            else:
                # 如果绝对路径不存在，尝试相对路径
                relative_path = "deep_sort/deep_sort/deep/checkpoint/ckpt.t7"
                if os.path.exists(relative_path):
                    self.deepsort_tracker = DeepSort(relative_path)
                    print(f"✓ DeepSort跟踪器已加载: {relative_path}")
                else:
                    print(f"⚠ DeepSort权重文件不存在: {self.deepsort_weights_path}")
                    print(f"⚠ 相对路径也不存在: {relative_path}")
                    return False
            
            # 加载AVA标签
            if os.path.exists(self.ava_labels_path):
                self.ava_labelnames, _ = AvaLabeledVideoFramePaths.read_label_map(self.ava_labels_path)
                print(f"✓ AVA标签已加载: {self.ava_labels_path}")
            else:
                print(f"⚠ AVA标签文件不存在: {self.ava_labels_path}")
                return False
            
            # 初始化颜色映射
            self.color_map = [[random.randint(0, 255) for _ in range(3)] for _ in range(80)]
            
            # 恢复原始目录
            os.chdir(original_cwd)
            
            self.models_initialized = True
            print("✓ 所有模型初始化完成")
            return True
            
        except Exception as e:
            print(f"✗ 模型初始化失败: {e}")
            # 恢复原始目录
            try:
                os.chdir(original_cwd)
            except:
                pass
            return False
    
    def detect_video(self, video_path: str, output_path: str = None, 
                    progress_callback: callable = None) -> Dict[str, Any]:
        """
        检测视频文件
        
        Args:
            video_path: 视频文件路径
            output_path: 输出视频路径
            progress_callback: 进度回调函数
            
        Returns:
            Dict: 检测结果
        """
        if not self.models_initialized:
            if not self.initialize_models():
                return {'success': False, 'error': '模型初始化失败'}
        
        try:
            # 创建任务ID
            task_id = f"video_{int(time.time())}"
            
            # 转换为绝对路径（在切换目录前）
            video_path = os.path.abspath(video_path)
            if output_path:
                output_path = os.path.abspath(output_path)
            
            # 检查视频文件是否存在
            if not os.path.exists(video_path):
                return {'success': False, 'error': f'视频文件不存在: {video_path}'}
            
            # 切换到算法目录
            original_cwd = os.getcwd()
            os.chdir(yolo_slowfast_path)
            
            # 准备检测参数
            config = type('Config', (), {})()
            config.input = video_path
            config.output = output_path or ''
            config.imsize = self.input_size
            config.device = self.device
            config.show = False
            config.conf = self.confidence_threshold
            config.iou = 0.4
            config.classes = None
            
            # 存储任务信息
            with self.task_lock:
                self.current_tasks[task_id] = {
                    'type': 'video',
                    'status': 'running',
                    'start_time': time.time(),
                    'progress': 0.0
                }
            
            # 执行检测
            results = self._run_detection(config, task_id, progress_callback)
            
            # 恢复原始目录
            os.chdir(original_cwd)
            
            # 更新任务状态
            with self.task_lock:
                if task_id in self.current_tasks:
                    self.current_tasks[task_id]['status'] = 'completed'
                    self.current_tasks[task_id]['end_time'] = time.time()
            
            return {
                'success': True,
                'task_id': task_id,
                'results': results,
                'output_path': output_path
            }
            
        except Exception as e:
            # 恢复原始目录
            try:
                os.chdir(original_cwd)
            except:
                pass
            
            # 更新任务状态
            with self.task_lock:
                if task_id in self.current_tasks:
                    self.current_tasks[task_id]['status'] = 'failed'
                    self.current_tasks[task_id]['error'] = str(e)
            
            return {'success': False, 'error': str(e)}
    
    def start_realtime_detection(self, source: int = 0, 
                                websocket_callback: callable = None) -> str:
        """
        启动实时检测
        
        Args:
            source: 摄像头ID
            websocket_callback: WebSocket回调函数
            
        Returns:
            str: 任务ID
        """
        if not self.models_initialized:
            if not self.initialize_models():
                raise Exception('模型初始化失败')
        
        task_id = f"realtime_{int(time.time())}"
        
        def realtime_worker():
            try:
                # 切换到算法目录
                original_cwd = os.getcwd()
                os.chdir(yolo_slowfast_path)
                
                # 准备检测参数
                config = type('Config', (), {})()
                config.input = source
                config.output = ''
                config.imsize = self.input_size
                config.device = self.device
                config.show = False
                config.conf = self.confidence_threshold
                config.iou = 0.4
                config.classes = None
                
                # 存储任务信息
                with self.task_lock:
                    self.current_tasks[task_id] = {
                        'type': 'realtime',
                        'status': 'running',
                        'start_time': time.time(),
                        'source': source
                    }
                
                # 执行实时检测
                self._run_realtime_detection(config, task_id, websocket_callback)
                
                # 恢复原始目录
                os.chdir(original_cwd)
                
            except Exception as e:
                print(f"实时检测错误: {e}")
                # 恢复原始目录
                try:
                    os.chdir(original_cwd)
                except:
                    pass
                
                # 更新任务状态
                with self.task_lock:
                    if task_id in self.current_tasks:
                        self.current_tasks[task_id]['status'] = 'failed'
                        self.current_tasks[task_id]['error'] = str(e)
        
        # 启动实时检测线程
        thread = threading.Thread(target=realtime_worker, daemon=True)
        thread.start()
        
        return task_id

    def generate_realtime_frames(self, source: Any):
        """
        生成实时视频帧流，用于HTTP视频流传输
        这是从 behavior_identify 项目迁移的功能

        Args:
            source: 视频源（摄像头ID或视频文件路径）

        Yields:
            bytes: JPEG格式的视频帧数据
        """
        print(f"开始生成实时视频帧流，视频源: {source}")

        # 重置停止标志
        self.should_stop_realtime = False

        if not self.models_initialized:
            print("模型未初始化，尝试初始化...")
            if not self.initialize_models():
                print("模型初始化失败，无法生成视频帧")
                return

        try:
            # 切换到算法目录
            original_cwd = os.getcwd()
            os.chdir(yolo_slowfast_path)

            # 确保导入必要的模块
            from yolo_slowfast import MyVideoCapture, ava_inference_transform, deepsort_update, plot_one_box

            # 处理视频源参数
            if source == '0' or source == 0:
                source = 0  # 摄像头
            elif isinstance(source, str) and source.isdigit():
                source = int(source)  # 摄像头ID

            print(f"处理后的视频源: {source}, 类型: {type(source)}")

            # 初始化视频捕获
            cap = MyVideoCapture(source)
            id_to_ava_labels = {}

            # 颜色映射
            import random
            coco_color_map = [[random.randint(0, 255) for _ in range(3)] for _ in range(80)]

            # clip 队列和动作识别线程
            clip_queue = queue.Queue()
            result_queue = queue.Queue()

            def slowfast_worker():
                # 仅当使用GPU时才创建独立的CUDA流
                import contextlib
                stream = torch.cuda.Stream() if 'cuda' in str(self.device) else None
                context_manager = torch.cuda.stream(stream) if stream else contextlib.nullcontext()

                while True:
                    # 检查停止信号
                    if self.should_stop_realtime:
                        print("SlowFast worker收到停止信号，退出...")
                        break

                    try:
                        # 使用超时获取任务，避免无限等待
                        item = clip_queue.get(timeout=1.0)
                        if item is None:
                            break
                    except:
                        # 超时或其他异常，继续检查停止信号
                        continue

                    idx, clip, pred_result = item

                    # 再次检查停止信号
                    if self.should_stop_realtime:
                        print("SlowFast worker在处理前收到停止信号，退出...")
                        clip_queue.task_done()
                        break

                    with context_manager:
                        if pred_result.pred[0].shape[0]:
                            inputs, inp_boxes, _ = ava_inference_transform(clip, pred_result.pred[0][:, 0:4], crop_size=self.input_size)
                            inp_boxes = torch.cat([torch.zeros(inp_boxes.shape[0], 1), inp_boxes], dim=1)
                            if isinstance(inputs, list):
                                inputs = [inp.unsqueeze(0).to(self.device, non_blocking=True) for inp in inputs]
                            else:
                                inputs = inputs.unsqueeze(0).to(self.device, non_blocking=True)

                            inp_boxes_gpu = inp_boxes.to(self.device, non_blocking=True)

                            with torch.no_grad():
                                slowfaster_preds = self.video_model(inputs, inp_boxes_gpu)

                            # 修复数据类型转换问题 - 确保正确的数据类型转换
                            slowfaster_preds_cpu = slowfaster_preds.cpu().float()  # 确保为float类型
                            pred_labels = torch.argmax(slowfaster_preds_cpu, dim=1).numpy().astype(np.int32)
                            track_ids = pred_result.pred[0][:, 5].astype(np.int32)

                            result_queue.put((idx, track_ids.tolist(), pred_labels.tolist()))
                    clip_queue.task_done()

                print("SlowFast worker线程已退出")

            # 启动动作识别工作线程
            threading.Thread(target=slowfast_worker, daemon=True).start()

            # 主处理循环
            while not cap.end and not self.should_stop_realtime:
                ret, img = cap.read()
                if not ret:
                    continue

                # 检查是否需要停止
                if self.should_stop_realtime:
                    print("收到停止信号，正在退出实时监控...")
                    break

                # YOLO检测
                results = self.yolo_model.predict(source=img, imgsz=self.input_size, device=self.device, verbose=False)
                boxes = results[0].boxes  # YOLOv8 Results object

                # 处理YOLO检测结果
                if boxes is not None and len(boxes) > 0:
                    # 再次检查停止信号
                    if self.should_stop_realtime:
                        print("在YOLO处理阶段收到停止信号，退出...")
                        break

                    pred_xyxy = boxes.xyxy.cpu().numpy()
                    pred_conf = boxes.conf.cpu().numpy().reshape(-1, 1)
                    pred_cls = boxes.cls.cpu().numpy().reshape(-1, 1)

                    pred = np.hstack((pred_xyxy, pred_conf, pred_cls))
                    xywh = np.hstack(((pred[:, 0:2] + pred[:, 2:4]) / 2, pred[:, 2:4] - pred[:, 0:2]))

                    # DeepSort跟踪
                    temp = deepsort_update(self.deepsort_tracker, pred, xywh, img)
                    temp = temp if len(temp) else np.ones((0, 8)).astype(np.float32)

                    # 再次检查停止信号
                    if self.should_stop_realtime:
                        print("在DeepSort处理阶段收到停止信号，退出...")
                        break

                    # 格式化检测结果
                    pred_result = type("YoloPred", (), {})()
                    pred_result.ims = [img]
                    pred_result.pred = [temp.astype(np.float32)]
                    pred_result.names = self.yolo_model.names

                    # 行为识别（SlowFast） - 当积累了25帧时
                    if len(cap.stack) == 25:
                        clip = cap.get_video_clip()
                        clip_queue.put((cap.idx, clip, pred_result))

                    # 处理动作识别结果
                    while not result_queue.empty():
                        try:
                            _, tids, avalabels = result_queue.get_nowait()
                            for tid, avalabel in zip(tids, avalabels):
                                id_to_ava_labels[tid] = self.ava_labelnames[avalabel + 1]
                        except queue.Empty:
                            break

                    # 再次检查停止信号
                    if self.should_stop_realtime:
                        print("在结果处理阶段收到停止信号，退出...")
                        break

                    # 绘制检测结果 - 使用与behavior_identify相同的逻辑
                    annotated_frame = img.copy()
                    for _, pred in enumerate(pred_result.pred):
                        if pred.shape[0]:
                            for _, (*box, cls, trackid, _, _) in enumerate(pred):
                                if int(cls) != 0:
                                    ava_label = ''
                                elif trackid in id_to_ava_labels.keys():
                                    ava_label = id_to_ava_labels[trackid].split(' ')[0]
                                else:
                                    ava_label = 'Unknown'
                                text = '{} {} {}'.format(int(trackid), pred_result.names[int(cls)], ava_label)
                                color = coco_color_map[int(cls)]
                                annotated_frame = plot_one_box(box, annotated_frame, color, text)

                    # 使用绘制后的帧
                    img = annotated_frame

                # 编码为JPEG
                ret, buffer = cv2.imencode('.jpg', img)
                if ret:
                    frame = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

                # 控制帧率
                time.sleep(0.033)  # 约30FPS

        except Exception as e:
            print(f"生成视频帧时出错: {e}")
        finally:
            # 清理资源
            try:
                clip_queue.put(None)  # 停止工作线程
                cap.release()
                os.chdir(original_cwd)
            except:
                pass
            print("视频帧生成结束")

    def stop_realtime_detection(self, task_id: str) -> bool:
        """
        停止实时检测

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功停止
        """
        with self.task_lock:
            if task_id in self.current_tasks:
                self.current_tasks[task_id]['status'] = 'stopped'
                return True
        return False

    def stop_realtime_monitoring(self):
        """停止所有实时监控"""
        print("收到停止实时监控请求")
        self.should_stop_realtime = True

        # 停止所有当前任务
        with self.task_lock:
            for task_id in list(self.current_tasks.keys()):
                if self.current_tasks[task_id]['status'] == 'running':
                    self.current_tasks[task_id]['status'] = 'stopped'
                    print(f"停止任务: {task_id}")

        print("实时监控已停止")
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict: 任务状态信息
        """
        with self.task_lock:
            return self.current_tasks.get(task_id, {'status': 'not_found'})
    
    def _run_detection(self, config, task_id: str, progress_callback: callable = None) -> List[Dict]:
        """
        执行检测的核心逻辑（基于现有算法）
        """
        results = []
        
        try:
            # 使用现有的main函数逻辑，但进行了修改以支持回调
            cap = MyVideoCapture(config.input)
            id_to_ava_labels = {}
            
            total_frames = int(cap.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            processed_frames = 0
            
            # 设置输出视频 - 修复编解码器问题
            outputvideo = None
            if config.output:
                video = cv2.VideoCapture(config.input)
                width, height = int(video.get(3)), int(video.get(4))
                fps = int(video.get(cv2.CAP_PROP_FPS)) or 25
                video.release()
                
                # 确保输出目录存在
                os.makedirs(os.path.dirname(config.output), exist_ok=True)
                
                # 使用浏览器兼容的MP4格式，优先尝试H.264编解码器
                output_mp4 = config.output.replace('.avi', '.mp4')
                
                # 尝试不同的编解码器，优先使用浏览器兼容性最好的
                codecs_to_try = [
                    ('avc1', 'H.264 (最佳浏览器兼容性)'),
                    ('h264', 'H.264'),
                    ('mp4v', 'MPEG-4'),
                ]
                
                outputvideo = None
                used_codec = None
                
                for codec, desc in codecs_to_try:
                    try:
                        fourcc = cv2.VideoWriter_fourcc(*codec)
                        test_writer = cv2.VideoWriter(output_mp4, fourcc, fps, (width, height))
                        
                        if test_writer.isOpened():
                            outputvideo = test_writer
                            used_codec = f"{codec} ({desc})"
                            config.output = output_mp4
                            print(f"✓ 使用 {used_codec} 编解码器输出: {output_mp4}")
                            break
                        else:
                            test_writer.release()
                    except Exception as e:
                        print(f"⚠ {codec} 编解码器失败: {e}")
                        continue
                
                # 如果所有MP4编解码器都失败，回退到AVI
                if not outputvideo or not outputvideo.isOpened():
                    print("⚠ 所有MP4编解码器失败，回退到AVI格式")
                    fourcc = cv2.VideoWriter_fourcc(*'XVID')
                    outputvideo = cv2.VideoWriter(config.output, fourcc, fps, (width, height))
                    if outputvideo.isOpened():
                        used_codec = "XVID (AVI)"
                        print(f"✓ 使用 {used_codec} 编解码器")
                    else:
                        print("❌ 所有视频编解码器都失败")
                        outputvideo = None
            
            while not cap.end:
                ret, img = cap.read()
                if not ret:
                    continue
                
                processed_frames += 1
                
                # YOLO检测
                yolo_results = self.yolo_model.predict(
                    source=img, 
                    imgsz=config.imsize, 
                    device=config.device, 
                    verbose=False
                )
                boxes = yolo_results[0].boxes
                
                # 处理检测结果
                if len(boxes) > 0:
                    pred_xyxy = boxes.xyxy.cpu().numpy()
                    pred_conf = boxes.conf.cpu().numpy().reshape(-1, 1)
                    pred_cls = boxes.cls.cpu().numpy().reshape(-1, 1)
                    
                    pred = np.hstack((pred_xyxy, pred_conf, pred_cls))
                    xywh = np.hstack(((pred[:, 0:2] + pred[:, 2:4]) / 2, pred[:, 2:4] - pred[:, 0:2]))
                    
                    # DeepSort跟踪
                    temp = deepsort_update(self.deepsort_tracker, pred, xywh, img)
                    temp = temp if len(temp) else np.ones((0, 8)).astype(np.float32)
                    
                                    # 行为识别（SlowFast） - 先进行行为识别再绘制视频帧
                if len(cap.stack) == 25:
                    clip = cap.get_video_clip()
                    if temp.shape[0] > 0:
                        try:
                            # 获取边界框位置（前4列）
                            boxes = temp[:, 0:4].astype(np.float32)
                            track_ids = temp[:, 5].astype(np.int32)  # 跟踪ID在第5列
                            
                            inputs, inp_boxes, _ = ava_inference_transform(clip, boxes, crop_size=config.imsize)
                            
                            # 修复数据类型问题
                            inp_boxes = inp_boxes.float()  # 确保为float类型
                            inp_boxes = torch.cat([torch.zeros(inp_boxes.shape[0], 1), inp_boxes], dim=1)
                            
                            if isinstance(inputs, list):
                                inputs = [inp.unsqueeze(0).to(self.device) for inp in inputs]
                            else:
                                inputs = inputs.unsqueeze(0).to(self.device)
                            
                            with torch.no_grad():
                                slowfaster_preds = self.video_model(inputs, inp_boxes.to(self.device))
                            
                            # 获取预测结果
                            pred_labels = torch.argmax(slowfaster_preds.cpu(), axis=1).numpy()
                            
                            # 更新行为标签映射
                            for tid, avalabel in zip(track_ids, pred_labels):
                                if avalabel < len(self.ava_labelnames):
                                    id_to_ava_labels[int(tid)] = self.ava_labelnames[avalabel + 1]
                                    
                            print(f"✓ SlowFast检测到{len(pred_labels)}个行为，更新标签映射")
                            
                        except Exception as e:
                            print(f"SlowFast处理错误: {e}")
                            import traceback
                            traceback.print_exc()

                # 创建可视化图像 - 在行为识别完成后绘制
                vis_img = img.copy()
                cv2.putText(vis_img, f'Frame: {processed_frames}', 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # 存储检测结果并绘制（包含最新的行为信息）
                for detection in temp:
                    if len(detection) >= 7:
                        x1, y1, x2, y2 = int(detection[0]), int(detection[1]), int(detection[2]), int(detection[3])
                        class_id = int(detection[4])  # 这是YOLO的类别ID
                        track_id = int(detection[5])  # 这是DeepSort的跟踪ID
                        confidence = float(detection[6])
                        
                        # 映射YOLO类别ID到类别名称
                        object_type = 'unknown'
                        if 0 <= class_id < len(self.coco_names):
                            object_type = self.coco_names[class_id]
                        
                        # 获取最新的行为标签
                        behavior_type = id_to_ava_labels.get(track_id, 'walking')
                        
                        # 绘制边界框
                        color = (0, 0, 255) if self._is_anomaly_behavior(behavior_type) else (0, 255, 0)
                        cv2.rectangle(vis_img, (x1, y1), (x2, y2), color, 2)
                        
                        # 绘制对象标签（包含行为信息）
                        label1 = f"ID:{track_id} {object_type}"
                        label2 = f"Action: {behavior_type}"  # 使用英文避免中文乱码
                        
                        cv2.putText(vis_img, label1, (x1, y1-25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                        cv2.putText(vis_img, label2, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        
                        result = {
                            'frame_number': processed_frames,
                            'timestamp': processed_frames / 25.0,
                            'object_id': track_id,
                            'object_type': object_type,
                            'confidence': confidence,
                            'bbox': {
                                'x1': float(detection[0]),
                                'y1': float(detection[1]),
                                'x2': float(detection[2]),
                                'y2': float(detection[3])
                            },
                            'behavior_type': behavior_type,
                            'is_anomaly': self._is_anomaly_behavior(behavior_type)
                        }
                        results.append(result)
                
                # 写入视频帧（修复帧格式问题）
                if outputvideo and outputvideo.isOpened():
                    # 确保帧尺寸正确
                    if vis_img.shape[:2] != (height, width):
                        vis_img = cv2.resize(vis_img, (width, height))
                    
                    # 确保帧格式正确（BGR）
                    if len(vis_img.shape) == 3 and vis_img.shape[2] == 3:
                        success = outputvideo.write(vis_img)
                        if not success:
                            print(f"⚠ 写入视频帧失败: 帧 {processed_frames}, 尺寸: {vis_img.shape}")
                    else:
                        print(f"⚠ 帧格式错误: {vis_img.shape}")
                        # 转换为BGR格式
                        if len(vis_img.shape) == 2:
                            vis_img = cv2.cvtColor(vis_img, cv2.COLOR_GRAY2BGR)
                        success = outputvideo.write(vis_img)
                
                # 更新进度
                if progress_callback and total_frames > 0:
                    progress = (processed_frames / total_frames) * 100
                    progress_callback(task_id, progress)
                
                # 检查任务是否被停止
                with self.task_lock:
                    if task_id in self.current_tasks and self.current_tasks[task_id]['status'] == 'stopped':
                        break
            
            # 清理资源
            cap.release()
            if outputvideo:
                outputvideo.release()
            
                # 检查输出文件
                if os.path.exists(config.output):
                    file_size = os.path.getsize(config.output)
                    print(f"✓ 视频保存成功: {config.output} ({file_size} bytes)")
                else:
                    print(f"❌ 输出文件未生成: {config.output}")
            
        except Exception as e:
            print(f"检测过程错误: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            
            # 确保资源清理
            try:
                if 'cap' in locals() and cap:
                    cap.release()
            except:
                pass
            
            try:
                if 'outputvideo' in locals() and outputvideo:
                    outputvideo.release()
            except:
                pass
            
            # 返回错误信息而不是重新抛出异常
            return []
        
        return results
    
    def _run_realtime_detection(self, config, task_id: str, websocket_callback: callable = None):
        """
        执行实时检测的核心逻辑
        """
        try:
            cap = MyVideoCapture(config.input)
            id_to_ava_labels = {}
            frame_count = 0
            
            while not cap.end:
                # 检查任务状态
                with self.task_lock:
                    if task_id in self.current_tasks and self.current_tasks[task_id]['status'] != 'running':
                        break
                
                ret, img = cap.read()
                if not ret:
                    continue
                
                frame_count += 1
                
                # YOLO检测
                yolo_results = self.yolo_model.predict(
                    source=img, 
                    imgsz=config.imsize, 
                    device=config.device, 
                    verbose=False
                )
                boxes = yolo_results[0].boxes
                
                # 处理检测结果
                detections = []
                if len(boxes) > 0:
                    pred_xyxy = boxes.xyxy.cpu().numpy()
                    pred_conf = boxes.conf.cpu().numpy().reshape(-1, 1)
                    pred_cls = boxes.cls.cpu().numpy().reshape(-1, 1)
                    
                    pred = np.hstack((pred_xyxy, pred_conf, pred_cls))
                    xywh = np.hstack(((pred[:, 0:2] + pred[:, 2:4]) / 2, pred[:, 2:4] - pred[:, 0:2]))
                    
                    # DeepSort跟踪
                    temp = deepsort_update(self.deepsort_tracker, pred, xywh, img)
                    temp = temp if len(temp) else np.ones((0, 8)).astype(np.float32)
                    
                    # 格式化检测结果
                    for detection in temp:
                        if len(detection) >= 7:
                            detection_data = {
                                'frame_number': frame_count,
                                'timestamp': time.time(),
                                'object_id': int(detection[4]),
                                'object_type': 'person',
                                'confidence': float(detection[6]),
                                'bbox': {
                                    'x1': float(detection[0]),
                                    'y1': float(detection[1]),
                                    'x2': float(detection[2]),
                                    'y2': float(detection[3])
                                },
                                'behavior_type': id_to_ava_labels.get(int(detection[4]), 'unknown'),
                                'is_anomaly': False
                            }
                            detections.append(detection_data)
                    
                    # 行为识别（SlowFast）
                    if len(cap.stack) == 25:
                        clip = cap.get_video_clip()
                        if temp.shape[0] > 0:
                            try:
                                inputs, inp_boxes, _ = ava_inference_transform(clip, temp[:, 0:4], crop_size=config.imsize)
                                inp_boxes = torch.cat([torch.zeros(inp_boxes.shape[0], 1), inp_boxes], dim=1)
                                
                                if isinstance(inputs, list):
                                    inputs = [inp.unsqueeze(0).to(config.device) for inp in inputs]
                                else:
                                    inputs = inputs.unsqueeze(0).to(config.device)
                                
                                with torch.no_grad():
                                    slowfaster_preds = self.video_model(inputs, inp_boxes.to(config.device))
                                
                                for tid, avalabel in zip(temp[:, 5].tolist(), np.argmax(slowfaster_preds.cpu(), axis=1).tolist()):
                                    behavior = self.ava_labelnames[avalabel + 1]
                                    id_to_ava_labels[tid] = behavior
                                    
                                    # 更新检测结果中的行为信息
                                    for det in detections:
                                        if det['object_id'] == tid:
                                            det['behavior_type'] = behavior
                                            det['is_anomaly'] = self._is_anomaly_behavior(behavior)
                            except Exception as e:
                                print(f"实时SlowFast处理错误: {e}")
                
                # 发送实时结果
                if websocket_callback and detections:
                    websocket_callback({
                        'type': 'detection_result',
                        'task_id': task_id,
                        'frame_number': frame_count,
                        'timestamp': time.time(),
                        'detections': detections
                    })
                
                # 检查异常行为并发送报警
                for detection in detections:
                    if detection['is_anomaly'] and websocket_callback:
                        websocket_callback({
                            'type': 'alert',
                            'task_id': task_id,
                            'alert_type': detection['behavior_type'],
                            'detection': detection
                        })
                
                # 控制帧率
                time.sleep(0.04)  # 约25 FPS
            
            # 清理资源
            cap.release()
            
        except Exception as e:
            print(f"实时检测错误: {e}")
            raise e
    
    def _is_anomaly_behavior(self, behavior: str) -> bool:
        """
        判断是否为异常行为
        
        Args:
            behavior: 行为名称
            
        Returns:
            bool: 是否为异常行为
        """
        if not behavior:
            return False
        
        behavior_lower = behavior.lower()
        return any(alert_behavior.lower() in behavior_lower for alert_behavior in self.alert_behaviors)
    
    def get_supported_behaviors(self) -> List[str]:
        """
        获取支持的行为类型列表
        
        Returns:
            List[str]: 行为类型列表
        """
        if self.ava_labelnames:
            return list(self.ava_labelnames.values())
        return []
    
    def update_config(self, new_config: Dict[str, Any]):
        """
        更新配置参数
        
        Args:
            new_config: 新的配置参数
        """
        self.config.update(new_config)
        
        # 更新相关参数
        if 'device' in new_config:
            self.device = new_config['device']
        if 'input_size' in new_config:
            self.input_size = new_config['input_size']
        if 'confidence_threshold' in new_config:
            self.confidence_threshold = new_config['confidence_threshold']
        if 'alert_behaviors' in new_config:
            self.alert_behaviors = new_config['alert_behaviors']


# 全局检测服务实例
detection_service = None

def get_detection_service(config: Dict[str, Any] = None) -> BehaviorDetectionService:
    """
    获取检测服务实例（单例模式）
    
    Args:
        config: 配置参数
        
    Returns:
        BehaviorDetectionService: 检测服务实例
    """
    global detection_service
    if detection_service is None:
        detection_service = BehaviorDetectionService(config)
    return detection_service 