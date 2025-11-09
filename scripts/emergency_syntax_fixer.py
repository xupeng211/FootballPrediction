#!/usr/bin/env python3
"""
紧急语法错误修复工具
专门修复B904修复过程中产生的语法错误
"""

import re
from pathlib import Path

def fix_duplicate_brackets():
    """修复重复的右括号问题"""

    # 需要修复的文件
    target_files = [
        "src/api/optimization/cache_performance_api.py",
        "src/api/optimization/database_performance_api.py",
        "src/realtime/match_api.py"
    ]

    total_fixes = 0

    for file_path in target_files:
        if not Path(file_path).exists():
            print(f"⚠️ 文件不存在: {file_path}")
            continue

        print(f"🔧 修复文件: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 备份原文件
            backup_path = file_path + '.syntax_backup'
            with open(backup_path, 'w', encoding='utf-8') as backup:
                backup.write(content)

            original_content = content

            # 修复模式1: 删除重复的右括号行
            # 匹配: ) from e\n        )
            content = re.sub(r'\) from e\n\s*\)', r') from e', content)

            # 修复模式2: 删除多余的右括号行
            # 匹配: }\n        )
            content = re.sub(r'\}\n\s*\)', r'}', content)

            # 修复模式3: 修复装饰器行中的异常链
            # 匹配: @router.get("/path") from e
            content = re.sub(r'(@router\.[^(]+\([^)]*\))\s+from e', r'\1', content)

            # 修复模式4: 删除连续的右括号
            # 匹配: )) from e
            content = re.sub(r'\)\)\s+from e', r') from e', content)

            # 修复模式5: 删除多余的空行和括号
            # 匹配: \n        )\n
            lines = content.split('\n')
            fixed_lines = []

            i = 0
            while i < len(lines):
                line = lines[i]

                # 检查是否是多余的右括号行
                if line.strip() == ')' and i > 0:
                    prev_line = lines[i-1].strip()
                    # 如果前一行以 from e 结束，则删除当前行
                    if prev_line.endswith(') from e'):
                        print(f"  ✅ 删除多余的右括号: 行 {i+1}")
                        total_fixes += 1
                        i += 1
                        continue
                    # 如果前一行是完整的raise语句，也删除
                    elif 'raise HTTPException(' in prev_line and ')' in prev_line:
                        print(f"  ✅ 删除多余的右括号: 行 {i+1}")
                        total_fixes += 1
                        i += 1
                        continue

                fixed_lines.append(line)
                i += 1

            content = '\n'.join(fixed_lines)

            # 写入修复后的内容
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"💾 已保存修复后的文件")
            else:
                print(f"ℹ️ 文件无需修改")
                # 删除不需要的备份
                Path(backup_path).unlink(missing_ok=True)

        except Exception as e:
            print(f"❌ 修复文件 {file_path} 时出错: {e}")

    return total_fixes

def verify_syntax_fixes():
    """验证语法修复效果"""
    print("\n🔍 验证语法修复效果...")

    target_files = [
        "src/api/optimization/cache_performance_api.py",
        "src/api/optimization/database_performance_api.py",
        "src/realtime/match_api.py"
    ]

    syntax_errors = 0

    for file_path in target_files:
        if not Path(file_path).exists():
            continue

        try:
            # 尝试编译文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            compile(content, file_path, 'exec')
            print(f"✅ {file_path}: 语法正确")

        except SyntaxError as e:
            print(f"❌ {file_path}: 语法错误 - {e}")
            syntax_errors += 1
        except Exception as e:
            print(f"⚠️ {file_path}: 其他错误 - {e}")

    return syntax_errors

def main():
    """主函数"""
    print("🚨 紧急语法错误修复工具")
    print("=" * 40)

    print("🔧 开始修复语法错误...")
    fix_count = fix_duplicate_brackets()

    print(f"\n📊 修复统计:")
    print(f"  🔧 修复操作: {fix_count} 次")

    print("\n🔍 验证修复效果...")
    syntax_errors = verify_syntax_fixes()

    if syntax_errors == 0:
        print("🎉 所有语法错误已修复!")
    else:
        print(f"⚠️ 还有 {syntax_errors} 个文件存在语法错误")

if __name__ == "__main__":
    main()