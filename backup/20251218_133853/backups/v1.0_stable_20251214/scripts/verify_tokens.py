#!/usr/bin/env python3
"""
快速验证 FotMob API 令牌是否有效
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def verify_tokens():
    """验证令牌有效性"""
    print("🔐 FotMob API 令牌验证器")
    print("=" * 50)

    # 检查环境变量
    token = os.getenv('FOTMOB_TOKEN')
    secret = os.getenv('FOTMOB_SECRET')

    print(f"📝 FOTMOB_TOKEN: {'✅ 存在' if token else '❌ 缺失'}")
    print(f"📝 FOTMOB_SECRET: {'✅ 存在' if secret else '❌ 缺失'}")

    if not token or not secret:
        print("\n❌ 令牌缺失，无法进行API测试")
        return False

    print(f"📏 Token 长度: {len(token)}")
    print(f"📏 Secret 长度: {len(secret)}")

    try:
        import httpx

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.fotmob.com/',
            'x-mas': token,
            'x-foo': secret,
        }

        # 测试API端点
        test_urls = [
            'https://www.fotmob.com/api/data/leagues?id=47',
            'https://www.fotmob.com/api/data/matches?date=20251207',
        ]

        print("\n🌐 测试API端点...")

        async with httpx.AsyncClient(timeout=10.0) as client:
            for url in test_urls:
                try:
                    response = await client.get(url, headers=headers)
                    status = response.status_code
                    print(f"  {url.split('/')[-1]}: {'✅' if status == 200 else f'❌ ({status})'}")

                    if status == 200:
                        data = response.json()
                        if 'leagues' in str(data).lower() or 'matches' in str(data).lower():
                            print("    📊 数据结构正确")
                        else:
                            print("    ⚠️ 数据结构异常")

                except Exception as e:
                    print(f"  {url.split('/')[-1]}: ❌ 异常 ({e})")

        print("\n✅ 令牌验证完成")
        return True

    except Exception as e:
        print(f"\n❌ 验证过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_tokens())
    sys.exit(0 if success else 1)
