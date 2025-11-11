#!/usr/bin/env python3
"""
简单A002冲突修复器
直接替换文件中的id参数为entity_id
"""

import os


def fix_file_a002(file_path, replacements):
    """修复单个文件中的A002问题"""
    if not os.path.exists(file_path):
        return False

    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original = content
        for replacement_pair in replacements:
            old, new = replacement_pair
            content = content.replace(old, new)

        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception:
        return False

def main():
    """主函数"""

    # 需要修复的文件列表
    files_to_fix = [
        'src/repositories/base_fixed.py',
        'src/repositories/prediction.py',
        'src/services/content_analysis.py'
    ]

    total_fixed = 0

    for file_path in files_to_fix:
        # 标准的id参数替换
        replacements = [
            ('(self, id:', '(self, entity_id:'),
            ('self.id = id', 'self.id = entity_id'),
            ('.id == id', '.id == entity_id'),
            ('id:', 'entity_id:'),  # 函数参数
        ]

        if fix_file_a002(file_path, replacements):
            total_fixed += 1
        else:
            pass

    if total_fixed > 0:

        # 检查剩余A002问题
        os.popen("ruff check src/ --output-format=concise | grep 'A002' | wc -l").read().strip()

        # 提交修复
        os.system('git add . && git commit -m "fix: 修复剩余的A002参数冲突问题"')
    else:
        pass


if __name__ == "__main__":
    main()
