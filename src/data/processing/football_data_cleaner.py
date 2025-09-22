"""
足球数据清洗器

实现足球数据的清洗和标准化逻辑。
包含时间统一、球队ID映射、赔率校验、比分校验等功能。

清洗规则：
- 时间数据：统一转换为UTC时间
- 球队名称：映射到标准team_id
- 赔率数据：精度保持3位小数，异常值标记
- 比分数据：非负整数，上限99
- 联赛名称：标准化联赛代码

基于 DATA_DESIGN.md 第4.1节设计。
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.database.connection import DatabaseManager


class FootballDataCleaner:
    """
    足球数据清洗器

    负责清洗和标准化从外部API采集的原始足球数据，
    确保数据质量和一致性。
    """

    def __init__(self):
        """初始化数据清洗器"""
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(f"cleaner.{self.__class__.__name__}")

        # 球队ID映射缓存
        self._team_id_cache: Dict[str, int] = {}
        # 联赛ID映射缓存
        self._league_id_cache: Dict[str, int] = {}

    async def clean_match_data(
        self, raw_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        清洗比赛数据

        Args:
            raw_data: 原始比赛数据

        Returns:
            Optional[Dict]: 清洗后的数据，无效则返回None
        """
        try:
            if not self._validate_match_data(raw_data):
                return None

            cleaned_data = {
                # 基础信息
                "external_match_id": str(raw_data.get("id", "")),
                "external_league_id": str(
                    raw_data.get("competition", {}).get("id", "")
                ),
                # 时间统一 - 转换为UTC
                "match_time": self._to_utc_time(raw_data.get("utcDate")),
                # 球队ID统一 - 映射到标准ID
                "home_team_id": await self._map_team_id(raw_data.get("homeTeam", {})),
                "away_team_id": await self._map_team_id(raw_data.get("awayTeam", {})),
                # 联赛ID映射
                "league_id": await self._map_league_id(raw_data.get("competition", {})),
                # 比赛状态标准化
                "match_status": self._standardize_match_status(raw_data.get("status")),
                # 比分验证 - 范围检查
                "home_score": self._validate_score(
                    raw_data.get("score", {}).get("fullTime", {}).get("home")
                ),
                "away_score": self._validate_score(
                    raw_data.get("score", {}).get("fullTime", {}).get("away")
                ),
                "home_ht_score": self._validate_score(
                    raw_data.get("score", {}).get("halfTime", {}).get("home")
                ),
                "away_ht_score": self._validate_score(
                    raw_data.get("score", {}).get("halfTime", {}).get("away")
                ),
                # 其他信息
                "season": self._extract_season(raw_data.get("season", {})),
                "matchday": raw_data.get("matchday"),
                "venue": self._clean_venue_name(raw_data.get("venue")),
                "referee": self._clean_referee_name(raw_data.get("referees")),
                # 元数据
                "cleaned_at": datetime.now(timezone.utc).isoformat(),
                "data_source": "cleaned",
            }

            return cleaned_data

        except Exception as e:
            self.logger.error(f"Failed to clean match data: {str(e)}")
            return None

    async def clean_odds_data(
        self, raw_odds: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        清洗赔率数据

        Args:
            raw_odds: 原始赔率数据列表

        Returns:
            List[Dict]: 清洗后的赔率数据列表
        """
        cleaned_odds = []

        for odds in raw_odds:
            try:
                # 基础字段验证
                if not self._validate_odds_data(odds):
                    continue

                # 提取和验证赔率值
                outcomes = odds.get("outcomes", [])
                cleaned_outcomes = []

                for outcome in outcomes:
                    price = outcome.get("price")
                    if price and self._validate_odds_value(price):
                        cleaned_outcomes.append(
                            {
                                "name": self._standardize_outcome_name(
                                    outcome.get("name")
                                ),
                                "price": round(float(price), 3),  # 保留3位小数
                            }
                        )

                if not cleaned_outcomes:
                    continue

                # 赔率合理性检查
                if not self._validate_odds_consistency(cleaned_outcomes):
                    self.logger.warning(
                        f"Inconsistent odds detected: {cleaned_outcomes}"
                    )
                    continue

                cleaned_data = {
                    "external_match_id": str(odds.get("match_id", "")),
                    "bookmaker": self._standardize_bookmaker_name(
                        odds.get("bookmaker")
                    ),
                    "market_type": self._standardize_market_type(
                        odds.get("market_type")
                    ),
                    "outcomes": cleaned_outcomes,
                    "last_update": self._to_utc_time(odds.get("last_update")),
                    "implied_probabilities": self._calculate_implied_probabilities(
                        cleaned_outcomes
                    ),
                    "cleaned_at": datetime.now(timezone.utc).isoformat(),
                    "data_source": "cleaned",
                }

                cleaned_odds.append(cleaned_data)

            except Exception as e:
                self.logger.error(f"Failed to clean odds data: {str(e)}")
                continue

        return cleaned_odds

    def _validate_match_data(self, raw_data: Dict[str, Any]) -> bool:
        """验证比赛数据的基础字段"""
        required_fields = ["id", "homeTeam", "awayTeam", "utcDate"]
        return all(field in raw_data for field in required_fields)

    def _validate_odds_data(self, raw_odds: Dict[str, Any]) -> bool:
        """验证赔率数据的基础字段"""
        required_fields = ["match_id", "bookmaker", "market_type", "outcomes"]
        return all(field in raw_odds for field in required_fields)

    def _to_utc_time(self, time_str: Optional[str]) -> Optional[str]:
        """
        时间统一转换为UTC

        Args:
            time_str: 时间字符串

        Returns:
            Optional[str]: UTC时间字符串，无效则返回None
        """
        if not time_str:
            return None

        try:
            # 处理不同的时间格式
            if time_str.endswith("Z"):
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            elif "+" in time_str or time_str.endswith("UTC"):
                dt = datetime.fromisoformat(time_str.replace("UTC", "+00:00"))
            else:
                # 假设是UTC时间
                dt = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc).isoformat()

        except (ValueError, TypeError) as e:
            self.logger.warning(f"Invalid time format: {time_str}, error: {str(e)}")
            return None

    async def _map_team_id(self, team_data: Dict[str, Any]) -> Optional[int]:
        """
        球队ID映射到标准ID

        Args:
            team_data: 球队数据

        Returns:
            Optional[int]: 标准球队ID，未找到则返回None
        """
        if not team_data:
            return None

        external_id = str(team_data.get("id", ""))
        team_name = team_data.get("name", "")

        # 检查缓存
        cache_key = f"{external_id}:{team_name}"
        if cache_key in self._team_id_cache:
            return self._team_id_cache[cache_key]

        try:
            # TODO: 从数据库查询或创建球队记录
            # 这里需要实现球队映射逻辑
            # 暂时返回外部ID的哈希值作为占位符
            team_id = hash(cache_key) % 100000
            self._team_id_cache[cache_key] = team_id
            return team_id

        except Exception as e:
            self.logger.error(f"Failed to map team ID for {team_data}: {str(e)}")
            return None

    async def _map_league_id(self, league_data: Dict[str, Any]) -> Optional[int]:
        """
        联赛ID映射到标准ID

        Args:
            league_data: 联赛数据

        Returns:
            Optional[int]: 标准联赛ID，未找到则返回None
        """
        if not league_data:
            return None

        external_id = str(league_data.get("id", ""))
        league_name = league_data.get("name", "")

        # 检查缓存
        cache_key = f"{external_id}:{league_name}"
        if cache_key in self._league_id_cache:
            return self._league_id_cache[cache_key]

        try:
            # TODO: 从数据库查询或创建联赛记录
            # 这里需要实现联赛映射逻辑
            # 暂时返回外部ID的哈希值作为占位符
            league_id = hash(cache_key) % 1000
            self._league_id_cache[cache_key] = league_id
            return league_id

        except Exception as e:
            self.logger.error(f"Failed to map league ID for {league_data}: {str(e)}")
            return None

    def _standardize_match_status(self, status: Optional[str]) -> str:
        """标准化比赛状态"""
        if not status:
            return "unknown"

        status_mapping = {
            "SCHEDULED": "scheduled",
            "TIMED": "scheduled",
            "IN_PLAY": "live",
            "PAUSED": "live",
            "FINISHED": "finished",
            "AWARDED": "finished",
            "POSTPONED": "postponed",
            "CANCELLED": "cancelled",
            "SUSPENDED": "suspended",
        }

        return status_mapping.get(status.upper(), "unknown")

    def _validate_score(self, score: Any) -> Optional[int]:
        """
        验证比分数据

        Args:
            score: 比分值

        Returns:
            Optional[int]: 有效的比分，无效则返回None
        """
        if score is None:
            return None

        try:
            score_int = int(score)
            # 比分必须是非负整数，上限99
            if 0 <= score_int <= 99:
                return score_int
            else:
                self.logger.warning(f"Score out of range: {score}")
                return None
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid score format: {score}")
            return None

    def _extract_season(self, season_data: Dict[str, Any]) -> Optional[str]:
        """提取赛季信息"""
        if not season_data:
            return None

        # 尝试不同的赛季格式
        season_id = season_data.get("id")
        if season_id:
            return str(season_id)

        # 从开始和结束年份构建赛季
        start_date = season_data.get("startDate")
        end_date = season_data.get("endDate")
        if start_date and end_date:
            try:
                start_year = datetime.fromisoformat(
                    start_date.replace("Z", "+00:00")
                ).year
                end_year = datetime.fromisoformat(end_date.replace("Z", "+00:00")).year
                return f"{start_year}-{end_year}"
            except ValueError:
                pass

        return None

    def _clean_venue_name(self, venue: Optional[str]) -> Optional[str]:
        """清洗场地名称"""
        if not venue:
            return None

        # 移除多余空格和特殊字符
        cleaned = re.sub(r"\s+", " ", str(venue).strip())
        return cleaned if cleaned else None

    def _clean_referee_name(
        self, referees: Optional[List[Dict[str, Any]]]
    ) -> Optional[str]:
        """清洗裁判姓名"""
        if not referees or not isinstance(referees, list):
            return None

        # 查找主裁判
        for referee in referees:
            if referee.get("role") == "REFEREE":
                name = referee.get("name")
                if name:
                    return re.sub(r"\s+", " ", str(name).strip())

        return None

    def _validate_odds_value(self, price: Any) -> bool:
        """验证赔率值"""
        try:
            odds_value = float(price)
            # 赔率必须大于1.01
            return odds_value >= 1.01
        except (ValueError, TypeError):
            return False

    def _standardize_outcome_name(self, name: Optional[str]) -> str:
        """标准化结果名称"""
        if not name:
            return "unknown"

        name_mapping = {
            "1": "home",
            "X": "draw",
            "2": "away",
            "HOME": "home",
            "DRAW": "draw",
            "AWAY": "away",
            "Over": "over",
            "Under": "under",
        }

        return name_mapping.get(str(name).strip(), str(name).lower())

    def _standardize_bookmaker_name(self, bookmaker: Optional[str]) -> str:
        """标准化博彩公司名称"""
        if not bookmaker:
            return "unknown"

        # 移除空格并转换为小写
        return re.sub(r"\s+", "_", str(bookmaker).strip().lower())

    def _standardize_market_type(self, market_type: Optional[str]) -> str:
        """标准化市场类型"""
        if not market_type:
            return "unknown"

        market_mapping = {
            "h2h": "1x2",
            "spreads": "asian_handicap",
            "totals": "over_under",
            "btts": "both_teams_score",
        }

        return market_mapping.get(str(market_type).lower(), str(market_type).lower())

    def _validate_odds_consistency(self, outcomes: List[Dict[str, Any]]) -> bool:
        """
        验证赔率合理性

        Args:
            outcomes: 赔率结果列表

        Returns:
            bool: 赔率是否合理
        """
        try:
            if not outcomes:
                return False

            # 计算总概率
            total_prob = sum(1.0 / outcome["price"] for outcome in outcomes)

            # 总概率应该在95%-120%之间（考虑博彩公司抽水）
            return 0.95 <= total_prob <= 1.20

        except (KeyError, ZeroDivisionError, TypeError):
            return False

    def _calculate_implied_probabilities(
        self, outcomes: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        计算隐含概率

        Args:
            outcomes: 赔率结果列表

        Returns:
            Dict[str, float]: 隐含概率字典
        """
        try:
            probabilities = {}
            total_prob = 0.0

            # 计算原始概率
            for outcome in outcomes:
                name = outcome["name"]
                price = outcome["price"]
                prob = 1.0 / price
                probabilities[name] = prob
                total_prob += prob

            # 标准化概率（去除博彩公司利润边际）
            if total_prob > 0:
                for name in probabilities:
                    probabilities[name] = probabilities[name] / total_prob

            return probabilities

        except (KeyError, ZeroDivisionError, TypeError):
            return {}
