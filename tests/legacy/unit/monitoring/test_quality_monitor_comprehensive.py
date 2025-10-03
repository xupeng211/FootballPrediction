from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import os
import sys

from unittest.mock import AsyncMock, MagicMock, Mock, patch
import asyncio
import pytest

"""
QualityMonitor 增强测试套件 - Phase 5.1 Batch-Δ-012

专门为 quality_monitor.py 设计的增强测试，目标是将其覆盖率从 8% 提升至 ≥70%
覆盖所有数据质量监控功能、数据库操作、一致性检查和趋势分析
"""

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
class TestQualityMonitorComprehensive:
    """QualityMonitor 综合测试类"""
    @pytest.fixture
    def monitor(self):
        """创建 QualityMonitor 实例"""
        from src.monitoring.quality_monitor import QualityMonitor, DataFreshnessResult, DataCompletenessResult
        monitor = QualityMonitor()
        return monitor
    @pytest.fixture
    def mock_session(self):
        """创建模拟数据库会话"""
        session = AsyncMock()
        return session
    @pytest.fixture
    def sample_freshness_result(self):
        """示例新鲜度结果"""
        from src.monitoring.quality_monitor import DataFreshnessResult
        return DataFreshnessResult(
        table_name = os.getenv("TEST_QUALITY_MONITOR_COMPREHENSIVE_TABLE_NAME_37"),": last_update_time=datetime.now() - timedelta(hours=1),": records_count=1000,": freshness_hours=1.0,"
            is_fresh=True,
            threshold_hours=24.0
        )
    @pytest.fixture
    def sample_completeness_result(self):
        "]""示例完整性结果"""
        from src.monitoring.quality_monitor import DataCompletenessResult
        return DataCompletenessResult(
        table_name = os.getenv("TEST_QUALITY_MONITOR_COMPREHENSIVE_TABLE_NAME_37"),": total_records=1000,": complete_records=950,": missing_records=50,"
            completeness_rate=0.95,
            missing_fields=["]home_score[", "]away_score["],": is_complete=True["""
        )
    # === DataFreshnessResult 测试 ===
    def test_data_freshness_result_initialization(self, sample_freshness_result):
        "]]""测试 DataFreshnessResult 初始化"""
    assert sample_freshness_result.table_name =="matches[" assert sample_freshness_result.records_count ==1000[""""
    assert sample_freshness_result.is_fresh is True
    assert sample_freshness_result.threshold_hours ==24.0
    def test_data_freshness_result_to_dict(self, sample_freshness_result):
        "]]""测试 DataFreshnessResult 转字典"""
        result_dict = sample_freshness_result.to_dict()
    assert isinstance(result_dict, dict)
    assert result_dict["table_name["] =="]matches[" assert result_dict["]records_count["] ==1000[" assert result_dict["]]is_fresh["] is True[""""
    assert "]]last_update_time[" in result_dict[""""
    def test_data_freshness_result_with_none_time(self):
        "]]""测试 DataFreshnessResult 处理 None 时间"""
        from src.monitoring.quality_monitor import DataFreshnessResult
        result = DataFreshnessResult(
        table_name = os.getenv("TEST_QUALITY_MONITOR_COMPREHENSIVE_TABLE_NAME_37"),": last_update_time=None,": records_count=0,": freshness_hours=0.0,"
            is_fresh=False,
            threshold_hours=24.0
        )
        result_dict = result.to_dict()
    assert result_dict["]last_update_time["] is None[""""
    # === DataCompletenessResult 测试 ===
    def test_data_completeness_result_initialization(self, sample_completeness_result):
        "]]""测试 DataCompletenessResult 初始化"""
    assert sample_completeness_result.table_name =="matches[" assert sample_completeness_result.total_records ==1000[""""
    assert sample_completeness_result.completeness_rate ==0.95
    assert sample_completeness_result.is_complete is True
    def test_data_completeness_result_to_dict(self, sample_completeness_result):
        "]]""测试 DataCompletenessResult 转字典"""
        result_dict = sample_completeness_result.to_dict()
    assert isinstance(result_dict, dict)
    assert result_dict["table_name["] =="]matches[" assert result_dict["]total_records["] ==1000[" assert result_dict["]]completeness_rate["] ==0.95[" assert "]]home_score[" in result_dict["]missing_fields["]""""
    # === QualityMonitor 主要方法测试 ===
    @pytest.mark.asyncio
    async def test_check_data_freshness_basic(self, monitor, mock_session):
        "]""测试基础数据新鲜度检查"""
        # 模拟数据库查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = datetime.now() - timedelta(hours=1)
        mock_result.scalars.return_value.all.return_value = [1000]
        mock_session.execute.return_value = mock_result
        result = await monitor.check_data_freshness(mock_session)
    assert result is not None
    assert isinstance(result, dict)
    assert "tables[" in result[""""
    assert "]]summary[" in result[""""
    assert len(result["]]tables["]) >= 4  # matches, odds, predictions, teams[""""
    @pytest.mark.asyncio
    async def test_check_data_freshness_with_old_data(self, monitor, mock_session):
        "]]""测试过期数据的新鲜度检查"""
        # 模拟过期数据
        old_time = datetime.now() - timedelta(hours=48)
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = old_time
        mock_result.scalars.return_value.all.return_value = [1000]
        mock_session.execute.return_value = mock_result
        result = await monitor.check_data_freshness(mock_session)
    assert result is not None
        # 检查是否有表被标记为不新鲜
        tables = result["tables["]"]": has_stale_table = any(not table["is_fresh["] for table in tables)"]": assert has_stale_table[""
    @pytest.mark.asyncio
    async def test_check_data_freshness_with_no_data(self, monitor, mock_session):
        "]""测试无数据情况的新鲜度检查"""
        # 模拟无数据
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_result.scalars.return_value.all.return_value = [0]
        mock_session.execute.return_value = mock_result
        result = await monitor.check_data_freshness(mock_session)
    assert result is not None
        # 检查无数据表的处理
        tables = result["tables["]"]": has_no_data_table = any(table["records_count["] ==0 for table in tables)"]": assert has_no_data_table[""
    @pytest.mark.asyncio
    async def test_check_data_completeness_basic(self, monitor, mock_session):
        "]""测试基础数据完整性检查"""
        # 模拟完整性查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [1000, 950, 50]
        mock_session.execute.return_value = mock_result
        result = await monitor.check_data_completeness(mock_session)
    assert result is not None
    assert isinstance(result, dict)
    assert "tables[" in result[""""
    assert "]]summary[" in result[""""
    assert "]]overall_completeness_rate[" in result["]summary["]""""
    @pytest.mark.asyncio
    async def test_check_data_completeness_with_missing_data(self, monitor, mock_session):
        "]""测试缺失数据情况下的完整性检查"""
        # 模拟有缺失数据
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [1000, 800, 200]
        mock_session.execute.return_value = mock_result
        result = await monitor.check_data_completeness(mock_session)
    assert result is not None
        summary = result["summary["]"]": assert summary["overall_completeness_rate["] < 0.9  # 80% 完整性["]"]""
    @pytest.mark.asyncio
    async def test_check_data_consistency_basic(self, monitor, mock_session):
        """测试基础数据一致性检查"""
        # 模拟一致性查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [0, 0, 0]  # 无不一致
        mock_session.execute.return_value = mock_result
        result = await monitor.check_data_consistency(mock_session)
    assert result is not None
    assert isinstance(result, dict)
    assert "foreign_key_issues[" in result[""""
    assert "]]odds_consistency_issues[" in result[""""
    assert "]]match_status_consistency_issues[" in result[""""
    assert "]]overall_consistency_score[" in result[""""
    @pytest.mark.asyncio
    async def test_check_data_consistency_with_issues(self, monitor, mock_session):
        "]]""测试存在一致性问题的检查"""
        # 模拟存在一致性问题
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [5, 3, 2]  # 有不一致
        mock_session.execute.return_value = mock_result
        result = await monitor.check_data_consistency(mock_session)
    assert result is not None
    assert result["overall_consistency_score["] < 1.0["]"]" assert result["foreign_key_issues["] > 0["]"]""
    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score_basic(self, monitor, mock_session):
        """测试基础质量评分计算"""
        # 模拟各个质量指标查询
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.side_effect = [
        [1000, 950, 50],  # 完整性
        [0, 0, 0],        # 一致性
        [0.95, 0.98, 0.92]  # 其他指标
        ]
        mock_session.execute.return_value = mock_result
        result = await monitor.calculate_overall_quality_score(mock_session)
    assert result is not None
    assert isinstance(result, dict)
    assert "overall_score[" in result[""""
    assert "]]quality_level[" in result[""""
    assert "]]freshness_score[" in result[""""
    assert "]]completeness_score[" in result[""""
    assert "]]consistency_score[" in result[""""
    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score_with_poor_metrics(self, monitor, mock_session):
        "]]""测试质量指标较差的情况"""
        # 模拟较差的质量指标
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.side_effect = [
        [1000, 500, 500],  # 低完整性
        [50, 30, 20],     # 一致性问题
        [0.5, 0.4, 0.3]   # 其他指标较差
        ]
        mock_session.execute.return_value = mock_result
        result = await monitor.calculate_overall_quality_score(mock_session)
    assert result is not None
    assert result["overall_score["] < 0.5["]"]" assert result["quality_level["] in ["]Poor[", "]Fair["]""""
    @pytest.mark.asyncio
    async def test_get_quality_trends_basic(self, monitor, mock_session):
        "]""测试基础质量趋势分析"""
        # 模拟历史数据查询
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
        (datetime.now() - timedelta(days=i), 0.9 - i*0.05)
        for i in range(7):
        ]
        mock_session.execute.return_value = mock_result
        result = await monitor.get_quality_trends(7, mock_session)
    assert result is not None
    assert isinstance(result, dict)
    assert "trends[" in result[""""
    assert "]]summary[" in result[""""
    assert len(result["]]trends["]) ==7[""""
    @pytest.mark.asyncio
    async def test_get_quality_trends_with_improvement(self, monitor, mock_session):
        "]]""测试质量趋势改善的情况"""
        # 模拟改善的趋势
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
        (datetime.now() - timedelta(days=i), 0.5 + i*0.05)
        for i in range(7):
        ]
        mock_session.execute.return_value = mock_result
        result = await monitor.get_quality_trends(7, mock_session)
    assert result is not None
        summary = result["summary["]"]": assert "trend_direction[" in summary[""""
    assert summary["]]trend_direction["] =="]improving["""""
    # === 内部方法测试 ===
    def test_get_quality_level_excellent(self, monitor):
        "]""测试优秀质量等级"""
        level = monitor._get_quality_level(0.95)
    assert level =="Excellent[" def test_get_quality_level_good("
    """"
        "]""测试良好质量等级"""
        level = monitor._get_quality_level(0.85)
    assert level =="Good[" def test_get_quality_level_fair("
    """"
        "]""测试一般质量等级"""
        level = monitor._get_quality_level(0.70)
    assert level =="Fair[" def test_get_quality_level_poor("
    """"
        "]""测试较差质量等级"""
        level = monitor._get_quality_level(0.50)
    assert level =="Poor[" def test_get_quality_level_bad("
    """"
        "]""测试糟糕质量等级"""
        level = monitor._get_quality_level(0.20)
    assert level =="Bad[" def test_generate_quality_recommendations_excellent("
    """"
        "]""测试优秀质量的建议"""
        recommendations = monitor._generate_quality_recommendations(0.95, {))
    assert isinstance(recommendations, list)
    assert len(recommendations) >= 0
    def test_generate_quality_recommendations_poor(self, monitor):
        """测试较差质量的建议"""
        metrics = {
        "completeness_score[": 0.5,""""
        "]consistency_score[": 0.4,""""
        "]freshness_score[": 0.3[""""
        }
        recommendations = monitor._generate_quality_recommendations(0.4, metrics)
    assert isinstance(recommendations, list)
    assert len(recommendations) > 0
        # 检查是否包含具体建议
        has_completeness_rec = any("]]completeness[": in rec.lower() for rec in recommendations)": has_consistency_rec = any("]consistency[": in rec.lower() for rec in recommendations)": assert has_completeness_rec or has_consistency_rec["""
    # === 边界条件和异常处理测试 ===
    @pytest.mark.asyncio
    async def test_check_data_freshness_database_error(self, monitor, mock_session):
        "]]""测试数据库错误处理"""
        mock_session.execute.side_effect = Exception("Database error[")": result = await monitor.check_data_freshness(mock_session)": assert result is not None[" assert "]]error[" in result[""""
    @pytest.mark.asyncio
    async def test_check_data_completeness_database_error(self, monitor, mock_session):
        "]]""测试完整性检查的数据库错误处理"""
        mock_session.execute.side_effect = Exception("Database error[")": result = await monitor.check_data_completeness(mock_session)": assert result is not None[" assert "]]error[" in result[""""
    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score_error_handling(self, monitor, mock_session):
        "]]""测试质量评分计算的错误处理"""
        mock_session.execute.side_effect = Exception("Database error[")": result = await monitor.calculate_overall_quality_score(mock_session)": assert result is not None[" assert "]]overall_score[" in result[""""
    assert result["]]overall_score["] ==0.0[""""
    @pytest.mark.asyncio
    async def test_get_quality_trends_with_invalid_days(self, monitor, mock_session):
        "]]""测试无效天数参数的趋势分析"""
        result = await monitor.get_quality_trends(-1, mock_session)
    assert result is not None
    assert "error[" in result[""""
    @pytest.mark.asyncio
    async def test_get_quality_trends_database_error(self, monitor, mock_session):
        "]]""测试趋势分析的数据库错误处理"""
        mock_session.execute.side_effect = Exception("Database error[")": result = await monitor.get_quality_trends(7, mock_session)": assert result is not None[" assert "]]error[" in result[""""
    # === 性能测试 ===
    @pytest.mark.asyncio
    async def test_multiple_quality_checks_performance(self, monitor, mock_session):
        "]]""测试多次质量检查的性能"""
        import time
        # 模拟快速查询响应
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [1000, 950, 50]
        mock_session.execute.return_value = mock_result
        start_time = time.time()
        # 执行多次检查
        for _ in range(10):
        await monitor.check_data_freshness(mock_session)
        await monitor.check_data_completeness(mock_session)
        end_time = time.time()
        execution_time = end_time - start_time
        # 应该在合理时间内完成
    assert execution_time < 5.0
    # === 数据验证测试 ===
    def test_quality_score_validation(self, monitor):
        """测试质量分数验证"""
        # 测试边界值
    assert monitor._get_quality_level(1.0) =="Excellent[" assert monitor._get_quality_level(0.0) =="]Bad[" assert monitor._get_quality_level(1.1) =="]Excellent["  # 处理大于1的情况[" assert monitor._get_quality_level(-0.1) =="]]Bad["     # 处理负数[" def test_recommendations_content_validation(self, monitor):"""
        "]]""测试建议内容验证"""
        recommendations = monitor._generate_quality_recommendations(0.3, {
        "completeness_score[": 0.2,""""
        "]consistency_score[": 0.3,""""
        "]freshness_score[": 0.4[""""
        ))
    assert isinstance(recommendations, list)
        # 检查建议不为空且包含有用信息
        for rec in recommendations:
    assert isinstance(rec, str)
    assert len(rec.strip()) > 0
    # === 配置相关测试 ===
    def test_default_thresholds(self, monitor):
        "]]""测试默认阈值配置"""
        # 测试服务是否使用了合理的默认阈值
    assert hasattr(monitor, 'freshness_threshold_hours')
    assert hasattr(monitor, 'completeness_threshold')
    assert hasattr(monitor, 'consistency_threshold')
    # === 集成测试 ===
    @pytest.mark.asyncio
    async def test_full_quality_assessment_workflow(self, monitor, mock_session):
        """测试完整质量评估工作流"""
        # 模拟完整的质量评估查询
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.side_effect = [
        # Freshness
        datetime.now() - timedelta(hours=1),
        [1000],
        # Completeness
            [1000, 950, 50],
            # Consistency
            [0, 0, 0],
            # Quality score components
            [0.95, 0.98, 0.92],
            # Trends
            [(datetime.now() - timedelta(days = i), 0.9 - i*0.05) for i in range(7)]
        ]
        mock_session.execute.return_value = mock_result
        # 执行完整工作流
        freshness = await monitor.check_data_freshness(mock_session)
        completeness = await monitor.check_data_completeness(mock_session)
        consistency = await monitor.check_data_consistency(mock_session)
        quality_score = await monitor.calculate_overall_quality_score(mock_session)
        trends = await monitor.get_quality_trends(7, mock_session)
        # 验证所有结果
    assert all(result is not None for result in ["freshness[", completeness, consistency, quality_score, trends])" assert quality_score["]overall_score["] > 0.8[" assert "]]Excellent[" in quality_score["]quality_level["]: from src.monitoring.quality_monitor import QualityMonitor, DataFreshnessResult, DataCompletenessResult["]: from src.monitoring.quality_monitor import DataFreshnessResult"]: from src.monitoring.quality_monitor import DataCompletenessResult": from src.monitoring.quality_monitor import DataFreshnessResult"
        import time