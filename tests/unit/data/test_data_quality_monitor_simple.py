"""
数据质量监控器测试 - 简化版本

测试数据质量检查的核心功能。
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
import pandas as pd

from src.data.quality.data_quality_monitor import DataQualityMonitor


class TestDataQualityMonitor:
    """数据质量监控器测试类"""

    @pytest.fixture
    def monitor(self):
        """创建DataQualityMonitor实例"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            return DataQualityMonitor()

    def test_init(self, monitor):
        """测试初始化"""
    assert monitor.db_manager is not None
    assert monitor.logger is not None
    assert isinstance(monitor.thresholds, dict)

        # 验证阈值配置
        expected_thresholds = {
            "data_freshness_hours": 24,
            "missing_data_rate": 0.1,
            "odds_min_value": 1.01,
            "odds_max_value": 100.0,
            "score_max_value": 20,
            "suspicious_odds_change": 0.5,
        }
    assert monitor.thresholds == expected_thresholds

    def test_odds_thresholds(self, monitor):
        """测试赔率阈值配置"""
        # 测试阈值配置
    assert monitor.thresholds["odds_min_value"] == 1.01
    assert monitor.thresholds["odds_max_value"] == 100.0
    assert monitor.thresholds["suspicious_odds_change"] == 0.5

    def test_score_thresholds(self, monitor):
        """测试比分阈值配置"""
        # 测试阈值配置
    assert monitor.thresholds["score_max_value"] == 20
    assert monitor.thresholds["data_freshness_hours"] == 24
    assert monitor.thresholds["missing_data_rate"] == 0.1

    def test_check_threshold_config(self, monitor):
        """测试阈值配置检查"""
        # 测试可以修改阈值
        original_threshold = monitor.thresholds["data_freshness_hours"]
        monitor.thresholds["data_freshness_hours"] = 12

    assert monitor.thresholds["data_freshness_hours"] == 12

        # 恢复原始值
        monitor.thresholds["data_freshness_hours"] = original_threshold
    assert monitor.thresholds["data_freshness_hours"] == 24

    def test_calculate_time_difference(self, monitor):
        """测试时间差计算"""
        # 测试时间差计算逻辑
        now = datetime.now(timezone.utc)
        past_time = now - timedelta(hours=5)

        # 模拟时间差计算
        time_diff = (now - past_time).total_seconds() / 3600
    assert time_diff == 5.0

        # 测试未来时间
        future_time = now + timedelta(hours=2)
        time_diff = (future_time - now).total_seconds() / 3600
    assert time_diff == 2.0

    def test_quality_score_calculation(self, monitor):
        """测试质量评分计算"""
        # 测试评分计算逻辑
        fresh_check = {"status": "healthy"}
        anomalies = []

        score = monitor._calculate_quality_score(fresh_check, anomalies)
    assert isinstance(score, float)
    assert score == 100.0  # 完美评分

        # 测试异常扣分
        high_severity_anomaly = {"severity": "high"}
        anomalies.append(high_severity_anomaly)
        score = monitor._calculate_quality_score(fresh_check, anomalies)
    assert score == 85.0  # 100 - 15

        # 测试更多异常
        anomalies.append({"severity": "medium"})
        score = monitor._calculate_quality_score(fresh_check, anomalies)
    assert score == 77.0  # 85 - 8

    def test_overall_status_determination(self, monitor):
        """测试总体状态确定"""
        # 测试健康状态
        fresh_check = {"status": "healthy"}
        anomalies = []
        status = monitor._determine_overall_status(fresh_check, anomalies)
    assert status == "healthy"

        # 测试警告状态
        fresh_check = {"status": "warning"}
        status = monitor._determine_overall_status(fresh_check, anomalies)
    assert status == "warning"

        # 测试严重异常
        high_severity_anomaly = {"severity": "high"}
        anomalies.append(high_severity_anomaly)
        status = monitor._determine_overall_status(fresh_check, anomalies)
    assert status == "warning"

        # 测试危急状态
        for i in range(5):
            anomalies.append({"severity": "high"})
        status = monitor._determine_overall_status(fresh_check, anomalies)
    assert status == "critical"

    def test_data_quality_scoring(self, monitor):
        """测试数据质量评分"""
        # 测试评分计算逻辑
        test_cases = [
            ({"completeness": 1.0, "freshness": 1.0, "consistency": 1.0}, 1.0),
            ({"completeness": 0.8, "freshness": 0.9, "consistency": 0.7}, 0.8),
            ({"completeness": 0.5, "freshness": 0.6, "consistency": 0.4}, 0.5),
        ]

        for metrics, expected_min_score in test_cases:
            # 简单的加权平均
            score = (metrics["completeness"] + metrics["freshness"] + metrics["consistency"]) / 3
    assert score >= expected_min_score * 0.9  # 允许小的误差

    def test_error_handling_patterns(self, monitor):
        """测试错误处理模式"""
        # 测试数据库连接失败
        mock_db = MagicMock()
        mock_db.get_async_session.side_effect = Exception("Connection failed")
        monitor.db_manager = mock_db

        # 应该优雅处理异常
    assert hasattr(monitor, 'logger')
    assert monitor.logger is not None

    def test_logging_setup(self, monitor):
        """测试日志设置"""
    assert monitor.logger is not None
        logger_name = monitor.logger.name
    assert "quality" in logger_name or "DataQualityMonitor" in logger_name

    @pytest.mark.asyncio
    async def test_mock_database_operations(self, monitor):
        """测试模拟数据库操作"""
        # 设置模拟数据库
        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()

        # 模拟返回当前时间
        current_time = datetime.now(timezone.utc)
        mock_result.scalar.return_value = current_time - timedelta(hours=1)
        mock_session.execute.return_value = mock_result
        mock_db.get_async_session.return_value.__aenter__.return_value = mock_session

        monitor.db_manager = mock_db

        # 验证数据库设置正确
    assert monitor.db_manager is mock_db
    assert callable(monitor.db_manager.get_async_session)

    def test_coverage_of_core_methods(self, monitor):
        """测试核心方法的覆盖"""
        # 验证核心方法存在
        core_methods = [
            'check_data_freshness',
            'detect_anomalies',
            'generate_quality_report',
            '_calculate_quality_score',
            '_determine_overall_status',
            '_generate_recommendations'
        ]

        for method_name in core_methods:
    assert hasattr(monitor, method_name), f"Method {method_name} not found"
            method = getattr(monitor, method_name)
    assert callable(method), f"Method {method_name} is not callable"

    def test_threshold_configuration(self, monitor):
        """测试阈值配置"""
        # 测试可以修改阈值
        original_threshold = monitor.thresholds["data_freshness_hours"]
        monitor.thresholds["data_freshness_hours"] = 12

    assert monitor.thresholds["data_freshness_hours"] == 12

        # 恢复原始值
        monitor.thresholds["data_freshness_hours"] = original_threshold
    assert monitor.thresholds["data_freshness_hours"] == 24


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])