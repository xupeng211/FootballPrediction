#!/usr/bin/env python3
"""
简单缩进错误修复工具 - Issue #345补充工具

专门修复简单的HTTPException缩进和括号错位问题
"""

import ast
import re
from pathlib import Path


def fix_httpexception_structure(content: str) -> tuple[str, int]:
    """修复HTTPException结构错误"""
    fixes_count = 0

    # 修复模式1: 括号后直接跟参数
    pattern1 = r'raise HTTPException\(\s*\n\s*\)\s*(status_code=.*?detail=.*?)\s*\)'
    matches1 = re.findall(pattern1, content, re.MULTILINE | re.DOTALL)
    if matches1:
        for match in matches1:
            replacement = f'raise HTTPException(\n                {match}\n            )'
            content = re.sub(pattern1, replacement, content, flags=re.MULTILINE | re.DOTALL)
            fixes_count += len(matches1)

    # 修复模式2: 重复的raise语句
    pattern2 = r'raise HTTPException\(\s*raise HTTPException\((.*?)\)\s*\)'
    matches2 = re.findall(pattern2, content, re.MULTILINE | re.DOTALL)
    if matches2:
        for match in matches2:
            replacement = f'raise HTTPException({match})'
            content = re.sub(pattern2, replacement, content, flags=re.MULTILINE | re.DOTALL)
            fixes_count += len(matches2)

    return content, fixes_count


def fix_indentation_errors(content: str) -> tuple[str, int]:
    """修复简单的缩进错误"""
    lines = content.split('\n')
    fixed_lines = []
    fixes_count = 0

    for i, line in enumerate(lines):
        # 检查HTTPException参数行的缩进问题
        if ('status_code=' in line or 'detail=' in line) and not line.startswith(' ' * 8):
            # 如果参数行缩进不足，补充到8个空格
            stripped = line.lstrip()
            if stripped.startswith(('status_code=', 'detail=')):
                line = '        ' + stripped
                fixes_count += 1

        fixed_lines.append(line)

    return '\n'.join(fixed_lines), fixes_count


def fix_file(file_path: Path) -> dict:
    """修复单个文件"""
    result = {
        'file': str(file_path),
        'success': False,
        'fixes': 0,
        'message': ''
    }

    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 应用修复
        content, http_fixes = fix_httpexception_structure(content)
        content, indent_fixes = fix_indentation_errors(content)

        total_fixes = http_fixes + indent_fixes

        if total_fixes > 0:
            # 验证修复结果
            try:
                ast.parse(content)

                # 保存修复后的文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                result['success'] = True
                result['fixes'] = total_fixes
                result['message'] = f'成功修复 {total_fixes} 个问题'

            except SyntaxError as e:
                result['success'] = False
                result['message'] = f'修复后仍有语法错误: {e.msg}'

                # 恢复原始内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
        else:
            # 检查是否原本就有语法错误
            try:
                ast.parse(content)
                result['success'] = True
                result['message'] = '文件语法正确'
            except SyntaxError as e:
                result['success'] = False
                result['message'] = f'存在无法自动修复的语法错误: {e.msg}'

    except Exception as e:
        result['success'] = False
        result['message'] = f'处理文件出错: {str(e)}'

    return result


def main():
    """主函数"""
    # 需要修复的文件列表 (从报告中提取的高优先级文件)
    files_to_fix = [
        'src/api/betting_api.py',
        'src/api/middleware.py',
        'src/api/simple_auth.py',
        'src/api/features.py',
        'src/api/events.py',
        'src/api/realtime_streaming.py',
        'src/api/observers.py',
        'src/api/performance_management.py',
        'src/api/predictions_enhanced.py',
        'src/api/auth/router.py'
    ]

    print("🔧 简单缩进错误修复工具")
    print("=" * 40)

    results = []
    success_count = 0

    for file_path_str in files_to_fix:
        file_path = Path(file_path_str)
        if file_path.exists():
            print(f"🔍 修复: {file_path_str}")
            result = fix_file(file_path)
            results.append(result)

            if result['success']:
                print(f"  ✅ {result['message']}")
                if result['fixes'] > 0:
                    success_count += 1
            else:
                print(f"  ❌ {result['message']}")
        else:
            print(f"⚠️  文件不存在: {file_path_str}")

    print()
    print("📊 修复统计:")
    print(f"  处理文件: {len(results)}")
    print(f"  成功修复: {success_count}")
    print(f"  仍有问题: {len(results) - success_count}")

    return success_count > 0


if __name__ == "__main__":
    main()
