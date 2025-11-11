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
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            if result.stdout:
                pass
            return True
        else:
            return False
    except subprocess.TimeoutExpired:
        return False
    except Exception:
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

    # 检查gh CLI是否可用
    if not run_command("gh --version", "检查GitHub CLI"):
        sys.exit(1)

    # 检查是否已认证
    if not run_command("gh auth status", "检查GitHub认证状态"):
        sys.exit(1)

    # 读取Issues数据
    try:
        with open("progressive_improvement_issues.json", encoding="utf-8") as f:
            issues = json.load(f)
    except FileNotFoundError:
        sys.exit(1)


    # 询问用户确认
    response = input("❓ 是否继续创建所有Issues? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        sys.exit(0)

    # 创建Issues
    created_count = 0
    failed_count = 0

    for i, issue in enumerate(issues, 1):

        if create_issue_with_cli(issue):
            created_count += 1
        else:
            failed_count += 1

        # 添加延迟避免API限制
        if i < len(issues):
            import time
            time.sleep(2)

    # 清理临时文件
    import os
    if os.path.exists("/tmp/issue_body.md"):
        os.remove("/tmp/issue_body.md")

    # 显示结果

    if created_count > 0:
        pass

if __name__ == "__main__":
    main()
