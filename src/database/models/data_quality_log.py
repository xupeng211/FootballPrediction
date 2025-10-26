from typing import Any, Dict, Optional
from datetime import datetime
from ..base import BaseModel
from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text, func

"""
数据质量日志数据库模型

记录数据质量检查中发现的问题和异常处理情况，
支持人工排查和质量改进追踪。

用途：
- 记录数据质量异常和错误
- 跟踪异常处理进度
- 支持数据治理决策
"""

from typing import Any, Dict, Optional
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from src.database.base import BaseModel
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text


class DataQualityLog(BaseModel):
    __table_args__ = {"extend_existing": True}
