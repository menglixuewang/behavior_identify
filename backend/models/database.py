"""
数据库模型定义
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship

db = SQLAlchemy()


class DetectionTask(db.Model):
    """检测任务表"""
    __tablename__ = 'detection_tasks'
    
    id = Column(Integer, primary_key=True)
    task_name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # 'video' 或 'camera'
    source_path = Column(String(500), nullable=True)  # 视频文件路径或摄像头ID
    output_path = Column(String(500), nullable=True)  # 输出文件路径
    status = Column(String(50), default='pending')  # pending, running, completed, failed
    progress = Column(Float, default=0.0)  # 处理进度 0-100
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 检测参数
    confidence_threshold = Column(Float, default=0.5)
    input_size = Column(Integer, default=640)
    device = Column(String(20), default='cpu')
    
    # 统计信息
    total_frames = Column(Integer, default=0)
    processed_frames = Column(Integer, default=0)
    detected_objects = Column(Integer, default=0)
    detected_behaviors = Column(Integer, default=0)
    
    # 关联的检测结果
    detection_results = relationship('DetectionResult', backref='task', lazy='dynamic')
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'task_name': self.task_name,
            'source_type': self.source_type,
            'source_path': self.source_path,
            'output_path': self.output_path,
            'status': self.status,
            'progress': self.progress,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'confidence_threshold': self.confidence_threshold,
            'input_size': self.input_size,
            'device': self.device,
            'total_frames': self.total_frames,
            'processed_frames': self.processed_frames,
            'detected_objects': self.detected_objects,
            'detected_behaviors': self.detected_behaviors
        }


class DetectionResult(db.Model):
    """检测结果表"""
    __tablename__ = 'detection_results'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('detection_tasks.id'), nullable=False)
    frame_number = Column(Integer, nullable=False)
    timestamp = Column(Float, nullable=False)  # 视频时间戳（秒）
    
    # 目标检测信息
    object_id = Column(Integer, nullable=True)  # 跟踪ID
    object_type = Column(String(50), nullable=False)  # 目标类型（person等）
    confidence = Column(Float, nullable=False)  # 检测置信度
    
    # 边界框信息
    bbox_x1 = Column(Float, nullable=False)
    bbox_y1 = Column(Float, nullable=False)
    bbox_x2 = Column(Float, nullable=False)
    bbox_y2 = Column(Float, nullable=False)
    
    # 行为识别信息
    behavior_type = Column(String(100), nullable=True)  # 行为类型
    behavior_confidence = Column(Float, nullable=True)  # 行为置信度
    is_anomaly = Column(Boolean, default=False)  # 是否为异常行为
    
    # 其他信息
    velocity_x = Column(Float, nullable=True)  # X方向速度
    velocity_y = Column(Float, nullable=True)  # Y方向速度
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'frame_number': self.frame_number,
            'timestamp': self.timestamp,
            'object_id': self.object_id,
            'object_type': self.object_type,
            'confidence': self.confidence,
            'bbox': {
                'x1': self.bbox_x1,
                'y1': self.bbox_y1,
                'x2': self.bbox_x2,
                'y2': self.bbox_y2
            },
            'behavior_type': self.behavior_type,
            'behavior_confidence': self.behavior_confidence,
            'is_anomaly': self.is_anomaly,
            'velocity': {
                'x': self.velocity_x,
                'y': self.velocity_y
            },
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AlertRecord(db.Model):
    """报警记录表"""
    __tablename__ = 'alert_records'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('detection_tasks.id'), nullable=False)
    alert_type = Column(String(100), nullable=False)  # 报警类型
    alert_level = Column(String(20), default='warning')  # info, warning, error, critical
    
    # 触发信息
    trigger_frame = Column(Integer, nullable=False)
    trigger_timestamp = Column(Float, nullable=False)
    trigger_object_id = Column(Integer, nullable=True)
    trigger_behavior = Column(String(100), nullable=False)
    trigger_confidence = Column(Float, nullable=False)
    
    # 位置信息
    location_x = Column(Float, nullable=True)
    location_y = Column(Float, nullable=True)
    
    # 报警状态
    status = Column(String(50), default='active')  # active, acknowledged, resolved
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # 描述信息
    description = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'alert_type': self.alert_type,
            'alert_level': self.alert_level,
            'trigger_frame': self.trigger_frame,
            'trigger_timestamp': self.trigger_timestamp,
            'trigger_object_id': self.trigger_object_id,
            'trigger_behavior': self.trigger_behavior,
            'trigger_confidence': self.trigger_confidence,
            'location': {
                'x': self.location_x,
                'y': self.location_y
            },
            'status': self.status,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'acknowledged_by': self.acknowledged_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'description': self.description,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SystemConfig(db.Model):
    """系统配置表"""
    __tablename__ = 'system_configs'
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text, nullable=False)
    config_type = Column(String(50), default='string')  # string, int, float, bool, json
    description = Column(Text, nullable=True)
    category = Column(String(50), default='general')  # general, detection, alert, system
    is_editable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'config_type': self.config_type,
            'description': self.description,
            'category': self.category,
            'is_editable': self.is_editable,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SystemLog(db.Model):
    """系统日志表"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    level = Column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    module = Column(String(100), nullable=False)  # 模块名称
    function = Column(String(100), nullable=True)  # 函数名称
    message = Column(Text, nullable=False)  # 日志消息
    
    # 上下文信息
    task_id = Column(Integer, nullable=True)
    user_ip = Column(String(45), nullable=True)
    request_id = Column(String(100), nullable=True)
    
    # 异常信息
    exception_type = Column(String(100), nullable=True)
    exception_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'level': self.level,
            'module': self.module,
            'function': self.function,
            'message': self.message,
            'task_id': self.task_id,
            'user_ip': self.user_ip,
            'request_id': self.request_id,
            'exception_type': self.exception_type,
            'exception_message': self.exception_message,
            'stack_trace': self.stack_trace,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


def init_default_configs():
    """初始化默认配置"""
    default_configs = [
        {
            'key': 'confidence_threshold',
            'value': '0.5',
            'type': 'float',
            'description': '检测置信度阈值',
            'category': 'detection'
        },
        {
            'key': 'iou_threshold',
            'value': '0.4',
            'type': 'float',
            'description': 'IOU阈值',
            'category': 'detection'
        },
        {
            'key': 'input_size',
            'value': '640',
            'type': 'int',
            'description': '输入图像尺寸',
            'category': 'detection'
        },
        {
            'key': 'alert_behaviors',
            'value': '["fall down", "fight", "enter", "exit"]',
            'type': 'json',
            'description': '触发报警的行为类型',
            'category': 'alert'
        },
        {
            'key': 'max_concurrent_detections',
            'value': '3',
            'type': 'int',
            'description': '最大并发检测任务数',
            'category': 'system'
        }
    ]
    
    for config in default_configs:
        existing = SystemConfig.query.filter_by(config_key=config['key']).first()
        if not existing:
            new_config = SystemConfig(
                config_key=config['key'],
                config_value=config['value'],
                config_type=config['type'],
                description=config['description'],
                category=config['category']
            )
            db.session.add(new_config)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing default configs: {e}")


def create_tables():
    """创建所有数据表"""
    db.create_all()
    init_default_configs()
    print("数据库表创建完成") 