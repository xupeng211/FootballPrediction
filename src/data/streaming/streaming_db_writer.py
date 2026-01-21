#!/usr/bin/env python3
"""
高性能流式数据库写入器 - Sprint 4 核心组件

专门针对50GB+大规模数据的批量数据库写入优化。
支持批量Upsert、事务管理和性能监控。

设计原则:
- Batch Operations (批量操作)
- Transaction Management (事务管理)
- Performance Monitoring (性能监控)
- Error Handling (错误处理)
- Retry Logic (重试逻辑)
"""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from decimal import Decimal
import logging
import time
from typing import Any

import pandas as pd

from src.database.connection import get_connection

logger = logging.getLogger(__name__)


@dataclass
class BatchWriteConfig:
    """批量写入配置"""

    # 批量大小配置
    batch_size: int = 1000
    max_queue_size: int = 10000
    flush_interval_seconds: float = 5.0

    # 性能配置
    enable_parallel_writes: bool = True
    max_concurrent_batches: int = 3
    write_timeout_seconds: float = 30.0

    # 重试配置
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    exponential_backoff: bool = True

    # 事务配置
    use_transactions: bool = True
    isolation_level: str = "READ_COMMITTED"


@dataclass
class WriteStats:
    """写入统计信息"""

    total_rows: int = 0
    successful_batches: int = 0
    failed_batches: int = 0
    total_time_seconds: float = 0.0
    avg_rows_per_second: float = 0.0
    avg_batch_time_ms: float = 0.0
    retry_count: int = 0


class StreamingDBWriter:
    """
    高性能流式数据库写入器

    专门处理大规模数据的批量写入，支持：
    - 批量Upsert操作
    - 异步并发写入
    - 事务管理和错误恢复
    - 性能监控和优化
    """

    def __init__(self, config: BatchWriteConfig | None = None):
        self.config = config or BatchWriteConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 写入队列和统计
        self._write_queue = asyncio.Queue(maxsize=self.config.max_queue_size)
        self._stats = WriteStats()
        self._start_time = time.time()
        self._running = False
        self._writer_tasks: list[asyncio.Task] = []

        # 连接池
        self._connection_pool: list[Any] = []

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()

    async def start(self) -> None:
        """启动写入器"""
        if self._running:
            return

        self._running = True

        # 创建连接池
        await self._initialize_connection_pool()

        # 启动写入任务
        for i in range(self.config.max_concurrent_batches):
            task = asyncio.create_task(self._batch_writer_worker(i))
            self._writer_tasks.append(task)

        self.logger.info(
            f"✅ 流式数据库写入器已启动 (并发数: {self.config.max_concurrent_batches})"
        )

    async def stop(self) -> None:
        """停止写入器"""
        if not self._running:
            return

        self._running = False

        # 等待队列清空
        await self._flush_remaining_data()

        # 停止写入任务
        for task in self._writer_tasks:
            task.cancel()

        await asyncio.gather(*self._writer_tasks, return_exceptions=True)

        # 关闭连接池
        await self._close_connection_pool()

        self._log_final_stats()
        self.logger.info("✅ 流式数据库写入器已停止")

    async def write_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        conflict_columns: list[str] | None = None,
        on_conflict: str = "UPDATE",
    ) -> None:
        """
        异步写入DataFrame

        Args:
            df: 要写入的数据
            table_name: 目标表名
            conflict_columns: 冲突检测列
            on_conflict: 冲突处理方式 (UPDATE/IGNORE)
        """
        if df.empty:
            return

        # 分片处理
        chunks = [
            df[i : i + self.config.batch_size] for i in range(0, len(df), self.config.batch_size)
        ]

        for chunk in chunks:
            write_task = {
                "data": chunk,
                "table_name": table_name,
                "conflict_columns": conflict_columns,
                "on_conflict": on_conflict,
                "timestamp": time.time(),
            }

            try:
                await asyncio.wait_for(
                    self._write_queue.put(write_task), timeout=self.config.write_timeout_seconds
                )
            except TimeoutError:
                self.logger.exception("写入队列已满，丢弃数据块")
                self._stats.failed_batches += 1

    async def write_matches_batch(self, matches_df: pd.DataFrame) -> None:
        """
        批量写入比赛数据 (专用优化)

        Args:
            matches_df: 比赛数据DataFrame
        """
        if matches_df.empty:
            return

        # 数据预处理
        processed_df = self._preprocess_matches_data(matches_df)

        # 使用专用的冲突处理
        await self.write_dataframe(
            processed_df, "matches", conflict_columns=["match_id"], on_conflict="UPDATE"
        )

    async def write_odds_batch(self, odds_df: pd.DataFrame) -> None:
        """
        批量写入赔率数据 (专用优化)

        Args:
            odds_df: 赔率数据DataFrame
        """
        if odds_df.empty:
            return

        # 数据预处理
        processed_df = self._preprocess_odds_data(odds_df)

        # 使用专用的冲突处理
        await self.write_dataframe(
            processed_df,
            "odds",
            conflict_columns=["match_id", "bookmaker", "timestamp"],
            on_conflict="UPDATE",
        )

    async def _batch_writer_worker(self, worker_id: int) -> None:
        """批量写入工作器"""

        while self._running:
            try:
                # 获取写入任务 (带超时)
                write_task = await asyncio.wait_for(self._write_queue.get(), timeout=1.0)

                # 执行写入
                await self._execute_batch_write(write_task, worker_id)

                # 标记任务完成
                self._write_queue.task_done()

            except TimeoutError:
                # 超时继续循环，检查_running状态
                continue
            except Exception as e:
                self.logger.exception(f"写入工作器 {worker_id} 异常: {e}")
                self._stats.failed_batches += 1

    async def _execute_batch_write(self, write_task: dict[str, Any], worker_id: int) -> None:
        """执行批量写入"""
        start_time = time.time()
        data = write_task["data"]
        table_name = write_task["table_name"]
        conflict_columns = write_task.get("conflict_columns")
        on_conflict = write_task.get("on_conflict", "UPDATE")

        # 重试逻辑
        for attempt in range(self.config.max_retries + 1):
            try:
                # 获取连接
                conn = await self._get_connection()

                with self._transaction_context(conn):
                    if conflict_columns:
                        # 批量Upsert
                        await self._batch_upsert(
                            conn, data, table_name, conflict_columns, on_conflict
                        )
                    else:
                        # 批量插入
                        await self._batch_insert(conn, data, table_name)

                # 更新统计
                batch_time = (time.time() - start_time) * 1000
                self._update_stats(len(data), batch_time, attempt > 0)

                self.logger.info(
                    f"工作器 {worker_id}: 写入 {len(data)} 行到 {table_name}, 耗时 {batch_time:.1f}ms"
                )
                return

            except Exception as e:
                if attempt < self.config.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.warning(
                        f"写入失败 (尝试 {attempt + 1}/{self.config.max_retries + 1}): {e}, {delay}秒后重试"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.exception(f"写入最终失败: {e}")
                    self._stats.failed_batches += 1
                    raise

    async def _batch_upsert(
        self,
        conn,
        data: pd.DataFrame,
        table_name: str,
        conflict_columns: list[str],
        on_conflict: str,
    ) -> None:
        """批量Upsert操作"""
        # 构建列名和占位符
        columns = data.columns.tolist()
        values = data.values.tolist()

        # 构建SQL语句
        placeholders = ", ".join(["$%d" % (i + 1) for i in range(len(columns))])
        conflict_cols = ", ".join(conflict_columns)

        # 更新子句
        update_clauses = []
        for col in columns:
            if col not in conflict_columns:
                update_clauses.append(f"{col} = EXCLUDED.{col}")

        update_clause = ", ".join(update_clauses) if update_clauses else "NOTHING"

        sql = f"""
        INSERT INTO {table_name} ({", ".join(columns)})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_cols}) DO {on_conflict}
        SET {update_clause}
        """

        # 执行批量操作
        await conn.executemany(sql, values)

    async def _batch_insert(self, conn, data: pd.DataFrame, table_name: str) -> None:
        """批量插入操作"""
        columns = data.columns.tolist()
        values = data.values.tolist()

        placeholders = ", ".join(["$%d" % (i + 1) for i in range(len(columns))])
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

        await conn.executemany(sql, values)

    def _preprocess_matches_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """预处理比赛数据"""
        # 复制数据避免修改原始DataFrame
        processed_df = df.copy()

        # 确保必要列存在
        required_columns = ["match_id", "home_team_id", "away_team_id", "match_date"]
        for col in required_columns:
            if col not in processed_df.columns:
                self.logger.warning(f"缺少必要列: {col}")
                continue

        # 数据类型转换
        if "match_date" in processed_df.columns:
            processed_df["match_date"] = pd.to_datetime(processed_df["match_date"])

        # 数值精度处理
        numeric_columns = ["home_score", "away_score", "home_xg", "away_xg"]
        for col in numeric_columns:
            if col in processed_df.columns:
                processed_df[col] = pd.to_numeric(processed_df[col], errors="coerce")

        return processed_df

    def _preprocess_odds_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """预处理赔率数据"""
        processed_df = df.copy()

        # 确保必要列存在
        required_columns = ["match_id", "bookmaker", "home_odds", "draw_odds", "away_odds"]
        for col in required_columns:
            if col not in processed_df.columns:
                self.logger.warning(f"缺少必要列: {col}")

        # 赔率精度处理 (使用Decimal确保精度)
        odds_columns = ["home_odds", "draw_odds", "away_odds"]
        for col in odds_columns:
            if col in processed_df.columns:
                # 转换为Decimal确保精度
                processed_df[col] = processed_df[col].apply(
                    lambda x: Decimal(str(x)) if pd.notna(x) and x != "" else None
                )

        # 时间戳处理
        if "timestamp" in processed_df.columns:
            processed_df["timestamp"] = pd.to_datetime(processed_df["timestamp"])

        return processed_df

    async def _initialize_connection_pool(self) -> None:
        """初始化连接池"""
        pool_size = self.config.max_concurrent_batches + 2  # 额外2个连接

        for _i in range(pool_size):
            conn = await get_connection()
            self._connection_pool.append(conn)

    async def _get_connection(self) -> Any:
        """获取数据库连接"""
        # 简化版连接获取，实际项目中应该使用连接池
        return await get_connection()

    async def _close_connection_pool(self) -> None:
        """关闭连接池"""
        for conn in self._connection_pool:
            try:
                if hasattr(conn, "close"):
                    await conn.close()
            except Exception as e:
                self.logger.warning(f"关闭连接失败: {e}")

        self._connection_pool.clear()

    @asynccontextmanager
    async def _transaction_context(self, conn):
        """事务上下文管理器"""
        if self.config.use_transactions:
            transaction = conn.transaction()
            await transaction.start()
            try:
                yield conn
                await transaction.commit()
            except Exception:
                await transaction.rollback()
                raise
        else:
            yield conn

    def _calculate_retry_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        if self.config.exponential_backoff:
            return self.config.retry_delay_seconds * (2**attempt)
        return self.config.retry_delay_seconds

    def _update_stats(self, rows_written: int, batch_time_ms: float, was_retry: bool) -> None:
        """更新写入统计"""
        self._stats.total_rows += rows_written
        self._stats.successful_batches += 1

        if was_retry:
            self._stats.retry_count += 1

        # 计算平均指标
        total_time = time.time() - self._start_time
        if total_time > 0:
            self._stats.avg_rows_per_second = self._stats.total_rows / total_time

        # 更新平均批次时间 (使用指数移动平均)
        alpha = 0.1  # 平滑因子
        if self._stats.avg_batch_time_ms == 0:
            self._stats.avg_batch_time_ms = batch_time_ms
        else:
            self._stats.avg_batch_time_ms = (
                alpha * batch_time_ms + (1 - alpha) * self._stats.avg_batch_time_ms
            )

    async def _flush_remaining_data(self) -> None:
        """刷新剩余数据"""
        self.logger.info("🔄 等待队列清空...")

        # 等待队列处理完成
        while not self._write_queue.empty():
            await asyncio.sleep(0.1)

        self.logger.info("✅ 队列已清空")

    def _log_final_stats(self) -> None:
        """记录最终统计"""
        total_time = time.time() - self._start_time

        self.logger.info(
            f"📊 写入统计完成:\n"
            f"  总行数: {self._stats.total_rows:,}\n"
            f"  成功批次: {self._stats.successful_batches:,}\n"
            f"  失败批次: {self._stats.failed_batches:,}\n"
            f"  重试次数: {self._stats.retry_count:,}\n"
            f"  总耗时: {total_time:.2f}s\n"
            f"  平均速率: {self._stats.avg_rows_per_second:.1f} 行/秒\n"
            f"  平均批次时间: {self._stats.avg_batch_time_ms:.1f}ms"
        )

    def get_write_stats(self) -> WriteStats:
        """获取写入统计"""
        return self._stats


# 便捷函数
async def create_streaming_writer(
    batch_size: int = 1000, max_concurrent: int = 3, enable_transactions: bool = True
) -> StreamingDBWriter:
    """
    创建流式数据库写入器

    Args:
        batch_size: 批量大小
        max_concurrent: 最大并发数
        enable_transactions: 启用事务

    Returns:
        StreamingDBWriter: 流式写入器实例
    """
    config = BatchWriteConfig(
        batch_size=batch_size,
        max_concurrent_batches=max_concurrent,
        use_transactions=enable_transactions,
    )

    writer = StreamingDBWriter(config)
    await writer.start()
    return writer
