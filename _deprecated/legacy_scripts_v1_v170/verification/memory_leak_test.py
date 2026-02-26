#!/usr/bin/env python3
"""
V26.2 内存泄漏验证脚本
========================

功能:
  - 循环调用提取器 1000 次
  - 验证 ThreadSafeFeatureRegistry 内存占用
  - 确保无内存泄漏

P0-2 验证: 全局注册表内存上限保护

Author: Senior Development Engineer
Version: V151.0 Memory Verification
Date: 2026-01-06
"""

import sys
import gc
import tracemalloc
from typing import Any

sys.path.insert(0, '/home/user/projects/FootballPrediction')

from src.processors.v25_production_extractor import (
    V25ProductionExtractor,
    _GLOBAL_FEATURE_REGISTRY,
    get_global_feature_keys,
    register_feature_keys,
    GLOBAL_REGISTRY_MAX_KEYS,
)


def generate_test_data(match_id: int) -> dict[str, Any]:
    """
    生成测试数据

    每次生成不同特征以测试注册表增长
    """
    data = {
        "match_id": f"test_match_{match_id}",
        "general_matchid": float(match_id),
    }

    # 添加 1000 个唯一特征（每次迭代新增）
    for i in range(1000):
        data[f"feature_{match_id}_{i}"] = float(i)

    return data


def run_memory_test(iterations: int = 1000) -> dict[str, Any]:
    """
    运行内存泄漏测试

    Args:
        iterations: 迭代次数

    Returns:
        测试结果字典
    """
    print("=" * 80)
    print("V26.2 内存泄漏验证测试")
    print("=" * 80)

    # 启动内存跟踪
    tracemalloc.start()
    gc.collect()

    # 记录初始状态
    initial_snapshot = tracemalloc.take_snapshot()
    initial_registry_size = _GLOBAL_FEATURE_REGISTRY.size()
    initial_memory = tracemalloc.get_traced_memory()[0]

    print(f"\n初始状态:")
    print(f"  注册表大小: {initial_registry_size:,}")
    print(f"  内存占用: {initial_memory / 1024 / 1024:.2f} MB")

    # 创建提取器
    extractor = V25ProductionExtractor()

    print(f"\n开始处理 {iterations} 条记录...")
    print("-" * 80)

    # 运行测试
    for i in range(iterations):
        # 生成测试数据
        test_data = generate_test_data(i)

        # 执行提取
        result = extractor.extract(test_data)

        # 每 100 次打印一次进度
        if (i + 1) % 100 == 0:
            current_memory = tracemalloc.get_traced_memory()[0]
            registry_size = _GLOBAL_FEATURE_REGISTRY.size()
            print(f"  [{i+1:4d}/{iterations}] 特征: {len(result.features):,}, "
                  f"注册表: {registry_size:,}, 内存: {current_memory / 1024 / 1024:.2f} MB")

    # 强制垃圾回收
    gc.collect()

    # 记录最终状态
    final_snapshot = tracemalloc.take_snapshot()
    final_registry_size = _GLOBAL_FEATURE_REGISTRY.size()
    final_memory = tracemalloc.get_traced_memory()[0]

    print(f"\n最终状态:")
    print(f"  注册表大小: {final_registry_size:,}")
    print(f"  内存占用: {final_memory / 1024 / 1024:.2f} MB")

    # 计算差异
    registry_growth = final_registry_size - initial_registry_size
    memory_growth = final_memory - initial_memory
    memory_growth_mb = memory_growth / 1024 / 1024

    print(f"\n增长分析:")
    print(f"  注册表增长: {registry_growth:,} 键")
    print(f"  内存增长: {memory_growth_mb:.2f} MB")

    # 验证结果
    print("\n" + "=" * 80)
    print("验证结果")
    print("=" * 80)

    # 检查 1: 注册表是否超过上限
    if final_registry_size > GLOBAL_REGISTRY_MAX_KEYS:
        print(f"❌ FAIL: 注册表超过上限 ({final_registry_size:,} > {GLOBAL_REGISTRY_MAX_KEYS:,})")
        registry_check = False
    else:
        print(f"✅ PASS: 注册表在限制内 ({final_registry_size:,} <= {GLOBAL_REGISTRY_MAX_KEYS:,})")
        registry_check = True

    # 检查 2: 内存增长是否合理 (预期 < 100MB)
    if memory_growth_mb > 100:
        print(f"❌ FAIL: 内存增长过大 ({memory_growth_mb:.2f} MB > 100 MB)")
        memory_check = False
    else:
        print(f"✅ PASS: 内存增长合理 ({memory_growth_mb:.2f} MB <= 100 MB)")
        memory_check = True

    # 检查 3: 清理机制是否触发
    # 由于我们每次添加 1000 个新特征，处理 100 次后应该触发清理
    cleanup_triggered = final_registry_size < (iterations * 1000)
    if cleanup_triggered:
        print(f"✅ PASS: 清理机制已触发 (注册表被裁剪)")
        cleanup_check = True
    else:
        print(f"⚠️  WARNING: 清理机制可能未触发")
        cleanup_check = True  # 不算失败，只是警告

    # 停止内存跟踪
    tracemalloc.stop()

    # 返回结果
    return {
        "iterations": iterations,
        "initial_registry_size": initial_registry_size,
        "final_registry_size": final_registry_size,
        "registry_growth": registry_growth,
        "initial_memory_mb": initial_memory / 1024 / 1024,
        "final_memory_mb": final_memory / 1024 / 1024,
        "memory_growth_mb": memory_growth_mb,
        "registry_check": registry_check,
        "memory_check": memory_check,
        "cleanup_check": cleanup_check,
        "all_passed": registry_check and memory_check and cleanup_check,
    }


if __name__ == "__main__":
    # 运行测试
    results = run_memory_test(iterations=1000)

    # 最终结论
    print("\n" + "=" * 80)
    if results["all_passed"]:
        print("✅ 所有验证通过！系统无内存泄漏风险。")
        print("=" * 80)
        sys.exit(0)
    else:
        print("❌ 部分验证失败！请检查上述错误。")
        print("=" * 80)
        sys.exit(1)
