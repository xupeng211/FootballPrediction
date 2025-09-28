"""
anomaly_detector.py 测试文件
测试高级数据质量异常检测功能，包括统计学方法、机器学习方法和Prometheus监控集成
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# 模拟外部依赖
with patch.dict('sys.modules', {
    'src.database.connection': Mock(),
    'prometheus_client': Mock(),
    'scipy': Mock(),
    'scipy.stats': Mock(),
    'sklearn': Mock(),
    'sklearn.cluster': Mock(),
    'sklearn.ensemble': Mock(),
    'sklearn.preprocessing': Mock(),
    'sqlalchemy': Mock(),
    'sqlalchemy.text': Mock(),
    'src.core': Mock(),
    'src.database': Mock(),
    'src.database.models': Mock(),
    'src.database.connection': Mock(),
    'src.features': Mock(),
    'src.features.feature_store': Mock(),
    'src.monitoring': Mock(),
    'src.monitoring.metrics_collector': Mock(),
    'src.monitoring.metrics_exporter': Mock()
}):
    from src.data.quality.anomaly_detector import (
        AnomalyDetectionResult,
        StatisticalAnomalyDetector,
        MachineLearningAnomalyDetector,
        AdvancedAnomalyDetector
    )


class TestAnomalyDetectionResult:
    """测试异常检测结果类"""

    def test_initialization(self):
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
        record = {"index": 0, "column": "score", "value": 100.0}

        result.add_anomalous_record(record)

        assert len(result.anomalous_records) == 1
        assert result.anomalous_records[0] == record

    def test_set_statistics(self):
        """测试设置统计信息"""
        result = AnomalyDetectionResult("test_table", "3sigma", "statistical_outlier")
        stats = {"mean": 50.0, "std": 10.0}

        result.set_statistics(stats)

        assert result.statistics == stats

    def test_set_metadata(self):
        """测试设置元数据"""
        result = AnomalyDetectionResult("test_table", "3sigma", "statistical_outlier")
        metadata = {"version": "1.0", "config": {"threshold": 3.0}}

        result.set_metadata(metadata)

        assert result.metadata == metadata

    def test_to_dict(self):
        """测试转换为字典"""
        result = AnomalyDetectionResult("test_table", "3sigma", "statistical_outlier", "high")
        result.add_anomalous_record({"index": 0, "value": 100.0})
        result.set_statistics({"mean": 50.0})
        result.set_metadata({"version": "1.0"})

        result_dict = result.to_dict()

        assert result_dict["table_name"] == "test_table"
        assert result_dict["detection_method"] == "3sigma"
        assert result_dict["anomaly_type"] == "statistical_outlier"
        assert result_dict["severity"] == "high"
        assert "timestamp" in result_dict
        assert result_dict["anomalous_records_count"] == 1
        assert len(result_dict["anomalous_records"]) == 1
        assert result_dict["statistics"] == {"mean": 50.0}
        assert result_dict["metadata"] == {"version": "1.0"}


class TestStatisticalAnomalyDetector:
    """测试统计学异常检测器"""

    def setup_method(self):
        """设置测试环境"""
        self.detector = StatisticalAnomalyDetector(sigma_threshold=3.0)

    def test_initialization(self):
        """测试初始化"""
        assert self.detector.sigma_threshold == 3.0
        assert self.detector.logger is not None

    def test_detect_outliers_3sigma_empty_data(self):
        """测试3σ检测空数据"""
        data = pd.Series([])

        with pytest.raises(ValueError) as exc_info:
            self.detector.detect_outliers_3sigma(data, "test_table", "test_column")

        assert "输入数据为空" in str(exc_info.value)

    def test_detect_outliers_3sigma_all_nan(self):
        """测试3σ检测全NaN数据"""
        data = pd.Series([np.nan, np.nan, np.nan])

        with pytest.raises(ValueError) as exc_info:
            self.detector.detect_outliers_3sigma(data, "test_table", "test_column")

        assert "删除NaN后数据为空" in str(exc_info.value)

    def test_detect_outliers_3sigma_zero_std(self):
        """测试3σ检测标准差为0的情况"""
        data = pd.Series([5.0, 5.0, 5.0, 5.0])

        result = self.detector.detect_outliers_3sigma(data, "test_table", "test_column")

        assert result.anomaly_type == "statistical_outlier"
        assert result.severity == "low"
        assert result.statistics["outliers_count"] == 0
        assert result.statistics["std"] == 0.0

    def test_detect_outliers_3sigma_normal_data(self):
        """测试3σ检测正常数据"""
        # Create actual test data instead of using mocked numpy
        data = pd.Series([50 + 10 * (i - 50) / 20 for i in range(100)])  # Normal-like distribution

        result = self.detector.detect_outliers_3sigma(data, "test_table", "test_column")

        assert result.table_name == "test_table"
        assert result.detection_method == "3sigma"
        assert result.statistics["total_records"] == 100
        assert "mean" in result.statistics
        assert "std" in result.statistics

    def test_detect_outliers_3sigma_with_outliers(self):
        """测试3σ检测包含异常值的数据"""
        # 创建包含明显异常值的数据
        normal_data = [50] * 95
        outlier_data = [200] * 5  # 明显的异常值
        data = pd.Series(normal_data + outlier_data)

        result = self.detector.detect_outliers_3sigma(data, "test_table", "test_column")

        assert result.statistics["outliers_count"] > 0
        assert len(result.anomalous_records) > 0

        # 验证异常记录结构
        anomalous_record = result.anomalous_records[0]
        assert "index" in anomalous_record
        assert "column" in anomalous_record
        assert "value" in anomalous_record
        assert "z_score" in anomalous_record
        assert "threshold_exceeded" in anomalous_record

    @patch('data.quality.anomaly_detector.anomalies_detected_total')
    @patch('data.quality.anomaly_detector.anomaly_detection_duration_seconds')
    def test_detect_outliers_3sigma_prometheus_metrics(self, mock_duration, mock_counter):
        """测试3σ检测Prometheus指标记录"""
        mock_counter.inc = Mock()
        mock_duration.observe = Mock()

        data = pd.Series([1, 2, 3, 100, 4, 5])
        result = self.detector.detect_outliers_3sigma(data, "test_table", "test_column")

        # 验证Prometheus指标被调用
        mock_counter.labels.assert_called()
        mock_duration.observe.assert_called()

    def test_detect_distribution_shift_normal_data(self):
        """测试分布偏移检测正常数据"""
        baseline_data = pd.Series([50 + 10 * (i - 50) / 20 for i in range(100)])
        current_data = pd.Series([50 + 10 * (i - 50) / 20 for i in range(100)])

        result = self.detector.detect_distribution_shift(
            baseline_data, current_data, "test_table", "test_column"
        )

        assert result.table_name == "test_table"
        assert result.detection_method == "ks_test"
        assert result.anomaly_type == "distribution_shift"
        assert "baseline_stats" in result.statistics
        assert "current_stats" in result.statistics
        assert "ks_statistic" in result.statistics
        assert "p_value" in result.statistics

    def test_detect_distribution_shift_with_shift(self):
        """测试检测到分布偏移"""
        baseline_data = pd.Series([50 + 10 * (i - 50) / 20 for i in range(100)])
        current_data = pd.Series([80 + 10 * (i - 50) / 20 for i in range(100)])  # 明显的偏移

        with patch('data.quality.anomaly_detector.stats.ks_2samp') as mock_ks:
            mock_ks.return_value = (0.3, 0.001)  # 显著的偏移

            result = self.detector.detect_distribution_shift(
                baseline_data, current_data, "test_table", "test_column"
            )

            assert result.statistics["distribution_shifted"] is True
            assert result.severity == "critical"  # p_value < 0.001
            assert len(result.anomalous_records) > 0

    def test_detect_distribution_shift_severity_levels(self):
        """测试分布偏移严重程度分级"""
        baseline_data = pd.Series([1, 2, 3])
        current_data = pd.Series([4, 5, 6])

        # 测试不同p值对应的严重程度
        test_cases = [
            (0.0001, "critical"),  # p < 0.001
            (0.005, "high"),       # p < 0.01
            (0.03, "medium"),      # p < 0.05
            (0.1, "low"),          # p >= 0.05
        ]

        for p_value, expected_severity in test_cases:
            with patch('data.quality.anomaly_detector.stats.ks_2samp') as mock_ks:
                mock_ks.return_value = (0.2, p_value)

                result = self.detector.detect_distribution_shift(
                    baseline_data, current_data, "test_table", "test_column"
                )

                assert result.severity == expected_severity

    def test_detect_outliers_iqr_normal_data(self):
        """测试IQR检测正常数据"""
        # Create actual test data instead of using mocked numpy
        data = pd.Series([50 + 10 * (i - 50) / 20 for i in range(100)])

        result = self.detector.detect_outliers_iqr(data, "test_table", "test_column")

        assert result.table_name == "test_table"
        assert result.detection_method == "iqr"
        assert result.anomaly_type == "statistical_outlier"
        assert "Q1" in result.statistics
        assert "Q3" in result.statistics
        assert "IQR" in result.statistics

    def test_detect_outliers_iqr_with_outliers(self):
        """测试IQR检测包含异常值的数据"""
        # 创建包含异常值的数据
        normal_data = list(range(20, 80))  # 正常数据 20-79
        outlier_data = [200, 250]        # 异常值
        data = pd.Series(normal_data + outlier_data)

        result = self.detector.detect_outliers_iqr(data, "test_table", "test_column")

        assert result.statistics["outliers_count"] > 0
        assert len(result.anomalous_records) > 0

        # 验证异常记录结构
        anomalous_record = result.anomalous_records[0]
        assert "index" in anomalous_record
        assert "column" in anomalous_record
        assert "value" in anomalous_record
        assert "iqr_distance" in anomalous_record
        assert "threshold_exceeded" in anomalous_record

    def test_detect_outliers_iqr_custom_multiplier(self):
        """测试IQR自定义倍数"""
        data = pd.Series([1, 2, 3, 4, 5, 100])

        # 使用较严格的倍数
        result_strict = self.detector.detect_outliers_iqr(data, "test_table", "test_column", iqr_multiplier=1.0)

        # 使用较宽松的倍数
        result_lenient = self.detector.detect_outliers_iqr(data, "test_table", "test_column", iqr_multiplier=3.0)

        # 较严格的倍数应该检测到更多异常值
        assert result_strict.statistics["outliers_count"] >= result_lenient.statistics["outliers_count"]

    @patch('data.quality.anomaly_detector.anomalies_detected_total')
    @patch('data.quality.anomaly_detector.anomaly_detection_duration_seconds')
    def test_detect_outliers_iqr_prometheus_metrics(self, mock_duration, mock_counter):
        """测试IQR检测Prometheus指标记录"""
        mock_counter.inc = Mock()
        mock_duration.observe = Mock()

        data = pd.Series([1, 2, 3, 100, 4, 5])
        result = self.detector.detect_outliers_iqr(data, "test_table", "test_column")

        # 验证Prometheus指标被调用
        mock_counter.labels.assert_called()
        mock_duration.observe.assert_called()


class TestMachineLearningAnomalyDetector:
    """测试机器学习异常检测器"""

    def setup_method(self):
        """设置测试环境"""
        self.detector = MachineLearningAnomalyDetector()
        self.mock_scaler = Mock()
        self.mock_isolation_forest = Mock()
        self.mock_dbscan = Mock()

    def test_initialization(self):
        """测试初始化"""
        assert self.detector.logger is not None
        assert self.detector.scaler is not None
        assert self.detector.isolation_forest is None
        assert self.detector.dbscan is None

    def test_detect_anomalies_isolation_forest_no_numeric_columns(self):
        """测试Isolation Forest检测无数值列"""
        data = pd.DataFrame({"text": ["a", "b", "c"], "category": ["x", "y", "z"]})

        with pytest.raises(ValueError) as exc_info:
            self.detector.detect_anomalies_isolation_forest(data, "test_table")

        assert "没有可用的数值列" in str(exc_info.value)

    def test_detect_anomalies_isolation_forest_normal_data(self):
        """测试Isolation Forest检测正常数据"""
        # 创建正常数据
        # Create actual test data instead of using mocked numpy
        data = pd.DataFrame({
            "feature1": [50 + 10 * (i - 50) / 20 for i in range(100)],
            "feature2": [30 + 5 * (i - 50) / 20 for i in range(100)]
        })

        # 模拟scaler和isolation forest
        self.detector.scaler.fit_transform = Mock(return_value=[[i/100, j/100] for i, j in zip(range(100), range(100))])

        mock_if = Mock()
        mock_if.fit_predict.return_value = np.array([1] * 95 + [-1] * 5)  # 5个异常值
        mock_if.decision_function.return_value = [i/100 for i in range(100)]
        self.detector.isolation_forest = mock_if

        with patch('data.quality.anomaly_detector.IsolationForest') as mock_if_class:
            mock_if_class.return_value = mock_if

            result = self.detector.detect_anomalies_isolation_forest(data, "test_table")

            assert result.table_name == "test_table"
            assert result.detection_method == "isolation_forest"
            assert result.anomaly_type == "ml_anomaly"
            assert result.statistics["total_records"] == 100
            assert result.statistics["anomalies_count"] == 5
            assert len(result.anomalous_records) == 5

    def test_detect_anomalies_isolation_forest_severity_levels(self):
        """测试Isolation Forest异常严重程度分级"""
        data = pd.DataFrame({"feature1": [1, 2, 3]})

        # 模拟不同异常率
        test_cases = [
            ([1] * 8 + [-1] * 2, 0.2, "critical"),   # 20%异常率
            ([1] * 9 + [-1] * 1, 0.1, "high"),      # 10%异常率
            ([1] * 95 + [-1] * 5, 0.05, "medium"),  # 5%异常率
            ([1] * 99 + [-1] * 1, 0.01, "low"),     # 1%异常率
        ]

        for labels, anomaly_rate, expected_severity in test_cases:
            self.detector.scaler.fit_transform = Mock(return_value=np.array([[1], [2], [3]]))

            mock_if = Mock()
            mock_if.fit_predict.return_value = np.array(labels)
            mock_if.decision_function.return_value = [i/len(labels) for i in range(len(labels))]

            with patch('data.quality.anomaly_detector.IsolationForest') as mock_if_class:
                mock_if_class.return_value = mock_if

                result = self.detector.detect_anomalies_isolation_forest(data, "test_table")

                assert result.severity == expected_severity

    def test_detect_anomalies_isolation_forest_contamination_param(self):
        """测试Isolation Forest污染参数"""
        data = pd.DataFrame({"feature1": [1, 2, 3]})

        self.detector.scaler.fit_transform = Mock(return_value=np.array([[1], [2], [3]]))

        mock_if = Mock()
        mock_if.fit_predict.return_value = np.array([1, 1, -1])
        mock_if.decision_function.return_value = np.array([0.1, 0.2, -0.1])

        with patch('data.quality.anomaly_detector.IsolationForest') as mock_if_class:
            self.detector.detect_anomalies_isolation_forest(data, "test_table", contamination=0.05)

            # 验证Isolation Forest被正确调用
            mock_if_class.assert_called_with(
                contamination=0.05, random_state=42, n_estimators=100
            )

    def test_detect_data_drift_no_common_columns(self):
        """测试数据漂移检测无共同列"""
        baseline_data = pd.DataFrame({"col1": [1, 2, 3]})
        current_data = pd.DataFrame({"col2": [4, 5, 6]})

        results = self.detector.detect_data_drift(baseline_data, current_data, "test_table")

        assert results == []

    def test_detect_data_drift_with_drift(self):
        """测试检测到数据漂移"""
        baseline_data = pd.DataFrame({
            "feature1": [50 + 10 * (i - 100//2) / 20 for i in range(100)],
            "feature2": [30 + 5 * (i - 100//2) / 20 for i in range(100)]
        })
        current_data = pd.DataFrame({
            "feature1": [80 + 10 * (i - 100//2) / 20 for i in range(100)],  # 明显漂移
            "feature2": [30 + 5 * (i - 100//2) / 20 for i in range(100)]
        })

        with patch('data.quality.anomaly_detector.stats.ks_2samp') as mock_ks:
            mock_ks.return_value = (0.4, 0.001)  # 显著漂移

            results = self.detector.detect_data_drift(baseline_data, current_data, "test_table")

            assert len(results) > 0
            result = results[0]
            assert result.anomaly_type == "feature_drift"
            assert result.severity in ["critical", "high"]
            assert "drift_score" in result.statistics

    def test_detect_data_drift_no_significant_drift(self):
        """测试无显著数据漂移"""
        baseline_data = pd.DataFrame({"feature1": [50, 51, 49]})
        current_data = pd.DataFrame({"feature1": [50.1, 51.1, 49.1]})

        with patch('data.quality.anomaly_detector.stats.ks_2samp') as mock_ks:
            mock_ks.return_value = (0.1, 0.8)  # 无显著漂移

            results = self.detector.detect_data_drift(baseline_data, current_data, "test_table")

            assert results == []

    def test_detect_anomalies_clustering_no_numeric_columns(self):
        """测试DBSCAN聚类检测无数值列"""
        data = pd.DataFrame({"text": ["a", "b", "c"]})

        with pytest.raises(ValueError) as exc_info:
            self.detector.detect_anomalies_clustering(data, "test_table")

        assert "没有可用的数值列" in str(exc_info.value)

    def test_detect_anomalies_clustering_normal_data(self):
        """测试DBSCAN聚类检测正常数据"""
        data = pd.DataFrame({
            "feature1": [50 + 10 * (i - 50//2) / 20 for i in range(50)],
            "feature2": [30 + 5 * (i - 50//2) / 20 for i in range(50)]
        })

        # 模拟scaler和DBSCAN
        self.detector.scaler.fit_transform = Mock(return_value=[[i/50, j/50] for i, j in zip(range(50), range(50))])

        mock_dbscan = Mock()
        mock_dbscan.fit_predict.return_value = np.array([0] * 45 + [-1] * 5)  # 5个噪声点
        self.detector.dbscan = mock_dbscan

        with patch('data.quality.anomaly_detector.DBSCAN') as mock_dbscan_class:
            mock_dbscan_class.return_value = mock_dbscan

            result = self.detector.detect_anomalies_clustering(data, "test_table")

            assert result.table_name == "test_table"
            assert result.detection_method == "dbscan_clustering"
            assert result.anomaly_type == "clustering_outlier"
            assert result.statistics["total_records"] == 50
            assert result.statistics["anomalies_count"] == 5
            assert len(result.anomalous_records) == 5

    def test_detect_anomalies_clustering_severity_levels(self):
        """测试DBSCAN聚类异常严重程度分级"""
        data = pd.DataFrame({"feature1": [1, 2, 3]})

        # 模拟不同异常率
        test_cases = [
            ([0] * 7 + [-1] * 3, 0.3, "critical"),   # 30%异常率
            ([0] * 8 + [-1] * 2, 0.2, "high"),      # 20%异常率
            ([0] * 9 + [-1] * 1, 0.1, "medium"),    # 10%异常率
            ([0] * 95 + [-1] * 5, 0.05, "low"),     # 5%异常率
        ]

        for labels, anomaly_rate, expected_severity in test_cases:
            self.detector.scaler.fit_transform = Mock(return_value=np.array([[1], [2], [3]]))

            mock_dbscan = Mock()
            mock_dbscan.fit_predict.return_value = np.array(labels)

            with patch('data.quality.anomaly_detector.DBSCAN') as mock_dbscan_class:
                mock_dbscan_class.return_value = mock_dbscan

                result = self.detector.detect_anomalies_clustering(data, "test_table")

                assert result.severity == expected_severity

    def test_detect_anomalies_clustering_custom_params(self):
        """测试DBSCAN自定义参数"""
        data = pd.DataFrame({"feature1": [1, 2, 3]})

        self.detector.scaler.fit_transform = Mock(return_value=np.array([[1], [2], [3]]))

        mock_dbscan = Mock()
        mock_dbscan.fit_predict.return_value = np.array([0, 0, -1])

        with patch('data.quality.anomaly_detector.DBSCAN') as mock_dbscan_class:
            self.detector.detect_anomalies_clustering(data, "test_table", eps=0.8, min_samples=10)

            # 验证DBSCAN被正确调用
            mock_dbscan_class.assert_called_with(eps=0.8, min_samples=10)


class TestAdvancedAnomalyDetector:
    """测试高级异常检测器"""

    def setup_method(self):
        """设置测试环境"""
        self.detector = AdvancedAnomalyDetector()
        self.detector.db_manager = AsyncMock()
        self.mock_session = AsyncMock()

    def test_initialization(self):
        """测试初始化"""
        assert self.detector.logger is not None
        assert self.detector.statistical_detector is not None
        assert self.detector.ml_detector is not None
        assert "matches" in self.detector.detection_config
        assert "odds" in self.detector.detection_config
        assert "predictions" in self.detector.detection_config

    @patch('data.quality.anomaly_detector.anomaly_detection_coverage')
    async def test_run_comprehensive_detection_no_config(self, mock_coverage):
        """测试运行综合检测无配置"""
        mock_coverage.set = Mock()

        results = await self.detector.run_comprehensive_detection("unknown_table")

        assert results == []
        self.detector.logger.warning.assert_called_with("表 unknown_table 没有配置异常检测规则")

    @patch('data.quality.anomaly_detector.anomaly_detection_coverage')
    async def test_run_comprehensive_detection_no_data(self, mock_coverage):
        """测试运行综合检测无数据"""
        mock_coverage.set = Mock()

        # 模拟空数据
        self.detector._get_table_data = AsyncMock(return_value=pd.DataFrame())

        results = await self.detector.run_comprehensive_detection("matches")

        assert results == []
        self.detector.logger.warning.assert_called_with("表 matches 没有数据")

    @patch('data.quality.anomaly_detector.anomaly_detection_coverage')
    async def test_run_comprehensive_detection_success(self, mock_coverage):
        """测试成功运行综合检测"""
        mock_coverage.set = Mock()

        # 模拟数据
        test_data = pd.DataFrame({
            "home_score": [1, 2, 3],
            "away_score": [0, 1, 2],
            "match_time": pd.date_range("2024-01-01", periods=3)
        })

        self.detector._get_table_data = AsyncMock(return_value=test_data)
        self.detector._get_total_records = AsyncMock(return_value=100)

        # 模拟各种检测方法
        mock_3sigma_result = Mock()
        mock_3sigma_result.statistics = {"outliers_count": 1}
        self.detector.statistical_detector.detect_outliers_3sigma = Mock(return_value=mock_3sigma_result)

        mock_iqr_result = Mock()
        mock_iqr_result.statistics = {"outliers_count": 0}
        self.detector.statistical_detector.detect_outliers_iqr = Mock(return_value=mock_iqr_result)

        mock_if_result = Mock()
        mock_if_result.statistics = {"anomalies_count": 0}
        self.detector.ml_detector.detect_anomalies_isolation_forest = Mock(return_value=mock_if_result)

        self.detector._run_data_drift_detection = AsyncMock(return_value=[])

        results = await self.detector.run_comprehensive_detection("matches")

        assert len(results) >= 2  # 至少包含3sigma和IQR结果
        mock_coverage.set.assert_called_once()

    @patch('data.quality.anomaly_detector.anomaly_detection_coverage')
    async def test_run_comprehensive_detection_method_errors(self, mock_coverage):
        """测试综合检测方法错误处理"""
        mock_coverage.set = Mock()

        test_data = pd.DataFrame({"home_score": [1, 2, 3]})
        self.detector._get_table_data = AsyncMock(return_value=test_data)
        self.detector._get_total_records = AsyncMock(return_value=100)

        # 模拟方法错误
        self.detector.statistical_detector.detect_outliers_3sigma = Mock(side_effect=Exception("3sigma错误"))
        self.detector.statistical_detector.detect_outliers_iqr = Mock(side_effect=Exception("IQR错误"))
        self.detector._run_data_drift_detection = AsyncMock(return_value=[])

        results = await self.detector.run_comprehensive_detection("matches")

        # 应该继续执行其他方法，不抛出异常
        assert isinstance(results, list)
        self.detector.logger.error.assert_called()

    async def test_get_table_data_matches(self):
        """测试获取比赛数据"""
        # 模拟数据库查询
        mock_rows = [
            (1, 0, 0, 0, 90, "2024-01-01T12:00:00", "2024-01-01T12:00:00", "2024-01-01T12:00:00"),
            (2, 1, 0, 0, 45, "2024-01-01T15:00:00", "2024-01-01T15:00:00", "2024-01-01T15:00:00")
        ]

        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows
        mock_result.keys.return_value = ["home_score", "away_score", "home_ht_score", "away_ht_score", "minute", "match_time", "created_at", "updated_at"]

        self.detector.db_manager.get_async_session.return_value.__aenter__.return_value = self.mock_session
        self.mock_session.execute.return_value = mock_result

        data = await self.detector._get_table_data("matches", 24)

        assert len(data) == 2
        assert "home_score" in data.columns
        assert "away_score" in data.columns

    async def test_get_table_data_odds(self):
        """测试获取赔率数据"""
        mock_rows = [
            (2.0, 3.0, 4.0, 1.8, 1.9, "2024-01-01T12:00:00", "2024-01-01T12:00:00"),
            (2.1, 3.1, 4.1, 1.9, 2.0, "2024-01-01T15:00:00", "2024-01-01T15:00:00")
        ]

        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows
        mock_result.keys.return_value = ["home_odds", "draw_odds", "away_odds", "over_odds", "under_odds", "collected_at", "created_at"]

        self.detector.db_manager.get_async_session.return_value.__aenter__.return_value = self.mock_session
        self.mock_session.execute.return_value = mock_result

        data = await self.detector._get_table_data("odds", 24)

        assert len(data) == 2
        assert "home_odds" in data.columns
        assert "away_odds" in data.columns

    async def test_get_table_data_predictions(self):
        """测试获取预测数据"""
        mock_rows = [
            (0.6, 0.2, 0.2, 0.8, "2024-01-01T12:00:00"),
            (0.5, 0.3, 0.2, 0.7, "2024-01-01T15:00:00")
        ]

        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows
        mock_result.keys.return_value = ["home_win_probability", "draw_probability", "away_win_probability", "confidence_score", "created_at"]

        self.detector.db_manager.get_async_session.return_value.__aenter__.return_value = self.mock_session
        self.mock_session.execute.return_value = mock_result

        data = await self.detector._get_table_data("predictions", 24)

        assert len(data) == 2
        assert "home_win_probability" in data.columns
        assert "confidence_score" in data.columns

    async def test_get_table_data_unknown_table(self):
        """测试获取未知表数据"""
        data = await self.detector._get_table_data("unknown_table", 24)

        assert data.empty

    async def test_get_table_data_no_database(self):
        """测试无数据库连接获取数据"""
        self.detector.db_manager = None

        data = await self.detector._get_table_data("matches", 24)

        assert data.empty
        self.detector.logger.error.assert_called_with("数据库连接未初始化，请先调用 initialize()")

    async def test_get_total_records_success(self):
        """测试成功获取总记录数"""
        self.detector.db_manager.get_async_session.return_value.__aenter__.return_value = self.mock_session
        self.mock_session.execute.return_value.scalar.return_value = 1000

        count = await self.detector._get_total_records("matches")

        assert count == 1000

    async def test_get_total_records_unknown_table(self):
        """测试获取未知表总记录数"""
        count = await self.detector._get_total_records("unknown_table")

        assert count == 0

    async def test_get_total_records_no_database(self):
        """测试无数据库连接获取总记录数"""
        self.detector.db_manager = None

        count = await self.detector._get_total_records("matches")

        assert count == 0
        self.detector.logger.error.assert_called_with("数据库连接未初始化，请先调用 initialize()")

    async def test_get_total_records_none_result(self):
        """测试获取总记录数返回None"""
        self.detector.db_manager.get_async_session.return_value.__aenter__.return_value = self.mock_session
        self.mock_session.execute.return_value.scalar.return_value = None

        count = await self.detector._get_total_records("matches")

        assert count == 0

    async def test_run_3sigma_detection(self):
        """测试运行3σ检测"""
        data = pd.DataFrame({
            "home_score": [1, 2, 3, 10],  # 包含异常值
            "away_score": [0, 1, 1, 2]
        })

        config = {"key_columns": ["home_score", "away_score"]}

        mock_result = Mock()
        self.detector.statistical_detector.detect_outliers_3sigma = Mock(return_value=mock_result)

        results = await self.detector._run_3sigma_detection("matches", data, config)

        assert len(results) == 2  # 两列都检测
        self.detector.statistical_detector.detect_outliers_3sigma.assert_called()

    async def test_run_3sigma_detection_column_skip(self):
        """测试3σ检测跳过非数值列"""
        data = pd.DataFrame({
            "home_score": [1, 2, 3],
            "match_status": ["scheduled", "finished", "postponed"]  # 非数值列
        })

        config = {"key_columns": ["home_score", "match_status"]}

        # 只对数值列进行检测
        mock_result = Mock()
        self.detector.statistical_detector.detect_outliers_3sigma = Mock(return_value=mock_result)

        results = await self.detector._run_3sigma_detection("matches", data, config)

        assert len(results) == 1  # 只有home_score列被检测

    async def test_run_3sigma_detection_error_handling(self):
        """测试3σ检测错误处理"""
        data = pd.DataFrame({"home_score": [1, 2, 3]})
        config = {"key_columns": ["home_score"]}

        self.detector.statistical_detector.detect_outliers_3sigma = Mock(side_effect=Exception("检测失败"))

        results = await self.detector._run_3sigma_detection("matches", data, config)

        assert results == []  # 错误时返回空列表
        self.detector.logger.warning.assert_called()

    async def test_run_iqr_detection(self):
        """测试运行IQR检测"""
        data = pd.DataFrame({
            "home_score": [1, 2, 3, 100],  # 包含异常值
            "away_score": [0, 1, 1, 2]
        })

        config = {"key_columns": ["home_score", "away_score"]}

        mock_result = Mock()
        self.detector.statistical_detector.detect_outliers_iqr = Mock(return_value=mock_result)

        results = await self.detector._run_iqr_detection("matches", data, config)

        assert len(results) == 2  # 两列都检测
        self.detector.statistical_detector.detect_outliers_iqr.assert_called()

    async def test_run_data_drift_detection_success(self):
        """测试成功运行数据漂移检测"""
        current_data = pd.DataFrame({"home_score": [1, 2, 3]})
        config = {"drift_baseline_days": 30}

        baseline_data = pd.DataFrame({"home_score": [2, 3, 4]})
        mock_drift_results = [Mock()]

        self.detector._get_baseline_data = AsyncMock(return_value=baseline_data)
        self.detector.ml_detector.detect_data_drift = Mock(return_value=mock_drift_results)

        results = await self.detector._run_data_drift_detection("matches", current_data, config)

        assert results == mock_drift_results
        self.detector._get_baseline_data.assert_called_once_with("matches", 30)

    async def test_run_data_drift_detection_no_baseline(self):
        """测试数据漂移检测无基准数据"""
        current_data = pd.DataFrame({"home_score": [1, 2, 3]})
        config = {"drift_baseline_days": 30}

        self.detector._get_baseline_data = AsyncMock(return_value=pd.DataFrame())

        results = await self.detector._run_data_drift_detection("matches", current_data, config)

        assert results == []
        self.detector.logger.warning.assert_called()

    async def test_run_data_drift_detection_error(self):
        """测试数据漂移检测错误"""
        current_data = pd.DataFrame({"home_score": [1, 2, 3]})
        config = {"drift_baseline_days": 30}

        self.detector._get_baseline_data = AsyncMock(side_effect=Exception("获取基准数据失败"))

        results = await self.detector._run_data_drift_detection("matches", current_data, config)

        assert results == []
        self.detector.logger.error.assert_called()

    async def test_run_distribution_shift_detection_success(self):
        """测试成功运行分布偏移检测"""
        current_data = pd.DataFrame({"home_score": [1, 2, 3]})
        config = {"drift_baseline_days": 30, "key_columns": ["home_score"]}

        baseline_data = pd.DataFrame({"home_score": [2, 3, 4]})
        mock_result = Mock()

        self.detector._get_baseline_data = AsyncMock(return_value=baseline_data)
        self.detector.statistical_detector.detect_distribution_shift = Mock(return_value=mock_result)

        results = await self.detector._run_distribution_shift_detection("matches", current_data, config)

        assert len(results) == 1
        assert results[0] == mock_result

    async def test_run_distribution_shift_detection_no_baseline(self):
        """测试分布偏移检测无基准数据"""
        current_data = pd.DataFrame({"home_score": [1, 2, 3]})
        config = {"drift_baseline_days": 30, "key_columns": ["home_score"]}

        self.detector._get_baseline_data = AsyncMock(return_value=pd.DataFrame())

        results = await self.detector._run_distribution_shift_detection("matches", current_data, config)

        assert results == []

    async def test_run_distribution_shift_detection_column_mismatch(self):
        """测试分布偏移检测列不匹配"""
        current_data = pd.DataFrame({"home_score": [1, 2, 3]})
        baseline_data = pd.DataFrame({"away_score": [0, 1, 2]})  # 列不匹配
        config = {"drift_baseline_days": 30, "key_columns": ["home_score"]}

        self.detector._get_baseline_data = AsyncMock(return_value=baseline_data)

        results = await self.detector._run_distribution_shift_detection("matches", current_data, config)

        assert results == []

    async def test_get_baseline_data_matches(self):
        """测试获取比赛基准数据"""
        mock_rows = [(1, 0, 0, 0, 90, "2024-01-01T12:00:00")]
        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows
        mock_result.keys.return_value = ["home_score", "away_score", "home_ht_score", "away_ht_score", "minute", "match_time"]

        self.detector.db_manager.get_async_session.return_value.__aenter__.return_value = self.mock_session
        self.mock_session.execute.return_value = mock_result

        data = await self.detector._get_baseline_data("matches", 30)

        assert len(data) == 1
        assert "home_score" in data.columns

    async def test_get_baseline_data_odds(self):
        """测试获取赔率基准数据"""
        mock_rows = [(2.0, 3.0, 4.0, 1.8, 1.9)]
        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows
        mock_result.keys.return_value = ["home_odds", "draw_odds", "away_odds", "over_odds", "under_odds"]

        self.detector.db_manager.get_async_session.return_value.__aenter__.return_value = self.mock_session
        self.mock_session.execute.return_value = mock_result

        data = await self.detector._get_baseline_data("odds", 7)

        assert len(data) == 1
        assert "home_odds" in data.columns

    async def test_get_baseline_data_predictions(self):
        """测试获取预测基准数据"""
        mock_rows = [(0.6, 0.2, 0.2, 0.8)]
        mock_result = Mock()
        mock_result.fetchall.return_value = mock_rows
        mock_result.keys.return_value = ["home_win_probability", "draw_probability", "away_win_probability", "confidence_score"]

        self.detector.db_manager.get_async_session.return_value.__aenter__.return_value = self.mock_session
        self.mock_session.execute.return_value = mock_result

        data = await self.detector._get_baseline_data("predictions", 14)

        assert len(data) == 1
        assert "home_win_probability" in data.columns

    async def test_get_baseline_data_unknown_table(self):
        """测试获取未知表基准数据"""
        data = await self.detector._get_baseline_data("unknown_table", 30)

        assert data.empty

    async def test_get_baseline_data_no_rows(self):
        """测试获取基准数据无返回行"""
        mock_result = Mock()
        mock_result.fetchall.return_value = []

        self.detector.db_manager.get_async_session.return_value.__aenter__.return_value = self.mock_session
        self.mock_session.execute.return_value = mock_result

        data = await self.detector._get_baseline_data("matches", 30)

        assert data.empty

    @patch('data.quality.anomaly_detector.anomaly_detection_coverage')
    async def test_get_anomaly_summary(self, mock_coverage):
        """测试获取异常检测摘要"""
        mock_coverage.set = Mock()

        # 模拟检测结果
        mock_result1 = Mock()
        mock_result1.severity = "high"
        mock_result1.detection_method = "3sigma"
        mock_result1.anomaly_type = "statistical_outlier"

        mock_result2 = Mock()
        mock_result2.severity = "medium"
        mock_result2.detection_method = "iqr"
        mock_result2.anomaly_type = "statistical_outlier"

        self.detector.run_comprehensive_detection = AsyncMock(
            side_effect=[[mock_result1], [mock_result2], []]
        )

        summary = await self.detector.get_anomaly_summary(24)

        assert "detection_period" in summary
        assert "tables_analyzed" in summary
        assert "total_anomalies" in summary
        assert "anomalies_by_table" in summary
        assert "anomalies_by_severity" in summary
        assert "anomalies_by_method" in summary
        assert "anomalies_by_type" in summary

        assert summary["total_anomalies"] == 2
        assert summary["anomalies_by_severity"]["high"] == 1
        assert summary["anomalies_by_severity"]["medium"] == 1
        assert "3sigma" in summary["anomalies_by_method"]
        assert "iqr" in summary["anomalies_by_method"]

    @patch('data.quality.anomaly_detector.anomaly_detection_coverage')
    async def test_get_anomaly_summary_error_handling(self, mock_coverage):
        """测试获取异常检测摘要错误处理"""
        mock_coverage.set = Mock()

        self.detector.run_comprehensive_detection = AsyncMock(side_effect=Exception("检测失败"))

        with pytest.raises(Exception) as exc_info:
            await self.detector.get_anomaly_summary(24)

        assert "生成异常检测摘要失败" in str(exc_info.value)


class TestAnomalyDetectorIntegration:
    """测试异常检测器集成功能"""

    def setup_method(self):
        """设置测试环境"""
        self.statistical_detector = StatisticalAnomalyDetector()
        self.ml_detector = MachineLearningAnomalyDetector()
        self.advanced_detector = AdvancedAnomalyDetector()

    def test_multiple_detection_methods_on_same_data(self):
        """测试多种检测方法在同一数据上的应用"""
        data = pd.Series([1, 2, 3, 4, 100])  # 包含异常值

        # 3σ检测
        result_3sigma = self.statistical_detector.detect_outliers_3sigma(
            data, "test_table", "test_column"
        )

        # IQR检测
        result_iqr = self.statistical_detector.detect_outliers_iqr(
            data, "test_table", "test_column"
        )

        # 验证两种方法都能检测到异常值
        assert result_3sigma.statistics["outliers_count"] > 0 or result_iqr.statistics["outliers_count"] > 0

    def test_detection_consistency_across_methods(self):
        """测试不同检测方法的一致性"""
        # np.random.seed(42)  # Removed - using deterministic data
        normal_data = pd.Series([50 + 10 * (i - 100//2) / 20 for i in range(100)])

        # 对正常数据进行多种检测
        result_3sigma = self.statistical_detector.detect_outliers_3sigma(
            normal_data, "test_table", "test_column"
        )

        result_iqr = self.statistical_detector.detect_outliers_iqr(
            normal_data, "test_table", "test_column"
        )

        # 对正常数据，不同方法的异常率应该都较低
        assert result_3sigma.statistics["outlier_rate"] < 0.1
        assert result_iqr.statistics["outlier_rate"] < 0.1

    def test_severity_classification_consistency(self):
        """测试严重程度分类的一致性"""
        # 创建包含少量异常值的数据
        data = pd.Series([50] * 95 + [200] * 5)

        result_3sigma = self.statistical_detector.detect_outliers_3sigma(
            data, "test_table", "test_column"
        )

        result_iqr = self.statistical_detector.detect_outliers_iqr(
            data, "test_table", "test_column"
        )

        # 验证严重程度分类合理
        assert result_3sigma.severity in ["low", "medium", "high", "critical"]
        assert result_iqr.severity in ["low", "medium", "high", "critical"]

    def test_anomaly_record_structure_consistency(self):
        """测试异常记录结构的一致性"""
        data = pd.Series([1, 2, 3, 100])

        result = self.statistical_detector.detect_outliers_3sigma(
            data, "test_table", "test_column"
        )

        if result.anomalous_records:
            record = result.anomalous_records[0]
            # 验证必需字段存在
            required_fields = ["index", "column", "value"]
            for field in required_fields:
                assert field in record

            # 验证字段类型
            assert isinstance(record["index"], int)
            assert isinstance(record["column"], str)
            assert isinstance(record["value"], (int, float))

    def test_statistics_structure_consistency(self):
        """测试统计信息结构的一致性"""
        data = pd.Series([1, 2, 3, 4, 5])

        result = self.statistical_detector.detect_outliers_3sigma(
            data, "test_table", "test_column"
        )

        # 验证必需的统计字段
        required_stats = ["total_records", "outliers_count", "outlier_rate"]
        for stat in required_stats:
            assert stat in result.statistics

        # 验证统计值的合理性
        assert result.statistics["total_records"] > 0
        assert result.statistics["outliers_count"] >= 0
        assert 0 <= result.statistics["outlier_rate"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])