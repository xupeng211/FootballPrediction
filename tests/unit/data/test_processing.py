"""
数据处理测试
Data Processing Tests

测试数据处理和质量监控系统的核心功能。
Tests core functionality of data processing and quality monitoring system.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from src.data.processing import FootballDataCleaner, MissingDataHandler
from src.data.processing.data_preprocessor import DataPreprocessor
from src.data.quality.anomaly_detector import AdvancedAnomalyDetector
from src.data.quality.data_quality_monitor import DataQualityMonitor


class TestFootballDataCleaner:
    """足球数据清洗器测试类"""

    @pytest.fixture
    def cleaner(self):
        """数据清洗器实例"""
        return FootballDataCleaner()

    @pytest.fixture
    def sample_raw_data(self):
        """示例原始数据"""
        return pd.DataFrame(
            {
                "match_id": [1, 2, 3, 4, 5, 6],
                "home_team": [
                    "Team A",
                    "Team B",
                    "Team A",
                    "Team C",
                    "Team B",
                    "Team D",
                ],
                "away_team": [
                    "Team B",
                    "Team A",
                    "Team C",
                    "Team B",
                    "Team A",
                    "Team C",
                ],
                "home_score": [2, 1, 3, 0, 2, 1],
                "away_score": [1, 2, 0, 1, 2, 3],
                "date": [
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-03",
                    "2024-01-04",
                    "2024-01-05",
                    "2024-01-06",
                ],
                "league": ["PL", "PL", "PL", "PL", "PL", "PL"],
            }
        )

    @pytest.fixture
    def dirty_data(self):
        """包含问题的脏数据"""
        return pd.DataFrame(
            {
                "match_id": [1, 2, 3, 4, 5, 6, 7, 8],
                "home_team": [
                    "Team A",
                    "Team B",
                    "Team A",
                    "Team C",
                    "Team B",
                    "Team D",
                    "Team A",
                    "Team E",
                ],
                "away_team": [
                    "Team B",
                    "Team A",
                    "Team C",
                    "Team B",
                    "Team A",
                    "Team C",
                    "Team B",
                    "Team F",
                ],
                "home_score": [2, 1, 3, 0, 2, 1, -5, 100],  # 异常值：-5, 100
                "away_score": [1, 2, 0, 1, 2, 3, -1, 50],  # 异常值：-1, 50
                "date": [
                    "2024-01-01",
                    "invalid_date",
                    "2024-01-03",
                    "2024-01-04",
                    "2024-01-05",
                    "2024-01-06",
                    "2024-01-07",
                    "2024-01-08",
                ],
                "league": ["PL", "PL", "PL", "PL", "PL", "PL", None, "PL"],  # 缺失值
            }
        )

    def test_cleaner_initialization(self, cleaner):
        """测试清洗器初始化"""
        assert cleaner is not None
        assert hasattr(cleaner, "logger")
        assert hasattr(cleaner, "cleaning_rules")
        assert hasattr(cleaner, "statistics")

    def test_remove_duplicates(self, cleaner):
        """测试移除重复数据"""
        data_with_duplicates = pd.DataFrame(
            {
                "match_id": [1, 1, 2, 3, 3, 4],
                "home_team": ["A", "A", "B", "C", "C", "D"],
                "away_team": ["B", "B", "A", "D", "D", "E"],
                "score": [1, 1, 2, 0, 0, 3],
            }
        )

        cleaned_data = cleaner.remove_duplicates(data_with_duplicates)

        assert len(cleaned_data) == 3  # 应该只有3条唯一记录
        assert list(cleaned_data["match_id"]) == [1, 2, 3, 4]

    def test_detect_outliers_iqr(self, cleaner):
        """测试使用IQR方法检测异常值"""
        scores = [1, 2, 2, 3, 3, 3, 4, 4, 100]  # 100是异常值
        outliers = cleaner.detect_outliers_iqr(scores)

        assert len(outliers) > 0
        assert 100 in outliers

    def test_detect_outliers_zscore(self, cleaner):
        """测试使用Z-score方法检测异常值"""
        scores = [10, 12, 11, 13, 12, 14, 13, 50]  # 50是异常值
        outliers = cleaner.detect_outliers_zscore(scores, threshold=2.0)

        assert len(outliers) > 0
        assert 50 in outliers

    def test_clean_numeric_data(self, cleaner, dirty_data):
        """测试清洗数值数据"""
        cleaned_data = cleaner.clean_numeric_data(
            dirty_data, ["home_score", "away_score"]
        )

        # 验证异常值被处理（可能被移除或替换）
        assert not cleaned_data["home_score"].isin([-5, 100]).any()
        assert not cleaned_data["away_score"].isin([-1, 50]).any()

    def test_clean_text_data(self, cleaner):
        """测试清洗文本数据"""
        dirty_text = pd.DataFrame(
            {
                "team_name": [
                    "  Team A  ",
                    "TEAM B",
                    "team c",
                    "Team-D",
                    "Team_E_F.C.",
                ],
                "league": [
                    "pl",
                    "Premier League",
                    "premier league",
                    "EPL",
                    "English Premier League",
                ],
            }
        )

        cleaned_text = cleaner.clean_text_data(dirty_text)

        # 验证文本标准化
        assert cleaned_text["team_name"].iloc[0] == "Team A"
        assert cleaned_text["team_name"].iloc[1] == "Team B"
        assert cleaned_text["team_name"].iloc[2] == "Team C"

    def test_validate_date_format(self, cleaner):
        """测试日期格式验证"""
        valid_dates = ["2024-01-01", "2024/01/01", "01-01-2024"]
        invalid_dates = ["invalid_date", "2024-13-01", "2024-01-32"]

        for date_str in valid_dates:
            result = cleaner.validate_date_format(date_str)
            assert result is not None

        for date_str in invalid_dates:
            result = cleaner.validate_date_format(date_str)
            assert result is None

    def test_clean_date_data(self, cleaner, dirty_data):
        """测试清洗日期数据"""
        cleaned_data = cleaner.clean_date_data(dirty_data, "date")

        # 验证无效日期被处理
        valid_dates = cleaned_data["date"].dropna()
        assert len(valid_dates) > 0

        # 验证日期格式一致性
        for date_val in valid_dates:
            if pd.notna(date_val):
                assert isinstance(date_val, (pd.Timestamp, datetime))

    def test_generate_cleaning_report(self, cleaner, dirty_data):
        """测试生成清洗报告"""
        cleaned_data = cleaner.clean_data(dirty_data)
        report = cleaner.generate_cleaning_report(dirty_data, cleaned_data)

        assert "original_rows" in report
        assert "cleaned_rows" in report
        assert "duplicates_removed" in report
        assert "outliers_detected" in report
        assert "missing_values_handled" in report

        assert report["original_rows"] >= report["cleaned_rows"]


class TestMissingDataHandler:
    """缺失数据处理器测试类"""

    @pytest.fixture
    def handler(self):
        """缺失数据处理器实例"""
        return MissingDataHandler()

    @pytest.fixture
    def data_with_missing(self):
        """包含缺失值的数据"""
        return pd.DataFrame(
            {
                "match_id": [1, 2, 3, 4, 5, 6, 7, 8],
                "home_score": [2, 1, None, 0, 2, 1, 3, None],
                "away_score": [1, None, 0, 1, 2, 3, None, 2],
                "possession": [55, 48, None, 52, 60, None, 45, 50],
                "shots": [10, None, 8, 12, 15, 9, None, 11],
                "date": [
                    "2024-01-01",
                    "2024-01-02",
                    None,
                    "2024-01-04",
                    None,
                    "2024-01-06",
                    "2024-01-07",
                    "2024-01-08",
                ],
            }
        )

    def test_handler_initialization(self, handler):
        """测试处理器初始化"""
        assert handler is not None
        assert hasattr(handler, "strategies")
        assert hasattr(handler, "thresholds")

    def test_analyze_missing_patterns(self, handler, data_with_missing):
        """测试分析缺失模式"""
        patterns = handler.analyze_missing_patterns(data_with_missing)

        assert "total_missing" in patterns
        assert "missing_by_column" in patterns
        assert "missing_percentage" in patterns
        assert "missing_patterns" in patterns

        # 验证缺失统计
        assert patterns["total_missing"] > 0
        assert len(patterns["missing_by_column"]) > 0

    def test_detect_missing_mechanism(self, handler, data_with_missing):
        """测试检测缺失机制"""
        mechanism = handler.detect_missing_mechanism(data_with_missing, "home_score")

        assert mechanism in ["MCAR", "MAR", "MNAR", "UNKNOWN"]

    def test_mean_imputation(self, handler, data_with_missing):
        """测试均值插补"""
        imputed_data = handler.mean_imputation(
            data_with_missing.copy(), ["home_score", "away_score"]
        )

        # 验证缺失值被插补
        assert imputed_data["home_score"].isna().sum() == 0
        assert imputed_data["away_score"].isna().sum() == 0

        # 验证插补值合理性
        mean_home = data_with_missing["home_score"].mean()
        assert any(
            abs(val - mean_home) < 0.001
            for val in imputed_data["home_score"]
            if pd.notna(val)
        )

    def test_median_imputation(self, handler, data_with_missing):
        """测试中位数插补"""
        imputed_data = handler.median_imputation(
            data_with_missing.copy(), ["possession"]
        )

        # 验证缺失值被插补
        assert imputed_data["possession"].isna().sum() == 0

        # 验证插补值是中位数
        median_possession = data_with_missing["possession"].median()
        assert any(
            abs(val - median_possession) < 0.001 for val in imputed_data["possession"]
        )

    def test_mode_imputation(self, handler, data_with_missing):
        """测试众数插补"""
        # 添加分类数据进行众数插补测试
        test_data = data_with_missing.copy()
        test_data["weather"] = [
            "sunny",
            "rainy",
            None,
            "sunny",
            "cloudy",
            "sunny",
            None,
            "rainy",
        ]

        imputed_data = handler.mode_imputation(test_data, ["weather"])

        # 验证缺失值被插补
        assert imputed_data["weather"].isna().sum() == 0

    def test_forward_fill(self, handler, data_with_missing):
        """测试前向填充"""
        imputed_data = handler.forward_fill(data_with_missing.copy(), ["home_score"])

        # 验证前向填充效果
        original_missing = data_with_missing["home_score"].isna().sum()
        imputed_missing = imputed_data["home_score"].isna().sum()
        assert imputed_missing <= original_missing

    def test_backward_fill(self, handler, data_with_missing):
        """测试后向填充"""
        imputed_data = handler.backward_fill(data_with_missing.copy(), ["away_score"])

        # 验证后向填充效果
        original_missing = data_with_missing["away_score"].isna().sum()
        imputed_missing = imputed_data["away_score"].isna().sum()
        assert imputed_missing <= original_missing

    def test_interpolation_imputation(self, handler, data_with_missing):
        """测试插值法"""
        imputed_data = handler.interpolation_imputation(
            data_with_missing.copy(), ["shots"]
        )

        # 验证插值效果
        original_missing = data_with_missing["shots"].isna().sum()
        imputed_missing = imputed_data["shots"].isna().sum()
        assert imputed_missing <= original_missing

    def test_auto_imputation_strategy(self, handler, data_with_missing):
        """测试自动选择插补策略"""
        strategy = handler.select_auto_strategy(data_with_missing, "home_score")

        assert strategy in ["mean", "median", "mode", "interpolation", "drop"]

    def test_validate_imputation_quality(self, handler, data_with_missing):
        """测试验证插补质量"""
        imputed_data = handler.auto_impute(data_with_missing.copy())
        quality_report = handler.validate_imputation_quality(
            data_with_missing, imputed_data
        )

        assert "original_shape" in quality_report
        assert "imputed_shape" in quality_report
        assert "imputation_methods" in quality_report
        assert "quality_score" in quality_report

        assert 0 <= quality_report["quality_score"] <= 1

    def test_handle_high_missing_columns(self, handler):
        """测试处理高缺失率列"""
        high_missing_data = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5],
                "good_column": [1, 2, 3, 4, 5],
                "bad_column": [1, None, None, None, None],  # 80%缺失
                "very_bad_column": [None, None, None, None, None],  # 100%缺失
            }
        )

        processed_data = handler.handle_high_missing_columns(
            high_missing_data, threshold=0.5
        )

        # 高缺失率列应该被移除
        assert "very_bad_column" not in processed_data.columns
        assert "bad_column" not in processed_data.columns
        assert "good_column" in processed_data.columns


class TestDataPreprocessor:
    """数据预处理器测试类"""

    @pytest.fixture
    def preprocessor(self):
        """数据预处理器实例"""
        return DataPreprocessor()

    @pytest.fixture
    def raw_data(self):
        """原始数据"""
        return pd.DataFrame(
            {
                "match_id": [1, 2, 3, 4, 5, 6, 7, 8],
                "home_team": [
                    "Team A",
                    "Team B",
                    "Team A",
                    "Team C",
                    "Team B",
                    "Team D",
                    "Team A",
                    "Team E",
                ],
                "away_team": [
                    "Team B",
                    "Team A",
                    "Team C",
                    "Team B",
                    "Team A",
                    "Team C",
                    "Team B",
                    "Team F",
                ],
                "home_score": [2, 1, None, 0, 2, 1, -5, 100],
                "away_score": [1, None, 0, 1, 2, 3, -1, 50],
                "date": [
                    "2024-01-01",
                    "invalid_date",
                    "2024-01-03",
                    "2024-01-04",
                    "2024-01-05",
                    "2024-01-06",
                    "2024-01-07",
                    "2024-01-08",
                ],
                "league": ["PL", "PL", "PL", "PL", "PL", "PL", None, "PL"],
                "possession": [55, 48, None, 52, 60, None, 45, 50],
            }
        )

    def test_preprocessor_initialization(self, preprocessor):
        """测试预处理器初始化"""
        assert preprocessor is not None
        assert hasattr(preprocessor, "cleaner")
        assert hasattr(preprocessor, "missing_handler")
        assert hasattr(preprocessor, "processing_history")

    def test_preprocessing_pipeline(self, preprocessor, raw_data):
        """测试完整预处理流水线"""
        processed_data, report = preprocessor.process(raw_data)

        # 验证处理结果
        assert isinstance(processed_data, pd.DataFrame)
        assert len(processed_data) > 0

        # 验证处理报告
        assert "initial_shape" in report
        assert "final_shape" in report
        assert "cleaning_steps" in report
        assert "missing_data_steps" in report
        assert "data_quality_score" in report

    def test_step_by_step_processing(self, preprocessor, raw_data):
        """测试分步处理"""
        # 第一步：数据清洗
        cleaned_data = preprocessor.clean_data(raw_data)
        assert isinstance(cleaned_data, pd.DataFrame)

        # 第二步：缺失值处理
        imputed_data = preprocessor.handle_missing_data(cleaned_data)
        assert isinstance(imputed_data, pd.DataFrame)

        # 第三步：数据验证
        validated_data = preprocessor.validate_data(imputed_data)
        assert isinstance(validated_data, pd.DataFrame)

    def test_data_quality_assessment(self, preprocessor, raw_data):
        """测试数据质量评估"""
        quality_score = preprocessor.assess_data_quality(raw_data)

        assert isinstance(quality_score, dict)
        assert "overall_score" in quality_score
        assert "completeness" in quality_score
        assert "consistency" in quality_score
        assert "validity" in quality_score

        assert 0 <= quality_score["overall_score"] <= 1

    def test_feature_engineering(self, preprocessor, raw_data):
        """测试特征工程"""
        processed_data, _ = preprocessor.process(raw_data)
        engineered_data = preprocessor.engineer_features(processed_data)

        # 验证新特征被创建
        assert len(engineered_data.columns) >= len(processed_data.columns)

        # 可能的新特征
        potential_features = [
            "goal_difference",
            "total_goals",
            "home_win",
            "away_win",
            "draw",
        ]
        for feature in potential_features:
            if feature in engineered_data.columns:
                assert len(engineered_data[feature]) > 0

    def test_data_transformation(self, preprocessor, raw_data):
        """测试数据转换"""
        processed_data, _ = preprocessor.process(raw_data)
        transformed_data = preprocessor.transform_data(processed_data)

        # 验证转换后的数据
        assert isinstance(transformed_data, pd.DataFrame)
        assert len(transformed_data) > 0

    def test_processing_history_tracking(self, preprocessor, raw_data):
        """测试处理历史追踪"""
        processed_data, report = preprocessor.process(raw_data)

        # 验证处理历史被记录
        assert len(preprocessor.processing_history) > 0

        latest_history = preprocessor.processing_history[-1]
        assert "timestamp" in latest_history
        assert "steps" in latest_history
        assert "input_shape" in latest_history
        assert "output_shape" in latest_history


class TestDataQualityMonitor:
    """数据质量监控器测试类"""

    @pytest.fixture
    def monitor(self):
        """数据质量监控器实例"""
        return DataQualityMonitor()

    @pytest.fixture
    def sample_data(self):
        """示例数据"""
        return pd.DataFrame(
            {
                "match_id": [1, 2, 3, 4, 5],
                "home_score": [2, 1, 3, 0, 2],
                "away_score": [1, 2, 0, 1, 2],
                "date": pd.date_range("2024-01-01", periods=5),
                "possession": [55.2, 48.5, 62.1, 51.0, 58.3],
                "shots": [12, 8, 15, 9, 11],
            }
        )

    def test_monitor_initialization(self, monitor):
        """测试监控器初始化"""
        assert monitor is not None
        assert hasattr(monitor, "quality_rules")
        assert hasattr(monitor, "metrics_history")
        assert hasattr(monitor, "alerts")

    def test_check_completeness(self, monitor, sample_data):
        """测试完整性检查"""
        completeness_score = monitor.check_completeness(sample_data)

        assert isinstance(completeness_score, dict)
        assert "overall_completeness" in completeness_score
        assert "column_completeness" in completeness_score
        assert 0 <= completeness_score["overall_completeness"] <= 1

    def test_check_validity(self, monitor, sample_data):
        """测试有效性检查"""
        validity_score = monitor.check_validity(sample_data)

        assert isinstance(validity_score, dict)
        assert "overall_validity" in validity_score
        assert "column_validity" in validity_score
        assert 0 <= validity_score["overall_validity"] <= 1

    def test_check_consistency(self, monitor, sample_data):
        """测试一致性检查"""
        consistency_score = monitor.check_consistency(sample_data)

        assert isinstance(consistency_score, dict)
        assert "overall_consistency" in consistency_score
        assert "consistency_issues" in consistency_score

    def test_check_freshness(self, monitor, sample_data):
        """测试新鲜度检查"""
        freshness_score = monitor.check_freshness(sample_data, "date", max_age_hours=24)

        assert isinstance(freshness_score, dict)
        assert "freshness_score" in freshness_score
        assert "oldest_record" in freshness_score
        assert "stale_records" in freshness_score

    def test_generate_quality_report(self, monitor, sample_data):
        """测试生成质量报告"""
        report = monitor.generate_quality_report(sample_data)

        assert isinstance(report, dict)
        assert "overall_score" in report
        assert "completeness" in report
        assert "validity" in report
        assert "consistency" in report
        assert "freshness" in report
        assert "recommendations" in report

    def test_detect_quality_issues(self, monitor, sample_data):
        """测试检测质量问题"""
        # 添加一些质量问题
        problematic_data = sample_data.copy()
        problematic_data.loc[0, "home_score"] = -5  # 负分数
        problematic_data.loc[1, "away_score"] = None  # 缺失值
        problematic_data.loc[2, "possession"] = 150  # 超出范围

        issues = monitor.detect_quality_issues(problematic_data)

        assert isinstance(issues, list)
        assert len(issues) > 0

        for issue in issues:
            assert "type" in issue
            assert "severity" in issue
            assert "description" in issue
            assert "affected_rows" in issue

    def test_monitor_data_drift(self, monitor):
        """测试数据漂移监控"""
        # 基准数据
        baseline_data = pd.DataFrame(
            {"score": [1, 2, 3, 4, 5], "possession": [50, 55, 60, 52, 58]}
        )

        # 新数据（有轻微漂移）
        new_data = pd.DataFrame(
            {"score": [2, 3, 4, 5, 6], "possession": [52, 57, 62, 54, 60]}
        )

        drift_report = monitor.monitor_data_drift(baseline_data, new_data)

        assert isinstance(drift_report, dict)
        assert "overall_drift_score" in drift_report
        assert "feature_drift" in drift_report
        assert "drift_detected" in drift_report


class TestAdvancedAnomalyDetector:
    """高级异常检测器测试类"""

    @pytest.fixture
    def detector(self):
        """异常检测器实例"""
        return AdvancedAnomalyDetector()

    @pytest.fixture
    def normal_data(self):
        """正常数据"""
        np.random.seed(42)
        return pd.DataFrame(
            {
                "home_score": np.random.normal(1.5, 0.8, 100),
                "away_score": np.random.normal(1.2, 0.6, 100),
                "possession": np.random.normal(52, 8, 100),
                "shots": np.random.normal(12, 3, 100),
            }
        )

    @pytest.fixture
    def data_with_anomalies(self):
        """包含异常值的数据"""
        np.random.seed(42)
        normal_data = np.random.normal(1.5, 0.8, 95)
        anomalies = [10, -5, 15, -8]  # 明显的异常值

        scores = np.concatenate([normal_data, anomalies])
        np.random.shuffle(scores)

        return pd.DataFrame(
            {
                "home_score": scores,
                "away_score": np.random.normal(1.2, 0.6, 100),
                "possession": np.random.normal(52, 8, 100),
                "shots": np.random.normal(12, 3, 100),
            }
        )

    def test_detector_initialization(self, detector):
        """测试检测器初始化"""
        assert detector is not None
        assert hasattr(detector, "methods")
        assert hasattr(detector, "thresholds")
        assert hasattr(detector, "anomaly_history")

    def test_statistical_anomaly_detection(self, detector, data_with_anomalies):
        """测试统计异常检测"""
        anomalies = detector.detect_statistical_anomalies(
            data_with_anomalies["home_score"], method="iqr"
        )

        assert isinstance(anomalies, list)
        assert len(anomalies) > 0

        # 验证异常值确实异常
        for idx in anomalies:
            value = data_with_anomalies.iloc[idx]["home_score"]
            assert (
                abs(value - data_with_anomalies["home_score"].mean())
                > 2 * data_with_anomalies["home_score"].std()
            )

    def test_zscore_anomaly_detection(self, detector, data_with_anomalies):
        """测试Z-score异常检测"""
        anomalies = detector.detect_statistical_anomalies(
            data_with_anomalies["home_score"], method="zscore", threshold=2.0
        )

        assert isinstance(anomalies, list)
        assert len(anomalies) > 0

    def test_isolation_forest_anomaly_detection(self, detector, data_with_anomalies):
        """测试Isolation Forest异常检测"""
        anomaly_scores = detector.detect_isolation_forest_anomalies(data_with_anomalies)

        assert isinstance(anomaly_scores, np.ndarray)
        assert len(anomaly_scores) == len(data_with_anomalies)

        # 验证异常分数范围
        assert all(-1 <= score <= 1 for score in anomaly_scores)

    def test_local_outlier_factor_detection(self, detector, data_with_anomalies):
        """测试LOF异常检测"""
        anomaly_scores = detector.detect_lof_anomalies(data_with_anomalies)

        assert isinstance(anomaly_scores, np.ndarray)
        assert len(anomaly_scores) == len(data_with_anomalies)

    def test_multivariate_anomaly_detection(self, detector, data_with_anomalies):
        """测试多元异常检测"""
        anomalies = detector.detect_multivariate_anomalies(data_with_anomalies)

        assert isinstance(anomalies, list)
        assert len(anomalies) >= 0

    def test_time_series_anomaly_detection(self, detector):
        """测试时间序列异常检测"""
        # 创建时间序列数据
        dates = pd.date_range("2024-01-01", periods=100)
        normal_values = np.random.normal(50, 5, 95)
        anomaly_values = [100, 0, 120, -10]
        values = np.concatenate([normal_values, anomaly_values])

        time_series_data = pd.DataFrame({"date": dates, "value": values})

        anomalies = detector.detect_time_series_anomalies(
            time_series_data, date_column="date", value_column="value"
        )

        assert isinstance(anomalies, list)

    def test_anomaly_explanation(self, detector, data_with_anomalies):
        """测试异常解释"""
        anomalies = detector.detect_statistical_anomalies(
            data_with_anomalies["home_score"]
        )

        if anomalies:
            explanation = detector.explain_anomaly(
                data_with_anomalies.iloc[anomalies[0]], data_with_anomalies
            )

            assert isinstance(explanation, dict)
            assert "anomaly_score" in explanation
            assert "contributing_features" in explanation
            assert "explanation" in explanation

    def test_batch_anomaly_detection(self, detector, data_with_anomalies):
        """测试批量异常检测"""
        detection_report = detector.detect_anomalies_batch(data_with_anomalies)

        assert isinstance(detection_report, dict)
        assert "total_anomalies" in detection_report
        assert "anomaly_indices" in detection_report
        assert "anomaly_scores" in detection_report
        assert "detection_method" in detection_report

    def test_anomaly_threshold_tuning(self, detector, normal_data):
        """测试异常阈值调优"""
        optimal_threshold = detector.tune_anomaly_threshold(normal_data)

        assert isinstance(optimal_threshold, float)
        assert optimal_threshold > 0

    def test_anomaly_detection_performance(self, detector, data_with_anomalies):
        """测试异常检测性能"""
        import time

        start_time = time.time()
        anomalies = detector.detect_statistical_anomalies(
            data_with_anomalies["home_score"]
        )
        end_time = time.time()

        # 验证性能
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成
        assert isinstance(anomalies, list)


class TestDataProcessingIntegration:
    """数据处理集成测试类"""

    def test_end_to_end_processing_pipeline(self):
        """测试端到端处理流水线"""
        # 创建包含各种问题的原始数据
        raw_data = pd.DataFrame(
            {
                "match_id": [1, 1, 2, 3, 4, 5, 6, 7, 8, 9],  # 包含重复
                "home_team": [
                    "Team A",
                    "Team A",
                    "Team B",
                    "Team C",
                    "Team D",
                    "Team E",
                    "Team F",
                    "Team G",
                    "Team H",
                    "Team I",
                ],
                "away_team": [
                    "Team B",
                    "Team B",
                    "Team A",
                    "Team D",
                    "Team C",
                    "Team F",
                    "Team E",
                    "Team J",
                    "Team K",
                    "Team L",
                ],
                "home_score": [2, 2, 1, None, 0, 2, 1, -5, 100, 3],  # 包含缺失和异常值
                "away_score": [1, 1, None, 0, 1, 2, 3, -1, 50, 1],  # 包含缺失和异常值
                "date": [
                    "2024-01-01",
                    "2024-01-01",
                    "invalid_date",
                    "2024-01-03",
                    None,
                    "2024-01-05",
                    "2024-01-06",
                    "2024-01-07",
                    "2024-01-08",
                    "2024-01-09",
                ],
                "league": ["PL", "PL", "PL", "PL", None, "PL", "PL", "PL", "PL", "PL"],
                "possession": [55, 55, 48, None, 52, 60, None, 45, 50, 58],
            }
        )

        # 执行完整处理流程
        preprocessor = DataPreprocessor()
        processed_data, processing_report = preprocessor.process(raw_data)

        # 质量监控
        monitor = DataQualityMonitor()
        quality_report = monitor.generate_quality_report(processed_data)

        # 异常检测
        detector = AdvancedAnomalyDetector()
        detector.detect_anomalies_batch(processed_data)

        # 验证最终结果
        assert isinstance(processed_data, pd.DataFrame)
        assert len(processed_data) > 0
        assert len(processed_data) < len(raw_data)  # 应该有数据被清理

        # 验证质量报告
        assert quality_report["overall_score"] > 0.5  # 质量应该显著提升

        # 验证处理报告
        assert processing_report["data_quality_score"] > 0.5

    def test_processing_performance_benchmark(self):
        """测试处理性能基准"""
        # 创建大数据集
        np.random.seed(42)
        large_dataset = pd.DataFrame(
            {
                "match_id": range(10000),
                "home_score": np.random.normal(1.5, 0.8, 10000),
                "away_score": np.random.normal(1.2, 0.6, 10000),
                "possession": np.random.normal(52, 8, 10000),
                "shots": np.random.normal(12, 3, 10000),
            }
        )

        # 添加一些问题数据
        large_dataset.loc[100:200, "home_score"] = None
        large_dataset.loc[300:350, "away_score"] = -10  # 异常值

        import time

        start_time = time.time()

        preprocessor = DataPreprocessor()
        processed_data, _ = preprocessor.process(large_dataset)

        end_time = time.time()
        processing_time = end_time - start_time

        # 性能验证
        assert processing_time < 10.0  # 应该在10秒内处理完10000条记录
        assert len(processed_data) > 9000  # 大部分数据应该被保留

    def test_real_time_processing_simulation(self):
        """测试实时处理模拟"""
        # 模拟实时数据流
        preprocessor = DataPreprocessor()
        monitor = DataQualityMonitor()

        processing_times = []
        quality_scores = []

        for i in range(10):
            # 模拟新批次数据
            batch_data = pd.DataFrame(
                {
                    "match_id": range(i * 100, (i + 1) * 100),
                    "home_score": np.random.normal(1.5, 0.8, 100),
                    "away_score": np.random.normal(1.2, 0.6, 100),
                    "timestamp": [datetime.now() for _ in range(100)],
                }
            )

            # 添加一些问题
            if i % 3 == 0:
                batch_data.loc[i * 10, "home_score"] = None

            import time

            start_time = time.time()

            processed_batch, _ = preprocessor.process(batch_data)
            quality_score = monitor.assess_data_quality(processed_batch)

            end_time = time.time()
            processing_times.append(end_time - start_time)
            quality_scores.append(quality_score["overall_score"])

        # 验证实时处理性能
        assert np.mean(processing_times) < 1.0  # 平均处理时间应该小于1秒
        assert np.mean(quality_scores) > 0.8  # 质量分数应该较高
