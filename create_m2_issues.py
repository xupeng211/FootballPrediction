#!/usr/bin/env python3
"""
M2 GitHub Issues创建脚本
M2 GitHub Issues Creation Script

自动创建M2规划的所有GitHub Issues
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

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
            return {
                "number": int(issue_number),
                "title": issue_data["title"],
                "html_url": url
            }
    except subprocess.CalledProcessError:
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
        sys.exit(1)

    # 加载Issues数据
    with open("m2_github_issues.json", encoding="utf-8") as f:
        data = json.load(f)

    issues = data["issues"]
    total_issues = len(issues)


    created_issues = []
    skipped_issues = []
    failed_issues = []

    for _i, issue in enumerate(issues, 1):
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
                else:
                    failed_issues.append(issue)
            else:
                failed_issues.append(issue)


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


    if failed_issues:
        for issue in failed_issues:
            pass

if __name__ == "__main__":
    main()
