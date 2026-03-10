#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# ║   TITAN V4.46.8 身价单位终极修正                                             ║
# ║   Market Value Unit Ultimate Fix                                     ║
# ═══════════════════════════════════════════════════════════════════════════════
#
# 修正规则:
# 1. 如果 > 100亿: 除以 1,000,000 (欧元 → 百万欧元)
# 2. 如果在 1万-10万之间: 除以 100 (错误的放大)
# 3. 重新计算 home_mv_share
#
# @module scripts.ops.fix_market_value_units
# @version V4.46.8-ULTIMATE
# ═══════════════════════════════════════════════════════════════════════════════

import argparse
import json
import os
import sys

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'host.docker.internal'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'football_db'),
        user=os.getenv('DB_USER', 'football_user'),
        password=os.getenv('DB_PASSWORD', 'football_pass'),
        cursor_factory=RealDictCursor
    )


def parse_jsonb(data):
    if not data:
        return {}
    if isinstance(data, str):
        try:
            return json.loads(data)
        except:
            return {}
    return data if isinstance(data, dict) else {}


def fix_single_value(value):
    """修正单个身价值"""
    if value is None:
        return None, "skip"

    try:
        val = float(value)
    except (ValueError, TypeError):
        return value, "skip"

    # > 100亿: 存的是欧元，需要除以 1M
    if val > 100_000_000_000:
        return val / 1_000_000, "divide_1m"

    # 1万-10万: 存的是被放大的百万欧元，需要除以 100
    if 10_000 <= val <= 100_000:
        return val / 100, "divide_100"

    return val, "ok"


def recalculate_mv_share(home_mv, away_mv):
    """重新计算身价占比"""
    if home_mv is None or away_mv is None:
        return None

    try:
        home = float(home_mv)
        away = float(away_mv)
    except (ValueError, TypeError):
        return None

    total = home + away
    if total <= 0:
        return 0.5

    return round(home / total, 4)


def fix_all_records(conn, dry_run=False):
    """修正所有异常记录"""
    cur = conn.cursor()
    cur.execute("""
        SELECT match_id, lineup_features
        FROM l3_features
        WHERE lineup_features IS NOT NULL
          AND lineup_features != '{}'::jsonb
    """)

    rows = cur.fetchall()
    cur.close()

    stats = {
        'total': len(rows),
        'fixed_too_large': 0,
        'fixed_bloated': 0,
        'fixed_share': 0,
        'skipped': 0,
        'errors': 0
    }

    for row in rows:
        try:
            lineup = parse_jsonb(row['lineup_features'])
            if not lineup:
                stats['skipped'] += 1
                continue

            needs_update = False

            # 修正 home_squad_value_eur
            if 'home_squad_value_eur' in lineup:
                new_val, action = fix_single_value(lineup['home_squad_value_eur'])
                if action == "divide_1m":
                    lineup['home_squad_value_eur'] = new_val
                    stats['fixed_too_large'] += 1
                    needs_update = True
                elif action == "divide_100":
                    lineup['home_squad_value_eur'] = new_val
                    stats['fixed_bloated'] += 1
                    needs_update = True

            # 修正 away_squad_value_eur
            if 'away_squad_value_eur' in lineup:
                new_val, action = fix_single_value(lineup['away_squad_value_eur'])
                if action == "divide_1m":
                    lineup['away_squad_value_eur'] = new_val
                    stats['fixed_too_large'] += 1
                    needs_update = True
                elif action == "divide_100":
                    lineup['away_squad_value_eur'] = new_val
                    stats['fixed_bloated'] += 1
                    needs_update = True

            # 重新计算 home_mv_share
            if 'home_squad_value_eur' in lineup and 'away_squad_value_eur' in lineup:
                new_share = recalculate_mv_share(
                    lineup['home_squad_value_eur'],
                    lineup['away_squad_value_eur']
                )
                if new_share is not None:
                    old_share = lineup.get('home_mv_share')
                    if old_share != new_share:
                        lineup['home_mv_share'] = new_share
                        stats['fixed_share'] += 1
                        needs_update = True

            # 更新数据库
            if needs_update and not dry_run:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE l3_features
                    SET lineup_features = %s::jsonb
                    WHERE match_id = %s
                """, (json.dumps(lineup), row['match_id']))
                cur.close()

        except Exception as e:
            stats['errors'] += 1
            print(f"  ❌ 错误 [{row['match_id']}]: {e}")

    if not dry_run:
        conn.commit()

    return stats


def run_ultimate_fix(dry_run=False):
    """执行终极修正"""
    print("\n" + "=" * 70)
    print("  🔧 TITAN V4.46.8 身价单位终极修正")
    print("=" * 70)

    conn = get_db_connection()

    # 执行修正
    print(f"\n[1/2] 扫描并修正数据...")
    if dry_run:
        print("      ⚠️ DRY RUN 模式 - 未实际修改数据")

    stats = fix_all_records(conn, dry_run=dry_run)
    conn.close()

    print(f"\n      📊 修正统计:")
    print(f"         总记录: {stats['total']}")
    print(f"         >100亿→÷1M: {stats['fixed_too_large']}")
    print(f"         1万-10万→÷100: {stats['fixed_bloated']}")
    print(f"         重算占比: {stats['fixed_share']}")
    print(f"         跳过: {stats['skipped']}")
    print(f"         错误: {stats['errors']}")

    print("\n" + "=" * 70)
    if dry_run:
        print("  ⚠️ DRY RUN 完成")
    else:
        print("  ✅ 终极修正完成!")
    print("=" * 70 + "\n")

    return stats


def main():
    parser = argparse.ArgumentParser(description='TITAN 身价单位终极修正')
    parser.add_argument('--dry-run', action='store_true', help='仅扫描不修改')
    args = parser.parse_args()

    run_ultimate_fix(dry_run=args.dry_run)
    return 00


if __name__ == '__main__':
    sys.exit(main())
