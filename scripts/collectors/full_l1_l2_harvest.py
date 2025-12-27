#!/usr/bin/env python3
"""
V35.3 全量 L1/L2 采集器
========================
完整采集 7 大联赛 × 5 赛季的所有比赛数据

作者: FootballPrediction Team
版本: V35.3
日期: 2025-12-26
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.collectors.fotmob_collector_l1_l2 import FotMobL1L2Collector

logger = logging.getLogger(__name__)


# 联赛配置 (与 global_l1_scanner.py 保持一致)
LEAGUE_CONFIGS = [
    {"id": 47, "name": "Premier League", "code": "PL"},  # 380 场/赛季
    {"id": 87, "name": "La Liga", "code": "LL"},  # 380 场/赛季
    {"id": 54, "name": "Serie A", "code": "SA"},  # 306 场/赛季
    {"id": 53, "name": "Bundesliga", "code": "BL"},  # 306 场/赛季
    {"id": 61, "name": "Ligue 1", "code": "L1"},  # 306 场/赛季
    {"id": 42, "name": "Champions League", "code": "UCL"},  # 144 场/赛季
]

# 赛季配置 (FotMob 格式)
SEASONS = {
    "20/21": "2021",
    "21/22": "2122",
    "22/23": "2223",
    "23/24": "2324",
    "24/25": "2425",
}


async def full_harvest(l2_limit: int = 10000, silent_mode: bool = True):
    """
    全量 L1/L2 采集

    Args:
        l2_limit: L2 采集数量限制
        silent_mode: 静默生产模式（减少日志输出）
    """
    log_level = logging.WARNING if silent_mode else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

    # 创建专用进度日志器（始终输出关键进度）
    progress_logger = logging.getLogger("progress")
    progress_logger.setLevel(logging.INFO)
    progress_logger.addHandler(logging.StreamHandler())
    progress_logger.propagate = False

    progress_logger.info("=" * 60)
    progress_logger.info("🌍 V35.3 全量 L1/L2 采集 - 静默生产模式")
    progress_logger.info(f"📊 目标: {len(LEAGUE_CONFIGS)} 大联赛 × {len(SEASONS)} 赛季")
    progress_logger.info("=" * 60)

    async with FotMobL1L2Collector(max_l2_concurrency=2, silent_mode=silent_mode) as collector:  # V26.0 限流参数
        all_matches = []
        total_combinations = len(LEAGUE_CONFIGS) * len(SEASONS)
        completed = 0
        last_progress = 0

        # 步骤 1: L1 采集所有联赛-赛季组合
        progress_logger.info("📋 步骤 1: L1 全量采集")

        for league in LEAGUE_CONFIGS:
            for season_name, season_code in SEASONS.items():
                completed += 1
                progress = int(completed / total_combinations * 100)

                # 只在完成 10% 或关键节点时输出进度
                if progress >= last_progress + 10 or completed == total_combinations:
                    progress_logger.info(f"⏳ L1 进度: {progress}% ({completed}/{total_combinations})")
                    last_progress = progress

                try:
                    matches = await collector.collect_season_matches(
                        league_id=league["id"],
                        season_code=season_code,
                        league_name=league["name"],  # ✅ 传递动态联赛名称
                        season_display=season_name,  # ✅ 传递动态赛季显示名称
                    )

                    # 标注联赛和赛季信息
                    for match in matches:
                        match["league_name"] = league["name"]
                        match["league_id"] = league["id"]
                        match["season"] = season_name

                    all_matches.extend(matches)

                except Exception as e:
                    logger.error(f"✗ {league['name']} {season_name} 失败: {e}")

        progress_logger.info("=" * 60)
        progress_logger.info(f"✅ L1 采集完成: {len(all_matches)} 场比赛")
        progress_logger.info("=" * 60)

        # 步骤 2: 保存 L1 数据到数据库
        progress_logger.info("💾 步骤 2: 保存 L1 数据到数据库...")

        saved_count = await collector.save_all_l1_matches(all_matches)
        progress_logger.info(f"✅ L1 保存完成: {saved_count}/{len(all_matches)} 场")

        # 步骤 3: L2 并发采集
        progress_logger.info("=" * 60)
        progress_logger.info(f"📊 步骤 3: L2 并发采集 (限制: {l2_limit} 场)")
        progress_logger.info("=" * 60)

        # 提取 match_id (使用 external_id + season 作为唯一键)
        match_ids = []
        for m in all_matches[:l2_limit]:
            external_id = m.get("id") or m.get("external_id")
            season = m.get("season", "unknown")
            if external_id:
                match_ids.append(f"{external_id}_{season}")  # 使用唯一复合键

        # 只采集新比赛（过滤已存在的）
        progress_logger.info("🔍 筛选新比赛...")
        new_match_ids = await collector._filter_new_matches(match_ids)
        progress_logger.info(f"🎯 待采集: {len(new_match_ids)}/{len(match_ids)} 场新比赛")

        if new_match_ids:
            # 标记状态为进行中
            await collector._update_collection_status_batch(new_match_ids, "in_progress")

            # 并发采集（带进度跟踪）
            total_l2 = len(new_match_ids)
            l2_completed = 0
            last_l2_progress = 0

            async def l2_with_progress(match_id: str):
                nonlocal l2_completed, last_l2_progress
                # V26.0 修复：采集并保存 L2 数据
                data = await collector.collect_l2_match_data(match_id)
                if data:
                    # 保存到数据库
                    await collector._save_l2_raw_data(match_id, data)
                l2_completed += 1
                l2_progress = int(l2_completed / total_l2 * 100)
                if l2_progress >= last_l2_progress + 10 or l2_completed == total_l2:
                    progress_logger.info(f"⏳ L2 进度: {l2_progress}% ({l2_completed}/{total_l2})")
                    last_l2_progress = l2_progress
                return data

            # 批量并发采集
            tasks = [l2_with_progress(mid) for mid in new_match_ids]
            l2_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 统计结果
            l2_stats = {
                "total": total_l2,
                "successful": sum(1 for r in l2_results if r and not isinstance(r, Exception)),
                "failed": sum(1 for r in l2_results if isinstance(r, Exception) or r is False),
            }

            progress_logger.info("=" * 60)
            progress_logger.info("📊 L2 采集统计")
            progress_logger.info(f"   总计: {l2_stats['total']}")
            progress_logger.info(f"   成功: {l2_stats['successful']}")
            progress_logger.info(f"   失败: {l2_stats['failed']}")
            progress_logger.info("=" * 60)
        else:
            l2_stats = {"total": 0, "successful": 0, "failed": 0}
            progress_logger.info("ℹ️  无新比赛需要采集")

        progress_logger.info("=" * 60)
        progress_logger.info("🎉 V35.3 全量 L1/L2 采集完成!")
        progress_logger.info("=" * 60)

        # 输出完整统计
        stats = collector.get_stats()
        progress_logger.info("📊 完整统计报告")
        for key, value in stats.items():
            progress_logger.info(f"   {key}: {value}")

        return l2_stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="V35.3 全量 L1/L2 采集器")
    parser.add_argument("--l2-limit", type=int, default=10000, help="L2 采集数量限制 (默认: 10000)")
    parser.add_argument("--verbose", action="store_true", help="启用详细日志输出")

    args = parser.parse_args()

    exit_code = asyncio.run(full_harvest(l2_limit=args.l2_limit, silent_mode=not args.verbose))
    sys.exit(exit_code if exit_code is not None else 0)
