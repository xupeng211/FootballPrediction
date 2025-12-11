#!/usr/bin/env python3
"""
Titan007 Prefect Flow 部署脚本
Titan007 Prefect Flow Deployment Script

将Titan007数据采集工作流注册到Prefect Server，支持：
- 自动检测和注册所有Flow
- 调度配置管理
- 部署验证
- 健康检查

使用方法:
    python scripts/deploy_flow.py --register  # 注册所有Flow
    python scripts/deploy_flow.py --deploy    # 注册并启动调度
    python scripts/deploy_flow.py --verify    # 验证部署状态
    python scripts/deploy_flow.py --list      # 列出已注册的Flow
    python scripts/deploy_flow.py --clean     # 清理过期的Flow
"""

import asyncio
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import argparse
from pathlib import Path

import httpx
from prefect.client.orchestration import get_client

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.flows.titan_flow import (
    titan_regular_flow,
    titan_live_flow,
    titan_hybrid_flow,
    titan_regular_schedule,
    titan_live_schedule,
    titan_weekend_schedule,
    titan_peak_season_schedule,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PrefectDeploymentManager:
    """Prefect部署管理器"""

    def __init__(self):
        self.client = None
        self.deployment_configs = self._get_deployment_configs()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.client = get_client()
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)

    def _get_deployment_configs(self) -> List[Dict[str, Any]]:
        """获取所有部署配置"""
        return [
            {
                "name": "titan-regular-deployment",
                "flow": titan_regular_flow,
                "schedule": titan_regular_schedule,
                "description": "Titan007常规数据采集 - 每天早上8点运行",
                "tags": ["titan", "regular", "daily"],
                "params": {"days_ahead": 1, "batch_size": 20, "max_concurrency": 15},
            },
            {
                "name": "titan-live-deployment",
                "flow": titan_live_flow,
                "schedule": titan_live_schedule,
                "description": "Titan007临场数据采集 - 每10分钟运行",
                "tags": ["titan", "live", "realtime"],
                "params": {"hours_ahead": 2, "batch_size": 10, "max_concurrency": 8},
            },
            {
                "name": "titan-hybrid-deployment",
                "flow": titan_hybrid_flow,
                "schedule": None,  # 手动触发
                "description": "Titan007混合数据采集 - 结合常规和临场模式",
                "tags": ["titan", "hybrid", "manual"],
                "params": {
                    "regular_hours_ahead": 1,
                    "live_hours_ahead": 2,
                    "enable_live": True,
                    "cleanup_days": 7,
                },
            },
            {
                "name": "titan-weekend-deployment",
                "flow": titan_regular_flow,
                "schedule": titan_weekend_schedule,
                "description": "Titan007周末数据采集 - 周六早上9点运行",
                "tags": ["titan", "weekend", "saturday"],
                "params": {
                    "days_ahead": 2,  # 周末采集更多天数的比赛
                    "batch_size": 25,
                    "max_concurrency": 20,
                },
            },
            {
                "name": "titan-peak-season-deployment",
                "flow": titan_hybrid_flow,
                "schedule": titan_peak_season_schedule,
                "description": "Titan007高峰期数据采集 - 赛季关键时期密集采集",
                "tags": ["titan", "peak", "season"],
                "params": {
                    "regular_hours_ahead": 2,
                    "live_hours_ahead": 3,
                    "enable_live": True,
                    "cleanup_days": 14,
                },
            },
        ]

    async def register_flows(self) -> Dict[str, Any]:
        """注册所有Flow到Prefect Server"""
        logger.info("🚀 开始注册Titan007 Prefect Flows...")

        results = {
            "success_count": 0,
            "error_count": 0,
            "deployments": [],
            "errors": [],
        }

        for config in self.deployment_configs:
            try:
                logger.info(f"📦 注册部署: {config['name']}")

                # 创建Deployment对象
                deployment = Deployment.build_from_flow(
                    flow=config["flow"],
                    name=config["name"],
                    schedule=config["schedule"],
                    description=config["description"],
                    tags=config["tags"],
                    parameters=config["params"],
                    version=f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                )

                # 注册部署
                deployment_id = await deployment.apply()

                results["success_count"] += 1
                results["deployments"].append(
                    {
                        "name": config["name"],
                        "deployment_id": deployment_id,
                        "flow_name": config["flow"].name,
                        "schedule": config["schedule"] is not None,
                        "description": config["description"],
                    }
                )

                logger.info(f"✅ 成功注册: {config['name']} (ID: {deployment_id})")

            except Exception as e:
                results["error_count"] += 1
                error_info = {
                    "name": config["name"],
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                results["errors"].append(error_info)

                logger.error(f"❌ 注册失败: {config['name']} - {error_info['error']}")

        logger.info(
            f"📊 Flow注册完成: 成功 {results['success_count']}, 失败 {results['error_count']}"
        )
        return results

    async def list_deployments(self) -> List[Dict[str, Any]]:
        """列出所有已注册的部署"""
        logger.info("📋 获取已注册的部署列表...")

        try:
            deployments = await self.client.read_deployments()

            deployment_list = []
            for deployment in deployments:
                deployment_info = {
                    "id": deployment.id,
                    "name": deployment.name,
                    "flow_id": deployment.flow_id,
                    "schedule": deployment.schedule is not None,
                    "is_active": deployment.is_active,
                    "created": deployment.created,
                    "updated": deployment.updated,
                    "tags": deployment.tags,
                }
                deployment_list.append(deployment_info)

            logger.info(f"📋 找到 {len(deployment_list)} 个部署")
            return deployment_list

        except Exception as e:
            logger.error(f"❌ 获取部署列表失败: {str(e)}")
            return []

    async def verify_deployment(self, deployment_name: str) -> Dict[str, Any]:
        """验证指定部署的健康状态"""
        logger.info(f"🔍 验证部署: {deployment_name}")

        try:
            # 获取部署信息
            deployments = await self.client.read_deployments()
            target_deployment = None

            for deployment in deployments:
                if deployment.name == deployment_name:
                    target_deployment = deployment
                    break

            if not target_deployment:
                return {
                    "status": "not_found",
                    "message": f"部署 '{deployment_name}' 未找到",
                }

            # 获取Flow Runs历史
            flow_runs = await self.client.read_flow_runs(
                deployment_id=target_deployment.id, limit=10
            )

            # 分析运行状态
            if not flow_runs:
                status_info = {
                    "status": "no_runs",
                    "message": "部署存在但从未运行",
                    "recent_runs": [],
                    "success_rate": 0.0,
                }
            else:
                successful_runs = sum(
                    1 for run in flow_runs if run.state.is_completed()
                )
                total_runs = len(flow_runs)
                success_rate = successful_runs / total_runs if total_runs > 0 else 0.0

                recent_runs = []
                for run in flow_runs[:5]:  # 最近5次运行
                    recent_runs.append(
                        {
                            "id": run.id,
                            "state": run.state.name,
                            "start_time": run.start_time,
                            "end_time": run.end_time,
                            "duration_seconds": (
                                run.end_time - run.start_time
                            ).total_seconds()
                            if run.end_time
                            else None,
                        }
                    )

                status_info = {
                    "status": "healthy" if success_rate >= 0.8 else "unhealthy",
                    "message": f"最近成功率: {success_rate:.1%} ({successful_runs}/{total_runs})",
                    "success_rate": success_rate,
                    "recent_runs": recent_runs,
                }

            # 添加部署基本信息
            status_info.update(
                {
                    "deployment_id": target_deployment.id,
                    "deployment_name": target_deployment.name,
                    "flow_name": target_deployment.flow_name,
                    "is_active": target_deployment.is_active,
                    "schedule": target_deployment.schedule is not None,
                }
            )

            logger.info(f"✅ 部署验证完成: {deployment_name} - {status_info['status']}")
            return status_info

        except Exception as e:
            logger.error(f"❌ 验证部署失败: {deployment_name} - {str(e)}")
            return {
                "status": "error",
                "message": f"验证失败: {str(e)}",
                "error_type": type(e).__name__,
            }

    async def cleanup_old_deployments(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """清理旧的部署"""
        logger.info(f"🧹 清理 {days_to_keep} 天前的旧部署...")

        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
            deployments = await self.client.read_deployments()

            old_deployments = []
            for deployment in deployments:
                if deployment.created.timestamp() < cutoff_date:
                    old_deployments.append(deployment)

            cleanup_results = {
                "total_deployments": len(deployments),
                "old_deployments_found": len(old_deployments),
                "deleted_count": 0,
                "failed_count": 0,
                "errors": [],
            }

            for deployment in old_deployments:
                try:
                    await self.client.delete_deployment(deployment.id)
                    cleanup_results["deleted_count"] += 1
                    logger.info(f"🗑️ 已删除旧部署: {deployment.name}")

                except Exception as e:
                    cleanup_results["failed_count"] += 1
                    error_info = {"deployment_name": deployment.name, "error": str(e)}
                    cleanup_results["errors"].append(error_info)
                    logger.error(f"❌ 删除部署失败: {deployment.name} - {str(e)}")

            logger.info(
                f"🧹 清理完成: 删除 {cleanup_results['deleted_count']}, 失败 {cleanup_results['failed_count']}"
            )
            return cleanup_results

        except Exception as e:
            logger.error(f"❌ 清理部署失败: {str(e)}")
            return {"error": str(e)}

    async def trigger_deployment(
        self, deployment_name: str, parameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """手动触发部署运行"""
        logger.info(f"🚀 手动触发部署: {deployment_name}")

        try:
            # 获取部署信息
            deployments = await self.client.read_deployments()
            target_deployment = None

            for deployment in deployments:
                if deployment.name == deployment_name:
                    target_deployment = deployment
                    break

            if not target_deployment:
                return {
                    "status": "not_found",
                    "message": f"部署 '{deployment_name}' 未找到",
                }

            # 创建Flow Run
            flow_run = await self.client.create_flow_run_from_deployment(
                deployment.id, parameters=parameters or {}
            )

            result = {
                "status": "triggered",
                "flow_run_id": flow_run.id,
                "flow_run_name": flow_run.name,
                "deployment_name": deployment_name,
                "state": flow_run.state.name,
                "expected_start_time": flow_run.expected_start_time,
            }

            logger.info(f"✅ 成功触发: {deployment_name} (Run ID: {flow_run.id})")
            return result

        except Exception as e:
            logger.error(f"❌ 触发部署失败: {deployment_name} - {str(e)}")
            return {
                "status": "error",
                "message": f"触发失败: {str(e)}",
                "error_type": type(e).__name__,
            }


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Titan007 Prefect Flow 部署管理工具")
    parser.add_argument(
        "--register", action="store_true", help="注册所有Flow到Prefect Server"
    )
    parser.add_argument("--deploy", action="store_true", help="注册并启动调度")
    parser.add_argument("--list", action="store_true", help="列出已注册的部署")
    parser.add_argument("--verify", type=str, help="验证指定部署的健康状态")
    parser.add_argument("--trigger", type=str, help="手动触发指定部署")
    parser.add_argument(
        "--clean", type=int, metavar="DAYS", help="清理指定天数前的旧部署"
    )
    parser.add_argument(
        "--health", action="store_true", help="检查Prefect Server健康状态"
    )

    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return

    # 健康检查
    if args.health:
        logger.info("🏥 检查Prefect Server健康状态...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:4200/api/health")
                if response.status_code == 200:
                    logger.info("✅ Prefect Server健康状态良好")
                    print("Prefect UI: http://localhost:4200")
                else:
                    logger.error(f"❌ Prefect Server状态异常: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ 无法连接到Prefect Server: {str(e)}")
        return

    # 其他操作需要部署管理器
    async with PrefectDeploymentManager() as manager:
        if args.register or args.deploy:
            results = await manager.register_flows()

            # 打印详细结果
            print("\n" + "=" * 60)
            print("📊 FLOW注册结果")
            print("=" * 60)
            print(f"✅ 成功注册: {results['success_count']}")
            print(f"❌ 注册失败: {results['error_count']}")

            if results["deployments"]:
                print("\n📋 已注册的部署:")
                for dep in results["deployments"]:
                    status = "🟢 调度已启用" if dep["schedule"] else "🔵 手动触发"
                    print(f"  • {dep['name']}: {dep['description']} {status}")

            if results["errors"]:
                print("\n❌ 注册错误:")
                for error in results["errors"]:
                    print(f"  • {error['name']}: {error['error']}")

            print("\n📈 Prefect UI: http://localhost:4200")
            print("📋 Flow监控: http://localhost:4200/flows")

        if args.list:
            deployments = await manager.list_deployments()

            print("\n" + "=" * 60)
            print("📋 已注册的部署列表")
            print("=" * 60)

            if not deployments:
                print("📭 暂无已注册的部署")
            else:
                for dep in deployments:
                    schedule_status = "🟢 已调度" if dep["schedule"] else "🔵 手动"
                    active_status = "✅ 活跃" if dep["is_active"] else "❌ 非活跃"

                    print(f"\n📦 {dep['name']}")
                    print(f"   ID: {dep['id']}")
                    print(f"   状态: {active_status} | {schedule_status}")
                    print(f"   创建时间: {dep['created']}")
                    if dep["tags"]:
                        print(f"   标签: {', '.join(dep['tags'])}")

        if args.verify:
            verification = await manager.verify_deployment(args.verify)

            print("\n" + "=" * 60)
            print(f"🔍 部署验证: {args.verify}")
            print("=" * 60)

            status_icon = (
                "✅" if verification["status"] in ["healthy", "no_runs"] else "❌"
            )
            print(f"{status_icon} 状态: {verification['status']}")
            print(f"📝 消息: {verification['message']}")

            if "deployment_id" in verification:
                print("\n📦 部署信息:")
                print(f"   ID: {verification['deployment_id']}")
                print(f"   Flow: {verification['flow_name']}")
                print(f"   活跃: {'是' if verification['is_active'] else '否'}")
                print(f"   调度: {'是' if verification['schedule'] else '否'}")

            if "recent_runs" in verification and verification["recent_runs"]:
                print("\n📊 最近运行记录:")
                for run in verification["recent_runs"]:
                    duration = (
                        f"{run['duration_seconds']:.1f}s"
                        if run["duration_seconds"]
                        else "运行中"
                    )
                    print(f"   • {run['state']}: {duration}")

            if "success_rate" in verification:
                rate = verification["success_rate"] * 100
                print(f"\n📈 成功率: {rate:.1f}%")

        if args.trigger:
            result = await manager.trigger_deployment(args.trigger)

            print("\n" + "=" * 60)
            print(f"🚀 触发部署: {args.trigger}")
            print("=" * 60)

            if result["status"] == "triggered":
                print("✅ 触发成功!")
                print(f"🏃 运行ID: {result['flow_run_id']}")
                print(f"📊 状态: {result['state']}")
                print(
                    f"\n📈 监控地址: http://localhost:4200/flow-run/{result['flow_run_id']}"
                )
            else:
                print(f"❌ 触发失败: {result['message']}")

        if args.clean:
            results = await manager.cleanup_old_deployments(args.clean)

            print("\n" + "=" * 60)
            print(f"🧹 清理 {args.clean} 天前的部署")
            print("=" * 60)

            if "total_deployments" in results:
                print(f"📊 总部署数: {results['total_deployments']}")
                print(f"🔍 找到旧部署: {results['old_deployments_found']}")
                print(f"✅ 成功删除: {results['deleted_count']}")
                print(f"❌ 删除失败: {results['failed_count']}")

            if results.get("errors"):
                print("\n❌ 删除错误:")
                for error in results["errors"]:
                    print(f"  • {error['deployment_name']}: {error['error']}")


if __name__ == "__main__":
    # 检查Prefect Server是否运行
    try:
        import asyncio

        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 部署操作已取消")
    except Exception as e:
        logger.error(f"❌ 部署脚本执行失败: {str(e)}")
        sys.exit(1)
