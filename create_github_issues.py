#!/usr/bin/env python3
"""
使用GitHub CLI创建渐进式改进Issues
Create Progressive Improvement Issues using GitHub CLI
"""

import json
import subprocess
import sys
from typing import Any


def run_command(cmd: str, description: str) -> bool:
    """运行命令并显示结果"""
    print(f"\n🔧 {description}")
    print(f"执行: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            if result.stdout:
                print(f"✅ 成功: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ 失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ 命令超时")
        return False
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False

def create_issue_with_cli(issue_data: dict[str, Any]) -> bool:
    """使用GitHub CLI创建单个Issue"""
    title = issue_data["title"]
    body = issue_data["body"]
    labels = ",".join(issue_data["labels"])

    # 构建gh命令
    cmd = f'gh issue create --title "{title}" --body "{body}" --label "{labels}"'

    # 由于body可能很长，我们将其写入临时文件
    with open("/tmp/issue_body.md", "w", encoding="utf-8") as f:
        f.write(body)

    cmd = f'gh issue create --title "{title}" --body-file /tmp/issue_body.md --label "{labels}"'

    return run_command(cmd, f"创建Issue: {title[:50]}...")

def main():
    """主函数"""
    print("🚀 使用GitHub CLI创建渐进式改进Issues")
    print("=" * 60)

    # 检查gh CLI是否可用
    if not run_command("gh --version", "检查GitHub CLI"):
        print("❌ GitHub CLI (gh) 未安装或不可用")
        print("💡 请安装GitHub CLI: https://cli.github.com/")
        sys.exit(1)

    # 检查是否已认证
    if not run_command("gh auth status", "检查GitHub认证状态"):
        print("❌ GitHub CLI 未认证")
        print("💡 请运行: gh auth login")
        sys.exit(1)

    # 读取Issues数据
    try:
        with open("progressive_improvement_issues.json", encoding="utf-8") as f:
            issues = json.load(f)
    except FileNotFoundError:
        print("❌ 找不到 progressive_improvement_issues.json 文件")
        print("💡 请先运行: python3 create_progressive_improvement_issues.py")
        sys.exit(1)

    print(f"📋 准备创建 {len(issues)} 个Issues")
    print()

    # 询问用户确认
    response = input("❓ 是否继续创建所有Issues? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ 操作已取消")
        sys.exit(0)

    # 创建Issues
    created_count = 0
    failed_count = 0

    for i, issue in enumerate(issues, 1):
        print(f"\n📝 [{i}/{len(issues)}] 创建Issue...")

        if create_issue_with_cli(issue):
            created_count += 1
            print(f"✅ Issue {i}/{len(issues)} 创建成功")
        else:
            failed_count += 1
            print(f"❌ Issue {i}/{len(issues)} 创建失败")

        # 添加延迟避免API限制
        if i < len(issues):
            print("⏳ 等待2秒...")
            import time
            time.sleep(2)

    # 清理临时文件
    import os
    if os.path.exists("/tmp/issue_body.md"):
        os.remove("/tmp/issue_body.md")

    # 显示结果
    print("\n📊 创建结果摘要")
    print("=" * 30)
    print(f"✅ 成功创建: {created_count} 个Issues")
    print(f"❌ 创建失败: {failed_count} 个Issues")
    print(f"📈 成功率: {created_count/len(issues)*100:.1f}%")

    if created_count > 0:
        print(f"\n🎯 成功创建了 {created_count} 个渐进式改进Issues!")
        print("💡 查看Issues: gh issue list --label progressive-improvement")
        print("📋 每个Issue都包含详细的渐进式改进策略指南")

if __name__ == "__main__":
    main()
