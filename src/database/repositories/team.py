"""
球队仓储

提供球队数据的访问操作。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload

from .base import BaseRepository, RepositoryConfig
from src.database.models.team import Team
from src.database.models.match import Match, MatchStatus


class TeamRepository(BaseRepository[Team]):
    """球队仓储类"""

    def __init__(self, session, config: Optional[RepositoryConfig] = None):
        super().__init__(session, Team, config or RepositoryConfig())

    # ==================== 基础查询 ====================

    async def get_by_name(self, name: str) -> Optional[Team]:
        """根据名称获取球队"""
        return await self.find_one({"name": name})

    async def get_by_short_name(self, short_name: str) -> Optional[Team]:
        """根据简称获取球队"""
        return await self.find_one({"short_name": short_name})

    async def search_teams(self, query: str, limit: int = 20) -> List[Team]:
        """搜索球队"""
        stmt = (
            select(self.model_class)
            .where(
                or_(
                    self.model_class.name.ilike(f"%{query}%"),
                    self.model_class.short_name.ilike(f"%{query}%"),
                    self.model_class.country.ilike(f"%{query}%"),
                )
            )
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 联赛相关查询 ====================

    async def get_by_league(self, league_id: int) -> List[Team]:
        """根据联赛获取球队"""
        # 通过比赛表获取联赛中的球队
        stmt = (
            select(self.model_class)
            .where(
                self.model_class.id.in_(
                    select(Match.home_team_id)
                    .where(Match.league_id == league_id)
                    .union(
                        select(Match.away_team_id).where(Match.league_id == league_id)
                    )
                )
            )
            .distinct()
            .order_by(self.model_class.name)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_country(self, country: str, limit: int = 100) -> List[Team]:
        """根据国家获取球队"""
        return await self.find({"country": country}, limit=limit, order_by="name")

    # ==================== 球队统计查询 ====================

    async def get_team_statistics(
        self, team_id: int, season: Optional[str] = None, last_matches: int = 10
    ) -> Dict[str, Any]:
        """获取球队统计信息"""
        team = await self.get_by_id(team_id)
        if not team:
            return {}

        # 构建查询条件
        match_filters = [
            or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
            Match.status == MatchStatus.FINISHED,
            Match.home_score.is_not(None),
            Match.away_score.is_not(None),
        ]

        if season:
            match_filters.append(Match.season == season)

        # 获取最近的比赛
        recent_matches_stmt = (
            select(Match)
            .where(and_(*match_filters))
            .order_by(desc(Match.match_time))
            .limit(last_matches)
        )

        recent_result = await self.session.execute(recent_matches_stmt)
        recent_matches = recent_result.scalars().all()

        # 计算统计
        stats = {
            "team_id": team_id,
            "team_name": team.name,
            "season": season,
            "matches_analyzed": len(recent_matches),
            "recent_form": [],
            "statistics": {
                "played": 0,
                "won": 0,
                "drawn": 0,
                "lost": 0,
                "goals_for": 0,
                "goals_against": 0,
                "clean_sheets": 0,
                "failed_to_score": 0,
            },
        }

        # 分析每场比赛
        for match in recent_matches:
            is_home = match.home_team_id == team_id
            team_score = match.home_score if is_home else match.away_score
            opponent_score = match.away_score if is_home else match.home_score

            # 更新统计
            stats["statistics"]["played"] += 1
            stats["statistics"]["goals_for"] += team_score
            stats["statistics"]["goals_against"] += opponent_score

            if team_score == 0:
                stats["statistics"]["failed_to_score"] += 1
            if opponent_score == 0:
                stats["statistics"]["clean_sheets"] += 1

            # 判断胜负
            if team_score > opponent_score:
                stats["statistics"]["won"] += 1
                result = "W"
            elif team_score < opponent_score:
                stats["statistics"]["lost"] += 1
                result = "L"
            else:
                stats["statistics"]["drawn"] += 1
                result = "D"

            # 添加到近期战绩
            stats["recent_form"].append(
                {
                    "match_id": match.id,
                    "date": match.match_time,
                    "is_home": is_home,
                    "team_score": team_score,
                    "opponent_score": opponent_score,
                    "result": result,
                    "opponent_id": match.away_team_id
                    if is_home
                    else match.home_team_id,
                }
            )

        # 计算其他指标
        played = stats["statistics"]["played"]
        if played > 0:
            stats["statistics"]["win_rate"] = stats["statistics"]["won"] / played
            stats["statistics"]["average_goals_for"] = (
                stats["statistics"]["goals_for"] / played
            )
            stats["statistics"]["average_goals_against"] = (
                stats["statistics"]["goals_against"] / played
            )
            stats["statistics"]["goal_difference"] = (
                stats["statistics"]["goals_for"] - stats["statistics"]["goals_against"]
            )
        else:
            stats["statistics"]["win_rate"] = 0
            stats["statistics"]["average_goals_for"] = 0
            stats["statistics"]["average_goals_against"] = 0
            stats["statistics"]["goal_difference"] = 0

        return stats

    async def get_team_head_to_head(
        self, team1_id: int, team2_id: int, limit: int = 10
    ) -> Dict[str, Any]:
        """获取两队历史交锋记录"""
        stmt = (
            select(Match)
            .where(
                and_(
                    or_(
                        and_(
                            Match.home_team_id == team1_id,
                            Match.away_team_id == team2_id,
                        ),
                        and_(
                            Match.home_team_id == team2_id,
                            Match.away_team_id == team1_id,
                        ),
                    ),
                    Match.status == MatchStatus.FINISHED,
                )
            )
            .order_by(desc(Match.match_time))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        matches = result.scalars().all()

        # 统计交锋记录
        h2h_stats = {
            "team1_id": team1_id,
            "team2_id": team2_id,
            "total_matches": len(matches),
            "team1_wins": 0,
            "team2_wins": 0,
            "draws": 0,
            "team1_goals": 0,
            "team2_goals": 0,
            "recent_matches": [],
        }

        for match in matches:
            team1_is_home = match.home_team_id == team1_id
            team1_score = match.home_score if team1_is_home else match.away_score
            team2_score = match.away_score if team1_is_home else match.home_score

            # 更新统计
            h2h_stats["team1_goals"] += team1_score
            h2h_stats["team2_goals"] += team2_score

            if team1_score > team2_score:
                h2h_stats["team1_wins"] += 1
            elif team1_score < team2_score:
                h2h_stats["team2_wins"] += 1
            else:
                h2h_stats["draws"] += 1

            # 添加到最近交锋
            h2h_stats["recent_matches"].append(
                {
                    "match_id": match.id,
                    "date": match.match_time,
                    "team1_home": team1_is_home,
                    "team1_score": team1_score,
                    "team2_score": team2_score,
                    "winner": 1
                    if team1_score > team2_score
                    else 2
                    if team2_score > team1_score
                    else 0,
                }
            )

        return h2h_stats

    # ==================== 排行榜查询 ====================

    async def get_league_standings(
        self, league_id: int, season: str
    ) -> List[Dict[str, Any]]:
        """获取联赛积分榜（通过比赛数据计算）"""
        # 获取联赛所有已完成的比赛
        stmt = select(Match).where(
            and_(
                Match.league_id == league_id,
                Match.season == season,
                Match.status == MatchStatus.FINISHED,
                Match.home_score.is_not(None),
                Match.away_score.is_not(None),
            )
        )

        result = await self.session.execute(stmt)
        matches = result.scalars().all()

        # 获取联赛中的球队
        team_ids = set()
        for match in matches:
            team_ids.add(match.home_team_id)
            team_ids.add(match.away_team_id)

        # 获取球队信息
        teams_stmt = select(Team).where(Team.id.in_(team_ids))
        teams_result = await self.session.execute(teams_stmt)
        teams = {team.id: team for team in teams_result.scalars().all()}

        # 计算积分榜
        standings = {}
        for match in matches:
            # 处理主队
            home_team = standings.get(match.home_team_id)
            if not home_team:
                home_team = {
                    "team_id": match.home_team_id,
                    "team_name": teams[match.home_team_id].name
                    if match.home_team_id in teams
                    else "Unknown",
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "goal_difference": 0,
                    "points": 0,
                }
                standings[match.home_team_id] = home_team

            # 处理客队
            away_team = standings.get(match.away_team_id)
            if not away_team:
                away_team = {
                    "team_id": match.away_team_id,
                    "team_name": teams[match.away_team_id].name
                    if match.away_team_id in teams
                    else "Unknown",
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "goal_difference": 0,
                    "points": 0,
                }
                standings[match.away_team_id] = away_team

            # 更新统计
            home_score = match.home_score
            away_score = match.away_score

            # 主队统计
            home_team["played"] += 1
            home_team["goals_for"] += home_score
            home_team["goals_against"] += away_score

            # 客队统计
            away_team["played"] += 1
            away_team["goals_for"] += away_score
            away_team["goals_against"] += home_score

            # 判断胜负并分配积分
            if home_score > away_score:
                home_team["won"] += 1
                home_team["points"] += 3
                away_team["lost"] += 1
            elif home_score < away_score:
                away_team["won"] += 1
                away_team["points"] += 3
                home_team["lost"] += 1
            else:
                home_team["drawn"] += 1
                away_team["drawn"] += 1
                home_team["points"] += 1
                away_team["points"] += 1

        # 计算净胜球
        for team in standings.values():
            team["goal_difference"] = team["goals_for"] - team["goals_against"]

        # 排序
        sorted_standings = sorted(
            standings.values(),
            key=lambda x: (x["points"], x["goal_difference"], x["goals_for"]),
            reverse=True,
        )

        # 添加排名
        for i, team in enumerate(sorted_standings):
            team["position"] = i + 1

        return sorted_standings

    # ==================== 批量操作 ====================

    async def update_team_logo(self, team_id: int, logo_url: str) -> bool:
        """更新球队Logo"""
        updates = {"logo_url": logo_url, "updated_at": datetime.now()}

        updated_count = await self.update_batch({"id": team_id}, updates)

        return updated_count > 0

    async def bulk_update_stadium(self, team_stadiums: Dict[int, str]) -> int:
        """批量更新球队主场"""
        updated_count = 0
        current_time = datetime.now()

        for team_id, stadium in team_stadiums.items():
            updates = {"stadium": stadium, "updated_at": current_time}

            count = await self.update_batch({"id": team_id}, updates)
            updated_count += count

        return updated_count

    # ==================== 高级查询 ====================

    async def get_top_scoring_teams(
        self, season: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取进球最多的球队"""
        # 构建查询
        match_filters = [
            Match.status == MatchStatus.FINISHED,
            Match.home_score.is_not(None),
            Match.away_score.is_not(None),
        ]

        if season:
            match_filters.append(Match.season == season)

        # 使用窗口函数计算球队进球数
        from sqlalchemy import text

        # 使用原生SQL进行复杂查询
        text(
            """
            SELECT
                t.id as team_id,
                t.name as team_name,
                SUM(
                    CASE
                        WHEN m.home_team_id = t.id THEN m.home_score
                        ELSE m.away_score
                    END
                ) as total_goals,
                COUNT(m.id) as matches_played,
                AVG(
                    CASE
                        WHEN m.home_team_id = t.id THEN m.home_score
                        ELSE m.away_score
                    END
                ) as avg_goals_per_match
            FROM teams t
            INNER JOIN matches m ON (m.home_team_id = t.id OR m.away_team_id = t.id)
            WHERE m.status = 'finished'
            AND m.home_score IS NOT NULL
            AND m.away_score IS NOT NULL
            {season_filter}
            GROUP BY t.id, t.name
            ORDER BY total_goals DESC
            LIMIT :limit
        """.format(season_filter="AND m.season = :season" if season else "")
        )

        params = {"limit": limit}
        if season:
            params["season"] = season

        result = await self.session.execute(sql_query_query, params)
        rows = result.fetchall()

        return [
            {
                "team_id": row.team_id,
                "team_name": row.team_name,
                "total_goals": row.total_goals,
                "matches_played": row.matches_played,
                "avg_goals_per_match": float(row.avg_goals_per_match),
            }
            for row in rows
        ]

    async def get_teams_with_best_defense(
        self, season: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取防守最好的球队（失球最少）"""
        # 类似上面的查询，但计算失球数
        from sqlalchemy import text

        sql_query = text(
            """
            SELECT
                t.id as team_id,
                t.name as team_name,
                SUM(
                    CASE
                        WHEN m.home_team_id = t.id THEN m.away_score
                        ELSE m.home_score
                    END
                ) as goals_conceded,
                COUNT(m.id) as matches_played,
                AVG(
                    CASE
                        WHEN m.home_team_id = t.id THEN m.away_score
                        ELSE m.home_score
                    END
                ) as avg_goals_conceded_per_match,
                SUM(
                    CASE
                        WHEN m.home_team_id = t.id THEN m.away_score
                        ELSE m.home_score
                    END
                ) = 0 as clean_sheets
            FROM teams t
            INNER JOIN matches m ON (m.home_team_id = t.id OR m.away_team_id = t.id)
            WHERE m.status = 'finished'
            AND m.home_score IS NOT NULL
            AND m.away_score IS NOT NULL
            {season_filter}
            GROUP BY t.id, t.name
            HAVING COUNT(m.id) >= 5
            ORDER BY avg_goals_conceded_per_match ASC
            LIMIT :limit
        """.format(season_filter="AND m.season = :season" if season else "")
        )

        params = {"limit": limit}
        if season:
            params["season"] = season

        result = await self.session.execute(sql_query, params)
        rows = result.fetchall()

        return [
            {
                "team_id": row.team_id,
                "team_name": row.team_name,
                "goals_conceded": row.goals_conceded,
                "matches_played": row.matches_played,
                "avg_goals_conceded_per_match": float(row.avg_goals_conceded_per_match),
                "clean_sheets": row.clean_sheets,
            }
            for row in rows
        ]
