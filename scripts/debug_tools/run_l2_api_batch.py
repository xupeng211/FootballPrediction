#!/usr/bin/env python3
"""
L2 API批处理作业 - 修复版本
L2 API Batch Job - Fixed Version
使用FotMob API采集器进行批量数据采集
"""

import asyncio
import logging
import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

from src.collectors.fotmob_api_collector import FotMobAPICollector, MatchDetailData
from src.database.async_manager import get_db_session, initialize_database
from sqlalchemy import text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/l2_api_batch.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)

class L2APIBatchJob:
    """L2 API批处理作业"""

    def __init__(self):
        self.logger = logger
        self.start_time = datetime.now()
        self.collector = None
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": self.start_time.isoformat(),
        }

    async def initialize(self):
        """初始化采集器"""
        try:
            # 初始化数据库
            await initialize_database()
            self.logger.info("✅ 数据库连接初始化完成")

            # 创建API采集器 (使用保守设置)
            self.collector = FotMobAPICollector(
                max_concurrent=6,          # 保守并发数
                timeout=45,                # 超时时间
                max_retries=3,             # 最大重试
                base_delay=2.0,            # 基础延迟
                enable_proxy=False,        # 禁用代理
                enable_jitter=True,        # 启用随机抖动
            )

            await self.collector.initialize()
            self.logger.info("✅ FotMob API采集器初始化完成")

        except Exception as e:
            self.logger.error(f"❌ 初始化失败: {e}")
            raise

    async def get_pending_matches(self, limit: int = 1000) -> list[str]:
        """获取待处理的比赛ID列表"""
        try:
            async with get_db_session() as session:
                query = text("""
                    SELECT fotmob_id
                    FROM matches
                    WHERE fotmob_id IS NOT NULL
                      AND data_completeness = 'partial'
                    ORDER BY match_date DESC NULLS LAST
                    LIMIT :limit
                """)

                result = await session.execute(query, {"limit": limit})
                matches = [row[0] for row in result.fetchall()]

                self.logger.info(f"📊 找到 {len(matches)} 场待处理的比赛")
                return matches

        except Exception as e:
            self.logger.error(f"❌ 获取待处理比赛失败: {e}")
            return []

    async def save_match_data(self, match_data: MatchDetailData) -> bool:
        """保存比赛数据到数据库"""
        try:
            async with get_db_session() as session:
                update_query = text("""
                    UPDATE matches SET
                        home_score = :home_score,
                        away_score = :away_score,
                        status = :status,
                        match_time = :match_time,
                        venue = :venue,
                        referee = :referee,
                        home_xg = :home_xg,
                        away_xg = :away_xg,
                        stats_json = :stats_json,
                        lineups_json = :lineups_json,
                        odds_snapshot_json = :odds_snapshot_json,
                        match_info = :match_info,
                        environment_json = :environment_json,
                        data_completeness = 'complete',
                        updated_at = :updated_at
                    WHERE fotmob_id = :fotmob_id
                """)

                await session.execute(update_query, {
                    "fotmob_id": match_data.fotmob_id,
                    "home_score": match_data.home_score,
                    "away_score": match_data.away_score,
                    "status": match_data.status,
                    "match_time": match_data.match_time,
                    "venue": match_data.venue,
                    "referee": match_data.referee,
                    "home_xg": match_data.xg_home,
                    "away_xg": match_data.xg_away,
                    "stats_json": match_data.stats_json,
                    "lineups_json": match_data.lineups_json,
                    "odds_snapshot_json": match_data.odds_snapshot_json,
                    "match_info": match_data.match_info,
                    "environment_json": match_data.environment_json,
                    "updated_at": datetime.now(),
                })

                await session.commit()
                return True

        except Exception as e:
            self.logger.error(f"❌ 保存比赛数据失败 {match_data.fotmob_id}: {e}")
            return False

    async def process_match(self, fotmob_id: str) -> bool:
        """处理单场比赛"""
        try:
            # 检查是否已经完成
            async with get_db_session() as session:
                check_query = text("""
                    SELECT data_completeness FROM matches
                    WHERE fotmob_id = :fotmob_id
                """)
                result = await session.execute(check_query, {"fotmob_id": fotmob_id})
                row = result.fetchone()

                if row and row[0] == 'complete':
                    self.logger.info(f"⏭️ 跳过已完成比赛: {fotmob_id}")
                    self.stats["skipped"] += 1
                    return True

            # 采集数据
            match_data = await self.collector.collect_match_details(fotmob_id)

            if match_data:
                # 保存数据
                success = await self.save_match_data(match_data)
                if success:
                    self.logger.info(f"✅ 成功处理: {fotmob_id}")
                    self.stats["successful"] += 1
                    return True
                else:
                    self.logger.error(f"❌ 保存失败: {fotmob_id}")
                    self.stats["failed"] += 1
                    return False
            else:
                self.logger.warning(f"⚠️ 数据采集失败: {fotmob_id}")
                self.stats["failed"] += 1
                return False

        except Exception as e:
            self.logger.error(f"❌ 处理比赛异常 {fotmob_id}: {e}")
            self.stats["failed"] += 1
            return False

    async def run_batch(self, limit: int = 1000):
        """运行批处理作业"""
        try:
            self.logger.info("🚀 启动L2 API批处理作业")
            self.logger.info(f"📅 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

            # 初始化
            await self.initialize()

            # 获取待处理比赛
            pending_matches = await self.get_pending_matches(limit)

            if not pending_matches:
                self.logger.info("ℹ️ 没有待处理的比赛")
                return

            self.logger.info(f"🎯 开始处理 {len(pending_matches)} 场比赛")

            # 批量处理
            for i, fotmob_id in enumerate(pending_matches, 1):
                self.stats["total_processed"] += 1

                # 显示进度
                if i % 10 == 0 or i == len(pending_matches):
                    progress = (i / len(pending_matches)) * 100
                    self.logger.info(f"📊 进度: {i}/{len(pending_matches)} ({progress:.1f}%)")

                # 处理比赛
                await self.process_match(fotmob_id)

                # 智能延迟
                if i < len(pending_matches):
                    delay = 1.5 + (i % 3) * 0.5  # 1.5-3秒随机延迟
                    await asyncio.sleep(delay)

            # 最终统计
            await self.print_final_stats()

        except Exception as e:
            self.logger.error(f"❌ 批处理作业失败: {e}")
            import traceback
            traceback.print_exc()
            raise

        finally:
            if self.collector:
                await self.collector.close()

    async def print_final_stats(self):
        """打印最终统计"""
        end_time = datetime.now()
        duration = end_time - self.start_time

        self.logger.info("🎉 批处理作业完成!")
        self.logger.info("="*50)
        self.logger.info(f"⏱️ 总执行时间: {duration}")
        self.logger.info(f"📊 总处理: {self.stats['total_processed']} 场")
        self.logger.info(f"✅ 成功: {self.stats['successful']} 场")
        self.logger.info(f"❌ 失败: {self.stats['failed']} 场")
        self.logger.info(f"⏭️ 跳过: {self.stats['skipped']} 场")

        if self.stats['total_processed'] > 0:
            success_rate = (self.stats['successful'] / self.stats['total_processed']) * 100
            self.logger.info(f"📈 成功率: {success_rate:.1f}%")

        # 显示采集器统计
        if self.collector:
            collector_stats = self.collector.get_stats()
            self.logger.info(f"🌐 API请求: {collector_stats.get('requests_made', 0)}")
            self.logger.info(f"📦 数据大小: {collector_stats.get('total_data_size', 0)} 字节")

async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="L2 API批处理作业")
    parser.add_argument("--max-matches", type=int, default=1000, help="最大处理比赛数 (默认: 1000)")

    args = parser.parse_args()

    # 创建并运行作业
    job = L2APIBatchJob()
    await job.run_batch(limit=args.max_matches)

if __name__ == "__main__":
    asyncio.run(main())
