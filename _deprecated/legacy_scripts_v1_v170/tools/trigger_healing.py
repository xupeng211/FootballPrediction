#!/usr/bin/env python3
"""
V37.6 全链路自愈脚本 - 123 场坏账定点爆破

功能:
    1. 查询所有有 l3_odds_data 但 payout_ratio 为 NULL/0 的比赛
    2. 对每场坏账触发 NOTIFY odds_updated 信号
    3. 监控自愈进度
    4. 捕获失败原因到 logs/failed_features.json

坏账定义:
    - matches.l3_odds_data IS NOT NULL
    - match_features.payout_ratio IS NULL OR payout_ratio = 0

Author: 首席 SRE & 数据质量官
Version: V37.6
Date: 2026-01-12
"""
import json
import logging
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import psycopg2
from src.config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_bad_debt_matches() -> List[Dict[str, Any]]:
    """
    查询所有坏账比赛（有 l3_odds_data 但无有效 payout_ratio）

    Returns:
        坏账比赛列表
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # 查询坏账
    cursor.execute("""
        SELECT m.match_id, m.league_name, m.home_team, m.away_team,
               m.match_date, m.l3_odds_data
        FROM matches m
        LEFT JOIN match_features mf ON m.match_id = mf.match_id
        WHERE m.l3_odds_data IS NOT NULL
          AND (mf.payout_ratio IS NULL OR mf.payout_ratio = 0)
        ORDER BY m.match_date DESC
    """)

    bad_debts = []
    for row in cursor.fetchall():
        match_id, league, home, away, match_date, odds_data = row
        bad_debts.append({
            'match_id': match_id,
            'league_name': league,
            'home_team': home,
            'away_team': away,
            'match_date': match_date.isoformat() if match_date else None,
            'has_odds': True
        })

    cursor.close()
    conn.close()

    return bad_debts


def trigger_notify_healing(match_ids: List[str]) -> int:
    """
    对坏账比赛触发 NOTIFY odds_updated 信号

    Args:
        match_ids: 比赛 ID 列表

    Returns:
        成功触发的数量
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    conn.autocommit = True
    cursor = conn.cursor()

    triggered = 0
    for match_id in match_ids:
        try:
            # 构造 NOTIFY 载荷
            payload = json.dumps({"match_id": match_id, "has_odds": True})

            # 发送 NOTIFY 信号
            cursor.execute("NOTIFY odds_updated, %s", (payload,))
            triggered += 1

        except Exception as e:
            logger.error(f"触发 NOTIFY 失败 {match_id}: {e}")

    cursor.close()
    conn.close()

    return triggered


def monitor_healing_progress(match_ids: List[str], max_wait_seconds: int = 600):
    """
    监控自愈进度

    Args:
        match_ids: 坏账比赛 ID 列表
        max_wait_seconds: 最大等待时间（秒）
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    conn.autocommit = True
    cursor = conn.cursor()

    start_time = time.time()
    last_report_time = 0

    logger.info(f"📍 开始监控 {len(match_ids)} 场坏账自愈（最多 {max_wait_seconds}s）...")

    while time.time() - start_time < max_wait_seconds:
        # 每 30 秒报告一次进度
        if time.time() - last_report_time > 30:
            elapsed = int(time.time() - start_time)

            # 查询当前状态
            placeholders = ','.join(['%s'] * len(match_ids))
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN mf.payout_ratio IS NOT NULL AND mf.payout_ratio > 0 THEN 1 END) as healed
                FROM matches m
                LEFT JOIN match_features mf ON m.match_id = mf.match_id
                WHERE m.match_id IN ({placeholders})
            """, match_ids)

            row = cursor.fetchone()
            if row:
                total, healed = row
                heal_rate = 100.0 * healed / total if total > 0 else 0

                logger.info(f"[{elapsed:3d}s] 📊 自愈进度: "
                           f"已治愈={healed}/{total} ({heal_rate:.1f}%) | "
                           f"待治愈={total - healed}")

                last_report_time = time.time()

                # 检查是否全部治愈
                if healed >= total * 0.95:  # 95% 治愈即认为成功
                    logger.info(f"✅ 达到 95% 治愈率，提前结束监控")
                    break

        time.sleep(5)

    # 获取最终统计
    placeholders = ','.join(['%s'] * len(match_ids))
    cursor.execute(f"""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN mf.payout_ratio IS NOT NULL AND mf.payout_ratio > 0 THEN 1 END) as healed
        FROM matches m
        LEFT JOIN match_features mf ON m.match_id = mf.match_id
        WHERE m.match_id IN ({placeholders})
    """, match_ids)

    row = cursor.fetchone()
    total, healed = row

    cursor.close()
    conn.close()

    return total, healed


def analyze_unhealed_matches(match_ids: List[str]) -> List[Dict[str, Any]]:
    """
    分析未治愈的比赛，捕获失败原因

    Args:
        match_ids: 比赛 ID 列表

    Returns:
        未治愈的比赛列表（含失败原因）
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # 查询未治愈的比赛
    placeholders = ','.join(['%s'] * len(match_ids))
    cursor.execute(f"""
        SELECT m.match_id, m.league_name, m.home_team, m.away_team,
               m.l3_odds_data, mf.payout_ratio
        FROM matches m
        LEFT JOIN match_features mf ON m.match_id = mf.match_id
        WHERE m.match_id IN ({placeholders})
          AND (mf.payout_ratio IS NULL OR mf.payout_ratio = 0)
    """, match_ids)

    unhealed = []
    for row in cursor.fetchall():
        match_id, league, home, away, odds_data, payout_ratio = row

        # 分析失败原因
        reason = "未知原因"
        if odds_data is None:
            reason = "无 l3_odds_data"
        else:
            # 检查 odds_data 格式
            try:
                if isinstance(odds_data, dict):
                    odds_dict = odds_data
                else:
                    odds_dict = json.loads(odds_data) if isinstance(odds_data, str) else {}

                # 检查必需字段
                has_home = 'home_odds' in odds_dict or 'closing_odds' in odds_dict
                has_draw = 'draw_odds' in odds_dict or 'closing_odds' in odds_dict
                has_away = 'away_odds' in odds_dict or 'closing_odds' in odds_dict

                if not (has_home and has_draw and has_away):
                    reason = "赔率格式不完整（缺少 home/draw/away 字段）"
                else:
                    reason = "特征提取失败（代码逻辑或数据问题）"

            except json.JSONDecodeError:
                reason = "l3_odds_data JSON 解析失败"
            except Exception as e:
                reason = f"分析异常: {str(e)}"

        unhealed.append({
            'match_id': match_id,
            'league_name': league,
            'home_team': home,
            'away_team': away,
            'payout_ratio': payout_ratio,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })

    cursor.close()
    conn.close()

    return unhealed


def save_failed_records(unhealed: List[Dict[str, Any]]):
    """
    保存失败记录到 logs/failed_features.json

    Args:
        unhealed: 未治愈的比赛列表
    """
    failed_file = Path("logs/failed_features.json")

    # 读取现有记录
    existing_records = []
    if failed_file.exists():
        try:
            with open(failed_file, 'r') as f:
                existing_records = json.load(f)
        except:
            existing_records = []

    # 合并新记录（去重）
    existing_match_ids = {r['match_id'] for r in existing_records}
    new_records = [r for r in unhealed if r['match_id'] not in existing_match_ids]

    # 限制最多 100 条记录
    merged_records = existing_records + new_records
    if len(merged_records) > 100:
        merged_records = merged_records[-100:]

    # 保存
    failed_file.parent.mkdir(exist_ok=True)
    with open(failed_file, 'w') as f:
        json.dump(merged_records, f, indent=2, ensure_ascii=False)

    logger.info(f"💾 失败记录已保存到 {failed_file}")
    logger.info(f"   总记录数: {len(merged_records)} (新增: {len(new_records)})")


def main():
    """主函数"""
    print("=" * 70)
    print("🚨 V37.6 全链路自愈 - 123 场坏账定点爆破")
    print("=" * 70)

    # 1. 检查 EventBus 状态
    print("\n📍 Step 1: 检查 EventBus 状态")
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'src.services.event_bus'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            pid = result.stdout.strip()
            print(f"   ✅ EventBus 运行中 (PID: {pid})")
        else:
            print("   ❌ EventBus 未运行，请先启动 EventBus")
            return False
    except:
        print("   ❌ 无法检查 EventBus 状态")
        return False

    # 2. 查询坏账数据
    print("\n📍 Step 2: 查询坏账数据")
    bad_debts = get_bad_debt_matches()
    print(f"   ✅ 发现 {len(bad_debts)} 场坏账")

    if len(bad_debts) == 0:
        print("   🎉 没有坏账，无需自愈！")
        return True

    # 显示前 5 场坏账
    print(f"   前 5 场坏账:")
    for i, bad in enumerate(bad_debts[:5], 1):
        print(f"      {i}. {bad['match_id']} | {bad['league_name']} | "
              f"{bad['home_team']} vs {bad['away_team']}")

    # 3. 触发 NOTIFY 自愈
    print(f"\n📍 Step 3: 触发 NOTIFY 自愈")
    match_ids = [b['match_id'] for b in bad_debts]
    triggered = trigger_notify_healing(match_ids)
    print(f"   ✅ 已触发 {triggered}/{len(match_ids)} 个 NOTIFY 信号")

    # 4. 监控自愈进度（10 分钟）
    print(f"\n📍 Step 4: 监控自愈进度")
    total, healed = monitor_healing_progress(match_ids, max_wait_seconds=600)

    heal_rate = 100.0 * healed / total if total > 0 else 0
    print(f"\n   最终结果: {healed}/{total} ({heal_rate:.1f}%)")

    # 5. 分析未治愈的比赛
    print(f"\n📍 Step 5: 分析未治愈的比赛")
    unhealed = analyze_unhealed_matches(match_ids)

    if unhealed:
        print(f"   ⚠️  未治愈: {len(unhealed)} 场")

        # 保存失败记录
        save_failed_records(unhealed)

        # 按失败原因统计
        reason_counts = {}
        for u in unhealed:
            reason = u['reason']
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        print(f"\n   失败原因统计:")
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
            print(f"      - {reason}: {count} 场")
    else:
        print(f"   ✅ 全部治愈！")

    # 6. 打印最终判定
    print("\n" + "=" * 70)
    print("📊 V37.6 全链路自愈结果")
    print("=" * 70)

    # 准入红线判定
    success = True
    if heal_rate < 80.0:
        success = False
        print(f"\n❌ 自愈 FAILED (治愈率: {heal_rate:.1f}% < 80%)")
        print(f"   准入红线: ❌ 失败")
        print(f"   禁止启动 8 Workers 全量收集！")
    else:
        print(f"\n✅ 自愈 PASSED (治愈率: {heal_rate:.1f}%)")
        print(f"   准入红线: ✅ 通过")
        print(f"   可以启动 8 Workers 全量收集")

    print("=" * 70)

    return success


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)
