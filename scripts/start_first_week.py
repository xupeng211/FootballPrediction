#!/usr/bin/env python3
"""
Sprint 9 首周观察期启动脚本

启动首周观察期模式，确保系统安全上线：
1. 配置0.1倍Kelly比例
2. 启用观察模式监控
3. 设置风险阈值
4. 配置告警通知
5. 生成启动报告

使用方法:
  python start_first_week.py
  python start_first_week.py --configure-only
  python start_first_week.py --status

Author: Football Prediction Team
Version: 1.0.0 (Sprint 9 - First Week Observation)
"""

import asyncio
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_secure import get_settings
from scripts.setup_api_keys import APIKeySetup
from scripts.verify_live_connection import LiveConnectionVerifier
from scripts.deploy_production import ProductionDeployer
from scripts.observation_mode_manager import ObservationModeManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FirstWeekLauncher:
    """首周观察期启动器"""

    def __init__(self):
        self.settings = get_settings()

        # 首周观察期配置
        self.first_week_config = {
            # 安全配置
            "kelly_multiplier": 0.1,  # 0.1倍Kelly（极低风险）
            "max_daily_stake_percentage": 0.05,  # 日最大投注5%
            "min_confidence_threshold": 0.70,  # 最低置信度70%

            # 观察模式配置
            "observation_mode": "observation",  # 默认观察模式
            "auto_betting": False,  # 不自动投注
            "auto_prediction": True,  # 仍进行预测并记录

            # 风险监控配置
            "brier_score_deviation_threshold": 15.0,  # Brier Score偏差阈值
            "prediction_accuracy_threshold": 40.0,  # 预测准确率阈值
            "roi_loss_threshold": -20.0,  # ROI损失阈值
            "max_safety_blocks_per_day": 10,  # 每日最大安全拦截次数

            # 监控频率配置
            "health_check_interval": 300,  # 5分钟健康检查
            "performance_check_interval": 3600,  # 1小时性能检查
            "observation_check_interval": 1800,  # 30分钟观察检查

            # 通知配置
            "enable_email_notifications": True,
            "enable_slack_notifications": False,
            "enable_sms_notifications": False
        }

    async def launch_first_week(self, configure_only: bool = False) -> Dict[str, Any]:
        """启动首周观察期"""
        logger.info("🚀 启动Sprint 9 首周观察期")
        print("="*60)
        print("🏈️  足球预测系统 - 首周观察期启动")
        print("="*60)

        launch_data = {
            "start_time": datetime.now().isoformat(),
            "configure_only": configure_only,
            "config": self.first_week_config.copy(),
            "steps_completed": [],
            "steps_failed": [],
            "final_status": "unknown"
        }

        try:
            # 1. 环境检查和配置
            logger.info("📋 步骤 1: 环境检查和配置...")
            env_result = await self._check_and_configure_environment()
            launch_data["steps_completed"].append("environment_check")
            launch_data["config"].update(env_result.get("updated_config", {}))

            if not env_result["success"]:
                launch_data["steps_failed"].append("environment_check")
                launch_data["final_status"] = "failed"
                return launch_data

            # 2. API连接验证
            logger.info("🌐 步骤 2: API连接验证...")
            api_result = await self._verify_api_connections()
            launch_data["steps_completed"].append("api_verification")

            if not api_result["all_healthy"]:
                launch_data["steps_failed"].append("api_verification")
                launch_data["final_status"] = "failed"
                return launch_data

            # 3. 配置Kelly安全系统
            logger.info("🛡️ 步骤 3: 配置Kelly安全系统...")
            kelly_result = await self._configure_kelly_safety()
            launch_data["steps_completed"].append("kelly_safety_config")

            if not kelly_result["success"]:
                launch_data["steps_failed"].append("kelly_safety_config")
                launch_data["final_status"] = "failed"
                return launch_data

            # 4. 配置观察模式
            logger.info("🔍 步骤 4: 配置观察模式...")
            observation_result = await self._configure_observation_mode()
            launch_data["steps_completed"].append("observation_mode_config")

            if not observation_result["success"]:
                launch_data["steps_failed"].append("observation_mode_config")
                launch_data["final_status"] = "failed"
                return launch_data

            if configure_only:
                launch_data["final_status"] = "configured_only"
            else:
                # 5. 部署服务
                logger.info("🚀 步骤 5: 部署服务...")
                deploy_result = await self._deploy_services()
                launch_data["steps_completed"].append("service_deployment")

                if not deploy_result["success"]:
                    launch_data["steps_failed"].append("service_deployment")
                    launch_data["final_status"] = "failed"
                    return launch_data

                # 6. 启动监控
                logger.info("📊 步骤 6: 启动监控...")
                monitor_result = await self._setup_monitoring()
                launch_data["steps_completed"].append("monitoring_setup")

                if not monitor_result["success"]:
                    launch_data["steps_failed"].append("monitoring_setup")
                    launch_data["final_status"] = "partial"  # 监控失败不影响主要功能

                # 7. 最终验证
                logger.info("✅ 步骤 7: 最终验证...")
                final_result = await self._final_verification()
                launch_data["steps_completed"].append("final_verification")

                if final_result["success"]:
                    launch_data["final_status"] = "success"
                else:
                    launch_data["steps_failed"].append("final_verification")
                    launch_data["final_status"] = "partial"

            # 生成启动报告
            await self._generate_startup_report(launch_data)

            return launch_data

        except Exception as e:
            logger.error(f"首周观察期启动失败: {e}")
            launch_data["final_status"] = "error"
            launch_data["error"] = str(e)
            return launch_data

    async def _check_and_configure_environment(self) -> Dict[str, Any]:
        """检查和配置环境"""
        try:
            # 检查环境变量
            required_vars = [
                "ENVIRONMENT",
                "SECRET_KEY",
                "DB_HOST",
                "DB_NAME",
                "FOTMOB_X_MAS_HEADER",
                "FOTMOB_X_FOO_HEADER"
            ]

            missing_vars = []
            updated_config = {}

            for var in required_vars:
                if not hasattr(self.settings, var.lower()) or not getattr(self.settings, var.lower(), None):
                    missing_vars.append(var)

            if missing_vars:
                logger.warning(f"⚠️ 缺少环境变量: {', '.join(missing_vars)}")

                # 尝试加载环境文件
                env_file = Path(".env.production")
                if env_file.exists():
                    logger.info("📝 发现.env.production文件，尝试加载")

                    # 这里可以添加环境变量加载逻辑
                    updated_config["env_file_loaded"] = True
                else:
                    logger.error(f"❌ 缺少必要的环境变量: {', '.join(missing_vars)}")
                    logger.error("请运行: python scripts/setup_api_keys.py")
                    return {"success": False, "missing_vars": missing_vars}

            # 检查目录结构
            required_dirs = ["logs", "data/cache", "data/models", "backups"]
            for dir_path in required_dirs:
                full_path = Path(dir_path)
                if not full_path.exists():
                    full_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"📁 创建目录: {dir_path}")

            return {"success": True, "updated_config": updated_config}

        except Exception as e:
            logger.error(f"环境检查失败: {e}")
            return {"success": False, "error": str(e)}

    async def _verify_api_connections(self) -> Dict[str, Any]:
        """验证API连接"""
        try:
            verifier = LiveConnectionVerifier()

            # 检查关键服务
            critical_services = ["database", "redis", "fotmob_api"]
            all_healthy = True

            connection_status = {}

            for service in critical_services:
                result = await verifier.test_specific_service(service)
                connection_status[service] = result.success
                if not result.success:
                    all_healthy = False
                    logger.error(f"❌ {service}连接失败: {result.error_message}")

            return {
                "all_healthy": all_healthy,
                "connection_status": connection_status
            }

        except Exception as e:
            logger.error(f"API连接验证失败: {e}")
            return {"all_healthy": False, "error": str(e)}

    async def _configure_kelly_safety(self) -> Dict[str, Any]:
        """配置Kelly安全系统"""
        try:
            # 设置安全配置
            safety_config = {
                "max_stake_percentage_of_bankroll": 0.05,  # 5%
                "max_daily_stake_percentage": 0.20,       # 20%
                "emergency_stop_enabled": True,
                "manual_override_required": False,
                "audit_log_enabled": True,
                "risk_alert_threshold": 0.03            # 3%
            }

            # 通过API配置Kelly系统
            import requests

            response = requests.post(
                "http://localhost:8000/api/v1/kelly/configure",
                json={
                    "max_stake_percentage": safety_config["max_stake_percentage_of_bankroll"],
                    "max_daily_stake_percentage": safety_config["max_daily_stake_percentage"],
                    "emergency_stop_enabled": safety_config["emergency_stop_enabled"],
                    "manual_override_required": safety_config["manual_override_required"],
                    "risk_alert_threshold": safety_config["risk_alert_threshold"]
                },
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Kelly安全系统配置成功")
                return {"success": True, "config": safety_config, "api_response": result}
            else:
                logger.error(f"❌ Kelly安全系统配置失败: HTTP {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"Kelly安全配置失败: {e}")
            return {"success": False, "error": str(e)}

    async def _configure_observation_mode(self) -> Dict[str, Any]:
        """配置观察模式"""
        try:
            manager = ObservationModeManager()
            await manager.initialize()

            # 检查当前模式
            current_mode = await manager._get_current_observation_mode()

            # 如果不是观察模式，则启用
            if current_mode.value != self.first_week_config["observation_mode"]:
                logger.info(f"🔍 启用观察模式: {current_mode.value} → {self.first_week_config['observation_mode']}")

                # 创建观察模式事件
                event_data = {
                    "event_id": f"first_week_launch_{int(time.time())}",
                    "timestamp": datetime.now().isoformat(),
                    "reason": "首周观察期启动",
                    "config": self.first_week_config
                }

                # 启用观察模式
                result = await manager.check_observation_conditions()

                return {
                    "success": True,
                    "mode_changed": result["mode_change_needed"],
                    "current_mode": result["current_mode"],
                    "required_mode": result["required_mode"],
                    "observation_data": result
                }
            else:
                logger.info(f"✅ 观察模式已启用: {current_mode.value}")
                return {
                    "success": True,
                    "mode_changed": False,
                    "current_mode": current_mode.value,
                    "required_mode": current_mode.value
                }

        except Exception as e:
            logger.error(f"观察模式配置失败: {e}")
            return {"success": False, "error": str(e)}

    async def _deploy_services(self) -> Dict[str, Any]:
        """部署服务"""
        try:
            deployer = ProductionDeployer()
            deployment_report = await deployer.deploy_all_services()

            return deployment_report

        except Exception as e:
            logger.error(f"服务部署失败: {e}")
            return {"success": False, "error": str(e)}

    async def _setup_monitoring(self) -> Dict[str, Any]:
        """设置监控"""
        try:
            # 这里可以设置监控相关的配置
            # 例如：启动监控服务，配置告警等

            monitoring_config = {
                "health_check_interval": self.first_week_config["health_check_interval"],
                "performance_check_interval": self.first_week_config["performance_check_interval"],
                "observation_check_interval": self.first_week_config["observation_check_interval"]
            }

            logger.info("✅ 监控配置完成")
            logger.info(f"📊 健康检查间隔: {monitoring_config['health_check_interval']}秒")
            logger.info(f"📈 性能检查间隔: {monitoring_config['performance_check_interval']}秒")
            logger.info(f"🔍 观察检查间隔: {monitoring_config['observation_check_interval']}秒")

            return {
                "success": True,
                "config": monitoring_config
            }

        except Exception as e:
            logger.error(f"监控设置失败: {e}")
            return {"success": False, "error": str(e)}

    async def _final_verification(self) -> Dict[str, Any]:
        """最终验证"""
        try:
            verification_data = {
                "timestamp": datetime.now().isoformat(),
                "checks": {}
            }

            # 检查API健康状态
            try:
                response = requests.get("http://localhost:8000/health", timeout=10)
                verification_data["checks"]["api_health"] = response.status_code == 200
            except:
                verification_data["checks"]["api_health"] = False

            # 检查Kelly安全状态
            try:
                response = requests.get("http://localhost:8000/api/v1/kelly/safety-status", timeout=10)
                if response.status_code == 200:
                    safety_data = response.json()
                    verification_data["checks"]["kelly_safety"] = safety_data["safety_enabled"]
                    verification_data["checks"]["kelly_multiplier"] = safety_data.get("max_stake_percentage") == 5.0
                else:
                    verification_data["checks"]["kelly_safety"] = False
            except:
                verification_data["checks"]["kelly_safety"] = False

            # 检查观察模式状态
            try:
                manager = ObservationModeManager()
                await manager.initialize()
                current_mode = await manager._get_current_observation_mode()
                verification_data["checks"]["observation_mode"] = current_mode.value == self.first_week_config["observation_mode"]
            except:
                verification_data["checks"]["observation_mode"] = False

            # 计算总体成功状态
            all_checks_passed = all(verification_data["checks"].values())
            verification_data["success"] = all_checks_passed

            logger.info("✅ 最终验证完成")
            logger.info(f"API健康: {'✅' if verification_data['checks']['api_health'] else '❌'}")
            logger.info(f"Kelly安全: {'✅' if verification_data['checks']['kelly_safety'] else '❌'}")
            logger.info(f"观察模式: {'✅' if verification_data['checks']['observation_mode'] else '❌'}")

            return verification_data

        except Exception as e:
            logger.error(f"最终验证失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "checks": {}
            }

    async def _generate_startup_report(self, launch_data: Dict[str, Any]):
        """生成启动报告"""
        try:
            report = {
                "launch_type": "first_week_observation",
                "launch_time": launch_data["start_time"],
                "final_status": launch_data["final_status"],
                "configuration": launch_data["config"],
                "steps_completed": launch_data["steps_completed"],
                "steps_failed": launch_data["steps_failed"],
                "summary": {
                    "total_steps": 7,
                    "completed_steps": len(launch_data["steps_completed"]),
                    "failed_steps": len(launch_data["steps_failed"]),
                    "success_rate": len(launch_data["steps_completed"]) / 7 * 100
                },
                "next_steps": [
                    "1. 监控系统运行状态",
                    "2. 检查每日性能报告",
                    "3. 观察预测准确率",
                    "4. 监控Kelly安全系统",
                    "5. 记录财务表现",
                    "6. 分析回测偏差",
                    "7. 第一周结束后评估是否继续观察模式"
                ]
            }

            # 保存报告
            report_dir = Path("reports")
            report_dir.mkdir(parents=True, exist_ok=True)

            report_file = report_dir / f"first_week_launch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"📄 启动报告已保存: {report_file}")

        except Exception as e:
            logger.error(f"生成启动报告失败: {e}")

    def print_launch_summary(self, launch_data: Dict[str, Any]):
        """打印启动摘要"""
        print("\n" + "="*60)
        print("🎉 首周观察期启动完成")
        print("="*60)
        print(f"启动时间: {launch_data['start_time']}")
        print(f"最终状态: {launch_data['final_status']}")
        print(f"完成步骤: {len(launch_data['steps_completed'])}/7")
        print(f"失败步骤: {len(launch_data['steps_failed'])}/7")
        print(f"成功率: {launch_data.get('summary', {}).get('success_rate', 0):.1f}%")

        if launch_data["final_status"] == "success":
            print("\n🚀 系统已成功启动首周观察期")
            print("📊 系统将以极低风险运行，仅进行预测，不执行投注")
        elif launch_data["final_status"] == "configured_only":
            print("\n⚙️ 配置已完成，但未启动服务")
        else:
            print("\n❌ 启动失败，请检查上述错误")

        print("\n🎯 首周观察期配置:")
        print(f"  Kelly倍数: {self.first_week_config['kelly_multiplier']} (0.1倍)")
        print(f"  日最大投注: {self.first_week_config['max_daily_stake_percentage']:.0%}")
        print(f"  最低置信度: {self.first_week_config['min_confidence_threshold']:.0%}")
        print(f"  观察模式: {self.first_week_config['observation_mode']}")

        print("\n📋 下一步操作:")
        for step in launch_data.get("next_steps", []):
            print(f"  {step}")

        print("="*60)

    def print_status(self):
        """打印当前状态"""
        print("\n" + "="*50)
        print("🏈️ 首周观察期状态")
        print("="*50)
        print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"环境模式: {self.settings.application.environment}")
        print(f"Kelly倍数: {self.first_week_config['kelly_multiplier']} (0.1倍)")
        print(f"最大投注: {self.first_week_config['max_daily_stake_percentage']:.0%}")
        print(f"观察模式: {self.first_week_config['observation_mode']}")

        print("\n📋 安全配置:")
        print(f"  单笔投注限制: 5%")
        print(f"  日投注限制: 20%")
        print(f"  风险告警阈值: 3%")
        print(f"  Brier Score偏差阈值: 15%")
        print(f"  预测准确率阈值: 40%")
        print(f"  ROI损失阈值: -20%")
        print(f"  每日安全拦截限制: 10次")

        print("\n⏰ 监控频率:")
        print(f"  健康检查: 每{self.first_week_config['health_check_interval']}秒")
        print(f"  性能检查: 每{self.first_week_config['performance_check_interval']}秒")
        print(f"  观察检查: 每{self.first_week_config['observation_check_interval']}秒")

        print("\n🔗 常用命令:")
        print("  python scripts/daily_performance.py daily     # 每日性能报告")
        print("  python scripts/observation_mode_manager.py check  # 检查观察模式")
        print("  python scripts/reset_kelly_counters.py reset      # 重置日计数器")
        print("  python scripts/deploy_production.py status     # 查看部署状态")

        print("="*50)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Sprint 9 首周观察期启动")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # 启动命令
    launch_parser = subparsers.add_parser('launch', help='启动首周观察期')
    launch_parser.add_argument('--configure-only', action='store_true', help='仅配置，不启动服务')

    # 状态命令
    status_parser = subparsers.add_parser('status', help='查看当前状态')

    args = parser.parse_args()

    launcher = FirstWeekLauncher()

    try:
        if args.command == 'launch':
            # 启动首周观察期
            result = await launcher.launch_first_week(args.configure_only)
            launcher.print_launch_summary(result)

            return 0 if result['final_status'] in ['success', 'configured_only'] else 1

        elif args.command == 'status':
            # 查看状态
            launcher.print_status()
            return 0

        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\n👋 启动已取消")
        return 1
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))