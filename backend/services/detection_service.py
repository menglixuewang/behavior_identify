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
        # 设备配置 - 修复GPU检测
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

        # 打印接收到的配置信息
        print(f"🔧 检测服务配置:")
        print(f"   - 设备: {self.device}")
        print(f"   - 输入尺寸: {self.input_size}")
        print(f"   - 置信度阈值: {self.confidence_threshold}")

        # 初始化标志
        self.models_initialized = False
        self.task_lock = threading.Lock()
        self.stopped_tasks = set()
        self.current_tasks = {}  # 当前运行的任务，保持兼容性

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

        # 报警配置 - 默认只对最重要的三种异常行为报警
        self.alert_behaviors = config.get('alert_behaviors', ['fall down', 'fight', 'enter'])
        self.output_format = config.get('output_format', 'both')
        self.save_results = config.get('save_results', True)

        # 创建前端选项与AVA标签的映射关系
        self.behavior_mapping = {
            'fall down': ['fall down'],
            'fight': ['fight/hit (a person)', 'martial art', 'kick (a person)', 'grab (a person)'],
            'enter': ['enter'],
            'exit': ['exit'],
            'run': ['run'],
            'sit': ['sit'],  # 注意：AVA中有两个sit标签(id:11和id:49)
            'stand': ['stand'],  # 注意：AVA中有两个stand标签(id:12和id:80)
            'walk': ['walk']
        }

        print(f"   - 报警行为: {self.alert_behaviors}")
        print(f"   - 输出格式: {self.output_format}")
        print(f"   - 保存结果: {self.save_results}")
        print(f"   - 行为映射: {self.behavior_mapping}")
        
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
        print(f"🎬 开始视频检测")
        print(f"📁 输入视频: {video_path}")
        print(f"📁 输出视频: {output_path}")
        print(f"🔧 检测参数: 设备={self.device}, 尺寸={self.input_size}, 置信度={self.confidence_threshold}")
        print(f"🚨 报警行为: {self.alert_behaviors}")
        print(f"💾 输出格式: {self.output_format}")
        print(f"💾 保存结果: {self.save_results}")

        if not self.models_initialized:
            print("🔄 模型未初始化，开始初始化...")
            if not self.initialize_models():
                print("❌ 模型初始化失败")
                return {'success': False, 'error': '模型初始化失败'}
            print("✅ 模型初始化成功")

        try:
            # 创建任务ID
            task_id = f"video_{int(time.time())}"
            print(f"🆔 任务ID: {task_id}")

            # 转换为绝对路径（在切换目录前）
            video_path = os.path.abspath(video_path)
            if output_path:
                output_path = os.path.abspath(output_path)

            print(f"📁 绝对路径 - 输入: {video_path}")
            print(f"📁 绝对路径 - 输出: {output_path}")

            # 检查视频文件是否存在
            if not os.path.exists(video_path):
                print(f"❌ 视频文件不存在: {video_path}")
                return {'success': False, 'error': f'视频文件不存在: {video_path}'}

            # 获取视频文件信息
            file_size = os.path.getsize(video_path)
            print(f"📊 视频文件大小: {file_size} bytes ({file_size/1024/1024:.2f} MB)")

            # 切换到算法目录
            original_cwd = os.getcwd()
            print(f"📂 当前目录: {original_cwd}")
            os.chdir(yolo_slowfast_path)
            print(f"📂 切换到算法目录: {yolo_slowfast_path}")

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

            print(f"⚙️ 算法配置:")
            print(f"   - input: {config.input}")
            print(f"   - output: {config.output}")
            print(f"   - imsize: {config.imsize}")
            print(f"   - device: {config.device}")
            print(f"   - conf: {config.conf}")
            print(f"   - iou: {config.iou}")
            
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
            raise e
        
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
        判断是否为异常行为（使用精确映射，排除正常行为）

        Args:
            behavior: 行为名称（来自AVA数据集）

        Returns:
            bool: 是否为异常行为
        """
        if not behavior:
            return False

        behavior_lower = behavior.lower().strip()

        # 强制排除的正常行为（即使用户选择了也不报警）
        normal_behaviors = ['walk', 'sit', 'stand', 'run']
        if behavior_lower in normal_behaviors:
            print(f"ℹ️ 行为 '{behavior}' 是正常行为，不触发报警")
            return False

        print(f"🔍 当前报警行为配置: {self.alert_behaviors}")
        print(f"🔍 检测到的行为: '{behavior}'")

        # 遍历用户选择的报警行为
        for alert_behavior in self.alert_behaviors:
            alert_behavior_lower = alert_behavior.lower().strip()

            # 再次检查是否为正常行为
            if alert_behavior_lower in normal_behaviors:
                print(f"⚠️ 跳过正常行为配置: '{alert_behavior}'")
                continue

            # 获取该报警行为对应的AVA标签列表
            mapped_behaviors = self.behavior_mapping.get(alert_behavior_lower, [alert_behavior_lower])

            # 检查当前检测到的行为是否匹配任何映射的AVA标签
            for mapped_behavior in mapped_behaviors:
                mapped_behavior_lower = mapped_behavior.lower().strip()
                if behavior_lower == mapped_behavior_lower or mapped_behavior_lower in behavior_lower:
                    print(f"🚨 检测到报警行为: '{behavior}' 匹配用户设置的 '{alert_behavior}'")
                    return True

        # 如果没有匹配，记录调试信息
        print(f"ℹ️ 行为 '{behavior}' 不在报警列表中")
        return False
    
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
    获取检测服务实例（支持配置更新）

    Args:
        config: 配置参数

    Returns:
        BehaviorDetectionService: 检测服务实例
    """
    global detection_service

    # 如果没有配置参数，使用默认配置
    if config is None:
        config = {
            'device': 'cpu',
            'input_size': 640,
            'confidence_threshold': 0.5,
            'alert_behaviors': ['fall down', 'fight', 'enter'],  # 默认只对最重要的三种异常行为报警
            'output_format': 'both',
            'save_results': True
        }

    print(f"🔧 get_detection_service 接收到的配置: {config}")

    # 如果服务不存在，创建新实例
    if detection_service is None:
        print("🆕 创建新的检测服务实例")
        detection_service = BehaviorDetectionService(config)
    else:
        # 如果服务已存在，更新配置
        print("🔄 更新现有检测服务配置")
        detection_service.device = config.get('device', detection_service.device)
        detection_service.input_size = config.get('input_size', detection_service.input_size)
        detection_service.confidence_threshold = config.get('confidence_threshold', detection_service.confidence_threshold)
        detection_service.alert_behaviors = config.get('alert_behaviors', detection_service.alert_behaviors)
        detection_service.output_format = config.get('output_format', detection_service.output_format)
        detection_service.save_results = config.get('save_results', detection_service.save_results)

        print(f"🔧 更新后的检测服务配置:")
        print(f"   - 设备: {detection_service.device}")
        print(f"   - 输入尺寸: {detection_service.input_size}")
        print(f"   - 置信度阈值: {detection_service.confidence_threshold}")
        print(f"   - 报警行为: {detection_service.alert_behaviors}")
        print(f"   - 输出格式: {detection_service.output_format}")
        print(f"   - 保存结果: {detection_service.save_results}")

    return detection_service