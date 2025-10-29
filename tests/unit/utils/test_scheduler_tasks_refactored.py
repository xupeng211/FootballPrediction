"""
测试重构后的调度任务模块

验证拆分后的各个组件是否正常工作。
"""

import pytest


@pytest.mark.unit
class TestBaseDataTask:
    """测试基础任务类"""

    def test_base_task_initialization(self):
        """测试基础任务初始化"""
        from src.scheduler.tasks.base.base_task import BaseDataTask

        # 基础任务类应该可以被继承
        assert hasattr(BaseDataTask, "on_failure")
        assert hasattr(BaseDataTask, "on_success")
        assert hasattr(BaseDataTask, "_send_alert_notification")


class TestDataCollectionTasks:
    """测试数据采集任务"""

    def test_import_data_collection_tasks(self):
        """测试导入数据采集任务"""
        from src.scheduler.tasks.data_collection import (
            collect_fixtures,
            collect_live_scores_conditional,
            collect_odds,
        )

        # 任务应该可以被导入
        assert collect_fixtures is not None
        assert collect_odds is not None
        assert collect_live_scores_conditional is not None

    @patch("src.scheduler.tasks.data_collection.fixtures_task.FixturesCollector")
    def test_collect_fixtures_task(self, mock_collector_class):
        """测试赛程采集任务"""
        from src.scheduler.tasks.data_collection.fixtures_task import collect_fixtures

        # Mock采集器
        mock_collector = Mock()
        mock_collector.collect_fixtures.return_value = {
            "status": "success",
            "fixtures_count": 10,
        }
        mock_collector_class.return_value = mock_collector

        # 任务应该存在
        assert collect_fixtures is not None
        assert hasattr(collect_fixtures, "run")


class TestFeatureCalculationTask:
    """测试特征计算任务"""

    def test_import_feature_calculation_task(self):
        """测试导入特征计算任务"""
        from src.scheduler.tasks.feature_calculation import calculate_features_batch

        # 任务应该可以被导入
        assert calculate_features_batch is not None


class TestCleanupTask:
    """测试数据清理任务"""

    def test_import_cleanup_task(self):
        """测试导入数据清理任务"""
        from src.scheduler.tasks.data_cleanup import cleanup_data

        # 任务应该可以被导入
        assert cleanup_data is not None


class TestQualityCheckTask:
    """测试质量检查任务"""

    def test_import_quality_check_task(self):
        """测试导入质量检查任务"""
        from src.scheduler.tasks.quality_check import run_quality_checks

        # 任务应该可以被导入
        assert run_quality_checks is not None


class TestBackupTask:
    """测试数据库备份任务"""

    def test_import_backup_task(self):
        """测试导入数据库备份任务"""
        from src.scheduler.tasks.database_backup import backup_database

        # 任务应该可以被导入
        assert backup_database is not None


class TestPredictionTask:
    """测试预测任务"""

    def test_import_prediction_task(self):
        """测试导入预测任务"""
        from src.scheduler.tasks.prediction import generate_predictions

        # 任务应该可以被导入
        assert generate_predictions is not None


class TestTransformationTask:
    """测试数据转换任务"""

    def test_import_transformation_task(self):
        """测试导入数据转换任务"""
        from src.scheduler.tasks.data_transformation import process_bronze_to_silver

        # 任务应该可以被导入
        assert process_bronze_to_silver is not None


class TestTasksModule:
    """测试任务模块导入"""

    def test_import_all_tasks(self):
        """测试导入所有任务"""
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

        # 所有任务都应该可以被导入
        assert BaseDataTask is not None
        assert collect_fixtures is not None
        assert collect_odds is not None
        assert collect_live_scores_conditional is not None
        assert calculate_features_batch is not None
        assert cleanup_data is not None
        assert run_quality_checks is not None
        assert backup_database is not None
        assert generate_predictions is not None
        assert process_bronze_to_silver is not None


class TestModuleStructure:
    """测试模块结构"""

    def test_module_attributes(self):
        """测试模块属性"""
        import src.scheduler.tasks

        # 模块应该有版本信息
        assert hasattr(src.scheduler.tasks, "__version__")
        assert hasattr(src.scheduler.tasks, "__description__")
        assert src.scheduler.tasks.__version__ == "2.0.0"


if __name__ == "__main__":
    pytest.main([__file__])
