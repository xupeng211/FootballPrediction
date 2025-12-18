#!/usr/bin/env python3
"""
简化的Titan管道测试脚本
用于验证修复后的功能
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_titan_imports():
    """测试Titan相关模块导入"""
    try:
        print("🧪 测试Titan模块导入...")

        # 测试flows导入
        from src.flows.titan_flow import (
            titan_regular_flow,
            titan_live_flow,
            titan_hybrid_flow,
            titan_regular_schedule,
            titan_live_schedule
        )
        print("✅ titan_flow.py 导入成功")

        # 测试tasks导入
        from src.tasks.titan_tasks import (
            fetch_fixtures,
            align_ids,
            batch_collect_odds,
            cleanup_history_data
        )
        print("✅ titan_tasks.py 导入成功")

        # 测试配置导入
        from src.config.titan_settings import get_titan_settings
        print("✅ titan_settings.py 导入成功")

        return True

    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_flow_creation():
    """测试Flow对象创建"""
    try:
        print("\n🎯 测试Flow对象创建...")

        from src.flows.titan_flow import titan_regular_flow

        print(f"✅ Flow对象创建成功: {titan_regular_flow.name}")
        print(f"   Flow描述: {titan_regular_flow.description}")

        return True

    except Exception as e:
        print(f"❌ Flow对象创建失败: {e}")
        return False

async def test_schedule_creation():
    """测试调度对象创建"""
    try:
        print("\n⏰ 测试调度对象创建...")

        from src.flows.titan_flow import (
            titan_regular_schedule,
            titan_live_schedule
        )

        print(f"✅ 常规调度创建成功: {titan_regular_schedule}")
        print(f"✅ 临场调度创建成功: {titan_live_schedule}")

        return True

    except Exception as e:
        print(f"❌ 调度对象创建失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始Titan管道简化测试...")

    tests = [
        ("模块导入测试", test_titan_imports),
        ("Flow创建测试", test_flow_creation),
        ("调度创建测试", test_schedule_creation),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 执行失败: {e}")
            results.append((test_name, False))

    # 输出测试结果
    print("\n📊 测试结果汇总:")
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1

    print(f"\n🎯 总体结果: {passed}/{len(results)} 测试通过")

    if passed == len(results):
        print("🎉 所有测试通过！项目已准备就绪！")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步修复")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)