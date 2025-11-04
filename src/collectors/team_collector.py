"""
球队数据采集器
Team Data Collector for Football-Data.org API
"""

import logging
from datetime import datetime
from typing import Any

from .base_collector import FootballDataCollector

logger = logging.getLogger(__name__)


class TeamCollector(FootballDataCollector):
    """球队数据采集器"""

    def __init__(self):
        super().__init__()

    async def collect_data(self) -> dict[str, Any]:
        """
        收集所有支持的联赛中的球队数据

        Returns:
            包含球队数据的字典
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "teams": {},
            "competitions": [],
            "errors": [],
        }

        try:
            # 获取支持的联赛
            all_competitions = await self.fetch_competitions()
            supported_competitions = [
                comp
                for comp in all_competitions
                if comp.get("code") in self.supported_competitions
            ]
            results["competitions"] = supported_competitions

            # 收集各联赛的球队数据
            for competition in supported_competitions:
                comp_id = competition["id"]
                comp_code = competition["code"]

                try:
                    logger.info(f"Collecting teams for competition: {comp_code}")

                    teams = await self.fetch_teams(str(comp_id))

                    # 标准化球队数据
                    normalized_teams = []
                    for team in teams:
                        normalized_team = self.normalize_team_data(team)
                        if normalized_team and "error" not in normalized_team:
                            normalized_teams.append(normalized_team)

                    results["teams"][comp_code] = normalized_teams
                    logger.info(
                        f"Collected {len(normalized_teams)} teams for {comp_code}"
                    )

                except Exception as e:
                    error_msg = f"Failed to collect teams for {comp_code}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    continue

        except Exception as e:
            error_msg = f"General team collection error: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        return results

    async def collect_competition_teams(
        self, competition_code: str
    ) -> list[dict[str, Any]]:
        """
        收集特定联赛的球队数据

        Args:
            competition_code: 联赛代码 (如 PL, CL等)

        Returns:
            标准化的球队数据列表
        """
        if competition_code not in self.supported_competitions:
            raise ValueError(f"Unsupported competition: {competition_code}")

        # 获取联赛信息
        all_competitions = await self.fetch_competitions()
        competition = next(
            (comp for comp in all_competitions if comp.get("code") == competition_code),
            None,
        )

        if not competition:
            raise ValueError(f"Competition {competition_code} not found")

        comp_id = competition["id"]

        try:
            teams = await self.fetch_teams(str(comp_id))
            normalized_teams = []

            for team in teams:
                normalized_team = self.normalize_team_data(team)
                if normalized_team and "error" not in normalized_team:
                    normalized_team["competition_info"] = {
                        "id": competition["id"],
                        "name": competition["name"],
                        "code": competition["code"],
                    }
                    normalized_teams.append(normalized_team)

            logger.info(
                f"Collected {len(normalized_teams)} teams for {competition_code}"
            )
            return normalized_teams

        except Exception as e:
            logger.error(f"Failed to collect teams for {competition_code}: {e}")
            raise

    def normalize_team_data(self, team: dict[str, Any]) -> dict[str, Any]:
        """
        标准化球队数据格式

        Args:
            team: 原始球队数据

        Returns:
            标准化后的球队数据
        """
        try:
            return {
                "external_id": str(team.get("id")),
    "name": team.get("name"),
    "short_name": team.get("shortName"),
    "tla": team.get("tla"),
    # Three Letter Abbreviation
                "crest": team.get("crest"),
    "address": team.get("address"),
    "website": team.get("website"),
    "founded": team.get("founded"),
    
                "club_colors": team.get("clubColors"),
                "venue": team.get("venue"),
                "area": {
                    "id": team.get("area", {}).get("id"),
                    "name": team.get("area", {}).get("name"),
                    "code": team.get("area", {}).get("code"),
                    "flag": team.get("area", {}).get("flag"),
                },
                "coach": self._normalize_coach_data(team.get("coach", {})),
                "squad": self._normalize_squad_data(team.get("squad",
    [])),
    "running_competitions": self._normalize_competitions_data(
                    team.get("runningCompetitions",
    [])
                ),
    
                "last_updated": team.get("lastUpdated"),
                "staff": team.get("staff", []),
            }

        except Exception as e:
            logger.error(f"Error normalizing team data: {e}")
            return {
                "external_id": str(team.get("id", "")),
                "name": team.get("name", "Unknown Team"),
                "error": str(e),
    "raw_data": team,
    }

    def _normalize_coach_data(self,
    coach: dict[str,
    Any]) -> dict[str,
    Any] | None:
        """标准化教练数据"""
        if not coach:
            return None

        try:
            return {
                "id": coach.get("id"),
    "first_name": coach.get("firstName"),
    "last_name": coach.get("lastName"),
    "name": coach.get("name"),
    
                "date_of_birth": coach.get("dateOfBirth"),
                "nationality": coach.get("nationality"),
                "contract": coach.get("contract", {}),
            }
        except Exception as e:
            logger.error(f"Error normalizing coach data: {e}")
            return None

    def _normalize_squad_data(
        self, squad: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """标准化阵容数据"""
        normalized_squad = []

        for player in squad:
            try:
                normalized_player = {
                    "id": player.get("id"),
    "name": player.get("name"),
    "position": player.get("position"),
    "date_of_birth": player.get("dateOfBirth"),
    
                    "nationality": player.get("nationality"),
                    "shirt_number": None,  # API中不包含球衣号码
                    "contract_until": None,
                }
                normalized_squad.append(normalized_player)
            except Exception as e:
                logger.error(f"Error normalizing player data: {e}")
                continue

        return normalized_squad

    def _normalize_competitions_data(
        self, competitions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """标准化参赛联赛数据"""
        normalized_competitions = []

        for comp in competitions:
            try:
                normalized_comp = {
                    "id": comp.get("id"),
    "name": comp.get("name"),
    "code": comp.get("code"),
    "type": comp.get("type"),
    
                    "emblem": comp.get("emblem"),
                }
                normalized_competitions.append(normalized_comp)
            except Exception as e:
                logger.error(f"Error normalizing competition data: {e}")
                continue

        return normalized_competitions

    async def collect_team_details(self, team_id: str) -> dict[str, Any] | None:
        """
        收集特定球队的详细信息

        Args:
            team_id: 球队ID

        Returns:
            球队详细信息
        """
        try:
            # 获取球队基本信息
            # 注意：Football-Data.org API 没有直接的 /teams/{id} 端点
            # 我们需要从联赛的球队列表中找到该球队
            all_competitions = await self.fetch_competitions()
            supported_competitions = [
                comp
                for comp in all_competitions
                if comp.get("code") in self.supported_competitions
            ]

            for competition in supported_competitions:
                try:
                    teams = await self.fetch_teams(str(competition["id"]))
                    team = next((t for t in teams if str(t.get("id")) == team_id), None)

                    if team:
                        normalized_team = self.normalize_team_data(team)
                        normalized_team["competition_info"] = {
                            "id": competition["id"],
                            "name": competition["name"],
                            "code": competition["code"],
                        }
                        return normalized_team

                except Exception as e:
                    logger.error(
                        f"Failed to get team {team_id} from competition {competition.get('code')}: {e}"
                    )
                    continue

            logger.warning(f"Team {team_id} not found in any supported competition")
            return None

        except Exception as e:
            logger.error(f"Failed to collect team details for {team_id}: {e}")
            return None

    async def collect_team_matches(
        self,
    team_id: str,
    limit: int = 20
    ) -> list[dict[str,
    Any]]:
        """
        收集特定球队的比赛数据

        Args:
            team_id: 球队ID
            limit: 限制数量

        Returns:
            比赛数据列表
        """
        try:
            matches = await self.fetch_team_matches(team_id,
    limit=limit)
            normalized_matches = []

            for match in matches:
                normalized_match = self._normalize_match_for_team(match, team_id)
                if normalized_match:
                    normalized_matches.append(normalized_match)

            logger.info(
                f"Collected {len(normalized_matches)} matches for team {team_id}"
            )
            return normalized_matches

        except Exception as e:
            logger.error(f"Failed to collect matches for team {team_id}: {e}")
            return []

    def _normalize_match_for_team(
        self,
    match: dict[str,
    Any],
    team_id: str
    ) -> dict[str,
    Any] | None:
        """为球队视角标准化比赛数据"""
        try:
            home_team = match.get("homeTeam", {})
            away_team = match.get("awayTeam", {})
            score = match.get("score", {})

            # 判断球队是主队还是客队
            is_home_team = str(home_team.get("id")) == team_id
            opponent = away_team if is_home_team else home_team

            # 获取比分
            full_time_score = score.get("fullTime", {})
            if is_home_team:
                team_score = full_time_score.get("home") or 0
                opponent_score = full_time_score.get("away") or 0
            else:
                team_score = full_time_score.get("away") or 0
                opponent_score = full_time_score.get("home") or 0

            # 判断比赛结果
            winner = score.get("winner")
            if winner == "HOME_TEAM" and is_home_team:
                result = "win"
            elif winner == "AWAY_TEAM" and not is_home_team:
                result = "win"
            elif winner == "DRAW":
                result = "draw"
            else:
                result = "loss" if winner else None

            return {
                "external_id": str(match.get("id")),
    "match_date": match.get("utcDate"),
    "status": match.get("status",
    "").lower(),
    
                "is_home_team": is_home_team,
                "opponent": {
                    "id": opponent.get("id"),
    "name": opponent.get("name"),
    "short_name": opponent.get("shortName"),
    "crest": opponent.get("crest"),
    
                },
                "team_score": team_score,
                "opponent_score": opponent_score,
                "result": result,
                "matchday": match.get("matchday"),
                "stage": match.get("stage"),
                "competition": {
                    "id": match.get("competition", {}).get("id"),
                    "name": match.get("competition", {}).get("name"),
                    "code": match.get("competition", {}).get("code"),
    },
    "venue": match.get("venue"),
    "last_updated": match.get("lastUpdated"),
    
            }

        except Exception as e:
            logger.error(f"Error normalizing match data for team {team_id}: {e}")
            return None

    async def search_teams(self,
    search_term: str) -> list[dict[str,
    Any]]:
        """
        搜索球队

        Args:
            search_term: 搜索关键词

        Returns:
            匹配的球队列表
        """
        try:
            all_teams = []
            search_term_lower = search_term.lower()

            # 在所有支持的联赛中搜索
            all_competitions = await self.fetch_competitions()
            supported_competitions = [
                comp
                for comp in all_competitions
                if comp.get("code") in self.supported_competitions
            ]

            for competition in supported_competitions:
                try:
                    teams = await self.fetch_teams(str(competition["id"]))

                    for team in teams:
                        team_name = team.get("name",
    "").lower()
                        short_name = team.get("shortName",
    "").lower()
                        tla = team.get("tla", "").lower()

                        # 检查是否匹配搜索词
                        if (
                            search_term_lower in team_name
                            or search_term_lower in short_name
                            or search_term_lower in tla
                        ):
                            normalized_team = self.normalize_team_data(team)
                            if normalized_team and "error" not in normalized_team:
                                normalized_team["competition_info"] = {
                                    "id": competition["id"],
                                    "name": competition["name"],
                                    "code": competition["code"],
                                }
                                all_teams.append(normalized_team)

                except Exception as e:
                    logger.error(
                        f"Failed to search teams in competition {competition.get('code')}: {e}"
                    )
                    continue

            # 去重（基于external_id）
            unique_teams = {}
            for team in all_teams:
                team_id = team["external_id"]
                if team_id not in unique_teams:
                    unique_teams[team_id] = team

            logger.info(f"Found {len(unique_teams)} teams matching '{search_term}'")
            return list(unique_teams.values())

        except Exception as e:
            logger.error(f"Failed to search teams: {e}")
            return []
