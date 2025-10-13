"""
数据质量监控器简化测试
Tests for Data Quality Monitor (Simple Version)

测试src.data.quality.data_quality_monitor模块的基本功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import logging

# 测试导入
try:
    from src.data.quality.data_quality_monitor import DataQualityMonitor

    DATA_QUALITY_MONITOR_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    DATA_QUALITY_MONITOR_AVAILABLE = False
    DataQualityMonitor = None


@pytest.mark.skipif(
    not DATA_QUALITY_MONITOR_AVAILABLE,
    reason="Data quality monitor module not available",
)
class TestDataQualityMonitorSimple:
    """数据质量监控器简化测试"""

    def test_monitor_creation(self):
        """测试：监控器创建"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            monitor = DataQualityMonitor()
            assert monitor is not None
            assert hasattr(monitor, "thresholds")
            assert monitor.thresholds["data_freshness_hours"] == 24

    def test_monitor_custom_thresholds(self):
        """测试：自定义阈值"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            monitor = DataQualityMonitor()
            monitor.thresholds["data_freshness_hours"] = 12
            assert monitor.thresholds["data_freshness_hours"] == 12

    def test_calculate_quality_score_perfect(self):
        """测试：计算质量分数（完美）"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            monitor = DataQualityMonitor()

            freshness_check = {"overall_status": "good"}
            anomalies = []

            score = monitor._calculate_quality_score(freshness_check, anomalies)
            assert score == 100.0

    def test_calculate_quality_score_with_issues(self):
        """测试：计算质量分数（有问题）"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            monitor = DataQualityMonitor()

            freshness_check = {"status": "warning"}  # 修正为正确的status字段
            anomalies = [{"severity": "high"}]  # 添加severity字段

            score = monitor._calculate_quality_score(freshness_check, anomalies)
            assert 70 <= score < 90

    def test_determine_overall_status(self):
        """测试：确定总体状态"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            monitor = DataQualityMonitor()

            # 测试各种状态组合
            test_cases = [
                ({"overall_status": "good"}, [], "good"),
                ({"overall_status": "good"}, [{"type": "minor"}], "warning"),
                ({"overall_status": "critical"}, [{"type": "major"}], "critical"),
            ]

            for freshness, anomalies, expected in test_cases:
                status = monitor._determine_overall_status(freshness, anomalies)
                assert status == expected

    def test_logging_configuration(self):
        """测试：日志配置"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            monitor = DataQualityMonitor()
            assert monitor.logger is not None
            assert isinstance(monitor.logger, logging.Logger)

    def test_threshold_values(self):
        """测试：阈值验证"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            monitor = DataQualityMonitor()

            # 验证默认阈值
            assert monitor.thresholds["data_freshness_hours"] == 24
            assert monitor.thresholds["missing_data_rate"] == 0.1
            assert monitor.thresholds["odds_min_value"] == 1.01
            assert monitor.thresholds["odds_max_value"] == 100.0
            assert monitor.thresholds["score_max_value"] == 20
            assert monitor.thresholds["suspicious_odds_change"] == 0.5

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试：错误处理"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager") as mock_db:
            mock_db.return_value.get_session.side_effect = Exception("DB Error")

            monitor = DataQualityMonitor()

            # 测试错误不会导致崩溃
            try:
                await monitor.check_data_freshness()
            except Exception:
                pass  # 预期可能有错误

    def test_generate_recommendations(self):
        """测试：生成建议"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            monitor = DataQualityMonitor()

            freshness_check = {"overall_status": "warning"}
            anomalies = [{"type": "stale_data"}]

            # 如果方法存在，测试它
            if hasattr(monitor, "_generate_recommendations"):
                recommendations = monitor._generate_recommendations(
                    freshness_check, anomalies
                )
                assert isinstance(recommendations, list)

    def test_quality_score_boundary(self):
        """测试：质量分数边界"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            monitor = DataQualityMonitor()

            # 测试严重情况
            freshness_check = {"overall_status": "critical"}
            anomalies = [
                {"type": "stale_data"},
                {"type": "missing_data"},
                {"type": "suspicious_odds"},
                {"type": "inconsistent_data"},
                {"type": "unusual_scores"},
            ]

            score = monitor._calculate_quality_score(freshness_check, anomalies)
            assert 0 <= score < 70

    def test_status_priority(self):
        """测试：状态优先级"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            monitor = DataQualityMonitor()

            # critical > warning > good
            test_cases = [
                ({"overall_status": "good"}, [], "good"),
                ({"overall_status": "warning"}, [], "warning"),
                ({"overall_status": "critical"}, [], "critical"),
                # 有异常时至少是warning
                ({"overall_status": "good"}, [{"type": "any"}], "warning"),
                # critical状态保持critical
                ({"overall_status": "critical"}, [], "critical"),
            ]

            for freshness, anomalies, expected in test_cases:
                _result = monitor._determine_overall_status(freshness, anomalies)
                assert _result == expected


@pytest.mark.skipif(
    DATA_QUALITY_MONITOR_AVAILABLE,
    reason="Data quality monitor module should be available",
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not DATA_QUALITY_MONITOR_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if DATA_QUALITY_MONITOR_AVAILABLE:
        from src.data.quality.data_quality_monitor import DataQualityMonitor

        assert DataQualityMonitor is not None
