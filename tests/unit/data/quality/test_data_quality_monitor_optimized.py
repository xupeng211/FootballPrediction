"""
数据质量监控器优化测试
Tests for Data Quality Monitor (Optimized Version)

使用高性能mock方案测试数据质量监控功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import logging
import asyncio

# 导入优化的 mock
from tests.mocks.fast_mocks import FastDatabaseManager, FastAsyncSession

# 测试导入
try:
    from src.data.quality.data_quality_monitor import DataQualityMonitor
    from src.database.connection import DatabaseManager

    DATA_QUALITY_MONITOR_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    DATA_QUALITY_MONITOR_AVAILABLE = False
    DataQualityMonitor = None
    DatabaseManager = None


@pytest.fixture
def mock_db_session():
    """高性能数据库会话 mock"""
    session = FastAsyncSession()
    return session


@pytest.fixture
def data_quality_monitor(mock_db_session):
    """创建数据质量监控器实例"""
    if not DATA_QUALITY_MONITOR_AVAILABLE:
        pytest.skip("Data quality monitor module not available")

    with patch("src.data.quality.data_quality_monitor.DatabaseManager") as mock_db:
        # 配置快速 mock
        mock_db.return_value.get_async_session.return_value.__aenter__.return_value = (
            mock_db_session
        )
        monitor = DataQualityMonitor()
        return monitor


@pytest.mark.skipif(
    not DATA_QUALITY_MONITOR_AVAILABLE,
    reason="Data quality monitor module not available",
)
class TestDataQualityMonitorOptimized:
    """数据质量监控器优化测试"""

    def test_monitor_creation(self, data_quality_monitor):
        """测试：监控器创建"""
        assert data_quality_monitor is not None
        assert hasattr(data_quality_monitor, "thresholds")
        assert data_quality_monitor.thresholds["data_freshness_hours"] == 24
        assert data_quality_monitor.thresholds["missing_data_rate"] == 0.1
        assert data_quality_monitor.thresholds["odds_min_value"] == 1.01
        assert data_quality_monitor.thresholds["odds_max_value"] == 100.0
        assert data_quality_monitor.thresholds["score_max_value"] == 20

    def test_monitor_custom_thresholds(self, data_quality_monitor):
        """测试：自定义阈值"""
        # 更新阈值
        data_quality_monitor.thresholds["data_freshness_hours"] = 12
        data_quality_monitor.thresholds["missing_data_rate"] = 0.05

        assert data_quality_monitor.thresholds["data_freshness_hours"] == 12
        assert data_quality_monitor.thresholds["missing_data_rate"] == 0.05

    def test_calculate_quality_score_perfect(self, data_quality_monitor):
        """测试：计算质量分数（完美）"""
        freshness_check = {"status": "healthy"}
        anomalies = []

        score = data_quality_monitor._calculate_quality_score(
            freshness_check, anomalies
        )
        assert score == 100.0

    def test_calculate_quality_score_with_issues(self, data_quality_monitor):
        """测试：计算质量分数（有问题）"""
        freshness_check = {"status": "warning"}
        anomalies = [
            {"type": "suspicious_odds", "severity": "high"},
            {"type": "unusual_score", "severity": "medium"},
        ]

        score = data_quality_monitor._calculate_quality_score(
            freshness_check, anomalies
        )
        assert 50 <= score < 90

    def test_determine_overall_status(self, data_quality_monitor):
        """测试：确定总体状态"""
        test_cases = [
            ({"status": "healthy"}, [], "healthy"),
            ({"status": "warning"}, [], "warning"),
            ({"status": "healthy"}, [{"severity": "high"}], "critical"),
            ({"status": "error"}, [], "critical"),
        ]

        for freshness, anomalies, expected in test_cases:
            status = data_quality_monitor._determine_overall_status(
                freshness, anomalies
            )
            assert status == expected

    def test_generate_recommendations(self, data_quality_monitor):
        """测试：生成建议"""
        freshness_check = {"status": "warning"}
        anomalies = [{"severity": "high"}]

        recommendations = data_quality_monitor._generate_recommendations(
            freshness_check, anomalies
        )
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any("检查数据采集" in r for r in recommendations)

    @pytest.mark.asyncio
    async def test_check_data_freshness_healthy(self, data_quality_monitor):
        """测试：检查数据新鲜度（健康状态）"""
        # Mock 数据库查询结果
        mock_result = Mock()
        mock_result.last_update = datetime.now() - timedelta(hours=1)

        with (
            patch.object(data_quality_monitor, "_check_fixtures_age") as mock_fixtures,
            patch.object(data_quality_monitor, "_check_odds_age") as mock_odds,
            patch.object(data_quality_monitor, "_find_missing_matches") as mock_missing,
        ):
            mock_fixtures.return_value = {
                "last_update": datetime.now().isoformat(),
                "hours_since_update": 1,
                "status": "ok",
            }
            mock_odds.return_value = {
                "last_update": datetime.now().isoformat(),
                "hours_since_update": 0.5,
                "status": "ok",
            }
            mock_missing.return_value = {"count": 0}

            report = await data_quality_monitor.check_data_freshness()

            assert report["status"] == "healthy"
            assert len(report["issues"]) == 0
            assert "details" in report

    @pytest.mark.asyncio
    async def test_check_data_freshness_stale(self, data_quality_monitor):
        """测试：检查数据新鲜度（过期状态）"""
        with (
            patch.object(data_quality_monitor, "_check_fixtures_age") as mock_fixtures,
            patch.object(data_quality_monitor, "_check_odds_age") as mock_odds,
            patch.object(data_quality_monitor, "_find_missing_matches") as mock_missing,
        ):
            # 模拟过期数据
            mock_fixtures.return_value = {
                "last_update": (datetime.now() - timedelta(hours=30)).isoformat(),
                "hours_since_update": 30,
                "status": "stale",
            }
            mock_odds.return_value = {
                "last_update": (datetime.now() - timedelta(hours=5)).isoformat(),
                "hours_since_update": 5,
                "status": "stale",
            }
            mock_missing.return_value = {"count": 5}

            report = await data_quality_monitor.check_data_freshness()

            assert report["status"] == "warning" or report["status"] == "critical"
            assert len(report["issues"]) > 0
            assert any("过期" in issue for issue in report["issues"])

    @pytest.mark.asyncio
    async def test_detect_anomalies(self, data_quality_monitor):
        """测试：异常检测"""
        with (
            patch.object(data_quality_monitor, "_find_suspicious_odds") as mock_odds,
            patch.object(data_quality_monitor, "_find_unusual_scores") as mock_scores,
            patch.object(
                data_quality_monitor, "_check_data_consistency"
            ) as mock_consistency,
        ):
            # 模拟异常
            mock_odds.return_value = [
                {
                    "type": "abnormal_odds_value",
                    "match_id": 123,
                    "odds": {"home": 150.0},
                    "severity": "high",
                }
            ]
            mock_scores.return_value = [
                {
                    "type": "unusual_high_score",
                    "match_id": 456,
                    "score": "10-8",
                    "severity": "medium",
                }
            ]
            mock_consistency.return_value = []

            anomalies = await data_quality_monitor.detect_anomalies()

            assert len(anomalies) == 2
            assert any(a["type"] == "abnormal_odds_value" for a in anomalies)
            assert any(a["type"] == "unusual_high_score" for a in anomalies)

    @pytest.mark.asyncio
    async def test_generate_quality_report(self, data_quality_monitor):
        """测试：生成质量报告"""
        with (
            patch.object(
                data_quality_monitor, "check_data_freshness"
            ) as mock_freshness,
            patch.object(data_quality_monitor, "detect_anomalies") as mock_anomalies,
        ):
            mock_freshness.return_value = {"status": "healthy", "details": {}}
            mock_anomalies.return_value = []

            report = await data_quality_monitor.generate_quality_report()

            assert "report_time" in report
            assert "overall_status" in report
            assert "quality_score" in report
            assert "freshness_check" in report
            assert "anomalies" in report
            assert "recommendations" in report

            assert report["overall_status"] == "healthy"
            assert report["quality_score"] == 100.0

    def test_error_handling(self, data_quality_monitor):
        """测试：错误处理"""
        # 测试计算质量分数的错误处理
        score = data_quality_monitor._calculate_quality_score(
            {"status": "error"}, [{"type": "error", "severity": "high"} * 10]
        )
        assert score >= 0

    def test_edge_cases(self, data_quality_monitor):
        """测试：边界情况"""
        # 空异常列表
        score = data_quality_monitor._calculate_quality_score({"status": "healthy"}, [])
        assert score == 100.0

        # 极端严重性
        anomalies = [{"severity": "high"}] * 20
        score = data_quality_monitor._calculate_quality_score(
            {"status": "healthy"}, anomalies
        )
        assert score == 0.0


@pytest.mark.skipif(
    not DATA_QUALITY_MONITOR_AVAILABLE,
    reason="Data quality monitor module not available",
)
class TestDataQualityMonitorIntegration:
    """数据质量监控器集成测试"""

    @pytest.mark.asyncio
    async def test_monitoring_pipeline(self):
        """测试：完整的监控管道"""
        # 使用真实的数据库连接 mock
        with patch("src.data.quality.data_quality_monitor.DatabaseManager") as mock_db:
            # 配置 mock
            mock_session = FastAsyncSession()
            mock_db.return_value.get_async_session.return_value.__aenter__.return_value = mock_session

            # 创建监控器
            monitor = DataQualityMonitor()

            # 执行监控流程
            freshness_report = await monitor.check_data_freshness()
            anomalies = await monitor.detect_anomalies()
            quality_report = await monitor.generate_quality_report()

            # 验证结果
            assert freshness_report is not None
            assert isinstance(anomalies, list)
            assert quality_report is not None
            assert "quality_score" in quality_report
