#!/usr/bin/env python3
"""
创建剩余的渐进式改进Issues（仅使用基础标签）
Create Remaining Progressive Improvement Issues (Using Basic Labels Only)
"""

import json
import subprocess
import sys
import time


def create_issue_with_basic_labels(title: str, body: str, original_labels: list[str]) -> bool:
    """使用基础标签创建Issue"""
    try:
        # 将body写入临时文件
        with open("/tmp/issue_body.md", "w", encoding="utf-8") as f:
            f.write(body)

        # 仅使用基础标签
        basic_labels = ["bug", "enhancement"]

        # 根据原始标签选择基础标签
        if any("bug" in label or "syntax-error" in label for label in original_labels):
            selected_label = "bug"
        else:
            selected_label = "enhancement"

        # 构建命令
        cmd = f'gh issue create --title "{title}" --body-file /tmp/issue_body.md --label "{selected_label}"'

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
    print("🚀 创建剩余的渐进式改进Issues（使用基础标签）")
    print("=" * 60)

    # 读取Issues数据
    try:
        with open("progressive_improvement_issues.json", encoding="utf-8") as f:
            issues = json.load(f)
    except FileNotFoundError:
        print("❌ 找不到 progressive_improvement_issues.json 文件")
        sys.exit(1)

    # 跳过前4个已创建的Issues
    remaining_issues = issues[4:]  # 跳过前4个（#261-#264已创建）
    print(f"📝 跳过前4个Issues（#261-#264已创建），准备创建剩余 {len(remaining_issues)} 个Issues")
    print()

    # 创建Issues
    created_count = 0
    failed_count = 0
    created_urls = []

    for i, issue in enumerate(remaining_issues, 5):  # 从5开始编号
        print(f"\n📝 [{i-4}/{len(remaining_issues)}] 创建Issue...")

        if create_issue_with_basic_labels(issue["title"], issue["body"], issue["labels"]):
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
            print(f"✅ Issue {i-4}/{len(remaining_issues)} 创建成功")
        else:
            failed_count += 1
            print(f"❌ Issue {i-4}/{len(remaining_issues)} 创建失败")

        # 添加延迟避免API限制
        if i <= len(remaining_issues):
            print("⏳ 等待3秒避免API限制...")
            time.sleep(3)

    # 清理临时文件
    import os
    if os.path.exists("/tmp/issue_body.md"):
        os.remove("/tmp/issue_body.md")

    # 显示结果
    print("\n📊 创建结果摘要")
    print("=" * 30)
    print(f"✅ 成功创建: {created_count} 个Issues")
    print(f"❌ 创建失败: {failed_count} 个Issues")
    print(f"📈 成功率: {created_count/len(remaining_issues)*100:.1f}%")

    # 显示创建的Issue URLs
    if created_urls:
        print("\n🔗 本次创建的Issues:")
        for i, url in enumerate(created_urls, 1):
            print(f"{i}. {url}")

    print(f"\n🎯 总结: 总共创建了 {3 + created_count} 个渐进式改进Issues!")
    print("💡 查看所有Issues: gh issue list")
    print("📋 每个Issue都包含详细的渐进式改进策略指南")
    print("🎯 建议按照优先级顺序处理Issues")

if __name__ == "__main__":
    main()
