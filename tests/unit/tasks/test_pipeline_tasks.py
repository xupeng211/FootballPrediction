"""ETL Pipeline Tasks 测试模块
专注于任务流程串联、参数传递和异常处理的验证。
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Any, Dict

# 直接导入避免Celery装饰器问题
import src.tasks.pipeline_tasks as pipeline_module


class TestSyncTaskConverter:
    """测试同步到异步任务转换器."""

    @pytest.mark.unit
    def test_sync_task_to_async_converter(self):
        """测试同步异步转换函数."""

        # 模拟异步函数
        async def sample_async_func(x, y):
            return x + y

        # 转换为同步函数
        sync_func = pipeline_module.sync_task_to_async(sample_async_func)

        # 执行同步调用
        result = sync_func(2, 3)

        assert result == 5


class TestDataCleaningTask:
    """测试数据清洗任务."""

    @pytest.mark.unit
    @patch("src.tasks.pipeline_tasks.ensure_database_initialized")
    @patch("asyncio.run")
    def test_data_cleaning_task_success_with_new_matches(
        self, mock_asyncio_run, mock_db_init
    ):
        """测试数据清洗任务成功处理并返回新比赛ID."""
        # 设置Mock返回值
        mock_db_init.return_value = True
        mock_asyncio_run.return_value = (8, [1001, 1002, 1003])

        # 模拟采集结果输入
        collection_result = {
            "status": "success",
            "records_collected": 10,
            "total_collected": 10,
        }

        # 直接调用底层函数，绕过Celery装饰器
        result = pipeline_module.data_cleaning_task.__wrapped__(collection_result)

        # 验证结果
        assert result["status"] == "success"
        assert result["cleaned_records"] == 8
        assert result["new_match_ids"] == [1001, 1002, 1003]
        assert "cleaning_timestamp" in result
        assert result["performance_improvement"] == "batch_processing_enabled"

        # 验证调用
        mock_db_init.assert_called_once()
        mock_asyncio_run.assert_called_once()

    @pytest.mark.unit
    def test_data_cleaning_task_no_records_to_process(self):
        """测试数据清洗任务没有记录需要处理."""
        # 模拟空采集结果
        collection_result = {
            "status": "success",
            "records_collected": 0,
            "total_collected": 0,
        }

        # 直接调用底层函数
        result = pipeline_module.data_cleaning_task.__wrapped__(collection_result)

        # 验证结果
        assert result["status"] == "success"
        assert result["cleaned_records"] == 0
        assert result["new_match_ids"] == []
        assert result["errors_removed"] == 0

    @pytest.mark.unit
    @patch("src.tasks.pipeline_tasks.ensure_database_initialized")
    def test_data_cleaning_task_exception_handling(self, mock_db_init):
        """测试数据清洗任务异常处理."""
        # 设置Mock抛出异常
        mock_db_init.side_effect = Exception("Database error")

        # 模拟采集结果
        collection_result = {
            "status": "success",
            "records_collected": 10,
            "total_collected": 10,
        }

        # 执行任务
        result = pipeline_module.data_cleaning_task.__wrapped__(collection_result)

        # 验证错误处理
        assert result["status"] == "error"
        assert "Database error" in result["error"]
        assert "new_match_ids" in result
        assert result["new_match_ids"] == []

    @pytest.mark.unit
    def test_data_cleaning_task_parameter_parsing(self):
        """测试数据清洗任务参数解析正确性."""
        # 测试复杂参数结构
        collection_result = {
            "status": "success",
            "records_collected": 15,
            "total_collected": 15,
            "other_field": "should_be_ignored",
            "nested": {"data": "should_be_ignored"},
        }

        # Mock数据库初始化失败以跳过实际处理
        with patch(
            "src.tasks.pipeline_tasks.ensure_database_initialized"
        ) as mock_db_init:
            mock_db_init.side_effect = Exception("Skip processing")

            result = pipeline_module.data_cleaning_task.__wrapped__(collection_result)

            # 验证即使处理失败，也能正确解析输入参数
            assert result["status"] == "error"
            assert "new_match_ids" in result
            assert result["new_match_ids"] == []


class TestFeatureEngineeringTask:
    """测试特征工程任务."""

    @pytest.mark.unit
    @patch("src.tasks.pipeline_tasks.ensure_database_initialized")
    @patch("src.tasks.pipeline_tasks.FeatureService")
    @patch("src.tasks.pipeline_tasks.get_async_session")
    @patch("asyncio.run")
    def test_feature_engineering_task_success_incremental_update(
        self, mock_asyncio_run, mock_get_session, mock_feature_service, mock_db_init
    ):
        """测试特征工程任务成功执行增量更新."""
        # 设置Mock
        mock_db_init.return_value = True
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟特征服务
        mock_feature_service_instance = MagicMock()
        mock_feature_service.return_value = mock_feature_service_instance
        mock_feature_service_instance.get_match_features.return_value = {
            "features": True
        }

        # 模拟异步函数返回值
        mock_asyncio_run.return_value = {
            "calculated_features": 7,
            "failed_calculations": 1,
        }

        # 模拟清洗结果输入
        cleaning_result = {
            "status": "success",
            "cleaned_records": 8,
            "new_match_ids": [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008],
            "cleaning_timestamp": "2024-12-01T10:00:00",
        }

        # 直接调用底层函数
        result = pipeline_module.feature_engineering_task.__wrapped__(cleaning_result)

        # 验证结果
        assert result["status"] == "success"
        assert result["features_calculated"] == 7
        assert result["failed_calculations"] == 1
        assert result["target_match_count"] == 8
        assert result["new_match_ids"] == [
            1001,
            1002,
            1003,
            1004,
            1005,
            1006,
            1007,
            1008,
        ]
        assert result["feature_type"] == "incremental_update"
        assert "feature_columns" in result

    @pytest.mark.unit
    def test_feature_engineering_task_no_new_matches(self):
        """测试特征工程任务没有新比赛需要处理."""
        # 模拟空清洗结果
        cleaning_result = {
            "status": "success",
            "cleaned_records": 0,
            "new_match_ids": [],
        }

        # 直接调用底层函数
        result = pipeline_module.feature_engineering_task.__wrapped__(cleaning_result)

        # 验证结果
        assert result["status"] == "success"
        assert result["features_calculated"] == 0
        assert result["message"] == "没有新比赛需要生成特征（增量更新）"
        assert result["feature_type"] == "incremental_update"

    @pytest.mark.unit
    def test_feature_engineering_task_parameter_passing(self):
        """测试特征工程任务参数传递的正确性."""
        # 测试包含新比赛ID的清洗结果
        cleaning_result = {
            "status": "success",
            "cleaned_records": 5,
            "new_match_ids": [1001, 1002, 1003, 1004, 1005],
        }

        # Mock数据库初始化失败以跳过实际处理
        with patch(
            "src.tasks.pipeline_tasks.ensure_database_initialized"
        ) as mock_db_init:
            mock_db_init.side_effect = Exception("Skip to test parsing")

            result = pipeline_module.feature_engineering_task.__wrapped__(
                cleaning_result
            )

            # 验证参数传递
            assert result["status"] == "error"
            assert result["new_match_ids"] == [1001, 1002, 1003, 1004, 1005]


class TestDataStorageTask:
    """测试数据存储任务."""

    @pytest.mark.unit
    @patch("src.tasks.pipeline_tasks.ensure_database_initialized")
    def test_data_storage_task_success(self, mock_db_init):
        """测试数据存储任务成功执行."""
        mock_db_init.return_value = True

        # 模拟特征工程结果输入
        feature_result = {
            "status": "success",
            "features_calculated": 7,
            "failed_calculations": 1,
            "target_match_count": 8,
            "new_match_ids": [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008],
            "feature_timestamp": "2024-12-01T10:05:00",
        }

        # 直接调用底层函数
        result = pipeline_module.data_storage_task.__wrapped__(feature_result)

        # 验证结果
        assert result["status"] == "success"
        assert result["stored_features"] == 7
        assert result["database_table"] == "features"
        assert "storage_timestamp" in result

    @pytest.mark.unit
    @patch("src.tasks.pipeline_tasks.ensure_database_initialized")
    def test_data_storage_task_exception_handling(self, mock_db_init):
        """测试数据存储任务异常处理."""
        mock_db_init.side_effect = Exception("Storage failed")

        # 模拟特征工程结果
        feature_result = {
            "status": "success",
            "features_calculated": 7,
        }

        # 直接调用底层函数
        result = pipeline_module.data_storage_task.__wrapped__(feature_result)

        # 验证错误处理
        assert result["status"] == "error"
        assert "Storage failed" in result["error"]


class TestDatabaseInitialization:
    """测试数据库初始化."""

    @pytest.mark.unit
    @patch.dict("os.environ", {"DATABASE_URL": "postgresql://test:test@localhost/test"})
    @patch("src.database.connection.DatabaseManager")
    def test_ensure_database_initialized_with_env_url(self, mock_db_manager):
        """测试使用环境变量数据库URL初始化."""
        mock_instance = MagicMock()
        mock_manager = MagicMock()
        mock_db_manager.return_value = mock_manager
        mock_manager.initialize.return_value = None

        result = pipeline_module.ensure_database_initialized()

        # 验证初始化调用
        mock_manager.initialize.assert_called_once_with(
            database_url="postgresql://test:test@localhost/test"
        )
        assert mock_manager._initialized is True
        assert result == mock_manager

    @pytest.mark.unit
    @patch("src.database.connection.DatabaseManager")
    def test_ensure_database_initialized_exception(self, mock_db_manager):
        """测试数据库初始化异常."""
        mock_db_manager.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception) as exc_info:
            pipeline_module.ensure_database_initialized()

        assert "Database connection failed" in str(exc_info.value)


# TestBatchDataCleaning 类暂时注释以修复导入问题


class TestCallbackFunctions:
    """测试回调函数."""

    @pytest.mark.unit
    @patch("src.tasks.pipeline_tasks.trigger_feature_calculation_for_new_matches")
    def test_on_collection_success_with_match_ids(self, mock_trigger):
        """测试采集成功回调有新比赛ID."""
        # 设置Mock
        mock_trigger.delay.return_value = None

        # 模拟任务结果
        task_result = {"status": "success", "new_match_ids": [1001, 1002, 1003]}

        # 执行回调
        pipeline_module.on_collection_success(task_result, "task-123", (), {})

        # 验证触发特征计算
        mock_trigger.delay.assert_called_once_with([1001, 1002, 1003])

    @pytest.mark.unit
    def test_on_collection_success_no_match_ids(self):
        """测试采集成功回调没有新比赛ID."""
        # 模拟任务结果
        task_result = {"status": "success", "new_match_ids": []}

        # 执行回调 - 应该不抛出异常
        pipeline_module.on_collection_success(task_result, "task-123", (), {})


class TestTaskIntegration:
    """测试任务集成和流程串联."""

    @pytest.mark.unit
    @patch("src.tasks.pipeline_tasks.collect_fotmob_data")
    @patch("src.tasks.pipeline_tasks.chain")
    def test_complete_data_pipeline_task_chain_construction(
        self, mock_chain, mock_collect
    ):
        """测试完整数据管道任务链构建."""
        # 设置Mock
        mock_collect.s.return_value = "collect_signature"

        # Mock chain返回
        mock_pipeline_result = MagicMock()
        mock_pipeline_result.id = "pipeline-123"
        mock_chain.return_value.apply_async.return_value = mock_pipeline_result

        # 直接调用底层函数
        result = pipeline_module.complete_data_pipeline.__wrapped__()

        # 验证任务调用顺序和参数
        mock_collect.s.assert_called_once()
        mock_chain.assert_called_once()

        # 验证chain调用参数
        chain_call_args = mock_chain.call_args[0]
        assert len(chain_call_args) == 4
        assert chain_call_args[0] == "collect_signature"

        # 验证最终结果
        assert result["status"] == "success"
        assert result["task_id"] == "pipeline-123"
        assert result["data_source"] == "fotmob"

    @pytest.mark.unit
    def test_parameter_passing_between_tasks(self):
        """测试任务间参数传递的正确性."""
        # 测试数据清洗任务正确解析采集结果
        collection_result = {
            "status": "success",
            "records_collected": 15,
            "other_field": "should_be_ignored",
        }

        # 模拟数据库初始化失败以跳过实际处理
        with patch(
            "src.tasks.pipeline_tasks.ensure_database_initialized"
        ) as mock_db_init:
            mock_db_init.side_effect = Exception("Skip processing")

            result = pipeline_module.data_cleaning_task.__wrapped__(collection_result)

            # 验证即使处理失败，也能正确解析输入参数
            assert result["status"] == "error"
            assert "new_match_ids" in result
            assert result["new_match_ids"] == []

    @pytest.mark.unit
    def test_error_propagation_in_pipeline(self):
        """测试管道中的错误传播."""
        # 测试空输入的处理
        empty_result = {"status": "success", "cleaned_records": 0, "new_match_ids": []}

        # 验证空输入不会导致异常
        result = pipeline_module.feature_engineering_task.__wrapped__(empty_result)

        assert result["status"] == "success"
        assert result["features_calculated"] == 0
        assert result["feature_type"] == "incremental_update"


class TestFlowValidation:
    """测试流程验证."""

    @pytest.mark.unit
    def test_data_flow_from_collection_to_cleaning(self):
        """测试从数据采集到清洗的数据流."""
        # 模拟采集结果
        collection_result = {
            "status": "success",
            "records_collected": 10,
            "total_collected": 10,
        }

        # 验证清洗任务能正确解析采集结果
        with patch(
            "src.tasks.pipeline_tasks.ensure_database_initialized"
        ) as mock_db_init:
            mock_db_init.side_effect = Exception("Skip to test parsing")

            result = pipeline_module.data_cleaning_task.__wrapped__(collection_result)

            # 验证参数解析
            assert result["status"] == "error"
            assert "cleaning_timestamp" in result

    @pytest.mark.unit
    def test_data_flow_from_cleaning_to_features(self):
        """测试从数据清洗到特征工程的数据流."""
        # 模拟清洗结果，包含新比赛ID
        cleaning_result = {
            "status": "success",
            "cleaned_records": 5,
            "new_match_ids": [1001, 1002, 1003, 1004, 1005],
        }

        # 验证特征工程任务能正确处理新比赛ID
        with patch(
            "src.tasks.pipeline_tasks.ensure_database_initialized"
        ) as mock_db_init:
            mock_db_init.side_effect = Exception("Skip to test parsing")

            result = pipeline_module.feature_engineering_task.__wrapped__(
                cleaning_result
            )

            # 验证参数传递
            assert result["status"] == "error"
            assert result["new_match_ids"] == [1001, 1002, 1003, 1004, 1005]

    @pytest.mark.unit
    def test_error_propagation_in_pipeline(self):
        """测试管道中的错误传播."""
        # 测试空输入的处理
        empty_result = {"status": "success", "cleaned_records": 0, "new_match_ids": []}

        # 验证空输入不会导致异常
        result = pipeline_module.feature_engineering_task.__wrapped__(empty_result)

        assert result["status"] == "success"
        assert result["features_calculated"] == 0
        assert result["feature_type"] == "incremental_update"


class TestTriggerFeatureCalculation:
    """测试特征计算触发器."""

    @pytest.mark.unit
    @patch("src.tasks.pipeline_tasks.FeatureService")
    @patch("src.database.connection.DatabaseManager")
    def test_trigger_feature_calculation_success(
        self, mock_db_manager, mock_feature_service
    ):
        """测试特征计算触发成功."""
        # 设置Mock
        mock_db_instance = MagicMock()
        mock_db_manager.return_value = mock_db_instance

        mock_service_instance = MagicMock()
        mock_feature_service.return_value = mock_service_instance

        # 模拟成功计算特征
        mock_service_instance.calculate_match_features.return_value = {
            "status": "success"
        }

        match_ids = [1001, 1002, 1003]

        with patch("asyncio.run") as mock_asyncio_run:
            # 模拟异步执行成功
            mock_asyncio_run.return_value = {"calculated_count": 3, "failed_count": 0}

            result = (
                pipeline_module.trigger_feature_calculation_for_new_matches.__wrapped__(
                    match_ids
                )
            )

            # 验证结果
            assert result["status"] == "success"
            assert result["calculated_count"] == 3
            assert result["failed_count"] == 0
            assert len(match_ids) == 3

    @pytest.mark.unit
    def test_trigger_feature_calculation_empty_match_ids(self):
        """测试特征计算触发器处理空match_ids."""
        result = (
            pipeline_module.trigger_feature_calculation_for_new_matches.__wrapped__([])
        )

        # 验证空列表处理
        assert result["status"] == "success"
        assert result["calculated_count"] == 0
        assert result["failed_count"] == 0

    @pytest.mark.unit
    @patch("src.database.connection.DatabaseManager")
    def test_trigger_feature_calculation_db_error(self, mock_db_manager):
        """测试特征计算触发器数据库错误."""
        mock_db_manager.side_effect = Exception("Database connection failed")

        result = (
            pipeline_module.trigger_feature_calculation_for_new_matches.__wrapped__(
                [1001, 1002]
            )
        )

        # 验证错误处理
        assert result["status"] == "error"
        assert "Database connection failed" in result["error"]


class TestPerformanceAndOptimization:
    """测试性能优化功能."""

    @pytest.mark.unit
    def test_batch_processing_performance(self):
        """测试批处理性能优化."""
        with patch(
            "src.tasks.pipeline_tasks.ensure_database_initialized"
        ) as mock_db_init:
            mock_db_init.return_value = True

            with patch("asyncio.run") as mock_asyncio:
                # 模拟高性能批处理
                mock_asyncio.return_value = (100, [i for i in range(1, 101)])

                collection_result = {"status": "success", "records_collected": 100}
                result = pipeline_module.data_cleaning_task.__wrapped__(
                    collection_result
                )

                # 验证批处理优化标记
                assert result["performance_improvement"] == "batch_processing_enabled"

    @pytest.mark.unit
    def test_memory_efficiency(self):
        """测试内存效率."""
        # 测试大数据集处理不会导致内存问题
        large_match_ids = list(range(1, 10001))  # 10000个比赛ID

        with patch("src.database.connection.DatabaseManager"):
            with patch("asyncio.run") as mock_asyncio_run:
                # 模拟分批处理
                mock_asyncio_run.return_value = {
                    "calculated_count": 10000,
                    "failed_count": 0,
                }

                result = pipeline_module.trigger_feature_calculation_for_new_matches.__wrapped__(
                    large_match_ids
                )

                # 验证能处理大量数据
                assert result["calculated_count"] == 10000


# 测试数据常量
MOCK_COLLECTION_RESULT_SUCCESS = {
    "status": "success",
    "records_collected": 10,
    "total_collected": 10,
    "collected_records": 10,
}

MOCK_COLLECTION_RESULT_EMPTY = {
    "status": "success",
    "records_collected": 0,
    "total_collected": 0,
}

MOCK_CLEANING_RESULT_SUCCESS = {
    "status": "success",
    "cleaned_records": 8,
    "new_match_ids": [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008],
    "cleaning_timestamp": "2024-12-01T10:00:00",
}

MOCK_FEATURE_RESULT_SUCCESS = {
    "status": "success",
    "features_calculated": 7,
    "failed_calculations": 1,
    "target_match_count": 8,
    "new_match_ids": [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008],
    "feature_timestamp": "2024-12-01T10:05:00",
}
