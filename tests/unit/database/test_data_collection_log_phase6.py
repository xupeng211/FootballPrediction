"""
Phase 6: data_collection_log.py 补测用例
目标：提升覆盖率从 62% 到 70%+
重点：验证器、属性方法、异常情况、边界条件
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.database.models.data_collection_log import (
    CollectionStatus,
    CollectionType,
    DataCollectionLog,
)


class TestDataCollectionLogValidation:
    """测试数据验证逻辑"""

    def test_validate_collection_type_valid(self):
        """测试有效的采集类型验证"""
        log = DataCollectionLog()

        # 测试所有有效类型
        for collection_type in CollectionType:
            result = log.validate_collection_type(
                "collection_type", collection_type.value
            )
            assert result == collection_type.value

    def test_validate_collection_type_invalid(self):
        """测试无效的采集类型验证"""
        log = DataCollectionLog()

        with pytest.raises(ValueError) as excinfo:
            log.validate_collection_type("collection_type", "invalid_type")

        assert "Invalid collection type: invalid_type" in str(excinfo.value)
        assert "Must be one of:" in str(excinfo.value)

    def test_validate_status_valid(self):
        """测试有效的状态验证"""
        log = DataCollectionLog()

        # 测试所有有效状态
        for status in CollectionStatus:
            result = log.validate_status("status", status.value)
            assert result == status.value

    def test_validate_status_invalid(self):
        """测试无效的状态验证"""
        log = DataCollectionLog()

        with pytest.raises(ValueError) as excinfo:
            log.validate_status("status", "invalid_status")

        assert "Invalid status: invalid_status" in str(excinfo.value)
        assert "Must be one of:" in str(excinfo.value)

    def test_validate_collection_type_edge_cases(self):
        """测试边界情况"""
        log = DataCollectionLog()

        # 测试空字符串
        with pytest.raises(ValueError):
            log.validate_collection_type("collection_type", "")

        # 测试 None 值（转换为字符串）
        with pytest.raises(ValueError):
            log.validate_collection_type("collection_type", str(None))

    def test_validate_status_edge_cases(self):
        """测试状态验证的边界情况"""
        log = DataCollectionLog()

        # 测试空字符串
        with pytest.raises(ValueError):
            log.validate_status("status", "")

        # 测试大小写敏感
        with pytest.raises(ValueError):
            log.validate_status("status", "SUCCESS")  # 应该是小写


class TestDataCollectionLogProperties:
    """测试属性方法"""

    def test_duration_seconds_with_both_times(self):
        """测试有开始和结束时间时的耗时计算"""
        log = DataCollectionLog()
        start_time = datetime(2023, 1, 1, 10, 0, 0)
        end_time = datetime(2023, 1, 1, 10, 5, 30)  # 5分30秒后

        log.start_time = start_time
        log.end_time = end_time

        duration = log.duration_seconds
        assert duration == 330.0  # 5*60 + 30 = 330秒

    def test_duration_seconds_missing_start_time(self):
        """测试缺少开始时间"""
        log = DataCollectionLog()
        log.start_time = None
        log.end_time = datetime.now()

        assert log.duration_seconds is None

    def test_duration_seconds_missing_end_time(self):
        """测试缺少结束时间"""
        log = DataCollectionLog()
        log.start_time = datetime.now()
        log.end_time = None

        assert log.duration_seconds is None

    def test_duration_seconds_both_missing(self):
        """测试开始和结束时间都缺少"""
        log = DataCollectionLog()
        log.start_time = None
        log.end_time = None

        assert log.duration_seconds is None

    def test_success_rate_with_data(self):
        """测试有数据时的成功率计算"""
        log = DataCollectionLog()
        log.success_count = 8
        log.error_count = 2

        assert log.success_rate == 0.8  # 8/(8+2) = 0.8

    def test_success_rate_zero_total(self):
        """测试总数为0时的成功率"""
        log = DataCollectionLog()
        log.success_count = 0
        log.error_count = 0

        assert log.success_rate == 0.0

    def test_success_rate_only_errors(self):
        """测试只有错误时的成功率"""
        log = DataCollectionLog()
        log.success_count = 0
        log.error_count = 5

        assert log.success_rate == 0.0

    def test_success_rate_only_success(self):
        """测试只有成功时的成功率"""
        log = DataCollectionLog()
        log.success_count = 10
        log.error_count = 0

        assert log.success_rate == 1.0

    def test_is_completed_success(self):
        """测试成功状态是否为已完成"""
        log = DataCollectionLog()
        log.status = CollectionStatus.SUCCESS.value
        assert log.is_completed is True

    def test_is_completed_failed(self):
        """测试失败状态是否为已完成"""
        log = DataCollectionLog()
        log.status = CollectionStatus.FAILED.value
        assert log.is_completed is True

    def test_is_completed_partial(self):
        """测试部分成功状态是否为已完成"""
        log = DataCollectionLog()
        log.status = CollectionStatus.PARTIAL.value
        assert log.is_completed is True

    def test_is_completed_running(self):
        """测试运行中状态不是已完成"""
        log = DataCollectionLog()
        log.status = CollectionStatus.RUNNING.value
        assert log.is_completed is False

    def test_is_successful_true(self):
        """测试成功状态"""
        log = DataCollectionLog()
        log.status = CollectionStatus.SUCCESS.value
        assert log.is_successful is True

    def test_is_successful_false(self):
        """测试非成功状态"""
        log = DataCollectionLog()

        # 测试其他所有状态
        for status in [
            CollectionStatus.FAILED,
            CollectionStatus.PARTIAL,
            CollectionStatus.RUNNING,
        ]:
            log.status = status.value
            assert log.is_successful is False


class TestDataCollectionLogMethods:
    """测试方法"""

    @patch("src.database.models.data_collection_log.datetime")
    def test_mark_started(self, mock_datetime):
        """测试标记开始"""
        mock_now = datetime(2023, 1, 1, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        log = DataCollectionLog()
        log.mark_started()

        assert log.start_time == mock_now
        assert log.status == CollectionStatus.RUNNING.value

    @patch("src.database.models.data_collection_log.datetime")
    def test_mark_completed_success(self, mock_datetime):
        """测试标记成功完成"""
        mock_now = datetime(2023, 1, 1, 10, 5, 0)
        mock_datetime.now.return_value = mock_now

        log = DataCollectionLog()
        log.mark_completed(
            status=CollectionStatus.SUCCESS,
            records_collected=100,
            success_count=95,
            error_count=5,
            error_message="Minor errors",
        )

        assert log.end_time == mock_now
        assert log.status == CollectionStatus.SUCCESS.value
        assert log.records_collected == 100
        assert log.success_count == 95
        assert log.error_count == 5
        assert log.error_message == "Minor errors"

    @patch("src.database.models.data_collection_log.datetime")
    def test_mark_completed_without_error_message(self, mock_datetime):
        """测试标记完成但不提供错误信息"""
        mock_now = datetime(2023, 1, 1, 10, 5, 0)
        mock_datetime.now.return_value = mock_now

        log = DataCollectionLog()
        log.error_message = "previous error"  # 设置之前的错误信息

        log.mark_completed(
            status=CollectionStatus.SUCCESS,
            records_collected=50,
            success_count=50,
            error_count=0,
            # 不提供 error_message
        )

        # error_message 应该保持之前的值
        assert log.error_message == "previous error"

    @patch("src.database.models.data_collection_log.datetime")
    def test_mark_completed_failed(self, mock_datetime):
        """测试标记失败完成"""
        mock_now = datetime(2023, 1, 1, 10, 5, 0)
        mock_datetime.now.return_value = mock_now

        log = DataCollectionLog()
        log.mark_completed(
            status=CollectionStatus.FAILED,
            records_collected=0,
            success_count=0,
            error_count=1,
            error_message="Connection timeout",
        )

        assert log.end_time == mock_now
        assert log.status == CollectionStatus.FAILED.value
        assert log.records_collected == 0
        assert log.success_count == 0
        assert log.error_count == 1
        assert log.error_message == "Connection timeout"


class TestDataCollectionLogRepresentation:
    """测试字符串表示和字典转换"""

    def test_repr(self):
        """测试字符串表示"""
        log = DataCollectionLog()
        log.id = 123
        log.data_source = "api-sports"
        log.collection_type = CollectionType.FIXTURES.value
        log.status = CollectionStatus.SUCCESS.value
        log.records_collected = 150

        repr_str = repr(log)

        assert "DataCollectionLog(" in repr_str
        assert "id=123" in repr_str
        assert "source=api-sports" in repr_str
        assert "type=fixtures" in repr_str
        assert "status=success" in repr_str
        assert "records=150" in repr_str

    def test_to_dict_basic(self):
        """测试基本字典转换"""
        log = DataCollectionLog()
        log.id = 456
        log.data_source = "rapid-api"
        log.collection_type = CollectionType.ODDS.value
        log.status = CollectionStatus.PARTIAL.value
        log.records_collected = 75
        log.success_count = 70
        log.error_count = 5
        log.error_message = "Some data missing"

        start_time = datetime(2023, 1, 1, 9, 0, 0)
        end_time = datetime(2023, 1, 1, 9, 10, 0)
        log.start_time = start_time
        log.end_time = end_time

        result = log.to_dict()

        expected_keys = {
            "id",
            "data_source",
            "collection_type",
            "status",
            "records_collected",
            "success_count",
            "error_count",
            "error_message",
            "start_time",
            "end_time",
            "created_at",
            "duration_seconds",
            "success_rate",
        }

        assert set(result.keys()) == expected_keys
        assert result["id"] == 456
        assert result["data_source"] == "rapid-api"
        assert result["collection_type"] == CollectionType.ODDS.value
        assert result["status"] == CollectionStatus.PARTIAL.value
        assert result["duration_seconds"] == 600.0  # 10分钟
        assert result["success_rate"] == 70 / 75  # 成功率


class TestDataCollectionLogEdgeCases:
    """测试边界情况和异常场景"""

    def test_negative_counts(self):
        """测试负数计数的成功率计算"""
        log = DataCollectionLog()
        log.success_count = -1  # 异常情况
        log.error_count = 5

        # 虽然数据异常，但代码应该不崩溃
        success_rate = log.success_rate
        assert success_rate == -0.25  # -1/(4) = -0.25

    def test_extremely_large_numbers(self):
        """测试极大数字"""
        log = DataCollectionLog()
        log.success_count = 999999999
        log.error_count = 1

        success_rate = log.success_rate
        assert success_rate > 0.99999  # 接近1但不等于1

    def test_zero_division_edge_case(self):
        """确保零除法处理正确"""
        log = DataCollectionLog()
        log.success_count = 0
        log.error_count = 0

        # 应该返回 0.0 而不是抛出异常
        assert log.success_rate == 0.0

    def test_duration_with_negative_time_difference(self):
        """测试时间差为负的异常情况"""
        log = DataCollectionLog()
        log.start_time = datetime(2023, 1, 1, 10, 0, 0)
        log.end_time = datetime(2023, 1, 1, 9, 0, 0)  # 结束时间早于开始时间

        duration = log.duration_seconds
        assert duration == -3600.0  # -1小时

    def test_mark_completed_with_enum_types(self):
        """测试使用枚举类型标记完成"""
        log = DataCollectionLog()

        # 确保方法接受枚举类型参数
        log.mark_completed(
            status=CollectionStatus.PARTIAL,  # 传入枚举而不是字符串
            records_collected=10,
            success_count=8,
            error_count=2,
        )

        assert log.status == CollectionStatus.PARTIAL.value

    def test_model_with_minimal_data(self):
        """测试最小数据集的模型"""
        log = DataCollectionLog()

        # 只设置必需字段
        log.data_source = "test-source"
        log.collection_type = CollectionType.FIXTURES.value
        log.status = CollectionStatus.RUNNING.value
        log.start_time = datetime.now()  # start_time 是必需字段

        # 其他属性应该有合理的默认行为
        assert log.duration_seconds is None  # 没有结束时间
        assert log.success_rate == 0.0  # 默认计数都是0
        assert not log.is_completed  # RUNNING状态未完成
        assert not log.is_successful  # RUNNING状态不算成功

    def test_concurrent_property_access(self):
        """测试并发属性访问"""
        log = DataCollectionLog()
        log.start_time = datetime(2023, 1, 1, 10, 0, 0)
        log.end_time = datetime(2023, 1, 1, 10, 5, 0)
        log.success_count = 10
        log.error_count = 0
        log.status = CollectionStatus.SUCCESS.value

        # 同时访问多个属性
        results = []
        results.append(log.duration_seconds)
        results.append(log.success_rate)
        results.append(log.is_completed)
        results.append(log.is_successful)

        assert results[0] == 300.0  # 5分钟
        assert results[1] == 1.0  # 100%成功
        assert results[2] is True  # 已完成
        assert results[3] is True  # 成功
