#!/usr/bin/env python3
"""
每日技术债务清理助手
帮助跟踪和执行技术债务清理任务
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class Task:
    def __init__(
        self,
        task_id: str,
        title: str,
        priority: str,
        estimated_time: int,
        status: str = "pending",
    ):
        self.id = task_id
        self.title = title
        self.priority = priority
        self.estimated_time = estimated_time
        self.status = status
        self.created_at = datetime.now()
        self.notes = ""


class TechnicalDebtManager:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.status_file = project_root / ".technical_debt_status.json"
        self.log_file = project_root / "logs" / "debt_cleanup.log"
        self.log_file.parent.mkdir(exist_ok=True)

        self.load_status()

    def load_status(self):
        """加载任务状态"""
        if self.status_file.exists():
            with open(self.status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.current_phase = data.get("current_phase", 1)
                self.completed_tasks = data.get("completed_tasks", [])
                self.current_task = data.get("current_task", None)
                self.daily_stats = data.get("daily_stats", {})
        else:
            self.current_phase = 1
            self.completed_tasks = []
            self.current_task = None
            self.daily_stats = {}

    def save_status(self):
        """保存任务状态"""
        data = {
            "current_phase": self.current_phase,
            "completed_tasks": self.completed_tasks,
            "current_task": self.current_task,
            "daily_stats": self.daily_stats,
            "last_updated": datetime.now().isoformat(),
        }
        with open(self.status_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        print(log_entry.strip())
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

    def get_phase_tasks(self, phase: int) -> List[Task]:
        """获取特定阶段的任务"""
        tasks = []

        if phase == 1:  # Phase 1: 紧急问题修复
            tasks = [
                Task("1.1.1", "修复 E2E 测试语法错误", "P0", 30),
                Task("1.1.2", "修复 Python 脚本变量引用错误", "P0", 15),
                Task("1.1.3", "修复 UTF-8 编码问题", "P0", 45),
                Task("1.2.1", "修复 src/api/data/* star imports", "P1", 30),
                Task("1.2.2", "修复 src/api/features/* star imports", "P1", 30),
                Task("1.2.3", "修复 src/api/health/* star imports", "P1", 30),
                Task("1.2.4", "修复其他模块 star imports", "P1", 60),
                Task("1.3.1", "修复测试文件中的 bare except", "P2", 120),
            ]
        elif phase == 2:  # Phase 2: 核心模块重构
            tasks = [
                Task("2.1.1", "重构 src/api/data.py", "P1", 240),
                Task("2.1.2", "重构 src/api/features.py", "P1", 180),
                Task("2.1.3", "重构 src/api/predictions.py", "P1", 180),
                Task("2.2.1", "整合监控模块 - 合并 alert_manager", "P2", 360),
                Task("2.2.2", "优化指标收集器", "P2", 240),
                Task("2.3.1", "统一缓存实现", "P2", 180),
            ]
        elif phase == 3:  # Phase 3: 测试覆盖率提升
            tasks = [
                Task("3.1.1", "API 端点测试 - data 模块", "P1", 160),
                Task("3.1.2", "API 端点测试 - features 模块", "P1", 120),
                Task("3.1.3", "API 端点测试 - predictions 模块", "P1", 160),
                Task("3.2.1", "服务层测试 - 核心服务", "P1", 480),
                Task("3.2.2", "数据库模型测试", "P1", 240),
                Task("3.3.1", "Utils 模块测试", "P2", 240),
                Task("3.3.2", "收集器测试", "P2", 360),
                Task("3.4.1", "修复 E2E 测试", "P2", 240),
            ]
        elif phase == 4:  # Phase 4: 代码质量优化
            tasks = [
                Task("4.1.1", "添加 MyPy 类型注解 - 公共接口", "P1", 300),
                Task("4.1.2", "添加 MyPy 类型注解 - 复杂函数", "P1", 300),
                Task("4.2.1", "完善 docstring - 公共类和方法", "P2", 360),
                Task("4.2.2", "更新 README 和文档", "P2", 240),
                Task("4.3.1", "数据库查询优化", "P3", 240),
                Task("4.3.2", "缓存策略优化", "P3", 180),
            ]

        # 过滤已完成的任务
        return [t for t in tasks if t.id not in self.completed_tasks]

    def show_daily_plan(self, hours: float = 4.0):
        """显示每日计划"""
        self.log(f"📋 生成每日技术债务清理计划（{hours}小时）")

        # 获取当前阶段的任务
        tasks = self.get_phase_tasks(self.current_phase)

        # 按优先级排序
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        tasks.sort(key=lambda t: priority_order.get(t.priority, 99))

        # 选择任务
        selected_tasks = []
        total_time = 0

        for task in tasks:
            if total_time + task.estimated_time <= hours * 60:
                selected_tasks.append(task)
                total_time += task.estimated_time

        if not selected_tasks:
            self.log("⚠️  没有合适的任务，考虑增加时间或进入下一阶段")
            return

        # 显示计划
        self.log(f"\n🎯 Phase {self.current_phase} 每日任务计划：")
        self.log(f"{'='*60}")

        for i, task in enumerate(selected_tasks, 1):
            self.log(f"\n{i}. [{task.priority}] {task.title}")
            self.log(f"   ⏱️  预计时间: {task.estimated_time}分钟")
            self.log(f"   📝 任务ID: {task.id}")

        self.log(f"\n{'='*60}")
        self.log(f"总预计时间: {total_time}分钟 ({total_time/60:.1f}小时)")

        return selected_tasks

    def start_task(self, task_id: str):
        """开始执行任务"""
        self.current_task = task_id
        self.save_status()
        self.log(f"🚀 开始执行任务: {task_id}")

        # 切换到工作分支
        subprocess.run(
            ["git", "checkout", "wip/technical-debt-and-refactoring"],
            cwd=self.project_root,
            capture_output=True,
        )

        # 创建任务分支
        branch_name = f"fix/task-{task_id.replace('.', '-').replace(' ', '-').lower()}"
        result = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=self.project_root,
            capture_output=True,
        )

        if result.returncode != 0:
            # 分支可能已存在，切换到它
            subprocess.run(
                ["git", "checkout", branch_name],
                cwd=self.project_root,
                capture_output=True,
            )

        self.log(f"📂 已创建/切换到分支: {branch_name}")

    def run_health_check(self):
        """运行健康检查"""
        self.log("🔍 运行代码健康检查...")

        # 运行快速测试
        result = subprocess.run(
            ["make", "test-quick"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            self.log("✅ 快速测试通过")
        else:
            self.log("❌ 快速测试失败")
            self.log(result.stderr)

        # 运行 lint 检查
        result = subprocess.run(
            ["make", "lint"], cwd=self.project_root, capture_output=True, text=True
        )
        if result.returncode == 0:
            self.log("✅ Lint 检查通过")
        else:
            self.log("❌ Lint 检查失败")
            # 统计错误数量
            lines = result.stderr.split("\n")
            errors = [line for line in lines if "error:" in line]
            self.log(f"发现 {len(errors)} 个 lint 错误")

    def complete_task(self, task_id: str, notes: str = ""):
        """完成任务"""
        if task_id not in self.completed_tasks:
            self.completed_tasks.append(task_id)

        # 记录每日统计
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.daily_stats:
            self.daily_stats[today] = {"completed": 0, "time_spent": 0}
        self.daily_stats[today]["completed"] += 1

        self.current_task = None
        self.save_status()

        self.log(f"✅ 任务完成: {task_id}")
        if notes:
            self.log(f"📝 备注: {notes}")

        # 检查是否需要进入下一阶段
        remaining_tasks = self.get_phase_tasks(self.current_phase)
        if not remaining_tasks:
            self.log(f"\n🎉 Phase {self.current_phase} 已全部完成！")
            if self.current_phase < 4:
                self.current_phase += 1
                self.save_status()
                self.log(f"🚀 自动进入 Phase {self.current_phase}")

    def show_progress(self):
        """显示整体进度"""
        self.log("\n📊 技术债务清理进度")
        self.log("=" * 60)

        for phase in range(1, 5):
            tasks = self.get_phase_tasks(phase)
            completed = len([t for t in tasks if t.id in self.completed_tasks])
            total = len(tasks)

            # 包括历史任务
            if phase == 1:
                total = 8  # Phase 1 总任务数
                completed = len([t for t in self.completed_tasks if t.startswith("1.")])
            elif phase == 2:
                total = 6
                completed = len([t for t in self.completed_tasks if t.startswith("2.")])
            elif phase == 3:
                total = 8
                completed = len([t for t in self.completed_tasks if t.startswith("3.")])
            elif phase == 4:
                total = 6
                completed = len([t for t in self.completed_tasks if t.startswith("4.")])

            progress = (completed / total * 100) if total > 0 else 0
            status = (
                "✅"
                if progress == 100
                else "🚧"
                if phase == self.current_phase
                else "⏳"
            )

            self.log(f"{status} Phase {phase}: {completed}/{total} ({progress:.1f}%)")

        self.log("=" * 60)

        # 显示今日统计
        today = datetime.now().strftime("%Y-%m-%d")
        if today in self.daily_stats:
            stats = self.daily_stats[today]
            self.log(f"\n今日完成任务: {stats['completed']} 个")

    def generate_summary(self):
        """生成总结报告"""
        report = f"""
# 技术债务清理总结报告

生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 整体进度
- 当前阶段: Phase {self.current_phase}
- 已完成任务: {len(self.completed_tasks)}
- 完成率: {len(self.completed_tasks) / 28 * 100:.1f}% (总共28个任务)

## 各阶段详情
"""

        for phase in range(1, 5):
            if phase == 1:
                total = 8
                completed = len([t for t in self.completed_tasks if t.startswith("1.")])
            elif phase == 2:
                total = 6
                completed = len([t for t in self.completed_tasks if t.startswith("2.")])
            elif phase == 3:
                total = 8
                completed = len([t for t in self.completed_tasks if t.startswith("3.")])
            elif phase == 4:
                total = 6
                completed = len([t for t in self.completed_tasks if t.startswith("4.")])

            progress = (completed / total * 100) if total > 0 else 0
            report += f"\n### Phase {phase}: {progress:.1f}% ({completed}/{total})\n"

        # 保存报告
        report_file = self.project_root / "DEBT_CLEANUP_SUMMARY.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        self.log(f"📄 总结报告已保存到: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="技术债务清理助手")
    parser.add_argument(
        "command",
        choices=["plan", "start", "check", "done", "progress", "summary", "health"],
        help="执行的命令",
    )
    parser.add_argument("--task", help="任务ID")
    parser.add_argument("--hours", type=float, default=4.0, help="计划工作小时数")
    parser.add_argument("--notes", help="任务备注")

    args = parser.parse_args()

    # 获取项目根目录
    project_root = Path(__file__).parent.parent

    manager = TechnicalDebtManager(project_root)

    if args.command == "plan":
        tasks = manager.show_daily_plan(args.hours)
        if tasks and input("\n是否开始执行第一个任务？(y/n): ").lower() == "y":
            manager.start_task(tasks[0].id)

    elif args.command == "start":
        if not args.task:
            print("错误: 请指定任务ID (--task)")
            sys.exit(1)
        manager.start_task(args.task)

    elif args.command == "check":
        manager.run_health_check()

    elif args.command == "done":
        if not args.task:
            # 完成当前任务
            task_id = manager.current_task
            if not task_id:
                print("错误: 没有正在执行的任务")
                sys.exit(1)
        else:
            task_id = args.task
        manager.complete_task(task_id, args.notes or "")

    elif args.command == "progress":
        manager.show_progress()

    elif args.command == "summary":
        manager.generate_summary()

    elif args.command == "health":
        manager.run_health_check()
        manager.show_progress()


if __name__ == "__main__":
    main()
