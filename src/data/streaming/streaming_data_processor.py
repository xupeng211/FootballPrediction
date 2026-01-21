#!/usr/bin/env python3
"""
高性能流式数据处理器 - Sprint 4 核心组件

专门针对50GB+大规模数据的内存高效处理。
使用生成器、分片读取和流式处理，确保内存占用平稳。

设计原则:
- Memory Efficiency (内存高效)
- Streaming Processing (流式处理)
- Chunk-based Operations (分片操作)
- Lazy Loading (懒加载)
- Zero Copy Optimization (零拷贝优化)
"""

from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
import gc
import logging
from pathlib import Path
import time
from typing import Any

import pandas as pd
import psutil

logger = logging.getLogger(__name__)


@dataclass
class StreamingConfig:
    """流式处理配置"""

    # 数据分片配置
    chunk_size: int = 10000  # 每次处理的行数
    max_memory_usage_mb: float = 1024.0  # 最大内存使用(MB)
    memory_check_interval: int = 10  # 内存检查间隔(分片数)

    # 性能配置
    enable_parallel_processing: bool = True
    max_workers: int = 4
    prefetch_chunks: int = 2

    # 类型优化配置
    categorical_columns: list[str] = field(
        default_factory=lambda: ["home_team_id", "away_team_id", "league_id"]
    )
    numeric_columns: list[str] = field(
        default_factory=lambda: ["home_score", "away_score", "home_odds", "draw_odds", "away_odds"]
    )
    datetime_columns: list[str] = field(default_factory=lambda: ["match_date"])
    boolean_columns: list[str] = field(default_factory=lambda: ["status"])

    # 精度配置
    use_decimal_for_precision: bool = True
    precision_columns: list[str] = field(
        default_factory=lambda: ["home_odds", "draw_odds", "away_odds"]
    )


@dataclass
class MemoryStats:
    """内存统计信息"""

    current_usage_mb: float
    peak_usage_mb: float
    processed_rows: int
    processing_rate_rows_per_sec: float
    gc_collections: int


class StreamingDataProcessor:
    """
    高性能流式数据处理器

    专门处理大规模数据的内存高效处理，支持：
    - 分片读取CSV/JSON
    - 内存监控和自动垃圾回收
    - 并行处理优化
    - 类型优化减少内存占用
    """

    def __init__(self, config: StreamingConfig | None = None):
        self.config = config or StreamingConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 内存监控
        self._memory_stats = MemoryStats(
            current_usage_mb=0.0,
            peak_usage_mb=0.0,
            processed_rows=0,
            processing_rate_rows_per_sec=0.0,
            gc_collections=0,
        )
        self._start_time = time.time()
        self._last_gc_time = time.time()

    @contextmanager
    def memory_monitor(self, operation_name: str):
        """内存监控上下文管理器"""
        start_memory = self._get_memory_usage()
        start_time = time.time()

        try:
            yield
        finally:
            end_memory = self._get_memory_usage()
            duration = time.time() - start_time
            memory_delta = end_memory - start_memory

            self.logger.info(
                f"{operation_name}: 内存变化 {memory_delta:+.1f}MB, 耗时 {duration:.2f}s, 当前内存 {end_memory:.1f}MB"
            )

            # 更新峰值内存
            self._memory_stats.peak_usage_mb = max(self._memory_stats.peak_usage_mb, end_memory)

    def stream_csv_file(
        self,
        file_path: str | Path,
        columns: list[str] | None = None,
        filters: dict[str, Any] | None = None,
    ) -> Iterator[pd.DataFrame]:
        """
        流式读取CSV文件

        Args:
            file_path: CSV文件路径
            columns: 需要读取的列列表
            filters: 过滤条件字典

        Yields:
            pd.DataFrame: 数据分片
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        self.logger.info(f"🔄 开始流式读取CSV: {file_path} (chunk_size={self.config.chunk_size})")

        with self.memory_monitor("csv_streaming"):
            # 使用pd.read_csv的分片功能
            reader = pd.read_csv(
                file_path,
                chunksize=self.config.chunk_size,
                usecols=columns,
                dtype=self._get_optimal_dtypes(),
                parse_dates=self.config.datetime_columns,
                engine="c",  # 使用C引擎提高性能
                low_memory=False,  # 禁用低内存模式以获得更好的类型推断
            )

            for chunk_idx, chunk in enumerate(reader):
                # 应用过滤器
                if filters:
                    chunk = self._apply_filters(chunk, filters)

                # 类型优化和内存优化
                chunk = self._optimize_chunk_memory(chunk)

                # 内存检查
                self._check_memory_usage(chunk_idx)

                # 更新统计
                self._update_stats(len(chunk))

                yield chunk

                # 定期垃圾回收
                if chunk_idx % self.config.memory_check_interval == 0:
                    self._force_gc_if_needed()

    def stream_json_file(
        self, file_path: str | Path, lines_per_chunk: int = 1000
    ) -> Iterator[pd.DataFrame]:
        """
        流式读取JSON Lines文件

        Args:
            file_path: JSON文件路径
            lines_per_chunk: 每个分片的行数

        Yields:
            pd.DataFrame: 数据分片
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        self.logger.info(f"🔄 开始流式读取JSON: {file_path} (lines_per_chunk={lines_per_chunk})")

        with self.memory_monitor("json_streaming"):
            chunk = []

            with open(file_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f):
                    if line.strip():  # 跳过空行
                        chunk.append(line)

                    if len(chunk) >= lines_per_chunk:
                        # 处理分片
                        df = self._process_json_chunk(chunk)
                        if df is not None and not df.empty:
                            df = self._optimize_chunk_memory(df)
                            self._check_memory_usage(line_num // lines_per_chunk)
                            self._update_stats(len(df))
                            yield df

                        chunk = []

            # 处理最后一个分片
            if chunk:
                df = self._process_json_chunk(chunk)
                if df is not None and not df.empty:
                    df = self._optimize_chunk_memory(df)
                    self._update_stats(len(df))
                    yield df

    def process_with_streaming(
        self,
        data_source: str | Path | Iterator[pd.DataFrame],
        processor_func: Callable[[pd.DataFrame], Any],
        output_handler: Callable[[Any], None] | None = None,
        parallel: bool | None = None,
    ) -> list[Any]:
        """
        使用流式处理数据

        Args:
            data_source: 数据源 (文件路径或数据迭代器)
            processor_func: 处理函数
            output_handler: 输出处理函数
            parallel: 是否并行处理

        Returns:
            list: 处理结果列表
        """
        if parallel is None:
            parallel = self.config.enable_parallel_processing

        # 获取数据迭代器
        if isinstance(data_source, (str, Path)):
            if Path(data_source).suffix == ".csv":
                data_iter = self.stream_csv_file(data_source)
            else:
                data_iter = self.stream_json_file(data_source)
        else:
            data_iter = data_source

        results = []

        if parallel and self.config.max_workers > 1:
            results = self._process_parallel(data_iter, processor_func, output_handler)
        else:
            results = self._process_sequential(data_iter, processor_func, output_handler)

        return results

    def _process_sequential(
        self,
        data_iter: Iterator[pd.DataFrame],
        processor_func: Callable[[pd.DataFrame], Any],
        output_handler: Callable[[Any], None] | None,
    ) -> list[Any]:
        """顺序处理数据"""
        results = []

        for chunk in data_iter:
            with self.memory_monitor("chunk_processing"):
                # 处理分片
                result = processor_func(chunk)

                # 输出处理
                if output_handler is not None:
                    output_handler(result)

                results.append(result)

        return results

    def _process_parallel(
        self,
        data_iter: Iterator[pd.DataFrame],
        processor_func: Callable[[pd.DataFrame], Any],
        output_handler: Callable[[Any], None] | None,
    ) -> list[Any]:
        """并行处理数据"""
        results = []

        # 预取分片以实现并行处理
        chunks_buffer = []

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = []

            for chunk in data_iter:
                chunks_buffer.append(chunk)

                # 当缓冲区达到预取数量时，提交任务
                if len(chunks_buffer) >= self.config.prefetch_chunks:
                    future = executor.submit(processor_func, chunks_buffer.pop(0))
                    futures.append(future)

                # 处理已完成的任务
                for future in as_completed(futures):
                    if future.done():
                        try:
                            result = future.result()
                            if output_handler is not None:
                                output_handler(result)
                            results.append(result)
                            futures.remove(future)
                        except Exception as e:
                            self.logger.exception(f"并行处理失败: {e}")

            # 处理剩余的任务
            for future in futures:
                try:
                    result = future.result()
                    if output_handler is not None:
                        output_handler(result)
                    results.append(result)
                except Exception as e:
                    self.logger.exception(f"并行处理失败: {e}")

            # 处理缓冲区剩余的分片
            for chunk in chunks_buffer:
                result = processor_func(chunk)
                if output_handler is not None:
                    output_handler(result)
                results.append(result)

        return results

    def _get_optimal_dtypes(self) -> dict[str, str]:
        """获取最优数据类型"""
        dtypes = {}

        # 分类列使用category类型减少内存
        for col in self.config.categorical_columns:
            dtypes[col] = "category"

        # 数值列使用合适的数据类型
        for col in self.config.numeric_columns:
            if col in ["home_score", "away_score"]:
                dtypes[col] = "int8"  # 比分通常很小
            else:
                dtypes[col] = "float32"  # 使用float32而不是float64

        # 布尔列
        for col in self.config.boolean_columns:
            dtypes[col] = "boolean"

        return dtypes

    def _optimize_chunk_memory(self, chunk: pd.DataFrame) -> pd.DataFrame:
        """优化分片内存使用"""
        # 转换数据类型
        for col, dtype in self._get_optimal_dtypes().items():
            if col in chunk.columns:
                chunk[col] = chunk[col].astype(dtype, copy=False)

        # 删除不必要的列
        chunk = chunk.drop(
            columns=[col for col in chunk.columns if col.startswith("Unnamed:")], errors="ignore"
        )

        # 重置索引以节省内存
        chunk.reset_index(drop=True, inplace=True)

        return chunk

    def _apply_filters(self, chunk: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
        """应用过滤器"""
        for column, condition in filters.items():
            if column not in chunk.columns:
                continue

            if isinstance(condition, dict):
                # 范围过滤
                if "min" in condition:
                    chunk = chunk[chunk[column] >= condition["min"]]
                if "max" in condition:
                    chunk = chunk[chunk[column] <= condition["max"]]
                if "values" in condition:
                    chunk = chunk[chunk[column].isin(condition["values"])]
            else:
                # 简单值过滤
                chunk = chunk[chunk[column] == condition]

        return chunk

    def _process_json_chunk(self, chunk_lines: list[str]) -> pd.DataFrame | None:
        """处理JSON分片"""
        try:
            import json

            data = [json.loads(line) for line in chunk_lines if line.strip()]
            return pd.DataFrame(data)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON解析失败: {e}")
            return None
        except Exception as e:
            self.logger.exception(f"JSON分片处理失败: {e}")
            return None

    def _get_memory_usage(self) -> float:
        """获取当前内存使用量(MB)"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def _check_memory_usage(self, chunk_idx: int) -> None:
        """检查内存使用"""
        current_memory = self._get_memory_usage()
        self._memory_stats.current_usage_mb = current_memory

        # 内存使用警告
        if current_memory > self.config.max_memory_usage_mb:
            self.logger.warning(
                f"内存使用过高: {current_memory:.1f}MB > {self.config.max_memory_usage_mb}MB"
            )
            self._force_gc_if_needed()

    def _force_gc_if_needed(self) -> None:
        """强制垃圾回收"""
        current_time = time.time()

        # 距离上次GC至少5秒
        if current_time - self._last_gc_time > 5:
            gc.collect()
            self._memory_stats.gc_collections += 1
            self._last_gc_time = current_time

            self._get_memory_usage()

    def _update_stats(self, processed_rows: int) -> None:
        """更新处理统计"""
        self._memory_stats.processed_rows += processed_rows

        # 计算处理速率
        elapsed_time = time.time() - self._start_time
        if elapsed_time > 0:
            self._memory_stats.processing_rate_rows_per_sec = (
                self._memory_stats.processed_rows / elapsed_time
            )

    def get_memory_stats(self) -> MemoryStats:
        """获取内存统计信息"""
        self._memory_stats.current_usage_mb = self._get_memory_usage()
        return self._memory_stats


# 便捷函数
def create_streaming_processor(
    chunk_size: int = 10000, max_memory_mb: float = 1024.0, enable_parallel: bool = True
) -> StreamingDataProcessor:
    """
    创建流式数据处理器

    Args:
        chunk_size: 分片大小
        max_memory_mb: 最大内存使用(MB)
        enable_parallel: 启用并行处理

    Returns:
        StreamingDataProcessor: 流式处理器实例
    """
    config = StreamingConfig(
        chunk_size=chunk_size,
        max_memory_usage_mb=max_memory_mb,
        enable_parallel_processing=enable_parallel,
    )
    return StreamingDataProcessor(config)


# 流式处理装饰器
def streaming_memory_monitor(max_memory_mb: float = 1024.0):
    """
    流式处理内存监控装饰器

    Args:
        max_memory_mb: 最大内存使用限制(MB)
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            processor = StreamingDataProcessor(StreamingConfig(max_memory_usage_mb=max_memory_mb))

            with processor.memory_monitor(func.__name__):
                return func(*args, **kwargs)

        return wrapper

    return decorator
