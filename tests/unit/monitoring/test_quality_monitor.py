"""
测试数据质量监控器
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.monitoring.quality_monitor import QualityMonitor, DataFreshnessResult, DataCompletenessResult


@pytest.fixture
def quality_monitor():
    """创建质量监控器实例"""
    return QualityMonitor()


class TestQualityMonitor:
    """测试数据质量监控器"""

    def test_init(self, quality_monitor):
        """测试初始化"""
        assert quality_monitor.freshness_checker is not None
        assert quality_monitor.completeness_checker is not None
        assert quality_monitor.consistency_checker is not None
        assert quality_monitor.score_calculator is not None
        assert quality_monitor.trend_analyzer is not None

    @pytest.mark.asyncio
    async def test_check_data_freshness(self, quality_monitor):
        """测试检查数据新鲜度"""
        with patch.object(quality_monitor.freshness_checker, 'check_data_freshness') as mock_check:
            mock_check.return_value = {
                "matches": DataFreshnessResult(
                    table_name="matches",
                    last_update_time=None,
                    records_count=100,
                    freshness_hours=1.0,
                    is_fresh=True,
                    threshold_hours=24
                )
            }

            results = await quality_monitor.check_data_freshness(["matches"])

            assert "matches" in results
            assert results["matches"].is_fresh is True
            mock_check.assert_called_once_with(["matches"])

    @pytest.mark.asyncio
    async def test_check_data_completeness(self, quality_monitor):
        """测试检查数据完整性"""
        with patch.object(quality_monitor.completeness_checker, 'check_data_completeness') as mock_check:
            mock_check.return_value = {
                "matches": DataCompletenessResult(
                    table_name="matches",
                    total_records=100,
                    missing_critical_fields={},
                    missing_rate=0.0,
                    completeness_score=100.0
                )
            }

            results = await quality_monitor.check_data_completeness(["matches"])

            assert "matches" in results
            assert results["matches"].completeness_score == 100.0
            mock_check.assert_called_once_with(["matches"])

    @pytest.mark.asyncio
    async def test_check_data_consistency(self, quality_monitor):
        """测试检查数据一致性"""
        with patch.object(quality_monitor.consistency_checker, 'check_data_consistency') as mock_check:
            mock_check.return_value = {
                "foreign_key_consistency": {"orphaned_home_teams": 0},
                "odds_consistency": {"invalid_odds_range": 0},
                "match_status_consistency": {"finished_matches_without_score": 0}
            }

            results = await quality_monitor.check_data_consistency()

            assert "foreign_key_consistency" in results
            assert "odds_consistency" in results
            assert "match_status_consistency" in results
            mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score(self, quality_monitor):
        """测试计算总体质量评分"""
        with patch.object(quality_monitor.score_calculator, 'calculate_overall_quality_score') as mock_calculate:
            mock_calculate.return_value = {
                "overall_score": 95.0,
                "freshness_score": 100.0,
                "completeness_score": 90.0,
                "consistency_score": 95.0,
                "quality_level": "优秀"
            }

            results = await quality_monitor.calculate_overall_quality_score()

            assert results["overall_score"] == 95.0
            assert results["quality_level"] == "优秀"
            mock_calculate.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_quality_trends(self, quality_monitor):
        """测试获取质量趋势"""
        with patch.object(quality_monitor.trend_analyzer, 'get_quality_trends') as mock_trends:
            mock_trends.return_value = {
                "current_quality": {"overall_score": 90.0},
                "trend_period_days": 7,
                "trend_data": [],
                "recommendations": []
            }

            results = await quality_monitor.get_quality_trends(days=7)

            assert results["trend_period_days"] == 7
            assert "current_quality" in results
            assert "recommendations" in results
            mock_trends.assert_called_once_with(7)


class TestDataFreshnessResult:
    """测试数据新鲜度结果"""

    def test_to_dict(self):
        """测试转换为字典"""
        from datetime import datetime

        result = DataFreshnessResult(
            table_name="matches",
            last_update_time=datetime(2024, 1, 1, 12, 0, 0),
            records_count=100,
            freshness_hours=1.5,
            is_fresh=True,
            threshold_hours=24
        )

        dict_result = result.to_dict()

        assert dict_result["table_name"] == "matches"
        assert dict_result["records_count"] == 100
        assert dict_result["freshness_hours"] == 1.5
        assert dict_result["is_fresh"] is True
        assert dict_result["last_update_time"] == "2024-01-01T12:00:00"


class TestDataCompletenessResult:
    """测试数据完整性结果"""

    def test_to_dict(self):
        """测试转换为字典"""
        result = DataCompletenessResult(
            table_name="matches",
            total_records=100,
            missing_critical_fields={"home_team_id": 0, "away_team_id": 0},
            missing_rate=0.0,
            completeness_score=100.0
        )

        dict_result = result.to_dict()

        assert dict_result["table_name"] == "matches"
        assert dict_result["total_records"] == 100
        assert dict_result["missing_rate"] == 0.0
        assert dict_result["completeness_score"] == 100.0