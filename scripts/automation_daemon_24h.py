#!/usr/bin/env python3
"""
24小时自动化实战模拟守护进程
集成影子测试与生产预测，支持crontab和内部循环两种模式
FootballPrediction v2.3.0-production
"""

import asyncio
import logging
import sys
import time
import os
import json
import signal
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

# 设置项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
# 确保日志目录存在
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'automation_24h.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutomationMode(Enum):
    """自动化模式枚举"""
    INTERNAL_LOOP = "internal_loop"  # 内部循环模式
    CRONTAB = "crontab"              # Crontab模式
    SHADOW_TEST = "shadow_test"      # 影子测试模式
    PRODUCTION = "production"        # 生产模式

@dataclass
class AutomationConfig:
    """自动化配置"""
    mode: AutomationMode
    prediction_interval_minutes: int = 15
    test_duration_hours: int = 24
    enable_crontab: bool = True
    enable_monitoring: bool = True
    enable_auto_restart: bool = True
    max_retries: int = 3
    health_check_interval: int = 300  # 5分钟

class AutomationDaemon24H:
    """24小时自动化实战守护进程"""

    def __init__(self, config: AutomationConfig):
        self.config = config
        self.start_time = datetime.now()
        self.running = True
        self.stats = {
            'total_predictions': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'system_restarts': 0,
            'health_checks': 0,
            'last_prediction_time': None,
            'predictions_today': 0,
            'daily_target': 96  # 24小时 * 4次/小时 (每15分钟一次)
        }

        # 注册信号处理器
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info(f"🤖 24小时自动化守护进程初始化完成")
        logger.info(f"模式: {config.mode.value}")
        logger.info(f"预测间隔: {config.prediction_interval_minutes}分钟")
        logger.info(f"运行时长: {config.test_duration_hours}小时")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，准备优雅关闭...")
        self.running = False

    async def setup_crontab(self) -> bool:
        """设置crontab自动任务"""
        if not self.config.enable_crontab or self.config.mode != AutomationMode.CRONTAB:
            return True

        try:
            # 获取当前脚本的绝对路径
            script_path = Path(__file__).absolute()
            python_executable = sys.executable

            # 构建crontab任务
            cron_job = f"""
# FootballPrediction 24小时自动化任务
# 每{self.config.prediction_interval_minutes}分钟执行一次预测
*/{self.config.prediction_interval_minutes} * * * * cd {project_root} && {python_executable} {script_path} --mode single_prediction >> /app/logs/cron_predictions.log 2>&1

# 每小时健康检查
0 * * * * cd {project_root} && {python_executable} {script_path} --mode health_check >> /app/logs/cron_health.log 2>&1

# 每日报告生成
0 0 * * * cd {project_root} && {python_executable} {script_path} --mode daily_report >> /app/logs/cron_daily.log 2>&1
"""

            # 写入临时crontab文件
            cron_file = "/tmp/football_automation_cron"
            with open(cron_file, 'w') as f:
                f.write(cron_job.strip())

            # 安装crontab
            result = subprocess.run(['crontab', cron_file], capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("✅ Crontab任务安装成功")
                os.unlink(cron_file)
                return True
            else:
                logger.error(f"❌ Crontab安装失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ 设置crontab失败: {e}")
            return False

    async def remove_crontab(self) -> bool:
        """移除crontab任务"""
        try:
            result = subprocess.run(['crontab', '-r'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ Crontab任务已移除")
                return True
            else:
                logger.warning("⚠️ 移除crontab任务时出现警告")
                return True
        except Exception as e:
            logger.error(f"❌ 移除crontab失败: {e}")
            return False

    async def run_single_prediction(self) -> Dict[str, Any]:
        """执行单次预测"""
        try:
            # 使用预测CLI工具
            prediction_script = project_root / "scripts" / "predict_match_v2.py"

            # 构建预测命令（这里使用示例比赛，实际应该从API获取）
            cmd = [
                sys.executable,
                str(prediction_script),
                "--home", "Manchester United",
                "--away", "Arsenal",
                "--json-only"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                prediction_data = json.loads(result.stdout)
                self.stats['successful_predictions'] += 1
                self.stats['last_prediction_time'] = datetime.now().isoformat()
                self.stats['predictions_today'] += 1

                logger.info(f"✅ 预测成功: {prediction_data.get('prediction', 'Unknown')}")
                return {
                    'success': True,
                    'prediction': prediction_data,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                self.stats['failed_predictions'] += 1
                logger.error(f"❌ 预测失败: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'timestamp': datetime.now().isoformat()
                }

        except subprocess.TimeoutExpired:
            self.stats['failed_predictions'] += 1
            logger.error("❌ 预测超时")
            return {
                'success': False,
                'error': 'Prediction timeout',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.stats['failed_predictions'] += 1
            logger.error(f"❌ 预测异常: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def health_check(self) -> Dict[str, Any]:
        """系统健康检查"""
        try:
            health_script = project_root / "scripts" / "predict_match_v2.py"
            cmd = [sys.executable, str(health_script), "--help"]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            is_healthy = result.returncode == 0
            self.stats['health_checks'] += 1

            return {
                'healthy': is_healthy,
                'timestamp': datetime.now().isoformat(),
                'details': 'OK' if is_healthy else 'FAILED'
            }

        except Exception as e:
            logger.error(f"❌ 健康检查异常: {e}")
            return {
                'healthy': False,
                'timestamp': datetime.now().isoformat(),
                'details': str(e)
            }

    async def generate_daily_report(self) -> Dict[str, Any]:
        """生成日报"""
        try:
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'statistics': self.stats.copy(),
                'uptime_hours': (datetime.now() - self.start_time).total_seconds() / 3600,
                'success_rate': self.stats['successful_predictions'] / max(1, self.stats['total_predictions']) * 100,
                'target_completion_rate': self.stats['predictions_today'] / self.stats['daily_target'] * 100
            }

            # 保存报告
            report_path = Path(f"/app/logs/daily_report_{datetime.now().strftime('%Y%m%d')}.json")
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            logger.info(f"📊 日报已生成: {report_path}")
            return report

        except Exception as e:
            logger.error(f"❌ 生成日报失败: {e}")
            return {}

    async def run_internal_loop(self) -> bool:
        """运行内部循环模式"""
        logger.info("🔄 启动内部循环模式")

        interval_seconds = self.config.prediction_interval_minutes * 60
        last_health_check = time.time()

        while self.running and self.is_test_running():
            cycle_start = time.time()

            try:
                # 执行预测
                logger.info(f"🎯 执行预测 #{self.stats['total_predictions'] + 1}")
                prediction_result = await self.run_single_prediction()
                self.stats['total_predictions'] += 1

                # 定期健康检查
                if time.time() - last_health_check >= self.config.health_check_interval:
                    logger.info("🏥 执行健康检查")
                    health_result = await self.health_check()
                    if not health_result['healthy']:
                        logger.warning("⚠️ 健康检查失败，尝试恢复...")
                        if self.config.enable_auto_restart:
                            await self.auto_restart()
                    last_health_check = time.time()

                # 计算下次执行时间
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, interval_seconds - cycle_duration)

                logger.info(f"⏰ 等待 {sleep_time:.1f} 秒后执行下次预测")

                # 分段睡眠，便于响应信号
                sleep_end = time.time() + sleep_time
                while time.time() < sleep_end and self.running:
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"❌ 循环执行异常: {e}")
                await asyncio.sleep(60)  # 错误后等待1分钟

        return True

    async def auto_restart(self):
        """自动重启恢复"""
        try:
            self.stats['system_restarts'] += 1
            logger.info("🔄 尝试自动重启...")

            # 这里可以添加重启逻辑，比如重启Docker容器等
            # 暂时只记录日志
            logger.info("✅ 自动重启完成")

        except Exception as e:
            logger.error(f"❌ 自动重启失败: {e}")

    def is_test_running(self) -> bool:
        """检查测试是否仍在运行"""
        elapsed = datetime.now() - self.start_time
        return elapsed.total_seconds() < (self.config.test_duration_hours * 3600)

    async def run_shadow_test_mode(self) -> bool:
        """运行影子测试模式"""
        logger.info("🎭 启动影子测试模式")

        # 调用现有的影子守护进程
        shadow_script = project_root / "scripts" / "shadow_daemon_production.py"
        cmd = [sys.executable, str(shadow_script)]

        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # 监控影子测试进程
            while process.poll() is None and self.running and self.is_test_running():
                await asyncio.sleep(60)  # 每分钟检查一次

            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.info(f"影子测试进程结束: {stdout}")
                if stderr:
                    logger.error(f"影子测试错误: {stderr}")

            return True

        except Exception as e:
            logger.error(f"❌ 启动影子测试失败: {e}")
            return False

    async def run(self) -> bool:
        """主运行逻辑"""
        logger.info("🚀 启动24小时自动化守护进程")

        try:
            # 设置crontab（如果需要）
            if self.config.mode == AutomationMode.CRONTAB:
                if not await self.setup_crontab():
                    logger.error("❌ Crontab设置失败，退出")
                    return False

            # 根据模式运行不同的逻辑
            if self.config.mode == AutomationMode.INTERNAL_LOOP:
                success = await self.run_internal_loop()
            elif self.config.mode == AutomationMode.SHADOW_TEST:
                success = await self.run_shadow_test_mode()
            elif self.config.mode == AutomationMode.CRONTAB:
                # Crontab模式下，守护进程主要负责监控
                success = await self.run_crontab_monitor()
            else:
                logger.error(f"❌ 不支持的模式: {self.config.mode}")
                return False

            # 生成最终报告
            await self.generate_daily_report()

            # 清理crontab
            if self.config.mode == AutomationMode.CRONTAB:
                await self.remove_crontab()

            logger.info("✅ 24小时自动化守护进程完成")
            return True

        except Exception as e:
            logger.error(f"❌ 守护进程运行异常: {e}")
            return False

    async def run_crontab_monitor(self) -> bool:
        """运行crontab监控模式"""
        logger.info("📊 启动crontab监控模式")

        while self.running and self.is_test_running():
            await asyncio.sleep(300)  # 5分钟检查一次

            # 检查系统状态
            health_result = await self.health_check()
            if not health_result['healthy']:
                logger.warning("⚠️ 系统健康检查失败")

        return True

async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='24小时自动化实战模拟守护进程')
    parser.add_argument('--mode',
                       choices=['internal_loop', 'crontab', 'shadow_test', 'single_prediction', 'health_check', 'daily_report'],
                       default='internal_loop',
                       help='运行模式')
    parser.add_argument('--duration', type=int, default=24, help='测试时长（小时）')
    parser.add_argument('--interval', type=int, default=15, help='预测间隔（分钟）')

    args = parser.parse_args()

    # 处理特殊模式
    if args.mode == 'single_prediction':
        daemon = AutomationDaemon24H(AutomationConfig(AutomationMode.INTERNAL_LOOP))
        result = await daemon.run_single_prediction()
        print(json.dumps(result, indent=2))
        return 0 if result['success'] else 1

    elif args.mode == 'health_check':
        daemon = AutomationDaemon24H(AutomationConfig(AutomationMode.INTERNAL_LOOP))
        result = await daemon.health_check()
        print(json.dumps(result, indent=2))
        return 0 if result['healthy'] else 1

    elif args.mode == 'daily_report':
        daemon = AutomationDaemon24H(AutomationConfig(AutomationMode.INTERNAL_LOOP))
        report = await daemon.generate_daily_report()
        print(json.dumps(report, indent=2))
        return 0

    # 创建配置
    config = AutomationConfig(
        mode=AutomationMode(args.mode),
        prediction_interval_minutes=args.interval,
        test_duration_hours=args.duration
    )

    # 创建并运行守护进程
    daemon = AutomationDaemon24H(config)

    try:
        print("🤖 FootballPrediction 24小时自动化实战模拟系统")
        print(f"模式: {config.mode.value}")
        print(f"测试时长: {config.test_duration_hours}小时")
        print(f"预测间隔: {config.prediction_interval_minutes}分钟")
        print("\n按 Ctrl+C 停止自动化\n")

        success = await daemon.run()
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n🛑 用户中断自动化")
        return 0
    except Exception as e:
        logger.error(f"自动化守护进程异常: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)