#!/usr/bin/env python3
"""
Mock工厂函数 - 标准化Mock对象创建
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock


def create_mock_di_container():
    """创建标准化的Mock依赖注入容器"""
    container = AsyncMock()

    # 创建标准化的Mock服务
    mock_services = {
        # 核心服务
        "model_service": create_mock_model_service(),
        "cache_service": create_mock_cache_service(),
        "database_service": create_mock_database_service(),
        # 业务服务
        "inference_service": create_mock_inference_service(),
        "collection_service": create_mock_collection_service(),
        "feature_extractor": create_mock_feature_extractor(),
        # 外部服务
        "fotmob_client": create_mock_fotmob_client(),
        "notification_service": create_mock_notification_service(),
    }

    # 设置resolve方法
    async def mock_resolve(service_name: str) -> Any:
        if service_name in mock_services:
            return mock_services[service_name]

        # 对于未Mock的服务，返回通用AsyncMock
        default_mock = AsyncMock()
        default_mock.configure_mock(
            **{
                "name": service_name,
                "initialize.return_value": None,
                "cleanup.return_value": None,
            }
        )
        mock_services[service_name] = default_mock
        return default_mock

    container.resolve = AsyncMock(side_effect=mock_resolve)
    container.register_singleton = MagicMock()
    container.register_factory = MagicMock()

    return container, mock_services


def create_mock_model_service() -> AsyncMock:
    """创建Mock模型服务"""
    model_service = AsyncMock()

    # 配置返回值
    model_service.configure_mock(
        **{
            "name": "model_service",
            "is_loaded.return_value": True,
            "model_info.return_value": {
                "name": "xgboost_v2",
                "version": "2.0.0",
                "features": 12,
                "accuracy": 0.67,
            },
        }
    )

    # 配置异步方法
    model_service.load_model = AsyncMock(return_value=True)
    model_service.predict = AsyncMock(
        return_value={
            "prediction": "HOME_WIN",
            "probabilities": [0.65, 0.25, 0.10],
            "confidence": 0.75,
        }
    )
    model_service.unload = AsyncMock(return_value=True)
    model_service.list_models = AsyncMock(return_value=["xgboost_v2", "random_forest"])

    return model_service


def create_mock_cache_service() -> AsyncMock:
    """创建Mock缓存服务"""
    cache_service = AsyncMock()

    cache_service.configure_mock(
        **{
            "name": "cache_service",
            "stats.return_value": {
                "hit_rate": 0.85,
                "total_requests": 1000,
                "cache_size": 150,
            },
        }
    )

    cache_service.get = AsyncMock(return_value=None)  # 默认缓存未命中
    cache_service.set = AsyncMock(return_value=True)
    cache_service.delete = AsyncMock(return_value=True)
    cache_service.clear_all = AsyncMock(return_value=True)
    cache_service.cleanup_expired = AsyncMock(return_value=True)

    return cache_service


def create_mock_database_service() -> AsyncMock:
    """创建Mock数据库服务"""
    db_service = AsyncMock()

    db_service.configure_mock(
        **{
            "name": "database_service",
            "is_connected.return_value": True,
            "connection_pool_size.return_value": 10,
        }
    )

    # Mock查询方法
    db_service.fetch_one = AsyncMock(
        return_value={
            "id": 1,
            "home_team": "Man Utd",
            "away_team": "Arsenal",
            "home_score": 2,
            "away_score": 1,
        }
    )

    db_service.fetch_many = AsyncMock(
        return_value=[
            {"id": 1, "home_team": "Man Utd", "away_team": "Arsenal"},
            {"id": 2, "home_team": "Chelsea", "away_team": "Liverpool"},
        ]
    )

    db_service.execute_query = AsyncMock(return_value={"affected_rows": 1})

    return db_service


def create_mock_inference_service() -> AsyncMock:
    """创建Mock推理服务"""
    inference_service = AsyncMock()

    inference_service.configure_mock(
        **{
            "name": "inference_service",
            "is_initialized.return_value": True,
            "stats.return_value": {
                "total_predictions": 500,
                "accuracy": 0.67,
                "avg_response_time": 0.05,
            },
        }
    )

    inference_service.predict_match = AsyncMock(
        return_value={
            "success": True,
            "prediction": "HOME_WIN",
            "probabilities": {"HOME": 0.65, "DRAW": 0.25, "AWAY": 0.10},
            "confidence": 0.75,
            "model_version": "xgboost_v2",
            "timestamp": "2024-01-15T10:00:00Z",
        }
    )

    inference_service.batch_predict = AsyncMock(
        return_value={
            "success": True,
            "results": [
                {"match_id": "1", "prediction": "HOME_WIN"},
                {"match_id": "2", "prediction": "DRAW"},
            ],
        }
    )

    inference_service.health_check = AsyncMock(
        return_value={
            "healthy": True,
            "initialized": True,
            "dependencies": {"model_service": True, "cache_service": True},
        }
    )

    return inference_service


def create_mock_feature_extractor() -> AsyncMock:
    """创建Mock特征提取器"""
    feature_extractor = AsyncMock()

    feature_extractor.configure_mock(
        **{
            "name": "feature_extractor",
            "feature_count.return_value": 12,
            "feature_names.return_value": [
                "home_form",
                "away_form",
                "h2h_home_wins",
                "h2h_draws",
                "h2h_away_wins",
                "home_goals_scored",
                "away_goals_scored",
                "venue_advantage",
                "league_strength",
                "team_strength_diff",
                "recent_performance",
                "head_to_head",
            ],
        }
    )

    feature_extractor.extract_features = AsyncMock(
        return_value={
            "features": [
                0.65,
                0.45,
                0.8,
                0.3,
                0.2,
                1.2,
                0.8,
                1.0,
                0.75,
                0.15,
                0.7,
                0.6,
            ],
            "feature_metadata": {
                "match_id": "test_match_001",
                "extraction_time": "2024-01-15T10:00:00Z",
                "source": "enhanced_fotmob",
            },
        }
    )

    return feature_extractor


def create_mock_collection_service() -> AsyncMock:
    """创建Mock数据收集服务"""
    collection_service = AsyncMock()

    collection_service.configure_mock(
        **{
            "name": "collection_service",
            "is_running.return_value": False,
            "stats.return_value": {
                "tasks_completed": 250,
                "tasks_failed": 5,
                "data_points_collected": 15000,
            },
        }
    )

    collection_service.start_collection = AsyncMock(return_value=True)
    collection_service.stop_collection = AsyncMock(return_value=True)
    collection_service.collect_match_data = AsyncMock(
        return_value={"success": True, "data_points": 125, "collection_time": 0.12}
    )

    return collection_service


def create_mock_fotmob_client() -> AsyncMock:
    """创建Mock FotMob客户端"""
    fotmob_client = AsyncMock()

    fotmob_client.configure_mock(
        **{
            "name": "fotmob_client",
            "api_rate_limit.return_value": 100,
            "api_status.return_value": "healthy",
        }
    )

    fotmob_client.get_match_data = AsyncMock(
        return_value={
            "match_id": "test_match_001",
            "home_team": "Man Utd",
            "away_team": "Arsenal",
            "score": {"home": 2, "away": 1},
            "statistics": {
                "possession": {"home": 60, "away": 40},
                "shots": {"home": 15, "away": 8},
                "corners": {"home": 6, "away": 3},
            },
        }
    )

    fotmob_client.get_team_stats = AsyncMock(
        return_value={
            "team": "Man Utd",
            "form": ["W", "D", "W", "L", "W"],
            "goals_scored": 15,
            "goals_conceded": 8,
        }
    )

    return fotmob_client


def create_mock_notification_service() -> AsyncMock:
    """创建Mock通知服务"""
    notification_service = AsyncMock()

    notification_service.configure_mock(
        **{
            "name": "notification_service",
            "is_connected.return_value": True,
            "channels.return_value": ["email", "slack", "webhook"],
        }
    )

    notification_service.send_alert = AsyncMock(
        return_value={"sent": True, "channel": "email", "message_id": "alert_001"}
    )

    notification_service.send_report = AsyncMock(return_value={"sent": True, "channel": "slack", "recipients": 5})

    return notification_service


def create_async_context_manager():
    """创建异步上下文管理器Mock"""

    class AsyncContextManagerMock:
        def __init__(self, return_value=None):
            self.return_value = return_value
            self.enter_count = 0
            self.exit_count = 0

        async def __aenter__(self):
            self.enter_count += 1
            return self.return_value

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.exit_count += 1
            return False

        def __enter__(self):
            # 同步版本，支持with语句
            self.enter_count += 1
            return self.return_value

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.exit_count += 1
            return False

    return AsyncContextManagerMock


def create_mock_coroutine(return_value=None, side_effect=None):
    """创建可等待的Mock协程"""

    async def mock_coroutine(*args, **kwargs):
        if side_effect:
            if isinstance(side_effect, Exception):
                raise side_effect
            elif callable(side_effect):
                return side_effect(*args, **kwargs)
        return return_value

    return mock_coroutine


def create_mock_event_loop():
    """创建Mock事件循环"""
    mock_loop = MagicMock()

    mock_loop.create_task.return_value = MagicMock()
    mock_loop.run_until_complete = AsyncMock()
    mock_loop.is_running.return_value = True
    mock_loop.time.return_value = 1642248000.0  # 示例时间戳

    return mock_loop


# 常用Mock组合
def create_complete_service_stack():
    """创建完整的服务栈Mock"""
    return {
        "di_container": create_mock_di_container(),
        "model_service": create_mock_model_service(),
        "cache_service": create_mock_cache_service(),
        "database_service": create_mock_database_service(),
        "feature_extractor": create_mock_feature_extractor(),
        "inference_service": create_mock_inference_service(),
        "collection_service": create_mock_collection_service(),
    }
