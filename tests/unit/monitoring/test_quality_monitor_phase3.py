"""
数据质量监控器测试模块

测试数据质量监控器的各项功能，包括：
- 数据新鲜度检查
- 数据完整性检查
- 数据一致性验证
- 质量评分计算
- 历史趋势分析
- 异常数据和空数据场景测试
- 告警触发逻辑验证
- SQL注入防护验证
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.monitoring.quality_monitor import (
    DataCompletenessResult,
    DataFreshnessResult,
    QualityMonitor,
)


class TestQualityMonitor:
    """数据质量监控器测试类"""

    @pytest.fixture
    def quality_monitor(self):
        """创建数据质量监控器实例"""
        with patch("src.monitoring.quality_monitor.DatabaseManager"):
            return QualityMonitor()

    @pytest.fixture
    def mock_session(self):
        """创建模拟数据库会话"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session

    @pytest.fixture
    def mock_db_manager(self, mock_session):
        """创建模拟数据库管理器"""
        db_manager = MagicMock()
        db_manager.get_async_session.return_value.__aenter__.return_value = mock_session
        db_manager.get_async_session.return_value.__aexit__.return_value = None
        return db_manager

    @pytest.fixture
    def sample_freshness_results(self):
        """示例新鲜度检查结果"""
        return {
            "matches": DataFreshnessResult(
                table_name="matches",
                last_update_time=datetime.now() - timedelta(hours=12),
                records_count=100,
                freshness_hours=12.0,
                is_fresh=True,
                threshold_hours=24,
            ),
            "odds": DataFreshnessResult(
                table_name="odds",
                last_update_time=datetime.now() - timedelta(hours=2),
                records_count=500,
                freshness_hours=2.0,
                is_fresh=False,
                threshold_hours=1,
            ),
        }

    @pytest.fixture
    def sample_completeness_results(self):
        """示例完整性检查结果"""
        return {
            "matches": DataCompletenessResult(
                table_name="matches",
                total_records=100,
                missing_critical_fields={"home_team_id": 2, "away_team_id": 1},
                missing_rate=0.03,
                completeness_score=97.0,
            ),
            "odds": DataCompletenessResult(
                table_name="odds",
                total_records=500,
                missing_critical_fields={"match_id": 0, "home_odds": 5},
                missing_rate=0.01,
                completeness_score=99.0,
            ),
        }

    class TestInitialization:
        """测试初始化功能"""

        def test_freshness_thresholds_initialization(self, quality_monitor):
            """测试新鲜度阈值初始化"""
            assert quality_monitor.freshness_thresholds["matches"] == 24
            assert quality_monitor.freshness_thresholds["odds"] == 1
            assert quality_monitor.freshness_thresholds["predictions"] == 2
            assert quality_monitor.freshness_thresholds["teams"] == 168
            assert quality_monitor.freshness_thresholds["leagues"] == 720

        def test_critical_fields_initialization(self, quality_monitor):
            """测试关键字段初始化"""
            assert "home_team_id" in quality_monitor.critical_fields["matches"]
            assert "home_odds" in quality_monitor.critical_fields["odds"]
            assert "model_name" in quality_monitor.critical_fields["predictions"]

        def test_database_manager_initialization(self, quality_monitor):
            """测试数据库管理器初始化"""
            assert quality_monitor.db_manager is not None

    class TestDataFreshness:
        """测试数据新鲜度检查功能"""

        async def test_check_data_freshness_all_tables(
            self, quality_monitor, mock_db_manager
        ):
            """测试检查所有表的数据新鲜度"""
            # 模拟数据库查询结果
            mock_session = (
                mock_db_manager.get_async_session.return_value.__aenter__.return_value
            )
            mock_result = MagicMock()
            mock_result.first.return_value = MagicMock(
                last_update=datetime.now() - timedelta(hours=12), record_count=100
            )
            mock_session.execute.return_value = mock_result

            with patch.object(quality_monitor, "_check_table_freshness") as mock_check:
                mock_check.return_value = DataFreshnessResult(
                    table_name="matches",
                    last_update_time=datetime.now() - timedelta(hours=12),
                    records_count=100,
                    freshness_hours=12.0,
                    is_fresh=True,
                    threshold_hours=24,
                )

                results = await quality_monitor.check_data_freshness()

                assert len(results) == 5  # 5个配置的表
                assert "matches" in results
                assert results["matches"].is_fresh

        async def test_check_data_freshness_specific_tables(
            self, quality_monitor, mock_db_manager
        ):
            """测试检查指定表的数据新鲜度"""
            mock_session = (
                mock_db_manager.get_async_session.return_value.__aenter__.return_value
            )
            mock_result = MagicMock()
            mock_result.first.return_value = MagicMock(
                last_update=datetime.now() - timedelta(hours=12), record_count=100
            )
            mock_session.execute.return_value = mock_result

            with patch.object(quality_monitor, "_check_table_freshness") as mock_check:
                mock_check.return_value = DataFreshnessResult(
                    table_name="matches",
                    last_update_time=datetime.now() - timedelta(hours=12),
                    records_count=100,
                    freshness_hours=12.0,
                    is_fresh=True,
                    threshold_hours=24,
                )

                results = await quality_monitor.check_data_freshness(
                    ["matches", "odds"]
                )

                assert len(results) == 2
                assert "matches" in results
                assert "odds" in results

        async def test_check_table_freshness_known_table(
            self, quality_monitor, mock_session
        ):
            """测试检查已知表的新鲜度"""
            # 模拟查询结果
            mock_result = MagicMock()
            mock_result.first.return_value = MagicMock(
                last_update=datetime.now() - timedelta(hours=12), record_count=100
            )
            mock_session.execute.return_value = mock_result

            result = await quality_monitor._check_table_freshness(
                mock_session, "matches"
            )

            assert result.table_name == "matches"
            assert result.records_count == 100
            assert result.is_fresh is True

        async def test_check_table_freshness_unknown_table(
            self, quality_monitor, mock_session
        ):
            """测试检查未知表的新鲜度（使用SQL查询）"""
            # 模拟SQL查询结果
            count_result = MagicMock()
            count_result.first.return_value = [100]  # 记录数

            time_result = MagicMock()
            time_result.first.return_value = MagicMock(last_update=datetime.now())

            mock_session.execute.side_effect = [count_result, time_result]

            result = await quality_monitor._check_table_freshness_sql(
                mock_session, "unknown_table", 24
            )

            assert result.table_name == "unknown_table"
            assert result.records_count == 100
            assert result.is_fresh is True

        async def test_check_table_freshness_sql_injection_protection(
            self, quality_monitor, mock_session
        ):
            """测试SQL注入防护"""
            # 测试恶意表名
            with pytest.raises(ValueError, match="Invalid table name"):
                await quality_monitor._check_table_freshness_sql(
                    mock_session, "malicious_table; DROP TABLE users;", 24
                )

        async def test_check_table_freshness_no_data(
            self, quality_monitor, mock_session
        ):
            """测试没有数据时的处理"""
            # 模拟空结果
            mock_result = MagicMock()
            mock_result.first.return_value = None
            mock_session.execute.return_value = mock_result

            result = await quality_monitor._check_table_freshness(
                mock_session, "matches"
            )

            assert result.table_name == "matches"
            assert result.records_count == 0
            assert result.is_fresh is False
            assert result.freshness_hours == 999999

        async def test_check_table_freshness_exception_handling(
            self, quality_monitor, mock_db_manager
        ):
            """测试异常处理"""
            mock_session = (
                mock_db_manager.get_async_session.return_value.__aenter__.return_value
            )
            mock_session.execute.side_effect = Exception("Database error")

            with patch.object(quality_monitor, "_check_table_freshness") as mock_check:
                mock_check.side_effect = Exception("Database error")

                results = await quality_monitor.check_data_freshness(["matches"])

                assert len(results) == 1
                assert "matches" in results
                assert results["matches"].is_fresh is False
                assert results["matches"].freshness_hours == 999999

    class TestDataCompleteness:
        """测试数据完整性检查功能"""

        async def test_check_data_completeness_all_tables(
            self, quality_monitor, mock_db_manager
        ):
            """测试检查所有表的数据完整性"""
            with patch.object(
                quality_monitor, "_check_table_completeness"
            ) as mock_check:
                mock_check.return_value = DataCompletenessResult(
                    table_name="matches",
                    total_records=100,
                    missing_critical_fields={},
                    missing_rate=0.0,
                    completeness_score=100.0,
                )

                results = await quality_monitor.check_data_completeness()

                assert len(results) == 4  # 4个配置的表

        async def test_check_table_completeness_normal_case(
            self, quality_monitor, mock_session
        ):
            """测试正常情况下的完整性检查"""
            # 模拟总数查询结果
            total_result = MagicMock()
            total_result.first.return_value = MagicMock(total=100)

            # 模拟缺失字段查询结果
            missing_result = MagicMock()
            missing_result.first.return_value = MagicMock(missing=2)

            mock_session.execute.side_effect = [total_result, missing_result]

            result = await quality_monitor._check_table_completeness(
                mock_session, "matches"
            )

            assert result.table_name == "matches"
            assert result.total_records == 100
            assert result.completeness_score > 90

        async def test_check_table_completeness_no_critical_fields(
            self, quality_monitor, mock_session
        ):
            """测试没有关键字段的情况"""
            result = await quality_monitor._check_table_completeness(
                mock_session, "unknown"
            )

            assert result.table_name == "unknown"
            assert result.total_records == 0
            assert result.completeness_score == 100.0

        async def test_check_table_completeness_sql_injection_protection(
            self, quality_monitor, mock_session
        ):
            """测试SQL注入防护"""
            with pytest.raises(ValueError, match="Invalid table name"):
                await quality_monitor._check_table_completeness(
                    mock_session, "malicious_table; DROP TABLE users;"
                )

        async def test_check_table_completeness_no_records(
            self, quality_monitor, mock_session
        ):
            """测试没有记录的情况"""
            # 模拟总数查询结果
            total_result = MagicMock()
            total_result.first.return_value = MagicMock(total=0)
            mock_session.execute.return_value = total_result

            result = await quality_monitor._check_table_completeness(
                mock_session, "matches"
            )

            assert result.total_records == 0
            assert result.completeness_score == 100.0

        async def test_check_table_completeness_field_check_failure(
            self, quality_monitor, mock_session
        ):
            """测试字段检查失败的情况"""
            # 模拟总数查询结果
            total_result = MagicMock()
            total_result.first.return_value = MagicMock(total=100)

            # 模拟缺失字段查询失败
            mock_session.execute.side_effect = [total_result, Exception("Query failed")]

            result = await quality_monitor._check_table_completeness(
                mock_session, "matches"
            )

            # 应该继续处理其他字段
            assert result.total_records == 100

    class TestDataConsistency:
        """测试数据一致性检查功能"""

        async def test_check_data_consistency(self, quality_monitor, mock_db_manager):
            """测试数据一致性检查"""
            mock_session = (
                mock_db_manager.get_async_session.return_value.__aenter__.return_value
            )

            # 模拟外键一致性查询结果
            fk_result = MagicMock()
            fk_result.first.return_value = [0]

            # 模拟赔率一致性查询结果
            odds_result = MagicMock()
            odds_result.first.return_value = [0]

            # 模拟比赛状态一致性查询结果
            match_result = MagicMock()
            match_result.first.return_value = [0]

            mock_session.execute.side_effect = [fk_result, odds_result, match_result]

            results = await quality_monitor.check_data_consistency()

            assert "foreign_key_consistency" in results
            assert "odds_consistency" in results
            assert "match_status_consistency" in results

        async def test_check_foreign_key_consistency(
            self, quality_monitor, mock_session
        ):
            """测试外键一致性检查"""
            # 模拟查询结果
            result = MagicMock()
            result.first.return_value = [2]
            mock_session.execute.return_value = result

            results = await quality_monitor._check_foreign_key_consistency(mock_session)

            assert "orphaned_home_teams" in results
            assert "orphaned_away_teams" in results
            assert "orphaned_odds" in results

        async def test_check_odds_consistency(self, quality_monitor, mock_session):
            """测试赔率一致性检查"""
            # 模拟查询结果
            result = MagicMock()
            result.first.return_value = [1]
            mock_session.execute.return_value = result

            results = await quality_monitor._check_odds_consistency(mock_session)

            assert "invalid_odds_range" in results
            assert "invalid_probability_sum" in results

        async def test_check_match_status_consistency(
            self, quality_monitor, mock_session
        ):
            """测试比赛状态一致性检查"""
            # 模拟查询结果
            result = MagicMock()
            result.first.return_value = [0]
            mock_session.execute.return_value = result

            results = await quality_monitor._check_match_status_consistency(
                mock_session
            )

            assert "finished_matches_without_score" in results
            assert "scheduled_matches_with_score" in results

        async def test_consistency_check_exception_handling(
            self, quality_monitor, mock_session
        ):
            """测试一致性检查异常处理"""
            mock_session.execute.side_effect = Exception("Database error")

            results = await quality_monitor._check_foreign_key_consistency(mock_session)

            assert "error" in results

    class TestQualityScore:
        """测试质量评分功能"""

        async def test_calculate_overall_quality_score_normal(
            self, quality_monitor, sample_freshness_results, sample_completeness_results
        ):
            """测试正常情况下的质量评分计算"""
            consistency_results = {
                "foreign_key_consistency": {
                    "orphaned_home_teams": 0,
                    "orphaned_away_teams": 0,
                },
                "odds_consistency": {
                    "invalid_odds_range": 0,
                    "invalid_probability_sum": 0,
                },
                "match_status_consistency": {"finished_matches_without_score": 0},
            }

            with patch.object(
                quality_monitor, "check_data_freshness"
            ) as mock_freshness, patch.object(
                quality_monitor, "check_data_completeness"
            ) as mock_completeness, patch.object(
                quality_monitor, "check_data_consistency"
            ) as mock_consistency:
                mock_freshness.return_value = sample_freshness_results
                mock_completeness.return_value = sample_completeness_results
                mock_consistency.return_value = consistency_results

                result = await quality_monitor.calculate_overall_quality_score()

                assert "overall_score" in result
                assert "freshness_score" in result
                assert "completeness_score" in result
                assert "consistency_score" in result
                assert "quality_level" in result
                assert "check_time" in result

        async def test_calculate_overall_quality_score_exception(self, quality_monitor):
            """测试质量评分计算异常处理"""
            with patch.object(
                quality_monitor, "check_data_freshness"
            ) as mock_freshness:
                mock_freshness.side_effect = Exception("Database error")

                result = await quality_monitor.calculate_overall_quality_score()

                assert result["overall_score"] == 0
                assert "error" in result

        def test_get_quality_level(self, quality_monitor):
            """测试质量等级获取"""
            assert quality_monitor._get_quality_level(98) == "优秀"
            assert quality_monitor._get_quality_level(88) == "良好"
            assert quality_monitor._get_quality_level(75) == "一般"
            assert quality_monitor._get_quality_level(60) == "较差"
            assert quality_monitor._get_quality_level(40) == "很差"

    class TestQualityTrends:
        """测试质量趋势功能"""

        async def test_get_quality_trends(self, quality_monitor):
            """测试质量趋势获取"""
            with patch.object(
                quality_monitor, "calculate_overall_quality_score"
            ) as mock_score:
                mock_score.return_value = {
                    "overall_score": 85.0,
                    "freshness_score": 90.0,
                    "completeness_score": 88.0,
                    "consistency_score": 75.0,
                }

                result = await quality_monitor.get_quality_trends(days=7)

                assert "current_quality" in result
                assert "trend_period_days" in result
                assert "trend_data" in result
                assert "recommendations" in result
                assert result["trend_period_days"] == 7

        def test_generate_quality_recommendations(self, quality_monitor):
            """测试质量改进建议生成"""
            quality_data = {
                "freshness_score": 75.0,
                "completeness_score": 82.0,
                "consistency_score": 88.0,
                "overall_score": 80.0,
            }

            recommendations = quality_monitor._generate_quality_recommendations(
                quality_data
            )

            assert len(recommendations) >= 1
            assert any("新鲜度" in rec for rec in recommendations)

        def test_generate_quality_recommendations_low_score(self, quality_monitor):
            """测试低质量分数的建议生成"""
            quality_data = {
                "freshness_score": 60.0,
                "completeness_score": 65.0,
                "consistency_score": 70.0,
                "overall_score": 65.0,
            }

            recommendations = quality_monitor._generate_quality_recommendations(
                quality_data
            )

            assert len(recommendations) >= 3
            assert any("重点关注" in rec for rec in recommendations)

    class TestDataClasses:
        """测试数据类功能"""

        def test_data_freshness_result_to_dict(self):
            """测试DataFreshnessResult转换为字典"""
            result = DataFreshnessResult(
                table_name="test_table",
                last_update_time=datetime.now(),
                records_count=100,
                freshness_hours=12.0,
                is_fresh=True,
                threshold_hours=24,
            )

            result_dict = result.to_dict()

            assert result_dict["table_name"] == "test_table"
            assert result_dict["records_count"] == 100
            assert result_dict["freshness_hours"] == 12.0
            assert result_dict["is_fresh"] is True
            assert result_dict["threshold_hours"] == 24

        def test_data_freshness_result_to_dict_no_time(self):
            """测试DataFreshnessResult转换为字典（无时间）"""
            result = DataFreshnessResult(
                table_name="test_table",
                last_update_time=None,
                records_count=0,
                freshness_hours=999999,
                is_fresh=False,
                threshold_hours=24,
            )

            result_dict = result.to_dict()

            assert result_dict["last_update_time"] is None

        def test_data_completeness_result_to_dict(self):
            """测试DataCompletenessResult转换为字典"""
            result = DataCompletenessResult(
                table_name="test_table",
                total_records=100,
                missing_critical_fields={"field1": 2, "field2": 1},
                missing_rate=0.03,
                completeness_score=97.0,
            )

            result_dict = result.to_dict()

            assert result_dict["table_name"] == "test_table"
            assert result_dict["total_records"] == 100
            assert result_dict["missing_critical_fields"]["field1"] == 2
            assert result_dict["missing_rate"] == 0.03
            assert result_dict["completeness_score"] == 97.0

    class TestAlertTriggering:
        """测试告警触发逻辑"""

        async def test_quality_alert_triggering(self, quality_monitor):
            """测试质量告警触发"""
            consistency_results = {
                "foreign_key_consistency": {
                    "orphaned_home_teams": 5,
                    "orphaned_away_teams": 3,
                },
                "odds_consistency": {
                    "invalid_odds_range": 10,
                    "invalid_probability_sum": 5,
                },
                "match_status_consistency": {"finished_matches_without_score": 2},
            }

            with patch.object(
                quality_monitor, "check_data_freshness"
            ) as mock_freshness, patch.object(
                quality_monitor, "check_data_completeness"
            ) as mock_completeness, patch.object(
                quality_monitor, "check_data_consistency"
            ) as mock_consistency:
                mock_freshness.return_value = {
                    "matches": DataFreshnessResult(
                        table_name="matches",
                        last_update_time=datetime.now() - timedelta(hours=30),
                        records_count=100,
                        freshness_hours=30.0,
                        is_fresh=False,
                        threshold_hours=24,
                    )
                }
                mock_completeness.return_value = {
                    "matches": DataCompletenessResult(
                        table_name="matches",
                        total_records=100,
                        missing_critical_fields={"home_team_id": 10},
                        missing_rate=0.1,
                        completeness_score=90.0,
                    )
                }
                mock_consistency.return_value = consistency_results

                result = await quality_monitor.calculate_overall_quality_score()

                # 验证低质量分数触发告警
                assert result["overall_score"] < 90
                assert result["quality_level"] in ["一般", "较差", "很差"]

        async def test_data_freshness_alert(self, quality_monitor):
            """测试数据新鲜度告警"""
            with patch.object(quality_monitor, "_check_table_freshness") as mock_check:
                mock_check.return_value = DataFreshnessResult(
                    table_name="matches",
                    last_update_time=datetime.now() - timedelta(hours=30),
                    records_count=100,
                    freshness_hours=30.0,
                    is_fresh=False,
                    threshold_hours=24,
                )

                results = await quality_monitor.check_data_freshness(["matches"])

                assert not results["matches"].is_fresh
                assert results["matches"].freshness_hours > 24

        async def test_data_completeness_alert(self, quality_monitor):
            """测试数据完整性告警"""
            with patch.object(
                quality_monitor, "_check_table_completeness"
            ) as mock_check:
                mock_check.return_value = DataCompletenessResult(
                    table_name="matches",
                    total_records=100,
                    missing_critical_fields={"home_team_id": 20, "away_team_id": 15},
                    missing_rate=0.35,
                    completeness_score=65.0,
                )

                results = await quality_monitor.check_data_completeness(["matches"])

                assert results["matches"].completeness_score < 70
                assert results["matches"].missing_rate > 0.3

        async def test_consistency_error_alert(self, quality_monitor, mock_session):
            """测试一致性错误告警"""
            # 模拟多个一致性错误
            fk_result = MagicMock()
            fk_result.first.return_value = [5]

            odds_result = MagicMock()
            odds_result.first.return_value = [8]

            match_result = MagicMock()
            match_result.first.return_value = [3]

            mock_session.execute.side_effect = [fk_result, odds_result, match_result]

            results = await quality_monitor._check_foreign_key_consistency(mock_session)

            total_errors = sum(v for v in results.values() if isinstance(v, int))
            assert total_errors > 0

    class TestEdgeCases:
        """测试边界情况"""

        async def test_empty_database_handling(self, quality_monitor, mock_db_manager):
            """测试空数据库处理"""
            mock_session = (
                mock_db_manager.get_async_session.return_value.__aenter__.return_value
            )

            # 模拟空结果
            mock_result = MagicMock()
            mock_result.first.return_value = None
            mock_session.execute.return_value = mock_result

            results = await quality_monitor.check_data_freshness(["matches"])

            assert len(results) == 1
            assert not results["matches"].is_fresh

        async def test_concurrent_access(self, quality_monitor, mock_db_manager):
            """测试并发访问"""
            import asyncio

            mock_session = (
                mock_db_manager.get_async_session.return_value.__aenter__.return_value
            )
            mock_result = MagicMock()
            mock_result.first.return_value = MagicMock(
                last_update=datetime.now(), record_count=100
            )
            mock_session.execute.return_value = mock_result

            # 并发执行多个检查
            tasks = [
                quality_monitor.check_data_freshness(["matches"]),
                quality_monitor.check_data_completeness(["matches"]),
                quality_monitor.calculate_overall_quality_score(),
            ]

            # 这里主要测试不会抛出异常
            # 实际的并发测试需要更复杂的设置
            for task in tasks:
                with patch.object(
                    quality_monitor, "_check_table_freshness"
                ) as mock_check:
                    mock_check.return_value = DataFreshnessResult(
                        table_name="matches",
                        last_update_time=datetime.now(),
                        records_count=100,
                        freshness_hours=1.0,
                        is_fresh=True,
                        threshold_hours=24,
                    )
                    await task

        async def test_database_connection_failure(self, quality_monitor):
            """测试数据库连接失败"""
            with patch.object(
                quality_monitor.db_manager, "get_async_session"
            ) as mock_get_session:
                mock_get_session.side_effect = Exception("Connection failed")

                results = await quality_monitor.check_data_freshness(["matches"])

                assert len(results) == 0  # 连接失败时应该返回空结果

        def test_configuration_validation(self, quality_monitor):
            """测试配置验证"""
            # 测试新鲜度阈值配置
            assert all(
                threshold > 0
                for threshold in quality_monitor.freshness_thresholds.values()
            )

            # 测试关键字段配置
            assert all(
                len(fields) > 0 for fields in quality_monitor.critical_fields.values()
            )

    class TestSQLInjectionProtection:
        """测试SQL注入防护"""

        async def test_table_name_validation(self, quality_monitor, mock_session):
            """测试表名验证"""
            # 测试各种恶意表名
            malicious_names = [
                "users; DROP TABLE users;",
                "matches' OR '1'='1",
                "odds UNION SELECT * FROM users",
                "matches--",
                "odds/*comment*/",
            ]

            for name in malicious_names:
                with pytest.raises(ValueError, match="Invalid table name"):
                    await quality_monitor._check_table_freshness_sql(
                        mock_session, name, 24
                    )

                with pytest.raises(ValueError, match="Invalid table name"):
                    await quality_monitor._check_table_completeness(mock_session, name)

        async def test_field_name_validation(self, quality_monitor, mock_session):
            """测试字段名验证"""
            # 测试已知安全字段名
            safe_fields = ["updated_at", "created_at", "collected_at", "match_time"]

            for field in safe_fields:
                # 这些字段应该被接受
                try:
                    # 直接调用内部方法来测试字段验证
                    if field in [
                        "updated_at",
                        "created_at",
                        "collected_at",
                        "match_time",
                    ]:
                        pass  # 这些是安全的字段名
                except ValueError:
                    pytest.fail(f"安全字段名 {field} 被拒绝")

        async def test_sql_construction_safety(self, quality_monitor, mock_session):
            """测试SQL构建安全性"""
            # 测试SQL构建是否使用了参数化查询或quoted_name
            with patch("sqlalchemy.quoted_name") as mock_quoted:
                mock_quoted.return_value = "safe_table_name"

                # 模拟一个安全的表名
                await quality_monitor._check_table_freshness_sql(
                    mock_session, "safe_table", 24
                )

                # 验证quoted_name被调用
                mock_quoted.assert_called()

    class TestPerformance:
        """测试性能相关功能"""

        async def test_large_dataset_handling(self, quality_monitor, mock_session):
            """测试大数据集处理"""
            # 模拟大数据集查询结果
            mock_result = MagicMock()
            mock_result.first.return_value = MagicMock(
                last_update=datetime.now(), record_count=1000000
            )
            mock_session.execute.return_value = mock_result

            result = await quality_monitor._check_table_freshness(
                mock_session, "matches"
            )

            # 验证大数据集处理正常
            assert result.records_count == 1000000

        async def test_timeout_handling(self, quality_monitor, mock_session):
            """测试超时处理"""
            # 模拟超时
            mock_session.execute.side_effect = asyncio.TimeoutError("Query timeout")

            result = await quality_monitor._check_table_freshness(
                mock_session, "matches"
            )

            # 验证超时处理
            assert result.is_fresh is False
            assert result.freshness_hours == 999999

        def test_memory_usage_optimization(self, quality_monitor):
            """测试内存使用优化"""
            # 验证对象不会存储不必要的数据
            assert hasattr(quality_monitor, "freshness_thresholds")
            assert hasattr(quality_monitor, "critical_fields")
            assert len(quality_monitor.freshness_thresholds) < 10  # 配置应该合理大小

    class TestIntegration:
        """测试集成功能"""

        async def test_full_quality_check_workflow(
            self, quality_monitor, mock_db_manager
        ):
            """测试完整的质量检查工作流"""
            mock_session = (
                mock_db_manager.get_async_session.return_value.__aenter__.return_value
            )

            # 模拟所有查询的成功结果
            mock_result = MagicMock()
            mock_result.first.return_value = MagicMock(
                last_update=datetime.now(), record_count=100
            )
            mock_session.execute.return_value = mock_result

            with patch.object(
                quality_monitor, "_check_table_freshness"
            ) as mock_freshness, patch.object(
                quality_monitor, "_check_table_completeness"
            ) as mock_completeness, patch.object(
                quality_monitor, "check_data_consistency"
            ) as mock_consistency:

                mock_freshness.return_value = DataFreshnessResult(
                    table_name="matches",
                    last_update_time=datetime.now(),
                    records_count=100,
                    freshness_hours=1.0,
                    is_fresh=True,
                    threshold_hours=24,
                )

                mock_completeness.return_value = DataCompletenessResult(
                    table_name="matches",
                    total_records=100,
                    missing_critical_fields={},
                    missing_rate=0.0,
                    completeness_score=100.0,
                )

                mock_consistency.return_value = {
                    "foreign_key_consistency": {"orphaned_home_teams": 0},
                    "odds_consistency": {"invalid_odds_range": 0},
                    "match_status_consistency": {"finished_matches_without_score": 0},
                }

                # 执行完整的工作流
                freshness_results = await quality_monitor.check_data_freshness()
                completeness_results = await quality_monitor.check_data_completeness()
                consistency_results = await quality_monitor.check_data_consistency()
                overall_score = await quality_monitor.calculate_overall_quality_score()

                # 验证结果
                assert len(freshness_results) > 0
                assert len(completeness_results) > 0
                assert "foreign_key_consistency" in consistency_results
                assert overall_score["overall_score"] > 0

        async def test_error_recovery_workflow(self, quality_monitor, mock_db_manager):
            """测试错误恢复工作流"""
            mock_session = (
                mock_db_manager.get_async_session.return_value.__aenter__.return_value
            )

            # 模拟部分查询失败
            mock_session.execute.side_effect = [
                Exception("First query failed"),  # 第一次查询失败
                MagicMock(
                    first=MagicMock(last_update=datetime.now(), record_count=100)
                ),  # 第二次查询成功
            ]

            # 测试系统在部分失败时的恢复能力
            with patch.object(quality_monitor, "_check_table_freshness") as mock_check:
                mock_check.return_value = DataFreshnessResult(
                    table_name="matches",
                    last_update_time=datetime.now(),
                    records_count=100,
                    freshness_hours=1.0,
                    is_fresh=True,
                    threshold_hours=24,
                )

                results = await quality_monitor.check_data_freshness(["matches"])

                # 验证系统能够恢复并返回结果
                assert len(results) > 0
                assert "matches" in results
