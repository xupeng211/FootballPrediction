#!/usr/bin/env python3
"""
完善模块文档 - 为重要模块添加更好的文档字符串
"""

import ast
from pathlib import Path
from typing import List


def find_modules_missing_docs(directory: Path) -> List[Path]:
    """查找缺少文档的模块"""
    modules_missing_docs = []

    for py_file in directory.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        # 跳过测试文件和__init__.py
        if py_file.name.startswith("test_") or py_file.name == "__init__.py":
            continue

        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否有模块级文档字符串
        try:
            tree = ast.parse(content)
            if (
                tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
                and isinstance(tree.body[0].value.value, str)
            ):
                continue  # 有文档字符串
        except Exception:
            pass

        modules_missing_docs.append(py_file)

    return modules_missing_docs


def generate_module_docstring(file_path: Path) -> str:
    """根据文件路径生成模块文档字符串"""
    rel_path = str(file_path).replace("src/", "")
    parts = rel_path.replace(".py", "").split("/")

    # 确定模块类型
    module_type = "未知"
    if "api" in parts:
        module_type = "API"
    elif "database" in parts:
        module_type = "数据库"
    elif "services" in parts:
        module_type = "服务"
    elif "models" in parts:
        module_type = "模型"
    elif "cache" in parts:
        module_type = "缓存"
    elif "monitoring" in parts:
        module_type = "监控"
    elif "streaming" in parts:
        module_type = "流处理"
    elif "tasks" in parts:
        module_type = "任务"
    elif "core" in parts:
        module_type = "核心"
    elif "utils" in parts:
        module_type = "工具"
    elif "features" in parts:
        module_type = "特征工程"
    elif "data" in parts:
        module_type = "数据"
    elif "cqrs" in parts:
        module_type = "CQRS"
    elif "observers" in parts:
        module_type = "观察者"
    elif "repositories" in parts:
        module_type = "仓储"
    elif "dependencies" in parts:
        module_type = "依赖注入"
    elif "patterns" in parts:
        module_type = "设计模式"

    module_name = parts[-1].replace("_", " ").title()

    # 生成文档字符串
    docstring = f'"""\n{module_name} - {module_type}模块\n\n'
    docstring += f"提供 {module_name.lower()} 相关的{module_type}功能。\n\n"
    docstring += "主要功能：\n"
    docstring += f"- [待补充 - {module_name}的主要功能]\n\n"
    docstring += "使用示例：\n"
    docstring += f"    from {'.'.join(parts[:-1])} import {module_name}\n"
    docstring += "    # 使用示例代码\n\n"
    docstring += "注意事项：\n"
    docstring += "- [待补充 - 使用注意事项]\n"
    docstring += '"""\n\n'

    return docstring


def enhance_file_docs(file_path: Path):
    """为文件添加文档字符串"""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 检查是否已有文档
    first_10_lines = "".join(lines[:10])
    if '"""' in first_10_lines:
        print(f"  ⚠️  {file_path}: 已有文档，跳过")
        return False

    # 找到第一个导入或类/函数定义
    first_code_line = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and (
            stripped.startswith(("import ", "from ", "class ", "def ", "async def "))
        ):
            first_code_line = i
            break

    # 生成并插入文档
    docstring = generate_module_docstring(file_path)
    lines.insert(first_code_line, docstring)

    # 写回文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return True


def main():
    """主函数"""
    print("=" * 80)
    print("📚 完善模块文档")
    print("=" * 80)

    # 查找缺少文档的模块
    print("\n🔍 查找缺少文档的模块...")

    # 优先处理重要目录
    important_dirs = [
        Path("src/api"),
        Path("src/core"),
        Path("src/services"),
        Path("src/database"),
        Path("src/cache"),
        Path("src/monitoring"),
    ]

    all_missing_docs = []
    for directory in important_dirs:
        if directory.exists():
            missing = find_modules_missing_docs(directory)
            all_missing_docs.extend(missing)
            print(f"  {directory}: {len(missing)} 个文件缺少文档")

    print(f"\n总计: {len(all_missing_docs)} 个文件缺少文档")

    if not all_missing_docs:
        print("\n✅ 所有重要模块都有文档！")
        return

    # 显示前10个文件
    print("\n📋 需要添加文档的文件（前10个）:")
    for file_path in all_missing_docs[:10]:
        rel_path = str(file_path).replace("src/", "")
        print(f"  - {rel_path}")

    # 询问是否继续
    print("\n📝 开始为文件添加文档...")

    fixed_count = 0
    for file_path in all_missing_docs[:20]:  # 只处理前20个
        rel_path = str(file_path).replace("src/", "")
        print(f"\n处理: {rel_path}")

        if enhance_file_docs(file_path):
            print("  ✅ 已添加文档")
            fixed_count += 1

    print("\n" + "=" * 80)
    print(f"✅ 完成！已为 {fixed_count} 个文件添加文档")
    print("=" * 80)

    if len(all_missing_docs) > 20:
        print(f"\n⚠️  还有 {len(all_missing_docs) - 20} 个文件需要处理")
        print("再次运行脚本继续处理")


if __name__ == "__main__":
    main()
