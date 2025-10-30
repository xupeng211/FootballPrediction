#!/usr/bin/env python3
"""
代码恢复脚本
从 git 历史中恢复被损坏的原始文件
保留有价值的模块化改进成果
"""

import os
import subprocess
import json
from typing import List, Set


def run_git_command(cmd: List[str]) -> str:
    """运行 git 命令"""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()


def get_files_at_commit(commit: str, path: str) -> Set[str]:
    """获取指定提交中某个路径下的所有文件"""
    try:
        output = run_git_command(["git", "ls-tree", "-r", "--name-only", commit, path])
        return set(output.split("\n")) if output else set()
    except Exception as e:
        print(f"获取文件列表失败: {e}")
        return set()


def find_corrupted_files():
    """识别被损坏的文件"""
    corrupted = []

    # 检查核心 Python 文件
    for root, dirs, files in os.walk("src"):
        # 跳过 _mod 目录（这些是新的模块化文件）
        dirs[:] = [d for d in dirs if not d.endswith("_mod")]

        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    # 尝试读取并检查语法
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # 简单检查：如果文件太小或缺少基本结构，可能已损坏
                    if len(content) < 100 or '"""' not in content:
                        corrupted.append(file_path)
                    else:
                        # 检查是否有明显的语法错误
                        try:
                            compile(content, file_path, "exec")
                        except SyntaxError:
                            corrupted.append(file_path)
            except Exception:
                    corrupted.append(file_path)

    return corrupted


def recover_file_from_git(commit: str, file_path: str):
    """从指定提交恢复单个文件"""
    try:
        # 从 git 获取文件内容
        content = run_git_command(["git", "show", f"{commit}:{file_path}"])

        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ 已恢复: {file_path}")
        return True
    except Exception as e:
        print(f"❌ 恢复失败 {file_path}: {e}")
        return False


def main():
    """主函数"""
    print("🔄 开始代码恢复流程...\n")

    # 1. 识别需要恢复的文件
    print("📋 第一步：识别损坏的文件...")
    corrupted_files = find_corrupted_files()

    if not corrupted_files:
        print("✅ 没有发现损坏的文件！")
        return

    print(f"发现 {len(corrupted_files)} 个可能损坏的文件")

    # 2. 确认恢复点
    recovery_commit = "dbdeb83"  # 损坏前的最后一次正常提交
    print(f"\n📚 第二步：从提交 {recovery_commit[:7]} 恢复文件...")

    # 3. 分类文件
    core_files = []
    test_files = []
    script_files = []

    for file_path in corrupted_files:
        if file_path.startswith("src/"):
            core_files.append(file_path)
        elif file_path.startswith("tests/"):
            test_files.append(file_path)
        elif file_path.startswith("scripts/"):
            script_files.append(file_path)

    print("\n📁 文件分类:")
    print(f"  - 核心代码: {len(core_files)} 个")
    print(f"  - 测试文件: {len(test_files)} 个")
    print(f"  - 脚本文件: {len(script_files)} 个")

    # 4. 恢复核心文件（优先）
    print("\n🔧 第三步：恢复核心代码文件...")
    recovered = 0
    failed = 0

    for file_path in core_files:
        if recover_file_from_git(recovery_commit, file_path):
            recovered += 1
        else:
            failed += 1

    # 5. 生成恢复报告
    print("\n📊 恢复报告:")
    print(f"  - 成功恢复: {recovered} 个文件")
    print(f"  - 恢复失败: {failed} 个文件")
    print(f"  - 成功率: {recovered/(recovered+failed)*100:.1f}%")

    # 6. 保存恢复记录
    recovery_log = {
        "commit": recovery_commit,
        "timestamp": "2025-01-09",
        "recovered_files": recovered,
        "failed_files": failed,
        "total_files": len(corrupted_files),
    }

    with open("recovery_log.json", "w") as f:
        json.dump(recovery_log, f, indent=2)

    print("\n✅ 恢复完成！恢复日志已保存到 recovery_log.json")
    print("\n📌 提示:")
    print("  - 已恢复损坏的原始文件")
    print("  - 保留了 *_mod/ 目录中的模块化改进")
    print("  - 建议运行 'git status' 查看变化")


if __name__ == "__main__":
    main()
