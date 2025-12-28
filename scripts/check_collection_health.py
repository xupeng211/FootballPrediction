#!/usr/bin/env python3
"""
V36.0 采集系统健康检查工具
==========================
一键查询数据库并输出采集健康度报告

功能:
1. 5 大联赛覆盖率统计
2. 元数据纯度检查
3. Serie A 缺失度分析
4. 数据质量评分

使用:
    python scripts/check_collection_health.py
    python scripts/check_collection_health.py --season 2324

作者: DevOps Team
版本: V36.0
日期: 2025-12-28
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import asyncpg

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings


# 联赛配置 (V36.0 白名单)
LEAGUE_CONFIGS = {
    47: ("Premier League", 380),
    55: ("La Liga", 380),
    54: ("Bundesliga", 306),
    61: ("Ligue 1", 380),
    135: ("Serie A", 380),
}


async def check_collection_health(season_id: str = "2324") -> Dict[str, Any]:
    """
    检查采集系统健康度

    Args:
        season_id: 赛季代码 (e.g., "2324") 或 显示名称 (e.g., "23/24")

    Returns:
        健康度报告字典
    """
    settings = get_settings()

    # 自动转换 season_id 到显示名称格式
    season_display = season_id
    if "/" not in season_id:
        # 如果是 "2324" 格式，转换为 "23/24"
        season_display = f"{season_id[:2]}/{season_id[2:]}"

    print("=" * 70)
    print("🏥 V36.0 采集系统健康检查")
    print("=" * 70)
    print(f"📅 检查赛季: {season_display} (代码: {season_id})")
    print(f"🕐 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    conn = await asyncpg.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )

    try:
        # 1. 联赛覆盖率统计
        print("\n📊 1. 联赛覆盖率统计")
        print("-" * 70)

        coverage_stats = []
        total_matches = 0
        total_expected = 0
        total_correct_metadata = 0

        for league_id, (league_name, expected_count) in LEAGUE_CONFIGS.items():
            # 查询该联赛的比赛数量
            query = """
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN league_name = $2 THEN 1 END) as correct_metadata,
                    MIN(match_time) as earliest,
                    MAX(match_time) as latest
                FROM matches
                WHERE league_id = $1 AND season = $3
            """
            row = await conn.fetchrow(query, league_id, league_name, season_id)

            total = row["total"]
            correct_metadata = row["correct_metadata"]
            earliest = row["earliest"]
            latest = row["latest"]

            coverage = (total / expected_count * 100) if expected_count > 0 else 0
            purity = (correct_metadata / total * 100) if total > 0 else 100

            coverage_stats.append({
                "league_id": league_id,
                "league_name": league_name,
                "total": total,
                "expected": expected_count,
                "coverage": coverage,
                "purity": purity,
                "earliest": earliest,
                "latest": latest,
            })

            total_matches += total
            total_expected += expected_count
            total_correct_metadata += correct_metadata

        # 输出覆盖率统计
        for stat in coverage_stats:
            status_icon = "✅" if stat["coverage"] >= 80 else "⚠️" if stat["coverage"] >= 50 else "❌"
            purity_icon = "✅" if stat["purity"] == 100 else "⚠️"

            print(f"\n{status_icon} {stat['league_name']} (ID: {stat['league_id']})")
            print(f"   已采集: {stat['total']}/{stat['expected']} 场")
            print(f"   覆盖率: {stat['coverage']:.1f}%")
            print(f"   {purity_icon} 元数据纯度: {stat['purity']:.1f}%")
            if stat["earliest"]:
                print(f"   时间范围: {stat['earliest'].strftime('%Y-%m-%d')} ~ {stat['latest'].strftime('%Y-%m-%d')}")

        # 2. 总体统计
        print("\n" + "=" * 70)
        print("📈 2. 总体统计")
        print("-" * 70)

        overall_coverage = (total_matches / total_expected * 100) if total_expected > 0 else 0
        overall_purity = (total_correct_metadata / total_matches * 100) if total_matches > 0 else 100

        print(f"总采集: {total_matches}/{total_expected} 场")
        print(f"总覆盖率: {overall_coverage:.1f}%")
        print(f"元数据纯度: {overall_purity:.1f}%")

        # 3. Serie A 缺失度分析
        print("\n" + "=" * 70)
        print("🔍 3. Serie A 缺失度分析")
        print("-" * 70)

        serie_a_id = 135
        serie_a_name, serie_a_expected = LEAGUE_CONFIGS[serie_a_id]

        query = """
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN league_name = $2 THEN 1 END) as correct_metadata
            FROM matches
            WHERE league_id = $1 AND season = $3
        """
        row = await conn.fetchrow(query, serie_a_id, serie_a_name, season_id)

        serie_a_total = row["total"]
        serie_a_correct = row["correct_metadata"]
        serie_a_missing = serie_a_expected - serie_a_total
        serie_a_purity = (serie_a_correct / serie_a_total * 100) if serie_a_total > 0 else 0

        print(f"\nSerie A (ID: {serie_a_id})")
        print(f"  已采集: {serie_a_total}/{serie_a_expected} 场")
        print(f"  缺失: {serie_a_missing} 场 ({serie_a_missing / serie_a_expected * 100:.1f}%)")
        print(f"  元数据纯度: {serie_a_purity:.1f}%")

        if serie_a_total == 0:
            print(f"  ❌ 警告: Serie A 数据完全缺失！")
            print(f"     → V35.4 修复前 Serie A (ID 135) 未配置")
        elif serie_a_purity < 100:
            print(f"  ⚠️  警告: 存在元数据污染！")
            print(f"     → {serie_a_total - serie_a_correct} 场比赛的 league_name 不正确")

        # 4. 数据质量评分
        print("\n" + "=" * 70)
        print("⭐ 4. 数据质量评分")
        print("-" * 70)

        scores = []

        # 覆盖率评分
        coverage_score = min(100, overall_coverage)
        scores.append(("覆盖率", coverage_score))

        # 元数据纯度评分
        purity_score = overall_purity
        scores.append(("元数据纯度", purity_score))

        # Serie A 专项评分
        serie_a_score = (serie_a_total / serie_a_expected * 100) if serie_a_expected > 0 else 0
        scores.append(("Serie A 覆盖率", serie_a_score))

        # 综合评分
        overall_score = (
            coverage_score * 0.4 +
            purity_score * 0.3 +
            serie_a_score * 0.3
        )

        for name, score in scores:
            stars = "⭐" * int(score / 20)
            bar = "█" * int(score / 5)
            print(f"  {name:12s}: {bar:20s} {score:5.1f}% {stars}")

        print(f"\n  {'综合评分':12s}: {'█' * int(overall_score / 5):20s} {overall_score:5.1f}%")

        # 评级
        if overall_score >= 90:
            grade = "A+ (优秀)"
            emoji = "🏆"
        elif overall_score >= 80:
            grade = "A (良好)"
            emoji = "🥇"
        elif overall_score >= 70:
            grade = "B (中等)"
            emoji = "🥈"
        elif overall_score >= 60:
            grade = "C (及格)"
            emoji = "🥉"
        else:
            grade = "D (不及格)"
            emoji = "❌"

        print(f"  评级: {emoji} {grade}")

        # 5. 建议
        print("\n" + "=" * 70)
        print("💡 5. 优化建议")
        print("-" * 70)

        suggestions = []

        if overall_coverage < 80:
            suggestions.append("• 建议运行全量采集: python scripts/collectors/full_l1_l2_harvest.py")

        if overall_purity < 100:
            suggestions.append("• 建议运行元数据修正: psql -f deploy/sql/fix_league_metadata_v35.4.sql")

        if serie_a_total == 0:
            suggestions.append("• ⚠️  Serie A 完全缺失，检查 V36.0 配置")

        if serie_a_purity < 100 and serie_a_total > 0:
            suggestions.append("• ⚠️  Serie A 存在元数据污染，可能需要重新采集")

        if not suggestions:
            suggestions.append("• ✅ 数据质量良好，继续保持！")
            suggestions.append("• 建议: 定期运行健康检查监控数据质量")

        for suggestion in suggestions:
            print(f"  {suggestion}")

        # 返回报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "season_id": season_id,
            "coverage_stats": coverage_stats,
            "total_matches": total_matches,
            "total_expected": total_expected,
            "overall_coverage": overall_coverage,
            "overall_purity": overall_purity,
            "serie_a_total": serie_a_total,
            "serie_a_expected": serie_a_expected,
            "serie_a_missing": serie_a_missing,
            "overall_score": overall_score,
        }

        return report

    finally:
        await conn.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="V36.0 采集系统健康检查工具"
    )
    parser.add_argument(
        "--season",
        type=str,
        default="2324",
        help="赛季代码 (默认: 2324)",
    )

    args = parser.parse_args()

    # 执行健康检查
    report = asyncio.run(check_collection_health(args.season))

    # 根据评分设置退出码
    if report["overall_score"] >= 70:
        print("\n" + "=" * 70)
        print("✅ 健康检查完成 - 系统状态良好")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("⚠️  健康检查完成 - 需要关注数据质量")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
