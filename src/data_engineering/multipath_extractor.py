#!/usr/bin/env python3
"""
V28.0 多路径 JSONB 提取器 (Multi-Path Extractor)
===================================================

核心设计:
1. 多路径探测：针对 raw_match_data 的 JSONB 结构，按优先级尝试多条路径
2. 降级解析：当核心路径失败时，自动降级到备用路径
3. 正则解析：针对比分字符串的正则表达式解析
4. 填充率优化：目标 80%+ 填充率

探测路径（按优先级）:
- 路径 1: content -> stats -> Periods -> All -> stats (核心统计)
- 路径 2: content -> matchFacts -> stats (备用路径)
- 路径 3: content -> header -> status -> scoreStr (比分正则解析)

Author: Senior Data Engineer
Version: V28.0
Date: 2025-12-27
"""

from dataclasses import dataclass, field
from enum import Enum
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class ExtractionPath(Enum):
    """提取路径枚举"""

    CORE_STATS = "core_stats"  # content -> stats -> Periods -> All -> stats
    MATCH_FACTS = "match_facts"  # content -> matchFacts -> stats
    SCORE_STRING = "score_string"  # content -> header -> status -> scoreStr


@dataclass
class MatchStats:
    """单场比赛统计数据"""

    match_id: str
    match_date: str
    home_team: str
    away_team: str
    home_score: int | None = None
    away_score: int | None = None

    # 主队统计
    home_xg: float | None = None
    home_possession: float | None = None
    home_shots: int | None = None
    home_shots_on_target: int | None = None
    home_passes: int | None = None
    home_team_rating: float | None = None

    # 客队统计
    away_xg: float | None = None
    away_possession: float | None = None
    away_shots: int | None = None
    away_shots_on_target: int | None = None
    away_passes: int | None = None
    away_team_rating: float | None = None

    # 元数据
    extraction_path: ExtractionPath | None = None
    extraction_success: bool = False

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "match_id": self.match_id,
            "match_date": self.match_date,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "home_xg": self.home_xg,
            "away_xg": self.away_xg,
            "home_possession": self.home_possession,
            "away_possession": self.away_possession,
            "home_shots": self.home_shots,
            "away_shots": self.away_shots,
            "home_shots_on_target": self.home_shots_on_target,
            "away_shots_on_target": self.away_shots_on_target,
            "home_passes": self.home_passes,
            "away_passes": self.away_passes,
            "home_team_rating": self.home_team_rating,
            "away_team_rating": self.away_team_rating,
            "extraction_path": self.extraction_path.value if self.extraction_path else None,
            "extraction_success": self.extraction_success,
        }


@dataclass
class ExtractionStats:
    """提取统计"""

    total_processed: int = 0
    path_success_count: dict[ExtractionPath, int] = field(default_factory=dict)

    def record_success(self, path: ExtractionPath) -> None:
        """记录路径成功"""
        if path not in self.path_success_count:
            self.path_success_count[path] = 0
        self.path_success_count[path] += 1

    def get_path_success_rate(self, path: ExtractionPath) -> float:
        """获取路径成功率"""
        if self.total_processed == 0:
            return 0.0
        return self.path_success_count.get(path, 0) / self.total_processed * 100


class MultiPathExtractor:
    """
    多路径 JSONB 提取器

    核心功能:
    1. 按优先级尝试多条提取路径
    2. 自动降级到备用路径
    3. 正则表达式解析比分字符串
    4. 统计提取成功率

    使用示例:
        extractor = MultiPathExtractor()
        stats = extractor.extract_from_jsonb(match_id, raw_data)
    """

    # 统计键到特征键的映射
    STAT_KEY_MAPPING = {
        "BallPossesion": ("home_possession", "away_possession"),
        "expected_goals": ("home_xg", "away_xg"),
        "total_shots": ("home_shots", "away_shots"),
        "ShotsOnTarget": ("home_shots_on_target", "away_shots_on_target"),
        "accurate_passes": ("home_passes", "away_passes"),
    }

    # 正则表达式模式
    SCORE_PATTERN = re.compile(r"(\d+)\s*[-:]\s*(\d+)")

    def __init__(self) -> None:
        """初始化提取器"""
        self.stats = ExtractionStats()

    def extract_from_jsonb(
        self,
        match_id: str,
        raw_data: dict[str, Any],
        match_date: str,
        home_team: str,
        away_team: str,
        home_score: int | None = None,
        away_score: int | None = None,
    ) -> MatchStats:
        """
        从 JSONB 数据中提取比赛统计

        Args:
            match_id: 比赛 ID
            raw_data: raw_match_data 的 raw_data 字段
            match_date: 比赛日期
            home_team: 主队名称
            away_team: 客队名称
            home_score: 主队得分（可选）
            away_score: 客队得分（可选）

        Returns:
            MatchStats: 提取的比赛统计数据
        """
        self.stats.total_processed += 1

        # 创建基础统计对象
        stats = MatchStats(
            match_id=match_id,
            match_date=match_date,
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
        )

        # 按优先级尝试提取路径
        # 路径 1: 核心统计路径
        if self._extract_from_core_stats(raw_data, stats):
            stats.extraction_path = ExtractionPath.CORE_STATS
            stats.extraction_success = True
            self.stats.record_success(ExtractionPath.CORE_STATS)
            return stats

        # 路径 2: matchFacts 备用路径
        if self._extract_from_match_facts(raw_data, stats):
            stats.extraction_path = ExtractionPath.MATCH_FACTS
            stats.extraction_success = True
            self.stats.record_success(ExtractionPath.MATCH_FACTS)
            return stats

        # 路径 3: 比分字符串正则解析
        if self._extract_from_score_string(raw_data, stats):
            stats.extraction_path = ExtractionPath.SCORE_STRING
            stats.extraction_success = True
            self.stats.record_success(ExtractionPath.SCORE_STRING)
            return stats

        # 所有路径都失败，返回部分数据
        stats.extraction_success = False
        logger.debug(f"所有提取路径都失败: match_id={match_id}")
        return stats

    def _extract_from_core_stats(self, raw_data: dict[str, Any], stats: MatchStats) -> bool:
        """
        从核心统计路径提取数据

        路径: content -> stats -> Periods -> All -> stats

        Args:
            raw_data: JSONB 原始数据
            stats: 统计对象（将被修改）

        Returns:
            bool: 是否提取成功
        """
        try:
            content = raw_data.get("content", {})
            stats_data = content.get("stats", {})
            periods = stats_data.get("Periods", {})
            all_stats = periods.get("All", {}).get("stats", [])

            if not all_stats:
                return False

            # 查找 top_stats 组
            top_stats = None
            for stat_group in all_stats:
                if stat_group.get("key") == "top_stats":
                    top_stats = stat_group.get("stats", [])
                    break

            if not top_stats:
                return False

            # 提取各项统计
            extracted_any = False
            for stat in top_stats:
                key = stat.get("key")
                values = stat.get("stats", [])

                if key in self.STAT_KEY_MAPPING and values and len(values) >= 2:
                    home_key, away_key = self.STAT_KEY_MAPPING[key]
                    home_value = self._parse_stat_value(values[0])
                    away_value = self._parse_stat_value(values[1])

                    if home_value is not None:
                        setattr(stats, home_key, home_value)
                        extracted_any = True
                    if away_value is not None:
                        setattr(stats, away_key, away_value)
                        extracted_any = True

            # 提取球队评分（注意：FotMob API 使用驼峰式命名）
            lineup = content.get("lineup", {})
            home_rating = lineup.get("homeTeam", {}).get("rating")
            away_rating = lineup.get("awayTeam", {}).get("rating")

            if home_rating:
                try:
                    stats.home_team_rating = float(home_rating)
                    extracted_any = True
                except (ValueError, TypeError):
                    pass
            if away_rating:
                try:
                    stats.away_team_rating = float(away_rating)
                    extracted_any = True
                except (ValueError, TypeError):
                    pass

            return extracted_any

        except Exception as e:
            logger.debug(f"核心路径提取失败: {e}")
            return False

    def _extract_from_match_facts(self, raw_data: dict[str, Any], stats: MatchStats) -> bool:
        """
        从 matchFacts 备用路径提取数据

        路径: content -> matchFacts -> stats

        Args:
            raw_data: JSONB 原始数据
            stats: 统计对象（将被修改）

        Returns:
            bool: 是否提取成功
        """
        try:
            content = raw_data.get("content", {})

            # 尝试多个可能的 matchFacts 键名
            match_facts = (
                content.get("matchFacts", {})
                or content.get("matchfacts", {})
                or content.get("header", {}).get("matchFacts", {})
            )

            if not match_facts:
                return False

            stats_data = match_facts.get("stats", [])
            if not stats_data:
                return False

            # 尝试从 stats 数组中提取数据
            extracted_any = False
            for stat in stats_data:
                if isinstance(stat, dict) and "name" in stat and "value" in stat:
                    name = stat["name"]
                    value = stat["value"]

                    # 映射到我们的特征
                    if "xg" in name.lower() or "expected_goals" in name.lower():
                        # 尝试解析 xG 值
                        parsed = self._parse_stat_value(value)
                        if parsed is not None and not stats.home_xg:
                            stats.home_xg = parsed
                            extracted_any = True

            return extracted_any

        except Exception as e:
            logger.debug(f"matchFacts 路径提取失败: {e}")
            return False

    def _extract_from_score_string(self, raw_data: dict[str, Any], stats: MatchStats) -> bool:
        """
        从比分字符串中提取数据（正则解析）

        路径: content -> header -> status -> scoreStr

        Args:
            raw_data: JSONB 原始数据
            stats: 统计对象（将被修改）

        Returns:
            bool: 是否提取成功
        """
        try:
            content = raw_data.get("content", {})
            header = content.get("header", {})
            status = header.get("status", {})

            # 尝试多个可能的比分字段
            score_str = status.get("scoreStr") or status.get("score_str") or header.get("scoreStr")

            if not score_str:
                return False

            # 使用正则表达式提取比分
            match = self.SCORE_PATTERN.search(str(score_str))
            if match:
                try:
                    home_score = int(match.group(1))
                    away_score = int(match.group(2))

                    # 只有当原数据中没有比分时才使用正则提取的比分
                    if stats.home_score is None:
                        stats.home_score = home_score
                    if stats.away_score is None:
                        stats.away_score = away_score

                    return True
                except (ValueError, IndexError):
                    pass

            return False

        except Exception as e:
            logger.debug(f"比分字符串解析失败: {e}")
            return False

    def _parse_stat_value(self, value: Any) -> float | None:
        """
        解析统计值

        处理多种格式:
        - 数字: 1.23
        - 字符串数字: "1.23"
        - 百分比字符串: "52%" -> 52.0
        - 复合字符串: "421 (84%)" -> 421.0
        - FotMob API 字典格式: {"value": "1.23"} -> 1.23

        Args:
            value: 统计值

        Returns:
            Optional[float]: 解析后的数值，如果无法解析则返回 None
        """
        if value is None:
            return None

        # FotMob API 格式: {"value": "..."}
        if isinstance(value, dict):
            value = value.get("value") if "value" in value else None
            if value is None:
                return None

        # 直接是数字
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            value = value.strip()

            # 提取数字部分
            match = re.search(r"[-+]?\d*\.?\d+", value)
            if match:
                try:
                    return float(match.group())
                except ValueError:
                    pass

        return None

    def get_extraction_report(self) -> dict[str, Any]:
        """获取提取报告"""
        return {
            "total_processed": self.stats.total_processed,
            "path_success_rates": {path.value: self.stats.get_path_success_rate(path) for path in ExtractionPath},
            "path_success_counts": self.stats.path_success_count,
        }


# ============================================================================
# 便捷函数
# ============================================================================


def extract_match_stats_batch(match_records: list[dict[str, Any]]) -> tuple[list[MatchStats], ExtractionStats]:
    """
    批量提取比赛统计

    Args:
        match_records: 比赛记录列表，每个记录包含:
            - match_id, match_date, home_team, away_team
            - raw_data (JSONB 数据)
            - home_score, away_score (可选)

    Returns:
        Tuple[List[MatchStats], ExtractionStats]: 提取的统计数据和提取统计
    """
    extractor = MultiPathExtractor()
    results = []

    for record in match_records:
        stats = extractor.extract_from_jsonb(
            match_id=record["match_id"],
            raw_data=record["raw_data"],
            match_date=record["match_date"],
            home_team=record["home_team"],
            away_team=record["away_team"],
            home_score=record.get("home_score"),
            away_score=record.get("away_score"),
        )
        results.append(stats)

    return results, extractor.stats
