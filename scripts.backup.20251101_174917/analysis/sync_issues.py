#!/usr/bin/env python3
"""
GitHub Issues 双向同步脚本
========================

这个脚本实现了 GitHub Issues 与本地 YAML 文件的双向同步功能。

功能：
- pull: 从 GitHub 拉取 Issues 到本地 issues.yaml
- push: 将本地 issues.yaml 推送到 GitHub
- sync: 先 pull 再 push，保持双向同步

使用方法：
    python scripts/sync_issues.py pull
    python scripts/sync_issues.py push
    python scripts/sync_issues.py sync

环境变量：
    GITHUB_TOKEN: GitHub Personal Access Token
    GITHUB_REPO: 仓库路径，格式: owner/repo

作者: DevOps Engineer
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

try:
    from github import Github
    from github.Repository import Repository
except ImportError:
    print("❌ 缺少依赖库，请安装: pip install PyGithub pyyaml")
    sys.exit(1)


# 配置常量
LOCAL_ISSUES_FILE = "issues.yaml"
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
GITHUB_REPO_ENV = "GITHUB_REPO"


def load_local_issues() -> List[Dict[str, Any]]:
    """
    从本地 YAML 文件加载 Issues 数据

    Returns:
        List[Dict]: Issues 数据列表，如果文件不存在则返回空列表

    Raises:
        Exception: 文件读取或解析失败时抛出异常
    """
    local_file = Path(LOCAL_ISSUES_FILE)

    if not local_file.exists():
        print(f"📝 本地文件 {LOCAL_ISSUES_FILE} 不存在，返回空列表")
        return []

    try:
        with open(local_file, "r", encoding="utf-8") as f:
            issues_data = yaml.safe_load(f) or []

        # 确保返回的是列表格式
        if not isinstance(issues_data, list):
            print(f"⚠️  警告: {LOCAL_ISSUES_FILE} 格式不正确，应为列表格式")
            return []

        print(f"📂 成功加载 {len(issues_data)} 个本地 Issues")
        return issues_data

    except Exception as e:
        print(f"❌ 读取本地文件失败: {e}")
        raise


def save_local_issues(issues: List[Dict[str, Any]]) -> None:
    """
    将 Issues 数据保存到本地 YAML 文件

    Args:
        issues: Issues 数据列表

    Raises:
        Exception: 文件写入失败时抛出异常
    """
    try:
        # 确保文件目录存在
        local_file = Path(LOCAL_ISSUES_FILE)
        local_file.parent.mkdir(parents=True, exist_ok=True)

        with open(local_file, "w", encoding="utf-8") as f:
            yaml.dump(
                issues,
                f,
                default_flow_style=False,
                allow_unicode=True,
                indent=2,
                sort_keys=False,
            )

        print(f"💾 成功保存 {len(issues)} 个 Issues 到 {LOCAL_ISSUES_FILE}")

    except Exception as e:
        print(f"❌ 保存本地文件失败: {e}")
        raise


def fetch_remote_issues(repo: Repository) -> List[Dict[str, Any]]:
    """
    从 GitHub 仓库获取所有 Issues

    Args:
        repo: GitHub 仓库对象

    Returns:
        List[Dict]: 远程 Issues 数据列表

    Raises:
        Exception: GitHub API 调用失败时抛出异常
    """
    try:
        # 获取所有状态的 Issues (open + closed)
        github_issues = list(repo.get_issues(state="all"))

        issues_data = []
        for issue in github_issues:
            # 转换为本地格式
            issue_dict = {
                "id": issue.number,
                "title": issue.title,
                "body": issue.body or "",
                "state": issue.state,
                "labels": [label.name for label in issue.labels],
            }
            issues_data.append(issue_dict)

        print(f"🔍 成功获取 {len(issues_data)} 个远程 Issues")
        return issues_data

    except Exception as e:
        print(f"❌ 获取远程 Issues 失败: {e}")
        raise


def update_remote_issues(
    repo: Repository, local_issues: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    将本地 Issues 推送到 GitHub，更新远程仓库

    Args:
        repo: GitHub 仓库对象
        local_issues: 本地 Issues 数据列表

    Returns:
        List[Dict]: 更新后的 Issues 数据列表（包含新创建 Issue 的 ID）

    Raises:
        Exception: GitHub API 调用失败时抛出异常
    """
    updated_issues = []

    try:
        # 获取远程现有 Issues 映射
        remote_issues = {issue.number: issue for issue in repo.get_issues(state="all")}

        for local_issue in local_issues:
            issue_id = local_issue.get("id")

            if not issue_id:
                # 本地新增 Issue，需要在 GitHub 创建
                try:
                    new_issue = repo.create_issue(
                        title=local_issue["title"],
                        body=local_issue.get("body", ""),
                        labels=local_issue.get("labels", []),
                    )

                    # 更新本地数据，添加新的 ID
                    local_issue["id"] = new_issue.number
                    local_issue["state"] = new_issue.state
                    updated_issues.append(local_issue)

                    print(f"✅ 成功创建新 Issue #{new_issue.number}: {local_issue['title']}")

                except Exception as e:
                    print(f"❌ 创建 Issue '{local_issue['title']}' 失败: {e}")
                    # 保留原始数据，继续处理其他 Issues
                    updated_issues.append(local_issue)

            else:
                # 检查远程是否存在对应 Issue
                if issue_id in remote_issues:
                    remote_issue = remote_issues[issue_id]

                    # 检查是否需要更新
                    need_update = (
                        remote_issue.title != local_issue["title"]
                        or remote_issue.body != local_issue.get("body", "")
                        or remote_issue.state != local_issue.get("state", "open")
                        or [label.name for label in remote_issue.labels]
                        != local_issue.get("labels", [])
                    )

                    if need_update:
                        try:
                            # 更新远程 Issue
                            remote_issue.edit(
                                title=local_issue["title"],
                                body=local_issue.get("body", ""),
                                state=local_issue.get("state", "open"),
                                labels=local_issue.get("labels", []),
                            )
                            print(f"🔄 成功更新 Issue #{issue_id}: {local_issue['title']}")

                        except Exception as e:
                            print(f"❌ 更新 Issue #{issue_id} 失败: {e}")

                else:
                    print(f"⚠️  警告: 本地 Issue #{issue_id} 在远程不存在，可能已被删除")

                updated_issues.append(local_issue)

        print(f"📤 完成推送，处理了 {len(updated_issues)} 个 Issues")
        return updated_issues

    except Exception as e:
        print(f"❌ 推送 Issues 失败: {e}")
        raise


def sync_issues(action: str) -> None:
    """
    执行 Issues 同步操作

    Args:
        action: 同步动作 ('pull', 'push', 'sync')

    Raises:
        SystemExit: 配置错误或操作失败时退出程序
    """
    # 检查环境变量配置
    github_token = os.getenv(GITHUB_TOKEN_ENV)
    github_repo = os.getenv(GITHUB_REPO_ENV)

    if not github_token:
        print(f"❌ 缺少环境变量: {GITHUB_TOKEN_ENV}")
        print("💡 请设置 GitHub Personal Access Token")
        print("   获取地址: https://github.com/settings/tokens")
        sys.exit(1)

    if not github_repo:
        print(f"❌ 缺少环境变量: {GITHUB_REPO_ENV}")
        print("💡 请设置仓库路径，格式: owner/repo")
        print(f"   例如: export {GITHUB_REPO_ENV}=microsoft/vscode")
        sys.exit(1)

    # 验证仓库路径格式
    if "/" not in github_repo or len(github_repo.split("/")) != 2:
        print(f"❌ 仓库路径格式错误: {github_repo}")
        print("💡 正确格式: owner/repo (例如: microsoft/vscode)")
        sys.exit(1)

    try:
        # 初始化 GitHub 客户端
        github_client = Github(github_token)
        repo = github_client.get_repo(github_repo)

        print(f"🔗 连接到仓库: {github_repo}")

        if action == "pull":
            # 从远程拉取到本地
            print("⬇️  开始从 GitHub 拉取 Issues...")
            remote_issues = fetch_remote_issues(repo)
            save_local_issues(remote_issues)
            print("✅ Pull 操作完成")

        elif action == "push":
            # 从本地推送到远程
            print("⬆️  开始推送本地 Issues 到 GitHub...")
            local_issues = load_local_issues()
            if not local_issues:
                print("📝 本地没有 Issues 数据，跳过推送")
                return
            updated_issues = update_remote_issues(repo, local_issues)
            save_local_issues(updated_issues)  # 保存更新后的数据（包含新 ID）
            print("✅ Push 操作完成")

        elif action == "sync":
            # 双向同步：先 pull 再 push
            print("🔄 开始双向同步...")

            # 步骤1: Pull
            print("⬇️  第一步: 从 GitHub 拉取最新数据...")
            remote_issues = fetch_remote_issues(repo)
            save_local_issues(remote_issues)

            # 步骤2: Push
            print("⬆️  第二步: 推送本地修改到 GitHub...")
            local_issues = load_local_issues()
            updated_issues = update_remote_issues(repo, local_issues)
            save_local_issues(updated_issues)

            print("✅ 双向同步完成")

        else:
            print(f"❌ 未知操作: {action}")
            print("💡 支持的操作: pull, push, sync")
            sys.exit(1)

    except Exception as e:
        print(f"❌ 同步操作失败: {e}")
        sys.exit(1)


def main():
    """主函数：处理命令行参数并执行相应操作"""
    parser = argparse.ArgumentParser(
        description="GitHub Issues 双向同步工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/sync_issues.py pull   # 从 GitHub 拉取到本地
  python scripts/sync_issues.py push   # 推送本地到 GitHub
  python scripts/sync_issues.py sync   # 双向同步

环境变量:
  GITHUB_TOKEN    GitHub Personal Access Token
  GITHUB_REPO     仓库路径 (格式: owner/repo)
        """,
    )

    parser.add_argument(
        "action",
        choices=["pull", "push", "sync"],
        help="同步操作: pull(拉取), push(推送), sync(双向同步)",
    )

    args = parser.parse_args()

    print("🚀 GitHub Issues 同步工具启动")
    print(f"📋 执行操作: {args.action}")
    print(f"📁 本地文件: {LOCAL_ISSUES_FILE}")

    sync_issues(args.action)


if __name__ == "__main__":
    main()
