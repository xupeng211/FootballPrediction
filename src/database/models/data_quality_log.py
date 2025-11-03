from src.database.base import BaseModel

"""
数据质量日志数据库模型

记录数据质量检查中发现的问题和异常处理情况,
支持人工排查和质量改进追踪.

用途:
- 记录数据质量异常和错误
- 跟踪异常处理进度
- 支持数据治理决策
"""


class DataQualityLog(BaseModel):
    __tablename__ = "data_quality_logs"
    __table_args__ = {"extend_existing": True}
