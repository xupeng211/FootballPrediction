"""数据服务模块
Data Service Module.

提供比赛数据管理的核心业务逻辑。
Provides core business logic for match data management.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DataService:
    """数据服务类 - 统一的数据管理服务."""

    def __init__(self):
        """初始化数据服务."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_matches_list(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """获取比赛列表
        Get matches list.

        Args:
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            比赛列表数据
        """
        sample_matches = [
            {
                "id": 12345,
                "home_team": {"id": 1, "name": "Manchester United", "short_name": "MU"},
                "away_team": {"id": 2, "name": "Liverpool", "short_name": "LIV"},
                "date": "2025-11-10T15:00:00.000Z",
                "status": "SCHEDULED",
                "venue": "Old Trafford",
                "league": {"id": 39, "name": "Premier League", "country": "England"},
            },
            {
                "id": 12346,
                "home_team": {"id": 3, "name": "Chelsea", "short_name": "CHE"},
                "away_team": {"id": 4, "name": "Arsenal", "short_name": "ARS"},
                "date": "2025-11-11T17:30:00.000Z",
                "status": "SCHEDULED",
                "venue": "Stamford Bridge",
                "league": {"id": 39, "name": "Premier League", "country": "England"},
            },
            {
                "id": 12347,
                "home_team": {"id": 5, "name": "Barcelona", "short_name": "BAR"},
                "away_team": {"id": 6, "name": "Real Madrid", "short_name": "RMA"},
                "date": "2025-11-12T20:00:00.000Z",
                "status": "SCHEDULED",
                "venue": "Camp Nou",
                "league": {"id": 140, "name": "La Liga", "country": "Spain"},
            },
        ]

        start = offset
        end = start + limit
        paginated_matches = sample_matches[start:end]

        return {
            "matches": paginated_matches,
            "total": len(sample_matches),
            "limit": limit,
            "offset": offset,
        }

    def get_match_by_id(self, match_id: int) -> dict[str, Any] | None:
        """根据ID获取比赛信息
        Get match information by ID.

        Args:
            match_id: 比赛ID

        Returns:
            比赛信息
        """
        sample_matches = {
            12345: {
                "id": 12345,
                "home_team": {"id": 1, "name": "Manchester United", "short_name": "MU"},
                "away_team": {"id": 2, "name": "Liverpool", "short_name": "LIV"},
                "date": "2025-11-10T15:00:00.000Z",
                "status": "SCHEDULED",
                "venue": "Old Trafford",
                "league": {"id": 39, "name": "Premier League", "country": "England"},
                "statistics": {
                    "possession": {"home": 52, "away": 48},
                    "shots": {"home": 12, "away": 8},
                    "corners": {"home": 6, "away": 4},
                },
            },
            12346: {
                "id": 12346,
                "home_team": {"id": 3, "name": "Chelsea", "short_name": "CHE"},
                "away_team": {"id": 4, "name": "Arsenal", "short_name": "ARS"},
                "date": "2025-11-11T17:30:00.000Z",
                "status": "SCHEDULED",
                "venue": "Stamford Bridge",
                "league": {"id": 39, "name": "Premier League", "country": "England"},
                "statistics": {
                    "possession": {"home": 48, "away": 52},
                    "shots": {"home": 9, "away": 11},
                    "corners": {"home": 5, "away": 7},
                },
            },
        }

        return sample_matches.get(match_id)

    def get_teams_list(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """获取球队列表
        Get teams list.

        Args:
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            球队列表数据
        """
        sample_teams = [
            {
                "id": 1,
                "name": "Manchester United",
                "short_name": "MU",
                "country": "England",
                "founded": 1878,
                "stadium": "Old Trafford",
                "league": {"id": 39, "name": "Premier League"},
            },
            {
                "id": 2,
                "name": "Liverpool",
                "short_name": "LIV",
                "country": "England",
                "founded": 1892,
                "stadium": "Anfield",
                "league": {"id": 39, "name": "Premier League"},
            },
            {
                "id": 3,
                "name": "Chelsea",
                "short_name": "CHE",
                "country": "England",
                "founded": 1905,
                "stadium": "Stamford Bridge",
                "league": {"id": 39, "name": "Premier League"},
            },
            {
                "id": 4,
                "name": "Arsenal",
                "short_name": "ARS",
                "country": "England",
                "founded": 1886,
                "stadium": "Emirates Stadium",
                "league": {"id": 39, "name": "Premier League"},
            },
            {
                "id": 5,
                "name": "Barcelona",
                "short_name": "BAR",
                "country": "Spain",
                "founded": 1899,
                "stadium": "Camp Nou",
                "league": {"id": 140, "name": "La Liga"},
            },
            {
                "id": 6,
                "name": "Real Madrid",
                "short_name": "RMA",
                "country": "Spain",
                "founded": 1902,
                "stadium": "Santiago Bernabéu",
                "league": {"id": 140, "name": "La Liga"},
            },
        ]

        start = offset
        end = start + limit
        paginated_teams = sample_teams[start:end]

        return {
            "teams": paginated_teams,
            "total": len(sample_teams),
            "limit": limit,
            "offset": offset,
        }

    def get_team_by_id(self, team_id: int) -> dict[str, Any] | None:
        """根据ID获取球队信息
        Get team information by ID.

        Args:
            team_id: 球队ID

        Returns:
            球队信息
        """
        sample_teams = {
            1: {
                "id": 1,
                "name": "Manchester United",
                "short_name": "MU",
                "country": "England",
                "founded": 1878,
                "stadium": "Old Trafford",
                "league": {"id": 39, "name": "Premier League"},
                "statistics": {
                    "matches_played": 38,
                    "wins": 21,
                    "draws": 8,
                    "losses": 9,
                    "goals_for": 62,
                    "goals_against": 38,
                },
            },
            2: {
                "id": 2,
                "name": "Liverpool",
                "short_name": "LIV",
                "country": "England",
                "founded": 1892,
                "stadium": "Anfield",
                "league": {"id": 39, "name": "Premier League"},
                "statistics": {
                    "matches_played": 38,
                    "wins": 25,
                    "draws": 7,
                    "losses": 6,
                    "goals_for": 68,
                    "goals_against": 33,
                },
            },
        }

        return sample_teams.get(team_id)

    def get_leagues_list(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """获取联赛列表
        Get leagues list.

        Args:
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            联赛列表数据
        """
        sample_leagues = [
            {
                "id": 39,
                "name": "Premier League",
                "country": "England",
                "founded": 1992,
                "teams": 20,
                "season": "2024/2025",
                "current_champion": "Manchester City",
            },
            {
                "id": 140,
                "name": "La Liga",
                "country": "Spain",
                "founded": 1929,
                "teams": 20,
                "season": "2024/2025",
                "current_champion": "Real Madrid",
            },
            {
                "id": 135,
                "name": "Serie A",
                "country": "Italy",
                "founded": 1898,
                "teams": 20,
                "season": "2024/2025",
                "current_champion": "Inter Milan",
            },
            {
                "id": 78,
                "name": "Bundesliga",
                "country": "Germany",
                "founded": 1963,
                "teams": 18,
                "season": "2024/2025",
                "current_champion": "Bayer Leverkusen",
            },
        ]

        start = offset
        end = start + limit
        paginated_leagues = sample_leagues[start:end]

        return {
            "leagues": paginated_leagues,
            "total": len(sample_leagues),
            "limit": limit,
            "offset": offset,
        }

    def get_odds_data(self, match_id: int | None = None) -> dict[str, Any]:
        """获取赔率数据
        Get odds data.

        Args:
            match_id: 可选的比赛ID过滤

        Returns:
            赔率数据
        """
        sample_odds = [
            {
                "match_id": 12345,
                "bookmakers": [
                    {
                        "name": "Bet365",
                        "odds": {"home_win": 2.10, "draw": 3.40, "away_win": 3.20},
                    },
                    {
                        "name": "William Hill",
                        "odds": {"home_win": 2.05, "draw": 3.50, "away_win": 3.30},
                    },
                ],
                "last_updated": "2025-11-12T10:00:00.000Z",
            },
            {
                "match_id": 12346,
                "bookmakers": [
                    {
                        "name": "Bet365",
                        "odds": {"home_win": 1.95, "draw": 3.60, "away_win": 3.80},
                    }
                ],
                "last_updated": "2025-11-12T10:00:00.000Z",
            },
        ]

        if match_id is not None:
            sample_odds = [odds for odds in sample_odds if odds["match_id"] == match_id]

        return {"odds": sample_odds, "total": len(sample_odds), "filter": match_id}


class MatchService:
    """比赛数据服务类."""

    def __init__(self):
        """初始化比赛数据服务."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_matches(self, limit: int = 10, offset: int = 0) -> dict[str, Any]:
        """获取比赛列表
        Get matches list.

        Args:
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            比赛列表数据
        """
        # 模拟返回比赛数据
        sample_matches = [
            {
                "id": 12345,
                "home_team": {"id": 1, "name": "Manchester United", "short_name": "MU"},
                "away_team": {"id": 2, "name": "Liverpool", "short_name": "LIV"},
                "date": "2025-11-10T15:00:00.000Z",
                "status": "SCHEDULED",
                "venue": "Old Trafford",
            },
            {
                "id": 12346,
                "home_team": {"id": 3, "name": "Chelsea", "short_name": "CHE"},
                "away_team": {"id": 4, "name": "Arsenal", "short_name": "ARS"},
                "date": "2025-11-11T17:30:00.000Z",
                "status": "SCHEDULED",
                "venue": "Stamford Bridge",
            },
        ]

        # 应用分页
        start = offset
        end = start + limit
        paginated_matches = sample_matches[start:end]

        return {
            "matches": paginated_matches,
            "total": len(sample_matches),
            "limit": limit,
            "offset": offset,
        }

    def get_match_by_id(self, match_id: int) -> dict[str, Any]:
        """根据ID获取比赛
        Get match by ID.

        Args:
            match_id: 比赛ID

        Returns:
            比赛数据
        """
        # 模拟返回指定比赛数据
        if match_id == 12345:
            return {
                "id": match_id,
                "home_team": {"id": 1, "name": "Manchester United", "short_name": "MU"},
                "away_team": {"id": 2, "name": "Liverpool", "short_name": "LIV"},
                "date": "2025-11-10T15:00:00.000Z",
                "status": "SCHEDULED",
                "venue": "Old Trafford",
                "league": {"id": 39, "name": "Premier League", "country": "England"},
            }
        else:
            return None


# 全局数据服务实例
_data_service: DataService | None = None


def get_data_service() -> DataService:
    """获取数据服务实例."""
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service
