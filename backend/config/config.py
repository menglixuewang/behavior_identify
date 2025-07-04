import os
from datetime import timedelta

class Config:
    """系统配置类"""
    
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'behavior-detection-secret-key-2023'
    
    # 数据库配置
    @staticmethod
    def get_database_uri():
        """获取数据库URI"""
        if os.environ.get('DATABASE_URL'):
            return os.environ.get('DATABASE_URL')

        # 构建指向instance目录的数据库路径
        config_dir = os.path.dirname(__file__)  # config目录
        backend_dir = os.path.dirname(config_dir)  # backend目录
        instance_dir = os.path.join(backend_dir, 'instance')  # instance目录
        db_path = os.path.join(instance_dir, 'behavior_detection.db')

        # 确保instance目录存在
        os.makedirs(instance_dir, exist_ok=True)

        return f'sqlite:///{db_path}'

    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs')
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'}

    # 模型根路径
    MODEL_PATH = 'D:/PyCharm 2024.2.4/PycharmProjects/behavior_identify/yolo_slowfast-master'

    # 检测算法配置
    YOLO_MODEL_PATH = os.path.join(MODEL_PATH, 'yolov8n.pt')
    SLOWFAST_WEIGHTS_PATH = os.path.join(MODEL_PATH, 'SLOWFAST_8x8_R50_DETECTION.pyth')
    DEEPSORT_WEIGHTS_PATH = os.path.join(MODEL_PATH, 'ckpt.t7')
    AVA_LABELS_PATH = os.path.join(MODEL_PATH, 'temp.pbtxt')
    
    # 检测参数配置
    CONFIDENCE_THRESHOLD = 0.5
    IOU_THRESHOLD = 0.4
    INPUT_SIZE = 640
    
    # 设备配置 - 自动检测GPU
    @staticmethod
    def get_default_device():
        """自动检测最佳设备"""
        try:
            import torch
            if torch.cuda.is_available():
                return 'cuda'
        except ImportError:
            pass
        return 'cpu'
    
    # 在类外部设置设备
    DEVICE = 'cpu'  # 默认CPU，稍后会动态设置
    
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
        
        # 动态设置设备
        Config.DEVICE = Config.get_default_device()


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