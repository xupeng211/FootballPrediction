#!/usr/bin/env python3
"""
快速语法错误修复工具
"""

import os
import re
from pathlib import Path

def fix_alert_engine_file():
    """修复alert_engine.py文件的语法错误"""
    file_path = Path("src/alerting/alert_engine.py")
    if not file_path.exists():
        print(f"❌ {file_path} 不存在")
        return False

    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        # 修复1: isinstance参数错误
        content = re.sub(
            r'isinstance\(value, \(int\)\)',
            'isinstance(value, int)',
            content
        )

        # 修复2: except语句缩进错误
        content = re.sub(
            r'return float\(value\) if isinstance\(value, int\) else None\s*\n\s+except Exception:\s*\n\s+return None',
            'return float(value) if isinstance(value, int) else None\n    except Exception:\n        return None',
            content,
            flags=re.MULTILINE
        )

        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            print(f"✅ 修复了 {file_path}")
            return True
        else:
            print(f"ℹ️  {file_path} 无需修复")
            return True

    except Exception as e:
        print(f"❌ 修复 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    print("🚀 快速语法错误修复工具")
    print("=" * 40)

    if fix_alert_engine_file():
        print("✅ 关键语法错误修复完成")
    
    return True

if __name__ == "__main__":
    main()
