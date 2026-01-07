#!/usr/bin/env python3
"""
V26.7 全量资产审计脚本 - "全家福"点名册
========================================

核心功能:
    1. 统计所有数据分布 (league_name, season, data_source)
    2. 计算特征覆盖率和版本分布
    3. 找出需要修复的问题记录

Author: Data Architect (Senior DBA)
Version: V26.7
Date: 2026-01-07
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg2
from psycopg2.extras import RealDictCursor
from src.config_unified import get_settings


def get_connection():
    """获取数据库连接"""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )


def audit_full_assets():
    """全量资产审计"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. 按 league_name, season, data_source 分组统计
    query = """
        SELECT
            league_name,
            season,
            data_source,
            COUNT(*) as total_matches,
            COUNT(CASE WHEN l2_raw_json IS NOT NULL THEN 1 END) as has_raw_data,
            COUNT(CASE WHEN l2_extracted_features IS NOT NULL THEN 1 END) as has_features,
            COUNT(CASE WHEN l2_data_version = 'V26.2' THEN 1 END) as v26_2_count,
            COUNT(CASE WHEN l2_data_version IS NULL OR l2_data_version != 'V26.2' THEN 1 END) as legacy_count
        FROM matches
        GROUP BY league_name, season, data_source
        ORDER BY data_source, league_name, season
    """

    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return results


def print_family_portrait(results):
    """打印全家福点名册"""
    print("=" * 100)
    print("📊 V26.7 全量资产审计 - 全家福点名册")
    print("=" * 100)
    print()

    # 按数据源分组
    fotmob_data = [r for r in results if r['data_source'] == 'fotmob']
    oddsportal_data = [r for r in results if r['data_source'] == 'oddsportal']
    other_data = [r for r in results if r['data_source'] not in ['fotmob', 'oddsportal']]

    # 汇总统计
    total_matches = sum(r['total_matches'] for r in results)
    total_with_features = sum(r['has_features'] for r in results)
    total_v26_2 = sum(r['v26_2_count'] for r in results)
    total_legacy = sum(r['legacy_count'] for r in results)

    print(f"📈 总体概览")
    print(f"   总比赛场次:     {total_matches:>15,} 场")
    print(f"   有特征数据:     {total_with_features:>15,} 场 ({total_with_features/total_matches*100:.1f}%)")
    print(f"   V26.2 深度特征: {total_v26_2:>15,} 场 ({total_v26_2/total_matches*100:.1f}%)")
    print(f"   旧版本数据:     {total_legacy:>15,} 场 ({total_legacy/total_matches*100:.1f}%)")
    print()

    # FotMob 数据源
    if fotmob_data:
        print("📋 FotMob 数据源明细")
        print()
        print("┌────────────────────────────┬────────┬──────────┬──────────┬──────────┬──────────┐")
        print("│ 联赛                      │ 赛季   │ 总场次   │ 有特征   │ V26.2    │ 旧版本   │")
        print("├────────────────────────────┼────────┼──────────┼──────────┼──────────┼──────────┤")

        for row in fotmob_data:
            league = row['league_name'][:24] if row['league_name'] else 'Unknown'
            season = row['season']
            total = row['total_matches']
            has_feat = row['has_features']
            v26_2 = row['v26_2_count']
            legacy = row['legacy_count']
            print(f"│ {league:<24} │ {season:>6} │ {total:>8} │ {has_feat:>8} │ {v26_2:>8} │ {legacy:>8} │")

        print("└────────────────────────────┴────────┴──────────┴──────────┴──────────┴──────────┘")
        print()

    # OddsPortal 数据源
    if oddsportal_data:
        print("📋 OddsPortal 数据源明细")
        print()
        print("┌────────────────────────────┬────────┬──────────┬──────────┬──────────┬──────────┐")
        print("│ 联赛                      │ 赛季   │ 总场次   │ 有特征   │ V26.2    │ 旧版本   │")
        print("├────────────────────────────┼────────┼──────────┼──────────┼──────────┼──────────┤")

        for row in oddsportal_data:
            league = row['league_name'][:24] if row['league_name'] else 'Unknown'
            season = row['season']
            total = row['total_matches']
            has_feat = row['has_features']
            v26_2 = row['v26_2_count']
            legacy = row['legacy_count']
            print(f"│ {league:<24} │ {season:>6} │ {total:>8} │ {has_feat:>8} │ {v26_2:>8} │ {legacy:>8} │")

        print("└────────────────────────────┴────────┴──────────┴──────────┴──────────┴──────────┘")
        print()

    # 问题数据
    problem_data = []
    for row in results:
        # Unknown League
        if not row['league_name'] or row['league_name'] == 'Unknown League':
            problem_data.append(('Unknown League', row['season'], row['data_source'], row['total_matches']))

        # 特征缺失
        missing_features = row['total_matches'] - row['has_features']
        if missing_features > 0:
            problem_data.append(('Missing Features', f"{row['league_name']} {row['season']}", row['data_source'], missing_features))

        # 旧版本数据
        if row['legacy_count'] > 0:
            problem_data.append(('Legacy Data', f"{row['league_name']} {row['season']}", row['data_source'], row['legacy_count']))

    if problem_data:
        print("⚠️  需要修复的问题数据")
        print()
        print("┌────────────────────────────┬────────────────────────┬──────────────┬──────────┐")
        print("│ 问题类型                  │ 详情                    │ 数据源       │ 数量     │")
        print("├────────────────────────────┼────────────────────────┼──────────────┼──────────┤")

        for problem in problem_data[:20]:  # 只显示前 20 条
            ptype, pdetail, psource, pcount = problem
            print(f"│ {ptype:<24} │ {pdetail:<22} │ {psource:<12} │ {pcount:>8} │")

        print("└────────────────────────────┴────────────────────────┴──────────────┴──────────┘")
        print()

    print("=" * 100)
    print("✅ 全家福审计完成")
    print("=" * 100)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="V26.7 全量资产审计")
    parser.add_argument("--format", type=str, choices=["table", "json"], default="table", help="输出格式")

    args = parser.parse_args()

    # 执行审计
    results = audit_full_assets()

    # 打印结果
    print_family_portrait(results)


if __name__ == "__main__":
    main()
