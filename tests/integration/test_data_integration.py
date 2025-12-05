from typing import Optional

#!/usr/bin/env python3
"""
数据集成测试脚本
用于验证数据源管理器和收集器功能
"""

import pytest

import asyncio
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, "/home/user/projects/FootballPrediction")

from src.cache.redis_manager import get_redis_manager
from src.collectors.data_sources import data_source_manager
from src.collectors.enhanced_fixtures_collector import EnhancedFixturesCollector
from src.database.connection import get_async_session


@pytest.mark.asyncio
async def test_data_sources():
    """测试数据源管理器"""

    # 检查可用数据源
    data_source_manager.get_available_sources()

    # 测试mock数据源
    mock_adapter = data_source_manager.get_adapter("mock")
    if mock_adapter:
        # 测试获取比赛数据
        matches = await mock_adapter.get_matches()

        # 显示前3场比赛
        if matches:
            for _i, _match in enumerate(matches[:3], 1):
                pass

        # 测试获取球队数据
        teams = await mock_adapter.get_teams()

        # 显示前5支球队
        if teams:
            for _i, team in enumerate(teams[:5], 1):
                if team.venue:
                    pass
    else:
        pass


@pytest.mark.asyncio
async def test_collector():
    """测试增强版收集器"""

    # 获取数据库和Redis会话
    try:
        async with get_async_session() as db_session:
            redis_manager = get_redis_manager()

            if not redis_manager:
                return

            collector = EnhancedFixturesCollector(db_session, redis_manager)

            # 测试收集比赛数据
            await collector.collect_all_fixtures(
                days_ahead=7,
                force_refresh=True,
                preferred_source="mock",  # 只收集7天的数据用于测试
            )

            # 测试收集球队数据
            await collector.collect_teams(force_refresh=True, preferred_source="mock")

            # 测试数据源状态
            await collector.get_data_source_status()

    except Exception:
        import traceback

        traceback.print_exc()


@pytest.mark.asyncio
async def test_specific_team():
    """测试指定球队的数据收集"""

    try:
        async with get_async_session() as db_session:
            redis_manager = get_redis_manager()

            if not redis_manager:
                return

            collector = EnhancedFixturesCollector(db_session, redis_manager)

            # 收集Manchester United的比赛
            team_name = "Manchester United"

            fixtures = await collector.collect_team_fixtures(
                team_name=team_name,
                days_ahead=30,
                force_refresh=True,
                preferred_source="mock",
            )

            # 显示比赛详情
            if fixtures:
                for _i, _fixture in enumerate(fixtures[:5], 1):
                    pass

    except Exception:
        import traceback

        traceback.print_exc()


@pytest.mark.asyncio
async def test_league_data():
    """测试联赛数据收集"""

    try:
        async with get_async_session() as db_session:
            redis_manager = get_redis_manager()

            if not redis_manager:
                return

            collector = EnhancedFixturesCollector(db_session, redis_manager)

            # 收集英超比赛
            league_name = "英超"

            fixtures = await collector.collect_league_fixtures(
                league_name=league_name,
                days_ahead=15,
                force_refresh=True,
                preferred_source="mock",
            )

            # 显示比赛统计
            if fixtures:
                home_teams = {}
                away_teams = {}

                for fixture in fixtures:
                    home_teams[fixture["home_team"]] = (
                        home_teams.get(fixture["home_team"], 0) + 1
                    )
                    away_teams[fixture["away_team"]] = (
                        away_teams.get(fixture["away_team"], 0) + 1
                    )

                set(list(home_teams.keys()) + list(away_teams.keys()))

    except Exception:
        import traceback

        traceback.print_exc()


async def main():
    """主测试函数"""

    # 测试数据源管理器
    await test_data_sources()

    # 测试收集器
    await test_collector()

    # 测试指定球队数据
    await test_specific_team()

    # 测试联赛数据
    await test_league_data()


if __name__ == "__main__":
    asyncio.run(main())