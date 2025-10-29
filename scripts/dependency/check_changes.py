#!/usr/bin/env python3
"""
检测依赖变更并提醒AI工具遵循正确的管理流程
"""

import subprocess
from pathlib import Path


def check_requirement_changes():
    """检查requirements目录的变更"""
    try:
        # 获取变更的requirements文件
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "requirements/"],
            capture_output=True,
            text=True,
        )

        changed_files = result.stdout.strip().split("\n") if result.stdout.strip() else []

        # 过滤出.in文件的变更
        in_files = [f for f in changed_files if f.endswith(".in")]
        lock_files = [f for f in changed_files if f.endswith(".lock")]

        if in_files and not lock_files:
            print("\n" + "=" * 60)
            print("🔍 检测到依赖变更！")
            print("=" * 60)
            print(f"\n变更的文件: {', '.join(in_files)}")
            print("\n⚠️  重要提醒：")
            print("您刚刚修改了依赖配置文件。")
            print("为确保依赖管理的一致性，请阅读 CLAUDE.md 中的依赖管理方案。")
            print("\n📋 必要的后续步骤：")
            print("1. 运行 'make lock-deps' 生成锁定文件")
            print("2. 运行 'make verify-deps' 验证依赖一致性")
            print("3. 提交所有 .lock 文件")
            print("\n💡 推荐使用辅助脚本：")
            print("   python scripts/dependency/add_dependency.py <package>")
            print("\n📖 详细信息请查看 CLAUDE.md 的'依赖管理'部分")
            print("=" * 60)

            # 询问是否要运行lock-deps
            response = input("\n是否现在运行 'make lock-deps'? (y/N): ")
            if response.lower() in ["y", "yes"]:
                print("\n🔒 正在锁定依赖...")
                subprocess.run(["make", "lock-deps"])
                print("✅ 完成！请记得提交生成的 .lock 文件。")

        return in_files or lock_files

    except Exception as e:
        print(f"检查依赖变更时出错: {e}")
        return False


def check_python_imports():
    """检查新添加的import语句"""
    try:
        # 获取暂存的Python文件
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "*.py"],
            capture_output=True,
            text=True,
        )

        python_files = result.stdout.strip().split("\n") if result.stdout.strip() else []

        new_imports = set()

        for py_file in python_files:
            if py_file and Path(py_file).exists():
                # 获取新增的行
                diff_result = subprocess.run(
                    ["git", "diff", "--cached", py_file], capture_output=True, text=True
                )

                lines = diff_result.stdout.split("\n")
                for line in lines:
                    if line.startswith("+") and ("import " in line or "from " in line):
                        # 提取包名
                        if "from " in line:
                            pkg = line.split("from ")[1].split(" ")[1].split(".")[0]
                        else:
                            pkg = line.split("import ")[1].split(" ")[0].split(".")[0]

                        # 过滤掉标准库和本地模块
                        if pkg not in [
                            "os",
                            "sys",
                            "json",
                            "datetime",
                            "pathlib",
                            "typing",
                            "unittest",
                            "pytest",
                            "fastapi",
                            "sqlalchemy",
                            "pydantic",
                            "src",
                        ]:
                            new_imports.add(pkg)

        if new_imports:
            print("\n" + "=" * 60)
            print("📦 检测到新的导入！")
            print("=" * 60)
            print(f"新导入的包: {', '.join(sorted(new_imports))}")
            print("\n⚠️  请确保：")
            print("1. 这些包已经在requirements/中声明")
            print("2. 已运行 'make lock-deps' 更新依赖")
            print("3. 已运行 'make verify-deps' 验证一致性")
            print("\n如果还没有添加依赖，请使用：")
            print("   python scripts/dependency/add_dependency.py <package>")
            print("=" * 60)

    except Exception as e:
        print(f"检查导入时出错: {e}")


def main():
    print("🔍 正在检查依赖变更...")

    # 检查requirements文件变更
    has_changes = check_requirement_changes()

    # 检查新的导入
    check_python_imports()

    if has_changes:
        print("\n✅ 检查完成！请按照上述提示操作。")
    else:
        print("\n✅ 没有检测到依赖变更。")


if __name__ == "__main__":
    main()
