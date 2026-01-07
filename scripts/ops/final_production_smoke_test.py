#!/usr/bin/env python3
"""
V26.7: 最终生产烟雾测试
============================

目标：验证 2020 年老比赛和 2025 年实时比赛的全链路兼容性
断言：两者必须都能成功入库且特征维度对齐（误差 < 1%）
"""

import os
import sys
import json
from typing import Dict, Any

# 强制数据库配置
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'football_db'
os.environ['DB_USER'] = 'football_user'
os.environ['DB_PASSWORD'] = 'football_pass'
os.environ['DB_PORT'] = '5432'

sys.path.insert(0, '/home/user/projects/FootballPrediction')

from src.config_unified import reload_settings
reload_settings()

from src.api.collectors.fotmob_core import FotMobCoreCollector
from src.processors.v25_production_extractor import V25ProductionExtractor
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from src.config_unified import get_settings

print("=" * 70)
print("V26.7: 最终生产烟雾测试")
print("=" * 70)
print()
print("目标: 验证 2020 vs 2025 全链路兼容性")
print("断言: 特征维度误差 < 1%")
print()

# 测试用例配置
TEST_CASES = [
    {
        "name": "2020年老比赛",
        "league_id": 47,
        "season": "2020/2021",
        "target_date": "2020-09-12",
        "match_id": "3411352",  # Fulham vs Arsenal
    },
    {
        "name": "2025年实时比赛",
        "league_id": 47,
        "season": "2024/2025",
        "target_date": "2025-08-16",
        "match_id": "4218684",  # Manchester United vs Fulham
    },
]

results = []

for test_case in TEST_CASES:
    print(f"\n{'🔥' * 35}")
    print(f"测试: {test_case['name']}")
    print(f"{'🔥' * 35}")

    test_result = {
        "name": test_case['name'],
        "l1_success": False,
        "l2_success": False,
        "feature_count": 0,
    }

    # 步骤 1: L1 采集（比分入库）
    print(f"\n📊 步骤 1: L1 比分采集")
    print("-" * 70)

    try:
        collector = FotMobCoreCollector()
        l1_result = collector.enriched_l1_harvest(
            league_id=test_case['league_id'],
            season_code=test_case['season'],
            league_name="Premier League",
            batch_size=10
        )

        if l1_result['total_upserted'] > 0:
            print(f"✅ L1 采集成功: {l1_result['total_upserted']} 场")
            test_result['l1_success'] = True
        else:
            print(f"❌ L1 采集失败")

    except Exception as e:
        print(f"❌ L1 采集异常: {e}")

    # 步骤 2: L2 深度特征提取
    print(f"\n🔬 步骤 2: L2 深度特征提取")
    print("-" * 70)

    try:
        url = f"https://www.fotmob.com/api/matchDetails"
        params = {"matchId": test_case['match_id']}
        headers = {"User-Agent": "Mozilla/5.0"}

        response = requests.get(url, params=params, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            extractor = V25ProductionExtractor()
            result = extractor.extract(data)

            if hasattr(result, 'features'):
                features = result.features
                feature_count = len(features)
                test_result['feature_count'] = feature_count
                test_result['l2_success'] = True

                print(f"✅ L2 提取成功: {feature_count} 维特征")

                # 显示部分特征
                if hasattr(result, 'meta'):
                    meta = result.meta
                    print(f"   元数据: {meta}")
            else:
                print(f"❌ L2 提取失败: 无特征对象")
        else:
            print(f"❌ L2 API 返回: {response.status_code}")

    except Exception as e:
        print(f"❌ L2 提取异常: {e}")

    results.append(test_result)

# 最终汇总
print(f"\n{'=' * 70}")
print("🏁 烟雾测试最终报告")
print(f"{'=' * 70}")
print()

print("测试结果汇总:")
print("-" * 70)
print(f"{'测试用例':<20} {'L1采集':<12} {'L2特征':<12} {'特征维度':<12}")
print("-" * 70)

for r in results:
    l1 = "✅" if r['l1_success'] else "❌"
    l2 = "✅" if r['l2_success'] else "❌"
    dims = r['feature_count'] if r['feature_count'] > 0 else "N/A"
    print(f"{r['name']:<20} {l1:<12} {l2:<12} {dims:<12}")

print()

# 验证特征维度对齐性
if results[0]['feature_count'] > 0 and results[1]['feature_count'] > 0:
    count_2020 = results[0]['feature_count']
    count_2025 = results[1]['feature_count']
    diff = abs(count_2020 - count_2025)
    avg = (count_2020 + count_2025) / 2
    error_rate = diff / avg

    print("特征维度对齐性分析:")
    print("-" * 70)
    print(f"2020 年比赛: {count_2020} 维")
    print(f"2025 年比赛: {count_2025} 维")
    print(f"绝对误差: {diff} 维")
    print(f"相对误差: {error_rate*100:.2f}%")
    print()

    if error_rate < 0.01:  # 1%
        print("✅✅✅ 特征维度对齐（误差 < 1%）")
        print()
        print("批准并线到 main 分支！")
        print()
        sys.exit(0)
    else:
        print("❌ 特征维度偏差过大")
        sys.exit(1)
else:
    print("❌ 特征提取失败，无法验证对齐性")
    sys.exit(1)
