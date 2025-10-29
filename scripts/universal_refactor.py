#!/usr/bin/env python3
"""
通用长文件重构工具
可以处理任意长文件的智能拆分
"""

import os
import re
import ast


def analyze_any_file(filepath):
    """分析任意文件的结构"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 尝试解析AST
        try:
            tree = ast.parse(content)
            functions = []
            classes = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(
                        {
                            "name": node.name,
                            "lineno": node.lineno,
                            "type": "function",
                            "decorators": [
                                d.id if isinstance(d, ast.Name) else str(d)
                                for d in node.decorator_list
                            ],
                        }
                    )
                elif isinstance(node, ast.ClassDef):
                    classes.append(
                        {
                            "name": node.name,
                            "lineno": node.lineno,
                            "type": "class",
                            "methods": [
                                n.name for n in node.body if isinstance(n, ast.FunctionDef)
                            ],
                        }
                    )

            return {
                "functions": functions,
                "classes": classes,
                "total_lines": len(content.split("\n")),
                "content": content,
                "ast_parsed": True,
            }
        except SyntaxError:
            # 如果无法解析AST，使用行分析
            return analyze_by_lines(content)
    except Exception as e:
        print(f"分析文件 {filepath} 失败: {e}")
        return None


def analyze_by_lines(content):
    """按行分析文件内容"""
    lines = content.split("\n")
    functions = []
    classes = []

    for i, line in enumerate(lines):
        line_num = i + 1
        line.strip()

        # 识别函数定义
        if re.match(r"^\s*def\s+\w+", line):
            func_name = re.search(r"def\s+(\w+)", line)
            if func_name:
                functions.append(
                    {
                        "name": func_name.group(1),
                        "lineno": line_num,
                        "type": "function",
                        "decorators": [],
                    }
                )

        # 识别类定义
        elif re.match(r"^\s*class\s+\w+", line):
            class_name = re.search(r"class\s+(\w+)", line)
            if class_name:
                classes.append(
                    {
                        "name": class_name.group(1),
                        "lineno": line_num,
                        "type": "class",
                        "methods": [],
                    }
                )

    return {
        "functions": functions,
        "classes": classes,
        "total_lines": len(lines),
        "content": content,
        "ast_parsed": False,
    }


def split_long_file(filepath, max_lines_per_file=250):
    """拆分长文件"""
    print(f"🔧 分析文件: {filepath}")

    analysis = analyze_any_file(filepath)
    if not analysis:
        print("❌ 文件分析失败")
        return False

    print("📊 分析结果:")
    print(f"   总行数: {analysis['total_lines']}")
    print(f"   函数数: {len(analysis['functions'])}")
    print(f"   类数: {len(analysis['classes'])}")
    print(f"   AST解析: {'成功' if analysis['ast_parsed'] else '失败 (使用行分析)'}")

    if analysis["total_lines"] <= max_lines_per_file:
        print(f"✅ 文件长度 ({analysis['total_lines']} 行) 在限制范围内，无需拆分")
        return True

    # 生成拆分策略
    all_items = analysis["functions"] + analysis["classes"]
    all_items.sort(key=lambda x: x["lineno"])

    # 按功能分组拆分
    groups = []
    current_group = []
    current_lines = 0

    for item in all_items:
        # 估算这个项目的大概行数
        item_lines = 50  # 默认估算
        if current_lines + item_lines > max_lines_per_file and current_group:
            groups.append(current_group)
            current_group = [item]
            current_lines = item_lines
        else:
            current_group.append(item)
            current_lines += item_lines

    if current_group:
        groups.append(current_group)

    # 读取原文件内容
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 创建拆分文件
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    output_dir = os.path.dirname(filepath)
    created_files = []

    for i, group in enumerate(groups):
        if group:
            # 创建新文件名
            if len(groups) == 1:
                filename = f"{base_name}_refactored.py"
            else:
                filename = f"{base_name}_part_{i+1}.py"

            filepath_new = os.path.join(output_dir, filename)

            # 提取相关代码
            relevant_lines = []

            # 添加文件头
            relevant_lines.append('"""\n')
            relevant_lines.append(f"{base_name} - 第{i+1}部分\n")
            relevant_lines.append(f"从原文件 {os.path.basename(filepath)} 拆分\n")
            relevant_lines.append(f'创建时间: {__import__("datetime").datetime.now()}\n')
            relevant_lines.append(f"包含项目: {len(group)} 个 (函数/类)\n")
            relevant_lines.append('"""\n\n')

            # 添加基础导入
            relevant_lines.append("import pytest\n")
            relevant_lines.append("from unittest.mock import Mock, patch\n")
            relevant_lines.append("import sys\n")
            relevant_lines.append("import os\n\n")

            # 提取每个项目的代码
            for item in group:
                start_line = item["lineno"] - 1
                if start_line < len(lines):
                    # 找到这个项目的结束位置
                    end_line = len(lines)
                    for next_item in all_items:
                        if next_item["lineno"] > item["lineno"]:
                            end_line = next_item["lineno"] - 1
                            break

                    # 提取代码，确保缩进正确
                    for j in range(start_line, min(end_line, len(lines))):
                        line_content = lines[j]
                        if j == start_line:
                            # 确保第一行没有多余缩进
                            if line_content.strip().startswith(("def ", "class ", "@")):
                                relevant_lines.append(line_content.lstrip() + "\n")
                            else:
                                relevant_lines.append(line_content)
                        else:
                            relevant_lines.append(line_content)

                    relevant_lines.append("\n")

            # 写入文件
            os.makedirs(os.path.dirname(filepath_new), exist_ok=True)
            with open(filepath_new, "w", encoding="utf-8") as f:
                f.writelines(relevant_lines)

            created_files.append(filepath_new)
            print(f"✅ 创建文件: {filename} ({len(relevant_lines)} 行)")

    # 备份原文件
    backup_file = filepath + ".backup"
    if not os.path.exists(backup_file):
        os.rename(filepath, backup_file)
        print(f"📦 原文件备份至: {backup_file}")

    print("\n📊 拆分总结:")
    print(f"   原文件: {filepath} ({analysis['total_lines']} 行)")
    print(f"   拆分文件数: {len(created_files)}")
    print("   创建文件:")
    for f in created_files:
        lines_count = len(open(f, "r", encoding="utf-8").readlines())
        print(f"     - {os.path.basename(f)} ({lines_count} 行)")

    return True


def main():
    """主函数"""
    # 检查命令行参数
    import sys

    if len(sys.argv) > 1:
        target_file = sys.argv[1]
        if not os.path.exists(target_file):
            print(f"❌ 文件不存在: {target_file}")
            return
    else:
        # 默认处理日期时间工具测试文件
        target_file = "tests/unit/utils/test_date_time_utils.py"
        if not os.path.exists(target_file):
            print(f"❌ 默认文件不存在: {target_file}")
            print("用法: python3 universal_refactor.py [文件路径]")
            return

    print("🚀 开始通用重构...")
    print(f"目标文件: {target_file}")

    if split_long_file(target_file):
        print("✅ 文件重构完成")

        # 验证拆分后的文件
        print("\n🔍 验证拆分结果...")
        base_name = os.path.splitext(os.path.basename(target_file))[0]
        output_dir = os.path.dirname(target_file)

        # 查找拆分文件
        import glob

        pattern = os.path.join(output_dir, f"{base_name}_part_*.py")
        split_files = glob.glob(pattern)

        if not split_files:
            pattern = os.path.join(output_dir, f"{base_name}_refactored.py")
            split_files = glob.glob(pattern)

        syntax_errors = 0
        for split_file in split_files:
            try:
                with open(split_file, "r", encoding="utf-8") as f:
                    content = f.read()
                ast.parse(content)
                print(f"  ✅ {os.path.basename(split_file)}: 语法正确")
            except SyntaxError as e:
                print(f"  ❌ {os.path.basename(split_file)}: 第{e.lineno}行语法错误")
                syntax_errors += 1

        if syntax_errors == 0:
            print("🎉 所有拆分文件语法正确！")
        else:
            print(f"⚠️ 有 {syntax_errors} 个文件存在语法错误")
    else:
        print("❌ 文件重构失败")


if __name__ == "__main__":
    main()
