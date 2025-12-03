#!/usr/bin/env python3
"""
L2深度数据审计脚本
首席数据审计师：分析已收集的高阶数据
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import psycopg2
from typing import Dict, List

def get_latest_l2_data():
    """获取最新的L2数据样本"""
    conn = psycopg2.connect(
        host='db',
        port=5432,
        user='postgres',
        password='postgres-dev-password',
        database='football_prediction'
    )

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, match_date, lineups, stats, events, home_team_id, away_team_id
                FROM matches
                WHERE lineups::text != '{}'
                ORDER BY updated_at DESC
                LIMIT 3
            """)

            records = cur.fetchall()
            return records

    finally:
        conn.close()

def analyze_stats_field(stats_str: str) -> Dict:
    """分析stats字段的内容"""
    try:
        stats = json.loads(stats_str) if isinstance(stats_str, str) else stats_str

        analysis = {
            "total_metrics": len(stats),
            "metrics": list(stats.keys()),
            "sample_values": {}
        }

        # 提取每个指标的样本值
        for key, value in stats.items():
            analysis["sample_values"][key] = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)

        return analysis

    except Exception as e:
        return {"error": str(e), "raw_data": str(stats_str)[:200]}

def analyze_lineups_field(lineups_str: str) -> Dict:
    """分析阵容字段的内容"""
    try:
        lineups = json.loads(lineups_str) if isinstance(lineups_str, str) else lineups_str

        analysis = {
            "has_home_lineup": "home_lineup" in lineups,
            "has_away_lineup": "away_lineup" in lineups,
            "home_team_players": len(lineups.get("home_lineup", [])),
            "away_team_players": len(lineups.get("away_lineup", [])),
            "total_players": len(lineups.get("home_lineup", [])) + len(lineups.get("away_lineup", []))
        }

        # 检查球员数据结构
        if lineups.get("home_lineup"):
            sample_player = lineups["home_lineup"][0]
            analysis["home_player_fields"] = list(sample_player.keys()) if sample_player else []

        if lineups.get("away_lineup"):
            sample_player = lineups["away_lineup"][0]
            analysis["away_player_fields"] = list(sample_player.keys()) if sample_player else []

        return analysis

    except Exception as e:
        return {"error": str(e), "raw_data": str(lineups_str)[:200]}

def analyze_events_field(events_str: str) -> Dict:
    """分析事件字段的内容"""
    try:
        events = json.loads(events_str) if isinstance(events_str, str) else events_str

        analysis = {
            "total_events": len(events),
            "event_types": set(),
            "sample_events": []
        }

        for event in events[:5]:  # 只看前5个事件
            if isinstance(event, dict):
                analysis["sample_events"].append(event)
                if "type" in event:
                    analysis["event_types"].add(event["type"])
            else:
                analysis["sample_events"].append({"raw_event": str(event)[:100]})

        analysis["event_types"] = list(analysis["event_types"])

        return analysis

    except Exception as e:
        return {"error": str(e), "raw_data": str(events_str)[:200]}

def main():
    """主审计函数"""
    print("🔍 L2深度数据审计开始...")
    print("=" * 60)

    records = get_latest_l2_data()

    if not records:
        print("❌ 未找到任何L2数据记录")
        return

    print(f"📊 找到 {len(records)} 条最新记录\n")

    for i, record in enumerate(records, 1):
        match_id, match_date, lineups, stats, events, home_id, away_id = record

        print(f"🎯 记录 {i}/{len(records)}: Match {match_id} ({match_date})")
        print(f"   主队ID: {home_id}, 客队ID: {away_id}")
        print("-" * 50)

        # 分析阵容数据
        print("👥 阵容数据分析:")
        lineup_analysis = analyze_lineups_field(str(lineups))
        if "error" not in lineup_analysis:
            print(f"   ✅ 主队球员: {lineup_analysis['home_team_players']} 名")
            print(f"   ✅ 客队球员: {lineup_analysis['away_team_players']} 名")
            print(f"   ✅ 总计: {lineup_analysis['total_players']} 名球员")

            if lineup_analysis.get("home_player_fields"):
                print(f"   📋 主队球员字段: {lineup_analysis['home_player_fields']}")
        else:
            print(f"   ❌ 阵容分析错误: {lineup_analysis['error']}")

        print()

        # 分析统计数据
        print("📈 统计数据分析:")
        stats_analysis = analyze_stats_field(str(stats))
        if "error" not in stats_analysis:
            print(f"   ✅ 统计指标数量: {stats_analysis['total_metrics']}")
            print(f"   📋 统计指标列表: {stats_analysis['metrics']}")

            for metric, value in stats_analysis['sample_values'].items():
                print(f"   📊 {metric}: {value}")
        else:
            print(f"   ❌ 统计分析错误: {stats_analysis['error']}")

        print()

        # 分析事件数据
        print("⚡ 事件数据分析:")
        events_analysis = analyze_events_field(str(events))
        if "error" not in events_analysis:
            print(f"   ✅ 事件总数: {events_analysis['total_events']}")
            print(f"   📋 事件类型: {events_analysis['event_types']}")

            if events_analysis['sample_events']:
                print("   📝 事件样本:")
                for j, event in enumerate(events_analysis['sample_events'][:3], 1):
                    print(f"      {j}. {event}")
        else:
            print(f"   ❌ 事件分析错误: {events_analysis['error']}")

        print("\n" + "=" * 60 + "\n")

if __name__ == "__main__":
    main()