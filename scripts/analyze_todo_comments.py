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

        except Exception:
            pass

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
    total_todos, todo_types, todo_files = analyze_todos()


    for _todo, _count in todo_types.most_common(10):
        pass

    for _file_path, _count in todo_files.most_common(10):
        pass

    # 分类显示
    categories = categorize_todos(todo_types)
    for _category, items in categories.items():
        sum(count for _, count in items)
        if items and len(items) <= 5:  # 只显示少于5项的详细内容
            for _todo, _count in items[:3]:
                pass

if __name__ == "__main__":
    main()
