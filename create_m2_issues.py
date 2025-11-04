#!/usr/bin/env python3
"""
M2 GitHub Issues创建脚本
M2 GitHub Issues Creation Script

自动创建M2规划的所有GitHub Issues
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# 配置GitHub仓库信息
REPO_OWNER = "xupeng211"
REPO_NAME = "FootballPrediction"

def create_issue(issue_data):
    """使用GitHub CLI创建单个Issue"""
    # 跳过已存在的Issues
    existing_issues = subprocess.run([
        "gh", "issue", "list",
        "--repo", f"{REPO_OWNER}/{REPO_NAME}",
        "--search", f'"{issue_data["title"]}" in:title',
        "--json", "number,title"
    ], capture_output=True, text=True)

    if existing_issues.returncode == 0:
        existing = json.loads(existing_issues.stdout)
        if existing:
            print(f"⚠️  Issue已存在: {issue_data['title']} (#{existing[0]['number']})")
            return existing[0]

    # 构建gh命令
    cmd = [
        "gh", "issue", "create",
        "--repo", f"{REPO_OWNER}/{REPO_NAME}",
        "--title", issue_data["title"],
        "--body", issue_data["body"],
        "--label", ",".join(issue_data["labels"])
    ]

    # 添加milestone（如果需要）
    if issue_data.get("milestone"):
        milestone_id = get_milestone_id(issue_data["milestone"])
        if milestone_id:
            cmd.extend(["--milestone", str(milestone_id)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # 解析返回的URL获取Issue信息
        url = result.stdout.strip()
        if url:
            issue_number = url.split('/')[-1]
            print(f"✅ 创建成功: {issue_data['title']} (#{issue_number})")
            return {
                "number": int(issue_number),
                "title": issue_data["title"],
                "html_url": url
            }
    except subprocess.CalledProcessError as e:
        print(f"❌ 创建失败: {issue_data['title']}")
        print(f"错误: {e.stderr}")
        return None

def get_milestone_id(milestone_title):
    """获取Milestone ID"""
    try:
        result = subprocess.run([
            "gh", "api",
            f"repos/{REPO_OWNER}/{REPO_NAME}/milestones",
            "--jq", f'.[] | select(.title=="{milestone_title}") | .number'
        ], capture_output=True, text=True, check=True)
        return int(result.stdout.strip()) if result.stdout.strip() else None
    except subprocess.CalledProcessError:
        return None

def main():
    """主函数"""
    # 检查是否存在JSON文件
    if not Path("m2_github_issues.json").exists():
        print("❌ 找不到 m2_github_issues.json 文件")
        sys.exit(1)

    # 加载Issues数据
    with open("m2_github_issues.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    issues = data["issues"]
    total_issues = len(issues)

    print(f"🚀 开始创建 {total_issues} 个GitHub Issues...")
    print(f"📋 Milestone: {data['milestone']['title']}")
    print(f"📅 截止日期: {data['milestone']['due_date']}")
    print("-" * 50)

    created_issues = []
    skipped_issues = []
    failed_issues = []

    for i, issue in enumerate(issues, 1):
        print(f"\n[{i}/{total_issues}] 处理: {issue['title']}")
        created_issue = create_issue(issue)

        if created_issue:
            created_issues.append(created_issue)
        else:
            # 检查是否为已存在的Issue
            existing_issues = subprocess.run([
                "gh", "issue", "list",
                "--repo", f"{REPO_OWNER}/{REPO_NAME}",
                "--search", f'"{issue["title"]}" in:title',
                "--json", "number,title"
            ], capture_output=True, text=True)

            if existing_issues.returncode == 0:
                existing = json.loads(existing_issues.stdout)
                if existing:
                    skipped_issues.append(existing[0])
                    print(f"⚠️  跳过已存在的Issue: #{existing[0]['number']}")
                else:
                    failed_issues.append(issue)
            else:
                failed_issues.append(issue)

    print("\n" + "=" * 50)
    print("📊 创建结果统计:")
    print(f"✅ 成功创建: {len(created_issues)} 个")
    print(f"⚠️  已存在跳过: {len(skipped_issues)} 个")
    print(f"❌ 创建失败: {len(failed_issues)} 个")
    print(f"📈 总处理数: {len(created_issues) + len(skipped_issues) + len(failed_issues)} / {total_issues}")

    # 保存创建结果
    result = {
        "milestone": data["milestone"],
        "created_issues": len(created_issues),
        "skipped_issues": len(skipped_issues),
        "failed_issues": len(failed_issues),
        "total_issues": total_issues,
        "success_rate": (len(created_issues) + len(skipped_issues)) / total_issues * 100,
    
        "created_at": datetime.now().isoformat(),
        "created": [
            {
                "number": issue["number"],
                "title": issue["title"],
                "url": issue.get("html_url",
    f"https://github.com/{REPO_OWNER}/{REPO_NAME}/issues/{issue['number']}")
            }
            for issue in created_issues
        ],
        "skipped": [
            {
                "number": issue["number"],
                "title": issue["title"],
                "url": f"https://github.com/{REPO_OWNER}/{REPO_NAME}/issues/{issue['number']}"
            }
            for issue in skipped_issues
        ],
        "failed": [
            {
                "title": issue["title"],
                "labels": issue["labels"]
            }
            for issue in failed_issues
        ]
    }

    with open("m2_issues_creation_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n📄 详细结果已保存到: m2_issues_creation_result.json")

    if failed_issues:
        print(f"\n❌ 以下Issues创建失败:")
        for issue in failed_issues:
            print(f"  - {issue['title']}")

if __name__ == "__main__":
    main()
