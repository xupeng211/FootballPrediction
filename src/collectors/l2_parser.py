#!/usr/bin/env python3
"""
L2数据解析器 - 企业级完整版本
L2 Data Parser - Enterprise Complete Version

用于解析从FotMob API获取的原始数据，提取结构化的L2信息：
- 比赛基本信息和元数据 (Referee, Weather, Attendance, Stadium)
- 球队统计数据和深度战术数据 (Odds, Formation, Lineups)
- 比赛事件数据
- 射门分布数据
- 球员评分数据
- 完整阵容信息

作者: L2开发团队
创建时间: 2025-12-10
版本: 2.6.0 (Enterprise Release - Ultimate Score Path Correction)
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field, ValidationError

from ..schemas.l2_schemas import (
    L2MatchData,
    TeamStats,
    L2MatchEvent,
    ShotData,
    L2PlayerRating,
    L2DataProcessingResult,
    RefereeInfo,
    WeatherInfo,
    StadiumInfo,
    OddsData,
    TeamLineup
)


class EventType(str, Enum):
    """比赛事件类型"""
    GOAL = "Goal"
    CARD = "Card"
    SUBSTITUTION = "Substitution"
    VAR = "Var"
    PENALTY_SHOOTOUT = "PenaltyShootout"
    PERIOD_START = "PeriodStart"


@dataclass
class ParsingContext:
    """解析上下文，用于在解析过程中传递状态信息"""
    raw_data: Dict[str, Any]
    parsed_sections: List[str]
    errors: List[str]
    logger: logging.Logger


class L2Parser:
    """
    L2数据解析器 - 企业级完整版本

    专门用于解析FotMob API返回的原始比赛数据，提取结构化的L2信息。
    支持完整的数据段解析和元数据提取。
    """

    def __init__(self, strict_mode: bool = False):
        """
        初始化解析器

        Args:
            strict_mode: 严格模式，启用时更严格的验证
        """
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(__name__)

        # 定义数据提取路径 - 黄金路径
        self.field_paths = {
            'match_id': ['general', 'matchId'],
            'home_team': ['general', 'homeTeam', 'name'],
            'away_team': ['general', 'awayTeam', 'name'],
            'competition': ['general', 'competition', 'name'],
            'home_score': ['header', 'teams', 0, 'score'],
            'away_score': ['header', 'teams', 1, 'score'],
            'kickoff_time': ['general', 'startTimeUTC'],
            'status': ['header', 'status', 'reason', 'short']
        }

    def parse_match_data(self, raw_data: Union[Dict[str, Any], str]) -> L2DataProcessingResult:
        """
        解析比赛数据的主入口方法

        Args:
            raw_data: FotMob API返回的原始数据（字典或JSON字符串）

        Returns:
            L2DataProcessingResult: 解析结果，包含所有提取的L2数据
        """
        try:
            # 初始化解析上下文
            if isinstance(raw_data, str):
                import json
                raw_data = json.loads(raw_data)

            ctx = ParsingContext(
                raw_data=raw_data,
                parsed_sections=[],
                errors=[],
                logger=self.logger
            )

            self.logger.info("Starting L2 data parsing")

            # 执行各个数据段的解析
            result_data = self._parse_all_sections(ctx)

            # 创建最终结果
            result = L2DataProcessingResult(
                success=True,
                data=result_data,
                parsed_sections=ctx.parsed_sections,
                errors=ctx.errors,
                metadata={
                    "total_sections": len(ctx.parsed_sections),
                    "parser_version": "2.6.0",
                    "strict_mode": self.strict_mode
                }
            )

            self.logger.info(f"Successfully parsed {len(ctx.parsed_sections)} data sections: {ctx.parsed_sections}")
            return result

        except Exception as e:
            error_msg = f"Error parsing match data: {str(e)}"
            self.logger.error(error_msg)

            return L2DataProcessingResult(
                success=False,
                data=L2MatchData(
                    match_id="",
                    fotmob_id="",
                    home_team="",
                    away_team="",
                    home_score=0,
                    away_score=0
                ),
                parsed_sections=[],
                errors=[error_msg],
                metadata={"parser_version": "2.6.0", "error": True}
            )

    def _parse_all_sections(self, ctx: ParsingContext) -> L2MatchData:
        """解析所有数据段"""

        # 基础信息 (始终最先解析)
        basic_info = self._extract_match_basic_info(ctx)

        # 核心统计数据
        team_stats = self._parse_team_stats(ctx)

        # 比赛事件
        match_events = self._parse_match_events(ctx)

        # 射门数据
        shot_data = self._parse_shot_data(ctx)

        # 球员评分
        player_ratings = self._parse_player_ratings(ctx)

        # 元数据 (体育场、裁判、天气等)
        metadata = self._parse_metadata(ctx)

        # 赔率数据
        odds_data = self._parse_odds_data(ctx)

        # 阵型和阵容数据
        home_formation, away_formation = self._extract_formations(ctx)
        home_lineup, away_lineup = self._extract_lineups(ctx)

        # 期望进球 (xG) 数据
        xg_data = self._parse_xg_data(ctx)

        # 组装最终数据
        return L2MatchData(
            # 必需的基础信息
            match_id=str(basic_info.get("match_id", "")),
            fotmob_id=str(basic_info.get("match_id", "")),
            home_team=str(basic_info.get("home_team", "")),
            away_team=str(basic_info.get("away_team", "")),
            home_score=int(basic_info.get("home_score", 0)),
            away_score=int(basic_info.get("away_score", 0)),
            status=str(basic_info.get("status", "scheduled")),
            kickoff_time=basic_info.get("kickoff_time"),

            # 统计数据
            home_stats=team_stats.get("home") if team_stats and team_stats.get("home") else TeamStats(),
            away_stats=team_stats.get("away") if team_stats and team_stats.get("away") else TeamStats(),

            # 比赛事件
            events=match_events,

            # 射门数据
            shot_map=shot_data,

            # 球员评分数据 (转换为字典格式)
            player_ratings={str(r.player_id or i): r for i, r in enumerate(player_ratings)} if player_ratings else {},

            # 元数据
            stadium_info=metadata.get("stadium") if metadata else None,
            referee_info=metadata.get("referee") if metadata else None,
            weather_info=metadata.get("weather") if metadata else None,

            # 阵容信息
            home_lineup=home_lineup,
            away_lineup=away_lineup,

            # 赔率数据
            odds_data=odds_data,

            # 数据完整性评分 (基于解析的段落数)
            data_completeness_score=min(len(ctx.parsed_sections) / 10.0, 1.0)
        )

    def _extract_match_basic_info(self, ctx: ParsingContext) -> Dict[str, Any]:
        """
        提取比赛基础信息 - 终极比分路径校正版本

        CRITICAL: 强制使用比分字符串作为主要提取源
        """
        try:
            basic_info = {}

            # Step 1: 首先提取比分字符串 (CRITICAL)
            self.logger.debug("Step 1: Extracting score string as primary source")
            score_str = self._parse_score(ctx.raw_data)

            if score_str and score_str != "0-0":
                # Step 2: 转换字符串为整数 (CRITICAL)
                self.logger.debug(f"Step 2: Converting score string '{score_str}' to integers")
                home_score, away_score = self._parse_score_to_ints(score_str)

                # Step 3: 赋值给basic_info (CRITICAL)
                basic_info['home_score'] = home_score
                basic_info['away_score'] = away_score

                self.logger.info(f"ULTIMATE: Extracted scores from string: home={home_score}, away={away_score}")
            else:
                # 备用方案：尝试直接路径提取
                self.logger.warning("Score string extraction failed, trying direct path extraction")

                home_score_raw = self._get_nested_value_robust(ctx.raw_data, ['header', 'teams', 0, 'score'])
                away_score_raw = self._get_nested_value_robust(ctx.raw_data, ['header', 'teams', 1, 'score'])

                if home_score_raw is not None and away_score_raw is not None:
                    basic_info['home_score'] = self._safe_int_convert(home_score_raw)
                    basic_info['away_score'] = self._safe_int_convert(away_score_raw)
                    self.logger.info(f"BACKUP: Extracted scores from direct path: home={basic_info['home_score']}, away={basic_info['away_score']}")
                else:
                    basic_info['home_score'] = 0
                    basic_info['away_score'] = 0
                    self.logger.warning("All score extraction methods failed, defaulting to 0-0")

            # Step 4: 最后提取其他字段 (CRITICAL)
            self.logger.debug("Step 4: Extracting other basic info fields")
            score_fields = {'home_score', 'away_score'}

            for field_name, path in self.field_paths.items():
                if field_name in score_fields:
                    continue  # 跳过比分字段，已处理

                value = self._get_nested_value_robust(ctx.raw_data, path)
                if value is not None:
                    basic_info[field_name] = value
                    self.logger.debug(f"Extracted {field_name}: {value}")

            # 最终比分验证
            self.logger.info(f"Final extracted scores: home={basic_info['home_score']}, away={basic_info['away_score']}")

            ctx.parsed_sections.append('basic_info')
            return basic_info

        except Exception as e:
            ctx.errors.append(f"Error parsing basic info: {str(e)}")
            self.logger.error(f"Critical error in basic info extraction: {e}")
            return {
                'home_score': 0,
                'away_score': 0
            }

    def _safe_int_convert(self, value: Any) -> int:
        """
        安全地将值转换为整数

        Args:
            value: 原始值（可能是字符串、数字等）

        Returns:
            int: 转换后的整数
        """
        try:
            if value is None:
                return 0
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            if isinstance(value, str):
                # 清理字符串并转换
                cleaned = re.sub(r'[^\d\.\-]', '', value.strip())
                if cleaned:
                    return int(float(cleaned))
            return 0
        except Exception as e:
            self.logger.debug(f"Failed to convert {value} to int: {e}")
            return 0

    def _get_nested_value_robust(self, data: Dict[str, Any], path: List[str]) -> Any:
        """
        从嵌套字典中获取值 - 最终健壮版本

        关键修复: 支持大小写不敏感的键名匹配和列表索引

        Args:
            data: 嵌套字典
            path: 访问路径

        Returns:
            Any: 找到的值，如果找不到返回None
        """
        current = data

        for key in path:
            # 处理列表索引 (数字索引)
            if isinstance(current, list) and isinstance(key, int):
                if 0 <= key < len(current):
                    current = current[key]
                    continue
                else:
                    self.logger.debug(f"Robust path matching: list index {key} out of range (len={len(current)})")
                    return None

            # 处理列表索引 (字符串形式的数字)
            elif isinstance(current, list) and isinstance(key, str) and key.isdigit():
                index = int(key)
                if 0 <= index < len(current):
                    current = current[index]
                    continue
                else:
                    self.logger.debug(f"Robust path matching: list index {index} out of range (len={len(current)})")
                    return None

            # 处理字典访问
            elif isinstance(current, dict):
                # 首先尝试精确匹配
                if key in current:
                    current = current[key]
                    continue

                # 精确匹配失败，尝试大小写不敏感匹配
                found_key = None
                for dict_key in current.keys():
                    if dict_key.lower() == key.lower():
                        found_key = dict_key
                        break

                if found_key is not None:
                    current = current[found_key]
                    self.logger.debug(f"Robust path matching: found '{found_key}' for '{key}'")
                else:
                    self.logger.debug(f"Robust path matching: key '{key}' not found in {list(current.keys())}")
                    return None
            else:
                self.logger.debug(f"Robust path matching: unexpected type {type(current)} for key '{key}'")
                return None

        return current

    def _parse_team_stats(self, ctx: ParsingContext) -> Optional[Dict[str, TeamStats]]:
        """解析球队统计数据"""
        try:
            stats_data = self._get_nested_value_robust(ctx.raw_data, ["content", "stats"])
            if not stats_data:
                return None

            home_stats = None
            away_stats = None

            if isinstance(stats_data, dict) and "stats" in stats_data:
                stats_list = stats_data["stats"]
                if isinstance(stats_list, list):
                    stats_dict = {}
                    for stat in stats_list:
                        if isinstance(stat, dict) and "type" in stat:
                            stats_dict[stat["type"]] = stat.get("stats", [])

                    # 解析各项统计数据
                    home_stats = self._parse_single_team_stats(stats_dict, team_index=0)
                    away_stats = self._parse_single_team_stats(stats_dict, team_index=1)

            ctx.parsed_sections.append('team_stats')
            return {"home": home_stats, "away": away_stats}

        except Exception as e:
            ctx.errors.append(f"Error parsing team stats: {str(e)}")
            return None

    def _parse_single_team_stats(self, stats_dict: Dict[str, Any], team_index: int) -> TeamStats:
        """
        解析单个球队的统计数据

        Args:
            stats_dict: 统计数据字典
            team_index: 球队索引 (0=主队, 1=客队)
        """
        return TeamStats(
            possession=self._extract_stat_value(stats_dict, "possession", team_index),
            shots=self._extract_stat_value(stats_dict, "shots", team_index),
            shots_on_target=self._extract_stat_value(stats_dict, "shotsOnTarget", team_index),
            corners=self._extract_stat_value(stats_dict, "corners", team_index),
            fouls=self._extract_stat_value(stats_dict, "fouls", team_index),
            yellow_cards=self._extract_stat_value(stats_dict, "yellowCards", team_index),
            red_cards=self._extract_stat_value(stats_dict, "redCards", team_index),
            expected_goals=self._extract_stat_value(stats_dict, "xg", team_index)
        )

    def _extract_stat_value(self, stats_dict: Dict[str, Any], stat_type: str, team_index: int) -> Optional[float]:
        """从统计数据字典中提取指定类型的值"""
        stat_data = stats_dict.get(stat_type)
        if stat_data and isinstance(stat_data, list) and len(stat_data) > team_index:
            value = stat_data[team_index]
            if value is not None:
                cleaned_value = self._clean_stat_value(value)
                return float(cleaned_value) if cleaned_value is not None else None
        return None

    def _clean_stat_value(self, value: Any) -> Optional[str]:
        """
        清洗统计数据值 - 最终修复版本

        使用正则表达式清洗带有百分比或后缀的字符串

        Args:
            value: 原始值

        Returns:
            Optional[str]: 清洗后的值
        """
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, str):
            # 使用正则表达式提取数字部分
            match = re.match(r'^([\d\.]+)', value.strip())
            if match:
                return match.group(1)

        return None

    def _parse_match_events(self, ctx: ParsingContext) -> List[L2MatchEvent]:
        """解析比赛事件"""
        try:
            events_data = self._get_nested_value_robust(ctx.raw_data, ["content", "events"])
            if not events_data:
                return []

            events = []
            if isinstance(events_data, list):
                for event in events_data:
                    if isinstance(event, dict):
                        # 使用schema中定义的EventType
                        event_type_str = self._map_event_type(event.get("type"))
                        try:
                            event_type = EventType(event_type_str)
                        except ValueError:
                            event_type = EventType.CARD  # 默认值

                        parsed_event = L2MatchEvent(
                            event_type=event_type_str,
                            minute=event.get("minute", 0),
                            player_name=event.get("player", {}).get("name") if event.get("player") else "",
                            team_id=str(event.get("team", {}).get("id", "")) if event.get("team") else "",
                            description=event.get("name", ""),
                            is_goal=event_type_str in ["Goal", "OwnGoal", "PenaltyGoal"],
                            is_own_goal=event_type_str == "OwnGoal",
                            card_type=event.get("cardType") if "card" in event_type_str.lower() else None,
                            substituted_player=event.get("substitutedPlayer", {}).get("name") if event_type_str == "Substitution" and event.get("substitutedPlayer") else None
                        )
                        events.append(parsed_event)

            ctx.parsed_sections.append('match_events')
            return events

        except Exception as e:
            ctx.errors.append(f"Error parsing match events: {str(e)}")
            return []

    def _parse_shot_data(self, ctx: ParsingContext) -> List[ShotData]:
        """解析射门数据"""
        try:
            shot_data = self._get_nested_value_robust(ctx.raw_data, ["content", "shotmap", "shots"])
            if not shot_data:
                return []

            shots = []
            if isinstance(shot_data, list):
                for shot in shot_data:
                    if isinstance(shot, dict):
                        parsed_shot = ShotData(
                            minute=shot.get("time", 0),
                            player_name=shot.get("playerName", ""),
                            team_id=str(shot.get("teamId", "")),
                            x=shot.get("position", {}).get("x", 0.0) if shot.get("position") else 0.0,
                            y=shot.get("position", {}).get("y", 0.0) if shot.get("position") else 0.0,
                            is_on_target=shot.get("isOnTarget", False),
                            expected_goals=shot.get("xg", 0.0),
                            shot_type=shot.get("shotType", ""),
                            is_goal=shot.get("shotType") == "Goal",
                            is_blocked=shot.get("isBlocked", False)
                        )
                        shots.append(parsed_shot)

            ctx.parsed_sections.append('shotmap')
            return shots

        except Exception as e:
            ctx.errors.append(f"Error parsing shot data: {str(e)}")
            return []

    def _parse_player_ratings(self, ctx: ParsingContext) -> List[L2PlayerRating]:
        """解析球员评分"""
        try:
            ratings_data = self._get_nested_value_robust(ctx.raw_data, ["content", "playerRatings"])
            if not ratings_data:
                return []

            ratings = []
            if isinstance(ratings_data, dict):
                # 处理主客队评分
                for team_key in ["home", "away"]:
                    team_ratings = ratings_data.get(team_key, {})
                    if isinstance(team_ratings, dict) and "ratings" in team_ratings:
                        for player_rating in team_ratings["ratings"]:
                            if isinstance(player_rating, dict):
                                rating = L2PlayerRating(
                                    player_id=str(player_rating.get("id", f"player_{len(ratings)}")),
                                    player_name=player_rating.get("playerName", ""),
                                    rating=float(player_rating.get("rating", 0.0)),
                                    position=player_rating.get("position"),
                                    minutes_played=player_rating.get("minutesPlayed")
                                )
                                ratings.append(rating)

            ctx.parsed_sections.append('player_ratings')
            return ratings

        except Exception as e:
            ctx.errors.append(f"Error parsing player ratings: {str(e)}")
            return []

    def _parse_metadata(self, ctx: ParsingContext) -> Optional[Dict[str, Any]]:
        """解析元数据（体育场、裁判、天气等）"""
        try:
            metadata = {}

            # 体育场信息
            stadium_name = self._get_nested_value_robust(ctx.raw_data, ["content", "ground", "name"])
            if stadium_name:
                metadata["stadium"] = StadiumInfo(name=stadium_name)

            # 裁判信息
            referee_data = self._get_nested_value_robust(ctx.raw_data, ["content", "referee"])
            if referee_data and isinstance(referee_data, dict):
                metadata["referee"] = RefereeInfo(
                    name=referee_data.get("name", ""),
                    nationality=referee_data.get("nationality", "")
                )

            # 天气信息
            weather_data = self._get_nested_value_robust(ctx.raw_data, ["content", "weather"])
            if weather_data and isinstance(weather_data, dict):
                metadata["weather"] = WeatherInfo(
                    condition=weather_data.get("condition", ""),
                    temperature=weather_data.get("temperature"),
                    humidity=weather_data.get("humidity"),
                    wind_speed=weather_data.get("windSpeed")
                )

            # 观众数量
            attendance = self._get_nested_value_robust(ctx.raw_data, ["content", "attendance"])
            if attendance:
                metadata["attendance"] = self._clean_numeric_value(attendance)

            if metadata:
                ctx.parsed_sections.append('metadata')
                return metadata

            return None

        except Exception as e:
            ctx.errors.append(f"Error parsing metadata: {str(e)}")
            return None

    def _parse_odds_data(self, ctx: ParsingContext) -> Optional[OddsData]:
        """解析赔率数据"""
        try:
            odds_paths = [
                ["content", "matchFacts", "odds"],
                ["content", "odds"],
                ["matchFacts", "odds"]
            ]

            odds_data = None
            for path in odds_paths:
                odds_data = self._get_nested_value_robust(ctx.raw_data, path)
                if odds_data:
                    break

            if odds_data and isinstance(odds_data, dict):
                result = OddsData(
                    home_win=odds_data.get("homeWin"),
                    draw=odds_data.get("draw"),
                    away_win=odds_data.get("awayWin"),
                    provider=odds_data.get("provider", ""),
                    snapshot_time=self._parse_datetime(odds_data.get("snapshotTime"))
                )
                ctx.parsed_sections.append('odds')
                return result

            return None

        except Exception as e:
            ctx.errors.append(f"Error parsing odds data: {str(e)}")
            return None

    def _extract_formations(self, ctx: ParsingContext) -> Tuple[Optional[str], Optional[str]]:
        """
        提取主客队阵型数据 - 修复版本

        基于实际数据结构：['content', 'lineup', 'homeTeam/awayTeam', 'formation']
        """
        try:
            # 基于实际数据结构的正确路径
            lineup_base = self._get_nested_value_robust(ctx.raw_data, ['content', 'lineup'])

            if not lineup_base or not isinstance(lineup_base, dict):
                return None, None

            home_formation = None
            away_formation = None

            # 从 homeTeam 和 awayTeam 中提取阵型
            if 'homeTeam' in lineup_base:
                home_team_data = lineup_base['homeTeam']
                if isinstance(home_team_data, dict) and 'formation' in home_team_data:
                    home_formation = self._validate_formation(home_team_data['formation'])

            if 'awayTeam' in lineup_base:
                away_team_data = lineup_base['awayTeam']
                if isinstance(away_team_data, dict) and 'formation' in away_team_data:
                    away_formation = self._validate_formation(away_team_data['formation'])

            # 备用路径检查（保持向后兼容）
            if not home_formation or not away_formation:
                # 检查其他可能的路径
                backup_paths = [
                    ['general', 'lineups'],
                    ['header', 'lineups'],
                    ['lineups']
                ]

                for path in backup_paths:
                    lineups_data = self._get_nested_value_robust(ctx.raw_data, path)
                    if lineups_data:
                        backup_home, backup_away = self._extract_formations_from_generic(lineups_data)
                        if not home_formation:
                            home_formation = backup_home
                        if not away_formation:
                            away_formation = backup_away
                        break

            if home_formation or away_formation:
                ctx.parsed_sections.append('formations')
                self.logger.debug(f"Extracted formations: home={home_formation}, away={away_formation}")

            return home_formation, away_formation

        except Exception as e:
            self.logger.warning(f"Error extracting formations: {e}")
            return None, None

    def _extract_lineups(self, ctx: ParsingContext) -> Tuple[Optional[TeamLineup], Optional[TeamLineup]]:
        """
        提取完整的阵容信息 - 新增方法

        从 ['content', 'lineup', 'homeTeam/awayTeam'] 中提取
        """
        try:
            lineup_base = self._get_nested_value_robust(ctx.raw_data, ['content', 'lineup'])

            if not lineup_base or not isinstance(lineup_base, dict):
                return None, None

            home_lineup = None
            away_lineup = None

            # 处理主队阵容
            if 'homeTeam' in lineup_base:
                home_team_data = lineup_base['homeTeam']
                if isinstance(home_team_data, dict):
                    home_lineup = self._parse_single_lineup(home_team_data, is_home=True)

            # 处理客队阵容
            if 'awayTeam' in lineup_base:
                away_team_data = lineup_base['awayTeam']
                if isinstance(away_team_data, dict):
                    away_lineup = self._parse_single_lineup(away_team_data, is_home=False)

            if home_lineup or away_lineup:
                ctx.parsed_sections.append('lineups')
                self.logger.debug(f"Extracted lineups: home={len(home_lineup.starters) if home_lineup else 0} starters, away={len(away_lineup.starters) if away_lineup else 0} starters")

            return home_lineup, away_lineup

        except Exception as e:
            self.logger.warning(f"Error extracting lineups: {e}")
            return None, None

    def _parse_single_lineup(self, team_data: Dict[str, Any], is_home: bool) -> Optional[TeamLineup]:
        """
        解析单个球队的阵容信息

        Args:
            team_data: 球队数据字典
            is_home: 是否为主队

        Returns:
            TeamLineup: 解析后的阵容对象
        """
        try:
            formation = self._validate_formation(team_data.get('formation'))
            starters = []
            substitutes = []

            # 解析首发阵容
            starters_data = team_data.get('starters', [])
            if isinstance(starters_data, list):
                for player in starters_data:
                    if isinstance(player, dict):
                        starter_info = {
                            'id': player.get('id'),
                            'name': player.get('name'),
                            'position': player.get('position'),
                            'shirt_number': player.get('shirtNumber'),
                            'rating': player.get('rating')
                        }
                        starters.append(starter_info)

            # 解析替补阵容
            subs_data = team_data.get('subs', [])
            if isinstance(subs_data, list):
                for player in subs_data:
                    if isinstance(player, dict):
                        sub_info = {
                            'id': player.get('id'),
                            'name': player.get('name'),
                            'position': player.get('position'),
                            'shirt_number': player.get('shirtNumber')
                        }
                        substitutes.append(sub_info)

            # 创建阵容对象
            lineup = TeamLineup(
                formation=formation,
                starters=starters,
                substitutes=substitutes,
                manager=team_data.get('coach', {}).get('name') if team_data.get('coach') else None
            )

            return lineup

        except Exception as e:
            self.logger.warning(f"Error parsing single lineup: {e}")
            return None

    def _validate_formation(self, formation: Any) -> Optional[str]:
        """
        验证和标准化阵型字符串

        Args:
            formation: 原始阵型数据

        Returns:
            Optional[str]: 验证后的阵型字符串
        """
        if not formation:
            return None

        if isinstance(formation, str):
            # 清理阵型字符串
            formation = formation.strip()

            # 验证阵型格式
            if re.match(r'^\d-\d-\d$', formation):  # 4-4-2, 4-3-3 等
                return formation
            elif re.match(r'^\d-\d-\d-\d$', formation):  # 4-2-3-1, 4-1-4-1 等
                return formation
            elif re.match(r'^\d-\d$', formation):  # 3-5, 4-4 等
                return formation
            # 常见阵型白名单
            elif formation in ['4-3-3', '4-4-2', '4-2-3-1', '3-5-2', '5-3-2', '4-1-4-1', '3-4-3', '3-4-2-1']:
                return formation

        return None

    def _extract_formations_from_generic(self, lineups_data: Any) -> Tuple[Optional[str], Optional[str]]:
        """
        从通用格式中提取阵型（备用方法）

        Args:
            lineups_data: 通用阵容数据

        Returns:
            Tuple[Optional[str], Optional[str]]: (主队阵型, 客队阵型)
        """
        if not isinstance(lineups_data, dict):
            return None, None

        home_formation = None
        away_formation = None

        # 结构1: {"home": {"formation": "4-3-3"}, "away": {"formation": "4-4-2"}}
        if 'home' in lineups_data and 'away' in lineups_data:
            home_formation = self._validate_formation(lineups_data['home'].get('formation'))
            away_formation = self._validate_formation(lineups_data['away'].get('formation'))

        # 结构2: [{"team": "home", "formation": "4-3-3"}, {"team": "away", "formation": "4-4-2"}]
        elif isinstance(lineups_data, list) and len(lineups_data) >= 2:
            for lineup in lineups_data[:2]:
                if isinstance(lineup, dict):
                    team_side = lineup.get('team', lineup.get('side', '')).lower()
                    formation = self._validate_formation(lineup.get('formation'))

                    if 'home' in team_side and formation:
                        home_formation = formation
                    elif 'away' in team_side and formation:
                        away_formation = formation

        return home_formation, away_formation

    def _parse_xg_data(self, ctx: ParsingContext) -> Optional[Dict[str, float]]:
        """解析期望进球(xG)数据"""
        try:
            xg_paths = [
                ["content", "stats", "stats"],
                ["content", "xg"],
                ["stats", "xg"]
            ]

            for path in xg_paths:
                stats_data = self._get_nested_value_robust(ctx.raw_data, path)
                if stats_data and isinstance(stats_data, list):
                    for stat in stats_data:
                        if isinstance(stat, dict) and stat.get("type") == "xg":
                            xg_values = stat.get("stats", [])
                            if len(xg_values) >= 2:
                                return {
                                    "home": float(xg_values[0]) if xg_values[0] else 0.0,
                                    "away": float(xg_values[1]) if xg_values[1] else 0.0
                                }

            # 从统计数据中提取xG
            if ctx.raw_data.get("content", {}).get("stats"):
                home_xg = ctx.raw_data["content"]["stats"].get("home", {}).get("xg")
                away_xg = ctx.raw_data["content"]["stats"].get("away", {}).get("xg")

                if home_xg is not None or away_xg is not None:
                    return {
                        "home": float(home_xg) if home_xg else 0.0,
                        "away": float(away_xg) if away_xg else 0.0
                    }

            return None

        except Exception as e:
            ctx.errors.append(f"Error parsing xG data: {str(e)}")
            return None

    # Helper methods
    def _get_nested_value(self, data: Dict[str, Any], path: List[str]) -> Any:
        """
        从嵌套字典中获取值 - 向后兼容方法

        Args:
            data: 嵌套字典
            path: 访问路径

        Returns:
            Any: 找到的值，如果找不到返回None
        """
        current = data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def _map_event_type(self, event_type: str) -> str:
        """映射事件类型"""
        type_mapping = {
            "goal": EventType.GOAL,
            "card": EventType.CARD,
            "substitution": EventType.SUBSTITUTION,
            "var": EventType.VAR,
            "penalty_shootout": EventType.PENALTY_SHOOTOUT
        }
        return type_mapping.get(event_type.lower(), event_type)

    def _parse_score(self, data: Dict[str, Any]) -> str:
        """
        解析比分 - 终极鲁棒版本

        优先使用备用路径获取比分字符串，如 "1-1"
        """
        try:
            # 方法1: 从 status.score 获取比分字符串
            score_from_status = self._get_nested_value_robust(data, ["header", "status", "score"])
            if score_from_status and isinstance(score_from_status, str) and '-' in score_from_status:
                # 处理带空格的比分字符串，例如 "2 - 2" -> "2-2"
                cleaned_score = score_from_status.replace(' ', '')
                # 验证比分格式是否有效 (如 "1-1", "2-0", "0-3")
                parts = cleaned_score.split('-')
                if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                    self.logger.debug(f"Found score string from status: {cleaned_score} (original: {score_from_status})")
                    return cleaned_score

            # 方法2: 从 teams 数组提取比分
            home_score = self._get_nested_value_robust(data, ["header", "teams", 0, "score"])
            away_score = self._get_nested_value_robust(data, ["header", "teams", 1, "score"])

            if home_score is not None and away_score is not None:
                score_str = f"{home_score}-{away_score}"
                self.logger.debug(f"Found score from teams array: {score_str}")
                return score_str

            # 方法3: 尝试其他可能的比分路径
            backup_paths = [
                ["header", "status", "scoreStr"],  # 实际数据的比分路径 (例如 "2 - 2")
                ["header", "scoreStr"],           # 备用路径
                ["general", "score"],             # 备用路径
                ["score"]                         # 备用路径
            ]

            for path in backup_paths:
                score_candidate = self._get_nested_value_robust(data, path)
                if score_candidate and isinstance(score_candidate, str) and '-' in score_candidate:
                    # 处理带空格的比分字符串，例如 "2 - 2" -> "2-2"
                    cleaned_score = score_candidate.replace(' ', '')
                    parts = cleaned_score.split('-')
                    if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                        self.logger.debug(f"Found score from backup path {path}: {cleaned_score} (original: {score_candidate})")
                        return cleaned_score

            # 所有方法都失败，返回默认值
            self.logger.warning("No valid score string found, returning default 0-0")
            return "0-0"

        except Exception as e:
            self.logger.debug(f"Error parsing score: {e}")
            return "0-0"

    def _parse_score_to_ints(self, score_str: str) -> Tuple[int, int]:
        """将比分字符串转换为整数元组"""
        try:
            if isinstance(score_str, str) and '-' in score_str:
                parts = score_str.split('-')
                if len(parts) == 2:
                    home = int(parts[0].strip())
                    away = int(parts[1].strip())
                    return home, away
            return 0, 0
        except:
            return 0, 0

    def _clean_numeric_value(self, value: Any) -> Optional[Union[int, float]]:
        """清理数值数据，移除非数字字符"""
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return value

        if isinstance(value, str):
            # 移除逗号、空格和其他非数字字符（保留小数点和负号）
            cleaned = re.sub(r'[^\d\.\-]', '', value.strip())

            if cleaned:
                try:
                    # 尝试转换为浮点数，如果是整数则返回整数
                    if '.' in cleaned:
                        return float(cleaned)
                    else:
                        return int(cleaned)
                except ValueError:
                    pass

        return None

    def _parse_datetime(self, dt_str: Any) -> Optional[datetime]:
        """解析日期时间字符串"""
        if not dt_str:
            return None

        try:
            # 如果是时间戳
            if isinstance(dt_str, (int, float)):
                return datetime.fromtimestamp(dt_str)

            if isinstance(dt_str, str):
                # 常见的日期时间格式
                formats = [
                    '%Y-%m-%dT%H:%M:%SZ',      # ISO 8601
                    '%Y-%m-%dT%H:%M:%S.%fZ',    # ISO 8601 with microseconds
                    '%Y-%m-%d %H:%M:%S',        # Standard format
                    '%Y-%m-%d',                 # Date only
                ]

                for fmt in formats:
                    try:
                        return datetime.strptime(dt_str, fmt)
                    except ValueError:
                        continue

        except Exception as e:
            self.logger.debug(f"Could not parse datetime '{dt_str}': {e}")

        return None