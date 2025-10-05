"""
增强的Mock助手
提供常用的Mock对象和装饰器
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch


class EnhancedMock:
    """增强的Mock类，提供更多便利方法"""

    @staticmethod
    def create_async_mock(return_value: Any = None, side_effect: Any = None):
        """创建异步Mock对象"""
        mock = AsyncMock()
        if return_value is not None:
            mock.return_value = return_value
        if side_effect is not None:
            mock.side_effect = side_effect
        return mock

    @staticmethod
    def create_database_mock():
        """创建数据库Mock"""
        db_mock = MagicMock()

        # 模拟连接
        db_mock.connect = AsyncMock()
        db_mock.disconnect = AsyncMock()
        db_mock.execute = AsyncMock(return_value=True)
        db_mock.fetch_one = AsyncMock(return_value={"id": 1})
        db_mock.fetch_all = AsyncMock(return_value=[])
        db_mock.fetch_val = AsyncMock(return_value=1)

        # 模拟事务
        db_mock.begin = AsyncMock()
        db_mock.commit = AsyncMock()
        db_mock.rollback = AsyncMock()

        return db_mock

    @staticmethod
    def create_redis_mock():
        """创建Redis Mock"""
        redis_mock = MagicMock()

        # 同步方法
        redis_mock.get = MagicMock(return_value=None)
        redis_mock.set = MagicMock(return_value=True)
        redis_mock.setex = MagicMock(return_value=True)
        redis_mock.delete = MagicMock(return_value=1)
        redis_mock.exists = MagicMock(return_value=0)
        redis_mock.expire = MagicMock(return_value=True)
        redis_mock.keys = MagicMock(return_value=[])

        # 异步方法
        redis_mock.async_get = AsyncMock(return_value=None)
        redis_mock.async_set = AsyncMock(return_value=True)
        redis_mock.async_delete = AsyncMock(return_value=1)

        return redis_mock

    @staticmethod
    def create_http_client_mock():
        """创建HTTP客户端Mock"""
        client_mock = MagicMock()

        # 模拟响应
        response_mock = MagicMock()
        response_mock.status_code = 200
        response_mock.json.return_value = {"success": True}
        response_mock.text = "OK"
        response_mock.headers = {"content-type": "application/json"}

        # 异步方法
        client_mock.get = AsyncMock(return_value=response_mock)
        client_mock.post = AsyncMock(return_value=response_mock)
        client_mock.put = AsyncMock(return_value=response_mock)
        client_mock.delete = AsyncMock(return_value=response_mock)

        # 同步方法
        client_mock.request = MagicMock(return_value=response_mock)

        return client_mock, response_mock

    @staticmethod
    def create_kafka_mock():
        """创建Kafka Mock"""
        producer_mock = MagicMock()
        consumer_mock = MagicMock()

        # Producer mock
        producer_mock.send = MagicMock(
            return_value=MagicMock(topic="test", partition=0, offset=0)
        )
        producer_mock.send_and_wait = AsyncMock(return_value=True)
        producer_mock.flush = MagicMock()
        producer_mock.close = MagicMock()

        # Consumer mock
        consumer_mock.poll = MagicMock(return_value=[])
        consumer_mock.subscribe = MagicMock()
        consumer_mock.commit = MagicMock()
        consumer_mock.close = MagicMock()

        return producer_mock, consumer_mock

    @staticmethod
    def create_ml_model_mock():
        """创建机器学习模型Mock"""
        model_mock = MagicMock()

        # 模拟预测
        model_mock.predict = AsyncMock(
            return_value={
                "prediction": "home_win",
                "confidence": 0.75,
                "probabilities": {"home_win": 0.75, "draw": 0.15, "away_win": 0.10},
            }
        )

        # 模拟批量预测
        model_mock.predict_batch = AsyncMock(
            return_value=[
                {"prediction": "home_win", "confidence": 0.75},
                {"prediction": "draw", "confidence": 0.60},
            ]
        )

        # 模拟特征重要性
        model_mock.feature_importance = {
            "team_form": 0.3,
            "head_to_head": 0.25,
            "home_advantage": 0.2,
            "player_stats": 0.25,
        }

        return model_mock


class MockContextManager:
    """Mock上下文管理器"""

    def __init__(self, return_value: Any = None, side_effect: Any = None):
        self.return_value = return_value
        self.side_effect = side_effect
        self.enter_called = False
        self.exit_called = False

    def __enter__(self):
        self.enter_called = True
        return self.return_value

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_called = True
        if self.side_effect:
            raise self.side_effect

    def __aenter__(self):
        self.enter_called = True
        return AsyncMock(return_value=self.return_value)

    def __aexit__(self, exc_type, exc_val, exc_tb):
        self.exit_called = True
        if self.side_effect:
            raise self.side_effect
        return AsyncMock()


def mock_external_services():
    """装饰器：Mock外部服务"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            with patch("src.database.base.DatabaseSession") as db_session:
                db_session.return_value.__aenter__.return_value = (
                    EnhancedMock.create_database_mock()
                )

                with patch("src.cache.redis_manager.redis_client") as redis_client:
                    redis_client.return_value = EnhancedMock.create_redis_mock()

                    return func(*args, **kwargs)

        return wrapper

    return decorator


def mock_api_responses(responses: Dict[str, Any]):
    """装饰器：Mock API响应"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            client_mock, response_mock = EnhancedMock.create_http_client_mock()

            def get_mock(url, **kwargs):
                for pattern, response in responses.items():
                    if pattern in url:
                        response_mock.status_code = response.get("status", 200)
                        response_mock.json.return_value = response.get("data", {})
                        return response_mock
                return response_mock

            client_mock.get.side_effect = get_mock

            with patch("httpx.AsyncClient", return_value=client_mock):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def mock_database_session(data: Optional[List[Dict]] = None):
    """装饰器：Mock数据库会话"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            db_mock = EnhancedMock.create_database_mock()

            if data:
                db_mock.fetch_all.return_value = data
                db_mock.fetch_one.return_value = data[0] if data else None

            with patch("src.database.base.DatabaseSession") as db_session:
                db_session.return_value.__aenter__.return_value = db_mock
                return func(*args, **kwargs)

        return wrapper

    return decorator


def mock_redis_cache(cache_data: Optional[Dict[str, Any]] = None):
    """装饰器：Mock Redis缓存"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            redis_mock = EnhancedMock.create_redis_mock()

            if cache_data:

                def get_mock(key):
                    value = cache_data.get(key)
                    return json.dumps(value) if value else None

                redis_mock.get.side_effect = get_mock

            with patch("src.cache.redis_manager.redis_client", redis_mock):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def mock_celery_task(task_name: str, return_value: Any = None):
    """装饰器：Mock Celery任务"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            task_mock = MagicMock()
            task_mock.apply.return_value.get.return_value = return_value or {
                "status": "success"
            }
            task_mock.apply_async.return_value.id = "task_id_123"

            with patch(f"src.tasks.{task_name}", task_mock):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def mock_mlflow_tracking():
    """装饰器：Mock MLflow跟踪"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            with patch("mlflow.start_run") as start_run:
                with patch("mlflow.log_metric") as log_metric:
                    with patch("mlflow.log_param") as log_param:
                        with patch("mlflow.set_tag") as set_tag:
                            start_run.return_value.__enter__.return_value = MagicMock()
                            return func(*args, **kwargs)

        return wrapper

    return decorator


class MockDataGenerator:
    """生成Mock数据的工具类"""

    @staticmethod
    def create_match_data(overrides: Optional[Dict] = None) -> Dict:
        """创建比赛数据"""
        data = {
            "id": 12345,
            "home_team_id": 10,
            "away_team_id": 20,
            "league_id": 1,
            "home_score": None,
            "away_score": None,
            "match_status": "scheduled",
            "start_time": datetime.now().isoformat(),
            "venue": "Test Stadium",
            "season": "2024-25",
        }
        if overrides:
            data.update(overrides)
        return data

    @staticmethod
    def create_team_data(overrides: Optional[Dict] = None) -> Dict:
        """创建球队数据"""
        data = {
            "id": 10,
            "team_name": "Test Team",
            "team_code": "TT",
            "country": "Testland",
            "founded_year": 1900,
            "stadium": "Test Stadium",
            "is_active": True,
        }
        if overrides:
            data.update(overrides)
        return data

    @staticmethod
    def create_prediction_data(overrides: Optional[Dict] = None) -> Dict:
        """创建预测数据"""
        data = {
            "match_id": 12345,
            "prediction": "home_win",
            "confidence": 0.75,
            "home_win_prob": 0.75,
            "draw_prob": 0.15,
            "away_win_prob": 0.10,
            "model_version": "v2.0",
            "created_at": datetime.now().isoformat(),
        }
        if overrides:
            data.update(overrides)
        return data

    @staticmethod
    def create_odds_data(overrides: Optional[Dict] = None) -> Dict:
        """创建赔率数据"""
        data = {
            "match_id": 12345,
            "home_win": 2.1,
            "draw": 3.4,
            "away_win": 3.2,
            "bookmaker": "TestBookmaker",
            "timestamp": datetime.now().isoformat(),
        }
        if overrides:
            data.update(overrides)
        return data


# 常用的Mock对象实例
MOCK_DATABASE = EnhancedMock.create_database_mock()
MOCK_REDIS = EnhancedMock.create_redis_mock()
MOCK_HTTP_CLIENT, MOCK_HTTP_RESPONSE = EnhancedMock.create_http_client_mock()
MOCK_KAFKA_PRODUCER, MOCK_KAFKA_CONSUMER = EnhancedMock.create_kafka_mock()
MOCK_ML_MODEL = EnhancedMock.create_ml_model_mock()
