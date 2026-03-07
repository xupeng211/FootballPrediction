#!/usr/bin/env python3
"""
V178 核心类型定义 - 零缺陷架构基础
==========================================

设计原则:
    - 类型安全: 封装所�?ID 和状态，杜绝手动拼接字符�?    - 不可变�? 所有值对象不可变，防止意外修�?    - 自验�? 构造时自动验证格式，fail-fast

V178 升级:
    - MatchID 支持新格�? {league_id}_{season}_{external_id}
    - 向后兼容旧格�? {external_id}_{season}

Author: Principal Architect
Version: V178.0.0 (Ultimate Hardening)
Date: 2026-03-03
"""

from dataclasses import dataclass
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)


# V4.42: 政忍统一 - 从售�?源导�? MatchStatus`nfrom src.constants.shared_constants import MatchStatus`n`n# 原本�? MatchStatus 定义已移�? shared_constants.py


@dataclass(frozen=True, slots=True)
class MatchID:
    """
    比赛ID值对�?- 类型安全�?ID 封装

    V178 升级:
        - 支持新格�? {league_id}_{season}_{external_id}
        - 向后兼容旧格�? {external_id}_{season}

    新格式示�? EN_2324_4507094
    旧格式示�? 4507094_2324 (向后兼容)

    设计原则:
        - 不可�? frozen=True 防止意外修改
        - 内存优化: slots=True 减少内存占用
        - 自验�? 构造时自动验证格式

    使用示例:
        # V178 新格�?        match_id = MatchID.parse("EN_2324_4507094")

        # 向后兼容旧格�?        match_id = MatchID.parse("4507094_2324")

        # 创建新格�?        match_id = MatchID.create("4507094", "2324", league_id="EN")

        # 获取各种格式
        str_id = str(match_id)           # "EN_2324_4507094" �?"4507094_2324"
        external = match_id.external_id  # "4507094"
        season = match_id.season         # "2324"
        league = match_id.league_id     # "EN"
    """

    league_id: str      # V178: 新增联赛代码
    season: str
    external_id: str

    # V178: 新格式正�?- league_season_external_id
    _NEW_PATTERN = re.compile(r'^([A-Z]{2,4})_(\d{4})_(\d+)$')
    # 旧格式正�?- external_id_season (向后兼容)
    _LEGACY_PATTERN = re.compile(r'^(\d+)_(\d{4})$')

    def __post_init__(self):
        """验证 ID 格式"""
        if not self.external_id or not self.external_id.isdigit():
            raise ValueError(f"external_id 必须是数�? {self.external_id}")

        if not self.season or len(self.season) != 4 or not self.season.isdigit():
            raise ValueError(f"season 必须�?4 位数�? {self.season}")

    @classmethod
    def create(cls, external_id: str, season: str, league_id: str = "XX") -> "MatchID":
        """
        创建 MatchID 实例（推荐使用）

        Args:
            external_id: 外部比赛 ID
            season: 赛季代码 (�?"2324")
            league_id: 联赛代码 (�?"EN")，默�?"XX" 表示未知

        Returns:
            MatchID 实例
        """
        return cls(league_id=league_id, external_id=external_id, season=season)

    @classmethod
    def parse(cls, match_id_str: str) -> "MatchID":
        """
        从字符串解析 MatchID

        V178: 支持双格式解�?        - 新格�? league_season_external_id (�?EN_2324_4507094)
        - 旧格�? external_id_season (�?4507094_2324)

        Args:
            match_id_str: ID 字符�?
        Returns:
            MatchID 实例

        Raises:
            ValueError: 格式无效
        """
        if not match_id_str:
            raise ValueError("match_id_str 不能为空")

        # V178: 优先尝试新格�?        new_match = cls._NEW_PATTERN.match(match_id_str.strip())
        if new_match:
            league_id, season, external_id = new_match.groups()
            return cls(league_id=league_id, season=season, external_id=external_id)

        # V178: 向后兼容旧格�?        legacy_match = cls._LEGACY_PATTERN.match(match_id_str.strip())
        if legacy_match:
            external_id, season = legacy_match.groups()
            return cls(league_id="XX", season=season, external_id=external_id)

        raise ValueError(
            f"无效�?match_id 格式: {match_id_str}�?
            f"期望新格�? <league>_<season>_<external_id> (�?EN_2324_4507094) "
            f"或旧格式: <external_id>_<season> (�?4507094_2324)"
        )

    def __str__(self) -> str:
        """返回标准字符串格�? league_season_external_id"""
        return f"{self.league_id}_{self.season}_{self.external_id}"

    def __repr__(self) -> str:
        return f"MatchID('{self}')"

    def to_int_pair(self) -> tuple[int, int]:
        """返回 (external_id_int, season_int) 元组"""
        return (int(self.external_id), int(self.season))

    def to_legacy_format(self) -> str:
        """返回旧格式字符串: external_id_season (向后兼容)"""
        return f"{self.external_id}_{self.season}"


class Season:
    """
    赛季工具�?- 赛季转换与验�?
    支持:
        - API 格式 <-> 存储格式 转换
        - 赛季别名映射
    """

    # 常见赛季别名映射
    _ALIASES = {
        "22/23": "2022",
        "23/24": "2023",
        "24/25": "2024",
        "2022-2023": "2022",
        "2023-2024": "2023",
        "2024-2025": "2024",
        "22-23": "2022",
        "23-24": "2023",
        "24-25": "2024",
    }

    @classmethod
    def normalize(cls, season: str) -> str:
        """
        标准化赛季代�?
        Args:
            season: 任意格式的赛季代�?
        Returns:
            标准化的 4 位代�?(�?"2023")

        Examples:
            >>> Season.normalize("23/24")
            '2023'
            >>> Season.normalize("2023-2024")
            '2023'
        """
        if not season:
            return "0000"

        season = season.strip()

        # 直接匹配
        if season in cls._ALIASES:
            return cls._ALIASES[season]

        # 4 位年�?        if season.isdigit() and len(season) == 4:
            return season

        # 2 位年�?(23 -> 2023)
        if season.isdigit() and len(season) == 2:
            year = int(season)
            return f"20{year}" if year < 50 else f"19{year}"

        logger.warning(f"无法识别的赛季格�? {season}，使用默认�?)
        return "0000"


# ============================================================================
# 便捷函数
# ============================================================================


def create_match_id(external_id: str, season: str, league_id: str = "XX") -> MatchID:
    """
    创建 MatchID 的便捷函�?
    V178: 新增 league_id 参数支持

    这是推荐的全局入口点，用于替代所有手动拼接字符串的操作�?    """
    return MatchID.create(external_id, Season.normalize(season), league_id)


def parse_match_id(match_id_str: str) -> MatchID:
    """解析 MatchID 的便捷函�?""
    return MatchID.parse(match_id_str)


# ============================================================================
# 模块测试
# ============================================================================

if __name__ == "__main__":
    # 测试 MatchID

    # 创建
    mid1 = MatchID.create("4507094", "2324")

    # 解析
    mid2 = MatchID.parse("4507094_2324")

    # 属性访�?
    # 测试 MatchStatus

    # 从字符串解析
    status1 = MatchStatus.from_string("finished")

    # 判断

    # 测试 Season
    for _s in ["23/24", "2023-2024", "23-24", "2023"]:
        pass

