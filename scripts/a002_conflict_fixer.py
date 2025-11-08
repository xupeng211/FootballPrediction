#!/usr/bin/env python3
"""
A002参数冲突快速修复器
批量修复函数参数与Python内置函数冲突的问题
"""

import os
import re


def fix_a002_conflicts():
    """修复A002参数冲突"""

    # 定义需要修复的文件和对应的参数替换规则
    replacements = {
        'src/domain_simple/league.py': [
            (r'def __init__\(\s*self,\s*id:', 'def __init__(\n        self,\n        league_id:'),
            (r'self\.id = id', 'self.id = league_id'),
        ],
        'src/domain_simple/match.py': [
            (r'def __init__\(\s*self,\s*id:', 'def __init__(\n        self,\n        match_id:'),
            (r'self\.id = id', 'self.id = match_id'),
        ],
        'src/domain_simple/odds.py': [
            (r'def __init__\(\s*self,\s*id:', 'def __init__(\n        self,\n        odds_id:'),
            (r'self\.id = id', 'self.id = odds_id'),
        ],
        'src/domain_simple/prediction.py': [
            (r'def __init__\(\s*self,\s*id:', 'def __init__(\n        self,\n        prediction_id:'),
            (r'self\.id = id', 'self.id = prediction_id'),
        ],
        'src/domain_simple/team.py': [
            (r'def __init__\(\s*self,\s*id:', 'def __init__(\n        self,\n        team_id:'),
            (r'self\.id = id', 'self.id = team_id'),
        ],
        'src/domain_simple/user.py': [
            (r'def __init__\(\s*self,\s*id:', 'def __init__(\n        self,\n        user_id:'),
            (r'self\.id = id', 'self.id = user_id'),
        ],
        'src/performance/api.py': [
            (r'def export_\w+\(\s*self,\s*format:', 'def export_\\1(\n        self,\n        export_format:'),
            (r'format=', 'export_format='),
        ],
        'src/repositories/base.py': [
            (r'def get_by_id\(\s*self,\s*id:', 'def get_by_id(\n        self,\n        entity_id:'),
            (r'def delete\(\s*self,\s*id:', 'def delete(\n        self,\n        entity_id:'),
            (r'def update\(\s*self,\s*id:', 'def update(\n        self,\n        entity_id:'),
        ],
    }

    fixed_files = []

    for file_path, patterns in replacements.items():
        if os.path.exists(file_path):
            try:
                with open(file_path, encoding='utf-8') as f:
                    content = f.read()

                original_content = content

                # 应用所有替换规则
                for pattern, replacement in patterns:
                    content = re.sub(pattern, replacement, content)

                # 如果有修改，写回文件
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_files.append(file_path)
                    print(f"✅ 修复完成: {file_path}")
                else:
                    print(f"⚪ 无需修复: {file_path}")

            except Exception as e:
                print(f"❌ 修复失败: {file_path} - {e}")
        else:
            print(f"⚠️  文件不存在: {file_path}")

    return fixed_files

def main():
    """主函数"""
    print("🔧 开始修复A002参数冲突...")

    # 备份当前修改
    os.system("git add .")
    print("💾 已备份当前修改到暂存区")

    # 执行修复
    fixed_files = fix_a002_conflicts()

    if fixed_files:
        print(f"\n🎉 成功修复 {len(fixed_files)} 个文件:")
        for file_path in fixed_files:
            print(f"  - {file_path}")

        # 检查修复效果
        print("\n📊 检查修复效果...")
        remaining_a002 = os.popen("ruff check src/ --output-format=concise | grep 'A002' | wc -l").read().strip()
        print(f"剩余A002问题数量: {remaining_a002}")

        # 提交修复
        print("\n💾 提交修复...")
        os.system('git commit -m "fix: 批量修复A002参数冲突问题"')

    else:
        print("⚠️  没有找到需要修复的文件")

    print("🏁 A002参数冲突修复完成")

if __name__ == "__main__":
    main()
