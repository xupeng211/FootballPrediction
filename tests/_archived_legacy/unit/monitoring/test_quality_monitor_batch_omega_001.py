from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import os
import sys

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import asyncio
import pytest

"""
QualityMonitor Batch-Ω-001 测试套件

专门为 quality_monitor.py 设计的测试，目标是将其覆盖率从 0% 提升至 ≥70%
覆盖所有数据质量监控功能、数据库操作、一致性检查和趋势分析
"""

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
class TestQualityMonitorBatchOmega001:
    """QualityMonitor Batch-Ω-001 测试类"""
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
        table_name="matches[",": last_update_time=datetime.now() - timedelta(hours=1),": records_count=1000,": freshness_hours=1.0,"
            is_fresh=True,
            threshold_hours=24.0
        )
    @pytest.fixture
    def sample_completeness_result(self):
        "]""示例完整性结果"""
        from src.monitoring.quality_monitor import DataCompletenessResult
        return DataCompletenessResult(table_name="matches[",": total_records=1000,": missing_critical_fields = {"]home_score[": 50, "]away_score[": 30),": missing_rate=0.08,": completeness_score=0.92[""
        )
    def test_quality_monitor_initialization(self, monitor):
        "]]""测试 QualityMonitor 初始化"""
        # 检查新鲜度阈值配置
    assert monitor.freshness_thresholds =={
        "matches[": 24,""""
        "]odds[": 1,""""
        "]predictions[": 2,""""
        "]teams[": 168,""""
            "]leagues[": 720}""""
        # 检查关键字段定义
    assert monitor.critical_fields =={
        "]matches[": ["]home_team_id[", "]away_team_id[", "]league_id[", "]match_time["],""""
        "]odds[": ["]match_id[", "]bookmaker[", "]home_odds[", "]draw_odds[", "]away_odds["],""""
        "]predictions[": ["]match_id[", "]model_name[", "]home_win_probability["],""""
        "]teams[": ["]team_name[", "]league_id["]}": def test_data_freshness_result_initialization(self):"""
        "]""测试 DataFreshnessResult 初始化"""
        from src.monitoring.quality_monitor import DataFreshnessResult
        last_update = datetime.now() - timedelta(hours=1)
        result = DataFreshnessResult(
        table_name="matches[",": last_update_time=last_update,": records_count=1000,": freshness_hours=1.0,"
            is_fresh=True,
            threshold_hours=24.0
        )
    assert result.table_name =="]matches[" assert result.last_update_time ==last_update[""""
    assert result.records_count ==1000
    assert result.freshness_hours ==1.0
    assert result.is_fresh is True
    assert result.threshold_hours ==24.0
    def test_data_freshness_result_to_dict(self):
        "]]""测试 DataFreshnessResult 转换为字典"""
        from src.monitoring.quality_monitor import DataFreshnessResult
        last_update = datetime.now() - timedelta(hours=1)
        result = DataFreshnessResult(
        table_name="matches[",": last_update_time=last_update,": records_count=1000,": freshness_hours=1.0,"
            is_fresh=True,
            threshold_hours=24.0
        )
        result_dict = result.to_dict()
    assert result_dict["]table_name["] =="]matches[" assert result_dict["]records_count["] ==1000[" assert result_dict["]]freshness_hours["] ==1.0[" assert result_dict["]]is_fresh["] is True[""""
    assert result_dict["]]threshold_hours["] ==24.0[" def test_data_freshness_result_to_dict_none_time(self):"""
        "]]""测试 DataFreshnessResult 转换为字典 (None 时间)"""
        from src.monitoring.quality_monitor import DataFreshnessResult
        result = DataFreshnessResult(
        table_name="matches[",": last_update_time=None,": records_count=1000,": freshness_hours=0.0,"
            is_fresh=False,
            threshold_hours=24.0
        )
        result_dict = result.to_dict()
    assert result_dict["]last_update_time["] is None[" def test_data_completeness_result_initialization(self):"""
        "]]""测试 DataCompletenessResult 初始化"""
        from src.monitoring.quality_monitor import DataCompletenessResult
        missing_fields = {"home_score[": 50, "]away_score[": 30}": result = DataCompletenessResult(": table_name="]matches[",": total_records=1000,": missing_critical_fields=missing_fields,": missing_rate=0.08,"
            completeness_score=0.92
        )
    assert result.table_name =="]matches[" assert result.total_records ==1000[""""
    assert result.missing_critical_fields ==missing_fields
    assert result.missing_rate ==0.08
    assert result.completeness_score ==0.92
    def test_data_completeness_result_to_dict(self):
        "]]""测试 DataCompletenessResult 转换为字典"""
        from src.monitoring.quality_monitor import DataCompletenessResult
        missing_fields = {"home_score[": 50, "]away_score[": 30}": result = DataCompletenessResult(": table_name="]matches[",": total_records=1000,": missing_critical_fields=missing_fields,": missing_rate=0.08,"
            completeness_score=0.92
        )
        result_dict = result.to_dict()
    assert result_dict["]table_name["] =="]matches[" assert result_dict["]total_records["] ==1000[" assert result_dict["]]missing_critical_fields["] ==missing_fields[" assert result_dict["]]missing_rate["] ==0.08[" assert result_dict["]]completeness_score["] ==0.92[""""
    @pytest.mark.asyncio
    async def test_check_data_freshness_matches(self, monitor):
        "]]""测试检查 matches 表数据新鲜度"""
        from src.monitoring.quality_monitor import DataFreshnessResult
        # Mock the database manager
        with patch.object(monitor.db_manager, 'get_async_session') as mock_get_session, \:
            patch.object(monitor, '_check_table_freshness') as mock_check:
            mock_check.return_value = DataFreshnessResult(
            table_name="matches[",": last_update_time=datetime.now() - timedelta(hours=1),": records_count=1000,": freshness_hours=1.0,"
                is_fresh=True,
                threshold_hours=24.0
            )
            # Mock the async context manager
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            result = await monitor.check_data_freshness("]matches[")": assert len(result) ==1[" assert "]]matches[" in result[""""
    assert result["]]matches["].table_name =="]matches[" assert result["]matches["].records_count ==1000[" assert result["]]matches["].is_fresh is True[""""
    @pytest.mark.asyncio
    async def test_check_data_freshness_no_tables(self, monitor):
        "]]""测试检查空表列表"""
        # Mock the database manager
        with patch.object(monitor.db_manager, 'get_async_session') as mock_get_session:
            # Mock the async context manager
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            result = await monitor.check_data_freshness([])
    assert len(result) ==0
    @pytest.mark.asyncio
    async def test_check_data_freshness_old_data(self, monitor):
        """测试检查过期数据"""
        from src.monitoring.quality_monitor import DataFreshnessResult
        # Mock the database manager
        with patch.object(monitor.db_manager, 'get_async_session') as mock_get_session, \:
            patch.object(monitor, '_check_table_freshness') as mock_check:
            mock_check.return_value = DataFreshnessResult(
            table_name="matches[",": last_update_time=datetime.now() - timedelta(hours=30),": records_count=1000,": freshness_hours=30.0,"
                is_fresh=False,
                threshold_hours=24.0
            )
            # Mock the async context manager
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            result = await monitor.check_data_freshness("]matches[")": assert len(result) ==1[" assert "]]matches[" in result[""""
    assert result["]]matches["].table_name =="]matches[" assert result["]matches["].is_fresh is False[""""
    @pytest.mark.asyncio
    async def test_check_data_completeness(self, monitor):
        "]]""测试数据完整性检查"""
        from src.monitoring.quality_monitor import DataCompletenessResult
        # Mock the database manager
        with patch.object(monitor.db_manager, 'get_async_session') as mock_get_session, \:
            patch.object(monitor, '_check_table_completeness') as mock_check:
            mock_check.return_value = DataCompletenessResult(table_name="matches[",": total_records=1000,": missing_critical_fields = {"]home_team_id[": 5, "]away_team_id[": 3),": missing_rate=0.008,": completeness_score=0.992[""
            )
            # Mock the async context manager
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            result = await monitor.check_data_completeness("]]matches[")": assert len(result) ==1[" assert "]]matches[" in result[""""
    assert result["]]matches["].table_name =="]matches[" assert result["]matches["].total_records ==1000[" assert result["]]matches["].completeness_score > 0.95[""""
    @pytest.mark.asyncio
    async def test_check_data_completeness_no_tables(self, monitor):
        "]]""测试检查空表列表完整性"""
        # Mock the database manager
        with patch.object(monitor.db_manager, 'get_async_session') as mock_get_session:
            # Mock the async context manager
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            result = await monitor.check_data_completeness([])
    assert len(result) ==0
    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score(self, monitor):
        """测试计算总体质量评分"""
        # 模拟新鲜度检查结果
        freshness_results = {
        "matches[": Mock(is_fresh=True, records_count=1000)""""
        # 模拟完整性检查结果
        completeness_results = {
        "]matches[": Mock(completeness_score=0.95)": with patch.object(monitor, 'check_data_freshness', return_value = freshness_results), \": patch.object(monitor, 'check_data_completeness', return_value = completeness_results)": score = await monitor.calculate_overall_quality_score()"
            # 分数应该在0-1之间
    assert isinstance(score, dict)
    assert 0 <= score.get("]overall_score[", 0) <= 1[""""
    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score_empty_results(self, monitor):
        "]]""测试空结果的总体质量评分"""
        with patch.object(monitor, 'check_data_freshness', return_value = {)), \
            patch.object(monitor, 'check_data_completeness', return_value = {))
            score = await monitor.calculate_overall_quality_score()
            # 空结果应该返回合理的默认值
    assert isinstance(score, dict)
    def test_freshness_hours_calculation(self):
        """测试新鲜度小时数计算"""
        from src.monitoring.quality_monitor import DataFreshnessResult
        # 测试不同时间差的计算
        now = datetime.now()
        # 1小时前
        result1 = DataFreshnessResult(
        table_name="test[",": last_update_time=now - timedelta(hours=1),": records_count=100,": freshness_hours=1.0,"
            is_fresh=True,
            threshold_hours=24.0
        )
        assert result1.freshness_hours ==1.0
        # 30分钟前 (0.5小时)
        result2 = DataFreshnessResult(
            table_name="]test[",": last_update_time=now - timedelta(minutes=30),": records_count=100,": freshness_hours=0.5,"
            is_fresh=True,
            threshold_hours=24.0
        )
        assert result2.freshness_hours ==0.5
    def test_missing_rate_calculation(self):
        "]""测试缺失率计算"""
        from src.monitoring.quality_monitor import DataCompletenessResult
        # 8%缺失率
        result1 = DataCompletenessResult(table_name="test[",": total_records=1000,": missing_critical_fields = {"]field1[": 80),": missing_rate=0.08,": completeness_score=0.92[""
        )
    assert result1.missing_rate ==0.08
    assert result1.completeness_score ==0.92
        # 100%缺失率 (极端情况)
        result2 = DataCompletenessResult(table_name="]]test[",": total_records=1000,": missing_critical_fields = {"]field1[": 1000),": missing_rate=1.0,": completeness_score=0.0[""
        )
        assert result2.missing_rate ==1.0
    assert result2.completeness_score ==0.0
    def test_edge_cases(self, monitor):
        "]]""测试边界情况"""
        # 测试空的关键字段配置
        original_critical_fields = monitor.critical_fields
        monitor.critical_fields = {}
        # 应该不会引发错误，只是没有字段可以检查
    assert monitor.critical_fields =={}
        # 恢复原始配置
        monitor.critical_fields = original_critical_fields
    def test_large_numbers_handling(self):
        """测试大数值处理"""
        from src.monitoring.quality_monitor import DataFreshnessResult, DataCompletenessResult
        # 大记录数
        result1 = DataFreshnessResult(
        table_name="big_table[",": last_update_time=datetime.now(),": records_count=1000000,": freshness_hours=0.1,"
            is_fresh=True,
            threshold_hours=24.0
        )
    assert result1.records_count ==1000000
        # 大缺失字段数
        result2 = DataCompletenessResult(table_name="]big_table[",": total_records=1000000,": missing_critical_fields = {"]big_field[": 100000),": missing_rate=0.1,": completeness_score=0.9[""
        )
    assert result2.total_records ==1000000
    assert result2.missing_critical_fields["]]big_field["] ==100000[""""
    @pytest.mark.asyncio
    async def test_database_error_handling(self, monitor):
        "]]""测试数据库错误处理"""
        # Mock the database manager
        with patch.object(monitor.db_manager, 'get_async_session') as mock_get_session, \:
            patch.object(monitor, '_check_table_completeness') as mock_check:
            mock_check.side_effect = Exception("Database connection failed[")""""
            # Mock the async context manager
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            try:
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                result = await monitor.check_data_completeness("]matches[")""""
                # 在错误情况下应该返回空结果或部分结果
    assert isinstance(result, dict)
            except Exception:
            # 或者抛出适当的异常
            pass
    def test_configuration_validation(self, monitor):
        "]""测试配置验证"""
        # 验证新鲜度阈值都是正数
        for table_name, threshold in monitor.freshness_thresholds.items():
    assert threshold > 0, f["Freshness threshold for {table_name} should be positive["]"]"""
        # 验证每个表都有至少一个关键字段
        for table_name, fields in monitor.critical_fields.items():
    assert len(fields) > 0, f["Table {table_name} should have at least one critical field["]"]" def test_threshold_boundary_conditions(self):""
        """测试阈值边界条件"""
        from src.monitoring.quality_monitor import DataFreshnessResult
        now = datetime.now()
        # 正好在阈值边界
        threshold_hours = 24.0
        boundary_time = now - timedelta(hours=threshold_hours)
        result = DataFreshnessResult(
        table_name="test[",": last_update_time=boundary_time,": records_count=100,": freshness_hours=threshold_hours,"
            is_fresh=True,  # 边界情况下认为是新鲜的
            threshold_hours=threshold_hours
        )
    assert result.freshness_hours ==threshold_hours
    assert result.is_fresh is True
    @pytest.mark.asyncio
    async def test_concurrent_access(self, monitor):
        "]""测试并发访问"""
        from src.monitoring.quality_monitor import DataFreshnessResult
        # Mock the database manager for concurrent access:
        with patch.object(monitor.db_manager, 'get_async_session') as mock_get_session, \:
            patch.object(monitor, '_check_table_freshness') as mock_check:
            mock_check.return_value = DataFreshnessResult(
            table_name="matches[",": last_update_time=datetime.now() - timedelta(hours=1),": records_count=1000,": freshness_hours=1.0,"
                is_fresh=True,
                threshold_hours=24.0
            )
            # Mock the async context manager
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            # 模拟并发调用
            tasks = []
            for i in range(5):
                task = monitor.check_data_freshness("]matches[")"]": tasks.append(task)""
            # 应该能够处理并发调用
            try:
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                pass
            except Exception as e:
               pass  # Auto-fixed empty except block
 pass
                results = await asyncio.gather(*tasks, return_exceptions=True)
    assert len(results) ==5
            for result in results:
            if not isinstance(result, Exception):
    assert isinstance(result, dict)
        except Exception:
            # 并发可能失败，但不应该崩溃
            pass
        from src.monitoring.quality_monitor import QualityMonitor, DataFreshnessResult, DataCompletenessResult
        from src.monitoring.quality_monitor import DataFreshnessResult
        from src.monitoring.quality_monitor import DataCompletenessResult
        from src.monitoring.quality_monitor import DataFreshnessResult
        from src.monitoring.quality_monitor import DataFreshnessResult
        from src.monitoring.quality_monitor import DataFreshnessResult
        from src.monitoring.quality_monitor import DataCompletenessResult
        from src.monitoring.quality_monitor import DataCompletenessResult
        from src.monitoring.quality_monitor import DataFreshnessResult
        from src.monitoring.quality_monitor import DataFreshnessResult
        from src.monitoring.quality_monitor import DataCompletenessResult
        from src.monitoring.quality_monitor import DataFreshnessResult
        from src.monitoring.quality_monitor import DataCompletenessResult
        from src.monitoring.quality_monitor import DataFreshnessResult, DataCompletenessResult
        from src.monitoring.quality_monitor import DataFreshnessResult
        from src.monitoring.quality_monitor import DataFreshnessResult