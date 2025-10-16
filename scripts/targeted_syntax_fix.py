#!/usr/bin/env python3
"""精确语法错误修复工具 - 基于具体错误模式的定向修复"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional

def fix_file_syntax(file_path: str) -> bool:
    """修复单个文件的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 1. 修复类型注解中的括号不匹配
        content = fix_type_annotations(content)

        # 2. 修复未闭合的字符串
        content = fix_unclosed_strings(content)

        # 3. 修复字典/列表的括号不匹配
        content = fix_bracket_mismatches(content)

        # 4. 修复文件头部的无效语法（通常是编码声明问题）
        content = fix_header_syntax(content)

        # 5. 修复缩进问题
        content = fix_indentation_issues(content)

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 修复了文件: {file_path}")
            return True

        # 尝试编译检查
        try:
            compile(content, file_path, 'exec')
            print(f"✓ 文件语法正确: {file_path}")
            return True
        except SyntaxError as e:
            print(f"✗ 仍有语法错误 {file_path}: {e}")
            return False

    except Exception as e:
        print(f"✗ 处理文件失败 {file_path}: {e}")
        return False

def fix_type_annotations(content: str) -> str:
    """修复类型注解中的常见错误"""
    # 修复 Optional[List[str] = None] -> Optional[List[str]] = None
    patterns = [
        (r'Optional\[List\[(.*?)\]\s*=\s*None\]', r'Optional[List[\1]] = None'),
        (r'Optional\[Dict\[(.*?)\]\s*=\s*None\]', r'Optional[Dict[\1]] = None'),
        (r'Optional\[Tuple\[(.*?)\]\s*=\s*None\]', r'Optional[Tuple[\1]] = None'),
        (r'Optional\[Union\[(.*?)\]\s*=\s*None\]', r'Optional[Union[\1]] = None'),
        (r'List\[Dict\[(.*?)\)\]', r'List[Dict[\1]]'),
        (r'Dict\[str, Any\)\]', r'Dict[str, Any]]'),
        (r'Tuple\[str, Any\)\]', r'Tuple[str, Any]]'),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    return content

def fix_unclosed_strings(content: str) -> str:
    """修复未闭合的字符串字面量"""
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        # 检查是否有未闭合的字符串（简单启发式）
        # 计算引号数量，忽略转义的引号
        quote_count = 0
        in_string = False
        escape_next = False
        quote_char = None

        for char in line:
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if not in_string and char in ['"', "'"]:
                in_string = True
                quote_char = char
                quote_count = 1
            elif in_string and char == quote_char:
                in_string = False
                quote_char = None
                quote_count += 1

        # 如果行末有未闭合的字符串，尝试修复
        if in_string and quote_char:
            # 检查是否是字典键缺少引号的情况
            if ':' in line and not line.strip().endswith(':'):
                # 可能是 "key: value 缺少结束引号
                if quote_count % 2 == 1:
                    line = line + quote_char
            else:
                # 直接添加结束引号
                line = line + quote_char

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def fix_bracket_mismatches(content: str) -> str:
    """修复括号不匹配问题"""
    # 修复常见的括号不匹配模式
    patterns = [
        # 修复多余的右括号
        (r'\]\s*\)\s*\]', ']]'),
        (r'\)\s*\]\s*\)', '))'),
        (r'\}\s*\]\s*\}', '}}'),
        # 修复字典/列表结尾的多余符号
        (r'[\]}]+$', ''),  # 移除行末多余的 ] 或 }
        (r'["\'}]+$', ''),  # 移除行末多余的 " 或 ' 或 }
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    return content

def fix_header_syntax(content: str) -> str:
    """修复文件头部的语法错误"""
    lines = content.split('\n')

    # 检查前几行是否有语法错误
    for i in range(min(5, len(lines))):
        line = lines[i].strip()
        # 移除无效的标记
        if line == '"""' and i > 0:
            # 可能是错误的文档字符串开始
            lines[i] = ''
        elif line.startswith('"""') and line.endswith('"""') and len(line) < 10:
            # 空的文档字符串
            lines[i] = ''

    return '\n'.join(lines)

def fix_indentation_issues(content: str) -> str:
    """修复缩进问题"""
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            fixed_lines.append(line)
            continue

        # 计算当前缩进
        indent = len(line) - len(stripped)

        # 修复8空格缩进问题（应该是4的倍数）
        if indent % 4 == 1:
            # 奇数缩进，调整到最近的偶数
            new_indent = indent - 1 if indent > 1 else indent + 1
            fixed_lines.append(' ' * new_indent + stripped)
        else:
            fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def main():
    """主函数"""
    print("精确语法错误修复工具")
    print("=" * 60)

    # 需要修复的文件列表（基于错误报告）
    files_to_fix = [
        "src/config/openapi_config.py",
        "src/repositories/prediction.py",
        "src/repositories/user.py",
        "src/repositories/match.py",
        "src/stubs/mocks/feast.py",
        "src/stubs/mocks/confluent_kafka.py",
        "src/facades/base.py",
        "src/facades/facades.py",
        "src/facades/factory.py",
        "src/patterns/decorator.py",
        "src/patterns/facade.py",
        "src/patterns/observer.py",
        "src/patterns/facade_simple.py",
        "src/monitoring/alert_handlers.py",
        "src/monitoring/alert_manager_mod/__init__.py",
        "src/performance/profiler.py",
        "src/performance/middleware.py",
        "src/performance/analyzer.py",
        "src/ml/model_training.py",
        "src/models/prediction_model.py",
        "src/models/common_models.py",
        "src/decorators/service.py",
        "src/decorators/base.py",
        "src/decorators/decorators.py",
        "src/realtime/websocket.py",
        "src/domain/models/league.py",
        "src/domain/models/prediction.py",
        "src/domain/models/team.py",
        "src/domain/models/match.py",
        "src/domain/strategies/config.py",
        "src/domain/strategies/base.py",
        "src/domain/strategies/historical.py",
        "src/domain/strategies/ensemble.py",
        "src/domain/strategies/statistical.py",
        "src/domain/strategies/ml_model.py",
        "src/domain/strategies/factory.py",
        "src/domain/services/scoring_service.py",
        "src/domain/services/team_service.py",
        "src/domain/events/base.py",
        "src/domain/events/prediction_events.py",
        "src/cqrs/dto.py",
        "src/cqrs/application.py",
        "src/streaming/kafka_consumer_simple.py",
        "src/streaming/stream_processor_simple.py",
        "src/streaming/kafka_producer_simple.py",
        "src/streaming/kafka_components_simple.py",
        "src/database/query_optimizer.py",
        "src/database/compatibility.py",
        "src/database/repositories/base.py",
    ]

    fixed_count = 0
    total_count = len(files_to_fix)

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_file_syntax(file_path):
                fixed_count += 1
        else:
            print(f"✗ 文件不存在: {file_path}")

    print("\n" + "=" * 60)
    print(f"修复完成: {fixed_count}/{total_count} 个文件")

    # 验证修复结果
    print("\n验证修复结果...")
    success_count = 0
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                compile(content, file_path, 'exec')
                success_count += 1
            except SyntaxError:
                pass

    print(f"语法正确的文件: {success_count}/{total_count}")
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
