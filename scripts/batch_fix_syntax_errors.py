#!/usr/bin/env python3
"""
批量修复常见语法错误
"""

import os
import re
from pathlib import Path

def fix_syntax_errors(file_path):
    """修复单个文件的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        modified = False

        # 1. 修复类型注解中的方括号错误
        patterns = [
            (r'Optional\[([^\]]+)\] = None', r'Optional[\1] = None'),
            (r'List\[([^\]]+)\] = \[\]', r'List[\1] = []'),
            (r'Dict\[str, Any\]\]\[str, Any\]', r'Dict[str, Any]'),
            (r'Optional\[Dict\[str, Any\]\]\[str, Any\]', r'Optional[Dict[str, Any]]'),
            (r': List\[Dict\[str, Any\](?!\])', ': List[Dict[str, Any]]'),
            (r': Optional\[Dict\[str, Any\](?!\])', ': Optional[Dict[str, Any]]'),
        ]

        for pattern, replacement in patterns:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                modified = True

        # 2. 修复未闭合的括号（简单情况）
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # 检查常见的未闭合情况
            if '=' in line and line.count('[') > line.count(']'):
                # 可能缺少右括号
                missing_brackets = line.count('[') - line.count(']')
                if missing_brackets > 0:
                    lines[i] = line.rstrip() + ']' * missing_brackets
                    modified = True

        if modified:
            content = '\n'.join(lines)

        # 3. 修复f-string错误
        # 简单的f-string修复
        content = re.sub(r'f"([^"]*)\{([^}]+)\["([^"]*)"', r'f"\1{\2}[\3"', content)
        content = re.sub(r'f"([^"]*)\{([^}]+)\]([^"]*)"', r'f"\1{\2}]\3"', content)

        # 4. 修复字典初始化错误
        content = re.sub(r'(\s+)(\w+):\s*\w+\s*=\s*{\s*}\s*"([^"]+)",', r'\1\2: {\3},', content)

        # 验证修复
        try:
            import ast
            ast.parse(content)
            if content != original:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True, "修复成功"
            return False, "无需修复"
        except SyntaxError as e:
            return False, f"仍有错误: {e.msg} at line {e.lineno}"

    except Exception as e:
        return False, f"处理文件出错: {e}"

def main():
    """主函数"""
    print("批量修复语法错误...\n")

    # 要修复的文件列表（来自之前的分析）
    files_to_fix = [
        'src/services/audit/__init__.py',
        'src/services/audit_service.py',
        'src/services/audit_service_mod/__init__.py',
        'src/services/data_processing.py',
        'src/services/enhanced_core.py',
        'src/services/event_prediction_service.py',
        'src/services/processing/caching/processing_cache.py',
        'src/services/processing/processors/match_processor.py',
        'src/services/processing/validators/data_validator.py',
        'src/services/strategy_prediction_service.py',
    ]

    success_count = 0
    failed_count = 0

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            success, message = fix_syntax_errors(file_path)
            if success:
                print(f"✓ {file_path} - {message}")
                success_count += 1
            else:
                print(f"✗ {file_path} - {message}")
                if "仍有错误" not in message:
                    failed_count += 1
        else:
            print(f"⚠ 文件不存在: {file_path}")

    print(f"\n修复完成:")
    print(f"  成功: {success_count} 个文件")
    print(f"  失败: {failed_count} 个文件")

if __name__ == "__main__":
    main()
