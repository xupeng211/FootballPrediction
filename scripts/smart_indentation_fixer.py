#!/usr/bin/env python3
"""
智能缩进修复工具
识别并修复常见的Python缩进模式错误
"""

import re
import ast
from pathlib import Path
from typing import List, Dict, Tuple


def fix_indentation_pattern(content: str) -> str:
    """
    修复常见的缩进模式错误
    """
    # 模式1: def method(self, params): """docstring""" code_on_same_line
    pattern1 = r'(    )def (\w+)\([^)]*\):\s*\"\"\"[^\"]*\"\"\"(.*)'
    content = re.sub(pattern1, r'\1def \2(\n\1        \"\"\"\"\"\"\"\n\1\3', content)

    # 模式2: def method(self, params): code_on_same_line
    pattern2 = r'(    )def (\w+)\([^)]*\):\s*([^#\n].*)'
    content = re.sub(pattern2, r'\1def \2(\n\1        \3', content)

    # 模式3: 类变量赋值在同一行
    pattern3 = r'(    )(\w+\s*=\s*[^#\n]+):?\s*([^#\n]+)'
    content = re.sub(pattern3, r'\1\2\n\1        \3', content)

    # 模式4: 普通变量赋值缺少缩进
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 跳过空行和注释
        if not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            continue

        # 检查是否是变量赋值且缺少缩进
        if ('=' in stripped and
            not stripped.startswith('def ') and
            not stripped.startswith('class ') and
            not line.startswith('    ') and
            not line.startswith('        ')):

            # 检查是否在类或方法上下文中
            if is_in_class_or_method_context(i, lines):
                fixed_lines.append('    ' + line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def is_in_class_or_method_context(line_num: int, lines: List[str]) -> bool:
    """
    检查指定行是否在类或方法上下文中
    """
    # 向上查找最近的类或方法定义
    for i in range(line_num - 1, -1, -1):
        line = lines[i].strip()
        if line.startswith('class '):
            return True
        elif line.startswith('def '):
            # 检查这个方法是否在类中
            if i > 0 and lines[i-1].strip().startswith('class '):
                return True
            return False
    return False


def fix_file_indentation(file_path: str) -> Tuple[bool, str]:
    """
    修复单个文件的缩进
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # 应用智能修复
        fixed_content = fix_indentation_pattern(original_content)

        # 验证修复结果
        try:
            ast.parse(fixed_content)
            if fixed_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                return True, "缩进错误修复成功"
            else:
                return True, "无需修复"
        except SyntaxError as e:
            return False, f"修复失败: {e}"

    except Exception as e:
        return False, f"处理失败: {e}"


def batch_fix_remaining_files() -> Dict[str, Tuple[bool, str]]:
    """
    批量修复剩余的文件
    """
    # 需要修复的文件列表（排除已修复的）
    remaining_files = [
        'src/models/model_training.py',
        'src/monitoring/metrics_collector_enhanced.py',
        'src/monitoring/system_monitor.py',
        'src/monitoring/metrics_collector.py',
        'src/monitoring/apm_integration.py',
        'src/monitoring/alert_manager.py',
        'src/monitoring/alert_manager_mod/__init__.py',
        'src/data/storage/lake.py',
        'src/data/quality/prometheus.py',
        'src/dependencies/optional.py',
        'src/features/feature_store.py',
        'src/middleware/performance_monitoring.py',
        'src/realtime/websocket.py',
        'src/tasks/celery_app.py',
        'src/tasks/data_collection_core.py',
        'src/tasks/streaming_tasks.py',
        'src/scheduler/job_manager.py',
        'src/ml/model_training.py'
    ]

    results = {}

    for file_path in remaining_files:
        if not Path(file_path).exists():
            results[file_path] = (False, "文件不存在")
            continue

        print(f"修复 {file_path}...")
        success, message = fix_file_indentation(file_path)
        results[file_path] = (success, message)

        if success:
            print(f"  ✅ {message}")
        else:
            print(f"  ❌ {message}")

    return results


def main():
    print("🔧 智能缩进修复工具启动...")

    results = batch_fix_remaining_files()

    # 统计结果
    success_count = sum(1 for success, _ in results.values() if success)
    fixed_count = sum(1 for success, msg in results.values()
                     if success and msg == "缩进错误修复成功")
    failed_files = [path for path, (success, _) in results.items() if not success]

    print("\n📊 修复结果:")
    print(f"   成功处理: {success_count}/{len(results)}")
    print(f"   实际修复: {fixed_count}")
    print(f"   处理失败: {len(failed_files)}")

    if failed_files:
        print("\n❌ 处理失败的文件:")
        for file_path in failed_files:
            print(f"   - {file_path}: {results[file_path][1]}")

    return results


if __name__ == "__main__":
    main()