#!/usr/bin/env python3
"""
Titan007 数据采集管道启动脚本
Titan007 Data Collection Pipeline Launcher

简化Prefect调度系统的使用，提供一键启动和监控功能。

使用方法:
    # 启动完整调度系统
    python scripts/run_titan_pipeline.py --start

    # 仅启动常规模式
    python scripts/run_titan_pipeline.py --mode regular

    # 启动临场模式（高频采集）
    python scripts/run_titan_pipeline.py --mode live

    # 混合模式（常规+临场）
    python scripts/run_titan_pipeline.py --mode hybrid

    # 监控系统状态
    python scripts/run_titan_pipeline.py --monitor

    # 快速测试
    python scripts/run_titan_pipeline.py --test
"""

import asyncio
import sys
import signal
import logging
from datetime import datetime
from pathlib import Path

import httpx

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.flows.titan_flow import titan_regular_flow
from scripts.deploy_flow import PrefectDeploymentManager

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TitanPipelineLauncher:
    """Titan007数据采集管道启动器"""

    def __init__(self):
        self.is_running = False
        self.monitoring = False
        self.current_mode = None

    async def start_full_system(self):
        """启动完整调度系统"""
        logger.info("🚀 启动Titan007完整调度系统...")

        # 1. 注册所有Flow
        async with PrefectDeploymentManager() as manager:
            logger.info("📦 注册Prefect Flows...")
            results = await manager.register_flows()

            if results["error_count"] > 0:
                logger.warning(f"⚠️ 部分Flow注册失败: {results['error_count']}个")
            else:
                logger.info("✅ 所有Flow注册成功")

        # 2. 启动监控
        self.is_running = True
        self.current_mode = "full"
        await self._start_monitoring()

    async def start_mode_specific(self, mode: str):
        """启动特定模式的Flow"""
        logger.info(f"🚀 启动Titan007 {mode} 模式...")

        mode_configs = {
            "regular": {
                "deployment": "titan-regular-deployment",
                "description": "常规模式 - 每日数据采集",
            },
            "live": {
                "deployment": "titan-live-deployment",
                "description": "临场模式 - 高频实时采集",
            },
            "hybrid": {
                "deployment": "titan-hybrid-deployment",
                "description": "混合模式 - 常规+临场",
            },
        }

        if mode not in mode_configs:
            raise ValueError(f"不支持的模式: {mode}")

        config = mode_configs[mode]

        # 触发指定部署
        async with PrefectDeploymentManager() as manager:
            logger.info(f"📋 触发部署: {config['deployment']}")
            result = await manager.trigger_deployment(config["deployment"])

            if result["status"] == "triggered":
                logger.info(f"✅ {config['description']} 启动成功")
                logger.info(f"🏃 运行ID: {result['flow_run_id']}")
                logger.info(
                    f"📈 监控地址: http://localhost:4200/flow-run/{result['flow_run_id']}"
                )
            else:
                logger.error(f"❌ 启动失败: {result['message']}")
                return

        self.current_mode = mode
        self.is_running = True

        # 启动监控
        await self._start_monitoring()

    async def run_test(self):
        """运行快速测试"""
        logger.info("🧪 运行Titan007快速测试...")

        try:
            # 测试常规模式（小规模）
            logger.info("📋 测试常规数据采集...")
            test_result = await titan_regular_flow(
                start_date=datetime.now().strftime("%Y-%m-%d"),
                days_ahead=1,
                batch_size=5,  # 小批次测试
                max_concurrency=3,
            )

            logger.info("✅ 常规模式测试完成")
            logger.info(f"📊 测试结果: {test_result}")

            # 验证结果
            if test_result.get("total_odds", 0) > 0:
                logger.info("🎉 数据采集测试成功!")
                logger.info(f"   - 获取比赛: {test_result.get('fixtures', 0)}")
                logger.info(f"   - ID对齐: {test_result.get('aligned', 0)}")
                logger.info(f"   - 采集成功: {test_result.get('collected', 0)}")
                logger.info(f"   - 总赔率数: {test_result.get('total_odds', 0)}")
            else:
                logger.warning("⚠️ 测试完成但未获取到数据，可能原因:")
                logger.warning("   - 当前时间无可用比赛")
                logger.warning("   - API访问受限")
                logger.warning("   - 网络连接问题")

        except Exception as e:
            logger.error(f"❌ 测试失败: {str(e)}")
            raise

    async def monitor_system(self):
        """监控系统状态"""
        logger.info("📊 监控Titan007系统状态...")

        async with PrefectDeploymentManager() as manager:
            deployments = await manager.list_deployments()

            if not deployments:
                print("📭 暂无活跃的部署")
                return

            print("\n" + "=" * 60)
            print("📊 Titan007 系统状态监控")
            print("=" * 60)

            total_deployments = len(deployments)
            active_deployments = sum(1 for dep in deployments if dep["is_active"])
            scheduled_deployments = sum(1 for dep in deployments if dep["schedule"])

            print(f"📦 总部署数: {total_deployments}")
            print(f"✅ 活跃部署: {active_deployments}")
            print(f"⏰ 调度部署: {scheduled_deployments}")

            print("\n📋 部署详情:")
            for dep in deployments:
                status = "✅" if dep["is_active"] else "❌"
                schedule = "⏰" if dep["schedule"] else "🔵"
                created = (
                    dep["created"].strftime("%m-%d %H:%M") if dep["created"] else "N/A"
                )

                print(f"   {status} {schedule} {dep['name']}")
                print(f"      创建: {created} | 标签: {', '.join(dep.get('tags', []))}")

            # 验证主要部署健康状态
            key_deployments = [
                "titan-regular-deployment",
                "titan-live-deployment",
                "titan-hybrid-deployment",
            ]

            print("\n🏥 健康检查:")
            for dep_name in key_deployments:
                verification = await manager.verify_deployment(dep_name)
                status_icon = (
                    "✅" if verification["status"] in ["healthy", "no_runs"] else "❌"
                )
                print(f"   {status_icon} {dep_name}: {verification['message']}")

            print("\n📈 监控地址: http://localhost:4200")
            print("📋 Flow列表: http://localhost:4200/flows")

    async def _start_monitoring(self):
        """启动后台监控"""
        logger.info("📊 启动系统监控...")

        self.monitoring = True
        monitor_count = 0

        while self.monitoring and self.is_running:
            try:
                if monitor_count % 6 == 0:  # 每分钟检查一次（每10秒检查，6次=1分钟）
                    await self._quick_health_check()

                monitor_count += 1
                await asyncio.sleep(10)  # 每10秒检查一次

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"⚠️ 监控异常: {str(e)}")
                await asyncio.sleep(30)  # 异常时等待30秒

    async def _quick_health_check(self):
        """快速健康检查"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # 检查Prefect Server
                response = await client.get("http://localhost:4200/api/health")
                if response.status_code == 200:
                    logger.debug("✅ Prefect Server健康")
                else:
                    logger.warning(f"⚠️ Prefect Server状态异常: {response.status_code}")

        except Exception as e:
            logger.warning(f"⚠️ 健康检查失败: {str(e)}")

    def stop(self):
        """停止系统"""
        logger.info("🛑 停止Titan007系统...")
        self.is_running = False
        self.monitoring = False


def setup_signal_handlers(launcher: TitanPipelineLauncher):
    """设置信号处理器"""

    def signal_handler(signum, frame):
        logger.info(f"\n🛑 收到信号 {signum}, 正在停止系统...")
        launcher.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Titan007 数据采集管道启动器")
    parser.add_argument("--start", action="store_true", help="启动完整调度系统")
    parser.add_argument(
        "--mode", choices=["regular", "live", "hybrid"], help="启动特定模式"
    )
    parser.add_argument("--monitor", action="store_true", help="监控系统状态")
    parser.add_argument("--test", action="store_true", help="运行快速测试")
    parser.add_argument(
        "--once", action="store_true", help="运行一次后退出（用于--test或--monitor）"
    )

    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return

    launcher = TitanPipelineLauncher()
    setup_signal_handlers(launcher)

    try:
        if args.start:
            await launcher.start_full_system()

        elif args.mode:
            await launcher.start_mode_specific(args.mode)

        elif args.test:
            await launcher.run_test()

        elif args.monitor:
            await launcher.monitor_system()

        else:
            parser.print_help()

    except KeyboardInterrupt:
        logger.info("\n👋 用户中断操作")
    except Exception as e:
        logger.error(f"❌ 启动失败: {str(e)}")
        sys.exit(1)
    finally:
        launcher.stop()


if __name__ == "__main__":
    asyncio.run(main())
