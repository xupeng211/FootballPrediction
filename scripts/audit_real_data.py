#!/usr/bin/env python3
"""
数据洁癖审计师 - 严格的真实数据审计
找出数据库中真正的xG数据
"""

import asyncio
import asyncpg
import json
from datetime import datetime


async def audit_real_xg_data():
    conn = await asyncpg.connect("postgresql://postgres:postgres-dev-password@db:5432/football_prediction")

    print("🔍 数据洁癖审计师 - 真实xG数据审计")
    print("="*60)

    # 1. 检查数据库中到底有什么xG相关的数据
    print("\n📊 步骤1: 全面扫描xG相关字段...")

    # 查看stats字段中是否有xG数据
    sample_result = await conn.fetch("""
        SELECT id, home_score, away_score, stats, odds, match_date
        FROM matches
        WHERE status IN ('completed', 'finished')
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
          AND stats IS NOT NULL
          AND stats != 'null'
        LIMIT 10
    """)

    print(f"   找到 {len(sample_result)} 个有stats的样本")

    # 深度分析stats字段结构
    real_xg_count = 0
    for i, row in enumerate(sample_result):
        if row['stats']:
            try:
                stats_data = json.loads(row['stats'])
                print(f"\n   样本 {i+1} (ID: {row['id']}):")
                print(f"   比分: {row['home_score']}-{row['away_score']}")

                # 递归搜索所有包含xg的键
                def find_xg_keys(obj, path=""):
                    xg_keys = []
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            current_path = f"{path}.{key}" if path else key
                            if 'xg' in key.lower() or 'expected_goal' in key.lower():
                                xg_keys.append((current_path, value))
                            elif isinstance(value, (dict, list)):
                                xg_keys.extend(find_xg_keys(value, current_path))
                    elif isinstance(obj, list):
                        for idx, item in enumerate(obj):
                            if isinstance(item, (dict, list)):
                                xg_keys.extend(find_xg_keys(item, f"{path}[{idx}]"))
                    return xg_keys

                xg_keys = find_xg_keys(stats_data)
                if xg_keys:
                    real_xg_count += 1
                    print(f"   ✅ 找到xG数据:")
                    for path, value in xg_keys[:5]:  # 只显示前5个
                        print(f"      {path}: {value}")
                else:
                    print(f"   ❌ 未找到xG数据")
                    # 显示stats的前几个键来了解结构
                    if isinstance(stats_data, dict):
                        print(f"   📋 可用键: {list(stats_data.keys())[:10]}")

            except json.JSONDecodeError:
                print(f"   ❌ JSON解析失败")

        if i >= 2:  # 只详细显示前3个样本
            break

    print(f"\n📊 xG数据统计:")
    print(f"   真实xG数据样本: {real_xg_count}/10")

    # 2. 更大范围的xG搜索
    print(f"\n🔍 步骤2: 大范围搜索真实xG数据...")

    # 搜索stats字段中包含xg关键词的记录
    xg_matches = await conn.fetch("""
        SELECT COUNT(*) as count
        FROM matches
        WHERE status IN ('completed', 'finished')
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
          AND stats IS NOT NULL
          AND stats != 'null'
          AND (stats::text ILIKE '%xg%'
               OR stats::text ILIKE '%expected_goal%'
               OR stats::text ILIKE '%xg_%'
               OR stats::text ILIKE '%xg-%')
    """)

    print(f"   包含xG关键词的记录: {xg_matches[0]['count']:,}")

    # 3. 检查odds数据
    print(f"\n💰 步骤3: 检查真实的赔率数据...")

    odds_samples = await conn.fetch("""
        SELECT id, odds, match_metadata
        FROM matches
        WHERE odds IS NOT NULL
          AND odds != 'null'
        LIMIT 5
    """)

    print(f"   找到 {len(odds_samples)} 个有odds的样本")

    for i, row in enumerate(odds_samples):
        try:
            if row['odds']:
                odds_data = json.loads(row['odds'])
                print(f"   样本 {i+1} odds结构:")
                if isinstance(odds_data, dict):
                    print(f"      键: {list(odds_data.keys())[:10]}")
                else:
                    print(f"      类型: {type(odds_data)}, 值: {str(odds_data)[:100]}")
        except:
            print(f"   样本 {i+1}: odds解析失败")

    # 4. 尝试找到一些FBref格式的xG数据
    print(f"\n⚽ 步骤4: 搜索FBref格式的xG数据...")

    # 假设FBref可能有特定格式的数据
    fbref_xg_samples = await conn.fetch("""
        SELECT id, home_score, away_score, stats
        FROM matches
        WHERE status IN ('completed', 'finished')
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
          AND stats IS NOT NULL
          AND stats != 'null'
          AND (
              stats::text ~ '[0-9]+\.[0-9]+.*xg' OR
              stats::text ~ 'xg.*[0-9]+\.[0-9]+' OR
              stats::text ~ 'Expected.*[0-9]+\.[0-9]+'
          )
        LIMIT 10
    """)

    print(f"   可能包含xG数值的记录: {len(fbref_xg_samples)}")

    # 5. 检查数据总量
    print(f"\n📈 步骤5: 数据总量统计...")

    total_stats = await conn.fetchval("""
        SELECT COUNT(*) FROM matches
        WHERE status IN ('completed', 'finished')
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
    """)

    print(f"   总完成比赛: {total_stats:,}")

    await conn.close()

    # 最终结论
    print(f"\n" + "="*60)
    print(f"🎯 数据洁癖审计师 - 初步结论:")

    if real_xg_count == 0:
        print(f"   ❌ 严重问题: 数据库中没有找到真实的xG数据!")
        print(f"   🔍 建议深入检查stats字段的具体结构")
        print(f"   📊 可能需要重新解析或获取xG数据")
    elif real_xg_count < 5:
        print(f"   ⚠️  xG数据极其稀少: {real_xg_count}/10 样本")
        print(f"   📉 数据质量不足以训练可靠模型")
    else:
        print(f"   ✅ 找到部分xG数据: {real_xg_count}/10 样本")
        print(f"   📊 可以尝试严格过滤后训练")


if __name__ == "__main__":
    asyncio.run(audit_real_xg_data())