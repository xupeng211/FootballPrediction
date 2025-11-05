"""
Football-Data.org API数据采集器
提供完整的足球数据采集功能
"""

import logging
import os
from datetime import datetime, timedelta
from urllib.parse import urljoin

from .base_collector import BaseCollector, CollectionResult, CollectorError

logger = logging.getLogger(__name__)


class FootballDataCollector(BaseCollector):
    """Football-Data.org 数据采集器"""

    def __init__(
        self,
    api_key: str | None = None,
    base_url: str = "https://api.football-data.org/v4",
    **kwargs,

    ):
        # 从环境变量获取API密钥，如果未提供则使用默认值
        api_key = api_key or os.getenv("FOOTBALL_DATA_API_KEY",
    "")
        if not api_key:
            raise CollectorError("Football-Data.org API key is required")

        # Football-Data.org的免费限制是10请求/分钟
        kwargs.setdefault("rate_limit",
    10)
        super().__init__(api_key,
    base_url,
    **kwargs)

        # 支持的联赛代码
        self.supported_competitions = [
            "PL",  # Premier League
            "CL",  # Champions League
            "BL",  # Bundesliga
            "SA",  # Serie A
            "PD",  # La Liga
            "FL1",  # Ligue 1
            "ELC",  # Championship
            "EC",  # European Championship
            "WC",  # World Cup
        ]

    async def _get_headers(self) -> dict[str, str]:
        """获取Football-Data.org API请求头"""
        return {
            "X-Auth-Token": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _build_url(self,
    endpoint: str,
    **params) -> str:
        """构建请求URL"""
        # 移除开头的斜杠并确保正确的路径
        endpoint = endpoint.lstrip("/")
        return urljoin(self.base_url + "/",
    endpoint)

    async def collect_matches(
        self,

        league_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> CollectionResult:
        """采集比赛数据"""
        try:
            if league_id:
                # 获取特定联赛的比赛
                endpoint = f"competitions/{league_id}/matches"
                params = {"limit": limit}

                if date_from:
                    params["dateFrom"] = date_from.strftime("%Y-%m-%d")
                if date_to:
                    params["dateTo"] = date_to.strftime("%Y-%m-%d")
                if status:
                    params["status"] = status
            else:
                # 获取所有比赛（默认限制数量）
                endpoint = "matches"
                params = {"limit": limit}

            result = await self.get(endpoint, params=params)

            if result.success and result.data:
                # 提取比赛数据
                matches = result.data.get("matches", [])
                logger.info(f"Successfully collected {len(matches)} matches")

                return CollectionResult(
                    success=True,
                    data={"matches": matches, "count": len(matches), "filters": params},
                    response_time=result.response_time,
                )
            else:
                return result

        except Exception as e:
            logger.error(f"Error collecting matches: {e}")
            return CollectionResult(
                success=False, error=f"Failed to collect matches: {str(e)}"
            )

    async def collect_teams(
        self, league_id: int | None = None, limit: int = 100
    ) -> CollectionResult:
        """采集球队数据"""
        try:
            if league_id:
                # 获取特定联赛的球队
                endpoint = f"competitions/{league_id}/teams"
                params = {"limit": limit}
            else:
                # 获取所有球队（不推荐，数据量太大）
                endpoint = "teams"
                params = {"limit": limit}

            result = await self.get(endpoint, params=params)

            if result.success and result.data:
                teams = result.data.get("teams", [])
                logger.info(f"Successfully collected {len(teams)} teams")

                return CollectionResult(
                    success=True,
                    data={"teams": teams, "count": len(teams), "league_id": league_id},
                    response_time=result.response_time,
                )
            else:
                return result

        except Exception as e:
            logger.error(f"Error collecting teams: {e}")
            return CollectionResult(
                success=False, error=f"Failed to collect teams: {str(e)}"
            )

    async def collect_players(
        self, team_id: int | None = None, limit: int = 50
    ) -> CollectionResult:
        """采集球员数据"""
        try:
            if not team_id:
                return CollectionResult(
                    success=False, error="Team ID is required for player collection"
                )

            endpoint = f"teams/{team_id}"
            result = await self.get(endpoint)

            if result.success and result.data:
                # Football-Data.org球员数据在team信息中的squad字段
                squad = result.data.get("squad", [])
                logger.info(
                    f"Successfully collected {len(squad)} players for team {team_id}"
                )

                return CollectionResult(
                    success=True,
                    data={
                        "players": squad,
                        "count": len(squad),
                        "team_id": team_id,
                        "team_info": {
                            "id": result.data.get("id"),
    "name": result.data.get("name"),
    "crest": result.data.get("crest"),
    },

                    },
                    response_time=result.response_time,
                )
            else:
                return result

        except Exception as e:
            logger.error(f"Error collecting players: {e}")
            return CollectionResult(
                success=False, error=f"Failed to collect players: {str(e)}"
            )

    async def collect_leagues(self, areas: list[int] | None = None) -> CollectionResult:
        """采集联赛数据"""
        try:
            endpoint = "competitions"
            params = {}

            if areas:
                params["areas"] = ",".join(map(str, areas))

            result = await self.get(endpoint, params=params)

            if result.success and result.data:
                competitions = result.data.get("competitions", [])

                # 过滤支持的联赛
                if self.supported_competitions:
                    supported_competitions = [
                        comp
                        for comp in competitions
                        if comp.get("code") in self.supported_competitions
                    ]
                else:
                    supported_competitions = competitions

                logger.info(
                    f"Successfully collected {len(supported_competitions)} competitions"
                )

                return CollectionResult(
                    success=True,
                    data={
                        "competitions": supported_competitions,
                        "count": len(supported_competitions),
    "total_available": len(competitions),
    "supported_codes": self.supported_competitions,
    },

                    response_time=result.response_time,
                )
            else:
                return result

        except Exception as e:
            logger.error(f"Error collecting leagues: {e}")
            return CollectionResult(
                success=False, error=f"Failed to collect leagues: {str(e)}"
            )

    async def collect_standings(self, league_id: int) -> CollectionResult:
        """采集联赛积分榜"""
        try:
            endpoint = f"competitions/{league_id}/standings"
            result = await self.get(endpoint)

            if result.success and result.data:
                standings = result.data.get("standings", [])
                logger.info(f"Successfully collected standings for league {league_id}")

                return CollectionResult(
                    success=True,
                    data={
                        "standings": standings,
                        "league_id": league_id,
                        "count": len(standings),
                    },
                    response_time=result.response_time,
                )
            else:
                return result

        except Exception as e:
            logger.error(f"Error collecting standings: {e}")
            return CollectionResult(
                success=False, error=f"Failed to collect standings: {str(e)}"
            )

    async def collect_comprehensive_data(
        self,
    competition_codes: list[str] | None = None,
    days_back: int = 30,
    days_forward: int = 7,

    ) -> CollectionResult:
        """
        采集全面的足球数据

        Args:
            competition_codes: 联赛代码列表，如None则使用默认支持的联赛
            days_back: 向前获取多少天的比赛数据
            days_forward: 向前获取多少天的未来比赛
        """
        try:
            if not competition_codes:
                competition_codes = self.supported_competitions[:5]  # 限制前5个联赛

            # 计算日期范围
            date_from = datetime.now() - timedelta(days=days_back)
            date_to = datetime.now() + timedelta(days=days_forward)

            comprehensive_data = {
                "collection_timestamp": datetime.now().isoformat(),
                "date_range": {
                    "from": date_from.strftime("%Y-%m-%d"),
                    "to": date_to.strftime("%Y-%m-%d"),
                },
                "competitions": {},
                "errors": [],
                "stats": {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                },
            }

            # 首先获取所有联赛信息
            leagues_result = await self.collect_leagues()
            if not leagues_result.success:
                return CollectionResult(
                    success=False,
                    error=f"Failed to collect leagues: {leagues_result.error}",
                )

            all_competitions = leagues_result.data["competitions"]

            # 过滤出需要的联赛
            target_competitions = [
                comp
                for comp in all_competitions
                if comp.get("code") in competition_codes
            ]

            logger.info(f"Collecting data for {len(target_competitions)} competitions")

            # 为每个联赛采集数据
            for competition in target_competitions:
                comp_id = competition["id"]
                comp_code = competition.get("code", "UNKNOWN")

                try:
                    logger.info(f"Collecting data for competition: {comp_code}")

                    comp_data = {
                        "info": competition,
                        "teams": None,
                        "matches_finished": None,
                        "matches_scheduled": None,
                        "standings": None,
                    }

                    # 采集球队数据
                    teams_result = await self.collect_teams(comp_id)
                    comp_data["teams"] = (
                        teams_result.data if teams_result.success else None
                    )
                    comprehensive_data["stats"]["total_requests"] += 1
                    if teams_result.success:
                        comprehensive_data["stats"]["successful_requests"] += 1
                    else:
                        comprehensive_data["stats"]["failed_requests"] += 1
                        comprehensive_data["errors"].append(
                            f"Teams for {comp_code}: {teams_result.error}"
                        )

                    # 采集已结束的比赛
                    matches_finished_result = await self.collect_matches(
                        comp_id, date_from=date_from, date_to=date_to, status="FINISHED"
                    )
                    comp_data["matches_finished"] = (
                        matches_finished_result.data
                        if matches_finished_result.success
                        else None
                    )
                    comprehensive_data["stats"]["total_requests"] += 1
                    if matches_finished_result.success:
                        comprehensive_data["stats"]["successful_requests"] += 1
                    else:
                        comprehensive_data["stats"]["failed_requests"] += 1
                        comprehensive_data["errors"].append(
                            f"Finished matches for {comp_code}: {matches_finished_result.error}"
                        )

                    # 采集即将开始的比赛
                    matches_scheduled_result = await self.collect_matches(
                        comp_id,
    date_from=datetime.now(),
    date_to=date_to,
    status="SCHEDULED",

                    )
                    comp_data["matches_scheduled"] = (
                        matches_scheduled_result.data
                        if matches_scheduled_result.success
                        else None
                    )
                    comprehensive_data["stats"]["total_requests"] += 1
                    if matches_scheduled_result.success:
                        comprehensive_data["stats"]["successful_requests"] += 1
                    else:
                        comprehensive_data["stats"]["failed_requests"] += 1
                        comprehensive_data["errors"].append(
                            f"Scheduled matches for {comp_code}: {matches_scheduled_result.error}"
                        )

                    # 采集积分榜
                    standings_result = await self.collect_standings(comp_id)
                    comp_data["standings"] = (
                        standings_result.data if standings_result.success else None
                    )
                    comprehensive_data["stats"]["total_requests"] += 1
                    if standings_result.success:
                        comprehensive_data["stats"]["successful_requests"] += 1
                    else:
                        comprehensive_data["stats"]["failed_requests"] += 1
                        comprehensive_data["errors"].append(
                            f"Standings for {comp_code}: {standings_result.error}"
                        )

                    comprehensive_data["competitions"][comp_code] = comp_data
                    logger.info(f"Successfully collected data for {comp_code}")

                except Exception as e:
                    error_msg = (
                        f"Failed to collect comprehensive data for {comp_code}: {e}"
                    )
                    logger.error(error_msg)
                    comprehensive_data["errors"].append(error_msg)
                    comprehensive_data["stats"]["failed_requests"] += 1

            # 计算总体统计
            total_teams = sum(
                len(comp.get("teams", {}).get("teams", []))
                for comp in comprehensive_data["competitions"].values()
                if comp.get("teams")
            )

            total_matches_finished = sum(
                len(comp.get("matches_finished", {}).get("matches", []))
                for comp in comprehensive_data["competitions"].values()
                if comp.get("matches_finished")
            )

            total_matches_scheduled = sum(
                len(comp.get("matches_scheduled", {}).get("matches", []))
                for comp in comprehensive_data["competitions"].values()
                if comp.get("matches_scheduled")
            )

            comprehensive_data["stats"].update(
                {
                    "total_competitions": len(target_competitions),
    "total_teams": total_teams,
    "total_matches_finished": total_matches_finished,
    "total_matches_scheduled": total_matches_scheduled,

                    "total_matches": total_matches_finished + total_matches_scheduled,
                    "success_rate": (
                        comprehensive_data["stats"]["successful_requests"]
                        / max(comprehensive_data["stats"]["total_requests"], 1)
                    )
                    * 100,
                }
            )

            logger.info(
                f"Comprehensive data collection completed. "
                f"Competitions: {len(target_competitions)}, "
                f"Teams: {total_teams}, "
                f"Matches: {total_matches_finished + total_matches_scheduled}"
            )

            return CollectionResult(
                success=True,
                data=comprehensive_data,
                response_time=0,  # 这个是多步骤操作，不计算单次响应时间
            )

        except Exception as e:
            logger.error(f"Error in comprehensive data collection: {e}")
            return CollectionResult(
                success=False, error=f"Failed to collect comprehensive data: {str(e)}"
            )

    async def health_check(self) -> bool:
        """健康检查 - 尝试获取联赛列表"""
        try:
            result = await self.collect_leagues()
            return result.success
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_supported_competitions(self) -> list[str]:
        """获取支持的联赛代码列表"""
        return self.supported_competitions.copy()

    async def get_competition_id_by_code(self, code: str) -> int | None:
        """根据联赛代码获取联赛ID"""
        try:
            result = await self.collect_leagues()
            if result.success and result.data:
                competitions = result.data.get("competitions", [])
                for comp in competitions:
                    if comp.get("code") == code:
                        return comp.get("id")
            return None
        except Exception as e:
            logger.error(f"Error getting competition ID for {code}: {e}")
            return None
