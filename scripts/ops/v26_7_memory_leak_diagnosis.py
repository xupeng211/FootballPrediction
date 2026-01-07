#!/usr/bin/env python3
"""
V26.7 内存泄漏诊断脚本

精确定位内存泄漏的根源
"""

import gc
import sys
import tracemalloc
from typing import Any

# 添加项目根目录到路径
sys.path.insert(0, ".")


def get_object_counts():
    """统计当前内存中的对象数量"""
    counts = {}
    for obj in gc.get_objects():
        obj_type = type(obj).__name__
        counts[obj_type] = counts.get(obj_type, 0) + 1
    return counts


def diagnose_memory_leak():
    """诊断内存泄漏"""
    print("=" * 80)
    print("🔬 V26.7 内存泄漏诊断")
    print("=" * 80)

    # 开始内存跟踪
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # 获取初始对象计数
    gc.collect()
    initial_counts = get_object_counts()
    print(f"\n初始对象数: {sum(initial_counts.values()):,}")

    # 模拟 10 场比赛的特征提取
    print("\n开始模拟提取...")

    for i in range(10):
        # 导入并创建提取器
        from src.processors.v25_production_extractor import V25ProductionExtractor

        # 模拟数据
        mock_data = {
            "general": {"matchId": f"match_{i}"},
            "stats": {f"feature_{j}": j for j in range(5000)}
        }

        # 提取特征
        extractor = V25ProductionExtractor()
        result = extractor.extract(mock_data)

        # 获取当前对象计数
        gc.collect()
        current_counts = get_object_counts()
        print(f"  场次 {i+1}: 总对象数 {sum(current_counts.values()):,} | "
              f"dict: {current_counts.get('dict', 0):,} | "
              f"ExtractionResult: {current_counts.get('ExtractionResult', 0):,}")

        # 删除引用
        del extractor, result, mock_data

    # 最终快照
    gc.collect()
    snapshot2 = tracemalloc.take_snapshot()
    final_counts = get_object_counts()

    print(f"\n最终对象数: {sum(final_counts.values()):,}")

    # 计算对象增长
    print("\n📊 对象增长分析:")
    print(f"  总增长: {sum(final_counts.values()) - sum(initial_counts.values()):+,}")

    # 找出增长最多的类型
    print("\n🔍 增长最多的对象类型:")
    growth = {}
    for obj_type, count in final_counts.items():
        initial = initial_counts.get(obj_type, 0)
        if count - initial > 0:
            growth[obj_type] = count - initial

    # 按增长排序
    sorted_growth = sorted(growth.items(), key=lambda x: x[1], reverse=True)[:10]
    for obj_type, count in sorted_growth:
        print(f"  {obj_type}: +{count:,}")

    # 内存快照对比
    print("\n💾 内存快照对比:")
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    for stat in top_stats[:10]:
        print(stat)


if __name__ == "__main__":
    diagnose_memory_leak()
