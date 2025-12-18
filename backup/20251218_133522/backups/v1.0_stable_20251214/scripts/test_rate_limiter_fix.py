#!/usr/bin/env python3
"""
测试 RateLimiter 修复
Test RateLimiter Fix
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

async def test_rate_limiter():
    """测试 RateLimiter 修复"""
    try:
        print("🔍 测试 RateLimiter 修复...")

        # 导入修复后的模块
        from collectors.fotmob_api_collector import FotMobAPICollector

        print("✅ 模块导入成功")

        # 测试 FotMobAPICollector 初始化
        print("🔍 测试 FotMobAPICollector 初始化...")
        collector = FotMobAPICollector(
            max_concurrent=4,
            timeout=30,
            max_retries=3,
            base_delay=1.0,
            enable_proxy=False,
            enable_jitter=True
        )

        print("✅ FotMobAPICollector 初始化成功！")

        # 测试异步初始化
        print("🔍 测试异步初始化...")
        await collector.initialize()
        print("✅ 异步初始化成功！")

        # 测试清理
        print("🔍 测试资源清理...")
        await collector.close()
        print("✅ 资源清理成功！")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_rate_limiter_directly():
    """直接测试 RateLimiter"""
    try:
        print("🔍 直接测试 RateLimiter...")

        from collectors.rate_limiter import RateLimiter

        # 创建正确的配置
        config = {
            "fotmob.com": {
                "rate": 2.0,
                "burst": 5,
                "max_wait_time": 30.0
            },
            "default": {
                "rate": 1.0,
                "burst": 1,
                "max_wait_time": 30.0
            }
        }

        limiter = RateLimiter(config=config)
        print("✅ RateLimiter 初始化成功！")

        # 测试 acquire 方法
        print("🔍 测试 acquire 方法...")
        async with limiter.acquire("fotmob.com"):
            print("✅ acquire 方法调用成功！")

        return True

    except Exception as e:
        print(f"❌ 直接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🧪 开始测试 RateLimiter 修复")

    # 测试1: 直接测试 RateLimiter
    print("\n📋 测试 1: 直接测试 RateLimiter")
    test1_success = await test_rate_limiter_directly()

    # 测试2: 测试 FotMobAPICollector 集成
    print("\n📋 测试 2: 测试 FotMobAPICollector 集成")
    test2_success = await test_rate_limiter()

    # 总结
    print("\n📊 测试总结:")
    print(f"  直接测试 RateLimiter: {'✅ 通过' if test1_success else '❌ 失败'}")
    print(f"  FotMobAPICollector 集成: {'✅ 通过' if test2_success else '❌ 失败'}")

    if test1_success and test2_success:
        print("\n🎉 所有测试通过！RateLimiter 修复成功！")
        return True
    else:
        print("\n❌ 测试失败，仍有问题需要修复")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
