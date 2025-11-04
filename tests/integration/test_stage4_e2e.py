#!/usr/bin/env python3
"""
第四阶段端到端测试脚本
Stage 4 End-to-End Test Script - Complete System Integration
"""

import asyncio
import sys
import os
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

# 添加项目根目录到Python路径
sys.path.insert(0, "/home/user/projects/FootballPrediction")

# 设置环境变量
os.environ["FOOTBALL_DATA_API_KEY"] = "ed809154dc1f422da46a18d8961a98a0"

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# 导入基础组件
try:
    from test_stage2_fixed import SimpleDataCollector
    from test_stage3_simple import SimpleCacheManager
except ImportError as e:
    logger.error(f"导入基础组件失败: {e}")
    sys.exit(1)


class Stage4E2ETester:
    """第四阶段端到端测试器"""

    def __init__(self):
        self.cache_manager = SimpleCacheManager()
        self.data_collector = None
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "errors": [],
            "performance_metrics": {},
            "data_quality_metrics": {},
        }
        self.performance_data = []

    async def initialize(self):
        """初始化测试环境"""
        try:
            self.data_collector = SimpleDataCollector()
            await self.data_collector.__aenter__()
            logger.info("✅ 测试环境初始化成功")
        except Exception as e:
            logger.error(f"❌ 测试环境初始化失败: {e}")
            raise

    async def cleanup(self):
        """清理测试环境"""
        try:
            if self.data_collector:
                await self.data_collector.__aexit__(None, None, None)
            self.cache_manager.clear_all()
            logger.info("✅ 测试环境清理完成")
        except Exception as e:
            logger.warning(f"⚠️ 测试环境清理失败: {e}")

    def record_performance(self, operation: str, duration: float, data_size: int = 0):
        """记录性能数据"""
        self.performance_data.append(
            {
                "operation": operation,
                "duration": duration,
                "data_size": data_size,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    async def test_complete_data_flow(self) -> bool:
        """测试完整数据流：API → 缓存 → 处理 → 存储"""
        try:
            logger.info("🔍 测试完整数据流...")

            # 第一步：API数据获取
            start_time = time.time()
            competitions_data = await self.data_collector._make_request_with_retry(
                "competitions"
            )
            api_duration = time.time() - start_time
            self.record_performance(
                "api_competitions_fetch",
                api_duration,
                len(competitions_data.get("competitions", [])),
            )

            if not competitions_data or "competitions" not in competitions_data:
                raise Exception("API数据获取失败")

            competitions = competitions_data["competitions"]
            premier_league = next(
                (comp for comp in competitions if comp.get("code") == "PL"), None
            )
            if not premier_league:
                raise Exception("未找到英超联赛数据")

            logger.info(
                f"  ✅ API数据获取成功: {len(competitions)}个联赛，耗时{api_duration:.3f}秒"
            )

            # 第二步：数据缓存
            start_time = time.time()
            cache_success = self.cache_manager.set_cache(
                "competitions", competitions, ttl_seconds=300
            )
            cache_duration = time.time() - start_time
            self.record_performance(
                "cache_competitions_set", cache_duration, len(competitions)
            )

            if not cache_success:
                raise Exception("数据缓存失败")

            logger.info(f"  ✅ 数据缓存成功，耗时{cache_duration:.3f}秒")

            # 第三步：缓存数据读取
            start_time = time.time()
            cached_competitions = self.cache_manager.get_cache("competitions")
            cache_read_duration = time.time() - start_time
            self.record_performance(
                "cache_competitions_get",
                cache_read_duration,
                len(cached_competitions or []),
            )

            if not cached_competitions or len(cached_competitions) != len(competitions):
                raise Exception("缓存数据读取失败")

            logger.info(f"  ✅ 缓存数据读取成功，耗时{cache_read_duration:.3f}秒")

            # 第四步：数据转换和处理
            start_time = time.time()
            processed_leagues = []
            for comp in competitions[:5]:  # 处理前5个联赛
                processed_league = {
                    "external_id": str(comp.get("id")),
                    "name": comp.get("name"),
                    "code": comp.get("code"),
                    "type": comp.get("type", "LEAGUE"),
                    "area_name": comp.get("area", {}).get("name", "Unknown"),
                    "current_matchday": comp.get("currentSeason", {}).get(
                        "currentMatchday"
                    ),
                    "processed_at": datetime.utcnow().isoformat(),
                }
                processed_leagues.append(processed_league)

            processing_duration = time.time() - start_time
            self.record_performance(
                "data_processing", processing_duration, len(processed_leagues)
            )

            logger.info(
                f"  ✅ 数据处理完成: {len(processed_leagues)}个联赛，耗时{processing_duration:.3f}秒"
            )

            # 第五步：处理后数据缓存
            start_time = time.time()
            final_cache_success = self.cache_manager.set_cache(
                "processed_leagues", processed_leagues, ttl_seconds=600
            )
            final_cache_duration = time.time() - start_time
            self.record_performance(
                "final_cache_set", final_cache_duration, len(processed_leagues)
            )

            if not final_cache_success:
                raise Exception("处理后数据缓存失败")

            logger.info(f"  ✅ 最终数据缓存成功，耗时{final_cache_duration:.3f}秒")

            # 数据质量验证
            quality_score = self._calculate_data_quality(processed_leagues)
            self.test_results["data_quality_metrics"]["leagues_quality"] = quality_score

            if quality_score < 80:
                raise Exception(f"数据质量评分过低: {quality_score}")

            logger.info(f"  ✅ 数据质量验证通过: {quality_score}/100")

            # 性能验证
            total_duration = (
                api_duration
                + cache_duration
                + cache_read_duration
                + processing_duration
                + final_cache_duration
            )
            if total_duration > 10.0:  # 超过10秒认为性能不佳
                logger.warning(f"  ⚠️ 完整数据流耗时较长: {total_duration:.3f}秒")

            logger.info(f"  ✅ 完整数据流测试通过，总耗时: {total_duration:.3f}秒")

            return True

        except Exception as e:
            logger.error(f"  ❌ 完整数据流测试失败: {e}")
            return False

    async def test_concurrent_data_access(self) -> bool:
        """测试并发数据访问"""
        try:
            logger.info("🔍 测试并发数据访问...")

            # 准备测试数据
            test_data = [
                {
                    "id": i,
                    "name": f"Team {i}",
                    "points": i * 3,
                    "created_at": datetime.utcnow().isoformat(),
                }
                for i in range(100)
            ]

            # 批量设置缓存
            for i, data in enumerate(test_data):
                self.cache_manager.set_cache(f"team_{i}", data, ttl_seconds=300)

            logger.info(f"  ✅ 准备了{len(test_data)}条测试数据")

            # 并发读取测试
            async def concurrent_read(team_id: int) -> bool:
                try:
                    cached_data = self.cache_manager.get_cache(f"team_{team_id}")
                    if cached_data and cached_data.get("id") == team_id:
                        return True
                    return False
                except Exception:
                    return False

            # 并发写入测试
            async def concurrent_write(team_id: int) -> bool:
                try:
                    data = {
                        "id": team_id,
                        "name": f"Concurrent Team {team_id}",
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                    return self.cache_manager.set_cache(
                        f"concurrent_team_{team_id}", data, ttl_seconds=300
                    )
                except Exception:
                    return False

            # 执行并发测试
            concurrent_read_count = 50
            concurrent_write_count = 30

            start_time = time.time()

            # 并发读取
            read_tasks = [
                concurrent_read(i % 100) for i in range(concurrent_read_count)
            ]
            read_results = await asyncio.gather(*read_tasks, return_exceptions=True)

            # 并发写入
            write_tasks = [concurrent_write(i) for i in range(concurrent_write_count)]
            write_results = await asyncio.gather(*write_tasks, return_exceptions=True)

            total_duration = time.time() - start_time

            # 统计结果
            successful_reads = sum(1 for result in read_results if result is True)
            successful_writes = sum(1 for result in write_results if result is True)

            read_success_rate = (successful_reads / concurrent_read_count) * 100
            write_success_rate = (successful_writes / concurrent_write_count) * 100

            logger.info(
                f"  ✅ 并发读取测试: {successful_reads}/{concurrent_read_count} 成功 ({read_success_rate:.1f}%)"
            )
            logger.info(
                f"  ✅ 并发写入测试: {successful_writes}/{concurrent_write_count} 成功 ({write_success_rate:.1f}%)"
            )
            logger.info(f"  ✅ 并发测试总耗时: {total_duration:.3f}秒")

            # 性能指标记录
            self.record_performance(
                "concurrent_operations",
                total_duration,
                concurrent_read_count + concurrent_write_count,
            )

            # 验证并发性能
            if read_success_rate < 90 or write_success_rate < 90:
                raise Exception(
                    f"并发性能不达标: 读取{read_success_rate:.1f}%, 写入{write_success_rate:.1f}%"
                )

            return True

        except Exception as e:
            logger.error(f"  ❌ 并发数据访问测试失败: {e}")
            return False

    async def test_data_consistency_across_components(self) -> bool:
        """测试组件间数据一致性"""
        try:
            logger.info("🔍 测试组件间数据一致性...")

            # 从API获取原始数据
            teams_data = await self.data_collector._make_request_with_retry(
                "competitions/2021/teams"
            )
            if not teams_data or "teams" not in teams_data:
                raise Exception("无法获取球队数据")

            original_teams = teams_data["teams"]
            logger.info(f"  ✅ 获取原始数据: {len(original_teams)}支球队")

            # 第一层缓存：原始API数据缓存
            api_cache_key = "api:teams:raw"
            self.cache_manager.set_cache(api_cache_key, original_teams, ttl_seconds=300)

            # 第二层缓存：处理后数据缓存
            processed_teams = []
            for team in original_teams:
                processed_team = {
                    "external_id": str(team.get("id")),
                    "name": team.get("name"),
                    "short_name": team.get("shortName"),
                    "tla": team.get("tla"),
                    "founded": team.get("founded"),
                    "venue": team.get("venue"),
                    "processed_at": datetime.utcnow().isoformat(),
                }
                processed_teams.append(processed_team)

            self.cache_manager.set_cache(
                "processed:teams", processed_teams, ttl_seconds=600
            )

            # 第三层缓存：摘要数据缓存
            summary_data = {
                "total_teams": len(processed_teams),
                "teams_with_venue": len([t for t in processed_teams if t.get("venue")]),
                "teams_with_founded": len(
                    [t for t in processed_teams if t.get("founded")]
                ),
                "generated_at": datetime.utcnow().isoformat(),
            }

            self.cache_manager.set_cache("summary:teams", summary_data, ttl_seconds=900)

            # 一致性验证
            api_cached = self.cache_manager.get_cache(api_cache_key)
            processed_cached = self.cache_manager.get_cache("processed:teams")
            summary_cached = self.cache_manager.get_cache("summary:teams")

            # 验证数据量一致性
            if len(api_cached) != len(original_teams):
                raise Exception("API缓存数据量不一致")

            if len(processed_cached) != len(processed_teams):
                raise Exception("处理后缓存数据量不一致")

            if len(api_cached) != len(processed_cached):
                raise Exception("原始数据和处理后数据量不一致")

            # 验证数据内容一致性
            original_ids = set(str(team.get("id")) for team in original_teams)
            processed_ids = set(team.get("external_id") for team in processed_cached)

            if original_ids != processed_ids:
                missing_in_processed = original_ids - processed_ids
                extra_in_processed = processed_ids - original_ids
                logger.warning(
                    f"  ⚠️ 数据ID不一致: 缺失{len(missing_in_processed)}, 多余{len(extra_in_processed)}"
                )

            # 验证摘要数据一致性
            if summary_cached["total_teams"] != len(processed_cached):
                raise Exception("摘要数据与实际数据不一致")

            logger.info(f"  ✅ 数据一致性验证通过")
            logger.info(f"    - API缓存: {len(api_cached)}条")
            logger.info(f"    - 处理后缓存: {len(processed_cached)}条")
            logger.info(f"    - 摘要缓存: {summary_cached['total_teams']}条")

            return True

        except Exception as e:
            logger.error(f"  ❌ 数据一致性测试失败: {e}")
            return False

    async def test_error_recovery_and_robustness(self) -> bool:
        """测试错误恢复和健壮性"""
        try:
            logger.info("🔍 测试错误恢复和健壮性...")

            # 测试1: 无效API端点处理
            try:
                invalid_data = await self.data_collector._make_request_with_retry(
                    "invalid/endpoint"
                )
                if invalid_data.get("status") != 404:
                    logger.warning("  ⚠️ 无效端点处理可能有问题")
                else:
                    logger.info("  ✅ 无效端点处理正确")
            except Exception as e:
                logger.warning(f"  ⚠️ 无效端点处理异常: {e}")

            # 测试2: 缓存键冲突处理
            test_data_1 = {"name": "Team 1", "value": 100}
            test_data_2 = {"name": "Team 2", "value": 200}

            self.cache_manager.set_cache("test_key", test_data_1)
            self.cache_manager.set_cache("test_key", test_data_2)  # 覆盖

            final_data = self.cache_manager.get_cache("test_key")
            if final_data.get("name") != "Team 2":
                raise Exception("缓存键覆盖处理失败")

            logger.info("  ✅ 缓存键覆盖处理正确")

            # 测试3: 大数据量处理
            large_dataset = [
                {
                    "id": i,
                    "data": "x" * 1000,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                for i in range(500)
            ]

            start_time = time.time()
            self.cache_manager.set_cache(
                "large_dataset", large_dataset, ttl_seconds=300
            )
            cache_duration = time.time() - start_time

            retrieved_data = self.cache_manager.get_cache("large_dataset")
            if len(retrieved_data) != 500:
                raise Exception("大数据量缓存失败")

            logger.info(f"  ✅ 大数据量处理成功: 500条记录，耗时{cache_duration:.3f}秒")

            # 测试4: 内存压力测试
            memory_test_data = []
            for i in range(100):
                data = {
                    "id": i,
                    "payload": "x" * 10000,  # 10KB per record
                    "metadata": {
                        "created": datetime.utcnow().isoformat(),
                        "type": "test",
                    },
                }
                memory_test_data.append(data)

            start_time = time.time()
            success_count = 0
            for i, data in enumerate(memory_test_data):
                if self.cache_manager.set_cache(
                    f"memory_test_{i}", data, ttl_seconds=60
                ):
                    success_count += 1

            memory_duration = time.time() - start_time
            logger.info(
                f"  ✅ 内存压力测试: {success_count}/100条记录成功，耗时{memory_duration:.3f}秒"
            )

            if success_count < 95:  # 至少95%成功率
                raise Exception(f"内存压力测试成功率过低: {success_count}%")

            return True

        except Exception as e:
            logger.error(f"  ❌ 错误恢复和健壮性测试失败: {e}")
            return False

    async def test_system_performance_benchmarks(self) -> bool:
        """测试系统性能基准"""
        try:
            logger.info("🔍 测试系统性能基准...")

            benchmark_results = {}

            # 基准1: API响应时间
            api_times = []
            for _ in range(5):
                start_time = time.time()
                await self.data_collector._make_request_with_retry("competitions")
                api_times.append(time.time() - start_time)

            avg_api_time = sum(api_times) / len(api_times)
            benchmark_results["avg_api_response_time"] = avg_api_time
            logger.info(f"  ✅ API平均响应时间: {avg_api_time:.3f}秒")

            # 基准2: 缓存写入性能
            cache_write_times = []
            test_data = {"test": "data", "timestamp": datetime.utcnow().isoformat()}

            for _ in range(100):
                start_time = time.time()
                self.cache_manager.set_cache(
                    f"benchmark_{_}", test_data, ttl_seconds=300
                )
                cache_write_times.append(time.time() - start_time)

            avg_cache_write_time = sum(cache_write_times) / len(cache_write_times)
            benchmark_results["avg_cache_write_time"] = avg_cache_write_time
            logger.info(f"  ✅ 缓存平均写入时间: {avg_cache_write_time:.6f}秒")

            # 基准3: 缓存读取性能
            cache_read_times = []
            for i in range(100):
                start_time = time.time()
                self.cache_manager.get_cache(f"benchmark_{i}")
                cache_read_times.append(time.time() - start_time)

            avg_cache_read_time = sum(cache_read_times) / len(cache_read_times)
            benchmark_results["avg_cache_read_time"] = avg_cache_read_time
            logger.info(f"  ✅ 缓存平均读取时间: {avg_cache_read_time:.6f}秒")

            # 基准4: 数据处理性能
            processing_times = []
            for _ in range(10):
                sample_data = [{"id": i, "value": i * 2} for i in range(100)]

                start_time = time.time()
                processed = [
                    {
                        "id": item["id"],
                        "doubled_value": item["value"] * 2,
                        "processed": True,
                    }
                    for item in sample_data
                ]
                processing_times.append(time.time() - start_time)

            avg_processing_time = sum(processing_times) / len(processing_times)
            benchmark_results["avg_processing_time"] = avg_processing_time
            logger.info(
                f"  ✅ 数据处理平均时间: {avg_processing_time:.6f}秒 (100条记录)"
            )

            # 性能评估
            performance_score = 100

            if avg_api_time > 3.0:
                performance_score -= 20
                logger.warning(f"  ⚠️ API响应时间较慢: {avg_api_time:.3f}秒")

            if avg_cache_write_time > 0.001:
                performance_score -= 15
                logger.warning(f"  ⚠️ 缓存写入时间较慢: {avg_cache_write_time:.6f}秒")

            if avg_cache_read_time > 0.0005:
                performance_score -= 15
                logger.warning(f"  ⚠️ 缓存读取时间较慢: {avg_cache_read_time:.6f}秒")

            if avg_processing_time > 0.01:
                performance_score -= 10
                logger.warning(f"  ⚠️ 数据处理时间较慢: {avg_processing_time:.6f}秒")

            benchmark_results["performance_score"] = performance_score
            self.test_results["performance_metrics"] = benchmark_results

            logger.info(f"  ✅ 系统性能评分: {performance_score}/100")

            if performance_score < 60:
                raise Exception(f"系统性能评分过低: {performance_score}")

            return True

        except Exception as e:
            logger.error(f"  ❌ 系统性能基准测试失败: {e}")
            return False

    def _calculate_data_quality(self, data: List[Dict[str, Any]]) -> int:
        """计算数据质量评分"""
        if not data:
            return 0

        quality_score = 0
        total_items = len(data)

        # 必需字段完整性 (40分)
        required_fields = ["external_id", "name"]
        for item in data:
            completeness = sum(1 for field in required_fields if item.get(field))
            quality_score += (completeness / len(required_fields)) * 40 / total_items

        # 数据类型正确性 (20分)
        type_correct_count = 0
        for item in data:
            if isinstance(item.get("external_id"), str) and isinstance(
                item.get("name"), str
            ):
                type_correct_count += 1
        quality_score += (type_correct_count / total_items) * 20

        # 数据丰富度 (20分)
        richness_score = 0
        optional_fields = ["code", "type", "area_name", "current_matchday"]
        for item in data:
            richness = sum(1 for field in optional_fields if item.get(field))
            richness_score += richness / len(optional_fields)
        quality_score += (richness_score / total_items) * 20

        # 时间戳一致性 (20分)
        timestamp_count = sum(1 for item in data if item.get("processed_at"))
        quality_score += (timestamp_count / total_items) * 20

        return int(quality_score)

    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有端到端测试"""
        print("🚀 开始第四阶段端到端测试")
        print("=" * 60)

        start_time = datetime.now()

        tests = [
            ("完整数据流测试", self.test_complete_data_flow),
            ("并发数据访问测试", self.test_concurrent_data_access),
            ("数据一致性测试", self.test_data_consistency_across_components),
            ("错误恢复和健壮性测试", self.test_error_recovery_and_robustness),
            ("系统性能基准测试", self.test_system_performance_benchmarks),
        ]

        for test_name, test_func in tests:
            print(f"\n🔍 执行 {test_name}...")
            self.test_results["total_tests"] += 1

            try:
                if await test_func():
                    print(f"✅ {test_name}通过")
                    self.test_results["passed_tests"] += 1
                else:
                    print(f"❌ {test_name}失败")
                    self.test_results["failed_tests"] += 1
            except Exception as e:
                print(f"❌ {test_name}异常: {e}")
                self.test_results["failed_tests"] += 1
                self.test_results["errors"].append(f"{test_name}: {e}")

        end_time = datetime.now()
        duration = end_time - start_time

        print("\n" + "=" * 60)
        print(f"📊 第四阶段端到端测试完成!")
        print(f"   总计: {self.test_results['total_tests']}")
        print(f"   通过: {self.test_results['passed_tests']}")
        print(f"   失败: {self.test_results['failed_tests']}")
        print(f"   耗时: {duration.total_seconds():.2f} 秒")

        # 性能指标摘要
        if self.test_results["performance_metrics"]:
            print(f"\n⚡ 性能指标摘要:")
            metrics = self.test_results["performance_metrics"]
            for key, value in metrics.items():
                if isinstance(value, float):
                    print(f"   {key}: {value:.6f}")
                else:
                    print(f"   {key}: {value}")

        # 数据质量指标
        if self.test_results["data_quality_metrics"]:
            print(f"\n📈 数据质量指标:")
            for key, value in self.test_results["data_quality_metrics"].items():
                print(f"   {key}: {value}/100")

        if self.test_results["errors"]:
            print("\n❌ 错误详情:")
            for error in self.test_results["errors"]:
                print(f"   - {error}")

        success_rate = 0
        if self.test_results["total_tests"] > 0:
            success_rate = (
                self.test_results["passed_tests"] / self.test_results["total_tests"]
            ) * 100

        print(f"\n🎯 成功率: {success_rate:.1f}%")

        if self.test_results["failed_tests"] == 0:
            print("🎉 所有测试通过！")
            print("✅ 完整数据流正常工作")
            print("✅ 并发访问性能优秀")
            print("✅ 数据一致性保证")
            print("✅ 错误恢复机制完善")
            print("✅ 系统性能达到基准")
            print("🚀 第四阶段端到端测试完成！")
            return True
        else:
            print("⚠️  部分测试失败，请检查实现")
            return False


async def main():
    """主测试函数"""
    tester = Stage4E2ETester()

    try:
        # 初始化测试环境
        await tester.initialize()

        # 运行所有测试
        success = await tester.run_all_tests()

        # 清理测试环境
        await tester.cleanup()

        print(f"\n退出码: {0 if success else 1}")
        return success

    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        print(f"\n❌ 测试执行异常: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
