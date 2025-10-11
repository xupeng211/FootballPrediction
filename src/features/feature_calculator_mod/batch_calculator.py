"""
批量计算模块

负责批量计算多个球队或比赛的特征，优化性能和数据库查询。
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional


from .recent_performance import RecentPerformanceCalculator


class BatchCalculator:
    """批量特征计算器"""

    def __init__(self, db_manager: Any):
        """
        初始化批量计算器

        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager
        self.recent_calculator = RecentPerformanceCalculator(db_manager)

    async def calculate_team_features(
        self, team_ids: List[int], calculation_date: Optional[datetime] = None
    ) -> Dict[int, Any]:
        """
        批量计算球队特征

        Args:
            team_ids: 球队ID列表
            calculation_date: 计算日期

        Returns:
            Dict[int, RecentPerformanceFeatures]: 球队ID到特征的映射
        """
        if calculation_date is None:
            calculation_date = datetime.now()

        results = {}
        async with self.db_manager.get_async_session() as session:
            tasks = [
                self.recent_calculator._calculate_recent_performance(
                    session, team_id, calculation_date
                )
                for team_id in team_ids
            ]

            features_list = await asyncio.gather(*tasks)

            for team_id, features in zip(team_ids, features_list):
                results[team_id] = features

        return results

    async def calculate_match_features_batch(
        self, match_ids: List[int], calculation_date: Optional[datetime] = None
    ) -> Dict[int, Dict[str, Any]]:
        """
        批量计算比赛特征

        Args:
            match_ids: 比赛ID列表
            calculation_date: 计算日期

        Returns:
            Dict[int, Dict]: 比赛ID到特征的映射
        """
        if calculation_date is None:
            calculation_date = datetime.now()

        # 首先获取比赛信息
        from sqlalchemy import select
        from ...database.models.match import Match

        async with self.db_manager.get_async_session() as session:
            match_query = select(Match).where(Match.match_id.in_(match_ids))  # type: ignore
            result = await session.execute(match_query)
            matches = result.scalars().all()

        # 为每场比赛计算特征
        match_features = {}
        for match in matches:
            from ..entities import MatchEntity

            match_entity = MatchEntity(  # type: ignore
                match_id=match.match_id,
                home_team_id=match.home_team_id,
                away_team_id=match.away_team_id,
                match_time=match.match_time,
            )

            # 使用完整的特征计算器
            from .core import FeatureCalculator

            calculator = FeatureCalculator()
            features = await calculator.calculate_all_match_features(
                match_entity, calculation_date
            )
            match_features[match.match_id] = features

        return match_features  # type: ignore

    async def calculate_historical_features_for_teams(
        self,
        team_ids: List[int],
        start_date: datetime,
        end_date: datetime,
        feature_types: List[str] = None,
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        批量计算球队的历史特征时间序列

        Args:
            team_ids: 球队ID列表
            start_date: 开始日期
            end_date: 结束日期
            feature_types: 需要计算的特征类型列表

        Returns:
            Dict[int, List[Dict]]: 球队ID到历史特征序列的映射
        """
        if feature_types is None:
            feature_types = ["recent_performance"]

        results: Dict[str, Any] = {team_id: [] for team_id in team_ids}  # type: ignore

        # 为每个球队生成时间序列特征
        for team_id in team_ids:
            # 生成日期序列（每周一个时间点）
            from datetime import timedelta

            current_date = start_date
            while current_date <= end_date:
                date_features = {
                    "team_id": team_id,
                    "calculation_date": current_date,
                    "features": {},
                }

                # 计算指定类型的特征
                if "recent_performance" in feature_types:
                    recent_features = await self.recent_calculator.calculate(
                        team_id, current_date
                    )
                    date_features["features"]["recent_performance"] = recent_features  # type: ignore

                # 可以添加更多特征类型
                # if "h2h" in feature_types:
                #     ...

                results[team_id].append(date_features)  # type: ignore
                current_date += timedelta(days=7)

        return results  # type: ignore

    async def precompute_features_for_season(
        self, season_year: int, feature_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        预计算整个赛季的特征

        Args:
            season_year: 赛季年份
            feature_types: 需要预计算的特征类型

        Returns:
            Dict[str, Any]: 预计算结果统计
        """
        if feature_types is None:
            feature_types = [
                "recent_performance",
                "historical_matchup",
                "odds_features",
            ]

        # 获取赛季的所有比赛
        from sqlalchemy import select, extract
        from ...database.models.match import Match

        async with self.db_manager.get_async_session() as session:
            season_query = select(Match).where(
                extract("year", Match.match_time) == season_year
            )
            result = await session.execute(season_query)
            matches = result.scalars().all()

        # 获取所有球队ID
        team_ids = set()
        for match in matches:
            team_ids.add(match.home_team_id)
            team_ids.add(match.away_team_id)

        # 批量计算特征
        computation_stats = {
            "season_year": season_year,
            "total_matches": len(matches),
            "total_teams": len(team_ids),
            "computed_features": {},
            "computation_time": None,
        }

        from datetime import datetime

        start_time = datetime.now()

        # 计算每种特征类型
        for feature_type in feature_types:
            if feature_type == "recent_performance":
                team_features = await self.calculate_team_features(
                    list(team_ids), datetime.now()
                )
                computation_stats["computed_features"]["recent_performance"] = {  # type: ignore
                    "team_count": len(team_features),
                    "status": "completed",
                }

            # 可以添加其他特征类型的预计算
            # elif feature_type == "historical_matchup":
            #     ...

        end_time = datetime.now()
        computation_stats["computation_time"] = (end_time - start_time).total_seconds()

        return computation_stats

    async def calculate_features_with_cache(
        self,
        team_ids: List[int],
        calculation_date: datetime,
        cache_ttl: int = 3600,
    ) -> Dict[int, Any]:
        """
        带缓存的批量特征计算

        Args:
            team_ids: 球队ID列表
            calculation_date: 计算日期
            cache_ttl: 缓存生存时间（秒）

        Returns:
            Dict[int, Any]: 球队特征映射
        """
        # 这里可以集成Redis缓存
        # 暂时直接计算，后续可以扩展缓存逻辑
        return await self.calculate_team_features(team_ids, calculation_date)

    def optimize_batch_size(
        self, total_items: int, max_concurrent_tasks: int = 100
    ) -> List[List[int]]:
        """
        优化批量计算的分批大小

        Args:
            total_items: 总项目数
            max_concurrent_tasks: 最大并发任务数

        Returns:
            List[List[int]]: 分批的项目列表
        """
        if total_items <= max_concurrent_tasks:
            return [list(range(total_items))]

        # 计算最优批次数
        batch_size = max_concurrent_tasks
        batches = []

        for i in range(0, total_items, batch_size):
            batch_end = min(i + batch_size, total_items)
            batches.append(list(range(i, batch_end)))

        return batches
