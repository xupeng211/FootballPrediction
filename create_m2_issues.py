#!/usr/bin/env python3
"""
M2 GitHub Issues创建脚本
M2 GitHub Issues Creation Script

自动创建M2规划的所有GitHub Issues
"""

import json
import requests
from pathlib import Path

# 配置GitHub API
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"  # 需要替换为实际的token
REPO_OWNER = "your-username"       # 需要替换为实际的用户名
REPO_NAME = "FootballPrediction"   # 仓库名称

def create_issue(issue_data):
    """创建单个Issue"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    payload = {
        "title": issue_data["title"],
        "body": issue_data["body"],
        "labels": issue_data["labels"],
        "milestone": issue_data.get("milestone")
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        issue = response.json()
        print(f"✅ 创建成功: {issue['title']} (#{issue['number']})")
        return issue
    else:
        print(f"❌ 创建失败: {issue_data['title']}")
        print(f"错误: {response.text}")
        return None

def main():
    """主函数"""
    # 加载Issues数据
    with open("m2_github_issues.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    issues = data["issues"]

    print(f"🚀 开始创建 {len(issues)} 个GitHub Issues...")

    created_issues = []
    for issue in issues:
        created_issue = create_issue(issue)
        if created_issue:
            created_issues.append(created_issue)

    print(f"\n🎉 成功创建 {len(created_issues)} 个Issues!")

    # 保存创建结果
    result = {
        "created_issues": len(created_issues),
        "total_issues": len(issues),
        "success_rate": len(created_issues) / len(issues) * 100,
        "created_at": datetime.now().isoformat(),
        "issues": [
            {
                "number": issue["number"],
                "title": issue["title"],
                "url": issue["html_url"]
            }
            for issue in created_issues
        ]
    }

    with open("m2_issues_creation_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
