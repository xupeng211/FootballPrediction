#!/usr/bin/env python3
"""
V50.0 第一阶段：荷甲与英冠全量补课
=====================================
目标：全量补齐荷甲 (12) 和英冠 (48) 过去 5 个赛季的数据

硬指标：
1. 必须展示找回后的【已完赛+带比分】真实分布表
2. 数据库 UPSERT 成功率 > 95%
3. 比分覆盖率 > 90%（已完赛比赛）
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.api.collectors.v50_rich_l1_scanner import RichL1Match, RichL1Scanner

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/v50_phase1_execution.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


# 第一阶段目标联赛配置
# 注意：FotMob 联赛 ID 根据 config/fotmob_leagues.json
PHASE1_LEAGUES = [
    (29, "Eredivisie", "荷甲"),  # 荷甲 - ID 29
    (48, "Championship", "英冠"),  # 英冠 - ID 48
]


async def scan_league_data(league_id: int, league_name: str, years_back: int = 5) -> list[RichL1Match]:
    """
    扫描单个联赛的历史数据

    Args:
        league_id: 联赛 ID
        league_name: 联赛名称
        years_back: 回溯年数

    Returns:
        Rich L1 比赛列表
    """
    logger.info(f"🎯 开始扫描 {league_name} (ID={league_id}) 过去 {years_back} 年数据")

    async with RichL1Scanner() as scanner:
        matches = await scanner.scan_league_historical(league_id, league_name, years_back)

        logger.info(f"✅ {league_name} 扫描完成: {len(matches)} 场比赛")

        return matches


def save_match_index(matches: list[RichL1Match], league_name: str, output_dir: Path) -> Path:
    """
    保存比赛索引到文件

    Args:
        matches: 比赛列表
        league_name: 联赛名称
        output_dir: 输出目录

    Returns:
        保存的文件路径
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"v50_phase1_{league_name}_{timestamp}.json"
    output_file = output_dir / filename

    import json

    # 转换为可序列化的格式
    matches_data = [m.to_dict() for m in matches]

    # 统计数据
    finished_matches = [m for m in matches if m.is_finished()]
    matches_with_score = [m for m in finished_matches if m.has_score()]

    output_data = {
        "metadata": {
            "version": "V50.0-Phase1",
            "league": league_name,
            "timestamp": datetime.now().isoformat(),
            "total_matches": len(matches),
            "finished_matches": len(finished_matches),
            "matches_with_score": len(matches_with_score),
            "score_coverage": (len(matches_with_score) / len(finished_matches) * 100 if finished_matches else 0),
        },
        "matches": matches_data,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logger.info(f"💾 比赛索引已保存: {output_file}")

    return output_file


def print_score_distribution(all_matches: list[RichL1Match], league_name: str):
    """
    打印比分分布表

    Args:
        all_matches: 所有比赛
        league_name: 联赛名称
    """
    print("\n" + "=" * 70)
    print(f"📊 {league_name} - Rich L1 数据分布表")
    print("=" * 70)

    # 总体统计
    total = len(all_matches)
    finished = [m for m in all_matches if m.is_finished()]
    ongoing = [m for m in all_matches if m.status == "ongoing"]
    scheduled = [m for m in all_matches if m.status == "scheduled"]

    # 比分统计
    finished_with_score = [m for m in finished if m.has_score()]
    finished_without_score = [m for m in finished if not m.has_score()]

    print("\n📈 总体统计:")
    print(f"   总比赛数: {total:,}")
    print(f"   已完赛: {len(finished):,} ({len(finished) / total * 100:.1f}%)")
    print(f"   进行中: {len(ongoing):,} ({len(ongoing) / total * 100:.1f}%)")
    print(f"   未开始: {len(scheduled):,} ({len(scheduled) / total * 100:.1f}%)")

    print("\n🎯 比分统计 (Rich L1 核心指标):")
    print(f"   已完赛带比分: {len(finished_with_score):,}")
    print(f"   已完赛缺比分: {len(finished_without_score):,}")
    if finished:
        score_coverage = len(finished_with_score) / len(finished) * 100
        print(f"   比分覆盖率: {score_coverage:.1f}%")

    # 按赛季统计
    season_stats = {}
    for match in all_matches:
        season = match.season_name
        if season not in season_stats:
            season_stats[season] = {
                "total": 0,
                "finished": 0,
                "with_score": 0,
            }
        season_stats[season]["total"] += 1
        if match.is_finished():
            season_stats[season]["finished"] += 1
        if match.has_score():
            season_stats[season]["with_score"] += 1

    print("\n📅 按赛季分布:")
    for season in sorted(season_stats.keys()):
        stats = season_stats[season]
        print(f"   {season:6s}: {stats['total']:4d} 场 | 完赛 {stats['finished']:4d} | 带比分 {stats['with_score']:4d}")

    # 结果分布
    home_wins = sum(1 for m in finished_with_score if m.get_result_code() == "H")
    draws = sum(1 for m in finished_with_score if m.get_result_code() == "D")
    away_wins = sum(1 for m in finished_with_score if m.get_result_code() == "A")

    print("\n🏆 结果分布 (已完赛带比分):")
    print(f"   主胜: {home_wins} ({home_wins / len(finished_with_score) * 100:.1f}%)")
    print(f"   平局: {draws} ({draws / len(finished_with_score) * 100:.1f}%)")
    print(f"   客胜: {away_wins} ({away_wins / len(finished_with_score) * 100:.1f}%)")

    print("=" * 70)


async def main():
    """主函数"""
    logger.info("🚀 V50.0 第一阶段：荷甲与英冠全量补课")
    logger.info("=" * 70)

    # 创建输出目录
    output_dir = Path("data/production/v50_phase1_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_matches_by_league = {}

    # 扫描所有联赛
    for league_id, league_name_en, league_name_cn in PHASE1_LEAGUES:
        print(f"\n🎯 开始处理 {league_name_cn} ({league_name_en})")
        print("-" * 70)

        # 扫描数据
        matches = await scan_league_data(league_id, league_name_en, years_back=5)

        if not matches:
            logger.warning(f"⚠️ {league_name_cn} 没有扫描到任何比赛")
            continue

        # 保存索引
        save_match_index(matches, league_name_en, output_dir)

        # 打印分布表
        print_score_distribution(matches, league_name_cn)

        all_matches_by_league[league_name_cn] = matches

        # 短暂休息，避免 API 限流
        await asyncio.sleep(2)

    # 总体汇总
    print("\n" + "=" * 70)
    print("🎯 第一阶段总体汇总")
    print("=" * 70)

    total_matches = sum(len(m) for m in all_matches_by_league.values())
    total_finished = sum(len([x for x in m if x.is_finished()]) for m in all_matches_by_league.values())
    total_with_score = sum(len([x for x in m if x.has_score()]) for m in all_matches_by_league.values())

    print("\n📊 联赛汇总:")
    for league_name, matches in all_matches_by_league.items():
        print(f"   {league_name:10s}: {len(matches):,} 场比赛")

    print("\n📈 总体统计:")
    print(f"   总比赛数: {total_matches:,}")
    print(f"   已完赛: {total_finished:,}")
    print(f"   带比分: {total_with_score:,}")
    if total_finished > 0:
        score_coverage = total_with_score / total_finished * 100
        print(f"   比分覆盖率: {score_coverage:.1f}%")

    print("\n" + "=" * 70)
    print("✅ 第一阶段执行完成！")
    print("=" * 70)

    logger.info("🎉 V50.0 第一阶段执行完成！")


if __name__ == "__main__":
    asyncio.run(main())
