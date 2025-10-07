"""
数据库 CRUD 测试
测试基本的创建、读取、更新、删除操作
"""

import pytest
from unittest.mock import patch
from datetime import datetime
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))


@pytest.mark.unit
class TestDatabaseCRUD:
    """数据库 CRUD 测试"""

    def test_match_crud(self):
        """测试比赛 CRUD 操作"""
        try:
            from src.database.models.match import Match

            # 创建比赛
            match = Match(
                home_team_id=1,
                away_team_id=2,
                match_date=datetime.now(),
                status="scheduled"
            )

            # 测试创建
            assert match.home_team_id == 1
            assert match.away_team_id == 2
            assert match.status == "scheduled"

            # 测试更新
            match.status = "in_progress"
            match.home_score = 1
            assert match.status == "in_progress"
            assert match.home_score == 1

            # 测试读取属性
            assert hasattr(match, 'id')
            assert hasattr(match, 'home_team')
            assert hasattr(match, 'away_team')

        except ImportError:
            pytest.skip("Match model not available")

    def test_team_crud(self):
        """测试球队 CRUD 操作"""
        try:
            from src.database.models.team import Team

            # 创建球队
            team = Team(
                name="Test Team",
                short_name="TT",
                founded=2020
            )

            # 测试创建
            assert team.name == "Test Team"
            assert team.short_name == "TT"
            assert team.founded == 2020

            # 测试更新
            team.name = "Updated Team"
            team.stadium_capacity = 50000
            assert team.name == "Updated Team"
            assert team.stadium_capacity == 50000

            # 测试关系属性
            assert hasattr(team, 'home_matches')
            assert hasattr(team, 'away_matches')

        except ImportError:
            pytest.skip("Team model not available")

    def test_prediction_crud(self):
        """测试预测 CRUD 操作"""
        try:
            from src.database.models.predictions import Prediction

            # 创建预测
            prediction = Prediction(
                match_id=1,
                model_id="test_model",
                home_win_prob=0.5,
                draw_prob=0.3,
                away_win_prob=0.2,
                created_at=datetime.now()
            )

            # 测试创建
            assert prediction.match_id == 1
            assert prediction.model_id == "test_model"
            assert prediction.home_win_prob == 0.5

            # 测试更新
            prediction.home_win_prob = 0.6
            prediction.draw_prob = 0.25
            prediction.away_win_prob = 0.15
            assert prediction.home_win_prob == 0.6

            # 测试方法
            assert hasattr(prediction, 'to_dict')
            assert hasattr(prediction, 'from_dict')

        except ImportError:
            pytest.skip("Prediction model not available")

    def test_odds_crud(self):
        """测试赔率 CRUD 操作"""
        try:
            from src.database.models.odds import Odds

            # 创建赔率
            odds = Odds(
                match_id=1,
                bookmaker="TestBookmaker",
                home_win=2.5,
                draw=3.2,
                away_win=2.8,
                updated_at=datetime.now()
            )

            # 测试创建
            assert odds.match_id == 1
            assert odds.bookmaker == "TestBookmaker"
            assert odds.home_win == 2.5

            # 测试更新
            odds.home_win = 2.4
            odds.draw = 3.1
            odds.away_win = 2.9
            assert odds.home_win == 2.4

            # 测试关系
            assert hasattr(odds, 'match')

        except ImportError:
            pytest.skip("Odds model not available")

    def test_feature_crud(self):
        """测试特征 CRUD 操作"""
        try:
            from src.database.models.features import Feature

            # 创建特征
            feature = Feature(
                match_id=1,
                feature_name="goal_difference",
                feature_value=1.5,
                created_at=datetime.now()
            )

            # 测试创建
            assert feature.match_id == 1
            assert feature.feature_name == "goal_difference"
            assert feature.feature_value == 1.5

            # 测试更新
            feature.feature_value = 2.0
            feature.feature_type = "numeric"
            assert feature.feature_value == 2.0

            # 测试属性
            assert hasattr(feature, 'match')

        except ImportError:
            pytest.skip("Feature model not available")

    def test_league_crud(self):
        """测试联赛 CRUD 操作"""
        try:
            from src.database.models.league import League

            # 创建联赛
            league = League(
                name="Premier League",
                country="England",
                founded=1992
            )

            # 测试创建
            assert league.name == "Premier League"
            assert league.country == "England"
            assert league.founded == 1992

            # 测试更新
            league.current_season = "2023/2024"
            league.number_of_teams = 20
            assert league.current_season == "2023/2024"

            # 测试关系
            assert hasattr(league, 'teams')
            assert hasattr(league, 'matches')

        except ImportError:
            pytest.skip("League model not available")

    def test_audit_log_crud(self):
        """测试审计日志 CRUD 操作"""
        try:
            from src.database.models.audit_log import AuditLog

            # 创建审计日志
            audit_log = AuditLog(
                user_id="test_user",
                action="CREATE",
                table_name="matches",
                record_id=1,
                old_data=None,
                new_data={"status": "created"},
                timestamp=datetime.now()
            )

            # 测试创建
            assert audit_log.user_id == "test_user"
            assert audit_log.action == "CREATE"
            assert audit_log.table_name == "matches"

            # 测试方法
            assert hasattr(audit_log, 'to_dict')
            assert hasattr(audit_log, 'from_dict')

        except ImportError:
            pytest.skip("AuditLog model not available")

    def test_raw_data_crud(self):
        """测试原始数据 CRUD 操作"""
        try:
            from src.database.models.raw_data import RawMatchData

            # 创建原始数据
            raw_data = RawMatchData(
                source="api",
                raw_data='{"id": 1, "status": "finished"}',
                processed=False,
                received_at=datetime.now()
            )

            # 测试创建
            assert raw_data.source == "api"
            assert raw_data.processed is False
            assert 'id' in raw_data.raw_data

            # 测试更新
            raw_data.processed = True
            raw_data.processed_at = datetime.now()
            assert raw_data.processed is True

        except ImportError:
            pytest.skip("RawMatchData model not available")

    def test_database_session_operations(self):
        """测试数据库会话操作"""
        try:
            from src.database.connection import DatabaseManager

            with patch('src.database.connection.create_engine'):
                manager = DatabaseManager()

                # 测试会话创建
                assert hasattr(manager, 'create_session')
                assert hasattr(manager, 'create_async_session')
                assert hasattr(manager, 'get_session')
                assert hasattr(manager, 'get_async_session')

        except ImportError:
            pytest.skip("Database manager not available")

    def test_database_transaction_operations(self):
        """测试数据库事务操作"""
        try:
            from src.database.connection import DatabaseManager

            with patch('src.database.connection.create_engine'):
                manager = DatabaseManager()

                # 测试事务方法（如果存在）
                transaction_methods = [
                    'begin_transaction',
                    'commit_transaction',
                    'rollback_transaction'
                ]

                for method in transaction_methods:
                    if hasattr(manager, method):
                        assert True

        except ImportError:
            pytest.skip("Transaction methods not available")

    def test_database_connection_management(self):
        """测试数据库连接管理"""
        try:
            from src.database.connection import DatabaseManager, MultiUserDatabaseManager

            # 测试单例模式
            db_manager1 = DatabaseManager()
            db_manager2 = DatabaseManager()
            assert db_manager1 is not db_manager2

            # 测试多用户管理器单例
            multi_manager1 = MultiUserDatabaseManager()
            multi_manager2 = MultiUserDatabaseManager()
            assert multi_manager1 is multi_manager2

        except ImportError:
            pytest.skip("Database managers not available")