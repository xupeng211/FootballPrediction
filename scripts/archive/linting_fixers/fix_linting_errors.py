#!/usr/bin/env python3
"""
修复代码中的linting错误
"""

import os
import re
import subprocess


def fix_whitespace_issues(file_path):
    """修复空白字符问题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 修复行尾空白字符
        lines = content.split("\n")
        fixed_lines = []

        for line in lines:
            # 移除行尾空白字符
            line = line.rstrip()
            # 移除空行中的空白字符
            if line.strip() == "":
                line = ""
            fixed_lines.append(line)

        # 重新组合内容
        fixed_content = "\n".join(fixed_lines)

        # 如果内容有变化，写回文件
        if fixed_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            print(f"✅ 修复空白字符问题: {file_path}")
            return True
    except Exception as e:
        print(f"❌ 修复 {file_path} 时出错: {e}")
        return False


def fix_unused_imports(file_path):
    """修复未使用的导入"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        fixed_lines = []
        imports_to_remove = set()

        # 分析导入语句
        for i, line in enumerate(lines):
            if re.match(r"^\s*(from\s+\S+\s+)?import\s+", line):
                # 提取导入的模块/函数名
                import_match = re.search(r"import\s+(.+)", line)
                if import_match:
                    imports = import_match.group(1).split(",")
                    for imp in imports:
                        imp = imp.strip().split(" as ")[0]
                        imports_to_remove.add(imp)

        # 检查哪些导入实际被使用
        content_lower = content.lower()
        for i, line in enumerate(lines):
            if re.match(r"^\s*(from\s+\S+\s+)?import\s+", line):
                import_match = re.search(r"import\s+(.+)", line)
                if import_match:
                    imports = import_match.group(1).split(",")
                    new_imports = []
                    for imp in imports:
                        imp_clean = imp.strip()
                        imp_name = imp_clean.split(" as ")[0]
                        # 检查是否在代码中被使用
                        if imp_name in content_lower and not re.search(
                            rf"\b{re.escape(imp_name)}\b", content_lower
                        ):
                            # 如果导入没有被使用，跳过
                            continue
                        new_imports.append(imp_clean)

                    if new_imports:
                        new_line = re.sub(r"import\s+.+", f'import {", ".join(new_imports)}', line)
                        fixed_lines.append(new_line)
                    else:
                        # 如果所有导入都没有被使用，跳过这行
                        continue
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        fixed_content = "\n".join(fixed_lines)
        if fixed_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            print(f"✅ 修复未使用导入: {file_path}")
            return True
    except Exception as e:
        print(f"❌ 修复导入 {file_path} 时出错: {e}")
        return False


def fix_undefined_names(file_path):
    """修复未定义名称的问题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 常见的未定义名称修复
        fixes = {
            "get_backup_status": "from src.tasks.backup_tasks import get_backup_status",
            "collect_odds_task": "from src.tasks.data_collection_tasks import collect_odds_task",
            "collect_scores_task": "from src.tasks.data_collection_tasks import collect_scores_task",
            "collect_all_data_task": "from src.tasks.data_collection_tasks import collect_all_data_task",
            "periodic_data_collection_task": "from src.tasks.data_collection_tasks import periodic_data_collection_task",
            "emergency_data_collection_task": "from src.tasks.data_collection_tasks import emergency_data_collection_task",
            "collect_fixtures_task": "from src.tasks.data_collection_tasks import collect_fixtures_task",
            "asyncio": "import asyncio",
        }

        lines = content.split("\n")
        fixed_lines = []
        imports_added = set()

        for line in lines:
            # 检查是否有未定义的名称
            for undefined_name, import_statement in fixes.items():
                if undefined_name in line and import_statement not in content:
                    if import_statement not in imports_added:
                        # 在文件开头添加导入
                        fixed_lines.insert(0, import_statement)
                        imports_added.add(import_statement)
                        print(f"✅ 添加导入: {import_statement}")

            fixed_lines.append(line)

        if imports_added:
            fixed_content = "\n".join(fixed_lines)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            print(f"✅ 修复未定义名称: {file_path}")
            return True
    except Exception as e:
        print(f"❌ 修复未定义名称 {file_path} 时出错: {e}")
        return False


def fix_arithmetic_operators(file_path):
    """修复算术运算符周围的空格"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 修复算术运算符周围的空格
        patterns = [
            (r"(\w)([+\-*/])(\w)", r"\1 \2 \3"),  # 操作符周围加空格
            (r"(\w)([+\-*/])(\s)", r"\1 \2\3"),  # 操作符前加空格
            (r"(\s)([+\-*/])(\w)", r"\1\2 \3"),  # 操作符后加空格
        ]

        fixed_content = content
        for pattern, replacement in patterns:
            fixed_content = re.sub(pattern, replacement, fixed_content)

        if fixed_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            print(f"✅ 修复算术运算符: {file_path}")
            return True
    except Exception as e:
        print(f"❌ 修复算术运算符 {file_path} 时出错: {e}")
        return False


def main():
    """主函数"""
    print("🔧 开始修复linting错误...")

    # 需要修复的文件列表
    files_to_fix = [
        "src/database/sql_compatibility.py",
        "src/tasks/error_logger.py",
        "src/tasks/monitoring.py",
        "tests/test_task_scheduler.py",
        "tests/unit/test_backup_tasks.py",
        "tests/unit/test_celery_app_comprehensive.py",
        "tests/unit/test_data_collection_tasks_comprehensive.py",
        "tests/unit/test_kafka_producer_comprehensive.py",
        "tests/unit/test_metrics_collector.py",
        "tests/unit/test_tasks_basic.py",
    ]

    fixed_count = 0

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            print(f"\n📝 处理文件: {file_path}")

            # 修复各种问题
            if fix_whitespace_issues(file_path):
                fixed_count += 1
            if fix_unused_imports(file_path):
                fixed_count += 1
            if fix_undefined_names(file_path):
                fixed_count += 1
            if fix_arithmetic_operators(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  文件不存在: {file_path}")

    print(f"\n✅ 修复完成! 共修复了 {fixed_count} 个问题")

    # 运行black格式化
    print("\n🎨 运行black格式化...")
    try:
        subprocess.run(["black", ".", "--line-length", "88"], check=True)
        print("✅ Black格式化完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ Black格式化失败: {e}")


if __name__ == "__main__":
    main()
