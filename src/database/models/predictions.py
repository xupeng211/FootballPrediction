"""
Predictions - 数据库模块

提供 predictions 相关的数据库功能.

主要功能：
- [待补充 - Predictions的主要功能]

使用示例:
    from database.models import Predictions
    # 使用示例代码

注意事项:
- [待补充 - 使用注意事项]
"""

from enum import Enum


from ..base import BaseModel

"""
预测结果数据模型

存储机器学习模型的预测结果,包括胜负概率,比分预测等.
"""


class PredictedResult(Enum):
    """预测结果枚举"""

    HOME_WIN = "home_win"  # 主队胜
    DRAW = "draw"  # 平局
    AWAY_WIN = "away_win"  # 客队胜


class Predictions(BaseModel):
    __table_args__ = {"extend_existing": True}
    __tablename__ = "predictions"
