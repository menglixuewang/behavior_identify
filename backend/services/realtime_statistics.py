"""
实时监控统计服务
用于跟踪和统计实时监控过程中的检测结果、报警信息等数据
不影响视频上传处理的统计功能
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
import threading


class RealtimeStatistics:
    """实时监控统计类"""
    
    def __init__(self, alert_behaviors: List[str] = None):
        """
        初始化实时统计
        
        Args:
            alert_behaviors: 报警行为列表
        """
        self.alert_behaviors = alert_behaviors or ['fall down', 'fight', 'enter', 'exit']
        
        # 统计数据
        self.start_time = time.time()
        self.total_detections = 0
        self.total_alerts = 0
        self.frame_count = 0
        
        # 行为统计
        self.behavior_counts = defaultdict(int)
        self.alert_behavior_counts = defaultdict(int)
        
        # 最近检测结果（保留最近100个）
        self.recent_detections = deque(maxlen=100)
        self.recent_alerts = deque(maxlen=50)
        
        # 性能统计
        self.fps_history = deque(maxlen=30)  # 保留最近30秒的FPS
        self.processing_times = deque(maxlen=30)  # 保留最近30次的处理时间
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 行为名称映射
        self.behavior_names = {
            'fall down': '跌倒检测',
            'fight': '打斗行为', 
            'enter': '区域闯入',
            'exit': '区域离开',
            'run': '快速奔跑',
            'sit': '坐下行为',
            'stand': '站立行为',
            'walk': '正常行走'
        }
    
    def update_frame_stats(self, fps: float = 0, processing_time: float = 0):
        """
        更新帧统计信息
        
        Args:
            fps: 当前帧率
            processing_time: 处理时间（秒）
        """
        with self._lock:
            self.frame_count += 1
            
            if fps > 0:
                self.fps_history.append(fps)
            
            if processing_time > 0:
                self.processing_times.append(processing_time)
    
    def add_detections(self, detections: List[Dict[str, Any]]):
        """
        添加检测结果
        
        Args:
            detections: 检测结果列表
        """
        if not detections:
            return
            
        with self._lock:
            current_time = time.time()
            
            for detection in detections:
                self.total_detections += 1
                
                # 统计行为类型
                behavior_type = detection.get('behavior_type')
                if behavior_type:
                    self.behavior_counts[behavior_type] += 1
                
                # 检查是否为报警行为
                is_anomaly = detection.get('is_anomaly', False)
                if is_anomaly:
                    self.total_alerts += 1
                    if behavior_type:
                        self.alert_behavior_counts[behavior_type] += 1
                    
                    # 添加到最近报警列表
                    alert_info = {
                        'timestamp': current_time,
                        'behavior_type': behavior_type,
                        'confidence': detection.get('confidence', 0),
                        'bbox': detection.get('bbox', []),
                        'object_id': detection.get('object_id')
                    }
                    self.recent_alerts.append(alert_info)
                
                # 添加到最近检测列表
                detection_info = {
                    'timestamp': current_time,
                    'behavior_type': behavior_type,
                    'confidence': detection.get('confidence', 0),
                    'is_anomaly': is_anomaly,
                    'object_id': detection.get('object_id')
                }
                self.recent_detections.append(detection_info)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取当前统计数据
        
        Returns:
            Dict: 统计数据字典
        """
        with self._lock:
            current_time = time.time()
            runtime_seconds = int(current_time - self.start_time)
            
            # 计算运行时长
            hours = runtime_seconds // 3600
            minutes = (runtime_seconds % 3600) // 60
            seconds = runtime_seconds % 60
            runtime_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # 计算平均FPS
            avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
            
            # 计算平均处理时间
            avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
            
            # 行为统计数据
            behavior_stats = []
            for behavior, count in self.behavior_counts.items():
                behavior_stats.append({
                    'behavior_type': behavior,
                    'behavior_name': self.behavior_names.get(behavior, behavior),
                    'count': count,
                    'alert_count': self.alert_behavior_counts.get(behavior, 0),
                    'is_alert_behavior': behavior in self.alert_behaviors
                })
            
            # 最近报警信息
            recent_alerts_info = []
            for alert in list(self.recent_alerts)[-10:]:  # 最近10个报警
                alert_time = datetime.fromtimestamp(alert['timestamp'])
                recent_alerts_info.append({
                    'behavior_type': alert['behavior_type'],
                    'behavior_name': self.behavior_names.get(alert['behavior_type'], alert['behavior_type']),
                    'confidence': alert['confidence'],
                    'time': alert_time.strftime('%H:%M:%S'),
                    'object_id': alert['object_id']
                })
            
            return {
                'runtime_seconds': runtime_seconds,
                'runtime_text': runtime_text,
                'total_detections': self.total_detections,
                'total_alerts': self.total_alerts,
                'frame_count': self.frame_count,
                'avg_fps': round(avg_fps, 1),
                'avg_processing_time': round(avg_processing_time * 1000, 1),  # 转换为毫秒
                'behavior_stats': behavior_stats,
                'recent_alerts': recent_alerts_info,
                'alert_behaviors': self.alert_behaviors
            }
    
    def reset(self):
        """重置统计数据"""
        with self._lock:
            self.start_time = time.time()
            self.total_detections = 0
            self.total_alerts = 0
            self.frame_count = 0
            self.behavior_counts.clear()
            self.alert_behavior_counts.clear()
            self.recent_detections.clear()
            self.recent_alerts.clear()
            self.fps_history.clear()
            self.processing_times.clear()
    
    def get_recent_detection_summary(self, seconds: int = 10) -> Dict[str, Any]:
        """
        获取最近N秒的检测摘要
        
        Args:
            seconds: 时间范围（秒）
            
        Returns:
            Dict: 检测摘要
        """
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - seconds
            
            recent_detections = [d for d in self.recent_detections if d['timestamp'] >= cutoff_time]
            recent_alerts = [a for a in self.recent_alerts if a['timestamp'] >= cutoff_time]
            
            # 统计最近的行为类型
            recent_behaviors = defaultdict(int)
            for detection in recent_detections:
                behavior = detection.get('behavior_type')
                if behavior:
                    recent_behaviors[behavior] += 1
            
            return {
                'time_range_seconds': seconds,
                'detection_count': len(recent_detections),
                'alert_count': len(recent_alerts),
                'behavior_counts': dict(recent_behaviors),
                'has_activity': len(recent_detections) > 0
            }


# 全局实时统计实例
_realtime_stats = None
_stats_lock = threading.Lock()


def get_realtime_statistics(alert_behaviors: List[str] = None) -> RealtimeStatistics:
    """
    获取实时统计实例（单例模式）
    
    Args:
        alert_behaviors: 报警行为列表
        
    Returns:
        RealtimeStatistics: 实时统计实例
    """
    global _realtime_stats
    
    with _stats_lock:
        if _realtime_stats is None:
            _realtime_stats = RealtimeStatistics(alert_behaviors)
        elif alert_behaviors and _realtime_stats.alert_behaviors != alert_behaviors:
            # 如果报警行为配置发生变化，更新配置
            _realtime_stats.alert_behaviors = alert_behaviors
    
    return _realtime_stats


def reset_realtime_statistics():
    """重置实时统计"""
    global _realtime_stats
    
    with _stats_lock:
        if _realtime_stats:
            _realtime_stats.reset()


def clear_realtime_statistics():
    """清除实时统计实例"""
    global _realtime_stats
    
    with _stats_lock:
        _realtime_stats = None
