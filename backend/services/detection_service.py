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
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化检测服务
        
        Args:
            config: 配置参数字典
        """
        self.config = config or {}
        self.device = self.config.get('device', 'cpu')
        self.imsize = self.config.get('input_size', 640)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.5)
        
        # 模型路径配置
        self.yolo_model_path = self.config.get('yolo_model_path', 'yolov8n.pt')
        self.slowfast_weights_path = self.config.get('slowfast_weights_path', 'SLOWFAST_8x8_R50_DETECTION.pyth')
        self.deepsort_weights_path = self.config.get('deepsort_weights_path', 'deep_sort/deep_sort/deep/checkpoint/ckpt.t7')
        self.ava_labels_path = self.config.get('ava_labels_path', 'selfutils/temp.pbtxt')
        
        # 算法模型
        self.yolo_model = None
        self.video_model = None
        self.deepsort_tracker = None
        self.ava_labelnames = None
        self.color_map = None
        
        # 运行状态
        self.is_initialized = False
        self.current_tasks = {}  # 当前运行的任务
        self.task_lock = threading.Lock()
        
        # 报警配置
        self.alert_behaviors = self.config.get('alert_behaviors', ['fall down', 'fight', 'enter', 'exit'])
        
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
                print(f"⚠ DeepSort权重文件不存在: {self.deepsort_weights_path}")
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
            
            self.is_initialized = True
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
        if not self.is_initialized:
            if not self.initialize_models():
                return {'success': False, 'error': '模型初始化失败'}
        
        try:
            # 创建任务ID
            task_id = f"video_{int(time.time())}"
            
            # 切换到算法目录
            original_cwd = os.getcwd()
            os.chdir(yolo_slowfast_path)
            
            # 准备检测参数
            config = type('Config', (), {})()
            config.input = video_path
            config.output = output_path or ''
            config.imsize = self.imsize
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
        if not self.is_initialized:
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
                config.imsize = self.imsize
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
            
            # 设置输出视频
            outputvideo = None
            if config.output:
                video = cv2.VideoCapture(config.input)
                width, height = int(video.get(3)), int(video.get(4))
                video.release()
                outputvideo = cv2.VideoWriter(
                    config.output, 
                    cv2.VideoWriter_fourcc(*"mp4v"), 
                    25, 
                    (width, height)
                )
            
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
                    
                    # 存储检测结果
                    for detection in temp:
                        if len(detection) >= 7:
                            result = {
                                'frame_number': processed_frames,
                                'timestamp': processed_frames / 25.0,
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
                                'is_anomaly': self._is_anomaly_behavior(id_to_ava_labels.get(int(detection[4]), ''))
                            }
                            results.append(result)
                    
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
                                    id_to_ava_labels[tid] = self.ava_labelnames[avalabel + 1]
                            except Exception as e:
                                print(f"SlowFast处理错误: {e}")
                
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
            self.imsize = new_config['input_size']
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