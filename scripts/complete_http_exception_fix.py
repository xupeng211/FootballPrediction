#!/usr/bin/env python3
"""
完整HTTPException修复脚本
Complete HTTPException Fix Script

彻底修复所有HTTPException语法问题。
"""

import os
import re


def complete_fix_file(file_path):
    """完整修复文件的HTTPException问题"""

    try:
        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复1: 删除多余的右括号和异常链
        # 查找: )  # TODO: 将魔法数字...\n            ) from e  # TODO: B904 exception chaining
        # 替换为: ) from e  # TODO: B904 exception chaining
        pattern1 = r'\)\s*#\s*TODO:\s*将魔法数字\s*\d+\s*提取为常量\s*\n\s*\)\s+from\s+e\s*#\s*TODO:\s*B904\s+exception\s+chaining'
        replacement1 = ') from e  # TODO: B904 exception chaining'

        content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)

        # 修复2: 处理复杂的分离情况
        # 查找: raise HTTPException(... from e\n            status_code=...\n            detail=...\n        )
        pattern2 = r'raise HTTPException\(\s*\.\.\.\s+from\s+e\s*\n((?:\s+.*?\n)*?)\s*\)'
        def fix_pattern2_match(match):
            inner = match.group(1)
            return f'raise HTTPException(\n{inner})'

        content = re.sub(pattern2, fix_pattern2_match, content, flags=re.MULTILINE)

        # 修复3: 删除多余的空括号行
        pattern3 = r'raise HTTPException\(\s*\n\s*\)\s*\n((?:\s+status_code=.*?\n)*)'
        replacement3 = r'raise HTTPException(\n\1)'

        content = re.sub(pattern3, replacement3, content, flags=re.MULTILINE)

        # 修复4: 清理文件末尾的异常链片段
        pattern4 = r'\n\s*\)\s+from\s+e\s*#\s*TODO:\s*B904\s+exception\s+chaining\s*$'
        content = re.sub(pattern4, '', content)

        # 修复5: 统一异常链格式
        pattern5 = r'\)\s*#\s*TODO:\s*将魔法数字\s*\d+\s*提取为常量\s*\n\s*\)\s+from\s+e\s*#\s*TODO:\s*B904\s+exception\s+chaining'
        replacement5 = ') from e  # TODO: B904 exception chaining'

        content = re.sub(pattern5, replacement5, content, flags=re.MULTILINE)

        # 修复6: 处理特殊格式问题
        # 删除多余的右括号行
        content = re.sub(r'\n\s*\)\s*$', '', content)

        # 写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        else:
            return False

    except Exception as e:
        print(f"修复失败 {file_path}: {e}")
        return False

def main():
    """主函数"""

    api_files = [
        "src/api/betting_api.py",
        "src/api/features.py",
        "src/api/features_simple.py",
        "src/api/middleware.py",
        "src/api/performance_management.py",
        "src/api/predictions_enhanced.py",
        "src/api/predictions_srs_simple.py",
        "src/api/realtime_streaming.py",
        "src/api/tenant_management.py",
        "src/api/routes/user_management.py"
    ]

    print("🔧 完整HTTPException修复器启动...")
    print(f"📁 目标文件: {len(api_files)} 个")

    fixed_count = 0

    for file_path in api_files:
        if os.path.exists(file_path):
            print(f"\n🔧 处理: {file_path}")
            if complete_fix_file(file_path):
                print("  ✅ 修复完成")
                fixed_count += 1
            else:
                print("  ℹ️  无需修复")
        else:
            print(f"\n⚠️  文件不存在: {file_path}")

    print(f"\n{'='*50}")
    print("📊 修复统计:")
    print(f"  ✅ 成功修复: {fixed_count} 个文件")
    print(f"  📁 总文件数: {len(api_files)} 个文件")

    print("\n🎯 验证修复效果:")
    print("  ruff check src/api/betting_api.py --output-format=concise")

    print("\n✨ 完整修复完成!")

if __name__ == "__main__":
    main()
