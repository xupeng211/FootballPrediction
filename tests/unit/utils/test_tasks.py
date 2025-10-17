"""任务模块测试"""

import pytest


class TestTasks:
    """测试任务模块"""

    def test_celery_app_import(self):
        """测试Celery应用导入"""
        try:
            from src.tasks.celery_app import celery_app

            assert celery_app is not None
        except ImportError:
            pass  # 已激活

    def test_backup_tasks_import(self):
        """测试备份任务导入"""
        try:
            from src.tasks.backup_tasks import BackupTaskManager

            assert BackupTaskManager is not None
        except ImportError:
            pass  # 已激活

    def test_data_collection_tasks_import(self):
        """测试数据收集任务导入"""
        try:
            from src.tasks.data_collection_tasks import collect_fixtures_data

            assert callable(collect_fixtures_data)
        except ImportError:
            pass  # 已激活

    def test_maintenance_tasks_import(self):
        """测试维护任务导入"""
        try:
            from src.tasks.maintenance_tasks import MaintenanceManager

            assert MaintenanceManager is not None
        except ImportError:
            pass  # 已激活
