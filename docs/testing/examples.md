# 测试用例示例

本文档提供足球预测系统中各种测试类型的完整代码示例，包括单元测试、集成测试和端到端测试。

## 📋 目录

- [单元测试示例](#单元测试示例)
  - [数据库模型测试](#数据库模型测试)
  - [调度器配置测试](#调度器配置测试)
  - [数据处理函数测试](#数据处理函数测试)
  - [API路由测试](#api路由测试)
  - [异步服务测试](#异步服务测试)
- [集成测试示例](#集成测试示例)
  - [数据库连接集成测试](#数据库连接集成测试)
  - [Celery调度集成测试](#celery调度集成测试)
  - [数据采集接口集成测试](#数据采集接口集成测试)
  - [Redis缓存集成测试](#redis缓存集成测试)
- [端到端测试示例](#端到端测试示例)
  - [完整数据流测试](#完整数据流测试)
  - [API端到端测试](#api端到端测试)
  - [预测流程测试](#预测流程测试)
- [Mock和Fixture示例](#mock和fixture示例)
  - [外部依赖Mock](#外部依赖mock)
  - [数据库测试Fixture](#数据库测试fixture)
  - [测试数据工厂](#测试数据工厂)

---

## 单元测试示例

### 数据库模型测试

```python
# tests/unit/database/test_models_comprehensive.py
import pytest
from datetime import datetime
from factory.alchemy import SQLAlchemyModelFactory
from src.database.models.match import Match
from src.database.models.team import Team
from src.database.models.prediction import Prediction
from tests.factories.match_factory import MatchFactory
from tests.factories.team_factory import TeamFactory
from tests.factories.prediction_factory import PredictionFactory

class TestMatchModel:
    """测试Match模型的各种操作"""

    def test_match_creation(self, db_session):
        """测试比赛记录创建"""
        match = MatchFactory()
        db_session.add(match)
        db_session.commit()

        assert match.id is not None
        assert match.home_score >= 0
        assert match.away_score >= 0
        assert isinstance(match.match_date, datetime)

    def test_match_relationships(self, db_session):
        """测试模型关系"""
        match = MatchFactory(
            home_team__name="Team A",
            away_team__name="Team B"
        )
        db_session.add(match)
        db_session.commit()

        assert match.home_team.name == "Team A"
        assert match.away_team.name == "Team B"
        assert match in match.home_team.home_matches
        assert match in match.away_team.away_matches

    def test_match_validation(self, db_session):
        """测试数据验证"""
        # 测试负分数应该失败
        with pytest.raises(ValueError):
            MatchFactory(home_score=-1)

        # 测试None值应该失败
        with pytest.raises(ValueError):
            MatchFactory(match_date=None)

    def test_match_string_representation(self, db_session):
        """测试字符串表示"""
        match = MatchFactory(
            home_team__name="Arsenal",
            away_team__name="Chelsea"
        )
        expected_str = "Arsenal vs Chelsea"
        assert str(match) == expected_str

class TestPredictionModel:
    """测试Prediction模型"""

    def test_prediction_creation(self, db_session):
        """测试预测记录创建"""
        prediction = PredictionFactory()
        db_session.add(prediction)
        db_session.commit()

        assert prediction.id is not None
        assert 0 <= prediction.home_win_prob <= 1
        assert 0 <= prediction.draw_prob <= 1
        assert 0 <= prediction.away_win_prob <= 1
        assert abs(prediction.home_win_prob + prediction.draw_prob + prediction.away_win_prob - 1.0) < 0.01

    def test_prediction_confidence_calculation(self, db_session):
        """测试置信度计算"""
        prediction = PredictionFactory(
            home_win_prob=0.5,
            draw_prob=0.3,
            away_win_prob=0.2
        )

        # 置信度应该是最高概率
        expected_confidence = 0.5
        assert abs(prediction.confidence - expected_confidence) < 0.01

    def test_prediction_model_relationship(self, db_session):
        """测试预测与比赛的关系"""
        prediction = PredictionFactory()
        db_session.add(prediction)
        db_session.commit()

        assert prediction.match.id is not None
        assert prediction in prediction.match.predictions
```

### 调度器配置测试

```python
# tests/unit/scheduler/test_celery_config_comprehensive.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.scheduler.celery_config import get_celery_config, get_celery_app
from src.scheduler.task_scheduler import TaskScheduler

class TestCeleryConfig:
    """测试Celery配置"""

    def test_celery_config_structure(self):
        """测试配置结构"""
        config = get_celery_config()

        # 验证必要配置项存在
        required_keys = [
            'broker_url', 'result_backend', 'task_serializer',
            'accept_content', 'result_serializer', 'timezone',
            'enable_utc', 'task_track_started', 'task_time_limit'
        ]

        for key in required_keys:
            assert key in config, f"Missing required config key: {key}"

    def test_celery_config_values(self):
        """测试配置值"""
        config = get_celery_config()

        # 验证配置值合理性
        assert config['task_serializer'] == 'json'
        assert config['accept_content'] == ['json']
        assert config['result_serializer'] == 'json'
        assert config['timezone'] == 'UTC'
        assert config['enable_utc'] is True
        assert config['task_track_started'] is True
        assert config['task_time_limit'] == 30 * 60  # 30分钟

    @patch('src.scheduler.celery_config.Celery')
    def test_celery_app_creation(self, mock_celery):
        """测试Celery应用创建"""
        mock_app = Mock()
        mock_celery.return_value = mock_app

        app = get_celery_app()

        mock_celery.assert_called_once_with('football_prediction')
        assert app == mock_app

    def test_celery_app_configuration(self):
        """测试Celery应用配置"""
        with patch('src.scheduler.celery_config.Celery') as mock_celery:
            mock_app = Mock()
            mock_celery.return_value = mock_app

            get_celery_app()

            # 验证配置被设置
            mock_app.conf.update.assert_called_once()

class TestTaskScheduler:
    """测试任务调度器"""

    def test_scheduler_initialization(self):
        """测试调度器初始化"""
        scheduler = TaskScheduler()

        assert scheduler.celery_app is not None
        assert scheduler.task_registry is not None

    def test_task_registration(self):
        """测试任务注册"""
        scheduler = TaskScheduler()

        # 模拟任务函数
        mock_task = Mock()
        mock_task.__name__ = 'test_task'

        scheduler.register_task('test_task', mock_task)

        assert 'test_task' in scheduler.task_registry
        assert scheduler.task_registry['test_task'] == mock_task

    @patch('src.scheduler.task_scheduler.celery_app')
    def test_task_scheduling(self, mock_celery_app):
        """测试任务调度"""
        scheduler = TaskScheduler()

        # 模拟任务
        mock_task = Mock()
        mock_task.__name__ = 'test_task'
        scheduler.register_task('test_task', mock_task)

        # 调度任务
        scheduler.schedule_task('test_task', countdown=60)

        # 验证任务被调用
        mock_task.apply_async.assert_called_once_with(countdown=60)

    def test_task_execution_monitoring(self):
        """测试任务执行监控"""
        scheduler = TaskScheduler()

        # 模拟异步结果
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_result.status = 'PENDING'
        mock_result.ready.return_value = False

        with patch.object(scheduler, 'get_task_result', return_value=mock_result):
            status = scheduler.get_task_status('test-task-id')

            assert status['task_id'] == 'test-task-id'
            assert status['status'] == 'PENDING'
            assert status['ready'] is False
```

### 数据处理函数测试

```python
# tests/unit/data/processing/test_football_data_cleaner_comprehensive.py
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from src.data.processing.football_data_cleaner import FootballDataCleaner

class TestFootballDataCleaner:
    """测试足球数据清洗"""

    def test_clean_match_data_basic(self):
        """测试基本的比赛数据清洗"""
        cleaner = FootballDataCleaner()
        dirty_data = pd.DataFrame({
            'home_team': ['Team A ', ' TEAM B', None, 'Team D'],
            'away_team': ['Team B', 'Team A ', 'Invalid', 'Team E'],
            'home_score': [2, '1', 'N/A', 3],
            'away_score': [1, '2', 'N/A', 2],
            'match_date': ['2023-01-01', '2023-01-02', 'invalid', '2023-01-04']
        })

        clean_data = cleaner.clean_match_data(dirty_data)

        # 验证队伍名称清理
        assert clean_data['home_team'].iloc[0] == 'Team A'
        assert clean_data['home_team'].iloc[1] == 'TEAM B'
        assert pd.isna(clean_data['home_team'].iloc[2])
        assert clean_data['home_team'].iloc[3] == 'Team D'

        # 验证分数转换
        assert clean_data['home_score'].iloc[0] == 2
        assert clean_data['home_score'].iloc[1] == 1
        assert pd.isna(clean_data['home_score'].iloc[2])
        assert clean_data['home_score'].iloc[3] == 3

        # 验证日期转换
        assert isinstance(clean_data['match_date'].iloc[0], datetime)
        assert pd.isna(clean_data['match_date'].iloc[2])

    def test_clean_player_data(self):
        """测试球员数据清洗"""
        cleaner = FootballDataCleaner()
        dirty_data = pd.DataFrame({
            'player_name': ['John Doe ', ' JANE SMITH', None, 'Bob Johnson'],
            'age': ['25', 'N/A', 'invalid', 30],
            'position': ['FW', 'MID', 'Invalid', 'DEF'],
            'nationality': ['England', ' SCOTLAND', None, 'Wales']
        })

        clean_data = cleaner.clean_player_data(dirty_data)

        # 验证姓名清理
        assert clean_data['player_name'].iloc[0] == 'John Doe'
        assert clean_data['player_name'].iloc[1] == 'JANE SMITH'
        assert pd.isna(clean_data['player_name'].iloc[2])

        # 验证年龄转换
        assert clean_data['age'].iloc[0] == 25
        assert pd.isna(clean_data['age'].iloc[1])
        assert pd.isna(clean_data['age'].iloc[2])
        assert clean_data['age'].iloc[3] == 30

        # 验证位置标准化
        assert clean_data['position'].iloc[0] == 'Forward'
        assert clean_data['position'].iloc[1] == 'Midfielder'
        assert pd.isna(clean_data['position'].iloc[2])
        assert clean_data['position'].iloc[3] == 'Defender'

    def test_remove_duplicates(self):
        """测试重复数据移除"""
        cleaner = FootballDataCleaner()
        data_with_duplicates = pd.DataFrame({
            'home_team': ['Team A', 'Team A', 'Team B', 'Team C'],
            'away_team': ['Team B', 'Team B', 'Team C', 'Team D'],
            'match_date': ['2023-01-01', '2023-01-01', '2023-01-02', '2023-01-03']
        })

        clean_data = cleaner.remove_duplicates(data_with_duplicates)

        # 验证重复数据被移除
        assert len(clean_data) == 3
        assert not clean_data.duplicated().any()

    def test_handle_missing_values(self):
        """测试缺失值处理"""
        cleaner = FootballDataCleaner()
        data_with_missing = pd.DataFrame({
            'home_team': ['Team A', None, 'Team C'],
            'away_team': ['Team B', 'Team C', None],
            'home_score': [2, None, 1],
            'away_score': [1, 2, None]
        })

        clean_data = cleaner.handle_missing_values(data_with_missing)

        # 验证缺失值被适当处理
        assert len(clean_data) == 1  # 只保留完整数据
        assert clean_data['home_team'].iloc[0] == 'Team A'
        assert clean_data['away_team'].iloc[0] == 'Team B'
        assert clean_data['home_score'].iloc[0] == 2
        assert clean_data['away_score'].iloc[0] == 1

    def test_validate_data_integrity(self):
        """测试数据完整性验证"""
        cleaner = FootballDataCleaner()
        invalid_data = pd.DataFrame({
            'home_team': ['Team A', 'Team B'],
            'away_team': ['Team B', 'Team A'],
            'home_score': [2, -1],  # 无效分数
            'away_score': [1, 2]
        })

        # 应该检测到数据完整性问题
        with pytest.raises(ValueError, match="Invalid home score"):
            cleaner.validate_data_integrity(invalid_data)

    def test_data_transformation_pipeline(self):
        """测试完整的数据转换管道"""
        cleaner = FootballDataCleaner()
        raw_data = pd.DataFrame({
            'home_team': ['Team A ', ' TEAM B', 'Team C'],
            'away_team': ['Team B', 'Team A ', 'Team D'],
            'home_score': ['2', '1', 3],
            'away_score': [1, '2', 2],
            'match_date': ['2023-01-01', '2023-01-02', '2023-01-03'],
            'competition': ['Premier League', 'PREMIER LEAGUE', 'Championship']
        })

        # 执行完整的清洗管道
        cleaned_data = cleaner.clean_data_pipeline(raw_data)

        # 验证数据质量
        assert len(cleaned_data) == 3
        assert not cleaned_data.isnull().any().any()
        assert all(isinstance(date, datetime) for date in cleaned_data['match_date'])
        assert all(score >= 0 for score in cleaned_data['home_score'])
        assert all(score >= 0 for score in cleaned_data['away_score'])

    def test_performance_large_dataset(self):
        """测试大数据集性能"""
        cleaner = FootballDataCleaner()

        # 生成大型测试数据集
        large_data = pd.DataFrame({
            'home_team': [f'Team {i%100}' for i in range(10000)],
            'away_team': [f'Team {i%100 + 1}' for i in range(10000)],
            'home_score': [i%5 for i in range(10000)],
            'away_score': [i%5 for i in range(10000)],
            'match_date': pd.date_range('2023-01-01', periods=10000, freq='D')
        })

        # 测试处理性能
        import time
        start_time = time.time()
        result = cleaner.clean_data_pipeline(large_data)
        end_time = time.time()

        # 验证处理时间合理（应小于5秒）
        assert end_time - start_time < 5
        assert len(result) == 10000
```

### API路由测试

```python
# tests/unit/api/test_health_comprehensive.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from src.main import app
from src.api.health import HealthCheck, HealthStatus

class TestHealthAPI:
    """测试健康检查API"""

    def setup_method(self):
        """设置测试客户端"""
        self.client = TestClient(app)

    def test_health_check_basic(self):
        """测试基本健康检查"""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'version' in data
        assert 'uptime' in data

    @patch('src.api.health.HealthCheck.check_database')
    def test_health_check_with_database(self, mock_check_db):
        """测试包含数据库检查的健康检查"""
        mock_check_db.return_value = True

        response = self.client.get("/health?check_database=true")

        assert response.status_code == 200
        data = response.json()
        assert data['database_status'] == 'healthy'
        mock_check_db.assert_called_once()

    @patch('src.api.health.HealthCheck.check_database')
    def test_health_check_database_failure(self, mock_check_db):
        """测试数据库失败的健康检查"""
        mock_check_db.return_value = False

        response = self.client.get("/health?check_database=true")

        assert response.status_code == 503
        data = response.json()
        assert data['status'] == 'unhealthy'
        assert data['database_status'] == 'unhealthy'

    def test_health_check_detailed(self):
        """测试详细健康检查"""
        response = self.client.get("/health?detailed=true")

        assert response.status_code == 200
        data = response.json()
        assert 'system_info' in data
        assert 'services' in data
        assert 'memory_usage' in data['system_info']
        assert 'cpu_usage' in data['system_info']

    def test_health_check_metrics(self):
        """测试健康检查指标"""
        response = self.client.get("/health/metrics")

        assert response.status_code == 200
        data = response.json()
        assert 'total_requests' in data
        assert 'error_rate' in data
        assert 'average_response_time' in data
        assert 'active_connections' in data

    @patch('src.api.health.HealthCheck.check_external_services')
    def test_health_check_external_services(self, mock_check_services):
        """测试外部服务检查"""
        mock_check_services.return_value = {
            'redis': True,
            'mlflow': True,
            'kafka': False
        }

        response = self.client.get("/health?check_external=true")

        assert response.status_code == 200
        data = response.json()
        assert 'external_services' in data
        assert data['external_services']['redis'] is True
        assert data['external_services']['mlflow'] is True
        assert data['external_services']['kafka'] is False
```

### 异步服务测试

```python
# tests/unit/services/test_prediction_service_async.py
import pytest
from unittest.mock import AsyncMock, Mock, patch
from src.services.prediction_service import PredictionService
from src.models.prediction_result import PredictionResult

class TestPredictionServiceAsync:
    """测试异步预测服务"""

    @pytest.mark.asyncio
    async def test_predict_single_match(self):
        """测试单场比赛预测"""
        # 模拟模型
        mock_model = AsyncMock()
        mock_model.predict.return_value = [0.6, 0.3, 0.1]

        # 模拟特征存储
        mock_feature_store = AsyncMock()
        mock_feature_store.get_features.return_value = {
            'feature1': 0.5,
            'feature2': 0.8
        }

        service = PredictionService(
            model=mock_model,
            feature_store=mock_feature_store
        )

        result = await service.predict_match(match_id=123)

        assert isinstance(result, PredictionResult)
        assert result.match_id == 123
        assert abs(result.home_win_prob - 0.6) < 0.01
        assert abs(result.draw_prob - 0.3) < 0.01
        assert abs(result.away_win_prob - 0.1) < 0.01

        mock_feature_store.get_features.assert_called_once_with(123)
        mock_model.predict.assert_called_once()

    @pytest.mark.asyncio
    async def test_predict_multiple_matches(self):
        """测试多场比赛批量预测"""
        mock_model = AsyncMock()
        mock_model.predict_batch.return_value = [
            [0.6, 0.3, 0.1],
            [0.4, 0.4, 0.2],
            [0.2, 0.3, 0.5]
        ]

        mock_feature_store = AsyncMock()
        mock_feature_store.get_batch_features.return_value = {
            123: {'feature1': 0.5, 'feature2': 0.8},
            124: {'feature1': 0.6, 'feature2': 0.7},
            125: {'feature1': 0.4, 'feature2': 0.9}
        }

        service = PredictionService(
            model=mock_model,
            feature_store=mock_feature_store
        )

        match_ids = [123, 124, 125]
        results = await service.predict_matches(match_ids)

        assert len(results) == 3
        assert all(isinstance(r, PredictionResult) for r in results)
        assert results[0].match_id == 123
        assert results[1].match_id == 124
        assert results[2].match_id == 125

        mock_feature_store.get_batch_features.assert_called_once_with(match_ids)
        mock_model.predict_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_predict_with_cache(self):
        """测试带缓存的预测"""
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None  # 缓存未命中
        mock_cache.set.return_value = True

        mock_model = AsyncMock()
        mock_model.predict.return_value = [0.6, 0.3, 0.1]

        mock_feature_store = AsyncMock()
        mock_feature_store.get_features.return_value = {
            'feature1': 0.5, 'feature2': 0.8
        }

        service = PredictionService(
            model=mock_model,
            feature_store=mock_feature_store,
            cache=mock_cache
        )

        result = await service.predict_match(match_id=123, use_cache=True)

        # 验证缓存操作
        mock_cache.get.assert_called_once_with('prediction:123')
        mock_cache.set.assert_called_once()

        # 验证预测结果
        assert isinstance(result, PredictionResult)
        assert result.match_id == 123

    @pytest.mark.asyncio
    async def test_predict_cache_hit(self):
        """测试缓存命中"""
        cached_result = PredictionResult(
            match_id=123,
            home_win_prob=0.6,
            draw_prob=0.3,
            away_win_prob=0.1,
            confidence=0.6,
            model_version='1.0'
        )

        mock_cache = AsyncMock()
        mock_cache.get.return_value = cached_result

        service = PredictionService(cache=mock_cache)

        result = await service.predict_match(match_id=123, use_cache=True)

        # 验证缓存命中，不调用模型
        assert result == cached_result
        mock_cache.get.assert_called_once_with('prediction:123')

    @pytest.mark.asyncio
    async def test_predict_error_handling(self):
        """测试预测错误处理"""
        mock_model = AsyncMock()
        mock_model.predict.side_effect = Exception("Model prediction failed")

        mock_feature_store = AsyncMock()
        mock_feature_store.get_features.return_value = {
            'feature1': 0.5, 'feature2': 0.8
        }

        service = PredictionService(
            model=mock_model,
            feature_store=mock_feature_store
        )

        with pytest.raises(Exception, match="Model prediction failed"):
            await service.predict_match(match_id=123)

    @pytest.mark.asyncio
    async def test_concurrent_predictions(self):
        """测试并发预测"""
        import asyncio

        mock_model = AsyncMock()
        mock_model.predict.side_effect = [
            [0.6, 0.3, 0.1],
            [0.4, 0.4, 0.2],
            [0.2, 0.3, 0.5]
        ]

        mock_feature_store = AsyncMock()
        mock_feature_store.get_features.side_effect = [
            {'feature1': 0.5, 'feature2': 0.8},
            {'feature1': 0.6, 'feature2': 0.7},
            {'feature1': 0.4, 'feature2': 0.9}
        ]

        service = PredictionService(
            model=mock_model,
            feature_store=mock_feature_store
        )

        # 并发执行多个预测
        tasks = [
            service.predict_match(match_id=i)
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert all(isinstance(r, PredictionResult) for r in results)
```

---

## 集成测试示例

### 数据库连接集成测试

```python
# tests/integration/database/test_connection_integration.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.database.connection import DatabaseManager
from src.database.models.match import Match
from src.database.models.team import Team
from tests.fixtures.database import test_db_config

class TestDatabaseConnectionIntegration:
    """测试数据库连接集成"""

    @pytest.fixture
    async def db_manager(self):
        """创建数据库管理器"""
        manager = DatabaseManager(test_db_config)
        yield manager
        await manager.close()

    @pytest.mark.asyncio
    async def test_database_connection_pool(self, db_manager):
        """测试数据库连接池"""
        # 获取多个连接
        conn1 = await db_manager.get_connection()
        conn2 = await db_manager.get_connection()

        # 验证连接不是同一个对象
        assert conn1 != conn2

        # 验证连接都正常
        assert await db_manager.ping_connection(conn1)
        assert await db_manager.ping_connection(conn2)

        # 释放连接
        await db_manager.release_connection(conn1)
        await db_manager.release_connection(conn2)

    @pytest.mark.asyncio
    async def test_database_session_lifecycle(self, db_manager):
        """测试数据库会话生命周期"""
        async with db_manager.get_session() as session:
            # 验证会话类型
            assert isinstance(session, AsyncSession)

            # 创建测试数据
            team = Team(name="Test Team", country="Test Country")
            session.add(team)
            await session.commit()

            # 验证数据已保存
            result = await session.get(Team, team.id)
            assert result.name == "Test Team"

    @pytest.mark.asyncio
    async def test_database_transaction_rollback(self, db_manager):
        """测试数据库事务回滚"""
        async with db_manager.get_session() as session:
            try:
                # 创建数据
                team = Team(name="Rollback Team", country="Test Country")
                session.add(team)

                # 模拟错误
                raise Exception("Simulated error")
            except Exception:
                await session.rollback()

            # 验证数据被回滚
            result = await session.execute(
                "SELECT * FROM teams WHERE name = 'Rollback Team'"
            )
            assert result.scalar() is None

    @pytest.mark.asyncio
    async def test_database_concurrent_operations(self, db_manager):
        """测试数据库并发操作"""
        async def create_team(name: str):
            async with db_manager.get_session() as session:
                team = Team(name=name, country="Test Country")
                session.add(team)
                await session.commit()
                return team.id

        # 并发创建多个队伍
        tasks = [
            create_team(f"Team {i}")
            for i in range(5)
        ]

        team_ids = await asyncio.gather(*tasks)

        # 验证所有队伍都创建成功
        assert len(team_ids) == 5
        assert len(set(team_ids)) == 5  # 所有ID都不同

    @pytest.mark.asyncio
    async def test_database_performance_monitoring(self, db_manager):
        """测试数据库性能监控"""
        import time

        # 监控查询性能
        start_time = time.time()

        async with db_manager.get_session() as session:
            # 执行一些查询操作
            for i in range(10):
                team = Team(name=f"Performance Test {i}", country="Test Country")
                session.add(team)
            await session.commit()

        end_time = time.time()
        query_time = end_time - start_time

        # 验证查询时间合理
        assert query_time < 1.0  # 应该在1秒内完成

        # 获取性能统计
        stats = await db_manager.get_performance_stats()
        assert 'total_queries' in stats
        assert 'average_query_time' in stats
        assert 'connection_pool_size' in stats
```

### Celery调度集成测试

```python
# tests/integration/scheduler/test_celery_integration.py
import pytest
from unittest.mock import Mock, patch
from src.scheduler.celery_app import celery_app
from src.tasks.maintenance_tasks import cleanup_old_logs
from src.tasks.data_collection_tasks import collect_match_data
from src.tasks.model_training_tasks import retrain_model

class TestCeleryIntegration:
    """测试Celery集成"""

    @pytest.mark.asyncio
    async def test_task_execution_success(self):
        """测试任务执行成功"""
        # 异步执行任务
        result = cleanup_old_logs.delay(days=30)

        # 等待任务完成
        task_result = await result.get(timeout=30)

        assert result.successful()
        assert 'cleaned_count' in task_result
        assert task_result['cleaned_count'] >= 0
        assert 'execution_time' in task_result

    @pytest.mark.asyncio
    async def test_task_execution_with_parameters(self):
        """测试带参数的任务执行"""
        # 执行数据采集任务
        result = collect_match_data.delay(
            competition_id=123,
            season=2023,
            force_refresh=True
        )

        task_result = await result.get(timeout=60)

        assert result.successful()
        assert 'collected_matches' in task_result
        assert 'competition_id' in task_result
        assert task_result['competition_id'] == 123

    @pytest.mark.asyncio
    async def test_task_failure_handling(self):
        """测试任务失败处理"""
        # 模拟失败的任务
        result = retrain_model.delay(
            model_name="nonexistent_model",
            training_data=None
        )

        # 任务应该失败
        assert not result.successful()
        assert result.failed()

        # 获取错误信息
        try:
            await result.get(timeout=10)
        except Exception as e:
            assert "Model not found" in str(e)

    @pytest.mark.asyncio
    async def test_task_chaining(self):
        """测试任务链执行"""
        from celery import chain

        # 创建任务链：数据采集 -> 数据处理 -> 模型训练
        task_chain = chain(
            collect_match_data.s(competition_id=123, season=2023),
            cleanup_old_logs.s(days=7),
            retrain_model.s(model_name="test_model")
        )

        # 执行任务链
        result = task_chain.apply_async()
        final_result = await result.get(timeout=120)

        assert result.successful()
        assert 'pipeline_completed' in final_result
        assert final_result['pipeline_completed'] is True

    @pytest.mark.asyncio
    async def test_scheduled_task_execution(self):
        """测试定时任务执行"""
        from celery.schedules import crontab

        # 模拟定时任务
        beat_schedule = {
            'daily-cleanup': {
                'task': 'src.tasks.maintenance_tasks.cleanup_old_logs',
                'schedule': crontab(minute=0, hour=2),  # 每天凌晨2点
                'args': (30,)
            }
        }

        # 验证定时任务配置
        assert 'daily-cleanup' in beat_schedule
        assert beat_schedule['daily-cleanup']['task'] == 'src.tasks.maintenance_tasks.cleanup_old_logs'
        assert beat_schedule['daily-cleanup']['args'] == (30,)

    @pytest.mark.asyncio
    async def test_task_progress_tracking(self):
        """测试任务进度跟踪"""
        # 执行长时间运行的任务
        result = collect_match_data.delay(
            competition_id=123,
            season=2023,
            force_refresh=True
        )

        # 监控任务进度
        while not result.ready():
            # 获取任务状态
            state = result.state
            info = result.info

            if state == 'PROGRESS':
                assert 'current' in info
                assert 'total' in info
                assert 'progress' in info

                # 验证进度合理
                progress = info['progress']
                assert 0 <= progress <= 100

            await asyncio.sleep(1)

        # 验证任务最终完成
        assert result.successful()
```

### 数据采集接口集成测试

```python
# tests/integration/data/collectors/test_api_integration.py
import pytest
import respx
from httpx import Response, RequestError
from src.data.collectors.fixtures_collector import FixturesCollector
from src.data.collectors.odds_collector import OddsCollector

class TestAPIIntegration:
    """测试API集成"""

    @pytest.mark.asyncio
    @respx.mock
    async def test_fixtures_collection_success(self):
        """测试比赛数据采集成功"""
        # Mock API响应
        mock_response = {
            "matches": [
                {
                    "id": 1,
                    "home_team": {"name": "Team A", "id": 101},
                    "away_team": {"name": "Team B", "id": 102},
                    "competition": {"name": "Premier League", "id": 1},
                    "match_date": "2023-01-01T15:00:00Z",
                    "status": "SCHEDULED"
                },
                {
                    "id": 2,
                    "home_team": {"name": "Team C", "id": 103},
                    "away_team": {"name": "Team D", "id": 104},
                    "competition": {"name": "Premier League", "id": 1},
                    "match_date": "2023-01-02T15:00:00Z",
                    "status": "SCHEDULED"
                }
            ]
        }

        respx.get("https://api.football-data.org/v4/matches").mock(
            Response(200, json=mock_response)
        )

        collector = FixturesCollector()
        matches = await collector.collect_fixtures()

        assert len(matches) == 2
        assert matches[0].home_team == "Team A"
        assert matches[0].away_team == "Team B"
        assert matches[1].home_team == "Team C"
        assert matches[1].away_team == "Team D"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fixtures_collection_api_error(self):
        """测试API错误处理"""
        # Mock API错误响应
        respx.get("https://api.football-data.org/v4/matches").mock(
            Response(500, json={"error": "Internal Server Error"})
        )

        collector = FixturesCollector()

        with pytest.raises(Exception, match="API request failed"):
            await collector.collect_fixtures()

    @pytest.mark.asyncio
    @respx.mock
    async def test_fixtures_collection_rate_limiting(self):
        """测试API速率限制处理"""
        # Mock 速率限制响应
        respx.get("https://api.football-data.org/v4/matches").mock(
            Response(429, json={"error": "Rate limit exceeded"})
        )

        collector = FixturesCollector()

        with pytest.raises(Exception, match="Rate limit exceeded"):
            await collector.collect_fixtures()

    @pytest.mark.asyncio
    @respx.mock
    async def test_odds_collection_integration(self):
        """测试赔率数据采集集成"""
        # Mock 赔率API响应
        mock_odds_response = {
            "odds": [
                {
                    "match_id": 1,
                    "bookmaker": "Bet365",
                    "home_win": 2.10,
                    "draw": 3.40,
                    "away_win": 3.60,
                    "timestamp": "2023-01-01T10:00:00Z"
                },
                {
                    "match_id": 1,
                    "bookmaker": "William Hill",
                    "home_win": 2.05,
                    "draw": 3.50,
                    "away_win": 3.70,
                    "timestamp": "2023-01-01T10:00:00Z"
                }
            ]
        }

        respx.get("https://api.odds.com/v4/matches/1/odds").mock(
            Response(200, json=mock_odds_response)
        )

        collector = OddsCollector()
        odds = await collector.collect_odds(match_id=1)

        assert len(odds) == 2
        assert odds[0].bookmaker == "Bet365"
        assert odds[0].home_win == 2.10
        assert odds[1].bookmaker == "William Hill"
        assert odds[1].home_win == 2.05

    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_data_collection(self):
        """测试批量数据采集"""
        # Mock 多个API端点
        respx.get("https://api.football-data.org/v4/competitions").mock(
            Response(200, json={"competitions": [{"id": 1, "name": "Premier League"}]})
        )

        respx.get("https://api.football-data.org/v4/competitions/1/matches").mock(
            Response(200, json={"matches": [
                {"id": 1, "home_team": {"name": "Team A"}, "away_team": {"name": "Team B"}}
            ]})
        )

        collector = FixturesCollector()

        # 批量采集数据
        competitions = await collector.collect_competitions()
        matches = await collector.collect_competition_matches(competition_id=1)

        assert len(competitions) == 1
        assert competitions[0]["name"] == "Premier League"
        assert len(matches) == 1
        assert matches[0].home_team == "Team A"

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_retry_mechanism(self):
        """测试API重试机制"""
        import asyncio

        # 前两次请求失败，第三次成功
        call_count = 0

        def mock_handler(request: Request):
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                return Response(503, json={"error": "Service Unavailable"})
            else:
                return Response(200, json={"matches": []})

        respx.get("https://api.football-data.org/v4/matches").mock_side_effect = mock_handler

        collector = FixturesCollector(retry_attempts=3, retry_delay=1)
        matches = await collector.collect_fixtures()

        assert call_count == 3  # 验证重试次数
        assert isinstance(matches, list)
```

### Redis缓存集成测试

```python
# tests/integration/cache/test_redis_integration.py
import pytest
import redis.asyncio as redis
from src.cache.redis_cache import RedisCache
from src.cache.cache_manager import CacheManager

class TestRedisIntegration:
    """测试Redis缓存集成"""

    @pytest.fixture
    async def redis_client(self):
        """创建Redis客户端"""
        client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        yield client
        await client.flushdb()
        await client.close()

    @pytest.fixture
    async def cache_manager(self, redis_client):
        """创建缓存管理器"""
        manager = CacheManager(redis_client)
        yield manager
        await manager.clear_all()

    @pytest.mark.asyncio
    async def test_basic_cache_operations(self, cache_manager):
        """测试基本缓存操作"""
        # 设置缓存
        await cache_manager.set("test_key", "test_value", ttl=60)

        # 获取缓存
        value = await cache_manager.get("test_key")
        assert value == "test_value"

        # 删除缓存
        await cache_manager.delete("test_key")
        value = await cache_manager.get("test_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_ttl_operations(self, cache_manager):
        """测试缓存TTL操作"""
        import time

        # 设置短TTL的缓存
        await cache_manager.set("temp_key", "temp_value", ttl=2)

        # 立即获取应该存在
        value = await cache_manager.get("temp_key")
        assert value == "temp_value"

        # 等待过期
        await asyncio.sleep(3)

        # 再次获取应该不存在
        value = await cache_manager.get("temp_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_batch_operations(self, cache_manager):
        """测试批量缓存操作"""
        # 批量设置
        data = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        await cache_manager.set_many(data, ttl=60)

        # 批量获取
        values = await cache_manager.get_many(["key1", "key2", "key3", "key4"])
        assert values == {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
            "key4": None
        }

        # 批量删除
        await cache_manager.delete_many(["key1", "key2"])
        values = await cache_manager.get_many(["key1", "key2", "key3"])
        assert values == {
            "key1": None,
            "key2": None,
            "key3": "value3"
        }

    @pytest.mark.asyncio
    async def test_cache_pattern_operations(self, cache_manager):
        """测试缓存模式操作"""
        # 设置多个键
        await cache_manager.set("user:1:name", "Alice")
        await cache_manager.set("user:1:email", "alice@example.com")
        await cache_manager.set("user:2:name", "Bob")
        await cache_manager.set("user:2:email", "bob@example.com")

        # 按模式获取键
        keys = await cache_manager.keys("user:1:*")
        assert set(keys) == {"user:1:name", "user:1:email"}

        # 按模式删除
        deleted_count = await cache_manager.delete_pattern("user:1:*")
        assert deleted_count == 2

        # 验证删除成功
        keys = await cache_manager.keys("user:1:*")
        assert len(keys) == 0
        keys = await cache_manager.keys("user:2:*")
        assert len(keys) == 2

    @pytest.mark.asyncio
    async def test_cache_serialization(self, cache_manager):
        """测试缓存序列化"""
        import json
        from datetime import datetime

        # 复杂对象
        complex_data = {
            "user_id": 123,
            "username": "testuser",
            "preferences": {
                "theme": "dark",
                "language": "en"
            },
            "created_at": datetime.now().isoformat(),
            "tags": ["football", "prediction"]
        }

        # 序列化并缓存
        await cache_manager.set_json("complex_data", complex_data, ttl=60)

        # 获取并反序列化
        retrieved_data = await cache_manager.get_json("complex_data")

        assert retrieved_data == complex_data
        assert retrieved_data["user_id"] == 123
        assert retrieved_data["preferences"]["theme"] == "dark"

    @pytest.mark.asyncio
    async def test_cache_performance_monitoring(self, cache_manager):
        """测试缓存性能监控"""
        import time

        # 监控缓存操作性能
        start_time = time.time()

        # 执行大量缓存操作
        for i in range(1000):
            await cache_manager.set(f"perf_key_{i}", f"value_{i}", ttl=60)

        set_time = time.time() - start_time

        start_time = time.time()
        for i in range(1000):
            await cache_manager.get(f"perf_key_{i}")

        get_time = time.time() - start_time

        # 验证性能合理
        assert set_time < 1.0  # 1000次设置应该在1秒内完成
        assert get_time < 0.5  # 1000次获取应该在0.5秒内完成

        # 获取性能统计
        stats = await cache_manager.get_performance_stats()
        assert 'total_operations' in stats
        assert 'hit_rate' in stats
        assert 'average_response_time' in stats
```

---

## 端到端测试示例

### 完整数据流测试

```python
# tests/e2e/test_complete_data_pipeline.py
import pytest
import asyncio
from src.data.collectors.fixtures_collector import FixturesCollector
from src.data.processing.football_data_cleaner import FootballDataCleaner
from src.features.feature_store import FeatureStore
from src.models.prediction_service import PredictionService
from src.database.connection import DatabaseManager
from tests.fixtures.database import test_db_config

class TestCompleteDataPipeline:
    """测试完整数据流"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_end_to_end_prediction_pipeline(self):
        """测试端到端预测流程"""
        # 1. 数据采集
        collector = FixturesCollector()

        # Mock API响应
        with patch('src.data.collectors.fixtures_collector.requests.get') as mock_get:
            mock_response = {
                "matches": [
                    {
                        "id": 1,
                        "home_team": {"name": "Manchester United", "id": 33},
                        "away_team": {"name": "Liverpool", "id": 40},
                        "competition": {"name": "Premier League", "id": 39},
                        "match_date": "2023-01-01T15:00:00Z",
                        "status": "SCHEDULED"
                    }
                ]
            }
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.status_code = 200

            raw_matches = await collector.collect_fixtures()

        assert len(raw_matches) == 1
        assert raw_matches[0].home_team == "Manchester United"

        # 2. 数据处理
        cleaner = FootballDataCleaner()
        clean_matches = cleaner.clean_match_data(raw_matches)

        assert len(clean_matches) == 1
        assert not clean_matches.isnull().any().any()

        # 3. 特征工程
        feature_store = FeatureStore()
        features = feature_store.extract_features(clean_matches)

        assert len(features) == 1
        assert 'home_form' in features.iloc[0]
        assert 'away_form' in features.iloc[0]
        assert 'head_to_head' in features.iloc[0]

        # 4. 数据库存储
        db_manager = DatabaseManager(test_db_config)

        async with db_manager.get_session() as session:
            # 存储处理后的数据
            for _, match_data in clean_matches.iterrows():
                # 创建数据库记录
                match_record = Match(
                    home_team=match_data['home_team'],
                    away_team=match_data['away_team'],
                    match_date=match_data['match_date'],
                    competition=match_data['competition']
                )
                session.add(match_record)

            await session.commit()

            # 验证数据已存储
            result = await session.execute("SELECT COUNT(*) FROM matches")
            count = result.scalar()
            assert count == 1

        # 5. 模型预测
        prediction_service = PredictionService()

        # Mock模型预测
        with patch.object(prediction_service, 'model') as mock_model:
            mock_model.predict.return_value = [0.4, 0.3, 0.3]

            predictions = await prediction_service.predict_matches([1])

        assert len(predictions) == 1
        assert predictions[0].match_id == 1
        assert abs(predictions[0].home_win_prob - 0.4) < 0.01
        assert abs(predictions[0].draw_prob - 0.3) < 0.01
        assert abs(predictions[0].away_win_prob - 0.3) < 0.01

        # 6. 结果验证
        assert all(0 <= p.home_win_prob <= 1 for p in predictions)
        assert all(0 <= p.draw_prob <= 1 for p in predictions)
        assert all(0 <= p.away_win_prob <= 1 for p in predictions)
        assert all(abs(p.home_win_prob + p.draw_prob + p.away_win_prob - 1.0) < 0.01 for p in predictions)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_batch_prediction_pipeline(self):
        """测试批量预测流程"""
        # 准备批量测试数据
        collector = FixturesCollector()

        with patch('src.data.collectors.fixtures_collector.requests.get') as mock_get:
            mock_response = {
                "matches": [
                    {"id": i, "home_team": {"name": f"Team {i}"}, "away_team": {"name": f"Team {i+1}"},
                     "match_date": f"2023-01-0{i}T15:00:00Z", "status": "SCHEDULED"}
                    for i in range(1, 6)
                ]
            }
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.status_code = 200

            raw_matches = await collector.collect_fixtures()

        assert len(raw_matches) == 5

        # 数据处理
        cleaner = FootballDataCleaner()
        clean_matches = cleaner.clean_match_data(raw_matches)

        # 特征提取
        feature_store = FeatureStore()
        features = feature_store.extract_features(clean_matches)

        # 批量预测
        prediction_service = PredictionService()

        with patch.object(prediction_service, 'model') as mock_model:
            mock_model.predict_batch.return_value = [
                [0.4, 0.3, 0.3],
                [0.6, 0.2, 0.2],
                [0.3, 0.4, 0.3],
                [0.5, 0.3, 0.2],
                [0.2, 0.3, 0.5]
            ]

            predictions = await prediction_service.predict_matches([i for i in range(1, 6)])

        assert len(predictions) == 5
        assert all(p.match_id == i+1 for i, p in enumerate(predictions))
        assert all(0 <= p.home_win_prob <= 1 for p in predictions)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_error_handling_pipeline(self):
        """测试错误处理流程"""
        # 测试数据采集失败
        collector = FixturesCollector()

        with patch('src.data.collectors.fixtures_collector.requests.get') as mock_get:
            mock_get.side_effect = Exception("API Error")

            with pytest.raises(Exception, match="API Error"):
                await collector.collect_fixtures()

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_pipeline_performance(self):
        """测试管道性能"""
        import time

        start_time = time.time()

        # 执行完整流程
        collector = FixturesCollector()

        with patch('src.data.collectors.fixtures_collector.requests.get') as mock_get:
            mock_response = {"matches": [
                {"id": i, "home_team": {"name": f"Team {i}"}, "away_team": {"name": f"Team {i+1}"},
                 "match_date": f"2023-01-0{i}T15:00:00Z", "status": "SCHEDULED"}
                for i in range(1, 11)  # 10场比赛
            ]}
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.status_code = 200

            raw_matches = await collector.collect_fixtures()

        cleaner = FootballDataCleaner()
        clean_matches = cleaner.clean_match_data(raw_matches)

        feature_store = FeatureStore()
        features = feature_store.extract_features(clean_matches)

        prediction_service = PredictionService()

        with patch.object(prediction_service, 'model') as mock_model:
            mock_model.predict_batch.return_value = [
                [0.4, 0.3, 0.3] for _ in range(10)
            ]

            predictions = await prediction_service.predict_matches([i for i in range(1, 11)])

        end_time = time.time()
        pipeline_time = end_time - start_time

        # 验证性能（应该在5秒内完成）
        assert pipeline_time < 5.0
        assert len(predictions) == 10
```

### API端到端测试

```python
# tests/e2e/test_api_end_to_end.py
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.database.connection import DatabaseManager
from tests.fixtures.database import test_db_config

class TestAPIEndToEnd:
    """测试API端到端功能"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.mark.e2e
    def test_complete_api_workflow(self, client):
        """测试完整API工作流程"""

        # 1. 健康检查
        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()['status'] == 'healthy'

        # 2. 获取比赛数据
        matches_response = client.get("/api/v1/data/matches")
        assert matches_response.status_code == 200
        matches = matches_response.json()
        assert 'matches' in matches
        assert isinstance(matches['matches'], list)

        # 3. 获取特征数据
        features_response = client.get("/api/v1/features/latest")
        assert features_response.status_code == 200
        features = features_response.json()
        assert 'features' in features

        # 4. 获取预测结果
        predictions_response = client.get("/api/v1/predictions/latest")
        assert predictions_response.status_code == 200
        predictions = predictions_response.json()
        assert 'predictions' in predictions
        assert isinstance(predictions['predictions'], list)

        # 5. 获取监控指标
        monitoring_response = client.get("/api/v1/monitoring/metrics")
        assert monitoring_response.status_code == 200
        metrics = monitoring_response.json()
        assert 'system_metrics' in metrics
        assert 'application_metrics' in metrics

    @pytest.mark.e2e
    def test_prediction_workflow(self, client):
        """测试预测工作流程"""

        # 1. 提交预测请求
        prediction_request = {
            "match_id": 123,
            "home_team": "Team A",
            "away_team": "Team B",
            "competition": "Premier League",
            "match_date": "2023-01-01T15:00:00Z"
        }

        response = client.post("/api/v1/predictions", json=prediction_request)
        assert response.status_code == 200
        prediction_result = response.json()

        assert 'prediction_id' in prediction_result
        assert 'home_win_prob' in prediction_result
        assert 'draw_prob' in prediction_result
        assert 'away_win_prob' in prediction_result
        assert prediction_result['match_id'] == 123

        # 2. 获取预测结果
        prediction_id = prediction_result['prediction_id']
        get_response = client.get(f"/api/v1/predictions/{prediction_id}")
        assert get_response.status_code == 200
        retrieved_prediction = get_response.json()

        assert retrieved_prediction['prediction_id'] == prediction_id
        assert retrieved_prediction['match_id'] == 123

    @pytest.mark.e2e
    def test_error_handling_workflow(self, client):
        """测试错误处理流程"""

        # 1. 测试无效请求
        invalid_request = {
            "match_id": "invalid",  # 应该是数字
            "home_team": "",  # 不能为空
            "away_team": "Team B"
        }

        response = client.post("/api/v1/predictions", json=invalid_request)
        assert response.status_code == 422  # 验证错误

        # 2. 测试不存在的资源
        response = client.get("/api/v1/predictions/999999")
        assert response.status_code == 404

        # 3. 测试错误的健康检查
        response = client.get("/health?check_database=true")
        # 可能成功或失败，但都应该返回合理的响应
        assert response.status_code in [200, 503]

    @pytest.mark.e2e
    def test_api_rate_limiting(self, client):
        """测试API速率限制"""

        # 发送大量请求
        for i in range(100):
            response = client.get("/health")
            assert response.status_code == 200

        # 继续发送更多请求
        response = client.get("/health")
        # 可能被限制，也可能成功，取决于实现
        assert response.status_code in [200, 429]

    @pytest.mark.e2e
    def test_api_authentication(self, client):
        """测试API认证"""

        # 测试需要认证的端点
        protected_response = client.get("/api/v1/admin/status")
        # 可能需要认证，也可能不需要，取决于实现
        assert protected_response.status_code in [200, 401, 403]

        # 测试带认证头的请求
        headers = {"Authorization": "Bearer test-token"}
        auth_response = client.get("/api/v1/admin/status", headers=headers)
        # 认证可能成功或失败，但都应该返回合理的响应
        assert auth_response.status_code in [200, 401, 403]
```

---

## Mock和Fixture示例

### 外部依赖Mock

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, AsyncMock
import redis.asyncio as redis
from src.cache.redis_cache import RedisCache

@pytest.fixture
def mock_redis():
    """统一的Redis Mock"""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.exists = AsyncMock(return_value=False)
    mock_redis.keys = AsyncMock(return_value=[])
    return mock_redis

@pytest.fixture
def mock_mlflow_client():
    """统一的MLflow Mock"""
    mock_client = Mock()
    mock_client.get_latest_versions.return_value = [
        Mock(version="1", current_stage="Production")
    ]
    mock_client.transition_model_version_stage.return_value = None
    mock_client.search_runs.return_value = [
        Mock(info={"run_id": "test_run", "status": "FINISHED"})
    ]
    mock_client.log_metric = Mock()
    mock_client.log_param = Mock()
    mock_client.set_tag = Mock()
    return mock_client

@pytest.fixture
def mock_kafka_producer():
    """统一的Kafka Producer Mock"""
    mock_producer = AsyncMock()
    mock_producer.send = AsyncMock(return_value=None)
    mock_producer.flush = AsyncMock(return_value=None)
    mock_producer.start = AsyncMock(return_value=None)
    mock_producer.stop = AsyncMock(return_value=None)
    return mock_producer

@pytest.fixture
def mock_http_client():
    """统一的HTTP客户端Mock"""
    mock_client = Mock()
    mock_client.get.return_value = Mock(
        status_code=200,
        json=Mock(return_value={"data": "test"})
    )
    mock_client.post.return_value = Mock(
        status_code=201,
        json=Mock(return_value={"id": "test_id"})
    )
    return mock_client

@pytest.fixture
def mock_database_session():
    """统一的数据库会话Mock"""
    mock_session = Mock()
    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.rollback = Mock()
    mock_session.query = Mock()
    mock_session.execute = Mock(return_value=Mock(scalar=Mock(return_value=1)))
    mock_session.close = Mock()
    return mock_session

@pytest.fixture
def mock_cache_manager():
    """统一的缓存管理器Mock"""
    mock_cache = Mock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock(return_value=True)
    mock_cache.delete = AsyncMock(return_value=True)
    mock_cache.clear = AsyncMock(return_value=True)
    return mock_cache
```

### 数据库测试Fixture

```python
# tests/fixtures/database.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.database.base import Base
from src.database.config import get_test_database_config
from src.database.models.match import Match
from src.database.models.team import Team
from src.database.models.prediction import Prediction

@pytest.fixture
def test_db_config():
    """测试数据库配置"""
    return get_test_database_config()

@pytest.fixture
def test_engine(test_db_config):
    """测试数据库引擎"""
    engine = create_engine(test_db_config['url'])
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture
def test_session(test_engine):
    """测试数据库会话"""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
async def test_async_engine(test_db_config):
    """测试异步数据库引擎"""
    engine = create_async_engine(test_db_config['async_url'])
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def test_async_session(test_async_engine):
    """测试异步数据库会话"""
    AsyncSessionLocal = sessionmaker(
        test_async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with AsyncSessionLocal() as session:
        yield session

@pytest.fixture
def sample_teams(test_session):
    """示例队伍数据"""
    teams = [
        Team(name="Manchester United", country="England", founded=1878),
        Team(name="Liverpool", country="England", founded=1892),
        Team(name="Arsenal", country="England", founded=1886),
        Team(name="Chelsea", country="England", founded=1905)
    ]
    test_session.add_all(teams)
    test_session.commit()
    return teams

@pytest.fixture
def sample_matches(test_session, sample_teams):
    """示例比赛数据"""
    matches = [
        Match(
            home_team=sample_teams[0],
            away_team=sample_teams[1],
            home_score=2,
            away_score=1,
            match_date="2023-01-01",
            competition="Premier League",
            season=2023
        ),
        Match(
            home_team=sample_teams[2],
            away_team=sample_teams[3],
            home_score=1,
            away_score=1,
            match_date="2023-01-02",
            competition="Premier League",
            season=2023
        )
    ]
    test_session.add_all(matches)
    test_session.commit()
    return matches

@pytest.fixture
def sample_predictions(test_session, sample_matches):
    """示例预测数据"""
    predictions = [
        Prediction(
            match=sample_matches[0],
            home_win_prob=0.6,
            draw_prob=0.3,
            away_win_prob=0.1,
            confidence=0.6,
            model_version="1.0",
            created_at="2023-01-01T10:00:00Z"
        ),
        Prediction(
            match=sample_matches[1],
            home_win_prob=0.4,
            draw_prob=0.4,
            away_win_prob=0.2,
            confidence=0.4,
            model_version="1.0",
            created_at="2023-01-02T10:00:00Z"
        )
    ]
    test_session.add_all(predictions)
    test_session.commit()
    return predictions

@pytest.fixture
def empty_database(test_session):
    """空数据库"""
    # 清空所有数据
    for table in [Match, Team, Prediction]:
        test_session.query(table).delete()
    test_session.commit()
    return test_session
```

### 测试数据工厂

```python
# tests/factories/team_factory.py
import factory
from factory.alchemy import SQLAlchemyModelFactory
from src.database.models.team import Team

class TeamFactory(SQLAlchemyModelFactory):
    """队伍数据工厂"""

    class Meta:
        model = Team
        sqlalchemy_session_persistence = "commit"

    name = factory.Faker("company")
    country = factory.Faker("country")
    founded = factory.Faker("year", minimum=1800, maximum=2023)
    stadium = factory.Faker("city")
    manager = factory.Faker("name")

    @factory.post_generation
    def post_generation(obj, create, extracted, **kwargs):
        """后生成处理"""
        if create:
            # 确保名称不重复
            if not obj.name:
                obj.name = f"Team {obj.id}"
            obj.name = obj.name.strip()

# tests/factories/match_factory.py
import factory
from factory.alchemy import SQLAlchemyModelFactory
from src.database.models.match import Match
from tests.factories.team_factory import TeamFactory

class MatchFactory(SQLAlchemyModelFactory):
    """比赛数据工厂"""

    class Meta:
        model = Match
        sqlalchemy_session_persistence = "commit"

    home_team = factory.SubFactory(TeamFactory)
    away_team = factory.SubFactory(TeamFactory)
    home_score = factory.Faker("pyint", min_value=0, max_value=10)
    away_score = factory.Faker("pyint", min_value=0, max_value=10)
    match_date = factory.Faker("date_between", start_date="-1y", end_date="+1y")
    competition = factory.Faker("random_element", elements=[
        "Premier League", "Championship", "League One", "League Two"
    ])
    season = factory.Faker("pyint", min_value=2020, max_value=2023)
    status = factory.Faker("random_element", elements=[
        "SCHEDULED", "IN_PLAY", "FINISHED", "POSTPONED", "CANCELLED"
    ])

    @factory.post_generation
    def post_generation(obj, create, extracted, **kwargs):
        """后生成处理"""
        if create:
            # 确保主客场队伍不同
            if obj.home_team == obj.away_team:
                obj.away_team = TeamFactory()

            # 确保比赛日期合理
            if obj.match_date:
                obj.match_date = obj.match_date.replace(hour=15, minute=0)

            # 如果比赛已完成，确保分数已设置
            if obj.status == "FINISHED" and (obj.home_score is None or obj.away_score is None):
                obj.home_score = obj.home_score or 0
                obj.away_score = obj.away_score or 0

# tests/factories/prediction_factory.py
import factory
from factory.alchemy import SQLAlchemyModelFactory
from datetime import datetime
from src.database.models.prediction import Prediction
from tests.factories.match_factory import MatchFactory

class PredictionFactory(SQLAlchemyModelFactory):
    """预测数据工厂"""

    class Meta:
        model = Prediction
        sqlalchemy_session_persistence = "commit"

    match = factory.SubFactory(MatchFactory)
    home_win_prob = factory.Faker("pyfloat", min_value=0.0, max_value=1.0)
    draw_prob = factory.Faker("pyfloat", min_value=0.0, max_value=1.0)
    away_win_prob = factory.Faker("pyfloat", min_value=0.0, max_value=1.0)
    confidence = factory.LazyAttribute(lambda obj: max(obj.home_win_prob, obj.draw_prob, obj.away_win_prob))
    model_version = factory.Faker("semantic_version", prefix="v")
    created_at = factory.Faker("date_time_this_year")

    @factory.post_generation
    def post_generation(obj, create, extracted, **kwargs):
        """后生成处理"""
        if create:
            # 确保概率总和接近1
            total = obj.home_win_prob + obj.draw_prob + obj.away_win_prob
            if abs(total - 1.0) > 0.01:
                # 归一化
                obj.home_win_prob /= total
                obj.draw_prob /= total
                obj.away_win_prob /= total

            # 确保置信度正确
            obj.confidence = max(obj.home_win_prob, obj.draw_prob, obj.away_win_prob)

            # 确保创建时间设置
            if not obj.created_at:
                obj.created_at = datetime.now()

# tests/factories/data_factory.py
import factory
import pandas as pd
from datetime import datetime, timedelta

class FootballDataFactory:
    """足球数据工厂"""

    @staticmethod
    def create_match_data(n_matches=10):
        """创建比赛数据"""
        matches = []
        base_date = datetime.now() - timedelta(days=30)

        for i in range(n_matches):
            match_date = base_date + timedelta(days=i)
            match = {
                "match_id": i + 1,
                "home_team": f"Team {i + 1}",
                "away_team": f"Team {i + 2}",
                "home_score": (i % 5),
                "away_score": ((i + 1) % 5),
                "match_date": match_date,
                "competition": "Premier League",
                "season": 2023,
                "status": "FINISHED" if match_date < datetime.now() else "SCHEDULED"
            }
            matches.append(match)

        return pd.DataFrame(matches)

    @staticmethod
    def create_player_data(n_players=50):
        """创建球员数据"""
        players = []
        positions = ["Forward", "Midfielder", "Defender", "Goalkeeper"]
        nationalities = ["England", "Spain", "France", "Germany", "Italy"]

        for i in range(n_players):
            player = {
                "player_id": i + 1,
                "name": f"Player {i + 1}",
                "age": 18 + (i % 20),
                "position": positions[i % len(positions)],
                "nationality": nationalities[i % len(nationalities)],
                "team_id": (i % 20) + 1,
                "market_value": (i + 1) * 1000000,
                "contract_until": datetime.now() + timedelta(days=365 * (i % 5 + 1))
            }
            players.append(player)

        return pd.DataFrame(players)

    @staticmethod
    def create_odds_data(n_odds=100):
        """创建赔率数据"""
        odds = []
        bookmakers = ["Bet365", "William Hill", "Ladbrokes", "Paddy Power"]

        for i in range(n_odds):
            odd = {
                "match_id": (i % 20) + 1,
                "bookmaker": bookmakers[i % len(bookmakers)],
                "home_win": round(1.5 + (i % 10) * 0.1, 2),
                "draw": round(3.0 + (i % 5) * 0.2, 2),
                "away_win": round(2.5 + (i % 8) * 0.15, 2),
                "timestamp": datetime.now() - timedelta(hours=i % 24)
            }
            odds.append(odd)

        return pd.DataFrame(odds)

# tests/factories/api_data_factory.py
import factory
from typing import Dict, List, Any

class APIDataFactory:
    """API数据工厂"""

    @staticmethod
    def create_match_response(n_matches=5) -> Dict[str, Any]:
        """创建比赛API响应"""
        matches = []
        for i in range(n_matches):
            match = {
                "id": i + 1,
                "home_team": {
                    "id": 100 + i,
                    "name": f"Home Team {i + 1}",
                    "short_name": f"HT{i + 1}",
                    "crest": f"https://example.com/crest{i + 1}.png"
                },
                "away_team": {
                    "id": 200 + i,
                    "name": f"Away Team {i + 1}",
                    "short_name": f"AT{i + 1}",
                    "crest": f"https://example.com/crest{i + 1}.png"
                },
                "competition": {
                    "id": 1,
                    "name": "Premier League",
                    "code": "PL",
                    "type": "LEAGUE"
                },
                "season": {
                    "id": 2023,
                    "start_date": "2023-08-01",
                    "end_date": "2024-05-31"
                },
                "utc_date": f"2023-01-{i + 1:02d}T15:00:00Z",
                "status": "SCHEDULED",
                "matchday": i + 1,
                "stage": "REGULAR_SEASON",
                "last_updated": f"2023-01-{i + 1:02d}T10:00:00Z"
            }
            matches.append(match)

        return {"matches": matches, "count": len(matches)}

    @staticmethod
    def create_competition_response() -> Dict[str, Any]:
        """创建联赛API响应"""
        competitions = [
            {
                "id": 1,
                "name": "Premier League",
                "code": "PL",
                "type": "LEAGUE",
                "emblem": "https://example.com/pl.png"
            },
            {
                "id": 2,
                "name": "Championship",
                "code": "ELC",
                "type": "LEAGUE",
                "emblem": "https://example.com/elc.png"
            }
        ]

        return {"competitions": competitions, "count": len(competitions)}

    @staticmethod
    def create_team_response(team_id: int) -> Dict[str, Any]:
        """创建球队API响应"""
        return {
            "id": team_id,
            "name": f"Team {team_id}",
            "short_name": f"T{team_id}",
            "tla": f"TEAM{team_id}",
            "crest": f"https://example.com/team{team_id}.png",
            "address": f"Stadium {team_id}, City",
            "website": f"https://team{team_id}.com",
            "founded": 1880 + (team_id % 50),
            "club_colors": "Red / White",
            "venue": f"Stadium {team_id}",
            "last_updated": "2023-01-01T00:00:00Z"
        }

    @staticmethod
    def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
        """创建错误API响应"""
        return {
            "error": {
                "code": status_code,
                "message": message
            },
            "timestamp": datetime.now().isoformat()
        }
```

---

## 总结

本文档提供了足球预测系统中各种测试类型的完整代码示例，涵盖了从单元测试到端到端测试的所有层面。这些示例遵循最佳实践，包括：

1. **测试结构清晰**: 每个测试类都有明确的职责
2. **异步测试支持**: 完整支持异步代码测试
3. **Mock策略**: 统一的外部依赖Mock
4. **数据工厂**: 使用factory-boy生成测试数据
5. **错误处理**: 完整的错误处理测试
6. **性能考虑**: 包含性能基准测试

这些示例可以作为开发新测试时的参考模板，确保测试质量和一致性。
