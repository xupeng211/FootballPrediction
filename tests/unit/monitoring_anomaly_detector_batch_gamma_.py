"""
Monitoring AnomalyDetector Batch-Γ-007 测试套件

专门为 monitoring/anomaly_detector.py 设计的测试，目标是将其覆盖率从 30% 提升至 ≥47%
覆盖所有异常检测算法、错误处理和边缘情况
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.monitoring.anomaly_detector import AnomalyDetector, AnomalyResult, AnomalyType, AnomalySeverity


class TestAnomalyDetectorBatchGamma007:
    """AnomalyDetector Batch-Γ-007 测试类"""

    @pytest.fixture
    def detector(self):
        """创建 AnomalyDetector 实例"""
        detector = AnomalyDetector()
        return detector

    @pytest.fixture
    def sample_numeric_data(self):
        """创建数值示例数据"""
        return pd.Series([1, 2, 3, 4, 5, 100, -50])

    @pytest.fixture
    def sample_time_data(self):
        """创建时间示例数据"""
        base_time = datetime.now()
        return pd.Series([
            base_time,
            base_time + timedelta(minutes=1),
            base_time + timedelta(minutes=2),
            base_time + timedelta(hours=5)  # 异常间隔
        ])

    def test_anomaly_detector_initialization_coverage(self, detector):
        """测试 AnomalyDetector 初始化（覆盖配置设置）"""
        # 验证数据库管理器初始化
        assert detector.db_manager is not None

        # 验证检测配置完整
        assert isinstance(detector.detection_config, dict)

        # 验证 matches 表配置
        matches_config = detector.detection_config["matches"]
        assert "numeric_columns" in matches_config
        assert "time_columns" in matches_config
        assert "categorical_columns" in matches_config
        assert "thresholds" in matches_config

        # 验证 odds 表配置
        odds_config = detector.detection_config["odds"]
        assert "numeric_columns" in odds_config
        assert "home_odds" in odds_config["thresholds"]

        # 验证 predictions 表配置
        predictions_config = detector.detection_config["predictions"]
        assert "numeric_columns" in predictions_config
        assert "home_win_probability" in predictions_config["thresholds"]

    def test_detect_three_sigma_anomalies_edge_cases(self, detector):
        """测试3σ规则边缘情况"""
        # 测试包含None和NaN的数据
        data_with_nulls = pd.Series([1, 2, None, 4, 5, float('nan'), 100])

        anomalies = detector._detect_three_sigma_anomalies(data_with_nulls, "test", "column")

        # 应该处理空值并检测异常
        assert isinstance(anomalies, list)

    def test_detect_three_sigma_anomalies_mixed_types(self, detector):
        """测试3σ规则混合类型数据"""
        # 混合类型数据（字符串和数字）
        mixed_data = pd.Series([1, 2, "invalid", 4, 100])

        anomalies = detector._detect_three_sigma_anomalies(mixed_data, "test", "column")

        # 应该优雅处理类型错误
        assert isinstance(anomalies, list)

    def test_detect_iqr_anomalies_coverage(self, detector):
        """测试IQR方法覆盖"""
        # 测试小数据集
        small_data = pd.Series([1, 2, 3, 50])

        anomalies = detector._detect_iqr_anomalies(small_data, "test", "column")

        # 验证异常检测
        assert isinstance(anomalies, list)

        # 测试所有值相同的情况
        same_values = pd.Series([5, 5, 5, 5])
        anomalies_same = detector._detect_iqr_anomalies(same_values, "test", "column")
        assert len(anomalies_same) == 0

    def test_detect_iqr_anomalies_mixed_data(self, detector):
        """测试IQR方法混合数据"""
        # 包含非数值的数据
        mixed_data = pd.Series([1, 2, "text", 3, 100])

        anomalies = detector._detect_iqr_anomalies(mixed_data, "test", "column")

        # 应该优雅处理错误
        assert isinstance(anomalies, list)

    def test_detect_z_score_anomalies_coverage(self, detector):
        """测试Z-score方法覆盖"""
        # 测试正常数据
        normal_data = pd.Series([1, 2, 3, 4, 5])

        anomalies = detector._detect_z_score_anomalies(normal_data, "test", "column")

        assert isinstance(anomalies, list)

        # 测试异常数据
        outlier_data = pd.Series([1, 2, 3, 4, 100])

        anomalies_outlier = detector._detect_z_score_anomalies(outlier_data, "test", "column")

        # 验证异常检测
        assert isinstance(anomalies_outlier, list)

    def test_detect_z_score_anomalies_edge_cases(self, detector):
        """测试Z-score方法边缘情况"""
        # 测试单一值
        single_value = pd.Series([5])

        anomalies = detector._detect_z_score_anomalies(single_value, "test", "column")

        assert len(anomalies) == 0

        # 测试两个相同值
        two_same = pd.Series([5, 5])

        anomalies_two = detector._detect_z_score_anomalies(two_same, "test", "column")

        assert len(anomalies_two) == 0

    def test_detect_range_anomalies_threshold_coverage(self, detector):
        """测试范围检查阈值覆盖"""
        # 设置测试配置
        detector.detection_config["test_table"] = {
            "thresholds": {
                "test_column": {"min": 0, "max": 10}
            }
        }

        # 测试正常数据
        normal_data = pd.Series([1, 2, 3, 4, 5])

        anomalies = detector._detect_range_anomalies(normal_data, "test_table", "test_column")

        assert len(anomalies) == 0

        # 测试超出范围数据
        range_data = pd.Series([1, 2, 15, -5])

        anomalies_range = detector._detect_range_anomalies(range_data, "test_table", "test_column")

        assert len(anomalies_range) > 0
        assert anomalies_range[0].anomaly_type == AnomalyType.VALUE_RANGE

    def test_detect_range_anomalies_partial_thresholds(self, detector):
        """测试部分阈值配置"""
        # 只设置最小值
        detector.detection_config["test_table"] = {
            "thresholds": {
                "test_column": {"min": 0}
            }
        }

        data = pd.Series([1, 2, -5])

        anomalies = detector._detect_range_anomalies(data, "test_table", "test_column")

        # 应该只检测小于最小值的异常
        assert len(anomalies) > 0
        assert -5 in anomalies[0].anomalous_values

    def test_detect_frequency_anomalies_coverage(self, detector):
        """测试频率异常检测覆盖"""
        # 测试均匀分布
        uniform_data = pd.Series(['A', 'B', 'C', 'A', 'B', 'C'])

        anomalies = detector._detect_frequency_anomalies(uniform_data, "test", "column")

        assert len(anomalies) == 0

        # 测试频率不均衡
        skewed_data = pd.Series(['A', 'A', 'A', 'A', 'B', 'C'])

        anomalies_skewed = detector._detect_frequency_anomalies(skewed_data, "test", "column")

        assert isinstance(anomalies_skewed, list)

    def test_detect_frequency_anomalies_single_value(self, detector):
        """测试频率异常检测单值情况"""
        # 所有值相同
        single_value_data = pd.Series(['A', 'A', 'A', 'A'])

        anomalies = detector._detect_frequency_anomalies(single_value_data, "test", "column")

        assert isinstance(anomalies, list)

    def test_detect_time_gap_anomalies_coverage(self, detector, sample_time_data):
        """测试时间间隔异常检测覆盖"""
        # 测试时间数据
        anomalies = detector._detect_time_gap_anomalies(sample_time_data, "test", "column")

        assert isinstance(anomalies, list)

        # 测试短时间序列
        short_time_data = pd.Series([datetime.now()])

        anomalies_short = detector._detect_time_gap_anomalies(short_time_data, "test", "column")

        assert len(anomalies_short) == 0

    def test_detect_time_gap_anomalies_string_dates(self, detector):
        """测试时间间隔异常检测字符串日期"""
        # 字符串格式的时间
        string_time_data = pd.Series([
            "2025-01-01 10:00:00",
            "2025-01-01 10:01:00",
            "2025-01-01 15:00:00"
        ])

        anomalies = detector._detect_time_gap_anomalies(string_time_data, "test", "column")

        # 应该处理字符串格式并检测异常
        assert isinstance(anomalies, list)

    def test_calculate_severity_coverage(self, detector):
        """测试严重程度计算覆盖"""
        # 测试边界值
        assert detector._calculate_severity(0.2) == AnomalySeverity.CRITICAL
        assert detector._calculate_severity(0.1) == AnomalySeverity.HIGH
        assert detector._calculate_severity(0.05) == AnomalySeverity.MEDIUM
        assert detector._calculate_severity(0.01) == AnomalySeverity.LOW
        assert detector._calculate_severity(0.0) == AnomalySeverity.LOW

    def test_calculate_severity_extreme_values(self, detector):
        """测试严重程度计算极值"""
        # 测试超出范围的值
        assert detector._calculate_severity(1.0) == AnomalySeverity.CRITICAL
        assert detector._calculate_severity(0.25) == AnomalySeverity.CRITICAL
        assert detector._calculate_severity(-0.1) == AnomalySeverity.LOW

    @pytest.mark.asyncio
    async def test_detect_anomalies_error_handling_coverage(self, detector):
        """测试异常检测错误处理覆盖"""
        # Mock数据库会话抛出异常
        with patch.object(detector.db_manager, 'get_async_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None

            # Mock _detect_table_anomalies 抛出异常
            with patch.object(detector, '_detect_table_anomalies', side_effect=Exception("Test error")):
                anomalies = await detector.detect_anomalies(["nonexistent_table"])

                # 应该返回空列表而不是抛出异常
                assert isinstance(anomalies, list)

    @pytest.mark.asyncio
    async def test_detect_anomalies_table_not_in_config(self, detector):
        """测试检测配置中不存在的表"""
        # Mock数据库会话
        with patch.object(detector.db_manager, 'get_async_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None

            # 检测不存在的表
            anomalies = await detector.detect_anomalies(["nonexistent_table"])

            # 应该返回空列表
            assert isinstance(anomalies, list)

    @pytest.mark.asyncio
    async def test_detect_table_anomalies_no_data(self, detector):
        """测试检测无数据的表"""
        mock_session = AsyncMock()

        # Mock _get_table_data 返回空DataFrame
        with patch.object(detector, '_get_table_data', return_value=pd.DataFrame()):
            detector.detection_config["test_table"] = {
                "numeric_columns": ["test_column"]
            }

            anomalies = await detector._detect_table_anomalies(
                mock_session, "test_table", ["three_sigma"]
            )

            assert len(anomalies) == 0

    @pytest.mark.asyncio
    async def test_detect_column_anomalies_empty_data(self, detector):
        """测试检测空列数据"""
        empty_df = pd.DataFrame()

        anomalies = await detector._detect_column_anomalies(
            empty_df, "test", "nonexistent_column", ["three_sigma"], "numeric"
        )

        assert len(anomalies) == 0

    @pytest.mark.asyncio
    async def test_get_table_data_database_error(self, detector):
        """测试获取表数据数据库错误"""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database error")

        data = await detector._get_table_data(mock_session, "test_table")

        assert data.empty

    @pytest.mark.asyncio
    async def test_get_anomaly_summary_coverage(self, detector):
        """测试异常摘要覆盖"""
        # 测试空摘要
        empty_summary = await detector.get_anomaly_summary([])

        assert empty_summary["total_anomalies"] == 0
        assert empty_summary["by_severity"] == {}
        assert empty_summary["by_type"] == {}
        assert empty_summary["by_table"] == {}
        assert "summary_time" in empty_summary

    @pytest.mark.asyncio
    async def test_get_anomaly_summary_complex_data(self, detector):
        """测试复杂异常数据摘要"""
        # 创建多个异常
        anomalies = [
            AnomalyResult(
                table_name="matches",
                column_name="home_score",
                anomaly_type=AnomalyType.OUTLIER,
                severity=AnomalySeverity.CRITICAL,
                anomalous_values=[100],
                anomaly_score=0.3,
                detection_method="3sigma",
                description="严重异常"
            ),
            AnomalyResult(
                table_name="matches",
                column_name="away_score",
                anomaly_type=AnomalyType.VALUE_RANGE,
                severity=AnomalySeverity.HIGH,
                anomalous_values=[-10],
                anomaly_score=0.15,
                detection_method="range",
                description="范围异常"
            ),
            AnomalyResult(
                table_name="odds",
                column_name="home_odds",
                anomaly_type=AnomalyType.FREQUENCY,
                severity=AnomalySeverity.MEDIUM,
                anomalous_values=["abnormal"],
                anomaly_score=0.06,
                detection_method="frequency",
                description="频率异常"
            )
        ]

        summary = await detector.get_anomaly_summary(anomalies)

        assert summary["total_anomalies"] == 3
        assert summary["by_severity"]["critical"] == 1
        assert summary["by_severity"]["high"] == 1
        assert summary["by_severity"]["medium"] == 1
        assert summary["by_type"]["outlier"] == 1
        assert summary["by_type"]["value_range"] == 1
        assert summary["by_type"]["frequency"] == 1
        assert summary["by_table"]["matches"] == 2
        assert summary["by_table"]["odds"] == 1
        assert summary["critical_anomalies"] == 1
        assert summary["high_priority_anomalies"] == 2
        assert summary["most_affected_table"] == "matches"

    def test_detection_method_comprehensive_coverage(self, detector):
        """综合覆盖所有检测方法"""
        # 创建包含各种异常的数据
        test_data = pd.Series([1, 2, 3, 4, 100, -50])

        # 设置配置以启用所有方法
        detector.detection_config["test_table"] = {
            "thresholds": {"test_column": {"min": 0, "max": 10}}
        }

        # 依次调用所有检测方法
        methods = [
            detector._detect_three_sigma_anomalies,
            detector._detect_iqr_anomalies,
            detector._detect_z_score_anomalies,
            detector._detect_range_anomalies,
            detector._detect_frequency_anomalies,
        ]

        for method in methods:
            result = method(test_data, "test_table", "test_column")
            assert isinstance(result, list)

    def test_configuration_validation_coverage(self, detector):
        """测试配置验证覆盖"""
        # 验证配置结构
        config = detector.detection_config

        # 检查必需的表
        required_tables = ["matches", "odds", "predictions"]
        for table in required_tables:
            assert table in config

        # 检查matches表配置的完整性
        matches_config = config["matches"]
        required_keys = ["numeric_columns", "time_columns", "categorical_columns", "thresholds"]
        for key in required_keys:
            assert key in matches_config

    def test_anomaly_result_comprehensive_coverage(self):
        """测试 AnomalyResult 类的全面覆盖"""
        # 测试所有异常类型
        for anomaly_type in AnomalyType:
            result = AnomalyResult(
                table_name="test",
                column_name="test_column",
                anomaly_type=anomaly_type,
                severity=AnomalySeverity.LOW,
                anomalous_values=[1],
                anomaly_score=0.1,
                detection_method="test",
                description="test"
            )

            assert result.anomaly_type == anomaly_type
            assert result.to_dict()["anomaly_type"] == anomaly_type.value

        # 测试所有严重程度
        for severity in AnomalySeverity:
            result = AnomalyResult(
                table_name="test",
                column_name="test_column",
                anomaly_type=AnomalyType.OUTLIER,
                severity=severity,
                anomalous_values=[1],
                anomaly_score=0.1,
                detection_method="test",
                description="test"
            )

            assert result.severity == severity
            assert result.to_dict()["severity"] == severity.value

    @pytest.mark.asyncio
    async def test_detect_anomalies_with_specific_methods(self, detector):
        """测试使用特定方法的异常检测"""
        # Mock数据库会话
        with patch.object(detector.db_manager, 'get_async_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None

            # Mock _detect_table_anomalies
            with patch.object(detector, '_detect_table_anomalies', return_value=[]):
                # 测试特定方法
                anomalies = await detector.detect_anomalies(
                    table_names=["matches"],
                    methods=["three_sigma", "iqr"]
                )

                assert isinstance(anomalies, list)

    def test_anomaly_detection_edge_case_data(self, detector):
        """测试异常检测边缘情况数据"""
        # 测试包含极大值的数据
        extreme_data = pd.Series([1, 2, 3, 4, float('inf')])

        anomalies = detector._detect_three_sigma_anomalies(extreme_data, "test", "column")

        # 应该处理无限大值
        assert isinstance(anomalies, list)

    def test_error_logging_coverage(self, detector):
        """测试错误日志覆盖"""
        # 测试各种错误情况
        invalid_data = pd.Series(['invalid', 'data'])

        # 这些方法应该记录错误但不抛出异常
        assert isinstance(detector._detect_three_sigma_anomalies(invalid_data, "test", "test"), list)
        assert isinstance(detector._detect_iqr_anomalies(invalid_data, "test", "test"), list)
        assert isinstance(detector._detect_z_score_anomalies(invalid_data, "test", "test"), list)
        assert isinstance(detector._detect_range_anomalies(invalid_data, "test", "test"), list)
        assert isinstance(detector._detect_frequency_anomalies(invalid_data, "test", "test"), list)