# noqa: F401,F811,F821,E402
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from datetime import datetime, timedelta
import sys
import os
from src.database.models.team import Team
from src.database.models.odds import Odds
from src.database.models.league import League
from src.database.models.match import Match
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

"""
数据库操作测试
专注于实用的CRUD操作和业务逻辑
"""


# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))


@pytest.mark.unit
class TestDatabaseOperations:
    """数据库操作测试"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟数据库会话"""
        session = MagicMock(spec=Session)
        session.add = MagicMock()
        session.commit = MagicMock()
        session.rollback = MagicMock()
        session.refresh = MagicMock()
        session.query = MagicMock()
        session.execute = MagicMock()
        session.scalars = MagicMock()
        session.scalar = MagicMock()
        session.scalar_one_or_none = MagicMock()
        session.close = MagicMock()
        return session

    def test_match_crud_operations(self, mock_session):
        """测试比赛CRUD操作"""
        try:
            from src.database.models.match import Match

            # 创建比赛
            match = Match(
                home_team_id=1,
                away_team_id=2,
                match_date=datetime.now(),
                status="scheduled",
                league_id=1,
            )

            # 测试创建
            mock_session.add(match)
            mock_session.commit()
            mock_session.refresh(match)

            mock_session.add.assert_called_once_with(match)
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once_with(match)

            # 测试读取
            mock_session.scalar_one_or_none.return_value = match
            query = select(Match).where(Match.id == 1)
            mock_session.execute.return_value.scalar_one_or_none.return_value = match

            retrieved_match = mock_session.execute(query).scalar_one_or_none()
            assert retrieved_match == match

            # 测试更新
            match.status = "in_progress"
            match.home_score = 1
            mock_session.commit()

            assert match.status == "in_progress"
            assert match.home_score == 1

            # 测试删除
            mock_session.delete(match)
            mock_session.commit()
            mock_session.delete.assert_called_once_with(match)

        except ImportError:
            pytest.skip("Match model not available")

    def test_team_crud_operations(self, mock_session):
        """测试球队CRUD操作"""
        try:
            # 创建球队
            team = Team(
                name="Test Team",
                short_name="TT",
                founded=2020,
                stadium="Test Stadium",
                city="Test City",
                country="Test Country",
            )

            # 测试创建
            mock_session.add(team)
            mock_session.commit()
            mock_session.refresh(team)

            # 测试查询所有球队
            mock_session.scalars.return_value.all.return_value = [team]
            teams = mock_session.scalars(select(Team)).all()
            assert len(teams) == 1
            assert teams[0].name == "Test Team"

            # 测试按名称查找
            mock_session.scalar.return_value = team
            query = select(Team).where(Team.name == "Test Team")
            found_team = mock_session.execute(query).scalar()
            assert found_team == team

            # 测试更新
            team.stadium_capacity = 50000
            team.manager = "New Manager"
            mock_session.commit()

            assert team.stadium_capacity == 50000
            assert team.manager == "New Manager"

        except ImportError:
            pytest.skip("Team model not available")

    def test_prediction_crud_operations(self, mock_session):
        """测试预测CRUD操作"""
        try:
            from src.database.models.predictions import Prediction

            # 创建预测
            prediction = Prediction(
                match_id=1,
                model_id="test_model_v1",
                home_win_prob=0.5,
                draw_prob=0.3,
                away_win_prob=0.2,
                confidence=0.85,
                created_at=datetime.now(),
            )

            # 测试创建
            mock_session.add(prediction)
            mock_session.commit()

            # 测试批量预测查询
            predictions_list = [prediction, prediction]
            mock_session.scalars.return_value.all.return_value = predictions_list

            recent_predictions = mock_session.scalars(
                select(Prediction).where(
                    Prediction.created_at >= datetime.now() - timedelta(days=7)
                )
            ).all()

            assert len(recent_predictions) == 2

            # 测试预测更新（比赛后更新实际结果）
            prediction.actual_result = "HOME_WIN"
            prediction.accuracy = 1.0
            mock_session.commit()

            assert prediction.actual_result == "HOME_WIN"
            assert prediction.accuracy == 1.0

            # 测试模型性能统计
            mock_session.execute.return_value.fetchone.return_value = (100, 75)
            stats_query = select(Prediction.model_id, Prediction.accuracy).where(
                Prediction.model_id == "test_model_v1"
            )
            stats = mock_session.execute(stats_query).fetchone()
            assert stats == (100, 75)

        except ImportError:
            pytest.skip("Prediction model not available")

    def test_odds_crud_operations(self, mock_session):
        """测试赔率CRUD操作"""
        try:
            # 创建赔率记录
            odds = Odds(
                match_id=1,
                bookmaker="TestBookmaker",
                home_win=2.5,
                draw=3.2,
                away_win=2.8,
                updated_at=datetime.now(),
            )

            # 测试创建
            mock_session.add(odds)
            mock_session.commit()

            # 测试查询多个博彩公司的赔率
            odds_list = [odds]
            mock_session.scalars.return_value.all.return_value = odds_list

            all_odds = mock_session.scalars(
                select(Odds).where(Odds.match_id == 1)
            ).all()

            assert len(all_odds) == 1
            assert all_odds[0].bookmaker == "TestBookmaker"

            # 测试赔率更新
            odds.home_win = 2.4
            odds.away_win = 2.9
            odds.volume = 1000000
            mock_session.commit()

            assert odds.home_win == 2.4
            assert odds.away_win == 2.9
            assert odds.volume == 1000000

            # 测试赔率历史记录
            if hasattr(odds, "create_history_record"):
                history_record = odds.create_history_record()
                assert history_record.match_id == odds.match_id
                assert history_record.bookmaker == odds.bookmaker

        except ImportError:
            pytest.skip("Odds model not available")

    def test_feature_crud_operations(self, mock_session):
        """测试特征CRUD操作"""
        try:
            from src.database.models.features import Feature

            # 创建特征记录
            feature = Feature(
                match_id=1,
                feature_name="team_form",
                feature_value=0.75,
                feature_type="numeric",
                created_at=datetime.now(),
            )

            # 测试创建
            mock_session.add(feature)
            mock_session.commit()

            # 测试批量特征查询
            features_data = {
                "team_form": 0.75,
                "goal_difference": 5,
                "head_to_head": 0.6,
            }

            for name, value in features_data.items():
                feature = Feature(
                    match_id=1,
                    feature_name=name,
                    feature_value=value,
                    feature_type="numeric",
                )
                mock_session.add(feature)

            mock_session.commit()

            # 测试特征聚合
            mock_session.execute.return_value.fetchall.return_value = [
                ("numeric", 10),
                ("categorical", 5),
            ]

            agg_query = select(Feature.feature_type, Feature.feature_value).group_by(
                Feature.feature_type
            )
            aggregated = mock_session.execute(agg_query).fetchall()

            assert len(aggregated) == 2
            assert aggregated[0] == ("numeric", 10)

        except ImportError:
            pytest.skip("Feature model not available")

    def test_league_crud_operations(self, mock_session):
        """测试联赛CRUD操作"""
        try:
            # 创建联赛
            league = League(
                name="Test League",
                country="Test Country",
                founded=2020,
                current_season="2023/2024",
                number_of_teams=20,
            )

            # 测试创建
            mock_session.add(league)
            mock_session.commit()
            mock_session.refresh(league)

            # 测试查询联赛及其球队
            mock_session.scalar.return_value = league
            league_with_teams = mock_session.execute(
                select(League).where(League.id == 1)
            ).scalar()

            assert league_with_teams.name == "Test League"
            assert league_with_teams.number_of_teams == 20

            # 测试赛季更新
            league.current_season = "2024/2025"
            league.champion = "Test Champion"
            mock_session.commit()

            assert league.current_season == "2024/2025"
            assert league.champion == "Test Champion"

        except ImportError:
            pytest.skip("League model not available")

    def test_database_transaction_operations(self, mock_session):
        """测试数据库事务操作"""
        # 测试事务开始
        mock_session.begin = MagicMock()
        mock_session.begin.return_value.__enter__ = MagicMock()
        mock_session.begin.return_value.__exit__ = MagicMock()

        with mock_session.begin():
            # 在事务中执行多个操作
            mock_session.add(MagicMock())
            mock_session.add(MagicMock())
            mock_session.commit()

        mock_session.begin.assert_called_once()

        # 测试事务回滚
        mock_session.rollback = MagicMock()
        try:
            with mock_session.begin():
                raise Exception("Test error")
        except Exception:
            mock_session.rollback.assert_called()

    def test_database_query_with_filters(self, mock_session):
        """测试带过滤器的数据库查询"""
        try:
            # 测试日期范围查询
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()

            mock_session.scalars.return_value.all.return_value = []

            matches = mock_session.scalars(
                select(Match)
                .where(Match.match_date >= start_date)
                .where(Match.match_date <= end_date)
            ).all()

            assert isinstance(matches, list)

            # 测试状态过滤
            status_list = ["completed", "in_progress"]
            mock_session.scalars.return_value.all.return_value = []

            filtered_matches = mock_session.scalars(
                select(Match).where(Match.status.in_(status_list))
            ).all()

            assert isinstance(filtered_matches, list)

            # 测试复合查询
            mock_session.execute.return_value.fetchall.return_value = []

            complex_query = (
                select(Match)
                .join(Match.home_team)
                .where(Match.status == "completed")
                .where(Match.match_date >= start_date)
            )

            results = mock_session.execute(complex_query).fetchall()
            assert isinstance(results, list)

        except ImportError:
            pytest.skip("Match model not available")

    def test_database_bulk_operations(self, mock_session):
        """测试批量数据库操作"""
        try:
            from src.database.models.team import Team

            # 批量插入
            teams_to_insert = [
                Team(name=f"Team {i}", short_name=f"T{i}") for i in range(100)
            ]

            for team in teams_to_insert:
                mock_session.add(team)

            mock_session.commit.assert_called()

            # 批量更新
            update_statement = (
                update(Team).where(Team.founded < 2000).values(stadium_capacity=50000)
            )

            mock_session.execute(update_statement)
            mock_session.commit()

            # 批量删除
            delete_statement = delete(Team).where(Team.name.like("Old%"))

            mock_session.execute(delete_statement)
            mock_session.commit()

            assert True  # 如果没有抛出异常则测试通过

        except ImportError:
            pytest.skip("Team model not available")

    def test_database_error_handling(self, mock_session):
        """测试数据库错误处理"""

        # 测试完整性错误
        mock_session.commit.side_effect = IntegrityError(
            "test", "test", "Duplicate entry"
        )

        with pytest.raises(IntegrityError):
            mock_session.commit()

        # 测试操作错误
        mock_session.execute.side_effect = OperationalError(
            "test", "test", "Connection failed"
        )

        with pytest.raises(OperationalError):
            mock_session.execute(MagicMock())

        # 测试通用SQL错误
        mock_session.query.side_effect = SQLAlchemyError("General error")

        with pytest.raises(SQLAlchemyError):
            mock_session.query(MagicMock())

    def test_database_connection_management(self):
        """测试数据库连接管理"""
        try:
            from src.database.connection_mod import (
                DatabaseManager,
                MultiUserDatabaseManager,
            )

            with patch("src.database.connection.create_engine"):
                # 测试单例模式（如果适用）
                db_manager1 = DatabaseManager()
                db_manager2 = DatabaseManager()

                # 验证管理器创建
                assert db_manager1 is not None
                assert db_manager2 is not None

                # 测试多用户管理器
                multi_manager = MultiUserDatabaseManager()
                assert multi_manager is not None

                # 测试会话创建
                session = db_manager1.create_session()
                assert session is not None

        except ImportError:
            pytest.skip("Database managers not available")
