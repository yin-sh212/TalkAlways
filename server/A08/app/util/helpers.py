import json
from datetime import datetime, date
from typing import Any


class DateTimeEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理datetime类型"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def format_response(code: int = 200, data: Any = None, message: str = ""):
    """统一响应格式"""
    return {
        "code": code,
        "data": data,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }


def parse_date(date_str: str) -> datetime:
    """解析日期字符串"""
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%Y-%m-%d %H:%M:%S"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"无法解析日期格式: {date_str}")