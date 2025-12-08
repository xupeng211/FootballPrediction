#!/usr/bin/env python3
"""
1 Hour Unattended Pilot Run Monitor
1小时无人值守试运行监控器

监控后台回填任务，确保其在1小时内持续稳定工作
"""

import subprocess
import time
import os
import sys
import signal
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class PilotRunMonitor:
    def __init__(self, duration_minutes: int = 60):
        self.duration_minutes = duration_minutes
        self.start_time = None
        self.backfill_process: Optional[subprocess.Popen] = None
        self.log_file_path = "logs/backfill_pilot.log"
        self.initial_match_count = 0
        self.monitoring_data = []

    def ensure_log_directory(self):
        """确保logs目录存在"""
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        logger.info(f"📁 日志目录已准备: {logs_dir.absolute()}")

    def start_backfill_process(self) -> bool:
        """启动回填任务进程"""
        logger.info("🚀 启动回填任务进程...")

        try:
            # 使用subprocess.Popen启动后台进程
            cmd = [
                "docker-compose", "exec", "app",
                "python", "scripts/backfill_full_history.py"
            ]

            # 创建日志文件
            with open(self.log_file_path, 'w') as log_file:
                log_file.write(f"=== 回填任务启动日志 {datetime.now()} ===\n")
                log_file.write(f"命令: {' '.join(cmd)}\n\n")

            # 启动进程，重定向输出到日志文件
            with open(self.log_file_path, 'a') as log_file:
                self.backfill_process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

            logger.info(f"✅ 回填任务已启动，PID: {self.backfill_process.pid}")
            logger.info(f"📝 日志文件: {os.path.abspath(self.log_file_path)}")

            # 等待几秒确保进程正常启动
            time.sleep(3)

            if self.backfill_process.poll() is None:
                logger.info("✅ 回填任务进程运行正常")
                return True
            else:
                logger.error(f"❌ 回填任务启动失败，退出码: {self.backfill_process.returncode}")
                return False

        except Exception as e:
            logger.error(f"❌ 启动回填任务失败: {e}")
            return False

    def get_match_count(self) -> int:
        """查询数据库中matches表的总记录数"""
        try:
            cmd = [
                "docker-compose", "exec", "db",
                "psql", "-U", "postgres", "-d", "football_prediction",
                "-c", "SELECT COUNT(*) FROM matches;"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # 解析输出获取记录数
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip() and not line.startswith(' count') and not line.startswith('-----'):
                        return int(line.strip())

            logger.warning(f"⚠️ 查询数据库失败: {result.stderr}")
            return 0

        except Exception as e:
            logger.error(f"❌ 数据库查询异常: {e}")
            return 0

    def get_last_log_lines(self, num_lines: int = 20) -> str:
        """获取日志文件的最后N行"""
        try:
            if not os.path.exists(self.log_file_path):
                return "日志文件不存在"

            cmd = ["tail", "-n", str(num_lines), self.log_file_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout if result.returncode == 0 else f"读取日志失败: {result.stderr}"

        except Exception as e:
            return f"读取日志异常: {e}"

    def monitoring_loop(self):
        """主监控循环"""
        logger.info(f"🔍 开始 {self.duration_minutes} 分钟监控循环...")
        self.start_time = datetime.now()
        self.initial_match_count = self.get_match_count()

        logger.info(f"📊 初始数据库记录数: {self.initial_match_count}")

        for minute in range(1, self.duration_minutes + 1):
            cycle_start = datetime.now()

            # 检查进程状态
            if self.backfill_process.poll() is not None:
                logger.error(f"💥 回填任务已停止！退出码: {self.backfill_process.returncode}")
                logger.error("📋 最后20行日志:")
                logger.error(self.get_last_log_lines())
                return False

            # 获取当前数据统计
            current_match_count = self.get_match_count()
            matches_added = current_match_count - self.initial_match_count
            elapsed_minutes = minute

            # 计算速度
            speed = matches_added / elapsed_minutes if elapsed_minutes > 0 else 0

            # 记录监控数据
            monitoring_point = {
                'minute': minute,
                'timestamp': datetime.now().isoformat(),
                'total_matches': current_match_count,
                'matches_added': matches_added,
                'speed_per_minute': round(speed, 2)
            }
            self.monitoring_data.append(monitoring_point)

            # 打印状态
            status_line = (
                f"[{minute:3d}/{self.duration_minutes}] "
                f"Status: ✅ Running | "
                f"Total: {current_match_count:4d} | "
                f"Added: +{matches_added:3d} | "
                f"Speed: {speed:5.1f}/min"
            )

            print(f"\r{status_line}", end="", flush=True)

            # 每5分钟记录一次到日志
            if minute % 5 == 0:
                logger.info(status_line)

            # 等待1分钟（减去本循环耗时）
            cycle_time = (datetime.now() - cycle_start).total_seconds()
            sleep_time = max(0, 60.0 - cycle_time)
            time.sleep(sleep_time)

        print()  # 换行
        logger.info("✅ 监控周期完成")
        return True

    def stop_backfill_process(self):
        """优雅地停止回填进程"""
        if self.backfill_process and self.backfill_process.poll() is None:
            logger.info("🛑 正在停止回填任务...")

            try:
                # 先尝试发送SIGTERM
                self.backfill_process.terminate()

                # 等待10秒
                try:
                    self.backfill_process.wait(timeout=10)
                    logger.info("✅ 回填任务已优雅停止")
                except subprocess.TimeoutExpired:
                    # 如果10秒后还没停止，强制杀死
                    logger.warning("⚠️ 优雅停止失败，强制终止进程")
                    self.backfill_process.kill()
                    self.backfill_process.wait()
                    logger.info("✅ 回填任务已强制停止")

            except Exception as e:
                logger.error(f"❌ 停止进程失败: {e}")

    def generate_report(self) -> str:
        """生成Markdown格式的监控报告"""
        if not self.monitoring_data:
            return "无监控数据"

        end_time = datetime.now()
        duration = end_time - self.start_time
        total_matches = self.monitoring_data[-1]['total_matches']
        matches_added = self.monitoring_data[-1]['matches_added']
        avg_speed = matches_added / (duration.total_seconds() / 60) if duration.total_seconds() > 0 else 0

        # 计算峰值速度
        peak_speed = max(point['speed_per_minute'] for point in self.monitoring_data)

        report = f"""# 🚀 1小时无人值守试运行报告

## 📊 执行摘要

- **开始时间**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
- **结束时间**: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
- **总耗时**: {duration}
- **任务状态**: {'✅ 成功完成' if all(p['speed_per_minute'] >= 0 for p in self.monitoring_data) else '⚠️ 有异常'}

## 📈 数据采集统计

- **初始记录数**: {self.initial_match_count}
- **最终记录数**: {total_matches}
- **新增记录数**: {matches_added}
- **平均速度**: {avg_speed:.1f} 条/分钟
- **峰值速度**: {peak_speed:.1f} 条/分钟

## 📋 详细监控数据

| 分钟 | 时间戳 | 总记录数 | 新增记录 | 速度(条/分钟) |
|------|--------|----------|----------|--------------|
"""

        # 添加详细数据（每5分钟一次）
        for i, point in enumerate(self.monitoring_data):
            if i % 5 == 0 or i == len(self.monitoring_data) - 1:  # 每5分钟或最后一次
                timestamp = datetime.fromisoformat(point['timestamp']).strftime('%H:%M:%S')
                report += f"| {point['minute']:3d} | {timestamp} | {point['total_matches']:4d} | {point['matches_added']:3d} | {point['speed_per_minute']:5.1f} |\n"

        report += f"""
## 📝 日志分析

- **日志文件**: `{self.log_file_path}`
- **日志大小**: {os.path.getsize(self.log_file_path) if os.path.exists(self.log_file_path) else 0} 字节

### 最后20行日志预览
```
{self.get_last_log_lines()}
```

## 🎯 结论

{"✅ 系统运行稳定，可以投入生产使用" if avg_speed > 0 else "⚠️ 需要进一步调试优化"}

## 📈 建议

1. {"继续执行大规模数据回填" if avg_speed > 5 else "优化数据采集速度"}
2. {"设置自动化监控告警" if len(self.monitoring_data) > 0 else "检查监控脚本"}
3. {"定期备份数据库" if matches_added > 0 else "检查数据采集流程"}

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return report

    def save_report(self, report: str):
        """保存报告到文件"""
        report_file = f"logs/pilot_run_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"📋 监控报告已保存: {report_file}")
            return report_file
        except Exception as e:
            logger.error(f"❌ 保存报告失败: {e}")
            return None

    def run(self) -> bool:
        """执行完整的监控流程"""
        logger.info("🎯 启动1小时无人值守试运行监控")

        try:
            # 确保日志目录存在
            self.ensure_log_directory()

            # 启动回填任务
            if not self.start_backfill_process():
                return False

            # 监控循环
            success = self.monitoring_loop()

            # 停止回填任务
            self.stop_backfill_process()

            # 生成并保存报告
            if success:
                report = self.generate_report()
                report_file = self.save_report(report)

                if report_file:
                    print(f"\n📋 详细报告已保存: {report_file}")

                print("\n" + "="*80)
                print("🎉 1小时无人值守试运行完成!")
                print("="*80)
                print(report)

            return success

        except KeyboardInterrupt:
            logger.info("⏹️ 用户中断监控")
            self.stop_backfill_process()
            return False
        except Exception as e:
            logger.error(f"💥 监控异常: {e}")
            self.stop_backfill_process()
            return False

def main():
    """主函数"""
    monitor = PilotRunMonitor(duration_minutes=60)
    success = monitor.run()

    if success:
        logger.info("✅ 无人值守试运行成功完成")
        sys.exit(0)
    else:
        logger.error("❌ 无人值守试运行失败")
        sys.exit(1)

if __name__ == "__main__":
    main()