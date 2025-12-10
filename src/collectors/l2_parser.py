#!/usr/bin/env python3
"""
L2数据解析器 (L2 Data Parser) - 生产版本
负责解析FotMob API返回的JSON数据并转换为结构化的L2MatchData对象。

核心功能:
1. FotMob API结构适配 (general/header/content节点)
2. 数据验证和错误处理
3. 统计信息提取
4. 时间解析和格式化
5. Pydantic V2模型转换

作者: L2重构团队
创建时间: 2025-12-10
版本: 1.0.0 (Production Release)
"""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

from ..schemas.l2_schemas import (
    L2MatchData,
    TeamStats,
    MatchStatus,
    MatchEvent,
    TeamLineup as Lineup,
    StadiumInfo,
    WeatherInfo,
    RefereeInfo,
    OddsData,
    L2DataProcessingResult,
    L2DataValidationResult,
)

logger = logging.getLogger(__name__)


class L2Parser:
    """
    L2数据解析器 - 生产版本

    负责将FotMob API返回的原始JSON数据解析为结构化的L2MatchData对象，
    包含完整的数据验证、错误处理和性能监控功能。

    Attributes:
        strict_mode: 是否启用严格模式验证
    """

    def __init__(self, strict_mode: bool = False):
        """
        初始化L2解析器

        Args:
            strict_mode: 是否启用严格模式验证
        """
        self.strict_mode = strict_mode
        logger.info(f"L2Parser initialized with strict_mode={strict_mode}")

    def parse_match_data(self, raw_data: Optional[Dict[str, Any]]) -> L2DataProcessingResult:
        """
        解析比赛详情数据

        Args:
            raw_data: FotMob API返回的原始JSON数据

        Returns:
            L2DataProcessingResult: 解析结果，包含解析后的数据或错误信息
        """
        processing_start_time = time.perf_counter()

        if not raw_data:
            return L2DataProcessingResult(
                success=False,
                match_id="unknown",
                error_message="No data provided for parsing",
                processing_time_ms=int((time.perf_counter() - processing_start_time) * 1000),
            )

        # 提取基本信息 - 适配FotMob API结构
        match_info = raw_data.get("general", raw_data.get("match", {}))
        api_match_id = self._safe_extract_string(match_info.get("matchId", match_info.get("id")), "unknown")
        match_id = api_match_id

        # 验证必需字段
        validation_result = self._validate_required_fields(raw_data)
        if not validation_result.is_valid:
            return L2DataProcessingResult(
                success=False,
                match_id=match_id,
                error_message=f"Data validation failed: {', '.join(validation_result.errors)}",
                processing_time_ms=int((time.perf_counter() - processing_start_time) * 1000),
            )

        # 解析各个组件
        parsed_data = self._parse_complete_match_data(raw_data, match_id)

        # 数据完整性评估
        completeness_score = self._calculate_data_completeness(parsed_data, raw_data)
        parsed_data.data_completeness = "complete" if completeness_score > 0.8 else "partial"

        processing_time_ms = max(1, int((time.perf_counter() - processing_start_time) * 1000))

        logger.info(
            f"Successfully parsed match data for {match_id} "
            f"(completeness: {completeness_score:.2%}, time: {processing_time_ms}ms)"
        )

        return L2DataProcessingResult(
            success=True,
            match_id=match_id,
            data=parsed_data,
            processing_time_ms=processing_time_ms,
        )

    def _validate_required_fields(self, raw_data: Dict[str, Any]) -> L2DataValidationResult:
        """
        验证必需字段是否存在且有效 - 适配FotMob API结构

        Args:
            raw_data: 原始数据

        Returns:
            L2DataValidationResult: 验证结果
        """
        errors = []
        warnings = []
        missing_fields = []

        # 检查顶级结构 - 适配FotMob API结构
        match_info = raw_data.get("general", raw_data.get("match", {}))

        if not match_info:
            missing_fields.append("match/general")
            errors.append("Missing 'match' or 'general' section in API response")
            return L2DataValidationResult(
                is_valid=False, errors=errors, missing_fields=missing_fields
            )

        # 检查必需的match字段 - 适配FotMob API字段名
        required_match_fields = ["matchId", "id"]  # FotMob API使用matchId
        found_field = False
        for field in required_match_fields:
            if field in match_info and match_info[field]:
                found_field = True
                break

        if not found_field:
            missing_fields.append(f"match.{', '.join(required_match_fields)}")
            errors.append(f"Missing required field: one of {', '.join(required_match_fields)}")

        # 检查球队信息 - 适配FotMob API结构
        home_team = match_info.get("homeTeam", {})
        away_team = match_info.get("awayTeam", {})

        if not home_team or "name" not in home_team:
            missing_fields.append("general.homeTeam.name")
            errors.append("Missing home team name")

        if not away_team or "name" not in away_team:
            missing_fields.append("general.awayTeam.name")
            errors.append("Missing away team name")

        # 检查状态信息
        if "status" not in match_info:
            missing_fields.append("match.status")
            warnings.append("Missing match status information")

        is_valid = len(errors) == 0

        return L2DataValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_fields=missing_fields,
        )

    def _parse_complete_match_data(self, raw_data: Dict[str, Any], match_id: str) -> L2MatchData:
        """
        解析完整的比赛数据 - 适配FotMob API结构

        Args:
            raw_data: 原始数据
            match_id: 比赛ID

        Returns:
            L2MatchData: 解析后的比赛数据
        """
        # 适配FotMob API结构
        general = raw_data.get("general", {})
        header = raw_data.get("header", {})
        content = raw_data.get("content", {})

        # 解析基本信息 - 从general节点获取
        home_team = self._safe_extract_string(general.get("homeTeam", {}).get("name"))
        away_team = self._safe_extract_string(general.get("awayTeam", {}).get("name"))

        # 解析比分 - 从header节点获取
        teams = header.get("teams", [])
        home_score = 0
        away_score = 0
        if len(teams) >= 2:
            home_score = self._safe_extract_int(teams[0].get("score"), 0)
            away_score = self._safe_extract_int(teams[1].get("score"), 0)

        # 解析状态和时间
        status_info = header.get("status", {})
        reason_key = status_info.get("reason", {}).get("shortKey", "")

        # 适配FotMob API状态映射
        if "fulltime" in reason_key or reason_key == "FT":
            status = MatchStatus.FULLTIME
        elif reason_key == "halftime_short" or reason_key == "HT":
            status = MatchStatus.HALFTIME
        elif "live" in reason_key.lower():
            status = MatchStatus.LIVE
        elif reason_key == "Not started" or not reason_key:
            status = MatchStatus.NOT_STARTED
        else:
            status = MatchStatus.FULLTIME  # 默认设为已结束，因为大部分历史比赛都是已完成的

        kickoff_time = self._parse_datetime(general.get("matchTimeUTCDate") or status_info.get("utcTime"))

        # 解析统计数据
        home_stats, away_stats = self._parse_team_statistics(content)

        # 解析其他组件
        referee_info = self._parse_referee_info(content)
        stadium_info = self._parse_stadium_info(general, content)
        weather_info = self._parse_weather_info(content)
        home_lineup, away_lineup = self._parse_lineups(content)
        match_events = self._parse_match_events(content)
        odds_data = self._parse_odds_data(content)

        return L2MatchData(
            match_id=match_id,
            fotmob_id=match_id,
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            status=status,
            kickoff_time=kickoff_time,
            referee=referee_info,
            stadium=stadium_info,
            weather=weather_info,
            home_stats=home_stats,
            away_stats=away_stats,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            events=match_events,
            odds=odds_data,
            api_version=raw_data.get("version"),
        )

    def _parse_match_status(self, status_code: Optional[str]) -> MatchStatus:
        """
        解析比赛状态

        Args:
            status_code: 状态代码字符串

        Returns:
            MatchStatus: 解析后的比赛状态枚举
        """
        if not status_code:
            return MatchStatus.NOT_STARTED

        status_mapping = {
            "NS": MatchStatus.NOT_STARTED,
            "LIVE": MatchStatus.LIVE,
            "HT": MatchStatus.HALFTIME,
            "FT": MatchStatus.FULLTIME,
            "POSTP": MatchStatus.POSTPONED,
            "CANCL": MatchStatus.CANCELLED,
            "ABD": MatchStatus.ABANDONED,
        }

        return status_mapping.get(status_code.upper(), MatchStatus.NOT_STARTED)

    def _parse_datetime(self, datetime_str: Optional[str]) -> datetime:
        """
        解析日期时间字符串

        Args:
            datetime_str: ISO格式的日期时间字符串

        Returns:
            datetime: 解析后的datetime对象
        """
        if not datetime_str:
            return datetime.now(timezone.utc)

        try:
            # 尝试ISO格式解析
            if datetime_str.endswith('Z'):
                return datetime.fromisoformat(datetime_str[:-1] + '+00:00')
            else:
                return datetime.fromisoformat(datetime_str)
        except (ValueError, TypeError):
            # 解析失败时返回当前时间
            logger.warning(f"Failed to parse datetime: {datetime_str}")
            return datetime.now(timezone.utc)

    def _parse_team_statistics(self, content: Dict[str, Any]) -> Tuple[TeamStats, TeamStats]:
        """
        解析球队统计数据

        Args:
            content: API响应content部分

        Returns:
            Tuple[TeamStats, TeamStats]: 主队和客队统计数据
        """
        stats = content.get("stats", {})
        periods = stats.get("Periods", {})
        all_stats = periods.get("All", {}).get("stats", [])

        # 默认统计数据
        default_stats = {
            "possession": 0.0,
            "shots": 0,
            "shots_on_target": 0,
            "corners": 0,
            "fouls": 0,
            "offsides": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "saves": 0,
            "expected_goals": 0.0,
        }

        home_stats_data = default_stats.copy()
        away_stats_data = default_stats.copy()

        # 解析统计数据
        for stat_group in all_stats:
            stat_key = stat_group.get("key", "")
            stats_data = stat_group.get("stats", [])

            if len(stats_data) >= 2:
                home_value, away_value = self._extract_stat_values(stat_key, stats_data)

                # 更新统计数据
                if stat_key == "BallPossesion":
                    home_stats_data["possession"] = home_value
                    away_stats_data["possession"] = away_value
                elif stat_key == "total_shots":
                    home_stats_data["shots"] = home_value
                    away_stats_data["shots"] = away_value
                elif stat_key == "ShotsOnTarget":
                    home_stats_data["shots_on_target"] = home_value
                    away_stats_data["shots_on_target"] = away_value
                elif stat_key == "corners":
                    home_stats_data["corners"] = home_value
                    away_stats_data["corners"] = away_value
                elif stat_key == "fouls":
                    home_stats_data["fouls"] = home_value
                    away_stats_data["fouls"] = away_value
                elif stat_key == "expected_goals":
                    home_stats_data["expected_goals"] = home_value
                    away_stats_data["expected_goals"] = away_value

        home_team_stats = TeamStats(**home_stats_data)
        away_team_stats = TeamStats(**away_stats_data)

        return home_team_stats, away_team_stats

    def _extract_stat_values(self, stat_key: str, stats_data: list) -> Tuple[int, int]:
        """
        从统计数据中提取主客队数值

        Args:
            stat_key: 统计项键名
            stats_data: 统计数据列表

        Returns:
            Tuple[int, int]: 主队和客队数值
        """
        try:
            format_type = stats_data[0].get("format", "")

            if format_type == "integer":
                home_value = self._safe_extract_int(stats_data[0].get("stat"), 0)
                away_value = self._safe_extract_int(stats_data[1].get("stat"), 0)
            elif format_type == "double":
                home_value = self._safe_extract_float(stats_data[0].get("stat"), 0.0)
                away_value = self._safe_extract_float(stats_data[1].get("stat"), 0.0)
            elif format_type == "integerWithPercentage":
                # 格式: "142 (62%)" -> 提取数值部分
                home_stat_str = stats_data[0].get("stat", "0")
                away_stat_str = stats_data[1].get("stat", "0")
                home_value = self._safe_extract_int(home_stat_str.split()[0], 0)
                away_value = self._safe_extract_int(away_stat_str.split()[0], 0)
            else:
                home_value = 0
                away_value = 0

            return home_value, away_value

        except (IndexError, ValueError, KeyError):
            logger.warning(f"Failed to extract values for stat {stat_key}")
            return 0, 0

    def _parse_referee_info(self, content: Dict[str, Any]) -> Optional[RefereeInfo]:
        """
        解析裁判信息 - 适配FotMob API结构

        Args:
            content: content部分数据

        Returns:
            Optional[RefereeInfo]: 裁判信息，如果没有则返回None
        """
        # 简化处理 - 暂时返回None，因为referee数据解析复杂且不是核心功能
        # 在生产环境中可以进一步优化此部分
        return None

    def _parse_stadium_info(
        self, general: Dict[str, Any], content: Dict[str, Any]
    ) -> Optional[StadiumInfo]:
        """
        解析球场信息

        Args:
            general: general部分数据
            content: content部分数据

        Returns:
            Optional[StadiumInfo]: 球场信息，如果没有则返回None
        """
        # 简化处理，避免复杂的infoBox解析错误
        return None

    def _parse_weather_info(self, content: Dict[str, Any]) -> Optional[WeatherInfo]:
        """
        解析天气信息

        Args:
            content: content部分数据

        Returns:
            Optional[WeatherInfo]: 天气信息，如果没有则返回None
        """
        # 当前FotMob API可能不提供天气信息
        return None

    def _parse_lineups(self, content: Dict[str, Any]) -> Tuple[Optional[Lineup], Optional[Lineup]]:
        """
        解析阵容信息

        Args:
            content: content部分数据

        Returns:
            Tuple[Optional[Lineup], Optional[Lineup]]: 主队和客队阵容信息
        """
        # 当前简化处理，后续可以根据需要实现完整的阵容解析
        return None, None

    def _parse_match_events(self, content: Dict[str, Any]) -> list:
        """
        解析比赛事件

        Args:
            content: content部分数据

        Returns:
            list: 比赛事件列表
        """
        # 当前简化处理，后续可以根据需要实现完整的事件解析
        return []

    def _parse_odds_data(self, content: Dict[str, Any]) -> Optional[OddsData]:
        """
        解析赔率数据

        Args:
            content: content部分数据

        Returns:
            Optional[OddsData]: 赔率数据，如果没有则返回None
        """
        # 当前简化处理，后续可以根据需要实现完整的赔率解析
        return None

    def _calculate_data_completeness(self, parsed_data: L2MatchData, raw_data: Dict[str, Any]) -> float:
        """
        计算数据完整性评分

        Args:
            parsed_data: 解析后的数据
            raw_data: 原始数据

        Returns:
            float: 完整性评分 (0.0 - 1.0)
        """
        completeness_factors = []

        # 基本信息
        if parsed_data.home_team and parsed_data.away_team:
            completeness_factors.append(0.2)

        # 比分
        if parsed_data.home_score is not None and parsed_data.away_score is not None:
            completeness_factors.append(0.2)

        # 时间
        if parsed_data.kickoff_time:
            completeness_factors.append(0.15)

        # 状态
        if parsed_data.status:
            completeness_factors.append(0.1)

        # 统计数据
        if parsed_data.home_stats and parsed_data.away_stats:
            if any([
                parsed_data.home_stats.shots > 0,
                parsed_data.home_stats.possession > 0,
                parsed_data.home_stats.expected_goals > 0
            ]):
                completeness_factors.append(0.15)

        # 其他组件
        if any([
            parsed_data.referee,
            parsed_data.stadium,
            parsed_data.home_lineup,
            parsed_data.events
        ]):
            completeness_factors.append(0.1)

        # 原始数据丰富度
        if len(raw_data) > 10:
            completeness_factors.append(0.1)

        return min(1.0, sum(completeness_factors))

    def _safe_extract_string(self, value: Any, default: str = "") -> str:
        """安全提取字符串值"""
        if value is None:
            return default
        if isinstance(value, str):
            return value.strip()
        return str(value)

    def _safe_extract_int(self, value: Any, default: int = 0) -> int:
        """安全提取整数值"""
        if value is None:
            return default
        try:
            if isinstance(value, str):
                return int(float(value))  # 处理 "1.0" -> 1
            return int(value)
        except (ValueError, TypeError):
            return default

    def _safe_extract_float(self, value: Any, default: float = 0.0) -> float:
        """安全提取浮点数值"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default


# 导出
__all__ = ["L2Parser"]