"""
测试调度任务模块化拆分
Test modular split of scheduler tasks
"""

import pytest


@pytest.mark.unit
class TestBaseModule:
    """测试基础任务模块"""

    def test_base_data_task_import(self):
        """测试基础任务类导入"""
from src.scheduler.tasks.base import BaseDataTask

        assert BaseDataTask is not None

    def test_base_data_task_methods(self):
        """测试基础任务类方法"""
from src.scheduler.tasks.base import BaseDataTask

        # 创建实例
        task = BaseDataTask()

        # 测试方法存在
        assert hasattr(task, "on_failure")
        assert hasattr(task, "on_success")
        assert hasattr(task, "get_retry_config")
        assert callable(task.get_retry_config)


class TestCollectionModule:
    """测试数据采集任务模块"""

    def test_collection_imports(self):
        """测试数据采集任务导入"""
from src.scheduler.tasks.collection import (
            collect_fixtures,
            collect_live_scores_conditional,
            collect_odds,
        )

        assert collect_fixtures is not None
        assert collect_odds is not None
        assert collect_live_scores_conditional is not None

    def test_collection_tasks_are_celery_tasks(self):
        """测试数据采集任务是Celery任务"""
        from celery import Task

from src.scheduler.tasks.collection import (
            collect_fixtures,
            collect_live_scores_conditional,
            collect_odds,
        )

        assert isinstance(collect_fixtures, Task)
        assert isinstance(collect_odds, Task)
        assert isinstance(collect_live_scores_conditional, Task)


class TestFeaturesModule:
    """测试特征计算任务模块"""

    def test_features_import(self):
        """测试特征计算任务导入"""
from src.scheduler.tasks.features import calculate_features_batch

        assert calculate_features_batch is not None

    def test_features_task_is_celery_task(self):
        """测试特征计算任务是Celery任务"""
        from celery import Task

from src.scheduler.tasks.features import calculate_features_batch

        assert isinstance(calculate_features_batch, Task)


class TestMaintenanceModule:
    """测试维护任务模块"""

    def test_maintenance_imports(self):
        """测试维护任务导入"""
from src.scheduler.tasks.maintenance import backup_database, cleanup_data

        assert cleanup_data is not None
        assert backup_database is not None

    def test_maintenance_tasks_are_celery_tasks(self):
        """测试维护任务是Celery任务"""
        from celery import Task

from src.scheduler.tasks.maintenance import backup_database, cleanup_data

        assert isinstance(cleanup_data, Task)
        assert isinstance(backup_database, Task)


class TestQualityModule:
    """测试质量检查任务模块"""

    def test_quality_import(self):
        """测试质量检查任务导入"""
from src.scheduler.tasks.quality import run_quality_checks

        assert run_quality_checks is not None

    def test_quality_task_is_celery_task(self):
        """测试质量检查任务是Celery任务"""
        from celery import Task

from src.scheduler.tasks.quality import run_quality_checks

        assert isinstance(run_quality_checks, Task)


class TestPredictionsModule:
    """测试预测任务模块"""

    def test_predictions_import(self):
        """测试预测任务导入"""
from src.scheduler.tasks.predictions import generate_predictions

        assert generate_predictions is not None

    def test_predictions_task_is_celery_task(self):
        """测试预测任务是Celery任务"""
        from celery import Task

from src.scheduler.tasks.predictions import generate_predictions

        assert isinstance(generate_predictions, Task)


class TestProcessingModule:
    """测试数据处理任务模块"""

    def test_processing_import(self):
        """测试数据处理任务导入"""
from src.scheduler.tasks.processing import process_bronze_to_silver

        assert process_bronze_to_silver is not None

    def test_processing_task_is_celery_task(self):
        """测试数据处理任务是Celery任务"""
        from celery import Task

from src.scheduler.tasks.processing import process_bronze_to_silver

        assert isinstance(process_bronze_to_silver, Task)


class TestModularStructure:
    """测试模块化结构"""

    def test_import_from_main_module(self):
        """测试从主模块导入"""
from src.scheduler.tasks import (
            BaseDataTask,
            backup_database,
            calculate_features_batch,
            cleanup_data,
            collect_fixtures,
            collect_live_scores_conditional,
            collect_odds,
            generate_predictions,
            process_bronze_to_silver,
            run_quality_checks,
        )

        assert BaseDataTask is not None
        assert collect_fixtures is not None
        assert collect_odds is not None
        assert collect_live_scores_conditional is not None
        assert calculate_features_batch is not None
        assert cleanup_data is not None
        assert backup_database is not None
        assert run_quality_checks is not None
        assert generate_predictions is not None
        assert process_bronze_to_silver is not None

    def test_backward_compatibility_imports(self):
        """测试向后兼容性导入"""
        # 从原始文件导入应该仍然有效
from src.scheduler.tasks import BaseDataTask as old_base
from src.scheduler.tasks import calculate_features_batch as old_features
from src.scheduler.tasks import collect_fixtures as old_fixtures

        assert old_base is not None
        assert old_fixtures is not None
        assert old_features is not None

    def test_task_aliases_exist(self):
        """测试任务别名存在"""
from src.scheduler.tasks import (
            calculate_features_task,
            collect_fixtures_task,
            collect_odds_task,
            generate_predictions_task,
            process_data_task,
        )

        assert calculate_features_task is not None
        assert collect_fixtures_task is not None
        assert collect_odds_task is not None
        assert generate_predictions_task is not None
        assert process_data_task is not None

    def test_task_aliases_are_correct(self):
        """测试任务别名正确"""
from src.scheduler.tasks import (
            calculate_features_batch,
            calculate_features_task,
            collect_fixtures,
            collect_fixtures_task,
        )

        # 别名应该指向相同的任务
        assert calculate_features_task == calculate_features_batch
        assert collect_fixtures_task == collect_fixtures

    def test_all_tasks_are_exported(self):
        """测试所有任务都被导出"""
from src.scheduler.tasks import __all__

        expected_exports = [
            "BaseDataTask",
            "collect_fixtures",
            "collect_odds",
            "collect_live_scores_conditional",
            "calculate_features_batch",
            "cleanup_data",
            "backup_database",
            "run_quality_checks",
            "generate_predictions",
            "process_bronze_to_silver",
            "calculate_features_task",
            "collect_fixtures_task",
            "collect_odds_task",
            "generate_predictions_task",
            "process_data_task",
        ]

        for export in expected_exports:
            assert export in __all__

    def test_module_structure_is_valid(self):
        """测试模块结构有效"""
        import src.scheduler.tasks as tasks_module

        # 验证模块有正确的属性
        assert hasattr(tasks_module, "BaseDataTask")
        assert hasattr(tasks_module, "collect_fixtures")
        assert hasattr(tasks_module, "calculate_features_batch")
        assert hasattr(tasks_module, "cleanup_data")
        assert hasattr(tasks_module, "run_quality_checks")
        assert hasattr(tasks_module, "generate_predictions")
        assert hasattr(tasks_module, "process_bronze_to_silver")


@pytest.mark.asyncio
async def test_integration_example():
    """测试集成示例"""
    from src.scheduler.tasks import BaseDataTask

    # 验证BaseDataTask可以正常使用
    task = BaseDataTask()

    # 测试get_retry_config方法
    _config = task.get_retry_config("test_task")
    assert isinstance(config, dict)
    assert "max_retries" in config
    assert "retry_delay" in config
