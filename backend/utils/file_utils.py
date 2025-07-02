"""
文件操作工具模块
"""
import os
import time
import shutil
from datetime import datetime, timedelta
from typing import Set, Union


def allowed_file(filename: str, allowed_extensions: Set[str]) -> bool:
    """
    检查文件扩展名是否被允许
    
    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名集合
        
    Returns:
        bool: 是否允许
    """
    if not filename or '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions


def get_file_size(file_obj) -> int:
    """
    获取文件大小
    
    Args:
        file_obj: 文件对象
        
    Returns:
        int: 文件大小（字节）
    """
    try:
        # 保存当前位置
        current_position = file_obj.tell()
        
        # 移动到文件末尾获取大小
        file_obj.seek(0, 2)
        size = file_obj.tell()
        
        # 恢复原始位置
        file_obj.seek(current_position)
        
        return size
    except Exception:
        return 0


def cleanup_old_files(directory: str, max_age_days: int = 7) -> int:
    """
    清理旧文件
    
    Args:
        directory: 目录路径
        max_age_days: 最大保留天数
        
    Returns:
        int: 清理的文件数量
    """
    if not os.path.exists(directory):
        return 0
    
    cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
    cleaned_count = 0
    
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            if os.path.isfile(file_path):
                # 获取文件修改时间
                file_mtime = os.path.getmtime(file_path)
                
                if file_mtime < cutoff_time:
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                        print(f"已删除旧文件: {file_path}")
                    except OSError as e:
                        print(f"删除文件失败 {file_path}: {e}")
    
    except OSError as e:
        print(f"清理目录失败 {directory}: {e}")
    
    return cleaned_count


def ensure_directory(directory: str) -> bool:
    """
    确保目录存在
    
    Args:
        directory: 目录路径
        
    Returns:
        bool: 是否成功
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except OSError:
        return False


def get_safe_filename(filename: str) -> str:
    """
    获取安全的文件名
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 安全的文件名
    """
    # 移除或替换不安全的字符
    unsafe_chars = '<>:"/\\|?*'
    safe_filename = filename
    
    for char in unsafe_chars:
        safe_filename = safe_filename.replace(char, '_')
    
    # 添加时间戳避免重名
    name, ext = os.path.splitext(safe_filename)
    timestamp = int(time.time())
    
    return f"{name}_{timestamp}{ext}"


def calculate_directory_size(directory: str) -> int:
    """
    计算目录大小
    
    Args:
        directory: 目录路径
        
    Returns:
        int: 目录大小（字节）
    """
    total_size = 0
    
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except (OSError, FileNotFoundError):
                    pass  # 忽略无法访问的文件
    except OSError:
        pass  # 忽略无法访问的目录
    
    return total_size


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        str: 格式化的大小字符串
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def copy_file_with_progress(src: str, dst: str, callback=None) -> bool:
    """
    带进度回调的文件复制
    
    Args:
        src: 源文件路径
        dst: 目标文件路径
        callback: 进度回调函数 callback(copied_bytes, total_bytes)
        
    Returns:
        bool: 是否成功
    """
    try:
        file_size = os.path.getsize(src)
        copied_bytes = 0
        
        with open(src, 'rb') as src_file:
            with open(dst, 'wb') as dst_file:
                while True:
                    chunk = src_file.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    
                    dst_file.write(chunk)
                    copied_bytes += len(chunk)
                    
                    if callback:
                        callback(copied_bytes, file_size)
        
        return True
        
    except (OSError, IOError):
        return False


def get_video_info(video_path: str) -> dict:
    """
    获取视频文件信息
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        dict: 视频信息
    """
    try:
        import cv2
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {}
        
        info = {
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'duration': 0
        }
        
        if info['fps'] > 0:
            info['duration'] = info['frame_count'] / info['fps']
        
        cap.release()
        return info
        
    except Exception:
        return {}


def validate_video_file(file_path: str) -> tuple[bool, str]:
    """
    验证视频文件
    
    Args:
        file_path: 视频文件路径
        
    Returns:
        tuple: (是否有效, 错误信息)
    """
    if not os.path.exists(file_path):
        return False, "文件不存在"
    
    if os.path.getsize(file_path) == 0:
        return False, "文件为空"
    
    try:
        import cv2
        
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return False, "无法打开视频文件"
        
        # 尝试读取第一帧
        ret, frame = cap.read()
        cap.release()
        
        if not ret or frame is None:
            return False, "无法读取视频帧"
        
        return True, ""
        
    except Exception as e:
        return False, f"视频验证失败: {str(e)}" 