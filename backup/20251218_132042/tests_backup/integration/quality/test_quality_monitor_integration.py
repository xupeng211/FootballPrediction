"""
Data Quality Monitor Integration Tests

数据质量监控器的集成测试，连接真实的PostgreSQL数据库和FeatureStore。
测试完整的端到端数据质量检查流程，包括数据插入、特征加载、规则验证等。

测试环境要求：
- Docker PostgreSQL 数据库运行
- FeatureStore 数据库表存在
- 网络连接正常

生成时间: 2025-12-05
测试框架: pytest + asyncio
数据库: PostgreSQL 15
"""

import pytest
import asyncio
import time
import json

# 集成测试需要导入真实的实现
from src.database.async_manager import get_db_session
from src.features.feature_store import FootballFeatureStore
from src.quality.data_quality_monitor import DataQualityMonitor
from src.quality.rules.missing_value_rule import MissingValueRule
from src.quality.rules.range_rule import RangeRule
from src.quality.rules.type_rule import TypeRule
from src.quality.rules.logical_relation_rule import LogicalRelationRule


class TestFeatureStoreIntegration:
    """FeatureStore 集成测试"""

    @pytest.fixture(scope="class")
    async def feature_store(self):
        """创建真实的 FeatureStore 实例"""
        feature_store = FootballFeatureStore()
        return feature_store

    @pytest.fixture(scope="class")
    async def test_match_data(self):
        """测试用比赛数据"""
        return {
            "match_id": 99999,  # 使用高ID避免与真实数据冲突
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
            "match_time": "2023-12-05T15:00:00Z",
            "match_status": "completed",
            "home_team_id": 101,
            "away_team_id": 102,
            "match_date": "2023-12-05",
        }

    @pytest.fixture(scope="class")
    async def invalid_match_data(self):
        """无效的测试数据（用于测试错误检测）"""
        return {
            "match_id": 99998,
            "full_time_score_home": None,  # 缺失值
            "full_time_score_away": 150,  # 超出范围
            "xg_home": -5.0,  # 负xG
            "shot_home": "invalid",  # 错误类型
            "possession_home": 150.0,  # 超出100%
            "possession_away": -10.0,  # 负值
            "shot_on_target_home": 20,  # 大于总射门数（假设总射门数是10）
            "shot_home": 10,
        }

    @pytest.fixture(autouse=True)
    async def setup_test_data(self, feature_store, test_match_data, invalid_match_data):
        """设置测试数据，在测试前后进行清理"""
        # 清理可能存在的测试数据
        await self._cleanup_test_data(
            feature_store, [test_match_data["match_id"], invalid_match_data["match_id"]]
        )

        # 插入测试数据
        await feature_store.save_features(test_match_data["match_id"], test_match_data)
        await feature_store.save_features(
            invalid_match_data["match_id"], invalid_match_data
        )

        yield

        # 清理测试数据
        await self._cleanup_test_data(
            feature_store, [test_match_data["match_id"], invalid_match_data["match_id"]]
        )

    async def _cleanup_test_data(self, feature_store, match_ids):
        """清理测试数据"""
        async with get_db_session() as session:
            # 这里假设有删除方法，实际实现可能需要调整
            for match_id in match_ids:
                try:
                    # 直接执行SQL删除（如果FeatureStore没有删除方法）
                    await session.execute(
                        "DELETE FROM feature_store WHERE match_id = :match_id",
                        {"match_id": match_id},
                    )
                    await session.commit()
                except Exception:
                    # 如果表不存在或删除失败，忽略错误
                    pass

    @pytest.mark.asyncio
    async def test_feature_store_basic_operations(self, feature_store, test_match_data):
        """测试 FeatureStore 基本操作"""
        match_id = test_match_data["match_id"]

        # 测试加载特征数据
        start_time = time.time()
        loaded_features = await feature_store.load_features(match_id)
        load_duration_ms = (time.time() - start_time) * 1000

        # 验证数据正确加载
        assert loaded_features is not None
        assert loaded_features["match_id"] == match_id
        assert loaded_features["full_time_score_home"] == 2
        assert loaded_features["full_time_score_away"] == 1

        # 性能检查：加载应该在合理时间内完成
        assert load_duration_ms < 100, f"特征数据加载耗时过长: {load_duration_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_feature_store_nonexistent_match(self, feature_store):
        """测试加载不存在的比赛数据"""
        result = await feature_store.load_features(999999999)
        assert result is None


class TestDataQualityMonitorIntegration:
    """DataQualityMonitor 集成测试"""

    @pytest.fixture(scope="class")
    async def data_quality_monitor(self, feature_store):
        """创建 DataQualityMonitor 实例"""
        rules = [MissingValueRule(), RangeRule(), TypeRule(), LogicalRelationRule()]

        monitor = DataQualityMonitor(
            rules=rules,
            feature_store=feature_store,
            enable_stats=True,
            max_concurrent_checks=5,
        )
        return monitor

    @pytest.mark.asyncio
    async def test_check_match_with_valid_data(
        self, data_quality_monitor, test_match_data
    ):
        """测试有效数据的检查"""
        match_id = test_match_data["match_id"]

        start_time = time.time()
        result = await data_quality_monitor.check_match(match_id)
        duration_ms = (time.time() - start_time) * 1000

        # 验证结果结构
        assert "match_id" in result
        assert "passed" in result
        assert "results" in result
        assert "summary" in result
        assert "timestamp" in result
        assert "check_duration_ms" in result

        # 验证具体内容
        assert result["match_id"] == match_id
        assert result["passed"]  # 有效数据应该通过所有检查
        assert len(result["results"]) == 4  # 4条规则

        # 验证规则结果
        for rule_result in result["results"]:
            assert "rule_name" in rule_result
            assert "passed" in rule_result
            assert "errors" in rule_result
            assert "severity" in rule_result
            assert rule_result["passed"]  # 所有规则都应该通过
            assert len(rule_result["errors"]) == 0

        # 性能检查
        assert duration_ms < 50, f"检查耗时过长: {duration_ms:.2f}ms"
        assert result["check_duration_ms"] < 50

    @pytest.mark.asyncio
    async def test_check_match_with_invalid_data(
        self, data_quality_monitor, invalid_match_data
    ):
        """测试无效数据的检查"""
        match_id = invalid_match_data["match_id"]

        result = await data_quality_monitor.check_match(match_id)

        # 验证结果结构
        assert result["match_id"] == match_id
        assert not result["passed"]  # 无效数据应该失败
        assert len(result["results"]) == 4

        # 验证有规则失败
        failed_rules = [r for r in result["results"] if not r["passed"]]
        assert len(failed_rules) > 0

        # 验证错误信息
        all_errors = []
        for rule_result in result["results"]:
            all_errors.extend(rule_result["errors"])

        assert len(all_errors) > 0

        # 检查特定类型的错误
        error_text = " ".join(all_errors).lower()
        assert any(
            keyword in error_text
            for keyword in [
                "缺失",
                "null",
                "missing",  # 缺失值错误
                "超出",
                "范围",
                "out of",  # 范围错误
                "类型",
                "type",  # 类型错误
                "逻辑",
                "logical",  # 逻辑错误
            ]
        )

    @pytest.mark.asyncio
    async def test_check_batch_performance(
        self, data_quality_monitor, test_match_data, invalid_match_data
    ):
        """测试批量检查性能"""
        match_ids = [test_match_data["match_id"], invalid_match_data["match_id"]]

        start_time = time.time()
        results = await data_quality_monitor.check_batch(match_ids)
        duration_ms = (time.time() - start_time) * 1000

        # 验证结果
        assert len(results) == 2
        assert results[0]["passed"]  # 有效数据通过
        assert not results[1]["passed"]  # 无效数据失败

        # 性能检查：批量检查应该很快
        assert duration_ms < 100, f"批量检查耗时过长: {duration_ms:.2f}ms"

        # 验证结果结构一致性
        for result in results:
            assert all(
                key in result
                for key in [
                    "match_id",
                    "passed",
                    "results",
                    "summary",
                    "timestamp",
                    "check_duration_ms",
                ]
            )

    @pytest.mark.asyncio
    async def test_stats_collection(
        self, data_quality_monitor, test_match_data, invalid_match_data
    ):
        """测试统计信息收集"""
        match_ids = [test_match_data["match_id"], invalid_match_data["match_id"]]

        # 执行几次检查
        await data_quality_monitor.check_match(test_match_data["match_id"])
        await data_quality_monitor.check_match(invalid_match_data["match_id"])
        await data_quality_monitor.check_batch(match_ids)

        # 获取统计信息
        stats = await data_quality_monitor.get_stats()

        # 验证统计信息
        assert stats["stats_enabled"]
        assert stats["total_checks"] == 4  # 2个单次 + 2个批量
        assert stats["passed_checks"] >= 2  # 至少有效数据的2次检查通过
        assert stats["failed_checks"] >= 2  # 至少无效数据的2次检查失败

        # 验证成功率计算
        assert (
            stats["success_rate"]
            == (stats["passed_checks"] / stats["total_checks"]) * 100
        )
        assert (
            stats["error_rate"]
            == (stats["failed_checks"] / stats["total_checks"]) * 100
        )

    @pytest.mark.asyncio
    async def test_health_check(self, data_quality_monitor, test_match_data):
        """测试健康检查"""
        # 执行一些检查以生成统计数据
        await data_quality_monitor.check_match(test_match_data["match_id"])

        health = await data_quality_monitor.health_check()

        # 验证健康检查结果
        assert "status" in health
        assert "feature_store_status" in health
        assert "rules_count" in health
        assert "stats" in health
        assert "last_check" in health

        assert health["rules_count"] == 4
        assert health["status"] in ["healthy", "warning", "unhealthy"]
        assert health["feature_store_status"] in ["healthy", "warning"]

        # 验证统计信息包含在健康检查中
        assert health["stats"]["stats_enabled"]

    @pytest.mark.asyncio
    async def test_concurrent_checks(self, data_quality_monitor, test_match_data):
        """测试并发检查"""
        import asyncio

        match_id = test_match_data["match_id"]

        # 并发执行多个检查（对同一个match_id）
        tasks = [
            data_quality_monitor.check_match(match_id),
            data_quality_monitor.check_match(match_id),
            data_quality_monitor.check_match(match_id),
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        duration_ms = (time.time() - start_time) * 1000

        # 验证所有检查都成功
        assert len(results) == 3
        for result in results:
            assert result["passed"]
            assert result["match_id"] == match_id

        # 并发检查应该比顺序执行快
        assert duration_ms < 150, f"并发检查耗时过长: {duration_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_rule_specific_errors(self, data_quality_monitor, invalid_match_data):
        """测试特定规则错误检测"""
        match_id = invalid_match_data["match_id"]

        result = await data_quality_monitor.check_match(match_id)

        # 查找特定规则的错误
        missing_value_errors = None
        range_errors = None
        type_errors = None
        logical_errors = None

        for rule_result in result["results"]:
            if rule_result["rule_name"] == "missing_value_check":
                missing_value_errors = rule_result["errors"]
            elif rule_result["rule_name"] == "range_check":
                range_errors = rule_result["errors"]
            elif rule_result["rule_name"] == "type_check":
                type_errors = rule_result["errors"]
            elif rule_result["rule_name"] == "logical_relation_check":
                logical_errors = rule_result["errors"]

        # 验证缺失值检测
        if missing_value_errors:
            assert any(
                keyword in " ".join(missing_value_errors).lower()
                for keyword in ["缺失", "null", "missing"]
            )

        # 验证范围检测
        if range_errors:
            assert any(
                keyword in " ".join(range_errors).lower()
                for keyword in ["范围", "range", "超出"]
            )

        # 验证类型检测
        if type_errors:
            assert any(
                keyword in " ".join(type_errors).lower() for keyword in ["类型", "type"]
            )

        # 验证逻辑关系检测
        if logical_errors:
            assert any(
                keyword in " ".join(logical_errors).lower()
                for keyword in ["逻辑", "logical", "关系"]
            )

    @pytest.mark.asyncio
    async def test_json_serialization(self, data_quality_monitor, test_match_data):
        """测试结果JSON序列化"""
        result = await data_quality_monitor.check_match(test_match_data["match_id"])

        # 尝试序列化为JSON
        try:
            json_str = json.dumps(result, default=str)
            parsed_back = json.loads(json_str)

            # 验证序列化/反序列化的正确性
            assert parsed_back["match_id"] == result["match_id"]
            assert parsed_back["passed"] == result["passed"]
            assert len(parsed_back["results"]) == len(result["results"])

        except (TypeError, ValueError) as e:
            pytest.fail(f"结果JSON序列化失败: {e}")

    @pytest.mark.asyncio
    async def test_large_dataset_performance(
        self, data_quality_monitor, test_match_data
    ):
        """测试大数据集性能"""
        match_id = test_match_data["match_id"]

        # 执行多次检查来模拟大数据集
        num_checks = 50
        start_time = time.time()

        tasks = [data_quality_monitor.check_match(match_id) for _ in range(num_checks)]
        results = await asyncio.gather(*tasks)

        duration_ms = (time.time() - start_time) * 1000

        # 验证所有检查都成功
        assert len(results) == num_checks
        assert all(result["passed"] for result in results)

        # 性能检查：50次检查应该在合理时间内完成
        assert duration_ms < 2000, f"大数据集检查耗时过长: {duration_ms:.2f}ms"
        avg_per_check = duration_ms / num_checks
        assert avg_per_check < 40, f"平均单次检查耗时过长: {avg_per_check:.2f}ms"

    @pytest.mark.asyncio
    async def test_error_recovery(self, data_quality_monitor):
        """测试错误恢复机制"""
        # 使用不存在的match_id来测试错误处理
        result = await data_quality_monitor.check_match(999999999)

        # 验证错误处理正确
        assert not result["passed"]
        assert "未找到" in result["summary"]["error"]
        assert len(result["results"]) == 0  # 没有规则被执行
        assert result["summary"]["failed_rules"] == 4  # 所有规则标记为失败

    @pytest.mark.asyncio
    async def test_memory_usage(self, data_quality_monitor, test_match_data):
        """测试内存使用（简单检查）"""
        import gc

        # 获取初始内存使用
        gc.collect()
        initial_objects = len(gc.get_objects())

        # 执行大量检查
        for _ in range(100):
            await data_quality_monitor.check_match(test_match_data["match_id"])

        # 检查内存泄漏
        gc.collect()
        final_objects = len(gc.get_objects())

        # 对象数量不应该大幅增加（允许一些合理的增长）
        object_increase = final_objects - initial_objects
        assert object_increase < 1000, f"可能存在内存泄漏，对象增加: {object_increase}"


# 数据库连接测试
@pytest.mark.asyncio
async def test_database_connection():
    """测试数据库连接"""
    try:
        async with get_db_session() as session:
            # 执行简单查询测试连接
            result = await session.execute("SELECT 1 as test")
            row = result.fetchone()
            assert row[0] == 1
    except Exception as e:
        pytest.fail(f"数据库连接失败: {e}")


# 环境检查
@pytest.mark.asyncio
async def test_environment_setup():
    """检查测试环境设置"""
    # 检查必要的环境变量
    import os

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL 环境变量未设置")

    # 检查数据库是否可访问
    try:
        async with get_db_session() as session:
            await session.execute("SELECT 1")
    except Exception as e:
        pytest.fail(f"数据库不可访问: {e}")

    print("✅ 测试环境设置正确")


# 性能基准测试
@pytest.mark.asyncio
@pytest.mark.performance
async def test_integration_performance_benchmark():
    """集成性能基准测试"""
    feature_store = FootballFeatureStore()
    rules = [MissingValueRule(), RangeRule(), TypeRule(), LogicalRelationRule()]
    monitor = DataQualityMonitor(rules, feature_store, enable_stats=False)

    # 创建测试数据
    test_match_id = 999999
    test_data = {
        "match_id": test_match_id,
        "full_time_score_home": 2,
        "full_time_score_away": 1,
        "xg_home": 1.5,
        "xg_away": 0.8,
        "shot_home": 15,
        "shot_away": 8,
        "possession_home": 60.0,
        "possession_away": 40.0,
    }

    try:
        # 插入测试数据
        await feature_store.save_features(test_match_id, test_data)

        # 性能测试
        start_time = time.time()
        results = await monitor.check_batch([test_match_id] * 100)  # 100次相同检查
        duration_ms = (time.time() - start_time) * 1000

        # 验证结果
        assert len(results) == 100
        assert all(result["passed"] for result in results)

        # 性能断言
        assert duration_ms < 3000, f"集成性能测试失败，耗时: {duration_ms:.2f}ms"
        avg_ms = duration_ms / 100
        assert avg_ms < 30, f"平均检查时间过长: {avg_ms:.2f}ms"

        print(f"✅ 集成性能测试通过: {avg_ms:.2f}ms/次")

    finally:
        # 清理测试数据
        try:
            async with get_db_session() as session:
                await session.execute(
                    "DELETE FROM feature_store WHERE match_id = :match_id",
                    {"match_id": test_match_id},
                )
                await session.commit()
        except Exception:
            pass
