#!/usr/bin/env python3
"""
批量创建所有渐进式改进Issues到远程GitHub仓库
Batch Create All Progressive Improvement Issues to Remote GitHub Repository
"""

import json
import subprocess
import time
import sys
from typing import Dict, List, Any

def create_issue_with_gh(title: str, body: str, labels: List[str]) -> bool:
    """使用GitHub CLI创建单个Issue"""
    try:
        # 将body写入临时文件
        with open("/tmp/issue_body.md", "w", encoding="utf-8") as f:
            f.write(body)

        # 过滤掉不存在的标签
        valid_labels = []
        for label in labels:
            if label != "progressive-improvement":  # 这个标签不存在，跳过
                valid_labels.append(label)

        labels_str = ",".join(valid_labels) if valid_labels else "bug"

        # 构建命令
        cmd = f'gh issue create --title "{title}" --body-file /tmp/issue_body.md --label "{labels_str}"'

        print(f"🔧 创建Issue: {title[:50]}...")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            url = result.stdout.strip()
            print(f"✅ 成功: {url}")
            return True
        else:
            print(f"❌ 失败: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 批量创建渐进式改进Issues到远程GitHub仓库")
    print("=" * 60)

    # 读取Issues数据
    try:
        with open("progressive_improvement_issues.json", "r", encoding="utf-8") as f:
            issues = json.load(f)
    except FileNotFoundError:
        print("❌ 找不到 progressive_improvement_issues.json 文件")
        sys.exit(1)

    print(f"📋 准备创建 {len(issues)} 个Issues")
    print()

    # 自动确认创建Issues
    print("🚀 自动确认创建所有Issues到远程仓库...")

    # 跳过第一个已创建的Issue
    remaining_issues = issues[1:]  # 跳过第一个（#261已创建）
    print(f"📝 跳过第一个Issue（已创建#261），准备创建剩余 {len(remaining_issues)} 个Issues")
    print()

    # 创建Issues
    created_count = 0
    failed_count = 0
    created_urls = []

    for i, issue in enumerate(remaining_issues, 2):  # 从2开始编号
        print(f"\n📝 [{i-1}/{len(remaining_issues)}] 创建Issue...")

        if create_issue_with_gh(issue["title"], issue["body"], issue["labels"]):
            created_count += 1
            # 获取最新创建的Issue URL
            result = subprocess.run("gh issue list --limit 1 --json url",
                                  shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if data and "url" in data[0]:
                        created_urls.append(data[0]["url"])
                except:
                    pass
            print(f"✅ Issue {i-1}/{len(remaining_issues)} 创建成功")
        else:
            failed_count += 1
            print(f"❌ Issue {i-1}/{len(remaining_issues)} 创建失败")

        # 添加延迟避免API限制
        if i <= len(remaining_issues):
            print("⏳ 等待3秒避免API限制...")
            time.sleep(3)

    # 清理临时文件
    import os
    if os.path.exists("/tmp/issue_body.md"):
        os.remove("/tmp/issue_body.md")

    # 显示结果
    print(f"\n📊 创建结果摘要")
    print("=" * 30)
    print(f"✅ 成功创建: {created_count} 个Issues")
    print(f"❌ 创建失败: {failed_count} 个Issues")
    print(f"📈 成功率: {created_count/len(remaining_issues)*100:.1f}%")

    # 显示创建的Issue URLs
    if created_urls:
        print(f"\n🔗 已创建的Issues:")
        for i, url in enumerate(created_urls, 1):
            print(f"{i}. {url}")

    if created_count > 0:
        print(f"\n🎯 成功创建了 {created_count} 个渐进式改进Issues!")
        print("💡 查看所有Issues: gh issue list")
        print("📋 每个Issue都包含详细的渐进式改进策略指南")
        print("🎯 建议按照优先级顺序处理Issues")

if __name__ == "__main__":
    main()