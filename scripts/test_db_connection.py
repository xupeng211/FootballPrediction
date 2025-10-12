#!/usr/bin/env python3
"""
测试数据库连接Mock
"""

import sys
import os
import subprocess

def test_db_connection():
    """测试数据库连接是否被正确Mock"""

    # 运行一个测试数据库连接的脚本
    cmd = [
        sys.executable, "-c",
        """
import sys
sys.path.insert(0, 'tests')
sys.path.insert(0, 'src')

# 先导入Mock
import conftest_mock

# 现在测试导入和使用
from src.database.connection import DatabaseManager
import asyncio

async def test_connection():
    db = DatabaseManager()
    print("✓ DatabaseManager 实例化成功")

    # 测试异步会话
    async with db.get_async_session() as session:
        print("✓ 异步会话创建成功")
        result = await session.execute("SELECT 1")
        print(f"✓ 查询执行成功（Mock结果）")

    # 测试同步会话
    with db.get_session() as session:
        print("✓ 同步会话创建成功")
        # 模拟会话操作
        print("✓ 会话操作成功（Mock）")

# 运行测试
asyncio.run(test_connection())
print("\\n✅ 数据库Mock测试通过！")
"""
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    print("输出:")
    print(result.stdout)
    if result.stderr:
        print("错误:")
        print(result.stderr)

    return result.returncode == 0


def test_api_connection():
    """测试API是否可以运行而不超时"""

    print("\n" + "="*60)
    print("测试API端点（无超时）...")

    env = os.environ.copy()
    env['PYTHONPATH'] = 'tests:src'
    env['TESTING'] = 'true'

    # 使用pytest运行一个简单的API测试
    cmd = [
        'pytest', 'tests/unit/api/test_health.py::test_health_check',
        '-v', '--disable-warnings', '--tb=short', '--timeout=5'
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)

        # 检查是否有超时错误
        output = result.stdout + result.stderr
        has_timeout = any(err in output.lower() for err in ['timeout', 'time out', '超时'])

        if has_timeout:
            print("⚠️  检测到超时错误")
            print("错误输出:")
            print(result.stderr[:500])
            return False
        else:
            print("✓ 无超时错误")
            print("输出:")
            print(result.stdout[:500])
            return True

    except subprocess.TimeoutExpired:
        print("⚠️  测试执行超时")
        return False


if __name__ == "__main__":
    print("Phase 3 Mock验证...")
    print("=" * 60)

    # 测试数据库连接
    db_ok = test_db_connection()

    # 测试API
    api_ok = test_api_connection()

    print("\n" + "=" * 60)
    print("总结:")
    print(f"  数据库Mock: {'✅ 通过' if db_ok else '❌ 失败'}")
    print(f"  API测试: {'✅ 通过' if api_ok else '❌ 失败'}")

    if db_ok and api_ok:
        print("\n✅ Phase 3 Mock基本成功！")
        sys.exit(0)
    else:
        print("\n⚠️  Phase 3 需要进一步优化")
        sys.exit(1)