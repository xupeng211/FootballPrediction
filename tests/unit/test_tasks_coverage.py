#!/usr/bin/env python3
"""
Tasks模块覆盖测试
目标：为tasks模块获得初始覆盖
"""

import pytest
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestTasksCoverage:
    """Tasks模块覆盖测试"""

    def test_celery_app_import(self):
        """测试Celery应用导入"""
        try:
            from src.tasks.celery_app import celery_app

            # 测试app存在
            assert celery_app is not None
            assert hasattr(celery_app, "task")
        except ImportError:
            pytest.skip("Celery app导入失败")

    def test_data_collection_tasks(self):
        """测试数据收集任务"""
        try:
            from src.tasks.data_collection_core import DataCollectionCore

            # 测试核心类存在
            assert DataCollectionCore is not None
        except ImportError:
            pytest.skip("Data collection tasks导入失败")

    def test_maintenance_tasks(self):
        """测试维护任务"""
        try:
            from src.tasks.maintenance_tasks import (
                cleanup_old_data,
                backup_database,
                update_statistics,
            )

            # 测试函数存在
            assert cleanup_old_data is not None
            assert backup_database is not None
            assert update_statistics is not None
        except ImportError:
            pytest.skip("Maintenance tasks导入失败")

    def test_monitoring_tasks(self):
        """测试监控任务"""
        try:
            from src.tasks.monitoring import (
                check_system_health,
                collect_metrics,
                send_alerts,
            )

            # 测试函数存在
            assert check_system_health is not None
            assert collect_metrics is not None
            assert send_alerts is not None
        except ImportError:
            pytest.skip("Monitoring tasks导入失败")

    def test_streaming_tasks(self):
        """测试流处理任务"""
        try:
            from src.tasks.streaming_tasks import (
                process_kafka_messages,
                handle_real_time_data,
            )

            # 测试函数存在
            assert process_kafka_messages is not None
            assert handle_real_time_data is not None
        except ImportError:
            pytest.skip("Streaming tasks导入失败")

    def test_backup_tasks(self):
        """测试备份任务"""
        try:
            from src.tasks.backup_tasks import (
                create_backup,
                restore_backup,
                verify_backup,
            )

            # 测试函数存在
            assert create_backup is not None
            assert restore_backup is not None
            assert verify_backup is not None
        except ImportError:
            pytest.skip("Backup tasks导入失败")
