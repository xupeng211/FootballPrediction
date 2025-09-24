"""
阶段2：数据质量监控器综合测试
目标：全面提升数据质量监控器模块覆盖率到70%+
重点：测试新鲜度检查、完整性检查、一致性检查、质量评分计算等核心功能
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.monitoring.quality_monitor import (
    DataCompletenessResult,
    DataFreshnessResult,
    QualityMonitor,
)


class TestQualityMonitorCore:
    """质量监控器核心功能测试"""

    def setup_method(self):
        """设置测试环境"""
        self.monitor = QualityMonitor()

    def test_monitor_initialization(self):
        """测试监控器初始化"""
        assert self.monitor.freshness_thresholds is not None
        assert isinstance(self.monitor.freshness_thresholds, dict)
        assert "matches" in self.monitor.freshness_thresholds
        assert "odds" in self.monitor.freshness_thresholds

        assert self.monitor.critical_fields is not None
        assert isinstance(self.monitor.critical_fields, dict)
        assert "matches" in self.monitor.critical_fields

        assert self.monitor.db_manager is not None

    def test_freshness_thresholds_configuration(self):
        """测试新鲜度阈值配置"""
        thresholds = self.monitor.freshness_thresholds
        assert thresholds["matches"] == 24
        assert thresholds["odds"] == 1
        assert thresholds["predictions"] == 2
        assert thresholds["teams"] == 168
        assert thresholds["leagues"] == 720

    def test_critical_fields_configuration(self):
        """测试关键字段配置"""
        fields = self.monitor.critical_fields
        assert "home_team_id" in fields["matches"]
        assert "away_team_id" in fields["matches"]
        assert "match_id" in fields["odds"]
        assert "model_name" in fields["predictions"]
        assert "team_name" in fields["teams"]

    def test_database_manager_initialization(self):
        """测试数据库管理器初始化"""
        from src.database.connection import DatabaseManager

        assert isinstance(self.monitor.db_manager, DatabaseManager)


class TestDataFreshnessResult:
    """数据新鲜度结果类测试"""

    def test_initialization(self):
        """测试初始化"""
        result = DataFreshnessResult(
            table_name="matches",
            last_update_time=datetime.now(),
            records_count=100,
            freshness_hours=1.5,
            is_fresh=True,
            threshold_hours=24,
        )

        assert result.table_name == "matches"
        assert result.last_update_time is not None
        assert result.records_count == 100
        assert result.freshness_hours == 1.5
        assert result.is_fresh is True
        assert result.threshold_hours == 24

    def test_to_dict(self):
        """测试字典转换"""
        update_time = datetime.now()
        result = DataFreshnessResult(
            table_name="matches",
            last_update_time=update_time,
            records_count=100,
            freshness_hours=1.5,
            is_fresh=True,
            threshold_hours=24,
        )

        result_dict = result.to_dict()
        assert result_dict["table_name"] == "matches"
        assert result_dict["last_update_time"] == update_time.isoformat()
        assert result_dict["records_count"] == 100
        assert result_dict["freshness_hours"] == 1.5
        assert result_dict["is_fresh"] is True
        assert result_dict["threshold_hours"] == 24

    def test_to_dict_with_none_time(self):
        """测试无更新时间的字典转换"""
        result = DataFreshnessResult(
            table_name="matches",
            last_update_time=None,
            records_count=0,
            freshness_hours=999999,
            is_fresh=False,
            threshold_hours=24,
        )

        result_dict = result.to_dict()
        assert result_dict["last_update_time"] is None


class TestDataCompletenessResult:
    """数据完整性结果类测试"""

    def test_initialization(self):
        """测试初始化"""
        result = DataCompletenessResult(
            table_name="matches",
            total_records=100,
            missing_critical_fields={"home_team_id": 5},
            missing_rate=0.05,
            completeness_score=95.0,
        )

        assert result.table_name == "matches"
        assert result.total_records == 100
        assert result.missing_critical_fields == {"home_team_id": 5}
        assert result.missing_rate == 0.05
        assert result.completeness_score == 95.0

    def test_to_dict(self):
        """测试字典转换"""
        result = DataCompletenessResult(
            table_name="matches",
            total_records=100,
            missing_critical_fields={"home_team_id": 5, "away_team_id": 3},
            missing_rate=0.08,
            completeness_score=92.0,
        )

        result_dict = result.to_dict()
        assert result_dict["table_name"] == "matches"
        assert result_dict["total_records"] == 100
        assert result_dict["missing_critical_fields"] == {
            "home_team_id": 5,
            "away_team_id": 3,
        }
        assert result_dict["missing_rate"] == 0.08
        assert result_dict["completeness_score"] == 92.0


class TestQualityMonitorDataFreshness:
    """质量监控器数据新鲜度检查测试"""

    def setup_method(self):
        """设置测试环境"""
        self.monitor = QualityMonitor()

    @pytest.mark.asyncio
    async def test_check_data_freshness_all_tables(self):
        """测试检查所有表的数据新鲜度"""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock数据库管理器
        with patch.object(
            self.monitor.db_manager, "get_async_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Mock各个表的检查结果
            with patch.object(self.monitor, "_check_table_freshness") as mock_check:
                mock_check.return_value = DataFreshnessResult(
                    table_name="matches",
                    last_update_time=datetime.now(),
                    records_count=100,
                    freshness_hours=1.0,
                    is_fresh=True,
                    threshold_hours=24,
                )

                results = await self.monitor.check_data_freshness()

                assert len(results) == len(self.monitor.freshness_thresholds)
                assert "matches" in results
                assert results["matches"].is_fresh is True

    @pytest.mark.asyncio
    async def test_check_data_freshness_specific_tables(self):
        """测试检查特定表的数据新鲜度"""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch.object(
            self.monitor.db_manager, "get_async_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch.object(self.monitor, "_check_table_freshness") as mock_check:
                mock_check.return_value = DataFreshnessResult(
                    table_name="matches",
                    last_update_time=datetime.now(),
                    records_count=50,
                    freshness_hours=2.0,
                    is_fresh=True,
                    threshold_hours=24,
                )

                results = await self.monitor.check_data_freshness(["matches"])

                assert len(results) == 1
                assert "matches" in results
                assert results["matches"].records_count == 50

    @pytest.mark.asyncio
    async def test_check_data_freshness_with_exception(self):
        """测试数据新鲜度检查异常处理"""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch.object(
            self.monitor.db_manager, "get_async_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch.object(self.monitor, "_check_table_freshness") as mock_check:
                mock_check.side_effect = Exception("Database error")

                results = await self.monitor.check_data_freshness(["matches"])

                assert len(results) == 1
                assert "matches" in results
                assert results["matches"].is_fresh is False
                assert results["matches"].records_count == 0
                assert results["matches"].freshness_hours == 999999

    @pytest.mark.asyncio
    async def test_check_table_freshness_matches(self):
        """测试检查比赛表新鲜度"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.first.return_value = Mock(
            last_update=datetime.now(), record_count=100
        )
        mock_session.execute.return_value = mock_result

        result = await self.monitor._check_table_freshness(mock_session, "matches")

        assert result.table_name == "matches"
        assert result.records_count == 100
        assert result.is_fresh is True

    @pytest.mark.asyncio
    async def test_check_table_freshness_odds(self):
        """测试检查赔率表新鲜度"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.first.return_value = Mock(
            last_update=datetime.now(), record_count=200
        )
        mock_session.execute.return_value = mock_result

        result = await self.monitor._check_table_freshness(mock_session, "odds")

        assert result.table_name == "odds"
        assert result.records_count == 200
        assert result.threshold_hours == 1

    @pytest.mark.asyncio
    async def test_check_table_freshness_old_data(self):
        """测试检查过期数据"""
        mock_session = AsyncMock(spec=AsyncSession)
        old_time = datetime.now() - timedelta(hours=30)
        mock_result = Mock()
        mock_result.first.return_value = Mock(last_update=old_time, record_count=100)
        mock_session.execute.return_value = mock_result

        result = await self.monitor._check_table_freshness(mock_session, "matches")

        assert result.is_fresh is False
        assert result.freshness_hours > 24

    @pytest.mark.asyncio
    async def test_check_table_freshness_no_data(self):
        """测试检查无数据表"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result

        result = await self.monitor._check_table_freshness(mock_session, "matches")

        assert result.records_count == 0
        assert result.is_fresh is False
        assert result.freshness_hours == 999999

    @pytest.mark.asyncio
    async def test_check_table_freshness_sql_fallback(self):
        """测试SQL方式检查表新鲜度"""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock count query
        count_result = Mock()
        count_result.first.return_value = [100]  # Return list for direct indexing

        # Mock time query
        time_result = Mock()
        time_result.first.return_value = Mock()
        time_result.first.return_value.last_update = datetime.now()

        async def mock_execute(query):
            if "COUNT(*)" in str(query):
                return count_result
            elif "MAX(" in str(query):
                return time_result
            return Mock()

        mock_session.execute = mock_execute

        result = await self.monitor._check_table_freshness_sql(
            mock_session, "leagues", 24
        )

        assert result.table_name == "leagues"
        assert result.records_count == 100
        assert result.is_fresh is True


class TestQualityMonitorDataCompleteness:
    """质量监控器数据完整性检查测试"""

    def setup_method(self):
        """设置测试环境"""
        self.monitor = QualityMonitor()

    @pytest.mark.asyncio
    async def test_check_data_completeness_all_tables(self):
        """测试检查所有表的数据完整性"""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch.object(
            self.monitor.db_manager, "get_async_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch.object(self.monitor, "_check_table_completeness") as mock_check:
                mock_check.return_value = DataCompletenessResult(
                    table_name="matches",
                    total_records=100,
                    missing_critical_fields={},
                    missing_rate=0.0,
                    completeness_score=100.0,
                )

                results = await self.monitor.check_data_completeness()

                assert len(results) == len(self.monitor.critical_fields)
                assert "matches" in results

    @pytest.mark.asyncio
    async def test_check_table_completeness(self):
        """测试检查单个表的完整性"""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock total count query
        total_result = Mock()
        total_result.first.return_value = Mock(total=100)

        # Mock missing fields queries
        missing_result = Mock()
        missing_result.first.return_value = Mock(missing=0)

        def mock_execute(query):
            if "COUNT(*) as total" in str(query):
                return total_result
            elif "WHERE" in str(query) and "IS NULL" in str(query):
                return missing_result
            return Mock()

        mock_session.execute = mock_execute

        result = await self.monitor._check_table_completeness(mock_session, "matches")

        assert result.table_name == "matches"
        assert result.total_records == 100
        assert result.missing_rate == 0.0
        assert result.completeness_score == 100.0

    @pytest.mark.asyncio
    async def test_check_table_completeness_with_missing_data(self):
        """测试检查有缺失数据的表完整性"""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock total count query
        total_result = Mock()
        total_result.first.return_value = Mock(total=100)

        # Mock missing fields queries
        def mock_execute(query):
            result = Mock()
            if "home_team_id" in str(query):
                result.first.return_value = Mock(missing=5)
            elif "away_team_id" in str(query):
                result.first.return_value = Mock(missing=3)
            else:
                result.first.return_value = Mock(missing=0)
            return result

        mock_session.execute = mock_execute

        result = await self.monitor._check_table_completeness(mock_session, "matches")

        assert result.table_name == "matches"
        assert result.total_records == 100
        assert result.missing_critical_fields["home_team_id"] == 5
        assert result.missing_critical_fields["away_team_id"] == 3
        assert result.missing_rate == 0.08  # (5+3)/(100*4) = 8%
        assert result.completeness_score == 92.0

    @pytest.mark.asyncio
    async def test_check_table_completeness_no_critical_fields(self):
        """测试检查无关键字段的表完整性"""
        mock_session = AsyncMock(spec=AsyncSession)

        result = await self.monitor._check_table_completeness(
            mock_session, "unknown_table"
        )

        assert result.table_name == "unknown_table"
        assert result.total_records == 0
        assert result.completeness_score == 100.0

    @pytest.mark.asyncio
    async def test_check_table_completeness_no_data(self):
        """测试检查无数据的表完整性"""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock total count query returning 0
        total_result = Mock()
        total_result.first.return_value = Mock(total=0)
        mock_session.execute.return_value = total_result

        result = await self.monitor._check_table_completeness(mock_session, "matches")

        assert result.table_name == "matches"
        assert result.total_records == 0
        assert result.completeness_score == 100.0


class TestQualityMonitorDataConsistency:
    """质量监控器数据一致性检查测试"""

    def setup_method(self):
        """设置测试环境"""
        self.monitor = QualityMonitor()

    @pytest.mark.asyncio
    async def test_check_data_consistency(self):
        """测试检查数据一致性"""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch.object(
            self.monitor.db_manager, "get_async_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch.object(
                self.monitor, "_check_foreign_key_consistency"
            ) as mock_fk:
                with patch.object(self.monitor, "_check_odds_consistency") as mock_odds:
                    with patch.object(
                        self.monitor, "_check_match_status_consistency"
                    ) as mock_match:
                        mock_fk.return_value = {
                            "orphaned_home_teams": 0,
                            "orphaned_away_teams": 0,
                        }
                        mock_odds.return_value = {"invalid_odds_range": 0}
                        mock_match.return_value = {"finished_matches_without_score": 0}

                        results = await self.monitor.check_data_consistency()

                        assert "foreign_key_consistency" in results
                        assert "odds_consistency" in results
                        assert "match_status_consistency" in results

    @pytest.mark.asyncio
    async def test_check_foreign_key_consistency(self):
        """测试检查外键一致性"""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock query results
        def mock_execute(query):
            result = Mock()
            if "orphaned_home_teams" in str(query):
                result.first.return_value = Mock()
                result.first.return_value.__getitem__ = lambda self, key: (
                    0 if key == 0 else None
                )
            elif "orphaned_away_teams" in str(query):
                result.first.return_value = Mock()
                result.first.return_value.__getitem__ = lambda self, key: (
                    2 if key == 0 else None
                )
            elif "orphaned_odds" in str(query):
                result.first.return_value = Mock()
                result.first.return_value.__getitem__ = lambda self, key: (
                    1 if key == 0 else None
                )
            return result

        mock_session.execute = mock_execute

        results = await self.monitor._check_foreign_key_consistency(mock_session)

        assert results["orphaned_home_teams"] == 0
        assert results["orphaned_away_teams"] == 2
        assert results["orphaned_odds"] == 1

    @pytest.mark.asyncio
    async def test_check_odds_consistency(self):
        """测试检查赔率一致性"""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock query results
        def mock_execute(query):
            result = Mock()
            if "home_odds <= 1.0" in str(query):
                result.first.return_value = Mock()
                result.first.return_value.__getitem__ = lambda self, key: (
                    3 if key == 0 else None
                )
            elif "1.0/home_odds" in str(query):
                result.first.return_value = Mock()
                result.first.return_value.__getitem__ = lambda self, key: (
                    2 if key == 0 else None
                )
            return result

        mock_session.execute = mock_execute

        results = await self.monitor._check_odds_consistency(mock_session)

        assert results["invalid_odds_range"] == 3
        assert results["invalid_probability_sum"] == 2

    @pytest.mark.asyncio
    async def test_check_match_status_consistency(self):
        """测试检查比赛状态一致性"""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock query results
        def mock_execute(query):
            result = Mock()
            if "finished" in str(query) and "IS NULL" in str(query):
                result.first.return_value = Mock()
                result.first.return_value.__getitem__ = lambda self, key: (
                    1 if key == 0 else None
                )
            elif "scheduled" in str(query) and "IS NOT NULL" in str(query):
                result.first.return_value = Mock()
                result.first.return_value.__getitem__ = lambda self, key: (
                    2 if key == 0 else None
                )
            return result

        mock_session.execute = mock_execute

        results = await self.monitor._check_match_status_consistency(mock_session)

        assert results["finished_matches_without_score"] == 1
        assert results["scheduled_matches_with_score"] == 2

    @pytest.mark.asyncio
    async def test_consistency_check_with_exception(self):
        """测试一致性检查异常处理"""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.side_effect = Exception("Database error")

        results = await self.monitor._check_foreign_key_consistency(mock_session)

        assert "error" in results
        assert "Database error" in results["error"]


class TestQualityMonitorScoreCalculation:
    """质量监控器评分计算测试"""

    def setup_method(self):
        """设置测试环境"""
        self.monitor = QualityMonitor()

    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score(self):
        """测试计算总体质量评分"""
        # Mock freshness results
        freshness_results = {
            "matches": DataFreshnessResult(
                "matches", datetime.now(), 100, 1.0, True, 24
            ),
            "odds": DataFreshnessResult("odds", datetime.now(), 200, 0.5, True, 1),
        }

        # Mock completeness results
        completeness_results = {
            "matches": DataCompletenessResult("matches", 100, {}, 0.0, 100.0),
            "odds": DataCompletenessResult("odds", 200, {}, 0.0, 100.0),
        }

        # Mock consistency results
        consistency_results = {
            "foreign_key_consistency": {
                "orphaned_home_teams": 0,
                "orphaned_away_teams": 0,
            },
            "odds_consistency": {"invalid_odds_range": 0},
            "match_status_consistency": {"finished_matches_without_score": 0},
        }

        with patch.object(self.monitor, "check_data_freshness") as mock_freshness:
            with patch.object(
                self.monitor, "check_data_completeness"
            ) as mock_completeness:
                with patch.object(
                    self.monitor, "check_data_consistency"
                ) as mock_consistency:
                    mock_freshness.return_value = freshness_results
                    mock_completeness.return_value = completeness_results
                    mock_consistency.return_value = consistency_results

                    score_result = await self.monitor.calculate_overall_quality_score()

                    assert "overall_score" in score_result
                    assert "freshness_score" in score_result
                    assert "completeness_score" in score_result
                    assert "consistency_score" in score_result
                    assert score_result["overall_score"] >= 90  # All good data

    @pytest.mark.asyncio
    async def test_calculate_quality_score_with_issues(self):
        """测试计算有问题的质量评分"""
        # Mock freshness results with stale data
        freshness_results = {
            "matches": DataFreshnessResult(
                "matches", datetime.now() - timedelta(hours=30), 100, 30.0, False, 24
            ),
            "odds": DataFreshnessResult("odds", datetime.now(), 200, 0.5, True, 1),
        }

        # Mock completeness results with missing data
        completeness_results = {
            "matches": DataCompletenessResult(
                "matches", 100, {"home_team_id": 10}, 0.1, 90.0
            ),
            "odds": DataCompletenessResult("odds", 200, {}, 0.0, 100.0),
        }

        # Mock consistency results with errors
        consistency_results = {
            "foreign_key_consistency": {
                "orphaned_home_teams": 5,
                "orphaned_away_teams": 3,
            },
            "odds_consistency": {"invalid_odds_range": 2},
            "match_status_consistency": {"finished_matches_without_score": 1},
        }

        with patch.object(self.monitor, "check_data_freshness") as mock_freshness:
            with patch.object(
                self.monitor, "check_data_completeness"
            ) as mock_completeness:
                with patch.object(
                    self.monitor, "check_data_consistency"
                ) as mock_consistency:
                    mock_freshness.return_value = freshness_results
                    mock_completeness.return_value = completeness_results
                    mock_consistency.return_value = consistency_results

                    score_result = await self.monitor.calculate_overall_quality_score()

                    assert (
                        score_result["overall_score"] < 90
                    )  # Should be lower due to issues

    @pytest.mark.asyncio
    async def test_calculate_quality_score_with_exception(self):
        """测试质量评分计算异常处理"""
        with patch.object(self.monitor, "check_data_freshness") as mock_freshness:
            mock_freshness.side_effect = Exception("Calculation error")

            score_result = await self.monitor.calculate_overall_quality_score()

            assert score_result["overall_score"] == 0
            assert "error" in score_result
            assert "Calculation error" in score_result["error"]

    def test_get_quality_level(self):
        """测试获取质量等级"""
        assert self.monitor._get_quality_level(98) == "优秀"
        assert self.monitor._get_quality_level(88) == "良好"
        assert self.monitor._get_quality_level(75) == "一般"
        assert self.monitor._get_quality_level(60) == "较差"
        assert self.monitor._get_quality_level(40) == "很差"


class TestQualityMonitorTrends:
    """质量监控器趋势分析测试"""

    def setup_method(self):
        """设置测试环境"""
        self.monitor = QualityMonitor()

    @pytest.mark.asyncio
    async def test_get_quality_trends(self):
        """测试获取质量趋势"""
        quality_data = {
            "overall_score": 85.0,
            "freshness_score": 90.0,
            "completeness_score": 88.0,
            "consistency_score": 75.0,
        }

        with patch.object(self.monitor, "calculate_overall_quality_score") as mock_calc:
            mock_calc.return_value = quality_data

            trends = await self.monitor.get_quality_trends(days=7)

            assert "current_quality" in trends
            assert "trend_period_days" in trends
            assert "trend_data" in trends
            assert "recommendations" in trends
            assert trends["trend_period_days"] == 7

    def test_generate_quality_recommendations(self):
        """测试生成质量改进建议"""
        # Test good quality
        good_quality = {
            "overall_score": 95,
            "freshness_score": 98,
            "completeness_score": 96,
            "consistency_score": 92,
        }

        recommendations = self.monitor._generate_quality_recommendations(good_quality)
        assert len(recommendations) == 0

        # Test poor quality
        poor_quality = {
            "overall_score": 45,
            "freshness_score": 60,
            "completeness_score": 70,
            "consistency_score": 80,
        }

        recommendations = self.monitor._generate_quality_recommendations(poor_quality)
        assert len(recommendations) > 0
        assert any("数据新鲜度较低" in rec for rec in recommendations)
        assert any("整体数据质量需要重点关注" in rec for rec in recommendations)


class TestQualityMonitorEdgeCases:
    """质量监控器边界情况测试"""

    def setup_method(self):
        """设置测试环境"""
        self.monitor = QualityMonitor()

    @pytest.mark.asyncio
    async def test_empty_freshness_results(self):
        """测试空新鲜度结果"""
        with patch.object(self.monitor, "check_data_freshness") as mock_freshness:
            with patch.object(
                self.monitor, "check_data_completeness"
            ) as mock_completeness:
                with patch.object(
                    self.monitor, "check_data_consistency"
                ) as mock_consistency:
                    mock_freshness.return_value = {}
                    mock_completeness.return_value = {}
                    mock_consistency.return_value = {}

                    score_result = await self.monitor.calculate_overall_quality_score()

                    assert score_result["overall_score"] == 0

    @pytest.mark.asyncio
    async def test_single_table_freshness(self):
        """测试单表新鲜度检查"""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch.object(
            self.monitor.db_manager, "get_async_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            with patch.object(self.monitor, "_check_table_freshness") as mock_check:
                mock_check.return_value = DataFreshnessResult(
                    table_name="matches",
                    last_update_time=datetime.now(),
                    records_count=100,
                    freshness_hours=1.0,
                    is_fresh=True,
                    threshold_hours=24,
                )

                results = await self.monitor.check_data_freshness(["matches"])

                assert len(results) == 1
                assert results["matches"].is_fresh is True

    @pytest.mark.asyncio
    async def test_large_freshness_hours(self):
        """测试大新鲜度小时数"""
        mock_session = AsyncMock(spec=AsyncSession)
        very_old_time = datetime.now() - timedelta(days=365)
        mock_result = Mock()
        mock_result.first.return_value = Mock(
            last_update=very_old_time, record_count=100
        )
        mock_session.execute.return_value = mock_result

        result = await self.monitor._check_table_freshness(mock_session, "matches")

        assert result.freshness_hours > 8000  # Should be about 8760 hours
        assert result.is_fresh is False

    @pytest.mark.asyncio
    async def test_completeness_calculation_precision(self):
        """测试完整性计算精度"""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock total count query
        total_result = Mock()
        total_result.first.return_value = Mock(total=1000)

        # Mock missing fields queries with fractional missing rates
        def mock_execute(query):
            result = Mock()
            if "home_team_id" in str(query):
                result.first.return_value = Mock(missing=17)
            elif "away_team_id" in str(query):
                result.first.return_value = Mock(missing=23)
            elif "league_id" in str(query):
                result.first.return_value = Mock(missing=5)
            else:
                result.first.return_value = Mock(missing=0)
            return result

        mock_session.execute = mock_execute

        result = await self.monitor._check_table_completeness(mock_session, "matches")

        # Total missing: 17 + 23 + 5 = 45
        # Total checks: 1000 * 4 = 4000
        # Missing rate: 45 / 4000 = 0.01125
        # Completeness score: 98.875%
        assert result.missing_rate == pytest.approx(0.01125, rel=1e-3)
        assert result.completeness_score == pytest.approx(98.875, rel=1e-3)

    def test_data_freshness_result_rounding(self):
        """测试数据新鲜度结果四舍五入"""
        result = DataFreshnessResult(
            table_name="matches",
            last_update_time=datetime.now(),
            records_count=100,
            freshness_hours=1.23456789,
            is_fresh=True,
            threshold_hours=24,
        )

        result_dict = result.to_dict()
        assert result_dict["freshness_hours"] == 1.23

    def test_data_completeness_result_rounding(self):
        """测试数据完整性结果四舍五入"""
        result = DataCompletenessResult(
            table_name="matches",
            total_records=100,
            missing_critical_fields={"home_team_id": 5},
            missing_rate=0.123456789,
            completeness_score=87.654321,
        )

        result_dict = result.to_dict()
        assert result_dict["missing_rate"] == 0.1235
        assert result_dict["completeness_score"] == 87.65


class TestQualityMonitorSQLInjection:
    """质量监控器SQL注入防护测试"""

    def setup_method(self):
        """设置测试环境"""
        self.monitor = QualityMonitor()

    @pytest.mark.asyncio
    async def test_sql_injection_prevention_freshness(self):
        """测试防止SQL注入 - 新鲜度检查"""
        mock_session = AsyncMock(spec=AsyncSession)

        # Test with malicious table name
        result = await self.monitor._check_table_freshness_sql(
            mock_session, "malicious_table; DROP TABLE users; --", 24
        )

        # Should return failure result, not execute malicious SQL
        assert result.table_name == "malicious_table; DROP TABLE users; --"
        assert result.is_fresh is False
        assert result.records_count == 0

    @pytest.mark.asyncio
    async def test_sql_injection_prevention_completeness(self):
        """测试防止SQL注入 - 完整性检查"""
        mock_session = AsyncMock(spec=AsyncSession)

        # Test with malicious table name
        with pytest.raises(ValueError):
            await self.monitor._check_table_completeness(
                mock_session, "malicious_table; DROP TABLE users; --"
            )

    @pytest.mark.asyncio
    async def test_valid_table_names(self):
        """测试有效表名"""
        mock_session = AsyncMock(spec=AsyncSession)

        # These should not raise exceptions
        for table_name in ["matches", "odds", "predictions", "teams", "leagues"]:
            try:
                await self.monitor._check_table_completeness(mock_session, table_name)
            except ValueError:
                pytest.fail(f"Valid table name {table_name} raised ValueError")


class TestQualityMonitorLogging:
    """质量监控器日志记录测试"""

    def setup_method(self):
        """设置测试环境"""
        self.monitor = QualityMonitor()

    @pytest.mark.asyncio
    async def test_logging_freshness_check(self):
        """测试新鲜度检查日志"""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("src.monitoring.quality_monitor.logger") as mock_logger:
            with patch.object(
                self.monitor.db_manager, "get_async_session"
            ) as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session

                with patch.object(self.monitor, "_check_table_freshness") as mock_check:
                    mock_check.return_value = DataFreshnessResult(
                        table_name="matches",
                        last_update_time=datetime.now(),
                        records_count=100,
                        freshness_hours=1.0,
                        is_fresh=True,
                        threshold_hours=24,
                    )

                    await self.monitor.check_data_freshness(["matches"])

                    mock_logger.info.assert_called_with(
                        "数据新鲜度检查完成，检查了 1 张表"
                    )
                    mock_logger.debug.assert_called_with("表 matches 新鲜度检查完成")

    @pytest.mark.asyncio
    async def test_logging_completeness_check(self):
        """测试完整性检查日志"""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("src.monitoring.quality_monitor.logger") as mock_logger:
            with patch.object(
                self.monitor.db_manager, "get_async_session"
            ) as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session

                with patch.object(
                    self.monitor, "_check_table_completeness"
                ) as mock_check:
                    mock_check.return_value = DataCompletenessResult(
                        table_name="matches",
                        total_records=100,
                        missing_critical_fields={},
                        missing_rate=0.0,
                        completeness_score=100.0,
                    )

                    await self.monitor.check_data_completeness(["matches"])

                    mock_logger.info.assert_called_with(
                        "数据完整性检查完成，检查了 1 张表"
                    )
                    mock_logger.debug.assert_called_with("表 matches 完整性检查完成")

    @pytest.mark.asyncio
    async def test_logging_error_handling(self):
        """测试错误处理日志"""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("src.monitoring.quality_monitor.logger") as mock_logger:
            with patch.object(
                self.monitor.db_manager, "get_async_session"
            ) as mock_get_session:
                mock_get_session.return_value.__aenter__.return_value = mock_session

                with patch.object(self.monitor, "_check_table_freshness") as mock_check:
                    mock_check.side_effect = Exception("Database connection failed")

                    await self.monitor.check_data_freshness(["matches"])

                    mock_logger.error.assert_called_with(
                        "检查表 matches 新鲜度失败: Database connection failed"
                    )

    @pytest.mark.asyncio
    async def test_logging_initialization(self):
        """测试初始化日志"""
        with patch("src.monitoring.quality_monitor.logger") as mock_logger:
            monitor = QualityMonitor()

            mock_logger.info.assert_called_with("数据质量监控器初始化完成")
