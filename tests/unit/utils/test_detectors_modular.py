""""""""
测试异常检测器模块化拆分
Test modular split of anomaly detectors
""""""""

import pandas as pd
import pytest


@pytest.mark.unit
class TestBaseModule:
    """测试基础模块"""

    def test_anomaly_detection_result_import(self):
        """测试异常检测结果类导入"""
from src.data.quality.detectors.base import AnomalyDetectionResult

        assert AnomalyDetectionResult is not None

    def test_anomaly_detection_result_creation(self):
        """测试异常检测结果创建"""
from src.data.quality.detectors.base import AnomalyDetectionResult

        _result = AnomalyDetectionResult(
            table_name="test_table",
            detection_method="3sigma",
            anomaly_type="statistical_outlier",
            severity="high",
        )

        assert _result.table_name == "test_table"
        assert _result.detection_method == "3sigma"
        assert _result.anomaly_type == "statistical_outlier"
        assert _result.severity == "high"
        assert len(result.anomalous_records) == 0
        assert isinstance(result.statistics, dict)
        assert isinstance(result.metadata, dict)

    def test_anomaly_detection_result_methods(self):
        """测试异常检测结果方法"""
from src.data.quality.detectors.base import AnomalyDetectionResult

        _result = AnomalyDetectionResult(
            table_name="test_table",
            detection_method="3sigma",
            anomaly_type="statistical_outlier",
        )

        # 测试添加异常记录
        result.add_anomalous_record({"index": 1, "value": 100.0, "z_score": 3.5})
        assert len(result.anomalous_records) == 1
        assert _result.anomalous_records[0]["index"] == 1

        # 测试设置统计信息
        _stats = {"mean": 50.0, "std": 10.0, "outliers_count": 1}
        result.set_statistics(stats)
        assert _result.statistics == stats

        # 测试转换为字典
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["table_name"] == "test_table"
        assert result_dict["anomalous_records_count"] == 1


class TestStatisticalDetector:
    """测试统计学异常检测器"""

    def test_statistical_detector_import(self):
        """测试统计学检测器导入"""
from src.data.quality.detectors.statistical import StatisticalAnomalyDetector

        assert StatisticalAnomalyDetector is not None

    def test_statistical_detector_init(self):
        """测试统计学检测器初始化"""
from src.data.quality.detectors.statistical import StatisticalAnomalyDetector

        detector = StatisticalAnomalyDetector(sigma_threshold=2.5)
        assert detector.sigma_threshold == 2.5
        assert hasattr(detector, "logger")

    def test_detect_outliers_3sigma(self):
        """测试3σ异常检测"""
from src.data.quality.detectors.statistical import StatisticalAnomalyDetector

        detector = StatisticalAnomalyDetector()

        # 创建测试数据（包含异常值）
        normal_data = [50, 51, 49, 48, 52, 51, 50, 49, 51, 50] * 10
        outliers = [150, -50]  # 明显的异常值
        test_data = pd.Series(normal_data + outliers)

        _result = detector.detect_outliers_3sigma(test_data, "test_table", "test_column")

        assert _result.table_name == "test_table"
        assert _result.detection_method == "3sigma"
        assert _result.anomaly_type == "statistical_outlier"
        assert len(result.anomalous_records) >= 2  # 至少检测到2个异常值
        assert "statistics" in result.to_dict()

    def test_detect_outliers_iqr(self):
        """测试IQR异常检测"""
from src.data.quality.detectors.statistical import StatisticalAnomalyDetector

        detector = StatisticalAnomalyDetector()

        # 创建测试数据
        test_data = pd.Series([10, 12, 11, 13, 9, 14, 100, 8, 15, 11])

        _result = detector.detect_outliers_iqr(test_data, "test_table", "test_column")

        assert _result.detection_method == "iqr"
        assert _result.anomaly_type == "statistical_outlier"
        assert len(result.anomalous_records) >= 1  # 至少检测到1个异常值（100）

    def test_detect_distribution_shift(self):
        """测试分布偏移检测"""
        import numpy as np

from src.data.quality.detectors.statistical import StatisticalAnomalyDetector

        detector = StatisticalAnomalyDetector()

        # 创建两个不同分布的数据
        baseline_data = pd.Series(np.random.normal(0, 1, 1000))
        current_data = pd.Series(np.random.normal(2, 1, 1000))  # 均值偏移

        _result = detector.detect_distribution_shift(
            baseline_data, current_data, "test_table", "test_column"
        )

        assert _result.detection_method == "ks_test"
        assert _result.anomaly_type == "distribution_shift"
        assert "ks_statistic" in result.statistics
        assert "p_value" in result.statistics


class TestMachineLearningDetector:
    """测试机器学习异常检测器"""

    def test_ml_detector_import(self):
        """测试机器学习检测器导入"""
from src.data.quality.detectors.machine_learning import (
            MachineLearningAnomalyDetector,
        )

        assert MachineLearningAnomalyDetector is not None

    def test_ml_detector_init(self):
        """测试机器学习检测器初始化"""
from src.data.quality.detectors.machine_learning import (
            MachineLearningAnomalyDetector,
        )

        detector = MachineLearningAnomalyDetector()
        assert hasattr(detector, "scaler")
        assert detector.isolation_forest is None
        assert detector.dbscan is None

    def test_detect_anomalies_isolation_forest(self):
        """测试Isolation Forest异常检测"""
        import numpy as np

from src.data.quality.detectors.machine_learning import (
            MachineLearningAnomalyDetector,
        )

        detector = MachineLearningAnomalyDetector()

        # 创建测试数据框
        np.random.seed(42)
        normal_data = np.random.normal(0, 1, (100, 3))
        anomalies = np.array([[5, 5, 5], [-5, -5, -5]])  # 明显的异常
        test_data = pd.DataFrame(
            np.vstack([normal_data, anomalies]),
            columns=["feature1", "feature2", "feature3"],
        )

        _result = detector.detect_anomalies_isolation_forest(test_data, "test_table")

        assert _result.table_name == "test_table"
        assert _result.detection_method == "isolation_forest"
        assert _result.anomaly_type == "ml_anomaly"
        assert len(result.anomalous_records) >= 2  # 至少检测到2个异常

    def test_detect_anomalies_clustering(self):
        """测试DBSCAN聚类异常检测"""
        import numpy as np

from src.data.quality.detectors.machine_learning import (
            MachineLearningAnomalyDetector,
        )

        detector = MachineLearningAnomalyDetector()

        # 创建测试数据框
        np.random.seed(42)
        cluster_data = np.random.normal(0, 1, (50, 2))
        noise = np.random.uniform(-5, 5, (10, 2))  # 噪声点
        test_data = pd.DataFrame(np.vstack([cluster_data, noise]), columns=["x", "y"])

        _result = detector.detect_anomalies_clustering(test_data, "test_table", eps=0.5)

        assert _result.detection_method == "dbscan_clustering"
        assert _result.anomaly_type == "clustering_outlier"
        assert "num_clusters" in result.statistics


class TestAdvancedDetector:
    """测试高级异常检测器"""

    def test_advanced_detector_import(self):
        """测试高级检测器导入"""
from src.data.quality.detectors.advanced import AdvancedAnomalyDetector

        assert AdvancedAnomalyDetector is not None

    def test_advanced_detector_init(self):
        """测试高级检测器初始化"""
from src.data.quality.detectors.advanced import AdvancedAnomalyDetector

        detector = AdvancedAnomalyDetector()
        assert hasattr(detector, "statistical_detector")
        assert hasattr(detector, "ml_detector")
        assert isinstance(detector.detection_config, dict)

    def test_detection_config_structure(self):
        """测试检测配置结构"""
from src.data.quality.detectors.advanced import AdvancedAnomalyDetector

        detector = AdvancedAnomalyDetector()

        # 验证配置包含必要的表
        assert "matches" in detector.detection_config
        assert "odds" in detector.detection_config
        assert "predictions" in detector.detection_config

        # 验证每个配置包含必要的键
        for table_name, config in detector.detection_config.items():
            assert "enabled_methods" in config
            assert "key_columns" in config
            assert "drift_baseline_days" in config


class TestMetricsModule:
    """测试监控指标模块"""

    def test_metrics_import(self):
        """测试监控指标导入"""
from src.data.quality.detectors.metrics import (
            anomalies_detected_total,
            anomaly_detection_coverage,
            anomaly_detection_duration_seconds,
            data_drift_score,
        )

        assert anomalies_detected_total is not None
        assert data_drift_score is not None
        assert anomaly_detection_duration_seconds is not None
        assert anomaly_detection_coverage is not None

    def test_metrics_are_callable(self):
        """测试监控指标可调用"""
from src.data.quality.detectors.metrics import (
            anomalies_detected_total,
            data_drift_score,
        )

        # 测试指标有labels方法
        assert hasattr(anomalies_detected_total, "labels")
        assert hasattr(data_drift_score, "labels")
        assert callable(anomalies_detected_total.labels)
        assert callable(data_drift_score.labels)


class TestModularStructure:
    """测试模块化结构"""

    def test_import_from_main_module(self):
        """测试从主模块导入"""
from src.data.quality.detectors import (
            AdvancedAnomalyDetector,
            AnomalyDetectionResult,
            MachineLearningAnomalyDetector,
            StatisticalAnomalyDetector,
            anomalies_detected_total,
        )

        assert AnomalyDetectionResult is not None
        assert StatisticalAnomalyDetector is not None
        assert MachineLearningAnomalyDetector is not None
        assert AdvancedAnomalyDetector is not None
        assert anomalies_detected_total is not None

    def test_backward_compatibility_imports(self):
        """测试向后兼容性导入"""
        # 从原始文件导入应该仍然有效
from src.data.quality.anomaly_detector_original import (
            AdvancedAnomalyDetector as old_advanced,
        )
from src.data.quality.anomaly_detector_original import (
            AnomalyDetectionResult as old_result,
        )
from src.data.quality.anomaly_detector_original import (
            StatisticalAnomalyDetector as old_statistical,
        )

        assert old_result is not None
        assert old_statistical is not None
        assert old_advanced is not None

    def test_all_classes_are_exported(self):
        """测试所有类都被导出"""
from src.data.quality.detectors import __all__

        expected_exports = [
            "AnomalyDetectionResult",
            "StatisticalAnomalyDetector",
            "MachineLearningAnomalyDetector",
            "AdvancedAnomalyDetector",
            "anomalies_detected_total",
            "data_drift_score",
            "anomaly_detection_duration_seconds",
            "anomaly_detection_coverage",
        ]

        for export in expected_exports:
            assert export in __all__


@pytest.mark.asyncio
async def test_integration_example():
    """测试集成示例"""
    from src.data.quality.detectors.advanced import AdvancedAnomalyDetector

    # 验证AdvancedAnomalyDetector可以正常使用
    detector = AdvancedAnomalyDetector()

    # 验证配置存在
    assert detector.detection_config is not None
    assert len(detector.detection_config) > 0

    # 验证子检测器已初始化
    assert detector.statistical_detector is not None
    assert detector.ml_detector is not None
