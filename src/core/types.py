#!/usr/bin/env python3
"""
V26.0 核心类型定义 - 零缺陷架构基础
==========================================

设计原则:
    - 类型安全: 封装所有 ID 和状态，杜绝手动拼接字符串
    - 不可变性: 所有值对象不可变，防止意外修改
    - 自验证: 构造时自动验证格式，fail-fast

Author: Principal Architect
Version: V26.0 (Stable)
Date: 2025-12-27
"""

from dataclasses import dataclass
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)


class MatchStatus(Enum):
    """
    比赛状态枚举 - 统一状态常量

    使用示例:
        if match.status == MatchStatus.FINISHED:
            process_features(match)
    """

    # 比赛状态
    SCHEDULED = "SCHEDULED"  # 已计划
    LIVE = "LIVE"  # 进行中
    FINISHED = "FINISHED"  # 已完成
    POSTPONED = "POSTPONED"  # 推迟
    CANCELLED = "CANCELLED"  # 取消

    # 特征提取状态
    PENDING = "PENDING"  # 待提取
    PROCESSING = "PROCESSING"  # 提取中
    COMPLETED = "COMPLETED"  # 已完成
    FAILED = "FAILED"  # 失败

    @classmethod
    def from_string(cls, value: str) -> "MatchStatus":
        """
        从字符串解析状态（大小写不敏感）

        Args:
            value: 状态字符串

        Returns:
            MatchStatus 枚举值

        Raises:
            ValueError: 无效的状态值
        """
        if not value:
            raise ValueError("状态值不能为空")

        normalized = value.strip().upper()
        for status in cls:
            if status.value == normalized:
                return status

        raise ValueError(f"无效的状态值: {value}，有效值: {[s.value for s in cls]}")

    def is_final(self) -> bool:
        """是否为终态（不会再变化）"""
        return self in {
            MatchStatus.FINISHED,
            MatchStatus.POSTPONED,
            MatchStatus.CANCELLED,
            MatchStatus.COMPLETED,
            MatchStatus.FAILED,
        }

    def allows_feature_extraction(self) -> bool:
        """是否允许提取特征"""
        return self == MatchStatus.FINISHED


@dataclass(frozen=True, slots=True)
class MatchID:
    """
    比赛ID值对象 - 类型安全的 ID 封装

    格式: {external_id}_{season}
    示例: 4507094_2324

    设计原则:
        - 不可变: frozen=True 防止意外修改
        - 内存优化: slots=True 减少内存占用
        - 自验证: 构造时自动验证格式

    使用示例:
        # 正确用法 - 使用类型安全的构造
        match_id = MatchID.create("4507094", "2324")
        match_id = MatchID.parse("4507094_2324")

        # 错误用法 - 手动拼接（严禁）
        # match_id = f"{external_id}_{season}"  # ❌ 禁止

        # 获取各种格式
        str_id = str(match_id)           # "4507094_2324"
        external = match_id.external_id  # "4507094"
        season = match_id.season         # "2324"
    """

    external_id: str
    season: str

    # ID 格式验证正则
    _ID_PATTERN = re.compile(r"^(\d+)_(\d{4})$")

    def __post_init__(self):
        """验证 ID 格式"""
        if not self.external_id or not self.external_id.isdigit():
            raise ValueError(f"external_id 必须是数字: {self.external_id}")

        if not self.season or len(self.season) != 4 or not self.season.isdigit():
            raise ValueError(f"season 必须是 4 位数字: {self.season}")

    @classmethod
    def create(cls, external_id: str, season: str) -> "MatchID":
        """
        创建 MatchID 实例（推荐使用）

        Args:
            external_id: 外部比赛 ID
            season: 赛季代码 (如 "2324")

        Returns:
            MatchID 实例
        """
        return cls(external_id=external_id, season=season)

    @classmethod
    def parse(cls, match_id_str: str) -> "MatchID":
        """
        从字符串解析 MatchID

        Args:
            match_id_str: ID 字符串，格式 "external_id_season"

        Returns:
            MatchID 实例

        Raises:
            ValueError: 格式无效
        """
        if not match_id_str:
            raise ValueError("match_id_str 不能为空")

        match = cls._ID_PATTERN.match(match_id_str.strip())
        if not match:
            raise ValueError(
                f"无效的 match_id 格式: {match_id_str}，期望格式: <external_id>_<season> (如 4507094_2324)"
            )

        external_id, season = match.groups()
        return cls(external_id=external_id, season=season)

    def __str__(self) -> str:
        """返回标准字符串格式: external_id_season"""
        return f"{self.external_id}_{self.season}"

    def __repr__(self) -> str:
        return f"MatchID('{self}')"

    def to_int_pair(self) -> tuple[int, int]:
        """返回 (external_id_int, season_int) 元组"""
        return (int(self.external_id), int(self.season))


class Season:
    """
    赛季工具类 - 赛季转换与验证

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
        标准化赛季代码

        Args:
            season: 任意格式的赛季代码

        Returns:
            标准化的 4 位代码 (如 "2023")

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

        # 4 位年份
        if season.isdigit() and len(season) == 4:
            return season

        # 2 位年份 (23 -> 2023)
        if season.isdigit() and len(season) == 2:
            year = int(season)
            return f"20{year}" if year < 50 else f"19{year}"

        logger.warning(f"无法识别的赛季格式: {season}，使用默认值")
        return "0000"


# ============================================================================
# 便捷函数
# ============================================================================


def create_match_id(external_id: str, season: str) -> MatchID:
    """
    创建 MatchID 的便捷函数

    这是推荐的全局入口点，用于替代所有手动拼接字符串的操作。
    """
    return MatchID.create(external_id, Season.normalize(season))


def parse_match_id(match_id_str: str) -> MatchID:
    """解析 MatchID 的便捷函数"""
    return MatchID.parse(match_id_str)


# ============================================================================
# 模块测试
# ============================================================================

if __name__ == "__main__":
    # 测试 MatchID
    print("=== MatchID 测试 ===")

    # 创建
    mid1 = MatchID.create("4507094", "2324")
    print(f"创建: {mid1}")

    # 解析
    mid2 = MatchID.parse("4507094_2324")
    print(f"解析: {mid2}")

    # 属性访问
    print(f"external_id: {mid2.external_id}")
    print(f"season: {mid2.season}")
    print(f"to_int_pair: {mid2.to_int_pair()}")

    # 测试 MatchStatus
    print("\n=== MatchStatus 测试 ===")

    # 从字符串解析
    status1 = MatchStatus.from_string("finished")
    print(f"解析状态: {status1}")

    # 判断
    print(f"是终态: {status1.is_final()}")
    print(f"允许提取特征: {status1.allows_feature_extraction()}")

    # 测试 Season
    print("\n=== Season 测试 ===")
    for s in ["23/24", "2023-2024", "23-24", "2023"]:
        print(f"{s} -> {Season.normalize(s)}")
