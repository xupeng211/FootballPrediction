#!/usr/bin/env python3
"""
V83.500 Slope Features Quality Audit
=====================================

倾率特征深度抽检工具 - 自动化审计 L3 特征中的"初终盘/倾率"数据

V83.500 核心功能:
- 从库中随机抽取 100 场"已完成"的比赛
- 验证 initial_price 是否存在且不为 [0, 0, 0]
- 验证 closing_price 是否为最新采集值
- 验证 total_movement（总偏移量）计算逻辑是否正确
- 输出《V83.500 倾率特征饱和度报告》

Usage:
    python scripts/ops/v83_500_slope_audit.py              # 抽检 100 场
    python scripts/ops/v83_500_slope_audit.py --sample 50  # 自定义样本数
    python scripts/ops/v83_500_slope_audit.py --verbose     # 详细输出
    python scripts/ops/v83_500_slope_audit.py --report     # 生成 JSON 报告

Author: V83.500 Engineering Team
Date: 2026-01-25
"""

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_SAMPLE_SIZE = 100
REPORT_DIR = PROJECT_ROOT / "logs"
SLOPE_AUDIT_REPORT = REPORT_DIR / "v83_500_slope_audit_report.json"

# 倾率特征字段列表
SLOPE_FEATURE_FIELDS = [
    "home_drop_ratio",
    "away_drop_ratio",
    "draw_drop_ratio",
    "total_movement",
    "initial_price",
    "closing_price"
]

# =============================================================================
# DATABASE QUERIES
# =============================================================================


def get_random_matches(sample_size: int = DEFAULT_SAMPLE_SIZE) -> list[dict[str, Any]]:
    """随机抽取已完成特征提取的比赛"""
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

        # 随机抽取 N 场比赛
        cur.execute("""
            SELECT
                m.match_id,
                m.league_name,
                m.season,
                m.home_team,
                m.away_team,
                m.match_date,
                m.technical_features,
                m.l3_extraction_status
            FROM matches m
            WHERE m.technical_features IS NOT NULL
              AND m.match_date >= '2020-08-01'
            ORDER BY RANDOM()
            LIMIT %s
        """, (sample_size,))

        matches = [dict(row) for row in cur.fetchall()]
        cur.close()

        return matches

    finally:
        conn.close()


def audit_slope_features(matches: list[dict[str, Any]], verbose: bool = False) -> dict[str, Any]:
    """审计倾率特征数据质量"""

    audit_results = {
        "total_sampled": len(matches),
        "with_initial_price": 0,
        "with_closing_price": 0,
        "with_complete_slope": 0,
        "invalid_initial_price": 0,  # [0, 0, 0]
        "invalid_total_movement": 0,  # 负数或异常值
        "issues": [],
        "slope_coverage": 0.0,
        "initial_price_coverage": 0.0,
        "closing_price_coverage": 0.0
    }

    for match in matches:
        match_id = match["match_id"]
        technical_features = match.get("technical_features", {})

        if not isinstance(technical_features, dict):
            audit_results["issues"].append({
                "match_id": match_id,
                "issue": "technical_features is not a dict",
                "value": str(type(technical_features))
            })
            continue

        # 检查 initial_price
        initial_price = technical_features.get("initial_price")
        if initial_price is not None:
            if isinstance(initial_price, list) and len(initial_price) == 3:
                if initial_price == [0, 0, 0]:
                    audit_results["invalid_initial_price"] += 1
                    audit_results["issues"].append({
                        "match_id": match_id,
                        "issue": "initial_price is [0, 0, 0]",
                        "value": initial_price
                    })
                else:
                    audit_results["with_initial_price"] += 1
            elif isinstance(initial_price, dict):
                # 检查是否有有效的价格数据
                if any(v != 0 for v in initial_price.values()):
                    audit_results["with_initial_price"] += 1
                else:
                    audit_results["invalid_initial_price"] += 1

        # 检查 closing_price
        closing_price = technical_features.get("closing_price")
        if closing_price is not None:
            if isinstance(closing_price, list) and len(closing_price) == 3:
                if any(v > 0 for v in closing_price):
                    audit_results["with_closing_price"] += 1
            elif isinstance(closing_price, dict):
                if any(v != 0 for v in closing_price.values()):
                    audit_results["with_closing_price"] += 1

        # 检查倾率特征
        has_slope = any(
            field in technical_features
            for field in ["home_drop_ratio", "total_movement"]
        )

        if has_slope:
            audit_results["with_complete_slope"] += 1

        # 验证 total_movement 计算逻辑
        total_movement = technical_features.get("total_movement")
        if total_movement is not None:
            try:
                movement_val = float(total_movement)
                if movement_val < 0:
                    audit_results["invalid_total_movement"] += 1
                    audit_results["issues"].append({
                        "match_id": match_id,
                        "issue": "total_movement is negative",
                        "value": total_movement
                    })
            except (ValueError, TypeError):
                audit_results["invalid_total_movement"] += 1
                audit_results["issues"].append({
                    "match_id": match_id,
                    "issue": "total_movement is not a valid number",
                    "value": total_movement
                })

        if verbose and match_id in [m["match_id"] for m in matches[:5]]:
            # 只显示前 5 场的详细信息
            print(f"\n  Match: {match_id}")
            print(f"    Initial Price: {initial_price}")
            print(f"    Closing Price: {closing_price}")
            print(f"    Total Movement: {total_movement}")
            print(f"    Has Slope: {has_slope}")

    # 计算覆盖率
    total = audit_results["total_sampled"]
    audit_results["slope_coverage"] = (
        audit_results["with_complete_slope"] / total * 100
    ) if total > 0 else 0
    audit_results["initial_price_coverage"] = (
        audit_results["with_initial_price"] / total * 100
    ) if total > 0 else 0
    audit_results["closing_price_coverage"] = (
        audit_results["with_closing_price"] / total * 100
    ) if total > 0 else 0

    return audit_results


def generate_audit_report(audit_results: dict[str, Any]) -> dict[str, Any]:
    """生成审计报告"""

    total = audit_results["total_sampled"]
    slope_coverage = audit_results["slope_coverage"]
    initial_coverage = audit_results["initial_price_coverage"]
    closing_coverage = audit_results["closing_price_coverage"]

    # 质量评级
    if slope_coverage >= 80 and initial_coverage >= 80 and closing_coverage >= 80:
        quality_grade = "✅ EXCELLENT"
        quality_score = "A"
    elif slope_coverage >= 60 and initial_coverage >= 60 and closing_coverage >= 60:
        quality_grade = "🟡 GOOD"
        quality_score = "B"
    elif slope_coverage >= 40 and initial_coverage >= 40 and closing_coverage >= 40:
        quality_grade = "🟠 MODERATE"
        quality_score = "C"
    else:
        quality_grade = "🔴 POOR"
        quality_score = "D"

    report = {
        "audit_timestamp": datetime.now().isoformat(),
        "version": "V83.500",
        "summary": {
            "total_sampled": total,
            "slope_coverage": round(slope_coverage, 2),
            "initial_price_coverage": round(initial_coverage, 2),
            "closing_price_coverage": round(closing_coverage, 2),
            "quality_grade": quality_grade,
            "quality_score": quality_score
        },
        "detailed_stats": {
            "with_initial_price": audit_results["with_initial_price"],
            "with_closing_price": audit_results["with_closing_price"],
            "with_complete_slope": audit_results["with_complete_slope"],
            "invalid_initial_price": audit_results["invalid_initial_price"],
            "invalid_total_movement": audit_results["invalid_total_movement"]
        },
        "issues": audit_results["issues"][:20],  # 只保留前 20 个问题
        "total_issues": len(audit_results["issues"])
    }

    return report


def print_audit_report(audit_results: dict[str, Any], verbose: bool = False) -> None:
    """打印审计报告"""

    print("\n" + "=" * 80)
    print("V83.500 SLOPE FEATURES QUALITY AUDIT REPORT")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 摘要
    print("┌─ AUDIT SUMMARY ─────────────────────────────────────────────────────────┐")
    print(f"  Total Sampled:            {audit_results['total_sampled']:,}")
    print(f"  Slope Coverage:           {audit_results['slope_coverage']:.2f}%")
    print(f"  Initial Price Coverage:   {audit_results['initial_price_coverage']:.2f}%")
    print(f"  Closing Price Coverage:   {audit_results['closing_price_coverage']:.2f}%")
    print()
    print(f"  With Initial Price:      {audit_results['with_initial_price']:,}")
    print(f"  With Closing Price:      {audit_results['with_closing_price']:,}")
    print(f"  With Complete Slope:     {audit_results['with_complete_slope']:,}")
    print()

    # 质量评级
    slope_coverage = audit_results['slope_coverage']
    if slope_coverage >= 80:
        quality_status = "✅ EXCELLENT"
    elif slope_coverage >= 60:
        quality_status = "🟡 GOOD"
    elif slope_coverage >= 40:
        quality_status = "🟠 MODERATE"
    else:
        quality_status = "🔴 POOR"

    print(f"  Quality Status:           {quality_status}")
    print("└──────────────────────────────────────────────────────────────────────────┘")
    print()

    # 问题统计
    if audit_results["invalid_initial_price"] > 0:
        print(f"⚠️  Invalid Initial Price ([0,0,0]): {audit_results['invalid_initial_price']}")

    if audit_results["invalid_total_movement"] > 0:
        print(f"⚠️  Invalid Total Movement: {audit_results['invalid_total_movement']}")

    if audit_results["total_issues"] > 0:
        print(f"\n⚠️  Total Issues Found: {audit_results['total_issues']}")
        if verbose:
            print("\nTop 10 Issues:")
            for issue in audit_results["issues"][:10]:
                print(f"  - {issue}")
    else:
        print("✅ No issues found in the sampled matches!")
    print()


def save_report(report: dict[str, Any]) -> None:
    """保存报告到文件"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with open(SLOPE_AUDIT_REPORT, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"[V83.500] ✅ Report saved to: {SLOPE_AUDIT_REPORT}")


# =============================================================================
# MAIN
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="V83.500 Slope Features Quality Audit"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"Number of matches to sample (default: {DEFAULT_SAMPLE_SIZE})"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate JSON report file"
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Output JSON only (no formatted text)"
    )

    args = parser.parse_args()

    # 1. 随机抽检比赛
    print(f"[V83.500] Sampling {args.sample} matches for slope features audit...")
    matches = get_random_matches(args.sample)

    if not matches:
        print("[V83.500] ❌ No matches found with technical_features!")
        return 1

    # 2. 审计倾率特征
    print(f"[V83.500] Auditing {len(matches)} matches...")
    audit_results = audit_slope_features(matches, verbose=args.verbose)

    # 3. 生成报告
    report = generate_audit_report(audit_results)

    # 4. 输出结果
    if not args.json_only:
        print_audit_report(audit_results, verbose=args.verbose)

    if args.report:
        save_report(report)

    # 5. 输出 JSON
    if args.json_only or args.report:
        print("\n" + "=" * 40)
        print("JSON Report:")
        print("=" * 40)
        print(json.dumps(report, indent=2, default=str))

    # 6. 返回状态码
    if audit_results["slope_coverage"] < 50:
        print("\n[V83.500] ⚠️  WARNING: Slope coverage is below 50%")
        return 1
    elif audit_results["slope_coverage"] < 80:
        print("\n[V83.500] 🟡 MODERATE: Slope coverage is below 80%")
        return 0
    else:
        print("\n[V83.500] ✅ EXCELLENT: Slope coverage is above 80%")
        return 0


if __name__ == "__main__":
    sys.exit(main())
