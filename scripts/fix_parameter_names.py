#!/usr/bin/env python3
"""
修复函数调用中的参数名称问题
"""

import re
import os
from pathlib import Path

def fix_parameter_names_in_file(file_path):
    """修复单个文件中的参数名称问题"""
    if not os.path.exists(file_path):
        return False, "File not found"

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Error reading file: {e}"

    original_content = content
    changes_made = []

    # 修复特定的构造函数调用
    patterns_to_fix = [
        # Team 构造函数：_stats → stats
        (r'Team\([^)]*?_stats\s*=', r'Team(stats='),

        # CommandResult 构造函数：_data → data
        (r'CommandResult\([^)]*?_data\s*=', r'CommandResult(data='),

        # CommandResponse 构造函数：_data → data
        (r'CommandResponse\([^)]*?_data\s*=', r'CommandResponse(data='),

        # AuditEvent 构造函数：_metadata → metadata
        (r'AuditEvent\([^)]*?_metadata\s*=', r'AuditEvent(metadata='),

        # PredictionOutput 构造函数：_metadata → metadata
        (r'PredictionOutput\([^)]*?_metadata\s*=', r'PredictionOutput(metadata='),

        # create_strategy 方法调用：_config → config
        (r'\.create_strategy\([^)]*?_config\s*=', r'.create_strategy(config='),

        # initialize 方法调用中的各种参数
        (r'\.initialize\([^)]*?_config\s*=', r'.initialize(config='),
        (r'\.initialize\([^)]*?_data\s*=', r'.initialize(data='),
    ]

    for pattern, replacement in patterns_to_fix:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changes_made.append(f"Applied parameter fix: {pattern}")
            content = new_content

    # 更复杂的修复：处理多行函数调用
    # 修复跨行的构造函数调用
    multiline_patterns = [
        # Team 构造函数（多行）
        (r'Team\(\s*[^)]*?_stats\s*=\s*([^,)]+)\s*,', r'Team(stats=\1,'),
        (r'Team\(\s*[^)]*?,\s*_stats\s*=\s*([^,)]+)\s*\)', r'Team(stats=\1)'),

        # CommandResult 构造函数（多行）
        (r'CommandResult\(\s*[^)]*?_data\s*=\s*([^,)]+)\s*,', r'CommandResult(data=\1,'),
        (r'CommandResult\(\s*[^)]*?,\s*_data\s*=\s*([^,)]+)\s*\)', r'CommandResult(data=\1)'),
    ]

    for pattern, replacement in multiline_patterns:
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
        if new_content != content:
            changes_made.append(f"Applied multiline fix: {pattern}")
            content = new_content

    # 如果有修改，写回文件
    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, f"Fixed {len(changes_made)} parameter issues"
        except Exception as e:
            return False, f"Error writing file: {e}"
    else:
        return False, "No changes needed"

def fix_unused_type_ignore_comments(file_path):
    """清理未使用的 type: ignore 注释"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, f"Error reading file: {e}"

    original_content = content

    # 移除重复的 type: ignore 注释
    # 简单的策略：如果一行有多个 type: ignore，只保留一个
    lines = content.split('\n')
    new_lines = []

    for line in lines:
        # 计算 type: ignore 出现的次数
        ignore_count = line.count('type: ignore')
        if ignore_count > 1:
            # 只保留第一个 type: ignore
            first_ignore_pos = line.find('type: ignore')
            before_ignore = line[:first_ignore_pos]
            after_ignore_start = line.find(']', first_ignore_pos)
            if after_ignore_start != -1:
                after_ignore = line[after_ignore_start + 1:]
                # 重新构建行，只保留一个 type: ignore
                new_line = before_ignore + 'type: ignore' + after_ignore
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    new_content = '\n'.join(new_lines)

    if new_content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True, "Cleaned duplicate type: ignore comments"
        except Exception as e:
            return False, f"Error writing file: {e}"
    else:
        return False, "No changes needed"

def fix_files_in_directory(directory, file_patterns=None):
    """修复目录中的文件"""
    if file_patterns is None:
        file_patterns = ['*.py']

    fixed_files = []
    failed_files = []

    for pattern in file_patterns:
        for file_path in Path(directory).rglob(pattern):
            # 跳过一些特殊目录
            if any(skip in str(file_path) for skip in ['.venv', '__pycache__', '.git']):
                continue

            # 修复参数名称
            success1, message1 = fix_parameter_names_in_file(str(file_path))
            # 清理 type: ignore 注释
            success2, message2 = fix_unused_type_ignore_comments(str(file_path))

            if success1 or success2:
                messages = []
                if success1:
                    messages.append(message1)
                if success2:
                    messages.append(message2)
                fixed_files.append((str(file_path), '; '.join(messages)))
                print(f"✅ Fixed: {file_path}")
            else:
                if "No changes needed" not in message1 and "No changes needed" not in message2:
                    failed_files.append((str(file_path), f"{message1}; {message2}"))
                    print(f"❌ Failed: {file_path} - {message1}; {message2}")

    return fixed_files, failed_files

def main():
    """主函数"""
    print("🔧 开始修复参数名称问题...")

    src_dir = '/home/user/projects/FootballPrediction/src'

    # 修复 src 目录
    print(f"\n📁 处理目录: {src_dir}")
    fixed, failed = fix_files_in_directory(src_dir, ['*.py'])

    print(f"\n📊 修复结果:")
    print(f"✅ 成功修复: {len(fixed)} 个文件")
    print(f"❌ 修复失败: {len(failed)} 个文件")

    if failed:
        print(f"\n❌ 失败的文件:")
        for file_path, error in failed[:3]:
            print(f"  {file_path}: {error}")
        if len(failed) > 3:
            print(f"  ... 还有 {len(failed) - 3} 个文件")

    # 显示一些修复的例子
    if fixed:
        print(f"\n✅ 修复示例:")
        for file_path, message in fixed[:3]:
            print(f"  {file_path}: {message}")
        if len(fixed) > 3:
            print(f"  ... 还有 {len(fixed) - 3} 个文件")

if __name__ == '__main__':
    main()