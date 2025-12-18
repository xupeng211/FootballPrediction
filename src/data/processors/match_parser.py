"""
Match Parser - Silver Layer Data Processor
比赛数据解析器 - 将原始JSON转换为结构化特征

Medallion Architecture:
- Bronze: 原始JSON数据存储
- Silver: 清洗和结构化的数据 (本文件)
- Gold: 聚合和特征工程数据

Principal Data Engineer: 首席数据工程师
Purpose: 容错的JSON解析，防止数据质量问题导致系统崩溃
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MatchParser:
    """
    比赛数据解析器

    核心功能：
    - 容错解析FotMob API返回的JSON数据
    - 提取关键统计信息
    - 处理缺失和异常数据
    - 扁平化嵌套JSON结构
    """

    def __init__(self):
        """初始化解析器"""
        self.default_values = {
            "possession": 50.0,  # 默认50%控球率
            "shots": 0,
            "shots_on_target": 0,
            "corners": 0,
            "fouls": 0,
            "offsides": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "rating": 6.5,  # 默认球员评分
            "value_millions": 0.0,  # 默认身价（百万欧元）
        }

    def safe_get(self, data: dict[str, Any], key: str, default: Any = None) -> Any:
        """安全获取字典值，支持嵌套键路径"""
        if not data or not isinstance(data, dict):
            return default

        keys = key.split(".")
        current = data

        try:
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return default
            return current
        except (TypeError, KeyError, AttributeError):
            return default

    def parse_stats(self, stats_json: [dict, str, None]) -> dict[str, float]:
        """
        解析比赛统计数据

        Args:
            stats_json: JSON字符串或字典格式的比赛统计

        Returns:
            包含扁平化统计数据的字典
        """
        if not stats_json:
            return self._get_default_stats()

        # 如果是字符串，尝试解析为JSON
        if isinstance(stats_json, str):
            try:
                stats_data = json.loads(stats_json)
            except json.JSONDecodeError as e:
                logger.warning(f"stats JSON解析失败: {e}")
                return self._get_default_stats()
        elif isinstance(stats_json, dict):
            stats_data = stats_json
        else:
            logger.warning(f"stats_json类型不支持: {type(stats_json)}")
            return self._get_default_stats()

        # 提取主队和客队统计
        result = {}

        # 主队统计
        home_stats = self.safe_get(stats_data, "home", {})
        result.update(
            {
                "home_possession": self.safe_get(
                    home_stats, "possession", self.default_values["possession"]
                ),
                "home_shots": self.safe_get(
                    home_stats, "shots", self.default_values["shots"]
                ),
                "home_shots_on_target": self.safe_get(
                    home_stats,
                    "shots_on_target",
                    self.default_values["shots_on_target"],
                ),
                "home_corners": self.safe_get(
                    home_stats, "corners", self.default_values["corners"]
                ),
                "home_fouls": self.safe_get(
                    home_stats, "fouls", self.default_values["fouls"]
                ),
                "home_offsides": self.safe_get(
                    home_stats, "offsides", self.default_values["offsides"]
                ),
                "home_yellow_cards": self.safe_get(
                    home_stats, "yellow_cards", self.default_values["yellow_cards"]
                ),
                "home_red_cards": self.safe_get(
                    home_stats, "red_cards", self.default_values["red_cards"]
                ),
            }
        )

        # 客队统计
        away_stats = self.safe_get(stats_data, "away", {})
        result.update(
            {
                "away_possession": self.safe_get(
                    away_stats, "possession", self.default_values["possession"]
                ),
                "away_shots": self.safe_get(
                    away_stats, "shots", self.default_values["shots"]
                ),
                "away_shots_on_target": self.safe_get(
                    away_stats,
                    "shots_on_target",
                    self.default_values["shots_on_target"],
                ),
                "away_corners": self.safe_get(
                    away_stats, "corners", self.default_values["corners"]
                ),
                "away_fouls": self.safe_get(
                    away_stats, "fouls", self.default_values["fouls"]
                ),
                "away_offsides": self.safe_get(
                    away_stats, "offsides", self.default_values["offsides"]
                ),
                "away_yellow_cards": self.safe_get(
                    away_stats, "yellow_cards", self.default_values["yellow_cards"]
                ),
                "away_red_cards": self.safe_get(
                    away_stats, "red_cards", self.default_values["red_cards"]
                ),
            }
        )

        # 计算差异统计
        result.update(
            {
                "possession_diff": result["home_possession"]
                - result["away_possession"],
                "shots_diff": result["home_shots"] - result["away_shots"],
                "shots_on_target_diff": result["home_shots_on_target"]
                - result["away_shots_on_target"],
                "corners_diff": result["home_corners"] - result["away_corners"],
            }
        )

        # 确保所有值都是数值类型
        for key, value in result.items():
            try:
                result[key] = float(value) if value is not None else 0.0
            except ValueError:
                logger.warning(f"统计值转换失败 {key}: {value}")
                result[key] = 0.0

        return result

    def parse_lineups(self, lineups_json: [dict, str, None]) -> dict[str, float]:
        """
        解析阵容数据

        Args:
            lineups_json: JSON字符串或字典格式的阵容数据

        Returns:
            包含阵容特征的字典
        """
        if not lineups_json:
            return self._get_default_lineups()

        # 如果是字符串，尝试解析为JSON
        if isinstance(lineups_json, str):
            try:
                lineups_data = json.loads(lineups_json)
            except json.JSONDecodeError as e:
                logger.warning(f"lineups JSON解析失败: {e}")
                return self._get_default_lineups()
        elif isinstance(lineups_json, dict):
            lineups_data = lineups_json
        else:
            logger.warning(f"lineups_json类型不支持: {type(lineups_json)}")
            return self._get_default_lineups()

        result = {}

        # 解析主队阵容
        home_lineup = self.safe_get(lineups_data, "home", {})
        home_players = self.safe_get(home_lineup, "players", [])

        # 解析客队阵容
        away_lineup = self.safe_get(lineups_data, "away", {})
        away_players = self.safe_get(away_lineup, "players", [])

        # 计算阵容特征
        result.update(
            {
                "home_players_count": len(home_players),
                "away_players_count": len(away_players),
                "home_avg_rating": self._calculate_avg_rating(home_players),
                "away_avg_rating": self._calculate_avg_rating(away_players),
                "home_total_value": self._calculate_total_value(home_players),
                "away_total_value": self._calculate_total_value(away_players),
                "lineups_completeness": self._assess_lineup_completeness(
                    home_players, away_players
                ),
            }
        )

        # 确保所有值都是数值类型
        for key, value in result.items():
            try:
                result[key] = float(value) if value is not None else 0.0
            except ValueError:
                logger.warning(f"阵容值转换失败 {key}: {value}")
                result[key] = 0.0

        return result

    def parse_odds(self, odds_json: [dict, str, None]) -> dict[str, float]:
        """
        解析赔率数据

        Args:
            odds_json: JSON字符串或字典格式的赔率数据

        Returns:
            包含赔率特征的字典
        """
        if not odds_json:
            return self._get_default_odds()

        # 如果是字符串，尝试解析为JSON
        if isinstance(odds_json, str):
            try:
                odds_data = json.loads(odds_json)
            except json.JSONDecodeError as e:
                logger.warning(f"odds JSON解析失败: {e}")
                return self._get_default_odds()
        elif isinstance(odds_json, dict):
            odds_data = odds_json
        else:
            logger.warning(f"odds_json类型不支持: {type(odds_json)}")
            return self._get_default_odds()

        result = {}

        # 尝试提取主要博彩公司的赔率
        bookmakers = ["Bet365", "William Hill", "Pinnacle", "Betfair"]

        home_odds_list = []
        draw_odds_list = []
        away_odds_list = []

        for bookmaker in bookmakers:
            bm_odds = self.safe_get(odds_data, bookmaker, {})

            home_odds = self.safe_get(bm_odds, "home")
            draw_odds = self.safe_get(bm_odds, "draw")
            away_odds = self.safe_get(bm_odds, "away")

            if home_odds is not None:
                try:
                    home_odds_list.append(float(home_odds))
                except ValueError:
                    pass

            if draw_odds is not None:
                try:
                    draw_odds_list.append(float(draw_odds))
                except ValueError:
                    pass

            if away_odds is not None:
                try:
                    away_odds_list.append(float(away_odds))
                except ValueError:
                    pass

        # 计算平均赔率
        result.update(
            {
                "avg_home_odds": (
                    sum(home_odds_list) / len(home_odds_list) if home_odds_list else 2.5
                ),
                "avg_draw_odds": (
                    sum(draw_odds_list) / len(draw_odds_list) if draw_odds_list else 3.2
                ),
                "avg_away_odds": (
                    sum(away_odds_list) / len(away_odds_list) if away_odds_list else 2.8
                ),
                "odds_completeness": len(home_odds_list) / len(bookmakers),
            }
        )

        # 计算隐含概率
        total_home_prob = (
            sum(1 / odds for odds in home_odds_list) if home_odds_list else 0
        )
        total_draw_prob = (
            sum(1 / odds for odds in draw_odds_list) if draw_odds_list else 0
        )
        total_away_prob = (
            sum(1 / odds for odds in away_odds_list) if away_odds_list else 0
        )

        total_prob = total_home_prob + total_draw_prob + total_away_prob

        if total_prob > 0:
            result.update(
                {
                    "implied_home_prob": (total_home_prob / total_prob) * 100,
                    "implied_draw_prob": (total_draw_prob / total_prob) * 100,
                    "implied_away_prob": (total_away_prob / total_prob) * 100,
                }
            )
        else:
            result.update(
                {
                    "implied_home_prob": 33.33,
                    "implied_draw_prob": 33.33,
                    "implied_away_prob": 33.34,
                }
            )

        return result

    def parse_match(self, match_data: dict[str, Any]) -> dict[str, Any]:
        """
        解析完整比赛数据

        Args:
            match_data: 包含所有比赛数据的字典

        Returns:
            合并后的特征字典
        """
        try:
            result = {}

            # 解析统计数据
            stats = self.parse_stats(match_data.get("stats"))
            result.update({f"stat_{k}": v for k, v in stats.items()})

            # 解析阵容数据
            lineups = self.parse_lineups(match_data.get("lineups"))
            result.update({f"lineup_{k}": v for k, v in lineups.items()})

            # 解析赔率数据
            odds = self.parse_odds(match_data.get("odds"))
            result.update({f"odds_{k}": v for k, v in odds.items()})

            # 添加基础信息
            result.update(
                {
                    "match_id": match_data.get("id"),
                    "home_team_id": match_data.get("home_team_id"),
                    "away_team_id": match_data.get("away_team_id"),
                    "home_score": match_data.get("home_score", 0),
                    "away_score": match_data.get("away_score", 0),
                    "match_date": match_data.get("match_date"),
                    "data_source": match_data.get("data_source", "unknown"),
                    "data_completeness": match_data.get("data_completeness", "partial"),
                }
            )

            return result

        except Exception as e:
            logger.error(f"解析比赛数据失败: {e}")
            # 返回基础信息，确保不会完全失败
            return {
                "match_id": match_data.get("id"),
                "home_team_id": match_data.get("home_team_id"),
                "away_team_id": match_data.get("away_team_id"),
                "parse_error": str(e),
            }

    def _get_default_stats(self) -> dict[str, float]:
        """获取默认统计数据"""
        result = {}
        for prefix in ["home_", "away_"]:
            for key in [
                "possession",
                "shots",
                "shots_on_target",
                "corners",
                "fouls",
                "offsides",
                "yellow_cards",
                "red_cards",
            ]:
                result[f"{prefix}{key}"] = self.default_values.get(key, 0.0)

        # 添加差异统计
        for key in ["possession", "shots", "shots_on_target", "corners"]:
            result[f"{key}_diff"] = 0.0

        return result

    def _get_default_lineups(self) -> dict[str, float]:
        """获取默认阵容数据"""
        return {
            "home_players_count": 11.0,  # 标准首发
            "away_players_count": 11.0,
            "home_avg_rating": self.default_values["rating"],
            "away_avg_rating": self.default_values["rating"],
            "home_total_value": self.default_values["value_millions"],
            "away_total_value": self.default_values["value_millions"],
            "lineups_completeness": 0.5,  # 默认50%完整度
        }

    def _get_default_odds(self) -> dict[str, float]:
        """获取默认赔率数据"""
        return {
            "avg_home_odds": 2.5,
            "avg_draw_odds": 3.2,
            "avg_away_odds": 2.8,
            "odds_completeness": 0.0,
            "implied_home_prob": 33.33,
            "implied_draw_prob": 33.33,
            "implied_away_prob": 33.34,
        }

    def _calculate_avg_rating(self, players: list[dict[str, Any]]) -> float:
        """计算球员平均评分"""
        if not players:
            return self.default_values["rating"]

        ratings = []
        for player in players:
            rating = self.safe_get(player, "rating")
            if rating is not None:
                try:
                    ratings.append(float(rating))
                except ValueError:
                    continue

        return sum(ratings) / len(ratings) if ratings else self.default_values["rating"]

    def _calculate_total_value(self, players: list[dict[str, Any]]) -> float:
        """计算球队总身价（百万欧元）"""
        if not players:
            return self.default_values["value_millions"]

        total_value = 0.0
        for player in players:
            value = self.safe_get(player, "value")
            if value is not None:
                try:
                    # 处理不同格式的身价数据
                    if isinstance(value, str):
                        # 移除货币符号和单位
                        value = (
                            value.replace("€", "")
                            .replace("m", "")
                            .replace("M", "")
                            .replace("万", "")
                            .strip()
                        )
                    total_value += float(value)
                except ValueError:
                    continue

        return total_value

    def _assess_lineup_completeness(
        self, home_players: list[dict[str, Any]], away_players: list[dict[str, Any]]
    ) -> float:
        """评估阵容数据完整度"""
        home_completeness = min(len(home_players) / 11.0, 1.0) if home_players else 0.0
        away_completeness = min(len(away_players) / 11.0, 1.0) if away_players else 0.0

        return (home_completeness + away_completeness) / 2.0


# 创建全局解析器实例
match_parser = MatchParser()
