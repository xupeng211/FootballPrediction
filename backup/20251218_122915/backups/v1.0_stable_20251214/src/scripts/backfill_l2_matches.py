#!/usr/bin/env python3
"""
生产级L2数据回填脚本 - Production Release
Production-Grade L2 Data Backfill Script

用于批量抓取历史比赛L2详情数据，支持：
- 流式处理避免内存溢出
- 并发控制防止服务器过载
- 实时进度监控和日志记录
- 优雅停机和断点续传
- 失败重试和错误隔离
- HTTP压缩数据处理
- JSON序列化错误修复

作者: L2重构团队
创建时间: 2025-12-10
版本: 1.0.0 (Production Release)
"""

import asyncio
import csv
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional, Set, Tuple
from dataclasses import dataclass, field

import aiofiles
import tqdm

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.collectors.l2_fetcher import L2Fetcher, L2FetchError
from src.collectors.l2_parser import L2Parser
from src.schemas.l2_schemas import L2MatchData


@dataclass
class BackfillConfig:
    """回填配置"""

    # 并发控制
    max_concurrent: int = 15
    batch_size: int = 1000  # 每批读取的match_ids数量
    request_timeout: float = 30.0
    max_retries: int = 5

    # 文件路径
    input_file: str = "data/l2_backfill_queue.csv"
    output_dir: str = "data/l2_output"
    log_file: str = "logs/backfill.log"
    failed_ids_file: str = "logs/failed_ids.txt"

    # 控制参数
    enable_progress_bar: bool = True
    save_interval: int = 10  # 每10个成功保存一次进度
    rate_limit_delay: float = 0.1  # 请求间隔（秒）


@dataclass
class BackfillStats:
    """回填统计信息"""

    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        """成功率"""
        return (self.successful / max(self.total_processed, 1)) * 100

    @property
    def elapsed_time(self) -> float:
        """已用时间（秒）"""
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def processing_rate(self) -> float:
        """处理速率（个/秒）"""
        return self.total_processed / max(self.elapsed_time, 1)


class BackfillManager:
    """
    L2数据回填管理器 - 生产版本

    负责批量处理比赛数据的L2详情抓取，具备流式处理、
    并发控制、错误恢复和进度监控等功能。
    """

    def __init__(self, config: Optional[BackfillConfig] = None):
        """
        初始化回填管理器

        Args:
            config: 回填配置，如果为None则使用默认配置
        """
        self.config = config or BackfillConfig()
        self.stats = BackfillStats()

        # 运行时状态
        self._running = False
        self._shutdown_requested = False
        self._processed_ids: Set[str] = set()
        self._failed_ids: Set[str] = set()

        # 组件初始化
        self._setup_logging()
        self._setup_directories()

        # 延迟初始化（在async环境中）
        self._fetcher: Optional[L2Fetcher] = None
        self._parser: Optional[L2Parser] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

        # 注册信号处理器
        self._setup_signal_handlers()

        self.logger.info("BackfillManager initialized with config: %s", self.config)

    def _setup_logging(self) -> None:
        """设置日志配置"""
        # 确保日志目录存在
        log_dir = Path(self.config.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # 配置日志格式
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(self.config.log_file, encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ],
        )

        self.logger = logging.getLogger(__name__)

        # 减少第三方库日志噪音
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("tenacity").setLevel(logging.WARNING)

    def _setup_directories(self) -> None:
        """创建必要的目录"""
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.failed_ids_file).parent.mkdir(parents=True, exist_ok=True)

    def _setup_signal_handlers(self) -> None:
        """设置信号处理器，支持优雅停机"""

        def signal_handler(signum, frame):
            self.logger.info(
                "Received signal %d, initiating graceful shutdown...", signum
            )
            self._shutdown_requested = True
            self._running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def _initialize_components(self) -> None:
        """在异步环境中初始化组件"""
        if not self._fetcher:
            from src.collectors.rate_limiter import RateLimiter

            # 创建依赖组件（简化版本，实际使用中可能需要具体配置）
            rate_limiter = RateLimiter()

            self._fetcher = L2Fetcher(
                timeout=self.config.request_timeout,
                max_retries=self.config.max_retries,
                rate_limiter=rate_limiter,
            )

            # L2Fetcher 使用延迟初始化，无需显式调用 initialize()

        if not self._parser:
            self._parser = L2Parser(strict_mode=False)

        if not self._semaphore:
            self._semaphore = asyncio.Semaphore(self.config.max_concurrent)

    async def _read_match_ids_stream(self) -> AsyncGenerator[str, None]:
        """
        流式读取match_ids，避免内存溢出

        Yields:
            str: match_id
        """
        self.logger.info("Reading match IDs from %s", self.config.input_file)

        try:
            async with aiofiles.open(
                self.config.input_file, "r", encoding="utf-8"
            ) as file:
                # 读取并跳过标题行
                header_line = await file.readline()
                self.logger.debug("CSV header: %s", header_line.strip())

                batch_count = 0
                async for line in file:
                    if self._shutdown_requested:
                        break

                    line = line.strip()
                    if not line:
                        continue

                    # 手动解析CSV（简单情况，只有一列）
                    match_id = line.split(",")[0].strip().strip("\"'")

                    if match_id and match_id not in self._processed_ids:
                        yield match_id
                        batch_count += 1

                        # 每批记录日志
                        if batch_count % self.config.batch_size == 0:
                            self.logger.info(
                                "Read %d match IDs so far (batch %d)",
                                batch_count,
                                batch_count // self.config.batch_size,
                            )

        except FileNotFoundError:
            self.logger.error("Input file not found: %s", self.config.input_file)
            raise
        except Exception as e:
            self.logger.error("Error reading match IDs: %s", e)
            raise

    async def _process_single_match(
        self, match_id: str
    ) -> Tuple[bool, Optional[L2MatchData]]:
        """
        处理单个比赛数据

        Args:
            match_id: 比赛ID

        Returns:
            Tuple[bool, Optional[L2MatchData]]: (成功标志, 解析后的数据)
        """
        async with self._semaphore:  # 控制并发数
            if self._shutdown_requested:
                return False, None

            try:
                # 获取原始数据
                raw_data = await self._fetcher.fetch_match_details(match_id)

                # 解析数据
                result = self._parser.parse_match_data(raw_data)

                if result.success:
                    self.logger.debug("Successfully processed match %s", match_id)
                    return True, result.data
                else:
                    self.logger.warning(
                        "Failed to parse match %s: %s", match_id, result.error_message
                    )
                    return False, None

            except L2FetchError as e:
                self.logger.error(
                    "Fetch error for match %s (status=%s): %s",
                    match_id,
                    e.status_code,
                    e.message,
                )
                return False, None
            except Exception as e:
                self.logger.error(
                    "Unexpected error processing match %s: %s", match_id, e
                )
                return False, None

    async def _save_match_data(self, match_id: str, match_data: L2MatchData) -> None:
        """
        保存比赛数据到文件

        Args:
            match_id: 比赛ID
            match_data: 比赛数据
        """
        filename = f"{match_id}.json"
        filepath = Path(self.config.output_dir) / filename

        try:
            import json

            data_dict = match_data.to_dict()

            # 处理datetime序列化问题
            def datetime_handler(obj):
                if hasattr(obj, "isoformat"):
                    return obj.isoformat()
                raise TypeError(repr(obj) + " is not JSON serializable")

            async with aiofiles.open(filepath, "w", encoding="utf-8") as file:
                await file.write(
                    json.dumps(
                        data_dict,
                        ensure_ascii=False,
                        indent=2,
                        default=datetime_handler,
                    )
                )

            self.logger.debug("Saved match data to %s", filepath)

        except Exception as e:
            self.logger.error("Failed to save match data for %s: %s", match_id, e)
            raise

    async def _log_failed_id(self, match_id: str) -> None:
        """记录失败的match_id"""
        try:
            async with aiofiles.open(
                self.config.failed_ids_file, "a", encoding="utf-8"
            ) as file:
                await file.write(f"{match_id}\n")
        except Exception as e:
            self.logger.error("Failed to log failed ID %s: %s", match_id, e)

    async def _save_progress(self) -> None:
        """保存处理进度"""
        progress_file = Path(self.config.output_dir) / "progress.txt"

        try:
            progress_data = {
                "processed_count": self.stats.total_processed,
                "successful_count": self.stats.successful,
                "failed_count": self.stats.failed,
                "processed_ids": list(self._processed_ids),
                "last_update": datetime.now().isoformat(),
            }

            import json

            async with aiofiles.open(progress_file, "w", encoding="utf-8") as file:
                await file.write(json.dumps(progress_data, indent=2))

        except Exception as e:
            self.logger.error("Failed to save progress: %s", e)

    async def run_backfill(self) -> BackfillStats:
        """
        运行数据回填主流程

        Returns:
            BackfillStats: 回填统计信息
        """
        self.logger.info("Starting L2 data backfill...")
        self._running = True
        self.stats.start_time = datetime.now()

        try:
            await self._initialize_components()

            # 创建进度条
            progress_bar = tqdm.tqdm(
                desc="Processing matches",
                unit="matches",
                disable=not self.config.enable_progress_bar,
            )

            # 创建并发任务队列
            tasks = set()
            save_counter = 0

            # 流式处理match_ids
            async for match_id in self._read_match_ids_stream():
                if self._shutdown_requested:
                    self.logger.info("Shutdown requested, stopping new tasks...")
                    break

                # 创建处理任务
                task = asyncio.create_task(self._process_single_match(match_id))
                tasks.add(task)

                # 控制并发队列大小
                if len(tasks) >= self.config.max_concurrent:
                    done, pending = await asyncio.wait(
                        tasks, return_when=asyncio.FIRST_COMPLETED
                    )

                    for completed_task in done:
                        try:
                            success, match_data = completed_task.result()
                            self.stats.total_processed += 1

                            if success and match_data:
                                # 保存数据
                                await self._save_match_data(match_id, match_data)
                                self.stats.successful += 1
                                self._processed_ids.add(match_id)

                            else:
                                # 记录失败
                                self.stats.failed += 1
                                self._failed_ids.add(match_id)
                                await self._log_failed_id(match_id)

                            save_counter += 1

                            # 定期保存进度
                            if save_counter >= self.config.save_interval:
                                await self._save_progress()
                                save_counter = 0

                        except Exception as e:
                            self.logger.error("Error in task result: %s", e)

                    tasks = pending

                # 更新进度条
                progress_bar.update(1)

                # 请求间延迟
                if self.config.rate_limit_delay > 0:
                    await asyncio.sleep(self.config.rate_limit_delay)

            # 等待剩余任务完成 - 修复 AsyncIO 警告的关键部分
            if tasks:
                self.logger.info(
                    "Waiting for %d remaining tasks to complete...", len(tasks)
                )

                # 使用 asyncio.gather 等待所有任务完成，避免 as_completed 的警告
                try:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            self.logger.error(
                                "Task %d failed with exception: %s", i, result
                            )
                            self.stats.failed += 1
                            continue

                        try:
                            success, match_data = result
                            self.stats.total_processed += 1

                            if success and match_data:
                                await self._save_match_data(match_id, match_data)
                                self.stats.successful += 1
                            else:
                                self.stats.failed += 1
                                await self._log_failed_id(match_id)

                        except Exception as e:
                            self.logger.error(
                                "Error processing final task result %d: %s", i, e
                            )
                            self.stats.failed += 1

                except Exception as e:
                    self.logger.error("Error waiting for final tasks: %s", e)

                    # 如果 gather 失败，尝试取消所有任务
                    for task in tasks:
                        if not task.done():
                            task.cancel()

                    # 等待取消完成
                    try:
                        await asyncio.gather(*tasks, return_exceptions=True)
                    except Exception as e:
                        pass

            progress_bar.close()

        except Exception as e:
            self.logger.error("Fatal error in backfill process: %s", e)
            raise
        finally:
            self._running = False

            # 清理资源 - 确保 fetcher 正确关闭
            try:
                if self._fetcher:
                    await self._fetcher.close()
            except Exception as e:
                self.logger.error("Error closing fetcher: %s", e)

            # 最终保存进度
            try:
                await self._save_progress()
            except Exception as e:
                self.logger.error("Error saving final progress: %s", e)

            self.logger.info(
                "Backfill completed. Total: %d, Success: %d, Failed: %d, Success Rate: %.2f%%",
                self.stats.total_processed,
                self.stats.successful,
                self.stats.failed,
                self.stats.success_rate,
            )

        return self.stats


def create_sample_input_file(file_path: str, num_ids: int = 1000) -> None:
    """
    创建示例输入文件用于测试

    Args:
        file_path: 文件路径
        num_ids: match_ids数量
    """
    import random

    # 确保目录存在
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["match_id"])  # 标题行

        # 生成示例match_ids
        for i in range(num_ids):
            match_id = f"{random.randint(1000000, 9999999)}"
            writer.writerow([match_id])

    print(f"Created sample input file with {num_ids} match_ids: {file_path}")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="L2数据回填脚本")
    parser.add_argument(
        "--input", "-i", default="data/l2_backfill_queue.csv", help="输入CSV文件路径"
    )
    parser.add_argument("--output", "-o", default="data/l2_output", help="输出目录路径")
    parser.add_argument("--concurrent", "-c", type=int, default=15, help="最大并发数")
    parser.add_argument("--create-sample", action="store_true", help="创建示例输入文件")

    args = parser.parse_args()

    # 创建示例文件（如果请求）
    if args.create_sample:
        create_sample_input_file(args.input, 100)
        return

    # 配置回填参数
    config = BackfillConfig(
        input_file=args.input,
        output_dir=args.output,
        max_concurrent=args.concurrent,
        enable_progress_bar=True,
    )

    # 运行回填
    manager = BackfillManager(config)

    try:
        stats = await manager.run_backfill()
        print("\n🎉 Backfill completed successfully!")
        print("📊 Statistics:")
        print(f"   Total processed: {stats.total_processed}")
        print(f"   Successful: {stats.successful}")
        print(f"   Failed: {stats.failed}")
        print(f"   Success rate: {stats.success_rate:.2f}%")
        print(f"   Processing rate: {stats.processing_rate:.2f} matches/sec")
        print(f"   Elapsed time: {stats.elapsed_time:.2f} seconds")

    except KeyboardInterrupt:
        print("\n⏹️ Backfill interrupted by user")
    except Exception as e:
        print(f"\n❌ Backfill failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
