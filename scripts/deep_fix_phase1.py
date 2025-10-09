#!/usr/bin/env python3
"""
深度修复Phase 1剩余错误
"""

import subprocess
import re
from pathlib import Path

def run_command(cmd):
    """运行命令并返回结果"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr

def fix_syntax_errors():
    """修复语法错误"""
    print("🔧 修复语法错误...")

    # 获取所有有语法错误的文件
    cmd = "ruff check src/ --select=E999 --output-format=concise | cut -d: -f1 | sort -u"
    stdout, stderr = run_command(cmd)

    files_with_syntax_errors = stdout.strip().split('\n') if stdout.strip() else []

    for file_path in files_with_syntax_errors:
        if not file_path or not Path(file_path).exists():
            continue

        print(f"  修复 {file_path}")

        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 修复常见的语法错误模式

        # 1. 修复未闭合的括号后跟导入语句
        content = re.sub(
            r'\)\s*\n\s*from\s+\.\.+import',
            ')\n\nfrom ..import',
            content
        )

        # 2. 修复类型注解中的语法错误
        content = re.sub(
            r'(\w+)\s*:\s*:\s*(\w+)',
            r'\1: \2',
            content
        )

        # 3. 修复意外的缩进
        lines = content.split('\n')
        fixed_lines = []
        for i, line in enumerate(lines):
            # 移除文件开头的意外缩进
            if i < 5 and line.strip() and not line.startswith('#'):
                # 如果是文件开头且有缩进，移除缩进
                if re.match(r'^\s+\w+', line):
                    fixed_lines.append(line.lstrip())
                    continue

            fixed_lines.append(line)

        content = '\n'.join(fixed_lines)

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

def fix_e402_errors():
    """修复E402导入组织错误"""
    print("\n🔧 修复E402导入组织错误...")

    # 获取所有E402错误
    cmd = "ruff check src/ --select=E402 --output-format=concise"
    stdout, stderr = run_command(cmd)

    errors = stdout.strip().split('\n') if stdout.strip() else []

    # 按文件分组
    files_to_fix = {}
    for error in errors:
        if not error:
            continue
        file_path = error.split(':')[0]
        if file_path not in files_to_fix:
            files_to_fix[file_path] = []
        files_to_fix[file_path].append(error)

    for file_path, error_list in files_to_fix.items():
        print(f"  修复 {file_path} ({len(error_list)}个错误)")

        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 收集所有导入语句
        imports = []
        non_import_lines = []

        lines = content.split('\n')
        for line in lines:
            stripped = line.strip()
            # 检查是否是导入语句
            if (stripped.startswith('import ') or
                stripped.startswith('from ')) and \
                not stripped.startswith('#'):
                imports.append(line)
            else:
                non_import_lines.append(line)

        # 重新组织文件
        # 文件开头：文档字符串、shebang、编码
        header_lines = []
        other_lines = []

        for line in non_import_lines:
            if line.strip().startswith('"""') or \
               line.strip().startswith('\'\'\'') or \
               line.startswith('#!') or \
               'coding' in line or \
               not line.strip():
                header_lines.append(line)
            else:
                other_lines.append(line)

        # 构建新内容
        new_content = '\n'.join(header_lines)
        if header_lines and (imports or other_lines):
            new_content += '\n'

        # 添加导入语句
        if imports:
            new_content += '\n'.join(imports) + '\n\n'

        # 添加其他代码
        new_content += '\n'.join(other_lines)

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

def fix_f401_errors():
    """修复F401未使用导入错误"""
    print("\n🔧 修复F401未使用导入错误...")

    # 使用ruff自动修复
    cmd = "ruff check src/ --select=F401 --fix"
    stdout, stderr = run_command(cmd)
    print(f"  自动修复完成")

def main():
    print("🚀 开始深度修复Phase 1剩余错误...")

    # 1. 修复语法错误
    fix_syntax_errors()

    # 2. 修复E402导入组织错误
    fix_e402_errors()

    # 3. 修复F401未使用导入
    fix_f401_errors()

    # 4. 修复F811重复定义
    print("\n🔧 修复F811重复定义...")
    cmd = "ruff check src/ --select=F811 --fix"
    stdout, stderr = run_command(cmd)

    # 5. 检查修复结果
    print("\n📊 检查修复结果...")
    cmd = "ruff check src/ --select=SyntaxError,E402,F401,F811,E722 | wc -l"
    stdout, stderr = run_command(cmd)
    remaining = int(stdout.strip()) if stdout.strip() else 0

    print(f"\n✅ 修复完成！剩余错误数：{remaining}")

    if remaining > 0:
        print("\n⚠️  仍有部分错误未修复，请查看具体错误信息")
        cmd = "ruff check src/ --select=SyntaxError,E402,F401,F811,E722 --output-format=concise | head -20"
        stdout, stderr = run_command(cmd)
        print(stdout)

if __name__ == "__main__":
    main()