"""
数据异常检测模块测试

测试覆盖：
- 统计学异常检测方法
- 机器学习异常检测方法
- 综合异常检测器
- Prometheus指标导出
- 各种边界情况和错误处理

基于项目测试规范，使用pytest框架和中文注释。
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from prometheus_client import CollectorRegistry

from src.data.quality.anomaly_detector import (
    AdvancedAnomalyDetector,
    AnomalyDetectionResult,
    MachineLearningAnomalyDetector,
    StatisticalAnomalyDetector,
    anomalies_detected_total,
    anomaly_detection_coverage,
    anomaly_detection_duration_seconds,
    data_drift_score,
)


class TestAnomalyDetectionResult:
    """异常检测结果类测试"""

    def test_init(self):
        """测试结果对象初始化"""
        result = AnomalyDetectionResult(
            table_name="test_table",
            detection_method="test_method",
            anomaly_type="test_anomaly",
            severity="medium",
        )

        assert result.table_name == "test_table"
        assert result.detection_method == "test_method"
        assert result.anomaly_type == "test_anomaly"
        assert result.severity == "medium"
        assert isinstance(result.timestamp, datetime)
        assert result.anomalous_records == []
        assert result.statistics == {}
        assert result.metadata == {}

    def test_add_anomalous_record(self):
        """测试添加异常记录"""
        result = AnomalyDetectionResult("table", "method", "type")

        record = {"id": 1, "value": 100}
        result.add_anomalous_record(record)

        assert len(result.anomalous_records) == 1
        assert result.anomalous_records[0] == record

    def test_set_statistics(self):
        """测试设置统计信息"""
        result = AnomalyDetectionResult("table", "method", "type")

        stats = {"mean": 10.5, "std": 2.3}
        result.set_statistics(stats)

        assert result.statistics == stats

    def test_set_metadata(self):
        """测试设置元数据"""
        result = AnomalyDetectionResult("table", "method", "type")

        metadata = {"threshold": 3.0, "algorithm": "3sigma"}
        result.set_metadata(metadata)

        assert result.metadata == metadata

    def test_to_dict(self):
        """测试转换为字典"""
        result = AnomalyDetectionResult("table", "method", "type", "high")
        result.add_anomalous_record({"id": 1})
        result.set_statistics({"count": 1})
        result.set_metadata({"version": "1.0"})

        result_dict = result.to_dict()

        assert result_dict["table_name"] == "table"
        assert result_dict["detection_method"] == "method"
        assert result_dict["anomaly_type"] == "type"
        assert result_dict["severity"] == "high"
        assert result_dict["anomalous_records_count"] == 1
        assert result_dict["anomalous_records"] == [{"id": 1}]
        assert result_dict["statistics"] == {"count": 1}
        assert result_dict["metadata"] == {"version": "1.0"}
        assert "timestamp" in result_dict


class TestStatisticalAnomalyDetector:
    """统计学异常检测器测试"""

    @pytest.fixture
    def detector(self):
        """检测器实例"""
        return StatisticalAnomalyDetector(sigma_threshold=3.0)

    @pytest.fixture
    def normal_data(self):
        """正常分布测试数据"""
        np.random.seed(42)
        return pd.Series(np.random.normal(10, 2, 100))

    @pytest.fixture
    def data_with_outliers(self):
        """包含异常值的测试数据"""
        np.random.seed(42)
        data = np.random.normal(10, 2, 100)
        # 添加明显的异常值
        data[0] = 50  # 远大于正常值
        data[1] = -30  # 远小于正常值
        return pd.Series(data)

    def test_init(self, detector):
        """测试初始化"""
        assert detector.sigma_threshold == 3.0
        assert detector.logger is not None

    def test_detect_outliers_3sigma_no_outliers(self, detector, normal_data):
        """测试3σ检测 - 无异常值情况"""
        result = detector.detect_outliers_3sigma(
            normal_data, "test_table", "test_column"
        )

        assert isinstance(result, AnomalyDetectionResult)
        assert result.table_name == "test_table"
        assert result.detection_method == "3sigma"
        assert result.anomaly_type == "statistical_outlier"
        assert len(result.anomalous_records) == 0  # 正常数据应该没有异常

    def test_detect_outliers_3sigma_with_outliers(self, detector, data_with_outliers):
        """测试3σ检测 - 有异常值情况"""
        result = detector.detect_outliers_3sigma(
            data_with_outliers, "test_table", "test_column"
        )

        assert isinstance(result, AnomalyDetectionResult)
        assert len(result.anomalous_records) == 2  # 应该检测到2个异常值

        # 检查统计信息
        assert "total_records" in result.statistics
        assert "outliers_count" in result.statistics
        assert "outlier_rate" in result.statistics
        assert result.statistics["outliers_count"] == 2

        # 检查异常记录详情
        for record in result.anomalous_records:
            assert "z_score" in record
            assert abs(record["z_score"]) > 3.0  # z分数应该大于阈值

    def test_detect_distribution_shift_no_shift(self, detector, normal_data):
        """测试分布偏移检测 - 无偏移情况"""
        # 创建相似的数据集
        np.random.seed(43)
        similar_data = pd.Series(np.random.normal(10, 2, 100))

        result = detector.detect_distribution_shift(
            normal_data, similar_data, "test_table", "test_column"
        )

        assert isinstance(result, AnomalyDetectionResult)
        assert result.detection_method == "ks_test"
        assert result.anomaly_type == "distribution_shift"

        # p值应该较大，表示无显著差异
        assert result.statistics["p_value"] > 0.05

    def test_detect_distribution_shift_with_shift(self, detector, normal_data):
        """测试分布偏移检测 - 有偏移情况"""
        # 创建明显不同的数据集
        np.random.seed(42)
        shifted_data = pd.Series(np.random.normal(20, 5, 100))  # 不同的均值和方差

        result = detector.detect_distribution_shift(
            normal_data, shifted_data, "test_table", "test_column"
        )

        assert isinstance(result, AnomalyDetectionResult)
        assert result.statistics["distribution_shifted"] is True
        assert result.statistics["p_value"] < 0.05
        assert len(result.anomalous_records) == 1  # 应该记录一个偏移事件

    def test_detect_outliers_iqr(self, detector, data_with_outliers):
        """测试IQR方法检测异常值"""
        result = detector.detect_outliers_iqr(
            data_with_outliers, "test_table", "test_column"
        )

        assert isinstance(result, AnomalyDetectionResult)
        assert result.detection_method == "iqr"
        assert result.anomaly_type == "statistical_outlier"
        assert len(result.anomalous_records) >= 1  # 应该检测到异常值

        # 检查IQR统计信息
        assert "Q1" in result.statistics
        assert "Q3" in result.statistics
        assert "IQR" in result.statistics
        assert "lower_bound" in result.statistics
        assert "upper_bound" in result.statistics

    def test_3sigma_with_constant_data(self, detector):
        """测试3σ检测 - 常数数据"""
        constant_data = pd.Series([5.0] * 100)

        result = detector.detect_outliers_3sigma(
            constant_data, "test_table", "test_column"
        )

        # 常数数据标准差为0，应该正确处理
        assert isinstance(result, AnomalyDetectionResult)
        assert len(result.anomalous_records) == 0

    def test_empty_data_handling(self, detector):
        """测试空数据处理"""
        empty_data = pd.Series([])

        with pytest.raises(Exception):  # 空数据应该引发异常
            detector.detect_outliers_3sigma(empty_data, "test_table", "test_column")


class TestMachineLearningAnomalyDetector:
    """机器学习异常检测器测试"""

    @pytest.fixture
    def detector(self):
        """检测器实例"""
        return MachineLearningAnomalyDetector()

    @pytest.fixture
    def normal_dataframe(self):
        """正常的多维数据"""
        np.random.seed(42)
        return pd.DataFrame(
            {
                "feature1": np.random.normal(10, 2, 100),
                "feature2": np.random.normal(5, 1, 100),
                "feature3": np.random.normal(0, 0.5, 100),
            }
        )

    @pytest.fixture
    def dataframe_with_anomalies(self):
        """包含异常的多维数据"""
        np.random.seed(42)
        data = pd.DataFrame(
            {
                "feature1": np.random.normal(10, 2, 100),
                "feature2": np.random.normal(5, 1, 100),
                "feature3": np.random.normal(0, 0.5, 100),
            }
        )
        # 添加明显的异常样本
        data.loc[0] = [50, 20, 10]  # 异常值
        data.loc[1] = [-30, -15, -5]  # 异常值
        return data

    def test_init(self, detector):
        """测试初始化"""
        assert detector.logger is not None
        assert detector.scaler is not None
        assert detector.isolation_forest is None
        assert detector.dbscan is None

    def test_isolation_forest_normal_data(self, detector, normal_dataframe):
        """测试Isolation Forest - 正常数据"""
        result = detector.detect_anomalies_isolation_forest(
            normal_dataframe, "test_table", contamination=0.1
        )

        assert isinstance(result, AnomalyDetectionResult)
        assert result.detection_method == "isolation_forest"
        assert result.anomaly_type == "ml_anomaly"

        # 正常数据的异常率应该接近设定的contamination参数
        anomaly_rate = len(result.anomalous_records) / len(normal_dataframe)
        assert 0.05 <= anomaly_rate <= 0.15  # 允许一定范围的误差

    def test_isolation_forest_with_anomalies(self, detector, dataframe_with_anomalies):
        """测试Isolation Forest - 包含异常数据"""
        result = detector.detect_anomalies_isolation_forest(
            dataframe_with_anomalies, "test_table", contamination=0.1
        )

        assert isinstance(result, AnomalyDetectionResult)
        assert len(result.anomalous_records) > 0

        # 检查异常记录格式
        for record in result.anomalous_records:
            assert "index" in record
            assert "anomaly_score" in record
            assert "features" in record
            assert len(record["features"]) == 3  # 3个特征

    def test_data_drift_detection_no_drift(self, detector, normal_dataframe):
        """测试数据漂移检测 - 无漂移"""
        # 创建相似的数据
        np.random.seed(43)
        similar_data = pd.DataFrame(
            {
                "feature1": np.random.normal(10, 2, 100),
                "feature2": np.random.normal(5, 1, 100),
                "feature3": np.random.normal(0, 0.5, 100),
            }
        )

        results = detector.detect_data_drift(
            normal_dataframe, similar_data, "test_table"
        )

        assert isinstance(results, list)
        # 相似数据应该检测到很少或没有漂移
        drift_count = len(results)
        assert drift_count <= 1  # 允许少量随机漂移

    def test_data_drift_detection_with_drift(self, detector, normal_dataframe):
        """测试数据漂移检测 - 有明显漂移"""
        # 创建明显不同的数据
        np.random.seed(42)
        drifted_data = pd.DataFrame(
            {
                "feature1": np.random.normal(20, 4, 100),  # 均值和方差都不同
                "feature2": np.random.normal(10, 2, 100),
                "feature3": np.random.normal(2, 1, 100),
            }
        )

        results = detector.detect_data_drift(
            normal_dataframe, drifted_data, "test_table"
        )

        assert isinstance(results, list)
        assert len(results) > 0  # 应该检测到漂移

        # 检查漂移结果格式
        for result in results:
            assert isinstance(result, AnomalyDetectionResult)
            assert result.detection_method == "data_drift"
            assert result.anomaly_type == "feature_drift"
            assert len(result.anomalous_records) > 0

    def test_clustering_anomaly_detection(self, detector, dataframe_with_anomalies):
        """测试聚类异常检测"""
        result = detector.detect_anomalies_clustering(
            dataframe_with_anomalies, "test_table"
        )

        assert isinstance(result, AnomalyDetectionResult)
        assert result.detection_method == "dbscan_clustering"
        assert result.anomaly_type == "clustering_outlier"

        # 检查聚类统计信息
        assert "num_clusters" in result.statistics
        assert "eps" in result.statistics
        assert "min_samples" in result.statistics

    def test_non_numeric_data_handling(self, detector):
        """测试非数值数据处理"""
        non_numeric_data = pd.DataFrame(
            {"text_column": ["a", "b", "c"] * 30, "category": ["x", "y", "z"] * 30}
        )

        with pytest.raises(ValueError):  # 应该引发ValueError
            detector.detect_anomalies_isolation_forest(non_numeric_data, "test_table")

    def test_small_dataset_handling(self, detector):
        """测试小数据集处理"""
        small_data = pd.DataFrame({"feature1": [1, 2, 3], "feature2": [4, 5, 6]})

        # 小数据集可能无法有效训练模型，但不应该崩溃
        result = detector.detect_anomalies_isolation_forest(small_data, "test_table")
        assert isinstance(result, AnomalyDetectionResult)


class TestAdvancedAnomalyDetector:
    """高级异常检测器综合测试"""

    @pytest.fixture
    def detector(self):
        """检测器实例"""
        return AdvancedAnomalyDetector()

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        with patch("src.data.quality.anomaly_detector.DatabaseManager") as mock:
            yield mock

    def test_init(self, detector):
        """测试初始化"""
        assert detector.db_manager is not None
        assert detector.logger is not None
        assert detector.statistical_detector is not None
        assert detector.ml_detector is not None
        assert "matches" in detector.detection_config
        assert "odds" in detector.detection_config
        assert "predictions" in detector.detection_config

    @pytest.mark.asyncio
    async def test_get_table_data_matches(self, detector, mock_db_manager):
        """测试获取比赛表数据"""
        # 模拟数据库会话
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (2, 1, 1, 0, 90, datetime.now(), datetime.now(), datetime.now())
        ]
        mock_result.keys.return_value = [
            "home_score",
            "away_score",
            "home_ht_score",
            "away_ht_score",
            "minute",
            "match_time",
            "created_at",
            "updated_at",
        ]
        mock_session.execute.return_value = mock_result
        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        data = await detector._get_table_data("matches", 24)

        assert isinstance(data, pd.DataFrame)
        assert len(data) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_table_data_empty_result(self, detector, mock_db_manager):
        """测试空数据结果"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        data = await detector._get_table_data("matches", 24)

        assert isinstance(data, pd.DataFrame)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_total_records(self, detector, mock_db_manager):
        """测试获取总记录数"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1000
        mock_session.execute.return_value = mock_result
        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        count = await detector._get_total_records("matches")

        assert count == 1000

    @pytest.mark.asyncio
    async def test_run_3sigma_detection(self, detector):
        """测试运行3σ检测"""
        # 准备测试数据
        test_data = pd.DataFrame(
            {
                "home_score": [1, 2, 3, 100, 1, 2],  # 包含异常值100
                "away_score": [0, 1, 2, 1, 0, 1],
            }
        )
        config = {"key_columns": ["home_score", "away_score"]}

        results = await detector._run_3sigma_detection("test_table", test_data, config)

        assert isinstance(results, list)
        assert len(results) == 2  # 两个列的检测结果
        for result in results:
            assert isinstance(result, AnomalyDetectionResult)
            assert result.detection_method == "3sigma"

    @pytest.mark.asyncio
    async def test_run_iqr_detection(self, detector):
        """测试运行IQR检测"""
        test_data = pd.DataFrame(
            {
                "home_score": [1, 2, 3, 100, 1, 2],  # 包含异常值
                "away_score": [0, 1, 2, 1, 0, 1],
            }
        )
        config = {"key_columns": ["home_score", "away_score"]}

        results = await detector._run_iqr_detection("test_table", test_data, config)

        assert isinstance(results, list)
        assert len(results) == 2
        for result in results:
            assert result.detection_method == "iqr"

    @pytest.mark.asyncio
    async def test_get_anomaly_summary(self, detector, mock_db_manager):
        """测试获取异常检测摘要"""
        # 模拟空的数据库返回
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result
        mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = (
            mock_session
        )

        summary = await detector.get_anomaly_summary(24)

        assert isinstance(summary, dict)
        assert "detection_period" in summary
        assert "tables_analyzed" in summary
        assert "total_anomalies" in summary
        assert "anomalies_by_table" in summary
        assert "anomalies_by_severity" in summary
        assert summary["detection_period"]["hours"] == 24


class TestPrometheusMetrics:
    """Prometheus指标测试 - 使用fake collector registry避免真实依赖"""

    @pytest.fixture
    def fake_registry(self):
        """
        创建fake collector registry用于测试
        这样可以避免与全局registry的冲突，确保测试隔离
        """
        return CollectorRegistry()

    @pytest.fixture
    def mock_metrics(self, fake_registry):
        """
        创建mock的Prometheus指标对象
        使用fake registry确保测试不会影响真实的指标收集
        """
        from prometheus_client import Counter, Gauge, Histogram

        # 使用fake registry创建测试专用的指标
        mock_counter = Counter(
            "test_anomalies_detected_total",
            "Test anomalies detected counter",
            ["table_name", "anomaly_type", "detection_method", "severity"],
            registry=fake_registry,
        )

        mock_gauge = Gauge(
            "test_data_drift_score",
            "Test data drift score gauge",
            ["table_name", "feature_name"],
            registry=fake_registry,
        )

        mock_histogram = Histogram(
            "test_anomaly_detection_duration_seconds",
            "Test anomaly detection duration histogram",
            ["table_name", "detection_method"],
            registry=fake_registry,
        )

        mock_coverage_gauge = Gauge(
            "test_anomaly_detection_coverage",
            "Test anomaly detection coverage gauge",
            ["table_name"],
            registry=fake_registry,
        )

        return {
            "counter": mock_counter,
            "gauge": mock_gauge,
            "histogram": mock_histogram,
            "coverage_gauge": mock_coverage_gauge,
        }

    def test_metrics_initialization(self):
        """测试指标初始化"""
        # 验证指标对象存在
        assert anomalies_detected_total is not None
        assert data_drift_score is not None
        assert anomaly_detection_duration_seconds is not None
        assert anomaly_detection_coverage is not None

    def test_anomalies_detected_counter(self, mock_metrics):
        """
        测试异常检测计数器
        使用mock counter避免访问私有属性，通过registry获取指标值
        注意：Counter会自动生成_created时间戳样本，所以会有2个样本
        """
        counter = mock_metrics["counter"]

        # 增加计数
        counter.labels(
            table_name="test_table",
            anomaly_type="test_anomaly",
            detection_method="test_method",
            severity="medium",
        ).inc(5)

        # 通过collect方法验证计数（避免访问私有属性）
        metric_families = list(counter.collect())
        assert len(metric_families) == 1

        samples = metric_families[0].samples
        # Counter会生成2个样本：主要计数器和_created时间戳
        assert len(samples) == 2

        # 找到主要计数器样本（不是_created样本）
        main_sample = next(s for s in samples if not s.name.endswith("_created"))
        assert main_sample.value == 5

    def test_data_drift_score_gauge(self, mock_metrics):
        """
        测试数据漂移评分仪表
        使用mock gauge通过collect方法获取值，避免访问私有属性
        """
        gauge = mock_metrics["gauge"]

        # 设置漂移评分
        gauge.labels(table_name="test_table", feature_name="test_feature").set(0.75)

        # 通过collect方法验证设置值
        metric_families = list(gauge.collect())
        assert len(metric_families) == 1

        samples = metric_families[0].samples
        assert len(samples) == 1
        assert samples[0].value == 0.75

    def test_duration_histogram(self, mock_metrics):
        """
        测试执行时间直方图
        使用mock histogram通过collect方法获取统计信息，避免访问私有属性
        """
        histogram = mock_metrics["histogram"]

        # 记录执行时间
        histogram.labels(
            table_name="test_table", detection_method="test_method"
        ).observe(1.5)

        # 通过collect方法验证记录了观测值
        metric_families = list(histogram.collect())
        assert len(metric_families) == 1

        samples = metric_families[0].samples
        # histogram会产生多个样本：_bucket, _count, _sum
        sum_sample = next(s for s in samples if s.name.endswith("_sum"))
        count_sample = next(s for s in samples if s.name.endswith("_count"))

        assert sum_sample.value == 1.5
        assert count_sample.value == 1

    def test_coverage_gauge(self, mock_metrics):
        """
        测试覆盖率仪表
        使用mock gauge通过collect方法获取值，避免访问私有属性
        """
        coverage_gauge = mock_metrics["coverage_gauge"]

        # 设置覆盖率
        coverage_gauge.labels(table_name="test_table").set(0.95)

        # 通过collect方法验证设置值
        metric_families = list(coverage_gauge.collect())
        assert len(metric_families) == 1

        samples = metric_families[0].samples
        assert len(samples) == 1
        assert samples[0].value == 0.95


class TestEdgeCases:
    """边界情况测试"""

    @pytest.fixture
    def detector(self):
        return StatisticalAnomalyDetector()

    def test_single_value_data(self, detector):
        """测试单值数据"""
        single_value_data = pd.Series([5.0])

        # 单值数据的标准差为0，应该正确处理
        result = detector.detect_outliers_3sigma(
            single_value_data, "test_table", "test_column"
        )

        assert isinstance(result, AnomalyDetectionResult)
        assert len(result.anomalous_records) == 0

    def test_nan_data_handling(self, detector):
        """测试NaN数据处理"""
        data_with_nan = pd.Series([1, 2, np.nan, 4, 5])

        # 包含NaN的数据应该被正确处理（dropna）
        result = detector.detect_outliers_3sigma(
            data_with_nan, "test_table", "test_column"
        )

        assert isinstance(result, AnomalyDetectionResult)
        # 统计应该基于非NaN值
        assert result.statistics["total_records"] == 4

    def test_all_same_values(self, detector):
        """测试所有值相同的情况"""
        same_values = pd.Series([10.0] * 100)

        result = detector.detect_outliers_3sigma(
            same_values, "test_table", "test_column"
        )

        assert isinstance(result, AnomalyDetectionResult)
        assert len(result.anomalous_records) == 0  # 相同值没有异常
        assert result.statistics["std"] == 0.0

    def test_very_large_numbers(self, detector):
        """测试极大数值"""
        large_numbers = pd.Series(
            [1e10, 1e10 + 1, 1e10 + 2, 1e15]
        )  # 包含一个异常大的值

        result = detector.detect_outliers_3sigma(
            large_numbers, "test_table", "test_column"
        )

        assert isinstance(result, AnomalyDetectionResult)
        # 应该检测到1e15这个异常值
        assert len(result.anomalous_records) >= 1


@pytest.mark.integration
class TestIntegrationScenarios:
    """集成测试场景"""

    @pytest.fixture
    def advanced_detector(self):
        """高级检测器"""
        return AdvancedAnomalyDetector()

    @pytest.mark.asyncio
    async def test_comprehensive_detection_workflow(self, advanced_detector):
        """测试综合检测工作流"""
        # 这是一个集成测试，需要真实的数据库连接
        # 在CI环境中会被跳过
        pytest.skip("需要真实数据库连接的集成测试")

    def test_multiple_detection_methods_consistency(self):
        """测试多种检测方法的一致性"""
        # 创建包含明显异常的测试数据
        np.random.seed(42)
        normal_data = np.random.normal(10, 2, 98)
        outliers = [50, -30]  # 明显的异常值
        test_data = pd.Series(list(normal_data) + outliers)

        # 使用不同方法检测
        statistical_detector = StatisticalAnomalyDetector()

        sigma_result = statistical_detector.detect_outliers_3sigma(
            test_data, "test_table", "test_column"
        )
        iqr_result = statistical_detector.detect_outliers_iqr(
            test_data, "test_table", "test_column"
        )

        # 两种方法都应该检测到异常
        assert len(sigma_result.anomalous_records) > 0
        assert len(iqr_result.anomalous_records) > 0

        # 检测到的异常值应该有重叠
        sigma_indices = {r["index"] for r in sigma_result.anomalous_records}
        iqr_indices = {r["index"] for r in iqr_result.anomalous_records}

        # 应该有共同检测到的异常
        common_anomalies = sigma_indices & iqr_indices
        assert len(common_anomalies) > 0


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])
