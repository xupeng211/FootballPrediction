#!/usr/bin/env python3
"""
V26.7 性能压测脚本 - 模拟100场6000维特征提取

目的：检测内存泄漏和资源回收问题
监控指标：
- 内存占用峰值
- 内存增长趋势
- 资源释放效率
"""

import gc
import os
import sys
import time
import tracemalloc
from datetime import datetime
from typing import Dict, List
import psutil
import numpy as np


# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


class MemoryProfiler:
    """内存性能分析器"""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.snapshots: List[Dict] = []
        self.start_time = None

    def start(self):
        """开始监控"""
        tracemalloc.start()
        self.start_time = time.time()
        self.take_snapshot("初始状态")

    def take_snapshot(self, label: str) -> Dict:
        """捕获内存快照"""
        memory_info = self.process.memory_info()
        current_time = time.time() - self.start_time if self.start_time else 0

        snapshot = {
            "label": label,
            "timestamp": current_time,
            "rss_mb": memory_info.rss / 1024 / 1024,  # 常驻集大小
            "vms_mb": memory_info.vms / 1024 / 1024,  # 虚拟内存大小
            "heap_mb": tracemalloc.get_traced_memory()[0] / 1024 / 1024,
        }

        self.snapshots.append(snapshot)
        return snapshot

    def get_current_memory_mb(self) -> float:
        """获取当前内存占用（MB）"""
        return self.process.memory_info().rss / 1024 / 1024

    def analyze_trend(self) -> Dict:
        """分析内存趋势"""
        if len(self.snapshots) < 2:
            return {"trend": "unknown", "growth_rate": 0}

        # 计算内存增长率
        start_mem = self.snapshots[0]["rss_mb"]
        end_mem = self.snapshots[-1]["rss_mb"]
        total_growth = end_mem - start_mem
        growth_rate = total_growth / start_mem if start_mem > 0 else 0

        # 判断趋势
        if growth_rate > 0.5:  # 增长超过50%
            trend = "⚠️ 持续上升（可能泄漏）"
        elif growth_rate > 0.2:  # 增长20%-50%
            trend = "⚡ 缓慢增长（需关注）"
        elif growth_rate < -0.1:  # 下降超过10%
            trend = "✅ 持续下降（正常回收）"
        else:  # 波动在 ±20%
            trend = "✅ 稳定（健康）"

        return {
            "trend": trend,
            "growth_rate": growth_rate,
            "total_growth_mb": total_growth,
            "start_memory_mb": start_mem,
            "end_memory_mb": end_mem,
        }


def generate_mock_l2_data(match_id: int) -> dict:
    """
    生成模拟的 L2 数据（6000 维特征）

    结构：模拟 FotMob L2 详情页数据
    """
    # 基础比赛信息
    base_data = {
        "match_id": match_id,
        "status": "finished",
        "home_team": f"Home Team {match_id % 20}",
        "away_team": f"Away Team {match_id % 20}",
        "home_score": match_id % 5,
        "away_score": match_id % 4,
        "league": "Premier League",
        "season": "23/24",
    }

    # 模拟 6000 维特征数据
    # 1. xG 数据（~500 维）
    xg_data = {
        f"xg_type_{i}": np.random.random() for i in range(500)
    }

    # 2. 射门数据（~800 维）
    shots_data = {
        f"shots_{i}": np.random.randint(0, 30) for i in range(800)
    }

    # 3. 传球数据（~1000 维）
    passing_data = {
        f"passing_{i}": np.random.randint(50, 800) for i in range(1000)
    }

    # 4. 防守数据（~700 维）
    defense_data = {
        f"defense_{i}": np.random.randint(0, 50) for i in range(700)
    }

    # 5. 球员数据（~1500 维，假设每队11人 x 约70维）
    player_data = {
        f"player_{i}_{j}": np.random.random()
        for i in range(22)
        for j in range(70)
    }

    # 6. 时间序列数据（~1500 维，假设每分钟25维）
    timeseries_data = {
        f"minute_{i}_{metric}": np.random.random()
        for i in range(90)
        for metric in ["xg", "shots", "passing", "defense", "position"]
    }

    # 合并所有特征
    all_features = {
        **base_data,
        **xg_data,
        **shots_data,
        **passing_data,
        **defense_data,
        **player_data,
        **timeseries_data,
    }

    return {"general": {"matchId": str(match_id)}, "stats": all_features}


def stress_test_feature_extraction(num_matches: int = 100):
    """
    性能压测主函数

    模拟连续提取 N 场比赛的 6000 维特征
    """
    print("=" * 80)
    print(f"🔥 V26.7 性能压测 - {num_matches} 场比赛 6000 维特征提取")
    print("=" * 80)

    # 初始化内存分析器
    profiler = MemoryProfiler()
    profiler.start()

    # 测试结果记录
    results = []

    print(f"\n📊 开始压测...\n")

    try:
        for i in range(num_matches):
            match_id = 4800000 + i  # 模拟比赛 ID

            # 模拟加载数据
            l2_data = generate_mock_l2_data(match_id)

            # 导入特征提取器（每次循环都重新导入，模拟真实场景）
            try:
                from src.processors.v25_production_extractor import V25ProductionExtractor

                extractor = V25ProductionExtractor()
                extraction_result = extractor.extract(l2_data)

                if extraction_result and extraction_result.features:
                    features = extraction_result.features
                    feature_count = len([k for k in features.keys() if not k.startswith("_")])

                    current_memory = profiler.get_current_memory_mb()
                    result = {
                        "match_id": match_id,
                        "feature_count": feature_count,
                        "memory_mb": current_memory,
                        "success": feature_count >= 6000,
                    }
                    results.append(result)

                    # 每 10 场输出一次进度
                    if (i + 1) % 10 == 0:
                        avg_mem = np.mean([r["memory_mb"] for r in results[-10:]])
                        print(
                            f"  进度: {i+1:3d}/{num_matches} | "
                            f"特征: {feature_count}维 | "
                            f"内存: {current_memory:.1f}MB | "
                            f"10场平均: {avg_mem:.1f}MB"
                        )
                        profiler.take_snapshot(f"第{i+1}场完成")

            except ImportError as e:
                print(f"❌ 无法导入特征提取器: {e}")
                return None
            except Exception as e:
                print(f"❌ 特征提取失败（比赛 {match_id}）: {e}")
                continue

            # 显式触发垃圾回收（模拟 Python 自动 GC）
            if i % 20 == 0:
                gc.collect()

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
    finally:
        # 最终快照
        profiler.take_snapshot("压测结束")

    # 分析结果
    print("\n" + "=" * 80)
    print("📊 压测结果分析")
    print("=" * 80)

    # 1. 内存趋势分析
    trend_analysis = profiler.analyze_trend()
    print(f"\n🔍 内存趋势:")
    print(f"  趋势: {trend_analysis['trend']}")
    print(f"  增长率: {trend_analysis['growth_rate']*100:.2f}%")
    print(f"  起始内存: {trend_analysis['start_memory_mb']:.1f}MB")
    print(f"  结束内存: {trend_analysis['end_memory_mb']:.1f}MB")
    print(f"  总增长: {trend_analysis['total_growth_mb']:.1f}MB")

    # 2. 特征提取统计
    feature_counts = [r["feature_count"] for r in results]
    print(f"\n📈 特征提取统计:")
    print(f"  成功场次: {len(results)}/{num_matches}")
    print(f"  平均维度: {np.mean(feature_counts):.0f}维")
    print(f"  最小维度: {np.min(feature_counts)}维")
    print(f"  最大维度: {np.max(feature_counts)}维")

    # 3. 内存峰值
    memory_values = [r["memory_mb"] for r in results]
    print(f"\n💾 内存峰值:")
    print(f"  峰值: {np.max(memory_values):.1f}MB")
    print(f"  谷值: {np.min(memory_values):.1f}MB")
    print(f"  平均: {np.mean(memory_values):.1f}MB")

    # 4. 内存泄漏检测
    print(f"\n🔬 内存泄漏检测:")
    if trend_analysis["growth_rate"] > 0.5:
        print("  ❌ 检测到可能的内存泄漏！")
        print("  建议: 检查 V25ProductionExtractor 的资源回收逻辑")
        leak_detection = "LEAK_DETECTED"
    elif trend_analysis["growth_rate"] > 0.2:
        print("  ⚠️  内存缓慢增长，需要关注")
        print("  建议: 考虑增加垃圾回收频率或优化数据结构")
        leak_detection = "NEEDS_ATTENTION"
    else:
        print("  ✅ 内存健康，无明显泄漏")
        leak_detection = "HEALTHY"

    # 5. 生成详细报告
    generate_detailed_report(profiler.snapshots, results, trend_analysis, leak_detection)

    return {
        "trend_analysis": trend_analysis,
        "leak_detection": leak_detection,
        "success_rate": len(results) / num_matches,
    }


def generate_detailed_report(
    snapshots: List[Dict],
    results: List[Dict],
    trend_analysis: Dict,
    leak_detection: str
):
    """生成详细报告文件"""

    report_dir = "docs"
    os.makedirs(report_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"{report_dir}/V26_7_STRESS_TEST_{timestamp}.txt"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("V26.7 性能压测详细报告\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"测试场次: {len(results)}\n")
        f.write(f"泄漏检测: {leak_detection}\n\n")

        f.write("-" * 80 + "\n")
        f.write("内存快照记录\n")
        f.write("-" * 80 + "\n\n")

        for snapshot in snapshots:
            f.write(
                f"{snapshot['label']:20s} | "
                f"时间: {snapshot['timestamp']:6.1f}s | "
                f"RSS: {snapshot['rss_mb']:7.1f}MB | "
                f"VMS: {snapshot['vms_mb']:7.1f}MB | "
                f"Heap: {snapshot['heap_mb']:7.1f}MB\n"
            )

        f.write("\n" + "-" * 80 + "\n")
        f.write("内存趋势分析\n")
        f.write("-" * 80 + "\n\n")

        f.write(f"趋势: {trend_analysis['trend']}\n")
        f.write(f"增长率: {trend_analysis['growth_rate']*100:.2f}%\n")
        f.write(f"起始内存: {trend_analysis['start_memory_mb']:.1f}MB\n")
        f.write(f"结束内存: {trend_analysis['end_memory_mb']:.1f}MB\n")
        f.write(f"总增长: {trend_analysis['total_growth_mb']:.1f}MB\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("报告结束\n")
        f.write("=" * 80 + "\n")

    print(f"\n📄 详细报告已保存至: {report_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="V26.7 性能压测脚本")
    parser.add_argument(
        "--matches",
        type=int,
        default=100,
        help="压测场次数（默认: 100）"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="快速模式（仅测试 10 场）"
    )

    args = parser.parse_args()

    num_matches = 10 if args.quick else args.matches

    result = stress_test_feature_extraction(num_matches)

    # 根据结果返回退出码
    if result and result["leak_detection"] == "LEAK_DETECTED":
        sys.exit(1)  # 检测到泄漏，返回错误码
    elif result and result["leak_detection"] == "NEEDS_ATTENTION":
        sys.exit(2)  # 需要关注，返回警告码
    else:
        sys.exit(0)  # 健康，返回成功码
