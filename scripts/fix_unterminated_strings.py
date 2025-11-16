#!/usr/bin/env python3
"""
未终止字符串修复工具
专门修复由于格式化导致的字符串语法错误
"""

import ast
import os
import re
from pathlib import Path

def _fix_unterminated_strings_in_file_manage_resource():
            content = f.read()
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return 0

def _fix_unterminated_strings_in_file_loop_process():
        line = lines[i].rstrip()

        # 检查是否有未终止的f-string

def _fix_unterminated_strings_in_file_check_condition():
            # 尝试找到多行f-string的结束
            next_lines = [line]
            j = i + 1

            # 查找后续行直到找到字符串结束

def _fix_unterminated_strings_in_file_check_condition():
                new_lines.extend(fixed_combined.split('\n'))
                fixed_count += 1
                i = j + 1
                continue

def _fix_unterminated_strings_in_file_check_condition():
            # 尝试修复函数调用格式
            fixed_line = fix_function_call_format(line, i)

def _fix_unterminated_strings_in_file_check_condition():
                new_lines.append(fixed_line)
                fixed_count += 1
                i += 1
                continue

def _fix_unterminated_strings_in_file_manage_resource():
                f.write('\n'.join(new_lines))
            print(f"修复 {file_path} 中的 {fixed_count} 个语法错误")
        except Exception as e:
            print(f"写入文件 {file_path} 失败: {e}")
            return 0

def fix_unterminated_strings_in_file(file_path: str) -> int:
    """修复单个文件中的未终止字符串错误"""
    try:
        _fix_unterminated_strings_in_file_manage_resource()
            content = f.read()
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return 0

    original_content = content
    fixed_count = 0

    # 修复多行f-string的问题
    lines = content.split('\n')
    new_lines = []

    i = 0
    _fix_unterminated_strings_in_file_loop_process()
        line = lines[i].rstrip()

        # 检查是否有未终止的f-string
        _fix_unterminated_strings_in_file_check_condition()
            # 尝试找到多行f-string的结束
            next_lines = [line]
            j = i + 1

            # 查找后续行直到找到字符串结束
            while j < len(lines):
                next_lines.append(lines[j])
                if lines[j].rstrip().endswith('"'):
                    break
                j += 1

            # 合并为完整的f-string
            combined = ' '.join(next_lines)
            # 修复缩进和格式
            fixed_combined = fix_multiline_fstring(combined, i)

            _fix_unterminated_strings_in_file_check_condition()
                new_lines.extend(fixed_combined.split('\n'))
                fixed_count += 1
                i = j + 1
                continue

        # 检查logger.info等函数调用的格式问题
        _fix_unterminated_strings_in_file_check_condition()
            # 尝试修复函数调用格式
            fixed_line = fix_function_call_format(line, i)
            _fix_unterminated_strings_in_file_check_condition()
                new_lines.append(fixed_line)
                fixed_count += 1
                i += 1
                continue

        new_lines.append(line)
        i += 1

    # 只有在有修复时才写回文件
    if fixed_count > 0:
        try:
            _fix_unterminated_strings_in_file_manage_resource()
                f.write('\n'.join(new_lines))
            print(f"修复 {file_path} 中的 {fixed_count} 个语法错误")
        except Exception as e:
            print(f"写入文件 {file_path} 失败: {e}")
            return 0

    return fixed_count

def fix_multiline_fstring(content: str, line_num: int) -> str:
    """修复多行f-string格式"""
    # 提取缩进
    indent_match = re.match(r'^(\s*)', content)
    base_indent = indent_match.group(1) if indent_match else ''

    # 分解多行f-string为单行
    lines = content.split('\n')
    if len(lines) <= 1:
        return content

    # 提取f-string内容
    fstring_pattern = r'f"([^"]*(?:\([^)]*\)[^"]*)*)"'
    matches = re.findall(fstring_pattern, content, re.DOTALL)

    if not matches:
        return content

    # 重构为更清晰的格式
    result_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            # 清理多余的空格和换行
            cleaned = re.sub(r'\s+', ' ', stripped)
            result_lines.append(cleaned)

    # 合并内容
    combined_content = ' '.join(result_lines)

    # 重新构造为合理的格式
    if len(combined_content) <= 88:  # 如果单行不超过限制
        return base_indent + combined_content
    else:
        # 分解为多行，保持可读性
        return format_long_fstring(combined_content, base_indent)

def format_long_fstring(content: str, base_indent: str) -> str:
    """格式化长f-string为多行"""
    # 在适当的逗号或运算符处分行
    parts = re.split(r'(,\s*|:\s*|\s+\+\s+)', content)
    if len(parts) <= 1:
        return content

    result_lines = []
    current_line = base_indent

    for part in parts:
        if len(current_line + part) <= 88:
            current_line += part
        else:
            if current_line.strip():
                result_lines.append(current_line.rstrip())
            current_line = base_indent + '    ' + part.lstrip()

    if current_line.strip():
        result_lines.append(current_line.rstrip())

    return '\n'.join(result_lines)

def fix_function_call_format(line: str, line_num: int) -> str:
    """修复函数调用格式"""
    # 特别处理logger.info等函数的多行调用
    if 'logger.' in line and '(' in line:
        # 查找函数名
        func_match = re.search(r'(\w+\.info\w*)\s*\(', line)
        if func_match:
            func_name = func_match.group(1)

            # 提取缩进
            indent_match = re.match(r'^(\s*)', line)
            base_indent = indent_match.group(1) if indent_match else ''

            # 如果是logger.info的多行调用，修复格式
            if 'logger.info' in line:
                # 重构为正确的格式
                return fix_logger_call_format(line, base_indent)

    return line

def fix_logger_call_format(line: str, base_indent: str) -> str:
    """修复logger.info调用格式"""
    # 查找logger.info的参数
    if 'f"' in line and line.count('"') % 2 == 1:
        # 未终止的f-string，需要查找完整的内容
        # 这里简化处理，直接修复格式
        pattern = r'(logger\.info\s*\()\s*(f"[^"]*)'
        match = re.search(pattern, line)
        if match:
            func_start = match.group(1)
            fstring_start = match.group(2)

            # 构造正确的多行格式
            return f"{func_start}\n{base_indent}    {fstring_start}\n{base_indent})"

    return line

def fix_all_unterminated_strings(project_root: str = ".") -> int:
    """修复整个项目的未终止字符串错误"""
    project_path = Path(project_root)
    total_fixed = 0

    # 需要修复的文件列表（基于Black错误信息）
    problem_files = [
        "src/api/betting_api.py",
        "src/cache/ttl_cache_enhanced/ttl_cache.py",
        "src/collectors/data_sources.py",
        "src/domain/strategies/base.py",
        "src/ml/models/base_model.py",
        "src/utils/validators.py",
        "src/ml/models/elo_model.py",
        "src/realtime/quality_monitor_server.py",
        "tests/integration/test_betting_core.py",
        "tests/integration/test_betting_ev_strategy.py",
        "tests/integration/api_data_consistency.py",
        "tests/integration/test_stage2_collectors.py",
        "tests/integration/test_srs_api.py",
        "tests/integration/test_stage2_fixed.py",
        "tests/integration/test_stage2_simple.py",
        "tests/integration/test_stage4_e2e.py"
    ]

    for file_path in problem_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            fixed = fix_unterminated_strings_in_file(full_path)
            total_fixed += fixed

    return total_fixed

def main():
    """主函数"""
    print("开始修复未终止字符串语法错误...")

    total_fixed = fix_all_unterminated_strings()

    print(f"\n总共修复了 {total_fixed} 个语法错误")

    # 验证修复结果
    print("\n验证修复结果...")
    try:
        result = subprocess.run(
            ['black', '--check', '--diff', 'src/', 'tests/'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ 所有文件格式正确")
        else:
            print("⚠️  仍有格式问题需要处理")
            print(result.stdout)
    except Exception as e:
        print(f"验证失败: {e}")

if __name__ == "__main__":
    import subprocess
    main()
