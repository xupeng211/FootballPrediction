#!/usr/bin/env python3
"""
测试维护自动化系统
Test Maintenance Automation System

集成所有测试工具的自动化维护平台，提供全面的测试健康管理和自动修复功能。

作者: Claude AI Assistant
版本: v1.0
创建时间: 2025-11-03
"""

import json
import sqlite3
import sys
import time
import asyncio
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class MaintenanceStatus(Enum):
    """维护状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class MaintenanceTask(Enum):
    """维护任务枚举"""
    HEALTH_CHECK = "health_check"
    COVERAGE_ANALYSIS = "coverage_analysis"
    QUALITY_GATE = "quality_gate"
    REPORT_GENERATION = "report_generation"
    AUTO_FIX = "auto_fix"
    CLEANUP = "cleanup"

@dataclass
class MaintenanceConfig:
    """维护配置"""
    # 运行间隔 (秒)
    health_check_interval: int = 300  # 5分钟
    coverage_analysis_interval: int = 3600  # 1小时
    quality_gate_interval: int = 1800  # 30分钟
    report_generation_interval: int = 7200  # 2小时
    auto_fix_interval: int = 86400  # 24小时
    cleanup_interval: int = 604800  # 7天

    # 阈值配置
    min_coverage_threshold: float = 30.0
    min_health_score: float = 70.0
    max_failed_tests: int = 5
    max_execution_time: int = 300

    # 自动修复配置
    enable_auto_fix: bool = True
    enable_auto_cleanup: bool = True
    enable_smart_optimization: bool = True

@dataclass
class MaintenanceTaskResult:
    """维护任务结果"""
    task: MaintenanceTask
    status: MaintenanceStatus
    start_time: datetime
    end_time: Optional[datetime]
    duration: float
    success: bool
    message: str
    data: Dict[str, Any]
    errors: List[str]

class TestMaintenanceAutomation:
    """测试维护自动化系统"""

    def __init__(self, project_root: Path, config: Optional[MaintenanceConfig] = None):
        self.project_root = project_root
        self.config = config or MaintenanceConfig()

        # 状态管理
        self.current_status = MaintenanceStatus.IDLE
        self.running_tasks = {}
        self.task_history = []
        self.shutdown_requested = False

        # 数据存储
        self.db_path = project_root / "data" / "maintenance_automation.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

        # 任务调度器
        self.task_schedules = {
            MaintenanceTask.HEALTH_CHECK: {
                "interval": self.config.health_check_interval,
                "last_run": None,
                "enabled": True
            },
            MaintenanceTask.COVERAGE_ANALYSIS: {
                "interval": self.config.coverage_analysis_interval,
                "last_run": None,
                "enabled": True
            },
            MaintenanceTask.QUALITY_GATE: {
                "interval": self.config.quality_gate_interval,
                "last_run": None,
                "enabled": True
            },
            MaintenanceTask.REPORT_GENERATION: {
                "interval": self.config.report_generation_interval,
                "last_run": None,
                "enabled": True
            },
            MaintenanceTask.AUTO_FIX: {
                "interval": self.config.auto_fix_interval,
                "last_run": None,
                "enabled": self.config.enable_auto_fix
            },
            MaintenanceTask.CLEANUP: {
                "interval": self.config.cleanup_interval,
                "last_run": None,
                "enabled": self.config.enable_auto_cleanup
            }
        }

    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS maintenance_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration REAL NOT NULL,
                    success BOOLEAN NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT NOT NULL,
                    errors TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_name
                ON maintenance_tasks(task_name)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_start_time
                ON maintenance_tasks(start_time)
            """)

    def save_task_result(self, result: MaintenanceTaskResult):
        """保存任务结果到数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO maintenance_tasks
                (task_name, status, start_time, end_time, duration,
                 success, message, data, errors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.task.value,
                result.status.value,
                result.start_time.isoformat(),
                result.end_time.isoformat() if result.end_time else None,
                result.duration,
                result.success,
                result.message,
                json.dumps(result.data),
                json.dumps(result.errors)
            ))

        self.task_history.append(result)
        # 保持历史记录在合理范围内
        if len(self.task_history) > 1000:
            self.task_history = self.task_history[-500:]

    async def execute_health_check(self) -> MaintenanceTaskResult:
        """执行健康检查任务"""
        start_time = datetime.now()

        try:
            # 导入健康监控器
            sys.path.append(str(self.project_root / "scripts" / "maintenance"))
            from test_health_monitor import TestHealthMonitor

            monitor = TestHealthMonitor(self.project_root)
            health_data = monitor.run_test_health_check()
            health_score = health_data.get('health_score', 0)
            alerts = health_data.get('alerts', [])

            data = {
                "health_score": health_score,
                "alerts_count": len(alerts),
                "critical_alerts": len([a for a in alerts if a.get("severity") == "critical"]),


                "timestamp": datetime.now().isoformat()
            }

            success = health_score >= self.config.min_health_score
            message = f"健康检查完成，评分: {health_score:.1f}" if success else f"健康评分过低: {health_score:.1f}"

            return MaintenanceTaskResult(
                task=MaintenanceTask.HEALTH_CHECK,
                status=MaintenanceStatus.COMPLETED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                success=success,
                message=message,
                data=data,
                errors=[]
            )

        except Exception as e:
            return MaintenanceTaskResult(
                task=MaintenanceTask.HEALTH_CHECK,
                status=MaintenanceStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                success=False,
                message=f"健康检查失败: {str(e)}",
                data={},
                errors=[str(e)]
            )

    async def execute_coverage_analysis(self) -> MaintenanceTaskResult:
        """执行覆盖率分析任务"""
        start_time = datetime.now()

        try:
            # 导入覆盖率趋势分析器
            sys.path.append(str(self.project_root / "scripts" / "maintenance"))
            from coverage_trend_analyzer import CoverageTrendAnalyzer

            analyzer = CoverageTrendAnalyzer(self.project_root)

            # 收集当前数据
            current_data = analyzer.collect_current_coverage()
            if current_data:
                analyzer.store_coverage_data(current_data)

                # 分析趋势
                trend_analysis = analyzer.analyze_trends(7)  # 分析最近7天

                data = {
                    "current_coverage": current_data.total_coverage,
                    "module_count": len(current_data.module_coverage),
                    "trend_direction": trend_analysis.trend_direction,
                    "trend_strength": trend_analysis.trend_strength,
                    "prediction_7d": trend_analysis.prediction_7d,
                    "timestamp": datetime.now().isoformat()
                }

                success = current_data.total_coverage >= self.config.min_coverage_threshold
                message = f"覆盖率分析完成，当前: {current_data.total_coverage:.1f}%"

            else:
                data = {"error": "无法收集覆盖率数据"}
                success = False
                message = "覆盖率数据收集失败"

            return MaintenanceTaskResult(
                task=MaintenanceTask.COVERAGE_ANALYSIS,
                status=MaintenanceStatus.COMPLETED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                success=success,
                message=message,
                data=data,
                errors=[]
            )

        except Exception as e:
            return MaintenanceTaskResult(
                task=MaintenanceTask.COVERAGE_ANALYSIS,
                status=MaintenanceStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                success=False,
                message=f"覆盖率分析失败: {str(e)}",
                data={},
                errors=[str(e)]
            )

    async def execute_quality_gate(self) -> MaintenanceTaskResult:
        """执行质量门禁任务"""
        start_time = datetime.now()

        try:
            # 导入质量门禁
            sys.path.append(str(self.project_root / "scripts" / "maintenance"))
            from ci_cd_quality_gate import QualityGate

            gate = QualityGate(self.project_root)
            report = gate.evaluate_quality_gate()

            data = {
                "overall_result": report.overall_result.value,
                "health_score": report.summary["health_score"],
                "total_metrics": report.total_metrics,
                "passed_metrics": report.passed_metrics,
                "failed_metrics": report.failed_metrics,
                "warning_metrics": report.warning_metrics,
                "timestamp": datetime.now().isoformat()
            }

            success = report.overall_result.value in ["pass", "warn"]
            message = f"质量门禁{report.overall_result.value.upper()}，评分: {report.summary['health_score']:.1f}"

            return MaintenanceTaskResult(
                task=MaintenanceTask.QUALITY_GATE,
                status=MaintenanceStatus.COMPLETED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                success=success,
                message=message,
                data=data,
                errors=[]
            )

        except Exception as e:
            return MaintenanceTaskResult(
                task=MaintenanceTask.QUALITY_GATE,
                status=MaintenanceStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                success=False,
                message=f"质量门禁检查失败: {str(e)}",
                data={},
                errors=[str(e)]
            )

    async def execute_report_generation(self) -> MaintenanceTaskResult:
        """执行报告生成任务"""
        start_time = datetime.now()

        try:
            # 导入报告生成器
            sys.path.append(str(self.project_root / "scripts" / "maintenance"))
            from test_report_generator import TestReportGenerator

            generator = TestReportGenerator(self.project_root)
            reports = generator.generate_all_reports()

            data = {
                "generated_reports": {format_type: str(file_path) for format_type,
    file_path in reports.items()},

                "report_count": len(reports),
                "timestamp": datetime.now().isoformat()
            }

            success = len(reports) > 0
            message = f"生成了 {len(reports)} 个报告"

            return MaintenanceTaskResult(
                task=MaintenanceTask.REPORT_GENERATION,
                status=MaintenanceStatus.COMPLETED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                success=success,
                message=message,
                data=data,
                errors=[]
            )

        except Exception as e:
            return MaintenanceTaskResult(
                task=MaintenanceTask.REPORT_GENERATION,
                status=MaintenanceStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                success=False,
                message=f"报告生成失败: {str(e)}",
                data={},
                errors=[str(e)]
            )

    async def execute_auto_fix(self) -> MaintenanceTaskResult:
        """执行自动修复任务"""
        start_time = datetime.now()

        try:
            # 这里可以集成自动修复逻辑
            # 例如运行 smart_quality_fixer.py
            fixer_script = self.project_root / "scripts" / "smart_quality_fixer.py"

            if fixer_script.exists():
                result = subprocess.run(
                    ["python3", str(fixer_script)],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                success = result.returncode == 0
                data = {
                    "fixer_executed": True,
                    "return_code": result.returncode,
                    "stdout": result.stdout[:1000],  # 限制输出长度
                    "timestamp": datetime.now().isoformat()
                }

                message = "自动修复完成" if success else "自动修复失败"

            else:
                data = {"fixer_executed": False, "reason": "修复脚本不存在"}
                success = True  # 脚本不不算失败
                message = "跳过自动修复（修复脚本不存在）"

            return MaintenanceTaskResult(
                task=MaintenanceTask.AUTO_FIX,
                status=MaintenanceStatus.COMPLETED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                success=success,
                message=message,
                data=data,
                errors=[]
            )

        except Exception as e:
            return MaintenanceTaskResult(
                task=MaintenanceTask.AUTO_FIX,
                status=MaintenanceStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                success=False,
                message=f"自动修复失败: {str(e)}",
                data={},
                errors=[str(e)]
            )

    async def execute_cleanup(self) -> MaintenanceTaskResult:
        """执行清理任务"""
        start_time = datetime.now()

        try:
            cleaned_files = 0
            cleaned_size = 0

            # 清理旧的覆盖率文件
            coverage_dir = self.project_root / "reports" / "coverage"
            if coverage_dir.exists():
                for file_path in coverage_dir.glob("*.json"):
                    if file_path.stat().st_mtime < time.time() - 7 * 24 * 3600:  # 7天前的文件
                        size = file_path.stat().st_size
                        file_path.unlink()
                        cleaned_files += 1
                        cleaned_size += size

            # 清理旧的报告文件
            reports_dirs = [
                self.project_root / "reports" / "test_health",
                self.project_root / "reports" / "quality_gate",
                self.project_root / "reports" / "coverage_trends"
            ]

            for reports_dir in reports_dirs:
                if reports_dir.exists():
                    for file_path in reports_dir.rglob("*.json"):
                        if file_path.stat().st_mtime < time.time() - 30 * 24 * 3600:  # 30天前的文件
                            size = file_path.stat().st_size
                            file_path.unlink()
                            cleaned_files += 1
                            cleaned_size += size

            data = {
                "cleaned_files": cleaned_files,
                "cleaned_size_mb": round(cleaned_size / (1024 * 1024), 2),
                "timestamp": datetime.now().isoformat()
            }

            message = f"清理完成，删除了 {cleaned_files} 个文件，释放 {data['cleaned_size_mb']} MB 空间"

            return MaintenanceTaskResult(
                task=MaintenanceTask.CLEANUP,
                status=MaintenanceStatus.COMPLETED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                success=True,
                message=message,
                data=data,
                errors=[]
            )

        except Exception as e:
            return MaintenanceTaskResult(
                task=MaintenanceTask.CLEANUP,
                status=MaintenanceStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                success=False,
                message=f"清理任务失败: {str(e)}",
                data={},
                errors=[str(e)]
            )

    async def execute_task(self, task: MaintenanceTask) -> MaintenanceTaskResult:
        """执行指定的维护任务"""
        if task in self.running_tasks:
            raise ValueError(f"任务 {task.value} 正在运行中")

        self.running_tasks[task] = datetime.now()

        try:
            if task == MaintenanceTask.HEALTH_CHECK:
                result = await self.execute_health_check()
            elif task == MaintenanceTask.COVERAGE_ANALYSIS:
                result = await self.execute_coverage_analysis()
            elif task == MaintenanceTask.QUALITY_GATE:
                result = await self.execute_quality_gate()
            elif task == MaintenanceTask.REPORT_GENERATION:
                result = await self.execute_report_generation()
            elif task == MaintenanceTask.AUTO_FIX:
                result = await self.execute_auto_fix()
            elif task == MaintenanceTask.CLEANUP:
                result = await self.execute_cleanup()
            else:
                raise ValueError(f"未知任务: {task}")

            # 保存结果
            self.save_task_result(result)

            return result

        finally:
            if task in self.running_tasks:
                del self.running_tasks[task]

    def should_run_task(self, task: MaintenanceTask) -> bool:
        """检查是否应该运行指定任务"""
        schedule = self.task_schedules.get(task)
        if not schedule or not schedule["enabled"]:
            return False

        if schedule["last_run"] is None:
            return True

        time_since_last = datetime.now() - schedule["last_run"]
        return time_since_last.total_seconds() >= schedule["interval"]

    async def run_scheduler(self):
        """运行任务调度器"""
        print("🤖 测试维护自动化系统启动")
        print(f"📋 项目路径: {self.project_root}")
        print(f"⚙️  配置: 健康检查间隔={self.config.health_check_interval}s,
    覆盖率分析间隔={self.config.coverage_analysis_interval}s")

        while not self.shutdown_requested:
            try:
                current_time = datetime.now()
                tasks_to_run = []

                # 检查哪些任务需要运行
                for task in MaintenanceTask:
                    if self.should_run_task(task):
                        tasks_to_run.append(task)

                # 执行任务
                if tasks_to_run:
                    print(f"🕐 {current_time.strftime('%H:%M:%S')} - 执行维护任务: {[t.value for t in tasks_to_run]}")

                    for task in tasks_to_run:
                        try:
                            print(f"   📋 开始执行: {task.value}")
                            result = await self.execute_task(task)

                            if result.success:
                                print(f"   ✅ {task.value} 完成: {result.message}")
                            else:
                                print(f"   ❌ {task.value} 失败: {result.message}")

                            # 更新调度时间
                            self.task_schedules[task]["last_run"] = current_time

                        except Exception as e:
                            print(f"   🚨 {task.value} 异常: {str(e)}")

                # 等待一段时间再检查
                await asyncio.sleep(60)  # 每分钟检查一次

            except KeyboardInterrupt:
                print("\n🛑 收到中断信号，正在关闭...")
                break
            except Exception as e:
                print(f"🚨 调度器异常: {str(e)}")
                await asyncio.sleep(60)

        print("👋 测试维护自动化系统已关闭")

    async def run_manual_task(self, task_name: str) -> MaintenanceTaskResult:
        """手动执行指定任务"""
        try:
            task = MaintenanceTask(task_name)
            print(f"🔧 手动执行任务: {task.value}")
            result = await self.execute_task(task)

            if result.success:
                print(f"✅ 任务完成: {result.message}")
            else:
                print(f"❌ 任务失败: {result.message}")

            return result

        except ValueError:
            print(f"❌ 未知任务: {task_name}")
            return MaintenanceTaskResult(
                task=MaintenanceTask.HEALTH_CHECK,  # 默认任务
                status=MaintenanceStatus.FAILED,
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration=0,
                success=False,
                message=f"未知任务: {task_name}",
                data={},
                errors=[f"未知任务: {task_name}"]
            )
        except Exception as e:
            print(f"🚨 任务执行异常: {str(e)}")
            return MaintenanceTaskResult(
                task=MaintenanceTask.HEALTH_CHECK,  # 默认任务
                status=MaintenanceStatus.FAILED,
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration=0,
                success=False,
                message=f"任务执行异常: {str(e)}",
                data={},
                errors=[str(e)]
            )

    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        now = datetime.now()

        # 统计最近24小时的任务结果
        recent_tasks = [t for t in self.task_history
                       if (now - t.start_time).total_seconds() < 24 * 3600]

        successful_tasks = len([t for t in recent_tasks if t.success])
        failed_tasks = len([t for t in recent_tasks if not t.success])

        # 计算下次运行时间
        next_runs = {}
        for task, schedule in self.task_schedules.items():
            if schedule["enabled"]:
                if schedule["last_run"]:
                    next_run = schedule["last_run"] + timedelta(seconds=schedule["interval"])
                    next_runs[task.value] = next_run.strftime("%H:%M:%S")
                else:
                    next_runs[task.value] = "立即"

        return {
            "current_status": self.current_status.value,
            "running_tasks": [t.value for t in self.running_tasks.keys()],
            "recent_tasks_24h": {
                "total": len(recent_tasks),
                "successful": successful_tasks,
                "failed": failed_tasks,
                "success_rate": (successful_tasks / len(recent_tasks) * 100) if recent_tasks else 0
            },
            "next_runs": next_runs,
            "total_history": len(self.task_history),
            "uptime": "运行中" if not self.shutdown_requested else "已停止"
        }

    def shutdown(self):
        """关闭自动化系统"""
        print("🛑 正在关闭测试维护自动化系统...")
        self.shutdown_requested = True

async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="测试维护自动化系统")
    parser.add_argument(
        "--project-root",
        type=Path,
        help="项目根目录路径"
    )
    parser.add_argument(
        "--task",
        choices=[t.value for t in MaintenanceTask],
        help="手动执行指定任务"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="显示系统状态"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="以守护进程模式运行"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="配置文件路径"
    )

    args = parser.parse_args()

    # 创建自动化系统实例
    project_root = args.project_root or Path(__file__).parent.parent.parent

    # 加载配置
    config = MaintenanceConfig()
    if args.config and args.config.exists():
        try:
            with open(args.config, 'r') as f:
                config_data = json.load(f)
                config = MaintenanceConfig(**config_data)
        except Exception as e:
            print(f"⚠️ 配置文件加载失败，使用默认配置: {e}")

    automation = TestMaintenanceAutomation(project_root, config)

    try:
        if args.status:
            # 显示状态
            summary = automation.get_status_summary()
            print("📊 测试维护自动化系统状态:")
            print(f"   当前状态: {summary['current_status']}")
            print(f"   运行中任务: {',
    '.join(summary['running_tasks']) if summary['running_tasks'] else '无'}")
            print(f"   24小时任务统计: {summary['recent_tasks_24h']['total']}个任务,
    成功率{summary['recent_tasks_24h']['success_rate']:.1f}%")
            print(f"   系统状态: {summary['uptime']}")

            print("\n⏰ 下次运行时间:")
            for task, next_time in summary['next_runs'].items():
                print(f"   {task}: {next_time}")

        elif args.task:
            # 手动执行任务
            result = await automation.run_manual_task(args.task)
            if result.data:
                print(f"\n📋 任务结果数据:")
                for key, value in result.data.items():
                    print(f"   {key}: {value}")

        elif args.daemon:
            # 守护进程模式
            print("🚀 启动守护进程模式...")
            await automation.run_scheduler()

        else:
            # 默认运行一次完整的维护流程
            print("🔧 执行一次性维护流程...")

            tasks = [
                MaintenanceTask.HEALTH_CHECK,
                MaintenanceTask.COVERAGE_ANALYSIS,
                MaintenanceTask.QUALITY_GATE,
                MaintenanceTask.REPORT_GENERATION
            ]

            for task in tasks:
                print(f"\n📋 执行任务: {task.value}")
                result = await automation.execute_task(task)

                if result.success:
                    print(f"✅ {result.message}")
                else:
                    print(f"❌ {result.message}")
                    if result.errors:
                        for error in result.errors:
                            print(f"   🚨 {error}")

            print(f"\n🎉 维护流程完成！")

    except KeyboardInterrupt:
        print("\n👋 用户中断，退出程序")
        automation.shutdown()
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        automation.shutdown()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
