"""
quality_monitor模块的基本测试
主要测试QualityMonitor类的基本功能以提升测试覆盖率
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.monitoring.quality_monitor import (DataCompletenessResult,
                                            DataFreshnessResult,
                                            QualityMonitor)


class TestQualityMonitor:
    """测试QualityMonitor基本功能"""

    def test_quality_monitor_initialization(self):
        """测试质量监控器初始化"""
        monitor = QualityMonitor()
        assert monitor is not None
        assert hasattr(monitor, "freshness_thresholds")
        assert hasattr(monitor, "critical_fields")
        assert hasattr(monitor, "db_manager")

    def test_freshness_thresholds_config(self):
        """测试新鲜度阈值配置"""
        monitor = QualityMonitor()
        assert monitor.freshness_thresholds["matches"] == 24
        assert monitor.freshness_thresholds["odds"] == 1
        assert monitor.freshness_thresholds["predictions"] == 2

    def test_critical_fields_config(self):
        """测试关键字段配置"""
        monitor = QualityMonitor()
        assert "matches" in monitor.critical_fields
        assert "home_team_id" in monitor.critical_fields["matches"]
        assert "away_team_id" in monitor.critical_fields["matches"]

    @pytest.mark.asyncio
    async def test_check_data_freshness_basic(self):
        """测试基本数据新鲜度检查"""
        monitor = QualityMonitor()
        with patch.object(monitor.db_manager, "get_async_session") as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()
            with patch.object(
                monitor, "_check_table_freshness"
            ) as mock_check_freshness:
                mock_check_freshness.return_value = DataFreshnessResult(
                    table_name="matches",
                    last_update_time=datetime.now(),
                    records_count=100,
                    freshness_hours=12.0,
                    is_fresh=True,
                    threshold_hours=24.0,
                )
                results = await monitor.check_data_freshness(["matches"])
                assert "matches" in results
                assert isinstance(results["matches"], DataFreshnessResult)

    @pytest.mark.asyncio
    async def test_check_data_completeness_basic(self):
        """测试基本数据完整性检查"""
        monitor = QualityMonitor()
        with patch.object(monitor.db_manager, "get_async_session") as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()
            with patch.object(
                monitor, "_check_table_completeness"
            ) as mock_check_completeness:
                mock_check_completeness.return_value = DataCompletenessResult(
                    table_name="matches",
                    total_records=100,
                    missing_critical_fields={"home_team_id": 0},
                    missing_rate=0.0,
                    completeness_score=100.0,
                )
                results = await monitor.check_data_completeness(["matches"])
                assert "matches" in results
                assert isinstance(results["matches"], DataCompletenessResult)

    @pytest.mark.asyncio
    async def test_check_data_consistency_basic(self):
        """测试基本数据一致性检查"""
        monitor = QualityMonitor()
        with patch.object(monitor.db_manager, "get_async_session") as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()
            with patch.object(
                monitor, "_check_foreign_key_consistency"
            ) as mock_fk_check:
                mock_fk_check.return_value = {"orphaned_home_teams": 0}
                with patch.object(
                    monitor, "_check_odds_consistency"
                ) as mock_odds_check:
                    mock_odds_check.return_value = {"invalid_odds_range": 0}
                    with patch.object(
                        monitor, "_check_match_status_consistency"
                    ) as mock_status_check:
                        mock_status_check.return_value = {
                            "finished_matches_without_score": 0
                        }
                        results = await monitor.check_data_consistency()
                        assert isinstance(results, dict)
                        assert "foreign_key_consistency" in results

    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score_basic(self):
        """测试计算总体质量评分"""
        monitor = QualityMonitor()
        with patch.object(monitor, "check_data_freshness") as mock_freshness:
            mock_freshness.return_value = {
                "matches": DataFreshnessResult(
                    "matches", datetime.now(), 100, 12.0, True, 24.0
                )
            }
            with patch.object(monitor, "check_data_completeness") as mock_completeness:
                mock_completeness.return_value = {
                    "matches": DataCompletenessResult(
                        "matches", 100, {"home_team_id": 0}, 0.0, 100.0
                    )
                }
                with patch.object(
                    monitor, "check_data_consistency"
                ) as mock_consistency:
                    mock_consistency.return_value = {
                        "foreign_key_consistency": {"orphaned_home_teams": 0},
                        "odds_consistency": {"invalid_odds_range": 0},
                        "match_status_consistency": {
                            "finished_matches_without_score": 0
                        },
                    }
                    result = await monitor.calculate_overall_quality_score()
                    assert isinstance(result, dict)
                    assert "overall_score" in result
                    assert "freshness_score" in result
                    assert "completeness_score" in result
                    assert "consistency_score" in result

    def test_get_quality_level(self):
        """测试质量等级判断"""
        monitor = QualityMonitor()
        assert monitor._get_quality_level(96) == "优秀"
        assert monitor._get_quality_level(90) == "良好"
        assert monitor._get_quality_level(75) == "一般"
        assert monitor._get_quality_level(60) == "较差"
        assert monitor._get_quality_level(40) == "很差"

    @pytest.mark.asyncio
    async def test_get_quality_trends_basic(self):
        """测试获取质量趋势"""
        monitor = QualityMonitor()
        with patch.object(monitor, "calculate_overall_quality_score") as mock_score:
            mock_score.return_value = {
                "overall_score": 85.0,
                "freshness_score": 90.0,
                "completeness_score": 85.0,
                "consistency_score": 80.0,
            }
            result = await monitor.get_quality_trends(7)
            assert isinstance(result, dict)
            assert "current_quality" in result
            assert "trend_period_days" in result
            assert "recommendations" in result


class TestDataResults:
    """测试数据结果类"""

    def test_data_freshness_result_creation(self):
        """测试数据新鲜度结果创建"""
        result = DataFreshnessResult(
            table_name="test_table",
            last_update_time=datetime.now(),
            records_count=100,
            freshness_hours=12.0,
            is_fresh=True,
            threshold_hours=24.0,
        )
        assert result.table_name == "test_table"
        assert result.records_count == 100
        assert result.freshness_hours == 12.0
        assert result.is_fresh is True

    def test_data_freshness_result_to_dict(self):
        """测试数据新鲜度结果转字典"""
        now = datetime.now()
        result = DataFreshnessResult(
            table_name="test_table",
            last_update_time=now,
            records_count=100,
            freshness_hours=12.0,
            is_fresh=True,
            threshold_hours=24.0,
        )
        dict_result = result.to_dict()
        assert isinstance(dict_result, dict)
        assert dict_result["table_name"] == "test_table"
        assert dict_result["records_count"] == 100
        assert dict_result["freshness_hours"] == 12.0

    def test_data_completeness_result_creation(self):
        """测试数据完整性结果创建"""
        result = DataCompletenessResult(
            table_name="test_table",
            total_records=100,
            missing_critical_fields={"field1": 5, "field2": 0},
            missing_rate=0.025,
            completeness_score=97.5,
        )
        assert result.table_name == "test_table"
        assert result.total_records == 100
        assert result.missing_rate == 0.025
        assert result.completeness_score == 97.5

    def test_data_completeness_result_to_dict(self):
        """测试数据完整性结果转字典"""
        result = DataCompletenessResult(
            table_name="test_table",
            total_records=100,
            missing_critical_fields={"field1": 5},
            missing_rate=0.05,
            completeness_score=95.0,
        )
        dict_result = result.to_dict()
        assert isinstance(dict_result, dict)
        assert dict_result["table_name"] == "test_table"
        assert dict_result["total_records"] == 100
        assert dict_result["missing_rate"] == 0.05
