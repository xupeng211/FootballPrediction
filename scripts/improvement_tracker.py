#!/usr/bin/env python3
"""
技术债务改进进度追踪器
文件: scripts/improvement_tracker.py

用法:
    python scripts/improvement_tracker.py status    # 查看当前状态
    python scripts/improvement_tracker.py start 1.1 # 开始任务1.1
    python scripts/improvement_tracker.py done 1.1  # 完成任务1.1
    python scripts/improvement_tracker.py report    # 生成周报
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 任务定义
TASKS = {
    "1.1": {
        "name": "修复CORS安全配置",
        "phase": "紧急修复",
        "week": 1,
        "hours": 2,
        "priority": "🔴 高",
        "script": "scripts/cleanup/fix_cors.sh",
    },
    "1.2": {
        "name": "清理遗留代码目录",
        "phase": "紧急修复",
        "week": 1,
        "hours": 4,
        "priority": "🔴 高",
        "script": "scripts/cleanup/remove_legacy_code.sh",
    },
    "1.3": {
        "name": "删除print语句",
        "phase": "紧急修复",
        "week": 1,
        "hours": 8,
        "priority": "🟡 中",
        "script": "scripts/cleanup/replace_print_with_logger.py",
    },
    "2.1": {
        "name": "简化依赖管理",
        "phase": "依赖优化",
        "week": 2,
        "hours": 6,
        "priority": "📦 高",
        "script": "scripts/cleanup/simplify_requirements.sh",
    },
    "2.2": {
        "name": "统一Docker配置",
        "phase": "配置优化",
        "week": 2,
        "hours": 6,
        "priority": "🐳 中",
        "script": None,
    },
    "3.1": {
        "name": "API层测试(29%→55%)",
        "phase": "测试提升",
        "week": "5-6",
        "hours": 20,
        "priority": "🧪 高",
        "script": None,
    },
    "3.2": {
        "name": "服务层测试(55%→85%)",
        "phase": "测试提升",
        "week": "7-8",
        "hours": 20,
        "priority": "🧪 高",
        "script": None,
    },
    "4.1": {
        "name": "拆分超大文件",
        "phase": "代码重构",
        "week": "9-10",
        "hours": 32,
        "priority": "🔨 中",
        "script": None,
    },
    "5.1": {
        "name": "完善类型注解",
        "phase": "质量提升",
        "week": "11-12",
        "hours": 40,
        "priority": "✨ 中",
        "script": "scripts/quality/fix_type_ignores.py",
    },
}

# 状态文件
STATUS_FILE = ".improvement_status.json"


class ImprovementTracker:
    """改进进度追踪器"""

    def __init__(self):
        self.status = self.load_status()

    def load_status(self) -> Dict:
        """加载状态"""
        if Path(STATUS_FILE).exists():
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "start_date": datetime.now().isoformat(),
            "current_week": 1,
            "tasks": {},
            "metrics": self.collect_metrics(),
        }

    def save_status(self):
        """保存状态"""
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.status, f, indent=2, ensure_ascii=False)

    def collect_metrics(self) -> Dict:
        """收集当前指标"""
        metrics = {}

        try:
            # 遗留代码目录
            result = subprocess.run(
                ["find", "src", "-name", "*_mod", "-o", "-name", "*_legacy"],
                capture_output=True,
                text=True,
                check=False,
            )
            metrics["legacy_dirs"] = len(
                [line for line in result.stdout.split("\n") if line]
            )

            # 备份文件
            result = subprocess.run(
                ["find", "src", "-name", "*.bak"],
                capture_output=True,
                text=True,
                check=False,
            )
            metrics["backup_files"] = len(
                [line for line in result.stdout.split("\n") if line]
            )

            # type: ignore
            result = subprocess.run(
                ["grep", "-r", "# type: ignore", "src", "--include=*.py"],
                capture_output=True,
                text=True,
                check=False,
            )
            metrics["type_ignores"] = len(result.stdout.split("\n")) - 1

            # print语句
            result = subprocess.run(
                ["grep", "-r", "print(", "src", "--include=*.py"],
                capture_output=True,
                text=True,
                check=False,
            )
            print_lines = result.stdout.split("\n")
            metrics["print_statements"] = len(
                [
                    line
                    for line in print_lines
                    if l and "pprint" not in l and "logger" not in l
                ]
            )

            # 测试覆盖率 - 需要运行pytest
            # metrics["coverage"] = "需运行 make coverage"

        except Exception as e:
            print(f"⚠️  收集指标时出错: {e}")

        metrics["collected_at"] = datetime.now().isoformat()
        return metrics

    def show_status(self):
        """显示当前状态"""
        print("📊 技术债务改进进度\n")
        print(f"开始时间: {self.status['start_date'][:10]}")
        print(f"当前周: Week {self.status['current_week']}")
        print()

        # 显示指标
        print("📈 当前指标:")
        metrics = self.status.get("metrics", {})
        start_metrics = {
            "legacy_dirs": 17,
            "backup_files": 12,
            "type_ignores": 1851,
            "print_statements": 300,
        }

        for key, target in [
            ("legacy_dirs", 0),
            ("backup_files", 0),
            ("type_ignores", 100),
            ("print_statements", 0),
        ]:
            current = metrics.get(key, start_metrics[key])
            start = start_metrics[key]
            if start > 0:
                progress = ((start - current) / start) * 100
            else:
                progress = 100 if current == 0 else 0

            status_icon = (
                "✅" if current <= target else "🔄" if current < start else "❌"
            )
            print(
                f"  {status_icon} {key}: {current} (起始: {start}, 目标: {target}) - {progress:.1f}%"
            )

        print()

        # 显示任务状态
        print("📋 任务进度:\n")

        completed = []
        in_progress = []
        pending = []

        for task_id, task in TASKS.items():
            status = self.status["tasks"].get(task_id, {})
            task_status = status.get("status", "pending")

            task_info = f"{task_id}. {task['name']} (Week {task['week']}, {task['hours']}h) {task['priority']}"

            if task_status == "completed":
                completed.append(task_info)
            elif task_status == "in_progress":
                in_progress.append(task_info)
            else:
                pending.append(task_info)

        if in_progress:
            print("🔄 进行中:")
            for task in in_progress:
                print(f"  {task}")
            print()

        if completed:
            print(f"✅ 已完成 ({len(completed)}/{len(TASKS)}):")
            for task in completed:
                print(f"  {task}")
            print()

        if pending:
            print(f"⏳ 待开始 ({len(pending)}/{len(TASKS)}):")
            for task in pending[:5]:
                print(f"  {task}")
            if len(pending) > 5:
                print(f"  ... 还有 {len(pending) - 5} 个任务")
            print()

        # 计算总体进度
        total_hours = sum(t["hours"] for t in TASKS.values())
        completed_hours = sum(
            TASKS[tid]["hours"]
            for tid, status in self.status["tasks"].items()
            if status.get("status") == "completed"
        )
        overall_progress = (completed_hours / total_hours) * 100

        print(
            f"📊 总体进度: {overall_progress:.1f}% ({completed_hours}/{total_hours}小时)"
        )

        # 下一步建议
        print("\n💡 下一步建议:")
        next_tasks = [
            task_id
            for task_id in sorted(TASKS.keys())
            if self.status["tasks"].get(task_id, {}).get("status") == "pending"
        ]
        if next_tasks:
            next_id = next_tasks[0]
            next_task = TASKS[next_id]
            print(f"  开始任务 {next_id}: {next_task['name']}")
            print(f"  预计时间: {next_task['hours']}小时")
            if next_task["script"]:
                print(f"  执行脚本: {next_task['script']}")
            print(f"\n  命令: python scripts/improvement_tracker.py start {next_id}")
        else:
            print("  🎉 所有任务已完成！")

    def start_task(self, task_id: str):
        """开始任务"""
        if task_id not in TASKS:
            print(f"❌ 任务 {task_id} 不存在")
            return

        task = TASKS[task_id]

        # 更新状态
        if task_id not in self.status["tasks"]:
            self.status["tasks"][task_id] = {}

        self.status["tasks"][task_id].update(
            {
                "status": "in_progress",
                "started_at": datetime.now().isoformat(),
            }
        )
        self.save_status()

        print(f"🚀 开始任务 {task_id}: {task['name']}")
        print(f"   阶段: {task['phase']}")
        print(f"   预计时间: {task['hours']}小时")
        print(f"   优先级: {task['priority']}")
        print()

        if task["script"]:
            print(f"📜 执行脚本: {task['script']}")
            print()

            script_path = Path(task["script"])
            if script_path.exists():
                print("✅ 脚本存在，请手动执行:")
                print(f"   {task['script']}")
            else:
                print("⚠️  脚本文件不存在，请参考方案文档手动执行")
        else:
            print("📝 此任务需要手动执行，请参考方案文档")

        print()
        print(f"完成后运行: python scripts/improvement_tracker.py done {task_id}")

    def complete_task(self, task_id: str, notes: Optional[str] = None):
        """完成任务"""
        if task_id not in TASKS:
            print(f"❌ 任务 {task_id} 不存在")
            return

        if task_id not in self.status["tasks"]:
            self.status["tasks"][task_id] = {}

        # 收集最新指标
        new_metrics = self.collect_metrics()

        self.status["tasks"][task_id].update(
            {
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "notes": notes,
                "metrics_after": new_metrics,
            }
        )

        self.status["metrics"] = new_metrics
        self.save_status()

        task = TASKS[task_id]
        print(f"✅ 任务完成: {task_id}. {task['name']}")
        print(f"   耗时: {task['hours']}小时（预估）")

        if notes:
            print(f"   备注: {notes}")

        # 显示指标变化
        print("\n📊 指标变化:")
        for key in ["legacy_dirs", "backup_files", "type_ignores", "print_statements"]:
            if key in new_metrics:
                print(f"   {key}: {new_metrics[key]}")

        print()
        self.show_status()

    def generate_report(self):
        """生成周报"""
        print("📄 技术债务改进周报\n")
        print(f"时间范围: Week {self.status['current_week']}")
        print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print()

        # 本周完成的任务
        completed_this_week = [
            (tid, task, self.status["tasks"][tid])
            for tid, task in TASKS.items()
            if tid in self.status["tasks"]
            and self.status["tasks"][tid].get("status") == "completed"
            and task["week"] == self.status["current_week"]
        ]

        if completed_this_week:
            print(f"✅ 本周完成 ({len(completed_this_week)}个任务):\n")
            for tid, task, status in completed_this_week:
                print(f"  {tid}. {task['name']}")
                print(f"     预计: {task['hours']}h")
                if status.get("notes"):
                    print(f"     备注: {status['notes']}")
                print()

        # 指标对比
        print("📊 指标变化:\n")
        metrics = self.status.get("metrics", {})
        start_metrics = {
            "legacy_dirs": 17,
            "backup_files": 12,
            "type_ignores": 1851,
            "print_statements": 300,
        }

        print("| 指标 | 初始 | 当前 | 目标 | 进度 |")
        print("|------|------|------|------|------|")
        for key, start in start_metrics.items():
            current = metrics.get(key, start)
            target = 0 if key != "type_ignores" else 100
            progress = ((start - current) / max(start - target, 1)) * 100
            print(f"| {key} | {start} | {current} | {target} | {progress:.1f}% |")

        print()

        # 下周计划
        print("📅 下周计划:\n")
        next_week = self.status["current_week"] + 1
        next_tasks = [
            (tid, task)
            for tid, task in TASKS.items()
            if task["week"] == next_week
            or (isinstance(task["week"], str) and str(next_week) in task["week"])
        ]

        if next_tasks:
            for tid, task in next_tasks:
                print(f"  {tid}. {task['name']} ({task['hours']}h)")
        else:
            print("  暂无任务计划")


def main():
    """主函数"""
    import sys

    tracker = ImprovementTracker()

    if len(sys.argv) < 2:
        tracker.show_status()
        return

    command = sys.argv[1]

    if command == "status":
        tracker.show_status()
    elif command == "start":
        if len(sys.argv) < 3:
            print("❌ 请指定任务ID: python scripts/improvement_tracker.py start 1.1")
            return
        task_id = sys.argv[2]
        tracker.start_task(task_id)
    elif command == "done":
        if len(sys.argv) < 3:
            print("❌ 请指定任务ID: python scripts/improvement_tracker.py done 1.1")
            return
        task_id = sys.argv[2]
        notes = sys.argv[3] if len(sys.argv) > 3 else None
        tracker.complete_task(task_id, notes)
    elif command == "report":
        tracker.generate_report()
    else:
        print(f"❌ 未知命令: {command}")
        print("\n用法:")
        print("  python scripts/improvement_tracker.py status    # 查看状态")
        print("  python scripts/improvement_tracker.py start 1.1 # 开始任务")
        print("  python scripts/improvement_tracker.py done 1.1  # 完成任务")
        print("  python scripts/improvement_tracker.py report    # 生成报告")


if __name__ == "__main__":
    main()
