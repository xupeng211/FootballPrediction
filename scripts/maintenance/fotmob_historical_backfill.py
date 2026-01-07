#!/usr/bin/env python3
"""
FotMob 历史数据回填脚本 - V26.6
=====================================

核心功能：
    1. 针对新增加的联赛，自动循环抓取过去 3-5 年的历史比赛 ID
    2. 依次调用 FotMobCoreCollector 进行数据采集
    3. 兼容 V26.5 安全锁和哨兵系统
    4. 支持断点续传和进度恢复

Usage:
    # 回填所有启用的联赛（默认 3 年）
    python scripts/maintenance/fotmob_historical_backfill.py

    # 回填指定联赛
    python scripts/maintenance/fotmob_historical_backfill.py --league-id 47 --years 5

    # 干跑模式（不实际采集）
    python scripts/maintenance/fotmob_historical_backfill.py --dry-run

Author: Data Engineering Expert
Version: V26.6
Date: 2026-01-06
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

import argparse

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.collectors.fotmob_core import FotMobCoreCollector
from src.api.collectors.collection_sentry import CollectionSentry
from src.config.harvest_config import get_config_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/v26_6_backfill.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FotMobHistoricalBackfill:
    """
    FotMob 历史数据回填引擎

    功能：
    1. 根据配置文件生成采集任务列表
    2. 调用 FotMob API 获取历史比赛 ID
    3. 批量采集比赛数据
    4. 集成 V26.5 哨兵系统
    """

    def __init__(
        self,
        config_path: str | None = None,
        enable_sentry: bool = True,
        dry_run: bool = False,
    ):
        """
        初始化回填引擎

        Args:
            config_path: 配置文件路径
            enable_sentry: 是否启用哨兵系统
            dry_run: 干跑模式（不实际采集）
        """
        self.config_manager = get_config_manager(config_path)
        self.collector = FotMobCoreCollector()
        self.enable_sentry = enable_sentry
        self.dry_run = dry_run

        # 初始化哨兵（如果启用）
        self.sentry: CollectionSentry | None = None
        if enable_sentry:
            strategy_config = self.config_manager.get_strategy_config()
            self.sentry = CollectionSentry(
                window_size=strategy_config.sentry_window_size,
                success_rate_threshold=strategy_config.sentry_success_rate_threshold,
                consecutive_failure_threshold=strategy_config.sentry_consecutive_failure_threshold,
                pause_duration_hours=strategy_config.sentry_pause_duration_hours,
            )
            logger.info("✅ V26.5 哨兵系统已启用")

        # 统计信息
        self.total_matches = 0
        self.success_count = 0
        self.failed_count = 0
        self.skipped_count = 0  # V26.7: 跳过的比赛数（未结束/取消）

    def discover_historical_matches(
        self, league_id: int, season_code: str
    ) -> list[int]:
        """
        发现历史比赛 ID

        Args:
            league_id: 联赛 ID
            season_code: 赛季代码（例如 "2324"）

        Returns:
            比赛 ID 列表
        """
        logger.info(f"🔍 发现历史比赛: league_id={league_id}, season={season_code}")

        try:
            match_ids = self.collector.discover_ligue_matches(league_id, season_code)
            logger.info(f"✅ 发现 {len(match_ids)} 场比赛")
            return match_ids
        except Exception as e:
            logger.error(f"❌ 发现比赛失败: {e}")
            return []

    def backfill_league(
        self, league_id: int, season: str, limit: int | None = None
    ) -> dict[str, int]:
        """
        回填单个联赛的指定赛季数据

        Args:
            league_id: 联赛 ID
            season: 赛季代码
            limit: 最大采集数量（None 表示无限制）

        Returns:
            统计信息字典
        """
        # 获取联赛配置
        league_config = self.config_manager.get_league_config(league_id)
        if not league_config:
            logger.error(f"❌ 联赛配置不存在: league_id={league_id}")
            return {"total": 0, "success": 0, "failed": 0}

        if not league_config.is_enabled():
            logger.warning(f"⚠️ 联赛未启用，跳过: {league_config.name_zh}")
            return {"total": 0, "success": 0, "failed": 0}

        logger.info(f"🎯 开始回填: {league_config.name_zh} {season}")
        logger.info(f"   联赛 ID: {league_id}")
        logger.info(f"   赛季代码: {season}")

        # 发现历史比赛 ID
        match_ids = self.discover_historical_matches(league_id, season)

        # V26.7: 累加跳过的比赛数
        skipped = self.collector.last_skipped_count
        self.skipped_count += skipped

        if not match_ids:
            logger.warning(f"⚠️ 未发现比赛: {league_config.name_zh} {season}")
            return {"total": 0, "success": 0, "failed": 0}

        # 应用限制
        if limit and limit < len(match_ids):
            match_ids = match_ids[:limit]
            logger.info(f"⚠️ 限制采集数量: {limit}")

        # 批量采集
        stats = self._backfill_matches(league_id, season, match_ids)

        return stats

    def _backfill_matches(
        self, league_id: int, season: str, match_ids: list[int]
    ) -> dict[str, int]:
        """
        批量采集比赛数据

        Args:
            league_id: 联赛 ID
            season: 赛季代码
            match_ids: 比赛 ID 列表

        Returns:
            统计信息字典
        """
        success_count = 0
        failed_count = 0

        for i, match_id in enumerate(match_ids, 1):
            try:
                logger.info(
                    f"[{i}/{len(match_ids)}] 采集比赛: {match_id} (league={league_id}, season={season})"
                )

                if self.dry_run:
                    logger.info(f"🔬 干跑模式: 跳过实际采集")
                    success_count += 1
                    continue

                # 哨兵健康检查（如果启用）
                if self.sentry:
                    is_healthy = self.sentry.check_health()
                    if not is_healthy:
                        logger.warning("⚠️ 哨兵检测到不健康状态")
                        try:
                            self.sentry.check_health_or_stop()
                        except Exception:
                            # 哨兵触发停机，中断采集
                            raise

                # 采集比赛数据
                result = self.collector.harvest_match_with_league(
                    match_id=match_id, league_id=league_id, season=season
                )

                if result:
                    success_count += 1
                    # 记录成功到哨兵
                    if self.sentry:
                        self.sentry.record_result(True)
                    logger.info(f"✅ 比赛 {match_id} 采集成功")
                else:
                    failed_count += 1
                    # 记录失败到哨兵
                    if self.sentry:
                        self.sentry.record_result(False)
                    logger.warning(f"⚠️ 比赛 {match_id} 采集失败")

                # 每 10 场打印进度
                if i % 10 == 0:
                    logger.info(
                        f"📊 进度: {i}/{len(match_ids)} | "
                        f"成功: {success_count} | 失败: {failed_count}"
                    )

            except Exception as e:
                failed_count += 1
                logger.error(f"❌ 比赛 {match_id} 异常: {e}")
                # 如果是哨兵触发的异常，重新抛出
                if "Sentry triggered" in str(e) or "SecurityInterrupt" in str(type(e)):
                    raise

        return {"total": len(match_ids), "success": success_count, "failed": failed_count}

    def backfill_all(
        self, league_id: int | None = None, years: int | None = None
    ) -> dict[str, dict[str, int]]:
        """
        回填所有启用的联赛

        Args:
            league_id: 指定联赛 ID（None 表示回填所有联赛）
            years: 回填年数（None 表示使用配置文件的默认值）

        Returns:
            各联赛的统计信息字典
        """
        logger.info("=" * 60)
        logger.info("🚀 开始历史数据回填")
        logger.info("=" * 60)

        if self.dry_run:
            logger.info("🔬 干跑模式: 不会实际采集数据")

        # 获取采集任务列表
        tasks = self.config_manager.get_harvest_tasks()

        # 过滤任务（如果指定联赛 ID）
        if league_id:
            tasks = [t for t in tasks if t["league_id"] == league_id]
            logger.info(f"🎯 指定联赛 ID: {league_id}")

        # 过滤任务（如果指定年数）
        if years:
            # 简单实现：只采集最近 N 年的赛季
            current_year = datetime.now().year
            recent_seasons = set()
            for y in range(years):
                season_code = f"{current_year - y:02d}{current_year - y + 1:02d}"
                recent_seasons.add(season_code[-2:])  # 取后两位

            tasks = [t for t in tasks if t["season"][-2:] in recent_seasons]
            logger.info(f"🎯 回填年数: {years}")

        logger.info(f"📋 总任务数: {len(tasks)}")

        # 执行回填
        all_stats = {}
        for i, task in enumerate(tasks, 1):
            logger.info("")
            logger.info(f"任务 [{i}/{len(tasks)}]")

            stats = self.backfill_league(
                league_id=task["league_id"],
                season=task["season"],
            )

            all_stats[f"{task['name_zh']}_{task['season']}"] = stats

            self.total_matches += stats["total"]
            self.success_count += stats["success"]
            self.failed_count += stats["failed"]

        # 最终报告
        self._print_final_report(all_stats)

        return all_stats

    def _print_final_report(self, all_stats: dict[str, dict[str, int]]) -> None:
        """打印最终报告"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 历史数据回填完成")
        logger.info("=" * 60)
        logger.info(f"总任务数: {len(all_stats)}")
        logger.info(f"总比赛数: {self.total_matches}")
        logger.info(f"成功: {self.success_count}")
        logger.info(f"失败: {self.failed_count}")
        logger.info(f"跳过: {self.skipped_count} (未结束/取消)")

        # V26.7: 成功率只计算实际尝试的比赛（不包括跳过的）
        if self.total_matches > 0:
            success_rate = 100 * self.success_count / self.total_matches
            logger.info(f"成功率: {success_rate:.1f}% (基于 {self.total_matches} 场已结束比赛)")
        else:
            logger.info("成功率: N/A (无比赛数据)")

        # V26.7: 显示跳过比赛的原因说明
        if self.skipped_count > 0:
            logger.info("")
            logger.info("📌 跳过比赛说明:")
            logger.info("   这些比赛尚未结束或已取消，因此被自动过滤")
            logger.info("   未结束的比赛不会计入失败率，也不会触发哨兵停机")

        logger.info("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FotMob 历史数据回填工具 - V26.6"
    )

    parser.add_argument(
        "--league-id",
        type=int,
        help="指定联赛 ID（默认回填所有启用的联赛）"
    )

    parser.add_argument(
        "--years",
        type=int,
        help="回填年数（默认使用配置文件默认值）"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="每赛季最大采集数量（用于测试）"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干跑模式（不实际采集数据）"
    )

    parser.add_argument(
        "--no-sentry",
        action="store_true",
        help="禁用 V26.5 哨兵系统"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/global_harvest_list.yaml",
        help="配置文件路径"
    )

    args = parser.parse_args()

    # 创建回填引擎
    backfill = FotMobHistoricalBackfill(
        config_path=args.config,
        enable_sentry=not args.no_sentry,
        dry_run=args.dry_run,
    )

    # 执行回填
    try:
        backfill.backfill_all(league_id=args.league_id, years=args.years)
    except KeyboardInterrupt:
        logger.info("")
        logger.info("👋 收到中断信号，正在退出...")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ 回填失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
