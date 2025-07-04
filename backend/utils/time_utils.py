"""
时间工具模块 - 统一处理北京时间
"""
from datetime import datetime, timezone, timedelta
import pytz

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_now():
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)

def get_beijing_datetime():
    """获取当前北京时间（不带时区信息，用于数据库存储）"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)

def utc_to_beijing(utc_dt):
    """将UTC时间转换为北京时间"""
    if utc_dt is None:
        return None
    
    # 如果是naive datetime，假设它是UTC时间
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=pytz.UTC)
    
    # 转换为北京时间
    beijing_dt = utc_dt.astimezone(BEIJING_TZ)
    return beijing_dt.replace(tzinfo=None)  # 移除时区信息

def beijing_to_utc(beijing_dt):
    """将北京时间转换为UTC时间"""
    if beijing_dt is None:
        return None
    
    # 如果是naive datetime，假设它是北京时间
    if beijing_dt.tzinfo is None:
        beijing_dt = BEIJING_TZ.localize(beijing_dt)
    
    # 转换为UTC时间
    utc_dt = beijing_dt.astimezone(pytz.UTC)
    return utc_dt.replace(tzinfo=None)  # 移除时区信息

def format_beijing_time(dt, format_str='%Y-%m-%d %H:%M:%S'):
    """格式化北京时间"""
    if dt is None:
        return None
    
    # 如果是UTC时间，先转换为北京时间
    if isinstance(dt, datetime):
        beijing_dt = utc_to_beijing(dt)
        return beijing_dt.strftime(format_str)
    
    return str(dt)

def parse_iso_to_beijing(iso_string):
    """解析ISO格式时间字符串为北京时间"""
    if not iso_string:
        return None
    
    try:
        # 解析ISO格式时间
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        
        # 转换为北京时间
        return utc_to_beijing(dt)
    except ValueError:
        return None

def get_timestamp():
    """获取当前时间戳（秒）"""
    return int(get_beijing_now().timestamp())

def get_timestamp_ms():
    """获取当前时间戳（毫秒）"""
    return int(get_beijing_now().timestamp() * 1000)

def datetime_to_iso_beijing(dt):
    """将datetime转换为ISO格式的北京时间字符串"""
    if dt is None:
        return None
    
    # 确保是北京时间
    beijing_dt = utc_to_beijing(dt) if dt.tzinfo is None else dt
    
    # 添加北京时区信息并转换为ISO格式
    beijing_dt_with_tz = BEIJING_TZ.localize(beijing_dt) if beijing_dt.tzinfo is None else beijing_dt
    return beijing_dt_with_tz.isoformat()

def get_date_range_beijing(days_ago=0):
    """获取北京时间的日期范围"""
    end_time = get_beijing_now()
    start_time = end_time - timedelta(days=days_ago)
    
    return start_time.replace(tzinfo=None), end_time.replace(tzinfo=None)

def is_same_day_beijing(dt1, dt2):
    """判断两个时间是否是同一天（北京时间）"""
    if dt1 is None or dt2 is None:
        return False
    
    beijing_dt1 = utc_to_beijing(dt1)
    beijing_dt2 = utc_to_beijing(dt2)
    
    return beijing_dt1.date() == beijing_dt2.date()

def get_today_start_end_beijing():
    """获取今天的开始和结束时间（北京时间）"""
    now = get_beijing_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=None)
    
    return today_start, today_end

# 向后兼容的函数名
def now():
    """获取当前北京时间（向后兼容）"""
    return get_beijing_datetime()

def utcnow():
    """获取当前北京时间（替代datetime.utcnow）"""
    return get_beijing_datetime()
