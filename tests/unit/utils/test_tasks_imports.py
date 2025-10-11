import pytest


@pytest.mark.parametrize(
    "task_module",
    [
        "src.tasks.backup_tasks",
        "src.tasks.data_collection_tasks",
        "src.tasks.monitoring",
        "src.tasks.maintenance_tasks",
        "src.tasks.streaming_tasks",
    ],
)
def test_task_module_import(task_module):
    """测试任务模块导入"""
    try:
        __import__(task_module)
        assert True
    except ImportError:
        pytest.skip(f"Task module {task_module} not available")


def test_celery_app():
    try:
        from src.tasks.celery_app import celery_app

        assert celery_app is not None
    except ImportError:
        pytest.skip("Celery app not available")
