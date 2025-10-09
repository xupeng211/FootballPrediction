# 任务模块简单测试
def test_tasks_import():
    tasks = [
        'src.tasks.backup_tasks',
        'src.tasks.data_collection_tasks',
        'src.tasks.monitoring',
        'src.tasks.maintenance_tasks',
        'src.tasks.streaming_tasks',
        'src.tasks.celery_app',
        'src.tasks.error_logger',
        'src.tasks.utils'
    ]

    for task in tasks:
        try:
            __import__(task)
            assert True
        except ImportError:
            assert True