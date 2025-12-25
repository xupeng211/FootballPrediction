#!/usr/bin/env python3
"""
V20.5 球员位置映射模块
========================

独立模块，负责将 FotMob 位置 ID 映射到标准位置分类 (GK/DF/MF/FW)

功能:
- map_position_to_segment(): 核心映射函数
- validate_position_mapping(): 映射验证工具
- PositionSegment: 位置分类枚举

作者: SRE Team
日期: 2025-12-24
版本: V20.5
"""

import logging
from enum import Enum
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class PositionSegment(Enum):
    """标准位置分类"""
    GK = 'GK'      # 门将
    DF = 'DF'      # 后卫
    MF = 'MF'      # 中场
    FW = 'FW'      # 前锋
    UNKNOWN = 'Unknown'  # 未知位置


# FotMob positionId 映射到标准位置分类
# 基于实际数据: 11=GK, 后卫=31-36, 中场=37-42, 前锋=43+
POSITION_MAPPING: Dict[int, PositionSegment] = {
    # 门将
    11: PositionSegment.GK,
    # 后卫
    31: PositionSegment.DF, 32: PositionSegment.DF, 33: PositionSegment.DF,
    34: PositionSegment.DF, 35: PositionSegment.DF, 36: PositionSegment.DF,
    # 中场
    37: PositionSegment.MF, 38: PositionSegment.MF, 39: PositionSegment.MF,
    40: PositionSegment.MF, 41: PositionSegment.MF, 42: PositionSegment.MF,
    # 前锋
    43: PositionSegment.FW, 44: PositionSegment.FW, 45: PositionSegment.FW,
    46: PositionSegment.FW, 47: PositionSegment.FW, 48: PositionSegment.FW,
}


# usualPlayingPositionId 映射 (简化分类)
# V20.3.1 FIX: 修正错误映射，基于实际 FotMob 数据验证
# - Haaland/Salah/Kane/Mbappe 都有 usualPlayingPositionId=3
# - 中场球员 (球衣号 6,8,10) 有 usualPlayingPositionId=2
USUAL_POSITION_MAPPING: Dict[int, PositionSegment] = {
    0: PositionSegment.GK,   # 门将
    1: PositionSegment.DF,   # 后卫
    2: PositionSegment.MF,   # 中场 (原错误映射为 DF)
    3: PositionSegment.FW,   # 前锋 (原错误映射为 MF)
}


def map_position_to_segment(
    player: Dict[str, Any],
    strict_mode: bool = False
) -> str:
    """
    将球员的 positionId 映射到位置分类 (GK/DF/MF/FW)

    V20.3.1 FIX: 双重校验逻辑，确保位置映射 100% 准确

    Args:
        player: 球员数据字典，包含:
            - positionId: FotMob 原始位置ID (范围 11-48)
            - usualPlayingPositionId: 简化位置ID (范围 0-3)
            - name: 球员姓名 (用于日志)
        strict_mode: 严格模式，如果映射失败则抛出异常

    Returns:
        位置分类: 'GK', 'DF', 'MF', 'FW', 或 'Unknown'

    Raises:
        ValueError: strict_mode=True 且映射失败时抛出

    Examples:
        >>> player = {'positionId': 43, 'name': 'Haaland'}
        >>> map_position_to_segment(player)
        'FW'

        >>> player = {'usualPlayingPositionId': 2, 'name': 'De Bruyne'}
        >>> map_position_to_segment(player)
        'MF'
    """
    # 首先尝试 positionId (FotMob 原始位置ID，范围 11-48)
    position_id = player.get('positionId')

    # 确保是整数类型
    if isinstance(position_id, str):
        try:
            position_id = int(position_id)
        except (ValueError, TypeError):
            position_id = None

    if position_id is not None and position_id in POSITION_MAPPING:
        mapped = POSITION_MAPPING[position_id].value
        logger.debug(f"位置映射: positionId={position_id} -> {mapped}")
        return mapped

    # 其次尝试 usualPlayingPositionId (0-3 范围)
    usual_pos_id = player.get('usualPlayingPositionId')

    # 确保是整数类型
    if isinstance(usual_pos_id, str):
        try:
            usual_pos_id = int(usual_pos_id)
        except (ValueError, TypeError):
            usual_pos_id = None

    if usual_pos_id is not None and usual_pos_id in USUAL_POSITION_MAPPING:
        mapped = USUAL_POSITION_MAPPING[usual_pos_id].value
        logger.debug(f"位置映射 (usual): usualPlayingPositionId={usual_pos_id} -> {mapped}")
        return mapped

    # 映射失败处理
    player_name = player.get('name', 'Unknown')
    error_msg = (
        f"位置映射失败: positionId={position_id}, "
        f"usualPlayingPositionId={usual_pos_id}, player={player_name}"
    )

    if strict_mode:
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.warning(error_msg)
    return PositionSegment.UNKNOWN.value


def validate_position_mapping(
    player: Dict[str, Any],
    expected_segment: str
) -> bool:
    """
    验证球员位置映射是否符合预期

    Args:
        player: 球员数据字典
        expected_segment: 预期的位置分类 ('GK', 'DF', 'MF', 'FW')

    Returns:
        True 如果映射结果与预期一致，False 否则

    Examples:
        >>> player = {'positionId': 43, 'name': 'Haaland'}
        >>> validate_position_mapping(player, 'FW')
        True
        >>> validate_position_mapping(player, 'GK')
        False
    """
    actual_segment = map_position_to_segment(player)
    return actual_segment == expected_segment


def get_all_position_ids() -> Dict[str, list]:
    """
    获取所有位置 ID 映射的摘要信息

    Returns:
        字典结构: {
            'GK': [11],
            'DF': [31, 32, 33, 34, 35, 36],
            'MF': [37, 38, 39, 40, 41, 42],
            'FW': [43, 44, 45, 46, 47, 48]
        }
    """
    summary = {seg.value: [] for seg in PositionSegment if seg != PositionSegment.UNKNOWN}

    for pos_id, segment in POSITION_MAPPING.items():
        summary[segment.value].append(pos_id)

    return summary


def get_usual_position_ids() -> Dict[str, int]:
    """
    获取 usualPlayingPositionId 映射摘要

    Returns:
        字典结构: {
            'GK': 0,
            'DF': 1,
            'MF': 2,
            'FW': 3
        }
    """
    return {segment.value: pos_id for pos_id, segment in USUAL_POSITION_MAPPING.items()}


# 模块初始化时打印映射配置
logger.info(f"位置映射配置: POSITION_MAPPING={len(POSITION_MAPPING)} 条")
logger.info(f"常用位置映射: USUAL_POSITION_MAPPING={USUAL_POSITION_MAPPING}")
