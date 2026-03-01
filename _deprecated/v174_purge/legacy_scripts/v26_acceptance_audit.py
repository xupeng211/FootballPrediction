#!/usr/bin/env python3
"""
V26.1 Gold-Finger 验收审计脚本
==============================

功能:
  1. 从数据库随机抽取 V26.0 记录
  2. 模拟"重解析"过程
  3. 生成验收审计表

Author: Senior Data Architect
Version: V150.5 Acceptance Audit
Date: 2026-01-06
"""

import sys
sys.path.insert(0, '/home/user/projects/FootballPrediction')

from src.config_unified import get_settings
from src.processors.v25_production_extractor import V25ProductionExtractor
import psycopg2
from psycopg2.extras import RealDictCursor

def run_acceptance_audit():
    """执行验收审计"""

    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )

    print("=" * 100)
    print("V26.1 Gold-Finger 验收审计")
    print("=" * 100)

    # 随机抽取 10 条 V26.0 记录
    with conn.cursor() as cur:
        cur.execute("""
            SELECT match_id, home_team, away_team, l2_raw_json
            FROM matches
            WHERE l2_raw_json->'adaptive_features'->'_meta'->>'extraction_version' = 'V26.0'
            ORDER BY RANDOM()
            LIMIT 10
        """)

        rows = cur.fetchall()

    if not rows:
        print("⚠️  未找到 V26.0 记录")
        return

    # 创建提取器实例
    extractor = V25ProductionExtractor()

    # 审计结果
    audit_results = []

    print(f"\n处理 {len(rows)} 条记录...\n")

    for i, row in enumerate(rows, 1):
        match_id = row['match_id']
        home_team = row['home_team']
        away_team = row['away_team']
        l2_data = row['l2_raw_json']

        # 获取原始特征数
        adaptive_features = l2_data.get('adaptive_features', {})
        original_meta = adaptive_features.get('_meta', {})
        original_count = original_meta.get('feature_count', 0)

        # 执行重解析
        try:
            result = extractor.extract(adaptive_features)
            new_count = len([k for k in result.features.keys() if not k.startswith('_')])
            new_meta = result.features.get('_meta', {})
            new_version = new_meta.get('extraction_version', 'UNKNOWN')

            # 计算压缩率
            if original_count > 0:
                compression_rate = (1 - new_count / original_count) * 100
            else:
                compression_rate = 0.0

            status = "✅ Success" if result.status.value in ['success', 'partial'] else "❌ Failed"

            audit_results.append({
                'match_id': match_id,
                'home_team': home_team,
                'away_team': away_team,
                'original_features': original_count,
                'new_features': new_count,
                'new_version': new_version,
                'compression_rate': compression_rate,
                'status': status
            })

            print(f"[{i}/10] {match_id}: {original_count:,} → {new_count:,} ({compression_rate:.1f}%)")

        except Exception as e:
            print(f"[{i}/10] {match_id}: ❌ Error - {e}")
            audit_results.append({
                'match_id': match_id,
                'home_team': home_team,
                'away_team': away_team,
                'original_features': original_count,
                'new_features': 0,
                'new_version': 'ERROR',
                'compression_rate': 0.0,
                'status': f"❌ Error: {str(e)[:50]}"
            })

    conn.close()

    # 输出审计表
    print("\n" + "=" * 100)
    print("验收审计表")
    print("=" * 100)
    print(f"{'Match ID':<15} {'比赛':<40} {'原特征':<12} {'新特征':<10} {'压缩率':<10} {'状态':<15}")
    print("-" * 100)

    for result in audit_results:
        match = f"{result['home_team']} vs {result['away_team']}"
        print(f"{result['match_id']:<15} {match:<40} {result['original_features']:>11,} "
              f"{result['new_features']:>9,} {result['compression_rate']:>9.1f}% {result['status']:<15}")

    # 统计摘要
    print("\n" + "=" * 100)
    print("统计摘要")
    print("=" * 100)

    successful = [r for r in audit_results if 'Success' in r['status']]
    avg_compression = sum(r['compression_rate'] for r in successful) / len(successful) if successful else 0

    print(f"成功处理: {len(successful)}/{len(rows)}")
    print(f"平均压缩率: {avg_compression:.2f}%")
    print(f"平均原始特征: {sum(r['original_features'] for r in audit_results) // len(audit_results):,}")
    print(f"平均新特征: {sum(r['new_features'] for r in successful) // len(successful) if successful else 0:,}")

    print("\n" + "=" * 100)
    if len(successful) == len(rows):
        print("✅ 验收通过！所有记录成功重解析")
    else:
        print(f"⚠️  部分通过：{len(successful)}/{len(rows)} 成功")
    print("=" * 100)

if __name__ == "__main__":
    run_acceptance_audit()
