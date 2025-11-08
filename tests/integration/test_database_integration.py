"""
数据库集成测试
Database Integration Tests

测试数据库操作的完整功能，包括模型CRUD、事务处理和数据完整性。
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Match, Prediction, Team


@pytest.mark.integration
@pytest.mark.db_integration
class TestDatabaseModels:
    """数据库模型集成测试"""

    async def test_team_crud_operations(self, test_db_session: AsyncSession):
        """测试球队CRUD操作"""
        # Create
        team = Team(
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
        stmt = select(Team).where(Team.id == team.id)
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

    async def test_match_crud_operations(
        self, test_db_session: AsyncSession, sample_data
    ):
        """测试比赛CRUD操作"""
        teams = sample_data["teams"]
        match = sample_data["match"]

        # Update match
        match.home_score = 2
        match.away_score = 1
        match.status = "finished"
        await test_db_session.commit()
        await test_db_session.refresh(match)

        assert match.home_score == 2
        assert match.away_score == 1
        assert match.status == "finished"

        # Query match with teams
        stmt = (
            select(Match, Team)
            .join(Team, Match.home_team_id == Team.id)
            .where(Match.id == match.id)
        )
        result = await test_db_session.execute(stmt)
        match_with_team = result.first()

        assert match_with_team is not None
        assert match_with_team[0].id == match.id
        assert match_with_team[1].id == teams[0].id

    async def test_prediction_crud_operations(
        self, test_db_session: AsyncSession, sample_data
    ):
        """测试预测CRUD操作"""
        match = sample_data["match"]

        # Create prediction
        prediction = Prediction(
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
        stmt = select(Prediction).where(Prediction.match_id == match.id)
        result = await test_db_session.execute(stmt)
        predictions = result.scalars().all()

        assert len(predictions) == 1
        assert predictions[0].predicted_outcome == "home"


@pytest.mark.integration
@pytest.mark.db_integration
class TestDatabaseTransactions:
    """数据库事务集成测试"""

    async def test_transaction_commit(self, test_db_session: AsyncSession):
        """测试事务提交"""
        # 开始事务
        async with test_db_session.begin():
            team1 = Team(name="Team 1", short_name="T1", country="Country")
            team2 = Team(name="Team 2", short_name="T2", country="Country")

            test_db_session.add(team1)
            test_db_session.add(team2)

        # 事务应该已提交
        stmt = select(Team).where(Team.short_name.in_(["T1", "T2"]))
        result = await test_db_session.execute(stmt)
        teams = result.scalars().all()

        assert len(teams) == 2

    async def test_transaction_rollback(self, test_db_session: AsyncSession):
        """测试事务回滚"""
        try:
            async with test_db_session.begin():
                team = Team(name="Rollback Team", short_name="RT", country="Country")
                test_db_session.add(team)

                # 故意抛出异常触发回滚
                raise Exception("Test rollback")

        except Exception:
            pass  # 预期的异常

        # 验证数据未被保存
        stmt = select(Team).where(Team.short_name == "RT")
        result = await test_db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_nested_transactions(self, test_db_session: AsyncSession):
        """测试嵌套事务"""
        async with test_db_session.begin():
            # 外层事务
            team1 = Team(name="Outer Team", short_name="OT", country="Country")
            test_db_session.add(team1)

            try:
                async with test_db_session.begin_nested():
                    # 内层事务
                    team2 = Team(name="Inner Team", short_name="IT", country="Country")
                    test_db_session.add(team2)

                    # 内层事务正常提交
            except Exception:
                pass

            # 外层事务继续
            team3 = Team(name="Third Team", short_name="TT", country="Country")
            test_db_session.add(team3)

        # 验证外层事务提交了
        stmt = select(Team).where(Team.short_name.in_(["OT", "TT"]))
        result = await test_db_session.execute(stmt)
        teams = result.scalars().all()

        assert len(teams) == 2


@pytest.mark.integration
@pytest.mark.db_integration
class TestDatabaseRelationships:
    """数据库关系集成测试"""

    async def test_match_team_relationship(
        self, test_db_session: AsyncSession, sample_data
    ):
        """测试比赛与球队关系"""
        teams = sample_data["teams"]
        match = sample_data["match"]

        # 测试从比赛访问球队
        await test_db_session.refresh(match)
        await test_db_session.refresh(teams[0])
        await test_db_session.refresh(teams[1])

        # 通过关系查询
        stmt = select(Match).where(Match.id == match.id)
        result = await test_db_session.execute(stmt)
        fetched_match = result.scalar_one()

        # 验证关系存在
        assert fetched_match.home_team_id == teams[0].id
        assert fetched_match.away_team_id == teams[1].id

    async def test_prediction_match_relationship(
        self, test_db_session: AsyncSession, sample_data
    ):
        """测试预测与比赛关系"""
        match = sample_data["match"]

        # 创建多个预测
        predictions = [
            Prediction(
                match_id=match.id,
                home_win_prob=0.5,
                draw_prob=0.3,
                away_win_prob=0.2,
                predicted_outcome="home",
                confidence=0.7,
                model_version="model_v1",
            ),
            Prediction(
                match_id=match.id,
                home_win_prob=0.4,
                draw_prob=0.4,
                away_win_prob=0.2,
                predicted_outcome="draw",
                confidence=0.6,
                model_version="model_v2",
            ),
        ]

        for pred in predictions:
            test_db_session.add(pred)
        await test_db_session.commit()

        # 查询比赛的所有预测
        stmt = select(Prediction).where(Prediction.match_id == match.id)
        result = await test_db_session.execute(stmt)
        match_predictions = result.scalars().all()

        assert len(match_predictions) == 2
        assert all(pred.match_id == match.id for pred in match_predictions)


@pytest.mark.integration
@pytest.mark.db_integration
class TestDatabaseConstraints:
    """数据库约束集成测试"""

    async def test_unique_constraints(self, test_db_session: AsyncSession):
        """测试唯一约束"""
        # 创建第一个球队
        team1 = Team(name="Unique Team", short_name="UT", country="Country")
        test_db_session.add(team1)
        await test_db_session.commit()

        # 尝试创建重复的short_name
        team2 = Team(name="Another Team", short_name="UT", country="Country")
        test_db_session.add(team2)

        # 应该抛出约束违反异常
        with pytest.raises(Exception):  # 具体异常类型可能因数据库而异
            await test_db_session.commit()

    async def test_foreign_key_constraints(self, test_db_session: AsyncSession):
        """测试外键约束"""
        # 尝试创建指向不存在比赛的预测
        prediction = Prediction(
            match_id=99999,  # 不存在的比赛ID
            home_win_prob=0.5,
            draw_prob=0.3,
            away_win_prob=0.2,
            predicted_outcome="home",
            confidence=0.7,
            model_version="test_model",
        )

        test_db_session.add(prediction)

        # 应该抛出外键约束违反异常
        with pytest.raises(Exception):  # 具体异常类型可能因数据库而异
            await test_db_session.commit()

    async def test_not_null_constraints(self, test_db_session: AsyncSession):
        """测试非空约束"""
        # 尝试创建没有必需字段的球队
        team = Team()  # 没有设置name
        test_db_session.add(team)

        # 应该抛出非空约束违反异常
        with pytest.raises(Exception):  # 具体异常类型可能因数据库而异
            await test_db_session.commit()


@pytest.mark.integration
@pytest.mark.db_integration
class TestDatabasePerformance:
    """数据库性能集成测试"""

    async def test_bulk_insert_performance(self, test_db_session: AsyncSession):
        """测试批量插入性能"""
        import time

        # 创建大量球队数据
        teams = []
        for i in range(100):
            team = Team(
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
        stmt = select(Team).where(Team.name.like("Performance Team%"))
        result = await test_db_session.execute(stmt)
        inserted_teams = result.scalars().all()

        assert len(inserted_teams) == 100

    async def test_query_performance(self, test_db_session: AsyncSession):
        """测试查询性能"""
        import time

        # 创建测试数据
        teams = []
        for i in range(50):
            team = Team(
                name=f"Query Team {i}", short_name=f"QT{i}", country="Test Country"
            )
            teams.append(team)

        test_db_session.add_all(teams)
        await test_db_session.commit()

        # 测试查询性能
        start_time = time.time()

        stmt = select(Team).where(Team.name.like("Query Team%"))
        result = await test_db_session.execute(stmt)
        queried_teams = result.scalars().all()

        end_time = time.time()
        query_time = end_time - start_time

        # 验证查询性能（应该在0.1秒内完成）
        assert query_time < 0.1
        assert len(queried_teams) == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
