import os
from datetime import timedelta

class Config:
    """系统配置类"""
    
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'behavior-detection-secret-key-2023'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///behavior_detection.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs')
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'}
    
    # 检测算法配置
    YOLO_MODEL_PATH = 'yolov8n.pt'
    SLOWFAST_WEIGHTS_PATH = 'SLOWFAST_8x8_R50_DETECTION.pyth'
    DEEPSORT_WEIGHTS_PATH = 'deep_sort/deep_sort/deep/checkpoint/ckpt.t7'
    AVA_LABELS_PATH = 'selfutils/temp.pbtxt'
    
    # 检测参数配置
    CONFIDENCE_THRESHOLD = 0.5
    IOU_THRESHOLD = 0.4
    INPUT_SIZE = 640
    DEVICE = 'cpu'  # 'cpu' 或 'cuda'
    
    # 报警配置
    ALERT_BEHAVIORS = [
        'fall down',    # 跌倒
        'fight',        # 打斗
        'enter',        # 闯入
        'exit'          # 离开
    ]
    
    # 系统运行配置
    DEBUG = True
    TESTING = False
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/app.log'
    
    # WebSocket配置
    SOCKETIO_ASYNC_MODE = 'eventlet'
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"
    
    # 性能配置
    MAX_CONCURRENT_DETECTIONS = 3
    CLIP_DURATION = 25  # 视频片段帧数
    VIDEO_FPS = 25
    
    # 数据保留配置
    DATA_RETENTION_DAYS = 30  # 数据保留天数
    AUTO_CLEANUP_ENABLED = True
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 创建必要的目录
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.OUTPUT_FOLDER, exist_ok=True)
        os.makedirs(os.path.dirname(Config.LOG_FILE), exist_ok=True)


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    DEVICE = 'cuda' if os.environ.get('USE_GPU') == 'true' else 'cpu'


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 