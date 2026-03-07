#!/usr/bin/env python3
"""
V79.200 Injury Parser - 伤病/缺阵数据深层解析器
==================================================

从 ultimate_extractor.py 和 starting_quality_assessor.py 拆分出来的
专门负责 L2 JSON 数据深层路径解析的模块。

核心功能：
1. 深度递归解析缺阵球员数据
2. 提取首发阵容数据
3. 安全的 JSON 路径访问（容错）

Author: V79.200 Engineering Team
Version: V79.200 "Deep JSON Parser"
Date: 2026-01-25
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Constants: JSON Path Patterns
# =============================================================================

# L2 JSON 路径常量 (V79.200 外部化)
L2_JSON_PATHS = {
    "lineup_root": "content.lineup",
    "home_unavailable": "content.lineup.homeTeam.unavailable",
    "away_unavailable": "content.lineup.awayTeam.unavailable",
    "home_starting": "content.lineup.homeTeam.starting",
    "away_starting": "content.lineup.awayTeam.starting",
}


# =============================================================================
# Deep JSON Path Parser
# =============================================================================

class DeepJSONParser:
    """
    V79.200 深层 JSON 路径解析器

    提供：
    1. 递归路径解析 (支持 "a.b.c" 格式)
    2. 容错机制 (路径不存在时返回默认值)
    3. JSON 字符串自动解析
    """

    @staticmethod
    def parse_json_string(
        data: dict[str, Any] | str | None,
        default: dict | None = None
    ) -> dict[str, Any]:
        """
        解析 JSON 字符串为字典

        Args:
            data: JSON 字符串或字典
            default: 默认值

        Returns:
            解析后的字典
        """
        if default is None:
            default = {}

        if data is None:
            return default

        if isinstance(data, dict):
            return data

        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse JSON string: {e}")
                return default

        return default

    @staticmethod
    def get_nested_value(
        data: dict[str, Any],
        path: str,
        default: Any = None
    ) -> Any:
        """
        递归获取嵌套值

        Args:
            data: 源字典
            path: 点分隔路径 (如 "content.lineup.homeTeam")
            default: 默认值

        Returns:
            找到的值或默认值

        Example:
            >>> data = {"content": {"lineup": {"homeTeam": {"name": "Arsenal"}}}}
            >>> DeepJSONParser.get_nested_value(data, "content.lineup.homeTeam.name")
            "Arsenal"
        """
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return default
            else:
                return default

        return current if current is not None else default


# =============================================================================
# Injury/Unavailable Data Extractor
# =============================================================================

class InjuryDataExtractor:
    """
    V79.200 伤病/缺阵数据提取器

    专门负责从 L2 raw JSON 中提取：
    1. 主客队缺阵球员列表
    2. 主客队首发阵容数据
    3. 球员详细属性 (身价、年龄、评分等)
    """

    def __init__(self):
        """初始化提取器"""
        self.parser = DeepJSONParser()

    def extract_lineup_root(
        self,
        l2_raw_json: dict[str, Any] | str | None
    ) -> dict[str, Any]:
        """
        提取 lineup 根节点

        Args:
            l2_raw_json: L2 原始 JSON 数据

        Returns:
            lineup 字典
        """
        data = self.parser.parse_json_string(l2_raw_json)
        return self.parser.get_nested_value(
            data,
            L2_JSON_PATHS["lineup_root"],
            default={}
        )

    def extract_unavailable_players(
        self,
        l2_raw_json: dict[str, Any] | str | None,
        team_side: str = "home"  # "home" or "away"
    ) -> list[dict[str, Any]]:
        """
        提取缺阵球员列表

        Args:
            l2_raw_json: L2 原始 JSON 数据
            team_side: 球队方 ("home" 或 "away")

        Returns:
            缺阵球员列表
        """
        data = self.parser.parse_json_string(l2_raw_json)

        path_key = f"{'home' if team_side == 'home' else 'away'}_unavailable"
        path = L2_JSON_PATHS.get(path_key, "")

        unavailable_list = self.parser.get_nested_value(data, path, default=[])

        if not isinstance(unavailable_list, list):
            logger.warning(
                f"Unavailable data for {team_side} is not a list: "
                f"{type(unavailable_list)}"
            )
            return []

        return unavailable_list

    def extract_starting_lineup(
        self,
        l2_raw_json: dict[str, Any] | str | None,
        team_side: str = "home"  # "home" or "away"
    ) -> list[dict[str, Any]]:
        """
        提取首发阵容列表

        Args:
            l2_raw_json: L2 原始 JSON 数据
            team_side: 球队方 ("home" 或 "away")

        Returns:
            首发球员列表
        """
        data = self.parser.parse_json_string(l2_raw_json)

        path_key = f"{'home' if team_side == 'home' else 'away'}_starting"
        path = L2_JSON_PATHS.get(path_key, "")

        starting_list = self.parser.get_nested_value(data, path, default=[])

        if not isinstance(starting_list, list):
            logger.warning(
                f"Starting data for {team_side} is not a list: "
                f"{type(starting_list)}"
            )
            return []

        return starting_list

    def extract_player_attribute(
        self,
        player: dict[str, Any],
        attribute: str,
        default: Any = None
    ) -> Any:
        """
        安全提取球员属性

        Args:
            player: 球员数据字典
            attribute: 属性名
            default: 默认值

        Returns:
            属性值或默认值
        """
        if not isinstance(player, dict):
            return default

        return player.get(attribute, default)


# =============================================================================
# Utility Functions
# =============================================================================

def extract_unavailable_features_from_l2(
    l2_raw_json: dict[str, Any] | str | None,
    extractor: InjuryDataExtractor | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    便捷函数：从 L2 数据提取主客队缺阵球员列表

    Args:
        l2_raw_json: L2 原始 JSON 数据
        extractor: InjuryDataExtractor 实例（可选）

    Returns:
        (主队缺阵列表, 客队缺阵列表)

    Example:
        >>> home, away = extract_unavailable_features_from_l2(l2_data)
        >>> print(f"Home unavailable: {len(home)}, Away unavailable: {len(away)}")
    """
    if extractor is None:
        extractor = InjuryDataExtractor()

    home_unavailable = extractor.extract_unavailable_players(l2_raw_json, "home")
    away_unavailable = extractor.extract_unavailable_players(l2_raw_json, "away")

    return home_unavailable, away_unavailable


def extract_starting_features_from_l2(
    l2_raw_json: dict[str, Any] | str | None,
    extractor: InjuryDataExtractor | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    便捷函数：从 L2 数据提取主客队首发阵容列表

    Args:
        l2_raw_json: L2 原始 JSON 数据
        extractor: InjuryDataExtractor 实例（可选）

    Returns:
        (主队首发列表, 客队首发列表)

    Example:
        >>> home_starting, away_starting = extract_starting_features_from_l2(l2_data)
    """
    if extractor is None:
        extractor = InjuryDataExtractor()

    home_starting = extractor.extract_starting_lineup(l2_raw_json, "home")
    away_starting = extractor.extract_starting_lineup(l2_raw_json, "away")

    return home_starting, away_starting


# =============================================================================
# Type Aliases
# =============================================================================

PlayerData = dict[str, Any]
PlayerList = list[PlayerData]
L2RawJSON = dict[str, Any] | str | None
