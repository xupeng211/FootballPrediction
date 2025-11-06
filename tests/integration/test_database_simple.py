"""
简化的数据库集成测试
Simplified Database Integration Tests

使用简化的数据模型进行数据库集成测试，避免复杂的关系定义。
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .test_models_simple import TestBase, TestMatch, TestPrediction, TestTeam


@pytest.mark.integration
@pytest.mark.db_integration
class TestSimpleDatabaseOperations:
    """简化的数据库操作集成测试"""

    @pytest.fixture(scope="class")
    async def test_db_engine(self):
        """创建测试数据库引擎"""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
        )

        # 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        yield engine
        await engine.dispose()

    @pytest.fixture(scope="class")
    async def test_db_session(self, test_db_engine):
        """创建测试数据库会话"""
        async_session_maker = async_sessionmaker(
            test_db_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session_maker() as session:
            yield session

    async def test_team_crud_operations(self, test_db_session: AsyncSession):
        """测试球队CRUD操作"""
        # Create
        team = TestTeam(
            name="Integration Test Team",
            short_name="ITT",
            country="Test Country",
            founded_year=2024,
            venue="Test Stadium",
            website="https://test-team.com",
        )

        test_db_session.add(team)
        await test_db_session.commit()
        await test_db_session.refresh(team)

        assert team.id is not None
        assert team.name == "Integration Test Team"

        # Read
        stmt = select(TestTeam).where(TestTeam.id == team.id)
        result = await test_db_session.execute(stmt)
        fetched_team = result.scalar_one()

        assert fetched_team is not None
        assert fetched_team.name == team.name
        assert fetched_team.short_name == "ITT"

        # Update
        fetched_team.name = "Updated Team Name"
        await test_db_session.commit()
        await test_db_session.refresh(fetched_team)

        assert fetched_team.name == "Updated Team Name"

        # Delete
        await test_db_session.delete(fetched_team)
        await test_db_session.commit()

        result = await test_db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_match_crud_operations(self, test_db_session: AsyncSession):
        """测试比赛CRUD操作"""
        # Create teams first
        home_team = TestTeam(name="Home Team", short_name="HT", country="Country")
        away_team = TestTeam(name="Away Team", short_name="AT", country="Country")

        test_db_session.add_all([home_team, away_team])
        await test_db_session.commit()
        await test_db_session.refresh(home_team)
        await test_db_session.refresh(away_team)

        # Create match
        match = TestMatch(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=datetime.utcnow() + timedelta(days=1),
            league="Test League",
            status="scheduled",
        )

        test_db_session.add(match)
        await test_db_session.commit()
        await test_db_session.refresh(match)

        assert match.id is not None
        assert match.home_team_id == home_team.id

        # Update match
        match.home_score = 2
        match.away_score = 1
        match.status = "finished"
        await test_db_session.commit()
        await test_db_session.refresh(match)

        assert match.home_score == 2
        assert match.away_score == 1
        assert match.status == "finished"

    async def test_prediction_crud_operations(self, test_db_session: AsyncSession):
        """测试预测CRUD操作"""
        # Create match first
        home_team = TestTeam(name="Pred Home", short_name="PH", country="Country")
        away_team = TestTeam(name="Pred Away", short_name="PA", country="Country")

        test_db_session.add_all([home_team, away_team])
        await test_db_session.commit()
        await test_db_session.refresh(home_team)
        await test_db_session.refresh(away_team)

        match = TestMatch(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=datetime.utcnow() + timedelta(days=1),
            league="Prediction League",
        )

        test_db_session.add(match)
        await test_db_session.commit()
        await test_db_session.refresh(match)

        # Create prediction
        prediction = TestPrediction(
            match_id=match.id,
            home_win_prob=0.6,
            draw_prob=0.25,
            away_win_prob=0.15,
            predicted_outcome="home",
            confidence=0.75,
            model_version="test_model_v1",
        )

        test_db_session.add(prediction)
        await test_db_session.commit()
        await test_db_session.refresh(prediction)

        assert prediction.id is not None
        assert prediction.match_id == match.id
        assert prediction.predicted_outcome == "home"

        # Query predictions for match
        stmt = select(TestPrediction).where(TestPrediction.match_id == match.id)
        result = await test_db_session.execute(stmt)
        predictions = result.scalars().all()

        assert len(predictions) == 1
        assert predictions[0].predicted_outcome == "home"

    async def test_transaction_commit(self, test_db_session: AsyncSession):
        """测试事务提交"""
        # 直接提交数据（session已经有事务）
        team1 = TestTeam(name="Transaction Team 1", short_name="TT1", country="Country")
        team2 = TestTeam(name="Transaction Team 2", short_name="TT2", country="Country")

        test_db_session.add_all([team1, team2])
        await test_db_session.commit()

        # 事务应该已提交
        stmt = select(TestTeam).where(TestTeam.short_name.in_(["TT1", "TT2"]))
        result = await test_db_session.execute(stmt)
        teams = result.scalars().all()

        assert len(teams) == 2

    async def test_transaction_rollback(self, test_db_session: AsyncSession):
        """测试事务回滚"""
        try:
            async with test_db_session.begin():
                team = TestTeam(
                    name="Rollback Team", short_name="RT", country="Country"
                )
                test_db_session.add(team)

                # 故意抛出异常触发回滚
                raise Exception("Test rollback")

        except Exception:
            pass  # 预期的异常

        # 验证数据未被保存
        stmt = select(TestTeam).where(TestTeam.short_name == "RT")
        result = await test_db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_bulk_operations_performance(self, test_db_session: AsyncSession):
        """测试批量操作性能"""
        import time

        # 创建大量球队数据
        teams = []
        for i in range(50):  # 减少数量以提高测试速度
            team = TestTeam(
                name=f"Performance Team {i}",
                short_name=f"PT{i}",
                country="Test Country",
                founded_year=2020 + (i % 10),
            )
            teams.append(team)

        # 测试批量插入性能
        start_time = time.time()

        test_db_session.add_all(teams)
        await test_db_session.commit()

        end_time = time.time()
        insert_time = end_time - start_time

        # 验证插入性能（应该在1秒内完成）
        assert insert_time < 1.0

        # 验证数据插入成功
        stmt = select(TestTeam).where(TestTeam.name.like("Performance Team%"))
        result = await test_db_session.execute(stmt)
        inserted_teams = result.scalars().all()

        assert len(inserted_teams) == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
