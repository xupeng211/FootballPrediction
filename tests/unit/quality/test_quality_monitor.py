"""
Data Quality Monitor Unit Tests

测试数据质量监控器的单元测试，包括规则检查、批量处理、错误处理等功能。
使用 AsyncMock 模拟 FeatureStoreProtocol，测试各种场景。

测试覆盖范围：
- DataQualityMonitor 主类功能测试
- 4条默认规则的单元测试
- 错误处理和边界条件测试
- 性能和统计信息测试

生成时间: 2025-12-05
测试框架: pytest + AsyncMock
"""

import pytest
import asyncio
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from typing import Any

from src.quality.data_quality_monitor import DataQualityMonitor, DataQualityStats
from src.quality.quality_protocol import DataQualityRule
from src.quality.rules.missing_value_rule import MissingValueRule
from src.quality.rules.range_rule import RangeRule
from src.quality.rules.type_rule import TypeRule
from src.quality.rules.logical_relation_rule import LogicalRelationRule


class MockFeatureStore:
    """模拟 FeatureStoreProtocol 用于测试"""

    def __init__(self):
        self.features_data = {
            1: self._create_valid_features(),
            2: self._create_missing_value_features(),
            3: self._create_range_violation_features(),
            4: self._create_type_error_features(),
            5: self._create_logical_error_features(),
        }

    async def load_features(self, match_id: int) -> dict[str, Any]:
        """模拟特征数据加载"""
        return self.features_data.get(match_id)

    def _create_valid_features(self) -> dict[str, Any]:
        """创建有效的特征数据"""
        return {
            "match_id": 1,
            "full_time_score_home": 2,
            "full_time_score_away": 1,
            "half_time_score_home": 1,
            "half_time_score_away": 0,
            "xg_home": 1.5,
            "xg_away": 0.8,
            "xg_draw": 1.2,
            "shot_home": 15,
            "shot_away": 8,
            "shot_on_target_home": 6,
            "shot_on_target_away": 3,
            "possession_home": 60.0,
            "possession_away": 40.0,
            "corners_home": 6,
            "corners_away": 3,
            "fouls_home": 12,
            "fouls_away": 10,
            "cards_yellow_home": 2,
            "cards_yellow_away": 3,
            "cards_red_home": 0,
            "cards_red_away": 1,
            "odds_b365_home": 2.1,
            "odds_b365_draw": 3.4,
            "odds_b365_away": 3.8,
            "passes_home": 450,
            "passes_away": 380,
            "passes_accurate_home": 380,
            "passes_accurate_away": 320,
            "crosses_home": 8,
            "crosses_away": 5,
            "crosses_accurate_home": 3,
            "crosses_accurate_away": 2,
        }

    def _create_missing_value_features(self) -> dict[str, Any]:
        """创建包含缺失值的特征数据"""
        features = self._create_valid_features()
        features["xg_home"] = None  # 缺失值
        features["shot_away"] = ""  # 空字符串
        del features["corners_home"]  # 完全缺失字段
        return features

    def _create_range_violation_features(self) -> dict[str, Any]:
        """创建超出范围的错误特征数据"""
        features = self._create_valid_features()
        features["possession_home"] = 150.0  # 超出控球率范围
        features["full_time_score_home"] = -1  # 负分数
        features["cards_yellow_home"] = 20  # 黄牌数过多
        return features

    def _create_type_error_features(self) -> dict[str, Any]:
        """创建类型错误的特征数据"""
        features = self._create_valid_features()
        features["match_id"] = "not_a_number"  # 字符串而非数字
        features["xg_home"] = "1.5"  # 字符串而非浮点数
        features["shot_home"] = 15.5  # 浮点数而非整数
        return features

    def _create_logical_error_features(self) -> dict[str, Any]:
        """创建逻辑关系错误的特征数据"""
        features = self._create_valid_features()
        features["shot_home"] = 3  # 射门数小于进球数
        features["shot_on_target_home"] = 15  # 射正数大于总射门数
        features["possession_home"] = 30.0
        features["possession_away"] = 25.0  # 控球率总和不为100%
        return features


class TestDataQualityRule(DataQualityRule):
    """测试用的简单规则"""

    def __init__(self, should_fail: bool = False, delay_ms: float = 0):
        self.rule_name = "test_rule"
        self.rule_description = "测试规则"
        self.should_fail = should_fail
        self.delay_ms = delay_ms

    async def check(self, features: dict[str, Any]) -> list[str]:
        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000)

        if self.should_fail:
            return ["测试错误"]
        return []


@pytest.fixture
def mock_feature_store():
    """创建模拟的 FeatureStore"""
    return MockFeatureStore()


@pytest.fixture
def default_rules():
    """创建默认的4条规则"""
    return [MissingValueRule(), RangeRule(), TypeRule(), LogicalRelationRule()]


@pytest.fixture
def data_quality_monitor(mock_feature_store, default_rules):
    """创建数据质量监控器实例"""
    return DataQualityMonitor(
        rules=default_rules,
        feature_store=mock_feature_store,
        enable_stats=True,
        max_concurrent_checks=5,
    )


class TestDataQualityMonitor:
    """DataQualityMonitor 主类测试"""

    @pytest.mark.asyncio
    async def test_check_match_success(self, data_quality_monitor, mock_feature_store):
        """测试比赛检查成功场景"""
        # 使用有效数据 (match_id=1)
        result = await data_quality_monitor.check_match(1)

        # 验证结果结构
        assert "match_id" in result
        assert "passed" in result
        assert "results" in result
        assert "summary" in result
        assert "timestamp" in result
        assert "check_duration_ms" in result

        # 验证具体内容
        assert result["match_id"] == 1
        assert result["passed"]  # 应该通过所有检查
        assert len(result["results"]) == 4  # 4条规则
        assert result["summary"]["passed_rules"] == 4
        assert result["summary"]["failed_rules"] == 0

        # 验证每个规则的结果
        for rule_result in result["results"]:
            assert rule_result["passed"]
            assert len(rule_result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_check_match_failure_missing_values(
        self, data_quality_monitor, mock_feature_store
    ):
        """测试缺失值失败场景"""
        result = await data_quality_monitor.check_match(2)  # 缺失值数据

        assert not result["passed"]
        assert result["summary"]["failed_rules"] > 0

        # 检查是否捕获到缺失值错误
        missing_value_errors = []
        for rule_result in result["results"]:
            if rule_result["rule_name"] == "missing_value_check":
                missing_value_errors.extend(rule_result["errors"])

        assert len(missing_value_errors) > 0
        assert any("缺失" in error for error in missing_value_errors)

    @pytest.mark.asyncio
    async def test_check_match_failure_range_violation(
        self, data_quality_monitor, mock_feature_store
    ):
        """测试范围违规失败场景"""
        result = await data_quality_monitor.check_match(3)  # 范围违规数据

        assert not result["passed"]

        # 检查是否捕获到范围错误
        range_errors = []
        for rule_result in result["results"]:
            if rule_result["rule_name"] == "range_check":
                range_errors.extend(rule_result["errors"])

        assert len(range_errors) > 0
        assert any(
            "超出范围" in error or "小于最小值" in error for error in range_errors
        )

    @pytest.mark.asyncio
    async def test_check_match_failure_type_error(
        self, data_quality_monitor, mock_feature_store
    ):
        """测试类型错误失败场景"""
        result = await data_quality_monitor.check_match(4)  # 类型错误数据

        assert not result["passed"]

        # 检查是否捕获到类型错误
        type_errors = []
        for rule_result in result["results"]:
            if rule_result["rule_name"] == "type_check":
                type_errors.extend(rule_result["errors"])

        assert len(type_errors) > 0

    @pytest.mark.asyncio
    async def test_check_match_failure_logical_error(
        self, data_quality_monitor, mock_feature_store
    ):
        """测试逻辑关系错误失败场景"""
        result = await data_quality_monitor.check_match(5)  # 逻辑错误数据

        assert not result["passed"]

        # 检查是否捕获到逻辑错误
        logical_errors = []
        for rule_result in result["results"]:
            if rule_result["rule_name"] == "logical_relation_check":
                logical_errors.extend(rule_result["errors"])

        assert len(logical_errors) > 0

    @pytest.mark.asyncio
    async def test_check_match_no_data(self, data_quality_monitor):
        """测试没有找到数据的场景"""
        result = await data_quality_monitor.check_match(999)  # 不存在的match_id

        assert not result["passed"]
        assert "未找到" in result["summary"]["error"]
        assert result["summary"]["failed_rules"] == 4  # 所有规则都失败

    @pytest.mark.asyncio
    async def test_check_batch(self, data_quality_monitor):
        """测试批量检查功能"""
        match_ids = [1, 2, 3, 4, 5]
        results = await data_quality_monitor.check_batch(match_ids)

        assert len(results) == 5
        assert all(result["match_id"] in match_ids for result in results)

        # 验证结果结构
        for result in results:
            assert "passed" in result
            assert "results" in result
            assert "summary" in result

        # 统计通过的比赛数量
        passed_count = sum(1 for r in results if r["passed"])
        assert passed_count == 1  # 只有 match_id=1 应该通过

    @pytest.mark.asyncio
    async def test_check_batch_empty_list(self, data_quality_monitor):
        """测试空列表批量检查"""
        results = await data_quality_monitor.check_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_get_stats(self, data_quality_monitor):
        """测试统计信息获取"""
        # 执行几次检查
        await data_quality_monitor.check_match(1)
        await data_quality_monitor.check_match(2)
        await data_quality_monitor.check_match(3)

        stats = await data_quality_monitor.get_stats()

        assert stats["stats_enabled"]
        assert stats["total_checks"] == 3
        assert stats["passed_checks"] == 1
        assert stats["failed_checks"] == 2
        assert stats["success_rate"] == 33.33  # 1/3 * 100
        assert stats["error_rate"] == 66.67  # 2/3 * 100

    @pytest.mark.asyncio
    async def test_health_check(self, data_quality_monitor, mock_feature_store):
        """测试健康检查"""
        health = await data_quality_monitor.health_check()

        assert "status" in health
        assert "rules_count" in health
        assert "feature_store_status" in health
        assert health["rules_count"] == 4

        # 由于没有实际运行检查，状态应该是警告或健康
        assert health["status"] in ["healthy", "warning", "unhealthy"]

    @pytest.mark.asyncio
    async def test_add_rule(self, data_quality_monitor):
        """测试添加规则"""
        original_count = len(data_quality_monitor.rules)

        new_rule = TestDataQualityRule()
        data_quality_monitor.add_rule(new_rule)

        assert len(data_quality_monitor.rules) == original_count + 1
        assert data_quality_monitor.rules[-1] == new_rule

    @pytest.mark.asyncio
    async def test_add_duplicate_rule(self, data_quality_monitor):
        """测试添加重复规则名称"""
        with pytest.raises(ValueError, match="规则名称.*已存在"):
            duplicate_rule = TestDataQualityRule()
            duplicate_rule.rule_name = "test_rule"  # 与默认规则重名
            data_quality_monitor.add_rule(duplicate_rule)

    @pytest.mark.asyncio
    async def test_remove_rule(self, data_quality_monitor):
        """测试移除规则"""
        original_count = len(data_quality_monitor.rules)
        rule_to_remove = data_quality_monitor.rules[0]
        rule_name = rule_to_remove.rule_name

        success = data_quality_monitor.remove_rule(rule_name)

        assert success
        assert len(data_quality_monitor.rules) == original_count - 1
        assert rule_to_remove not in data_quality_monitor.rules

    @pytest.mark.asyncio
    async def test_remove_nonexistent_rule(self, data_quality_monitor):
        """测试移除不存在的规则"""
        success = data_quality_monitor.remove_rule("nonexistent_rule")
        assert not success

    @pytest.mark.asyncio
    async def test_get_rule_names(self, data_quality_monitor):
        """测试获取规则名称列表"""
        rule_names = data_quality_monitor.get_rule_names()
        assert len(rule_names) == 4
        assert "missing_value_check" in rule_names
        assert "range_check" in rule_names
        assert "type_check" in rule_names
        assert "logical_relation_check" in rule_names

    @pytest.mark.asyncio
    async def test_check_performance(self, data_quality_monitor):
        """测试检查性能"""
        import time

        start_time = time.time()
        result = await data_quality_monitor.check_match(1)
        end_time = time.time()

        duration_ms = (end_time - start_time) * 1000

        # 验证结果正确
        assert result["passed"]

        # 性能检查（单次检查应该很快）
        assert duration_ms < 100  # 应该在100ms内完成
        assert result["check_duration_ms"] < 100

    @pytest.mark.asyncio
    async def test_concurrent_checks(self, data_quality_monitor):
        """测试并发检查"""
        import asyncio

        # 并发执行多个检查
        tasks = [
            data_quality_monitor.check_match(1),
            data_quality_monitor.check_match(2),
            data_quality_monitor.check_match(3),
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        duration_ms = (end_time - start_time) * 1000

        assert len(results) == 3
        assert results[0]["passed"]  # match 1
        assert not results[1]["passed"]  # match 2
        assert not results[2]["passed"]  # match 3

        # 并发应该比顺序执行快
        assert duration_ms < 200  # 3个并发检查应该在200ms内完成

    def test_empty_rules_validation(self):
        """测试空规则列表验证"""
        mock_store = MockFeatureStore()

        with pytest.raises(ValueError, match="至少需要提供一个数据质量规则"):
            DataQualityMonitor(rules=[], feature_store=mock_store)

    def test_invalid_rule_validation(self):
        """测试无效规则验证"""
        mock_store = MockFeatureStore()

        # 创建没有check方法的规则
        class InvalidRule:
            rule_name = "invalid"
            rule_description = "无效规则"

        with pytest.raises(ValueError, match="必须实现 check 方法"):
            DataQualityMonitor(rules=[InvalidRule()], feature_store=mock_store)


class TestSpecificRules:
    """测试具体规则的单元测试"""

    @pytest.mark.asyncio
    async def test_missing_value_rule(self):
        """测试缺失值规则"""
        rule = MissingValueRule()

        # 测试正常数据
        good_features = {
            "match_id": 1,
            "full_time_score_home": 2,
            "xg_home": 1.5,
            "shot_home": 10,
        }
        errors = await rule.check(good_features)
        assert len(errors) == 0

        # 测试缺失值数据
        bad_features = {
            "full_time_score_home": None,  # None值
            "xg_home": "",  # 空字符串
            # match_id 完全缺失
        }
        errors = await rule.check(bad_features)
        assert len(errors) > 0
        assert any("缺失" in error for error in errors)

    @pytest.mark.asyncio
    async def test_range_rule(self):
        """测试范围规则"""
        rule = RangeRule()

        # 测试正常范围内的数据
        good_features = {
            "full_time_score_home": 2,  # 在0-99范围内
            "possession_home": 60.0,  # 在0-100范围内
            "xg_home": 1.5,  # 在0-10范围内
        }
        errors = await rule.check(good_features)
        assert len(errors) == 0

        # 测试超出范围的数据
        bad_features = {
            "full_time_score_home": -1,  # 小于最小值
            "possession_home": 150.0,  # 大于最大值
            "xg_home": 15.0,  # 大于最大值
        }
        errors = await rule.check(bad_features)
        assert len(errors) > 0
        assert any("小于最小值" in error or "大于最大值" in error for error in errors)

    @pytest.mark.asyncio
    async def test_type_rule(self):
        """测试类型规则"""
        rule = TypeRule()

        # 测试正确类型
        good_features = {
            "match_id": 1,  # int
            "xg_home": 1.5,  # float
            "match_time": "2023-01-01",  # str
        }
        errors = await rule.check(good_features)
        assert len(errors) == 0

        # 测试错误类型
        bad_features = {
            "match_id": "not_a_number",  # 应该是int
            "xg_home": "1.5",  # 应该是float
        }
        errors = await rule.check(bad_features)
        assert len(errors) > 0
        assert any("类型错误" in error for error in errors)

    @pytest.mark.asyncio
    async def test_logical_relation_rule(self):
        """测试逻辑关系规则"""
        rule = LogicalRelationRule()

        # 测试正确的逻辑关系
        good_features = {
            "full_time_score_home": 2,
            "half_time_score_home": 1,  # 全场 >= 半场
            "shot_home": 15,
            "shot_on_target_home": 6,  # 射正 <= 总射门
            "possession_home": 60.0,
            "possession_away": 40.0,  # 和接近100%
        }
        errors = await rule.check(good_features)
        # 可能有一些关于xG的警告，但不应该有严重的逻辑错误
        severe_errors = [e for e in errors if "xG" not in e]
        assert len(severe_errors) == 0

        # 测试错误的逻辑关系
        bad_features = {
            "full_time_score_home": 1,
            "half_time_score_home": 2,  # 全场 < 半场 (错误)
            "shot_home": 5,
            "shot_on_target_home": 10,  # 射正 > 总射门 (错误)
        }
        errors = await rule.check(bad_features)
        assert len(errors) > 0


class TestErrorHandling:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_feature_store_exception(self, default_rules):
        """测试 FeatureStore 异常处理"""
        # 创建会抛出异常的 mock
        mock_store = AsyncMock()
        mock_store.load_features.side_effect = Exception("数据库连接失败")

        monitor = DataQualityMonitor(
            rules=default_rules, feature_store=mock_store, enable_stats=False
        )

        result = await monitor.check_match(1)

        assert not result["passed"]
        assert "错误" in result["summary"]["error"]

    @pytest.mark.asyncio
    async def test_rule_execution_exception(self, mock_feature_store):
        """测试规则执行异常处理"""
        # 创建会抛出异常的规则
        failing_rule = TestDataQualityRule(should_fail=False)
        failing_rule.check = AsyncMock(side_effect=Exception("规则执行失败"))

        monitor = DataQualityMonitor(
            rules=[failing_rule], feature_store=mock_feature_store, enable_stats=False
        )

        result = await monitor.check_match(1)

        assert not result["passed"]
        assert len(result["results"]) == 1
        assert not result["results"][0]["passed"]
        assert "异常" in result["results"][0]["errors"][0]


class TestDataQualityStats:
    """测试统计信息类"""

    def test_stats_initialization(self):
        """测试统计信息初始化"""
        stats = DataQualityStats()

        assert stats.total_checks == 0
        assert stats.passed_checks == 0
        assert stats.failed_checks == 0
        assert stats.success_rate == 0.0
        assert stats.error_rate == 0.0

    def test_stats_to_dict(self):
        """测试统计信息序列化"""
        now = datetime.now(timezone.utc)
        stats = DataQualityStats(
            total_checks=10, passed_checks=7, failed_checks=3, last_check_time=now
        )

        stats_dict = stats.to_dict()

        assert stats_dict["total_checks"] == 10
        assert stats_dict["passed_checks"] == 7
        assert stats_dict["failed_checks"] == 3
        assert stats_dict["success_rate"] == 70.0
        assert stats_dict["error_rate"] == 30.0
        assert stats_dict["last_check_time"] == now.isoformat()


# 性能基准测试
@pytest.mark.asyncio
@pytest.mark.slow
async def test_performance_benchmark():
    """性能基准测试"""
    import time

    mock_store = MockFeatureStore()
    rules = default_rules()
    monitor = DataQualityMonitor(rules, mock_store, enable_stats=False)

    # 测试大量检查的性能
    match_ids = list(range(1, 100))

    start_time = time.time()
    results = await monitor.check_batch(match_ids)
    end_time = time.time()

    duration_ms = (end_time - start_time) * 1000

    assert len(results) == 99
    assert duration_ms < 5000  # 99个检查应该在5秒内完成

    # 计算平均每个检查的时间
    avg_ms_per_check = duration_ms / 99
    assert avg_ms_per_check < 50  # 平均每个检查应该少于50ms


# 集成测试场景
@pytest.mark.asyncio
async def test_end_to_end_workflow():
    """端到端工作流测试"""
    mock_store = MockFeatureStore()
    rules = default_rules()
    monitor = DataQualityMonitor(rules, mock_store)

    # 1. 检查单个比赛
    result1 = await monitor.check_match(1)
    assert result1["passed"]

    # 2. 批量检查
    batch_results = await monitor.check_batch([1, 2, 3])
    assert len(batch_results) == 3
    passed = sum(1 for r in batch_results if r["passed"])
    assert passed == 1  # 只有第一个通过

    # 3. 获取统计信息
    stats = await monitor.get_stats()
    assert stats["total_checks"] == 4  # 1个单次 + 3个批量
    assert stats["passed_checks"] == 2  # match_id=1 被检查两次

    # 4. 健康检查
    health = await monitor.health_check()
    assert "status" in health
    assert health["rules_count"] == 4
