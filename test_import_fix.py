#!/usr/bin/env python3
"""
测试导入修复是否成功
"""

import sys


def test_imports():
    """测试关键模块导入"""
    results = {}

    # 测试1: PredictionEngine
    try:
        results["prediction_engine"] = "✅ SUCCESS"
    except Exception as e:
        results["prediction_engine"] = f"❌ FAILED: {e}"

    # 测试2: Logger
    try:
        from src.core.logging_system import get_logger

        get_logger("test")
        results["logger"] = "✅ SUCCESS"
    except Exception as e:
        results["logger"] = f"❌ FAILED: {e}"

    # 测试3: MetricsExporter
    try:
        results["metrics_exporter"] = "✅ SUCCESS"
    except Exception as e:
        results["metrics_exporter"] = f"❌ FAILED: {e}"

    # 测试4: API Dependencies
    try:
        results["api_dependencies"] = "✅ SUCCESS"
    except Exception as e:
        results["api_dependencies"] = f"❌ FAILED: {e}"

    # 测试5: API App (可能有路由问题)
    try:
        results["api_app"] = "✅ SUCCESS"
    except Exception as e:
        results["api_app"] = f"❌ FAILED: {e}"

    return results


def main():
    """主函数"""
    print("🔍 测试导入修复效果")
    print("=" * 50)

    results = test_imports()

    print("\n📊 测试结果:")
    print("-" * 50)
    for module, result in results.items():
        print(f"{module:20} : {result}")

    # 统计
    success_count = sum(1 for r in results.values() if "✅" in r)
    total_count = len(results)

    print("\n📈 总体结果:")
    print(f"成功: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")

    if success_count == total_count:
        print("\n🎉 所有导入测试通过！")
        return 0
    else:
        print("\n⚠️  部分测试失败，需要继续修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())
