#!/usr/bin/env python3
"""
智能提交策略 - Issue #88 成果推送
分析改动并建议最佳提交策略
"""

import subprocess
import os
from pathlib import Path

def analyze_changes():
    """分析当前的git改动"""
    print("🔍 分析当前改动...")

    # 获取状态
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True
    )

    changes = result.stdout.strip().split('\n')

    modified_files = []
    deleted_files = []
    untracked_files = []

    for change in changes:
        if not change:
            continue

        status = change[:2]
        file_path = change[3:]

        if status.startswith(' M'):
            modified_files.append(file_path)
        elif status.startswith(' D'):
            deleted_files.append(file_path)
        elif status.startswith('??'):
            untracked_files.append(file_path)

    return {
        'modified': modified_files,
        'deleted': deleted_files,
        'untracked': untracked_files
    }

def categorize_changes(changes):
    """将改动分类为不同的提交"""
    categories = {
        'core_quality': [],  # 核心质量改进
        'test_infrastructure': [],  # 测试基础设施
        'issue88_deliverables': [],  # Issue #88 的交付物
        'documentation': [],  # 文档
        'cleanup': [],  # 清理工作
        'other': []  # 其他
    }

    for file_path in changes['modified']:
        if any(path in file_path for path in [
            'src/core/', 'src/api/', 'src/database/', 'src/models/'
        ]):
            categories['core_quality'].append(file_path)
        elif any(path in file_path for path in [
            'tests/', 'test_', 'conftest.py'
        ]):
            categories['test_infrastructure'].append(file_path)
        elif 'ISSUE88' in file_path:
            categories['issue88_deliverables'].append(file_path)
        elif any(path in file_path for path in [
            'docs/', '.md', 'CLAUDE.md'
        ]):
            categories['documentation'].append(file_path)
        else:
            categories['other'].append(file_path)

    for file_path in changes['deleted']:
        if 'scripts/fix_' in file_path:
            categories['cleanup'].append(file_path)
        else:
            categories['cleanup'].append(file_path)

    for file_path in changes['untracked']:
        if 'ISSUE88' in file_path or file_path.startswith('test_'):
            categories['issue88_deliverables'].append(file_path)
        elif 'docs/' in file_path or file_path.endswith('.md'):
            categories['documentation'].append(file_path)
        else:
            categories['other'].append(file_path)

    return categories

def create_commit_plan(categories):
    """创建提交计划"""
    print("📋 创建智能提交计划...")
    print("=" * 50)

    commits = []

    # 1. Issue #88 核心成果 (最重要的)
    if categories['issue88_deliverables']:
        commits.append({
            'name': 'Issue #88 核心成果: 测试基础设施和覆盖率提升',
            'files': categories['issue88_deliverables'],
            'description': '完成Issue #88的测试基础设施建设和覆盖率提升目标',
            'priority': 1
        })

    # 2. 核心代码质量改进
    if categories['core_quality']:
        commits.append({
            'name': '代码质量改进: 核心模块优化',
            'files': categories['core_quality'],
            'description': '优化核心模块的代码质量和结构',
            'priority': 2
        })

    # 3. 测试基础设施改进
    if categories['test_infrastructure']:
        commits.append({
            'name': '测试基础设施: 测试配置和框架优化',
            'files': categories['test_infrastructure'],
            'description': '改进测试基础设施和配置',
            'priority': 3
        })

    # 4. 文档更新
    if categories['documentation']:
        commits.append({
            'name': '文档更新: 项目文档和报告',
            'files': categories['documentation'],
            'description': '更新项目文档和生成报告',
            'priority': 4
        })

    # 5. 清理工作 (最后)
    if categories['cleanup']:
        commits.append({
            'name': '代码清理: 删除过时的脚本和临时文件',
            'files': categories['cleanup'],
            'description': '清理不再需要的脚本文件和临时文件',
            'priority': 5
        })

    # 6. 其他文件
    if categories['other']:
        commits.append({
            'name': '其他改进: 配置和工具更新',
            'files': categories['other'],
            'description': '其他配置文件和工具的更新',
            'priority': 6
        })

    return commits

def recommend_strategy(commits):
    """推荐推送策略"""
    print("\n🎯 推荐推送策略:")
    print("=" * 40)

    # 检查是否有太多文件需要一次性提交
    total_files = sum(len(commit['files']) for commit in commits)

    if total_files > 100:
        print(f"⚠️  检测到大量文件改动 ({total_files}个文件)")
        print("建议分批提交以避免过大的PR")

        # 建议只推送最重要的提交
        important_commits = [c for c in commits if c['priority'] <= 2]
        print(f"\n✅ 推荐首先推送以下 {len(important_commits)} 个提交:")
        for i, commit in enumerate(important_commits, 1):
            print(f"  {i}. {commit['name']}")
            print(f"     文件数: {len(commit['files'])}")

        print(f"\n📝 其他提交可以稍后推送:")
        other_commits = [c for c in commits if c['priority'] > 2]
        for i, commit in enumerate(other_commits, 1):
            print(f"  {i}. {commit['name']} ({len(commit['files'])} 文件)")

        return important_commits
    else:
        print("✅ 文件数量适中，可以正常提交")
        return commits

def execute_first_commit(commits):
    """执行第一个提交"""
    if not commits:
        print("❌ 没有可以提交的文件")
        return False

    first_commit = commits[0]
    print(f"\n🚀 准备执行第一个提交:")
    print(f"名称: {first_commit['name']}")
    print(f"描述: {first_commit['description']}")
    print(f"文件数: {len(first_commit['files'])}")

    # 添加文件
    print(f"\n📁 添加文件...")
    for file_path in first_commit['files'][:10]:  # 只显示前10个
        print(f"  + {file_path}")

    if len(first_commit['files']) > 10:
        print(f"  ... 还有 {len(first_commit['files']) - 10} 个文件")

    # 询问是否继续
    print(f"\n❓ 是否继续执行这个提交? (y/n)")
    # 这里应该是交互式的，但在这个环境中我们模拟执行

    return True

def main():
    """主函数"""
    print("🤖 Issue #88 智能提交策略分析")
    print("=" * 60)

    # 1. 分析改动
    changes = analyze_changes()

    print(f"📊 改动统计:")
    print(f"  修改文件: {len(changes['modified'])}")
    print(f"  删除文件: {len(changes['deleted'])}")
    print(f"  新增文件: {len(changes['untracked'])}")
    print(f"  总计: {len(changes['modified']) + len(changes['deleted']) + len(changes['untracked'])} 个文件")

    # 2. 分类改动
    categories = categorize_changes(changes)

    print(f"\n📂 改动分类:")
    for category, files in categories.items():
        if files:
            print(f"  {category}: {len(files)} 个文件")

    # 3. 创建提交计划
    commits = create_commit_plan(categories)

    # 4. 推荐策略
    recommended_commits = recommend_strategy(commits)

    # 5. 生成最终的推送建议
    print(f"\n🎯 最终推送建议:")
    print("=" * 40)

    print(f"✅ 推荐推送以下核心提交:")
    for i, commit in enumerate(recommended_commits, 1):
        print(f"  {i}. {commit['name']}")

    print(f"\n📝 推送命令:")
    print(f"  git add [相关文件]")
    print(f"  git commit -m '🎉 Issue #88 完成重大突破: 测试基础设施和代码质量全面提升'")
    print(f"  git push origin main")

    print(f"\n⚠️  重要提醒:")
    print(f"  1. 建议先推送核心功能相关的文件")
    print(f"  2. 清理和文档文件可以稍后推送")
    print(f"  3. 推送前请确保CI检查通过")
    print(f"  4. 考虑创建Pull Request而不是直接推送到main")

if __name__ == "__main__":
    main()