from datetime import datetime

from src.monitoring.quality_monitor import (
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import os

"""
quality_monitor模块的基本测试
主要测试QualityMonitor类的基本功能以提升测试覆盖率
"""

    DataCompletenessResult,
    DataFreshnessResult,
    QualityMonitor)
@pytest.fixture
def mock_db_manager():
    """Fixture for a mocked DatabaseManager."""
    db_manager = MagicMock()
    mock_session = AsyncMock()
    async_context_manager = AsyncMock()
    async_context_manager.__aenter__.return_value = mock_session
    db_manager.get_async_session.return_value = async_context_manager
    return db_manager, mock_session
@pytest.fixture
def quality_monitor(mock_db_manager):
    """Returns a mocked instance of the QualityMonitor."""
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.database.connection.DatabaseManager[", lambda: mock_db_manager[0])": monitor = QualityMonitor()": yield monitor, mock_db_manager[1]": class TestQualityMonitor:"
    "]""测试QualityMonitor基本功能"""
    def test_quality_monitor_initialization(self, quality_monitor):
        """测试质量监控器初始化"""
        monitor, _ = quality_monitor
    assert monitor is not None
    assert hasattr(monitor, "freshness_thresholds[")" assert hasattr(monitor, "]critical_fields[")" assert hasattr(monitor, "]db_manager[")" def test_freshness_thresholds_config(self, quality_monitor):"""
        "]""测试新鲜度阈值配置"""
        monitor, _ = quality_monitor
    assert monitor.freshness_thresholds["matches["] ==24["]"]" assert monitor.freshness_thresholds["odds["] ==1["]"]" assert monitor.freshness_thresholds["predictions["] ==2["]"]" def test_critical_fields_config(self, quality_monitor):"
        """测试关键字段配置"""
        monitor, _ = quality_monitor
    assert "matches[" in monitor.critical_fields[""""
    assert "]]home_team_id[" in monitor.critical_fields["]matches["]: assert "]away_team_id[" in monitor.critical_fields["]matches["]""""
    @pytest.mark.asyncio
    async def test_check_data_freshness_basic(self, quality_monitor):
        "]""测试基本数据新鲜度检查"""
        monitor, _ = quality_monitor
        with patch.object(monitor, "_check_table_freshness[") as mock_check_freshness:": mock_check_freshness.return_value = DataFreshnessResult(": table_name = os.getenv("TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_46"),": last_update_time=datetime.now(),": records_count=100,": freshness_hours=12.0,"
                is_fresh=True,
                threshold_hours=24.0)
            await monitor.check_data_freshness("]matches[")": assert "]matches[" in results[""""
    assert isinstance(results["]]matches["], DataFreshnessResult)""""
    @pytest.mark.asyncio
    async def test_check_data_freshness_failure_fallback(self, quality_monitor):
        "]""当内部检查失败时返回默认失败结果"""
        monitor, _ = quality_monitor
        with patch.object(:
            monitor, "_check_table_freshness[", side_effect=RuntimeError("]boom[")""""
        ):
            results = await monitor.check_data_freshness("]matches[")": results["]matches["]: assert fallback.is_fresh is False[" assert fallback.records_count ==0["""
    assert fallback.freshness_hours ==999999
    @pytest.mark.asyncio
    async def test_check_data_completeness_basic(self, quality_monitor):
        "]]]""测试基本数据完整性检查"""
        monitor, _ = quality_monitor
        with patch.object(:
            monitor, "_check_table_completeness["""""
        ) as mock_check_completeness:
            mock_check_completeness.return_value = DataCompletenessResult(table_name = os.getenv("TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_46"),": total_records=100,": missing_critical_fields = {"]home_team_id[": 0),": missing_rate=0.0,": completeness_score=100.0)": await monitor.check_data_completeness("]matches[")": assert "]matches[" in results[""""
    assert isinstance(results["]]matches["], DataCompletenessResult)""""
    @pytest.mark.asyncio
    async def test_check_data_completeness_handles_error(self, quality_monitor):
        "]""当完整性检查抛出异常时记录错误"""
        monitor, _ = quality_monitor
        with patch.object(:
            monitor, "_check_table_completeness[", side_effect=RuntimeError("]fail[")""""
        ):
            await monitor.check_data_completeness("]matches[")": assert results =={}"""
    @pytest.mark.asyncio
    async def test_check_data_consistency_basic(self, quality_monitor):
        "]""测试基本数据一致性检查"""
        monitor, _ = quality_monitor
        with patch.object(:
            monitor, "_check_foreign_key_consistency["""""
        ) as mock_fk_check, patch.object(
            monitor, "]_check_odds_consistency["""""
        ) as mock_odds_check, patch.object(
            monitor, "]_check_match_status_consistency["""""
        ) as mock_status_check:
            mock_fk_check.return_value = {"]orphaned_home_teams[": 0}": mock_odds_check.return_value = {"]invalid_odds_range[": 0}": mock_status_check.return_value = {"]finished_matches_without_score[": 0}": await monitor.check_data_consistency()": assert isinstance(results, dict)" assert "]foreign_key_consistency[" in results[""""
    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score_basic(self, quality_monitor):
        "]]""测试计算总体质量评分"""
        monitor, _ = quality_monitor
        with patch.object(:
            monitor, "check_data_freshness["""""
        ) as mock_freshness, patch.object(
            monitor, "]check_data_completeness["""""
        ) as mock_completeness, patch.object(
            monitor, "]check_data_consistency["""""
        ) as mock_consistency:
            mock_freshness.return_value = {
                "]matches[": DataFreshnessResult("]matches[", datetime.now()": mock_completeness.return_value = {"""
                "]matches[": DataCompletenessResult("]matches[", 100, {"]home_team_id[": 0}, 0.0, 100.0[""""
                )
            mock_consistency.return_value = {
                "]]foreign_key_consistency[": {"]orphaned_home_teams[": 0},""""
                "]odds_consistency[": {"]invalid_odds_range[": 0},""""
                "]match_status_consistency[": {"]finished_matches_without_score[": 0}}": await monitor.calculate_overall_quality_score()": assert isinstance(result, dict)" assert "]overall_score[" in result[""""
    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score_handles_exception(
        self, quality_monitor
    ):
        "]]""当子检查失败时返回错误信息"""
        monitor, _ = quality_monitor
        with patch.object(:
            monitor, "check_data_freshness[", side_effect=RuntimeError("]boom[")""""
        ):
            await monitor.calculate_overall_quality_score()
    assert result["]overall_score["] ==0[" assert "]]error[" in result[""""
    def test_get_quality_level(self, quality_monitor):
        "]]""测试质量等级判断"""
        monitor, _ = quality_monitor
    assert monitor._get_quality_level(96) =="优秀[" assert monitor._get_quality_level(90) =="]良好[" assert monitor._get_quality_level(75) =="]一般[" assert monitor._get_quality_level(60) =="]较差[" assert monitor._get_quality_level(40) =="]很差[" def test_generate_quality_recommendations_alerts("
    """"
        "]""低评分时应生成改进建议"""
        monitor, _ = quality_monitor
        quality_data = {
            "freshness_score[": 70,""""
            "]completeness_score[": 80,""""
            "]consistency_score[": 85,""""
            "]overall_score[": 65}": monitor._generate_quality_recommendations(quality_data)": assert any("]新鲜度[" in note for note in suggestions)""""
    assert any("]完整性[" in note for note in suggestions)""""
    assert any("]整体数据质量[" in note for note in suggestions)""""
    @pytest.mark.asyncio
    async def test_get_quality_trends_basic(self, quality_monitor):
        "]""测试获取质量趋势"""
        monitor, _ = quality_monitor
        with patch.object(monitor, "calculate_overall_quality_score[") as mock_score:": mock_score.return_value = {"""
                "]overall_score[": 85.0,""""
                "]freshness_score[": 90.0,""""
                "]completeness_score[": 85.0,""""
                "]consistency_score[": 80.0}": await monitor.get_quality_trends(7)": assert isinstance(result, dict)" assert "]current_quality[" in result[""""
class TestDataResults:
    "]]""测试数据结果类"""
    def test_data_freshness_result_creation(self):
        """测试数据新鲜度结果创建"""
        DataFreshnessResult(
            table_name = os.getenv("TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_144"),": last_update_time=datetime.now(),": records_count=100,": freshness_hours=12.0,"
            is_fresh=True,
            threshold_hours=24.0)
    assert result.table_name =="]test_table[" def test_data_freshness_result_to_dict("
    """"
        "]""测试数据新鲜度结果转字典"""
        now = datetime.now()
        result = DataFreshnessResult(
            table_name = os.getenv("TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_144"),": last_update_time=now,": records_count=100,": freshness_hours=12.0,"
            is_fresh=True,
            threshold_hours=24.0)
        result.to_dict()
    assert isinstance(dict_result, dict)
    assert dict_result["]table_name["] =="]test_table[" def test_data_completeness_result_creation("
    """"
        "]""测试数据完整性结果创建"""
        DataCompletenessResult(table_name = os.getenv("TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_144"),": total_records=100,": missing_critical_fields = {"]field1[": 5, "]field2[": 0),": missing_rate=0.025,": completeness_score=97.5)": assert result.table_name =="]test_table[" def test_data_completeness_result_to_dict("
    """"
        "]""测试数据完整性结果转字典"""
        result = DataCompletenessResult(table_name = os.getenv("TEST_QUALITY_MONITOR_BASIC_TABLE_NAME_144"),": total_records=100,": missing_critical_fields = {"]field1[": 5),": missing_rate=0.05,": completeness_score=95.0)": result.to_dict()"
    assert isinstance(dict_result, dict)
    assert dict_result["]table_name["] =="]test_table"