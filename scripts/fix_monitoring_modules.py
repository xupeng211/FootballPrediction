#!/usr/bin/env python3
"""
监控模块批量修复工具
"""

import re
from pathlib import Path

def fix_monitoring_file(file_path):
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        # 修复常见的缩进模式
        patterns = [
            # 模式1: def method(self, params): docstring code_on_same_line
            (r'(    )def (\w+)\([^)]*\):\s*\"\"\"[^\"]*\"\"\"(.*)', r'\1def \2(\n\1        \"\"\"\"\"\"\"\n\1\3'),
            # 模式2: def method(self, params): code_on_same_line
            (r'(    )def (\w+)\([^)]*\):\s*([^#\n].*)', r'\1def \2(\n\1        \3'),
        ]

        fixed_content = content
        for pattern, replacement in patterns:
            fixed_content = re.sub(pattern, replacement, fixed_content, flags=re.MULTILINE)

        # 手动修复一些特定模式
        fixed_content = re.sub(
            r'def (\w+)\([^)]*\):\s*\"\"\"([^\"]*?)\"\"\"([^#\n]*\n\s+self\.\w+)',
            r'def \1(\n        \"\"\"\2\"\"\"\n\3',
            fixed_content,
            flags=re.MULTILINE
        )

        if fixed_content != content:
            with open(file_path, 'w') as f:
                f.write(fixed_content)
            print(f'✅ 修复 {file_path}')
        else:
            print(f'⚠️  {file_path} 无需修复')

        return True
    except Exception as e:
        print(f'❌ 修复 {file_path} 失败: {e}')
        return False

def main():
    # 需要修复的监控模块文件
    monitoring_files = [
        'src/monitoring/metrics_collector_enhanced.py',
        'src/monitoring/system_monitor.py',
        'src/monitoring/metrics_collector.py',
        'src/monitoring/apm_integration.py',
        'src/monitoring/alert_manager.py',
        'src/monitoring/alert_manager_mod/__init__.py'
    ]

    print('开始批量修复监控模块...')
    success_count = 0
    for file_path in monitoring_files:
        if fix_monitoring_file(file_path):
            success_count += 1

    print(f'修复完成: {success_count}/{len(monitoring_files)}')

    # 验证修复结果
    print('\n验证修复结果:')
    for file_path in monitoring_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            compile(content, file_path, 'exec')
            print(f'✅ {file_path} 语法正确')
        except SyntaxError as e:
            print(f'❌ {file_path} 仍有语法错误: {e}')

if __name__ == "__main__":
    main()