#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# ║   TITAN V4.46.7 特征冒烟测试                                                 ║
# ║   Second Line of Defense - Data Integrity Smoke Test                         ║
# ═══════════════════════════════════════════════════════════════════════════════
#
# 每日入库后自动自检，拒绝"静默失败"
#
# @module scripts.ops.smoke_test_features
# @version V4.46.7
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================================
# 配置
# ============================================================================

@dataclass
class HealthThreshold:
    MV_MIN: float = 1_000_000       # 100 万
    MV_MAX: float = 10_000_000_000  # 100 亿
    ELO_MIN: float = 800
    ELO_MAX: float = 2200
    ZERO_MV_SHARE_THRESHOLD: float = 0.10

@dataclass
class CheckResult:
    name: str
    status: str  # PASS, WARN, FAIL
    message: str
    details: Dict = field(default_factory=dict)
    score: float = 100.0

# ============================================================================
# 数据库连接
# ============================================================================

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'host.docker.internal'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'football_db'),
        user=os.getenv('DB_USER', 'football_user'),
        password=os.getenv('DB_PASSWORD', 'football_pass'),
        cursor_factory=RealDictCursor
    )

# ============================================================================
# 冒烟测试
# ============================================================================

def check_data_volume(conn) -> CheckResult:
    """检查数据量"""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN m.status = 'finished' THEN 1 END) as finished
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
    """)
    row = cur.fetchone()
    cur.close()

    total, finished = row['total'], row['finished']

    if total < 100:
        return CheckResult("📊 数据量", "WARN", f"数据量偏低: {total} 场", {'total': total}, 60)
    elif total < 500:
        return CheckResult("📊 数据量", "PASS", f"数据量中等: {total} 场", {'total': total}, 80)
    else:
        return CheckResult("📊 数据量", "PASS", f"数据量充足: {total} 场 (完赛 {finished})", {'total': total}, 100)


def check_mv_share_extremes(conn) -> CheckResult:
    """检查身价占比极端值"""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN (lineup_features->>'home_mv_share')::float IN (0, 1) THEN 1 END) as extremes
        FROM l3_features
        WHERE lineup_features IS NOT NULL AND lineup_features != '{}'::jsonb
    """)
    row = cur.fetchone()
    cur.close()

    total = row['total'] or 1
    extremes = row['extremes'] or 0
    ratio = extremes / total

    if ratio > 0.10:
        return CheckResult("💰 身价占比", "WARN", f"极端值过多: {extremes}/{total} ({ratio:.1%})", {'ratio': ratio}, 50)
    elif extremes > 0:
        return CheckResult("💰 身价占比", "PASS", f"少量极端值: {extremes}/{total} ({ratio:.1%})", {'ratio': ratio}, 90)
    else:
        return CheckResult("💰 身价占比", "PASS", "无极端值", {'ratio': 0}, 100)


def check_mv_unit(conn) -> CheckResult:
    """检查身价单位"""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as too_high
        FROM l3_features
        WHERE (lineup_features->>'home_squad_value_eur')::numeric > 10000000000
    """)
    too_high = cur.fetchone()['too_high'] or 0
    cur.close()

    if too_high > 0:
        return CheckResult("📏 身价单位", "FAIL", f"⚠️ {too_high} 条 > 100亿 (单位可能错误)", {'too_high': too_high}, 30)
    return CheckResult("📏 身价单位", "PASS", "单位正常 (100万-100亿)", {}, 100)


def check_elo_range(conn) -> CheckResult:
    """检查 Elo 范围"""
    cur = conn.cursor()
    cur.execute("""
        SELECT AVG((elo_features->>'home_elo_pre')::float) as avg_elo,
               STDDEV((elo_features->>'home_elo_pre')::float) as std_elo
        FROM l3_features
        WHERE elo_features IS NOT NULL AND elo_features != '{}'::jsonb
    """)
    row = cur.fetchone()
    cur.close()

    avg_elo = float(row['avg_elo'] or 1500)
    std_elo = float(row['std_elo'] or 0)

    if 1400 <= avg_elo <= 1600 and std_elo > 50:
        return CheckResult("⚔️ Elo分布", "PASS", f"均值 {avg_elo:.0f}, 标准差 {std_elo:.0f}", {'avg': avg_elo}, 100)
    return CheckResult("⚔️ Elo分布", "WARN", f"分布异常: 均值 {avg_elo:.0f}", {'avg': avg_elo}, 70)


def check_h2h_coverage(conn) -> CheckResult:
    """检查 H2H 覆盖率"""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN h2h_features IS NOT NULL AND h2h_features != '{}'::jsonb THEN 1 END) as with_h2h
        FROM l3_features
    """)
    row = cur.fetchone()
    cur.close()

    total = row['total'] or 1
    with_h2h = row['with_h2h'] or 0
    rate = with_h2h / total

    if rate >= 0.8:
        return CheckResult("🔄 H2H覆盖", "PASS", f"覆盖率 {rate:.1%}", {'rate': rate}, 100)
    elif rate >= 0.5:
        return CheckResult("🔄 H2H覆盖", "PASS", f"覆盖率 {rate:.1%}", {'rate': rate}, 80)
    else:
        return CheckResult("🔄 H2H覆盖", "WARN", f"覆盖率偏低 {rate:.1%}", {'rate': rate}, 60)


def check_full_coverage(conn) -> CheckResult:
    """检查完整特征覆盖率"""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN
                   elo_features IS NOT NULL AND elo_features != '{}'::jsonb
                   AND lineup_features IS NOT NULL AND lineup_features != '{}'::jsonb
               THEN 1 END) as full
        FROM l3_features
    """)
    row = cur.fetchone()
    cur.close()

    total = row['total'] or 1
    full = row['full'] or 0
    rate = full / total

    if rate >= 0.7:
        return CheckResult("📈 完整特征", "PASS", f"{full}/{total} ({rate:.1%})", {'rate': rate}, 100)
    elif rate >= 0.5:
        return CheckResult("📈 完整特征", "PASS", f"{full}/{total} ({rate:.1%})", {'rate': rate}, 80)
    else:
        return CheckResult("📈 完整特征", "WARN", f"覆盖率低 {rate:.1%}", {'rate': rate}, 50)


# ============================================================================
# 主程序
# ============================================================================

def run_smoke_test():
    """运行冒烟测试"""
    print("\n" + "=" * 70)
    print("  🔍 TITAN V4.46.7 特征冒烟测试")
    print("=" * 70)

    conn = get_db_connection()
    results = [
        check_data_volume(conn),
        check_mv_share_extremes(conn),
        check_mv_unit(conn),
        check_elo_range(conn),
        check_h2h_coverage(conn),
        check_full_coverage(conn),
    ]
    conn.close()

    # 打印报告
    print("\n" + "─" * 70)
    print(f"  {'检查项':<18} | {'状态':<8} | {'健康分':<8} | 详情")
    print("─" * 70)

    for r in results:
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(r.status, "❓")
        print(f"  {r.name:<16} | {icon} {r.status:<4} | {r.score:>6.0f}/100 | {r.message}")

    print("─" * 70)

    # 计算总分
    total_score = sum(r.score for r in results) / len(results)

    if total_score >= 90:
        grade = "🟢 优秀"
    elif total_score >= 75:
        grade = "🟡 良好"
    elif total_score >= 60:
        grade = "🟠 及格"
    else:
        grade = "🔴 危险"

    print(f"\n  📊 数据库健康分: {total_score:.1f}/100 | 等级: {grade}")
    print("=" * 70 + "\n")

    return total_score, results


def main():
    parser = argparse.ArgumentParser(description='TITAN 特征冒烟测试')
    parser.add_argument('--json', action='store_true', help='JSON 输出')
    args = parser.parse_args()

    score, results = run_smoke_test()

    if args.json:
        output = {
            'timestamp': datetime.now().isoformat(),
            'health_score': score,
            'checks': [{'name': r.name, 'status': r.status, 'score': r.score, 'message': r.message} for r in results]
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

    # 返回码
    if score >= 75:
        return 0
    elif score >= 50:
        return 1
    return 2


if __name__ == '__main__':
    sys.exit(main())
