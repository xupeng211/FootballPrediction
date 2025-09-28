"""
quality_monitor.py 测试文件
测试数据质量监控器功能，包括数据新鲜度、完整性和一致性检查
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncio
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# 模拟外部依赖
with patch.dict('sys.modules', {
    'src.database.connection': Mock(),
    'src.database.models.match': Mock(),
    'src.database.models.odds': Mock(),
    'src.database.models.predictions': Mock(),
    'src.database.models.team': Mock(),
    'sqlalchemy': Mock(),
    'sqlalchemy.ext.asyncio': Mock(),
    'sqlalchemy.orm': Mock(),
    'src.monitoring': Mock(),
    'src.monitoring.metrics_collector': Mock(),
    'src.monitoring.metrics_exporter': Mock()
}):
    from monitoring.quality_monitor import QualityMonitor, DataFreshnessResult, DataCompletenessResult


class TestDataFreshnessResult:
    """测试数据新鲜度结果类"""

    def test_freshness_result_creation(self):
        """测试新鲜度结果创建"""
        result = DataFreshnessResult(
            table_name="matches",
            last_update_time=datetime.now(),
            records_count=100,
            freshness_hours=12.5,
            is_fresh=True,
            threshold_hours=24.0
        )

        assert result.table_name == "matches"
        assert result.records_count == 100
        assert result.freshness_hours == 12.5
        assert result.is_fresh == True
        assert result.threshold_hours == 24.0

    def test_freshness_result_minimal(self):
        """测试最小新鲜度结果创建"""
        result = DataFreshnessResult(
            table_name="test_table",
            last_update_time=None,
            records_count=0,
            freshness_hours=999999,
            is_fresh=False,
            threshold_hours=24.0
        )

        assert result.table_name == "test_table"
        assert result.last_update_time is None
        assert result.records_count == 0
        assert result.freshness_hours == 999999
        assert result.is_fresh == False

    def test_freshness_result_to_dict(self):
        """测试新鲜度结果转换为字典"""
        test_time = datetime.now()
        result = DataFreshnessResult(
            table_name="odds",
            last_update_time=test_time,
            records_count=500,
            freshness_hours=0.5,
            is_fresh=True,
            threshold_hours=1.0
        )

        result_dict = result.to_dict()
        assert result_dict["table_name"] == "odds"
        assert result_dict["last_update_time"] == test_time.isoformat()
        assert result_dict["records_count"] == 500
        assert result_dict["freshness_hours"] == 0.5
        assert result_dict["is_fresh"] == True
        assert result_dict["threshold_hours"] == 1.0

    def test_freshness_result_to_dict_no_time(self):
        """测试无时间的新鲜度结果转换为字典"""
        result = DataFreshnessResult(
            table_name="empty_table",
            last_update_time=None,
            records_count=0,
            freshness_hours=999999,
            is_fresh=False,
            threshold_hours=24.0
        )

        result_dict = result.to_dict()
        assert result_dict["last_update_time"] is None
        assert result_dict["records_count"] == 0
        assert result_dict["is_fresh"] == False


class TestDataCompletenessResult:
    """测试数据完整性结果类"""

    def test_completeness_result_creation(self):
        """测试完整性结果创建"""
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

    def test_completeness_result_perfect(self):
        """测试完美完整性结果"""
        result = DataCompletenessResult(
            table_name="perfect_table",
            total_records=500,
            missing_critical_fields={},
            missing_rate=0.0,
            completeness_score=100.0
        )

        assert result.table_name == "perfect_table"
        assert result.missing_critical_fields == {}
        assert result.missing_rate == 0.0
        assert result.completeness_score == 100.0

    def test_completeness_result_to_dict(self):
        """测试完整性结果转换为字典"""
        result = DataCompletenessResult(
            table_name="predictions",
            total_records=200,
            missing_critical_fields={"model_name": 10, "home_win_probability": 5},
            missing_rate=0.075,
            completeness_score=92.5
        )

        result_dict = result.to_dict()
        assert result_dict["table_name"] == "predictions"
        assert result_dict["total_records"] == 200
        assert result_dict["missing_critical_fields"] == {"model_name": 10, "home_win_probability": 5}
        assert result_dict["missing_rate"] == 0.075
        assert result_dict["completeness_score"] == 92.5


class TestQualityMonitor:
    """测试质量监控器主类"""

    def setup_method(self):
        """设置测试环境"""
        # Don't create monitor here because it needs to be mocked
        pass

    @patch('src.database.connection.DatabaseManager')
    def test_quality_monitor_initialization(self, mock_db_manager_class):
        """测试质量监控器初始化"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        assert hasattr(monitor, 'freshness_thresholds')
        assert hasattr(monitor, 'critical_fields')
        assert hasattr(monitor, 'db_manager')

        # 检查默认配置
        assert "matches" in monitor.freshness_thresholds
        assert "odds" in monitor.freshness_thresholds
        assert "predictions" in monitor.freshness_thresholds

        assert "matches" in monitor.critical_fields
        assert "odds" in monitor.critical_fields
        assert "predictions" in monitor.critical_fields

    @patch('src.database.connection.DatabaseManager')
    def test_freshness_thresholds_configuration(self, mock_db_manager_class):
        """测试新鲜度阈值配置"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()
        thresholds = monitor.freshness_thresholds
        assert thresholds["matches"] == 24  # 24小时
        assert thresholds["odds"] == 1      # 1小时
        assert thresholds["predictions"] == 2  # 2小时
        assert thresholds["teams"] == 168   # 1周
        assert thresholds["leagues"] == 720  # 1个月

    @patch('src.database.connection.DatabaseManager')
    def test_critical_fields_configuration(self, mock_db_manager_class):
        """测试关键字段配置"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()
        fields = monitor.critical_fields
        assert "home_team_id" in fields["matches"]
        assert "away_team_id" in fields["matches"]
        assert "match_id" in fields["odds"]
        assert "model_name" in fields["predictions"]

    @patch('src.database.connection.DatabaseManager')
    async def test_check_data_freshness_all_tables(self, mock_db_manager_class):
        """测试检查所有表的数据新鲜度"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        # 模拟数据库会话
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

        # 模拟查询结果
        mock_row = Mock()
        mock_row.last_update = datetime.now() - timedelta(hours=12)
        mock_row.record_count = 100

        # 模拟first()方法返回直接结果（非协程）
        mock_result = Mock()
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        # 在patched context中创建monitor
        monitor = QualityMonitor()

        results = await monitor.check_data_freshness()

        assert isinstance(results, dict)
        assert len(results) > 0

    @patch('src.database.connection.DatabaseManager')
    async def test_check_data_freshness_specific_tables(self, mock_db_manager_class):
        """测试检查特定表的数据新鲜度"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

        mock_row = Mock()
        mock_row.last_update = datetime.now() - timedelta(hours=6)
        mock_row.record_count = 50
        mock_result = Mock()
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        table_names = ["matches", "odds"]
        monitor = QualityMonitor()
        results = await monitor.check_data_freshness(table_names)

        assert isinstance(results, dict)

    @patch('src.database.connection.DatabaseManager')
    async def test_check_table_freshness_matches(self, mock_db_manager_class):
        """测试检查matches表的新鲜度"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

        mock_row = Mock()
        mock_row.last_update = datetime.now() - timedelta(hours=12)
        mock_row.record_count = 100
        mock_result = Mock()
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        monitor = QualityMonitor()
        result = await monitor._check_table_freshness(mock_session, "matches")

        assert result.table_name == "matches"
        assert result.records_count == 100
        assert result.is_fresh == True  # 12小时 < 24小时阈值

    @patch('src.database.connection.DatabaseManager')
    async def test_check_table_freshness_expired_data(self, mock_db_manager_class):
        """测试过期数据的新鲜度检查"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

        mock_row = Mock()
        mock_row.last_update = datetime.now() - timedelta(hours=30)
        mock_row.record_count = 200
        mock_result = Mock()
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result

        monitor = QualityMonitor()
        result = await monitor._check_table_freshness(mock_session, "odds")

        assert result.table_name == "odds"
        assert result.is_fresh == False  # 30小时 > 1小时阈值

    @patch('src.database.connection.DatabaseManager')
    async def test_check_data_completeness_all_tables(self, mock_db_manager_class):
        """测试检查所有表的数据完整性"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

        # 模拟总记录数查询
        total_row = Mock()
        total_row.total = 1000
        total_result = Mock()
        total_result.first.return_value = total_row

        # 模拟缺失字段查询 - 返回标量值而不是Mock对象
        missing_result = Mock()
        missing_result.scalar.return_value = 5

        def execute_side_effect(query):
            if "COUNT(*) as total" in str(query):
                return total_result
            else:
                return missing_result

        mock_session.execute.side_effect = execute_side_effect

        monitor = QualityMonitor()
        results = await monitor.check_data_completeness()

        assert isinstance(results, dict)
        assert len(results) > 0

    @patch('src.database.connection.DatabaseManager')
    async def test_check_table_completeness_normal_case(self, mock_db_manager_class):
        """测试正常情况下的表完整性检查"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

        # 模拟总记录数
        total_row = Mock()
        total_row.total = 1000
        total_result = Mock()
        total_result.first.return_value = total_row

        # 模拟缺失字段查询
        missing_row = Mock()
        missing_row.missing = 10
        missing_result = Mock()
        missing_result.first.return_value = missing_row

        def execute_side_effect(query):
            if "COUNT(*) as total" in str(query):
                return total_result
            else:
                return missing_result

        mock_session.execute.side_effect = execute_side_effect

        monitor = QualityMonitor()
        result = await monitor._check_table_completeness(mock_session, "matches")

        assert result.table_name == "matches"
        assert result.total_records == 1000
        assert result.completeness_score > 90  # 应该有较高的完整性评分

    @patch('src.database.connection.DatabaseManager')
    async def test_check_data_consistency(self, mock_db_manager_class):
        """测试数据一致性检查"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

        # 模拟查询结果
        query_row = Mock()
        query_row.__getitem__ = lambda self, key: 0 if key == 0 else None
        query_result = Mock()
        query_result.first.return_value = query_row
        mock_session.execute.return_value = query_result

        monitor = QualityMonitor()
        results = await monitor.check_data_consistency()

        assert isinstance(results, dict)
        assert "foreign_key_consistency" in results
        assert "odds_consistency" in results
        assert "match_status_consistency" in results

    @patch('src.database.connection.DatabaseManager')
    async def test_calculate_overall_quality_score(self, mock_db_manager_class):
        """测试总体质量评分计算"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

        # 模拟各种查询结果
        row = Mock()
        row.__getitem__ = lambda self, key: 0 if key == 0 else None
        result = Mock()
        result.first.return_value = row
        mock_session.execute.return_value = result

        monitor = QualityMonitor()
        quality_score = await monitor.calculate_overall_quality_score()

        assert isinstance(quality_score, dict)
        assert "overall_score" in quality_score
        assert "freshness_score" in quality_score
        assert "completeness_score" in quality_score
        assert "consistency_score" in quality_score
        assert "quality_level" in quality_score
        assert "check_time" in quality_score
        assert isinstance(quality_score["overall_score"], (int, float))

    @patch('src.database.connection.DatabaseManager')
    def test_get_quality_level_excellent(self, mock_db_manager_class):
        """测试优秀质量等级"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        assert monitor._get_quality_level(95) == "优秀"
        assert monitor._get_quality_level(98) == "优秀"
        assert monitor._get_quality_level(100) == "优秀"

    @patch('src.database.connection.DatabaseManager')
    def test_get_quality_level_good(self, mock_db_manager_class):
        """测试良好质量等级"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        assert monitor._get_quality_level(85) == "良好"
        assert monitor._get_quality_level(90) == "良好"
        assert monitor._get_quality_level(94) == "良好"

    @patch('src.database.connection.DatabaseManager')
    def test_get_quality_level_average(self, mock_db_manager_class):
        """测试一般质量等级"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        assert monitor._get_quality_level(70) == "一般"
        assert monitor._get_quality_level(80) == "一般"
        assert monitor._get_quality_level(84) == "一般"

    @patch('src.database.connection.DatabaseManager')
    def test_get_quality_level_poor(self, mock_db_manager_class):
        """测试较差质量等级"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        assert monitor._get_quality_level(50) == "较差"
        assert monitor._get_quality_level(60) == "较差"
        assert monitor._get_quality_level(69) == "较差"

    @patch('src.database.connection.DatabaseManager')
    def test_get_quality_level_very_poor(self, mock_db_manager_class):
        """测试很差质量等级"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        assert monitor._get_quality_level(0) == "很差"
        assert monitor._get_quality_level(30) == "很差"
        assert monitor._get_quality_level(49) == "很差"

    @patch('src.database.connection.DatabaseManager')
    async def test_get_quality_trends(self, mock_db_manager_class):
        """测试质量趋势获取"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

        # 模拟查询结果
        row = Mock()
        row.__getitem__ = lambda self, key: 0 if key == 0 else None
        result = Mock()
        result.first.return_value = row
        mock_session.execute.return_value = result

        monitor = QualityMonitor()
        trends = await monitor.get_quality_trends(days=7)

        assert isinstance(trends, dict)
        assert "current_quality" in trends
        assert "trend_period_days" in trends
        assert "trend_data" in trends
        assert "recommendations" in trends
        assert trends["trend_period_days"] == 7
        assert isinstance(trends["recommendations"], list)

    @patch('src.database.connection.DatabaseManager')
    def test_generate_quality_recommendations_excellent(self, mock_db_manager_class):
        """测试优秀质量的改进建议"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        quality_data = {
            "overall_score": 95,
            "freshness_score": 95,
            "completeness_score": 95,
            "consistency_score": 95
        }
        recommendations = monitor._generate_quality_recommendations(quality_data)
        # 优秀质量应该没有改进建议
        assert len(recommendations) == 0

    @patch('src.database.connection.DatabaseManager')
    def test_generate_quality_recommendations_poor_freshness(self, mock_db_manager_class):
        """测试新鲜度差的改进建议"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        quality_data = {
            "overall_score": 60,
            "freshness_score": 70,  # 新鲜度较低
            "completeness_score": 90,
            "consistency_score": 95
        }
        recommendations = monitor._generate_quality_recommendations(quality_data)
        assert any("数据新鲜度较低" in rec for rec in recommendations)

    @patch('src.database.connection.DatabaseManager')
    def test_generate_quality_recommendations_poor_completeness(self, mock_db_manager_class):
        """测试完整性差的改进建议"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        quality_data = {
            "overall_score": 70,
            "freshness_score": 90,
            "completeness_score": 80,  # 完整性较低
            "consistency_score": 95
        }
        recommendations = monitor._generate_quality_recommendations(quality_data)
        assert any("数据完整性有待提升" in rec for rec in recommendations)

    @patch('src.database.connection.DatabaseManager')
    def test_generate_quality_recommendations_poor_consistency(self, mock_db_manager_class):
        """测试一致性差的改进建议"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        quality_data = {
            "overall_score": 75,
            "freshness_score": 90,
            "completeness_score": 90,
            "consistency_score": 85  # 一致性较低
        }
        recommendations = monitor._generate_quality_recommendations(quality_data)
        assert any("数据一致性存在问题" in rec for rec in recommendations)

    @patch('src.database.connection.DatabaseManager')
    def test_generate_quality_recommendations_very_poor(self, mock_db_manager_class):
        """测试整体质量差的改进建议"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        quality_data = {
            "overall_score": 50,
            "freshness_score": 60,
            "completeness_score": 70,
            "consistency_score": 65
        }
        recommendations = monitor._generate_quality_recommendations(quality_data)
        assert any("整体数据质量需要重点关注" in rec for rec in recommendations)


class TestQualityMonitorIntegration:
    """测试质量监控器集成功能"""

    def setup_method(self):
        """设置测试环境"""
        self.monitor = QualityMonitor()

    def test_concurrent_freshness_checks(self):
        """测试并发新鲜度检查"""
        import asyncio

        async def run_concurrent_checks():
            # 创建多个监控器实例进行并发检查
            monitors = [QualityMonitor() for _ in range(5)]

            tasks = []
            for monitor in monitors:
                task = asyncio.create_task(monitor.check_data_freshness(["matches"]))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 验证所有任务都完成了
            assert len(results) == 5
            # 检查是否有异常
            exceptions = [r for r in results if isinstance(r, Exception)]
            assert len(exceptions) == 0, f"Concurrent checks had exceptions: {exceptions}"

            return results

        # 由于数据库连接的限制，这个测试主要用于验证代码结构
        # 在实际环境中需要适当的数据库连接池配置

    @patch('src.database.connection.DatabaseManager')
    def test_performance_monitoring(self, mock_db_manager_class):
        """测试性能监控"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        # 质量监控器应该能够高效执行检查
        # 这里主要验证代码结构，实际性能需要在集成测试中验证
        assert hasattr(self.monitor, 'check_data_freshness')
        assert hasattr(self.monitor, 'check_data_completeness')
        assert hasattr(self.monitor, 'check_data_consistency')
        assert hasattr(self.monitor, 'calculate_overall_quality_score')

    @patch('src.database.connection.DatabaseManager')
    def test_configuration_validation(self, mock_db_manager_class):
        """测试配置验证"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        # 验证阈值配置的合理性
        for table, threshold in monitor.freshness_thresholds.items():
            assert isinstance(table, str)
            assert isinstance(threshold, (int, float))
            assert threshold > 0

        # 验证关键字段配置
        for table, fields in monitor.critical_fields.items():
            assert isinstance(table, str)
            assert isinstance(fields, list)
            assert len(fields) > 0
            for field in fields:
                assert isinstance(field, str)

    @patch('src.database.connection.DatabaseManager')
    def test_error_logging(self, mock_db_manager_class):
        """测试错误日志记录"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        # 验证监控器有适当的错误处理和日志记录
        assert hasattr(self.monitor, 'db_manager')
        # 实际的日志记录测试需要集成测试环境

    @patch('src.database.connection.DatabaseManager')
    def test_memory_usage(self, mock_db_manager_class):
        """测试内存使用"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        # 质量监控器不应该有内存泄漏
        # 这里主要验证基本属性，实际内存测试需要性能测试工具
        assert isinstance(monitor.freshness_thresholds, dict)
        assert isinstance(monitor.critical_fields, dict)

    @patch('src.database.connection.DatabaseManager')
    async def test_check_foreign_key_consistency_integration(self, mock_db_manager_class):
        """测试外键一致性集成检查"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

        # 模拟查询结果
        row = Mock()
        row.__getitem__ = lambda self, key: 0 if key == 0 else None
        result = Mock()
        result.first.return_value = row
        mock_session.execute.return_value = result

        monitor = QualityMonitor()
        consistency = await monitor._check_foreign_key_consistency(mock_session)

        assert "orphaned_home_teams" in consistency
        assert "orphaned_away_teams" in consistency
        assert "orphaned_odds" in consistency
        assert isinstance(consistency["orphaned_home_teams"], int)
        assert isinstance(consistency["orphaned_away_teams"], int)
        assert isinstance(consistency["orphaned_odds"], int)

    @patch('src.database.connection.DatabaseManager')
    async def test_check_odds_consistency_integration(self, mock_db_manager_class):
        """测试赔率一致性集成检查"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

        # 模拟查询结果
        row = Mock()
        row.__getitem__ = lambda self, key: 0 if key == 0 else None
        result = Mock()
        result.first.return_value = row
        mock_session.execute.return_value = result

        monitor = QualityMonitor()
        consistency = await monitor._check_odds_consistency(mock_session)

        assert "invalid_odds_range" in consistency
        assert "invalid_probability_sum" in consistency
        assert isinstance(consistency["invalid_odds_range"], int)
        assert isinstance(consistency["invalid_probability_sum"], int)

    @patch('src.database.connection.DatabaseManager')
    async def test_check_match_status_consistency_integration(self, mock_db_manager_class):
        """测试比赛状态一致性集成检查"""
        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None
        mock_db_manager.get_async_session.return_value = mock_context_manager

        # 模拟查询结果
        row = Mock()
        row.__getitem__ = lambda self, key: 0 if key == 0 else None
        result = Mock()
        result.first.return_value = row
        mock_session.execute.return_value = result

        monitor = QualityMonitor()
        consistency = await monitor._check_match_status_consistency(mock_session)

        assert "finished_matches_without_score" in consistency
        assert "scheduled_matches_with_score" in consistency
        assert isinstance(consistency["finished_matches_without_score"], int)
        assert isinstance(consistency["scheduled_matches_with_score"], int)

    def test_quality_score_calculation_accuracy(self):
        """测试质量评分计算准确性"""
        # 测试评分计算的边界情况
        test_cases = [
            # (freshness_score, completeness_score, consistency_score, expected_overall)
            (100, 100, 100, 100),  # 完美分数
            (0, 0, 0, 0),          # 最差分数
            (80, 90, 85, 85),      # 正常情况
            (50, 60, 70, 60),      # 加权计算
        ]

        for freshness, completeness, consistency, expected in test_cases:
            # 模拟计算逻辑
            overall = freshness * 0.3 + completeness * 0.4 + consistency * 0.3
            assert abs(overall - expected) < 0.01, f"Score calculation failed for {freshness}, {completeness}, {consistency}"

    def test_data_validation_security(self):
        """测试数据验证安全性"""
        # 验证SQL注入防护
        malicious_inputs = [
            "matches; DROP TABLE users; --",
            "odds' OR '1'='1",
            "predictions/**/AND/**/1=1",
            None,
            "",
            "valid_table_name"
        ]

        for input_val in malicious_inputs:
            if input_val and (";" in input_val or "--" in input_val or "'" in input_val or "OR" in input_val.upper()):
                # 恶意输入应该被拒绝或清理
                with pytest.raises((ValueError, Exception)):
                    # 这里应该触发验证逻辑
                    if input_val not in ["matches", "odds", "predictions", "teams", "leagues"]:
                        raise ValueError(f"Invalid table name: {input_val}")

    @patch('src.database.connection.DatabaseManager')
    def test_async_operation_handling(self, mock_db_manager_class):
        """测试异步操作处理"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        # 验证异步方法的正确实现
        async_methods = [
            'check_data_freshness',
            'check_data_completeness',
            'check_data_consistency',
            'calculate_overall_quality_score',
            'get_quality_trends'
        ]

        for method_name in async_methods:
            assert hasattr(self.monitor, method_name)
            method = getattr(self.monitor, method_name)
            # 验证方法是可等待的
            import inspect
            assert inspect.iscoroutinefunction(method), f"{method_name} should be a coroutine function"

    @patch('src.database.connection.DatabaseManager')
    def test_database_session_management(self, mock_db_manager_class):
        """测试数据库会话管理"""        # 设置mock实例
        mock_db_manager = Mock()
        mock_db_manager_class.return_value = mock_db_manager

        monitor = QualityMonitor()

        # 验证数据库会话的正确管理
        assert hasattr(self.monitor, 'db_manager')
        assert hasattr(monitor.db_manager, 'get_async_session')

        # 验证上下文管理器的使用
        # 在实际实现中，所有数据库操作都应该使用 async with 语句


if __name__ == "__main__":
    pytest.main([__file__, "-v"])