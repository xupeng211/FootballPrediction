#!/usr/bin/env python3
"""
修复配置文件语法错误的脚本
"""

import os
import re
from pathlib import Path

def fix_config_files():
    """修复配置文件中的语法错误"""

    # 需要修复的配置文件
    config_files = [
        'config/batch_processing_config.py',
        'config/cache_strategy_config.py',
        'config/distributed_cache_config.py',
        'config/stream_processing_config.py'
    ]

    for config_file in config_files:
        if not os.path.exists(config_file):
            print(f"⚠️  配置文件不存在: {config_file}")
            continue

        print(f"🔧 修复配置文件: {config_file}")

        # 读取文件内容
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 修复空的import语句
        content = re.sub(r'from src\.core\.config import\s*\n', '', content)

        # 移除多余的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

        # 如果文件为空或只有注释，创建一个基本的配置文件
        if not content.strip() or content.strip().startswith('"""') and content.strip().endswith('"""'):
            config_name = Path(config_file).stem
            content = f'''"""
{config_name.replace('_', ' ').title()} Configuration
"""

from typing import Dict, Any

class {config_name.replace('_', '').title()}Config:
    """配置类"""

    def __init__(self):
        self.settings: Dict[str, Any] = {{
            # 默认配置
        }}

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.settings.get(key, default)

# 全局配置实例
config = {config_name.replace('_', '').title()}Config()
'''

        # 写回文件
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ 已修复: {config_file}")

def fix_final_system_validation():
    """修复final_system_validation.py的语法错误"""

    file_path = 'final_system_validation.py'
    if not os.path.exists(file_path):
        print(f"⚠️  文件不存在: {file_path}")
        return

    print(f"🔧 修复文件: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复缺少except/finally的try语句
    lines = content.split('\n')
    fixed_lines = []

    for i, line in enumerate(lines):
        if i == 177:  # 第178行(0-indexed)
            if 'try:' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not ('except' in next_line or 'finally' in next_line):
                    fixed_lines.append(line)
                    fixed_lines.append('    except Exception as e:')
                    fixed_lines.append('        print(f"Validation error: {{e}}")')
                    continue
        fixed_lines.append(line)

    content = '\n'.join(fixed_lines)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 已修复: {file_path}")

def fix_noqa_warnings():
    """修复无效的noqa注释"""

    files_to_fix = [
        'src/utils/_retry/__init__.py'
    ]

    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            continue

        print(f"🔧 修复noqa注释: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 修复无效的B311规则代码
        content = re.sub(r'# noqa:\s*B311', '# noqa: B311', content)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ 已修复: {file_path}")

def main():
    """主函数"""
    print("🔧 开始修复配置文件语法错误...")

    fix_config_files()
    fix_final_system_validation()
    fix_noqa_warnings()

    print("✅ 配置文件语法错误修复完成!")

if __name__ == "__main__":
    main()