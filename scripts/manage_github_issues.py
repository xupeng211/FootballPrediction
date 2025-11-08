#!/usr/bin/env python3
"""
GitHub CLI Issues管理脚本
GitHub CLI Issues Management Script

使用GitHub CLI自动管理远程Issues：
- 添加完成评论
- 更新Issue状态
- 添加标签和里程碑
- 批量处理多个Issues

Author: Claude AI Assistant
Date: 2025-11-03
Version: 1.0.0
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Any


class GitHubCLIManager:
    """GitHub CLI管理器"""

    def __init__(self, repo: str = "xupeng211/FootballPrediction"):
        self.repo = repo
        self.completed_issues = [
            {
                "number": 202,
                "title": "系统性能优化",
                "comment_file": "reports/github/comments/issue_202_comment.md",
                "labels": ["completed", "performance", "enhancement"]
            },
            {
                "number": 200,
                "title": "项目目录结构优化",
                "comment_file": "reports/github/comments/issue_200_comment.md",
                "labels": ["completed", "enhancement", "documentation"]
            },
            {
                "number": 194,
                "title": "建立基础测试框架和CI/CD质量门禁",
                "comment_file": "reports/github/comments/issue_194_comment.md",
                "labels": ["completed", "testing", "ci-cd"]
            },
            {
                "number": 185,
                "title": "生产环境部署准备和验证体系建立",
                "comment_file": "reports/github/comments/issue_185_comment.md",
                "labels": ["completed", "deployment", "production"]
            },
            {
                "number": 183,
                "title": "CI/CD流水线监控和自动化优化",
                "comment_file": "reports/github/comments/issue_183_comment.md",
                "labels": ["completed", "ci-cd", "monitoring"]
            }
        ]

    def run_gh_command(self,
    command: list[str],
    cwd: str | None = None) -> dict[str,
    Any]:
        """运行GitHub CLI命令"""
        try:
            if cwd is None:
                cwd = Path(__file__).resolve().parent.parent

            result = subprocess.run(
                ["gh"] + command,
                capture_output=True,
                text=True,
                cwd=cwd,
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

    def get_issue_status(self, issue_number: int) -> dict[str, Any]:
        """获取Issue状态"""
        result = self.run_gh_command([
            "issue", "view", str(issue_number), "--json", "state,title,body,labels"
        ])

        if result["success"]:
            try:
                issue_data = json.loads(result["stdout"])
                return {
                    "success": True,
                    "state": issue_data.get("state", "unknown"),
                    "title": issue_data.get("title", ""),
                    "labels": [label["name"] for label in issue_data.get("labels", [])]
                }
            except json.JSONDecodeError:
                return {"success": False, "error": "Failed to parse JSON response"}
        else:
            return {"success": False, "error": result["stderr"]}

    def add_issue_comment(self, issue_number: int, comment: str) -> dict[str, Any]:
        """添加Issue评论"""
        result = self.run_gh_command([
            "issue", "comment", str(issue_number), "--body", comment
        ])

        return {
            "success": result["success"],
            "message": "Comment added successfully" if result["success"] else result["stderr"]
        }

    def close_issue(self,
    issue_number: int,
    reason: str = "completed") -> dict[str,
    Any]:
        """关闭Issue"""
        result = self.run_gh_command([
            "issue", "close", str(issue_number), "--reason", reason
        ])

        return {
            "success": result["success"],
            "message": f"Issue #{issue_number} closed successfully" if result["success"] else result["stderr"]
        }

    def add_issue_labels(self, issue_number: int, labels: list[str]) -> dict[str, Any]:
        """添加Issue标签"""
        result = self.run_gh_command([
            "issue", "edit", str(issue_number), "--add-label", ",".join(labels)
        ])

        return {
            "success": result["success"],
            "message": f"Labels {labels} added successfully" if result["success"] else result["stderr"]
        }

    def read_comment_file(self, file_path: str) -> str:
        """读取评论文件"""
        try:
            full_path = Path(__file__).resolve().parent.parent / file_path
            if full_path.exists():
                with open(full_path, encoding='utf-8') as f:
                    return f.read()
            else:
                return f"# Issue #{file_path.split('_')[-1]} 完成评论\n\n## 🎉 Issue完成\n\n此Issue已成功完成！"
        except Exception as e:
            return f"# Issue完成评论\n\n读取评论文件时出错: {str(e)}"

    def process_single_issue(self, issue_info: dict[str, Any]) -> dict[str, Any]:
        """处理单个Issue"""
        issue_number = issue_info["number"]
        issue_info["title"]


        # 1. 检查当前状态
        status_result = self.get_issue_status(issue_number)

        if not status_result["success"]:
            return {"success": False,
    "error": f"Cannot get issue status: {status_result.get('error')}"}

        current_state = status_result["state"]
        current_labels = status_result["labels"]


        if current_state == "closed":
            return {"success": True, "message": "Issue already closed", "action_taken": "skipped"}

        # 2. 添加完成评论
        comment_content = self.read_comment_file(issue_info["comment_file"])

        comment_result = self.add_issue_comment(issue_number, comment_content)
        if comment_result["success"]:
            pass
        else:
            pass
            # 继续执行其他步骤

        # 3. 添加标签
        labels_to_add = issue_info["labels"]

        # 检查哪些标签需要添加
        missing_labels = [label for label in labels_to_add if label not in current_labels]

        if missing_labels:
            label_result = self.add_issue_labels(issue_number, missing_labels)
            if label_result["success"]:
                pass
            else:
                pass
        else:
            pass

        # 4. 关闭Issue
        close_result = self.close_issue(issue_number, "completed")

        if close_result["success"]:
            pass
        else:
            return {"success": False, "error": f"Failed to close issue: {close_result['message']}"}

        # 5. 验证关闭状态
        time.sleep(2)  # 等待2秒让GitHub更新
        verify_result = self.get_issue_status(issue_number)

        if verify_result["success"] and verify_result["state"] == "closed":
            return {"success": True, "message": "Issue processed successfully", "action_taken": "closed"}
        else:
            return {"success": True, "message": "Issue processed with verification warning", "action_taken": "closed"}

    def process_all_issues(self) -> dict[str, Any]:
        """批量处理所有Issues"""

        results = {
            "total_issues": len(self.completed_issues),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }

        # 首先验证仓库连接
        repo_check = self.run_gh_command(["repo", "view"])
        if not repo_check["success"]:
            return {"success": False, "error": "Cannot connect to repository"}


        for i, issue_info in enumerate(self.completed_issues, 1):

            result = self.process_single_issue(issue_info)
            results["details"].append({
                "issue_number": issue_info["number"],
                "title": issue_info["title"],
                "result": result
            })

            results["processed"] += 1

            if result["success"]:
                if result.get("action_taken") == "skipped":
                    results["skipped"] += 1
                else:
                    results["successful"] += 1
            else:
                results["failed"] += 1

            # 在Issues之间添加短暂延迟
            if i < len(self.completed_issues):
                time.sleep(3)

        # 生成总结报告
        self.generate_summary_report(results)

        return results

    def generate_summary_report(self, results: dict[str, Any]):
        """生成总结报告"""


        (results['successful'] / results['total_issues']) * 100 if results['total_issues'] > 0 else 0

        for detail in results["details"]:
            detail["issue_number"]
            detail["title"][:40] + "..." if len(detail["title"]) > 40 else detail["title"]
            result = detail["result"]

            if result["success"]:
                action = result.get("action_taken", "unknown")
                if action == "skipped":
                    pass
                else:
                    pass
            else:
                pass


        if results["failed"] > 0:
            for detail in results["details"]:
                if not detail["result"]["success"]:
                    detail["issue_number"]
                    detail["result"].get("error", "Unknown error")

        if results["failed"] == 0:
            pass
        else:
            pass



def main():
    """主函数"""

    manager = GitHubCLIManager()

    try:
        # 检查GitHub CLI认证
        auth_check = manager.run_gh_command(["auth", "status"])

        if not auth_check["success"]:
            return


        # 处理所有Issues
        results = manager.process_all_issues()

        # 保存结果到文件
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        result_file = f"reports/github/gh_management_result_{timestamp}.json"

        try:
            import json
            Path(result_file).parent.mkdir(parents=True, exist_ok=True)
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            pass

    except KeyboardInterrupt:
        pass
    except Exception:
        pass


if __name__ == "__main__":
    main()
