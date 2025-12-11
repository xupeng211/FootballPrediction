#!/usr/bin/env python3
"""
L2 Worker 守护进程 - 企业级持续数据采集服务
L2 Worker Daemon - Enterprise-grade Continuous Data Collection Service

特性Features:
- 持续运行，自动重启
- 批量处理 + 智能休眠
- 资源限制保护
- 健康检查和错误恢复
- 可配置的并发控制
"""

import asyncio
import logging
import sys
import os
import json
import signal
from pathlib import Path
from typing import Any
from datetime import datetime

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.collectors.fotmob_api_collector import FotMobAPICollector
from src.database.async_manager import initialize_database, get_db_session
from sqlalchemy import text

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class L2WorkerDaemon:
    """L2 Worker 守护进程"""

    def __init__(self):
        self.running = True
        self.stats = {
            "start_time": datetime.now(),
            "total_processed": 0,
            "total_failed": 0,
            "last_batch_time": None,
            "consecutive_failures": 0,
            "batches_processed": 0,
        }
        self.config = self._load_config()
        self.collector = None

        # 注册信号处理
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _load_config(self) -> dict[str, Any]:
        """加载配置"""
        return {
            "batch_size": int(os.getenv("L2_WORKER_BATCH_SIZE", "20")),
            "sleep_interval": int(os.getenv("L2_WORKER_SLEEP_INTERVAL", "10")),
            "max_concurrent": int(os.getenv("L2_WORKER_MAX_CONCURRENT", "5")),
            "max_consecutive_failures": int(os.getenv("L2_WORKER_MAX_FAILURES", "10")),
            "health_check_interval": int(
                os.getenv("L2_WORKER_HEALTH_CHECK", "300")
            ),  # 5分钟
            "timeout": int(os.getenv("L2_WORKER_TIMEOUT", "30")),
            "base_delay": float(os.getenv("L2_WORKER_BASE_DELAY", "1.5")),
            "enable_jitter": os.getenv("L2_WORKER_JITTER", "true").lower() == "true",
        }

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"🛑 收到信号 {signum}，准备优雅关闭...")
        self.running = False

    async def initialize(self):
        """初始化服务"""
        try:
            logger.info("🚀 初始化L2 Worker守护进程")

            # 初始化数据库
            db_url = os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://postgres:postgres@db:5432/football_prediction",
            )
            initialize_database(db_url)
            logger.info("✅ 数据库连接初始化完成")

            # 初始化采集器
            self.collector = FotMobAPICollector(
                max_concurrent=self.config["max_concurrent"],
                timeout=self.config["timeout"],
                base_delay=self.config["base_delay"],
                enable_proxy=False,
                enable_jitter=self.config["enable_jitter"],
            )

            await self.collector.initialize()
            logger.info("✅ FotMob采集器初始化完成")

            # 输出配置信息
            logger.info("📋 Worker配置:")
            logger.info(f"   批量大小: {self.config['batch_size']}")
            logger.info(f"   休眠间隔: {self.config['sleep_interval']}秒")
            logger.info(f"   最大并发: {self.config['max_concurrent']}")
            logger.info(f"   健康检查: {self.config['health_check_interval']}秒")

        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            raise

    async def get_pending_matches(self, limit: int) -> list:
        """获取待处理的比赛"""
        async with get_db_session() as session:
            query = text("""
                SELECT fotmob_id, home_team_id, away_team_id
                FROM matches
                WHERE fotmob_id IS NOT NULL
                  AND home_xg IS NULL
                LIMIT :limit
            """)

            result = await session.execute(query, {"limit": limit})
            return result.fetchall()

    async def process_match_batch(self, matches: list) -> dict[str, int]:
        """处理一批比赛"""
        if not matches:
            return {"success": 0, "failed": 0}

        success_count = 0
        failed_count = 0

        logger.info(f"🔄 开始处理批次: {len(matches)} 场比赛")

        for i, (fotmob_id, _home_team_id, _away_team_id) in enumerate(matches, 1):
            if not self.running:
                logger.info("🛑 收到停止信号，中断批次处理")
                break

            try:
                logger.info(f"📊 [{i}/{len(matches)}] 处理: {fotmob_id}")

                # 采集数据
                match_data = await self.collector.collect_match_details(fotmob_id)

                if match_data:
                    # 更新数据库
                    await self._update_match_data(fotmob_id, match_data)

                    logger.info(
                        f"✅ 成功: {fotmob_id} - xG: {match_data.xg_home} vs {match_data.xg_away}"
                    )
                    success_count += 1
                else:
                    logger.warning(f"⚠️ 失败: {fotmob_id} - 数据采集失败")
                    failed_count += 1

            except Exception as e:
                logger.error(f"❌ 处理失败 {fotmob_id}: {e}")
                failed_count += 1

            # 智能延迟
            if i < len(matches):
                delay = self.config["base_delay"] + (i % 3) * 0.3
                await asyncio.sleep(delay)

        self.stats["total_processed"] += success_count
        self.stats["total_failed"] += failed_count
        self.stats["last_batch_time"] = datetime.now()
        self.stats["batches_processed"] += 1

        # 更新连续失败计数
        if success_count == 0:
            self.stats["consecutive_failures"] += 1
        else:
            self.stats["consecutive_failures"] = 0

        logger.info(f"📊 批次完成: 成功 {success_count}, 失败 {failed_count}")

        return {"success": success_count, "failed": failed_count}

    async def _update_match_data(self, fotmob_id: str, match_data):
        """更新比赛数据到数据库"""
        async with get_db_session() as session:
            update_query = text("""
                UPDATE matches SET
                    home_xg = :home_xg,
                    away_xg = :away_xg,
                    home_score = :home_score,
                    away_score = :away_score,
                    status = :status,
                    venue = :venue,
                    referee = :referee,
                    stats_json = :stats_json,
                    lineups_json = :lineups_json,
                    environment_json = :environment_json,
                    data_completeness = 'complete',
                    updated_at = NOW()
                WHERE fotmob_id = :fotmob_id
            """)

            await session.execute(
                update_query,
                {
                    "fotmob_id": fotmob_id,
                    "home_xg": match_data.xg_home,
                    "away_xg": match_data.xg_away,
                    "home_score": match_data.home_score,
                    "away_score": match_data.away_score,
                    "status": match_data.status,
                    "venue": match_data.venue,
                    "referee": match_data.referee,
                    "stats_json": json.dumps(match_data.stats_json)
                    if match_data.stats_json
                    else None,
                    "lineups_json": json.dumps(match_data.lineups_json)
                    if match_data.lineups_json
                    else None,
                    "environment_json": json.dumps(match_data.environment_json)
                    if match_data.environment_json
                    else None,
                },
            )

            await session.commit()

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with get_db_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"❌ 健康检查失败: {e}")
            return False

    async def get_database_stats(self) -> dict[str, Any]:
        """获取数据库统计信息"""
        async with get_db_session() as session:
            # 总体统计
            total_query = text("""
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(CASE WHEN home_xg IS NOT NULL THEN 1 END) as l2_completed,
                    COUNT(CASE WHEN home_xg IS NULL THEN 1 END) as l2_pending
                FROM matches
                WHERE fotmob_id IS NOT NULL
            """)

            result = await session.execute(total_query)
            stats = result.fetchone()

            return {
                "total_matches": stats.total_matches,
                "l2_completed": stats.l2_completed,
                "l2_pending": stats.l2_pending,
                "completion_rate": round(
                    stats.l2_completed * 100.0 / stats.total_matches, 2
                )
                if stats.total_matches > 0
                else 0,
            }

    def print_status(self):
        """打印状态信息"""
        uptime = datetime.now() - self.stats["start_time"]

        logger.info("=" * 60)
        logger.info("📊 L2 Worker 守护进程状态")
        logger.info("=" * 60)
        logger.info(f"⏱️  运行时间: {uptime}")
        logger.info(f"📦 处理批次: {self.stats['batches_processed']}")
        logger.info(f"✅ 总成功: {self.stats['total_processed']}")
        logger.info(f"❌ 总失败: {self.stats['total_failed']}")
        logger.info(f"🔄 连续失败: {self.stats['consecutive_failures']}")

        if self.stats["last_batch_time"]:
            time_since_batch = datetime.now() - self.stats["last_batch_time"]
            logger.info(f"⏰ 上次批次: {time_since_batch} ago")

    async def run(self):
        """主运行循环"""
        logger.info("🚀 L2 Worker守护进程启动")

        last_health_check = datetime.now()

        try:
            while self.running:
                try:
                    # 健康检查
                    if (datetime.now() - last_health_check).seconds > self.config[
                        "health_check_interval"
                    ]:
                        if not await self.health_check():
                            logger.error("❌ 健康检查失败，等待重试...")
                            await asyncio.sleep(60)  # 等待1分钟后重试
                            continue
                        last_health_check = datetime.now()

                    # 检查连续失败次数
                    if (
                        self.stats["consecutive_failures"]
                        >= self.config["max_consecutive_failures"]
                    ):
                        logger.error(
                            f"❌ 连续失败次数过多 ({self.stats['consecutive_failures']})，延长等待时间"
                        )
                        await asyncio.sleep(300)  # 等待5分钟
                        continue

                    # 获取待处理比赛
                    matches = await self.get_pending_matches(self.config["batch_size"])

                    if matches:
                        # 处理批次
                        await self.process_match_batch(matches)

                        # 打印进度
                        db_stats = await self.get_database_stats()
                        logger.info(
                            f"📈 数据库进度: {db_stats['l2_completed']}/{db_stats['total_matches']} "
                            f"({db_stats['completion_rate']}%)"
                        )

                    else:
                        logger.info("🎯 没有待处理的比赛，休眠...")

                    # 休眠
                    await asyncio.sleep(self.config["sleep_interval"])

                except Exception as e:
                    logger.error(f"❌ 运行循环错误: {e}")
                    self.stats["consecutive_failures"] += 1
                    await asyncio.sleep(60)  # 错误后等待1分钟

        except KeyboardInterrupt:
            logger.info("🛑 用户中断")
        except Exception as e:
            logger.error(f"💥 致命错误: {e}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        """清理资源"""
        logger.info("🧹 清理资源...")

        if self.collector:
            await self.collector.close()

        # 最终状态报告
        self.print_status()

        logger.info("✅ L2 Worker守护进程已停止")


async def main():
    """主函数"""
    daemon = L2WorkerDaemon()

    try:
        await daemon.initialize()
        await daemon.run()
    except Exception as e:
        logger.error(f"💥 守护进程失败: {e}")
        sys.exit(1)

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("🛑 用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 程序异常: {e}")
        sys.exit(1)
