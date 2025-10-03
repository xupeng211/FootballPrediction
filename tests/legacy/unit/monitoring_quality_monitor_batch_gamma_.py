from datetime import datetime
import os
import sys

from src.monitoring.quality_monitor import QualityMonitor, DataFreshnessResult
from unittest.mock import Mock, AsyncMock
import pytest

"""
QualityMonitor Batch-Γ-006 测试套件

专门为 quality_monitor.py 设计的测试，目标是将其覆盖率从 8% 提升至 ≥43%
覆盖所有质量监控功能、数据验证、异常检测、报告生成等
"""

# Add the project root to sys.path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
from src.monitoring.quality_monitor import QualityMonitor, DataFreshnessResult
class TestQualityMonitorBatchGamma006:
    """QualityMonitor Batch-Γ-006 测试类"""
    @pytest.fixture
    def quality_monitor(self):
        """创建质量监控器实例"""
        monitor = QualityMonitor()
        return monitor
    @pytest.fixture
    def sample_freshness_result(self):
        """示例新鲜度结果"""
        return DataFreshnessResult(
            table_name = os.getenv("MONITORING_QUALITY_MONITOR_BATCH_GAMMA__TABLE_NAME"),": last_update_time=datetime.now(),": records_count=1000,": freshness_hours=5.0,"
            is_fresh=True,
            threshold_hours=24.0)
    def test_quality_monitor_initialization(self, quality_monitor):
        "]""测试质量监控器初始化"""
        # 验证监控器初始化成功
        assert quality_monitor is not None
        # 验证数据新鲜度阈值配置
        assert isinstance(quality_monitor.freshness_thresholds, dict)
        assert "matches[" in quality_monitor.freshness_thresholds[""""
        assert "]]odds[" in quality_monitor.freshness_thresholds[""""
        assert "]]predictions[" in quality_monitor.freshness_thresholds[""""
        assert quality_monitor.freshness_thresholds["]]matches["] ==24[" assert quality_monitor.freshness_thresholds["]]odds["] ==1[""""
        # 验证关键字段定义
        assert isinstance(quality_monitor.critical_fields, dict)
        assert "]]matches[" in quality_monitor.critical_fields[""""
        assert "]]odds[" in quality_monitor.critical_fields[""""
        assert "]]predictions[" in quality_monitor.critical_fields[""""
        # 验证数据库管理器初始化
        assert quality_monitor.db_manager is not None
    def test_freshness_thresholds_configuration(self, quality_monitor):
        "]]""测试新鲜度阈值配置"""
        thresholds = quality_monitor.freshness_thresholds
        # 验证所有必需的阈值都存在
        expected_tables = ["matches[", "]odds[", "]predictions[", "]teams[", "]leagues["]": for table in expected_tables:": assert table in thresholds, f["]Missing threshold for table["] [{table}]" assert isinstance("""
                thresholds["]table[", (int, float)""""
            ), f["]Invalid threshold type for {table}"]:": assert thresholds["table[" > 0, f["]Threshold should be positive for {table}"] def test_critical_fields_configuration(self, quality_monitor)""""
        """测试关键字段配置"""
        critical_fields = quality_monitor.critical_fields
        # 验证所有必需表的字段定义
        expected_tables = ["matches[", "]odds[", "]predictions[", "]teams["]": for table in expected_tables:": assert (" table in critical_fields"
            ), f["]Missing critical fields for table["]: [{table}]:": assert isinstance(" critical_fields["]table[", list[""""
            ), f["]]Fields should be a list for {table}"]:": assert (" len(critical_fields["table[") > 0[""""
            ), f["]]Should have critical fields for {table}"]:": def test_get_quality_level(self, quality_monitor):"""
        """测试质量等级评估"""
        # 测试不同分数的等级评估
        assert quality_monitor._get_quality_level(95.0) =="优秀[" assert quality_monitor._get_quality_level(85.0) =="]良好[" assert quality_monitor._get_quality_level(75.0) =="]一般[" assert quality_monitor._get_quality_level(65.0) =="]较差[" assert quality_monitor._get_quality_level(0.0) =="]很差[" assert quality_monitor._get_quality_level(100.0) =="]优秀[" def test_get_quality_level_boundary_values("
    """"
        "]""测试质量等级边界值"""
        # 测试边界值
        assert quality_monitor._get_quality_level(95.0) =="优秀["  # 边界[" assert quality_monitor._get_quality_level(94.9) =="]]良好[" assert quality_monitor._get_quality_level(85.0) =="]良好["  # 边界[" assert quality_monitor._get_quality_level(84.9) =="]]一般[" assert quality_monitor._get_quality_level(70.0) =="]一般["  # 边界[" assert quality_monitor._get_quality_level(69.9) =="]]较差[" assert quality_monitor._get_quality_level(50.0) =="]较差["  # 边界[" assert quality_monitor._get_quality_level(49.9) =="]]很差[" def test_data_freshness_result_initialization("
    """"
        "]""测试DataFreshnessResult初始化"""
        result = DataFreshnessResult(
            table_name = os.getenv("MONITORING_QUALITY_MONITOR_BATCH_GAMMA__TABLE_NAME"),": last_update_time=datetime.now(),": records_count=500,": freshness_hours=2.5,"
            is_fresh=True,
            threshold_hours=24.0)
        # 验证所有属性正确设置
        assert result.table_name =="]test_table[" assert result.records_count ==500[""""
        assert result.freshness_hours ==2.5
        assert result.is_fresh is True
        assert result.threshold_hours ==24.0
    def test_data_freshness_result_to_dict(self, sample_freshness_result):
        "]]""测试DataFreshnessResult转换为字典"""
        result_dict = sample_freshness_result.to_dict()
        # 验证字典格式
        assert isinstance(result_dict, dict)
        assert "table_name[" in result_dict[""""
        assert "]]last_update_time[" in result_dict[""""
        assert "]]records_count[" in result_dict[""""
        assert "]]freshness_hours[" in result_dict[""""
        assert "]]is_fresh[" in result_dict[""""
        assert "]]threshold_hours[" in result_dict[""""
        assert result_dict["]]table_name["] =="]matches[" assert result_dict["]records_count["] ==1000[" assert result_dict["]]is_fresh["] is True[""""
        assert isinstance(result_dict["]]freshness_hours["], float)" assert result_dict["]freshness_hours["] ==round(" sample_freshness_result.freshness_hours, 2["""
        )
    def test_data_freshness_result_to_dict_with_none_time(self):
        "]]""测试DataFreshnessResult转换为字典 - 无时间戳"""
        result = DataFreshnessResult(
            table_name = os.getenv("MONITORING_QUALITY_MONITOR_BATCH_GAMMA__TABLE_NAME"),": last_update_time=None,": records_count=0,": freshness_hours=0.0,"
            is_fresh=False,
            threshold_hours=24.0)
        result_dict = result.to_dict()
        assert result_dict["]last_update_time["] is None[" def test_generate_quality_recommendations(self, quality_monitor):"""
        "]]""测试生成质量改进建议"""
        # Mock质量问题
        quality_issues = {
            "freshness_score[": 65.0,""""
            "]completeness_score[": 70.0,""""
            "]consistency_score[": 80.0}": result = quality_monitor._generate_quality_recommendations(quality_issues)"""
        # 验证改进建议结果
        assert isinstance(result, list)
        assert len(result) >= 1  # 应该至少有一个建议
        assert all(isinstance(rec, str) for rec in result)  # 所有建议都应该是字符串
    def test_generate_quality_recommendations_all_excellent(self, quality_monitor):
        "]""测试生成质量改进建议 - 全部优秀"""
        quality_issues = {
            "freshness_score[": 95.0,""""
            "]completeness_score[": 98.0,""""
            "]consistency_score[": 96.0}": result = quality_monitor._generate_quality_recommendations(quality_issues)"""
        # 验证优秀质量的处理
        assert isinstance(result, list)
        # 质量优秀时应该没有或很少建议
        assert len(result) <= 1
    def test_generate_quality_recommendations_all_poor(self, quality_monitor):
        "]""测试生成质量改进建议 - 全部较差"""
        quality_issues = {
            "freshness_score[": 30.0,""""
            "]completeness_score[": 25.0,""""
            "]consistency_score[": 35.0}": result = quality_monitor._generate_quality_recommendations(quality_issues)"""
        # 验证较差质量的处理
        assert isinstance(result, list)
        assert len(result) > 0  # 质量差时应该有建议
    def test_error_handling_strategies(self, quality_monitor):
        "]""测试错误处理策略"""
        # 验证监控器能够优雅地处理各种错误情况
        assert hasattr(quality_monitor, "freshness_thresholds[")" assert hasattr(quality_monitor, "]critical_fields[")" assert quality_monitor.freshness_thresholds is not None["""
        assert quality_monitor.critical_fields is not None
    def test_configuration_validation(self, quality_monitor):
        "]]""测试配置验证"""
        # 验证所有必需的配置都存在且格式正确
        assert isinstance(quality_monitor.freshness_thresholds, dict)
        assert isinstance(quality_monitor.critical_fields, dict)
        # 验证阈值都是正数
        for threshold in quality_monitor.freshness_thresholds.values():
            assert isinstance(threshold, (int, float))
            assert threshold > 0
        # 验证关键字段都是列表且不为空
        for fields in quality_monitor.critical_fields.values():
            assert isinstance(fields, list)
            assert len(fields) > 0
    def test_configuration_completeness(self, quality_monitor):
        """测试配置完整性"""
        # 验证新鲜度阈值配置完整性
        freshness_keys = set(quality_monitor.freshness_thresholds.keys())
        critical_keys = set(quality_monitor.critical_fields.keys())
        # 验证关键表都有配置
        essential_tables = {"matches[", "]odds[", "]predictions["}": assert essential_tables.issubset(" freshness_keys[""
        ), "]]Missing essential tables in freshness thresholds[": assert essential_tables.issubset(" critical_keys["""
        ), "]]Missing essential tables in critical fields[": def test_threshold_values_reasonable("
    """"
        "]""测试阈值设置的合理性"""
        # 验证阈值设置合理性
        assert (
            quality_monitor.freshness_thresholds["odds["]"]"""
            < quality_monitor.freshness_thresholds["matches["]"]"""
        )  # 赔率应该更频繁更新
        assert (
            quality_monitor.freshness_thresholds["predictions["]"]"""
            < quality_monitor.freshness_thresholds["matches["]"]"""
        )  # 预测应该更频繁更新
        assert (
            quality_monitor.freshness_thresholds["teams["]"]"""
            > quality_monitor.freshness_thresholds["matches["]"]"""
        )  # 球队数据更新频率较低
        assert (
            quality_monitor.freshness_thresholds["leagues["]"]"""
            > quality_monitor.freshness_thresholds["teams["]"]"""
        )  # 联赛数据更新频率最低
    def test_critical_fields_content(self, quality_monitor):
        """测试关键字段内容"""
        # 验证关键字段包含必要的字段
        matches_fields = quality_monitor.critical_fields["matches["]"]": assert any(""
            "team[": in field.lower() for field in matches_fields:""""
        ), "]Matches should have team-related fields[": assert any(""""
            "]time[": in field.lower() for field in matches_fields:""""
        ), "]Matches should have time-related fields[": odds_fields = quality_monitor.critical_fields["]odds["]: assert any(""""
            "]odds[": in field.lower() for field in odds_fields:""""
        ), "]Odds should have odds-related fields[": assert "]match_id[" in odds_fields, "]Odds should reference match_id["""""
    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score_basic(self, quality_monitor):
        "]""测试计算总体质量评分 - 基础版本"""
        # Mock子方法调用 - 返回对象而非字典
        quality_monitor.check_data_freshness = AsyncMock(return_value={
                "matches[": Mock(is_fresh=True, freshness_hours=5.0)""""
        )
        quality_monitor.check_data_completeness = AsyncMock(return_value={
                "]matches[": Mock(completeness_score=95.0)""""
        )
        quality_monitor.check_data_consistency = AsyncMock(return_value = {"]overall_consistency_score[": 88.0)""""
        )
        result = await quality_monitor.calculate_overall_quality_score()
        # 验证质量评分结果
        assert isinstance(result, dict)
        assert "]overall_score[" in result[""""
        assert "]]freshness_score[" in result[""""
        assert "]]completeness_score[" in result[""""
        assert "]]consistency_score[" in result[""""
        assert "]]quality_level[" in result[""""
        assert 0 <= result["]]overall_score["] <= 100[" assert result["]]quality_level["] in ["]优秀[", "]良好[", "]一般[", "]较差[", "]很差["]""""
    @pytest.mark.asyncio
    async def test_get_quality_trends_basic(self, quality_monitor):
        "]""测试获取质量趋势 - 基础版本"""
        # Mock子方法调用
        quality_monitor.calculate_overall_quality_score = AsyncMock(return_value={
                "overall_score[": 88.0,""""
                "]freshness_score[": 90.0,""""
                "]completeness_score[": 85.0,""""
                "]consistency_score[": 88.0,""""
                "]quality_level[": [良好])""""
        )
        result = await quality_monitor.get_quality_trends(days=7)
        # 验证趋势分析结果
        assert isinstance(result, dict)
        assert "]current_quality[" in result[""""
        assert "]]trend_period_days[" in result[""""
        assert "]]trend_data[" in result[""""
        assert "]]recommendations[" in result[""""
        assert result["]]trend_period_days["] ==7[" assert isinstance(result["]]trend_data["], list)" assert isinstance(result["]recommendations["], list)""""
    @pytest.mark.asyncio
    async def test_get_quality_trends_empty_data(self, quality_monitor):
        "]""测试获取质量趋势 - 空数据"""
        # Mock子方法调用
        quality_monitor.calculate_overall_quality_score = AsyncMock(return_value={
                "overall_score[": 0.0,""""
                "]freshness_score[": 0.0,""""
                "]completeness_score[": 0.0,""""
                "]consistency_score[": 0.0,""""
                "]quality_level[": [很差])""""
        )
        result = await quality_monitor.get_quality_trends(days=7)
        # 验证空数据处理
        assert isinstance(result, dict)
        assert "]current_quality[" in result[""""
        assert result["]]trend_period_days["] ==7[" assert result["]]current_quality["]"]overall_score[" ==0.0[""""
    @pytest.mark.asyncio
    async def test_get_quality_trends_single_data_point(self, quality_monitor):
        "]]""测试获取质量趋势 - 单个数据点"""
        # Mock子方法调用
        quality_monitor.calculate_overall_quality_score = AsyncMock(return_value={
                "overall_score[": 85.0,""""
                "]freshness_score[": 85.0,""""
                "]completeness_score[": 85.0,""""
                "]consistency_score[": 85.0,""""
                "]quality_level[": [良好])""""
        )
        result = await quality_monitor.get_quality_trends(days=7)
        # 验证单个数据处理
        assert isinstance(result, dict)
        assert "]current_quality[" in result[""""
        assert result["]]current_quality["]"]overall_score[" ==85.0[" assert result["]]trend_period_days"] ==7