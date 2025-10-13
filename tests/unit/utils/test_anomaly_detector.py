from datetime import datetime
from unittest.mock import MagicMock
import numpy as np
import pandas as pd
import pytest
from src.monitoring.anomaly_detector import AnomalyType
from src.data.quality.anomaly_detector import StatisticalAnomalyDetector
# 添加异常值
# 检测到home_goals=50和shots=100的异常
# home_goals列应该检测到异常
# 应该检测到2个异常点
# 创建季节性数据
# 创建正常数据
# 添加异常点
# 应该检测到至少2个异常
# 最后一个值的Z-score应该最大
# 应该检测到Unknown League
# 模拟实时数据流
# 初始化检测器
# 添加正常数据
# 检测正常数据
# 检测异常数据
# 统计异常评分
# 距离异常评分
# 模拟绘图（不实际显示）
# 验证方法被调用（通过mock）
# Mock通知器
# 初始阈值
# 更新阈值
# 验证阈值已更新
# 自定义检测函数
# 检测值为负数的异常
# 注册自定义检测器
# 测试数据
# 历史异常数据
# 学习模式
# 使用学习到的模式进行预测


"""
数据质量测试 - 异常检测器
"""


@pytest.mark.unit
class TestAnomalyDetector:
    """AnomalyDetector测试"""

    @pytest.fixture
    def detector(self):
        """创建检测器实例"""
        detector = StatisticalAnomalyDetector()
        detector.logger = MagicMock()
        return detector

    @pytest.fixture
    def sample_data(self):
        """示例数据"""
        return pd.DataFrame(
            {
                "match_id": [1, 2, 3, 4, 5, 100],  # 最后一个是异常值
                "home_goals": [1, 2, 1, 0, 2, 50],  # 50是异常
                "away_goals": [0, 1, 2, 1, 0, 0],
                "possession": [55, 60, 45, 50, 58, 95],  # 95%接近异常
                "shots": [10, 12, 8, 9, 11, 100],  # 100次射门是异常
            }
        )

    @pytest.fixture
    def time_series_data(self):
        """时间序列数据"""
        dates = pd.date_range("2025-01-01", periods=100)
        values = np.random.normal(50, 5, 100)
        values[50] = 200  # 异常高峰
        values[75] = -50  # 异常低谷

        return pd.DataFrame({"timestamp": dates, "value": values})

    def test_detector_initialization(self, detector):
        """测试检测器初始化"""
        assert detector is not None
        assert detector.logger is not None
        assert hasattr(detector, "threshold")
        assert hasattr(detector, "methods")

    def test_detect_statistical_outliers(self, detector, sample_data):
        """测试统计异常检测"""
        anomalies = detector.detect_statistical_outliers(
            sample_data, columns=["home_goals", "shots"], method="zscore", threshold=3
        )

        assert isinstance(anomalies, list)
        assert len(anomalies) > 0
        assert any(a["index"] == 5 for a in anomalies)

    def test_detect_iqr_outliers(self, detector, sample_data):
        """测试IQR异常检测"""
        anomalies = detector.detect_iqr_outliers(
            sample_data, columns=["home_goals", "possession"]
        )

        assert isinstance(anomalies, dict)
        assert "home_goals" in anomalies
        assert "possession" in anomalies
        assert len(anomalies["home_goals"]) > 0

    def test_detect_isolation_forest(self, detector, sample_data):
        """测试孤立森林异常检测"""
        anomalies = detector.detect_isolation_forest(sample_data, contamination=0.1)

        assert isinstance(anomalies, list)
        assert len(anomalies) >= 0
        if anomalies:
            assert "index" in anomalies[0]
            assert "score" in anomalies[0]

    def test_detect_time_series_anomalies(self, detector, time_series_data):
        """测试时间序列异常检测"""
        anomalies = detector.detect_time_series_anomalies(
            time_series_data, timestamp_col="timestamp", value_col="value", method="stl"
        )

        assert isinstance(anomalies, list)
        assert len(anomalies) >= 2

    def test_detect_seasonal_anomalies(self, detector):
        """测试季节性异常检测"""
        dates = pd.date_range("2024-01-01", periods=365)
        seasonal_data = 50 + 20 * np.sin(2 * np.pi * np.arange(365) / 30)
        seasonal_data[180] = 200  # 添加异常

        df = pd.DataFrame({"date": dates, "value": seasonal_data})

        anomalies = detector.detect_seasonal_anomalies(
            df, date_col="date", value_col="value", period=30
        )

        assert isinstance(anomalies, list)
        assert len(anomalies) >= 1

    def test_detect_multivariate_anomalies(self, detector):
        """测试多变量异常检测"""
        np.random.seed(42)
        normal_data = np.random.multivariate_normal([0, 0], [[1, 0.5], [0.5, 1]], 100)

        anomalies_points = np.array([[10, 10], [-10, -10]])
        _data = np.vstack([normal_data, anomalies_points])

        df = pd.DataFrame(data, columns=["feature1", "feature2"])

        detected = detector.detect_multivariate_anomalies(df, method="mahalanobis")

        assert isinstance(detected, list)
        assert len(detected) >= 2

    def test_calculate_zscore(self, detector):
        """测试Z-score计算"""
        _data = [1, 2, 3, 4, 5, 100]
        zscores = detector._calculate_zscore(data)

        assert len(zscores) == len(data)
        assert zscores[-1] > 3  # 异常阈值

    def test_calculate_iqr_bounds(self, detector):
        """测试IQR边界计算"""
        _data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100]
        bounds = detector._calculate_iqr_bounds(data)

        assert "lower_bound" in bounds
        assert "upper_bound" in bounds
        assert bounds["upper_bound"] < 100  # 100应该在范围外

    def test_detect_categorical_anomalies(self, detector):
        """测试分类变量异常检测"""
        df = pd.DataFrame(
            {
                "league": [
                    "Premier League",
                    "La Liga",
                    "Serie A",
                    "Premier League",
                    "La Liga",
                    "Premier League",
                    "Unknown League",
                ],  # Unknown League是异常
                "season": [
                    "2023-24",
                    "2023-24",
                    "2023-24",
                    "2023-24",
                    "2023-24",
                    "2023-24",
                    "2030-31",
                ],  # 2030-31是异常
            }
        )

        anomalies = detector.detect_categorical_anomalies(
            df, columns=["league", "season"], min_frequency=2
        )

        assert isinstance(anomalies, dict)
        assert "league" in anomalies
        assert "season" in anomalies
        assert "Unknown League" in str(anomalies["league"])

    def test_detect_null_anomalies(self, detector):
        """测试空值异常检测"""
        df = pd.DataFrame(
            {
                "match_id": [1, 2, None, 4, 5],
                "score": ["2-1", None, "1-1", "3-0", None],
                "attendance": [50000, 45000, 48000, None, 52000],
            }
        )

        null_anomalies = detector.detect_null_anomalies(df)

        assert isinstance(null_anomalies, dict)
        assert null_anomalies["match_id"]["count"] == 1
        assert null_anomalies["score"]["count"] == 2
        assert null_anomalies["attendance"]["count"] == 1

    def test_detect_duplicate_anomalies(self, detector):
        """测试重复值异常检测"""
        df = pd.DataFrame(
            {
                "match_id": [1, 2, 3, 1, 4, 2],  # 1和2重复
                "data": ["a", "b", "c", "a", "d", "b"],
            }
        )

        duplicates = detector.detect_duplicate_anomalies(df, subset=["match_id"])

        assert isinstance(duplicates, pd.DataFrame)
        assert len(duplicates) == 4  # 2个重复值 × 2次出现

    @pytest.mark.asyncio
    async def test_batch_anomaly_detection(self, detector, sample_data):
        """测试批量异常检测"""
        results = await detector.batch_detect_anomalies(
            sample_data, methods=["zscore", "iqr", "isolation_forest"]
        )

        assert isinstance(results, dict)
        assert "zscore" in results
        assert "iqr" in results
        assert "isolation_forest" in results

    @pytest.mark.asyncio
    async def test_real_time_anomaly_detection(self, detector):
        """测试实时异常检测"""
        normal_data = {"value": 10, "timestamp": datetime.now()}
        anomaly_data = {"value": 1000, "timestamp": datetime.now()}

        detector.initialize_real_time_detection(window_size=100)

        for _ in range(100):
            _data = {"value": np.random.normal(10, 2), "timestamp": datetime.now()}
            detector.update_real_time_data(data)

        normal_result = detector.detect_real_time_anomaly(normal_data)
        assert normal_result["is_anomaly"] is False

        anomaly_result = detector.detect_real_time_anomaly(anomaly_data)
        assert anomaly_result["is_anomaly"] is True

    def test_calculate_anomaly_score(self, detector):
        """测试异常评分计算"""
        score = detector.calculate_anomaly_score(
            value=100, mean=50, std=10, method="statistical"
        )
        assert score > 3  # Z-score > 3

        score = detector.calculate_anomaly_score(
            value=10, centroid=0, threshold=5, method="distance"
        )
        assert score > 1

    def test_visualize_anomalies(self, detector, sample_data):
        """测试异常可视化"""
        anomalies = [{"index": 5, "value": 50, "column": "home_goals"}]

        detector.visualize_anomalies(
            _data =sample_data,
            anomalies=anomalies,
            column="home_goals",
            save_path="/tmp/anomaly_plot.png",
        )

        assert hasattr(detector, "visualize_anomalies")

    def test_export_anomaly_report(self, detector, sample_data):
        """测试导出异常报告"""
        anomalies = [
            {"type": "statistical", "index": 5, "column": "home_goals", "score": 5.2},
            {"type": "iqr", "index": 5, "column": "shots", "value": 100},
        ]

        report = detector.generate_anomaly_report(
            _data =sample_data, anomalies=anomalies, include_summary=True
        )

        assert isinstance(report, dict)
        assert "summary" in report
        assert "anomalies" in report
        assert report["summary"]["total_anomalies"] == 2

    @pytest.mark.asyncio
    async def test_anomaly_notification(self, detector):
        """测试异常通知"""
        mock_notifier = MagicMock()
        mock_notifier.send.return_value = True
        detector.add_notifier(mock_notifier)

        anomaly = {
            "type": "critical",
            "description": "Extreme outlier detected",
            "severity": "high",
        }

        _result = await detector.notify_anomaly(anomaly)
        assert result is True
        mock_notifier.send.assert_called_once()

    def test_anomaly_types(self):
        """测试异常类型枚举"""
        assert AnomalyType.STATISTICAL.value == "statistical"
        assert AnomalyType.TEMPORAL.value == "temporal"
        assert AnomalyType.CATEGORICAL.value == "categorical"
        assert AnomalyType.MULTIVARIATE.value == "multivariate"

    def test_threshold_adaptation(self, detector):
        """测试阈值自适应"""
        initial_threshold = detector.threshold

        detector.adapt_threshold(new_data=[1, 2, 3, 1000], method="percentile")

        assert detector.threshold != initial_threshold

    def test_custom_anomaly_detector(self, detector):
        """测试自定义异常检测器"""

        def custom_detector(data):
            anomalies = []
            for idx, row in data.iterrows():
                if row["value"] < 0:
                    anomalies.append({"index": idx, "value": row["value"]})
            return anomalies

        detector.register_custom_detector("negative_values", custom_detector)

        test_data = pd.DataFrame({"value": [1, 2, -5, 3, -1, 4]})

        results = detector.detect_anomalies(test_data, method="negative_values")

        assert len(results) == 2  # 检测到2个负值

    @pytest.mark.asyncio
    async def test_anomaly_pattern_learning(self, detector):
        """测试异常模式学习"""
        historical_anomalies = [
            {"timestamp": datetime(2025, 1, 1, 10, 0), "pattern": "morning_spike"},
            {"timestamp": datetime(2025, 1, 2, 10, 0), "pattern": "morning_spike"},
            {"timestamp": datetime(2025, 1, 1, 15, 0), "pattern": "afternoon_dip"},
            {"timestamp": datetime(2025, 1, 2, 15, 0), "pattern": "afternoon_dip"},
        ]

        patterns = detector.learn_anomaly_patterns(historical_anomalies)

        assert isinstance(patterns, dict)
        assert "morning_spike" in patterns
        assert "afternoon_dip" in patterns

        current_time = datetime(2025, 1, 3, 10, 0)
        _prediction = detector.predict_anomaly_probability(current_time, patterns)
        assert prediction > 0.5  # 上午10点异常概率高
