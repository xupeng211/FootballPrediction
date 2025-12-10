#!/usr/bin/env python3
"""
修复版FotMob L2 详情采集任务
Chief Reverse Engineer - 专门解决数据提取问题

基于现场取证结果，修复数据保存逻辑，确保xG、赔率、射门等高级特征正确保存到数据库
"""

import asyncio
import logging
import sys
import random
import time
from datetime import datetime
import json
from typing import Optional,  Any, 
from pathlib import Path

# 添加项目根路径 - 标准化导入
sys.path.append(str(Path(__file__).parent.parent.parent))

# 配置日志 - 标准化路径
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/l2_details_fixed.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

# 使用修复版采集器
from src.data.collectors.fotmob_browser_fixed import FotmobFixedScraper
from src.database.async_manager import get_db_session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class FotMobL2DetailsFixedJob:
    """修复版FotMob L2 详情采集任务"""

    def __init__(self):
        self.logger = logger

    async def get_pending_matches(self, limit: int = 50) -> list[str]:
        """获取待处理的比赛ID列表"""
        async with get_db_session() as session:
            query = text(
                """
                SELECT fotmob_id
                FROM matches
                WHERE data_completeness = 'partial'
                AND data_source = 'fotmob_v2'
                AND fotmob_id IS NOT NULL
                ORDER BY match_date DESC
                LIMIT :limit
            """
            )

            result = await session.execute(query, {"limit": limit})
            return [row[0] for row in result.fetchall()]

    async def process_match_details(self, fotmob_id: str) -> bool:
        """
        处理单场比赛详情 - 修复版

        关键改进：使用正确的数据结构和保存逻辑
        """
        try:
            self.logger.info(f"🔍 处理比赛详情: {fotmob_id}")

            # 使用修复版采集器
            async with FotmobFixedScraper() as scraper:
                match_data = await scraper.scrape_match_details(fotmob_id)

                if not match_data:
                    self.logger.warning(f"⚠️ 未获取到比赛详情: {fotmob_id}")
                    return False

                # 保存到数据库
                success = await self.save_match_details_to_db(fotmob_id, match_data)

                if success:
                    # 更新比赛完整性状态
                    await self.mark_match_complete(fotmob_id)
                    self.logger.info(f"✅ 比赛详情处理完成: {fotmob_id}")

                    # 打印关键数据用于验证
                    self.print_match_summary(fotmob_id, match_data)
                    return True
                else:
                    self.logger.warning(f"⚠️ 比赛详情保存失败: {fotmob_id}")
                    return False

        except Exception as e:
            self.logger.error(f"❌ 处理比赛详情失败 {fotmob_id}: {e}")
            return False

    def print_match_summary(self, fotmob_id: str, match_data):
        """打印比赛数据摘要用于验证"""
        shots = match_data.shots or []
        stats = match_data.stats or {}
        odds = match_data.odds or {}
        lineups = match_data.lineups or {}

        print(f"\n🎯 比赛 {fotmob_id} 数据摘要:")
        print(
            f"   比赛: {match_data.home_team} {match_data.home_score}-{match_data.away_score} {match_data.away_team}"
        )
        print(f"   🎯 射门数据: {len(shots)} 次")
        print(
            f"   📈 xG数据: 主队 {stats.get('home_xg', 0):.2f}, 客队 {stats.get('away_xg', 0):.2f}"
        )
        print(
            f"   👥 阵容数据: 主队 {len(lineups.get('home', {}).get('players', []))} 人, 客队 {len(lineups.get('away', {}).get('players', []))} 人"
        )
        print(f"   💰 赔率数据: {len(odds.get('providers', []))} 个提供商")

        # 显示前3个射门样本
        if shots:
            print("   🔍 射门样本 (前3次):")
            for i, shot in enumerate(shots[:3], 1):
                print(
                    f"      {i}. 第{shot.get('minute', 0)}分钟 - {shot.get('player', 'Unknown')} ({shot.get('team', 'unknown')}) - xG: {shot.get('xg', 0):.3f}"
                )

    async def save_match_details_to_db(self, fotmob_id: str, match_data) -> bool:
        """保存比赛详情到数据库 - 修复版"""
        try:
            async with get_db_session() as session:
                # 准备要更新的数据
                stats_data = match_data.stats or {}
                lineup_data = match_data.lineups or {}
                odds_data = match_data.odds or {}
                shots_data = match_data.shots or []

                # 构建统计JSON
                stats_json = {
                    "possession": stats_data.get("possession", {}),
                    "shots": stats_data.get("shots", {}),
                    "passes": stats_data.get("passes", {}),
                    "corners": stats_data.get("corners", {}),
                    "home_xg": stats_data.get("home_xg", 0.0),
                    "away_xg": stats_data.get("away_xg", 0.0),
                    "total_xg": stats_data.get("total_xg", 0.0),
                }

                # 构建阵容JSON
                lineup_json = {
                    "home": lineup_data.get("home", {}),
                    "away": lineup_data.get("away", {}),
                }

                # 构建赔率JSON
                odds_json = {
                    "providers": odds_data.get("providers", []),
                    "bet365": odds_data.get("bet365", {}),
                    "williamHill": odds_data.get("williamHill", {}),
                    "raw_data": odds_data.get("raw_data", {}),
                }

                # 构建比赛元数据JSON
                metadata_json = {
                    "home_xg": stats_data.get("home_xg", 0.0),
                    "away_xg": stats_data.get("away_xg", 0.0),
                    "total_shots": len(shots_data),
                    "referee": "Unknown",  # 可以从match_data中提取
                    "venue": "Unknown",  # 可以从match_data中提取
                    "weather": {},  # 可以从match_data中提取
                    "shot_count": len(shots_data),
                    "lineup_players": len(
                        lineup_json.get("home", {}).get("players", [])
                    )
                    + len(lineup_json.get("away", {}).get("players", [])),
                }

                # 更新数据库记录
                update_query = text(
                    """
                    UPDATE matches
                    SET
                        stats = :stats,
                        lineups = :lineups,
                        odds = :odds,
                        match_metadata = :metadata,
                        updated_at = :updated_at
                    WHERE fotmob_id = :fotmob_id
                """
                )

                await session.execute(
                    update_query,
                    {
                        "fotmob_id": fotmob_id,
                        "stats": json.dumps(stats_json),
                        "lineups": json.dumps(lineup_json),
                        "odds": json.dumps(odds_json),
                        "metadata": json.dumps(metadata_json),
                        "updated_at": datetime.now(),
                    },
                )

                self.logger.info(f"✅ 保存比赛详情成功: {fotmob_id}")
                self.logger.info(f"   📊 统计数据: {len(json.dumps(stats_json))} 字符")
                self.logger.info(f"   👥 阵容数据: {len(json.dumps(lineup_json))} 字符")
                self.logger.info(f"   💰 赔率数据: {len(json.dumps(odds_json))} 字符")
                self.logger.info(f"   🎯 射门数据: {len(shots_data)} 次")

                return True

        except Exception as e:
            self.logger.error(f"❌ 保存比赛详情失败 {fotmob_id}: {e}")
            return False

    async def mark_match_complete(self, fotmob_id: str):
        """标记比赛数据完整"""
        try:
            async with get_db_session() as session:
                update_query = text(
                    """
                    UPDATE matches
                    SET data_completeness = 'complete',
                        updated_at = :updated_at
                    WHERE fotmob_id = :fotmob_id
                """
                )

                await session.execute(
                    update_query, {"updated_at": datetime.now(), "fotmob_id": fotmob_id}
                )

        except Exception as e:
            self.logger.error(f"❌ 标记比赛完整失败 {fotmob_id}: {e}")

    async def run_job(self):
        """运行修复版L2详情采集任务"""
        try:
            self.logger.info("🚀 启动修复版FotMob L2详情采集任务")

            # 获取待处理的比赛
            pending_matches = await self.get_pending_matches(limit=10)  # 先测试10个
            self.logger.info(f"📊 找到 {len(pending_matches)} 场待处理的比赛")

            if not pending_matches:
                self.logger.info("ℹ️ 没有待处理的比赛，任务完成")
                return

            success_count = 0
            total_count = len(pending_matches)

            for i, fotmob_id in enumerate(pending_matches, 1):
                self.logger.info(f"🔄 处理进度: {i}/{total_count}")

                try:
                    success = await self.process_match_details(fotmob_id)
                    if success:
                        success_count += 1

                    # 智能延迟
                    delay = random.uniform(1.0, 3.0)
                    if i < total_count:
                        await asyncio.sleep(delay)

                except Exception as e:
                    self.logger.error(f"❌ 处理比赛 {fotmob_id} 时发生异常: {e}")
                    continue

            completion_rate = (
                (success_count / total_count) * 100 if total_count > 0 else 0
            )
            self.logger.info(
                f"🎉 修复版L2详情采集完成: {success_count}/{total_count} ({completion_rate:.1f}%)"
            )

        except Exception as e:
            self.logger.error(f"❌ L2详情采集失败: {e}")
            raise


async def main():
    """主函数"""
    job = FotMobL2DetailsFixedJob()
    await job.run_job()


if __name__ == "__main__":
    asyncio.run(main())
