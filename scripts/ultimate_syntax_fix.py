#!/usr/bin/env python3
"""终极语法错误修复工具 - 处理所有剩余的错误"""

import ast
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Dict

def get_python_syntax_error(file_path: str) -> Optional[Tuple[int, int, str]]:
    """获取Python语法错误的详细信息"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', file_path],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            # 解析错误信息
            error_output = result.stderr
            # 示例: File "test.py", line 10
            #     "key": value,
            #           ^
            # SyntaxError: invalid syntax
            lines = error_output.split('\n')
            for i, line in enumerate(lines):
                if 'line ' in line and 'File "' in line:
                    # 提取行号
                    line_match = re.search(r'line (\d+)', line)
                    if line_match:
                        error_line = int(line_match.group(1))
                        # 尝试获取列位置
                        error_col = None
                        if i + 1 < len(lines) and '^' in lines[i + 1]:
                            error_col = lines[i + 1].find('^') + 1
                        # 获取错误消息
                        error_msg = "Syntax error"
                        for j in range(i, min(i + 5, len(lines))):
                            if 'SyntaxError:' in lines[j]:
                                error_msg = lines[j].split('SyntaxError:')[-1].strip()
                                break
                        return (error_line, error_col or 0, error_msg)
        return None
    except Exception:
        return None

def fix_file_with_ast(file_path: str) -> bool:
    """使用AST修复文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        modified = False

        # 1. 修复类型注解中的括号不匹配
        patterns_to_fix = [
            # Dict[str, List[float] = { -> Dict[str, List[float]] = {
            (r'(\w+)\[([^]]+)=\s*\{', r'\1[\2]] = {'),
            # Optional[List[str] = None] -> Optional[List[str]] = None
            (r'Optional\[(\w+)\[([^\]]+)\]\s*=\s*None\]', r'Optional[\1[\2]]] = None'),
            # List[Dict[str, Any]) -> List[Dict[str, Any]]
            (r'List\[Dict\[str, Any\)\]', r'List[Dict[str, Any]]'),
            # Tuple[str, Any]) -> Tuple[str, Any]]
            (r'Tuple\[([^\]]+)\)\]', r'Tuple[\1]]'),
            # Dict[str, List[float] = { -> Dict[str, List[float]] = {
            (r'Dict\[str,\s*List\[float\]\s*=\s*\{', r'Dict[str, List[float]] = {'),
            # Dict[str, List[float] = {" -> Dict[str, List[float]] = {
            (r'Dict\[str,\s*List\[float\]\s*=\s*\{"', r'Dict[str, List[float]] = {"'),
            # Dict[str, Any]: { -> Dict[str, Any]: {
            (r'Dict\[str,\s*Any\]\s*:\s*\{', r'Dict[str, Any]: {'),
        ]

        for pattern, replacement in patterns_to_fix:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                modified = True

        # 2. 修复列表/字典初始化错误
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            # 修复 "memory": ["", -> "memory": [],
            if ': ["",' in line:
                line = line.replace(': ["',': []')
                modified = True
            # 修复 "cpu": ["", -> "cpu": [],
            if ': ["",' in line:
                line = line.replace(': ["',': []')
                modified = True
            # 修复 : ["", : [} -> : [] }
            if ': ["", : [' in line:
                line = line.replace(': ["", : [',': [] ')
                modified = True
            # 修复 ["", : [} -> []
            if '["", : [' in line:
                line = line.replace('["", : [','[')
                modified = True
            # 修复 {"", : [} -> {}
            if '{"", : [' in line:
                line = line.replace('{"", : [','{')
                modified = True

            fixed_lines.append(line)

        content = '\n'.join(fixed_lines)

        # 3. 修复未闭合的字符串和括号
        try:
            # 尝试解析，如果失败则进行简单修复
            ast.parse(content)
        except SyntaxError:
            # 简单的字符串修复
            lines = content.split('\n')
            for i in range(len(lines)):
                line = lines[i]
                # 检查未闭合的字符串
                if line.count('"') % 2 == 1 and not line.strip().startswith('#'):
                    if not line.endswith(('"', "'", ',')):
                        # 如果行末没有引号，尝试添加
                        if i < len(lines) - 1:
                            next_line = lines[i + 1]
                            if next_line.strip() and not next_line.startswith(('', ')', ']', '}')):
                                line = line + '"'
                                lines[i] = line
                                modified = True
            content = '\n'.join(lines)

        # 写回文件
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"修复失败 {file_path}: {e}")
        return False

def fix_specific_known_errors(file_path: str) -> bool:
    """修复已知的特定错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        modified = False

        # 根据文件路径应用特定修复
        if 'scheduler/job_manager.py' in file_path:
            # 修复 ResourceMonitor 类中的错误
            content = content.replace(
                'self.resource_stats: Dict[str, List[float] = {',
                'self.resource_stats: Dict[str, List[float]] = {'
            )
            content = content.replace(
                '"memory": ["", \n            "cpu": ["",',
                '"memory": [],\n            "cpu": []'
            )
            content = content.replace(
                '"memory": ["", : [}',
                '"memory": []'
            )
            modified = True

        elif 'data/features/feature_definitions.py' in file_path:
            # 修复 MockFeatureView 的参数
            content = re.sub(
                r'"([^"]+)":\s*(Optional\[.*?\]|None)',
                lambda m: f'{m.group(1)}: {m.group(2)}',
                content
            )
            # 修复字典值中的额外引号
            content = content.replace('"team": "data", "type": "match_context"}""', '"team": "data", "type": "match_context"}')
            content = content.replace('"team": "data", "type": "team_performance"}""', '"team": "data", "type": "team_performance"}')
            content = content.replace('"team": "data", "type": "betting_odds"}""', '"team": "data", "type": "betting_odds"}')
            content = content.replace('"team": "data", "type": "historical_matchup"}""', '"team": "data", "type": "historical_matchup"}')
            # 修复特征服务定义
            content = content.replace('"name": "match_prediction_v1",",', '"name": "match_prediction_v1",')
            content = content.replace('"features": [""', '"features": [')
            content = content.replace(']",', '],')
            content = content.replace('"tags": {"model": "match_outcome", "version": "v1"},"', '"tags": {"model": "match_outcome", "version": "v1"}')
            modified = True

        elif 'data/features/feature_store.py' in file_path:
            # 修复类型注解
            content = content.replace(
                'self._temp_dir: Optional[tempfile.TemporaryDirectory[str] = None',
                'self._temp_dir: Optional[tempfile.TemporaryDirectory[str]] = None'
            )
            # 修复配置字典
            content = re.sub(r'"([^"]+)":\s*([^,}]+)', r'\1: \2', content)
            # 修复连接字符串
            content = content.replace('"connection_string": os.getenv("REDIS_URL", "redis://localhost:6379/1")""',
                                    '"connection_string": os.getenv("REDIS_URL", "redis://localhost:6379/1")')
            modified = True

        elif 'lineage/lineage_reporter.py' in file_path:
            # 修复参数定义中的引号
            lines = content.split('\n')
            fixed_lines = []
            for line in lines:
                # 修复函数参数
                if re.match(r'^\s+"[^"]+":\s*\w+', line):
                    line = re.sub(r'^(\s+)"([^"]+)":', r'\1\2:', line)
                # 修复字典键
                if '"marquez_url":' in line:
                    line = line.replace('"marquez_url":', 'marquez_url:')
                if '"namespace":' in line:
                    line = line.replace('"namespace":', 'namespace:')
                fixed_lines.append(line)
            content = '\n'.join(fixed_lines)
            modified = True

        # 通用修复：移除多余的引号和逗号
        content = re.sub(r'"}""$', '"}', content)  # 移除文件末尾的多余引号
        content = re.sub(r'",', ',', content)  # 修复字符串后的多余逗号

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"特定修复失败 {file_path}: {e}")
        return False

def main():
    """主函数"""
    print("终极语法错误修复工具")
    print("=" * 60)

    # 查找所有Python文件
    python_files = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))

    print(f"找到 {len(python_files)} 个Python文件")

    # 获取有语法错误的文件
    error_files = []
    print("\n检查语法错误...")
    for file_path in python_files:
        error = get_python_syntax_error(file_path)
        if error:
            error_files.append((file_path, error))

    print(f"发现 {len(error_files)} 个文件有语法错误")

    if not error_files:
        print("\n🎉 所有文件语法正确!")
        return True

    # 修复错误
    fixed_count = 0
    for file_path, (line, col, msg) in error_files:
        print(f"\n修复: {file_path}")
        print(f"  错误: 第{line}行{f', 第{col}列' if col > 0 else ''} - {msg}")

        # 尝试特定修复
        if fix_specific_known_errors(file_path):
            print(f"  ✓ 特定修复成功")
            fixed_count += 1
            continue

        # 尝试AST修复
        if fix_file_with_ast(file_path):
            print(f"  ✓ AST修复成功")
            fixed_count += 1
            continue

        # 如果还有错误，显示详细信息
        new_error = get_python_syntax_error(file_path)
        if new_error:
            print(f"  ✗ 仍有错误: 第{new_error[0]}行 - {new_error[2]}")
        else:
            print(f"  ✓ 修复成功")
            fixed_count += 1

    # 最终验证
    print("\n" + "=" * 60)
    print("最终验证...")

    success_count = 0
    remaining_errors = []

    for file_path in python_files:
        error = get_python_syntax_error(file_path)
        if not error:
            success_count += 1
        else:
            remaining_errors.append((file_path, error))

    print(f"\n语法正确: {success_count}/{len(python_files)} ({success_count/len(python_files)*100:.1f}%)")
    print(f"修复成功: {fixed_count} 个文件")

    if remaining_errors:
        print(f"\n剩余 {len(remaining_errors)} 个文件需要手动修复:")
        for file_path, (line, col, msg) in remaining_errors[:10]:  # 只显示前10个
            print(f"  - {file_path}: 第{line}行 - {msg}")

        if len(remaining_errors) > 10:
            print(f"  ... 还有 {len(remaining_errors) - 10} 个文件")

        # 生成修复脚本
        with open('manual_fix_commands.sh', 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("# 手动修复命令\n\n")
            for file_path, (line, col, msg) in remaining_errors:
                f.write(f'echo "修复文件: {file_path}"\n')
                f.write(f'# 错误: 第{line}行 - {msg}\n')
                f.write(f'# vim {file_path} +{line}\n\n')

        os.chmod('manual_fix_commands.sh', 0o755)
        print("\n生成手动修复脚本: manual_fix_commands.sh")

        return False
    else:
        print("\n🎉 所有文件语法正确!")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
