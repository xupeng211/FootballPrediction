#!/usr/bin/env python3
"""
V37.5 L3 特征探索脚本 (L3 Feature Explorer)
==============================================

用途：
1. 从 raw_match_data 表中提取高级特征（Big Chances + Player Ratings）
2. 统计数据覆盖率
3. 生成特征可用性报告

目标特征：
- Big Chances Created (创造重大机会)
- Player Ratings (全场最高分球员)

作者: ML Architect
日期: 2025-12-29
Phase: L3 Feature Exploration
Version: V37.5
"""

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import asyncpg
from tabulate import tabulate

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ============================================
# 数据库连接
# ============================================
async def get_db_pool():
    """获取数据库连接池"""
    import subprocess

    # 从 Docker 获取数据库密码
    result = subprocess.run(
        ["docker", "exec", "football_prediction_db", "printenv", "POSTGRES_PASSWORD"],
        capture_output=True,
        text=True,
    )
    db_password = result.stdout.strip() or "football123"

    return await asyncpg.create_pool(
        host="localhost",
        port=5432,
        database="football_prediction_dev",
        user="football_user",
        password=db_password,
        min_size=1,
        max_size=3,
    )


# ============================================
# 特征提取函数
# ============================================
def extract_big_chances(raw_api_data: dict) -> dict[str, Any] | None:
    """
    从原始 API 响应中提取 Big Chances Created

    路径: content.stats.Periods.All.stats -> 查找 "big_chance" 相关字段

    Returns:
        {"home": int, "away": int} 或 None
    """
    try:
        content = raw_api_data.get("content", {})
        stats_obj = content.get("stats", {})

        if not stats_obj:
            return None

        # 获取 Periods
        periods = stats_obj.get("Periods") or stats_obj.get("Period")
        if not periods or not isinstance(periods, dict):
            return None

        # 获取 All (全场统计)
        all_stats = periods.get("All", {})
        if not all_stats:
            return None

        # 遍历 stats 数组查找 big_chance
        stats_array = all_stats.get("stats", [])
        if not stats_array:
            return None

        for stat_group in stats_array:
            for stat in stat_group.get("stats", []):
                stat_key = stat.get("key", "").lower()
                if "big_chance" in stat_key or "bigchance" in stat_key:
                    stats_value = stat.get("stats", [])
                    if isinstance(stats_value, list) and len(stats_value) >= 2:
                        try:
                            return {
                                "home": int(stats_value[0]),
                                "away": int(stats_value[1]),
                            }
                        except (ValueError, TypeError):
                            return None

        return None

    except Exception:
        return None


def extract_player_ratings(raw_api_data: dict) -> dict[str, Any] | None:
    """
    从原始 API 响应中提取 Player Ratings

    路径: content.lineup -> home/away -> players -> 提取 rating
    返回全场最高分球员

    Returns:
        {"home_best": {"name": str, "rating": float}, "away_best": {...}}
        或 None
    """
    try:
        content = raw_api_data.get("content", {})
        lineup = content.get("lineup", {})

        if not lineup:
            return None

        result = {}

        for team in ["home", "away"]:
            if team not in lineup:
                result[f"{team}_best"] = None
                continue

            team_data = lineup[team]
            players = team_data.get("players", [])

            if not players:
                result[f"{team}_best"] = None
                continue

            # 查找评分最高的球员
            best_player = None
            best_rating = -1.0

            for player in players:
                rating = player.get("rating", 0)
                if rating and isinstance(rating, (int, float)) and rating > best_rating:
                    best_rating = rating
                    best_player = {
                        "name": player.get("name", {}).get("fullName", "Unknown"),
                        "id": player.get("id", None),
                        "rating": rating,
                    }

            result[f"{team}_best"] = best_player

        return result

    except Exception:
        return None


# ============================================
# 数据分析函数
# ============================================
async def analyze_feature_coverage(pool: asyncpg.Pool) -> dict[str, Any]:
    """
    分析已采集数据的特征覆盖率

    Returns:
        包含 Big Chances 和 Player Ratings 覆盖率的字典
    """
    async with pool.acquire() as conn:
        # 获取 Premier League (league_id=47) 的数据
        rows = await conn.fetch(
            """
            SELECT raw_data
            FROM raw_match_data r
            JOIN matches m ON r.match_id = m.match_id
            WHERE m.league_id = 47
            ORDER BY r.created_at DESC
            LIMIT 2000
            """
        )

        total = len(rows)
        big_chances_found = 0
        player_ratings_found = 0
        big_chances_samples = []
        player_ratings_samples = []

        for row in rows:
            # asyncpg 返回的 jsonb 可能是 str 或 dict
            if isinstance(row["raw_data"], str):
                raw_data = json.loads(row["raw_data"])
            else:
                raw_data = row["raw_data"]

            # raw_data 列包含 L2MatchDetailSchema.to_dict() 格式
            # 原始 API 响应在 raw_data["raw_data"] 中
            raw_api = raw_data.get("raw_data", {})

            if not raw_api:
                continue

            # 提取 Big Chances
            big_chances = extract_big_chances(raw_api)
            if big_chances:
                big_chances_found += 1
                if len(big_chances_samples) < 5:
                    big_chances_samples.append(big_chances)

            # 提取 Player Ratings
            ratings = extract_player_ratings(raw_api)
            if ratings:
                if ratings.get("home_best") or ratings.get("away_best"):
                    player_ratings_found += 1
                    if len(player_ratings_samples) < 5:
                        player_ratings_samples.append(ratings)

        return {
            "total_matches": total,
            "big_chances": {
                "found": big_chances_found,
                "coverage": round(big_chances_found / total * 100, 2) if total > 0 else 0,
                "samples": big_chances_samples,
            },
            "player_ratings": {
                "found": player_ratings_found,
                "coverage": round(player_ratings_found / total * 100, 2) if total > 0 else 0,
                "samples": player_ratings_samples,
            },
        }


# ============================================
# 报告生成
# ============================================
def generate_report(analysis: dict[str, Any]) -> str:
    """生成特征覆盖率报告"""

    report = []
    report.append("=" * 80)
    report.append(" " * 20 + "L3 特征探索报告 (V37.5)")
    report.append("=" * 80)
    report.append(f"\n生成时间: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    report.append("数据范围: Premier League (League ID: 47)")

    # 总体统计
    report.append("\n" + "=" * 80)
    report.append("📊 特征覆盖率统计")
    report.append("=" * 80)

    coverage_table = [
        [
            "Big Chances Created",
            f"{analysis['big_chances']['found']}",
            f"{analysis['total_matches']}",
            f"{analysis['big_chances']['coverage']}%",
            "✅ 可用" if analysis["big_chances"]["coverage"] > 80 else "⚠️ 需检查",
        ],
        [
            "Player Ratings",
            f"{analysis['player_ratings']['found']}",
            f"{analysis['total_matches']}",
            f"{analysis['player_ratings']['coverage']}%",
            "✅ 可用" if analysis["player_ratings"]["coverage"] > 80 else "⚠️ 需检查",
        ],
    ]

    report.append(
        tabulate(
            coverage_table,
            headers=["特征", "可用数量", "总场数", "覆盖率", "状态"],
            tablefmt="grid",
        )
    )

    # Big Chances 样本
    report.append("\n" + "=" * 80)
    report.append("🎯 Big Chances Created 样本数据")
    report.append("=" * 80)

    if analysis["big_chances"]["samples"]:
        for i, sample in enumerate(analysis["big_chances"]["samples"], 1):
            report.append(f"\n样本 {i}: 主队 {sample['home']} - 客队 {sample['away']}")
    else:
        report.append("\n⚠️  未找到 Big Chances 数据样本")

    # Player Ratings 样本
    report.append("\n" + "=" * 80)
    report.append("⭐ Player Ratings 样本数据 (最高分球员)")
    report.append("=" * 80)

    if analysis["player_ratings"]["samples"]:
        for i, sample in enumerate(analysis["player_ratings"]["samples"], 1):
            home_best = sample.get("home_best")
            away_best = sample.get("away_best")

            report.append(f"\n样本 {i}:")
            if home_best:
                report.append(f"  主队最佳: {home_best['name']} (评分: {home_best['rating']})")
            else:
                report.append("  主队最佳: (数据缺失)")

            if away_best:
                report.append(f"  客队最佳: {away_best['name']} (评分: {away_best['rating']})")
            else:
                report.append("  客队最佳: (数据缺失)")
    else:
        report.append("\n⚠️  未找到 Player Ratings 数据样本")

    # JSONB 路径说明
    report.append("\n" + "=" * 80)
    report.append("📝 JSONB 路径说明")
    report.append("=" * 80)

    report.append("\nBig Chances Created:")
    report.append("  路径: raw_data -> 'raw_data' -> 'content' -> 'stats' -> 'Periods' -> 'All' -> 'stats'")
    report.append("  查找: key 包含 'big_chance' 的统计项")

    report.append("\nPlayer Ratings:")
    report.append("  路径: raw_data -> 'raw_data' -> 'content' -> 'lineup' -> 'home'/'away' -> 'players'")
    report.append("  提取: rating 字段最高的球员")

    # 结论
    report.append("\n" + "=" * 80)
    report.append("🎯 结论与建议")
    report.append("=" * 80)

    big_chances_status = (
        "✅ 数据可用，可用于 L3 特征工程"
        if analysis["big_chances"]["coverage"] > 80
        else "⚠️ 覆盖率较低，建议进一步调查"
    )
    player_ratings_status = (
        "✅ 数据可用，可用于 L3 特征工程"
        if analysis["player_ratings"]["coverage"] > 80
        else "⚠️ 覆盖率较低，建议进一步调查"
    )

    report.append(f"\nBig Chances Created: {big_chances_status}")
    report.append(f"Player Ratings: {player_ratings_status}")

    if analysis["big_chances"]["coverage"] > 80 and analysis["player_ratings"]["coverage"] > 80:
        report.append("\n🎉 两个特征均具备高覆盖率，可立即用于 L3 特征工程！")
    else:
        report.append("\n📋 建议运行更深入的诊断，确认数据结构是否正确")

    report.append("\n" + "=" * 80)

    return "\n".join(report)


# ============================================
# 主流程
# ============================================
async def main():
    print("🔍 L3 特征探索器启动...")
    print("目标: Big Chances Created + Player Ratings\n")

    pool = await get_db_pool()

    try:
        # 分析特征覆盖率
        print("📊 正在分析已采集数据...")
        analysis = await analyze_feature_coverage(pool)

        # 生成报告
        report = generate_report(analysis)
        print("\n" + report)

        # 保存报告
        report_path = project_root / "logs" / "l3_feature_explorer_report.txt"
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n📝 报告已保存至: {report_path}")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
