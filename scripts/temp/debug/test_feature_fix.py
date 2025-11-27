#!/usr/bin/env python3
"""测试特征生成脚本修复的临时文件"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scripts.generate_features import FeatureGenerator
import asyncio

async def test():
    generator = FeatureGenerator()
    print('🔍 测试数据库连接...')
    success = generator.load_data()
    if success:
        print('✅ 数据库连接成功，特征生成脚本已修复')
        return True
    else:
        print('❌ 数据库连接仍然失败')
        return False

if __name__ == "__main__":
    result = asyncio.run(test())
    print(f'测试结果: {result}')