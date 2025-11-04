"""
比赛数据采集器
专门负责采集和管理比赛相关数据
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from .base_collector import BaseCollector, CollectionResult

logger = logging.getLogger(__name__)


class MatchCollector(BaseCollector):
    """比赛数据采集器"""

    def __init__(
        self,
    api_key: str | None = None,
    base_url: str | None = None,
    **kwargs
    ):
        # 从环境变量获取默认值
        api_key = api_key or os.getenv("FOOTBALL_DATA_API_KEY",
    "")
        base_url = base_url or os.getenv(
            "FOOTBALL_DATA_BASE_URL", "https://api.football-data.org/v4"
        )

        if not api_key:
            raise ValueError("API key is required for MatchCollector")

        super().__init__(api_key, base_url, **kwargs)

        self.match_status_mapping = {
            "SCHEDULED": "scheduled",
            "TIMED": "scheduled",
            "POSTPONED": "postponed",
            "CANCELLED": "cancelled",
            "FINISHED": "finished",
            "LIVE": "live",
            "IN_PLAY": "live",
            "PAUSED": "paused",
            "AWARDED": "finished",
        }

    async def _get_headers(self) -> dict[str, str]:
        """获取请求头"""
        return {"X-Auth-Token": self.api_key, "Content-Type": "application/json"}

    def _build_url(self, endpoint: str, **params) -> str:
        """构建请求URL"""
        from urllib.parse import urljoin

        # 移除开头的斜杠
        endpoint = endpoint.lstrip("/")

        if params:
            query_string = "&".join(
                [f"{k}={v}" for k, v in params.items() if v is not None]
            )
            return urljoin(self.base_url + "/", f"{endpoint}?{query_string}")
        return urljoin(self.base_url + "/",
    endpoint)

    async def collect_matches(
        self,
    league_id: int | None = None,
    date_from: datetime | None = None,
    
        date_to: datetime | None = None,
        status: str | None = None,
    ) -> CollectionResult:
        """采集比赛数据"""
        try:
            if league_id:
                endpoint = f"competitions/{league_id}/matches"
            else:
                endpoint = "matches"

            params = {}
            if date_from:
                params["dateFrom"] = date_from.strftime("%Y-%m-%d")
            if date_to:
                params["dateTo"] = date_to.strftime("%Y-%m-%d")
            if status:
                params["status"] = status

            result = await self.get(endpoint, params=params)

            if result.success:
                matches = result.data.get("matches", [])
                return CollectionResult(
                    success=True,
                    data={"matches": matches, "count": len(matches)},
                    response_time=result.response_time,
                )
            else:
                return result

        except Exception as e:
            logger.error(f"Error collecting matches: {e}")
            return CollectionResult(
                success=False, error=f"Failed to collect matches: {str(e)}"
            )

    async def collect_teams(self,
    league_id: int | None = None) -> CollectionResult:
        """采集球队数据 - MatchCollector不实现此功能"""
        return CollectionResult(
            success=False,
    error="MatchCollector does not support team collection"
        )

    async def collect_players(self,
    team_id: int | None = None) -> CollectionResult:
        """采集球员数据 - MatchCollector不实现此功能"""
        return CollectionResult(
            success=False,
    error="MatchCollector does not support player collection"
        )

    async def collect_leagues(self) -> CollectionResult:
        """采集联赛数据 - MatchCollector不实现此功能"""
        return CollectionResult(
            success=False, error="MatchCollector does not support league collection"
        )

    # 兼容性方法 - 保持向后兼容
    async def fetch_competitions(self) -> list[dict[str, Any]]:
        """获取所有可用的比赛"""
        try:
            result = await self.get("competitions")
            if result.success:
                return result.data.get("competitions", [])
            return []
        except Exception as e:
            logger.error(f"Failed to fetch competitions: {e}")
            return []

    async def fetch_teams(self, competition_id: str) -> list[dict[str, Any]]:
        """获取指定比赛的球队列表"""
        try:
            result = await self.get(f"competitions/{competition_id}/teams")
            if result.success:
                return result.data.get("teams", [])
            return []
        except Exception as e:
            logger.error(f"Failed to fetch teams for competition {competition_id}: {e}")
            return []

    async def fetch_matches(
        self, competition_id: str, **kwargs
    ) -> list[dict[str, Any]]:
        """获取比赛数据"""
        try:
            result = await self.get(
                f"competitions/{competition_id}/matches", params=kwargs
            )
            if result.success:
                return result.data.get("matches", [])
            return []
        except Exception as e:
            logger.error(
                f"Failed to fetch matches for competition {competition_id}: {e}"
            )
            return []

    async def collect_upcoming_matches(
        self,
    days_ahead: int = 7
    ) -> list[dict[str,
    Any]]:
        """
        收集未来指定天数内的比赛

        Args:
            days_ahead: 未来天数

        Returns:
            即将开始的比赛列表
        """
        upcoming_matches = []

        try:
            # 计算日期范围
            today = datetime.utcnow().date()
            end_date = today + timedelta(days=days_ahead)

            all_competitions = await self.fetch_competitions()
            supported_competitions = [
                comp
                for comp in all_competitions
                if comp.get("code") in self.supported_competitions
            ]

            for competition in supported_competitions:
                comp_id = competition["id"]
                comp_code = competition["code"]

                try:
                    matches = await self.fetch_matches(
                        str(comp_id),
    dateFrom=today.isoformat(),
    
                        dateTo=end_date.isoformat(),
                    )

                    # 过滤出即将开始的比赛
                    for match in matches:
                        if match.get("status") in ["SCHEDULED", "TIMED"]:
                            match["competition_info"] = {
                                "id": competition["id"],
                                "name": competition["name"],
                                "code": competition["code"],
                                "emblem": competition.get("emblem"),
                            }
                            upcoming_matches.append(match)

                except Exception as e:
                    logger.error(
                        f"Failed to collect upcoming matches for {comp_code}: {e}"
                    )
                    continue

        except Exception as e:
            logger.error(f"Failed to collect upcoming matches: {e}")

        # 按比赛时间排序
        upcoming_matches.sort(key=lambda x: x.get("utcDate",
    ""))

        return upcoming_matches

    async def collect_recent_matches(self,
    days_back: int = 7) -> list[dict[str,
    Any]]:
        """
        收集过去指定天数内的比赛结果

        Args:
            days_back: 过去天数

        Returns:
            已结束的比赛列表
        """
        recent_matches = []

        try:
            # 计算日期范围
            today = datetime.utcnow().date()
            start_date = today - timedelta(days=days_back)

            all_competitions = await self.fetch_competitions()
            supported_competitions = [
                comp
                for comp in all_competitions
                if comp.get("code") in self.supported_competitions
            ]

            for competition in supported_competitions:
                comp_id = competition["id"]
                comp_code = competition["code"]

                try:
                    matches = await self.fetch_matches(
                        str(comp_id),
    
                        dateFrom=start_date.isoformat(),
                        dateTo=today.isoformat(),
                    )

                    # 过滤出已结束的比赛
                    for match in matches:
                        if match.get("status") == "FINISHED":
                            match["competition_info"] = {
                                "id": competition["id"],
                                "name": competition["name"],
                                "code": competition["code"],
                                "emblem": competition.get("emblem"),
                            }
                            recent_matches.append(match)

                except Exception as e:
                    logger.error(
                        f"Failed to collect recent matches for {comp_code}: {e}"
                    )
                    continue

        except Exception as e:
            logger.error(f"Failed to collect recent matches: {e}")

        # 按比赛时间排序（最新的在前）
        recent_matches.sort(key=lambda x: x.get("utcDate",
    ""),
    reverse=True)

        return recent_matches

    def normalize_match_data(self,
    match: dict[str,
    Any]) -> dict[str,
    Any]:
        """
        标准化比赛数据格式

        Args:
            match: 原始比赛数据

        Returns:
            标准化后的比赛数据
        """
        try:
            # 获取基本信息
            home_team = match.get("homeTeam", {})
            away_team = match.get("awayTeam", {})
            score = match.get("score", {})
            competition = match.get("competition", {})

            # 解析比赛时间
            utc_date = match.get("utcDate", "")
            match_date = None
            if utc_date:
                try:
                    match_date = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
                except ValueError:
                    match_date = None

            # 获取比分
            full_time_score = score.get("fullTime", {})
            home_score = full_time_score.get("home") or 0
            away_score = full_time_score.get("away") or 0

            # 标准化状态
            original_status = match.get("status", "")
            normalized_status = self.match_status_mapping.get(
                original_status, original_status.lower()
            )

            # 判断比赛结果
            winner = score.get("winner")
            if winner == "HOME_TEAM":
                result = "home_win"
            elif winner == "AWAY_TEAM":
                result = "away_win"
            elif winner == "DRAW":
                result = "draw"
            else:
                result = None

            return {
                "external_id": str(match.get("id")),
    "competition_id": competition.get("id"),
    "competition_name": competition.get("name"),
    "competition_code": competition.get("code"),
    
                "match_date": match_date,
                "status": normalized_status,
                "home_team_id": home_team.get("id"),
    "home_team_name": home_team.get("name"),
    "home_team_short_name": home_team.get("shortName"),
    "home_team_crest": home_team.get("crest"),
    
                "away_team_id": away_team.get("id"),
    "away_team_name": away_team.get("name"),
    "away_team_short_name": away_team.get("shortName"),
    "away_team_crest": away_team.get("crest"),
    
                "home_score": home_score,
                "away_score": away_score,
                "result": result,
                "matchday": match.get("matchday"),
    "stage": match.get("stage"),
    "venue": None,
    # API中不包含venue信息
                "last_updated": match.get("lastUpdated"),
    
            }

        except Exception as e:
            logger.error(f"Error normalizing match data: {e}")
            return {
                "external_id": str(match.get("id",
    "")),
    "error": str(e),
    "raw_data": match,
    
            }

    async def collect_normalized_matches(
        self,
    match_type: str = "all"
    ) -> list[dict[str,
    Any]]:
        """
        收集并标准化比赛数据

        Args:
            match_type: 比赛类型 ('upcoming',
    'recent',
    'all')

        Returns:
            标准化的比赛数据列表
        """
        all_matches = []

        if match_type in ["upcoming", "all"]:
            upcoming_matches = await self.collect_upcoming_matches()
            normalized_upcoming = [
                self.normalize_match_data(match) for match in upcoming_matches
            ]
            all_matches.extend(normalized_upcoming)

        if match_type in ["recent", "all"]:
            recent_matches = await self.collect_recent_matches()
            normalized_recent = [
                self.normalize_match_data(match) for match in recent_matches
            ]
            all_matches.extend(normalized_recent)

        # 过滤掉标准化失败的数据
        valid_matches = [match for match in all_matches if "error" not in match]

        logger.info(
                        f"Collected and normalized {len(valid_matches)} matches (type: {match_type})"
        )

        return valid_matches
