#!/usr/bin/env python3
"""
简单文件重构工具 - 按功能拆分长测试文件
"""

import os
import re
import ast


def analyze_test_file(filepath):
    """分析测试文件结构"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 解析AST
        tree = ast.parse(content)

        # 收集所有函数和类
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
                            d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list
                        ],
                    }
                )
            elif isinstance(node, ast.ClassDef):
                classes.append(
                    {
                        "name": node.name,
                        "lineno": node.lineno,
                        "type": "class",
                        "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                    }
                )

        return {
            "functions": functions,
            "classes": classes,
            "total_lines": len(content.split("\n")),
            "content": content,
        }
    except Exception as e:
        print(f"分析文件 {filepath} 失败: {e}")
        return None


def split_prediction_algorithms_test():
    """拆分预测算法测试文件"""
    source_file = "tests/unit/domain/test_prediction_algorithms_comprehensive.py"

    print("🔧 分析预测算法测试文件...")
    analysis = analyze_test_file(source_file)

    if not analysis:
        print("❌ 文件分析失败")
        return False

    print("📊 分析结果:")
    print(f"   总行数: {analysis['total_lines']}")
    print(f"   函数数: {len(analysis['functions'])}")
    print(f"   类数: {len(analysis['classes'])}")

    # 简单拆分策略：按函数数量平分
    total_items = len(analysis["functions"]) + len(analysis["classes"])
    items_per_file = max(5, total_items // 4)  # 最多4个文件，每个至少5个项

    # 分组
    all_items = analysis["functions"] + analysis["classes"]
    all_items.sort(key=lambda x: x["lineno"])  # 按行号排序

    groups = []
    current_group = []

    for item in all_items:
        current_group.append(item)
        if len(current_group) >= items_per_file:
            groups.append(current_group)
            current_group = []

    if current_group:  # 添加最后一组
        groups.append(current_group)

    # 读取原文件内容
    with open(source_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 为每个分组创建新文件
    output_dir = "tests/unit/domain/"
    created_files = []

    for i, group in enumerate(groups):
        if group:
            # 创建新文件
            filename = os.path.join(output_dir, f"test_prediction_algorithms_part_{i+1}.py")

            # 提取相关代码
            relevant_lines = []

            # 添加文件头
            relevant_lines.append('"""\n')
            relevant_lines.append(f"预测算法测试 - 第{i+1}部分\n")
            relevant_lines.append("从原文件 test_prediction_algorithms_comprehensive.py 拆分\n")
            relevant_lines.append(f'创建时间: {__import__("datetime").datetime.now()}\n')
            relevant_lines.append('"""\n\n')

            # 添加基础导入
            relevant_lines.append("import pytest\n")
            relevant_lines.append("from unittest.mock import Mock, patch\n\n")

            # 提取相关函数和类
            for item in group:
                start_line = item["lineno"] - 1
                if start_line < len(lines):
                    # 简单提取：从函数开始到下一个函数或文件结束
                    end_line = len(lines)
                    for next_item in all_items:
                        if next_item["lineno"] > item["lineno"]:
                            end_line = next_item["lineno"] - 1
                            break

                    relevant_lines.extend(lines[start_line:end_line])
                    relevant_lines.append("\n")

            # 写入文件
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "w", encoding="utf-8") as f:
                f.writelines(relevant_lines)

            created_files.append(filename)
            print(f"✅ 创建文件: {filename} ({len(relevant_lines)} 行)")

    # 备份原文件
    backup_file = source_file + ".backup"
    os.rename(source_file, backup_file)
    print(f"📦 原文件备份至: {backup_file}")

    print("\n📊 拆分总结:")
    print(f"   原文件: {source_file} ({analysis['total_lines']} 行)")
    print(f"   拆分文件数: {len(created_files)}")
    print("   创建文件:")
    for f in created_files:
        lines_count = len(open(f, "r", encoding="utf-8").readlines())
        print(f"     - {os.path.basename(f)} ({lines_count} 行)")

    return True


def main():
    """主函数"""
    print("🚀 开始简单重构...")

    # 处理预测算法测试文件
    if split_prediction_algorithms_test():
        print("✅ 预测算法测试文件重构完成")
    else:
        print("❌ 预测算法测试文件重构失败")

    print("\n🎯 建议下一步:")
    print("   1. 验证拆分后的文件语法正确")
    print("   2. 运行测试确保功能正常")
    print("   3. 处理下一个长文件")


if __name__ == "__main__":
    main()
