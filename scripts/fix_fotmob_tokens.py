#!/usr/bin/env python3
"""
FotMob API Token 快速修复器
FotMob API Token Quick Fix

基于现有x-mas令牌，手动构造x-foo令牌
"""

import asyncio
import json
import os
import sys
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent))

def generate_foo_token(mas_token: str) -> str:
    """
    基于x-mas令牌生成x-foo令牌
    从现有x-mas中提取foo部分并重新编码
    """
    try:
        # 解码x-mas令牌
        decoded = base64.b64decode(mas_token)
        data = json.loads(decoded.decode('utf-8'))

        # 提取foo字段
        foo_value = data.get('body', {}).get('foo', '')

        if not foo_value:
            # 如果没有foo字段，使用默认值
            foo_value = "production:428fa0355f09ca88f97b178eb5a79ef0cfbd0dfc"

        # 构造新的foo token
        foo_data = {
            "foo": foo_value,
            "timestamp": int(datetime.now().timestamp())
        }

        # 编码为base64
        foo_json = json.dumps(foo_data, separators=(',', ':'))
        foo_token = base64.b64encode(foo_json.encode('utf-8')).decode('utf-8')

        return foo_token

    except Exception as e:
        print(f"❌ 生成foo token失败: {e}")
        return "production:428fa0355f09ca88f97b178eb5a79ef0cfbd0dfc"

def update_env_file(mas_token: str, foo_token: str):
    """
    更新.env文件中的FotMob令牌
    """
    env_path = Path(__file__).parent.parent / '.env'

    if not env_path.exists():
        print(f"❌ .env文件不存在: {env_path}")
        return False

    try:
        # 读取现有.env文件
        with open(env_path, encoding='utf-8') as f:
            lines = f.readlines()

        # 更新令牌
        updated_lines = []
        fotmob_updated = False

        for line in lines:
            if line.strip().startswith('FOTMOB_X_MAS_TOKEN='):
                updated_lines.append(f"FOTMOB_X_MAS_TOKEN={mas_token}\n")
                fotmob_updated = True
            elif line.strip().startswith('FOTMOB_X_FOO_TOKEN='):
                updated_lines.append(f"FOTMOB_X_FOO_TOKEN={foo_token}\n")
                fotmob_updated = True
            else:
                updated_lines.append(line)

        # 如果没有找到FotMob令牌，添加它们
        if not fotmob_updated:
            updated_lines.extend([
                f"FOTMOB_X_MAS_TOKEN={mas_token}\n",
                f"FOTMOB_X_FOO_TOKEN={foo_token}\n"
            ])

        # 写回文件
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)

        print(f"✅ .env文件更新成功: {env_path}")
        return True

    except Exception as e:
        print(f"❌ 更新.env文件失败: {e}")
        return False

def test_fotmob_api(mas_token: str, foo_token: str) -> bool:
    """
    测试FotMob API连通性
    """
    import httpx

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.fotmob.com/',
        'x-mas': mas_token,
        'x-foo': foo_token
    }

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                'https://www.fotmob.com/api/leagues?id=87',
                headers=headers
            )

            if response.status_code == 200:
                print("✅ FotMob API测试成功")
                return True
            else:
                print(f"❌ FotMob API测试失败: {response.status_code}")
                print(f"响应内容: {response.text[:200]}")
                return False

    except Exception as e:
        print(f"❌ API测试异常: {e}")
        return False

def main():
    """
    主修复流程
    """
    print("🔧 FotMob Token 快速修复器")
    print("=" * 50)

    # 最新的x-mas令牌（从之前的输出中提取）
    latest_mas_token = "eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9sZWFndWVzP2lkPTg3IiwiY29kZSI6MTc2NTEyMTc0OTUyNSwiZm9vIjoicHJvZHVjdGlvbjo0MjhmYTAzNTVmMDljYTg4Zjk3YjE3OGViNWE3OWVmMGNmYmQwZGZjIn0sInNpZ25hdHVyZSI6IkIwQzkyMzkxMTM4NTdCNUFBMjk5Rjc5M0QxOTYwRkZCIn0="

    print(f"🔑 使用x-mas令牌: {latest_mas_token[:50]}...")

    # 生成foo令牌
    foo_token = generate_foo_token(latest_mas_token)
    print(f"🔑 生成x-foo令牌: {foo_token}")

    # 测试API
    print("\n🧪 测试API连通性...")
    if test_fotmob_api(latest_mas_token, foo_token):
        print("✅ 令牌验证成功")

        # 更新.env文件
        print("\n📝 更新环境变量...")
        if update_env_file(latest_mas_token, foo_token):
            print("✅ 修复完成！请重启相关服务。")

            # 提供重启命令
            print("\n🔄 重启命令:")
            print("   docker-compose restart data-collector-l2")
            print("   docker-compose restart data-collector")

            return True
        else:
            return False
    else:
        print("❌ 令牌验证失败，需要手动检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
