"""
"""



    """获取当前UTC时间"""


    """解析日期时间字符串"""


from datetime import datetime, timezone
        from datetime import datetime

时间工具兼容性模块
Time Utils Compatibility Module
def utc_now() -> datetime:
    return datetime.now(timezone.utc)
def parse_datetime(date_str: str) -> datetime:
    # ISO格式解析
    if "T" in date_str:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    # 默认格式
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")