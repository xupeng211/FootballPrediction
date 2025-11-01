#!/usr/bin/env python3
"""
修复配置文件类型注解导入的脚本
"""

import os
import re

def fix_config_imports():
    """修复配置文件的类型注解导入"""

    config_files = [
        'config/batch_processing_config.py',
        'config/cache_strategy_config.py',
        'config/distributed_cache_config.py',
        'config/stream_processing_config.py'
    ]

    for config_file in config_files:
        if not os.path.exists(config_file):
            continue

        print(f"🔧 修复类型注解导入: {config_file}")

        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 在第一个三引号注释后添加类型导入
        if 'from typing import' not in content:
            content = re.sub(
                r'"""([^"]*)"""\s*\n',
                r'"""\1"""\n\nfrom typing import Dict, Any, List, Optional\n',
                content,
                count=1
            )

        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ 已修复: {config_file}")

def main():
    """主函数"""
    print("🔧 开始修复配置文件类型注解导入...")
    fix_config_imports()
    print("✅ 类型注解导入修复完成!")

if __name__ == "__main__":
    main()