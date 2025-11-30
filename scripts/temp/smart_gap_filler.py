#!/usr/bin/env python3
"""
智能数据补漏系统 - Smart Gap Filler
Data Operations Engineer: 修复966天数据空缺，支持未来Elo计算

核心策略：安全慢速采集，智能错误处理，进度实时监控
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
import traceback
import sys
import signal

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/app/gap_fill.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class SmartGapFiller:
    """智能数据补漏系统 - 专注于安全高效的数据空缺修复"""

    def __init__(self):
        # 数据库连接配置
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction",
        )
        self.engine = create_async_engine(
            database_url.replace("postgresql://", "postgresql+asyncpg://"),
            echo=False,
            pool_size=5,
            max_overflow=10,
        )
        self.AsyncSessionLocal = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        # 补漏配置
        self.start_date = date(2022, 1, 1)  # 从2022年开始补漏
        self.end_date = datetime.now().date()  # 到今天
        self.min_sleep = 8  # 最小等待时间（秒）
        self.max_sleep = 15  # 最大等待时间（秒）
        self.max_retries = 3  # 最大重试次数
        self.batch_size = 10  # 每次处理的天数

        # 运行状态
        self.is_running = True
        self.processed_dates = 0
        self.successful_fills = 0
        self.failed_attempts = 0

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """信号处理器 - 优雅关闭"""
        logger.info(f"🛑 收到信号 {signum}，准备优雅关闭...")
        self.is_running = False

    async def close(self):
        """关闭数据库连接"""
        await self.engine.dispose()

    async def get_async_session(self) -> AsyncSession:
        """获取数据库会话"""
        async with self.AsyncSessionLocal() as session:
            yield session

    async def get_existing_match_dates(self) -> list[date]:
        """获取已有比赛数据的日期"""
        logger.info("📅 查询现有比赛数据日期...")

        async with self.AsyncSessionLocal() as session:
            query = text("""
                SELECT DISTINCT DATE(match_date) as match_day
                FROM matches
                WHERE match_date IS NOT NULL
                ORDER BY match_day
            """)

            result = await session.execute(query)
            dates = [row.match_day for row in result.fetchall()]

            logger.info(f"✅ 发现 {len(dates)} 天有比赛数据")
            return dates

    async def get_gap_dates(self, existing_dates: list[date]) -> list[date]:
        """识别数据空缺的日期"""
        logger.info("🔍 识别数据空缺日期...")

        # 生成完整日期范围
        full_date_range = []
        current_date = self.start_date
        while current_date <= self.end_date:
            full_date_range.append(current_date)
            current_date += timedelta(days=1)

        # 找出空缺日期
        existing_set = set(existing_dates)
        gap_dates = [d for d in full_date_range if d not in existing_set]

        logger.info(f"🎯 发现 {len(gap_dates)} 个数据空缺日期")
        return gap_dates

    async def check_date_data_quality(self, target_date: date) -> dict[str, Any]:
        """检查指定日期的数据质量"""
        logger.debug(f"🔍 检查 {target_date} 的数据质量...")

        async with self.AsyncSessionLocal() as session:
            query = text("""
                SELECT
                    COUNT(*) as match_count,
                    COUNT(DISTINCT league_id) as unique_leagues,
                    MIN(match_date) as earliest_time,
                    MAX(match_date) as latest_time
                FROM matches
                WHERE DATE(match_date) = :target_date
            """)

            result = await session.execute(query, {"target_date": target_date})
            row = result.fetchone()

            return {
                "match_count": row.match_count or 0,
                "unique_leagues": row.unique_leagues or 0,
                "has_data": row.match_count > 0,
                "earliest_time": row.earliest_time,
                "latest_time": row.latest_time,
            }

    async def trigger_fotmob_collection_for_date(self, target_date: date) -> bool:
        """为指定日期触发FotMob数据采集"""
        logger.info(f"🚀 为 {target_date} 触发FotMob数据采集...")

        try:
            # 导入数据采集任务
            from src.tasks.data_collection_tasks import collect_fotmob_data

            # 准备日期参数 (YYYYMMDD格式)
            date_str = target_date.strftime("%Y%m%d")

            # 调用Celery任务
            task = collect_fotmob_data.delay(date=date_str)

            logger.info(f"📤 已提交 {target_date} 的数据采集任务: {task.id}")

            # 等待任务完成（最多等待10分钟）
            try:
                result = task.get(timeout=600)  # 10分钟超时
                logger.info(f"✅ {target_date} 数据采集完成: {result}")
                return True
            except Exception:
                logger.error(f"❌ {target_date} 数据采集超时或失败: {e}")
                return False

        except ImportError as e:
            logger.error(f"❌ 无法导入数据采集模块: {e}")
            return False
        except Exception:
            logger.error(f"❌ {target_date} 采集触发失败: {e}")
            return False

    async def verify_data_filling(self, target_date: date) -> bool:
        """验证数据填补是否成功"""
        logger.debug(f"🔍 验证 {target_date} 数据填补结果...")

        quality_info = await self.check_date_data_quality(target_date)

        if quality_info["has_data"]:
            logger.info(
                f"✅ {target_date} 数据填补成功: {quality_info['match_count']}场比赛"
            )
            return True
        else:
            logger.warning(f"⚠️ {target_date} 数据填补后仍无数据")
            return False

    async def safe_fill_single_date(
        self, target_date: date, retry_count: int = 0
    ) -> bool:
        """安全地填补单个日期的数据"""
        logger.info(
            f"🔧 开始填补 {target_date} 数据 (尝试 {retry_count + 1}/{self.max_retries})"
        )

        try:
            # 1. 检查当前数据状态
            current_quality = await self.check_date_data_quality(target_date)
            if current_quality["has_data"]:
                logger.info(
                    f"ℹ️ {target_date} 已有数据 ({current_quality['match_count']}场)，跳过"
                )
                return True

            # 2. 触发数据采集
            collection_success = await self.trigger_fotmob_collection_for_date(
                target_date
            )

            if collection_success:
                # 3. 等待一段时间让数据写入数据库
                await asyncio.sleep(random.uniform(3, 6))

                # 4. 验证数据填补结果
                fill_success = await self.verify_data_filling(target_date)

                if fill_success:
                    self.successful_fills += 1
                    logger.info(f"🎉 {target_date} 数据填补成功!")
                    return True
                else:
                    logger.warning(f"⚠️ {target_date} 数据采集成功但验证失败")
            else:
                logger.warning(f"⚠️ {target_date} 数据采集失败")

            # 5. 重试逻辑
            if retry_count < self.max_retries - 1:
                wait_time = random.uniform(30, 60) * (retry_count + 1)  # 递增等待时间
                logger.info(f"🔄 {retry_count + 1}秒后重试 {target_date}...")
                await asyncio.sleep(wait_time)
                return await self.safe_fill_single_date(target_date, retry_count + 1)
            else:
                logger.error(f"💀 {target_date} 达到最大重试次数，放弃")
                self.failed_attempts += 1
                return False

        except Exception:
            logger.error(f"💥 {target_date} 填补过程异常: {traceback.format_exc()}")

            if retry_count < self.max_retries - 1:
                wait_time = random.uniform(60, 120) * (retry_count + 1)
                logger.info(f"🔄 异常重试 {retry_count + 1}秒后重试 {target_date}...")
                await asyncio.sleep(wait_time)
                return await self.safe_fill_single_date(target_date, retry_count + 1)
            else:
                logger.error(f"💀 {target_date} 异常达到最大重试次数，放弃")
                self.failed_attempts += 1
                return False

    async def process_batch_dates(self, date_batch: list[date]) -> dict[str, int]:
        """处理一批日期的数据填补"""
        logger.info(
            f"📦 处理日期批次: {date_batch[0]} 至 {date_batch[-1]} ({len(date_batch)}天)"
        )

        batch_results = {"success": 0, "failed": 0, "skipped": 0}

        for i, target_date in enumerate(date_batch):
            if not self.is_running:
                logger.info("🛑 收到停止信号，结束批次处理")
                break

            logger.info(f"🎯 处理进度: {i + 1}/{len(date_batch)} - {target_date}")

            # 检查是否已有数据
            current_quality = await self.check_date_data_quality(target_date)
            if current_quality["has_data"]:
                logger.info(f"⏭️ {target_date} 已有数据，跳过")
                batch_results["skipped"] += 1
                continue

            # 执行数据填补
            success = await self.safe_fill_single_date(target_date)

            if success:
                batch_results["success"] += 1
            else:
                batch_results["failed"] += 1

            self.processed_dates += 1

            # 安全等待 - 避免请求过于频繁
            if i < len(date_batch) - 1:  # 不是最后一个
                sleep_time = random.uniform(self.min_sleep, self.max_sleep)
                logger.info(f"😴 等待 {sleep_time:.1f}秒后处理下一天...")
                await asyncio.sleep(sleep_time)

        return batch_results

    async def execute_gap_filling(self):
        """执行完整的数据填补流程"""
        logger.info("🚀 启动智能数据补漏系统...")
        logger.info(f"📅 目标日期范围: {self.start_date} 至 {self.end_date}")
        logger.info(
            f"⚙️ 安全配置: 等待时间 {self.min_sleep}-{self.max_sleep}秒, 最大重试 {self.max_retries}次"
        )

        try:
            # 1. 获取现有数据日期
            existing_dates = await self.get_existing_match_dates()

            # 2. 识别空缺日期
            gap_dates = await self.get_gap_dates(existing_dates)

            if not gap_dates:
                logger.info("🎉 未发现数据空缺，系统运行正常!")
                return

            logger.info(f"🎯 需要填补 {len(gap_dates)} 个空缺日期")

            # 3. 按批次处理
            total_batches = (len(gap_dates) + self.batch_size - 1) // self.batch_size

            for batch_num in range(total_batches):
                if not self.is_running:
                    logger.info("🛑 收到停止信号，结束数据填补")
                    break

                start_idx = batch_num * self.batch_size
                end_idx = min((batch_num + 1) * self.batch_size, len(gap_dates))
                batch_dates = gap_dates[start_idx:end_idx]

                logger.info(f"🔄 处理批次 {batch_num + 1}/{total_batches}")

                # 处理当前批次
                batch_results = await self.process_batch_dates(batch_dates)

                # 批次间休息时间
                if batch_num < total_batches - 1 and self.is_running:
                    batch_sleep = random.uniform(self.min_sleep * 2, self.max_sleep * 2)
                    logger.info(f"🛌 批次间休息 {batch_sleep:.1f}秒...")
                    await asyncio.sleep(batch_sleep)

            # 4. 生成最终报告
            await self.generate_final_report()

        except Exception:
            logger.error(f"💥 数据填补系统异常: {traceback.format_exc()}")
            raise
        finally:
            await self.close()

    async def generate_final_report(self):
        """生成最终报告"""
        logger.info("📊 生成数据填补最终报告...")

        # 重新检查数据质量
        current_dates = await self.get_existing_match_dates()
        gap_dates = await self.get_gap_dates(current_dates)

        report = {
            "timestamp": datetime.now().isoformat(),
            "processed_dates": self.processed_dates,
            "successful_fills": self.successful_fills,
            "failed_attempts": self.failed_attempts,
            "remaining_gaps": len(gap_dates),
            "total_dates_with_data": len(current_dates),
            "data_coverage_percentage": (
                len(current_dates) / ((self.end_date - self.start_date).days + 1)
            )
            * 100,
            "success_rate": (self.successful_fills / max(self.processed_dates, 1))
            * 100,
        }

        logger.info("=" * 80)
        logger.info("📊 数据填补系统最终报告")
        logger.info("=" * 80)
        logger.info(f"📅 处理日期总数: {report['processed_dates']}")
        logger.info(f"✅ 成功填补: {report['successful_fills']}")
        logger.info(f"❌ 失败次数: {report['failed_attempts']}")
        logger.info(f"🕳️ 剩余空缺: {report['remaining_gaps']}")
        logger.info(f"📈 数据覆盖率: {report['data_coverage_percentage']:.1f}%")
        logger.info(f"🎯 成功率: {report['success_rate']:.1f}%")
        logger.info("=" * 80)

        # 保存报告到文件
        with open("/app/gap_fill_report.json", "w", encoding="utf-8") as f:
            import json

            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info("📋 报告已保存至: /app/gap_fill_report.json")


async def main():
    """主函数"""
    logger.info("🚀 智能数据补漏系统启动")
    logger.info("🎯 目标: 修复966天数据空缺，支持Elo计算")
    logger.info("🛡️ 安全第一: 慢速采集，智能重试，优雅关闭")

    filler = SmartGapFiller()

    try:
        await filler.execute_gap_filling()
        logger.info("🎉 数据补漏系统完成!")
    except KeyboardInterrupt:
        logger.info("🛑 用户中断，系统优雅关闭")
    except Exception:
        logger.error(f"💥 系统异常退出: {e}")
        raise
    finally:
        logger.info("👋 智能数据补漏系统退出")


if __name__ == "__main__":
    asyncio.run(main())
