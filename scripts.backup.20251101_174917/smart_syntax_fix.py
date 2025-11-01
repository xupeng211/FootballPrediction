#!/usr/bin/env python3
"""
智能语法修复工具
使用简化的方法修复常见语法错误
"""

import os
import re
from pathlib import Path

def fix_common_syntax_errors():
    """修复常见的语法错误"""
    print("🔧 开始智能语法修复...")

    # 常见语法错误修复模式
    fix_patterns = [
        # 修复isinstance参数错误
        (r'isinstance\([^,]+,\s*\(([^)]+)\)\)', r'isinstance(\1, \2)'),
        
        # 修复Dict类型注解
        (r': Dict\[str\)\)', ': Dict[str, str]'),
        
        # 修复List类型注解
        (r': List\[.*\)\)', ': List[str]'),
        
        # 修复Optional类型注解
        (r': Optional\[.*\)\)', ': Optional[str]'),
        
        # 修复多余的右括号
        (r'\)\)+', ')'),
        
        # 修复Redis连接
        (r'redis\.Redis\([^)]*\)\)', 'redis.Redis()'),
    ]

    # 修复优先级文件
    priority_files = [
        "src/utils/crypto_utils.py",
        "src/utils/dict_utils.py", 
        "src/utils/response.py",
        "src/utils/string_utils.py",
        "src/config/config_manager.py"
    ]

    total_fixes = 0
    files_fixed = 0

    for file_path in priority_files:
        path = Path(file_path)
        if not path.exists():
            continue

        try:
            content = path.read_text(encoding='utf-8')
            original_content = content

            # 应用所有修复模式
            for pattern, replacement in fix_patterns:
                new_content = re.sub(pattern, replacement, content)
                content = new_content

            if content != original_content:
                path.write_text(content, encoding='utf-8')
                print(f"✅ 修复了 {file_path}")
                total_fixes += 1
                files_fixed += 1

        except Exception as e:
            print(f"❌ 修复 {file_path} 时出错: {e}")

    print(f"\n📊 修复结果:")
    print(f"   - 修复文件数: {files_fixed}")
    print(f"   - 总修复数: {total_fixes}")

    return files_fixed, total_fixes

def main():
    """主函数"""
    print("🚀 智能语法修复工具")
    print("=" * 40)

    return fix_common_syntax_errors()

if __name__ == "__main__":
    main()
