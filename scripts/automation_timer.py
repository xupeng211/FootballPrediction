#!/usr/bin/env python3
"""
自动化定时器 - 在6/12/24小时自动触发对账单生成
FootballPrediction v2.3.0-production
"""

import asyncio
import logging
import sys
import signal
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import subprocess

# 设置项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "logs" / "automation_timer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutomationTimer:
    """自动化定时器"""

    def __init__(self, start_time: datetime, duration_hours: int = 24):
        self.start_time = start_time
        self.duration_hours = duration_hours
        self.running = True

        # 预定义的触发时间点（小时）
        self.trigger_points = [6, 12, 24]
        self.completed_triggers = set()

        # 注册信号处理器
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info(f"🕐 自动化定时器已启动")
        logger.info(f"⏰ 开始时间: {start_time}")
        logger.info(f"⏱️ 运行时长: {duration_hours}小时")
        logger.info(f"🎯 触发点: {self.trigger_points}小时")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，准备优雅关闭...")
        self.running = False

    def get_elapsed_hours(self) -> float:
        """获取已运行小时数"""
        return (datetime.now() - self.start_time).total_seconds() / 3600

    def should_trigger_report(self) -> Optional[int]:
        """检查是否应该触发报告生成"""
        elapsed = self.get_elapsed_hours()

        for trigger_point in self.trigger_points:
            if trigger_point not in self.completed_triggers and elapsed >= trigger_point:
                return trigger_point

        return None

    async def generate_settlement_report(self, trigger_hour: int) -> bool:
        """生成对账单"""
        try:
            logger.info(f"📊 开始生成{trigger_hour}小时对账单")

            # 调用对账单生成脚本
            script_path = project_root / "scripts" / "settlement_report.py"
            cmd = [sys.executable, str(script_path), "--type", f"{trigger_hour}h", "--quiet"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                cwd=project_root
            )

            if result.returncode == 0:
                logger.info(f"✅ {trigger_hour}小时对账单生成成功")
                self.completed_triggers.add(trigger_hour)
                return True
            else:
                logger.error(f"❌ {trigger_hour}小时对账单生成失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"❌ {trigger_hour}小时对账单生成超时")
            return False
        except Exception as e:
            logger.error(f"❌ {trigger_hour}小时对账单生成异常: {e}")
            return False

    def generate_system_status_report(self) -> Dict[str, Any]:
        """生成系统状态报告"""
        try:
            # 检查自动化守护进程
            automation_process = None
            try:
                result = subprocess.run(['pgrep', '-f', 'automation_daemon_24h.py'],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    automation_process = result.stdout.strip()
            except:
                pass

            # 检查影子守护进程
            shadow_process = None
            try:
                result = subprocess.run(['pgrep', '-f', 'shadow_daemon_production.py'],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    shadow_process = result.stdout.strip()
            except:
                pass

            # 检查数据文件
            l2_files_count = 0
            l2_dir = project_root / "data" / "l2_output"
            if l2_dir.exists():
                l2_files_count = len(list(l2_dir.glob("*.json")))

            return {
                'timestamp': datetime.now().isoformat(),
                'elapsed_hours': self.get_elapsed_hours(),
                'automation_process_pid': automation_process,
                'shadow_process_pid': shadow_process,
                'l2_data_files': l2_files_count,
                'completed_triggers': list(self.completed_triggers),
                'pending_triggers': [t for t in self.trigger_points if t not in self.completed_triggers],
                'system_status': 'Running' if self.running else 'Stopping'
            }

        except Exception as e:
            logger.error(f"生成系统状态报告失败: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'system_status': 'Error'
            }

    async def save_status_report(self, status: Dict[str, Any]):
        """保存状态报告"""
        try:
            reports_dir = project_root / "reports"
            reports_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"timer_status_{timestamp}.json"
            filepath = reports_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False, default=str)

        except Exception as e:
            logger.error(f"保存状态报告失败: {e}")

    async def run(self):
        """运行定时器主循环"""
        logger.info("🚀 自动化定时器开始运行")

        last_status_time = time.time()
        status_interval = 1800  # 每30分钟保存一次状态报告

        try:
            while self.running and self.get_elapsed_hours() < self.duration_hours:
                # 检查是否需要触发报告
                trigger_hour = self.should_trigger_report()
                if trigger_hour:
                    await self.generate_settlement_report(trigger_hour)

                # 定期保存状态报告
                current_time = time.time()
                if current_time - last_status_time >= status_interval:
                    status = self.generate_system_status_report()
                    await self.save_status_report(status)
                    last_status_time = current_time

                # 短暂休眠
                await asyncio.sleep(60)  # 每分钟检查一次

            # 最终状态报告
            if self.running:
                logger.info("🏁 定时器运行完成，生成最终报告")
                status = self.generate_system_status_report()
                await self.save_status_report(status)

                # 确保所有触发点都完成（如果时间允许）
                remaining_time = self.duration_hours - self.get_elapsed_hours()
                if remaining_time > 0:
                    for trigger_point in self.trigger_points:
                        if trigger_point not in self.completed_triggers:
                            if self.get_elapsed_hours() >= trigger_point:
                                await self.generate_settlement_report(trigger_point)

        except Exception as e:
            logger.error(f"❌ 定时器运行异常: {e}")

        logger.info("🔚 自动化定时器已停止")

async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='自动化定时器')
    parser.add_argument('--duration', type=int, default=24, help='运行时长（小时）')
    parser.add_argument('--start-time', help='开始时间 (YYYY-MM-DD HH:MM:SS)')

    args = parser.parse_args()

    # 确定开始时间
    if args.start_time:
        start_time = datetime.strptime(args.start_time, "%Y-%m-%d %H:%M:%S")
    else:
        start_time = datetime.now()

    try:
        # 创建定时器
        timer = AutomationTimer(start_time, args.duration)

        print("🕐 FootballPrediction 自动化定时器")
        print(f"⏰ 开始时间: {start_time}")
        print(f"⏱️ 运行时长: {args.duration}小时")
        print(f"🎯 自动触发: 6h, 12h, 24h 对账单")
        print("\n按 Ctrl+C 停止定时器\n")

        # 运行定时器
        await timer.run()

        return 0

    except KeyboardInterrupt:
        print("\n🛑 用户中断定时器")
        return 0
    except Exception as e:
        logger.error(f"定时器异常: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)