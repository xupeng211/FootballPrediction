import pytest

from src.tasks.celery_app import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    TASK_MONITORING,
    DatabaseManager,
    RedisManager,
    TaskRetryConfig,
    app,
)

pytestmark = pytest.mark.unit


def test_stubbed_managers_expose_expected_interfaces() -> None:
    db_manager = DatabaseManager()
    redis_manager = RedisManager()

    assert db_manager.get_connection() is None
    assert redis_manager.get_redis_client() is None

    # Methods should execute without raising errors
    db_manager.close_connection()
    redis_manager.close_connection()


def test_celery_configuration_uses_shared_broker_settings() -> None:
    assert app.conf.broker_url == CELERY_BROKER_URL
    assert app.conf.result_backend == CELERY_RESULT_BACKEND
    assert (
        app.conf.task_routes["tasks.data_collection_tasks.collect_fixtures_task"][
            "queue"
        ]
        == "fixtures"
    )


def test_task_retry_config_returns_specific_and_default_values() -> None:
    odds_config = TaskRetryConfig.get_retry_config("collect_odds_task")
    assert odds_config["retry_delay"] == 60
    assert odds_config["retry_backoff"] is True

    fallback = TaskRetryConfig.get_retry_config("unknown_task")
    assert fallback["max_retries"] == TaskRetryConfig.DEFAULT_MAX_RETRIES
    assert fallback["retry_backoff"] is False


def test_task_monitoring_thresholds_are_accessible() -> None:
    assert TASK_MONITORING["enable_metrics"] is True
    assert TASK_MONITORING["error_threshold"] == 0.1
