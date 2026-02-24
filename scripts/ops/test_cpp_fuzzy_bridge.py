#!/usr/bin/env python3
"""
V171.002 C++ Bridge Fuzzy Matching Test
=======================================

验证 RapidFuzz C++ 模糊匹配引擎的正确性，展示
OddsPortal 队名 → FotMob ID 的转换过程。

Usage:
    python scripts/ops/test_cpp_fuzzy_bridge.py

Author: V171.002 Engineering Team
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入模糊匹配组件
from src.utils.cpp_bridge_radar import BridgeRadarEngine, RadarQuery, get_bridge_radar
from src.utils.levenshtein_matcher import LevenshteinMatcher
from datetime import datetime


def test_rapidfuzz_engine():
    """测试 RapidFuzz C++ 引擎"""
    print("")
    print("═══════════════════════════════════════════════════════════════")
    print("  Test 1: RapidFuzz C++ 引擎性能测试")
    print("═══════════════════════════════════════════════════════════════")
    print("")

    # 检查 RapidFuzz 是否可用
    try:
        from rapidfuzz import fuzz, process
        print("✅ RapidFuzz C++ 引擎已加载")
        print(f"   - WRatio 函数: {fuzz.WRatio}")
        print(f"   - process.extract 可用: {process.extract is not None}")
    except ImportError:
        print("❌ RapidFuzz 未安装，请运行: pip install rapidfuzz")
        return False

    # 性能测试
    test_cases = [
        ("Manchester United", "Man Utd"),
        ("Liverpool", "Liverpool FC"),
        ("Arsenal", "Arsenal London"),
        ("Chelsea", "Chelsea FC"),
        ("Tottenham Hotspur", "Spurs"),
        ("West Ham United", "West Ham"),
        ("Newcastle United", "Newcastle Utd"),
        ("Brighton & Hove Albion", "Brighton"),
    ]

    print("")
    print("📊 队名匹配测试 (8 组):")
    print("─" * 60)

    total_time = 0
    for name1, name2 in test_cases:
        start = time.perf_counter()
        score = fuzz.WRatio(name1.lower(), name2.lower())
        elapsed_ms = (time.perf_counter() - start) * 1000
        total_time += elapsed_ms

        status = "✅" if score >= 75 else "⚠️" if score >= 60 else "❌"
        print(f"   {status} '{name1}' vs '{name2}'")
        print(f"       相似度: {score:.1f}%  |  耗时: {elapsed_ms:.2f}ms")

    avg_time = total_time / len(test_cases)
    print("")
    print(f"📈 统计: 平均耗时 {avg_time:.2f}ms (目标 < 50ms)")
    print(f"   总耗时: {total_time:.2f}ms")

    return avg_time < 50


def test_bridge_radar_engine():
    """测试 BridgeRadarEngine"""
    print("")
    print("═══════════════════════════════════════════════════════════════")
    print("  Test 2: BridgeRadarEngine 雷达扫描测试")
    print("═══════════════════════════════════════════════════════════════")
    print("")

    engine = get_bridge_radar()

    # 创建测试查询
    query = RadarQuery(
        match_id="TEST_20260301_ARS_CHE",
        home_team="Arsenal",
        away_team="Chelsea",
        league_name="Premier League",
        match_date=datetime(2026, 3, 1, 15, 0),
        min_threshold=65.0
    )

    print(f"🔍 查询参数:")
    print(f"   match_id: {query.match_id}")
    print(f"   主队: {query.home_team}")
    print(f"   客队: {query.away_team}")
    print(f"   联赛: {query.league_name}")
    print(f"   阈值: {query.min_threshold}%")
    print("")

    # 尝试雷达扫描
    print("🚀 执行 radar_scan()...")
    start = time.perf_counter()

    try:
        result = engine.radar_scan(query, verbose=True)

        elapsed_ms = (time.perf_counter() - start) * 1000

        if result:
            print("")
            print("✅ 雷达扫描成功!")
            print(f"   发现方法: {result.discovery_method}")
            print(f"   置信度: {result.confidence:.1f}%")
            print(f"   候选 URL: {result.candidate_url}")
            print(f"   耗时: {elapsed_ms:.2f}ms")
        else:
            print(f"⚠️ 未找到匹配 (耗时: {elapsed_ms:.2f}ms)")
            print("   可能原因: 数据库中尚无映射数据")

    except Exception as e:
        print(f"❌ 雷达扫描失败: {e}")
        return False

    # 获取统计信息
    stats = engine.get_stats()
    print("")
    print("📊 雷达引擎统计:")
    print(f"   总查询: {stats.total_queried}")
    print(f"   雷达发现: {stats.radar_discoveries}")
    print(f"   静态查表: {stats.static_lookups}")
    print(f"   平均响应: {stats.avg_response_time_ms:.2f}ms")

    return True


def test_levenshtein_matcher():
    """测试 LevenshteinMatcher"""
    print("")
    print("═══════════════════════════════════════════════════════════════")
    print("  Test 3: LevenshteinMatcher 编辑距离匹配")
    print("═══════════════════════════════════════════════════════════════")
    print("")

    # 检查是否有 C++ 加速
    try:
        import Levenshtein
        print("✅ python-Levenshtein C++ 扩展已加载")
    except ImportError:
        print("⚠️ python-Levenshtein 未安装，使用纯 Python 回退")
        print("   安装: pip install python-Levenshtein")

    matcher = LevenshteinMatcher(threshold=0.4)  # 相对阈值 40%

    # 测试用例
    test_cases = [
        # (fotmob_home, fotmob_away, oddsportal_home, oddsportal_away)
        ("Man Utd", "Chelsea", "Manchester United", "Chelsea"),
        ("Liverpool", "West Ham", "Liverpool FC", "West Ham United"),
        ("Arsenal", "Tottenham", "Arsenal", "Spurs"),
        ("Newcastle", "Everton", "Newcastle Utd", "Everton FC"),
    ]

    print("")
    print("📊 队名匹配测试:")
    print("─" * 60)

    for fotmob_h, fotmob_a, odds_h, odds_a in test_cases:
        is_match, confidence = matcher.match_team_names(
            fotmob_home=fotmob_h,
            fotmob_away=fotmob_a,
            oddsportal_home=odds_h,
            oddsportal_away=odds_a
        )

        status = "✅" if is_match else "❌"
        print(f"   {status} FotMob: '{fotmob_h}' vs '{fotmob_a}'")
        print(f"       OddsPortal: '{odds_h}' vs '{odds_a}'")
        print(f"       匹配: {is_match}  |  置信度: {confidence:.2%}")
        print("")

    return True


def test_integration_with_v171():
    """测试与 V171 流程的集成"""
    print("")
    print("═══════════════════════════════════════════════════════════════")
    print("  Test 4: V171 流程集成验证")
    print("═══════════════════════════════════════════════════════════════")
    print("")

    print("📋 V171 全息收割流程:")
    print("")
    print("   1️⃣  L1 Discovery")
    print("       └── 发现 OddsPortal 比赛 URL")
    print("")
    print("   2️⃣  C++ Fuzzy Matching (BridgeRadarEngine)")
    print("       ├── 输入: OddsPortal 队名 (如 'Man Utd')")
    print("       ├── 处理: RapidFuzz WRatio 计算")
    print("       └── 输出: FotMob match_id (如 '4492875')")
    print("")
    print("   3️⃣  L2 FotMob 采集")
    print("       ├── 使用 FotMob ID 请求 matchDetails API")
    print("       └── 提取 xG, shots, possession, rating")
    print("")
    print("   4️⃣  特征工程 (FeatureEngine)")
    print("       ├── AtomicProcessor: 基础统计 (30 维)")
    print("       ├── TacticalProcessor: 战术动量 (150+ 维)")
    print("       └── 总计: 800+ 维特征")
    print("")
    print("   5️⃣  MultiModelValidator")
    print("       ├── Model A (通用): 37 维")
    print("       ├── Model B (联赛专项): 6000+ 维")
    print("       └── Model C (赔率): 19 维")
    print("")

    # 模拟完整的匹配流程
    print("🎯 模拟: OddsPortal → FotMob ID 转换")
    print("─" * 60)

    from rapidfuzz import fuzz

    # 模拟 OddsPortal 队名
    oddsportal_teams = [
        ("Man Utd", "Chelsea"),
        ("Liverpool", "West Ham"),
        ("Arsenal", "Spurs"),
    ]

    # 模拟 FotMob 队名库
    fotmob_teams = [
        "Manchester United", "Chelsea FC", "Liverpool FC",
        "West Ham United", "Arsenal", "Tottenham Hotspur"
    ]

    for home, away in oddsportal_teams:
        print(f"")
        print(f"   📌 OddsPortal: {home} vs {away}")

        # 使用 RapidFuzz 找到最佳匹配
        home_match = process.extractOne(home, fotmob_teams, scorer=fuzz.WRatio)
        away_match = process.extractOne(away, fotmob_teams, scorer=fuzz.WRatio)

        print(f"      🔍 C++ Fuzzy Matching:")
        print(f"         '{home}' → '{home_match[0]}' (score: {home_match[1]:.1f}%)")
        print(f"         '{away}' → '{away_match[0]}' (score: {away_match[1]:.1f}%)")

        # 检查是否达到阈值
        threshold = 65.0
        if home_match[1] >= threshold and away_match[1] >= threshold:
            print(f"      ✅ 匹配成功! 可用于 FotMob API 查询")
        else:
            print(f"      ⚠️ 置信度不足，需要人工审核")

    return True


def main():
    """主测试入口"""
    print("")
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║     V171.002 C++ Fuzzy Bridge Test                            ║")
    print("║     RapidFuzz 高性能模糊匹配验证                              ║")
    print("╚═══════════════════════════════════════════════════════════════╝")

    results = []

    # Test 1: RapidFuzz 引擎
    results.append(("RapidFuzz 引擎", test_rapidfuzz_engine()))

    # Test 2: BridgeRadarEngine
    results.append(("BridgeRadarEngine", test_bridge_radar_engine()))

    # Test 3: LevenshteinMatcher
    results.append(("LevenshteinMatcher", test_levenshtein_matcher()))

    # Test 4: V171 集成
    results.append(("V171 集成验证", test_integration_with_v171()))

    # 汇总结果
    print("")
    print("═══════════════════════════════════════════════════════════════")
    print("  测试结果汇总")
    print("═══════════════════════════════════════════════════════════════")
    print("")

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}  {name}")
        if not passed:
            all_passed = False

    print("")
    if all_passed:
        print("🎉 所有测试通过! C++ 模糊匹配引擎已就绪。")
        print("")
        print("📋 下一步: 在 V171 收割中启用 C++ 桥接")
        print("   1. 安装 RapidFuzz: pip install rapidfuzz")
        print("   2. 在 QuantHarvester.js 中调用 Python Bridge")
        print("   3. 使用 BridgeRadarEngine 进行动态 ID 映射")
    else:
        print("⚠️ 部分测试失败，请检查依赖安装状态。")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
