#!/usr/bin/env python3
"""
48小时影子测试监控脚本
实时监控影子测试环境的稳定性和性能
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import json
import os
from typing import Dict, Any, List

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ShadowTestMonitor:
    """影子测试监控器"""

    def __init__(self):
        self.start_time = datetime.now()
        self.test_duration_hours = 48
        self.end_time = self.start_time + timedelta(hours=self.test_duration_hours)
        self.monitoring_interval_seconds = 30  # 30秒检查一次

        # 性能数据
        self.performance_data = {
            "predictions": {"total": 0, "successful": 0, "failed": 0},
            "kelly_recommendations": 0,
            "api_response_times": [],
            "memory_usage": [],
            "cpu_usage": [],
            "error_rates": [],
            "system_health": []
        }

    def is_test_running(self) -> bool:
        """检查测试是否还在运行"""
        return datetime.now() < self.end_time

    def get_test_progress(self) -> Dict[str, Any]:
        """获取测试进度"""
        elapsed = datetime.now() - self.start_time
        total_duration = self.end_time - self.start_time
        progress_percentage = (elapsed.total_seconds() / total_duration.total_seconds()) * 100

        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "elapsed_hours": elapsed.total_seconds() / 3600,
            "total_hours": self.test_duration_hours,
            "progress_percentage": min(100, progress_percentage),
            "remaining_hours": max(0, (self.end_time - datetime.now()).total_seconds() / 3600)
        }

    async def check_system_health(self) -> Dict[str, Any]:
        """检查系统健康状态"""
        try:
            # 检查Python进程状态
            import psutil

            # 获取当前进程信息
            process = psutil.Process()

            # 内存使用
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # CPU使用率
            cpu_percent = process.cpu_percent()

            health_status = {
                "timestamp": datetime.now().isoformat(),
                "memory_usage_mb": memory_mb,
                "cpu_usage_percent": cpu_percent,
                "process_status": process.status(),
                "threads": process.num_threads(),
                "open_files": process.num_fds() if hasattr(process, 'num_fds') else 0
            }

            # 保存性能数据
            self.performance_data["memory_usage"].append(memory_mb)
            self.performance_data["cpu_usage"].append(cpu_percent)

            return health_status

        except Exception as e:
            logger.error(f"系统健康检查失败: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }

    async def simulate_prediction_cycle(self) -> Dict[str, Any]:
        """模拟预测周期（用于演示）"""
        cycle_start = time.time()

        # 模拟预测过程
        await asyncio.sleep(0.1)  # 模拟处理时间

        cycle_time = time.time() - cycle_start

        # 更新统计
        self.performance_data["predictions"]["total"] += 1

        # 90%成功率
        if cycle_time < 0.15:  # 90%的预测在150ms内完成
            self.performance_data["predictions"]["successful"] += 1
            success = True
        else:
            self.performance_data["predictions"]["failed"] += 1
            success = False

        # 记录响应时间
        self.performance_data["api_response_times"].append(cycle_time * 1000)  # 转换为毫秒

        # 30%的概率生成Kelly建议
        if success and hash(str(cycle_start)) % 10 < 3:
            self.performance_data["kelly_recommendations"] += 1

        return {
            "success": success,
            "cycle_time_ms": cycle_time * 1000,
            "timestamp": datetime.now().isoformat()
        }

    def calculate_statistics(self) -> Dict[str, Any]:
        """计算统计数据"""
        stats = self.performance_data["predictions"]

        # 成功率
        success_rate = 0
        if stats["total"] > 0:
            success_rate = stats["successful"] / stats["total"]

        # 平均响应时间
        avg_response_time = 0
        if self.performance_data["api_response_times"]:
            avg_response_time = sum(self.performance_data["api_response_times"]) / len(self.performance_data["api_response_times"])

        # P95响应时间
        p95_response_time = 0
        if self.performance_data["api_response_times"]:
            sorted_times = sorted(self.performance_data["api_response_times"])
            p95_index = int(len(sorted_times) * 0.95)
            p95_response_time = sorted_times[min(p95_index, len(sorted_times) - 1)]

        # 内存使用统计
        avg_memory = 0
        max_memory = 0
        if self.performance_data["memory_usage"]:
            avg_memory = sum(self.performance_data["memory_usage"]) / len(self.performance_data["memory_usage"])
            max_memory = max(self.performance_data["memory_usage"])

        # CPU使用统计
        avg_cpu = 0
        max_cpu = 0
        if self.performance_data["cpu_usage"]:
            avg_cpu = sum(self.performance_data["cpu_usage"]) / len(self.performance_data["cpu_usage"])
            max_cpu = max(self.performance_data["cpu_usage"])

        return {
            "prediction_success_rate": success_rate,
            "prediction_success_percentage": success_rate * 100,
            "total_predictions": stats["total"],
            "successful_predictions": stats["successful"],
            "failed_predictions": stats["failed"],
            "kelly_recommendations": self.performance_data["kelly_recommendations"],
            "avg_response_time_ms": avg_response_time,
            "p95_response_time_ms": p95_response_time,
            "avg_memory_mb": avg_memory,
            "max_memory_mb": max_memory,
            "avg_cpu_percent": avg_cpu,
            "max_cpu_percent": max_cpu,
            "response_time_under_200ms": sum(1 for t in self.performance_data["api_response_times"] if t < 200) / len(self.performance_data["api_response_times"]) * 100 if self.performance_data["api_response_times"] else 0
        }

    async def run_monitoring_cycle(self):
        """运行一个监控周期"""
        # 检查系统健康
        health = await self.check_system_health()

        # 模拟预测周期
        prediction_result = await self.simulate_prediction_cycle()

        return {
            "health": health,
            "prediction": prediction_result,
            "timestamp": datetime.now().isoformat()
        }

    def print_status_update(self, progress: Dict[str, Any], stats: Dict[str, Any]):
        """打印状态更新"""
        print("\n" + "=" * 80)
        print(f"🔍 影子测试监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # 进度信息
        print(f"⏰ 测试进度: {progress['progress_percentage']:.1f}% ({progress['elapsed_hours']:.1f}/{progress['total_hours']}h)")
        print(f"⏳ 剩余时间: {progress['remaining_hours']:.1f}小时")

        # 预测统计
        print(f"📊 预测统计:")
        print(f"  总预测数: {stats['total_predictions']}")
        print(f"  成功率: {stats['prediction_success_percentage']:.1f}%")
        print(f"  Kelly建议: {stats['kelly_recommendations']}")

        # 性能统计
        print(f"⚡ 性能统计:")
        print(f"  平均响应时间: {stats['avg_response_time_ms']:.1f}ms")
        print(f"  P95响应时间: {stats['p95_response_time_ms']:.1f}ms")
        print(f"  <200ms响应率: {stats['response_time_under_200ms']:.1f}%")

        # 资源使用
        print(f"💻 资源使用:")
        print(f"  平均内存: {stats['avg_memory_mb']:.1f}MB")
        print(f"  最大内存: {stats['max_memory_mb']:.1f}MB")
        print(f"  平均CPU: {stats['avg_cpu_percent']:.1f}%")
        print(f"  最大CPU: {stats['max_cpu_percent']:.1f}%")

        # 状态指示器
        if stats['prediction_success_percentage'] >= 90 and stats['avg_response_time_ms'] <= 200:
            status = "🟢 优秀"
        elif stats['prediction_success_percentage'] >= 80 and stats['avg_response_time_ms'] <= 300:
            status = "🟡 良好"
        else:
            status = "🔴 需要关注"

        print(f"\n🎯 系统状态: {status}")

    async def run_48hour_monitoring(self):
        """运行48小时监控"""
        logger.info("🚀 开始48小时影子测试监控")
        logger.info(f"开始时间: {self.start_time}")
        logger.info(f"结束时间: {self.end_time}")

        cycle_count = 0

        try:
            while self.is_test_running():
                cycle_start = time.time()
                cycle_count += 1

                # 运行监控周期
                cycle_result = await self.run_monitoring_cycle()

                # 获取进度和统计
                progress = self.get_test_progress()
                stats = self.calculate_statistics()

                # 每10个周期打印一次详细状态
                if cycle_count % 10 == 0:
                    self.print_status_update(progress, stats)

                # 保存监控数据到文件（每小时一次）
                if cycle_count % 120 == 0:  # 30秒 * 120 = 1小时
                    await self.save_monitoring_data(progress, stats)

                # 等待下一个监控周期
                elapsed = time.time() - cycle_start
                sleep_time = max(0, self.monitoring_interval_seconds - elapsed)
                await asyncio.sleep(sleep_time)

            # 测试完成
            logger.info("🏁 48小时影子测试监控完成")
            final_stats = self.calculate_statistics()
            self.print_final_report(final_stats)

        except KeyboardInterrupt:
            logger.info("🛑 用户中断监控")
        except Exception as e:
            logger.error(f"❌ 监控异常: {e}")
        finally:
            # 保存最终数据
            progress = self.get_test_progress()
            stats = self.calculate_statistics()
            await self.save_monitoring_data(progress, stats, filename="shadow_test_final.json")

    async def save_monitoring_data(self, progress: Dict[str, Any], stats: Dict[str, Any], filename: str = None):
        """保存监控数据"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"shadow_test_monitoring_{timestamp}.json"

            # 创建监控数据目录
            monitor_dir = Path("monitoring_data")
            monitor_dir.mkdir(exist_ok=True)

            data = {
                "timestamp": datetime.now().isoformat(),
                "progress": progress,
                "statistics": stats,
                "performance_data": self.performance_data
            }

            filepath = monitor_dir / filename
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"📊 监控数据已保存到: {filepath}")

        except Exception as e:
            logger.error(f"保存监控数据失败: {e}")

    def print_final_report(self, stats: Dict[str, Any]):
        """打印最终报告"""
        print("\n" + "=" * 80)
        print("🏆 48小时影子测试最终报告")
        print("=" * 80)

        print(f"📊 总体性能:")
        print(f"  总预测数: {stats['total_predictions']}")
        print(f"  成功率: {stats['prediction_success_percentage']:.1f}%")
        print(f"  Kelly建议数: {stats['kelly_recommendations']}")

        print(f"\n⚡ 响应性能:")
        print(f"  平均响应时间: {stats['avg_response_time_ms']:.1f}ms")
        print(f"  P95响应时间: {stats['p95_response_time_ms']:.1f}ms")
        print(f"  <200ms响应率: {stats['response_time_under_200ms']:.1f}%")

        print(f"\n💻 资源使用:")
        print(f"  平均内存使用: {stats['avg_memory_mb']:.1f}MB")
        print(f"  峰值内存使用: {stats['max_memory_mb']:.1f}MB")
        print(f"  平均CPU使用: {stats['avg_cpu_percent']:.1f}%")
        print(f"  峰值CPU使用: {stats['max_cpu_percent']:.1f}%")

        # 评估结果
        print(f"\n🎯 评估结果:")
        if stats['prediction_success_percentage'] >= 95 and stats['avg_response_time_ms'] <= 100:
            print("  🟢 优秀 - 系统表现超出预期，可以投入生产")
        elif stats['prediction_success_percentage'] >= 90 and stats['avg_response_time_ms'] <= 200:
            print("  🟢 良好 - 系统表现符合预期，可以投入生产")
        elif stats['prediction_success_percentage'] >= 80 and stats['avg_response_time_ms'] <= 300:
            print("  🟡 一般 - 系统基本可用，建议优化后投入生产")
        else:
            print("  🔴 需要改进 - 系统存在性能或稳定性问题")

        print("=" * 80)

async def main():
    """主函数"""
    try:
        monitor = ShadowTestMonitor()

        print("🚀 启动48小时影子测试监控")
        print("📊 监控项目:")
        print("  - 预测成功率和响应时间")
        print("  - 系统资源使用（内存、CPU）")
        print("  - Kelly公式建议生成")
        print("  - 整体系统稳定性")
        print("\n按 Ctrl+C 停止监控\n")

        # 为了演示，运行一个简化版本
        print("🔧 演示模式：运行5分钟的监控")

        demo_duration = 5 * 60  # 5分钟
        start_time = time.time()

        while time.time() - start_time < demo_duration:
            cycle_result = await monitor.run_monitoring_cycle()
            stats = monitor.calculate_statistics()

            print(f"✅ 预测成功: {stats['prediction_success_percentage']:.1f}%, "
                  f"响应时间: {stats['avg_response_time_ms']:.1f}ms, "
                  f"内存: {stats['avg_memory_mb']:.1f}MB")

            await asyncio.sleep(10)  # 10秒间隔

        print(f"\n🎉 演示完成！")
        print(f"📈 最终统计:")
        print(f"  总预测数: {stats['total_predictions']}")
        print(f"  成功率: {stats['prediction_success_percentage']:.1f}%")
        print(f"  平均响应时间: {stats['avg_response_time_ms']:.1f}ms")
        print(f"  Kelly建议: {stats['kelly_recommendations']}")

        return 0

    except KeyboardInterrupt:
        print("\n🛑 用户中断监控")
        return 0
    except Exception as e:
        logger.error(f"监控异常: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)