#!/usr/bin/env python3
"""
L2数据解析器 - 生产版本
L2 Data Parser - Production Release

用于解析从FotMob API获取的原始数据，提取结构化的L2信息：
- 比赛基本信息
- 球队统计数据
- 比赛事件数据
- 射门分布数据
- 球员评分数据
- 阵容信息

作者: L2开发团队
创建时间: 2025-12-10
版本: 1.0.0 (Production Release)
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
    L2TeamStats,
    L2MatchEvent,
    L2ShotData,
    L2PlayerRating,
    L2DataProcessingResult
)


class EventType(str, Enum):
    """比赛事件类型"""
    GOAL = "Goal"
    CARD = "Card"
    SUBSTITUTION = "Substitution"
    VAR = "Var"
    PENALTY_SHOOTOUT = "PenaltyShootout"
    PERIOD_START = "PeriodStart"
    PERIOD_END = "PeriodEnd"


class CardType(str, Enum):
    """卡片类型"""
    YELLOW = "Yellow"
    RED = "Red"
    SECOND_YELLOW = "SecondYellow"


@dataclass
class ParsingContext:
    """解析上下文信息"""
    match_id: str
    raw_data: Dict[str, Any]
    strict_mode: bool = True

    # 解析状态
    parsed_sections: List[str] = None

    def __post_init__(self):
        if self.parsed_sections is None:
            self.parsed_sections = []


class L2Parser:
    """
    L2数据解析器 - 生产版本

    提供强大的数据解析功能，支持多种数据格式、错误恢复、
    数据验证和结构化输出等功能。
    """

    def __init__(self, strict_mode: bool = True):
        """
        初始化L2数据解析器

        Args:
            strict_mode: 严格模式，True时遇到错误会抛出异常，
                        False时会尽可能解析数据并记录警告
        """
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(__name__)

        # 数据提取路径映射 - 修正为小写以匹配FotMob API结构
        self._data_paths = {
            'match_id': ['general', 'matchId'],
            'home_team': ['general', 'homeTeam', 'name'],
            'away_team': ['general', 'awayTeam', 'name'],
            'home_score': ['header', 'teams', 0, 'score'],
            'away_score': ['header', 'teams', 1, 'score'],
            'status': ['header', 'status', 'finished'],  # 🔧 修正路径
            'match_time': ['general', 'status', 'started'],
            'stadium': ['content', 'matchFacts', 'infoBox', 'Stadium'],  # 🔧 修正路径
            'attendance': ['header', 'attendance'],
            'referee': ['header', 'referee', 'name'],
            'weather': ['header', 'weather', 'condition']
        }

        # 统计数据字段映射 - 支持大小写变体
        self._stats_fields_mapping = {
            'possession': ['possession', 'Possession'],
            'shots': ['shots', 'Shots'],
            'shots_on_target': ['shotsOnTarget', 'ShotsOnTarget'],
            'corners': ['corners', 'Corners'],
            'fouls': ['fouls', 'Fouls'],
            'offsides': ['offsides', 'Offsides'],
            'yellow_cards': ['yellowCards', 'YellowCards'],
            'red_cards': ['redCards', 'RedCards'],
            'saves': ['saves', 'Saves'],
            'expected_goals': ['expectedGoals', 'ExpectedGoals', 'xG'],
            'big_chances_created': ['bigChancesCreated', 'BigChancesCreated'],
            'big_chances_missed': ['bigChancesMissed', 'BigChancesMissed'],
            'passes': ['passes', 'Passes'],
            'tackles': ['tackles', 'Tackles'],
            'interceptions': ['interceptions', 'Interceptions'],
            'clearances': ['clearances', 'Clearances'],
            'aerials_won': ['aerialsWon', 'AerialsWon'],
            'blocked_shots': ['blockedShots', 'BlockedShots'],
            'counter_attacks': ['counterAttacks', 'CounterAttacks'],
            'through_balls': ['throughBalls', 'ThroughBalls'],
            'long_balls': ['longBalls', 'LongBalls'],
            'crosses': ['crosses', 'Crosses'],
            'touches': ['touches', 'Touches']
        }

    def _get_nested_value(
        self,
        data: Dict[str, Any],
        path: List[Union[str, int]],
        default: Any = None
    ) -> Any:
        """
        从嵌套字典中获取值，支持大小写不敏感和整数索引

        Args:
            data: 源数据字典
            path: 值的路径，支持字符串键和整数索引
            default: 默认值

        Returns:
            Any: 找到的值或默认值
        """
        if not data or not path:
            return default

        current = data

        try:
            for key in path:
                if isinstance(current, dict):
                    if isinstance(key, int):
                        # 整数键，直接匹配或转换为字符串匹配
                        if key in current:
                            current = current[key]
                        else:
                            # 尝试字符串形式的数字键
                            key_str = str(key)
                            if key_str in current:
                                current = current[key_str]
                            else:
                                # 大小写不敏感匹配
                                found = False
                                for dict_key in current.keys():
                                    if str(dict_key).lower() == key_str.lower():
                                        current = current[dict_key]
                                        found = True
                                        break
                                if not found:
                                    return default
                    else:
                        # 字符串键，直接匹配
                        if key in current:
                            current = current[key]
                            continue

                        # 大小写不敏感匹配
                        found = False
                        for dict_key in current.keys():
                            if dict_key.lower() == key.lower():
                                current = current[dict_key]
                                found = True
                                break
                        if not found:
                            return default

                elif isinstance(current, list):
                    # 处理列表索引
                    if isinstance(key, int):
                        if 0 <= key < len(current):
                            current = current[key]
                        else:
                            return default
                    elif isinstance(key, str) and key.isdigit():
                        index = int(key)
                        if 0 <= index < len(current):
                            current = current[index]
                        else:
                            return default
                    else:
                        return default
                else:
                    return default

            return current

        except (KeyError, TypeError, IndexError, ValueError):
            return default

    def _get_value_from_alternatives(
        self,
        data: Dict[str, Any],
        keys: List[str],
        default: Any = None
    ) -> Any:
        """
        从备选键名列表中获取第一个存在的值

        Args:
            data: 源数据字典
            keys: 备选键名列表，按优先级顺序
            default: 默认值

        Returns:
            Any: 找到的值或默认值
        """
        if not data or not keys:
            return default

        for key in keys:
            if key in data:
                return data[key]
            # 尝试大小写不敏感匹配
            for data_key in data.keys():
                if data_key.lower() == key.lower():
                    return data[data_key]

        return default

    def _smart_unwrap(
        self,
        data: Any,
        expected_type: str = 'list',
        target_key: Optional[str] = None
    ) -> Any:
        """
        智能拆包数据 - 处理FotMob API的"包装"数据结构

        Args:
            data: 原始数据
            expected_type: 期望的数据类型 ('list', 'dict')
            target_key: 目标键名（如 'events', 'shots', 'stats'）

        Returns:
            拆包后的数据
        """
        if data is None:
            return None

        # 如果已经是期望的类型，直接返回
        if (expected_type == 'list' and isinstance(data, list)) or \
           (expected_type == 'dict' and isinstance(data, dict)):
            return data

        # 如果是字典，尝试拆包
        if isinstance(data, dict):
            # 1. 尝试直接使用 target_key
            if target_key and target_key in data:
                unwrapped = data[target_key]
                if (expected_type == 'list' and isinstance(unwrapped, list)) or \
                   (expected_type == 'dict' and isinstance(unwrapped, dict)):
                    return unwrapped

            # 2. 尝试常见的数据键名
            common_keys = {
                'list': ['events', 'shots', 'players', 'ratings', 'lineups', 'starters', 'substitutes'],
                'dict': ['stats', 'teamStats', 'playerStats', 'matchStats']
            }

            if target_key:
                common_keys[expected_type].insert(0, target_key)

            for key in common_keys.get(expected_type, []):
                if key in data:
                    value = data[key]
                    if isinstance(value, list) if expected_type == 'list' else isinstance(value, dict):
                        return value

            # 3. 尝试找到第一个列表/字典值
            for value in data.values():
                if isinstance(value, list) if expected_type == 'list' else isinstance(value, dict):
                    return value

        return data  # 返回原始数据，让调用方处理

    def _extract_match_basic_info(self, ctx: ParsingContext) -> Dict[str, Any]:
        """
        提取比赛基本信息

        Args:
            ctx: 解析上下文

        Returns:
            Dict[str, Any]: 比赛基本信息
        """
        self.logger.debug("Extracting match basic info for match %s", ctx.match_id)

        basic_info = {}

        for field, path in self._data_paths.items():
            value = self._get_nested_value(ctx.raw_data, path)

            # 🔧 特殊处理 status 字段 - 将布尔值转换为字符串枚举
            if field == 'status':
                status = self._extract_match_status(ctx.raw_data)
                if status:
                    basic_info[field] = status
                elif self.strict_mode:
                    raise ValueError(f"Required field '{field}' could not be determined")
                else:
                    self.logger.warning("Could not determine match status, using default")
                    basic_info[field] = self._get_default_value(field)
                continue

            if value is not None:
                basic_info[field] = value
            elif self.strict_mode:
                raise ValueError(f"Required field '{field}' not found at path {path}")
            else:
                self.logger.warning(
                    "Field '%s' not found at path %s, using default value",
                    field, path
                )
                basic_info[field] = self._get_default_value(field)

        ctx.parsed_sections.append('basic_info')
        self.logger.debug("Extracted basic info: %s", basic_info)

        return basic_info

    def _extract_match_status(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """
        提取比赛状态 - 特殊处理布尔值转换为字符串枚举

        Args:
            raw_data: 原始数据字典

        Returns:
            Optional[str]: 比赛状态字符串
        """
        # 尝试多个可能的状态路径
        status_paths = [
            ['header', 'status'],
            ['general', 'status'],
            ['status'],
            ['content', 'matchFacts', 'status']
        ]

        status_obj = None
        found_path = None

        for path in status_paths:
            status_obj = self._get_nested_value(raw_data, path)
            if status_obj:
                found_path = path
                self.logger.debug(f"Found status object at path: {path}")
                break

        if not status_obj:
            self.logger.warning("No status object found in any known path")
            return None

        self.logger.debug(f"Status object type: {type(status_obj)}, content: {status_obj}")

        # 🔧 处理布尔值状态对象
        if isinstance(status_obj, dict):
            if status_obj.get('finished'):
                status = 'finished'
                self.logger.debug("Match finished (finished=True)")
            elif status_obj.get('started') and not status_obj.get('finished'):
                status = 'live'
                self.logger.debug("Match live (started=True, finished=False)")
            elif status_obj.get('cancelled'):
                status = 'cancelled'
                self.logger.debug("Match cancelled")
            elif status_obj.get('postponed'):
                status = 'postponed'
                self.logger.debug("Match postponed")
            else:
                status = 'scheduled'
                self.logger.debug("Match scheduled (no status flags set)")
        elif isinstance(status_obj, bool):
            # 直接布尔值的情况
            if status_obj:
                status = 'finished'
                self.logger.debug("Match finished (direct boolean=True)")
            else:
                status = 'scheduled'
                self.logger.debug("Match scheduled (direct boolean=False)")
        elif isinstance(status_obj, str):
            # 已经是字符串，直接使用
            status = status_obj.lower()
            self.logger.debug(f"Match status string: {status}")

            # 标准化状态值
            status_mapping = {
                'ft': 'finished',
                'finished': 'finished',
                'live': 'live',
                'ongoing': 'live',
                'scheduled': 'scheduled',
                'upcoming': 'scheduled',
                'postponed': 'postponed',
                'cancelled': 'cancelled',
                'abandoned': 'abandoned'
            }
            status = status_mapping.get(status, 'scheduled')
        else:
            self.logger.warning(f"Unexpected status object type: {type(status_obj)}")
            return None

        self.logger.debug(f"Final determined status: {status}")
        return status

    def _extract_team_stats(self, ctx: ParsingContext) -> Tuple[L2TeamStats, L2TeamStats]:
        """
        提取球队统计数据

        Args:
            ctx: 解析上下文

        Returns:
            Tuple[L2TeamStats, L2TeamStats]: (主队统计, 客队统计)
        """
        self.logger.debug("Extracting team stats for match %s", ctx.match_id)

        # 尝试多个可能的统计数据位置 - 修正为小写，添加 FotMob V3 和旧版路径
        stats_paths = [
            ['stats', 'teamStats'],
            ['teamStats'],
            ['content', 'stats', 'teamStats'],
            ['content', 'matchFacts', 'stats'],
            ['content', 'matchFacts', 'teamMatchStats'],  # 🔧 添加 FotMob V3 常见路径
            ['content', 'stats', 'Periods', 'All', 'stats'],  # 🔧 添加旧版 FotMob 路径
            ['header', 'stats'],
            ['stats'],
            ['matchFacts', 'stats'],
            ['matchFacts', 'teamMatchStats'],  # 🔧 添加 FotMob V3 常见路径
            ['stats', 'Periods', 'All', 'stats']  # 🔧 添加旧版 FotMob 路径
        ]

        team_stats_data = None

        for path in stats_paths:
            team_stats_data = self._get_nested_value(ctx.raw_data, path)
            if team_stats_data:
                self.logger.debug(f"Found team stats at path: {path}")
                break

        if not team_stats_data:
            if self.strict_mode:
                raise ValueError("Team stats data not found")
            else:
                self.logger.warning("Team stats data not found, using default stats")
                return self._create_default_team_stats(ctx.match_id)

        # 🔧 智能拆包：处理包装的数据结构
        team_stats_data = self._smart_unwrap(team_stats_data, expected_type='list', target_key='stats')

        # 🎯 处理 FotMob 新版数据结构：包含多个统计类别的列表
        if isinstance(team_stats_data, list) and team_stats_data and isinstance(team_stats_data[0], dict):
            if 'stats' in team_stats_data[0] and 'title' in team_stats_data[0]:
                # 新版数据格式：{"title": "Shots", "stats": [stat1, stat2, ...]}
                home_stats_data = self._extract_new_format_team_stats(team_stats_data, 'home')
                away_stats_data = self._extract_new_format_team_stats(team_stats_data, 'away')
            else:
                # 旧版数据格式：直接的主客队统计数组
                home_stats_data = team_stats_data[0]
                away_stats_data = team_stats_data[1]
        elif isinstance(team_stats_data, dict):
            if 'home' in team_stats_data and 'away' in team_stats_data:
                home_stats_data = team_stats_data['home']
                away_stats_data = team_stats_data['away']
            elif 'Home' in team_stats_data and 'Away' in team_stats_data:
                home_stats_data = team_stats_data['Home']
                away_stats_data = team_stats_data['Away']
            else:
                if self.strict_mode:
                    raise ValueError("Cannot determine home/away team stats structure")
                else:
                    self.logger.warning("Cannot determine team stats structure, using defaults")
                    return self._create_default_team_stats(ctx.match_id)
        else:
            if self.strict_mode:
                raise ValueError(f"Unexpected team stats format: {type(team_stats_data)}")
            else:
                self.logger.warning("Unexpected team stats format, using defaults")
                return self._create_default_team_stats(ctx.match_id)

        # 解析统计数据
        try:
            home_stats = self._parse_single_team_stats(home_stats_data, "home")
            away_stats = self._parse_single_team_stats(away_stats_data, "away")

            ctx.parsed_sections.append('team_stats')
            self.logger.debug(
                "Extracted team stats - Home: %s, Away: %s",
                home_stats.dict(), away_stats.dict()
            )

            return home_stats, away_stats

        except Exception as e:
            if self.strict_mode:
                raise ValueError(f"Error parsing team stats: {str(e)}")
            else:
                self.logger.error("Error parsing team stats: %s", e)
                return self._create_default_team_stats(ctx.match_id)

    def _parse_single_team_stats(self, stats_data: Dict[str, Any], team_type: str) -> L2TeamStats:
        """
        解析单个球队的统计数据

        Args:
            stats_data: 球队统计数据
            team_type: 球队类型 ("home" 或 "away")

        Returns:
            L2TeamStats: 解析后的统计数据
        """
        parsed_stats = {}

        # 🎯 处理新格式的统计数据：已经是从 _extract_new_format_team_stats 提取的平面字典
        if not stats_data:
            self.logger.warning(f"No stats data provided for {team_type} team")
            stats_data = {}

        # 直接从平面字典中提取统计数据
        for stat_field, _ in self._stats_fields_mapping.items():
            value = stats_data.get(stat_field)

            # 🧹 清洗统计数据中的非数字字符
            if value is not None:
                value = self._clean_stat_value(value)

            # 类型转换
            if value is not None:
                try:
                    if stat_field in ['possession']:
                        parsed_stats[stat_field] = float(value)
                    elif stat_field in [
                        'shots', 'shots_on_target', 'corners', 'fouls', 'offsides',
                        'yellow_cards', 'red_cards', 'saves', 'passes', 'tackles',
                        'interceptions', 'clearances', 'aerials_won', 'blocked_shots',
                        'counter_attacks', 'through_balls', 'long_balls', 'crosses',
                        'touches', 'big_chances_created', 'big_chances_missed'
                    ]:
                        parsed_stats[stat_field] = int(value)
                    elif stat_field in ['expected_goals']:
                        parsed_stats[stat_field] = float(value)
                    else:
                        parsed_stats[stat_field] = value

                except (ValueError, TypeError):
                    self.logger.warning(
                        "Invalid value for %s %s: %s",
                        team_type, stat_field, value
                    )
                    parsed_stats[stat_field] = self._get_default_stat_value(stat_field)
            else:
                parsed_stats[stat_field] = self._get_default_stat_value(stat_field)

        return L2TeamStats(**parsed_stats)

    def _clean_stat_value(self, value: Any) -> Any:
        """
        清洗统计数据中的非数字字符

        Args:
            value: 原始数值（可能包含非数字字符）

        Returns:
            Any: 清洗后的数值
        """
        if not isinstance(value, str):
            return value

        import re

        # 移除常见的非数字后缀，例如：
        # "17 (33%)" -> "17"
        # "66%" -> "66"
        # "1.91xG" -> "1.91"
        # "123.5K" -> "123.5"

        # 提取字符串开头的数字部分（支持小数点）
        match = re.match(r'^([\d\.]+)', value.strip())
        if match:
            cleaned_value = match.group(1)
            self.logger.debug(f"Cleaned stat value: '{value}' -> '{cleaned_value}'")
            return cleaned_value

        # 如果没有找到数字模式，返回原值
        self.logger.debug(f"No numeric pattern found in value: '{value}'")
        return value

    def _extract_new_format_team_stats(self, stats_categories: List[Dict], team_type: str) -> Dict:
        """
        从新版 FotMob 数据格式中提取指定球队的统计数据

        新版数据格式：
        [
          {"title": "Top stats", "stats": [stat1, stat2, ...]},
          {"title": "Shots", "stats": [stat1, stat2, ...]},
          ...
        ]

        Args:
            stats_categories: 统计类别列表
            team_type: 'home' 或 'away'

        Returns:
            Dict: 提取的统计数据
        """
        team_stats = {}
        team_index = 0 if team_type == 'home' else 1

        for category in stats_categories:
            if not isinstance(category, dict) or 'stats' not in category:
                continue

            category_stats = category['stats']
            if not isinstance(category_stats, list):
                continue

            for stat_item in category_stats:
                if not isinstance(stat_item, dict) or 'stats' not in stat_item:
                    continue

                stat_values = stat_item['stats']
                if not isinstance(stat_values, list) or len(stat_values) <= team_index:
                    continue

                # 获取统计键名
                stat_key = self._normalize_stat_key(stat_item.get('key', ''))
                if not stat_key:
                    # 如果没有 key，尝试从 title 生成
                    stat_key = self._normalize_stat_key(stat_item.get('title', ''))

                if stat_key:
                    team_stats[stat_key] = stat_values[team_index]

        self.logger.debug(f"Extracted {len(team_stats)} stats for {team_type} team: {list(team_stats.keys())}")
        return team_stats

    def _normalize_stat_key(self, key: str) -> str:
        """
        标准化统计键名

        Args:
            key: 原始键名

        Returns:
            str: 标准化后的键名
        """
        if not key:
            return ""

        # 移除特殊字符并转换为小写
        normalized = key.lower().replace(' ', '_').replace('-', '_')

        # 常见的键名映射
        key_mapping = {
            'ballpossesion': 'possession',  # FotMob 拼写错误
            'expected_goals': 'expected_goals',
            'expected_goals_(xg)': 'expected_goals',
            'total_shots': 'shots',
            'shots_on_target': 'shots_on_target',
            'yellow_cards': 'yellow_cards',
            'red_cards': 'red_cards',
            'fouls': 'fouls',
            'offsides': 'offsides',
            'corners': 'corners',
            'passes': 'passes',
            'tackles': 'tackles',
            'interceptions': 'interceptions',
            'clearances': 'clearances',
            'blocked_shots': 'blocked_shots',
            'aerials_won': 'aerials_won',
            'saves': 'saves',
            'crosses': 'crosses',
            'long_balls': 'long_balls',
            'through_balls': 'through_balls',
            'counter_attacks': 'counter_attacks',
            'duel_won': 'duels_won',
            'big_chances_created': 'big_chances_created',
            'big_chances_missed': 'big_chances_missed',
            'touches': 'touches',
            'matchstats.headers.tackles': 'tackles'
        }

        return key_mapping.get(normalized, normalized)

    def _extract_match_events(self, ctx: ParsingContext) -> List[L2MatchEvent]:
        """
        提取比赛事件数据 - 优化版本，支持事件类型白名单过滤

        Args:
            ctx: 解析上下文

        Returns:
            List[L2MatchEvent]: 比赛事件列表
        """
        self.logger.debug("Extracting match events for match %s", ctx.match_id)

        # 🎯 核心事件类型白名单 - 仅处理我们需要的业务事件
        CORE_EVENT_TYPES = ['goal', 'card', 'substitution']  # 大小写不敏感

        # 尝试多个可能的事件数据位置 - 修正为小写
        events_paths = [
            ['content', 'stats', 'events'],
            ['stats', 'events'],
            ['events'],
            ['matchFacts', 'events'],
            ['content', 'matchFacts', 'events'],
            ['header', 'events']
        ]

        events_data = None

        for path in events_paths:
            events_data = self._get_nested_value(ctx.raw_data, path)
            if events_data:
                self.logger.debug(f"Found events at path: {path}")
                break

        if not events_data:
            if self.strict_mode:
                raise ValueError("Match events data not found")
            else:
                self.logger.warning("Match events data not found, returning empty list")
                return []

        # 🔧 智能拆包：处理包装的事件数据
        events_data = self._smart_unwrap(events_data, expected_type='list', target_key='events')

        if not isinstance(events_data, list):
            if self.strict_mode:
                raise ValueError(f"Events data is not a list: {type(events_data)}")
            else:
                self.logger.warning("Events data is not a list, returning empty list")
                return []

        events = []
        skipped_count = 0
        processed_count = 0

        for i, event_data in enumerate(events_data):
            try:
                # 🔍 预检查事件类型 - 白名单过滤
                if not isinstance(event_data, dict):
                    self.logger.debug("Event data %d is not a dictionary, skipping", i)
                    skipped_count += 1
                    continue

                # 🔧 修复：使用备选键名提取而不是嵌套路径
                event_type_str = self._get_value_from_alternatives(event_data, ['type', 'Type'], '')
                if not event_type_str:
                    self.logger.debug("Event %d has no type field, skipping", i)
                    skipped_count += 1
                    continue

                event_type_lower = event_type_str.lower()
                if event_type_lower not in CORE_EVENT_TYPES:
                    self.logger.debug(
                        "Skipping non-core event %d: type='%s' (not in whitelist: %s)",
                        i, event_type_str, CORE_EVENT_TYPES
                    )
                    skipped_count += 1
                    continue

                # ✅ 在白名单内，进行完整解析
                event = self._parse_single_event(event_data, i)
                if event:
                    events.append(event)
                    processed_count += 1
                    self.logger.debug(
                        "Processed core event %d: type=%s, player=%s",
                        i, event.event_type, event.player_name
                    )
                else:
                    self.logger.debug("Failed to parse event %d despite being in whitelist", i)
                    skipped_count += 1

            except Exception as e:
                error_msg = f"Error parsing event {i}: {str(e)}"
                if self.strict_mode:
                    raise ValueError(error_msg)
                else:
                    self.logger.warning(error_msg)
                    skipped_count += 1
                    continue

        ctx.parsed_sections.append('match_events')

        # 📊 记录处理统计信息
        total_events = len(events_data)
        self.logger.info(
            "Event processing summary - Total: %d, Processed: %d, Skipped: %d, Yielded: %d",
            total_events, processed_count, skipped_count, len(events)
        )

        if len(events) == 0 and total_events > 0:
            self.logger.warning(
                "No core events extracted from %d total events. Check event types: %s",
                total_events, [self._get_value_from_alternatives(event, ['type', 'Type'], 'unknown')
                             for event in events_data[:5] if isinstance(event, dict)]
            )

        return events

    def _parse_single_event(self, event_data: Dict[str, Any], index: int) -> Optional[L2MatchEvent]:
        """
        解析单个比赛事件 - 数据质量修复版本

        Args:
            event_data: 事件数据 (假设已通过白名单过滤)
            index: 事件索引

        Returns:
            Optional[L2MatchEvent]: 解析后的事件，解析失败返回None
        """
        if not isinstance(event_data, dict):
            self.logger.debug("Event data %d is not a dictionary", index)
            return None

        # 🔧 修复：使用备选键名提取而不是嵌套路径
        event_type_str = self._get_value_from_alternatives(event_data, ['type', 'Type'], '')

        # 🔧 修复时间提取 - 添加 timeStr 支持 (FotMob 常用字段)
        minute = self._get_value_from_alternatives(event_data, ['minute', 'Minute', 'timeStr', 'time'], 0)

        team_id = self._get_value_from_alternatives(event_data, ['teamId', 'team'], '')

        # 🔧 修复球员名称提取 - 处理字典格式的 player 对象
        player_name = self._get_value_from_alternatives(event_data, ['playerName', 'player'], '')

        if not event_type_str:
            self.logger.debug("Event %d has empty type field", index)
            return None

        # 🔧 清理球员名称 - 处理字典对象
        if isinstance(player_name, dict):
            player_name = (
                player_name.get('name') or
                player_name.get('fullName') or
                player_name.get('firstName') or
                str(player_name)
            )

        # 🔧 时间字符串处理 - 解析 "45+3" 格式
        if isinstance(minute, str):
            minute = self._parse_minute_string(minute)
        elif isinstance(minute, (int, float)):
            minute = int(minute)
        else:
            minute = 0

        # 🎯 事件类型转换 - 优化处理首字母大写格式
        event_type_lower = event_type_str.lower()

        # 直接匹配核心事件类型 (避免枚举转换的复杂性)
        if event_type_lower in ['goal', 'gol']:
            event_type_str = 'Goal'
        elif event_type_lower in ['card', 'yellowcard', 'redcard']:
            event_type_str = 'Card'
        elif event_type_lower in ['substitution', 'sub']:
            event_type_str = 'Substitution'
        elif event_type_lower in ['var']:
            event_type_str = 'Var'
        else:
            # 如果通过了白名单但仍然无法识别，记录为debug而不是warning
            self.logger.debug("Unexpected event type after whitelist: %s", event_type_str)
            return None

        # 转换为枚举类型
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            self.logger.debug("Failed to convert event type to enum: %s", event_type_str)
            return None

        # 处理特殊字段
        is_goal = False
        is_own_goal = False
        card_type = None
        substituted_player = None

        if event_type == EventType.GOAL:
            is_goal = True
            # 🔧 修复：使用备选键名提取
            is_own_goal = self._get_value_from_alternatives(event_data, ['isOwnGoal', 'ownGoal'], False)

            # 确保 is_own_goal 是布尔类型
            if isinstance(is_own_goal, str):
                is_own_goal = is_own_goal.lower() in ['true', '1', 'yes']
            elif is_own_goal is None:
                is_own_goal = False

        elif event_type == EventType.CARD:
            # 🔧 修复：使用备选键名提取
            card_type_str = self._get_value_from_alternatives(event_data, ['cardType', 'card'], '')
            try:
                card_type = CardType(card_type_str.title())
            except ValueError:
                card_type_lower = card_type_str.lower()
                if 'yellow' in card_type_lower:
                    card_type = CardType.YELLOW
                elif 'red' in card_type_lower:
                    card_type = CardType.RED
                elif 'second' in card_type_lower:
                    card_type = CardType.SECOND_YELLOW
                else:
                    card_type = None

        elif event_type == EventType.SUBSTITUTION:
            # 🔧 修复：使用备选键名提取
            substituted_player = self._get_value_from_alternatives(event_data, ['substitutedPlayer', 'playerOut'], '')

        # 🔧 修复：使用备选键名提取
        description = self._get_value_from_alternatives(event_data, ['description', 'desc'], '')
        if isinstance(description, dict):
            # 如果是字典，尝试获取文本值
            description = description.get('text', '') or str(description)
        elif not isinstance(description, str):
            description = str(description) if description is not None else ''

        # 创建事件对象
        try:
            event = L2MatchEvent(
                event_type=str(event_type.value),
                minute=minute,
                player_name=str(player_name) if player_name else '',
                team_id=str(team_id) if team_id else '',
                description=description,
                is_goal=is_goal,
                is_own_goal=is_own_goal,
                card_type=str(card_type.value) if card_type else None,
                substituted_player=str(substituted_player) if substituted_player else None
            )

            self.logger.debug(
                "Parsed event: type=%s, minute=%d, player=%s",
                event.event_type, event.minute, event.player_name
            )

            return event

        except ValidationError as e:
            self.logger.error("Validation error for event %d: %s", index, e)
            if self.strict_mode:
                raise
            else:
                return None

    def _parse_minute_string(self, time_str: str) -> int:
        """
        解析时间字符串，支持 "45+3" 格式

        Args:
            time_str: 时间字符串

        Returns:
            int: 解析后的分钟数
        """
        if not isinstance(time_str, str):
            return 0

        try:
            # 处理 "45+3" 格式
            if '+' in time_str:
                parts = time_str.split('+')
                if len(parts) >= 2:
                    base_minute = int(parts[0].strip())
                    added_minute = int(parts[1].strip())
                    return base_minute + added_minute

            # 处理纯数字
            return int(float(time_str))

        except (ValueError, TypeError):
            self.logger.debug(f"Failed to parse minute string: {time_str}")
            return 0

    def _extract_shot_data(self, ctx: ParsingContext) -> List[L2ShotData]:
        """
        提取射门数据

        Args:
            ctx: 解析上下文

        Returns:
            List[L2ShotData]: 射门数据列表
        """
        self.logger.debug("Extracting shot data for match %s", ctx.match_id)

        # 尝试多个可能的射门数据位置 - 修正为小写
        shot_paths = [
            ['content', 'stats', 'shots'],
            ['stats', 'shots'],
            ['shots'],
            ['header', 'shots'],
            ['matchFacts', 'shots'],
            ['content', 'matchFacts', 'shots']
        ]

        shots_data = None

        for path in shot_paths:
            shots_data = self._get_nested_value(ctx.raw_data, path)
            if shots_data:
                self.logger.debug(f"Found shots at path: {path}")
                break

        if not shots_data:
            if self.strict_mode:
                raise ValueError("Shot data not found")
            else:
                self.logger.warning("Shot data not found, returning empty list")
                return []

        # 🔧 智能拆包：处理包装的射门数据
        shots_data = self._smart_unwrap(shots_data, expected_type='list', target_key='shots')

        if not isinstance(shots_data, list):
            if self.strict_mode:
                raise ValueError(f"Shot data is not a list: {type(shots_data)}")
            else:
                self.logger.warning("Shot data is not a list, returning empty list")
                return []

        shots = []

        for i, shot_data in enumerate(shots_data):
            try:
                shot = self._parse_single_shot(shot_data, i)
                if shot:
                    shots.append(shot)

            except Exception as e:
                error_msg = f"Error parsing shot {i}: {str(e)}"
                if self.strict_mode:
                    raise ValueError(error_msg)
                else:
                    self.logger.warning(error_msg)
                    continue

        ctx.parsed_sections.append('shot_data')
        self.logger.debug("Extracted %d shot data points", len(shots))

        return shots

    def _parse_single_shot(self, shot_data: Dict[str, Any], index: int) -> Optional[L2ShotData]:
        """
        解析单个射门数据 - 数据质量修复版本

        Args:
            shot_data: 射门数据
            index: 射门索引

        Returns:
            Optional[L2ShotData]: 解析后的射门数据
        """
        if not isinstance(shot_data, dict):
            self.logger.warning("Shot data %d is not a dictionary", index)
            return None

        # 🔧 修复：使用备选键名提取而不是嵌套路径
        # 🔧 修复时间提取 - 添加 timeStr 支持 (FotMob 常用字段)
        minute = self._get_value_from_alternatives(shot_data, ['minute', 'Minute', 'timeStr', 'time'], 0)
        player_name = self._get_value_from_alternatives(shot_data, ['playerName', 'player'], '')
        team_id = self._get_value_from_alternatives(shot_data, ['teamId', 'team'], '')
        x = self._get_value_from_alternatives(shot_data, ['x', 'X'], 0.0)
        y = self._get_value_from_alternatives(shot_data, ['y', 'Y'], 0.0)
        is_on_target = self._get_value_from_alternatives(shot_data, ['isOnTarget', 'onTarget'], False)
        expected_goals = self._get_value_from_alternatives(shot_data, ['expectedGoals', 'xg', 'xG'], 0.0)
        shot_type = self._get_value_from_alternatives(shot_data, ['shotType', 'type'], '')
        is_goal = self._get_value_from_alternatives(shot_data, ['isGoal', 'goal'], False)
        is_blocked = self._get_value_from_alternatives(shot_data, ['isBlocked', 'blocked'], False)

        # 🔧 清理球员名称 - 处理字典对象
        if isinstance(player_name, dict):
            player_name = (
                player_name.get('name') or
                player_name.get('fullName') or
                player_name.get('firstName') or
                str(player_name)
            )

        # 🔧 时间字符串处理 - 解析 "45+3" 格式
        if isinstance(minute, str):
            minute = self._parse_minute_string(minute)
        elif isinstance(minute, (int, float)):
            minute = int(minute)
        else:
            minute = 0

        # 类型转换和默认值处理
        try:
            minute = int(minute) if minute is not None else 0
            x = float(x) if x is not None else 0.0
            y = float(y) if y is not None else 0.0
            expected_goals = float(expected_goals) if expected_goals is not None else 0.0

            if isinstance(is_on_target, str):
                is_on_target = is_on_target.lower() in ['true', '1', 'yes']
            else:
                is_on_target = bool(is_on_target)

            if isinstance(is_goal, str):
                is_goal = is_goal.lower() in ['true', '1', 'yes']
            else:
                is_goal = bool(is_goal)

            if isinstance(is_blocked, str):
                is_blocked = is_blocked.lower() in ['true', '1', 'yes']
            else:
                is_blocked = bool(is_blocked)

        except (ValueError, TypeError) as e:
            self.logger.warning("Type conversion error for shot %d: %s", index, e)
            minute, x, y, expected_goals = 0, 0.0, 0.0, 0.0
            is_on_target, is_goal, is_blocked = False, False, False

        # 确保字符串类型
        player_name = str(player_name) if player_name else ''
        team_id = str(team_id) if team_id else ''
        shot_type = str(shot_type) if shot_type else ''

        try:
            shot = L2ShotData(
                minute=minute,
                player_name=player_name,
                team_id=team_id,
                x=x,
                y=y,
                is_on_target=is_on_target,
                expected_goals=expected_goals,
                shot_type=shot_type,
                is_goal=is_goal,
                is_blocked=is_blocked
            )

            self.logger.debug(
                "Parsed shot: minute=%d, player=%s, x=%.2f, y=%.2f, goal=%s",
                shot.minute, shot.player_name, shot.x, shot.y, shot.is_goal
            )

            return shot

        except ValidationError as e:
            self.logger.error("Validation error for shot %d: %s", index, e)
            if self.strict_mode:
                raise
            else:
                return None

    def _extract_player_ratings(self, ctx: ParsingContext) -> Dict[str, L2PlayerRating]:
        """
        提取球员评分数据

        Args:
            ctx: 解析上下文

        Returns:
            Dict[str, L2PlayerRating]: 球员评分数据
        """
        self.logger.debug("Extracting player ratings for match %s", ctx.match_id)

        # 尝试多个可能的球员评分位置 - 修正为小写
        rating_paths = [
            ['content', 'stats', 'playerRatings'],
            ['stats', 'playerRatings'],
            ['playerRatings'],
            ['ratings'],
            ['header', 'ratings'],
            ['matchFacts', 'ratings']
        ]

        ratings_data = None

        for path in rating_paths:
            ratings_data = self._get_nested_value(ctx.raw_data, path)
            if ratings_data:
                self.logger.debug(f"Found ratings at path: {path}")
                break

        if not ratings_data:
            if self.strict_mode:
                raise ValueError("Player ratings data not found")
            else:
                self.logger.warning("Player ratings data not found, returning empty dict")
                return {}

        # 🔧 智能拆包：处理包装的评分数据
        ratings_data = self._smart_unwrap(ratings_data, expected_type='dict', target_key='ratings')

        player_ratings = {}

        if isinstance(ratings_data, dict):
            for player_id, rating_data in ratings_data.items():
                try:
                    rating = self._parse_single_player_rating(player_id, rating_data)
                    if rating:
                        player_ratings[str(player_id)] = rating
                except Exception as e:
                    if self.strict_mode:
                        raise ValueError(f"Error parsing player rating for {player_id}: {str(e)}")
                    else:
                        self.logger.warning("Error parsing player rating for %s: %s", player_id, e)
                        continue
        else:
            if self.strict_mode:
                raise ValueError(f"Player ratings data is not a dictionary: {type(ratings_data)}")
            else:
                self.logger.warning("Player ratings data is not a dictionary, returning empty dict")
                return {}

        ctx.parsed_sections.append('player_ratings')
        self.logger.debug("Extracted ratings for %d players", len(player_ratings))

        return player_ratings

    def _parse_single_player_rating(
        self,
        player_id: str,
        rating_data: Union[Dict[str, Any], float, int, str]
    ) -> Optional[L2PlayerRating]:
        """
        解析单个球员评分

        Args:
            player_id: 球员ID
            rating_data: 评分数据

        Returns:
            Optional[L2PlayerRating]: 解析后的评分数据
        """
        try:
            if isinstance(rating_data, (int, float)):
                rating = float(rating_data)
                player_name = ''
            elif isinstance(rating_data, str):
                rating = float(rating_data) if rating_data.replace('.', '').isdigit() else 0.0
                player_name = ''
            elif isinstance(rating_data, dict):
                # 🔧 修复：使用备选键名提取而不是嵌套路径
                rating = float(self._get_value_from_alternatives(rating_data, ['rating', 'Rating'], 0.0))
                player_name = str(self._get_value_from_alternatives(rating_data, ['playerName', 'name'], ''))
            else:
                self.logger.warning("Invalid rating data type for player %s: %s", player_id, type(rating_data))
                return None

            # 验证评分范围
            if not (0.0 <= rating <= 10.0):
                self.logger.warning("Invalid rating value for player %s: %s", player_id, rating)
                if self.strict_mode:
                    return None
                else:
                    rating = max(0.0, min(10.0, rating))

            player_rating = L2PlayerRating(
                player_id=str(player_id),
                player_name=player_name,
                rating=rating
            )

            self.logger.debug(
                "Parsed player rating: id=%s, name=%s, rating=%.2f",
                player_rating.player_id, player_rating.player_name, player_rating.rating
            )

            return player_rating

        except (ValueError, TypeError) as e:
            self.logger.error("Error parsing player rating for %s: %s", player_id, e)
            if self.strict_mode:
                return None
            else:
                return None

    def _get_default_value(self, field: str) -> Any:
        """获取字段的默认值"""
        defaults = {
            'match_id': '',
            'home_team': '',
            'away_team': '',
            'home_score': 0,
            'away_score': 0,
            'status': '',
            'match_time': '',
            'stadium': '',
            'attendance': 0,
            'referee': '',
            'weather': ''
        }
        return defaults.get(field, None)

    def _get_default_stat_value(self, stat_field: str) -> Any:
        """获取统计字段的默认值"""
        if stat_field in ['possession', 'expected_goals']:
            return 0.0
        elif stat_field in [
            'shots', 'shots_on_target', 'corners', 'fouls', 'offsides',
            'yellow_cards', 'red_cards', 'saves', 'passes', 'tackles',
            'interceptions', 'clearances', 'aerials_won', 'blocked_shots',
            'counter_attacks', 'through_balls', 'long_balls', 'crosses',
            'touches', 'big_chances_created', 'big_chances_missed'
        ]:
            return 0
        else:
            return None

    def _create_default_team_stats(self, match_id: str) -> Tuple[L2TeamStats, L2TeamStats]:
        """创建默认的球队统计数据"""
        default_stats = {
            'possession': 0.0,
            'shots': 0,
            'shots_on_target': 0,
            'corners': 0,
            'fouls': 0,
            'offsides': 0,
            'yellow_cards': 0,
            'red_cards': 0,
            'saves': 0,
            'expected_goals': 0.0,
            'big_chances_created': 0,
            'big_chances_missed': 0,
            'passes': 0,
            'tackles': 0,
            'interceptions': 0
        }

        home_stats = L2TeamStats(**default_stats)
        away_stats = L2TeamStats(**default_stats)

        return home_stats, away_stats

    def _extract_match_id(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """
        从原始数据中提取比赛ID，支持多种可能的路径

        Args:
            raw_data: 原始数据字典

        Returns:
            Optional[str]: 比赛ID，如果无法找到则返回None
        """
        self.logger.debug("Attempting to extract match_id from raw data")

        # 尝试多种可能的路径来提取match_id
        possible_paths = [
            # 标准路径 - 修正为小写
            ['general', 'matchId'],
            ['matchId'],

            # FotMob API 常见路径
            ['id'],
            ['match', 'id'],
            ['matchId'],
            ['match_id'],

            # 嵌套结构路径 - 修正为小写
            ['header', 'id'],
            ['header', 'matchId'],
            ['content', 'matchFacts', 'matchId'],
            ['matchDetails', 'general', 'matchId'],

            # 其他可能的路径
            ['data', 'id'],
            ['response', 'id'],
            ['data', 'matchId'],
            ['response', 'matchId'],
        ]

        for path in possible_paths:
            match_id = self._get_nested_value(raw_data, path)
            if match_id:
                # 清理和验证ID
                match_id_str = str(match_id).strip()
                if match_id_str and match_id_str.isdigit():
                    self.logger.debug(f"Found match_id {match_id_str} at path {' -> '.join(path)}")
                    return match_id_str
                elif match_id_str:
                    # 如果不是纯数字但非空，也返回
                    self.logger.debug(f"Found match_id {match_id_str} (non-numeric) at path {' -> '.join(path)}")
                    return match_id_str

        # 尝试从URL中提取（如果存在）
        try:
            for key in raw_data.keys():
                if 'url' in key.lower():
                    url = str(raw_data[key])
                    match_id_match = re.search(r'/(\d{6,8})/?(?:[^0-9]|$)', url)
                    if match_id_match:
                        match_id = match_id_match.group(1)
                        self.logger.debug(f"Extracted match_id {match_id} from URL {key}")
                        return match_id
        except Exception as e:
            self.logger.debug(f"Error extracting match_id from URL: {e}")

        # 尝试从数据根级别的任意数值字段中提取
        try:
            for key, value in raw_data.items():
                if key.lower() in ['match', 'matchid', 'match_id', 'id', 'gameid', 'game_id']:
                    if isinstance(value, (int, str)):
                        match_id_str = str(value).strip()
                        if match_id_str.isdigit() and len(match_id_str) >= 6:
                            self.logger.debug(f"Found potential match_id {match_id_str} at root key '{key}'")
                            return match_id_str
        except Exception as e:
            self.logger.debug(f"Error scanning root keys: {e}")

        self.logger.warning("Could not extract match_id from any known path")
        return None

    def parse_match_data(self, raw_data: Dict[str, Any]) -> L2DataProcessingResult:
        """
        解析比赛数据的主入口

        Args:
            raw_data: 原始数据字典

        Returns:
            L2DataProcessingResult: 解析结果
        """
        if not isinstance(raw_data, dict):
            return L2DataProcessingResult(
                success=False,
                data=None,
                error_message="Input data is not a dictionary",
                parsed_sections=[]
            )

        # 获取match_id
        match_id = self._extract_match_id(raw_data)

        if not match_id:
            return L2DataProcessingResult(
                success=False,
                data=None,
                error_message="Cannot extract match_id from raw data",
                parsed_sections=[]
            )

        ctx = ParsingContext(match_id=match_id, raw_data=raw_data, strict_mode=self.strict_mode)

        try:
            # 提取基本信息
            basic_info = self._extract_match_basic_info(ctx)

            # 提取球队统计
            home_stats, away_stats = self._extract_team_stats(ctx)

            # 提取比赛事件
            events = self._extract_match_events(ctx)

            # 提取射门数据
            shot_data = self._extract_shot_data(ctx)

            # 提取球员评分
            player_ratings = self._extract_player_ratings(ctx)

            # 创建L2MatchData对象
            l2_data = L2MatchData(
                match_id=basic_info.get('match_id', ''),
                fotmob_id=basic_info.get('match_id', ''),
                home_team=basic_info.get('home_team', ''),
                away_team=basic_info.get('away_team', ''),
                home_score=basic_info.get('home_score', 0),
                away_score=basic_info.get('away_score', 0),
                status=basic_info.get('status', ''),
                home_stats=home_stats,
                away_stats=away_stats,
                events=events,
                shot_map=shot_data,
                player_ratings=player_ratings,
                data_source="fotmob",
                collected_at=datetime.now(),
                data_completeness_score=0.8  # 默认完整性分数
            )

            self.logger.info(
                "Successfully parsed match data for %s: %s vs %s (%d-%d), %d events, %d shots",
                match_id,
                l2_data.home_team,
                l2_data.away_team,
                l2_data.home_score,
                l2_data.away_score,
                len(events),
                len(shot_data)
            )

            return L2DataProcessingResult(
                success=True,
                data=l2_data,
                error_message=None,
                parsed_sections=ctx.parsed_sections
            )

        except Exception as e:
            error_message = f"Error parsing match data: {str(e)}"
            self.logger.error("%s (match: %s, sections: %s)", error_message, match_id, ctx.parsed_sections)

            return L2DataProcessingResult(
                success=False,
                data=None,
                error_message=error_message,
                parsed_sections=ctx.parsed_sections
            )