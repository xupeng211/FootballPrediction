"""
异常检测器测试 - 简化版本

测试异常检测的核心功能，专注于实际存在的方法。
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from src.data.quality.anomaly_detector import (
    AnomalyDetectionResult,
    StatisticalAnomalyDetector,
    MachineLearningAnomalyDetector,
    AdvancedAnomalyDetector
)


class TestAnomalyDetectionResult:
    """异常检测结果类测试"""

    def test_init(self):
        """测试初始化"""
        result = AnomalyDetectionResult(
            table_name="test_table",
            detection_method="3sigma",
            anomaly_type="statistical_outlier",
            severity="medium"
        )

        assert result.table_name == "test_table"
        assert result.detection_method == "3sigma"
        assert result.anomaly_type == "statistical_outlier"
        assert result.severity == "medium"
        assert isinstance(result.timestamp, datetime)
        assert result.anomalous_records == []
        assert result.statistics == {}
        assert result.metadata == {}

    def test_add_anomalous_record(self):
        """测试添加异常记录"""
        result = AnomalyDetectionResult("test_table", "3sigma", "statistical_outlier")

        record = {"index": 0, "value": 100.0, "z_score": 3.5}
        result.add_anomalous_record(record)

        assert len(result.anomalous_records) == 1
        assert result.anomalous_records[0] == record

    def test_set_statistics(self):
        """测试设置统计信息"""
        result = AnomalyDetectionResult("test_table", "3sigma", "statistical_outlier")

        stats = {"total_records": 100, "outliers_count": 5}
        result.set_statistics(stats)

        assert result.statistics == stats

    def test_set_metadata(self):
        """测试设置元数据"""
        result = AnomalyDetectionResult("test_table", "3sigma", "statistical_outlier")

        metadata = {"detection_time": "2024-01-01T00:00:00Z"}
        result.set_metadata(metadata)

        assert result.metadata == metadata

    def test_to_dict(self):
        """测试转换为字典"""
        result = AnomalyDetectionResult("test_table", "3sigma", "statistical_outlier")
        record = {"index": 0, "value": 100.0}
        result.add_anomalous_record(record)

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["table_name"] == "test_table"
        assert result_dict["detection_method"] == "3sigma"
        assert result_dict["anomaly_type"] == "statistical_outlier"
        assert result_dict["anomalous_records_count"] == 1
        assert len(result_dict["anomalous_records"]) == 1


class TestStatisticalAnomalyDetector:
    """统计学异常检测器测试"""

    @pytest.fixture
    def detector(self):
        """创建检测器实例"""
        return StatisticalAnomalyDetector(sigma_threshold=3.0)

    def test_init(self, detector):
        """测试初始化"""
        assert detector.sigma_threshold == 3.0
        assert detector.logger is not None

    def test_detect_outliers_3sigma_normal_data(self, detector):
        """测试正常数据的3σ检测"""
        # 创建正态分布数据
        np.random.seed(42)
        normal_data = pd.Series(np.random.normal(100, 10, 100))

        result = detector.detect_outliers_3sigma(normal_data, "test_table", "test_column")

        assert result.table_name == "test_table"
        assert result.detection_method == "3sigma"
        assert result.anomaly_type == "statistical_outlier"
        assert "total_records" in result.statistics
        assert "outliers_count" in result.statistics
        assert "mean" in result.statistics
        assert "std" in result.statistics

    def test_detect_outliers_3sigma_with_outliers(self, detector):
        """测试包含异常值的3σ检测"""
        # 创建包含明显异常值的数据 - 使用标准正态分布数据加上一个极端值
        np.random.seed(42)
        normal_data = list(np.random.normal(0, 1, 100))  # 均值0，标准差1的正态分布
        normal_data.append(10)  # 添加一个10个标准差外的异常值
        data = pd.Series(normal_data)

        result = detector.detect_outliers_3sigma(data, "test_table", "test_column")

        assert len(result.anomalous_records) > 0

    def test_detect_outliers_3sigma_empty_data(self, detector):
        """测试空数据的3σ检测"""
        empty_data = pd.Series([])

        with pytest.raises(ValueError, match="输入数据为空"):
            detector.detect_outliers_3sigma(empty_data, "test_table", "test_column")

    def test_detect_outliers_3sigma_all_same_values(self, detector):
        """测试所有值相同的情况"""
        same_values_data = pd.Series([5.0, 5.0, 5.0, 5.0, 5.0])

        result = detector.detect_outliers_3sigma(same_values_data, "test_table", "test_column")

        assert result.statistics["std"] == 0.0
        assert len(result.anomalous_records) == 0

    def test_detect_outliers_iqr(self, detector):
        """测试IQR异常检测"""
        # 创建包含异常值的数据
        data = pd.Series([1, 2, 3, 4, 5, 100, 200])

        result = detector.detect_outliers_iqr(data, "test_table", "test_column")

        assert result.table_name == "test_table"
        assert result.detection_method == "iqr"
        assert result.anomaly_type == "statistical_outlier"
        assert "Q1" in result.statistics
        assert "Q3" in result.statistics
        assert "IQR" in result.statistics

    def test_detect_distribution_shift(self, detector):
        """测试分布偏移检测"""
        # 创建两个不同分布的数据集
        baseline_data = pd.Series(np.random.normal(100, 10, 50))
        current_data = pd.Series(np.random.normal(150, 15, 50))  # 明显不同的分布

        result = detector.detect_distribution_shift(
            baseline_data, current_data, "test_table", "test_column"
        )

        assert result.table_name == "test_table"
        assert result.detection_method == "ks_test"
        assert result.anomaly_type == "distribution_shift"
        assert "ks_statistic" in result.statistics
        assert "p_value" in result.statistics
        assert "baseline_stats" in result.statistics
        assert "current_stats" in result.statistics


class TestMachineLearningAnomalyDetector:
    """机器学习异常检测器测试"""

    @pytest.fixture
    def detector(self):
        """创建检测器实例"""
        return MachineLearningAnomalyDetector()

    def test_init(self, detector):
        """测试初始化"""
        assert detector.logger is not None
        assert detector.scaler is not None
        assert detector.isolation_forest is None
        assert detector.dbscan is None

    def test_detect_anomalies_isolation_forest(self, detector):
        """测试Isolation Forest异常检测"""
        # 创建包含异常值的数据
        np.random.seed(42)
        normal_data = np.random.multivariate_normal([0, 0], [[1, 0.5], [0.5, 1]], 95)
        outlier_data = np.random.multivariate_normal([5, 5], [[1, 0], [0, 1]], 5)
        data = np.vstack([normal_data, outlier_data])

        df = pd.DataFrame(data, columns=['feature1', 'feature2'])

        result = detector.detect_anomalies_isolation_forest(df, "test_table")

        assert result.table_name == "test_table"
        assert result.detection_method == "isolation_forest"
        assert result.anomaly_type == "ml_anomaly"
        assert "total_records" in result.statistics
        assert "anomalies_count" in result.statistics
        assert "anomaly_rate" in result.statistics

    def test_detect_anomalies_isolation_forest_insufficient_data(self, detector):
        """测试数据不足的情况"""
        # 创建少量数据
        data = pd.DataFrame({'feature1': [1, 2], 'feature2': [3, 4]})

        # 方法应该能处理小数据集
        result = detector.detect_anomalies_isolation_forest(data, "test_table")

        assert result.table_name == "test_table"
        assert result.detection_method == "isolation_forest"

    def test_detect_data_drift(self, detector):
        """测试数据漂移检测"""
        # 创建基准和当前数据
        np.random.seed(42)
        baseline_data = pd.DataFrame({
            'feature1': np.random.normal(100, 10, 50),
            'feature2': np.random.normal(50, 5, 50)
        })

        current_data = pd.DataFrame({
            'feature1': np.random.normal(120, 10, 50),  # 均值偏移
            'feature2': np.random.normal(50, 5, 50)
        })

        results = detector.detect_data_drift(baseline_data, current_data, "test_table")

        assert isinstance(results, list)
        # 由于均值偏移，应该检测到漂移
        assert len(results) > 0

        for result in results:
            assert result.table_name == "test_table"
            assert result.detection_method == "data_drift"
            assert result.anomaly_type == "feature_drift"

    def test_detect_anomalies_clustering(self, detector):
        """测试DBSCAN聚类异常检测"""
        # 创建包含聚类和噪声点的数据
        np.random.seed(42)
        cluster1 = np.random.multivariate_normal([0, 0], [[1, 0], [0, 1]], 40)
        cluster2 = np.random.multivariate_normal([5, 5], [[1, 0], [0, 1]], 40)
        outliers = np.random.uniform(-5, 10, (10, 2))

        data = np.vstack([cluster1, cluster2, outliers])
        df = pd.DataFrame(data, columns=['feature1', 'feature2'])

        result = detector.detect_anomalies_clustering(df, "test_table")

        assert result.table_name == "test_table"
        assert result.detection_method == "dbscan_clustering"
        assert result.anomaly_type == "clustering_outlier"
        assert "total_records" in result.statistics
        assert "anomalies_count" in result.statistics
        assert "num_clusters" in result.statistics


class TestAdvancedAnomalyDetector:
    """高级异常检测器测试"""

    @pytest.fixture
    def detector(self):
        """创建检测器实例"""
        with patch("src.data.quality.anomaly_detector.DatabaseManager"):
            return AdvancedAnomalyDetector()

    def test_init(self, detector):
        """测试初始化"""
        assert detector.db_manager is not None
        assert detector.logger is not None
        assert detector.statistical_detector is not None
        assert detector.ml_detector is not None
        assert isinstance(detector.detection_config, dict)

        # 验证配置结构
        expected_tables = ["matches", "odds", "predictions"]
        for table in expected_tables:
            assert table in detector.detection_config
            assert "enabled_methods" in detector.detection_config[table]
            assert "key_columns" in detector.detection_config[table]

    def test_detection_config_structure(self, detector):
        """测试检测配置结构"""
        config = detector.detection_config

        # 验证matches表配置
        assert "3sigma" in config["matches"]["enabled_methods"]
        assert "home_score" in config["matches"]["key_columns"]
        assert "away_score" in config["matches"]["key_columns"]

        # 验证odds表配置
        assert "3sigma" in config["odds"]["enabled_methods"]
        assert "home_odds" in config["odds"]["key_columns"]
        assert "away_odds" in config["odds"]["key_columns"]

        # 验证predictions表配置
        assert "data_drift" in config["predictions"]["enabled_methods"]
        assert "home_win_probability" in config["predictions"]["key_columns"]

    @pytest.mark.asyncio
    async def test_run_comprehensive_detection_with_mock_data(self, detector):
        """测试使用模拟数据的综合异常检测"""
        # 模拟数据库返回数据
        mock_data = pd.DataFrame({
            'home_score': [1, 2, 3, 1, 0],
            'away_score': [0, 1, 2, 1, 3],
            'match_time': pd.date_range('2024-01-01', periods=5)
        })

        with patch.object(detector, '_get_table_data', return_value=mock_data), \
             patch.object(detector, '_get_total_records', return_value=100):

            results = await detector.run_comprehensive_detection("matches", 24)

            assert isinstance(results, list)
            # 由于我们使用了模拟数据，可能会返回一些结果

    @pytest.mark.asyncio
    async def test_run_comprehensive_detection_invalid_table(self, detector):
        """测试无效表名的综合异常检测"""
        with patch.object(detector, '_get_table_data', return_value=pd.DataFrame()):
            results = await detector.run_comprehensive_detection("invalid_table", 24)

            # 无效表名应该返回空结果
            assert results == []

    @pytest.mark.asyncio
    async def test_get_anomaly_summary(self, detector):
        """测试获取异常检测摘要"""
        # 模拟run_comprehensive_detection返回空结果
        with patch.object(detector, 'run_comprehensive_detection', return_value=[]):
            summary = await detector.get_anomaly_summary(24)

            assert isinstance(summary, dict)
            assert "detection_period" in summary
            assert "tables_analyzed" in summary
            assert "total_anomalies" in summary
            assert "anomalies_by_table" in summary
            assert "anomalies_by_severity" in summary
            assert "anomalies_by_method" in summary
            assert "anomalies_by_type" in summary

            # 验证摘要结构
            assert summary["total_anomalies"] == 0
            assert isinstance(summary["tables_analyzed"], list)
            assert isinstance(summary["anomalies_by_severity"], dict)
            assert "low" in summary["anomalies_by_severity"]
            assert "medium" in summary["anomalies_by_severity"]
            assert "high" in summary["anomalies_by_severity"]
            assert "critical" in summary["anomalies_by_severity"]


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])