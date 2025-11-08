#!/usr/bin/env python3
"""
F821未定义名称最终修复器
修复参数替换后引起的未定义名称问题
"""

import os


def fix_f821_issues():
    """修复F821未定义名称问题"""

    # 定义需要修复的文件和具体问题
    fixes = {
        'src/repositories/base_fixed.py': [
            ('entity_id)', 'id)'),  # 恢复不正确的替换
        ],
        'src/repositories/prediction.py': [
            ('entity_id)', 'id)'),  # 恢复不正确的替换
            ('user_id)', 'id)'),    # 恢复不正确的替换
            ('match_id)', 'id)'),   # 恢复不正确的替换
        ],
        'src/scheduler/celery_config.py': [
            ('return len(matches) > 0', 'return len(_matches) > 0'),  # matches未定义
        ],
        'src/services/content_analysis.py': [
            ('content_id)', 'id)'),    # 恢复不正确的替换
            ('user_id)', 'id)'),      # 恢复不正确的替换
        ],
    }

    fixed_files = []

    for file_path, replacements in fixes.items():
        if os.path.exists(file_path):
            try:
                with open(file_path, encoding='utf-8') as f:
                    content = f.read()

                original_content = content
                modified = False

                # 应用修复
                for old, new in replacements:
                    if old in content:
                        content = content.replace(old, new)
                        modified = True

                if modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_files.append(file_path)
                    print(f"✅ 修复F821: {file_path}")

            except Exception as e:
                print(f"❌ 修复失败 {file_path}: {e}")

    return fixed_files

def main():
    """主函数"""
    print("🔧 开始修复F821未定义名称问题...")

    # 备份
    os.system("git add .")
    print("💾 已备份当前修改")

    # 执行修复
    fixed_files = fix_f821_issues()

    if fixed_files:
        print(f"\n🎉 修复了 {len(fixed_files)} 个文件")

        # 检查修复效果
        remaining_f821 = os.popen("ruff check src/ --output-format=concise | grep 'F821' | wc -l").read().strip()
        print(f"剩余F821问题: {remaining_f821}")

        # 提交修复
        os.system('git add . && git commit -m "fix: 修复F821未定义名称问题"')
    else:
        print("⚠️ 没有文件需要修复")

    print("🏁 F821修复完成")

if __name__ == "__main__":
    main()
