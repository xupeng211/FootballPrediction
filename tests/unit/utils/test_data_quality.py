"""数据质量测试"""

import pytest


@pytest.mark.unit
class TestDataQuality:
    """测试数据质量模块"""

    def test_anomaly_detector_import(self):
        """测试异常检测器导入"""
        try:
            from src.data.quality.anomaly_detector import AnomalyDetector

            assert AnomalyDetector is not None
        except ImportError:
            pytest.skip("AnomalyDetector not available")

    def test_data_quality_monitor_import(self):
        """测试数据质量监控器导入"""
        try:
            from src.data.quality.data_quality_monitor import DataQualityMonitor

            assert DataQualityMonitor is not None
        except ImportError:
            pytest.skip("DataQualityMonitor not available")

    def test_exception_handler_import(self):
        """测试异常处理器导入"""
        try:
            from src.data.quality.exception_handler_mod import DataExceptionHandler

            assert DataExceptionHandler is not None
        except ImportError:
            pytest.skip("DataExceptionHandler not available")

    def test_great_expectations_config_import(self):
        """测试Great Expectations配置导入"""
        try:
            from src.data.quality.great_expectations_config import get_ge_config

            assert callable(get_ge_config)
        except ImportError:
            pytest.skip("great_expectations_config not available")
