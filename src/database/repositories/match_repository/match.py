"""比赛仓储实现 - V2全栈架构师升级
Match Repository Implementation with V2 Deep Data Support.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.match import Match
from src.database.repositories.base import AbstractRepository


class MatchRepository(AbstractRepository[Match]):
    """比赛数据仓储类."""

    def __init__(self, session: AsyncSession):
        """函数文档字符串."""
        # 添加pass语句
        super().__init__(session, Match)

    async def create(self, match_data: dict) -> Match:
        """创建比赛记录 - V2支持深度数据."""
        # 确保V2字段自动设置
        if 'data_source' not in match_data:
            match_data['data_source'] = 'fotmob_v2'
        if 'collection_time' not in match_data:
            match_data['collection_time'] = datetime.now()

        match = Match(**match_data)
        self.session.add(match)
        await self.session.commit()
        await self.session.refresh(match)
        return match

    async def get_by_id(self, match_id: int) -> Match | None:
        """根据ID获取比赛."""
        return await self.session.get(Match, match_id)

    async def get_by_team(self, team_id: int) -> list[Match]:
        """根据队伍ID获取比赛列表."""
        # 这里应该实现具体的查询逻辑
        # 暂时返回空列表
        return []

    async def update(self, match_id: int, match_data: dict) -> Match | None:
        """更新比赛信息."""
        match = await self.get_by_id(match_id)
        if match:
            for key, value in match_data.items():
                setattr(match, key, value)
            await self.session.commit()
            await self.session.refresh(match)
        return match

    async def delete(self, match_id: int) -> bool:
        """删除比赛记录."""
        match = await self.get_by_id(match_id)
        if match:
            await self.session.delete(match)
            await self.session.commit()
            return True
        return False

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[Match]:
        """获取所有比赛列表."""
        result = await self.session.execute(select(Match).offset(offset).limit(limit))
        return result.scalars().all()

    async def get_by_competition(self, competition_id: str) -> list[Match]:
        """根据比赛ID获取比赛列表."""
        # 这里应该实现具体的查询逻辑
        # 暂时返回空列表
        return []

    # 🚀 V2深度数据专用方法 - 全栈架构师添加
    async def create_from_fotmob_v2(self, fotmob_data: dict[str, Any]) -> Match:
        """从FotMob V2数据创建比赛记录."""
        # 转换FotMob数据格式到数据库格式
        match_data = {
            'id': fotmob_data.get('match_id'),
            'home_team_id': fotmob_data.get('home_team_id'),
            'away_team_id': fotmob_data.get('away_team_id'),
            'home_score': fotmob_data.get('home_score', 0),
            'away_score': fotmob_data.get('away_score', 0),
            'status': fotmob_data.get('status', 'scheduled'),
            'venue': fotmob_data.get('venue'),
            'league_id': fotmob_data.get('league_id'),
            'season': fotmob_data.get('season', '2024-25'),

            # V2深度数据字段
            'lineups': fotmob_data.get('lineups'),
            'stats': fotmob_data.get('stats'),
            'events': fotmob_data.get('events'),
            'odds': fotmob_data.get('odds'),
            'metadata': {
                'kickoff_time': fotmob_data.get('kickoff_time'),
                'utc_time': fotmob_data.get('utc_time'),
                'league_name': fotmob_data.get('league_name'),
                'home_team_name': fotmob_data.get('home_team_name'),
                'away_team_name': fotmob_data.get('away_team_name'),
            },

            # 数据来源和质量追踪
            'data_source': 'fotmob_v2',
            'data_completeness': fotmob_data.get('data_completeness', 'partial'),
            'collection_time': datetime.now(),
        }

        return await self.create(match_data)

    async def get_matches_with_lineups(self, limit: int = 50) -> list[Match]:
        """获取有阵容数据的比赛."""
        result = await self.session.execute(
            select(Match)
            .where(Match.lineups.isnot(None))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_matches_with_stats(self, limit: int = 50) -> list[Match]:
        """获取有统计数据的比赛."""
        result = await self.session.execute(
            select(Match)
            .where(Match.stats.isnot(None))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_complete_matches(self, limit: int = 50) -> list[Match]:
        """获取数据完整的比赛（有阵容和统计）."""
        result = await self.session.execute(
            select(Match)
            .where(
                and_(
                    Match.lineups.isnot(None),
                    Match.stats.isnot(None),
                    Match.data_completeness == 'complete'
                )
            )
            .limit(limit)
        )
        return result.scalars().all()

    async def update_deep_data(self, match_id: int, deep_data: dict[str, Any]) -> Match | None:
        """更新比赛的深度数据."""
        match = await self.get_by_id(match_id)
        if match:
            # 更新深度数据字段
            if 'lineups' in deep_data:
                match.lineups = deep_data['lineups']
            if 'stats' in deep_data:
                match.stats = deep_data['stats']
            if 'events' in deep_data:
                match.events = deep_data['events']
            if 'odds' in deep_data:
                match.odds = deep_data['odds']
            if 'metadata' in deep_data:
                if isinstance(match.metadata, dict):
                    match.metadata.update(deep_data['metadata'])
                else:
                    match.metadata = deep_data['metadata']

            # 更新数据完整度
            completeness_score = 0
            if match.lineups: completeness_score += 1
            if match.stats: completeness_score += 1
            if match.events: completeness_score += 1

            if completeness_score >= 3:
                match.data_completeness = 'complete'
            elif completeness_score >= 2:
                match.data_completeness = 'detailed'
            else:
                match.data_completeness = 'partial'

            match.collection_time = datetime.now()

            await self.session.commit()
            await self.session.refresh(match)
        return match

    async def get_data_quality_stats(self) -> dict[str, int]:
        """获取数据质量统计."""
        total_result = await self.session.execute(select(Match))
        total = len(total_result.scalars().all())

        lineups_result = await self.session.execute(
            select(Match).where(Match.lineups.isnot(None))
        )
        with_lineups = len(lineups_result.scalars().all())

        stats_result = await self.session.execute(
            select(Match).where(Match.stats.isnot(None))
        )
        with_stats = len(stats_result.scalars().all())

        complete_result = await self.session.execute(
            select(Match).where(Match.data_completeness == 'complete')
        )
        complete = len(complete_result.scalars().all())

        return {
            'total_matches': total,
            'matches_with_lineups': with_lineups,
            'matches_with_stats': with_stats,
            'complete_matches': complete,
            'lineups_coverage': with_lineups / total if total > 0 else 0,
            'stats_coverage': with_stats / total if total > 0 else 0,
            'complete_coverage': complete / total if total > 0 else 0,
        }
