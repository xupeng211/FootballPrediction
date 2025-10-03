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
            title="创建依赖诊断工具",
            description="开发一个全面的依赖诊断工具，能够检测版本冲突、循环依赖等问题",
            status=TaskStatus.TODO,
            priority=TaskPriority.URGENT,
            assignee="AI Assistant",
            estimated_hours=1.0,
            tags=["diagnosis", "tooling"]
        ))

        self.add_task(Task(
            id="PH1-2",
            title="生成完整依赖树",
            description="使用pipdeptree等工具生成项目的完整依赖关系图",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee="AI Assistant",
            estimated_hours=0.5,
            dependencies=["PH1-1"],
            tags=["diagnosis", "analysis"]
        ))

        self.add_task(Task(
            id="PH1-3",
            title="识别冲突源头",
            description="分析依赖树，定位scipy/highspy等具体冲突点",
            status=TaskStatus.TODO,
            priority=TaskPriority.URGENT,
            assignee="AI Assistant",
            estimated_hours=1.0,
            dependencies=["PH1-2"],
            tags=["conflict", "analysis"]
        ))

        self.add_task(Task(
            id="PH1-4",
            title="分析版本兼容性矩阵",
            description="创建各包版本的兼容性矩阵，找出最佳组合",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee="AI Assistant",
            estimated_hours=1.5,
            dependencies=["PH1-3"],
            tags=["compatibility", "matrix"]
        ))

        # Phase 2: 紧急修复
        self.add_task(Task(
            id="PH2-1",
            title="备份当前环境",
            description="使用pip freeze备份当前所有依赖版本",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee="AI Assistant",
            estimated_hours=0.5,
            dependencies=["PH1-4"],
            tags=["backup", "safety"]
        ))

        self.add_task(Task(
            id="PH2-2",
            title="创建干净虚拟环境",
            description="创建全新的Python虚拟环境，避免污染",
            status=TaskStatus.TODO,
            priority=TaskPriority.URGENT,
            assignee="AI Assistant",
            estimated_hours=0.5,
            dependencies=["PH2-1"],
            tags=["environment", "clean"]
        ))

        self.add_task(Task(
            id="PH2-3",
            title="解决关键冲突",
            description="修复scipy/highspy类型注册冲突",
            status=TaskStatus.TODO,
            priority=TaskPriority.URGENT,
            assignee="AI Assistant",
            estimated_hours=2.0,
            dependencies=["PH2-2"],
            tags=["fix", "conflict"]
        ))

        self.add_task(Task(
            id="PH2-4",
            title="验证核心功能",
            description="测试导入和基本功能是否正常",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee="AI Assistant",
            estimated_hours=1.0,
            dependencies=["PH2-3"],
            tags=["validation", "testing"]
        ))

        # Phase 3: 自动化工具建设
        self.add_task(Task(
            id="PH3-1",
            title="开发依赖检测脚本",
            description="创建自动检测依赖冲突的脚本",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee="AI Assistant",
            estimated_hours=3.0,
            dependencies=["PH2-4"],
            tags=["automation", "detection"]
        ))

        self.add_task(Task(
            id="PH3-2",
            title="创建CI检查流程",
            description="在GitHub Actions中添加依赖冲突检查",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee="AI Assistant",
            estimated_hours=2.0,
            dependencies=["PH3-1"],
            tags=["CI", "automation"]
        ))

        self.add_task(Task(
            id="PH3-3",
            title="建立依赖监控仪表板",
            description="创建Web界面展示依赖状态",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee="AI Assistant",
            estimated_hours=3.0,
            dependencies=["PH3-2"],
            tags=["dashboard", "monitoring"]
        ))

        self.add_task(Task(
            id="PH3-4",
            title="设置自动化报告",
            description="定期生成依赖健康报告",
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee="AI Assistant",
            estimated_hours=1.0,
            dependencies=["PH3-3"],
            tags=["report", "automation"]
        ))

        # Phase 4: 预防机制
        self.add_task(Task(
            id="PH4-1",
            title="依赖锁定策略",
            description="制定和实施依赖版本锁定策略",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee="AI Assistant",
            estimated_hours=2.0,
            dependencies=["PH3-4"],
            tags=["strategy", "locking"]
        ))

        self.add_task(Task(
            id="PH4-2",
            title="版本管理规范",
            description="建立包版本更新和管理规范",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee="AI Assistant",
            estimated_hours=1.5,
            dependencies=["PH4-1"],
            tags=["management", "process"]
        ))

        self.add_task(Task(
            id="PH4-3",
            title="更新流程标准化",
            description="标准化依赖更新流程",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee="AI Assistant",
            estimated_hours=1.0,
            dependencies=["PH4-2"],
            tags=["process", "standardization"]
        ))

        self.add_task(Task(
            id="PH4-4",
            title="文档和培训",
            description="编写文档并培训团队",
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee="AI Assistant",
            estimated_hours=1.0,
            dependencies=["PH4-3"],
            tags=["documentation", "training"]
        ))

        # Phase 5: 验证与优化
        self.add_task(Task(
            id="PH5-1",
            title="端到端测试",
            description="运行完整的测试套件验证修复",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            assignee="AI Assistant",
            estimated_hours=2.0,
            dependencies=["PH4-4"],
            tags=["testing", "E2E"]
        ))

        self.add_task(Task(
            id="PH5-2",
            title="性能基准测试",
            description="测试修复后的性能表现",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            assignee="AI Assistant",
            estimated_hours=1.0,
            dependencies=["PH5-1"],
            tags=["performance", "benchmark"]
        ))

        self.add_task(Task(
            id="PH5-3",
            title="文档更新",
            description="更新所有相关文档",
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee="AI Assistant",
            estimated_hours=1.0,
            dependencies=["PH5-2"],
            tags=["documentation", "update"]
        ))

        self.add_task(Task(
            id="PH5-4",
            title="团队培训",
            description="培训团队使用新工具和流程",
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            assignee="AI Assistant",
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
    <div class="header">
        <h1>🎯 依赖解决任务看板</h1>
        <p>生成时间: {timestamp}</p>
    </div>

    <div class="stats">
        <div class="stat-box">
            <h3>{total}</h3>
            <p>总任务数</p>
        </div>
        <div class="stat-box">
            <h3>{done}</h3>
            <p>已完成</p>
        </div>
        <div class="stat-box">
            <h3>{in_progress}</h3>
            <p>进行中</p>
        </div>
        <div class="stat-box">
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
            html += f'<div class="phase-header">{phase_id}: {phase_name}</div>\n'

            phase_tasks = [t for t in self.tasks.values() if t.id.startswith(phase_id)]
            for task in sorted(phase_tasks, key=lambda t: t.id):
                priority_class = f"priority-{task.priority.name.lower()}"
                status_class = f"status-{task.status.name.lower()}"

                html += f'<div class="task {priority_class} {status_class}">\n'
                html += f'<div class="task-header">\n'
                html += f'<span class="task-title">[{task.id}] {task.title}</span>\n'
                html += f'<span>{task.estimated_hours}h</span>\n'
                html += f'</div>\n'
                html += f'<div class="task-meta">\n'
                html += f'状态: {task.status.value} | 负责人: {task.assignee}\n'
                html += f'</div>\n'
                if task.dependencies:
                    html += f'<div class="dependencies">依赖: {", ".join(task.dependencies)}</div>\n'
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