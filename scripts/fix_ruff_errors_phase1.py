#!/usr/bin/env python3
"""
修复 Ruff 错误 - Phase 1: 自动化修复简单错误
处理 F541 (f-string 无占位符) 和部分其他错误
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

def run_command(cmd: List[str], description: str) -> Tuple[bool, str]:
    """运行命令并返回结果"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"📝 命令: {' '.join(cmd)}")
    print('='*60)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ 成功: {result.stdout[:500]}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ 失败: {e.stderr[:500]}")
        return False, e.stderr

def fix_f541_errors():
    """修复 F541: f-string without any placeholders"""
    print("\n🎯 修复 F541: f-string without any placeholders")

    # 查找所有 F541 错误
    cmd = ["ruff", "check", "--select=F541", "--output-format=json", "src/", "tests/"]
    success, output = run_command(cmd, "查找 F541 错误")

    if not success:
        print("⚠️ 无法获取 F541 错误列表")
        return

    # 使用 ruff 自动修复
    cmd = ["ruff", "check", "--select=F541", "--fix", "src/", "tests/"]
    success, output = run_command(cmd, "自动修复 F541 错误")

    if success:
        print("✅ F541 错误修复完成")
    else:
        print("⚠️ F541 错误修复失败，尝试手动修复...")

        # 手动修复模式
        fix_f541_manually()

def fix_f541_manually():
    """手动修复 F541 错误"""
    patterns = [
        # f"\n" -> "\n"
        (r'f"\\n"', '"\\n"'),
        # f"文本" -> "文本"
        (r'f"([^{}]*)"', r'"\1"'),
        # f'文本' -> '文本'
        (r"f'([^{}]*)'", r"'\1'"),
    ]

    files_to_fix = []
    for root, dirs, files in os.walk("."):
        # 跳过 .venv, __pycache__ 等
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

        for file in files:
            if file.endswith('.py'):
                files_to_fix.append(os.path.join(root, file))

    fixed_count = 0
    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 应用修复模式
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)

            # 如果内容有变化，写回文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_count += 1

        except Exception as e:
            print(f"⚠️ 修复文件 {file_path} 时出错: {e}")

    print(f"✅ 手动修复了 {fixed_count} 个文件的 F541 错误")

def fix_e722_errors():
    """修复 E722: Do not use bare `except`"""
    print("\n🎯 修复 E722: Do not use bare `except`")

    # 使用 ruff 自动修复（如果支持）
    cmd = ["ruff", "check", "--select=E722", "--fix", "src/", "tests/"]
    success, output = run_command(cmd, "尝试自动修复 E722 错误")

    if not success:
        print("⚠️ 自动修复失败，跳过 E722 错误（需要手动处理）")

def fix_unused_variables():
    """修复未使用变量（添加前缀下划线）"""
    print("\n🎯 修复 F841: Local variable is assigned to but never used")

    # 获取所有 F841 错误
    cmd = ["ruff", "check", "--select=F841", "--output-format=json", "src/", "tests/"]
    success, output = run_command(cmd, "查找 F841 错误")

    if not success:
        print("⚠️ 无法获取 F841 错误列表")
        return

    # 生成修复脚本
    fix_script = generate_unused_var_fix_script()
    with open("fix_unused_vars.py", "w") as f:
        f.write(fix_script)

    print("✅ 生成了修复脚本: fix_unused_vars.py")
    print("💡 运行 'python fix_unused_vars.py' 来修复未使用变量")

def generate_unused_var_fix_script():
    """生成修复未使用变量的脚本"""
    return '''#!/usr/bin/env python3
"""
自动修复未使用变量 - 添加下划线前缀
"""

import ast
import os
import re
from pathlib import Path

def fix_unused_in_file(file_path):
    """修复单个文件中的未使用变量"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 获取 ruff 的错误信息
    import subprocess
    cmd = ["ruff", "check", "--select=F841", "--output-format=json", file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return False

    # 解析错误
    try:
        import json
        errors = json.loads(result.stdout)
    except:
        return False

    # 按行号排序，从后往前修复
    errors.sort(key=lambda x: x['location']['row'], reverse=True)

    lines = content.split('\\n')
    modified = False

    for error in errors:
        row = error['location']['row'] - 1  # 转换为0基索引
        if row < len(lines):
            line = lines[row]

            # 提取变量名
            var_name = error['message'].split('`')[1] if '`' in error['message'] else None

            if var_name:
                # 替换变量名（简单情况）
                pattern = rf'\\b{re.escape(var_name)}\\s*='
                if re.search(pattern, line):
                    # 如果已经以下划线开头，跳过
                    if not var_name.startswith('_'):
                        # 添加下划线前缀
                        new_line = re.sub(pattern, f'_{var_name} =', line)
                        lines[row] = new_line
                        modified = True
                        print(f"  修复: {var_name} -> _{var_name} (行 {row+1})")

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\\n'.join(lines))
        return True

    return False

def main():
    """主函数"""
    print("🔧 修复未使用变量...")

    fixed_files = 0
    for py_file in Path('.').rglob('*.py'):
        if '.venv' not in str(py_file) and '__pycache__' not in str(py_file):
            if fix_unused_in_file(str(py_file)):
                fixed_files += 1

    print(f"\\n✅ 修复了 {fixed_files} 个文件的未使用变量")

if __name__ == "__main__":
    main()
'''

def fix_e712_errors():
    """修复 E712: Avoid equality comparisons to `False`"""
    print("\n🎯 修复 E712: Avoid equality comparisons to False")

    patterns = [
        (r'== False', 'is False'),
        (r'!= False', 'is not False'),
        (r'== True', 'is True'),
        (r'!= True', 'is not True'),
    ]

    files_to_fix = []
    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith('.py'):
                files_to_fix.append(os.path.join(root, file))

    for root, dirs, files in os.walk("tests"):
        for file in files:
            if file.endswith('.py'):
                files_to_fix.append(os.path.join(root, file))

    fixed_count = 0
    for file_path in files_to_fix:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 应用修复模式
            for pattern, replacement in patterns:
                content = re.sub(pattern, replacement, content)

            # 如果内容有变化，写回文件
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_count += 1

        except Exception as e:
            print(f"⚠️ 修复文件 {file_path} 时出错: {e}")

    print(f"✅ 修复了 {fixed_count} 个文件的 E712 错误")

def main():
    """主函数"""
    print("🚀 开始 Phase 1: 修复简单 Ruff 错误")
    print("="*60)

    # 1. 修复 F541 (f-string 无占位符)
    fix_f541_errors()

    # 2. 修复 E712 (与 False/True 比较)
    fix_e712_errors()

    # 3. 修复 E722 (裸露 except) - 部分可自动修复
    fix_e722_errors()

    # 4. 生成未使用变量修复脚本
    fix_unused_variables()

    print("\n" + "="*60)
    print("✅ Phase 1 修复完成！")
    print("\n📋 后续步骤：")
    print("1. 运行 'python fix_unused_vars.py' 修复未使用变量")
    print("2. 运行 'ruff check --fix src/ tests/' 进行进一步自动修复")
    print("3. 手动修复剩余的错误")
    print("4. 运行 'make lint' 验证修复结果")

if __name__ == "__main__":
    main()
