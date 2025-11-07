#!/usr/bin/env python3
"""
分析TODO注释的类型和分布
"""

import re
from collections import Counter
from pathlib import Path


def analyze_todos():
    """分析TODO注释"""
    todo_types = Counter()
    todo_files = Counter()
    total_todos = 0

    # 遍历所有Python文件
    for py_file in Path("src").rglob("*.py"):
        try:
            with open(py_file, encoding='utf-8') as f:
                content = f.read()

            # 查找所有TODO注释
            todos = re.findall(r'# TODO: (.+)', content)
            if todos:
                todo_files[py_file] += len(todos)
                for todo in todos:
                    todo_types[todo] += 1
                    total_todos += 1

        except Exception as e:
            print(f"❌ 处理文件失败 {py_file}: {e}")

    return total_todos, todo_types, todo_files

def categorize_todos(todo_types):
    """将TODO分类"""
    categories = {
        "魔法数字": [],
        "实现逻辑": [],
        "优化改进": [],
        "文档注释": [],
        "错误处理": [],
        "其他": []
    }

    for todo, count in todo_types.items():
        todo_lower = todo.lower()
        if "魔法数字" in todo:
            categories["魔法数字"].append((todo, count))
        elif any(keyword in todo_lower for keyword in ["实现", "implement", "pass"]):
            categories["实现逻辑"].append((todo, count))
        elif any(keyword in todo_lower for keyword in ["优化", "optimize", "改进", "improve", "重构", "refactor"]):
            categories["优化改进"].append((todo, count))
        elif any(keyword in todo_lower for keyword in ["文档", "document", "docstring", "注释"]):
            categories["文档注释"].append((todo, count))
        elif any(keyword in todo_lower for keyword in ["错误", "error", "异常", "exception", "处理", "handle"]):
            categories["错误处理"].append((todo, count))
        else:
            categories["其他"].append((todo, count))

    return categories

def main():
    """主函数"""
    print("🔍 分析TODO注释...")
    total_todos, todo_types, todo_files = analyze_todos()

    print("\n📊 TODO注释统计:")
    print(f"   总数量: {total_todos}")
    print(f"   涉及文件: {len(todo_files)}")

    print("\n🏆 最常见的TODO类型 (前10):")
    for todo, count in todo_types.most_common(10):
        print(f"   {count:3d}: {todo}")

    print("\n📁 TODO最多的文件 (前10):")
    for file_path, count in todo_files.most_common(10):
        print(f"   {count:3d}: {file_path}")

    # 分类显示
    categories = categorize_todos(todo_types)
    print("\n📋 TODO分类统计:")
    for category, items in categories.items():
        total = sum(count for _, count in items)
        print(f"   {category}: {total} 项")
        if items and len(items) <= 5:  # 只显示少于5项的详细内容
            for todo, count in items[:3]:
                print(f"      - {todo} ({count})")

if __name__ == "__main__":
    main()
