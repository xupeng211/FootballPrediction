"""
特征实体定义
Feature Entity Definitions

定义 Feast 特征存储的实体。
"""

from typing import Dict

from .mock_feast import Entity, ValueType


def get_entity_definitions() -> Dict[str, Entity]:
    """
    获取实体定义

    Returns:
        Dict[str, Entity]: 实体名称到实体对象的映射
    """
    return {
        "match": Entity(
            name="match",
            value_type=ValueType.INT64,
            description="比赛实体，用于比赛级别的特征",
        ),
        "team": Entity(
            name="team",
            value_type=ValueType.INT64,
            description="球队实体，用于球队级别的特征",
        ),
    }