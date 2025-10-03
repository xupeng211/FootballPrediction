#!/usr/bin/env python3
"""
依赖解决任务看板
类似Notion风格的任务管理系统
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum

class TaskStatus(Enum):
    TODO = "待处理"
    IN_PROGRESS = "进行中"
    DONE = "已完成"
    BLOCKED = "阻塞"
    CANCELLED = "取消"

class TaskPriority(Enum):
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    URGENT = "紧急"

@dataclass
class Task:
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee: str
    estimated_hours: float
    actual_hours: float = 0.0
    dependencies: List[str] = None
    subtasks: List[str] = None
    created_at: str = None
    updated_at: str = None
    tags: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.subtasks is None:
            self.subtasks = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.tags is None:
            self.tags = []

class DependencyTaskBoard:
    def __init__(self, board_file: str = "dependency_task_board.json"):
        self.board_file = board_file
        self.tasks: Dict[str, Task] = {}
        self.load_board()

    def load_board(self):
        """加载任务板"""
        if os.path.exists(self.board_file):
            try:
                with open(self.board_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_id, task_data in data.items():
                        # 转换状态和优先级
                        task_data['status'] = TaskStatus(task_data['status'])
                        task_data['priority'] = TaskPriority(task_data['priority'])
                        self.tasks[task_id] = Task(**task_data)
            except Exception as e:
                print(f"加载任务板失败: {e}")
                self.initialize_board()
        else:
            self.initialize_board()

    def save_board(self):
        """保存任务板"""
        data = {}
        for task_id, task in self.tasks.items():
            task_dict = asdict(task)
            # 转换枚举为字符串
            task_dict['status'] = task.status.value
            task_dict['priority'] = task.priority.value
            data[task_id] = task_dict

        with open(self.board_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def initialize_board(self):
        """初始化任务板"""
        # Phase 1: 诊断与分析
        self.add_task(Task(
            id="PH1-1",
            title = os.getenv("TASK_BOARD_TITLE_96"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_96"),
            status=TaskStatus.TODO,
            priority=TaskPriority.URGENT,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=1.0,
            tags=["diagnosis", "tooling"]
        ))

        self.add_task(Task(
            id="PH1-2",
            title = os.getenv("TASK_BOARD_TITLE_105"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_106"),
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=0.5,
            dependencies=["PH1-1"],
            tags=["diagnosis", "analysis"]
        ))

        self.add_task(Task(
            id="PH1-3",
            title = os.getenv("TASK_BOARD_TITLE_114"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_114"),
            status=TaskStatus.TODO,
            priority=TaskPriority.URGENT,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=1.0,
            dependencies=["PH1-2"],
            tags=["conflict", "analysis"]
        ))

        self.add_task(Task(
            id="PH1-4",
            title = os.getenv("TASK_BOARD_TITLE_124"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_125"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=1.5,
            dependencies=["PH1-3"],
            tags=["compatibility", "matrix"]
        ))

        # Phase 2: 紧急修复
        self.add_task(Task(
            id="PH2-1",
            title = os.getenv("TASK_BOARD_TITLE_135"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_135"),
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=0.5,
            dependencies=["PH1-4"],
            tags=["backup", "safety"]
        ))

        self.add_task(Task(
            id="PH2-2",
            title = os.getenv("TASK_BOARD_TITLE_146"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_147"),
            status=TaskStatus.TODO,
            priority=TaskPriority.URGENT,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=0.5,
            dependencies=["PH2-1"],
            tags=["environment", "clean"]
        ))

        self.add_task(Task(
            id="PH2-3",
            title = os.getenv("TASK_BOARD_TITLE_157"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_157"),
            status=TaskStatus.TODO,
            priority=TaskPriority.URGENT,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=2.0,
            dependencies=["PH2-2"],
            tags=["fix", "conflict"]
        ))

        self.add_task(Task(
            id="PH2-4",
            title = os.getenv("TASK_BOARD_TITLE_167"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_168"),
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=1.0,
            dependencies=["PH2-3"],
            tags=["validation", "testing"]
        ))

        # Phase 3: 自动化工具建设
        self.add_task(Task(
            id="PH3-1",
            title = os.getenv("TASK_BOARD_TITLE_178"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_179"),
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=3.0,
            dependencies=["PH2-4"],
            tags=["automation", "detection"]
        ))

        self.add_task(Task(
            id="PH3-2",
            title = os.getenv("TASK_BOARD_TITLE_186"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_187"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=2.0,
            dependencies=["PH3-1"],
            tags=["CI", "automation"]
        ))

        self.add_task(Task(
            id="PH3-3",
            title = os.getenv("TASK_BOARD_TITLE_197"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_197"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=3.0,
            dependencies=["PH3-2"],
            tags=["dashboard", "monitoring"]
        ))

        self.add_task(Task(
            id="PH3-4",
            title = os.getenv("TASK_BOARD_TITLE_207"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_208"),
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=1.0,
            dependencies=["PH3-3"],
            tags=["report", "automation"]
        ))

        # Phase 4: 预防机制
        self.add_task(Task(
            id="PH4-1",
            title = os.getenv("TASK_BOARD_TITLE_218"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_219"),
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=2.0,
            dependencies=["PH3-4"],
            tags=["strategy", "locking"]
        ))

        self.add_task(Task(
            id="PH4-2",
            title = os.getenv("TASK_BOARD_TITLE_229"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_229"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=1.5,
            dependencies=["PH4-1"],
            tags=["management", "process"]
        ))

        self.add_task(Task(
            id="PH4-3",
            title = os.getenv("TASK_BOARD_TITLE_237"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_239"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=1.0,
            dependencies=["PH4-2"],
            tags=["process", "standardization"]
        ))

        self.add_task(Task(
            id="PH4-4",
            title="文档和培训",
            description = os.getenv("TASK_BOARD_DESCRIPTION_248"),
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=1.0,
            dependencies=["PH4-3"],
            tags=["documentation", "training"]
        ))

        # Phase 5: 验证与优化
        self.add_task(Task(
            id="PH5-1",
            title="端到端测试",
            description = os.getenv("TASK_BOARD_DESCRIPTION_258"),
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=2.0,
            dependencies=["PH4-4"],
            tags=["testing", "E2E"]
        ))

        self.add_task(Task(
            id="PH5-2",
            title = os.getenv("TASK_BOARD_TITLE_268"),
            description = os.getenv("TASK_BOARD_DESCRIPTION_269"),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=1.0,
            dependencies=["PH5-1"],
            tags=["performance", "benchmark"]
        ))

        self.add_task(Task(
            id="PH5-3",
            title="文档更新",
            description = os.getenv("TASK_BOARD_DESCRIPTION_279"),
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=1.0,
            dependencies=["PH5-2"],
            tags=["documentation", "update"]
        ))

        self.add_task(Task(
            id="PH5-4",
            title="团队培训",
            description = os.getenv("TASK_BOARD_DESCRIPTION_291"),
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee = os.getenv("TASK_BOARD_ASSIGNEE_99"),
            estimated_hours=1.0,
            dependencies=["PH5-3"],
            tags=["training", "team"]
        ))

    def add_task(self, task: Task):
        """添加任务"""
        self.tasks[task.id] = task
        self.save_board()

    def update_task(self, task_id: str, **kwargs):
        """更新任务"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = datetime.now().isoformat()
            self.save_board()

    def get_task(self, task_id: str) -> Task:
        """获取任务"""
        return self.tasks.get(task_id)

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """按状态获取任务"""
        return [task for task in self.tasks.values() if task.status == status]

    def get_tasks_by_priority(self, priority: TaskPriority) -> List[Task]:
        """按优先级获取任务"""
        return [task for task in self.tasks.values() if task.priority == priority]

    def get_ready_tasks(self) -> List[Task]:
        """获取可以开始的任务（依赖已完成）"""
        ready_tasks = []
        for task in self.tasks.values():
            if task.status == TaskStatus.TODO:
                dependencies_met = all(
                    self.tasks[dep_id].status == TaskStatus.DONE
                    for dep_id in task.dependencies
                    if dep_id in self.tasks
                )
                if dependencies_met:
                    ready_tasks.append(task)
        return sorted(ready_tasks, key=lambda t: t.priority.value, reverse=True)

    def display_board(self):
        """显示任务板"""
        print("\n" + "="*80)
        print("🎯 依赖解决任务看板")
        print("="*80)

        # 统计信息
        total = len(self.tasks)
        todo = len(self.get_tasks_by_status(TaskStatus.TODO))
        in_progress = len(self.get_tasks_by_status(TaskStatus.IN_PROGRESS))
        done = len(self.get_tasks_by_status(TaskStatus.DONE))
        blocked = len(self.get_tasks_by_status(TaskStatus.BLOCKED))

        print(f"\n📊 总览: {total} 个任务 | ✅ 已完成: {done} | 🔄 进行中: {in_progress} | ⏳ 待处理: {todo} | 🚫 阻塞: {blocked}")

        # 显示当前可以开始的任务
        ready_tasks = self.get_ready_tasks()
        if ready_tasks:
            print("\n🚀 可以开始的任务:")
            for task in ready_tasks[:5]:  # 显示前5个
                print(f"  • [{task.id}] {task.title} ({task.priority.value}) - {task.estimated_hours}h")

        # 按Phase显示
        phases = {
            "PH1": "诊断与分析",
            "PH2": "紧急修复",
            "PH3": "自动化工具建设",
            "PH4": "预防机制",
            "PH5": "验证与优化"
        }

        for phase_id, phase_name in phases.items():
            print(f"\n{phase_id}: {phase_name}")
            print("-" * 60)
            phase_tasks = [t for t in self.tasks.values() if t.id.startswith(phase_id)]

            for task in sorted(phase_tasks, key=lambda t: t.id):
                status_icon = {
                    TaskStatus.TODO: "⏳",
                    TaskStatus.IN_PROGRESS: "🔄",
                    TaskStatus.DONE: "✅",
                    TaskStatus.BLOCKED: "🚫",
                    TaskStatus.CANCELLED: "❌"
                }.get(task.status, "❓")

                priority_icon = {
                    TaskPriority.URGENT: "🔥",
                    TaskPriority.HIGH: "⬆️",
                    TaskPriority.MEDIUM: "➡️",
                    TaskPriority.LOW: "⬇️"
                }.get(task.priority, "")

                print(f"{status_icon} {priority_icon} [{task.id}] {task.title}")
                print(f"    状态: {task.status.value} | 负责人: {task.assignee} | 预估: {task.estimated_hours}h")
                if task.dependencies:
                    print(f"    依赖: {', '.join(task.dependencies)}")
                if task.status == TaskStatus.IN_PROGRESS:
                    progress = min(100, (task.actual_hours / task.estimated_hours) * 100) if task.estimated_hours > 0 else 0
                    print(f"    进度: {progress:.0f}% ({task.actual_hours}/{task.estimated_hours}h)")

    def save_html_report(self, filename: str = "dependency_task_board.html"):
        """生成HTML报告"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>依赖解决任务看板</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .header { text-align: center; margin-bottom: 30px; }
        .stats { display: flex; justify-content: center; gap: 30px; margin-bottom: 30px; }
        .stat-box { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .phase { margin-bottom: 30px; }
        .phase-header { background: #4CAF50; color: white; padding: 10px 20px; border-radius: 8px 8px 0 0; }
        .task { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .task-header { display: flex; justify-content: space-between; align-items: center; }
        .task-title { font-size: 18px; font-weight: bold; }
        .task-meta { color: #666; font-size: 14px; margin-top: 5px; }
        .priority-urgent { border-left: 4px solid #f44336; }
        .priority-high { border-left: 4px solid #ff9800; }
        .priority-medium { border-left: 4px solid #2196f3; }
        .priority-low { border-left: 4px solid #4caf50; }
        .status-todo { opacity: 0.8; }
        .status-inprogress { background: #e3f2fd; }
        .status-done { background: #e8f5e9; text-decoration: line-through; }
        .dependencies { color: #d32f2f; font-size: 12px; margin-top: 5px; }
    </style>
</head>
<body>
    <div class = os.getenv("TASK_BOARD_CLASS_447")>
        <h1>🎯 依赖解决任务看板</h1>
        <p>生成时间: {timestamp}</p>
    </div>

    <div class="stats">
        <div class = os.getenv("TASK_BOARD_CLASS_449")>
            <h3>{total}</h3>
            <p>总任务数</p>
        </div>
        <div class = os.getenv("TASK_BOARD_CLASS_449")>
            <h3>{done}</h3>
            <p>已完成</p>
        </div>
        <div class = os.getenv("TASK_BOARD_CLASS_449")>
            <h3>{in_progress}</h3>
            <p>进行中</p>
        </div>
        <div class = os.getenv("TASK_BOARD_CLASS_449")>
            <h3>{todo}</h3>
            <p>待处理</p>
        </div>
    </div>
""".format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total=len(self.tasks),
            done=len(self.get_tasks_by_status(TaskStatus.DONE)),
            in_progress=len(self.get_tasks_by_status(TaskStatus.IN_PROGRESS)),
            todo=len(self.get_tasks_by_status(TaskStatus.TODO))
        )

        phases = {
            "PH1": "诊断与分析",
            "PH2": "紧急修复",
            "PH3": "自动化工具建设",
            "PH4": "预防机制",
            "PH5": "验证与优化"
        }

        for phase_id, phase_name in phases.items():
            html += f'<div class="phase">\n'
            html += f'<div class = os.getenv("TASK_BOARD_CLASS_463")>{phase_id}: {phase_name}</div>\n'

            phase_tasks = [t for t in self.tasks.values() if t.id.startswith(phase_id)]
            for task in sorted(phase_tasks, key=lambda t: t.id):
                priority_class = f"priority-{task.priority.name.lower()}"
                status_class = f"status-{task.status.name.lower()}"

                html += f'<div class = os.getenv("TASK_BOARD_CLASS_475")>\n'
                html += f'<div class = os.getenv("TASK_BOARD_CLASS_478")>\n'
                html += f'<span class = os.getenv("TASK_BOARD_CLASS_479")>[{task.id}] {task.title}</span>\n'
                html += f'<span>{task.estimated_hours}h</span>\n'
                html += f'</div>\n'
                html += f'<div class = os.getenv("TASK_BOARD_CLASS_486")>\n'
                html += f'状态: {task.status.value} | 负责人: {task.assignee}\n'
                html += f'</div>\n'
                if task.dependencies:
                    html += f'<div class = os.getenv("TASK_BOARD_CLASS_493")>依赖: {", ".join(task.dependencies)}</div>\n'
                html += f'</div>\n'

            html += f'</div>\n'

        html += """
</body>
</html>
"""

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"\n📄 HTML报告已生成: {filename}")

if __name__ == "__main__":
    board = DependencyTaskBoard()
    board.display_board()
    board.save_html_report()