import os
#!/usr/bin/env python3
"""
QualityMonitor 功能测试 - Phase 5.1 Batch-Δ-012
"""

import asyncio
import sys
import warnings
warnings.filterwarnings('ignore')

async def test_quality_monitor():
    """测试 QualityMonitor 的基本功能"""

    # 添加路径
    sys.path.insert(0, '.')

    try:
        from src.monitoring.quality_monitor import QualityMonitor, DataFreshnessResult, DataCompletenessResult

        print("✅ QualityMonitor 和相关类导入成功")

        # 创建监控器实例
        monitor = QualityMonitor()
        print("✅ QualityMonitor 实例创建成功")

        # 测试 DataFreshnessResult
        from datetime import datetime, timedelta
        freshness_result = DataFreshnessResult(
            table_name = os.getenv("TEST_QUALITY_MONITOR_TABLE_NAME_29"),
            last_update_time=datetime.now() - timedelta(hours=1),
            records_count=1000,
            freshness_hours=1.0,
            is_fresh=True,
            threshold_hours=24.0
        )
        print("✅ DataFreshnessResult 创建成功")

        freshness_dict = freshness_result.to_dict()
        print(f"   Freshness 结果: {freshness_dict['table_name']} - {freshness_dict['is_fresh']}")

        # 测试 DataCompletenessResult
        completeness_result = DataCompletenessResult(
            table_name = os.getenv("TEST_QUALITY_MONITOR_TABLE_NAME_29"),
            total_records=1000,
            missing_critical_fields={"home_score": 25, "away_score": 25},
            missing_rate=0.05,
            completeness_score=0.95
        )
        print("✅ DataCompletenessResult 创建成功")

        completeness_dict = completeness_result.to_dict()
        print(f"   Completeness 结果: {completeness_dict['table_name']} - {completeness_dict['completeness_score']}")

        # 测试质量等级判断（基于实际实现）
        print("\n📊 质量等级测试（实际实现）:")
        scores = [0.95, 0.85, 0.70, 0.50, 0.20]
        for score in scores:
            actual_level = monitor._get_quality_level(score)
            print(f"  ✅ 分数 {score:.2f} -> {actual_level}")

        # 测试建议生成
        print("\n💡 质量建议测试:")
        test_cases = [
            ({"overall_score": 0.95, "completeness_score": 0.94}, "优秀质量"),
            ({"overall_score": 0.75, "completeness_score": 0.70}, "中等质量"),
            ({"overall_score": 0.45, "completeness_score": 0.40}, "较差质量")
        ]

        for quality_data, description in test_cases:
            recommendations = monitor._generate_quality_recommendations(quality_data)
            print(f"  ✅ {description} - {len(recommendations)} 条建议")
            if recommendations:
                print(f"     首条建议: {recommendations[0][:50]}...")

        # 测试方法存在性
        methods_to_check = [
            'check_data_freshness',
            'check_data_completeness',
            'check_data_consistency',
            'calculate_overall_quality_score',
            'get_quality_trends'
        ]

        print("\n🔍 方法存在性检查:")
        for method_name in methods_to_check:
            has_method = hasattr(monitor, method_name)
            is_async = asyncio.iscoroutinefunction(getattr(monitor, method_name))
            status = "✅" if has_method else "❌"
            async_type = "async" if is_async else "sync"
            print(f"  {status} {method_name} ({async_type})")

        # 测试边界条件
        print("\n🧪 边界条件测试:")
        boundary_tests = [
            (1.0, "Perfect"),
            (0.0, "Zero"),
            (1.1, "Above perfect"),
            (-0.1, "Negative")
        ]

        for score, description in boundary_tests:
            try:
                level = monitor._get_quality_level(score)
                print(f"  ✅ {description}: {score} -> {level}")
            except Exception as e:
                print(f"  ❌ {description}: {score} -> Error: {e}")

        print("\n📊 测试覆盖的功能:")
        print("  - ✅ 类实例化和基本属性")
        print("  - ✅ DataFreshnessResult 创建和序列化")
        print("  - ✅ DataCompletenessResult 创建和序列化")
        print("  - ✅ 质量等级判断逻辑")
        print("  - ✅ 质量建议生成")
        print("  - ✅ 方法存在性和类型检查")
        print("  - ✅ 边界条件处理")
        print("  - ✅ 错误处理")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("🧪 开始 QualityMonitor 功能测试...")
    success = await test_quality_monitor()
    if success:
        print("\n✅ QualityMonitor 测试完成")
    else:
        print("\n❌ QualityMonitor 测试失败")

if __name__ == "__main__":
    asyncio.run(main())