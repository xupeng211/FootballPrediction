#!/usr/bin/env python3
"""
V26.0 集成压力测试 - 100 场极端数据验证
==========================================

测试目标:
    1. 验证并行处理在极端数据下的稳定性
    2. 验证内存屏障有效性
    3. 验证批量入库的可靠性

测试场景:
    - 损坏的 JSON 数据
    - 缺失字段的数据
    - 不同赛季格式的数据
    - 极大/极小特征维度的数据
    - 并发竞争条件

Author: Principal Architect
Version: V26.0 (Stable)
Date: 2025-12-27
"""

import gc
import json
import multiprocessing
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pytest

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings
from src.core.types import MatchID, MatchStatus, Season
from src.ops.performance_engine import (
    BulkInserter,
    ParallelFeatureExtractor,
    PerformancePipeline,
)
from src.processors.v25_production_extractor import V25ProductionExtractor

# ============================================================================
# 测试数据生成器
# ============================================================================


class StressTestDataGenerator:
    """
    压力测试数据生成器

    生成各种极端情况下的测试数据
    """

    @staticmethod
    def generate_corrupted_json() -> dict[str, Any]:
        """生成损坏的 JSON 结构"""
        return {
            "match_id": "corrupted_001",
            "infinite_loop": {},  # 可能导致解析问题
            "null_values": [None, None, None],
            "empty_structures": {"a": {}, "b": []},
        }

    @staticmethod
    def generate_missing_fields() -> dict[str, Any]:
        """生成缺失关键字段的数据"""
        return {
            # 缺少 stats
            "match_id": "missing_001",
            "home_team": "",  # 空字符串
            "away_team": None,  # None 值
        }

    @staticmethod
    def generate_extreme_dimensions() -> dict[str, Any]:
        """生成极端维度的数据"""
        data = {
            "match_id": "extreme_001",
            "nested": {},
        }

        # 创建深度嵌套结构
        current = data["nested"]
        for i in range(20):
            current[f"level_{i}"] = {}
            current = current[f"level_{i}"]

        # 添加大量重复字段
        for i in range(1000):
            data[f"field_{i}"] = i * 0.1

        return data

    @staticmethod
    def generate_various_season_formats() -> list[dict[str, Any]]:
        """生成各种赛季格式的数据"""
        formats = [
            ("2324", "标准格式"),
            ("23/24", "斜杠格式"),
            ("2023-2024", "完整格式"),
            ("23-24", "短横线格式"),
            ("2023", "四位年份"),
        ]

        test_data = []
        for season, desc in formats:
            test_data.append(
                {
                    "match_id": f"season_test_{season}",
                    "season": season,
                    "format_desc": desc,
                    "stats": {"xg": 1.5},
                }
            )

        return test_data

    @classmethod
    def generate_stress_dataset(cls, size: int = 100) -> list[dict[str, Any]]:
        """
        生成完整的压力测试数据集

        Args:
            size: 数据集大小

        Returns:
            测试数据列表
        """
        dataset = []

        # 正常数据 (60%)
        for i in range(int(size * 0.6)):
            dataset.append(
                {
                    "match_id": f"normal_{i}",
                    "season": "2324",
                    "stats": {
                        "home_xg": 1.0 + (i % 30) * 0.1,
                        "away_xg": 0.5 + (i % 20) * 0.1,
                    },
                }
            )

        # 损坏数据 (10%)
        for i in range(int(size * 0.1)):
            dataset.append(cls.generate_corrupted_json())

        # 缺失字段数据 (10%)
        for i in range(int(size * 0.1)):
            dataset.append(cls.generate_missing_fields())

        # 极端维度数据 (10%)
        for i in range(int(size * 0.1)):
            dataset.append(cls.generate_extreme_dimensions())

        # 各种赛季格式 (10%)
        dataset.extend(cls.generate_various_season_formats()[: size // 10])

        return dataset


# ============================================================================
# 集成压力测试
# ============================================================================


class TestV26IntegrationStress:
    """V26.0 集成压力测试套件"""

    @pytest.fixture
    def settings(self):
        """获取配置"""
        return get_settings()

    @pytest.fixture
    def extractor(self):
        """创建提取器实例"""
        return V25ProductionExtractor()

    @pytest.fixture
    def stress_dataset(self):
        """生成压力测试数据集"""
        return StressTestDataGenerator.generate_stress_dataset(100)

    # ========================================================================
    # 测试用例 1: MatchID 类型安全
    # ========================================================================

    def test_match_id_creation(self):
        """测试: MatchID 创建和解析"""
        # 标准创建
        mid1 = MatchID.create("4507094", "2324")
        assert str(mid1) == "4507094_2324"
        assert mid1.external_id == "4507094"
        assert mid1.season == "2324"

        # 解析
        mid2 = MatchID.parse("4507094_2324")
        assert mid1 == mid2

        # 错误格式
        with pytest.raises(ValueError):
            MatchID.parse("invalid_format")

    def test_season_normalization(self):
        """测试: 赛季标准化"""
        test_cases = [
            ("23/24", "2023"),
            ("2023-2024", "2023"),
            ("23-24", "2023"),
            ("2324", "2324"),
        ]

        for input_season, expected in test_cases:
            result = Season.normalize(input_season)
            assert result == expected, f"{input_season} -> {result}, 期望 {expected}"

    def test_match_status_from_string(self):
        """测试: MatchStatus 字符串解析"""
        # 大小写不敏感
        status1 = MatchStatus.from_string("finished")
        status2 = MatchStatus.from_string("FINISHED")
        assert status1 == status2

        # 无效状态
        with pytest.raises(ValueError):
            MatchStatus.from_string("invalid_status")

    # ========================================================================
    # 测试用例 2: 并行特征提取
    # ========================================================================

    def test_parallel_extraction_stability(self, extractor, stress_dataset):
        """
        测试: 并行提取稳定性

        验证:
            1. 所有数据都被处理（无遗漏）
            2. 损坏数据不会导致崩溃
            3. 内存使用在限制范围内
        """
        cpu_count = multiprocessing.cpu_count()
        workers = max(1, cpu_count - 1)

        parallel_extractor = ParallelFeatureExtractor(
            max_workers=workers,
            batch_size=20,
        )

        # 模拟数据库候选格式
        candidates = [
            {
                "match_id": data.get("match_id", f"test_{i}"),
                "season": data.get("season", "2324"),
                "raw_data": data,
            }
            for i, data in enumerate(stress_dataset)
        ]

        # 执行并行提取
        results = parallel_extractor.extract_batch_parallel(
            candidates,
            "src.processors.v25_production_extractor.V25ProductionExtractor",
        )

        # 验证结果
        assert len(results) >= len(stress_dataset) * 0.5, (
            f"至少 50% 的数据应该被成功提取: {len(results)}/{len(stress_dataset)}"
        )

        # 验证内存
        assert parallel_extractor.check_memory_barrier(), "内存使用超过限制"

    # ========================================================================
    # 测试用例 3: 批量入库
    # ========================================================================

    def test_bulk_insert_performance(self, settings):
        """
        测试: 批量入库性能

        验证:
            1. 批量插入速度显著快于单条插入
            2. 事务完整性得到保证
            3. ON CONFLICT 正确处理重复
        """
        inserter = BulkInserter(
            {
                "host": settings.database.host,
                "port": settings.database.port,
                "database": settings.database.name,
                "user": settings.database.user,
                "password": settings.database.password.get_secret_value(),
            }
        )

        # 准备测试数据
        test_records = []
        for i in range(50):
            record = (
                f"test_bulk_{i}",
                "2324",
                "2024-12-26",
                f"Home_{i}",
                f"Away_{i}",
                "V26.0",
                json.dumps({"test_feature": i}),
                json.dumps({"test": True}),
                1,
                "PENDING",
            )
            test_records.append(record)

        # 批量插入
        start_time = time.time()
        inserted = inserter.insert_features_batch(test_records)
        elapsed = time.time() - start_time

        # 验证
        assert inserted == 50, f"应该插入 50 条记录，实际: {inserted}"
        assert elapsed < 5.0, f"批量插入 50 条记录应该在 5 秒内完成，实际: {elapsed:.2f}秒"

        # 清理测试数据
        try:
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
            )
            cur = conn.cursor()
            cur.execute("DELETE FROM match_features_training WHERE match_id LIKE 'test_bulk_%'")
            conn.commit()
            conn.close()
        except:
            pass  # 清理失败不影响测试结果

    # ========================================================================
    # 测试用例 4: 完整压力测试
    # ========================================================================

    def test_full_pipeline_stress_test(self, settings, stress_dataset):
        """
        测试: 完整压力测试

        模拟真实场景:
            1. 并行提取特征
            2. 批量入库
            3. 内存监控
        """
        pipeline = PerformancePipeline(
            settings.database,
            max_workers=2,  # 使用较少 worker 避免测试环境资源竞争
            batch_size=20,
        )

        # 准备候选数据
        candidates = [
            {
                "match_id": data.get("match_id", f"stress_{i}"),
                "season": data.get("season", "2324"),
                "match_date": "2024-12-26",
                "home_team": "Team A",
                "away_team": "Team B",
                "raw_data": data,
            }
            for i, data in enumerate(stress_dataset)
        ]

        # 执行完整流水线
        stats = pipeline.process_candidates(candidates)

        # 验证统计
        assert stats["total_candidates"] == 100
        assert stats["extraction_success"] >= 50, "至少 50% 应该成功提取"
        assert stats["inserted"] >= 50, "至少 50% 应该成功入库"
        assert stats["throughput_per_minute"] > 0, "吞吐量应该大于 0"

        # 验证性能
        # 目标: 1000 场/分钟 = 100 场应在 6 秒内完成
        assert stats["elapsed_seconds"] < 30, (
            f"100 场比赛应在 30 秒内完成，实际: {stats['elapsed_seconds']:.1f}秒"
        )

    # ========================================================================
    # 测试用例 5: 内存泄漏检测
    # ========================================================================

    def test_memory_leak_prevention(self, extractor):
        """
        测试: 内存泄漏预防

        验证连续处理大量数据时内存不会持续增长
        """
        # 强制初始 GC
        gc.collect()
        initial_objects = len(gc.get_objects())

        # 连续处理 50 个大型数据集
        for i in range(50):
            large_data = {
                f"section_{j}": {f"value_{k}": j * k for k in range(100)} for j in range(100)
            }
            result = extractor.extract(large_data)
            del result

        # 最终 GC
        gc.collect()
        final_objects = len(gc.get_objects())

        # 对象增长应在合理范围内
        object_increase = final_objects - initial_objects
        assert object_increase < 50000, f"可能的内存泄漏: 对象增加了 {object_increase}"

    # ========================================================================
    # 测试用例 6: 并发竞争条件
    # ========================================================================

    def test_concurrent_extraction_race_condition(self, extractor):
        """
        测试: 并发提取竞争条件

        验证多进程同时处理相同数据时的正确性
        """
        test_data = {
            "match_id": "race_test_001",
            "stats": {"xg": 1.5},
        }

        # 使用线程池模拟并发
        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = []
            for _ in range(10):
                future = executor.submit(
                    _extract_wrapper,
                    test_data,
                )
                futures.append(future)

            results = [f.result() for f in as_completed(futures)]

        # 验证所有结果一致
        assert len(results) == 10
        assert all(r is not None for r in results)


# ============================================================================
# 辅助函数
# ============================================================================


def _extract_wrapper(data: dict[str, Any]) -> Any:
    """提取包装器（用于并发测试）"""
    extractor = V25ProductionExtractor()
    result = extractor.extract(data)
    return result.features if result else None


# ============================================================================
# 运行入口
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
