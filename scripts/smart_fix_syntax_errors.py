#!/usr/bin/env python3
"""
智能修复语法错误
"""

import ast
import os
from pathlib import Path

def analyze_and_fix_syntax_error(file_path):
    """分析并修复特定的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 尝试解析并获取具体的错误位置
        try:
            ast.parse(''.join(lines))
            return True, "语法正确"
        except SyntaxError as e:
            print(f"\n正在修复: {file_path}")
            print(f"错误: {e.msg} at line {e.lineno}")

            # 根据错误类型和位置进行修复
            if e.lineno and e.lineno <= len(lines):
                line_idx = e.lineno - 1
                line = lines[line_idx]

                # 修复特定类型的错误
                if "does not match opening parenthesis" in e.msg:
                    # 括号不匹配，通常是类型注解问题
                    if "Optional[" in line and "] =" in line:
                        # Optional[Type] = None 错误
                        lines[line_idx] = line.replace("] =", "] =")
                    elif "List[" in line or "Dict[" in line:
                        # 缺少右括号
                        if line.count("[") > line.count("]"):
                            lines[line_idx] = line.rstrip() + "]"

                elif "unmatched ']'" in e.msg:
                    # 多余的右括号
                    if "]]" in line:
                        lines[line_idx] = line.replace("]]", "]")

                elif "unmatched '}'" in e.msg:
                    # 多余的右大括号
                    if "}}" in line:
                        lines[line_idx] = line.replace("}}", "}")

                elif "unexpected indent" in e.msg:
                    # 缩进错误
                    # 查看前后行的缩进
                    if line_idx > 0:
                        prev_indent = len(lines[line_idx - 1]) - len(lines[line_idx - 1].lstrip())
                        curr_indent = len(line) - len(line.lstrip())
                        if curr_indent > prev_indent and not line.strip().startswith(('def', 'class', 'if', 'for', 'while', 'try', 'except', 'with', 'elif', 'else')):
                            # 可能是字典初始化的错误缩进
                            if ":" in line and not line.strip().endswith(":"):
                                # 修复字典初始化
                                lines[line_idx - 1] = lines[line_idx - 1].rstrip() + " {\n"
                                lines[line_idx] = "    " + line

                elif "expected ':'" in e.msg:
                    # 缺少冒号
                    if any(keyword in line for keyword in ["def ", "if ", "for ", "while ", "class ", "elif ", "else:", "try:", "except", "with:", "except "]):
                        if not line.rstrip().endswith(":"):
                            lines[line_idx] = line.rstrip() + ":\n"

                elif "invalid syntax" in e.msg and "comma" in e.msg:
                    # 缺少逗号
                    # 查找可能需要添加逗号的地方
                    if '"' in line and '"' in line[line.find('"') + 1:]:
                        # 可能在字符串之间需要逗号
                        pass

                # 写回文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

            # 再次验证
            try:
                ast.parse(''.join(lines))
                return True, "修复成功"
            except SyntaxError as e2:
                return False, f"仍有错误: {e2.msg}"

        return False, "未知错误"

    except Exception as e:
        return False, f"处理出错: {e}"

def main():
    """主函数"""
    print("智能修复语法错误...\n")

    # 要修复的文件列表
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
    failed_files = []

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            success, message = analyze_and_fix_syntax_error(file_path)
            if success:
                print(f"✓ {file_path} - {message}")
                success_count += 1
            else:
                print(f"✗ {file_path} - {message}")
                failed_files.append(file_path)

    print(f"\n修复完成:")
    print(f"  成功: {success_count} 个文件")
    print(f"  失败: {len(failed_files)} 个文件")

    if failed_files:
        print("\n失败的文件:")
        for f in failed_files:
            print(f"  - {f}")

if __name__ == "__main__":
    main()
