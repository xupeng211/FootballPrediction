"""
异常检测器增强测试 - 覆盖率提升版本

针对 AnomalyDetector 和相关类的详细测试，专注于提升覆盖率至 70%+
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.monitoring.anomaly_detector import (
    AnomalyResult,
    AnomalyType,
    AnomalySeverity,
    AnomalyDetector
)


class TestAnomalyResult:
    """异常结果类测试"""

    def test_init_minimal(self):
        """测试最小初始化"""
        result = AnomalyResult(
            timestamp=datetime.now(timezone.utc),
            value=100.0,
            expected_range=(50.0, 80.0),
            severity=0.8,
            anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
            detection_method=DetectionMethod.THREE_SIGMA
        )

        assert isinstance(result.timestamp, datetime)
        assert result.value == 100.0
        assert result.expected_range == (50.0, 80.0)
        assert result.severity == 0.8
        assert result.anomaly_type == AnomalyType.STATISTICAL_OUTLIER
        assert result.detection_method == DetectionMethod.THREE_SIGMA
        assert result.metadata == {}

    def test_init_with_metadata(self):
        """测试带元数据的初始化"""
        metadata = {"sensor_id": "sensor_1", "location": "server_room"}
        result = AnomalyResult(
            timestamp=datetime.now(timezone.utc),
            value=200.0,
            expected_range=(100.0, 150.0),
            severity=0.9,
            anomaly_type=AnomalyType.THRESHOLD_VIOLATION,
            detection_method=DetectionMethod.FIXED_THRESHOLD,
            metadata=metadata
        )

        assert result.metadata == metadata

    def test_is_anomaly(self):
        """测试是否为异常"""
        # 明显异常
        result_high = AnomalyResult(
            timestamp=datetime.now(timezone.utc),
            value=100.0,
            expected_range=(50.0, 80.0),
            severity=0.8,
            anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
            detection_method=DetectionMethod.THREE_SIGMA
        )
        assert result_high.is_anomaly()

        # 轻微异常
        result_low = AnomalyResult(
            timestamp=datetime.now(timezone.utc),
            value=100.0,
            expected_range=(50.0, 80.0),
            severity=0.3,
            anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
            detection_method=DetectionMethod.THREE_SIGMA
        )
        assert not result_low.is_anomaly()

    def test_to_dict(self):
        """测试转换为字典"""
        result = AnomalyResult(
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            value=100.0,
            expected_range=(50.0, 80.0),
            severity=0.8,
            anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
            detection_method=DetectionMethod.THREE_SIGMA,
            metadata={"test": "value"}
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["timestamp"] == "2024-01-15T10:30:00+00:00"
        assert result_dict["value"] == 100.0
        assert result_dict["expected_range"] == [50.0, 80.0]
        assert result_dict["severity"] == 0.8
        assert result_dict["anomaly_type"] == "STATISTICAL_OUTLIER"
        assert result_dict["detection_method"] == "THREE_SIGMA"
        assert result_dict["metadata"] == {"test": "value"}

    def test_from_dict(self):
        """测试从字典创建"""
        result_data = {
            "timestamp": "2024-01-15T10:30:00+00:00",
            "value": 100.0,
            "expected_range": [50.0, 80.0],
            "severity": 0.8,
            "anomaly_type": "STATISTICAL_OUTLIER",
            "detection_method": "THREE_SIGMA",
            "metadata": {"test": "value"}
        }

        result = AnomalyResult.from_dict(result_data)

        assert result.timestamp == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert result.value == 100.0
        assert result.expected_range == (50.0, 80.0)
        assert result.severity == 0.8
        assert result.anomaly_type == AnomalyType.STATISTICAL_OUTLIER
        assert result.detection_method == DetectionMethod.THREE_SIGMA

    def test_str_representation(self):
        """测试字符串表示"""
        result = AnomalyResult(
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            value=100.0,
            expected_range=(50.0, 80.0),
            severity=0.8,
            anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
            detection_method=DetectionMethod.THREE_SIGMA
        )

        result_str = str(result)

        assert "AnomalyResult" in result_str
        assert "100.0" in result_str
        assert "STATISTICAL_OUTLIER" in result_str
        assert "THREE_SIGMA" in result_str

    def test_anomaly_types(self):
        """测试异常类型"""
        types = [
            AnomalyType.STATISTICAL_OUTLIER,
            AnomalyType.THRESHOLD_VIOLATION,
            AnomalyType.PATTERN_DEVIATION,
            AnomalyType.SEASONAL_ANOMALY,
            AnomalyType.CONTEXTUAL_ANOMALY
        ]

        for anomaly_type in types:
            result = AnomalyResult(
                timestamp=datetime.now(timezone.utc),
                value=100.0,
                expected_range=(50.0, 80.0),
                severity=0.8,
                anomaly_type=anomaly_type,
                detection_method=DetectionMethod.THREE_SIGMA
            )
            assert result.anomaly_type == anomaly_type

    def test_detection_methods(self):
        """测试检测方法"""
        methods = [
            DetectionMethod.THREE_SIGMA,
            DetectionMethod.IQR,
            DetectionMethod.Z_SCORE,
            DetectionMethod.MODIFIED_Z_SCORE,
            DetectionMethod.ISOLATION_FOREST,
            DetectionMethod.DBSCAN,
            DetectionMethod.FIXED_THRESHOLD,
            DetectionMethod.DYNAMIC_THRESHOLD
        ]

        for method in methods:
            result = AnomalyResult(
                timestamp=datetime.now(timezone.utc),
                value=100.0,
                expected_range=(50.0, 80.0),
                severity=0.8,
                anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
                detection_method=method
            )
            assert result.detection_method == method


class TestStatisticalDetector:
    """统计学检测器测试"""

    @pytest.fixture
    def detector(self):
        """创建检测器实例"""
        return StatisticalDetector()

    def test_init(self, detector):
        """测试初始化"""
        assert detector.sigma_threshold == 3.0
        assert detector.iqr_multiplier == 1.5
        assert detector.z_score_threshold == 3.0
        assert detector.min_samples == 10

    def test_detect_three_sigma_normal_data(self, detector):
        """测试3σ检测正常数据"""
        # 创建正态分布数据
        np.random.seed(42)
        normal_data = np.random.normal(100, 10, 1000)

        results = detector.detect_three_sigma(normal_data)

        # 正态数据应该很少异常
        assert len(results) < len(normal_data) * 0.05  # 少于5%的异常

    def test_detect_three_sigma_with_outliers(self, detector):
        """测试3σ检测包含异常值的数据"""
        # 创建包含异常值的数据
        np.random.seed(42)
        normal_data = list(np.random.normal(100, 10, 100))
        normal_data.extend([200, 250, -50, 300])  # 添加明显的异常值

        results = detector.detect_three_sigma(normal_data)

        # 应该检测到异常值
        assert len(results) >= 3  # 至少检测到3个异常

        # 验证异常结果的属性
        for result in results:
            assert result.anomaly_type == AnomalyType.STATISTICAL_OUTLIER
            assert result.detection_method == DetectionMethod.THREE_SIGMA
            assert result.is_anomaly()

    def test_detect_three_sigma_insufficient_data(self, detector):
        """测试3σ检测数据不足的情况"""
        # 数据不足
        small_data = [1, 2, 3, 4, 5]

        results = detector.detect_three_sigma(small_data)

        # 应该返回空列表或很少结果
        assert len(results) == 0

    def test_detect_three_sigma_constant_data(self, detector):
        """测试3σ检测常数数据"""
        constant_data = [100, 100, 100, 100, 100]

        results = detector.detect_three_sigma(constant_data)

        # 常数数据应该没有异常
        assert len(results) == 0

    def test_detect_iqr_normal_data(self, detector):
        """测试IQR检测正常数据"""
        # 创建正态分布数据
        np.random.seed(42)
        normal_data = np.random.normal(100, 10, 1000)

        results = detector.detect_iqr(normal_data)

        # 正态数据应该很少异常
        assert len(results) < len(normal_data) * 0.05  # 少于5%的异常

    def test_detect_iqr_with_outliers(self, detector):
        """测试IQR检测包含异常值的数据"""
        # 创建包含异常值的数据
        normal_data = list(np.random.normal(100, 10, 100))
        normal_data.extend([200, 250, -50, 300])  # 添加明显的异常值

        results = detector.detect_iqr(normal_data)

        # 应该检测到异常值
        assert len(results) >= 3  # 至少检测到3个异常

        # 验证异常结果的属性
        for result in results:
            assert result.anomaly_type == AnomalyType.STATISTICAL_OUTLIER
            assert result.detection_method == DetectionMethod.IQR
            assert result.is_anomaly()

    def test_detect_z_score_normal_data(self, detector):
        """测试Z-score检测正常数据"""
        # 创建正态分布数据
        np.random.seed(42)
        normal_data = np.random.normal(100, 10, 1000)

        results = detector.detect_z_score(normal_data)

        # 正态数据应该很少异常
        assert len(results) < len(normal_data) * 0.05  # 少于5%的异常

    def test_detect_z_score_with_outliers(self, detector):
        """测试Z-score检测包含异常值的数据"""
        # 创建包含异常值的数据
        normal_data = list(np.random.normal(100, 10, 100))
        normal_data.extend([200, 250, -50, 300])  # 添加明显的异常值

        results = detector.detect_z_score(normal_data)

        # 应该检测到异常值
        assert len(results) >= 3  # 至少检测到3个异常

        # 验证异常结果的属性
        for result in results:
            assert result.anomaly_type == AnomalyType.STATISTICAL_OUTLIER
            assert result.detection_method == DetectionMethod.Z_SCORE
            assert result.is_anomaly()

    def test_detect_modified_z_score_normal_data(self, detector):
        """测试修正Z-score检测正常数据"""
        # 创建正态分布数据
        np.random.seed(42)
        normal_data = np.random.normal(100, 10, 1000)

        results = detector.detect_modified_z_score(normal_data)

        # 正态数据应该很少异常
        assert len(results) < len(normal_data) * 0.05  # 少于5%的异常

    def test_detect_modified_z_score_with_outliers(self, detector):
        """测试修正Z-score检测包含异常值的数据"""
        # 创建包含异常值的数据
        normal_data = list(np.random.normal(100, 10, 100))
        normal_data.extend([200, 250, -50, 300])  # 添加明显的异常值

        results = detector.detect_modified_z_score(normal_data)

        # 应该检测到异常值
        assert len(results) >= 3  # 至少检测到3个异常

        # 验证异常结果的属性
        for result in results:
            assert result.anomaly_type == AnomalyType.STATISTICAL_OUTLIER
            assert result.detection_method == DetectionMethod.MODIFIED_Z_SCORE
            assert result.is_anomaly()

    def test_calculate_statistics(self, detector):
        """测试计算统计信息"""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        stats = detector.calculate_statistics(data)

        assert "mean" in stats
        assert "std" in stats
        assert "median" in stats
        assert "q1" in stats
        assert "q3" in stats
        assert "iqr" in stats
        assert "min" in stats
        assert "max" in stats
        assert "count" in stats

        assert stats["mean"] == 5.5
        assert stats["median"] == 5.5
        assert stats["min"] == 1
        assert stats["max"] == 10
        assert stats["count"] == 10

    def test_calculate_statistics_empty_data(self, detector):
        """测试计算空数据的统计信息"""
        stats = detector.calculate_statistics([])

        assert stats["mean"] == 0
        assert stats["std"] == 0
        assert stats["median"] == 0
        assert stats["min"] == 0
        assert stats["max"] == 0
        assert stats["count"] == 0

    def test_calculate_statistics_single_value(self, detector):
        """测试计算单值数据的统计信息"""
        stats = detector.calculate_statistics([42])

        assert stats["mean"] == 42
        assert stats["std"] == 0
        assert stats["median"] == 42
        assert stats["min"] == 42
        assert stats["max"] == 42
        assert stats["count"] == 1


class TestTimeSeriesDetector:
    """时间序列检测器测试"""

    @pytest.fixture
    def detector(self):
        """创建检测器实例"""
        return TimeSeriesDetector()

    def test_init(self, detector):
        """测试初始化"""
        assert detector.window_size == 100
        assert detector.step_size == 10
        assert detector.trend_threshold == 0.1
        assert detector.seasonality_threshold == 0.2

    def test_detect_trend_anomaly_increasing(self, detector):
        """测试检测上升趋势异常"""
        # 创建上升趋势数据
        base_data = list(range(100))
        trend_data = base_data + [110, 120, 130, 140, 150]  # 突然加速上升

        results = detector.detect_trend_anomaly(trend_data)

        # 应该检测到趋势异常
        assert len(results) > 0

        # 验证异常结果的属性
        for result in results:
            assert result.anomaly_type == AnomalyType.PATTERN_DEVIATION
            assert result.detection_method == DetectionMethod.TREND_ANALYSIS

    def test_detect_trend_anomaly_decreasing(self, detector):
        """测试检测下降趋势异常"""
        # 创建下降趋势数据
        base_data = list(range(100, 0, -1))
        trend_data = base_data + [-10, -20, -30, -40, -50]  # 突然加速下降

        results = detector.detect_trend_anomaly(trend_data)

        # 应该检测到趋势异常
        assert len(results) > 0

        # 验证异常结果的属性
        for result in results:
            assert result.anomaly_type == AnomalyType.PATTERN_DEVIATION
            assert result.detection_method == DetectionMethod.TREND_ANALYSIS

    def test_detect_trend_anomaly_normal_data(self, detector):
        """测试检测正常数据的趋势"""
        # 创建正常波动数据
        np.random.seed(42)
        normal_data = list(np.random.normal(100, 5, 150))

        results = detector.detect_trend_anomaly(normal_data)

        # 正常数据应该很少趋势异常
        assert len(results) < len(normal_data) * 0.05  # 少于5%的异常

    def test_detect_seasonal_anomaly(self, detector):
        """测试检测季节性异常"""
        # 创建季节性数据
        seasonal_pattern = [10, 20, 30, 20, 10] * 20  # 重复的季节性模式
        seasonal_data = seasonal_pattern + [100, 200, 300]  # 突然的季节性异常

        results = detector.detect_seasonal_anomaly(seasonal_data)

        # 应该检测到季节性异常
        assert len(results) > 0

        # 验证异常结果的属性
        for result in results:
            assert result.anomaly_type == AnomalyType.SEASONAL_ANOMALY
            assert result.detection_method == DetectionMethod.SEASONAL_DECOMPOSITION

    def test_detect_seasonal_anomaly_normal_seasonal(self, detector):
        """测试检测正常季节性数据"""
        # 创建正常的季节性数据
        seasonal_data = [10, 20, 30, 20, 10] * 30

        results = detector.detect_seasonal_anomaly(seasonal_data)

        # 正常季节性数据应该很少异常
        assert len(results) < len(seasonal_data) * 0.05  # 少于5%的异常

    def test_detect_change_point(self, detector):
        """测试检测变化点"""
        # 创建包含变化点的数据
        before_change = [50, 51, 49, 50, 52] * 20
        after_change = [100, 101, 99, 100, 102] * 20
        change_point_data = before_change + after_change

        results = detector.detect_change_point(change_point_data)

        # 应该检测到变化点
        assert len(results) > 0

        # 验证异常结果的属性
        for result in results:
            assert result.anomaly_type == AnomalyType.PATTERN_DEVIATION
            assert result.detection_method == DetectionMethod.CHANGE_POINT_DETECTION

    def test_detect_change_point_no_change(self, detector):
        """测试检测无变化点的数据"""
        # 创建稳定数据
        stable_data = [50, 51, 49, 50, 52] * 40

        results = detector.detect_change_point(stable_data)

        # 稳定数据应该很少变化点
        assert len(results) < len(stable_data) * 0.05  # 少于5%的异常

    def test_detect_pattern_anomaly(self, detector):
        """测试检测模式异常"""
        # 创建规律模式数据
        pattern_data = [1, 2, 3, 1, 2, 3] * 25  # 重复模式
        anomaly_data = pattern_data + [100, 200, 300]  # 模式异常

        results = detector.detect_pattern_anomaly(anomaly_data)

        # 应该检测到模式异常
        assert len(results) > 0

        # 验证异常结果的属性
        for result in results:
            assert result.anomaly_type == AnomalyType.PATTERN_DEVIATION
            assert result.detection_method == DetectionMethod.PATTERN_ANALYSIS

    def test_calculate_moving_average(self, detector):
        """测试计算移动平均"""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        moving_avg = detector.calculate_moving_average(data, window_size=3)

        assert len(moving_avg) == len(data) - 2
        assert moving_avg[0] == 2.0  # (1+2+3)/3
        assert moving_avg[1] == 3.0  # (2+3+4)/3
        assert moving_avg[-1] == 9.0  # (8+9+10)/3

    def test_calculate_moving_average_large_window(self, detector):
        """测试计算大窗口的移动平均"""
        data = [1, 2, 3, 4, 5]

        moving_avg = detector.calculate_moving_average(data, window_size=10)

        # 窗口大于数据长度时，应该返回空列表
        assert len(moving_avg) == 0

    def test_detect_volatility_anomaly(self, detector):
        """测试检测波动性异常"""
        # 创建低波动数据
        low_volatility = [100, 101, 99, 100, 101] * 20
        # 创建高波动异常
        high_volatility = [50, 150, 30, 170, 20]

        volatility_data = low_volatility + high_volatility

        results = detector.detect_volatility_anomaly(volatility_data)

        # 应该检测到波动性异常
        assert len(results) > 0

        # 验证异常结果的属性
        for result in results:
            assert result.anomaly_type == AnomalyType.PATTERN_DEVIATION
            assert result.detection_method == DetectionMethod.VOLATILITY_ANALYSIS


class TestAnomalyDetector:
    """异常检测器主类测试"""

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        db_manager = Mock()
        db_manager.execute_query = Mock()
        db_manager.execute_update = Mock()
        db_manager.connection = Mock()
        return db_manager

    @pytest.fixture
    def detector(self, mock_db_manager):
        """创建检测器实例"""
        with patch('src.monitoring.anomaly_detector.DatabaseManager', return_value=mock_db_manager):
            return AnomalyDetector(mock_db_manager)

    def test_init(self, detector):
        """测试初始化"""
        assert detector.db_manager is not None
        assert detector.statistical_detector is not None
        assert detector.time_series_detector is not None
        assert isinstance(detector.config, dict)

    def test_detect_anomalies_statistical(self, detector):
        """测试统计学异常检测"""
        data = [1, 2, 3, 4, 5, 100, 7, 8, 9, 10]  # 包含异常值

        results = detector.detect_anomalies(
            data=data,
            methods=["statistical"],
            metric_name="test_metric"
        )

        assert isinstance(results, list)
        assert len(results) > 0

        # 验证结果属性
        for result in results:
            assert isinstance(result, AnomalyResult)
            assert result.metric_name == "test_metric"

    def test_detect_anomalies_time_series(self, detector):
        """测试时间序列异常检测"""
        # 创建包含趋势异常的数据
        base_data = list(range(100))
        trend_data = base_data + [110, 120, 130, 140, 150]

        results = detector.detect_anomalies(
            data=trend_data,
            methods=["time_series"],
            metric_name="trend_metric"
        )

        assert isinstance(results, list)
        assert len(results) > 0

    def test_detect_anomalies_all_methods(self, detector):
        """测试使用所有检测方法"""
        data = [1, 2, 3, 4, 5, 100, 7, 8, 9, 10]

        results = detector.detect_anomalies(
            data=data,
            methods=["all"],
            metric_name="test_metric"
        )

        assert isinstance(results, list)
        # 应该有来自不同方法的检测结果

    def test_detect_anomalies_with_config(self, detector):
        """测试带配置的异常检测"""
        data = [1, 2, 3, 4, 5, 100, 7, 8, 9, 10]

        config = {
            "statistical": {
                "sigma_threshold": 2.0,
                "methods": ["three_sigma", "iqr"]
            },
            "time_series": {
                "window_size": 50,
                "trend_threshold": 0.2
            }
        }

        results = detector.detect_anomalies(
            data=data,
            methods=["statistical", "time_series"],
            metric_name="test_metric",
            config=config
        )

        assert isinstance(results, list)

    def test_detect_anomalies_empty_data(self, detector):
        """测试空数据异常检测"""
        results = detector.detect_anomalies(
            data=[],
            methods=["statistical"],
            metric_name="test_metric"
        )

        assert results == []

    def test_detect_anomalies_insufficient_data(self, detector):
        """测试数据不足的异常检测"""
        results = detector.detect_anomalies(
            data=[1, 2, 3],
            methods=["statistical"],
            metric_name="test_metric"
        )

        assert results == []

    def test_detect_anomalies_dataframe_input(self, detector):
        """测试DataFrame输入的异常检测"""
        df = pd.DataFrame({
            "value": [1, 2, 3, 4, 5, 100, 7, 8, 9, 10],
            "timestamp": pd.date_range("2024-01-01", periods=10)
        })

        results = detector.detect_anomalies(
            data=df,
            methods=["statistical"],
            metric_name="test_metric",
            value_column="value"
        )

        assert isinstance(results, list)

    def test_get_anomaly_summary(self, detector):
        """测试获取异常摘要"""
        # 创建一些异常结果
        anomalies = [
            AnomalyResult(
                timestamp=datetime.now(timezone.utc),
                value=100.0,
                expected_range=(50.0, 80.0),
                severity=0.8,
                anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
                detection_method=DetectionMethod.THREE_SIGMA
            ),
            AnomalyResult(
                timestamp=datetime.now(timezone.utc),
                value=200.0,
                expected_range=(100.0, 150.0),
                severity=0.9,
                anomaly_type=AnomalyType.THRESHOLD_VIOLATION,
                detection_method=DetectionMethod.FIXED_THRESHOLD
            )
        ]

        summary = detector.get_anomaly_summary(anomalies)

        assert isinstance(summary, dict)
        assert "total_anomalies" in summary
        assert "anomalies_by_type" in summary
        assert "anomalies_by_method" in summary
        assert "severity_distribution" in summary
        assert "time_range" in summary

        assert summary["total_anomalies"] == 2
        assert summary["anomalies_by_type"]["STATISTICAL_OUTLIER"] == 1
        assert summary["anomalies_by_type"]["THRESHOLD_VIOLATION"] == 1

    def test_get_anomaly_summary_empty(self, detector):
        """测试获取空异常摘要"""
        summary = detector.get_anomaly_summary([])

        assert isinstance(summary, dict)
        assert summary["total_anomalies"] == 0
        assert summary["anomalies_by_type"] == {}
        assert summary["anomalies_by_method"] == {}

    def test_configure_detection_parameters(self, detector):
        """测试配置检测参数"""
        config = {
            "statistical": {
                "sigma_threshold": 2.5,
                "iqr_multiplier": 1.8,
                "z_score_threshold": 2.8
            },
            "time_series": {
                "window_size": 150,
                "step_size": 15,
                "trend_threshold": 0.15
            }
        }

        detector.configure_detection_parameters(config)

        # 验证配置已应用
        assert detector.statistical_detector.sigma_threshold == 2.5
        assert detector.statistical_detector.iqr_multiplier == 1.8
        assert detector.time_series_detector.window_size == 150
        assert detector.time_series_detector.step_size == 15

    def test_detect_anomalies_with_time_series_data(self, detector):
        """测试带时间戳的时间序列异常检测"""
        timestamps = pd.date_range("2024-01-01", periods=100, freq="H")
        values = list(range(100)) + [150, 160, 170]  # 添加异常值

        data = pd.DataFrame({
            "timestamp": timestamps,
            "value": values
        })

        results = detector.detect_anomalies(
            data=data,
            methods=["time_series"],
            metric_name="time_series_metric",
            timestamp_column="timestamp",
            value_column="value"
        )

        assert isinstance(results, list)
        assert len(results) > 0

    def test_batch_detect_anomalies(self, detector):
        """测试批量异常检测"""
        data_sets = {
            "metric1": [1, 2, 3, 4, 5, 100, 7, 8, 9, 10],
            "metric2": [10, 20, 30, 40, 50, 500, 70, 80, 90, 100],
            "metric3": [5, 5, 5, 5, 5, 5, 50, 5, 5, 5]  # 单个异常值
        }

        results = detector.batch_detect_anomalies(
            data_sets=data_sets,
            methods=["statistical"]
        )

        assert isinstance(results, dict)
        assert "metric1" in results
        assert "metric2" in results
        assert "metric3" in results

        for metric_name, anomalies in results.items():
            assert isinstance(anomalies, list)

    def test_detect_anomalies_with_custom_thresholds(self, detector):
        """测试使用自定义阈值的异常检测"""
        data = [1, 2, 3, 4, 5, 100, 7, 8, 9, 10]

        results = detector.detect_anomalies(
            data=data,
            methods=["statistical"],
            metric_name="test_metric",
            thresholds={
                "three_sigma": {"sigma_threshold": 2.0},
                "iqr": {"iqr_multiplier": 2.0}
            }
        )

        assert isinstance(results, list)

    def test_health_check(self, detector):
        """测试健康检查"""
        health_status = detector.health_check()

        assert isinstance(health_status, dict)
        assert "status" in health_status
        assert "detectors" in health_status
        assert "config" in health_status
        assert "last_detection_time" in health_status

    def test_get_detection_statistics(self, detector):
        """测试获取检测统计"""
        stats = detector.get_detection_statistics()

        assert isinstance(stats, dict)
        assert "total_detections" in stats
        assert "anomalies_detected" in stats
        assert "methods_used" in stats
        assert "average_severity" in stats


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])