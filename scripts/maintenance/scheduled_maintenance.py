#!/usr/bin/env python3
"""
定期维护任务调度器
Scheduled Maintenance Task Scheduler

用于定期执行目录维护任务

作者: Claude AI Assistant
版本: v1.0
创建时间: 2025-11-03
"""

import os
import sys
import time
import json
import signal
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.maintenance.directory_maintenance import DirectoryMaintenance
from scripts.maintenance.maintenance_logger import MaintenanceLogger, MaintenanceRecord

class ScheduledMaintenance:
    """定期维护调度器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.maintenance = DirectoryMaintenance(project_root)
        self.logger = MaintenanceLogger(project_root)
        self.running = True

        # 维护配置
        self.schedules = {
            "daily": {
                "interval_hours": 24,
                "actions": ["clean_temp", "clean_cache", "generate_report"],
                "description": "每日基础维护"
            },
            "weekly": {
                "interval_hours": 168,  # 7 * 24
                "actions": ["clean_temp", "clean_cache", "archive_reports", "auto_fix", "generate_report"],
                "description": "每周完整维护"
            },
            "monthly": {
                "interval_hours": 720,  # 30 * 24
                "actions": ["deep_clean", "archive_reports", "auto_fix", "generate_report"],
                "description": "每月深度维护"
            }
        }

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # 状态文件路径
        self.state_file = self.project_root / "logs" / "maintenance" / "scheduler_state.json"

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n📡 收到信号 {signum}，正在停止维护调度器...")
        self.running = False

    def _load_scheduler_state(self) -> Dict[str, Any]:
        """加载调度器状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  加载调度器状态失败: {e}")

        return {
            "last_run": {
                "daily": None,
                "weekly": None,
                "monthly": None
            },
            "next_run": {
                "daily": None,
                "weekly": None,
                "monthly": None
            },
            "statistics": {
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0
            }
        }

    def _save_scheduler_state(self, state: Dict[str, Any]):
        """保存调度器状态"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  保存调度器状态失败: {e}")

    def _should_run_task(self, task_type: str, state: Dict[str, Any]) -> bool:
        """检查是否应该运行任务"""
        last_run = state["last_run"].get(task_type)
        if not last_run:
            return True

        last_run_time = datetime.fromisoformat(last_run)
        interval_hours = self.schedules[task_type]["interval_hours"]
        next_run_time = last_run_time + timedelta(hours=interval_hours)

        return datetime.now() >= next_run_time

def __execute_maintenance_task_check_condition():
                temp_count = self.maintenance.clean_temp_files()
                results["fixes_applied"]["temp_files_cleaned"] = temp_count


def __execute_maintenance_task_check_condition():
                cache_count = self.maintenance.clean_cache_dirs()
                results["fixes_applied"]["cache_dirs_cleaned"] = cache_count


def __execute_maintenance_task_check_condition():
                archive_count = self.maintenance.archive_old_reports()
                results["fixes_applied"]["reports_archived"] = archive_count


def __execute_maintenance_task_check_condition():
                        results["fixes_applied"][key] += value
                    else:
                        results["fixes_applied"][key] = value


def __execute_maintenance_task_check_condition():
                # 深度清理
                temp_count = self.maintenance.clean_temp_files()
                cache_count = self.maintenance.clean_cache_dirs()
                archive_count = self.maintenance.archive_old_reports(days_old=7)  # 更积极的归档
                fixes = self.maintenance.auto_fix_issues(dry_run=False)

                results["fixes_applied"]["temp_files_cleaned"] = results["fixes_applied"].get("temp_files_cleaned",
    0) + temp_count
                results["fixes_applied"]["cache_dirs_cleaned"] = results["fixes_applied"].get("cache_dirs_cleaned",
    0) + cache_count
                results["fixes_applied"]["reports_archived"] = results["fixes_applied"].get("reports_archived",
    0) + archive_count

def __execute_maintenance_task_check_condition():
                        results["fixes_applied"][key] += value
                    else:
                        results["fixes_applied"][key] = value

            # 生成最终健康报告
            final_health_report = self.maintenance.generate_health_report()
            final_health_score = final_health_report.get("health_score", 0)

            # 记录健康快照
            self.logger.log_health_snapshot(final_health_report)

            results["final_health_score"] = final_health_score
            results["health_score_change"] = final_health_score - initial_health_score
            results["success"] = True

            print(f"✅ {task_type} 维护任务完成!")
            print(f"📊 健康评分变化: {initial_health_score} → {final_health_score} ({results['health_score_change']:+d})")

        except Exception as e:
            results["error"] = str(e)
            print(f"❌ {task_type} 维护任务失败: {e}")

        finally:
            results["end_time"] = datetime.now().isoformat()
            results["execution_time_seconds"] = round(time.time() - start_time, 2)

            # 记录维护日志
            record = MaintenanceRecord(
                timestamp=results["start_time"],
                action_type=f"scheduled_{task_type}",
                description=self.schedules[task_type]["description"],
                files_affected=sum(results["fixes_applied"].values()),
                size_freed_mb=0,  # 可以从维护结果中计算
                issues_found=0,   # 可以从维护结果中计算
                issues_fixed=sum(results["fixes_applied"].values()),
                health_score_before=initial_health_score,
                health_score_after=final_health_score or initial_health_score,
                execution_time_seconds=results["execution_time_seconds"],
                success=results["success"],
                error_message=results.get("error")
            )

            self.logger.log_maintenance(record)

        return results

    def _execute_maintenance_task(self, task_type: str) -> Dict[str, Any]:
        """执行维护任务"""
        print(f"\n🚀 开始执行 {task_type} 维护任务...")
        print(f"📝 任务描述: {self.schedules[task_type]['description']}")
        print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        start_time = time.time()
        initial_health_report = self.maintenance.generate_health_report()
        initial_health_score = initial_health_report.get("health_score", 0)

        actions = self.schedules[task_type]["actions"]
        results = {
            "task_type": task_type,
            "start_time": datetime.now().isoformat(),
            "actions": actions,
            "initial_health_score": initial_health_score,
            "success": False,
            "error": None,
            "fixes_applied": {},
            "final_health_score": None,
            "execution_time_seconds": 0
        }

        try:
            # 根据任务类型执行不同的维护操作
            __execute_maintenance_task_check_condition()
                temp_count = self.maintenance.clean_temp_files()
                results["fixes_applied"]["temp_files_cleaned"] = temp_count

            __execute_maintenance_task_check_condition()
                cache_count = self.maintenance.clean_cache_dirs()
                results["fixes_applied"]["cache_dirs_cleaned"] = cache_count

            __execute_maintenance_task_check_condition()
                archive_count = self.maintenance.archive_old_reports()
                results["fixes_applied"]["reports_archived"] = archive_count

            if "auto_fix" in actions:
                fixes = self.maintenance.auto_fix_issues(dry_run=False)
                for key, value in fixes.items():
                    __execute_maintenance_task_check_condition()
                        results["fixes_applied"][key] += value
                    else:
                        results["fixes_applied"][key] = value

            __execute_maintenance_task_check_condition()
                # 深度清理
                temp_count = self.maintenance.clean_temp_files()
                cache_count = self.maintenance.clean_cache_dirs()
                archive_count = self.maintenance.archive_old_reports(days_old=7)  # 更积极的归档
                fixes = self.maintenance.auto_fix_issues(dry_run=False)

                results["fixes_applied"]["temp_files_cleaned"] = results["fixes_applied"].get("temp_files_cleaned",
    0) + temp_count
                results["fixes_applied"]["cache_dirs_cleaned"] = results["fixes_applied"].get("cache_dirs_cleaned",
    0) + cache_count
                results["fixes_applied"]["reports_archived"] = results["fixes_applied"].get("reports_archived",
    0) + archive_count
                for key, value in fixes.items():
                    __execute_maintenance_task_check_condition()
                        results["fixes_applied"][key] += value
                    else:
                        results["fixes_applied"][key] = value

            # 生成最终健康报告
            final_health_report = self.maintenance.generate_health_report()
            final_health_score = final_health_report.get("health_score", 0)

            # 记录健康快照
            self.logger.log_health_snapshot(final_health_report)

            results["final_health_score"] = final_health_score
            results["health_score_change"] = final_health_score - initial_health_score
            results["success"] = True

            print(f"✅ {task_type} 维护任务完成!")
            print(f"📊 健康评分变化: {initial_health_score} → {final_health_score} ({results['health_score_change']:+d})")

        except Exception as e:
            results["error"] = str(e)
            print(f"❌ {task_type} 维护任务失败: {e}")

        finally:
            results["end_time"] = datetime.now().isoformat()
            results["execution_time_seconds"] = round(time.time() - start_time, 2)

            # 记录维护日志
            record = MaintenanceRecord(
                timestamp=results["start_time"],
                action_type=f"scheduled_{task_type}",
                description=self.schedules[task_type]["description"],
                files_affected=sum(results["fixes_applied"].values()),
                size_freed_mb=0,  # 可以从维护结果中计算
                issues_found=0,   # 可以从维护结果中计算
                issues_fixed=sum(results["fixes_applied"].values()),
                health_score_before=initial_health_score,
                health_score_after=final_health_score or initial_health_score,
                execution_time_seconds=results["execution_time_seconds"],
                success=results["success"],
                error_message=results.get("error")
            )

            self.logger.log_maintenance(record)

        return results

    def run_maintenance_cycle(self) -> Dict[str, Any]:
        """运行一次维护周期"""
        print("🔄 开始维护周期检查...")
        state = self._load_scheduler_state()
        executed_tasks = []

        # 检查各种类型的任务
        for task_type in ["daily", "weekly", "monthly"]:
            if self._should_run_task(task_type, state):
                print(f"⏰ 到期执行 {task_type} 任务")
                results = self._execute_maintenance_task(task_type)
                executed_tasks.append(results)

                # 更新状态
                state["last_run"][task_type] = datetime.now().isoformat()
                interval_hours = self.schedules[task_type]["interval_hours"]
                next_run = datetime.now() + timedelta(hours=interval_hours)
                state["next_run"][task_type] = next_run.isoformat()

                # 更新统计
                state["statistics"]["total_runs"] += 1
                if results["success"]:
                    state["statistics"]["successful_runs"] += 1
                else:
                    state["statistics"]["failed_runs"] += 1

                # 保存状态
                self._save_scheduler_state(state)

            else:
                next_run = state["next_run"].get(task_type)
                if next_run:
                    next_run_time = datetime.fromisoformat(next_run)
                    print(f"⏭️  {task_type} 任务下次运行时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if not executed_tasks:
            print("✅ 当前没有到期任务")

        return {
            "executed_tasks": executed_tasks,
            "scheduler_state": state,
            "timestamp": datetime.now().isoformat()
        }

    def run_daemon_mode(self, check_interval_minutes: int = 60):
        """以守护进程模式运行"""
        print(f"🤖 启动维护调度器守护进程")
        print(f"📁 项目根目录: {self.project_root}")
        print(f"⏱️  检查间隔: {check_interval_minutes} 分钟")
        print(f"📊 调度状态文件: {self.state_file}")
        print("按 Ctrl+C 停止调度器\n")

        while self.running:
            try:
                # 运行维护周期
                cycle_results = self.run_maintenance_cycle()

                # 等待下次检查
                for i in range(check_interval_minutes):
                    if not self.running:
                        break
                    time.sleep(60)  # 等待1分钟

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ 维护周期执行出错: {e}")
                # 等待后重试
                time.sleep(300)  # 5分钟后重试

        print("\n🛑 维护调度器已停止")

    def run_once(self):
        """运行一次维护检查"""
        print("🔍 执行单次维护检查...")
        results = self.run_maintenance_cycle()

        if results["executed_tasks"]:
            print(f"\n📊 执行了 {len(results['executed_tasks'])} 个任务:")
            for task in results["executed_tasks"]:
                status = "✅ 成功" if task["success"] else "❌ 失败"
                print(f"   - {task['task_type']}: {status} ({task['execution_time_seconds']}s)")
        else:
            print("📊 没有执行任何任务")

        return results

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="FootballPrediction 定期维护调度器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python3 scheduled_maintenance.py --once              # 单次运行
  python3 scheduled_maintenance.py --daemon            # 守护进程模式
  python3 scheduled_maintenance.py --daemon --interval 30  # 30分钟检查间隔
        """
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        help="项目根目录路径 (默认: 自动检测)"
    )

    parser.add_argument(
        "--daemon",
        action="store_true",
        help="以守护进程模式运行"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="守护进程检查间隔(分钟) (默认: 60)"
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="只运行一次维护检查"
    )

    args = parser.parse_args()

    # 创建调度器实例
    project_root = args.project_root or Path(__file__).parent.parent.parent
    scheduler = ScheduledMaintenance(project_root)

    try:
        if args.once or not args.daemon:
            # 单次运行模式
            scheduler.run_once()
        else:
            # 守护进程模式
            scheduler.run_daemon_mode(args.interval)

    except KeyboardInterrupt:
        print("\n👋 用户中断，退出程序")
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()