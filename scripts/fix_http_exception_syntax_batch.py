#!/usr/bin/env python3
"""
批量修复HTTPException语法错误脚本
Batch Fix HTTPException Syntax Errors Script

专门处理Issue #352中的10个API文件的HTTPException结构问题。
"""

import os
import re
import sys
from pathlib import Path

def fix_http_exception_syntax(file_path):
    """修复单个文件中的HTTPException语法错误"""

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复模式1: 分离的HTTPException参数
        # 将类似下面的结构：
        # raise HTTPException(
        #
        # )
        #     status_code=404,
        #     detail="错误信息",
        # )
        #
        # 修复为：
        # raise HTTPException(
        #     status_code=404,
        #     detail="错误信息",
        # )

        pattern1 = r'raise HTTPException\(\s*\n\s*\)\s*\n(\s+)(status_code=\d+.*?\n\s*detail=.*?\n\s*\)'
        replacement1 = r'raise HTTPException(\n\1\2'

        content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE | re.DOTALL)

        # 修复模式2: 文件末尾多余的异常链片段
        # 删除文件末尾的: ) from e  # TODO: B904 exception chaining
        pattern2 = r'\n\s*\)\s+from\s+e\s*#\s*TODO:\s*B904\s+exception\s+chaining\s*$'
        content = re.sub(pattern2, '', content, flags=re.MULTILINE)

        # 修复模式3: HTTPException参数分散问题
        # 将:
        # raise HTTPException(
        #     ... from e
        # )
        #     status_code=422,
        #     detail="错误信息",
        # )
        #
        # 修复为:
        # raise HTTPException(
        #     status_code=422,
        #     detail="错误信息",
        # )

        pattern3 = r'raise HTTPException\(\s*\n\s*\.\.\.\s+from\s+e\s*\n\s*\)\s*\n(\s+)(status_code=\d+.*?\n\s*detail=.*?\n\s*\)'
        replacement3 = r'raise HTTPException(\n\1\2'

        content = re.sub(pattern3, replacement3, content, flags=re.MULTILINE | re.DOTALL)

        # 修复模式4: 更复杂的分离情况
        # 处理各种HTTPException参数分离的变体
        patterns = [
            # 基本分离模式
            (r'raise HTTPException\(\s*\n\s*\)\s*\n(\s+)([a-zA-Z_][a-zA-Z0-9_]*=.+?)\s*\)', r'raise HTTPException(\n\1\2)'),

            # 带有换行的分离模式
            (r'raise HTTPException\(\s*\n\s*\)\s*\n((?:\s+[a-zA-Z_][a-zA-Z0-9_]*=.*?\n)+)\s*\)', r'raise HTTPException(\n\1)'),

            # 多行参数分离
            (r'raise HTTPException\(\s*\n\s*\)\s*\n((?:\s+.*?\n)+?)\s*\)', r'raise HTTPException(\n\1)'),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)

        # 修复模式5: 清理多余的空行和空格
        content = re.sub(r'\n\s*\n\s*\)\s*\n(\s+)', r'\n\1', content)
        content = re.sub(r'\n\s*$', '\n', content)  # 确保文件末尾只有一个换行符

        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复完成: {file_path}")
            return True
        else:
            print(f"ℹ️  无需修复: {file_path}")
            return False

    except Exception as e:
        print(f"❌ 修复失败: {file_path} - 错误: {e}")
        return False

def main():
    """主函数"""

    # Issue #352中指定的10个API文件
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

    print("🔧 开始批量修复HTTPException语法错误...")
    print(f"📁 目标文件数量: {len(api_files)}")

    fixed_count = 0
    failed_count = 0

    for file_path in api_files:
        if os.path.exists(file_path):
            if fix_http_exception_syntax(file_path):
                fixed_count += 1
            else:
                print(f"ℹ️  文件无需修复: {file_path}")
        else:
            print(f"⚠️  文件不存在: {file_path}")
            failed_count += 1

    print("\n" + "="*60)
    print(f"📊 修复统计:")
    print(f"  ✅ 修复成功: {fixed_count} 个文件")
    print(f"  ❌ 修复失败: {failed_count} 个文件")
    print(f"  📁 总文件数: {len(api_files)} 个文件")

    if fixed_count > 0:
        print("\n🎯 建议下一步操作:")
        print("  1. 运行语法检查验证修复效果:")
        print("     ruff check src/api/ --output-format=concise")
        print("  2. 运行测试验证功能完整性:")
        print("     python -m pytest tests/unit/api/ -v")
        print("  3. 提交修复结果:")
        print("     git add src/api/ && git commit -m 'fix: 批量修复HTTPException语法错误'")

    print("\n✨ 批量修复完成!")

if __name__ == "__main__":
    main()