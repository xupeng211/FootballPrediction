#!/usr/bin/env python3
"""
直接在远程GitHub仓库创建Issues
Create Issues Directly in Remote GitHub Repository
"""

import json
import os
import subprocess
import time
from typing import Any


class RemoteGitHubIssuesCreator:
    """远程GitHub Issues创建器"""

    def __init__(self):
        self.repo = ""
        self.created_issues = []

    def check_github_cli(self) -> bool:
        """检查GitHub CLI是否可用"""
        try:
            result = subprocess.run(["gh", "--version"], capture_output=True, check=True)
            print(f"✅ GitHub CLI已安装: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ GitHub CLI未安装")
            print("💡 安装方法:")
            print("   Ubuntu/Debian: sudo apt install gh")
            print("   macOS: brew install gh")
            print("   其他系统: https://cli.github.com/")
            return False

    def check_github_auth(self) -> bool:
        """检查GitHub认证状态"""
        try:
            result = subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)
            print("✅ GitHub CLI已登录")
            return True
        except subprocess.CalledProcessError:
            print("❌ GitHub CLI未登录")
            print("💡 请运行: gh auth login")
            return False

    def load_issues_data(self) -> list[dict[str, Any]]:
        """加载Issues数据"""
        all_issues = []

        # 加载主要Issues
        try:
            with open("generated_issues.json", encoding='utf-8') as f:
                main_issues = json.load(f)
                all_issues.extend(main_issues)
                print(f"✅ 加载主要Issues: {len(main_issues)}个")
        except FileNotFoundError:
            print("❌ 未找到 generated_issues.json")
            print("💡 请先运行: python3 create_github_issues_batch.py")
            return []

        # 加载测试Issues
        try:
            with open("test_improvement_issues.json", encoding='utf-8') as f:
                test_issues = json.load(f)
                all_issues.extend(test_issues)
                print(f"✅ 加载测试Issues: {len(test_issues)}个")
        except FileNotFoundError:
            print("❌ 未找到 test_improvement_issues.json")
            print("💡 请先运行: python3 create_test_improvement_issues.py")
            return []

        print(f"📊 总计Issues: {len(all_issues)}个")
        return all_issues

    def create_single_issue(self, issue: dict[str, Any], index: int, total: int) -> bool:
        """创建单个Issue"""
        title = issue["title"]
        body = issue["body"]
        labels = issue.get("labels", [])

        try:
            # 过滤有效的标签（避免不存在的标签）
            valid_labels = []
            for label in labels:
                # 跳过一些可能不存在的自定义标签
                if label not in ["batch", "progressive-improvement"]:
                    valid_labels.append(label)

            # 如果没有有效标签，使用默认标签
            if not valid_labels:
                valid_labels = ["enhancement"]

            # 构建标签参数
            label_params = []
            for label in valid_labels:
                label_params.extend(["--label", label])

            # 将body写入临时文件
            temp_file = f"/tmp/issue_body_{index}.md"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(body)

            # 构建命令
            cmd = [
                "gh", "issue", "create",
                "--repo", self.repo,
                "--title", title,
                "--body-file", temp_file
            ] + label_params

            print(f"🔧 [{index}/{total}] 创建: {title[:60]}...")

            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            # 清理临时文件
            if os.path.exists(temp_file):
                os.remove(temp_file)

            if result.returncode == 0:
                issue_url = result.stdout.strip()
                print(f"✅ 成功: {issue_url}")
                return True
            else:
                print(f"❌ 失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print(f"⏰ 超时: {title[:60]}...")
            return False
        except Exception as e:
            print(f"❌ 异常: {title[:60]} - {e}")
            return False

    def create_issues_batch(self, issues: list[dict[str, Any]], batch_size: int = 10) -> int:
        """批量创建Issues"""
        total = len(issues)
        success_count = 0

        print(f"\n🚀 开始批量创建 {total} 个Issues到 {self.repo}")
        print("=" * 60)

        for i in range(0, total, batch_size):
            batch = issues[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            print(f"\n📦 处理批次 {batch_num}/{total_batches} ({len(batch)} 个Issues)")

            for j, issue in enumerate(batch, 1):
                index = i + j
                if self.create_single_issue(issue, index, total):
                    success_count += 1

                # 添加延迟避免API限制
                if index < total:  # 不是最后一个Issue
                    print("⏳ 等待3秒避免API限制...")
                    time.sleep(3)

            # 批次间更长的延迟
            if batch_num < total_batches:
                print(f"🔄 批次 {batch_num} 完成，等待10秒后继续...")
                time.sleep(10)

        return success_count

    def verify_created_issues(self) -> int:
        """验证创建的Issues数量"""
        try:
            result = subprocess.run(
                ["gh", "issue", "list", "--repo", self.repo, "--limit", "100", "--json", "title,url"],
                capture_output=True,
                text=True,
                check=True
            )

            if result.returncode == 0:
                issues = json.loads(result.stdout)
                return len(issues)
            else:
                print(f"❌ 验证失败: {result.stderr}")
                return 0

        except Exception as e:
            print(f"❌ 验证异常: {e}")
            return 0

    def show_created_issues(self, limit: int = 10):
        """显示最近创建的Issues"""
        try:
            result = subprocess.run(
                ["gh", "issue", "list", "--repo", self.repo, "--limit", str(limit), "--json", "title,url,labels,state"],
                capture_output=True,
                text=True,
                check=True
            )

            if result.returncode == 0:
                issues = json.loads(result.stdout)
                print(f"\n📋 最近创建的 {len(issues)} 个Issues:")
                print("=" * 50)

                for i, issue in enumerate(issues, 1):
                    title = issue["title"]
                    url = issue["url"]
                    labels = [label["name"] for label in issue.get("labels", [])]
                    state = issue["state"]

                    # 优先级标记
                    priority = ""
                    if "critical" in labels:
                        priority = "🚨"
                    elif "high" in labels:
                        priority = "🔥"
                    elif "medium" in labels:
                        priority = "⚡"
                    elif "low" in labels:
                        priority = "💡"

                    print(f"{i}. {priority} {title}")
                    print(f"   🏷️  {', '.join(labels)}")
                    print(f"   🔗 {url}")
                    print(f"   📊 状态: {state}")
                    print()

        except Exception as e:
            print(f"❌ 获取Issues列表失败: {e}")

    def run_interactive(self):
        """交互式运行"""
        print("🚀 远程GitHub Issues创建工具")
        print("=" * 50)

        # 检查环境
        if not self.check_github_cli():
            return False

        if not self.check_github_auth():
            return False

        # 获取仓库地址
        print("\n📁 请输入GitHub仓库信息:")
        self.repo = input("仓库地址 (格式: owner/repo): ").strip()

        if not self.repo:
            print("❌ 仓库地址不能为空")
            return False

        print(f"🎯 目标仓库: {self.repo}")

        # 确认创建
        print("\n⚠️  即将在远程仓库创建Issues，此操作不可撤销!")
        confirm = input("确认继续? (y/N): ").strip().lower()

        if confirm not in ['y', 'yes']:
            print("❌ 操作已取消")
            return False

        # 加载Issues数据
        issues = self.load_issues_data()
        if not issues:
            return False

        # 创建Issues
        success_count = self.create_issues_batch(issues)

        # 显示结果
        print("\n📊 创建结果:")
        print("=" * 30)
        print(f"✅ 成功创建: {success_count}/{len(issues)} 个Issues")
        print(f"📈 成功率: {success_count/len(issues)*100:.1f}%")

        if success_count > 0:
            print(f"\n🎉 成功创建了 {success_count} 个Issues到远程仓库!")
            print(f"🔗 仓库地址: https://github.com/{self.repo}")

            # 显示创建的Issues
            print("\n📋 显示最近创建的Issues:")
            self.show_created_issues(min(success_count, 10))

            print("\n💡 后续操作:")
            print(f"   1. 访问仓库查看所有Issues: https://github.com/{self.repo}/issues")
            print("   2. 按优先级开始处理Issues")
            print("   3. 使用项目看板追踪进度")
            print("   4. 参考 QUALITY_IMPROVEMENT_ROADMAP.md 执行策略")

        return success_count > 0

    def run_batch(self, repo: str):
        """批量运行模式"""
        self.repo = repo

        # 检查环境
        if not self.check_github_cli():
            return False

        if not self.check_github_auth():
            return False

        print(f"🎯 目标仓库: {self.repo}")

        # 加载Issues数据
        issues = self.load_issues_data()
        if not issues:
            return False

        # 创建Issues
        success_count = self.create_issues_batch(issues)

        # 显示结果
        print("\n📊 批量创建完成:")
        print(f"✅ 成功: {success_count}/{len(issues)} 个Issues")

        if success_count > 0:
            self.show_created_issues(min(success_count, 5))

        return success_count > 0


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="远程GitHub Issues创建工具")
    parser.add_argument("--repo", help="GitHub仓库地址 (owner/repo)")
    parser.add_argument("--batch", action="store_true", help="批量模式，无需交互确认")

    args = parser.parse_args()

    creator = RemoteGitHubIssuesCreator()

    if args.repo:
        # 直接指定仓库
        if args.batch:
            creator.run_batch(args.repo)
        else:
            creator.run_interactive()
    else:
        # 交互模式
        creator.run_interactive()


if __name__ == "__main__":
    main()
