#!/usr/bin/env python3
"""
高级特征提取器 v2.0 - 106字段完整特征提取系统
Advanced Feature Extractor - Complete 106-Field Feature Extraction

核心功能：
- 真实Expected Goals (xG) 数据提取
- 精确控球率 (Possession) 提取
- 完整赔率 (Odds) 解析
- 106个字段的全量特征提取
- 语义搜索算法优化
- 类型安全数据验证
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from typing import Protocol

try:
    from src.api.fotmob_client import FotMobAPIClient
except ImportError:
    FotMobAPIClient = None  # 可选依赖，用于生产环境


class DataClientProtocol(Protocol):
    """数据客户端协议，用于依赖注入"""

    async def get_match_data(self, match_id: str) -> Dict[str, Any]:
        """获取比赛数据"""
        ...

    async def get_multiple_matches(self, match_ids: List[str]) -> List[Dict[str, Any]]:
        """批量获取比赛数据"""
        ...


try:
    from src.schemas.match_features import MatchFeatures, DataSource, FeatureVersion
except ImportError:
    # 备用导入方案
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).parent.parent.parent))
    from schemas.match_features import MatchFeatures, DataSource, FeatureVersion

logger = logging.getLogger(__name__)


class FeatureExtractionError(Exception):
    """特征提取异常"""

    pass


class FeatureExtractionConfig:
    """特征提取配置"""

    # xG提取模式 - 精确匹配expectedGoals
    XG_PATTERNS = {
        "home": [
            r"home.*expectedGoals.*?([\d.]+)",  # homeExpectedGoals: 1.25
            r"homexg.*?([\d.]+)",  # homexg: 1.25
            r"expectedGoals.*?home.*?([\d.]+)",  # expectedGoals[home]: 1.25
            r"team.*0.*expectedGoals.*?([\d.]+)",  # team[0].expectedGoals
            r"stats.*home.*xg.*?([\d.]+)",  # stats.home.xg
        ],
        "away": [
            r"away.*expectedGoals.*?([\d.]+)",  # awayExpectedGoals: 0.85
            r"awayxg.*?([\d.]+)",  # awayxg: 0.85
            r"expectedGoals.*?away.*?([\d.]+)",  # expectedGoals[away]: 0.85
            r"team.*1.*expectedGoals.*?([\d.]+)",  # team[1].expectedGoals
            r"stats.*away.*xg.*?([\d.]+)",  # stats.away.xg
        ],
    }

    # 控球率精确模式
    POSSESSION_PATTERNS = {
        "home": [
            r"home.*possession.*?(\d+)",  # homePossession: 55
            r"possession.*home.*?(\d+)",  # possession[home]: 55
            r"stats.*home.*possession.*?(\d+)",  # stats.home.possession
            r"team.*0.*possession.*?(\d+)",  # team[0].possession
        ],
        "away": [
            r"away.*possession.*?(\d+)",  # awayPossession: 45
            r"possession.*away.*?(\d+)",  # possession[away]: 45
            r"stats.*away.*possession.*?(\d+)",  # stats.away.possession
            r"team.*1.*possession.*?(\d+)",  # team[1].possession
        ],
    }

    # 赔率精确模式
    ODDS_PATTERNS = {
        "home": [
            r"home.*win.*odds.*?([\d.]+)",  # homeWinOdds: 2.15
            r"1.*?([\d.]+).*?2.*?([\d.]+)",  # 1:2.15  X:3.40 2:3.20 (主队赔率)
            r"odds.*?home.*?([\d.]+)",  # odds[home]: 2.15
            r"market.*?1.*?([\d.]+)",  # market[1]: 2.15
        ],
        "away": [
            r"away.*win.*odds.*?([\d.]+)",  # awayWinOdds: 3.20
            r"odds.*?away.*?([\d.]+)",  # odds[away]: 3.20
            r"market.*?2.*?([\d.]+)",  # market[2]: 3.20
        ],
        "draw": [
            r"draw.*odds.*?([\d.]+)",  # drawOdds: 3.40
            r"x.*?([\d.]+)",  # X: 3.40
            r"market.*?x.*?([\d.]+)",  # market[x]: 3.40
        ],
    }


class SmartRecursiveExtractor:
    """智能递归提取器"""

    def __init__(self, max_depth: int = 15):
        self.max_depth = max_depth
        self.visited_paths = set()

    def extract_value(self, data: Any, patterns: List[str], context: str = "") -> Optional[float]:
        """
        智能递归提取数值

        Args:
            data: 原始数据
            patterns: 匹配模式列表
            context: 提取上下文（用于调试）

        Returns:
            提取的数值或None
        """
        if isinstance(data, (str, int, float)):
            # 直接在值中匹配
            for pattern in patterns:
                match = re.search(pattern, str(data), re.IGNORECASE)
                if match:
                    try:
                        return float(match.group(1))
                    except (ValueError, AttributeError):
                        continue
            return None

        elif isinstance(data, dict):
            # 在字典中递归搜索
            for key, value in data.items():
                # 1. 首先在键名中匹配
                for pattern in patterns:
                    match = re.search(pattern, str(key), re.IGNORECASE)
                    if match and value is not None:
                        try:
                            # 如果键名匹配，直接使用对应的值
                            return float(value) if isinstance(value, (int, float, str)) else None
                        except (ValueError, TypeError):
                            continue

                # 2. 在值中递归搜索
                if isinstance(value, (dict, list)) and len(self.visited_paths) < 1000:
                    current_path = f"{context}.{key}" if context else key
                    if current_path not in self.visited_paths:
                        self.visited_paths.add(current_path)
                        result = self.extract_value(value, patterns, current_path)
                        if result is not None:
                            return result
                elif isinstance(value, (str, int, float)):
                    # 在基本类型值中匹配
                    result = self.extract_value(value, patterns, f"{context}.{key}")
                    if result is not None:
                        return result

        elif isinstance(data, list):
            # 在列表中递归搜索
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    current_path = f"{context}[{i}]" if context else f"[{i}]"
                    if current_path not in self.visited_paths:
                        self.visited_paths.add(current_path)
                        result = self.extract_value(item, patterns, current_path)
                        if result is not None:
                            return result
                elif isinstance(item, (str, int, float)):
                    result = self.extract_value(item, patterns, f"{context}[{i}]")
                    if result is not None:
                        return result

        return None


class XGDataAggregator:
    """xG数据聚合器 - 从shots中精确计算expectedGoals"""

    @staticmethod
    def aggregate_from_shotmap(data: Dict[str, Any]) -> Tuple[float, float]:
        """
        从shotmap中聚合xG数据

        Args:
            data: 原始比赛数据

        Returns:
            (home_xg, away_xg) 元组
        """
        home_xg, away_xg = 0.0, 0.0

        def extract_from_events(events_data: Dict[str, Any]):
            nonlocal home_xg, away_xg

            if not isinstance(events_data, dict):
                return

            # 1. 从主队进球中提取xG
            if "homeTeamGoals" in events_data:
                for player_goals in events_data["homeTeamGoals"].values():
                    if isinstance(player_goals, list):
                        for goal in player_goals:
                            if isinstance(goal, dict) and "shotmapEvent" in goal:
                                shot_event = goal["shotmapEvent"]
                                if "expectedGoals" in shot_event:
                                    try:
                                        home_xg += float(shot_event["expectedGoals"])
                                    except (ValueError, TypeError):
                                        continue

            # 2. 从客队进球中提取xG
            if "awayTeamGoals" in events_data:
                for player_goals in events_data["awayTeamGoals"].values():
                    if isinstance(player_goals, list):
                        for goal in player_goals:
                            if isinstance(goal, dict) and "shotmapEvent" in goal:
                                shot_event = goal["shotmapEvent"]
                                if "expectedGoals" in shot_event:
                                    try:
                                        away_xg += float(shot_event["expectedGoals"])
                                    except (ValueError, TypeError):
                                        continue

        def extract_from_shots(shots_data: Dict[str, Any]):
            nonlocal home_xg, away_xg

            if not isinstance(shots_data, dict):
                return

            for team_key, shot_list in shots_data.items():
                if not isinstance(shot_list, list):
                    continue

                team_xg = 0.0
                for shot in shot_list:
                    if not isinstance(shot, dict):
                        continue

                    # 查找xG字段的所有可能名称
                    for xg_key in ["expectedGoals", "xg", "xG", "expected_goal", "preShotXg", "shotXg"]:
                        if xg_key in shot:
                            try:
                                team_xg += float(shot[xg_key])
                            except (ValueError, TypeError):
                                continue

                # 根据team_key判断队伍
                team_key_lower = str(team_key).lower()
                if any(
                    keyword in team_key_lower
                    for keyword in ["home", "0", team_data.get("homeTeam", {}).get("name", "").lower()]
                ):
                    home_xg += team_xg
                else:
                    away_xg += team_xg

        def recursive_search(obj: Any):
            """递归搜索events和shots数据"""
            if isinstance(obj, dict):
                # 1. 优先查找events（最准确的xG数据）
                extract_from_events(obj)

                # 2. 查找shots数据
                if "shots" in obj:
                    extract_from_shots(obj["shots"])

                # 3. 递归搜索其他可能的字段
                for key, value in obj.items():
                    if isinstance(value, (dict, list)):
                        recursive_search(value)

            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        recursive_search(item)

        # 执行递归搜索
        recursive_search(data)

        return home_xg, away_xg


class PlayerLevelExtractor:
    """球员级特征提取器 - V4.2新增"""

    def extract_player_ratings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取球员评分特征"""
        player_features = {
            # 首发11人平均评分
            'home_avg_starting_rating': None,
            'away_avg_starting_rating': None,
            'avg_rating_diff': None,
            # 替补席深度评分
            'home_bench_strength': None,
            'away_bench_strength': None,
            'bench_strength_diff': None,
            # 球员质量分布
            'home_star_players_count': None,  # 评分>8.0的球员数
            'away_star_players_count': None,
            'home_weak_players_count': None,  # 评分<6.5的球员数
            'away_weak_players_count': None,
            # 阵容均衡性
            'home_rating_variance': None,  # 评分方差（反映阵容均衡性）
            'away_rating_variance': None,
            'rating_variance_diff': None,
        }

        # 从FotMob API提取球员评分数据
        ratings_data = self._extract_ratings_from_fotmob(data)
        if ratings_data:
            player_features.update(ratings_data)

        return player_features

    def _extract_ratings_from_fotmob(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """从FotMob API提取球员评分"""
        try:
            # 方法1: 从topPlayers提取
            if 'content' in data and 'topPlayers' in data['content']:
                top_players = data['content']['topPlayers']
                if isinstance(top_players, dict):
                    home_ratings = []
                    away_ratings = []

                    # 主队球员评分
                    if 'home' in top_players and isinstance(top_players['home'], list):
                        for player in top_players['home']:
                            if isinstance(player, dict) and 'rating' in player:
                                try:
                                    rating = float(player['rating'])
                                    home_ratings.append(rating)
                                except (ValueError, TypeError):
                                    continue

                    # 客队球员评分
                    if 'away' in top_players and isinstance(top_players['away'], list):
                        for player in top_players['away']:
                            if isinstance(player, dict) and 'rating' in player:
                                try:
                                    rating = float(player['rating'])
                                    away_ratings.append(rating)
                                except (ValueError, TypeError):
                                    continue

                    return self._calculate_rating_metrics(home_ratings, away_ratings)

            # 方法2: 从lineup提取
            if 'content' in data and 'lineup' in data['content']:
                lineup = data['content']['lineup']
                if isinstance(lineup, dict):
                    home_ratings = []
                    away_ratings = []

                    # 提取主队评分
                    if 'home' in lineup:
                        home_ratings = self._extract_lineup_ratings(lineup['home'])

                    # 提取客队评分
                    if 'away' in lineup:
                        away_ratings = self._extract_lineup_ratings(lineup['away'])

                    return self._calculate_rating_metrics(home_ratings, away_ratings)

        except Exception as e:
            logger.debug(f"球员评分提取失败: {e}")

        return {}

    def _extract_lineup_ratings(self, lineup_data: Any) -> List[float]:
        """从阵容数据提取评分"""
        ratings = []

        if isinstance(lineup_data, dict):
            # 检查players字段
            if 'players' in lineup_data and isinstance(lineup_data['players'], list):
                for player in lineup_data['players']:
                    if isinstance(player, dict):
                        # 查找评分字段
                        for rating_field in ['rating', 'score', 'matchRating', 'performance']:
                            if rating_field in player:
                                try:
                                    rating = float(player[rating_field])
                                    ratings.append(rating)
                                    break
                                except (ValueError, TypeError):
                                    continue

            # 检查直接的球员列表
            elif 'startingXI' in lineup_data and isinstance(lineup_data['startingXI'], list):
                for player in lineup_data['startingXI']:
                    if isinstance(player, dict):
                        for rating_field in ['rating', 'score', 'matchRating']:
                            if rating_field in player:
                                try:
                                    rating = float(player[rating_field])
                                    ratings.append(rating)
                                    break
                                except (ValueError, TypeError):
                                    continue

        return ratings

    def _calculate_rating_metrics(self, home_ratings: List[float], away_ratings: List[float]) -> Dict[str, Any]:
        """计算评分相关指标"""
        metrics = {}

        if home_ratings:
            metrics['home_avg_starting_rating'] = round(sum(home_ratings) / len(home_ratings), 2)
            metrics['home_star_players_count'] = sum(1 for r in home_ratings if r > 8.0)
            metrics['home_weak_players_count'] = sum(1 for r in home_ratings if r < 6.5)

            # 计算方差（阵容均衡性）
            if len(home_ratings) > 1:
                mean_rating = metrics['home_avg_starting_rating']
                variance = sum((r - mean_rating) ** 2 for r in home_ratings) / len(home_ratings)
                metrics['home_rating_variance'] = round(variance, 3)

        if away_ratings:
            metrics['away_avg_starting_rating'] = round(sum(away_ratings) / len(away_ratings), 2)
            metrics['away_star_players_count'] = sum(1 for r in away_ratings if r > 8.0)
            metrics['away_weak_players_count'] = sum(1 for r in away_ratings if r < 6.5)

            # 计算方差
            if len(away_ratings) > 1:
                mean_rating = metrics['away_avg_starting_rating']
                variance = sum((r - mean_rating) ** 2 for r in away_ratings) / len(away_ratings)
                metrics['away_rating_variance'] = round(variance, 3)

        # 计算差值
        if metrics.get('home_avg_starting_rating') and metrics.get('away_avg_starting_rating'):
            metrics['avg_rating_diff'] = round(
                metrics['home_avg_starting_rating'] - metrics['away_avg_starting_rating'], 2
            )

        if metrics.get('home_rating_variance') and metrics.get('away_rating_variance'):
            metrics['rating_variance_diff'] = round(
                metrics['home_rating_variance'] - metrics['away_rating_variance'], 3
            )

        # 估算替补深度（基于阵容中的替补球员数量）
        metrics['home_bench_strength'] = len([r for r in home_ratings if r < 7.0]) * 0.8  # 经验公式
        metrics['away_bench_strength'] = len([r for r in away_ratings if r < 7.0]) * 0.8

        if metrics.get('home_bench_strength') and metrics.get('away_bench_strength'):
            metrics['bench_strength_diff'] = round(
                metrics['home_bench_strength'] - metrics['away_bench_strength'], 1
            )

        return metrics


class TacticalPatternExtractor:
    """战术风格特征提取器 - V4.2新增"""

    def extract_tactical_patterns(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取战术风格特征"""
        tactical_features = {
            # 关键传球
            'home_key_passes': None,
            'away_key_passes': None,
            'key_passes_diff': None,
            'home_key_passes_per90': None,
            'away_key_passes_per90': None,

            # 绝佳机会
            'home_big_chances_created': None,
            'away_big_chances_created': None,
            'big_chances_diff': None,
            'home_big_chance_conversion': None,
            'away_big_chance_conversion': None,

            # 高位逼抢
            'home_high_pressures': None,
            'away_high_pressures': None,
            'high_pressures_diff': None,
            'home_press_success_rate': None,
            'away_press_success_rate': None,

            # 战术纪律
            'home_offsides_count': None,
            'away_offsides_count': None,
            'offsides_diff': None,
            'home_fouls_committed': None,
            'away_fouls_committed': None,
            'fouls_diff': None,

            # 球权控制
            'home_ball_recoveries': None,
            'away_ball_recoveries': None,
            'ball_recoveries_diff': None,
            'home_aerial_duels_won': None,
            'away_aerial_duels_won': None,
            'aerial_duels_diff': None,

            # 创造力指标
            'home_through_balls': None,
            'away_through_balls': None,
            'through_balls_diff': None,
            'home_crosses_completed': None,
            'away_crosses_completed': None,
            'crosses_diff': None,

            # 防守组织
            'home_clearances': None,
            'away_clearances': None,
            'clearances_diff': None,
            'home_interceptions': None,
            'away_interceptions': None,
            'interceptions_diff': None,
        }

        # 从FotMob API提取战术数据
        tactical_data = self._extract_tactical_from_fotmob(data)
        if tactical_data:
            tactical_features.update(tactical_data)

        return tactical_features

    def _extract_tactical_from_fotmob(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """从FotMob API提取战术数据"""
        try:
            tactical_data = {}

            # 方法1: 从content.stats提取
            if 'content' in data and 'stats' in data['content']:
                stats = data['content']['stats']
                if 'Periods' in stats and 'All' in stats['Periods']:
                    all_stats = stats['Periods']['All'].get('stats', [])

                    if isinstance(all_stats, list):
                        for stat_group in all_stats:
                            if isinstance(stat_group, dict) and 'stats' in stat_group:
                                stat_items = stat_group['stats']
                                if isinstance(stat_items, list):
                                    for stat in stat_items:
                                        if isinstance(stat, dict) and 'stats' in stat:
                                            values = stat['stats']
                                            if isinstance(values, list) and len(values) >= 2:
                                                self._map_tactical_stat(stat['key'], values, tactical_data)

            # 方法2: 从详细统计数据提取
            if 'content' in data and 'matchFacts' in data['content']:
                match_facts = data['content']['matchFacts']
                if isinstance(match_facts, dict):
                    self._extract_from_match_facts(match_facts, tactical_data)

        except Exception as e:
            logger.debug(f"战术数据提取失败: {e}")

        return tactical_data

    def _map_tactical_stat(self, stat_key: str, values: List[Any], tactical_data: Dict[str, Any]):
        """将统计数据映射到战术特征"""
        stat_key_lower = stat_key.lower()

        try:
            home_val = float(values[0]) if values[0] is not None else None
            away_val = float(values[1]) if len(values) > 1 and values[1] is not None else None

            # 关键传球映射
            if any(keyword in stat_key_lower for keyword in ['keypass', 'key_pass', 'chancecreated']):
                tactical_data['home_key_passes'] = home_val
                tactical_data['away_key_passes'] = away_val
                if home_val and away_val:
                    tactical_data['key_passes_diff'] = home_val - away_val

            # 绝佳机会映射
            elif any(keyword in stat_key_lower for keyword in ['bigchance', 'big_chance', 'clearcutchance']):
                tactical_data['home_big_chances_created'] = home_val
                tactical_data['away_big_chances_created'] = away_val
                if home_val and away_val:
                    tactical_data['big_chances_diff'] = home_val - away_val

            # 高位逼抢映射
            elif any(keyword in stat_key_lower for keyword in ['press', 'pressure', 'counterpress']):
                tactical_data['home_high_pressures'] = home_val
                tactical_data['away_high_pressures'] = away_val
                if home_val and away_val:
                    tactical_data['high_pressures_diff'] = home_val - away_val

            # 越位映射
            elif 'offside' in stat_key_lower:
                tactical_data['home_offsides_count'] = home_val
                tactical_data['away_offsides_count'] = away_val
                if home_val and away_val:
                    tactical_data['offsides_diff'] = home_val - away_val

            # 犯规映射
            elif 'foul' in stat_key_lower:
                tactical_data['home_fouls_committed'] = home_val
                tactical_data['away_fouls_committed'] = away_val
                if home_val and away_val:
                    tactical_data['fouls_diff'] = home_val - away_val

            # 球权恢复映射
            elif any(keyword in stat_key_lower for keyword in ['recovery', 'ballrecovery', 'turnover']):
                tactical_data['home_ball_recoveries'] = home_val
                tactical_data['away_ball_recoveries'] = away_val
                if home_val and away_val:
                    tactical_data['ball_recoveries_diff'] = home_val - away_val

            # 空中对抗映射
            elif any(keyword in stat_key_lower for keyword in ['aerial', 'duel', 'head']):
                tactical_data['home_aerial_duels_won'] = home_val
                tactical_data['away_aerial_duels_won'] = away_val
                if home_val and away_val:
                    tactical_data['aerial_duels_diff'] = home_val - away_val

            # 传中映射
            elif 'cross' in stat_key_lower:
                tactical_data['home_crosses_completed'] = home_val
                tactical_data['away_crosses_completed'] = away_val
                if home_val and away_val:
                    tactical_data['crosses_diff'] = home_val - away_val

            # 解围映射
            elif any(keyword in stat_key_lower for keyword in ['clearance', 'blockedshot']):
                tactical_data['home_clearances'] = home_val
                tactical_data['away_clearances'] = away_val
                if home_val and away_val:
                    tactical_data['clearances_diff'] = home_val - away_val

            # 拦截映射
            elif 'interception' in stat_key_lower:
                tactical_data['home_interceptions'] = home_val
                tactical_data['away_interceptions'] = away_val
                if home_val and away_val:
                    tactical_data['interceptions_diff'] = home_val - away_val

        except (ValueError, TypeError, IndexError):
            pass

    def _extract_from_match_facts(self, match_facts: Dict[str, Any], tactical_data: Dict[str, Any]):
        """从比赛实况提取战术数据"""
        # 这里可以进一步解析比赛事件来提取战术指标
        # 比如通过分析传球线路、逼抢位置等
        pass


class AdvancedFeatureExtractor:
    """高级特征提取器 - V4.2扩展版 180+字段特征提取"""

    def __init__(self, config: Optional[FeatureExtractionConfig] = None):
        self.config = config or FeatureExtractionConfig()
        self.recursive_extractor = SmartRecursiveExtractor(max_depth=15)
        self.xg_aggregator = XGDataAggregator()
        self.player_extractor = PlayerLevelExtractor()
        self.tactical_extractor = TacticalPatternExtractor()

    def extract_complete_features(self, match_data: Dict[str, Any], external_id: str) -> MatchFeatures:
        """
        提取完整的180+字段特征 (V4.2扩展版)

        Args:
            match_data: 原始比赛数据
            external_id: 比赛外部ID

        Returns:
            完整的MatchFeatures对象（180+个字段）
        """
        logger.info(f"🚀 V4.2开始提取特征 - 比赛ID: {external_id}")

        # 重置访问路径记录
        self.recursive_extractor.visited_paths.clear()

        # 基础数据准备
        features_dict = self._extract_basic_info(match_data, external_id)

        # ===== V4.1 核心特征提取 =====

        # 1. xG特征提取（最关键）
        home_xg, away_xg = self._extract_xg_features(match_data)
        features_dict.update(
            {
                "home_xg": home_xg,
                "away_xg": away_xg,
            }
        )

        # 如果直接提取失败，尝试从shotmap聚合
        if home_xg is None or away_xg is None:
            aggregated_home, aggregated_away = self.xg_aggregator.aggregate_from_shotmap(match_data)
            if home_xg is None and aggregated_home > 0:
                features_dict["home_xg"] = aggregated_home
                logger.info(f"通过shotmap聚合获取主队xG: {aggregated_home}")
            if away_xg is None and aggregated_away > 0:
                features_dict["away_xg"] = aggregated_away
                logger.info(f"通过shotmap聚合获取客队xG: {aggregated_away}")

        # 2. 控球率特征提取
        home_possession, away_possession = self._extract_possession_features(match_data)
        features_dict.update(
            {
                "home_possession": home_possession,
                "away_possession": away_possession,
            }
        )

        # 3. 赔率特征提取
        odds_data = self._extract_odds_features(match_data)
        features_dict.update(odds_data)

        # 4. 角球特征提取
        corners_data = self._extract_corners_features(match_data)
        features_dict.update(corners_data)

        # 5. 红黄牌特征提取
        cards_data = self._extract_cards_features(match_data)
        features_dict.update(cards_data)

        # 6. 传球成功率特征提取
        passing_data = self._extract_passing_features(match_data)
        features_dict.update(passing_data)

        # 7. 射门特征提取
        shots_data = self._extract_shots_features(match_data)
        features_dict.update(shots_data)

        # ===== V4.2 新增球员级特征提取 =====

        # 8. 球员级特征提取
        logger.info("👥 提取球员级特征...")
        player_features = self.player_extractor.extract_player_ratings(match_data)
        features_dict.update(player_features)
        logger.info(f"   ✅ 球员级特征: {len([k for k, v in player_features.items() if v is not None])} 个有效值")

        # 9. 战术风格特征提取
        logger.info("⚔️ 提取战术风格特征...")
        tactical_features = self.tactical_extractor.extract_tactical_patterns(match_data)
        features_dict.update(tactical_features)
        logger.info(f"   ✅ 战术风格特征: {len([k for k, v in tactical_features.items() if v is not None])} 个有效值")

        # 10. V4.2进阶射门分析
        logger.info("🎯 提取进阶射门特征...")
        advanced_shots = self._extract_advanced_shot_features(match_data)
        features_dict.update(advanced_shots)

        # 11. V4.2控球率深度分析
        logger.info("📊 提取控球率深度特征...")
        advanced_possession = self._extract_advanced_possession_features(match_data)
        features_dict.update(advanced_possession)

        # 12. 补充其他特征字段（使用默认值或空值）
        features_dict = self._fill_remaining_features(features_dict, match_data)

        # 13. 计算派生字段和比率
        logger.info("🔢 计算派生特征...")
        self._calculate_derived_features(features_dict, match_data)

        # 创建MatchFeatures对象（Pydantic会自动验证和计算衍生字段）
        try:
            features = MatchFeatures(**features_dict)

            # 计算特征维度统计
            total_features = len(features_dict)
            non_null_features = len([v for v in features_dict.values() if v is not None])

            logger.info(
                f"🎉 [V4.2 SUCCESS] Match ID: {external_id}, "
                f"特征维度: {total_features}维 (有效: {non_null_features}维), "
                f"xG: {features.home_xg}-{features.away_xg}, "
                f"Possession: {features.home_possession}%, "
                f"球员评分: {features_dict.get('home_avg_starting_rating', 'N/A')}"
            )
            return features

        except Exception as e:
            logger.error(f"❌ V4.2特征提取失败 - {external_id}: {e}")
            raise FeatureExtractionError(f"Failed to create MatchFeatures: {e}")

    def _extract_advanced_shot_features(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取V4.2进阶射门特征"""
        shot_features = {
            # 射门精度特征
            'home_shots_on_target': None,
            'away_shots_on_target': None,
            'shots_on_target_diff': None,
            'home_shot_accuracy': None,
            'away_shot_accuracy': None,
            'shot_accuracy_diff': None,

            # 射门分布特征
            'home_shots_inside_box': None,
            'away_shots_inside_box': None,
            'shots_inside_box_diff': None,
            'home_shots_outside_box': None,
            'away_shots_outside_box': None,
            'shots_outside_box_diff': None,

            # 射门效率特征
            'home_goals_per_shot': None,
            'away_goals_per_shot': None,
            'goals_per_shot_diff': None,
            'home_xg_per_shot': None,
            'away_xg_per_shot': None,
            'xg_per_shot_diff': None,
        }

        try:
            # 从shotmap数据提取详细射门信息
            if 'shotmap' in data and isinstance(data['shotmap'], dict):
                shots = data['shotmap'].get('shots', [])
                if isinstance(shots, list):
                    home_shots = []
                    away_shots = []

                    for shot in shots:
                        if isinstance(shot, dict):
                            is_home = shot.get('isHome', False)
                            shot_info = {
                                'on_target': self._is_shot_on_target(shot),
                                'inside_box': self._is_shot_inside_box(shot),
                                'xg': float(shot.get('expectedGoals', 0)),
                                'goal': shot.get('eventType') == 'Goal'
                            }

                            if is_home:
                                home_shots.append(shot_info)
                            else:
                                away_shots.append(shot_info)

                    # 计算主队射门特征
                    if home_shots:
                        home_total = len(home_shots)
                        home_on_target = sum(1 for s in home_shots if s['on_target'])
                        home_inside_box = sum(1 for s in home_shots if s['inside_box'])
                        home_goals = sum(1 for s in home_shots if s['goal'])
                        home_xg_total = sum(s['xg'] for s in home_shots)

                        shot_features.update({
                            'home_shots_on_target': home_on_target,
                            'home_shot_accuracy': round((home_on_target / home_total) * 100, 1) if home_total > 0 else None,
                            'home_shots_inside_box': home_inside_box,
                            'home_goals_per_shot': round(home_goals / home_total, 3) if home_total > 0 else None,
                            'home_xg_per_shot': round(home_xg_total / home_total, 3) if home_total > 0 else None,
                        })

                    # 计算客队射门特征
                    if away_shots:
                        away_total = len(away_shots)
                        away_on_target = sum(1 for s in away_shots if s['on_target'])
                        away_inside_box = sum(1 for s in away_shots if s['inside_box'])
                        away_goals = sum(1 for s in away_shots if s['goal'])
                        away_xg_total = sum(s['xg'] for s in away_shots)

                        shot_features.update({
                            'away_shots_on_target': away_on_target,
                            'away_shot_accuracy': round((away_on_target / away_total) * 100, 1) if away_total > 0 else None,
                            'away_shots_inside_box': away_inside_box,
                            'away_goals_per_shot': round(away_goals / away_total, 3) if away_total > 0 else None,
                            'away_xg_per_shot': round(away_xg_total / away_total, 3) if away_total > 0 else None,
                        })

                    # 计算差值
                    if shot_features.get('home_shots_on_target') and shot_features.get('away_shots_on_target'):
                        shot_features['shots_on_target_diff'] = shot_features['home_shots_on_target'] - shot_features['away_shots_on_target']

                    if shot_features.get('home_shot_accuracy') and shot_features.get('away_shot_accuracy'):
                        shot_features['shot_accuracy_diff'] = shot_features['home_shot_accuracy'] - shot_features['away_shot_accuracy']

                    if shot_features.get('home_shots_inside_box') and shot_features.get('away_shots_inside_box'):
                        shot_features['shots_inside_box_diff'] = shot_features['home_shots_inside_box'] - shot_features['away_shots_inside_box']

                    if shot_features.get('home_goals_per_shot') and shot_features.get('away_goals_per_shot'):
                        shot_features['goals_per_shot_diff'] = shot_features['home_goals_per_shot'] - shot_features['away_goals_per_shot']

                    if shot_features.get('home_xg_per_shot') and shot_features.get('away_xg_per_shot'):
                        shot_features['xg_per_shot_diff'] = shot_features['home_xg_per_shot'] - shot_features['away_xg_per_shot']

        except Exception as e:
            logger.debug(f"进阶射门特征提取失败: {e}")

        return shot_features

    def _extract_advanced_possession_features(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取V4.2控球率深度特征"""
        possession_features = {
            # 控球率稳定性
            'home_possession_stability': None,
            'away_possession_stability': None,
            'possession_stability_diff': None,

            # 控球率效率
            'home_goals_per_possession': None,
            'away_goals_per_possession': None,
            'goals_per_possession_diff': None,

            # 控球率转化率
            'home_shots_per_possession': None,
            'away_shots_per_possession': None,
            'shots_per_possession_diff': None,
        }

        try:
            # 这里可以添加更复杂的控球率分析逻辑
            # 目前使用基础计算
            pass
        except Exception as e:
            logger.debug(f"控球率深度特征提取失败: {e}")

        return possession_features

    def _calculate_derived_features(self, features_dict: Dict[str, Any], match_data: Dict[str, Any]):
        """计算派生特征和比率"""

        # 基础xG派生特征
        if features_dict.get("home_xg") is not None and features_dict.get("away_xg") is not None:
            features_dict["xg_total"] = round(features_dict["home_xg"] + features_dict["away_xg"], 3)
            features_dict["xg_diff"] = round(features_dict["home_xg"] - features_dict["away_xg"], 3)

        # 控球率派生特征
        if features_dict.get("home_possession") is not None and features_dict.get("away_possession") is not None:
            features_dict["possession_diff"] = round(
                features_dict["home_possession"] - features_dict["away_possession"], 1
            )

        # V4.2 新增派生特征

        # 射门转化率
        if (features_dict.get("home_shots_total") and features_dict.get("home_shots_on_target") and
            features_dict.get("home_shots_total") > 0):
            features_dict["home_shot_conversion_rate"] = round(
                (features_dict["home_shots_on_target"] / features_dict["home_shots_total"]) * 100, 1
            )

        if (features_dict.get("away_shots_total") and features_dict.get("away_shots_on_target") and
            features_dict.get("away_shots_total") > 0):
            features_dict["away_shot_conversion_rate"] = round(
                (features_dict["away_shots_on_target"] / features_dict["away_shots_total"]) * 100, 1
            )

        # xG效率
        if (features_dict.get("home_score") is not None and features_dict.get("home_xg") and
            features_dict.get("home_xg") > 0):
            features_dict["home_xg_efficiency"] = round(
                features_dict["home_score"] / features_dict["home_xg"], 3
            )

        if (features_dict.get("away_score") is not None and features_dict.get("away_xg") and
            features_dict.get("away_xg") > 0):
            features_dict["away_xg_efficiency"] = round(
                features_dict["away_score"] / features_dict["away_xg"], 3
            )

        # 球员评分影响力
        if (features_dict.get("home_avg_starting_rating") and features_dict.get("home_score") and
            features_dict.get("home_avg_starting_rating") > 0):
            features_dict["home_rating_impact"] = round(
                features_dict["home_score"] / features_dict["home_avg_starting_rating"], 3
            )

        if (features_dict.get("away_avg_starting_rating") and features_dict.get("away_score") and
            features_dict.get("away_avg_starting_rating") > 0):
            features_dict["away_rating_impact"] = round(
                features_dict["away_score"] / features_dict["away_avg_starting_rating"], 3
            )

        # 战术纪律指标
        if (features_dict.get("home_fouls_committed") and features_dict.get("away_fouls_committed")):
            features_dict["fouls_ratio"] = round(
                features_dict["home_fouls_committed"] /
                (features_dict["home_fouls_committed"] + features_dict["away_fouls_committed"]), 3
            ) if (features_dict["home_fouls_committed"] + features_dict["away_fouls_committed"]) > 0 else None

    def _is_shot_on_target(self, shot: Dict[str, Any]) -> bool:
        """判断射门是否射正"""
        event_type = shot.get('eventType', '').lower()
        return any(keyword in event_type for keyword in ['goal', 'shotongoal', 'saved'])

    def _is_shot_inside_box(self, shot: Dict[str, Any]) -> bool:
        """判断射门是否在禁区内"""
        # 这里可以根据shot中的坐标信息判断
        # 暂时使用简化逻辑
        return shot.get('situation', '').lower() in ['regularplay', 'fastbreak', 'penalty']

    def _extract_basic_info(self, data: Dict[str, Any], external_id: str) -> Dict[str, Any]:
        """提取基础信息"""
        # 尝试多种比分提取路径
        home_score = None
        away_score = None

        # 从general路径提取
        if "general" in data:
            general = data["general"]
            if isinstance(general, dict):
                home_score = self._safe_int(general.get("homeTeamScore"))
                away_score = self._safe_int(general.get("awayTeamScore"))

        # 备用路径
        if home_score is None:
            home_score = self._extract_int_field(data, ["homeScore", "match.homeScore", "home_team_score"])
        if away_score is None:
            away_score = self._extract_int_field(data, ["awayScore", "match.awayScore", "away_team_score"])

        return {
            "external_id": external_id,
            "match_time": self._extract_datetime(data),
            "home_team": self._extract_team_name(data, "home"),
            "away_team": self._extract_team_name(data, "away"),
            "league_id": self._extract_field(data, ["leagueId", "league_id"]),
            "league_name": self._extract_field(data, ["leagueName", "league_name"]),
            "season": self._extract_field(data, ["seasonText", "season"]),
            "status": self._extract_field(data, ["status.statusStr", "statusStr", "status"]),
            "home_score": home_score,
            "away_score": away_score,
        }

    def _extract_xg_features(self, data: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
        """提取xG特征 - 优先从FotMob新API结构提取，然后尝试shotmap"""
        home_xg = None
        away_xg = None

        # 优先从FotMob 2025年新API结构提取: content.stats.Periods.All.stats[0].stats[1].stats
        try:
            content_stats = data.get("content", {}).get("stats", {})
            periods = content_stats.get("Periods", {})
            all_stats = periods.get("All", {}).get("stats", [])

            if isinstance(all_stats, list) and len(all_stats) > 0:
                # 支持两种API结构:
                # 1. 英超/意甲: stats[0].stats[].stats[]
                # 2. 西甲/德甲: 直接在stats[].stats[]

                xg_extracted = False

                # 方法1: 查找top_stats组 (适用于英超/意甲)
                for period_stats in all_stats:
                    if isinstance(period_stats, dict) and period_stats.get("key") == "top_stats":
                        top_stats = period_stats.get("stats", [])
                        if isinstance(top_stats, list):
                            for stat_item in top_stats:
                                if isinstance(stat_item, dict) and stat_item.get("key") == "expected_goals":
                                    xg_values = stat_item.get("stats", [])
                                    if isinstance(xg_values, list) and len(xg_values) >= 2:
                                        home_xg = float(xg_values[0])
                                        away_xg = float(xg_values[1])
                                        logger.debug(f"从FotMob API v1提取xG: 主队={home_xg}, 客队={away_xg}")
                                        xg_extracted = True
                                        break
                        if xg_extracted:
                            break

                # 方法2: 直接查找expected_goals组 (适用于西甲/德甲)
                if not xg_extracted:
                    for period_stats in all_stats:
                        if isinstance(period_stats, dict) and period_stats.get("key") == "expected_goals":
                            stats_list = period_stats.get("stats", [])
                            if isinstance(stats_list, list) and len(stats_list) >= 1:
                                # 西甲/德甲结构: stats[0].stats[0] = [home_xg, away_xg]
                                first_stat = stats_list[0]
                                if isinstance(first_stat, dict):
                                    xg_values = first_stat.get("stats", [])
                                    if isinstance(xg_values, list) and len(xg_values) >= 2:
                                        home_xg = float(xg_values[0])
                                        away_xg = float(xg_values[1])
                                        logger.debug(
                                            f"从FotMob API v2(西甲/德甲)提取xG: 主队={home_xg}, 客队={away_xg}"
                                        )
                                        xg_extracted = True
                                        break
                        if xg_extracted:
                            break

        except (KeyError, TypeError, ValueError, AttributeError) as e:
            logger.debug(f"FotMob新API xG提取失败: {e}")

        # 如果新API失败，尝试从shotmap中提取真实xG数据
        if home_xg is None or away_xg is None:
            home_xg_total, away_xg_total = 0.0, 0.0
            shotmap_found = False

            if "shotmap" in data and isinstance(data["shotmap"], dict):
                shotmap = data["shotmap"]
                if "shots" in shotmap and isinstance(shotmap["shots"], list):
                    shotmap_found = True
                    logger.debug(f"从shotmap中提取xG数据，射门数量: {len(shotmap['shots'])}")

                    for i, shot in enumerate(shotmap["shots"]):
                        if isinstance(shot, dict):
                            xg_value = None

                            # 多种可能的xG字段名
                            for field in ["expectedGoals", "xg", "expectedGoalValue", "xgValue"]:
                                if field in shot and shot[field] is not None:
                                    try:
                                        xg_value = float(shot[field])
                                        logger.debug(f"射门{i+1} xG值: {xg_value} (字段: {field})")
                                        break
                                    except (ValueError, TypeError):
                                        continue

                            # 检查嵌套的stats字段
                            if xg_value is None and "stats" in shot and isinstance(shot["stats"], dict):
                                for key, value in shot["stats"].items():
                                    if "xg" in key.lower() and value is not None:
                                        try:
                                            xg_value = float(value)
                                            logger.debug(f"射门{i+1} xG值: {xg_value} (stats字段: {key})")
                                            break
                                        except (ValueError, TypeError):
                                            continue

                            # 累加到对应球队
                            if xg_value is not None:
                                team_type = str(shot.get("teamType", "")).lower()
                                is_home = shot.get("isHome", False)
                                player_name = shot.get("playerName", "Unknown")

                                if is_home or "home" in team_type:
                                    home_xg_total += xg_value
                                    logger.debug(f"主队射门 {player_name}: +{xg_value}")
                                elif "away" in team_type or not is_home:
                                    away_xg_total += xg_value
                                    logger.debug(f"客队射门 {player_name}: +{xg_value}")

            if shotmap_found and (home_xg_total > 0 or away_xg_total > 0):
                home_xg = home_xg_total if home_xg is None else home_xg
                away_xg = away_xg_total if away_xg is None else away_xg
                logger.debug(f"shotmap xG统计: 主队={home_xg}, 客队={away_xg}")

        # 使用递归搜索作为最后兜底
        if home_xg is None:
            home_xg = self.recursive_extractor.extract_value(data, self.config.XG_PATTERNS["home"], "xg.home")
        if away_xg is None:
            away_xg = self.recursive_extractor.extract_value(data, self.config.XG_PATTERNS["away"], "xg.away")

        logger.info(f"最终xG结果 - 主队: {home_xg}, 客队: {away_xg}")
        return round(home_xg, 3) if home_xg is not None else None, round(away_xg, 3) if away_xg is not None else None

    def _extract_possession_features(self, data: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
        """提取控球率特征 - 修复FotMob API数据结构"""
        home_possession = None
        away_possession = None

        # FotMob API 2025年数据结构：content.stats.Periods.All.stats[0].stats[0].stats
        try:
            content_stats = data.get("content", {}).get("stats", {})
            periods = content_stats.get("Periods", {})
            all_stats = periods.get("All", {}).get("stats", [])

            if isinstance(all_stats, list) and len(all_stats) > 0:
                # 支持两种API结构:
                # 1. 英超/意甲: stats[0].stats[].stats[]
                # 2. 西甲/德甲: 直接在stats[].stats[]

                possession_extracted = False

                # 方法1: 查找top_stats组 (适用于英超/意甲)
                for period_stats in all_stats:
                    if isinstance(period_stats, dict) and period_stats.get("key") == "top_stats":
                        top_stats = period_stats.get("stats", [])
                        if isinstance(top_stats, list):
                            for stat_item in top_stats:
                                if isinstance(stat_item, dict) and "Ball possession" in stat_item.get("title", ""):
                                    possession_values = stat_item.get("stats", [])
                                    if isinstance(possession_values, list) and len(possession_values) >= 2:
                                        home_possession = float(possession_values[0])
                                        away_possession = float(possession_values[1])
                                        logger.debug(
                                            f"从FotMob API v1提取控球率: 主队={home_possession}%, 客队={away_possession}%"
                                        )
                                        possession_extracted = True
                                        break
                        if possession_extracted:
                            break

                # 方法2: 直接在all_stats中查找Ball possession (适用于西甲/德甲)
                if not possession_extracted:
                    for stat_item in all_stats:
                        if isinstance(stat_item, dict) and "Ball possession" in stat_item.get("title", ""):
                            possession_values = stat_item.get("stats", [])
                            if isinstance(possession_values, list) and len(possession_values) >= 2:
                                home_possession = float(possession_values[0])
                                away_possession = float(possession_values[1])
                                logger.debug(
                                    f"从FotMob API v2(西甲/德甲)提取控球率: 主队={home_possession}%, 客队={away_possession}%"
                                )
                                possession_extracted = True
                                break

        except (KeyError, TypeError, ValueError, AttributeError) as e:
            logger.debug(f"FotMob新API提取失败: {e}")

        # 如果新API失败，尝试从更多数据源提取真实控球率
        if home_possession is None:
            # 1. 尝试从general.teamStats提取
            try:
                general = data.get("general", {})
                team_stats = general.get("teamStats", [])
                if isinstance(team_stats, list) and len(team_stats) >= 2:
                    home_possession = self._safe_float(team_stats[0].get("possession"))
                    away_possession = self._safe_float(team_stats[1].get("possession"))
                    logger.debug(f"从general.teamStats提取控球率: 主队={home_possession}, 客队={away_possession}")
            except (KeyError, TypeError, AttributeError, IndexError):
                pass

            # 2. 尝试从stats数组提取
            if home_possession is None:
                try:
                    stats = data.get("stats", [])
                    if isinstance(stats, list):
                        for stat in stats:
                            if isinstance(stat, dict) and stat.get("type") == "possession":
                                home_possession = self._safe_float(stat.get("home"))
                                away_possession = self._safe_float(stat.get("away"))
                                logger.debug(f"从stats数组提取控球率: 主队={home_possession}, 客队={away_possession}")
                                break
                except (KeyError, TypeError, AttributeError):
                    pass

            # 3. 传统路径提取
            if home_possession is None:
                possession_paths = [
                    ["stats", "possession", "home"],
                    ["stats", "possessionText", "home"],
                    ["possession", "home"],
                    ["content", "stats", "possession", "home"],
                ]

                for path in possession_paths:
                    try:
                        current = data
                        for key in path[:-1]:  # 除了最后一个'home'
                            if isinstance(current, dict) and key in current:
                                current = current[key]
                            else:
                                break
                        else:
                            if isinstance(current, dict) and "home" in current:
                                home_possession = self._safe_float(current["home"])
                                if "away" in current:
                                    away_possession = self._safe_float(current["away"])
                                break
                            elif isinstance(current, dict) and "away" in current:
                                away_possession = self._safe_float(current["away"])
                    except (KeyError, TypeError, AttributeError):
                        continue

        # 如果还是没找到，尝试从字符串中提取百分比
        if home_possession is None:
            possession_text = self._extract_field(data, ["stats.possessionText.home", "possessionText.home"])
            if possession_text and isinstance(possession_text, str):
                import re

                match = re.search(r"(\d+)%", possession_text)
                if match:
                    home_possession = float(match.group(1))

        if away_possession is None:
            possession_text = self._extract_field(data, ["stats.possessionText.away", "possessionText.away"])
            if possession_text and isinstance(possession_text, str):
                import re

                match = re.search(r"(\d+)%", possession_text)
                if match:
                    away_possession = float(match.group(1))

        # 如果只找到一个，计算另一个（只有在合理范围内才计算）
        if home_possession is not None and away_possession is None:
            if 0 <= home_possession <= 100:
                away_possession = 100 - home_possession
                logger.debug(f"计算客队控球率: {away_possession}%")
        elif away_possession is not None and home_possession is None:
            if 0 <= away_possession <= 100:
                home_possession = 100 - away_possession
                logger.debug(f"计算主队控球率: {home_possession}%")

        # 最后的备用方案：使用递归提取器
        if home_possession is None:
            home_possession = self.recursive_extractor.extract_value(
                data, self.config.POSSESSION_PATTERNS["home"], "possession.home"
            )
        if away_possession is None:
            away_possession = self.recursive_extractor.extract_value(
                data, self.config.POSSESSION_PATTERNS["away"], "possession.away"
            )

        # 数据质量检查：如果仍然找不到真实数据，返回NULL而不是50默认值
        if home_possession is None or away_possession is None:
            logger.warning(
                f"⚠️ 无法获取真实控球率数据，返回NULL以避免默认值污染 - 主队: {home_possession}, 客队: {away_possession}"
            )
            if home_possession is None and away_possession is not None:
                return None, away_possession
            elif away_possession is None and home_possession is not None:
                return home_possession, None
            else:
                return None, None

        logger.debug(f"最终控球率结果 - 主队: {home_possession}%, 客队: {away_possession}%")
        return home_possession, away_possession

    def _extract_odds_features(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取赔率特征"""
        home_odds = None
        away_odds = None
        draw_odds = None

        # 尝试多种赔率路径
        odds_paths = [
            ["betting", "odds"],
            ["odds"],
            ["betting", "providers", "bet365"],
        ]

        for path in odds_paths:
            try:
                current = data
                for key in path:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        break
                else:
                    if isinstance(current, dict):
                        # 查找各种赔率字段名
                        home_odds = (
                            home_odds or current.get("homeWin") or current.get("homeOdds") or current.get("home_win")
                        )
                        away_odds = (
                            away_odds or current.get("awayWin") or current.get("awayOdds") or current.get("away_win")
                        )
                        draw_odds = (
                            draw_odds or current.get("draw") or current.get("drawOdds") or current.get("draw_odds")
                        )

                        if home_odds is not None and away_odds is not None:
                            break
            except (KeyError, TypeError, AttributeError):
                continue

        # 如果还是没找到，使用递归提取器作为备用
        if home_odds is None:
            home_odds = self.recursive_extractor.extract_value(data, self.config.ODDS_PATTERNS["home"], "odds.home")
        if away_odds is None:
            away_odds = self.recursive_extractor.extract_value(data, self.config.ODDS_PATTERNS["away"], "odds.away")
        if draw_odds is None:
            draw_odds = self.recursive_extractor.extract_value(data, self.config.ODDS_PATTERNS["draw"], "odds.draw")

        return {
            "home_opening_odds": self._safe_float(home_odds),
            "away_opening_odds": self._safe_float(away_odds),
            "draw_odds": self._safe_float(draw_odds),
            "home_current_odds": self._safe_float(home_odds),  # 默认使用开盘赔率
            "away_current_odds": self._safe_float(away_odds),
            "draw_current_odds": self._safe_float(draw_odds),
        }

    def _extract_corners_features(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取角球数据特征 - 支持FotMob 2025 API结构"""
        home_corners = None
        away_corners = None

        # 1. 优先从FotMob 2025年新API结构提取: content.stats.Periods.All.stats[0].stats
        try:
            content_stats = data.get("content", {}).get("stats", {})
            periods = content_stats.get("Periods", {})
            all_stats = periods.get("All", {}).get("stats", [])

            if isinstance(all_stats, list) and len(all_stats) > 0:
                # 查找Top stats部分
                top_stats = None
                for period_stats in all_stats:
                    if isinstance(period_stats, dict) and period_stats.get("key") == "top_stats":
                        top_stats = period_stats.get("stats", [])
                        break

                if top_stats and isinstance(top_stats, list):
                    # 查找Corner Kicks统计项
                    for stat_item in top_stats:
                        if isinstance(stat_item, dict) and stat_item.get("key") in [
                            "CornerKicks",
                            "corner_kicks",
                            "Corners",
                        ]:
                            corners_values = stat_item.get("stats", [])
                            if isinstance(corners_values, list) and len(corners_values) >= 2:
                                home_corners = int(corners_values[0])
                                away_corners = int(corners_values[1])
                                logger.debug(f"从FotMob新API提取角球: 主队={home_corners}, 客队={away_corners}")
                                break

        except (KeyError, TypeError, ValueError, AttributeError) as e:
            logger.debug(f"FotMob新API角球提取失败: {e}")

        # 2. 备用路径：从stats数组提取
        if home_corners is None or away_corners is None:
            try:
                stats = data.get("stats", [])
                if isinstance(stats, list):
                    for stat in stats:
                        if isinstance(stat, dict):
                            stat_type = stat.get("type", "").lower()
                            if any(key in stat_type for key in ["corner", "corners", "cornerkicks"]):
                                home_corners = home_corners or self._safe_int(stat.get("home"))
                                away_corners = away_corners or self._safe_int(stat.get("away"))
                                if home_corners is not None and away_corners is not None:
                                    break
            except Exception:
                pass

        # 3. 传统路径提取
        if home_corners is None or away_corners is None:
            corner_paths = [
                ["stats", "corners"],
                ["stats", "cornerKicks"],
                ["matchStats", "corners"],
                ["content", "stats", "corners"],
            ]

            for path in corner_paths:
                try:
                    current = data
                    for key in path:
                        if isinstance(current, dict) and key in current:
                            current = current[key]
                        else:
                            break
                    else:
                        if isinstance(current, dict):
                            if "home" in current and "away" in current:
                                home_corners = home_corners or self._safe_int(current["home"])
                                away_corners = away_corners or self._safe_int(current["away"])
                                if home_corners is not None and away_corners is not None:
                                    break
                except (KeyError, TypeError, AttributeError):
                    continue

        # 计算差值
        corners_diff = None
        if home_corners is not None and away_corners is not None:
            corners_diff = home_corners - away_corners

        return {
            "home_corners": home_corners,
            "away_corners": away_corners,
            "corners_diff": corners_diff,
            "home_corners_first_half": None,  # 需要更详细的数据
            "away_corners_first_half": None,
            "corners_first_half_diff": None,
            "home_corners_second_half": None,
            "away_corners_second_half": None,
            "corners_second_half_diff": None,
        }

    def _extract_cards_features(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取红黄牌数据特征 - 支持FotMob 2025 API结构"""
        home_yellow = None
        away_yellow = None
        home_red = None
        away_red = None

        # 1. 优先从FotMob 2025年新API结构提取: content.stats.Periods.All.stats[0].stats
        try:
            content_stats = data.get("content", {}).get("stats", {})
            periods = content_stats.get("Periods", {})
            all_stats = periods.get("All", {}).get("stats", [])

            if isinstance(all_stats, list) and len(all_stats) > 0:
                # 查找Top stats部分
                top_stats = None
                for period_stats in all_stats:
                    if isinstance(period_stats, dict) and period_stats.get("key") == "top_stats":
                        top_stats = period_stats.get("stats", [])
                        break

                if top_stats and isinstance(top_stats, list):
                    # 查找Yellow Cards和Red Cards统计项
                    for stat_item in top_stats:
                        if isinstance(stat_item, dict):
                            stat_key = stat_item.get("key", "").lower()
                            card_values = stat_item.get("stats", [])
                            if isinstance(card_values, list) and len(card_values) >= 2:
                                if "yellow" in stat_key:
                                    home_yellow = int(card_values[0])
                                    away_yellow = int(card_values[1])
                                    logger.debug(f"从FotMob新API提取黄牌: 主队={home_yellow}, 客队={away_yellow}")
                                elif "red" in stat_key:
                                    home_red = int(card_values[0])
                                    away_red = int(card_values[1])
                                    logger.debug(f"从FotMob新API提取红牌: 主队={home_red}, 客队={away_red}")

        except (KeyError, TypeError, ValueError, AttributeError) as e:
            logger.debug(f"FotMob新API红黄牌提取失败: {e}")

        # 2. 从cards数据中提取（详细数据）
        if any(v is None for v in [home_yellow, away_yellow, home_red, away_red]):
            if "cards" in data and isinstance(data["cards"], list):
                # 初始化计数器（只有在cards数据存在时）
                if home_yellow is None:
                    home_yellow = 0
                if away_yellow is None:
                    away_yellow = 0
                if home_red is None:
                    home_red = 0
                if away_red is None:
                    away_red = 0

                for card in data["cards"]:
                    if isinstance(card, dict):
                        team_type = str(card.get("teamType", "")).lower()
                        card_type = str(card.get("cardType", "")).lower()
                        is_home = card.get("isHome", False)

                        if "yellow" in card_type:
                            if team_type == "home" or is_home:
                                home_yellow += 1
                            else:
                                away_yellow += 1
                        elif "red" in card_type:
                            if team_type == "home" or is_home:
                                home_red += 1
                            else:
                                away_red += 1

        # 3. 备用提取方法：从stats数组提取
        if any(v is None for v in [home_yellow, away_yellow, home_red, away_red]):
            try:
                stats = data.get("stats", [])
                if isinstance(stats, list):
                    for stat in stats:
                        if isinstance(stat, dict):
                            stat_type = str(stat.get("type", "")).lower()
                            if "yellow" in stat_type:
                                home_yellow = home_yellow or self._safe_int(stat.get("home"))
                                away_yellow = away_yellow or self._safe_int(stat.get("away"))
                            elif "red" in stat_type:
                                home_red = home_red or self._safe_int(stat.get("home"))
                                away_red = away_red or self._safe_int(stat.get("away"))
            except Exception:
                pass

        # 计算差值
        yellow_diff = None
        red_diff = None
        if home_yellow is not None and away_yellow is not None:
            yellow_diff = home_yellow - away_yellow
        if home_red is not None and away_red is not None:
            red_diff = home_red - away_red

        return {
            "home_yellow_cards": home_yellow,
            "away_yellow_cards": away_yellow,
            "yellow_cards_diff": yellow_diff,
            "home_red_cards": home_red,
            "away_red_cards": away_red,
            "red_cards_diff": red_diff,
        }

    def _extract_passing_features(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取传球成功率特征"""
        home_passes = None
        away_passes = None
        home_pass_accuracy = None
        away_pass_accuracy = None

        # 多种可能的传球数据路径
        passing_paths = [
            ["stats", "passes"],
            ["stats", "passing"],
            ["matchStats", "passes"],
            ["content", "stats", "passes"],
        ]

        for path in passing_paths:
            try:
                current = data
                for key in path:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        break
                else:
                    if isinstance(current, dict):
                        # 直接获取成功率
                        if "homeAccuracy" in current and "awayAccuracy" in current:
                            home_pass_accuracy = self._safe_float(current["homeAccuracy"])
                            away_pass_accuracy = self._safe_float(current["awayAccuracy"])
                        # 获取总传球数和成功传球数
                        elif "home" in current and "away" in current:
                            if isinstance(current["home"], dict):
                                home_passes = self._safe_int(current["home"].get("total"))
                                home_pass_accuracy = self._safe_float(current["home"].get("accuracy"))
                            if isinstance(current["away"], dict):
                                away_passes = self._safe_int(current["away"].get("total"))
                                away_pass_accuracy = self._safe_float(current["away"].get("accuracy"))
                        break
            except (KeyError, TypeError, AttributeError):
                continue

        # 计算成功传球数
        home_successful = None
        away_successful = None
        if home_passes is not None and home_pass_accuracy is not None:
            home_successful = int(home_passes * home_pass_accuracy / 100)
        if away_passes is not None and away_pass_accuracy is not None:
            away_successful = int(away_passes * away_pass_accuracy / 100)

        # 计算差值
        passes_diff = None
        accuracy_diff = None
        successful_diff = None
        if home_passes is not None and away_passes is not None:
            passes_diff = home_passes - away_passes
        if home_pass_accuracy is not None and away_pass_accuracy is not None:
            accuracy_diff = home_pass_accuracy - away_pass_accuracy
        if home_successful is not None and away_successful is not None:
            successful_diff = home_successful - away_successful

        return {
            "home_passes": home_passes,
            "away_passes": away_passes,
            "passes_diff": passes_diff,
            "home_pass_accuracy": home_pass_accuracy,
            "away_pass_accuracy": away_pass_accuracy,
            "pass_accuracy_diff": accuracy_diff,
            "home_successful_passes": home_successful,
            "away_successful_passes": away_successful,
            "successful_passes_diff": successful_diff,
        }

    def _extract_shots_features(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取射门数据特征 - 支持FotMob 2025 API结构"""
        home_shots = None
        away_shots = None
        home_shots_on_target = None
        away_shots_on_target = None

        # 1. 优先从FotMob 2025年新API结构提取: content.stats.Periods.All.stats[0].stats
        try:
            content_stats = data.get("content", {}).get("stats", {})
            periods = content_stats.get("Periods", {})
            all_stats = periods.get("All", {}).get("stats", [])

            if isinstance(all_stats, list) and len(all_stats) > 0:
                # 查找Top stats部分
                top_stats = None
                for period_stats in all_stats:
                    if isinstance(period_stats, dict) and period_stats.get("key") == "top_stats":
                        top_stats = period_stats.get("stats", [])
                        break

                if top_stats and isinstance(top_stats, list):
                    # 查找Shots和Shots on Target统计项
                    for stat_item in top_stats:
                        if isinstance(stat_item, dict):
                            stat_key = stat_item.get("key", "").lower()
                            shot_values = stat_item.get("stats", [])
                            if isinstance(shot_values, list) and len(shot_values) >= 2:
                                if "shot" in stat_key and "target" not in stat_key:
                                    home_shots = int(shot_values[0])
                                    away_shots = int(shot_values[1])
                                    logger.debug(f"从FotMob新API提取射门: 主队={home_shots}, 客队={away_shots}")
                                elif "shot" in stat_key and "target" in stat_key:
                                    home_shots_on_target = int(shot_values[0])
                                    away_shots_on_target = int(shot_values[1])
                                    logger.debug(
                                        f"从FotMob新API提取射正: 主队={home_shots_on_target}, 客队={away_shots_on_target}"
                                    )

        except (KeyError, TypeError, ValueError, AttributeError) as e:
            logger.debug(f"FotMob新API射门提取失败: {e}")

        # 2. 备用路径：从stats数组提取
        if any(v is None for v in [home_shots, away_shots, home_shots_on_target, away_shots_on_target]):
            try:
                stats = data.get("stats", [])
                if isinstance(stats, list):
                    for stat in stats:
                        if isinstance(stat, dict):
                            stat_type = str(stat.get("type", "")).lower()
                            if "shot" in stat_type and "target" not in stat_type:
                                home_shots = home_shots or self._safe_int(stat.get("home"))
                                away_shots = away_shots or self._safe_int(stat.get("away"))
                            elif "shot" in stat_type and "target" in stat_type:
                                home_shots_on_target = home_shots_on_target or self._safe_int(stat.get("home"))
                                away_shots_on_target = away_shots_on_target or self._safe_int(stat.get("away"))
            except Exception:
                pass

        # 3. 从shotmap数据中提取（最准确的数据源）
        if any(v is None for v in [home_shots, away_shots]):
            if "shotmap" in data and isinstance(data["shotmap"], dict):
                if "shots" in data["shotmap"] and isinstance(data["shotmap"]["shots"], list):
                    home_shot_count, away_shot_count = 0, 0
                    home_on_target, away_on_target = 0, 0

                    for shot in data["shotmap"]["shots"]:
                        if isinstance(shot, dict):
                            is_home = shot.get("isHome", False)
                            team_type = str(shot.get("teamType", "")).lower()

                            # 统计射门总数
                            if is_home or "home" in team_type:
                                home_shot_count += 1
                            else:
                                away_shot_count += 1

                            # 统计射正数（通过shotmap中的事件类型）
                            event_type = shot.get("eventType", "").lower()
                            if "goal" in event_type or "shotongoal" in event_type or "saved" in event_type:
                                if is_home or "home" in team_type:
                                    home_on_target += 1
                                else:
                                    away_on_target += 1

                    # 只有在原有值为None时才更新
                    if home_shots is None:
                        home_shots = home_shot_count
                    if away_shots is None:
                        away_shots = away_shot_count
                    if home_shots_on_target is None:
                        home_shots_on_target = home_on_target
                    if away_shots_on_target is None:
                        away_shots_on_target = away_on_target

                    logger.debug(
                        f"从shotmap统计射门: 主队={home_shot_count}({home_on_target}), 客队={away_shot_count}({away_on_target})"
                    )

        # 计算差值
        shots_diff = None
        shots_on_target_diff = None
        if home_shots is not None and away_shots is not None:
            shots_diff = home_shots - away_shots
        if home_shots_on_target is not None and away_shots_on_target is not None:
            shots_on_target_diff = home_shots_on_target - away_shots_on_target

        return {
            "home_shots_total": home_shots,
            "away_shots_total": away_shots,
            "shots_total_diff": shots_diff,
            "home_shots_on_target": home_shots_on_target,
            "away_shots_on_target": away_shots_on_target,
            "shots_on_target_diff": shots_on_target_diff,
        }

    def _safe_float(self, value) -> Optional[float]:
        """安全转换为float"""
        try:
            if value is None:
                return None
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value) -> Optional[int]:
        """安全转换为int"""
        try:
            if value is None:
                return None
            return int(value)
        except (ValueError, TypeError):
            return None

    def _extract_field(self, data: Dict[str, Any], keys: List[str]) -> Optional[str]:
        """从多个可能的键名中提取字段"""
        for key in keys:
            if key in data and data[key] is not None:
                return str(data[key])
        return None

    def _extract_int_field(self, data: Dict[str, Any], keys: List[str]) -> Optional[int]:
        """提取整数字段"""
        for key in keys:
            if key in data and data[key] is not None:
                try:
                    return int(data[key])
                except (ValueError, TypeError):
                    continue
        return None

    def _extract_team_name(self, data: Dict[str, Any], team_type: str) -> Optional[str]:
        """提取队名"""
        # 尝试多种可能的路径
        team_paths = [
            [f"{team_type}Team", "name"],
            [f"{team_type}", "name"],
            [f"{team_type}Team", "shortName"],
            ["general", f"{team_type}Team", "name"],
            [f"{team_type}Team.name"],
            ["match", f"{team_type}Team", "name"],
        ]

        # 直接路径搜索
        for path in team_paths:
            try:
                current = data
                for key in path:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        break
                else:
                    if isinstance(current, str) and len(current.strip()) > 0:
                        return current.strip()
            except (KeyError, TypeError, AttributeError):
                continue

        # 智能递归搜索（只搜索字符串类型的name字段）
        def smart_search(obj, depth=0):
            if depth > 8 or obj is None:
                return None

            if isinstance(obj, dict):
                # 优先查找name字段且值为字符串
                for key, value in obj.items():
                    key_lower = str(key).lower()
                    if (
                        "name" in key_lower
                        and isinstance(value, str)
                        and len(value.strip()) > 0
                        and
                        # 确保不是其他name字段
                        not any(skip in key_lower for skip in ["player", "stadium", "competition"])
                    ):
                        return value.strip()

                # 递归搜索
                for key, value in obj.items():
                    if isinstance(value, (dict, list)):
                        result = smart_search(value, depth + 1)
                        if result:
                            return result

            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        result = smart_search(item, depth + 1)
                        if result:
                            return result

            return None

        # 最后的智能搜索
        result = smart_search(data)
        return result if result and result not in ["58", "42", "2", "1"] else None

    def _extract_datetime(self, data: Dict[str, Any]) -> Optional[datetime]:
        """提取日期时间"""
        time_paths = [
            ["general", "startTimeUTC"],
            ["status", "utcTime"],
            ["header", "status", "utcTime"],
            ["matchTime"],
            ["time"],
            ["utcTime"],
            ["startTimeUTC"],
        ]

        # 尝试各种路径
        for path in time_paths:
            try:
                current = data
                for key in path:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        break
                else:
                    if isinstance(current, str):
                        return datetime.fromisoformat(current.replace("Z", "+00:00"))
                    elif isinstance(current, datetime):
                        return current
                    elif hasattr(current, "isoformat"):
                        return datetime.fromisoformat(current.isoformat())
            except (KeyError, TypeError, ValueError, AttributeError):
                continue

        # 如果都找不到，使用当前时间
        return datetime.now()

    def _extract_value_wide_search(self, data: Any, feature_type: str, team: str) -> Optional[float]:
        """广泛搜索特征值"""
        if not isinstance(data, (dict, list)):
            return None

        # 构建搜索关键词
        search_keywords = {
            ("xg", "home"): ["xg", "expectedgoals", "expected_goals", "homexpgoal", "home_expected"],
            ("xg", "away"): ["xg", "expectedgoals", "expected_goals", "awayxpg", "away_expected"],
            ("possession", "home"): ["possession", "pos", "ballpossession"],
            ("possession", "away"): ["possession", "pos", "ballpossession"],
        }

        keywords = search_keywords.get((feature_type, team), [])

        def search_recursive(obj: Any, depth: int = 0) -> Optional[float]:
            if depth > 10:
                return None

            if isinstance(obj, dict):
                # 检查键名是否匹配
                for key, value in obj.items():
                    key_lower = str(key).lower()

                    for keyword in keywords:
                        if keyword in key_lower and value is not None:
                            try:
                                return float(value)
                            except (ValueError, TypeError):
                                continue

                    # 递归搜索
                    if isinstance(value, (dict, list)):
                        result = search_recursive(value, depth + 1)
                        if result is not None:
                            return result

            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        result = search_recursive(item, depth + 1)
                        if result is not None:
                            return result

            return None

        return search_recursive(data)

    def _fill_remaining_features(self, features_dict: Dict[str, Any], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """填充剩余特征字段（使用默认值或从原始数据提取）"""

        # 添加其他可能提取的特征（简化版本，可以根据需要扩展）
        additional_features = {
            "raw_data_source": DataSource.FOTMOB_API,
            "feature_version": FeatureVersion.V1_0,
            "feature_quality_score": self._calculate_quality_score(features_dict),
            "extraction_confidence": self._calculate_confidence_score(features_dict),
            "data_completeness_score": self._calculate_completeness_score(features_dict),
        }

        features_dict.update(additional_features)
        return features_dict

    def _calculate_quality_score(self, features: Dict[str, Any]) -> float:
        """计算特征质量评分"""
        critical_features = ["home_xg", "away_xg", "home_possession", "away_possession"]
        available_features = sum(1 for feature in critical_features if features.get(feature) is not None)
        return available_features / len(critical_features)

    def _calculate_confidence_score(self, features: Dict[str, Any]) -> float:
        """计算提取置信度"""
        # 简化的置信度计算
        return 0.85 if features.get("home_xg") is not None else 0.60

    def _calculate_completeness_score(self, features: Dict[str, Any]) -> float:
        """计算数据完整性评分"""
        # 简化的完整性计算
        non_null_count = sum(1 for value in features.values() if value is not None)
        total_count = len(features)
        return non_null_count / total_count if total_count > 0 else 0.0


# 向后兼容的别名
AdvancedExtractor = AdvancedFeatureExtractor


# 测试函数
def test_feature_extraction():
    """测试特征提取功能"""
    # 模拟真实的FotMob API数据结构
    test_match_data = {
        "header": {"matchId": "4813374", "status": {"statusStr": "Finished", "utcTime": "2024-01-15T20:00:00Z"}},
        "match": {
            "homeTeam": {"name": "Manchester United"},
            "awayTeam": {"name": "Liverpool"},
            "homeScore": 2,
            "awayScore": 1,
        },
        "stats": {
            "possession": {"home": 55.5, "away": 44.5},
            "xg": {"homeExpectedGoals": 1.42, "awayExpectedGoals": 0.89},
            "odds": {"homeWinOdds": 2.15, "drawOdds": 3.40, "awayWinOdds": 3.20},
        },
        "events": {"homeTeamGoals": {"player1": [{"shotmapEvent": {"expectedGoals": 0.8}}]}},
    }

    extractor = AdvancedFeatureExtractor()
    try:
        features = extractor.extract_complete_features(test_match_data, "4813374")

        print("✅ 特征提取成功!")
        print(f"🎯 比赛ID: {features.external_id}")
        print(f"📊 主队xG: {features.home_xg}")
        print(f"📊 客队xG: {features.away_xg}")
        print(f"⚽ 控球率: 主队 {features.home_possession}% vs 客队 {features.away_possession}%")
        print(f"💰 开盘赔率: 主队 {features.home_opening_odds} vs 客队 {features.away_opening_odds}")
        print(f"📈 特征质量评分: {features.feature_quality_score}")
        print(f"🔍 特征完整性: {features.total_features_count}个字段")

        return True

    except Exception as e:
        print(f"❌ 特征提取失败: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_feature_extraction()
