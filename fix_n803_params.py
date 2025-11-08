#!/usr/bin/env python3
"""
修复N803参数命名错误
Fix N803 parameter naming errors
"""

import re
from pathlib import Path

def fix_n803_in_file(file_path: Path, replacements: dict[str, str]) -> bool:
    """修复单个文件中的N803错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        modified = False

        for old_param, new_param in replacements.items():
            # 修复函数参数定义
            # 匹配 def func_name(..., X_val, ...) 或 def func_name(..., X, ...)
            pattern = rf'(\s+{old_param}\s*:\s*[^,\)]+)'
            new_content = re.sub(pattern, f'    {new_param}' + content[content.find(old_param):content.find(old_param)+len(old_param)-len(old_param)], content)

            # 更简单的方法：直接替换所有出现的大写参数名
            if old_param in content:
                # 只替换函数参数中的，避免替换类名等
                lines = content.split('\n')
                new_lines = []

                for line in lines:
                    # 检查是否是函数定义行
                    if re.match(r'\s*def\s+', line) and old_param in line:
                        # 替换函数参数
                        line = line.replace(f'{old_param}:', f'{new_param}:')
                        line = line.replace(f'{old_param} =', f'{new_param} =')
                        line = line.replace(f', {old_param},', f', {new_param},')
                        line = line.replace(f', {old_param})', f', {new_param})')
                        line = line.replace(f'({old_param},', f'({new_param},')
                        line = line.replace(f'({old_param})', f'({new_param})')
                        modified = True
                    else:
                        # 在函数体内也要替换
                        if old_param in line and not line.strip().startswith('#'):
                            # 避免替换字符串中的内容
                            if not re.search(rf'["\'][^{""\'}]*{old_param}[^{""\'}]*["\']', line):
                                line = line.replace(f'{old_param}', f'{new_param}')
                                modified = True

                    new_lines.append(line)

                content = '\n'.join(new_lines)

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"修复文件 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    base_path = Path("src")

    # 需要修复的参数映射
    replacements = {
        'X_val': 'x_val',
        'X': 'x'
    }

    # 包含N803错误的文件列表
    files_to_fix = [
        "ml/model_training.py",
        "models/model_training.py",
        "models/prediction_model.py"
    ]

    fixed_count = 0

    for file_path_str in files_to_fix:
        file_path = base_path / file_path_str
        if file_path.exists():
            print(f"正在修复: {file_path}")
            if fix_n803_in_file(file_path, replacements):
                print(f"✓ 修复了: {file_path}")
                fixed_count += 1
            else:
                print(f"- 无需修复或修复失败: {file_path}")
        else:
            print(f"文件不存在: {file_path}")

    print(f"\n总共修复了 {fixed_count} 个文件")

if __name__ == "__main__":
    main()