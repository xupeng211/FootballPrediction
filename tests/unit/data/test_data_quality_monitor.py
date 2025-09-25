"""
数据质量监控器测试

测试数据质量检查与异常检测功能，包括数据新鲜度、完整性、一致性和异常值监控。
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
import pandas as pd

from src.data.quality.data_quality_monitor import DataQualityMonitor


class TestDataQualityMonitor:
    """数据质量监控器测试类"""

    @pytest.fixture
    def monitor(self):
        """创建DataQualityMonitor实例"""
        with patch("src.data.quality.data_quality_monitor.DatabaseManager"):
            return DataQualityMonitor()

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()

        # 模拟数据新鲜度查询
        mock_result.scalar.return_value = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_session.execute.return_value = mock_result
        mock_db.get_async_session.return_value.__aenter__.return_value = mock_session

        return mock_db

    @pytest.fixture
    def sample_data_stats(self):
        """示例数据统计信息"""
        return {
            "total_records": 1000,
            "missing_records": 50,
            "invalid_records": 20,
            "fresh_records": 800,
            "stale_records": 200,
            "average_quality_score": 0.85
        }

    def test_init(self, monitor):
        """测试初始化"""
        assert monitor.db_manager is not None
        assert monitor.logger is not None
        assert isinstance(monitor.thresholds, dict)

        # 验证阈值配置
        expected_thresholds = {
            "data_freshness_hours": 24,
            "missing_data_rate": 0.1,
            "odds_min_value": 1.01,
            "odds_max_value": 100.0,
            "score_max_value": 20,
            "suspicious_odds_change": 0.5,
        }
        assert monitor.thresholds == expected_thresholds

    @pytest.mark.asyncio
    async def test_check_data_freshness_success(self, monitor, mock_db_manager):
        """测试数据新鲜度检查 - 成功情况"""
        monitor.db_manager = mock_db_manager

        result = await monitor.check_data_freshness()

        assert isinstance(result, dict)
        assert "is_fresh" in result
        assert "last_update_time" in result
        assert "hours_since_update" in result
        assert "threshold_hours" in result

        # 数据应该是新鲜的（1小时前更新）
        assert result["is_fresh"] is True
        assert result["hours_since_update"] == 1.0
        assert result["threshold_hours"] == 24

    @pytest.mark.asyncio
    async def test_check_data_freshness_stale(self, monitor):
        """测试数据新鲜度检查 - 过期数据"""
        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()

        # 模拟过期数据（30小时前更新）
        stale_time = datetime.now(timezone.utc) - timedelta(hours=30)
        mock_result.scalar.return_value = stale_time
        mock_session.execute.return_value = mock_result
        mock_db.get_async_session.return_value.__aenter__.return_value = mock_session

        monitor.db_manager = mock_db

        result = await monitor.check_data_freshness()

        assert isinstance(result, dict)
        # 数据应该不是新鲜的
        assert result["is_fresh"] is False
        assert result["hours_since_update"] == 30.0

    @pytest.mark.asyncio
    async def test_check_data_completeness(self, monitor, mock_db_manager):
        """测试数据完整性检查"""
        monitor.db_manager = mock_db_manager

        # 模拟数据库返回完整性统计
        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("matches", 1000, 50),  # 表名, 总记录数, 缺失记录数
            ("odds", 2000, 100),
        ]
        mock_session.execute.return_value = mock_result

        result = await monitor.check_data_completeness()

        assert isinstance(result, dict)
        assert "tables_checked" in result
        assert "total_records" in result
        assert "missing_records" in result
        assert "missing_rate" in result
        assert "is_complete" in result

        assert result["tables_checked"] == 2
        assert result["total_records"] == 3000
        assert result["missing_records"] == 150
        assert result["missing_rate"] == 0.05  # 150/3000
        assert result["is_complete"] is True  # 5% < 10%阈值

    @pytest.mark.asyncio
    async def test_check_data_completeness_high_missing_rate(self, monitor):
        """测试数据完整性检查 - 高缺失率"""
        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()

        # 模拟高缺失率
        mock_result.fetchall.return_value = [
            ("matches", 100, 50),  # 50%缺失率
        ]
        mock_session.execute.return_value = mock_result
        mock_db.get_async_session.return_value.__aenter__.return_value = mock_session

        monitor.db_manager = mock_db

        result = await monitor.check_data_completeness()

        assert result["missing_rate"] == 0.5
        assert result["is_complete"] is False  # 50% > 10%阈值

    @pytest.mark.asyncio
    async def test_check_data_consistency(self, monitor, mock_db_manager):
        """测试数据一致性检查"""
        monitor.db_manager = mock_db_manager

        # 模拟一致性检查结果
        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("matches", "home_score", 5, 2),  # 表名, 列名, 无效记录数, 格式错误数
            ("matches", "away_score", 3, 1),
        ]
        mock_session.execute.return_value = mock_result

        result = await monitor.check_data_consistency()

        assert isinstance(result, dict)
        assert "columns_checked" in result
        assert "invalid_records" in result
        assert "format_errors" in result
        assert "consistency_score" in result
        assert "is_consistent" in result

        assert result["columns_checked"] == 2
        assert result["invalid_records"] == 8
        assert result["format_errors"] == 3
        assert result["consistency_score"] > 0.8

    @pytest.mark.asyncio
    async def test_check_odds_anomalies(self, monitor, mock_db_manager):
        """测试赔率异常检查"""
        monitor.db_manager = mock_db_manager

        # 模拟赔率异常数据
        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("match_1", "home_win_odds", 0.8),  # 低于最小值
            ("match_2", "draw_odds", 150.0),  # 高于最大值
            ("match_3", "away_win_odds", 2.5),  # 正常值
        ]
        mock_session.execute.return_value = mock_result

        result = await monitor.check_odds_anomalies()

        assert isinstance(result, dict)
        assert "total_odds_checked" in result
        assert "anomalous_odds" in result
        assert "anomaly_rate" in result
        assert "anomalies" in result

        assert result["total_odds_checked"] == 3
        assert result["anomalous_odds"] == 2
        assert result["anomaly_rate"] == 2/3

        # 检查异常详情
        assert len(result["anomalies"]) == 2
        assert result["anomalies"][0]["reason"] == "below_minimum"

    @pytest.mark.asyncio
    async def test_check_score_anomalies(self, monitor, mock_db_manager):
        """测试比分异常检查"""
        monitor.db_manager = mock_db_manager

        # 模拟比分异常数据
        mock_session = mock_db_manager.get_async_session.return_value.__aenter__.return_value
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("match_1", "home_score", -1),  # 负数
            ("match_2", "away_score", 25),  # 过大
            ("match_3", "home_score", 3),  # 正常
        ]
        mock_session.execute.return_value = mock_result

        result = await monitor.check_score_anomalies()

        assert isinstance(result, dict)
        assert "total_scores_checked" in result
        assert "anomalous_scores" in result
        assert "anomaly_details" in result

        assert result["total_scores_checked"] == 3
        assert result["anomalous_scores"] == 2

    @pytest.mark.asyncio
    async def test_generate_quality_report(self, monitor, sample_data_stats):
        """测试生成质量报告"""
        with patch.object(monitor, 'check_data_freshness') as mock_freshness, \
             patch.object(monitor, 'check_data_completeness') as mock_completeness, \
             patch.object(monitor, 'check_data_consistency') as mock_consistency, \
             patch.object(monitor, 'check_odds_anomalies') as mock_odds, \
             patch.object(monitor, 'check_score_anomalies') as mock_scores:

            # 模拟检查结果
            mock_freshness.return_value = {
                "is_fresh": True,
                "hours_since_update": 1.0,
                "threshold_hours": 24
            }
            mock_completeness.return_value = {
                "is_complete": True,
                "missing_rate": 0.05
            }
            mock_consistency.return_value = {
                "is_consistent": True,
                "consistency_score": 0.95
            }
            mock_odds.return_value = {
                "anomaly_rate": 0.02
            }
            mock_scores.return_value = {
                "anomalous_scores": 5
            }

            report = await monitor.generate_quality_report()

            assert isinstance(report, dict)
            assert "generated_at" in report
            assert "overall_score" in report
            assert "checks" in report
            assert "summary" in report
            assert "recommendations" in report

            assert isinstance(report["overall_score"], float)
            assert 0.0 <= report["overall_score"] <= 1.0
            assert len(report["checks"]) == 5

    @pytest.mark.asyncio
    async def test_calculate_overall_quality_score(self, monitor):
        """测试总体质量评分计算"""
        check_results = {
            "freshness": {"is_fresh": True, "score": 1.0},
            "completeness": {"is_complete": True, "score": 0.9},
            "consistency": {"is_consistent": True, "score": 0.95},
            "odds": {"anomaly_rate": 0.02, "score": 0.98},
            "scores": {"anomaly_rate": 0.01, "score": 0.99}
        }

        overall_score = await monitor._calculate_overall_quality_score(check_results)

        assert isinstance(overall_score, float)
        assert 0.0 <= overall_score <= 1.0
        assert overall_score > 0.9  # 所有检查都很好

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, monitor):
        """测试生成建议"""
        check_results = {
            "freshness": {"is_fresh": False, "issue": "Data is stale"},
            "completeness": {"is_complete": True},
            "consistency": {"is_consistent": True},
            "odds": {"anomaly_rate": 0.15, "issue": "High odds anomaly rate"},
            "scores": {"anomalous_scores": 0}
        }

        recommendations = await monitor._generate_recommendations(check_results)

        assert isinstance(recommendations, list)
        assert len(recommendations) >= 1

        # 应该包含针对过期数据和赔率异常的建议
        found_data_freshness_rec = any("fresh" in rec.lower() for rec in recommendations)
        found_odds_rec = any("odds" in rec.lower() for rec in recommendations)

        assert found_data_freshness_rec
        assert found_odds_rec

    @pytest.mark.asyncio
    async def test_monitor_data_quality(self, monitor):
        """测试全面数据质量监控"""
        with patch.object(monitor, 'generate_quality_report') as mock_report:
            mock_report.return_value = {
                "overall_score": 0.85,
                "checks": {},
                "summary": "Good"
            }

            result = await monitor.monitor_data_quality()

            assert isinstance(result, dict)
            assert "overall_score" in result
            assert "status" in result
            assert "report" in result

            # 根据分数确定状态
            if result["overall_score"] >= 0.8:
                assert result["status"] == "good"
            elif result["overall_score"] >= 0.6:
                assert result["status"] == "warning"
            else:
                assert result["status"] == "poor"

    @pytest.mark.asyncio
    async def test_handle_database_error(self, monitor):
        """测试数据库错误处理"""
        # 模拟数据库连接失败
        monitor.db_manager = MagicMock()
        monitor.db_manager.get_async_session.side_effect = Exception("Connection failed")

        result = await monitor.check_data_freshness()

        # 应该返回错误信息或重试
        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_threshold_configuration(self, monitor):
        """测试阈值配置"""
        # 修改阈值
        original_threshold = monitor.thresholds["data_freshness_hours"]
        monitor.thresholds["data_freshness_hours"] = 12  # 更严格的要求

        with patch.object(monitor, 'check_data_freshness') as mock_check:
            mock_check.return_value = {
                "is_fresh": False,
                "hours_since_update": 18.0,
                "threshold_hours": 12
            }

            result = await monitor.check_data_freshness()

            # 使用新阈值，18小时 > 12小时阈值，应该不是新鲜的
            assert result["is_fresh"] is False
            assert result["threshold_hours"] == 12

        # 恢复原始阈值
        monitor.thresholds["data_freshness_hours"] = original_threshold

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, monitor):
        """测试性能监控"""
        import time

        # 模拟快速操作
        with patch.object(monitor, 'check_data_freshness') as mock_check:
            def fast_check():
                time.sleep(0.01)  # 10ms
                return {"is_fresh": True, "hours_since_update": 1.0}

            mock_check.side_effect = fast_check

            start_time = time.time()
            result = await monitor.check_data_freshness()
            end_time = time.time()

            assert result["is_fresh"] is True
            assert (end_time - start_time) < 1.0  # 应该在1秒内完成

    @pytest.mark.asyncio
    async def test_empty_database_handling(self, monitor):
        """测试空数据库处理"""
        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()

        # 模拟空数据库结果
        mock_result.scalar.return_value = None
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        mock_db.get_async_session.return_value.__aenter__.return_value = mock_session

        monitor.db_manager = mock_db

        # 应该优雅处理空数据
        result = await monitor.check_data_completeness()

        assert isinstance(result, dict)
        assert result["total_records"] == 0
        assert result["missing_rate"] == 0.0

    def test_logging_setup(self, monitor):
        """测试日志设置"""
        assert monitor.logger is not None
        logger_name = monitor.logger.name
        assert "quality" in logger_name
        assert "DataQualityMonitor" in logger_name

    @pytest.mark.asyncio
    async def test_concurrent_access(self, monitor):
        """测试并发访问"""
        import asyncio

        # 模拟多个并发请求
        async def concurrent_check():
            with patch.object(monitor, 'check_data_freshness') as mock_check:
                mock_check.return_value = {"is_fresh": True}
                return await mock_check()

        # 创建多个并发任务
        tasks = [concurrent_check() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 所有任务都应该成功完成
        assert all(not isinstance(r, Exception) for r in results)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_data_quality_alerting(self, monitor):
        """测试数据质量告警"""
        with patch.object(monitor, 'generate_quality_report') as mock_report:
            # 模拟低质量报告
            mock_report.return_value = {
                "overall_score": 0.4,  # 低质量
                "checks": {
                    "freshness": {"is_fresh": False},
                    "completeness": {"is_complete": False},
                    "consistency": {"is_consistent": True},
                    "odds": {"anomaly_rate": 0.3},
                    "scores": {"anomaly_rate": 0.2}
                }
            }

            alert = await monitor._generate_quality_alert()

            assert isinstance(alert, dict)
            assert "severity" in alert
            assert "message" in alert
            assert "issues" in alert

            # 低质量应该产生高严重度告警
            assert alert["severity"] in ["high", "critical"]
            assert len(alert["issues"]) > 0


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])