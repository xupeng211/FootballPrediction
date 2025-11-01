#!/usr/bin/env python3
"""
综合语法验证器
检查所有Python文件的语法错误并提供修复建议
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple, Optional

def check_syntax_errors(file_path: Path) -> List[Tuple[int, str, str]]:
    """检查文件的语法错误"""
    errors = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 尝试解析AST
        try:
            ast.parse(content)
        except SyntaxError as e:
            errors.append((e.lineno or 0, e.msg, f"SyntaxError: {e.text or ''}"))
        except Exception as e:
            errors.append((0, str(e), "Parse Error"))

    except UnicodeDecodeError:
        errors.append((0, "Encoding Error", "无法解码文件"))
    except Exception as e:
        errors.append((0, str(e), "File Read Error"))

    return errors

def find_all_python_files(root_dir: Path) -> List[Path]:
    """查找所有Python文件"""
    python_files = []
    for pattern in ["*.py"]:
        python_files.extend(root_dir.rglob(pattern))
    return python_files

def main():
    """主函数"""
    print("🔍 综合语法验证器启动...")

    # 查找所有Python文件（排除虚拟环境）
    root_dir = Path(".")
    python_files = find_all_python_files(root_dir)

    # 过滤掉虚拟环境中的文件
    python_files = [f for f in python_files if ".venv" not in str(f) and "node_modules" not in str(f)]

    print(f"📁 找到 {len(python_files)} 个Python文件")

    total_errors = 0
    files_with_errors = []

    for file_path in python_files:
        errors = check_syntax_errors(file_path)
        if errors:
            files_with_errors.append((file_path, errors))
            total_errors += len(errors)

    print(f"\n📊 语法检查结果:")
    print(f"  检查文件数: {len(python_files)}")
    print(f"  有错误的文件: {len(files_with_errors)}")
    print(f"  总错误数: {total_errors}")

    if files_with_errors:
        print(f"\n🔧 需要修复的文件:")
        for file_path, errors in files_with_errors[:10]:  # 只显示前10个
            print(f"  📄 {file_path}")
            for line_no, msg, context in errors[:3]:  # 每个文件只显示前3个错误
                print(f"    行 {line_no}: {msg}")

        if len(files_with_errors) > 10:
            print(f"  ... 还有 {len(files_with_errors) - 10} 个文件有错误")

    print(f"\n✅ 语法验证完成!")
    return total_errors == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)