#!/usr/bin/env python3
"""
Claude Code 作业同步环境设置脚本
Claude Code Work Sync Environment Setup Script

帮助用户设置和验证Claude Code作业同步所需的环境：
- 检查GitHub CLI安装和认证
- 验证Git环境配置
- 创建必要的目录结构
- 测试GitHub仓库连接
- 提供设置指导和故障排除

Author: Claude AI Assistant
Date: 2025-11-06
Version: 1.0.0
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class ClaudeSyncSetup:
    """Claude同步环境设置器"""

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.required_dirs = [
            "reports",
            "reports/github",
            "reports/github/comments"
        ]

    def run_command(self, command: list[str], timeout: int = 30) -> dict[str, Any]:
        """运行命令"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
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

    def check_python_version(self) -> dict[str, Any]:
        """检查Python版本"""
        version = sys.version_info
        return {
            "valid": version.major >= 3 and version.minor >= 8,
            "version": f"{version.major}.{version.minor}.{version.micro}",
            "message": f"Python {version.major}.{version.minor}.{version.micro}"
        }

    def check_git(self) -> dict[str, Any]:
        """检查Git环境"""
        # 检查Git是否安装
        git_check = self.run_command(["git", "--version"])
        if not git_check["success"]:
            return {
                "installed": False,
                "version": None,
                "configured": False,
                "error": "Git not found"
            }

        version = git_check["stdout"]

        # 检查Git配置
        config_checks = {}
        for config_key in ["user.name", "user.email"]:
            config_result = self.run_command(["git", "config", "--global", config_key])
            config_checks[config_key] = config_result["success"] and config_result["stdout"] != ""

        configured = all(config_checks.values())

        return {
            "installed": True,
            "version": version,
            "configured": configured,
            "config": config_checks,
            "error": None
        }

    def check_github_cli(self) -> dict[str, Any]:
        """检查GitHub CLI"""
        # 检查gh命令是否存在
        gh_check = self.run_command(["gh", "--version"])
        if not gh_check["success"]:
            return {
                "installed": False,
                "version": None,
                "authenticated": False,
                "error": "GitHub CLI not found"
            }

        version = gh_check["stdout"]

        # 检查认证状态
        auth_check = self.run_command(["gh", "auth", "status"])
        authenticated = auth_check["success"]

        return {
            "installed": True,
            "version": version,
            "authenticated": authenticated,
            "auth_status": auth_check["stdout"] if authenticated else None,
            "error": None
        }

    def check_repository_access(self) -> dict[str, Any]:
        """检查仓库访问权限"""
        gh_check = self.run_command(["gh", "repo", "view"])
        if not gh_check["success"]:
            return {
                "access": False,
                "repo_info": None,
                "error": gh_check["stderr"]
            }

        # 尝试获取仓库信息
        repo_info = self.run_command([
            "gh", "repo", "view", "--json", "name,owner,visibility,isPrivate"
        ])

        if repo_info["success"]:
            try:
                data = json.loads(repo_info["stdout"])
                return {
                    "access": True,
                    "repo_info": data,
                    "error": None
                }
            except json.JSONDecodeError:
                return {
                    "access": True,
                    "repo_info": {"raw": repo_info["stdout"]},
                    "error": None
                }
        else:
            return {
                "access": False,
                "repo_info": None,
                "error": repo_info["stderr"]
            }

    def create_directories(self) -> bool:
        """创建必要的目录结构"""
        success = True
        for dir_path in self.required_dirs:
            full_path = self.project_root / dir_path
            try:
                full_path.mkdir(parents=True, exist_ok=True)
                print(f"✅ 目录已创建: {full_path}")
            except Exception as e:
                print(f"❌ 创建目录失败 {full_path}: {e}")
                success = False
        return success

    def check_permissions(self) -> dict[str, Any]:
        """检查GitHub Issues权限"""
        try:
            # 尝试列出Issues（测试权限）
            issues_check = self.run_command([
                "gh", "issue", "list", "--limit", "1"
            ])

            if issues_check["success"]:
                return {
                    "can_create_issues": True,
                    "can_manage_issues": True,
                    "error": None
                }
            else:
                return {
                    "can_create_issues": False,
                    "can_manage_issues": False,
                    "error": issues_check["stderr"]
                }
        except Exception as e:
            return {
                "can_create_issues": False,
                "can_manage_issues": False,
                "error": str(e)
            }

    def test_issue_creation(self, dry_run: bool = True) -> dict[str, Any]:
        """测试Issue创建功能"""
        if dry_run:
            return {
                "success": True,
                "issue_url": None,
                "message": "Dry run - Issue creation test skipped"
            }

        test_title = f"Claude Sync Test - {self.get_timestamp()}"
        test_body = """This is a test issue created by Claude Code Work Sync Setup.

If you see this issue, the setup is working correctly! You can safely close this issue.

🤖 Created by: Claude Sync Setup Tool
🕐 Created at: """ + self.get_timestamp()

        create_result = self.run_command([
            "gh", "issue", "create",
            "--title", test_title,
            "--body", test_body,
            "--label", "test,claude-sync"
        ])

        if create_result["success"]:
            output = create_result["stdout"]
            # 提取Issue URL
            lines = output.split('\n')
            issue_url = lines[-1] if lines else None

            return {
                "success": True,
                "issue_url": issue_url,
                "message": "Test issue created successfully"
            }
        else:
            return {
                "success": False,
                "issue_url": None,
                "error": create_result["stderr"]
            }

    def get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def run_full_setup(self, test_issue: bool = False) -> dict[str, Any]:
        """运行完整的环境检查和设置"""
        print("🔧 Claude Code 作业同步环境设置")
        print("=" * 60)

        results = {
            "timestamp": self.get_timestamp(),
            "python": None,
            "git": None,
            "github_cli": None,
            "repository": None,
            "permissions": None,
            "directories": None,
            "test_issue": None,
            "overall_status": "unknown",
            "recommendations": []
        }

        # 1. 检查Python版本
        print("\n🐍 检查Python环境...")
        python_check = self.check_python_version()
        results["python"] = python_check

        if python_check["valid"]:
            print(f"✅ {python_check['message']}")
        else:
            print(f"❌ Python版本过低: {python_check['version']} (需要3.8+)")
            results["recommendations"].append("请升级Python到3.8或更高版本")

        # 2. 检查Git环境
        print("\n📦 检查Git环境...")
        git_check = self.check_git()
        results["git"] = git_check

        if git_check["installed"]:
            print(f"✅ Git已安装: {git_check['version']}")
            if git_check["configured"]:
                print("✅ Git配置正确")
            else:
                print("⚠️ Git配置不完整")
                results["recommendations"].append("请配置Git用户信息: git config --global user.name 'Your Name' 和 git config --global user.email 'your.email@example.com'")
        else:
            print("❌ Git未安装")
            results["recommendations"].append("请安装Git: https://git-scm.com/downloads")

        # 3. 检查GitHub CLI
        print("\n🔗 检查GitHub CLI...")
        gh_check = self.check_github_cli()
        results["github_cli"] = gh_check

        if gh_check["installed"]:
            print(f"✅ GitHub CLI已安装: {gh_check['version']}")
            if gh_check["authenticated"]:
                print("✅ GitHub CLI已认证")
                if gh_check["auth_status"]:
                    print(f"   认证信息: {gh_check['auth_status']}")
            else:
                print("❌ GitHub CLI未认证")
                results["recommendations"].append("请认证GitHub CLI: gh auth login")
        else:
            print("❌ GitHub CLI未安装")
            results["recommendations"].append("请安装GitHub CLI: https://cli.github.com/manual/installation")

        # 4. 检查仓库访问权限
        if gh_check.get("authenticated"):
            print("\n🏠 检查仓库访问权限...")
            repo_check = self.check_repository_access()
            results["repository"] = repo_check

            if repo_check["access"]:
                print("✅ 仓库访问正常")
                if repo_check.get("repo_info"):
                    repo_info = repo_check["repo_info"]
                    if isinstance(repo_info, dict) and "name" in repo_info:
                        print(f"   仓库: {repo_info.get('owner', {}).get('login', 'Unknown')}/{repo_info['name']}")
                        print(f"   可见性: {'Private' if repo_info.get('isPrivate') else 'Public'}")
            else:
                print("❌ 无法访问仓库")
                results["recommendations"].append(f"仓库访问失败: {repo_check.get('error', 'Unknown error')}")

            # 5. 检查Issues权限
            print("\n📝 检查Issues管理权限...")
            perm_check = self.check_permissions()
            results["permissions"] = perm_check

            if perm_check["can_manage_issues"]:
                print("✅ Issues管理权限正常")
            else:
                print("❌ Issues管理权限不足")
                results["recommendations"].append(f"Issues权限问题: {perm_check.get('error', 'Unknown error')}")

        # 6. 创建目录结构
        print("\n📁 创建目录结构...")
        dirs_created = self.create_directories()
        results["directories"] = dirs_created

        if dirs_created:
            print("✅ 目录结构创建完成")
        else:
            print("❌ 目录创建失败")

        # 7. 测试Issue创建（可选）
        if test_issue and gh_check.get("authenticated") and results.get("permissions", {}).get("can_manage_issues"):
            print("\n🧪 测试Issue创建...")
            test_result = self.test_issue_creation(dry_run=False)
            results["test_issue"] = test_result

            if test_result["success"]:
                print(f"✅ 测试Issue创建成功: {test_result['issue_url']}")
            else:
                print(f"❌ 测试Issue创建失败: {test_result.get('error', 'Unknown error')}")

        # 8. 总体状态评估
        print("\n" + "=" * 60)
        print("📊 环境设置总结")
        print("=" * 60)

        critical_issues = []
        warnings = []

        # 评估各个组件
        if not python_check["valid"]:
            critical_issues.append("Python版本不符合要求")
        if not git_check["installed"]:
            critical_issues.append("Git未安装")
        if not git_check["configured"]:
            warnings.append("Git配置不完整")
        if not gh_check["installed"]:
            critical_issues.append("GitHub CLI未安装")
        if not gh_check.get("authenticated"):
            critical_issues.append("GitHub CLI未认证")
        if gh_check.get("authenticated") and not results.get("repository", {}).get("access"):
            critical_issues.append("仓库访问权限问题")
        if gh_check.get("authenticated") and not results.get("permissions", {}).get("can_manage_issues"):
            critical_issues.append("Issues管理权限不足")

        # 确定总体状态
        if not critical_issues:
            if not warnings:
                results["overall_status"] = "excellent"
                print("🎉 环境设置完美！Claude Code作业同步已准备就绪")
            else:
                results["overall_status"] = "good"
                print("✅ 环境设置良好，但有一些小问题需要注意")
        else:
            results["overall_status"] = "needs_attention"
            print("⚠️ 环境设置需要处理一些问题才能正常使用")

        # 输出详细状态
        print("\n📈 组件状态:")
        print(f"   Python: {'✅' if python_check['valid'] else '❌'}")
        print(f"   Git: {'✅' if git_check['installed'] and git_check['configured'] else '⚠️' if git_check['installed'] else '❌'}")
        print(f"   GitHub CLI: {'✅' if gh_check.get('authenticated') else '⚠️' if gh_check.get('installed') else '❌'}")
        print(f"   仓库访问: {'✅' if results.get('repository', {}).get('access') else '❌'}")
        print(f"   Issues权限: {'✅' if results.get('permissions', {}).get('can_manage_issues') else '❌'}")
        print(f"   目录结构: {'✅' if dirs_created else '❌'}")

        # 输出建议
        if results["recommendations"]:
            print("\n💡 改进建议:")
            for i, rec in enumerate(results["recommendations"], 1):
                print(f"   {i}. {rec}")

        # 输出下一步操作
        print("\n🚀 下一步操作:")
        if results["overall_status"] == "excellent":
            print("   🎯 开始使用: make claude-start-work")
            print("   📋 查看帮助: make claude-list-work")
            print("   🔗 同步作业: make claude-sync")
        elif results["overall_status"] == "good":
            print("   🔧 解决警告问题后即可正常使用")
            print("   🎯 尝试使用: make claude-start-work")
        else:
            print("   🔧 请先解决上述关键问题")
            print("   📖 重新运行设置: python3 scripts/setup_claude_sync.py")

        return results

    def generate_setup_report(self, results: dict[str, Any]) -> str:
        """生成设置报告"""
        report = f"""# Claude Code 作业同步环境设置报告

## 📊 设置时间

{results['timestamp']}

## 🎯 总体状态

{results['overall_status']}

## 🔧 组件状态

### Python环境
- **版本**: {results['python']['version']}
- **状态**: {'✅ 正常' if results['python']['valid'] else '❌ 需要升级'}

### Git环境
- **安装**: {'✅ 已安装' if results['git']['installed'] else '❌ 未安装'}
- **版本**: {results['git']['version'] if results['git']['installed'] else 'N/A'}
- **配置**: {'✅ 已配置' if results['git']['configured'] else '⚠️ 需要配置'}

### GitHub CLI
- **安装**: {'✅ 已安装' if results['github_cli']['installed'] else '❌ 未安装'}
- **版本**: {results['github_cli']['version'] if results['github_cli']['installed'] else 'N/A'}
- **认证**: {'✅ 已认证' if results['github_cli']['authenticated'] else '❌ 需要认证'}

### 仓库访问
- **权限**: {'✅ 正常' if results.get('repository', {}).get('access') else '❌ 无权限'}
- **信息**: {json.dumps(results.get('repository', {}).get('repo_info', {}), indent=2, ensure_ascii=False) if results.get('repository') else 'N/A'}

### Issues权限
- **管理权限**: {'✅ 正常' if results.get('permissions', {}).get('can_manage_issues') else '❌ 权限不足'}

### 目录结构
- **状态**: {'✅ 已创建' if results['directories'] else '❌ 创建失败'}

## 💡 改进建议

"""

        if results["recommendations"]:
            for i, rec in enumerate(results["recommendations"], 1):
                report += f"{i}. {rec}\n"
        else:
            report += "无，环境设置完美！\n"

        report += f"""
## 🚀 使用指南

环境设置完成后，你可以使用以下命令：

```bash
# 开始新作业
make claude-start-work

# 完成作业
make claude-complete-work

# 同步到GitHub
make claude-sync

# 查看作业记录
make claude-list-work
```

---

🤖 **生成时间**: {results['timestamp']}
🔧 **工具**: Claude Sync Setup v1.0.0
"""

        return report


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Claude Code 作业同步环境设置")
    parser.add_argument("--test-issue", action="store_true", help="测试Issue创建功能")
    parser.add_argument("--report", help="生成设置报告到指定文件")

    args = parser.parse_args()

    setup = ClaudeSyncSetup()

    try:
        # 运行环境检查
        results = setup.run_full_setup(test_issue=args.test_issue)

        # 生成报告（如果指定）
        if args.report:
            report = setup.generate_setup_report(results)
            try:
                with open(args.report, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"\n📄 设置报告已保存到: {args.report}")
            except Exception as e:
                print(f"\n❌ 保存报告失败: {e}")

        # 返回适当的退出码
        if results["overall_status"] == "excellent":
            sys.exit(0)
        elif results["overall_status"] == "good":
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ 设置过程被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 设置过程失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
