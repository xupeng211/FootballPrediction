#!/usr/bin/env python3
"""智能语法检查和修复工具 - 使用Python编译器进行精确诊断"""

import ast
import os
import re
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional, Dict

class PythonSyntaxChecker:
    """Python语法检查器"""

    def __init__(self):
        self.errors = {}

    def check_file(self, file_path: str) -> Optional[Tuple[int, int, str, List[str]]]:
        """检查文件语法，返回详细的错误信息"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 尝试解析
            ast.parse(content)
            return None

        except SyntaxError as e:
            # 获取错误行内容
            lines = content.split('\n')
            error_line_content = lines[e.lineno - 1] if e.lineno <= len(lines) else ""

            # 获取上下文
            context_start = max(0, e.lineno - 3)
            context_end = min(len(lines), e.lineno + 2)
            context = lines[context_start:context_end]

            return (e.lineno, e.offset or 0, str(e), context)

    def generate_fix(self, file_path: str, error_info: Tuple[int, int, str, List[str]]) -> Optional[str]:
        """根据错误信息生成修复建议"""
        line_num, col, msg, context = error_info
        error_line = context[line_num - (context[0] if context else 0) - 1] if context else ""

        # 根据错误类型生成修复
        if "illegal target for annotation" in msg:
            # 修复类型注解错误
            if col > 0 and col < len(error_line):
                # 查找引号位置
                if error_line[col-1] == '"':
                    # 移除引号
                    fixed_line = error_line[:col-1] + error_line[col:]
                    return fixed_line
        elif "unterminated string literal" in msg:
            # 修复未闭合的字符串
            if error_line.count('"') % 2 == 1:
                # 添加闭合引号
                if error_line.rstrip().endswith(','):
                    return error_line[:-1] + '",'
                else:
                    return error_line + '"'
        elif "invalid syntax" in msg:
            # 通用语法错误修复
            # 检查常见的错误模式
            if ': "' in error_line and not error_line.rstrip().endswith('"'):
                # 可能缺少闭合引号
                if error_line.count('"') % 2 == 1:
                    return error_line + '"'
            # 检查字典格式
            if error_line.strip().startswith('"') and ':' in error_line:
                # 可能是字典键的问题
                if not error_line.strip().endswith(','):
                    return error_line + ','

        return None

def fix_file_with_context(file_path: str) -> bool:
    """使用上下文信息修复文件"""
    checker = PythonSyntaxChecker()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')
        modified = False

        # 多轮修复
        for round_num in range(5):  # 最多5轮
            error_info = checker.check_file(file_path)
            if not error_info:
                break

            line_num, col, msg, context = error_info

            # 尝试修复
            fix = checker.generate_fix(file_path, error_info)
            if fix and line_num <= len(lines):
                old_line = lines[line_num - 1]
                lines[line_num - 1] = fix
                content = '\n'.join(lines)

                # 验证修复
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name

                try:
                    with open(tmp_path, 'r') as tmp_f:
                        tmp_content = tmp_f.read()
                    ast.parse(tmp_content)
                    # 修复成功
                    modified = True
                    print(f"  第{line_num}行修复: {old_line[:50]}... -> {fix[:50]}...")
                except SyntaxError:
                    # 修复失败，恢复
                    lines[line_num - 1] = old_line
                    content = '\n'.join(lines)
                finally:
                    os.unlink(tmp_path)

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"  修复失败: {e}")

    return False

def create_ide_commands(error_files: List[Tuple[str, Tuple[int, int, str, List[str]]]]) -> None:
    """创建IDE命令文件"""
    with open('ide_fix_commands.py', 'w') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('"""IDE修复命令生成器\n')
        f.write('使用方法: python -c "import ide_fix_commands; ide_fix_commands.run()"\n"""\n\n')
        f.write('import subprocess\nimport sys\n\n')
        f.write('ERRORS = [\n')

        for file_path, (line, col, msg, context) in error_files[:50]:  # 只处理前50个
            f.write(f'    ("{file_path}", {line}, {col}, "{msg}"),\n')

        f.write(']\n\n')
        f.write('def open_in_editor(file_path, line):\n')
        f.write('    """在编辑器中打开文件到指定行"""\n')
        f.write('    editors = [\n')
        f.write('        ["code", "--goto", f"{file_path}:{line}"],  # VS Code\n')
        f.write('        ["vim", f"+{line}", file_path],           # Vim\n')
        f.write('        ["nano", f"+{line}", file_path],         # Nano\n')
        f.write('    ]\n')
        f.write('    \n')
        f.write('    for editor_cmd in editors:\n')
        f.write('        try:\n')
        f.write('            subprocess.run(editor_cmd, check=True)\n')
        f.write('            print(f"Opened {file_path} at line {line}")\n')
        f.write('            return\n')
        f.write('        except:\n')
        f.write('            continue\n')
        f.write('    print(f"Could not open {file_path} in any editor")\n\n')

        f.write('def run():\n')
        f.write('    """运行修复命令"""\n')
        f.write('    print("IDE修复助手")\n')
        f.write('    print("=" * 50)\n\n')
        f.write('    for file_path, line, col, msg in ERRORS:\n')
        f.write('        print(f"\\n文件: {file_path}")\n')
        f.write('        print(f"错误: 第{line}行第{col}列 - {msg}")\n')
        f.write('        print("修复建议:")\n')
        f.write('        \n')
        f.write('        # 读取错误行\n')
        f.write('        with open(file_path, \'r\') as f:\n')
        f.write('            lines = f.readlines()\n')
        f.write('        \n')
        f.write('        if line <= len(lines):\n')
        f.write('            error_line = lines[line - 1].strip()\n')
        f.write('            print(f"  当前行: {error_line}")\n')
        f.write('            \n')
        f.write('            # 生成修复建议\n')
        f.write('            if "illegal target" in msg:\n')
        f.write('                print("  建议: 移除参数名周围的引号")\n')
        f.write('                print("  示例: \\"param\\" -> param")\n')
        f.write('            elif "unterminated string" in msg:\n')
        f.write('                print("  建议: 添加闭合的引号")\n')
        f.write('                print("  示例: \\"value -> \\"value\\"")\n')
        f.write('            elif "invalid syntax" in msg:\n')
        f.write('                print("  建议: 检查语法，可能需要添加引号或逗号")\n')
        f.write('            \n')
        f.write('            print(f"\\n是否在编辑器中打开? (y/n)")\n')
        f.write('            # input()  # 取消注释以启用交互\n')
        f.write('            # open_in_editor(file_path, line)\n\n')

        f.write('if __name__ == "__main__":\n')
        f.write('    run()\n')

    os.chmod('ide_fix_commands.py', 0o755)

def create_batch_fix_script(error_files: List[Tuple[str, Tuple[int, int, str, List[str]]]]) -> None:
    """创建批量修复脚本"""
    with open('batch_fix.py', 'w') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('"""批量语法修复脚本\n')
        f.write('自动修复常见的语法错误\n"""\n\n')
        f.write('import os\nimport re\n\n')

        # 收集所有错误模式
        error_patterns = {}
        for file_path, (line, col, msg, context) in error_files:
            if "illegal target" in msg:
                error_patterns.setdefault('illegal_target', []).append((file_path, line))
            elif "unterminated string" in msg:
                error_patterns.setdefault('unterminated_string', []).append((file_path, line))
            elif "invalid syntax" in msg:
                error_patterns.setdefault('invalid_syntax', []).append((file_path, line))

        # 生成修复函数
        f.write('def fix_illegal_targets():\n')
        f.write('    """修复类型注解中的引号错误"""\n')
        f.write('    files = [\n')
        for file_path, line in error_patterns.get('illegal_target', [])[:20]:
            f.write(f'        "{file_path}",\n')
        f.write('    ]\n\n')
        f.write('    for file_path in files:\n')
        f.write('        if os.path.exists(file_path):\n')
        f.write('            with open(file_path, \'r\') as f:\n')
        f.write('                content = f.read()\n')
        f.write('            \n')
        f.write('            # 移除参数名中的引号\n')
        f.write('            import re\n')
        f.write('            content = re.sub(r\'^(\\s+)"([^"]+)":\', r\'\\1\\2:\', content, flags=re.MULTILINE)\n')
        f.write('            \n')
        f.write('            with open(file_path, \'w\') as f:\n')
        f.write('                f.write(content)\n')
        f.write('            print(f"修复: {file_path}")\n\n')

        f.write('def fix_unterminated_strings():\n')
        f.write('    """修复未闭合的字符串"""\n')
        f.write('    files = [\n')
        for file_path, line in error_patterns.get('unterminated_string', [])[:20]:
            f.write(f'        "{file_path}",\n')
        f.write('    ]\n\n')
        f.write('    for file_path in files:\n')
        f.write('        if os.path.exists(file_path):\n')
        f.write('            with open(file_path, \'r\') as f:\n')
        f.write('                lines = f.readlines()\n')
        f.write('            \n')
        f.write('            for i, line in enumerate(lines):\n')
        f.write('                if line.count(\'"\') % 2 == 1:\n')
        f.write('                    if line.rstrip().endswith(\',\'):\n')
        f.write('                        lines[i] = line[:-1] + \'",\\n\'\n')
        f.write('                    else:\n')
        f.write('                        lines[i] = line + \'"\\n\'\n')
        f.write('            \n')
        f.write('            with open(file_path, \'w\') as f:\n')
        f.write('                f.writelines(lines)\n')
        f.write('            print(f"修复: {file_path}")\n\n')

        f.write('def main():\n')
        f.write('    print("批量修复脚本")\n')
        f.write('    print("=" * 40)\n\n')
        f.write('    print("1. 修复类型注解错误...")\n')
        f.write('    fix_illegal_targets()\n\n')
        f.write('    print("\\n2. 修复未闭合字符串...")\n')
        f.write('    fix_unterminated_strings()\n\n')
        f.write('    print("\\n修复完成!")\n\n')

        f.write('if __name__ == "__main__":\n')
        f.write('    main()\n')

    os.chmod('batch_fix.py', 0o755)

def main():
    """主函数"""
    print("智能语法检查和修复工具")
    print("=" * 60)

    # 查找所有Python文件
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    print(f"找到 {len(python_files)} 个Python文件")

    # 检查语法错误
    print("\n检查语法错误...")
    error_files = []
    checker = PythonSyntaxChecker()

    for file_path in python_files:
        error_info = checker.check_file(file_path)
        if error_info:
            error_files.append((file_path, error_info))

    print(f"发现 {len(error_files)} 个文件有语法错误")

    if not error_files:
        print("\n🎉 所有文件语法正确!")
        return True

    # 尝试自动修复
    print("\n尝试自动修复...")
    fixed_count = 0

    for file_path, error_info in error_files[:50]:  # 先处理前50个
        print(f"\n修复: {file_path}")
        print(f"  错误: 第{error_info[0]}行 - {error_info[2][:50]}...")

        if fix_file_with_context(file_path):
            # 再次检查
            new_error = checker.check_file(file_path)
            if not new_error:
                print(f"  ✓ 修复成功!")
                fixed_count += 1
            else:
                print(f"  ✗ 仍有错误")
        else:
            print(f"  ✗ 无法自动修复")

    # 创建辅助脚本
    print("\n创建辅助脚本...")

    # 获取最新错误列表
    remaining_errors = []
    for file_path in python_files:
        error_info = checker.check_file(file_path)
        if error_info:
            remaining_errors.append((file_path, error_info))

    create_ide_commands(remaining_errors)
    create_batch_fix_script(remaining_errors)

    # 生成快速修复命令
    with open('quick_fix.sh', 'w') as f:
        f.write('#!/bin/bash\n')
        f.write('# 快速修复命令\n\n')
        f.write('echo "使用Python编译器检查语法错误..."\n\n')

        for file_path, (line, col, msg, context) in remaining_errors[:10]:
            f.write(f'echo "文件: {file_path}"\n')
            f.write(f'echo "  第{line}行: {msg}"\n')
            f.write(f'python -m py_compile "{file_path}" 2>&1 | head -20\n')
            f.write('echo "---"\n')

    os.chmod('quick_fix.sh', 0o755)

    # 最终统计
    print("\n" + "=" * 60)
    print(f"自动修复成功: {fixed_count} 个文件")

    success_count = len(python_files) - len(remaining_errors)
    print(f"语法正确: {success_count}/{len(python_files)} ({success_count/len(python_files)*100:.1f}%)")
    print(f"剩余错误: {len(remaining_errors)} 个文件")

    if remaining_errors:
        print("\n可用的修复工具:")
        print("1. ./batch_fix.py - 批量修复常见错误")
        print("2. python -c 'import ide_fix_commands; ide_fix_commands.run()' - IDE修复助手")
        print("3. ./quick_fix.sh - 查看详细错误信息")
        print("\n建议运行: ./batch_fix.py")

        return False
    else:
        print("\n🎉 所有文件语法正确!")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
