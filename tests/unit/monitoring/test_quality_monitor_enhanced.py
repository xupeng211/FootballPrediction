"""
数据质量监控器增强测试 - 覆盖率提升版本

针对 QualityMonitor 和相关类的详细测试，专注于提升覆盖率至 70%+
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.monitoring.quality_monitor import (
    DataFreshnessResult,
    DataCompletenessResult,
    QualityMonitor
)


class TestDataFreshnessResult:
    """数据新鲜度结果类测试"""

    def test_init_minimal(self):
        """测试最小初始化"""
        result = DataFreshnessResult(
            table_name="matches",
            last_update_time=datetime.now(timezone.utc),
            records_count=1000,
            freshness_hours=2.5,
            is_fresh=True,
            threshold_hours=24.0
        )

        assert result.table_name == "matches"
        assert isinstance(result.last_update_time, datetime)
        assert result.records_count == 1000
        assert result.freshness_hours == 2.5
        assert result.is_fresh is True
        assert result.threshold_hours == 24.0

    def test_init_without_update_time(self):
        """测试无更新时间的初始化"""
        result = DataFreshnessResult(
            table_name="matches",
            last_update_time=None,
            records_count=0,
            freshness_hours=999999,
            is_fresh=False,
            threshold_hours=24.0
        )

        assert result.last_update_time is None
        assert result.records_count == 0
        assert result.is_fresh is False

    def test_to_dict(self):
        """测试转换为字典"""
        test_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = DataFreshnessResult(
            table_name="matches",
            last_update_time=test_time,
            records_count=1000,
            freshness_hours=2.5,
            is_fresh=True,
            threshold_hours=24.0
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["table_name"] == "matches"
        assert result_dict["last_update_time"] == "2024-01-15T10:30:00+00:00"
        assert result_dict["records_count"] == 1000
        assert result_dict["freshness_hours"] == 2.5
        assert result_dict["is_fresh"] is True
        assert result_dict["threshold_hours"] == 24.0

    def test_to_dict_none_time(self):
        """测试转换字典时时间为None的情况"""
        result = DataFreshnessResult(
            table_name="matches",
            last_update_time=None,
            records_count=0,
            freshness_hours=999999,
            is_fresh=False,
            threshold_hours=24.0
        )

        result_dict = result.to_dict()

        assert result_dict["last_update_time"] is None

    def test_freshness_thresholds(self):
        """测试各种新鲜度阈值"""
        thresholds = [1.0, 24.0, 168.0, 720.0]

        for threshold in thresholds:
            result = DataFreshnessResult(
                table_name="test_table",
                last_update_time=datetime.now(timezone.utc),
                records_count=100,
                freshness_hours=threshold / 2,  # 新鲜
                is_fresh=True,
                threshold_hours=threshold
            )
            assert result.threshold_hours == threshold


class TestDataCompletenessResult:
    """数据完整性结果类测试"""

    def test_init_minimal(self):
        """测试最小初始化"""
        result = DataCompletenessResult(
            table_name="matches",
            total_records=1000,
            missing_critical_fields={"home_team_id": 5, "away_team_id": 3},
            missing_rate=0.008,
            completeness_score=99.2
        )

        assert result.table_name == "matches"
        assert result.total_records == 1000
        assert result.missing_critical_fields == {"home_team_id": 5, "away_team_id": 3}
        assert result.missing_rate == 0.008
        assert result.completeness_score == 99.2

    def test_init_perfect_completeness(self):
        """测试完美完整性初始化"""
        result = DataCompletenessResult(
            table_name="matches",
            total_records=1000,
            missing_critical_fields={},
            missing_rate=0.0,
            completeness_score=100.0
        )

        assert result.missing_critical_fields == {}
        assert result.missing_rate == 0.0
        assert result.completeness_score == 100.0

    def test_to_dict(self):
        """测试转换为字典"""
        result = DataCompletenessResult(
            table_name="matches",
            total_records=1000,
            missing_critical_fields={"home_team_id": 5, "away_team_id": 3},
            missing_rate=0.008,
            completeness_score=99.2
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["table_name"] == "matches"
        assert result_dict["total_records"] == 1000
        assert result_dict["missing_critical_fields"] == {"home_team_id": 5, "away_team_id": 3}
        assert result_dict["missing_rate"] == 0.008
        assert result_dict["completeness_score"] == 99.2

    def test_completeness_score_range(self):
        """测试完整性评分范围"""
        # 完美完整性
        perfect = DataCompletenessResult("table1", 100, {}, 0.0, 100.0)
        assert perfect.completeness_score == 100.0

        # 部分缺失
        partial = DataCompletenessResult("table2", 100, {"field1": 10}, 0.1, 90.0)
        assert partial.completeness_score == 90.0

        # 严重缺失
        poor = DataCompletenessResult("table3", 100, {"field1": 50}, 0.5, 50.0)
        assert poor.completeness_score == 50.0


class TestQualityMonitor:
    """数据质量监控器测试"""

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        db_manager = Mock()
        db_manager.get_async_session = Mock()
        return db_manager

    @pytest.fixture
    def quality_monitor(self, mock_db_manager):
        """创建质量监控器实例"""
        with patch('src.monitoring.quality_monitor.DatabaseManager', return_value=mock_db_manager):
            return QualityMonitor()

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = Mock()
        session.execute = Mock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session

    def test_init(self, quality_monitor):
        """测试初始化"""
        assert quality_monitor.db_manager is not None
        assert isinstance(quality_monitor.freshness_thresholds, dict)
        assert isinstance(quality_monitor.critical_fields, dict)

        # 验证新鲜度阈值配置
        expected_thresholds = {
            "matches": 24,
            "odds": 1,
            "predictions": 2,
            "teams": 168,
            "leagues": 720,
        }
        assert quality_monitor.freshness_thresholds == expected_thresholds

        # 验证关键字段配置
        expected_fields = {
            "matches": ["home_team_id", "away_team_id", "league_id", "match_time"],
            "odds": ["match_id", "bookmaker", "home_odds", "draw_odds", "away_odds"],
            "predictions": ["match_id", "model_name", "home_win_probability"],
            "teams": ["team_name", "league_id"],
        }
        assert quality_monitor.critical_fields == expected_fields

    def test_get_quality_level(self, quality_monitor):
        """测试获取质量等级"""
        assert quality_monitor._get_quality_level(96) == "优秀"
        assert quality_monitor._get_quality_level(90) == "良好"
        assert quality_monitor._get_quality_level(80) == "一般"
        assert quality_monitor._get_quality_level(60) == "较差"
        assert quality_monitor._get_quality_level(40) == "很差"

        # 边界值测试
        assert quality_monitor._get_quality_level(95) == "优秀"
        assert quality_monitor._get_quality_level(85) == "良好"
        assert quality_monitor._get_quality_level(70) == "一般"
        assert quality_monitor._get_quality_level(50) == "较差"
        assert quality_monitor._get_quality_level(49) == "很差"

    @pytest.mark.asyncio
    async def test_check_data_freshness_default_tables(self, quality_monitor, mock_session, mock_db_manager):
        """测试检查默认表的数据新鲜度"""
        # 设置mock返回值
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

        # Mock查询结果
        mock_result = Mock()
        mock_result.first.return_value = Mock()
        mock_result.first.return_value.last_update = datetime.now(timezone.utc) - timedelta(hours=2)
        mock_result.first.return_value.record_count = 1000
        mock_session.execute.return_value = mock_result

        results = await quality_monitor.check_data_freshness()

        assert isinstance(results, dict)
        assert len(results) > 0

        # 验证所有配置的表都被检查
        for table_name in quality_monitor.freshness_thresholds.keys():
            assert table_name in results

    @pytest.mark.asyncio
    async def test_check_data_freshness_specific_tables(self, quality_monitor, mock_session, mock_db_manager):
        """测试检查特定表的数据新鲜度"""
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

        # Mock查询结果
        mock_result = Mock()
        mock_result.first.return_value = Mock()
        mock_result.first.return_value.last_update = datetime.now(timezone.utc) - timedelta(hours=2)
        mock_result.first.return_value.record_count = 100
        mock_session.execute.return_value = mock_result

        results = await quality_monitor.check_data_freshness(["matches", "odds"])

        assert isinstance(results, dict)
        assert "matches" in results
        assert "odds" in results
        assert "predictions" not in results  # 不在请求的表中

    @pytest.mark.asyncio
    async def test_check_data_freshness_with_exception(self, quality_monitor, mock_session, mock_db_manager):
        """测试数据新鲜度检查异常处理"""
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        mock_session.execute.side_effect = Exception("Database error")

        results = await quality_monitor.check_data_freshness(["matches"])

        assert isinstance(results, dict)
        assert "matches" in results
        assert results["matches"].is_fresh is False
        assert results["matches"].records_count == 0

    @pytest.mark.asyncio
    async def test_check_table_freshness_matches(self, quality_monitor, mock_session):
        """测试检查matches表的新鲜度"""
        from unittest.mock import patch
        from src.database.models.match import Match

        # Mock查询结果
        mock_row = Mock()
        mock_row.last_update = datetime.now(timezone.utc) - timedelta(hours=2)
        mock_row.record_count = 1000
        mock_result = Mock()
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        with patch('src.monitoring.quality_monitor.Match', Match):
            result = await quality_monitor._check_table_freshness(mock_session, "matches")

            assert result.table_name == "matches"
            assert result.records_count == 1000
            assert result.is_fresh is True  # 2小时 < 24小时阈值

    @pytest.mark.asyncio
    async def test_check_table_freshness_odds(self, quality_monitor, mock_session):
        """测试检查odds表的新鲜度"""
        from unittest.mock import patch
        from src.database.models.odds import Odds

        # Mock查询结果
        mock_row = Mock()
        mock_row.last_update = datetime.now(timezone.utc) - timedelta(hours=2)
        mock_row.record_count = 500
        mock_result = Mock()
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        with patch('src.monitoring.quality_monitor.Odds', Odds):
            result = await quality_monitor._check_table_freshness(mock_session, "odds")

            assert result.table_name == "odds"
            assert result.records_count == 500
            assert result.is_fresh is False  # 2小时 > 1小时阈值

    @pytest.mark.asyncio
    async def test_check_table_freshness_stale_data(self, quality_monitor, mock_session):
        """测试检查过期数据的新鲜度"""
        from unittest.mock import patch
        from src.database.models.match import Match

        # Mock过期数据
        mock_row = Mock()
        mock_row.last_update = datetime.now(timezone.utc) - timedelta(hours=30)
        mock_row.record_count = 1000
        mock_result = Mock()
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        with patch('src.monitoring.quality_monitor.Match', Match):
            result = await quality_monitor._check_table_freshness(mock_session, "matches")

            assert result.table_name == "matches"
            assert result.is_fresh is False  # 30小时 > 24小时阈值

    @pytest.mark.asyncio
    async def test_check_table_freshness_no_data(self, quality_monitor, mock_session):
        """测试检查无数据表的新鲜度"""
        from unittest.mock import patch
        from src.database.models.match import Match

        # Mock无数据
        mock_result = Mock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result

        with patch('src.monitoring.quality_monitor.Match', Match):
            result = await quality_monitor._check_table_freshness(mock_session, "matches")

            assert result.table_name == "matches"
            assert result.records_count == 0
            assert result.is_fresh is False

    @pytest.mark.asyncio
    async def test_check_table_freshness_sql(self, quality_monitor, mock_session):
        """测试使用SQL检查表的新鲜度"""
        # Mock计数查询
        mock_count_result = Mock()
        mock_count_result.first.return_value = [1000]
        mock_session.execute.return_value = mock_count_result

        # Mock时间查询
        mock_time_result = Mock()
        mock_time_result.first.return_value = Mock()
        mock_time_result.first.return_value.last_update = datetime.now(timezone.utc) - timedelta(hours=2)

        # 让session.execute依次返回计数和时间查询结果
        call_count = 0
        def execute_side_effect(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_count_result
            else:
                return mock_time_result

        mock_session.execute.side_effect = execute_side_effect

        result = await quality_monitor._check_table_freshness_sql(mock_session, "test_table", 24.0)

        assert result.table_name == "test_table"
        assert result.records_count == 1000
        assert result.is_fresh is True

    @pytest.mark.asyncio
    async def test_check_table_freshness_sql_invalid_table(self, quality_monitor, mock_session):
        """测试SQL方式检查无效表名"""
        with pytest.raises(ValueError, match="Invalid table name"):
            await quality_monitor._check_table_freshness_sql(mock_session, "invalid_table", 24.0)

    @pytest.mark.asyncio
    async def test_check_data_completeness_default_tables(self, quality_monitor, mock_session, mock_db_manager):
        """测试检查默认表的数据完整性"""
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

        # Mock查询结果
        mock_total_result = Mock()
        mock_total_result.first.return_value = Mock()
        mock_total_result.first.return_value.total = 1000

        mock_missing_result = Mock()
        mock_missing_result.first.return_value = Mock()
        mock_missing_result.first.return_value.missing = 5

        # 让session.execute依次返回总数和缺失查询结果
        call_count = 0
        def execute_side_effect(query):
            nonlocal call_count
            call_count += 1
            if "COUNT(*) as total" in str(query):
                return mock_total_result
            else:
                return mock_missing_result

        mock_session.execute.side_effect = execute_side_effect

        results = await quality_monitor.check_data_completeness()

        assert isinstance(results, dict)
        assert len(results) > 0

        # 验证所有配置的表都被检查
        for table_name in quality_monitor.critical_fields.keys():
            assert table_name in results

    @pytest.mark.asyncio
    async def test_check_data_completeness_specific_tables(self, quality_monitor, mock_session, mock_db_manager):
        """测试检查特定表的数据完整性"""
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

        # Mock查询结果
        mock_total_result = Mock()
        mock_total_result.first.return_value = Mock()
        mock_total_result.first.return_value.total = 100

        mock_missing_result = Mock()
        mock_missing_result.first.return_value = Mock()
        mock_missing_result.first.return_value.missing = 2

        call_count = 0
        def execute_side_effect(query):
            nonlocal call_count
            call_count += 1
            if "COUNT(*) as total" in str(query):
                return mock_total_result
            else:
                return mock_missing_result

        mock_session.execute.side_effect = execute_side_effect

        results = await quality_monitor.check_data_completeness(["matches"])

        assert isinstance(results, dict)
        assert "matches" in results
        assert "odds" not in results  # 不在请求的表中

    @pytest.mark.asyncio
    async def test_check_table_completeness(self, quality_monitor, mock_session):
        """测试检查单个表的数据完整性"""
        # Mock总数查询
        mock_total_result = Mock()
        mock_total_result.first.return_value = Mock()
        mock_total_result.first.return_value.total = 1000

        # Mock缺失查询
        mock_missing_result = Mock()
        mock_missing_result.first.return_value = Mock()
        mock_missing_result.first.return_value.missing = 10

        call_count = 0
        def execute_side_effect(query):
            nonlocal call_count
            call_count += 1
            if "COUNT(*) as total" in str(query):
                return mock_total_result
            else:
                return mock_missing_result

        mock_session.execute.side_effect = execute_side_effect

        result = await quality_monitor._check_table_completeness(mock_session, "matches")

        assert result.table_name == "matches"
        assert result.total_records == 1000
        assert result.completeness_score < 100.0  # 有缺失字段

    @pytest.mark.asyncio
    async def test_check_table_completeness_no_critical_fields(self, quality_monitor, mock_session):
        """测试检查无关键字段的表"""
        result = await quality_monitor._check_table_completeness(mock_session, "unknown_table")

        assert result.table_name == "unknown_table"
        assert result.total_records == 0
        assert result.completeness_score == 100.0

    @pytest.mark.asyncio
    async def test_check_table_completeness_no_data(self, quality_monitor, mock_session):
        """测试检查无数据的表完整性"""
        # Mock无数据
        mock_total_result = Mock()
        mock_total_result.first.return_value = Mock()
        mock_total_result.first.return_value.total = 0
        mock_session.execute.return_value = mock_total_result

        result = await quality_monitor._check_table_completeness(mock_session, "matches")

        assert result.table_name == "matches"
        assert result.total_records == 0
        assert result.completeness_score == 100.0

    @pytest.mark.asyncio
    async def test_check_table_completeness_invalid_table(self, quality_monitor, mock_session):
        """测试检查无效表的完整性"""
        with pytest.raises(ValueError, match="Invalid table name"):
            await quality_monitor._check_table_completeness(mock_session, "invalid_table")

    @pytest.mark.asyncio
    async def test_check_data_consistency(self, quality_monitor, mock_session, mock_db_manager):
        """测试检查数据一致性"""
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

        # Mock一致性查询结果
        mock_consistency_result = Mock()
        mock_consistency_result.first.return_value = [0]  # 无错误
        mock_session.execute.return_value = mock_consistency_result

        results = await quality_monitor.check_data_consistency()

        assert isinstance(results, dict)
        assert "foreign_key_consistency" in results
        assert "odds_consistency" in results
        assert "match_status_consistency" in results

    @pytest.mark.asyncio
    async def test_check_foreign_key_consistency(self, quality_monitor, mock_session):
        """测试检查外键一致性"""
        # Mock查询结果
        mock_result = Mock()
        mock_result.first.return_value = [0]  # 无孤立记录
        mock_session.execute.return_value = mock_result

        results = await quality_monitor._check_foreign_key_consistency(mock_session)

        assert isinstance(results, dict)
        assert "orphaned_home_teams" in results
        assert "orphaned_away_teams" in results
        assert "orphaned_odds" in results
        assert results["orphaned_home_teams"] == 0
        assert results["orphaned_away_teams"] == 0
        assert results["orphaned_odds"] == 0

    @pytest.mark.asyncio
    async def test_check_foreign_key_consistency_with_errors(self, quality_monitor, mock_session):
        """测试检查外键一致性（有错误）"""
        call_count = 0
        def execute_side_effect(query):
            nonlocal call_count
            call_count += 1
            mock_result = Mock()
            mock_result.first.return_value = [call_count * 5]  # 模拟不同的错误数量
            return mock_result

        mock_session.execute.side_effect = execute_side_effect

        results = await quality_monitor._check_foreign_key_consistency(mock_session)

        assert results["orphaned_home_teams"] == 5
        assert results["orphaned_away_teams"] == 10
        assert results["orphaned_odds"] == 15

    @pytest.mark.asyncio
    async def test_check_odds_consistency(self, quality_monitor, mock_session):
        """测试检查赔率一致性"""
        # Mock查询结果
        mock_result = Mock()
        mock_result.first.return_value = [0]  # 无无效赔率
        mock_session.execute.return_value = mock_result

        results = await quality_monitor._check_odds_consistency(mock_session)

        assert isinstance(results, dict)
        assert "invalid_odds_range" in results
        assert "invalid_probability_sum" in results
        assert results["invalid_odds_range"] == 0
        assert results["invalid_probability_sum"] == 0

    @pytest.mark.asyncio
    async def test_check_odds_consistency_with_errors(self, quality_monitor, mock_session):
        """测试检查赔率一致性（有错误）"""
        call_count = 0
        def execute_side_effect(query):
            nonlocal call_count
            call_count += 1
            mock_result = Mock()
            mock_result.first.return_value = [call_count * 2]  # 模拟错误数量
            return mock_result

        mock_session.execute.side_effect = execute_side_effect

        results = await quality_monitor._check_odds_consistency(mock_session)

        assert results["invalid_odds_range"] == 2
        assert results["invalid_probability_sum"] == 4

    @pytest.mark.asyncio
    async def test_check_match_status_consistency(self, quality_monitor, mock_session):
        """测试检查比赛状态一致性"""
        # Mock查询结果
        mock_result = Mock()
        mock_result.first.return_value = [0]  # 无不一致
        mock_session.execute.return_value = mock_result

        results = await quality_monitor._check_match_status_consistency(mock_session)

        assert isinstance(results, dict)
        assert "finished_matches_without_score" in results
        assert "scheduled_matches_with_score" in results
        assert results["finished_matches_without_score"] == 0
        assert results["scheduled_matches_with_score"] == 0

    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score(self, quality_monitor, mock_db_manager):
        """测试计算总体质量评分"""
        # Mock所有检查方法
        freshness_results = {
            "matches": DataFreshnessResult("matches", datetime.now(timezone.utc), 1000, 2.5, True, 24.0),
            "odds": DataFreshnessResult("odds", datetime.now(timezone.utc), 500, 0.5, True, 1.0),
        }

        completeness_results = {
            "matches": DataCompletenessResult("matches", 1000, {}, 0.0, 100.0),
            "odds": DataCompletenessResult("odds", 500, {"match_id": 2}, 0.004, 99.6),
        }

        consistency_results = {
            "foreign_key_consistency": {"orphaned_home_teams": 0, "orphaned_away_teams": 0, "orphaned_odds": 0},
            "odds_consistency": {"invalid_odds_range": 0, "invalid_probability_sum": 0},
            "match_status_consistency": {"finished_matches_without_score": 0, "scheduled_matches_with_score": 0},
        }

        with patch.object(quality_monitor, 'check_data_freshness', return_value=freshness_results), \
             patch.object(quality_monitor, 'check_data_completeness', return_value=completeness_results), \
             patch.object(quality_monitor, 'check_data_consistency', return_value=consistency_results):

            result = await quality_monitor.calculate_overall_quality_score()

            assert isinstance(result, dict)
            assert "overall_score" in result
            assert "freshness_score" in result
            assert "completeness_score" in result
            assert "consistency_score" in result
            assert "quality_level" in result
            assert "check_time" in result

            # 验证评分范围
            assert 0 <= result["overall_score"] <= 100
            assert 0 <= result["freshness_score"] <= 100
            assert 0 <= result["completeness_score"] <= 100
            assert 0 <= result["consistency_score"] <= 100

    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score_with_errors(self, quality_monitor):
        """测试计算总体质量评分（有错误）"""
        with patch.object(quality_monitor, 'check_data_freshness', side_effect=Exception("DB error")):
            result = await quality_monitor.calculate_overall_quality_score()

            assert result["overall_score"] == 0
            assert "error" in result

    @pytest.mark.asyncio
    async def test_get_quality_trends(self, quality_monitor):
        """测试获取质量趋势"""
        quality_data = {
            "overall_score": 85.0,
            "freshness_score": 90.0,
            "completeness_score": 80.0,
            "consistency_score": 85.0,
        }

        with patch.object(quality_monitor, 'calculate_overall_quality_score', return_value=quality_data):
            result = await quality_monitor.get_quality_trends(days=7)

            assert isinstance(result, dict)
            assert "current_quality" in result
            assert "trend_period_days" in result
            assert "trend_data" in result
            assert "recommendations" in result
            assert result["trend_period_days"] == 7

    def test_generate_quality_recommendations(self, quality_monitor):
        """测试生成质量改进建议"""
        # 优秀质量 - 无建议
        excellent_data = {
            "overall_score": 96,
            "freshness_score": 95,
            "completeness_score": 97,
            "consistency_score": 96,
        }
        recommendations = quality_monitor._generate_quality_recommendations(excellent_data)
        assert len(recommendations) == 0

        # 新鲜度低
        low_freshness_data = {
            "overall_score": 60,
            "freshness_score": 70,
            "completeness_score": 90,
            "consistency_score": 95,
        }
        recommendations = quality_monitor._generate_quality_recommendations(low_freshness_data)
        assert any("数据新鲜度较低" in rec for rec in recommendations)

        # 完整性低
        low_completeness_data = {
            "overall_score": 65,
            "freshness_score": 90,
            "completeness_score": 75,
            "consistency_score": 90,
        }
        recommendations = quality_monitor._generate_quality_recommendations(low_completeness_data)
        assert any("数据完整性有待提升" in rec for rec in recommendations)

        # 一致性低
        low_consistency_data = {
            "overall_score": 70,
            "freshness_score": 90,
            "completeness_score": 95,
            "consistency_score": 80,
        }
        recommendations = quality_monitor._generate_quality_recommendations(low_consistency_data)
        assert any("数据一致性存在问题" in rec for rec in recommendations)

        # 整体质量差
        poor_quality_data = {
            "overall_score": 40,
            "freshness_score": 50,
            "completeness_score": 45,
            "consistency_score": 60,
        }
        recommendations = quality_monitor._generate_quality_recommendations(poor_quality_data)
        assert any("整体数据质量需要重点关注" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_check_data_completeness_with_exception(self, quality_monitor, mock_session, mock_db_manager):
        """测试数据完整性检查异常处理"""
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        mock_session.execute.side_effect = Exception("Database error")

        results = await quality_monitor.check_data_completeness(["matches"])

        assert isinstance(results, dict)
        # 异常情况下应该返回空结果或默认结果

    @pytest.mark.asyncio
    async def test_check_data_consistency_with_exception(self, quality_monitor, mock_session, mock_db_manager):
        """测试数据一致性检查异常处理"""
        mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        mock_session.execute.side_effect = Exception("Database error")

        results = await quality_monitor.check_data_consistency()

        assert isinstance(results, dict)
        assert "foreign_key_consistency" in results
        assert "error" in results["foreign_key_consistency"]


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])