#!/usr/bin/env python3
"""
Sprint 9 生产环境正式部署脚本

自动化生产环境部署流程：
1. 环境验证
2. 服务启动
3. 健康检查
4. 监控配置
5. 定时任务设置

使用方法:
  python deploy_production.py --deploy
  python deploy_production.py --status
  python deploy_production.py --stop

Author: Football Prediction Team
Version: 1.0.0 (Sprint 9 - Production Deployment)
"""

import os
import sys
import json
import time
import asyncio
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import psutil

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_secure import get_settings
from scripts.verify_live_connection import LiveConnectionVerifier


class ProductionDeployer:
    """生产环境部署器"""

    def __init__(self):
        self.settings = get_settings()
        self.project_root = Path(__file__).parent.parent
        self.deploy_log = []
        self.cron_jobs = []

        # Docker Compose配置
        self.compose_files = [
            self.project_root / "docker-compose.prod.yml",
            self.project_root / "docker-compose.monitoring.yml",
        ]

        # 必需的目录
        self.required_dirs = [
            "logs",
            "data/cache",
            "data/models",
            "backups",
            "monitoring/grafana/dashboards",
            "monitoring/grafana/datasources",
            "monitoring/prometheus",
        ]

    async def deploy_all_services(self) -> Dict[str, Any]:
        """部署所有服务"""
        print("🚀 开始Sprint 9 生产环境部署")
        print("=" * 60)

        # 1. 环境验证
        if not await self._verify_environment():
            return {"success": False, "error": "环境验证失败"}

        # 2. 目录准备
        await self._prepare_directories()

        # 3. 配置文件验证
        if not await self._verify_configurations():
            return {"success": False, "error": "配置验证失败"}

        # 4. 服务部署
        deployment_result = await self._deploy_services()

        if not deployment_result["success"]:
            return deployment_result

        # 5. 健康检查
        health_result = await self._health_check()

        if not health_result["success"]:
            return {"success": False, "error": "健康检查失败"}

        # 6. 监控配置
        await self._setup_monitoring()

        # 7. 定时任务配置
        await self._setup_cron_jobs()

        # 8. 部署后验证
        final_verification = await self._final_verification()

        # 9. 生成部署报告
        deployment_report = await self._generate_deployment_report(
            {
                "deployment_success": final_verification["success"],
                "services_deployed": deployment_result["services"],
                "health_status": health_result,
                "monitoring_ready": True,
                "cron_jobs_configured": len(self.cron_jobs),
            }
        )

        return deployment_report

    async def _verify_environment(self) -> bool:
        """验证部署环境"""
        print("🔍 验证部署环境...")

        try:
            # 检查Docker
            try:
                result = subprocess.run(
                    ["docker", "--version"], capture_output=True, text=True, check=True
                )
                docker_version = result.stdout.strip()
                print(f"✅ Docker: {docker_version}")
            except subprocess.CalledProcessError:
                print("❌ Docker未安装或无法访问")
                return False

            # 检查Docker Compose
            try:
                result = subprocess.run(
                    ["docker-compose", "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                compose_version = result.stdout.strip()
                print(f"✅ Docker Compose: {compose_version}")
            except subprocess.CalledProcessError:
                print("❌ Docker Compose未安装或无法访问")
                return False

            # 检查系统资源
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            print(f"💻 系统资源:")
            print(f"  CPU核心: {cpu_count}")
            print(
                f"  内存: {memory.total / (1024**3):.1f}GB (可用: {memory.available / (1024**3):.1f}GB)"
            )
            print(
                f"  磁盘: {disk.total / (1024**3):.1f}GB (可用: {disk.free / (1024**3):.1f}GB)"
            )

            # 检查最低要求
            if cpu_count < 4:
                print("⚠️ CPU核心数少于4，可能影响性能")
            if memory.total < 8 * 1024**3:
                print("⚠️ 内存少于8GB，可能影响性能")
            if disk.free < 50 * 1024**3:
                print("⚠️ 可用磁盘空间少于50GB，可能影响运行")

            # 验证API连接
            print("\n🔗 验证API连接...")
            verifier = LiveConnectionVerifier()
            quick_test = await verifier.test_specific_service("fotmob")

            if quick_test.success:
                print("✅ API连接验证通过")
            else:
                print("❌ API连接验证失败，请先运行: python setup_api_keys.py")
                return False

            return True

        except Exception as e:
            print(f"❌ 环境验证失败: {e}")
            return False

    async def _prepare_directories(self):
        """准备必需目录"""
        print("📁 准备目录结构...")

        for dir_path in self.required_dirs:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)

            # 设置权限
            if "logs" in dir_path:
                os.chmod(full_path, 0o755)
            elif "backups" in dir_path:
                os.chmod(full_path, 0o755)

            print(f"✅ {dir_path}")

    async def _verify_configurations(self) -> bool:
        """验证配置文件"""
        print("⚙️ 验证配置文件...")

        required_files = [
            ".env.production",
            "docker-compose.prod.yml",
            "docker-compose.monitoring.yml",
        ]

        for file_name in required_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                print(f"✅ {file_name}")
            else:
                print(f"❌ 缺少配置文件: {file_name}")
                return False

        # 验证环境变量
        env_file = self.project_root / ".env.production"
        if env_file.exists():
            required_vars = [
                "ENVIRONMENT",
                "SECRET_KEY",
                "DB_HOST",
                "DB_NAME",
                "FOTMOB_X_MAS_HEADER",
                "FOTMOB_X_FOO_HEADER",
            ]

            with open(env_file, "r") as f:
                env_content = f.read()

            for var in required_vars:
                if f"{var}=" in env_content:
                    print(f"✅ 环境变量: {var}")
                else:
                    print(f"❌ 缺少环境变量: {var}")
                    return False

        return True

    async def _deploy_services(self) -> Dict[str, Any]:
        """部署服务"""
        print("🚀 部署应用服务...")

        services_deployed = []

        try:
            # 停止现有服务
            print("🛑 停止现有服务...")
            subprocess.run(
                [
                    "docker-compose",
                    "-f",
                    "docker-compose.prod.yml",
                    "down",
                    "--remove-orphans",
                ],
                cwd=self.project_root,
                capture_output=True,
            )

            # 构建并启动服务
            print("🔨 构建并启动服务...")
            result = subprocess.run(
                [
                    "docker-compose",
                    "-f",
                    "docker-compose.prod.yml",
                    "up",
                    "-d",
                    "--build",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print(f"❌ 服务启动失败: {result.stderr}")
                return {"success": False, "error": result.stderr}

            # 等待服务启动
            print("⏳ 等待服务启动...")
            await asyncio.sleep(30)

            # 检查服务状态
            result = subprocess.run(
                [
                    "docker-compose",
                    "-f",
                    "docker-compose.prod.yml",
                    "ps",
                    "--format",
                    "json",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                services = json.loads(result.stdout)
                for service in services:
                    if service.get("State") == "running":
                        services_deployed.append(service["Service"])
                        print(f"✅ {service['Service']}: 运行中")
                    else:
                        print(
                            f"❌ {service['Service']}: {service.get('State', 'unknown')}"
                        )

            # 启动监控服务
            if (self.project_root / "docker-compose.monitoring.yml").exists():
                print("📊 启动监控服务...")
                subprocess.run(
                    [
                        "docker-compose",
                        "-f",
                        "docker-compose.monitoring.yml",
                        "up",
                        "-d",
                    ],
                    cwd=self.project_root,
                    capture_output=True,
                )

                await asyncio.sleep(15)

            return {"success": True, "services": services_deployed}

        except Exception as e:
            print(f"❌ 服务部署失败: {e}")
            return {"success": False, "error": str(e)}

    async def _health_check(self) -> Dict[str, Any]:
        """健康检查"""
        print("🏥 执行健康检查...")

        try:
            # API健康检查
            import requests

            # 等待服务完全启动
            await asyncio.sleep(15)

            health_checks = {
                "api": False,
                "database": False,
                "redis": False,
                "model": False,
            }

            # API健康检查
            try:
                response = requests.get("http://localhost:8000/health", timeout=10)
                if response.status_code == 200:
                    health_checks["api"] = True
                    print("✅ API健康检查通过")
                else:
                    print(f"❌ API健康检查失败: HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ API健康检查异常: {e}")

            # 数据库健康检查
            try:
                response = requests.get(
                    "http://localhost:8000/api/v1/health/database", timeout=10
                )
                if response.status_code == 200:
                    health_checks["database"] = True
                    print("✅ 数据库健康检查通过")
                else:
                    print(f"❌ 数据库健康检查失败: HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ 数据库健康检查异常: {e}")

            # Redis健康检查
            try:
                response = requests.get(
                    "http://localhost:8000/api/v1/health/redis", timeout=10
                )
                if response.status_code == 200:
                    health_checks["redis"] = True
                    print("✅ Redis健康检查通过")
                else:
                    print(f"❌ Redis健康检查失败: HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ Redis健康检查异常: {e}")

            # 模型健康检查
            try:
                response = requests.get(
                    "http://localhost:8000/api/v1/health/model", timeout=10
                )
                if response.status_code == 200:
                    health_checks["model"] = True
                    print("✅ 模型健康检查通过")
                else:
                    print(f"❌ 模型健康检查失败: HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ 模型健康检查异常: {e}")

            all_healthy = all(health_checks.values())

            return {
                "success": all_healthy,
                "health_checks": health_checks,
                "overall_status": "healthy" if all_healthy else "unhealthy",
            }

        except Exception as e:
            print(f"❌ 健康检查失败: {e}")
            return {"success": False, "error": str(e), "overall_status": "error"}

    async def _setup_monitoring(self):
        """设置监控"""
        print("📊 配置监控系统...")

        # 检查监控服务状态
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=grafana", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and result.stdout.strip():
                print("✅ Grafana监控已启动")
                print(f"📈 访问地址: http://localhost:3000 (admin/admin123)")
            else:
                print("⚠️ Grafana监控未启动，请检查docker-compose.monitoring.yml")

            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    "name=prometheus",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and result.stdout.strip():
                print("✅ Prometheus监控已启动")
                print(f"📊 访问地址: http://localhost:9090")
            else:
                print("⚠️ Prometheus监控未启动")

        except Exception as e:
            print(f"⚠️ 监控配置检查异常: {e}")

    async def _setup_cron_jobs(self):
        """设置定时任务"""
        print("⏰ 配置定时任务...")

        cron_jobs = [
            {
                "name": "数据收集任务",
                "schedule": "*/30 * * * *",
                "command": f"cd {self.project_root} && docker-compose -f docker-compose.prod.yml exec -T app python scripts/collectors/scheduled_data_collector.py",
                "description": "每30分钟收集足球数据",
            },
            {
                "name": "模型重训练任务",
                "schedule": "0 2 * * *",
                "command": f"cd {self.project_root} && docker-compose -f docker-compose.prod.yml exec -T app python scripts/retrain_models.py",
                "description": "每天凌晨2点重训练模型",
            },
            {
                "name": "数据备份任务",
                "schedule": "0 3 * * *",
                "command": f"cd {self.project_root} && docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U football_user football_prediction_prod > backups/backup_$(date +\\%Y\\%m\\%d).sql",
                "description": "每天凌晨3点备份数据库",
            },
            {
                "name": "系统健康检查",
                "schedule": "*/5 * * * *",
                "command": f"cd {self.project_root} && python scripts/health_check.py",
                "description": "每5分钟检查系统健康",
            },
            {
                "name": "日志清理任务",
                "schedule": "0 4 * * 0",
                "command": f'find {self.project_root}/logs -name "*.log" -mtime +7 -delete',
                "description": "每周日凌晨4点清理旧日志",
            },
            {
                "name": "Kelly日计数器重置",
                "schedule": "0 0 * * *",
                "command": f"cd {self.project_root} && python scripts/reset_kelly_counters.py",
                "description": "每天凌晨0点重置Kelly日计数器",
            },
            {
                "name": "每日性能报告",
                "schedule": "0 23 * * *",
                "command": f"cd {self.project_root} && python scripts/daily_performance.py",
                "description": "每天23点生成性能报告",
            },
        ]

        # 生成crontab配置
        crontab_content = "# Football Prediction System - Production Cron Jobs\n"
        crontab_content += f"# Generated at: {datetime.now().isoformat()}\n\n"

        for job in cron_jobs:
            crontab_content += f"# {job['description']}\n"
            crontab_content += f"{job['schedule']} {job['command']}\n\n"
            self.cron_jobs.append(job)

        # 保存crontab配置
        crontab_file = self.project_root / "production_crontab"
        with open(crontab_file, "w") as f:
            f.write(crontab_content)

        print(f"✅ Cron配置已保存: {crontab_file}")
        print("📝 请手动添加到系统crontab:")
        print(f"   crontab {crontab_file}")

        # 尝试自动安装crontab（如果权限允许）
        try:
            subprocess.run(["crontab", str(crontab_file)], check=True)
            print("✅ Cron任务已自动安装")
        except subprocess.CalledProcessError:
            print("⚠️ 需要手动安装Cron任务")
        except Exception as e:
            print(f"⚠️ Cron任务安装失败: {e}")

    async def _final_verification(self) -> Dict[str, Any]:
        """最终验证"""
        print("🔍 执行最终验证...")

        verification_results = {
            "api_accessible": False,
            "prediction_working": False,
            "kelly_safety_active": False,
            "monitoring_accessible": False,
        }

        try:
            import requests

            # API可访问性
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                verification_results["api_accessible"] = response.status_code == 200
            except:
                pass

            # 预测功能测试
            try:
                test_data = {"home_team": "Manchester United", "away_team": "Arsenal"}
                response = requests.post(
                    "http://localhost:8000/api/v1/predict", json=test_data, timeout=10
                )
                verification_results["prediction_working"] = response.status_code == 200
            except:
                pass

            # Kelly安全状态检查
            try:
                response = requests.get(
                    "http://localhost:8000/api/v1/kelly/safety-status", timeout=5
                )
                if response.status_code == 200:
                    safety_data = response.json()
                    verification_results["kelly_safety_active"] = safety_data.get(
                        "safety_enabled", False
                    )
            except:
                pass

            # 监控可访问性检查
            try:
                response = requests.get("http://localhost:3000", timeout=5)
                verification_results["monitoring_accessible"] = (
                    response.status_code == 200
                )
            except:
                pass

            all_passed = all(verification_results.values())

            if all_passed:
                print("✅ 所有验证通过")
            else:
                print("⚠️ 部分验证未通过")
                for check, passed in verification_results.items():
                    status = "✅" if passed else "❌"
                    print(f"  {status} {check}")

            return {"success": all_passed, "verification_results": verification_results}

        except Exception as e:
            print(f"❌ 最终验证失败: {e}")
            return {"success": False, "error": str(e)}

    async def _generate_deployment_report(
        self, deployment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成部署报告"""
        report = {
            "deployment_time": datetime.now().isoformat(),
            "environment": "production",
            "version": "v2.0.0-sprint9",
            "deployment_data": deployment_data,
            "system_info": {
                "server_ip": "localhost",  # 在实际部署中应获取真实IP
                "services_count": len(deployment_data.get("services_deployed", [])),
                "cron_jobs_count": len(self.cron_jobs),
                "monitoring_enabled": True,
            },
            "next_steps": [
                "1. 监控系统运行状态",
                "2. 检查API预测结果",
                "3. 验证Kelly安全系统",
                "4. 观察性能指标",
                "5. 设置告警通知",
            ],
        }

        # 保存报告
        report_file = (
            self.project_root
            / "logs"
            / f"deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"📄 部署报告已保存: {report_file}")

        return report

    async def get_deployment_status(self) -> Dict[str, Any]:
        """获取部署状态"""
        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "-f",
                    "docker-compose.prod.yml",
                    "ps",
                    "--format",
                    "json",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                services = json.loads(result.stdout)
                running_services = [s for s in services if s.get("State") == "running"]

                return {
                    "total_services": len(services),
                    "running_services": len(running_services),
                    "service_details": services,
                    "overall_status": (
                        "running"
                        if len(running_services) == len(services)
                        else "partial"
                    ),
                }
            else:
                return {"overall_status": "error", "error": result.stderr}

        except Exception as e:
            return {"overall_status": "error", "error": str(e)}

    async def stop_all_services(self) -> bool:
        """停止所有服务"""
        print("🛑 停止所有服务...")

        try:
            # 停止应用服务
            subprocess.run(
                [
                    "docker-compose",
                    "-f",
                    "docker-compose.prod.yml",
                    "down",
                    "--remove-orphans",
                ],
                cwd=self.project_root,
                check=True,
            )

            # 停止监控服务
            subprocess.run(
                [
                    "docker-compose",
                    "-f",
                    "docker-compose.monitoring.yml",
                    "down",
                    "--remove-orphans",
                ],
                cwd=self.project_root,
                check=False,
            )  # 监控服务可能不存在

            print("✅ 所有服务已停止")
            return True

        except Exception as e:
            print(f"❌ 停止服务失败: {e}")
            return False


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Sprint 9 生产环境部署")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 部署命令
    deploy_parser = subparsers.add_parser("deploy", help="部署生产环境")
    deploy_parser.add_argument("--force", action="store_true", help="强制重新部署")

    # 状态命令
    status_parser = subparsers.add_parser("status", help="查看部署状态")

    # 停止命令
    stop_parser = subparsers.add_parser("stop", help="停止所有服务")

    args = parser.parse_args()

    deployer = ProductionDeployer()

    try:
        if args.command == "deploy":
            report = await deployer.deploy_all_services()

            print(f"\n🎉 部署完成!")
            print(f"=" * 50)
            print(
                f"部署状态: {'✅ 成功' if report['deployment_success'] else '❌ 失败'}"
            )
            print(f"服务数量: {len(report.get('services_deployed', []))}")
            print(
                f"监控状态: {'✅ 就绪' if report.get('monitoring_ready') else '❌ 未就绪'}"
            )
            print(f"定时任务: {len(report.get('cron_jobs_configured', 0))} 个")

            if not report["deployment_success"]:
                print(f"❌ 部署失败: {report.get('error', 'Unknown error')}")
                return 1

            print(f"\n📋 下一步操作:")
            for step in report.get("next_steps", []):
                print(f"  {step}")

            return 0

        elif args.command == "status":
            status = await deployer.get_deployment_status()

            print(f"\n📊 部署状态:")
            print(f"=" * 30)
            print(f"总体状态: {status['overall_status']}")
            print(
                f"运行服务: {status.get('running_services', 0)}/{status.get('total_services', 0)}"
            )

            if "service_details" in status:
                print(f"\n服务详情:")
                for service in status["service_details"]:
                    status_icon = "✅" if service.get("State") == "running" else "❌"
                    print(
                        f"  {status_icon} {service.get('Service', 'unknown')}: {service.get('State', 'unknown')}"
                    )

            return 0

        elif args.command == "stop":
            success = await deployer.stop_all_services()
            return 0 if success else 1

        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print(f"\n👋 部署已取消")
        return 1
    except Exception as e:
        print(f"❌ 部署失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
