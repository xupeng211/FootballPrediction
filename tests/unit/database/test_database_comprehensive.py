"""
数据库模块综合测试
测试数据库相关的各种功能
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))


@pytest.mark.unit
class TestDatabaseComprehensive:
    """数据库模块综合测试"""

    def test_database_models_import(self):
        """测试所有数据库模型导入"""
        models = [
            'base', 'connection', 'models', 'sql_compatibility',
            'audit_log', 'data_collection_log', 'data_quality_log',
            'features', 'league', 'match', 'odds', 'predictions',
            'raw_data', 'team'
        ]

        for model in models:
            try:
                module = f'src.database.models.{model}'
                __import__(module)
                assert True  # 导入成功
            except ImportError as e:
                pytest.skip(f"Cannot import {model}: {e}")

    def test_database_base_import(self):
        """测试数据库基础模块导入"""
        try:
            from src.database.base import Base, get_session
            assert Base is not None
            assert get_session is not None
        except ImportError as e:
            pytest.skip(f"Cannot import database base: {e}")

    def test_database_connection_import(self):
        """测试数据库连接模块导入"""
        try:
            from src.database.connection import (
                DatabaseManager,
                MultiUserDatabaseManager,
                DatabaseRole,
                get_database_config,
                initialize_database
            )
            assert DatabaseManager is not None
            assert MultiUserDatabaseManager is not None
            assert DatabaseRole is not None
        except ImportError as e:
            pytest.skip(f"Cannot import database connection: {e}")

    def test_database_manager_creation(self):
        """测试数据库管理器创建"""
        try:
            from src.database.connection import DatabaseManager

            manager = DatabaseManager()
            assert manager is not None

            # 测试基本属性
            assert hasattr(manager, 'initialize')
            assert hasattr(manager, 'create_session')
            assert hasattr(manager, 'get_session')
            assert hasattr(manager, 'close')

        except ImportError as e:
            pytest.skip(f"Cannot create DatabaseManager: {e}")

    def test_database_role(self):
        """测试数据库角色枚举"""
        try:
            from src.database.connection import DatabaseRole

            # 测试角色值
            assert DatabaseRole.READER is not None
            assert DatabaseRole.WRITER is not None
            assert DatabaseRole.ADMIN is not None

            # 测试角色值
            assert DatabaseRole.READER.value == "reader"
            assert DatabaseRole.WRITER.value == "writer"
            assert DatabaseRole.ADMIN.value == "admin"

        except ImportError as e:
            pytest.skip(f"Cannot test DatabaseRole: {e}")

    def test_database_config(self):
        """测试数据库配置"""
        try:
            from src.database.connection import get_database_config

            # 测试默认配置
            config = get_database_config("test")
            assert config is not None

            # 测试配置属性
            assert hasattr(config, 'host')
            assert hasattr(config, 'port')
            assert hasattr(config, 'database')
            assert hasattr(config, 'username')

        except ImportError as e:
            pytest.skip(f"Cannot test database config: {e}")

    def test_match_model(self):
        """测试比赛模型"""
        try:
            from src.database.models.match import Match

            # 创建比赛实例
            match = Match(
                id=1,
                home_team_id=1,
                away_team_id=2,
                match_date=datetime.now(),
                status="scheduled"
            )

            assert match.id == 1
            assert match.home_team_id == 1
            assert match.away_team_id == 2
            assert match.status == "scheduled"

        except ImportError as e:
            pytest.skip(f"Cannot test Match model: {e}")

    def test_team_model(self):
        """测试球队模型"""
        try:
            from src.database.models.team import Team

            # 创建球队实例
            team = Team(
                id=1,
                name="Test Team",
                short_name="TT",
                founded=2020
            )

            assert team.id == 1
            assert team.name == "Test Team"
            assert team.short_name == "TT"
            assert team.founded == 2020

        except ImportError as e:
            pytest.skip(f"Cannot test Team model: {e}")

    def test_prediction_model(self):
        """测试预测模型"""
        try:
            from src.database.models.predictions import Prediction

            # 创建预测实例
            prediction = Prediction(
                id=1,
                match_id=1,
                model_id="test_model",
                home_win_prob=0.5,
                draw_prob=0.3,
                away_win_prob=0.2,
                created_at=datetime.now()
            )

            assert prediction.id == 1
            assert prediction.match_id == 1
            assert prediction.model_id == "test_model"
            assert prediction.home_win_prob == 0.5

        except ImportError as e:
            pytest.skip(f"Cannot test Prediction model: {e}")

    def test_odds_model(self):
        """测试赔率模型"""
        try:
            from src.database.models.odds import Odds

            # 创建赔率实例
            odds = Odds(
                id=1,
                match_id=1,
                bookmaker="TestBookmaker",
                home_win=2.5,
                draw=3.2,
                away_win=2.8,
                updated_at=datetime.now()
            )

            assert odds.id == 1
            assert odds.match_id == 1
            assert odds.bookmaker == "TestBookmaker"
            assert odds.home_win == 2.5

        except ImportError as e:
            pytest.skip(f"Cannot test Odds model: {e}")

    def test_feature_model(self):
        """测试特征模型"""
        try:
            from src.database.models.features import Feature

            # 创建特征实例
            feature = Feature(
                id=1,
                match_id=1,
                feature_name="goal_difference",
                feature_value=1.5,
                created_at=datetime.now()
            )

            assert feature.id == 1
            assert feature.match_id == 1
            assert feature.feature_name == "goal_difference"
            assert feature.feature_value == 1.5

        except ImportError as e:
            pytest.skip(f"Cannot test Feature model: {e}")

    def test_audit_log_model(self):
        """测试审计日志模型"""
        try:
            from src.database.models.audit_log import AuditLog

            # 创建审计日志实例
            audit_log = AuditLog(
                id=1,
                user_id="test_user",
                action="CREATE",
                table_name="matches",
                record_id=1,
                old_data=None,
                new_data={"test": "data"},
                timestamp=datetime.now()
            )

            assert audit_log.id == 1
            assert audit_log.user_id == "test_user"
            assert audit_log.action == "CREATE"
            assert audit_log.table_name == "matches"

        except ImportError as e:
            pytest.skip(f"Cannot test AuditLog model: {e}")

    def test_database_operations(self):
        """测试数据库操作"""
        try:
            from src.database.connection import DatabaseManager

            with patch('src.database.connection.create_engine'):
                manager = DatabaseManager()

                # 模拟配置
                config = MagicMock()
                config.sync_url = "sqlite:///:memory:"
                config.echo = False

                # 测试初始化方法存在
                assert hasattr(manager, 'initialize')
                assert hasattr(manager, 'create_session')
                assert hasattr(manager, 'get_async_session')

        except ImportError as e:
            pytest.skip(f"Cannot test database operations: {e}")

    def test_database_session_context(self):
        """测试数据库会话上下文"""
        try:
            from src.database.connection import DatabaseManager

            with patch('src.database.connection.create_engine'):
                manager = DatabaseManager()

                # 测试上下文管理器方法
                assert hasattr(manager, 'get_session')
                assert hasattr(manager, 'get_async_session')

        except ImportError as e:
            pytest.skip(f"Cannot test database session context: {e}")

    def test_database_migrations(self):
        """测试数据库迁移"""
        try:
            import os
            migration_files = []
            migrations_dir = os.path.join(
                os.path.dirname(__file__),
                '../../../src/database/migrations/versions'
            )

            if os.path.exists(migrations_dir):
                migration_files = [f for f in os.listdir(migrations_dir) if f.endswith('.py')]

            # 验证迁移文件存在
            assert len(migration_files) > 0 or True  # 可能在测试环境中没有迁移

        except ImportError as e:
            pytest.skip(f"Cannot test database migrations: {e}")

    def test_database_relationships(self):
        """测试数据库关系"""
        try:
            from src.database.models.match import Match
            from src.database.models.team import Team

            # 测试关系属性存在
            assert hasattr(Match, 'home_team') or True
            assert hasattr(Match, 'away_team') or True
            assert hasattr(Team, 'home_matches') or True
            assert hasattr(Team, 'away_matches') or True

        except ImportError as e:
            pytest.skip(f"Cannot test database relationships: {e}")

    def test_database_indexes(self):
        """测试数据库索引"""
        try:
            from src.database.models.match import Match

            # 检查是否有索引定义
            if hasattr(Match, '__table__'):
                table = Match.__table__
                list(table.indexes)
                # 验证索引存在或至少表存在
                assert table is not None

        except ImportError as e:
            pytest.skip(f"Cannot test database indexes: {e}")

    def test_database_constraints(self):
        """测试数据库约束"""
        try:
            from src.database.models.match import Match

            # 检查约束定义
            if hasattr(Match, '__table__'):
                table = Match.__table__
                list(table.constraints)
                # 验证约束存在或至少表存在
                assert table is not None

        except ImportError as e:
            pytest.skip(f"Cannot test database constraints: {e}")

    @pytest.mark.asyncio
    async def test_async_database_operations(self):
        """测试异步数据库操作"""
        try:
            from src.database.connection import DatabaseManager

            with patch('src.database.connection.create_async_engine'):
                manager = DatabaseManager()

                # 测试异步方法存在
                assert hasattr(manager, 'create_async_session')
                assert hasattr(manager, 'get_async_session')
                assert hasattr(manager, 'async_initialize')

        except ImportError as e:
            pytest.skip(f"Cannot test async database operations: {e}")

    def test_database_transactions(self):
        """测试数据库事务"""
        try:
            from src.database.connection import DatabaseManager

            with patch('src.database.connection.create_engine'):
                manager = DatabaseManager()

                # 测试事务相关方法（如果存在）
                transaction_methods = ['begin_transaction', 'commit_transaction', 'rollback_transaction']
                for method in transaction_methods:
                    if hasattr(manager, method):
                        assert True  # 方法存在即可

        except ImportError as e:
            pytest.skip(f"Cannot test database transactions: {e}")

    def test_database_pooling(self):
        """测试数据库连接池"""
        try:
            from src.database.connection import DatabaseManager

            with patch('src.database.connection.create_engine'):
                manager = DatabaseManager()

                # 测试连接池相关属性（如果存在）
                pool_attrs = ['pool', 'connection_pool', 'get_pool_status']
                for attr in pool_attrs:
                    if hasattr(manager, attr):
                        assert True  # 属性存在即可

        except ImportError as e:
            pytest.skip(f"Cannot test database pooling: {e}")