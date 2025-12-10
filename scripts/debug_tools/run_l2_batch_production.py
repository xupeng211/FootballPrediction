#!/usr/bin/env python3
"""
L2批处理作业 - 生产版本
L2 Batch Job - Production Version
安全、可控的批量数据采集
"""

import asyncio
import logging
import sys
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

from src.jobs.run_l2_details import FotMobL2DetailsJob
from src.database.async_manager import get_db_session
from sqlalchemy import text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/l2_batch_production.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)

class ProductionL2BatchJob:
    """生产级L2批处理作业"""

    def __init__(self):
        self.logger = logger
        self.start_time = datetime.now()
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": self.start_time.isoformat(),
        }

    async def get_batch_stats(self) -> Dict[str, Any]:
        """获取当前批次统计信息"""
        try:
            async with get_db_session() as session:
                # 查询整体统计
                total_query = text("""
                    SELECT
                        COUNT(*) as total_matches,
                        COUNT(CASE WHEN data_completeness = 'partial' THEN 1 END) as pending_matches,
                        COUNT(CASE WHEN data_completeness = 'complete' THEN 1 END) as completed_matches,
                        COUNT(CASE WHEN stats_json IS NOT NULL THEN 1 END) as with_stats,
                        COUNT(CASE WHEN lineups_json IS NOT NULL THEN 1 END) as with_lineups,
                        COUNT(CASE WHEN environment_json IS NOT NULL THEN 1 END) as with_environment
                    FROM matches
                    WHERE fotmob_id IS NOT NULL
                """)

                result = await session.execute(total_query)
                row = result.fetchone()

                if row:
                    return {
                        "total_matches": row.total_matches,
                        "pending_matches": row.pending_matches,
                        "completed_matches": row.completed_matches,
                        "matches_with_stats": row.with_stats,
                        "matches_with_lineups": row.with_lineups,
                        "matches_with_environment": row.with_environment,
                        "completion_rate": round((row.completed_matches / row.total_matches) * 100, 2) if row.total_matches > 0 else 0
                    }

        except Exception as e:
            self.logger.error(f"❌ 获取批次统计失败: {e}")

        return {}

    async def estimate_completion_time(self, remaining_matches: int) -> str:
        """估算完成时间"""
        if self.stats["total_processed"] == 0:
            return "计算中..."

        elapsed = (datetime.now() - self.start_time).total_seconds()
        avg_time_per_match = elapsed / self.stats["total_processed"]

        estimated_seconds = remaining_matches * avg_time_per_match
        estimated_completion = datetime.now() + timedelta(seconds=estimated_seconds)

        return estimated_completion.strftime("%Y-%m-%d %H:%M:%S")

    async def run_production_job(self, max_matches: int = None):
        """运行生产级批处理作业"""
        try:
            self.logger.info("🚀 启动L2批处理作业 - 生产版本")
            self.logger.info(f"📅 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

            # 获取初始统计
            initial_stats = await self.get_batch_stats()
            self.logger.info("📊 初始数据库状态:")
            for key, value in initial_stats.items():
                self.logger.info(f"   {key}: {value}")

            # 初始化L2采集器作业
            l2_job = FotMobL2DetailsJob()

            # 设置合理的限制 (基于配置)
            limit = max_matches or 1000  # 默认每批次1000场
            self.logger.info(f"🎯 本批次处理上限: {limit} 场比赛")

            # 执行批处理
            await l2_job.run_job(limit=limit)

            # 获取最终统计
            final_stats = await self.get_batch_stats()
            self.logger.info("🎉 批处理作业完成!")
            self.logger.info("📊 最终数据库状态:")
            for key, value in final_stats.items():
                self.logger.info(f"   {key}: {value}")

            # 计算执行时间
            end_time = datetime.now()
            duration = end_time - self.start_time
            self.logger.info(f"⏱️ 总执行时间: {duration}")

        except Exception as e:
            self.logger.error(f"❌ 批处理作业失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def run_with_monitoring(self, max_matches: int = None, monitoring_interval: int = 60):
        """带监控的批处理运行"""
        self.logger.info("📡 启动监控模式...")

        # 启动监控任务
        monitor_task = asyncio.create_task(
            self.monitoring_loop(monitoring_interval)
        )

        try:
            # 运行主要作业
            await self.run_production_job(max_matches)
        finally:
            # 停止监控
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

    async def monitoring_loop(self, interval: int):
        """监控循环"""
        while True:
            try:
                await asyncio.sleep(interval)

                stats = await self.get_batch_stats()

                self.logger.info("📊 [监控] 实时进度:")
                self.logger.info(f"   总比赛: {stats.get('total_matches', 0)}")
                self.logger.info(f"   待处理: {stats.get('pending_matches', 0)}")
                self.logger.info(f"   已完成: {stats.get('completed_matches', 0)}")
                self.logger.info(f"   完成率: {stats.get('completion_rate', 0)}%")

                if stats.get('pending_matches', 0) > 0:
                    eta = await self.estimate_completion_time(stats['pending_matches'])
                    self.logger.info(f"   预计完成: {eta}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ 监控错误: {e}")

async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="L2批处理作业 - 生产版本")
    parser.add_argument("--max-matches", type=int, default=1000, help="最大处理比赛数 (默认: 1000)")
    parser.add_argument("--monitor", action="store_true", help="启用实时监控")
    parser.add_argument("--monitor-interval", type=int, default=60, help="监控间隔 (秒, 默认: 60)")

    args = parser.parse_args()

    # 创建批处理作业实例
    job = ProductionL2BatchJob()

    if args.monitor:
        await job.run_with_monitoring(
            max_matches=args.max_matches,
            monitoring_interval=args.monitor_interval
        )
    else:
        await job.run_production_job(max_matches=args.max_matches)

if __name__ == "__main__":
    asyncio.run(main())