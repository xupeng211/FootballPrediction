#!/usr/bin/env python3
"""
快速修复主要的lint错误
"""

import subprocess
from pathlib import Path


def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def fix_imports(file_path):
    """修复导入问题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        fixed_lines = []
        imports_section = True
        seen_imports = set()

        for line in lines:
            stripped = line.strip()

            # 跳过空行和注释
            if not stripped or stripped.startswith("#"):
                fixed_lines.append(line)
                continue

            # 检查是否是导入语句
            is_import = stripped.startswith("import ") or stripped.startswith("from ")

            if is_import and imports_section:
                # 去除前导空格
                fixed_line = line.lstrip()

                # 检查重复导入
                if fixed_line not in seen_imports:
                    seen_imports.add(fixed_line)
                    fixed_lines.append(fixed_line)
            elif not is_import and imports_section:
                # 遇到第一个非导入语句，结束导入部分
                imports_section = False
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        # 写回文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(fixed_lines) + "\n")

        return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def fix_bare_except(file_path):
    """修复裸露的except语句"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 简单替换裸露的except
        content = content.replace("except Exception:", "except Exception:")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return True
    except Exception as e:
        print(f"Error fixing bare except in {file_path}: {e}")
        return False


def main():
    """主函数"""
    # 获取项目根目录
    root_dir = Path(__file__).parent.parent

    # 需要修复的文件模式
    patterns = [
        "tests/unit/**/*.py",
        "tests/integration/**/*.py",
        "tests/e2e/**/*.py",
        "tests/performance/**/*.py",
    ]

    fixed_files = []

    for pattern in patterns:
        for file_path in root_dir.glob(pattern):
            if file_path.is_file():
                # 修复导入问题
                if fix_imports(file_path):
                    fixed_files.append(str(file_path))

                # 修复裸露的except
                fix_bare_except(file_path)

    print(f"Fixed {len(fixed_files)} files")

    # 运行ruff自动修复
    print("Running ruff auto-fix...")
    success, stdout, stderr = run_command("ruff check --fix", cwd=root_dir)
    if success:
        print("Ruff auto-fix completed")
    else:
        print(f"Ruff auto-fix failed: {stderr}")


if __name__ == "__main__":
    main()
