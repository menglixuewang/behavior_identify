"""
日志工具模块
"""
import os
import logging
import logging.handlers
from datetime import datetime


def setup_logger(log_file='app.log', log_level='INFO'):
    """
    设置日志记录器
    
    Args:
        log_file: 日志文件路径
        log_level: 日志级别
        
    Returns:
        logger: 配置好的日志记录器
    """
    # 创建日志目录
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # 创建日志记录器
    logger = logging.getLogger('behavior_detection')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
    )
    
    # 文件处理器（带轮转）
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


def log_request(logger, request, response_status=None):
    """
    记录HTTP请求日志
    
    Args:
        logger: 日志记录器
        request: Flask请求对象
        response_status: 响应状态码
    """
    try:
        log_data = {
            'method': request.method,
            'url': request.url,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'content_length': request.content_length,
            'timestamp': datetime.now().isoformat()
        }
        
        if response_status:
            log_data['status'] = response_status
        
        logger.info(f"HTTP请求: {log_data}")
        
    except Exception as e:
        logger.error(f"记录请求日志失败: {e}")


def log_detection_task(logger, task_id, action, details=None):
    """
    记录检测任务日志
    
    Args:
        logger: 日志记录器
        task_id: 任务ID
        action: 操作类型
        details: 详细信息
    """
    try:
        log_data = {
            'task_id': task_id,
            'action': action,
            'timestamp': datetime.now().isoformat()
        }
        
        if details:
            log_data['details'] = details
        
        logger.info(f"检测任务: {log_data}")
        
    except Exception as e:
        logger.error(f"记录任务日志失败: {e}")


def log_error(logger, error, context=None):
    """
    记录错误日志
    
    Args:
        logger: 日志记录器
        error: 错误对象或错误信息
        context: 上下文信息
    """
    try:
        import traceback
        
        error_info = {
            'error_type': type(error).__name__ if hasattr(error, '__class__') else 'Unknown',
            'error_message': str(error),
            'timestamp': datetime.now().isoformat()
        }
        
        if context:
            error_info['context'] = context
        
        if hasattr(error, '__traceback__'):
            error_info['traceback'] = traceback.format_exception(
                type(error), error, error.__traceback__
            )
        
        logger.error(f"系统错误: {error_info}")
        
    except Exception as e:
        logger.error(f"记录错误日志失败: {e}") 