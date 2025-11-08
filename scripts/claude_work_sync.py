#!/usr/bin/env python3
"""
Claude Code 作业同步工具
Claude Code Work Synchronization Tool

专门用于将Claude Code的作业内容自动同步到远程GitHub Issues：
- 自动检测作业完成状态
- 生成详细的作业报告
- 使用GitHub CLI自动创建/更新Issues
- 支持多种作业类型（开发、测试、文档等）
- 智能标签分类和里程碑管理

Author: Claude AI Assistant
Date: 2025-11-06
Version: 2.0.0
"""

import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class WorkItem:
    """作业项目数据结构"""
    id: str
    title: str
    description: str
    work_type: str  # 'development', 'testing', 'documentation', 'bugfix', 'feature'
    status: str  # 'pending', 'in_progress', 'completed', 'review'
    priority: str  # 'low', 'medium', 'high', 'critical'
    completion_percentage: int
    started_at: str | None = None
    completed_at: str | None = None
    deliverables: list[str] = None
    technical_details: dict[str, Any] = None
    test_results: dict[str, Any] = None
    files_modified: list[str] = None
    time_spent_minutes: int = 0
    challenges_faced: list[str] = None
    solutions_implemented: list[str] = None
    next_steps: list[str] = None

    def __post_init__(self):
        if self.deliverables is None:
            self.deliverables = []
        if self.technical_details is None:
            self.technical_details = {}
        if self.test_results is None:
            self.test_results = {}
        if self.files_modified is None:
            self.files_modified = []
        if self.challenges_faced is None:
            self.challenges_faced = []
        if self.solutions_implemented is None:
            self.solutions_implemented = []
        if self.next_steps is None:
            self.next_steps = []


class ClaudeWorkSynchronizer:
    """Claude Code作业同步器"""

    def __init__(self, repo: str = "xupeng211/FootballPrediction"):
        self.repo = repo
        self.project_root = Path(__file__).resolve().parent.parent
        self.work_log_file = self.project_root / "claude_work_log.json"
        self.sync_log_file = self.project_root / "claude_sync_log.json"

        # 作业类型映射到GitHub标签 - 使用仓库中实际存在的标签
        self.type_label_map = {
            'development': ['enhancement'],
            'testing': ['enhancement'],
            'documentation': ['documentation'],
            'bugfix': ['bug'],
            'feature': ['enhancement'],
            'optimization': ['performance'],
            'refactoring': ['enhancement'],
            'deployment': ['deployment']
        }

        # 优先级映射到GitHub标签 - 使用仓库中实际存在的标签
        self.priority_label_map = {
            'low': ['medium'],
            'medium': ['medium'],
            'high': ['high', 'priority-high'],
            'critical': ['critical', 'priority-high']
        }

    def run_git_command(self, command: list[str]) -> dict[str, Any]:
        """运行Git命令"""
        try:
            result = subprocess.run(
                ["git"] + command,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=30
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def run_gh_command(self, command: list[str]) -> dict[str, Any]:
        """运行GitHub CLI命令"""
        try:
            result = subprocess.run(
                ["gh"] + command,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=60
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timeout",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def get_git_status(self) -> dict[str, Any]:
        """获取Git状态信息"""
        status = {}

        # 当前分支
        branch_result = self.run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        status["current_branch"] = branch_result["stdout"] if branch_result["success"] else "unknown"

        # 最新提交
        commit_result = self.run_git_command(["log", "--oneline", "-1"])
        status["latest_commit"] = commit_result["stdout"] if commit_result["success"] else "unknown"

        # 未提交的更改
        status_result = self.run_git_command(["status", "--porcelain"])
        status["has_changes"] = len(status_result["stdout"]) > 0 if status_result["success"] else False

        # 修改的文件
        if status["has_changes"]:
            files_result = self.run_git_command(["diff", "--name-only"])
            status["modified_files"] = files_result["stdout"].split('\n') if files_result["success"] else []
        else:
            status["modified_files"] = []

        return status

    def load_work_log(self) -> list[WorkItem]:
        """加载作业日志"""
        if not self.work_log_file.exists():
            return []

        try:
            with open(self.work_log_file, encoding='utf-8') as f:
                data = json.load(f)
                return [WorkItem(**item) for item in data]
        except Exception as e:
            print(f"❌ 加载作业日志失败: {e}")
            return []

    def save_work_log(self, work_items: list[WorkItem]):
        """保存作业日志"""
        try:
            with open(self.work_log_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(item) for item in work_items], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ 保存作业日志失败: {e}")

    def load_sync_log(self) -> dict[str, Any]:
        """加载同步日志"""
        if not self.sync_log_file.exists():
            return {}

        try:
            with open(self.sync_log_file, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载同步日志失败: {e}")
            return {}

    def save_sync_log(self, sync_data: dict[str, Any]):
        """保存同步日志"""
        try:
            with open(self.sync_log_file, 'w', encoding='utf-8') as f:
                json.dump(sync_data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"❌ 保存同步日志失败: {e}")

    def add_work_item(self, work_item: WorkItem):
        """添加新的作业项目"""
        work_items = self.load_work_log()

        # 检查是否已存在
        existing_item = next((item for item in work_items if item.id == work_item.id), None)
        if existing_item:
            # 更新现有项目
            work_items[work_items.index(existing_item)] = work_item
            print(f"📝 更新作业项目: {work_item.id}")
        else:
            # 添加新项目
            work_items.append(work_item)
            print(f"➕ 添加新作业项目: {work_item.id}")

        self.save_work_log(work_items)

    def create_work_item_from_current_work(self,
                                         title: str,
                                         description: str,
                                         work_type: str,
                                         priority: str = "medium") -> WorkItem:
        """从当前工作创建作业项目"""
        work_id = f"claude_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 获取当前Git状态
        git_status = self.get_git_status()

        # 获取修改的文件
        modified_files = []
        if git_status["has_changes"]:
            diff_result = self.run_git_command(["diff", "--name-only", "--cached"])
            if diff_result["success"]:
                modified_files.extend(diff_result["stdout"].split('\n'))

            diff_result = self.run_git_command(["diff", "--name-only"])
            if diff_result["success"]:
                modified_files.extend(diff_result["stdout"].split('\n'))

        work_item = WorkItem(
            id=work_id,
            title=title,
            description=description,
            work_type=work_type,
            status="in_progress",
            priority=priority,
            completion_percentage=0,
            started_at=datetime.now().isoformat(),
            files_modified=list(set(filter(None, modified_files))),
            technical_details={
                "git_branch": git_status["current_branch"],
                "latest_commit": git_status["latest_commit"],
                "has_uncommitted_changes": git_status["has_changes"]
            }
        )

        self.add_work_item(work_item)
        return work_item

    def complete_work_item(self, work_id: str,
                          completion_percentage: int = 100,
                          deliverables: list[str] = None,
                          test_results: dict[str, Any] = None,
                          challenges: list[str] = None,
                          solutions: list[str] = None,
                          next_steps: list[str] = None) -> bool:
        """完成作业项目"""
        work_items = self.load_work_log()

        work_item = next((item for item in work_items if item.id == work_id), None)
        if not work_item:
            print(f"❌ 未找到作业项目: {work_id}")
            return False

        # 更新项目状态
        work_item.status = "completed"
        work_item.completion_percentage = completion_percentage
        work_item.completed_at = datetime.now().isoformat()

        if deliverables:
            work_item.deliverables.extend(deliverables)
        if test_results:
            work_item.test_results.update(test_results)
        if challenges:
            work_item.challenges_faced.extend(challenges)
        if solutions:
            work_item.solutions_implemented.extend(solutions)
        if next_steps:
            work_item.next_steps.extend(next_steps)

        # 计算工作时长
        if work_item.started_at:
            started = datetime.fromisoformat(work_item.started_at)
            completed = datetime.fromisoformat(work_item.completed_at)
            work_item.time_spent_minutes = int((completed - started).total_seconds() / 60)

        self.save_work_log(work_items)
        print(f"✅ 作业项目已完成: {work_id}")
        return True

    def generate_issue_body(self, work_item: WorkItem) -> str:
        """生成GitHub Issue正文"""
        status_emoji = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "review": "👀"
        }

        priority_emoji = {
            "low": "🔵",
            "medium": "🟡",
            "high": "🟠",
            "critical": "🔴"
        }

        body = f"""# {work_item.title}

{status_emoji.get(work_item.status, '❓')} **状态**: {work_item.title} ({work_item.status})
{priority_emoji.get(work_item.priority, '⚪')} **优先级**: {work_item.priority}
📊 **完成度**: {work_item.completion_percentage}%
⏰ **开始时间**: {work_item.started_at or 'N/A'}
{'🏁 **完成时间**: ' + work_item.completed_at if work_item.completed_at else ''}

## 📝 描述

{work_item.description}

## 🏗️ 技术详情

```json
{json.dumps(work_item.technical_details or {}, indent=2, ensure_ascii=False)}
```

## 📁 修改的文件

{chr(10).join(f'- `{file}`' for file in work_item.files_modified) if work_item.files_modified else '无文件修改'}

## 🎯 交付成果

{chr(10).join(f'- {deliverable}' for deliverable in work_item.deliverables) if work_item.deliverables else '待定'}

## 🧪 测试结果

"""

        if work_item.test_results:
            for test_name, test_result in work_item.test_results.items():
                body += f"### {test_name}\n"
                if isinstance(test_result, dict):
                    body += "```json\n" + json.dumps(test_result, indent=2, ensure_ascii=False) + "\n```\n\n"
                else:
                    body += f"{test_result}\n\n"
        else:
            body += "暂无测试结果\n\n"

        body += "## ⚠️ 遇到的挑战\n\n"
        if work_item.challenges_faced:
            body += chr(10).join(f"- {challenge}" for challenge in work_item.challenges_faced)
        else:
            body += "无重大挑战"

        body += "\n\n## 💡 实施的解决方案\n\n"
        if work_item.solutions_implemented:
            body += chr(10).join(f"- {solution}" for solution in work_item.solutions_implemented)
        else:
            body += "待记录"

        body += "\n\n## 📋 后续步骤\n\n"
        if work_item.next_steps:
            body += chr(10).join(f"- {step}" for step in work_item.next_steps)
        else:
            body += "无后续步骤"

        if work_item.time_spent_minutes > 0:
            hours = work_item.time_spent_minutes // 60
            minutes = work_item.time_spent_minutes % 60
            body += f"\n\n## ⏱️ 工作时长\n\n总计: {hours}小时{minutes}分钟 ({work_item.time_spent_minutes}分钟)"

        body += f"""

---

🤖 **自动生成于**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔧 **工具**: Claude Work Synchronizer v2.0.0
📊 **作业ID**: {work_item.id}
🏷️ **类型**: {work_item.work_type}

*此Issue由Claude Code自动创建和管理*
"""

        return body

    def create_or_update_github_issue(self, work_item: WorkItem) -> dict[str, Any]:
        """创建或更新GitHub Issue"""

        # 准备标签
        labels = []

        # 添加类型标签
        if work_item.work_type in self.type_label_map:
            labels.extend(self.type_label_map[work_item.work_type])

        # 添加优先级标签
        if work_item.priority in self.priority_label_map:
            labels.extend(self.priority_label_map[work_item.priority])

        # 添加状态标签 - 使用仓库中实际存在的标签或跳过
        status_labels = {
            "pending": None,  # 暂时跳过，仓库中没有对应标签
            "in_progress": None,  # 暂时跳过，仓库中没有对应标签
            "completed": "resolved",  # 使用resolved标签表示已完成
            "review": None  # 暂时跳过，仓库中没有对应标签
        }
        if work_item.status in status_labels and status_labels[work_item.status]:
            labels.append(status_labels[work_item.status])

        # 添加Claude相关标签 - 暂时跳过不存在的标签
        # labels.append("claude-code")  # 仓库中不存在
        # labels.append("automated")  # 仓库中不存在

        # 检查是否已存在相同标题的Issue
        search_result = self.run_gh_command([
            "issue", "list",
            "--repo", self.repo,
            "--search", work_item.title,
            "--limit", "10",  # 增加limit以确保找到所有可能的匹配项
            "--json", "number,title,state"
        ])

        issue_number = None
        action = "created"

        if search_result["success"] and search_result["stdout"]:
            try:
                issues = json.loads(search_result["stdout"])
                if issues:
                    # 找到已存在的Issue
                    existing_issue = issues[0]
                    issue_number = existing_issue["number"]

                    # 如果状态已变为完成，关闭Issue
                    if work_item.status == "completed" and existing_issue["state"].lower() == "open":
                        # 添加评论
                        body = self.generate_issue_body(work_item)
                        comment_result = self.run_gh_command([
                            "issue", "comment", str(issue_number),
                            "--body", body
                        ])

                        if comment_result["success"]:
                            # 关闭Issue
                            close_result = self.run_gh_command([
                                "issue", "close", str(issue_number),
                                "--reason", "completed"
                            ])

                            if close_result["success"]:
                                action = "completed_and_closed"
                            else:
                                action = "commented"
                        else:
                            action = "failed_to_comment"

                    elif existing_issue["state"].lower() == "open":
                        # 更新Issue
                        body = self.generate_issue_body(work_item)
                        comment_result = self.run_gh_command([
                            "issue", "comment", str(issue_number),
                            "--body", body
                        ])

                        if comment_result["success"]:
                            action = "updated"
                        else:
                            action = "failed_to_update"
                    else:
                        action = "already_closed"

            except json.JSONDecodeError:
                pass

        # 创建新Issue
        if issue_number is None:
            body = self.generate_issue_body(work_item)
            # 构建命令，每个标签需要单独的--label参数
            cmd = [
                "issue", "create",
                "--repo", self.repo,
                "--title", work_item.title,
                "--body", body
            ]
            # 为每个标签添加--label参数
            for label in labels:
                cmd.extend(["--label", label])

            create_result = self.run_gh_command(cmd)

            if create_result["success"]:
                # 提取Issue号码
                output = create_result["stdout"]
                if "https://github.com/" in output:
                    issue_url = output.strip().split('\n')[-1]
                    issue_number = issue_url.split('/')[-1]
                    action = "created"
                else:
                    action = "created_url_unknown"
            else:
                action = "failed_to_create"

        return {
            "success": action in ["created", "updated", "completed_and_closed", "already_closed"],
            "action": action,
            "issue_number": issue_number,
            "labels": labels
        }

    def sync_all_work_items(self) -> dict[str, Any]:
        """同步所有作业项目到GitHub Issues"""
        print("🚀 开始同步Claude Code作业到GitHub Issues")
        print("=" * 80)

        # 检查GitHub CLI认证
        print("🔍 检查GitHub CLI认证...")
        auth_check = self.run_gh_command(["auth", "status"])
        if not auth_check["success"]:
            print("❌ GitHub CLI未认证，请先运行: gh auth login")
            return {"success": False, "error": "GitHub CLI not authenticated"}

        print("✅ GitHub CLI认证成功")

        # 加载作业项目
        work_items = self.load_work_log()
        if not work_items:
            print("📝 没有找到作业项目")
            return {"success": True, "message": "No work items found"}

        print(f"📋 找到 {len(work_items)} 个作业项目")

        results = {
            "total_items": len(work_items),
            "sync_results": [],
            "successful_syncs": 0,
            "failed_syncs": 0,
            "sync_timestamp": datetime.now().isoformat()
        }

        for i, work_item in enumerate(work_items, 1):
            print(f"\n📝 [{i}/{len(work_items)}] 处理作业项目: {work_item.id}")
            print(f"   标题: {work_item.title}")
            print(f"   状态: {work_item.status} ({work_item.completion_percentage}%)")

            sync_result = self.create_or_update_github_issue(work_item)
            results["sync_results"].append({
                "work_id": work_item.id,
                "title": work_item.title,
                "result": sync_result
            })

            if sync_result["success"]:
                results["successful_syncs"] += 1
                action_desc = {
                    "created": "✅ 创建新Issue",
                    "updated": "🔄 更新Issue",
                    "completed_and_closed": "✅ 完成并关闭Issue",
                    "already_closed": "ℹ️ Issue已关闭"
                }
                print(f"   {action_desc.get(sync_result['action'], '✅ 处理成功')}")
                if sync_result.get("issue_number"):
                    print(f"   Issue #{sync_result['issue_number']}")
            else:
                results["failed_syncs"] += 1
                print(f"   ❌ 同步失败: {sync_result.get('action', 'Unknown error')}")

            # 添加延迟避免API限制
            if i < len(work_items):
                time.sleep(2)

        # 生成同步报告
        self.generate_sync_report(results)

        # 保存同步记录
        sync_log = self.load_sync_log()
        sync_log[datetime.now().isoformat()] = results
        self.save_sync_log(sync_log)

        # 输出总结
        self.print_sync_summary(results)

        # 添加success键用于主函数判断
        results["success"] = True
        return results

    def generate_sync_report(self, results: dict[str, Any]):
        """生成同步报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.project_root / "reports" / f"claude_sync_report_{timestamp}.md"

        report_file.parent.mkdir(parents=True, exist_ok=True)

        report_content = f"""# Claude Code 作业同步报告

## 📊 同步统计

- **同步时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **总作业项目**: {results['total_items']}
- **成功同步**: {results['successful_syncs']}
- **同步失败**: {results['failed_syncs']}
- **成功率**: {(results['successful_syncs'] / results['total_items'] * 100):.1f}%

## 📋 详细结果

"""

        for sync_result in results["sync_results"]:
            work_item = sync_result
            result = work_item["result"]

            status_emoji = "✅" if result["success"] else "❌"
            action_desc = {
                "created": "创建新Issue",
                "updated": "更新Issue",
                "completed_and_closed": "完成并关闭Issue",
                "already_closed": "Issue已关闭",
                "failed_to_create": "创建失败",
                "failed_to_update": "更新失败",
                "failed_to_comment": "评论失败"
            }

            report_content += f"""### {status_emoji} {work_item['title']}

- **作业ID**: {work_item['work_id']}
- **结果**: {action_desc.get(result['action'], result['action'])}
- **Issue编号**: #{result.get('issue_number', 'N/A')}
- **标签**: {', '.join(result.get('labels', []))}

"""

        report_content += f"""
---

🤖 **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔧 **工具**: Claude Work Synchronizer v2.0.0
📊 **项目**: {self.repo}
"""

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"📄 同步报告已保存到: {report_file}")
        except Exception as e:
            print(f"❌ 保存同步报告失败: {e}")

    def print_sync_summary(self, results: dict[str, Any]):
        """打印同步总结"""
        print("\n" + "=" * 80)
        print("📊 Claude Code 作业同步总结")
        print("=" * 80)

        print("📈 同步统计:")
        print(f"   总作业项目: {results['total_items']}")
        print(f"   成功同步: {results['successful_syncs']}")
        print(f"   同步失败: {results['failed_syncs']}")

        success_rate = (results['successful_syncs'] / results['total_items']) * 100 if results['total_items'] > 0 else 0
        print(f"   成功率: {success_rate:.1f}%")

        if results['successful_syncs'] > 0:
            print("\n✅ 成功同步的Issues:")
            for sync_result in results["sync_results"]:
                if sync_result["result"]["success"]:
                    issue_num = sync_result["result"].get("issue_number", "N/A")
                    title = sync_result["title"][:40] + "..." if len(sync_result["title"]) > 40 else sync_result["title"]
                    action = sync_result["result"]["action"]
                    action_desc = {
                        "created": "➕ 创建",
                        "updated": "🔄 更新",
                        "completed_and_closed": "✅ 完成",
                        "already_closed": "ℹ️ 已关闭"
                    }
                    print(f"   Issue #{issue_num} ({title}): {action_desc.get(action, '处理')}")

        if results['failed_syncs'] > 0:
            print("\n❌ 同步失败的项目:")
            for sync_result in results["sync_results"]:
                if not sync_result["result"]["success"]:
                    title = sync_result["title"][:40] + "..." if len(sync_result["title"]) > 40 else sync_result["title"]
                    action = sync_result["result"]["action"]
                    print(f"   {title}: {action}")

        print("\n🎯 建议:")
        if results['failed_syncs'] == 0:
            print("   🎉 所有作业项目都已成功同步！")
            print("   📄 建议查看GitHub仓库确认所有Issues状态")
        else:
            print(f"   ⚠️  有 {results['failed_syncs']} 个项目同步失败")
            print("   🔧 建议检查GitHub CLI认证和网络连接")
            print("   📝 可以手动创建失败的Issues")

        print(f"\n🕐 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)


def main():
    """主函数"""
    print("🔗 Claude Code 作业同步工具 v2.0.0")
    print("=" * 60)

    synchronizer = ClaudeWorkSynchronizer()

    try:
        # 检查参数
        if len(os.sys.argv) > 1:
            command = os.sys.argv[1]

            if command == "start-work":
                # 开始新作业
                try:
                    title = input("📝 输入作业标题: ")
                    description = input("📄 输入作业描述: ")
                    work_type = input("🏷️ 输入作业类型 (development/testing/documentation/bugfix/feature): ")
                    priority = input("⚡ 输入优先级 (low/medium/high/critical, 默认medium): ") or "medium"
                except EOFError:
                    print("❌ 交互式输入被中断，请确保在终端中运行")
                    return

                work_item = synchronizer.create_work_item_from_current_work(
                    title=title,
                    description=description,
                    work_type=work_type,
                    priority=priority
                )
                print(f"✅ 作业已创建: {work_item.id}")

            elif command == "complete-work":
                # 完成作业
                work_id = input("🆔 输入作业ID: ")

                work_items = synchronizer.load_work_log()
                work_item = next((item for item in work_items if item.id == work_id), None)

                if work_item:
                    print(f"📋 找到作业: {work_item.title}")

                    # 询问交付成果
                    deliverables_input = input("🎯 输入交付成果 (用逗号分隔，可选): ")
                    deliverables = [d.strip() for d in deliverables_input.split(',')] if deliverables_input else []

                    success = synchronizer.complete_work_item(
                        work_id=work_id,
                        deliverables=deliverables
                    )

                    if success:
                        print("✅ 作业已完成，将自动同步到GitHub")
                    else:
                        print("❌ 完成作业失败")
                else:
                    print(f"❌ 未找到作业: {work_id}")

            elif command == "list-work":
                # 列出所有作业
                work_items = synchronizer.load_work_log()
                if work_items:
                    print(f"\n📋 找到 {len(work_items)} 个作业项目:")
                    for i, item in enumerate(work_items, 1):
                        print(f"{i}. {item.id} - {item.title} ({item.status}, {item.completion_percentage}%)")
                else:
                    print("📝 没有找到作业项目")

            elif command == "sync":
                # 同步到GitHub
                results = synchronizer.sync_all_work_items()

                if results["success"]:
                    print("\n🎉 同步完成！")
                else:
                    print(f"\n❌ 同步失败: {results.get('error', 'Unknown error')}")

            else:
                print(f"❌ 未知命令: {command}")
                print("可用命令: start-work, complete-work, list-work, sync")
        else:
            # 默认执行同步
            results = synchronizer.sync_all_work_items()

    except KeyboardInterrupt:
        print("\n⚠️ 操作被用户中断")
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
