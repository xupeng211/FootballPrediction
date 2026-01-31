#!/usr/bin/env python3
"""
V82.000 Quality Gate & Pending Review Tracker
==============================================

质量闭环：
1. FeatureExtractionSchema 验证
2. pending_review.json 生成（70-85% 置信度映射）
3. 质量审计报告

Usage:
    python scripts/ops/v82_000_quality_gate.py --validate-features
    python scripts/ops/v82_000_quality_gate.py --generate-pending
    python scripts/ops/v82_000_quality_gate.py --audit-report

Author: V82.000 Engineering Team
Date: 2026-01-25
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_unified import get_settings
import psycopg2
from psycopg2.extras import RealDictCursor


# =============================================================================
# CONSTANTS
# =============================================================================

LOGS_DIR = PROJECT_ROOT / "logs"
PENDING_REVIEW_JSON = LOGS_DIR / "pending_review.json"
QUALITY_AUDIT_JSON = LOGS_DIR / "quality_audit.json"

# V26.7 特征清单（预期特征）
V26_7_FEATURE_COUNT = 6346


# =============================================================================
# FEATURE EXTRACTION SCHEMA VALIDATION
# =============================================================================

def validate_feature_extraction_schema() -> Dict[str, Any]:
    """验证特征提取 Schema 完整性"""
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )

    try:
        cur = conn.cursor()

        # 1. 检查 technical_features 完整性
        cur.execute("""
            SELECT
                COUNT(*) as total_matches,
                COUNT(CASE WHEN technical_features IS NOT NULL AND technical_features != '{}' THEN 1 END) as with_features,
                COUNT(CASE WHEN technical_features IS NULL OR technical_features = '{}' THEN 1 END) as without_features
            FROM matches
            WHERE match_date >= '2020-08-01'
        """)
        feature_stats = cur.fetchone()

        # 2. 抽样检查特征（检查键的数量）
        cur.execute("""
            SELECT
                match_id,
                home_team,
                away_team,
                jsonb_object_keys(technical_features) as feature_keys
            FROM matches
            WHERE technical_features IS NOT NULL
              AND technical_features != '{}'
              AND match_date >= '2020-08-01'
            LIMIT 100
        """)
        sample_features = cur.fetchall()

        # 3. 特征键数量分布
        key_distribution = defaultdict(int)
        for row in sample_features:
            keys = row.get('feature_keys', [])
            key_distribution[len(keys)] += 1

        # 4. 异常特征检测（空对象）
        cur.execute("""
            SELECT
                COUNT(*) as anomaly_count
            FROM matches
            WHERE technical_features = '{}'
        """)
        anomaly_result = cur.fetchone()

        cur.close()

        return {
            'total_matches': feature_stats['total_matches'],
            'with_features': feature_stats['with_features'],
            'without_features': feature_stats['without_features'],
            'coverage_rate': feature_stats['with_features'] / feature_stats['total_matches'] if feature_stats['total_matches'] > 0 else 0,
            'sample_size': len(sample_features),
            'key_distribution': dict(key_distribution),
            'anomaly_count': anomaly_result['anomaly_count'],
            'expected_keys': V26_7_FEATURE_COUNT,
            'validation_passed': anomaly_result['anomaly_count'] == 0
        }

    finally:
        conn.close()


# =============================================================================
# PENDING REVIEW TRACKER
# =============================================================================

def generate_pending_review_list() -> List[Dict[str, Any]]:
    """生成待审核映射列表（70-85% 置信度）"""
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )

    try:
        cur = conn.cursor()

        # 查询待审核映射（confidence 在 0.70 - 0.85 之间）
        cur.execute("""
            SELECT
                mm.fotmob_id,
                mm.home_team,
                mm.away_team,
                mm.league_name,
                mm.match_date,
                mm.oddsportal_url,
                ROUND((mm.confidence * 100)::numeric, 2) as confidence_percent,
                mm.mapping_method,
                mm.review_status,
                mm.review_notes,
                m.match_id as fotmob_match_id,
                CASE
                    WHEN m.home_team IS NULL OR m.away_team IS NULL THEN 'MISSING_MATCH'
                    WHEN ABS(LEVENSHTEIN(mm.home_team, COALESCE(m.home_team, ''))) > 5 THEN 'TEAM_MISMATCH'
                    ELSE 'OK'
                END as validation_flag
            FROM matches_mapping mm
            LEFT JOIN matches m ON mm.fotmob_id = m.match_id
            WHERE mm.confidence >= 0.70
              AND mm.confidence < 0.85
              AND mm.review_status IN ('pending', 'pending_review')
            ORDER BY mm.confidence DESC, mm.match_date DESC
        """)
        pending_reviews = cur.fetchall()

        cur.close()

        return [dict(row) for row in pending_reviews]

    finally:
        conn.close()


def save_pending_review_json(pending_list: List[Dict[str, Any]]) -> None:
    """保存待审核列表到 JSON"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    output = {
        'generated_at': datetime.now().isoformat(),
        'total_count': len(pending_list),
        'by_league': defaultdict(int),
        'by_confidence_range': defaultdict(int),
        'validation_flags': defaultdict(int),
        'pending_reviews': pending_list
    }

    # 统计信息
    for item in pending_list:
        league = item.get('league_name', 'Unknown')
        conf = item.get('confidence_percent', 0)
        flag = item.get('validation_flag', 'UNKNOWN')

        output['by_league'][league] += 1

        if conf >= 80:
            output['by_confidence_range']['80-85%'] += 1
        else:
            output['by_confidence_range']['70-80%'] += 1

        output['validation_flags'][flag] += 1

    # 转换 defaultdict 为 dict
    output['by_league'] = dict(output['by_league'])
    output['by_confidence_range'] = dict(output['by_confidence_range'])
    output['validation_flags'] = dict(output['validation_flags'])

    with open(PENDING_REVIEW_JSON, 'w') as f:
        json.dump(output, f, indent=2, default=str)


# =============================================================================
# QUALITY AUDIT REPORT
# =============================================================================

def generate_quality_audit_report() -> Dict[str, Any]:
    """生成质量审计报告"""
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )

    try:
        cur = conn.cursor()

        # 1. 映射质量统计
        cur.execute("""
            SELECT
                review_status,
                COUNT(*) as count,
                AVG(confidence * 100) as avg_confidence,
                MIN(confidence * 100) as min_confidence,
                MAX(confidence * 100) as max_confidence
            FROM matches_mapping
            WHERE review_status IS NOT NULL
            GROUP BY review_status
            ORDER BY review_status
        """)
        review_stats = [dict(row) for row in cur.fetchall()]

        # 2. 高置信度映射（> 90%）
        cur.execute("""
            SELECT
                COUNT(*) as high_conf_count,
                COUNT(*) * 100.0 / (SELECT COUNT(*) FROM matches_mapping WHERE oddsportal_url IS NOT NULL) as high_conf_rate
            FROM matches_mapping
            WHERE confidence >= 0.90
              AND oddsportal_url IS NOT NULL
        """)
        high_conf = cur.fetchone()

        # 3. 低置信度映射（< 65%）
        cur.execute("""
            SELECT
                COUNT(*) as low_conf_count,
                COUNT(*) * 100.0 / (SELECT COUNT(*) FROM matches_mapping WHERE oddsportal_url IS NOT NULL) as low_conf_rate
            FROM matches_mapping
            WHERE confidence < 0.65
              AND oddsportal_url IS NOT NULL
        """)
        low_conf = cur.fetchone()

        # 4. 按联赛统计
        cur.execute("""
            SELECT
                mm.league_name,
                COUNT(*) as total_mappings,
                AVG(mm.confidence * 100) as avg_confidence,
                COUNT(CASE WHEN mm.review_status = 'approved' THEN 1 END) as approved_count,
                COUNT(CASE WHEN mm.review_status = 'pending_review' THEN 1 END) as pending_count
            FROM matches_mapping mm
            WHERE mm.league_name IS NOT NULL
            GROUP BY mm.league_name
            ORDER BY total_mappings DESC
            LIMIT 10
        """)
        league_stats = [dict(row) for row in cur.fetchall()]

        # 5. FeatureExtractionSchema 验证
        schema_validation = validate_feature_extraction_schema()

        cur.close()

        return {
            'generated_at': datetime.now().isoformat(),
            'mapping_quality': {
                'review_stats': review_stats,
                'high_confidence': dict(high_conf),
                'low_confidence': dict(low_conf),
                'total_mappings': sum(s['count'] for s in review_stats)
            },
            'league_breakdown': league_stats,
            'schema_validation': schema_validation,
            'overall_health_score': calculate_health_score(schema_validation, high_conf, low_conf)
        }

    finally:
        conn.close()


def calculate_health_score(schema_validation: Dict, high_conf: Dict, low_conf: Dict) -> float:
    """计算整体健康评分 (0-10)"""
    score = 10.0

    # 特征完整性 (-2 分)
    if not schema_validation['validation_passed']:
        score -= 2.0

    # 异常特征 (-1 分)
    if schema_validation['anomaly_count'] > 0:
        score -= 1.0

    # 高置信度率 (+0.5 分)
    if high_conf.get('high_conf_rate', 0) > 80:
        score += 0.5

    # 低置信度率 (-1 分)
    if low_conf.get('low_conf_rate', 0) > 10:
        score -= 1.0

    return max(0.0, min(10.0, score))


# =============================================================================
# DISPLAY FUNCTIONS
# =============================================================================

def print_schema_validation_report(validation: Dict[str, Any]) -> None:
    """打印 Schema 验证报告"""
    print("=" * 80)
    print("V82.000 FEATURE EXTRACTION SCHEMA VALIDATION")
    print("=" * 80)
    print()

    print(f"  Total Matches:        {validation['total_matches']:,}")
    print(f"  With Features:        {validation['with_features']:,} ({validation['coverage_rate']*100:.1f}%)")
    print(f"  Without Features:     {validation['without_features']:,}")
    print()

    print("  Sample Key Distribution (100 samples):")
    for key_count, count in sorted(validation['key_distribution'].items()):
        bar = "█" * (count * 2)
        print(f"    {key_count:5d} keys: {count:3d} {bar}")

    print()
    print(f"  Expected Keys:         {validation['expected_keys']:,}")
    print(f"  Anomaly Count:         {validation['anomaly_count']}")
    print()

    status_icon = "✅" if validation['validation_passed'] else "❌"
    print(f"  Validation Status:     {status_icon} {'PASSED' if validation['validation_passed'] else 'FAILED'}")
    print()


def print_pending_review_summary(pending_list: List[Dict[str, Any]]) -> None:
    """打印待审核摘要"""
    print("=" * 80)
    print("V82.000 PENDING REVIEW SUMMARY")
    print("=" * 80)
    print()

    print(f"  Total Pending:         {len(pending_list):,}")
    print()

    print("  By League:")
    for league, count in sorted(pending_list[0].items() if pending_list else {}, key=lambda x: -x[1]):
        print(f"    {league}: {count}")

    print()

    print("  By Confidence Range:")
    print(f"    80-85%: {pending_list[1].get('80-85%', 0)}")
    print(f"    70-80%: {pending_list[1].get('70-80%', 0)}")

    print()

    print("  Validation Flags:")
    print(f"    OK: {pending_list[2].get('OK', 0)}")
    print(f"    MISSING_MATCH: {pending_list[2].get('MISSING_MATCH', 0)}")
    print(f"    TEAM_MISMATCH: {pending_list[2].get('TEAM_MISMATCH', 0)}")

    print()


def print_quality_audit_report(audit: Dict[str, Any]) -> None:
    """打印质量审计报告"""
    print("=" * 80)
    print("V82.000 QUALITY AUDIT REPORT")
    print("=" * 80)
    print()

    # 健康评分
    health_score = audit['overall_health_score']
    health_color = "🟢" if health_score >= 8 else "🟡" if health_score >= 6 else "🔴"
    print(f"  Overall Health Score: {health_color} {health_score:.1f}/10.0")
    print()

    # 映射质量
    print("  Mapping Quality:")
    for stat in audit['mapping_quality']['review_stats']:
        status = stat['review_status']
        count = stat['count']
        avg_conf = stat.get('avg_confidence', 0)
        print(f"    {status}: {count:,} (avg conf: {avg_conf:.1f}%)")

    print()

    # 高/低置信度
    print(f"  High Confidence (>90%): {audit['mapping_quality']['high_confidence']['high_conf_rate']:.1f}%")
    print(f"  Low Confidence (<65%): {audit['mapping_quality']['low_confidence']['low_conf_rate']:.1f}%")
    print()

    # Schema 验证
    schema = audit['schema_validation']
    schema_status = "✅ PASSED" if schema['validation_passed'] else "❌ FAILED"
    print(f"  Schema Validation:     {schema_status}")
    print(f"  Feature Coverage:      {schema['coverage_rate']*100:.1f}%")
    print(f"  Anomalies:             {schema['anomaly_count']}")
    print()


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="V82.000 Quality Gate & Pending Review Tracker")
    parser.add_argument('--validate-features', action='store_true', help='验证特征提取 Schema')
    parser.add_argument('--generate-pending', action='store_true', help='生成 pending_review.json')
    parser.add_argument('--audit-report', action='store_true', help='生成质量审计报告')
    parser.add_argument('--full-check', action='store_true', help='完整质量检查（所有验证）')

    args = parser.parse_args()

    # 完整质量检查
    if args.full_check:
        print("[V82.000] Running full quality check...\n")

        # 1. Schema 验证
        validation = validate_feature_extraction_schema()
        print_schema_validation_report(validation)

        # 2. 待审核列表
        pending_list = generate_pending_review_list()
        save_pending_review_json(pending_list)
        print(f"[V82.000] ✅ Saved {len(pending_list)} pending reviews to {PENDING_REVIEW_JSON}")
        print()

        # 3. 质量审计报告
        audit = generate_quality_audit_report()
        print_quality_audit_report(audit)

        # 保存审计报告
        with open(QUALITY_AUDIT_JSON, 'w') as f:
            json.dump(audit, f, indent=2, default=str)
        print(f"[V82.000] ✅ Saved quality audit to {QUALITY_AUDIT_JSON}")

        return 0

    # 单独命令
    if args.validate_features:
        validation = validate_feature_extraction_schema()
        print_schema_validation_report(validation)
        return 0 if validation['validation_passed'] else 1

    if args.generate_pending:
        pending_list = generate_pending_review_list()
        save_pending_review_json(pending_list)
        print(f"[V82.000] ✅ Generated {PENDING_REVIEW_JSON} with {len(pending_list)} pending reviews")
        print_pending_review_summary(json.load(open(PENDING_REVIEW_JSON)))
        return 0

    if args.audit_report:
        audit = generate_quality_audit_report()
        print_quality_audit_report(audit)

        with open(QUALITY_AUDIT_JSON, 'w') as f:
            json.dump(audit, f, indent=2, default=str)
        print(f"[V82.000] ✅ Saved quality audit to {QUALITY_AUDIT_JSON}")
        return 0

    # 默认：显示帮助
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
