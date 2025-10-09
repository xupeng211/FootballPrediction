#!/usr/bin/env python3
"""
恢复用户的代码拆分成果

从commit 58498a0中提取所有拆分的模块，恢复用户的代码拆分工作。
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, List, Set


def run_git_command(cmd: List[str]) -> str:
    """运行git命令并返回输出"""
    result = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    if result.returncode != 0:
        print(f"命令失败: {' '.join(cmd)}")
        print(f"错误: {result.stderr}")
        return ""
    return result.stdout


def get_files_from_commit(commit: str, path: str = "") -> Set[str]:
    """获取指定commit中特定路径下的所有文件"""
    cmd = ["git", "ls-tree", "-r", "--name-only", commit]
    if path:
        cmd.append(path)

    output = run_git_command(cmd)
    files = set()
    for line in output.strip().split("\n"):
        if line.strip():
            files.add(line.strip())
    return files


def get_file_content_at_commit(commit: str, file_path: str) -> str:
    """获取指定commit中文件的内容"""
    cmd = ["git", "show", f"{commit}:{file_path}"]
    output = run_git_command(cmd)
    return output


def restore_split_modules():
    """恢复用户拆分的所有模块"""

    print("=" * 60)
    print("恢复用户的代码拆分成果")
    print("=" * 60)

    # 用户拆分的commit
    split_commit = "58498a0"

    # 检查commit是否存在
    cmd = ["git", "cat-file", "-t", split_commit]
    result = run_git_command(cmd)
    if not result or "commit" not in result:
        print(f"错误: 找不到commit {split_commit}")
        return

    print(f"从commit {split_commit} 恢复拆分代码...\n")

    # 获取该commit中的所有文件
    all_files = get_files_from_commit(split_commit)

    # 识别拆分的模块（包含_mod的目录和文件）
    split_modules = []
    for file_path in all_files:
        if "_mod" in file_path or file_path.endswith("_mod.py"):
            split_modules.append(file_path)

    print(f"发现 {len(split_modules)} 个拆分模块:")
    for module in sorted(split_modules):
        print(f"  - {module}")

    print("\n开始恢复拆分模块...")

    restored_count = 0
    for module_path in split_modules:
        # 跳过已经存在的文件
        if os.path.exists(module_path):
            print(f"跳过已存在的文件: {module_path}")
            continue

        # 获取文件内容
        content = get_file_content_at_commit(split_commit, module_path)

        if content:
            # 确保目录存在
            full_path = Path(module_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            with open(module_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"✓ 恢复: {module_path}")
            restored_count += 1
        else:
            print(f"✗ 无法恢复: {module_path}")

    print(f"\n成功恢复 {restored_count} 个拆分模块!")

    # 特别检查audit_service的拆分
    print("\n" + "=" * 60)
    print("检查audit_service拆分情况:")
    print("=" * 60)

    audit_mod_dir = Path("src/services/audit_service_mod")
    if audit_mod_dir.exists():
        audit_files = list(audit_mod_dir.rglob("*.py"))
        print(f"audit_service_mod目录存在，包含 {len(audit_files)} 个文件:")
        for f in sorted(audit_files):
            print(f"  - {f.relative_to('.')}")
    else:
        print("audit_service_mod目录不存在")

    # 检查其他重要的拆分
    important_splits = [
        "src/services/manager_mod.py",
        "src/services/data_processing_mod",
        "src/database/connection_mod",
        "src/cache/ttl_cache_improved_mod",
        "src/data/processing/football_data_cleaner_mod",
        "src/data/quality/exception_handler_mod",
        "src/monitoring/system_monitor_mod",
        "src/monitoring/metrics_collector_enhanced_mod",
        "src/scheduler/recovery_handler_mod",
        "src/collectors/odds_collector_improved.py",
        "src/collectors/scores_collector_improved.py",
    ]

    print("\n检查其他重要拆分:")
    for split_path in important_splits:
        if os.path.exists(split_path):
            print(f"✓ 存在: {split_path}")
        else:
            print(f"✗ 缺失: {split_path}")

    print("\n" + "=" * 60)
    print("代码拆分恢复完成!")
    print("=" * 60)
    print("\n建议下一步:")
    print("1. 运行 'make lint' 检查代码质量")
    print("2. 运行 'make test-quick' 快速测试")
    print("3. 根据需要调整导入语句")


if __name__ == "__main__":
    restore_split_modules()
