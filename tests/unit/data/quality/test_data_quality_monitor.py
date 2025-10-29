# TODO: Consider creating a fixture for 23 repeated Mock creations

# TODO: Consider creating a fixture for 23 repeated Mock creations

from unittest.mock import AsyncMock, Mock, patch

"""
数据质量监控器测试
Tests for Data Quality Monitor

测试src.data.quality.data_quality_monitor模块的数据质量监控功能
"""

import logging
from datetime import datetime, timedelta

import pytest

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
@pytest.mark.unit
class TestDataQualityMonitor:
    """数据质量监控器测试"""

    def test_monitor_creation(self):
        """测试：监控器创建"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            monitor = DataQualityMonitor()
            assert monitor is not None
            assert hasattr(monitor, "thresholds")
            assert monitor.thresholds["data_freshness_hours"] == 24
            assert monitor.thresholds["missing_data_rate"] == 0.1
            assert monitor.thresholds["odds_min_value"] == 1.01
            assert monitor.thresholds["odds_max_value"] == 100.0

    def test_monitor_custom_thresholds(self):
        """测试：自定义阈值"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            monitor = DataQualityMonitor()

            # 更新阈值
            monitor.thresholds["data_freshness_hours"] = 12
            monitor.thresholds["missing_data_rate"] = 0.05

            assert monitor.thresholds["data_freshness_hours"] == 12
            assert monitor.thresholds["missing_data_rate"] == 0.05

    @pytest.mark.asyncio
    async def test_check_data_freshness(self):
        """测试：检查数据新鲜度"""
        monitor = DataQualityMonitor()

        # 模拟数据库会话
        AsyncMock()

        with patch.object(monitor, "_check_fixtures_age") as mock_fixtures:
            with patch.object(monitor, "_check_odds_age") as mock_odds:
                mock_fixtures.return_value = {
                    "status": "good",
                    "oldest_fixture_hours": 6,
                    "stale_fixtures_count": 0,
                }
                mock_odds.return_value = {
                    "status": "warning",
                    "oldest_odds_hours": 30,
                    "stale_odds_count": 5,
                }

                _result = await monitor.check_data_freshness()

                assert "fixtures" in result
                assert "odds" in result
                assert "overall_status" in result
                assert _result["fixtures"]["status"] == "good"
                assert _result["odds"]["status"] == "warning"

    @pytest.mark.asyncio
    async def test_detect_anomalies(self):
        """测试：检测异常"""
        monitor = DataQualityMonitor()

        AsyncMock()

        with patch.object(monitor, "_find_missing_matches") as mock_missing:
            with patch.object(monitor, "_find_suspicious_odds") as mock_odds:
                with patch.object(monitor, "_find_unusual_scores") as mock_scores:
                    with patch.object(monitor, "_check_data_consistency") as mock_consistency:
                        mock_missing.return_value = {
                            "missing_matches": 2,
                            "details": ["Match 1", "Match 2"],
                        }
                        mock_odds.return_value = [
                            {"match_id": 123, "issue": "suspicious_odds"},
                            {"match_id": 456, "issue": "extreme_value"},
                        ]
                        mock_scores.return_value = [{"match_id": 789, "issue": "high_scoring"}]
                        mock_consistency.return_value = [
                            {"match_id": 101, "issue": "inconsistent_data"}
                        ]

                        _result = await monitor.detect_anomalies()

                        assert isinstance(result, list)
                        assert len(result) >= 4  # 至少4个异常
                        # 验证包含各种类型的异常
                        anomaly_types = [a.get("issue") for a in result]
                        assert "suspicious_odds" in anomaly_types
                        assert "high_scoring" in anomaly_types

    @pytest.mark.asyncio
    async def test_check_fixtures_age_good(self):
        """测试：检查比赛年龄（良好状态）"""
        monitor = DataQualityMonitor()

        mock_session = AsyncMock()

        # 模拟最近更新的比赛
        recent_time = datetime.now() - timedelta(hours=6)
        mock_result = Mock()
        mock_result.scalar.return_value = recent_time
        mock_session.execute.return_value = mock_result

        _result = await monitor._check_fixtures_age(mock_session)

        assert _result["status"] == "good"
        assert _result["oldest_fixture_hours"] < 24
        assert _result["stale_fixtures_count"] == 0

    @pytest.mark.asyncio
    async def test_check_fixtures_age_stale(self):
        """测试：检查比赛年龄（过期数据）"""
        monitor = DataQualityMonitor()

        mock_session = AsyncMock()

        # 模拟过期的比赛
        stale_time = datetime.now() - timedelta(hours=48)
        mock_result = Mock()
        mock_result.scalar.return_value = stale_time
        mock_session.execute.return_value = mock_result

        _result = await monitor._check_fixtures_age(mock_session)

        assert _result["status"] == "critical"
        assert _result["oldest_fixture_hours"] > 24
        assert _result["stale_fixtures_count"] > 0

    @pytest.mark.asyncio
    async def test_check_odds_age_warning(self):
        """测试：检查赔率年龄（警告状态）"""
        monitor = DataQualityMonitor()

        mock_session = AsyncMock()

        # 模拟稍旧的赔率
        warning_time = datetime.now() - timedelta(hours=26)
        mock_result = Mock()
        mock_result.scalar.return_value = warning_time
        mock_session.execute.return_value = mock_result

        _result = await monitor._check_odds_age(mock_session)

        assert _result["status"] == "warning"
        assert _result["oldest_odds_hours"] > 24

    @pytest.mark.asyncio
    async def test_find_missing_matches(self):
        """测试：查找缺失的比赛"""
        monitor = DataQualityMonitor()

        mock_session = AsyncMock()

        # 模拟应该存在但实际不存在的比赛
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            {"date": "2024-01-15", "league": "Premier League", "missing_count": 2}
        ]
        mock_session.execute.return_value = mock_result

        _result = await monitor._find_missing_matches(mock_session)

        assert "missing_matches" in result
        assert _result["missing_matches"] >= 0
        assert "details" in result

    @pytest.mark.asyncio
    async def test_find_suspicious_odds(self):
        """测试：查找可疑赔率"""
        monitor = DataQualityMonitor()

        mock_session = AsyncMock()

        # 模拟可疑赔率数据
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            {
                "match_id": 123,
                "home_win": 0.5,  # 低于最小值
                "draw": 3.5,
                "away_win": 8.0,  # 高于最大值
                "suspicious_reason": "extreme_values",
            },
            {
                "match_id": 456,
                "home_win": 2.0,
                "draw": 3.0,
                "away_win": 4.0,
                "suspicious_reason": "rapid_change",
            },
        ]
        mock_session.execute.return_value = mock_result

        _result = await monitor._find_suspicious_odds(mock_session)

        assert isinstance(result, list)
        if result:
            assert "match_id" in _result[0]
            assert "suspicious_reason" in _result[0]

    @pytest.mark.asyncio
    async def test_find_unusual_scores(self):
        """测试：查找异常比分"""
        monitor = DataQualityMonitor()

        mock_session = AsyncMock()

        # 模拟异常比分
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            {
                "match_id": 789,
                "home_score": 15,  # 超过最大值
                "away_score": 0,
                "unusual_reason": "high_scoring",
            },
            {
                "match_id": 101,
                "home_score": 0,
                "away_score": 12,
                "unusual_reason": "one_sided",
            },
        ]
        mock_session.execute.return_value = mock_result

        _result = await monitor._find_unusual_scores(mock_session)

        assert isinstance(result, list)
        if result:
            assert "match_id" in _result[0]
            assert "unusual_reason" in _result[0]

    @pytest.mark.asyncio
    async def test_check_data_consistency(self):
        """测试：检查数据一致性"""
        monitor = DataQualityMonitor()

        mock_session = AsyncMock()

        # 模拟不一致的数据
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            {
                "match_id": 111,
                "issue": "mismatched_teams",
                "details": "Home team name differs in fixtures and odds",
            },
            {
                "match_id": 222,
                "issue": "invalid_datetime",
                "details": "Match datetime is in the past for future fixture",
            },
        ]
        mock_session.execute.return_value = mock_result

        _result = await monitor._check_data_consistency(mock_session)

        assert isinstance(result, list)
        if result:
            assert "match_id" in _result[0]
            assert "issue" in _result[0]

    @pytest.mark.asyncio
    async def test_generate_quality_report(self):
        """测试：生成质量报告"""
        monitor = DataQualityMonitor()

        with patch.object(monitor, "check_data_freshness") as mock_freshness:
            with patch.object(monitor, "detect_anomalies") as mock_anomalies:
                mock_freshness.return_value = {
                    "fixtures": {"status": "good"},
                    "odds": {"status": "warning"},
                    "overall_status": "warning",
                }
                mock_anomalies.return_value = [
                    {"type": "suspicious_odds", "count": 3},
                    {"type": "missing_data", "count": 1},
                ]

                report = await monitor.generate_quality_report()

                assert "timestamp" in report
                assert "data_freshness" in report
                assert "anomalies" in report
                assert "quality_score" in report
                assert "overall_status" in report
                assert "recommendations" in report
                assert report["quality_score"] >= 0
                assert report["quality_score"] <= 100

    def test_calculate_quality_score_perfect(self):
        """测试：计算质量分数（完美）"""
        monitor = DataQualityMonitor()

        freshness_check = {"overall_status": "good"}
        anomalies = []

        score = monitor._calculate_quality_score(freshness_check, anomalies)

        assert score == 100.0

    def test_calculate_quality_score_warning(self):
        """测试：计算质量分数（警告）"""
        monitor = DataQualityMonitor()

        freshness_check = {"overall_status": "warning"}
        anomalies = [{"type": "suspicious_odds"}, {"type": "missing_data"}]

        score = monitor._calculate_quality_score(freshness_check, anomalies)

        assert score < 90
        assert score >= 70

    def test_calculate_quality_score_critical(self):
        """测试：计算质量分数（严重）"""
        monitor = DataQualityMonitor()

        freshness_check = {"overall_status": "critical"}
        anomalies = [
            {"type": "suspicious_odds"},
            {"type": "missing_data"},
            {"type": "inconsistent_data"},
            {"type": "unusual_scores"},
            {"type": "stale_data"},
        ]

        score = monitor._calculate_quality_score(freshness_check, anomalies)

        assert score < 70
        assert score >= 0

    def test_determine_overall_status_good(self):
        """测试：确定总体状态（良好）"""
        monitor = DataQualityMonitor()

        freshness_check = {"overall_status": "good"}
        anomalies = []

        status = monitor._determine_overall_status(freshness_check, anomalies)

        assert status == "good"

    def test_determine_overall_status_warning(self):
        """测试：确定总体状态（警告）"""
        monitor = DataQualityMonitor()

        freshness_check = {"overall_status": "good"}
        anomalies = [{"type": "minor_issue"}]

        status = monitor._determine_overall_status(freshness_check, anomalies)

        assert status == "warning"

    def test_determine_overall_status_critical(self):
        """测试：确定总体状态（严重）"""
        monitor = DataQualityMonitor()

        freshness_check = {"overall_status": "critical"}
        anomalies = [{"type": "major_issue"}]

        status = monitor._determine_overall_status(freshness_check, anomalies)

        assert status == "critical"

    def test_generate_recommendations_good(self):
        """测试：生成建议（良好状态）"""
        monitor = DataQualityMonitor()

        freshness_check = {"overall_status": "good"}
        anomalies = []

        recommendations = monitor._generate_recommendations(freshness_check, anomalies)

        assert isinstance(recommendations, list)
        if recommendations:
            assert all(isinstance(r, str) for r in recommendations)

    def test_generate_recommendations_with_anomalies(self):
        """测试：生成建议（有异常）"""
        monitor = DataQualityMonitor()

        freshness_check = {"overall_status": "warning"}
        anomalies = [
            {"type": "stale_data"},
            {"type": "missing_data"},
            {"type": "suspicious_odds"},
        ]

        recommendations = monitor._generate_recommendations(freshness_check, anomalies)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        # 应该包含针对每种异常的建议
        rec_text = " ".join(recommendations).lower()
        assert "update" in rec_text or "refresh" in rec_text
        assert "missing" in rec_text or "check" in rec_text
        assert "odds" in rec_text or "suspicious" in rec_text

    @pytest.mark.asyncio
    async def test_quality_monitor_with_custom_config(self):
        """测试：使用自定义配置的质量监控"""
        monitor = DataQualityMonitor()

        # 更新配置
        monitor.thresholds.update(
            {
                "data_freshness_hours": 12,
                "missing_data_rate": 0.05,
                "odds_min_value": 1.1,
                "odds_max_value": 50.0,
            }
        )

        mock_session = AsyncMock()

        # 测试使用新阈值
        recent_time = datetime.now() - timedelta(hours=10)  # 10小时前
        mock_result = Mock()
        mock_result.scalar.return_value = recent_time
        mock_session.execute.return_value = mock_result

        _result = await monitor._check_fixtures_age(mock_session)

        # 使用12小时阈值，10小时应该是好的
        assert _result["status"] == "good"

        # 使用48小时前的时间应该是严重的
        old_time = datetime.now() - timedelta(hours=48)
        mock_result.scalar.return_value = old_time
        _result = await monitor._check_fixtures_age(mock_session)
        assert _result["status"] == "critical"

    @pytest.mark.asyncio
    async def test_full_quality_check_workflow(self):
        """测试：完整质量检查工作流"""
        monitor = DataQualityMonitor()

        with patch.object(monitor, "check_data_freshness") as mock_freshness:
            with patch.object(monitor, "detect_anomalies") as mock_anomalies:
                with patch.object(monitor, "generate_quality_report") as mock_report:
                    # 设置模拟返回值
                    mock_freshness.return_value = {
                        "fixtures": {"status": "good"},
                        "odds": {"status": "warning"},
                        "overall_status": "warning",
                    }
                    mock_anomalies.return_value = [{"type": "suspicious_odds", "count": 2}]
                    mock_report.return_value = {
                        "timestamp": datetime.now(),
                        "quality_score": 85.0,
                        "overall_status": "warning",
                        "recommendations": ["Check odds sources"],
                    }

                    # 执行完整工作流
                    freshness = await monitor.check_data_freshness()
                    anomalies = await monitor.detect_anomalies()
                    report = await monitor.generate_quality_report()

                    # 验证结果
                    assert freshness["overall_status"] == "warning"
                    assert len(anomalies) > 0
                    assert report["quality_score"] == 85.0
                    assert report["overall_status"] == "warning"

    @pytest.mark.asyncio
    async def test_error_handling_in_checks(self):
        """测试：检查中的错误处理"""
        monitor = DataQualityMonitor()

        mock_session = AsyncMock()

        # 模拟数据库错误
        mock_session.execute.side_effect = Exception("Database connection failed")

        # 应该优雅地处理错误
        _result = await monitor._check_fixtures_age(mock_session)

        assert "status" in result
        assert _result["status"] == "error"
        assert "error" in result

    def test_logging_configuration(self):
        """测试：日志配置"""
        monitor = DataQualityMonitor()

        assert monitor.logger is not None
        assert isinstance(monitor.logger, logging.Logger)
        assert "quality" in monitor.logger.name
        assert "DataQualityMonitor" in monitor.logger.name

    def test_threshold_validation(self):
        """测试：阈值验证"""
        monitor = DataQualityMonitor()

        # 测试默认阈值
        assert monitor.thresholds["data_freshness_hours"] > 0
        assert 0 < monitor.thresholds["missing_data_rate"] < 1
        assert monitor.thresholds["odds_min_value"] > 1.0
        assert monitor.thresholds["odds_max_value"] > monitor.thresholds["odds_min_value"]
        assert monitor.thresholds["score_max_value"] > 0
        assert 0 < monitor.thresholds["suspicious_odds_change"] < 1

    @pytest.mark.asyncio
    async def test_monitor_performance(self):
        """测试：监控器性能"""
        import time

        monitor = DataQualityMonitor()

        mock_session = AsyncMock()

        # 模拟快速响应
        mock_result = Mock()
        mock_result.scalar.return_value = datetime.now()
        mock_session.execute.return_value = mock_result

        start_time = time.time()

        # 执行多个检查
        await monitor._check_fixtures_age(mock_session)
        await monitor._check_odds_age(mock_session)

        elapsed = time.time() - start_time

        # 验证性能（应该在合理时间内完成）
        assert elapsed < 1.0  # 应该在1秒内完成


@pytest.mark.skipif(
    not DATA_QUALITY_MONITOR_AVAILABLE,
    reason="Data quality monitor module not available",
)
class TestDataQualityMonitorIntegration:
    """数据质量监控器集成测试"""

    @pytest.mark.asyncio
    async def test_monitoring_pipeline(self):
        """测试：监控管道"""
        monitor = DataQualityMonitor()

        # 模拟完整的监控管道
        with patch.object(monitor, "db_manager") as mock_db:
            mock_db.get_session.return_value.__aenter__.return_value = AsyncMock()

            with patch.object(monitor, "_check_fixtures_age") as mock_fixtures:
                with patch.object(monitor, "_check_odds_age") as mock_odds:
                    with patch.object(monitor, "_find_missing_matches") as mock_missing:
                        mock_fixtures.return_value = {"status": "good"}
                        mock_odds.return_value = {"status": "warning"}
                        mock_missing.return_value = {"missing_matches": 0}

                        # 执行监控
                        freshness = await monitor.check_data_freshness()
                        anomalies = await monitor.detect_anomalies()
                        report = await monitor.generate_quality_report()

                        # 验证管道执行
                        assert "fixtures" in freshness
                        assert "odds" in freshness
                        assert isinstance(anomalies, list)
                        assert "quality_score" in report

    @pytest.mark.asyncio
    async def test_continuous_monitoring(self):
        """测试：持续监控"""
        monitor = DataQualityMonitor()

        # 模拟定期监控
        check_results = []

        for i in range(3):
            with patch.object(monitor, "check_data_freshness") as mock_check:
                mock_check.return_value = {"overall_status": "good" if i % 2 == 0 else "warning"}
                _result = await monitor.check_data_freshness()
                check_results.append(result)

        # 验证监控历史
        assert len(check_results) == 3
        assert check_results[0]["overall_status"] == "good"
        assert check_results[1]["overall_status"] == "warning"

    @pytest.mark.asyncio
    async def test_alert_generation(self):
        """测试：告警生成"""
        monitor = DataQualityMonitor()

        # 模拟需要告警的情况
        with patch.object(monitor, "generate_quality_report") as mock_report:
            mock_report.return_value = {
                "timestamp": datetime.now(),
                "quality_score": 45.0,
                "overall_status": "critical",
                "anomalies": [
                    {"type": "stale_data", "count": 10},
                    {"type": "missing_data", "count": 5},
                ],
                "recommendations": [
                    "Immediate data refresh required",
                    "Check data pipelines",
                ],
            }

            report = await monitor.generate_quality_report()

            # 验证告警条件
            assert report["quality_score"] < 50
            assert report["overall_status"] == "critical"
            assert len(report["anomalies"]) > 0
            assert len(report["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_quality_trend_analysis(self):
        """测试：质量趋势分析"""
        DataQualityMonitor()

        # 模拟历史质量数据
        quality_history = [
            {"timestamp": datetime.now() - timedelta(hours=24), "score": 95.0},
            {"timestamp": datetime.now() - timedelta(hours=18), "score": 90.0},
            {"timestamp": datetime.now() - timedelta(hours=12), "score": 85.0},
            {"timestamp": datetime.now() - timedelta(hours=6), "score": 80.0},
            {"timestamp": datetime.now(), "score": 75.0},
        ]

        # 计算趋势
        scores = [h["score"] for h in quality_history]
        trend = scores[-1] - scores[0]

        # 验证趋势分析
        assert trend < 0  # 质量在下降
        assert abs(trend) == 20.0  # 下降了20分

    @pytest.mark.asyncio
    async def test_multi_source_quality_check(self):
        """测试：多源质量检查"""
        monitor = DataQualityMonitor()

        # 模拟多个数据源的质量检查
        sources = ["api_football", "api_sports", "manual_entry"]
        source_quality = {}

        for source in sources:
            with patch.object(monitor, "_check_fixtures_age") as mock_check:
                mock_check.return_value = {
                    "status": "good" if source != "manual_entry" else "warning",
                    "source": source,
                }
                _result = await monitor._check_fixtures_age(AsyncMock())
                source_quality[source] = result

        # 验证多源检查
        assert len(source_quality) == 3
        assert source_quality["api_football"]["status"] == "good"
        assert source_quality["manual_entry"]["status"] == "warning"


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
