#!/usr/bin/env python3
"""
智能修复剩余的语法错误
"""

import os
import re
import ast
from pathlib import Path

def check_syntax(file_path: str) -> bool:
    """检查文件语法是否正确"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True
    except SyntaxError:
        return False
    except Exception:
        return False

def fix_smart(content: str, file_path: str) -> str:
    """智能修复语法错误"""
    lines = content.split('\n')
    modified = False

    for i, line in enumerate(lines):
        original_line = line

        # 1. 修复未闭合的字符串（最常见的问题）
        # 检查字典值中的字符串
        if ': ' in line and ('"' in line or "'" in line):
            # 模式：键值对
            # 修复 "key": "value,  ->  "key": "value",
            # 修复 "key": 'value,  ->  "key": 'value',

            # 处理双引号
            if '"' in line:
                # 查找所有键值对
                colon_pos = line.find(': ')
                if colon_pos > 0:
                    # 检查冒号后面的部分
                    value_part = line[colon_pos + 2:].strip()

                    # 如果以引号开始但没有结束引号
                    if value_part.startswith('"') and not value_part.endswith('"'):
                        # 处理不同的情况
                        if value_part.endswith(','):
                            # 有逗号的情况
                            value_part = value_part[:-1] + '",'
                        else:
                            # 没有逗号
                            value_part = value_part + '"'

                        # 重构行
                        line = line[:colon_pos + 2] + value_part
                        modified = True

            # 处理单引号（类似逻辑）
            elif "'" in line:
                colon_pos = line.find(': ')
                if colon_pos > 0:
                    value_part = line[colon_pos + 2:].strip()

                    if value_part.startswith("'") and not value_part.endswith("'"):
                        if value_part.endswith(','):
                            value_part = value_part[:-1] + "',"
                        else:
                            value_part = value_part + "'"

                        line = line[:colon_pos + 2] + value_part
                        modified = True

        # 2. 修复括号不匹配
        # List[Dict[str, Any])  ->  List[Dict[str, Any]]
        line = re.sub(r'List\[Dict\[str, Any\]\)', r'List[Dict[str, Any]]', line)
        # Optional[Dict[str, Any])  ->  Optional[Dict[str, Any]]
        line = re.sub(r'Optional\[Dict\[str, Any\]\)', r'Optional[Dict[str, Any]]', line)
        # Optional[List[Dict[str, Any]])  ->  Optional[List[Dict[str, Any]]]
        line = re.sub(r'Optional\[List\[Dict\[str, Any\]\)\]', r'Optional[List[Dict[str, Any]]]', line)

        # 3. 修复函数参数列表
        # (data: List[Dict[str, Any]) -> (data: List[Dict[str, Any]])
        line = re.sub(r'\(([^)]*List\[Dict\[str, Any\])\)', r'(\1])', line)
        line = re.sub(r'\(([^)]*Optional\[Dict\[str, Any\])\)', r'(\1])', line)

        # 4. 修复特殊的语法错误
        # 修复 "threshold": self.thresholds["response_time"]["poor",
        if '["' in line and line.endswith(','):
            line = line[:-1] + '"],'
            modified = True

        # 修复 f-string
        if line.startswith('f"') or line.startswith("f'"):
            if line.count('"') % 2 == 1 and line.endswith('"'):
                line += '"'
                modified = True
            elif line.count("'") % 2 == 1 and line.endswith("'"):
                line += "'"
                modified = True

        # 修复返回语句
        if line.strip().startswith('return f"') and line.count('"') % 2 == 1:
            if line.endswith(',') or line.endswith('}') or line.endswith(']'):
                line = line[:-1] + '"'
            else:
                line += '"'
            modified = True

        # 如果行被修改，更新列表
        if line != original_line:
            lines[i] = line

    # 5. 修复多行问题
    content = '\n'.join(lines)

    # 修复特定的多行模式
    # 查找未闭合的字典或列表
    open_braces = 0
    open_brackets = 0
    in_string = False
    string_char = None
    escape_next = False

    for i, char in enumerate(content):
        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        if not in_string:
            if char == '"' or char == "'":
                in_string = True
                string_char = char
            elif char == '{':
                open_braces += 1
            elif char == '}':
                open_braces -= 1
            elif char == '[':
                open_brackets += 1
            elif char == ']':
                open_brackets -= 1
        else:
            if char == string_char:
                in_string = False
                string_char = None

    # 如果有不匹配的括号，尝试修复
    if open_braces > 0:
        content += '}' * open_braces
        modified = True
    elif open_braces < 0:
        # 找到最后一个多余的 } 并删除
        pos = content.rfind('}')
        if pos > 0:
            content = content[:pos] + content[pos + 1:]
            modified = True

    if open_brackets > 0:
        content += ']' * open_brackets
        modified = True
    elif open_brackets < 0:
        # 找到最后一个多余的 ] 并删除
        pos = content.rfind(']')
        if pos > 0:
            content = content[:pos] + content[pos + 1:]
            modified = True

    return content

def main():
    """主函数"""
    print("开始智能修复剩余语法错误...")

    # 查找所有Python文件
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    # 检查哪些文件有语法错误
    error_files = []
    for file_path in python_files:
        if not check_syntax(file_path):
            error_files.append(file_path)

    print(f"\n发现 {len(error_files)} 个文件有语法错误")

    if not error_files:
        print("所有文件语法都正确！")
        return

    # 修复每个文件
    fixed_count = 0
    remaining_errors = []

    for file_path in error_files:
        print(f"\n处理: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            content = original_content
            content = fix_smart(content, file_path)

            # 如果有修复，保存文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✓ 文件已修复")

                # 验证修复是否成功
                if check_syntax(file_path):
                    print(f"  ✓ 语法错误已修复")
                    fixed_count += 1
                else:
                    print(f"  ✗ 仍有语法错误")
                    remaining_errors.append(file_path)
            else:
                print(f"  - 未找到需要修复的内容")
                remaining_errors.append(file_path)

        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            remaining_errors.append(file_path)

    print(f"\n修复完成！")
    print(f"- 处理文件: {len(error_files)}")
    print(f"- 成功修复: {fixed_count}")

    if remaining_errors:
        print(f"\n仍有 {len(remaining_errors)} 个文件存在语法错误:")
        for file_path in remaining_errors[:20]:
            print(f"  - {file_path}")
        if len(remaining_errors) > 20:
            print(f"  ... 还有 {len(remaining_errors) - 20} 个文件")

        # 生成一个简单的修复脚本
        print("\n生成快速修复脚本...")
        with open('quick_fix.py', 'w') as f:
            f.write("""#!/usr/bin/env python3
# 快速修复脚本
import os

files_with_errors = """ + str(remaining_errors) + """

for file_path in files_with_errors:
    print(f"手动修复: {file_path}")
    print(f"vim '{file_path}'")
""")
        print("已生成 quick_fix.py 文件，可以手动修复剩余错误")
    else:
        print("\n✓ 所有文件的语法错误都已修复！")
        print(f"\n统计:")
        print(f"- 总文件数: {len(python_files)}")
        print(f"- 成功修复: {fixed_count}")
        print(f"- 成功率: {(len(python_files) - len(remaining_errors)) / len(python_files) * 100:.1f}%")

if __name__ == "__main__":
    main()
