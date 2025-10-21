"""
数据库查询优化集成测试
测试各种查询模式的性能和正确性
"""

import pytest
from sqlalchemy import text, select, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from datetime import datetime, timezone, timedelta
import time


class TestDatabaseQueries:
    """数据库查询测试"""

    @pytest.mark.asyncio
    async def test_simple_select(self, db_session):
        """测试简单查询"""
        from src.database.models import Team

        # 创建测试数据
        _teams = []
        for i in range(10):
            team = Team(
                name=f"Query Team {i}", city=f"Query City {i}", founded=2000 + i
            )
            teams.append(team)
        db_session.add_all(teams)
        await db_session.commit()

        # 简单查询
        _result = await db_session.execute(select(Team).where(Team.founded > 2005))
        _teams = result.scalars().all()

        assert len(teams) == 4  # 2006-2009
        assert all(team.founded > 2005 for team in teams)

    @pytest.mark.asyncio
    async def test_complex_join(self, db_session):
        """测试复杂连接查询"""
        from src.database.models import Team, Match, Prediction, User

        # 创建测试数据
        _teams = []
        for i in range(6):
            team = Team(name=f"Join Team {i}", city="Join City", founded=2000 + i)
            teams.append(team)
        db_session.add_all(teams)
        await db_session.commit()

        # 创建比赛
        _matches = []
        for i in range(5):
            match = Match(
                home_team_id=teams[i].id,
                away_team_id=teams[i + 1].id,
                match_date=datetime.now(timezone.utc),
                competition="Join League",
                season="2024/2025",
                status="COMPLETED",
                home_score=2,
                away_score=1,
            )
            matches.append(match)
        db_session.add_all(matches)
        await db_session.commit()

        # 创建用户和预测
        _user = User(
            username="join_user",
            email="join@example.com",
            password_hash="hashed",
            role="user",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        predictions = []
        for match in matches:
            pred = Prediction(
                user_id=user.id,
                match_id=match.id,
                _prediction="HOME_WIN",
                confidence=0.8,
                status="COMPLETED",
                is_correct=True,
            )
            predictions.append(pred)
        db_session.add_all(predictions)
        await db_session.commit()

        # 复杂连接查询
        _result = await db_session.execute(
            text(
                """
            SELECT
                t.name as team_name,
                COUNT(m.id) as total_matches,
                COUNT(p.id) as predictions_count,
                AVG(p.confidence) as avg_confidence
            FROM teams t
            LEFT JOIN matches m ON (t.id = m.home_team_id OR t.id = m.away_team_id)
            LEFT JOIN predictions p ON m.id = p.match_id
            WHERE t.name LIKE 'Join Team%'
            GROUP BY t.id, t.name
            ORDER BY total_matches DESC
        """
            )
        )

        rows = result.fetchall()
        assert len(rows) == 6
        assert rows[0].total_matches == 2  # Team 0 和 Team 5 各参与 1 场，其他参与 2 场

    @pytest.mark.asyncio
    async def test_aggregation_queries(self, db_session):
        """测试聚合查询"""
        from src.database.models import Prediction, User

        # 创建用户
        users = []
        for i in range(5):
            _user = User(
                username=f"agg_user_{i}",
                email=f"agg{i}@example.com",
                password_hash="hashed",
                role="user",
            )
            users.append(user)
        db_session.add_all(users)
        await db_session.commit()

        # 创建预测数据
        predictions = []
        for user in users:
            for i in range(20):
                pred = Prediction(
                    user_id=user.id,
                    match_id=1,
                    _prediction="HOME_WIN" if i % 2 == 0 else "DRAW",
                    confidence=0.5 + (i * 0.025),
                    status="COMPLETED" if i < 15 else "PENDING",
                    is_correct=(i % 3 == 0),
                    created_at=datetime.now(timezone.utc) - timedelta(days=i),
                )
                predictions.append(pred)
        db_session.add_all(predictions)
        await db_session.commit()

        # 测试各种聚合函数
        _result = await db_session.execute(
            select(
                func.count(Prediction.id).label("total"),
                func.avg(Prediction.confidence).label("avg_confidence"),
                func.max(Prediction.confidence).label("max_confidence"),
                func.min(Prediction.confidence).label("min_confidence"),
                func.sum(func.cast(Prediction.is_correct, int)).label("correct_count"),
            ).where(Prediction.user_id == users[0].id)
        )

        row = result.first()
        assert row.total == 20
        assert row.avg_confidence == pytest.approx(0.7375, rel=1e-2)
        assert row.correct_count == 7  # 0, 3, 6, 9, 12, 15, 18

    @pytest.mark.asyncio
    async def test_window_functions(self, db_session):
        """测试窗口函数"""
        from src.database.models import User, Prediction

        # 创建用户
        users = []
        for i in range(3):
            _user = User(
                username=f"window_user_{i}",
                email=f"window{i}@example.com",
                password_hash="hashed",
                role="user",
            )
            users.append(user)
        db_session.add_all(users)
        await db_session.commit()

        # 创建不同时间的预测
        predictions = []
        for user_idx, user in enumerate(users):
            for i in range(5):
                pred = Prediction(
                    user_id=user.id,
                    match_id=1,
                    _prediction="HOME_WIN",
                    confidence=0.5 + (i * 0.1),
                    status="COMPLETED",
                    is_correct=(i + user_idx) % 2 == 0,
                    created_at=datetime.now(timezone.utc) - timedelta(hours=i),
                )
                predictions.append(pred)
        db_session.add_all(predictions)
        await db_session.commit()

        # 使用窗口函数查询
        _result = await db_session.execute(
            text(
                """
            SELECT
                u.username,
                p.confidence,
                ROW_NUMBER() OVER (PARTITION BY u.id ORDER BY p.created_at) as rn,
                LAG(p.confidence) OVER (PARTITION BY u.id ORDER BY p.created_at) as prev_confidence,
                AVG(p.confidence) OVER (PARTITION BY u.id ORDER BY p.created_at
                    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as moving_avg
            FROM users u
            JOIN predictions p ON u.id = p.user_id
            ORDER BY u.id, p.created_at
        """
            )
        )

        rows = result.fetchall()
        assert len(rows) == 15
        # 验证窗口函数结果
        for i, row in enumerate(rows):
            if i % 5 == 0:  # 每个用户的第一条记录
                assert row.rn == 1
                assert row.prev_confidence is None
            else:
                assert row.rn == (i % 5) + 1

    @pytest.mark.asyncio
    async def test_subqueries(self, db_session):
        """测试子查询"""
        from src.database.models import User, Prediction, Team, Match

        # 创建测试数据
        _teams = []
        for i in range(4):
            team = Team(name=f"Sub Team {i}", city="Sub City", founded=2000 + i)
            teams.append(team)
        db_session.add_all(teams)
        await db_session.commit()

        # 创建比赛
        match = Match(
            home_team_id=teams[0].id,
            away_team_id=teams[1].id,
            match_date=datetime.now(timezone.utc),
            competition="Sub League",
            season="2024/2025",
            status="COMPLETED",
            home_score=2,
            away_score=1,
        )
        db_session.add(match)
        await db_session.commit()
        await db_session.refresh(match)

        # 创建用户
        users = []
        for i in range(5):
            _user = User(
                username=f"sub_user_{i}",
                email=f"sub{i}@example.com",
                password_hash="hashed",
                role="user",
            )
            users.append(user)
            db_session.add(user)
        await db_session.commit()

        # 获取用户 ID
        user_ids = [u.id for u in users]

        # 创建预测
        predictions = []
        for i, user_id in enumerate(user_ids):
            pred = Prediction(
                user_id=user_id,
                match_id=match.id,
                _prediction="HOME_WIN",
                confidence=0.5 + (i * 0.1),
                status="COMPLETED",
                is_correct=(i % 2 == 0),
            )
            predictions.append(pred)
        db_session.add_all(predictions)
        await db_session.commit()

        # 使用子查询查找预测准确率高于平均的用户
        _result = await db_session.execute(
            text(
                """
            SELECT u.username, u.email
            FROM users u
            WHERE u.id IN (
                SELECT p.user_id
                FROM predictions p
                WHERE p.status = 'COMPLETED'
                GROUP BY p.user_id
                HAVING AVG(CAST(p.is_correct AS INT)) > (
                    SELECT AVG(CAST(p2.is_correct AS INT))
                    FROM predictions p2
                    WHERE p2.status = 'COMPLETED'
                )
            )
        """
            )
        )

        rows = result.fetchall()
        # 平均准确率应该是 0.6 (3/5)，高于平均的用户是 user_0, user_2, user_4
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_cte_queries(self, db_session):
        """测试公用表表达式 (CTE)"""
        from src.database.models import Team, Match

        # 创建测试数据
        _teams = []
        for i in range(6):
            team = Team(name=f"CTE Team {i}", city="CTE City", founded=2000 + i)
            teams.append(team)
        db_session.add_all(teams)
        await db_session.commit()

        # 创建比赛数据
        for i in range(5):
            match = Match(
                home_team_id=teams[i].id,
                away_team_id=teams[i + 1].id,
                match_date=datetime.now(timezone.utc) + timedelta(days=i),
                competition="CTE League",
                season="2024/2025",
                status="UPCOMING" if i > 2 else "COMPLETED",
                home_score=0 if i > 2 else (i + 1),
                away_score=0 if i > 2 else i,
            )
            db_session.add(match)
        await db_session.commit()

        # 使用 CTE 查询
        _result = await db_session.execute(
            text(
                """
            WITH team_stats AS (
                SELECT
                    t.id,
                    t.name,
                    COUNT(m.id) as total_matches,
                    SUM(m.home_score + m.away_score) as total_goals
                FROM teams t
                LEFT JOIN matches m ON (t.id = m.home_team_id OR t.id = m.away_team_id)
                WHERE m.status = 'COMPLETED'
                GROUP BY t.id, t.name
            ),
            avg_goals AS (
                SELECT AVG(total_goals) as avg_goals_per_team
                FROM team_stats
                WHERE total_matches > 0
            )
            SELECT
                ts.name,
                ts.total_matches,
                ts.total_goals,
                ag.avg_goals_per_team
            FROM team_stats ts
            CROSS JOIN avg_goals ag
            WHERE ts.total_goals > ag.avg_goals_per_team
        """
            )
        )

        rows = result.fetchall()
        # Team 0, Team 1, Team 2 参与了完成的比赛并有进球
        assert len(rows) == 2  # 只有进球数高于平均的队伍

    @pytest.mark.asyncio
    async def test_eager_loading(self, db_session):
        """测试预加载 (eager loading)"""
        from src.database.models import User, Prediction

        # 创建用户和预测
        users = []
        for i in range(3):
            _user = User(
                username=f"eager_user_{i}",
                email=f"eager{i}@example.com",
                password_hash="hashed",
                role="user",
            )
            users.append(user)
            db_session.add(user)
        await db_session.commit()

        # 获取用户 ID
        user_ids = [u.id for u in users]

        # 创建预测
        predictions = []
        for user_id in user_ids:
            for i in range(5):
                pred = Prediction(
                    user_id=user_id,
                    match_id=1,
                    _prediction="HOME_WIN",
                    confidence=0.5 + (i * 0.1),
                    status="COMPLETED",
                    is_correct=(i % 2 == 0),
                )
                predictions.append(pred)
                db_session.add(pred)
        await db_session.commit()

        # 使用 selectinload 预加载
        start_time = time.time()
        _result = await db_session.execute(
            select(User).options(selectinload(User.predictions))
        )
        users_with_predictions = result.scalars().unique().all()
        selectinload_time = time.time() - start_time

        # 验证预加载的数据
        for user in users_with_predictions:
            assert len(user.predictions) == 5

        # 使用 joinedload 预加载
        start_time = time.time()
        _result = await db_session.execute(
            select(User).options(joinedload(User.predictions))
        )
        users_with_predictions_joined = result.scalars().unique().all()
        joinedload_time = time.time() - start_time

        # 验证结果一致
        assert len(users_with_predictions) == len(users_with_predictions_joined)
        assert len(users_with_predictions) == 3

        # 性能比较（joinedload 应该更快）
        assert joinedload_time <= selectinload_time * 2  # 允许一定误差

    @pytest.mark.asyncio
    async def test_pagination(self, db_session):
        """测试分页查询"""
        from src.database.models import Team

        # 创建测试数据
        _teams = []
        for i in range(25):
            team = Team(
                name=f"Page Team {i:02d}", city=f"Page City {i}", founded=2000 + i
            )
            teams.append(team)
        db_session.add_all(teams)
        await db_session.commit()

        # 测试分页
        page_size = 10
        page = 1
        all_teams = []

        while True:
            offset = (page - 1) * page_size
            _result = await db_session.execute(
                select(Team).order_by(Team.founded).offset(offset).limit(page_size)
            )
            page_teams = result.scalars().all()

            if not page_teams:
                break

            all_teams.extend(page_teams)
            page += 1

        # 验证分页结果
        assert len(all_teams) == 25
        assert all_teams[0].name == "Page Team 00"
        assert all_teams[-1].name == "Page Team 24"

        # 测试计数查询
        _result = await db_session.execute(select(func.count(Team.id)))
        total_count = result.scalar()
        assert total_count == 25

    @pytest.mark.asyncio
    async def test_index_hints(self, db_session):
        """测试索引提示"""
        from src.database.models import User, Prediction

        # 创建大量数据
        users = []
        for i in range(100):
            _user = User(
                username=f"index_user_{i:03d}",
                email=f"index{i:03d}@example.com",
                password_hash="hashed",
                role="user",
            )
            users.append(user)
            db_session.add(user)
        await db_session.commit()

        # 创建预测
        predictions = []
        for user in users:
            for j in range(10):
                pred = Prediction(
                    user_id=user.id,
                    match_id=1,
                    _prediction="HOME_WIN",
                    confidence=0.5 + (j * 0.05),
                    status="COMPLETED",
                    is_correct=(j % 2 == 0),
                )
                predictions.append(pred)
                db_session.add(pred)
        await db_session.commit()

        # 使用索引优化查询
        start_time = time.time()
        _result = await db_session.execute(
            select(Prediction)
            .where(Prediction.user_id.in_([u.id for u in users[:10]]))
            .order_by(Prediction.created_at.desc())
        )
        predictions = result.scalars().all()
        query_time = time.time() - start_time

        # 验证性能
        assert len(predictions) == 100
        assert query_time < 0.5  # 应该很快

        # 验证排序正确
        for i in range(len(predictions) - 1):
            assert predictions[i].created_at >= predictions[i + 1].created_at
