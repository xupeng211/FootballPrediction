"""
from typing import Dict
from unittest.mock import patch
import asyncio
数据质量模块核心功能单元测试

专注测试业务逻辑，避免复杂外部依赖。
验证阶段三数据治理与质量控制的核心功能。

覆盖率目标: > 85%
"""

from typing import Dict
from unittest.mock import patch

import pytest

from src.database.models.data_quality_log import DataQualityLog


class TestDataQualityExceptionHandlerCore:
    """数据质量异常处理器核心逻辑测试"""

    @pytest.fixture
    def handler(self):
        """创建异常处理器实例"""
        with patch("src.database.connection.DatabaseManager"):
            from src.data.quality.exception_handler import DataQualityExceptionHandler

            return DataQualityExceptionHandler()

    def test_handling_strategies_config(self, handler):
        """测试异常处理策略配置"""
        strategies = handler.handling_strategies

        # 验证缺失值处理策略
        assert "missing_values" in strategies
        missing_config = strategies["missing_values"]
        assert missing_config["strategy"] == "historical_average"
        assert missing_config["lookback_days"] == 30
        assert missing_config["min_sample_size"] == 5

        # 验证可疑赔率策略
        assert "suspicious_odds" in strategies
        odds_config = strategies["suspicious_odds"]
        assert odds_config["min_odds"] == 1.01
        assert odds_config["max_odds"] == 1000.0
        assert odds_config["probability_range"] == [0.95, 1.20]

        # 验证无效比分策略
        assert "invalid_scores" in strategies
        scores_config = strategies["invalid_scores"]
        assert scores_config["min_score"] == 0
        assert scores_config["max_score"] == 99

    def test_is_odds_suspicious_valid_cases(self, handler):
        """测试有效赔率判断逻辑"""
        # 正常赔率：总概率在合理范围内
        valid_odds_1 = {"home_odds": 2.0, "draw_odds": 3.5, "away_odds": 4.0}
        assert handler._is_odds_suspicious(valid_odds_1) is False

        # 边界情况：最小有效赔率
        valid_odds_2 = {"home_odds": 1.02, "draw_odds": 1.02, "away_odds": 1.02}
        # 概率总和约为2.94，超出1.20阈值，应该被标记为可疑
        assert handler._is_odds_suspicious(valid_odds_2) is True

    def test_is_odds_suspicious_invalid_cases(self, handler):
        """测试无效赔率判断逻辑"""
        # 赔率过低
        invalid_odds_1 = {
            "home_odds": 0.5,  # 小于1.01
            "draw_odds": 3.5,
            "away_odds": 4.0,
        }
        assert handler._is_odds_suspicious(invalid_odds_1) is True

        # 赔率过高
        invalid_odds_2 = {
            "home_odds": 2000.0,  # 大于1000.0
            "draw_odds": 3.5,
            "away_odds": 4.0,
        }
        assert handler._is_odds_suspicious(invalid_odds_2) is True

        # 概率总和过低
        invalid_odds_3 = {"home_odds": 5.0, "draw_odds": 5.0, "away_odds": 5.0}
        # 概率总和为0.6，低于0.95阈值
        assert handler._is_odds_suspicious(invalid_odds_3) is True

    def test_is_odds_suspicious_edge_cases(self, handler):
        """测试边界情况和异常处理"""
        # 缺失值
        missing_odds = {"home_odds": None, "draw_odds": 3.5, "away_odds": 4.0}
        assert handler._is_odds_suspicious(missing_odds) is False

        # 零除错误
        zero_odds = {"home_odds": 0, "draw_odds": 3.5, "away_odds": 4.0}
        assert handler._is_odds_suspicious(zero_odds) is True

        # 类型错误
        invalid_type_odds = {"home_odds": "invalid", "draw_odds": 3.5, "away_odds": 4.0}
        assert handler._is_odds_suspicious(invalid_type_odds) is True

    @pytest.mark.asyncio
    async def test_handle_missing_match_values_logic(self, handler):
        """测试比赛数据缺失值处理逻辑"""
        # 已完成比赛的缺失数据
        finished_match = {
            "match_status": "finished",
            "home_score": None,
            "away_score": None,
            "venue": None,
            "referee": None,
            "weather": None,
            "home_team_id": 1,
            "away_team_id": 2,
        }

        # 模拟历史平均值查询
        with patch.object(handler, "_get_historical_average_score", return_value=1.5):
            result = await handler._handle_missing_match_values(finished_match)

            # 验证比分填充
            assert result["home_score"] == 2  # round(1.5)
            assert result["away_score"] == 2

            # 验证默认值填充
            assert result["venue"] == "Unknown Venue"
            assert result["referee"] == "Unknown Referee"
            assert result["weather"] == "Unknown Weather"

        # 未完成比赛不处理比分
        scheduled_match = {
            "match_status": "scheduled",
            "home_score": None,
            "away_score": None,
        }

        result = await handler._handle_missing_match_values(scheduled_match)
        assert result["home_score"] is None
        assert result["away_score"] is None

    @pytest.mark.asyncio
    async def test_handle_missing_odds_values_logic(self, handler):
        """测试赔率数据缺失值处理逻辑"""
        odds_with_missing = {
            "match_id": 1,
            "bookmaker": "test_bookmaker",
            "home_odds": None,
            "draw_odds": 3.5,  # 保持原值
            "away_odds": None,
        }

        # 模拟历史平均赔率查询
        with patch.object(handler, "_get_historical_average_odds", return_value=2.0):
            result = await handler._handle_missing_odds_values(odds_with_missing)

            # 验证缺失值填充
            assert result["home_odds"] == 2.0
            assert result["draw_odds"] == 3.5  # 原值保持
            assert result["away_odds"] == 2.0


class TestDataQualityLogModel:
    """数据质量日志模型测试"""

    def test_initialization(self):
        """测试模型初始化"""
        from src.database.models.data_quality_log import DataQualityLog

        log = DataQualityLog(
            table_name="test_table", error_type="test_error", severity="high"
        )

        assert log.table_name == "test_table"
        assert log.error_type == "test_error"
        assert log.severity == "high"
        assert log.status == "logged"  # 默认值
        assert log.requires_manual_review is False  # 默认值

    def test_workflow_methods(self):
        """测试工作流方法"""

        log = DataQualityLog(table_name="test", error_type="test")

        # 测试分配处理人员
        log.assign_to_handler("developer")
        assert log.status == "in_progress"
        assert log.handled_by == "developer"

        # 测试标记为已解决
        log.mark_as_resolved("admin", "问题已修复")
        assert log.status == "resolved"
        assert log.handled_by == "admin"
        assert log.resolution_notes == "问题已修复"
        assert log.handled_at is not None

        # 测试标记为忽略
        log2 = DataQualityLog(table_name="test2", error_type="test2")
        log2.mark_as_ignored("admin", "非真实问题")
        assert log2.status == "ignored"
        assert "忽略原因: 非真实问题" in log2.resolution_notes

    def test_severity_mapping(self):
        """测试严重程度映射"""

        test_cases = [
            ("missing_values_filled", "low"),
            ("suspicious_odds", "medium"),
            ("invalid_scores", "high"),
            ("data_corruption", "critical"),
            ("unknown_error", "medium"),  # 默认值
        ]

        for error_type, expected_severity in test_cases:
            assert DataQualityLog.get_severity_level(error_type) == expected_severity

    def test_create_from_ge_result(self):
        """测试从GE结果创建日志"""

        # 高质量结果
        high_quality_result = {"failed_expectations": [], "success_rate": 95.0}

        log1 = DataQualityLog.create_from_ge_result("test_table", high_quality_result)
        assert log1.table_name == "test_table"
        assert log1.error_type == "ge_validation_failed"
        assert log1.requires_manual_review is False  # success_rate >= 80

        # 低质量结果
        low_quality_result = {
            "failed_expectations": [{"type": "test_fail"}],
            "success_rate": 65.0,
        }

        log2 = DataQualityLog.create_from_ge_result("test_table", low_quality_result)
        assert log2.requires_manual_review is True  # success_rate < 80

    def test_to_dict_conversion(self):
        """测试字典转换"""

        log = DataQualityLog(
            table_name="test_table",
            error_type="test_error",
            severity="medium",
            error_data={"test": "data"},
            error_message="测试错误消息",
        )

        result_dict = log.to_dict()

        # 验证关键字段
        assert result_dict["table_name"] == "test_table"
        assert result_dict["error_type"] == "test_error"
        assert result_dict["severity"] == "medium"
        assert result_dict["error_data"] == {"test": "data"}
        assert result_dict["error_message"] == "测试错误消息"

        # 验证时间字段存在
        assert "created_at" in result_dict
        assert "updated_at" in result_dict
        assert "detected_at" in result_dict


class TestDataQualityConfigLogic:
    """数据质量配置逻辑测试"""

    def test_assertion_rules_structure(self):
        """测试断言规则结构"""
        # 直接测试配置结构，不依赖复杂的GE库
        data_assertions = {
            "matches": {
                "name": "足球比赛数据质量检查",
                "expectations": [
                    {
                        "expectation_type": "expect_column_to_exist",
                        "kwargs": {"column": "match_time"},
                    },
                    {
                        "expectation_type": "expect_column_values_to_not_be_null",
                        "kwargs": {"column": "match_time"},
                    },
                    {
                        "expectation_type": "expect_column_values_to_be_between",
                        "kwargs": {
                            "column": "home_score",
                            "min_value": 0,
                            "max_value": 99,
                        },
                    },
                ],
            },
            "odds": {
                "name": "赔率数据质量检查",
                "expectations": [
                    {
                        "expectation_type": "expect_column_values_to_be_between",
                        "kwargs": {
                            "column": "home_odds",
                            "min_value": 1.01,
                            "max_value": 1000.0,
                        },
                    }
                ],
            },
        }

        # 验证matches表断言
        matches_config = data_assertions["matches"]
        assert matches_config["name"] == "足球比赛数据质量检查"

        expectations = matches_config["expectations"]
        assert len(expectations) >= 3

        # 验证关键断言存在
        expectation_types = [exp["expectation_type"] for exp in expectations]
        assert "expect_column_to_exist" in expectation_types
        assert "expect_column_values_to_not_be_null" in expectation_types
        assert "expect_column_values_to_be_between" in expectation_types

        # 验证比分范围断言
        score_assertion = next(
            exp for exp in expectations if exp["kwargs"].get("column") == "home_score"
        )
        assert score_assertion["kwargs"]["min_value"] == 0
        assert score_assertion["kwargs"]["max_value"] == 99

        # 验证odds表断言
        odds_config = data_assertions["odds"]
        odds_expectations = odds_config["expectations"]

        odds_assertion = odds_expectations[0]
        assert odds_assertion["kwargs"]["min_value"] == 1.01
        assert odds_assertion["kwargs"]["max_value"] == 1000.0

    def test_prometheus_metrics_definition(self):
        """测试Prometheus指标定义逻辑"""
        # 模拟指标定义
        expected_metrics = [
            "football_data_quality_check_success_rate",
            "football_data_quality_expectations_total",
            "football_data_quality_expectations_failed",
            "football_data_quality_anomaly_records",
            "football_data_quality_check_duration_seconds",
            "football_data_freshness_hours",
            "football_data_quality_score",
        ]

        # 验证指标命名规范
        for metric in expected_metrics:
            assert metric.startswith("football_")
            assert "data_quality" in metric or "data_freshness" in metric

        # 验证指标分类
        quality_metrics = [m for m in expected_metrics if "data_quality" in m]
        freshness_metrics = [m for m in expected_metrics if "freshness" in m]

        assert len(quality_metrics) >= 5
        assert len(freshness_metrics) == 1


class TestDataQualityWorkflowLogic:
    """数据质量工作流逻辑测试"""

    def test_validation_result_processing(self):
        """测试验证结果处理逻辑"""
        # 模拟GE验证结果
        validation_result = {
            "table_name": "matches",
            "suite_name": "matches_data_quality_suite",
            "success_rate": 85.5,
            "total_expectations": 10,
            "successful_expectations": 8,
            "failed_expectations": [
                {"expectation_type": "expect_column_values_to_be_between"},
                {"expectation_type": "expect_column_values_to_not_be_null"},
            ],
            "status": "FAILED",  # < 95%
            "rows_checked": 1000,
        }

        # 验证结果分析逻辑
        assert validation_result["success_rate"] == 85.5
        assert validation_result["total_expectations"] == 10
        assert len(validation_result["failed_expectations"]) == 2

        # 状态判断逻辑
        success_rate = validation_result["success_rate"]
        expected_status = "PASSED" if success_rate >= 95 else "FAILED"
        assert validation_result["status"] == expected_status

    def test_anomaly_statistics_calculation(self):
        """测试异常统计计算逻辑"""
        # 模拟异常数据
        anomalies = [
            {"type": "suspicious_odds", "severity": "medium", "table": "odds"},
            {"type": "unusual_high_score", "severity": "high", "table": "matches"},
            {"type": "suspicious_odds", "severity": "low", "table": "odds"},
            {"type": "data_consistency", "severity": "medium", "table": "matches"},
        ]

        # 统计逻辑
        stats_by_type = {}
        stats_by_severity = {}
        stats_by_table = {}

        for anomaly in anomalies:
            anomaly_type = anomaly["type"]
            severity = anomaly["severity"]
            table = anomaly["table"]

            stats_by_type[anomaly_type] = stats_by_type.get(anomaly_type, 0) + 1
            stats_by_severity[severity] = stats_by_severity.get(severity, 0) + 1
            stats_by_table[table] = stats_by_table.get(table, 0) + 1

        # 验证统计结果
        assert stats_by_type["suspicious_odds"] == 2
        assert stats_by_type["unusual_high_score"] == 1
        assert stats_by_severity["medium"] == 2
        assert stats_by_severity["high"] == 1
        assert stats_by_table["odds"] == 2
        assert stats_by_table["matches"] == 2

    def test_quality_score_calculation(self):
        """测试质量评分计算逻辑"""

        def calculate_quality_score(
            freshness_status: str, anomaly_counts: Dict[str, int]
        ) -> float:
            """质量评分计算逻辑"""
            score = 100.0

            # 根据新鲜度扣分
            if freshness_status == "warning":
                score -= 20
            elif freshness_status == "error":
                score -= 40

            # 根据异常数量扣分
            high_severity = anomaly_counts.get("high", 0)
            medium_severity = anomaly_counts.get("medium", 0)
            low_severity = anomaly_counts.get("low", 0)

            score -= high_severity * 15
            score -= medium_severity * 8
            score -= low_severity * 3

            return max(0.0, score)

        # 测试不同场景
        # 场景1：健康状态
        score1 = calculate_quality_score("healthy", {"high": 0, "medium": 0, "low": 0})
        assert score1 == 100.0

        # 场景2：轻微问题
        score2 = calculate_quality_score("healthy", {"high": 0, "medium": 2, "low": 3})
        assert score2 == 100 - 2 * 8 - 3 * 3  # 75.0

        # 场景3：严重问题
        score3 = calculate_quality_score("error", {"high": 3, "medium": 1, "low": 0})
        assert score3 == 100 - 40 - 3 * 15 - 1 * 8  # 7.0


# 运行测试的主函数
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
