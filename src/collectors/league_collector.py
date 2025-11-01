"""
联赛数据采集器
League Data Collector for Football-Data.org API
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .base_collector import FootballDataCollector

logger = logging.getLogger(__name__)


class LeagueCollector(FootballDataCollector):
    """联赛数据采集器"""

    def __init__(self):
        super().__init__()

    async def collect_data(self) -> Dict[str, Any]:
        """
        收集所有支持的联赛数据

        Returns:
            包含联赛数据的字典
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "leagues": {},
            "standings": {},
            "errors": [],
        }

        try:
            # 获取所有支持的联赛
            all_competitions = await self.fetch_competitions()
            supported_competitions = [
                comp
                for comp in all_competitions
                if comp.get("code") in self.supported_competitions
            ]

            # 收集每个联赛的数据
            for competition in supported_competitions:
                comp_code = competition["code"]
                comp_id = competition["id"]

                try:
                    logger.info(f"Collecting league data for: {comp_code}")

                    # 标准化联赛信息
                    normalized_league = self.normalize_league_data(competition)
                    results["leagues"][comp_code] = normalized_league

                    # 收集积分榜数据
                    try:
                        standings = await self.fetch_standings(str(comp_id))
                        normalized_standings = self.normalize_standings_data(
                            standings, competition
                        )
                        results["standings"][comp_code] = normalized_standings
                        logger.info(f"Collected standings for {comp_code}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to collect standings for {comp_code}: {e}"
                        )
                        results["standings"][comp_code] = []

                except Exception as e:
                    error_msg = f"Failed to collect league data for {comp_code}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    continue

        except Exception as e:
            error_msg = f"General league collection error: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        return results

    async def collect_league_details(self, competition_code: str) -> Dict[str, Any]:
        """
        收集特定联赛的完整数据

        Args:
            competition_code: 联赛代码 (如 PL, CL等)

        Returns:
            联赛完整数据
        """
        if competition_code not in self.supported_competitions:
            raise ValueError(f"Unsupported competition: {competition_code}")

        try:
            # 获取联赛信息
            all_competitions = await self.fetch_competitions()
            competition = next(
                (
                    comp
                    for comp in all_competitions
                    if comp.get("code") == competition_code
                ),
                None,
            )

            if not competition:
                raise ValueError(f"Competition {competition_code} not found")

            comp_id = str(competition["id"])

            # 收集积分榜
            standings = await self.fetch_standings(comp_id)
            normalized_standings = self.normalize_standings_data(standings, competition)

            # 收集当前轮次的比赛
            current_matchday = competition.get("currentMatchday")
            matches = []
            if current_matchday:
                matches = await self.fetch_matches(comp_id, matchday=current_matchday)

            result = {
                "league": self.normalize_league_data(competition),
                "standings": normalized_standings,
                "current_matches": matches,
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"Collected complete data for {competition_code}")
            return result

        except Exception as e:
            logger.error(
                f"Failed to collect league details for {competition_code}: {e}"
            )
            raise

    def normalize_league_data(self, competition: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化联赛数据格式

        Args:
            competition: 原始联赛数据

        Returns:
            标准化后的联赛数据
        """
        try:
            return {
                "external_id": str(competition.get("id")),
                "name": competition.get("name"),
                "code": competition.get("code"),
                "type": competition.get("type"),  # LEAGUE, CUP, etc.
                "emblem": competition.get("emblem"),
                "area": {
                    "id": competition.get("area", {}).get("id"),
                    "name": competition.get("area", {}).get("name"),
                    "code": competition.get("area", {}).get("code"),
                    "flag": competition.get("area", {}).get("flag"),
                },
                "season": self._normalize_season_data(competition.get("season", {})),
                "last_updated": competition.get("lastUpdated"),
            }

        except Exception as e:
            logger.error(f"Error normalizing league data: {e}")
            return {
                "external_id": str(competition.get("id", "")),
                "name": competition.get("name", "Unknown League"),
                "error": str(e),
                "raw_data": competition,
            }

    def _normalize_season_data(self, season: Dict[str, Any]) -> Dict[str, Any]:
        """标准化赛季数据"""
        if not season:
            return {}

        try:
            return {
                "id": season.get("id"),
                "start_date": season.get("startDate"),
                "end_date": season.get("endDate"),
                "current_matchday": season.get("currentMatchday"),
                "winner": season.get("winner"),
            }
        except Exception as e:
            logger.error(f"Error normalizing season data: {e}")
            return {}

    def normalize_standings_data(
        self, standings: List[Dict[str, Any]], competition: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        标准化积分榜数据格式

        Args:
            standings: 原始积分榜数据
            competition: 联赛信息

        Returns:
            标准化后的积分榜数据
        """
        normalized_standings = []

        try:
            if not standings:
                return normalized_standings

            for standing in standings:
                table = standing.get("table", [])
                group = standing.get("group", None)
                stage = standing.get("stage", None)
                table_type = standing.get("type", "TOTAL")

                for idx, team_standing in enumerate(table):
                    normalized_team = {
                        "position": idx + 1,
                        "team": {
                            "id": team_standing.get("team", {}).get("id"),
                            "name": team_standing.get("team", {}).get("name"),
                            "short_name": team_standing.get("team", {}).get(
                                "shortName"
                            ),
                            "crest": team_standing.get("team", {}).get("crest"),
                            "tla": team_standing.get("team", {}).get("tla"),
                        },
                        "played_games": team_standing.get("playedGames", 0),
                        "form": team_standing.get("form", None),
                        "won": team_standing.get("won", 0),
                        "draw": team_standing.get("draw", 0),
                        "lost": team_standing.get("lost", 0),
                        "points": team_standing.get("points", 0),
                        "goals_for": team_standing.get("goalsFor", 0),
                        "goals_against": team_standing.get("goalsAgainst", 0),
                        "goal_difference": team_standing.get("goalDifference", 0),
                        "competition": {
                            "id": competition.get("id"),
                            "name": competition.get("name"),
                            "code": competition.get("code"),
                        },
                        "group": group,
                        "stage": stage,
                        "table_type": table_type,
                    }
                    normalized_standings.append(normalized_team)

        except Exception as e:
            logger.error(f"Error normalizing standings data: {e}")

        return normalized_standings

    async def collect_league_statistics(self, competition_code: str) -> Dict[str, Any]:
        """
        收集联赛统计数据

        Args:
            competition_code: 联赛代码

        Returns:
            联赛统计数据
        """
        try:
            league_details = await self.collect_league_details(competition_code)
            standings = league_details.get("standings", [])

            if not standings:
                return {}

            # 计算统计数据
            total_teams = len(standings)
            total_games_played = sum(team["played_games"] for team in standings)
            total_goals_for = sum(team["goals_for"] for team in standings)
            total_goals_against = sum(team["goals_against"] for team in standings)
            total_points = sum(team["points"] for team in standings)

            stats = {
                "competition": league_details.get("league"),
                "statistics": {
                    "total_teams": total_teams,
                    "total_games_played": total_games_played,
                    "total_goals_for": total_goals_for,
                    "total_goals_against": total_goals_against,
                    "total_goals": total_goals_for + total_goals_against,
                    "average_goals_per_game": round(
                        (total_goals_for + total_goals_against)
                        / max(total_games_played, 1),
                        2,
                    ),
                    "average_points_per_game": round(
                        total_points / max(total_games_played, 1), 2
                    ),
                    "highest_points": max(team["points"] for team in standings)
                    if standings
                    else 0,
                    "lowest_points": min(team["points"] for team in standings)
                    if standings
                    else 0,
                },
                "top_scorers": standings[:5],  # 积分榜前5名
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(f"Collected statistics for {competition_code}")
            return stats

        except Exception as e:
            logger.error(
                f"Failed to collect league statistics for {competition_code}: {e}"
            )
            return {}

    async def collect_top_teams(
        self, competition_code: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        收集联赛排名靠前的球队

        Args:
            competition_code: 联赛代码
            limit: 限制数量

        Returns:
            球队列表
        """
        try:
            league_details = await self.collect_league_details(competition_code)
            standings = league_details.get("standings", [])

            # 按积分排序并返回前N名
            top_teams = sorted(standings, key=lambda x: x["points"], reverse=True)[
                :limit
            ]

            logger.info(f"Collected top {len(top_teams)} teams for {competition_code}")
            return top_teams

        except Exception as e:
            logger.error(f"Failed to collect top teams for {competition_code}: {e}")
            return []

    async def collect_league_matches_by_round(
        self, competition_code: str, matchday: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        收集特定轮次的比赛

        Args:
            competition_code: 联赛代码
            matchday: 轮次（可选，默认当前轮次）

        Returns:
            比赛数据
        """
        try:
            # 获取联赛信息
            all_competitions = await self.fetch_competitions()
            competition = next(
                (
                    comp
                    for comp in all_competitions
                    if comp.get("code") == competition_code
                ),
                None,
            )

            if not competition:
                raise ValueError(f"Competition {competition_code} not found")

            comp_id = str(competition["id"])

            # 如果没有指定轮次，使用当前轮次
            if matchday is None:
                matchday = competition.get("currentMatchday")

            if not matchday:
                raise ValueError(
                    f"No matchday specified and no current matchday found for {competition_code}"
                )

            # 获取比赛数据
            matches = await self.fetch_matches(comp_id, matchday=matchday)

            result = {
                "competition": self.normalize_league_data(competition),
                "matchday": matchday,
                "matches": matches,
                "total_matches": len(matches),
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(
                f"Collected {len(matches)} matches for {competition_code} matchday {matchday}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Failed to collect league matches by round for {competition_code}: {e}"
            )
            return {}

    async def search_competitions(self, search_term: str) -> List[Dict[str, Any]]:
        """
        搜索联赛

        Args:
            search_term: 搜索关键词

        Returns:
            匹配的联赛列表
        """
        try:
            all_competitions = await self.fetch_competitions()
            search_term_lower = search_term.lower()
            matching_competitions = []

            for competition in all_competitions:
                name = competition.get("name", "").lower()
                code = competition.get("code", "").lower()

                if (
                    search_term_lower in name
                    or search_term_lower in code
                    or competition.get("id") == search_term
                ):
                    normalized_league = self.normalize_league_data(competition)
                    if normalized_league and "error" not in normalized_league:
                        matching_competitions.append(normalized_league)

            logger.info(
                f"Found {len(matching_competitions)} competitions matching '{search_term}'"
            )
            return matching_competitions

        except Exception as e:
            logger.error(f"Failed to search competitions: {e}")
            return []

    async def get_available_seasons(self, competition_code: str) -> List[int]:
        """
        获取联赛可用的赛季

        Args:
            competition_code: 联赛代码

        Returns:
            赛季列表
        """
        try:
            # Football-Data.org API 主要返回当前赛季数据
            # 这里返回一些常见的过去赛季
            current_year = datetime.now().year
            seasons = []

            # 返回最近5个赛季
            for year in range(current_year - 4, current_year + 1):
                # 足球赛季通常是跨年的，例如 2024-25 赛季
                if year < current_year:
                    seasons.append(year)
                else:
                    seasons.append(year)

            logger.info(f"Available seasons for {competition_code}: {seasons}")
            return seasons

        except Exception as e:
            logger.error(f"Failed to get available seasons for {competition_code}: {e}")
            return []
