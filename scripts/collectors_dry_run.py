#!/usr/bin/env python3
"""
采集器全链路集成测试 (Dry-Run)
Collectors Full-Chain Integration Test (Dry-Run)

该脚本执行从工厂创建客户端到采集数据的完整流程验证：
1. 使用 HttpClientFactory 创建 FotMob 采集器实例
2. 执行真实的采集任务（限制数量）
3. 验证请求成功率、速率限制、Token刷新机制
4. 生成详细的运行报告

使用示例:
    python scripts/collectors_dry_run.py --source fotmob --max-fixtures 5
    python scripts/collectors_dry_run.py --source fotmob --test-health --verbose
    python scripts/collectors_dry_run.py --source fotmob --test-rate-limiting

作者: Lead Collector Engineer
创建时间: 2025-12-06
版本: 1.0.0
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.collectors.http_client_factory import get_http_client_factory, FotMobConfig


class DryRunTester:
    """Dry-Run 测试器"""

    def __init__(self, args):
        self.args = args
        self.source = getattr(args, "source", "fotmob")
        self.verbose = getattr(args, "verbose", False)
        self.max_fixtures = getattr(args, "max_fixtures", 5)
        self.max_matches = getattr(args, "max_matches", 10)
        self.test_health = getattr(args, "test_health", False)
        self.test_rate_limiting = getattr(args, "test_rate_limiting", False)
        self.use_proxies = getattr(args, "use_proxies", False)

        # 测试结果
        self.test_results = {
            "test_start_time": time.time(),
            "test_end_time": None,
            "total_duration": 0.0,
            "fixtures_collected": 0,
            "matches_collected": 0,
            "teams_collected": 0,
            "health_checks": 0,
            "errors": [],
            "monitoring_stats": {},
        }

    async def setup(self) -> None:
        """设置测试环境"""
        print("🏭 设置 Dry-Run 测试环境...")

        try:
            # 获取工厂实例
            self.factory = get_http_client_factory()
            print("   ✅ HTTP客户端工厂获取完成")

            # 配置数据源
            if self.source == "fotmob":
                config = FotMobConfig()

                # 根据参数调整配置
                if self.use_proxies:
                    print("   🌐 启用代理配置")
                    # 代理配置已在默认配置中
                else:
                    print("   ⚠️ 禁用代理配置")
                    config.proxy_config = None

                # 自定义配置用于测试
                if self.test_rate_limiting:
                    print("   🚦 调整速率限制用于测试")
                    config.rate_limit_config = {
                        "rate": 1.0,  # 1 QPS - 用于测试速率限制
                        "burst": 2,  # 突发容量
                        "max_wait_time": 15.0,
                    }

                self.factory.register_config(self.source, config)
                print(f"   ✅ {self.source} 配置注册完成")

            else:
                raise ValueError(f"Unsupported data source: {self.source}")

            print("✅ 测试环境设置完成")

        except Exception as e:
            print(f"❌ 环境设置失败: {e}")
            raise

    async def teardown(self) -> None:
        """清理测试环境"""
        print("\n🧹 清理测试环境...")

        try:
            # 记录测试结束时间
            self.test_results["test_end_time"] = time.time()
            self.test_results["total_duration"] = (
                self.test_results["test_end_time"]
                - self.test_results["test_start_time"]
            )

            # 获取监控统计
            monitor = self.factory.get_monitor()
            self.test_results["monitoring_stats"] = monitor.get_stats()

            print("   ✅ 统计信息已收集")

        except Exception as e:
            print(f"⚠️ 清理过程中出现错误: {e}")

    async def run_health_check(self) -> bool:
        """运行健康检查测试"""
        print("\n🏥 运行健康检查测试...")

        try:
            # 创建采集器
            collector = await self.factory.create_collector(self.source)

            # 执行健康检查
            health_result = await collector.check_health()

            print(f"   📊 健康状态: {health_result['status']}")
            print(f"   📊 响应时间: {health_result['response_time_ms']:.2f}ms")

            if "details" in health_result:
                details = health_result["details"]
                if "api_connectivity" in details:
                    print(
                        f"   📊 API连通性: {'✅ 正常' if details['api_connectivity'] else '❌ 异常'}"
                    )
                if "token_stats" in details:
                    token_stats = details["token_stats"]
                    print(
                        f"   📊 Token状态: 有效={token_stats['valid_tokens']}, 使用次数={token_stats['total_usage']}"
                    )

            # 清理
            await collector.close()
            self.test_results["health_checks"] += 1

            print("   ✅ 健康检查完成")
            return True

        except Exception as e:
            error_msg = f"健康检查失败: {e}"
            print(f"   ❌ {error_msg}")
            self.test_results["errors"].append(error_msg)
            return False

    async def test_fixture_collection(self) -> bool:
        """测试赛程数据采集"""
        print(f"\n⚽ 测试赛程数据采集 (最多 {self.max_fixtures} 场比赛)...")

        try:
            # 创建采集器
            collector = await self.factory.create_collector(self.source)

            # 采集英超联赛赛程 (league_id=47)
            print("   📋 开始采集英超赛程数据...")

            fixtures = await collector.collect_fixtures(47, "2024-2025")

            if not fixtures:
                print("   ⚠️ 未获取到赛程数据")
                self.test_results["errors"].append("未获取到赛程数据")
                return False

            print(f"   ✅ 成功采集 {len(fixtures)} 场比赛赛程")

            # 显示前几场比赛信息
            for i, fixture in enumerate(fixtures[:3], 1):
                print(
                    f"      {i}. {fixture['home_team']} vs {fixture['away_team']} "
                    f"({fixture.get('status', 'N/A')})"
                )

            if len(fixtures) > self.max_fixtures:
                fixtures = fixtures[: self.max_fixtures]
                print(f"   📋 限制为 {self.max_fixtures} 场比赛进行后续测试")

            self.test_results["fixtures_collected"] = len(fixtures)

            # 清理
            await collector.close()

            return True

        except Exception as e:
            error_msg = f"赛程采集失败: {e}"
            print(f"   ❌ {error_msg}")
            self.test_results["errors"].append(error_msg)
            return False

    async def test_match_details_collection(self) -> bool:
        """测试比赛详情采集"""
        print(f"\n📊 测试比赛详情采集 (最多 {self.max_matches} 场比赛)...")

        try:
            # 先获取赛程数据
            collector = await self.factory.create_collector(self.source)
            fixtures = await collector.collect_fixtures(47, "2024-2025")
            await collector.close()

            if not fixtures:
                print("   ⚠️ 无法获取赛程数据，跳过比赛详情测试")
                return False

            # 选择比赛进行详情采集
            test_matches = fixtures[: self.max_matches]
            print(f"   📋 开始采集 {len(test_matches)} 场比赛详情...")

            successful_matches = 0
            for i, fixture in enumerate(test_matches, 1):
                match_id = fixture.get("match_id")
                if not match_id:
                    continue

                try:
                    print(
                        f"   📊 {i}/{len(test_matches)} 采集比赛详情: {fixture['home_team']} vs {fixture['away_team']}"
                    )

                    details = await collector.collect_match_details(match_id)

                    # 验证关键字段
                    if "home_team" in details and "away_team" in details:
                        successful_matches += 1
                        print(
                            f"      ✅ 成功 - 比分: {details.get('home_score', 'N/A')}-{details.get('away_score', 'N/A')}"
                        )
                    else:
                        print("      ⚠️ 数据不完整")

                except Exception as e:
                    print(f"      ❌ 失败: {e}")

            self.test_results["matches_collected"] = successful_matches
            print(f"   ✅ 成功采集 {successful_matches}/{len(test_matches)} 场比赛详情")

            # 清理
            await collector.close()

            return successful_matches > 0

        except Exception as e:
            error_msg = f"比赛详情采集失败: {e}"
            print(f"   ❌ {error_msg}")
            self.test_results["errors"].append(error_msg)
            return False

    async def test_rate_limiting(self) -> bool:
        """测试速率限制"""
        if not self.test_rate_limiting:
            return True

        print("\n🚦 测试速率限制机制...")

        try:
            # 创建采集器
            collector = await self.factory.create_collector(self.source)

            # 并发执行多个健康检查来测试速率限制
            start_time = time.monotonic()

            tasks = []
            for _i in range(5):  # 5个并发请求
                task = asyncio.create_task(collector.check_health())
                tasks.append(task)

            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            elapsed = time.monotonic() - start_time
            successful = sum(1 for r in results if not isinstance(r, Exception))

            print(f"   📊 5个并发请求耗时: {elapsed:.3f}s")
            print(f"   📊 成功请求: {successful}/5")

            # 验证速率限制是否生效
            if elapsed >= 3.0:  # 应该被速率限制延迟
                print("   ✅ 速率限制生效")
                rate_limit_test_passed = True
            else:
                print("   ⚠️ 速率限制可能未生效")
                rate_limit_test_passed = False

            # 清理
            await collector.close()

            return rate_limit_test_passed

        except Exception as e:
            error_msg = f"速率限制测试失败: {e}"
            print(f"   ❌ {error_msg}")
            self.test_results["errors"].append(error_msg)
            return False

    async def run_concurrent_test(self) -> bool:
        """运行并发测试"""
        print("\n🔄 运行并发测试...")

        try:
            # 创建采集器
            collector = await self.factory.create_collector(self.source)

            # 并发执行多个不同类型的请求
            async def task_health():
                return await collector.check_health()

            async def task_fixtures():
                return await collector.collect_fixtures(47, "2024-2025")

            async def task_team_info():
                return await collector.collect_team_info("8456")  # Arsenal team ID

            # 创建并发任务
            tasks = [
                asyncio.create_task(task_health()),
                asyncio.create_task(task_fixtures()),
                asyncio.create_task(task_team_info()),
            ]

            # 执行并发任务
            start_time = time.monotonic()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.monotonic() - start_time

            # 分析结果
            successful = sum(1 for r in results if not isinstance(r, Exception))

            print(f"   📊 并发测试耗时: {elapsed:.3f}s")
            print(f"   📊 成功任务: {successful}/{len(tasks)}")

            # 清理
            await collector.close()

            return successful >= len(tasks) // 2  # 至少一半成功

        except Exception as e:
            error_msg = f"并发测试失败: {e}"
            print(f"   ❌ {error_msg}")
            self.test_results["errors"].append(error_msg)
            return False

    async def generate_report(self) -> None:
        """生成测试报告"""
        print("\n📄 生成测试报告...")

        # 创建报告目录
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        # 生成报告内容
        report = {
            "test_summary": {
                "test_source": self.source,
                "test_duration": round(self.test_results["total_duration"], 2),
                "test_start": time.strftime(
                    "%Y-%m-%d %H:%M:%S UTC",
                    time.gmtime(self.test_results["test_start_time"]),
                ),
                "test_end": time.strftime(
                    "%Y-%m-%d %H:%M:%S UTC",
                    time.gmtime(self.test_results["test_end_time"]),
                )
                if self.test_results["test_end_time"]
                else None,
            },
            "collection_results": {
                "fixtures_collected": self.test_results["fixtures_collected"],
                "matches_collected": self.test_results["matches_collected"],
                "teams_collected": self.test_results["teams_collected"],
                "health_checks": self.test_results["health_checks"],
            },
            "monitoring_statistics": self.test_results.get("monitoring_stats", {}),
            "errors": self.test_results["errors"],
        }

        # 写入Markdown报告
        report_file = reports_dir / "dry_run_results.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# 采集器 Dry-Run 测试报告\n\n")
            f.write("## 测试概览\n")
            f.write(f"- **数据源**: {report['test_summary']['test_source']}\n")
            f.write(
                f"- **测试时长**: {report['test_summary']['test_duration']:.2f}秒\n"
            )
            f.write(f"- **测试开始**: {report['test_summary']['test_start']}\n")
            if report["test_summary"]["test_end"]:
                f.write(f"- **测试结束**: {report['test_summary']['test_end']}\n")
            f.write("\n")

            f.write("## 采集结果\n")
            f.write(
                f"- **赛程数据采集**: {report['collection_results']['fixtures_collected']} 场\n"
            )
            f.write(
                f"- **比赛详情采集**: {report['collection_results']['matches_collected']} 场\n"
            )
            f.write(
                f"- **球队信息采集**: {report['collection_results']['teams_collected']} 个\n"
            )
            f.write(
                f"- **健康检查次数**: {report['collection_results']['health_checks']} 次\n"
            )
            f.write("\n")

            f.write("## 监控统计\n")
            monitor_stats = report.get("monitoring_statistics", {})
            if monitor_stats:
                f.write(f"- **总请求数**: {monitor_stats.get('total_requests', 0)}\n")
                f.write(
                    f"- **成功请求数**: {monitor_stats.get('successful_requests', 0)}\n"
                )
                f.write(
                    f"- **失败请求数**: {monitor_stats.get('failed_requests', 0)}\n"
                )
                f.write(f"- **成功率**: {monitor_stats.get('success_rate', 0):.1f}%\n")
                f.write(
                    f"- **平均响应时间**: {monitor_stats.get('avg_response_time_ms', 0):.2f}ms\n"
                )
                f.write(
                    f"- **Token刷新次数**: {monitor_stats.get('token_refreshes', 0)}\n"
                )
                f.write(
                    f"- **代理轮换次数**: {monitor_stats.get('proxy_rotations', 0)}\n"
                )
            f.write("\n")

            if report["errors"]:
                f.write("## 错误信息\n")
                for i, error in enumerate(report["errors"], 1):
                    f.write(f"{i}. {error}\n")
                f.write("\n")

            f.write("## 测试配置\n")
            f.write(f"- **数据源**: {self.source}\n")
            f.write(f"- **最大赛程数**: {self.max_fixtures}\n")
            f.write(f"- **最大比赛数**: {self.max_matches}\n")
            f.write(f"- **健康检查**: {'启用' if self.test_health else '禁用'}\n")
            f.write(
                f"- **速率限制测试**: {'启用' if self.test_rate_limiting else '禁用'}\n"
            )
            f.write(f"- **代理使用**: {'启用' if self.use_proxies else '禁用'}\n")
            f.write(f"- **详细输出**: {'启用' if self.verbose else '禁用'}\n")

        # 写入JSON报告
        json_report_file = reports_dir / "dry_run_results.json"
        with open(json_report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print("   ✅ 报告已保存:")
        print(f"      📄 Markdown: {report_file}")
        print(f"      📊 JSON: {json_report_file}")

    async def run_all_tests(self) -> None:
        """运行所有测试"""
        print(f"🚀 开始执行 {self.source} 采集器 Dry-Run 测试...")
        print(f"   配置: 最大赛程={self.max_fixtures}, 最大比赛={self.max_matches}")
        print(f"   配置: 健康检查={'启用' if self.test_health else '禁用'}")
        print(f"   配置: 速率限制测试={'启用' if self.test_rate_limiting else '禁用'}")
        print(f"   配置: 代理={'启用' if self.use_proxies else '禁用'}")

        # 定义测试列表
        tests = []

        if self.test_health:
            tests.append(("健康检查测试", self.run_health_check))

        tests.append(("赛程数据采集测试", self.test_fixture_collection))
        tests.append(("比赛详情采集测试", self.test_match_details_collection))

        if self.test_rate_limiting:
            tests.append(("速率限制测试", self.test_rate_limiting))

        tests.append(("并发测试", self.run_concurrent_test))

        # 运行测试
        passed_tests = 0
        total_tests = len(tests)

        for test_name, test_func in tests:
            try:
                result = await test_func()
                if result:
                    passed_tests += 1
                    print(f"✅ {test_name}: 通过")
                else:
                    print(f"❌ {test_name}: 失败")
            except Exception as e:
                print(f"💥 {test_name}: 异常 - {e}")
                self.test_results["errors"].append(f"{test_name} 异常: {e}")

        # 生成测试结果摘要
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print("\n📊 测试结果摘要:")
        print(f"   总测试数: {total_tests}")
        print(f"   通过测试: {passed_tests} ({success_rate:.1f}%)")
        print(f"   失败测试: {total_tests - passed_tests} ({100 - success_rate:.1f}%)")

        if self.test_results["errors"]:
            print("\n❌ 错误详情:")
            for i, error in enumerate(self.test_results["errors"], 1):
                print(f"   {i}. {error}")

        # 结果评估
        if success_rate >= 80:
            print("\n🎉 测试结果: 优秀 (成功率 >= 80%)")
        elif success_rate >= 60:
            print("\n✅ 测试结果: 良好 (成功率 >= 60%)")
        else:
            print("\n⚠️ 测试结果: 需要改进 (成功率 < 60%)")

        # 生成报告
        await self.generate_report()


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="采集器全链路集成测试 (Dry-Run)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基础测试
  python scripts/collectors_dry_run.py --source fotmob --max-fixtures 5

  # 包含健康检查的完整测试
  python scripts/collectors_dry_run.py --source fotmob --test-health --max-fixtures 10

  # 测试速率限制
  python scripts/collectors_dry_run.py --source fotmob --test-rate-limiting

  # 使用代理的测试
  python scripts/collectors_dry_run.py --source fotmob --use-proxies --verbose
        """,
    )

    parser.add_argument(
        "--source", default="fotmob", choices=["fotmob"], help="数据源 (默认: fotmob)"
    )

    parser.add_argument(
        "--max-fixtures", type=int, default=5, help="最大采集赛程数量 (默认: 5)"
    )

    parser.add_argument(
        "--max-matches", type=int, default=10, help="最大采集比赛详情数量 (默认: 10)"
    )

    parser.add_argument("--test-health", action="store_true", help="包含健康检查测试")

    parser.add_argument(
        "--test-rate-limiting", action="store_true", help="测试速率限制机制"
    )

    parser.add_argument("--use-proxies", action="store_true", help="使用代理进行测试")

    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_args()

    try:
        tester = DryRunTester(args)
        await tester.setup()
        await tester.run_all_tests()
        await tester.teardown()

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
    except Exception as e:
        print(f"❌ 错误: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
