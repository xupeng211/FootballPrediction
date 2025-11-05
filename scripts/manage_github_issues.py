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

import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

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
    command: List[str],
    cwd: Optional[str] = None) -> Dict[str,
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

    def get_issue_status(self, issue_number: int) -> Dict[str, Any]:
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

    def add_issue_comment(self, issue_number: int, comment: str) -> Dict[str, Any]:
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
    reason: str = "completed") -> Dict[str,
    Any]:
        """关闭Issue"""
        result = self.run_gh_command([
            "issue", "close", str(issue_number), "--reason", reason
        ])

        return {
            "success": result["success"],
            "message": f"Issue #{issue_number} closed successfully" if result["success"] else result["stderr"]
        }

    def add_issue_labels(self, issue_number: int, labels: List[str]) -> Dict[str, Any]:
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
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return f"# Issue #{file_path.split('_')[-1]} 完成评论\n\n## 🎉 Issue完成\n\n此Issue已成功完成！"
        except Exception as e:
            return f"# Issue完成评论\n\n读取评论文件时出错: {str(e)}"

    def process_single_issue(self, issue_info: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个Issue"""
        issue_number = issue_info["number"]
        title = issue_info["title"]

        print(f"\n🔍 处理 Issue #{issue_number}: {title}")
        print("-" * 50)

        # 1. 检查当前状态
        print("1️⃣ 检查Issue状态...")
        status_result = self.get_issue_status(issue_number)

        if not status_result["success"]:
            print(f"   ❌ 无法获取Issue状态: {status_result.get('error', 'Unknown error')}")
            return {"success": False,
    "error": f"Cannot get issue status: {status_result.get('error')}"}

        current_state = status_result["state"]
        current_labels = status_result["labels"]

        print(f"   当前状态: {current_state}")
        print(f"   当前标签: {', '.join(current_labels) if current_labels else 'None'}")

        if current_state == "closed":
            print(f"   ✅ Issue #{issue_number} 已经关闭，跳过处理")
            return {"success": True, "message": "Issue already closed", "action_taken": "skipped"}

        # 2. 添加完成评论
        print("2️⃣ 添加完成评论...")
        comment_content = self.read_comment_file(issue_info["comment_file"])

        comment_result = self.add_issue_comment(issue_number, comment_content)
        if comment_result["success"]:
            print(f"   ✅ 评论添加成功")
        else:
            print(f"   ⚠️  评论添加失败: {comment_result['message']}")
            # 继续执行其他步骤

        # 3. 添加标签
        print("3️⃣ 添加标签...")
        labels_to_add = issue_info["labels"]

        # 检查哪些标签需要添加
        missing_labels = [label for label in labels_to_add if label not in current_labels]

        if missing_labels:
            label_result = self.add_issue_labels(issue_number, missing_labels)
            if label_result["success"]:
                print(f"   ✅ 标签添加成功: {', '.join(missing_labels)}")
            else:
                print(f"   ⚠️  标签添加失败: {label_result['message']}")
        else:
            print(f"   ✅ 所有标签已存在，无需添加")

        # 4. 关闭Issue
        print("4️⃣ 关闭Issue...")
        close_result = self.close_issue(issue_number, "completed")

        if close_result["success"]:
            print(f"   ✅ Issue #{issue_number} 关闭成功")
        else:
            print(f"   ❌ Issue关闭失败: {close_result['message']}")
            return {"success": False, "error": f"Failed to close issue: {close_result['message']}"}

        # 5. 验证关闭状态
        print("5️⃣ 验证关闭状态...")
        time.sleep(2)  # 等待2秒让GitHub更新
        verify_result = self.get_issue_status(issue_number)

        if verify_result["success"] and verify_result["state"] == "closed":
            print(f"   ✅ Issue #{issue_number} 状态确认已关闭")
            return {"success": True, "message": "Issue processed successfully", "action_taken": "closed"}
        else:
            print(f"   ⚠️  Issue状态验证失败，但操作可能已成功")
            return {"success": True, "message": "Issue processed with verification warning", "action_taken": "closed"}

    def process_all_issues(self) -> Dict[str, Any]:
        """批量处理所有Issues"""
        print("🚀 开始使用GitHub CLI批量管理Issues")
        print("=" * 80)

        results = {
            "total_issues": len(self.completed_issues),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }

        # 首先验证仓库连接
        print("🔍 验证GitHub CLI连接...")
        repo_check = self.run_gh_command(["repo", "view"])
        if not repo_check["success"]:
            print(f"❌ 无法连接到仓库: {repo_check['stderr']}")
            return {"success": False, "error": "Cannot connect to repository"}

        print(f"✅ 成功连接到仓库: {self.repo}")

        for i, issue_info in enumerate(self.completed_issues, 1):
            print(f"\n📋 进度: {i}/{len(self.completed_issues)}")

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
                    print(f"   📄 Issue #{issue_info['number']} 已跳过")
                else:
                    results["successful"] += 1
                    print(f"   🎉 Issue #{issue_info['number']} 处理成功")
            else:
                results["failed"] += 1
                print(f"   ❌ Issue #{issue_info['number']} 处理失败: {result.get('error',
    'Unknown error')}")

            # 在Issues之间添加短暂延迟
            if i < len(self.completed_issues):
                print("   ⏳ 等待3秒...")
                time.sleep(3)

        # 生成总结报告
        self.generate_summary_report(results)

        return results

    def generate_summary_report(self, results: Dict[str, Any]):
        """生成总结报告"""
        print("\n" + "=" * 80)
        print("📊 GitHub Issues管理总结报告")
        print("=" * 80)

        print(f"📈 处理统计:")
        print(f"   总Issues数: {results['total_issues']}")
        print(f"   已处理: {results['processed']}")
        print(f"   成功: {results['successful']}")
        print(f"   失败: {results['failed']}")
        print(f"   跳过: {results['skipped']}")

        success_rate = (results['successful'] / results['total_issues']) * 100 if results['total_issues'] > 0 else 0
        print(f"   成功率: {success_rate:.1f}%")

        print(f"\n📋 详细结果:")
        for detail in results["details"]:
            issue_num = detail["issue_number"]
            title = detail["title"][:40] + "..." if len(detail["title"]) > 40 else detail["title"]
            result = detail["result"]

            if result["success"]:
                action = result.get("action_taken", "unknown")
                if action == "skipped":
                    status = "⏭️ 已跳过"
                else:
                    status = "✅ 成功"
            else:
                status = "❌ 失败"

            print(f"   Issue #{issue_num} ({title}): {status}")

        if results["failed"] > 0:
            print(f"\n⚠️  失败的Issues:")
            for detail in results["details"]:
                if not detail["result"]["success"]:
                    issue_num = detail["issue_number"]
                    error = detail["result"].get("error", "Unknown error")
                    print(f"   Issue #{issue_num}: {error}")

        print(f"\n🎯 建议:")
        if results["failed"] == 0:
            print("   🎉 所有Issues都已成功处理！")
            print("   📄 建议查看GitHub仓库确认所有状态")
        else:
            print(f"   ⚠️  有 {results['failed']} 个Issues处理失败")
            print("   🔧 建议手动检查失败的Issues")
            print("   📝 可以使用GitHub网页界面进行手动操作")

        print(f"\n🕐 完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)


def main():
    """主函数"""
    print("🔗 GitHub CLI Issues管理工具")
    print("=" * 50)

    manager = GitHubCLIManager()

    try:
        # 检查GitHub CLI认证
        print("🔍 检查GitHub CLI认证...")
        auth_check = manager.run_gh_command(["auth", "status"])

        if not auth_check["success"]:
            print("❌ GitHub CLI未认证，请先运行: gh auth login")
            return

        print("✅ GitHub CLI认证成功")

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
            print(f"\n📄 详细结果已保存到: {result_file}")
        except Exception as e:
            print(f"\n⚠️  保存结果文件失败: {e}")

    except KeyboardInterrupt:
        print("\n⚠️ 操作被用户中断")
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")


if __name__ == "__main__":
    main()