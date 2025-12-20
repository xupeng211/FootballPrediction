#!/usr/bin/env python3
"""
压力测试框架 - Sprint 4 核心组件

专门针对50GB大规模数据处理的压力测试框架。
提供数据生成、性能基准测试和稳定性验证。

设计原则:
- Scalability Testing (可伸缩性测试)
- Performance Benchmarking (性能基准测试)
- Stability Validation (稳定性验证)
- Resource Monitoring (资源监控)
- Realistic Data Simulation (真实数据模拟)
"""

import asyncio
import logging
import time
import threading
import psutil
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import random
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)


@dataclass
class StressTestConfig:
    """压力测试配置"""

    # 数据规模配置
    target_data_size_gb: float = 50.0
    chunk_size: int = 10000
    match_count_per_file: int = 50000

    # 测试时长配置
    test_duration_minutes: int = 60
    warmup_duration_minutes: int = 5

    # 并发配置
    concurrent_readers: int = 4
    concurrent_writers: int = 3
    concurrent_predictors: int = 2

    # 性能目标配置
    max_memory_usage_mb: float = 4096.0  # 4GB
    max_cpu_usage_percent: float = 80.0
    max_io_wait_time_ms: float = 100.0
    min_throughput_rows_per_sec: float = 1000.0

    # 输出配置
    output_dir: str = "stress_test_results"
    enable_detailed_logging: bool = True
    generate_reports: bool = True


@dataclass
class ResourceUsage:
    """资源使用情况"""

    timestamp: datetime
    cpu_percent: float
    memory_usage_mb: float
    disk_usage_mb: float
    network_io_mb: float
    active_threads: int
    open_files: int

    @classmethod
    def current(cls) -> "ResourceUsage":
        """获取当前资源使用"""
        process = psutil.Process()
        return cls(
            timestamp=datetime.now(),
            cpu_percent=process.cpu_percent(),
            memory_usage_mb=process.memory_info().rss / 1024 / 1024,
            disk_usage_mb=psutil.disk_usage(".").used / 1024 / 1024,
            network_io_mb=0.0,  # 简化实现
            active_threads=threading.active_count(),
            open_files=len(process.open_files()),
        )


@dataclass
class PerformanceMetrics:
    """性能指标"""

    total_rows_processed: int = 0
    total_rows_generated: int = 0
    total_rows_predicted: int = 0
    total_rows_written: int = 0

    read_throughput_rows_per_sec: float = 0.0
    write_throughput_rows_per_sec: float = 0.0
    prediction_throughput_rows_per_sec: float = 0.0

    avg_read_time_ms: float = 0.0
    avg_write_time_ms: float = 0.0
    avg_prediction_time_ms: float = 0.0

    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    total_errors: int = 0

    test_duration_seconds: float = 0.0
    success_rate: float = 0.0


class StressTestFramework:
    """
    压力测试框架

    提供：
    - 50GB数据生成
    - 多组件并发测试
    - 性能基准测试
    - 资源使用监控
    - 测试报告生成
    """

    def __init__(self, config: Optional[StressTestConfig] = None):
        self.config = config or StressTestConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 测试状态
        self._running = False
        self._start_time = None
        self._metrics = PerformanceMetrics()
        self._resource_history: List[ResourceUsage] = []

        # 任务管理
        self._tasks: List[asyncio.Task] = []
        self._executor: Optional[ThreadPoolExecutor] = None
        self._process_executor: Optional[ProcessPoolExecutor] = None

        # 结果存储
        self._results: Dict[str, Any] = {}

    async def run_comprehensive_stress_test(self) -> Dict[str, Any]:
        """运行综合压力测试"""
        self.logger.info("🚀 开始50GB压力测试")
        self._start_time = datetime.now()
        self._running = True

        try:
            # 1. 环境准备
            await self._prepare_test_environment()

            # 2. 数据生成测试
            await self._test_data_generation()

            # 3. 读取性能测试
            await self._test_read_performance()

            # 4. 写入性能测试
            await self._test_write_performance()

            # 5. 预测性能测试
            await self._test_prediction_performance()

            # 6. 并发混合测试
            await self._test_mixed_workload()

            # 7. 长期稳定性测试
            await self._test_long_term_stability()

            # 8. 资源极限测试
            await self._test_resource_limits()

        except Exception as e:
            self.logger.error(f"压力测试失败: {e}")
            raise
        finally:
            await self._cleanup_test()

        # 生成测试报告
        return await self._generate_test_report()

    async def _prepare_test_environment(self) -> None:
        """准备测试环境"""
        self.logger.info("🔧 准备测试环境")

        # 创建输出目录
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(exist_ok=True)

        # 检查系统资源
        system_info = await self._get_system_info()
        self.logger.info(f"系统信息: {system_info}")

        # 预热
        self.logger.info(f"🔥 预热系统 ({self.config.warmup_duration_minutes}分钟)")
        await asyncio.sleep(self.config.warmup_duration_minutes * 60)

    async def _test_data_generation(self) -> None:
        """测试数据生成"""
        self.logger.info("📊 开始数据生成测试")

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_data.csv"

            start_time = time.time()

            # 生成50GB测试数据
            await self._generate_large_dataset(test_file, target_size_gb=50.0)

            generation_time = time.time() - start_time
            file_size_mb = test_file.stat().st_size / 1024 / 1024

            self.logger.info(
                f"✅ 数据生成完成: {file_size_mb:.1f}MB, "
                f"耗时 {generation_time:.1f}s, "
                f"速率 {file_size_mb/generation_time:.1f}MB/s"
            )

            # 验证数据质量
            await self._validate_generated_data(test_file)

            self._results["data_generation"] = {
                "file_size_mb": file_size_mb,
                "generation_time_s": generation_time,
                "generation_rate_mb_per_s": file_size_mb / generation_time,
                "validation_passed": True,
            }

    async def _test_read_performance(self) -> None:
        """测试读取性能"""
        self.logger.info("📖 开始读取性能测试")

        # 创建测试数据
        test_data = await self._create_test_dataset_size_gb(10.0)  # 10GB测试数据
        test_file = Path(self.config.output_dir) / "read_test.csv"
        test_data.to_csv(test_file, index=False)

        # 测试不同读取策略
        read_strategies = {
            "pandas_chunk": self._test_pandas_chunk_read,
            "streaming_processor": self._test_streaming_processor_read,
            "direct_numpy": self._test_direct_numpy_read,
        }

        for strategy_name, strategy_func in read_strategies.items():
            self.logger.info(f"测试读取策略: {strategy_name}")
            result = await strategy_func(test_file)
            self._results[f"read_{strategy_name}"] = result

    async def _test_write_performance(self) -> None:
        """测试写入性能"""
        self.logger.info("💾 开始写入性能测试")

        # 创建测试数据
        test_data = await self._create_test_dataset_size_mb(1000)  # 1GB测试数据

        write_strategies = {
            "batch_insert": self._test_batch_insert,
            "streaming_writer": self._test_streaming_writer_write,
            "bulk_upsert": self._test_bulk_upsert,
        }

        for strategy_name, strategy_func in write_strategies.items():
            self.logger.info(f"测试写入策略: {strategy_name}")
            result = await strategy_func(test_data)
            self._results[f"write_{strategy_name}"] = result

    async def _test_prediction_performance(self) -> None:
        """测试预测性能"""
        self.logger.info("🤖 开始预测性能测试")

        # 准备测试数据
        test_features = np.random.rand(100000, 13)  # 10万条特征数据

        prediction_strategies = {
            "vectorized": self._test_vectorized_prediction,
            "batch_processing": self._test_batch_prediction,
            "parallel_prediction": self._test_parallel_prediction,
        }

        for strategy_name, strategy_func in prediction_strategies.items():
            self.logger.info(f"测试预测策略: {strategy_name}")
            result = await strategy_func(test_features)
            self._results[f"prediction_{strategy_name}"] = result

    async def _test_mixed_workload(self) -> None:
        """测试混合工作负载"""
        self.logger.info("⚡ 开始混合工作负载测试")

        test_duration_seconds = self.config.test_duration_minutes * 60 - 300  # 预留5分钟清理
        test_file = Path(self.config.output_dir) / "mixed_workload.csv"

        # 生成测试数据
        test_data = await self._create_test_dataset_size_gb(20.0)
        test_data.to_csv(test_file, index=False)

        # 并发任务
        tasks = []

        # 读取任务
        for i in range(self.config.concurrent_readers):
            task = asyncio.create_task(self._continuous_read_task(test_file, test_duration_seconds))
            tasks.append(task)

        # 写入任务
        for i in range(self.config.concurrent_writers):
            task = asyncio.create_task(self._continuous_write_task(test_duration_seconds))
            tasks.append(task)

        # 预测任务
        for i in range(self.config.concurrent_predictors):
            task = asyncio.create_task(self._continuous_prediction_task(test_duration_seconds))
            tasks.append(task)

        # 监控资源使用
        monitor_task = asyncio.create_task(self._monitor_resources(test_duration_seconds))
        tasks.append(monitor_task)

        # 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _test_long_term_stability(self) -> None:
        """测试长期稳定性"""
        self.logger.info("⏱ 开始长期稳定性测试")

        stability_duration_seconds = 3600  # 1小时
        self.logger.info(f"稳定性测试时长: {stability_duration_seconds}秒")

        start_time = time.time()
        error_count = 0
        operation_count = 0

        while time.time() - start_time < stability_duration_seconds:
            try:
                # 执行随机操作
                operation = random.choice(["read", "write", "predict"])

                if operation == "read":
                    await self._random_read_operation()
                elif operation == "write":
                    await self._random_write_operation()
                else:
                    await self._random_prediction_operation()

                operation_count += 1

                # 检查资源使用
                current_resources = ResourceUsage.current()
                if (
                    current_resources.cpu_percent > self.config.max_cpu_usage_percent
                    or current_resources.memory_usage_mb > self.config.max_memory_usage_mb
                ):
                    error_count += 1
                    self.logger.warning(
                        f"资源使用过高: CPU {current_resources.cpu_percent:.1f}%, "
                        f"内存 {current_resources.memory_usage_mb:.1f}MB"
                    )

                # 短暂休息避免过度消耗
                await asyncio.sleep(0.1)

            except Exception as e:
                error_count += 1
                self.logger.error(f"稳定性测试操作失败: {e}")

        self._results["stability"] = {
            "duration_s": time.time() - start_time,
            "total_operations": operation_count,
            "error_count": error_count,
            "success_rate": (operation_count - error_count) / max(operation_count, 1),
            "avg_error_rate": error_count / max(operation_count, 1),
        }

    async def _test_resource_limits(self) -> None:
        """测试资源极限"""
        self.logger.info("🎯 开始资源极限测试")

        # 内存极限测试
        await self._test_memory_limits()

        # CPU极限测试
        await self._test_cpu_limits()

        # 并发极限测试
        await self._test_concurrency_limits()

    async def _test_memory_limits(self) -> None:
        """测试内存极限"""
        self.logger.info("💾 测试内存极限")

        # 尝试分配大型数组
        memory_test_sizes = [100, 500, 1000, 2000, 4000]  # MB

        for size_mb in memory_test_sizes:
            try:
                # 分配内存
                large_array = np.random.rand(size_mb * 1024 * 256 // 8)  # 假设每个元素8字节
                memory_usage = psutil.virtual_memory().used / 1024 / 1024

                self.logger.info(f"分配 {size_mb}MB内存: 实际使用 {memory_usage:.1f}MB")

                # 短暂使用和释放
                await asyncio.sleep(1)
                del large_array
                gc.collect()

            except MemoryError:
                self.logger.error(f"内存分配失败: {size_mb}MB")
                break

    async def _test_cpu_limits(self) -> None:
        """测试CPU极限"""
        self.logger.info("🔥 测试CPU极限")

        cpu_loads = [0.1, 0.3, 0.5, 0.7, 0.9]

        for load in cpu_loads:
            start_time = time.time()
            target_duration = 10  # 10秒

            # CPU密集型任务
            while time.time() - start_time < target_duration:
                # 矩暂计算
                result = sum(np.random.rand(1000) ** 2)
                await asyncio.sleep(0.01)

            actual_duration = time.time() - start_time
            cpu_percent = psutil.cpu_percent(interval=1)

            self.logger.info(
                f"CPU负载 {load}: 目标 {target_duration}s, "
                f"实际 {actual_duration:.1f}s, CPU使用率 {cpu_percent:.1f}%"
            )

    async def _test_concurrency_limits(self) -> None:
        """测试并发极限"""
        self.logger.info("⚡ 测试并发极限")

        # 逐渐增加并发数
        concurrency_levels = [2, 4, 8, 16, 32, 64, 128]
        max_successful_level = 0

        for level in concurrency_levels:
            try:
                # 创建并发任务
                tasks = [asyncio.create_task(self._dummy_task()) for _ in range(level)]

                # 等待任务完成
                start_time = time.time()
                await asyncio.gather(*tasks)
                completion_time = time.time() - start_time

                self.logger.info(f"并发数 {level}: {len(tasks)} 任务完成, 耗时 {completion_time:.1f}s")
                max_successful_level = level

            except Exception as e:
                self.logger.error(f"并发数 {level} 失败: {e}")
                break

        self._results["concurrency"] = {
            "max_successful_level": max_successful_level,
            "test_passed": max_successful_level >= self.config.concurrent_readers,
        }

    # 数据生成方法
    async def _generate_large_dataset(self, file_path: Path, target_size_gb: float) -> None:
        """生成大型数据集"""
        target_size_bytes = target_size_bytes = target_size_gb * 1024 * 1024 * 1024
        chunk_size = self.config.chunk_size

        # 计算需要的数据量
        estimated_row_size = 200  # 估计每行200字节
        target_rows = int(target_size_bytes / estimated_row_size)

        self.logger.info(f"生成目标: {target_size_gb}GB, 估计 {target_rows:,} 行")

        # 分批生成数据
        with open(file_path, "w") as f:
            # 写入CSV头部
            f.write(
                "match_id,home_team_id,away_team_id,home_score,away_score,home_xg,away_xg,home_odds,draw_odds,away_odds,match_date,status\n"
            )

            rows_generated = 0
            chunk_start_time = time.time()

            while rows_generated < target_rows:
                # 生成数据块
                chunk_data = self._generate_data_chunk(min(chunk_size, target_rows - rows_generated), rows_generated)

                # 写入数据
                for row in chunk_data:
                    f.write(",".join(map(str, row)) + "\n")

                rows_generated += len(chunk_data)

                # 进度报告
                if rows_generated % 100000 == 0:
                    elapsed = time.time() - chunk_start_time
                    progress = rows_generated / target_rows
                    rate = rows_generated / elapsed if elapsed > 0 else 0
                    eta_seconds = (target_rows - rows_generated) / rate if rate > 0 else 0

                    self.logger.info(
                        f"生成进度: {progress:.1%}, "
                        f"{rows_generated:,}/{target_rows:,} 行, "
                        f"速率: {rate:.0f} 行/秒, "
                        f"剩余时间: {eta_seconds:.0f}s"
                    )

        self._metrics.total_rows_generated = rows_generated

    def _generate_data_chunk(self, count: int, offset: int) -> List[List[Any]]:
        """生成数据块"""
        chunk_data = []

        for i in range(count):
            row_num = offset + i

            # 生成匹配ID
            match_id = f"match_{row_num:08d}"

            # 生成团队ID (复用一些ID以模拟现实数据)
            team_ids = list(range(1, 500))
            home_team_id = random.choice(team_ids)
            away_team_id = random.choice(team_ids)
            while away_team_id == home_team_id:
                away_team_id = random.choice(team_ids)

            # 生成比分
            home_score = random.randint(0, 5)
            away_score = random.randint(0, 5)

            # 生成xG (预期进球)
            home_xg = round(random.uniform(0.1, 4.0), 2)
            away_xg = round(random.uniform(0.1, 4.0), 2)

            # 生成赔率
            home_odds = round(random.uniform(1.5, 5.0), 2)
            draw_odds = round(random.uniform(2.5, 4.0), 2)
            away_odds = round(random.uniform(2.0, 6.0), 2)

            # 确保赔率合理性
            while home_odds + draw_odds + away_odds < 2.5:
                home_odds = round(random.uniform(1.5, 5.0), 2)
                draw_odds = round(random.uniform(2.5, 4.0), 2)
                away_odds = round(random.uniform(2.0, 6.0), 2)

            # 生成日期
            days_ago = random.randint(0, 365 * 3)
            match_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

            # 生成状态
            status = random.choice(["SCHEDULED", "FINISHED"])

            chunk_data.append(
                [
                    match_id,
                    home_team_id,
                    away_team_id,
                    home_score,
                    away_score,
                    home_xg,
                    away_xg,
                    home_odds,
                    draw_odds,
                    away_odds,
                    match_date,
                    status,
                ]
            )

        return chunk_data

    async def _create_test_dataset_size_gb(self, size_gb: float) -> pd.DataFrame:
        """创建指定GB大小的测试数据集"""
        target_rows = int(size_gb * 1024 * 1024 * 1024 / 200)  # 假设每行200字节
        target_rows = min(target_rows, 1000000)  # 限制最大行数

        return await self._create_test_dataset_size_mb(target_rows // 1000)  # 转换为MB

    async def _create_test_dataset_size_mb(self, size_mb: float) -> pd.DataFrame:
        """创建指定MB大小的测试数据集"""
        target_rows = int(size_mb * 1024 / 0.2)  # 假设每行0.2KB

        # 生成数据
        data = []
        for i in range(target_rows):
            data.append(
                {
                    "match_id": f"test_match_{i:08d}",
                    "feature_1": np.random.rand(),
                    "feature_2": np.random.rand(),
                    "feature_3": np.random.rand(),
                    "feature_4": np.random.rand(),
                    "feature_5": np.random.rand(),
                    "feature_6": np.random.rand(),
                    "feature_7": np.random.rand(),
                    "feature_8": np.random.rand(),
                    "feature_9": np.random.rand(),
                    "feature_10": np.random.rand(),
                    "feature_11": np.random.rand(),
                    "feature_12": np.random.rand(),
                    "feature_13": np.random.rand(),
                }
            )

        return pd.DataFrame(data)

    # 测试策略方法
    async def _test_pandas_chunk_read(self, file_path: Path) -> Dict[str, Any]:
        """测试Pandas分块读取"""
        chunk_times = []
        total_rows = 0

        start_time = time.time()

        for chunk in pd.read_csv(file_path, chunksize=self.config.chunk_size):
            chunk_start = time.time()
            process_chunk(chunk)  # 模拟处理
            chunk_time = time.time() - chunk_start

            chunk_times.append(chunk_time)
            total_rows += len(chunk)

        total_time = time.time() - start_time
        throughput = total_rows / total_time if total_time > 0 else 0

        return {
            "total_rows": total_rows,
            "total_time_s": total_time,
            "avg_chunk_time_ms": np.mean(chunk_times) * 1000,
            "throughput_rows_per_sec": throughput,
            "chunk_size": self.config.chunk_size,
        }

    async def _test_streaming_processor_read(self, file_path: Path) -> Dict[str, Any]:
        """测试流式处理器读取"""
        from ..data.streaming.streaming_data_processor import StreamingDataProcessor

        processor = StreamingDataProcessor(StreamingConfig(chunk_size=self.config.chunk_size))

        read_times = []
        total_rows = 0

        start_time = time.time()

        for chunk in processor.stream_csv_file(file_path):
            chunk_start = time.time()
            process_chunk(chunk)  # 模拟处理
            chunk_time = time.time() - chunk_start

            read_times.append(chunk_time)
            total_rows += len(chunk)

        total_time = time.time() - start_time
        throughput = total_rows / total_time if total_time > 0 else 0

        return {
            "total_rows": total_rows,
            "total_time_s": total_time,
            "avg_chunk_time_ms": np.mean(read_times) * 1000,
            "throughput_rows_per_sec": throughput,
            "memory_stats": processor.get_memory_stats()._asdict(),
        }

    async def _test_direct_numpy_read(self, file_path: Path) -> Dict[str, Any]:
        """测试直接NumPy读取"""
        # 这个测试需要更复杂的实现，简化版本
        return {
            "note": "直接NumPy读取需要更复杂的实现",
            "file_size_mb": file_path.stat().st_size / 1024 / 1024,
        }

    async def _test_batch_insert(self, data: pd.DataFrame) -> Dict[str, Any]:
        """测试批量插入"""
        # 这里应该测试数据库批量插入性能
        return {"rows": len(data), "note": "需要集成实际数据库连接"}

    async def _test_streaming_writer_write(self, data: pd.DataFrame) -> Dict[str, Any]:
        """测试流式写入器写入"""
        # 这里应该测试流式写入器性能
        return {"rows": len(data), "note": "需要集成实际数据库连接"}

    async def _test_bulk_upsert(self, data: pd.DataFrame) -> Dict[str, Any]:
        """测试批量Upsert"""
        # 这里应该测试批量Upsert性能
        return {"rows": len(data), "note": "需要集成实际数据库连接"}

    async def _test_vectorized_prediction(self, features: np.ndarray) -> Dict[str, Any]:
        """测试向量化预测"""
        start_time = time.time()

        # 向量化预测
        probabilities = 1.0 / (1.0 + np.exp(-features))
        probabilities = probabilities / np.sum(probabilities, axis=1, keepdims=True)
        predictions = np.argmax(probabilities, axis=1)

        prediction_time = (time.time() - start_time) * 1000

        return {
            "rows": len(features),
            "prediction_time_ms": prediction_time,
            "throughput_rows_per_sec": len(features) / (prediction_time / 1000),
            "vectorized": True,
        }

    async def _test_batch_prediction(self, features: np.ndarray) -> Dict[str, Any]:
        """测试批量预测"""
        batch_sizes = [100, 1000, 10000]
        results = []

        for batch_size in batch_sizes:
            if batch_size > len(features):
                continue

            batch_features = features[:batch_size]
            start_time = time.time()

            # 批量预测
            for i in range(len(batch_features)):
                # 简化的预测逻辑
                proba = np.random.rand(3)
                pred = np.argmax(proba)

            prediction_time = (time.time() - start_time) * 1000
            throughput = batch_size / (prediction_time / 1000)

            results.append(
                {
                    "batch_size": batch_size,
                    "prediction_time_ms": prediction_time,
                    "throughput_rows_per_sec": throughput,
                }
            )

        avg_throughput = np.mean([r["throughput_rows_per_sec"] for r in results])

        return {
            "batch_sizes": batch_sizes,
            "results": results,
            "avg_throughput_rows_per_sec": avg_throughput,
        }

    async def _test_parallel_prediction(self, features: np.ndarray) -> Dict[str, Any]:
        """测试并行预测"""
        # 分割数据
        chunk_size = len(features) // 4
        feature_chunks = [features[i : i + chunk_size] for i in range(0, len(features), chunk_size)]

        start_time = time.time()

        # 并行预测
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(self._predict_chunk, chunk) for chunk in feature_chunks]
            results = await asyncio.gather(*[asyncio.wrap_future(future) for future in futures])

        prediction_time = (time.time() - start_time) * 1000
        total_rows = len(features)

        return {
            "rows": total_rows,
            "prediction_time_ms": prediction_time,
            "throughput_rows_per_sec": total_rows / (prediction_time / 1000),
            "parallel_workers": 4,
            "chunk_size": chunk_size,
        }

    def _predict_chunk(self, features: np.ndarray) -> List[int]:
        """预测数据块"""
        predictions = []
        for feature_vector in features:
            # 简化的预测逻辑
            proba = np.random.rand(3)
            pred = int(np.argmax(proba))
            predictions.append(pred)
        return predictions

    # 持续任务方法
    async def _continuous_read_task(self, test_file: Path, duration_seconds: int) -> None:
        """持续读取任务"""
        start_time = time.time()
        operation_count = 0

        while time.time() - start_time < duration_seconds:
            try:
                # 模拟读取操作
                for chunk in pd.read_csv(test_file, chunksize=100):
                    await asyncio.sleep(0.01)  # 模拟处理时间
                    operation_count += 1

            except Exception as e:
                self._metrics.total_errors += 1
                self.logger.error(f"持续读取任务异常: {e}")

        self._metrics.total_rows_read += operation_count * 100  # 假设每个chunk 100行

    async def _continuous_write_task(self, duration_seconds: int) -> None:
        """持续写入任务"""
        start_time = time.time()
        operation_count = 0

        while time.time() - start_time < duration_seconds:
            try:
                # 模拟写入操作
                await asyncio.sleep(0.05)  # 模拟写入时间
                operation_count += 1

            except Exception as e:
                self._metrics.total_errors += 1
                self.logger.error(f"持续写入任务异常: {e}")

        self._metrics.total_rows_written += operation_count

    async def _continuous_prediction_task(self, duration_seconds: int) -> None:
        """持续预测任务"""
        start_time = time.time()
        operation_count = 0

        while time.time() - start_time < duration_seconds:
            try:
                # 模拟预测操作
                features = np.random.rand(100, 13)
                probabilities = 1.0 / (1.0 + np.exp(-features))
                predictions = np.argmax(probabilities, axis=1)

                await asyncio.sleep(0.001)  # 模拟计算时间
                operation_count += len(predictions)

            except Exception as e:
                self._metrics.total_errors += 1
                self.logger.error(f"持续预测任务异常: {e}")

        self._metrics.total_rows_predicted += operation_count

    async def _monitor_resources(self, duration_seconds: int) -> None:
        """监控资源使用"""
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            current_resources = ResourceUsage.current()
            self._resource_history.append(current_resources)

            # 更新峰值指标
            self._metrics.peak_memory_mb = max(self._metrics.peak_memory_mb, current_resources.memory_usage_mb)
            self._metrics.peak_cpu_percent = max(self._metrics.peak_cpu_percent, current_resources.cpu_percent)

            await asyncio.sleep(1)  # 每秒监控一次

    async def _random_read_operation(self) -> None:
        """随机读取操作"""
        # 模拟读取
        await asyncio.sleep(0.01)

    async def _random_write_operation(self) -> None:
        """随机写入操作"""
        # 模拟写入
        await asyncio.sleep(0.02)

    async def _random_prediction_operation(self) -> None:
        """随机预测操作"""
        features = np.random.rand(100, 13)
        # 简单计算
        result = np.sum(features**2)
        await asyncio.sleep(0.001)

    async def _dummy_task(self) -> None:
        """虚拟任务"""
        await asyncio.sleep(0.1)

    async def _validate_generated_data(self, file_path: Path) -> None:
        """验证生成的数据质量"""
        # 读取文件样本进行验证
        sample_df = pd.read_csv(file_path, nrows=1000)

        # 基本验证
        assert len(sample_df) > 0, "文件为空"
        assert "match_id" in sample_df.columns, "缺少match_id列"
        assert "home_score" in sample_df.columns, "缺少home_score列"

        # 数值范围验证
        assert sample_df["home_score"].between(0, 50).all(), "home_score超出合理范围"
        assert sample_df["away_score"].between(0, 50).all(), "away_score超出合理范围"

        self.logger.info("✅ 数据质量验证通过")

    async def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
            "disk_total_gb": psutil.disk_usage("/").total / 1024 / 1024 / 1024,
            "python_version": sys.version,
            "platform": sys.platform,
        }

    async def _cleanup_test(self) -> None:
        """清理测试环境"""
        self.logger.info("🧹 清理测试环境")

        # 取消所有任务
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # 等待任务完成
        await asyncio.gather(*self._tasks, return_exceptions=True)

        # 关闭执行器
        if self._executor:
            self._executor.shutdown(wait=True)
        if self._process_executor:
            self._process_executor.shutdown(wait=True)

        # 强制垃圾回收
        gc.collect()

        self._running = False

    async def _generate_test_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        self.logger.info("📊 生成测试报告")

        total_time = (datetime.now() - self._start_time).total_seconds()
        success_rate = 1.0 - (self._metrics.total_errors / max(self._metrics.total_rows_processed, 1))

        report = {
            "test_config": {
                "target_data_size_gb": self.config.target_data_size_gb,
                "test_duration_minutes": self.config.test_duration_minutes,
                "concurrent_readers": self.config.concurrent_readers,
                "concurrent_writers": self.config.concurrent_writers,
                "concurrent_predictors": self.config.concurrent_predictors,
                "max_memory_usage_mb": self.config.max_memory_usage_mb,
                "max_cpu_usage_percent": self.config.max_cpu_usage_percent,
            },
            "performance_metrics": {
                "total_rows_processed": self._metrics.total_rows_processed,
                "total_rows_generated": self._metrics.total_rows_generated,
                "total_rows_predicted": self._metrics.total_rows_predicted,
                "total_rows_written": self.__metrics.total_rows_written,
                "total_errors": self._metrics.total_errors,
                "success_rate": success_rate,
                "test_duration_seconds": total_time,
                "peak_memory_mb": self._metrics.peak_memory_mb,
                "peak_cpu_percent": self._metrics.peak_cpu_percent,
            },
            "test_results": self._results,
            "resource_history": [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "cpu_percent": r.cpu_percent,
                    "memory_usage_mb": r.memory_usage_mb,
                }
                for r in self._resource_history[::10]  # 每10个记录取1个
            ],
            "system_info": await self._get_system_info(),
        }

        # 保存报告
        if self.config.generate_reports:
            report_file = (
                Path(self.config.output_dir) / f"stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(f"📋 测试报告已保存: {report_file}")

        return report


def process_chunk(chunk: pd.DataFrame) -> None:
    """处理数据块（模拟）"""
    # 模拟处理逻辑
    time.sleep(0.001)


# 便捷函数
async def run_50gb_stress_test(
    config: Optional[StressTestConfig] = None,
) -> Dict[str, Any]:
    """
    运行50GB压力测试

    Args:
        config: 测试配置

    Returns:
        Dict[str, Any]: 测试报告
    """
    framework = StressTestFramework(config)
    return await framework.run_comprehensive_stress_test()


def create_stress_test_config(
    target_data_size_gb: float = 50.0,
    test_duration_minutes: int = 60,
    max_memory_mb: float = 4096.0,
    enable_detailed_logging: bool = True,
) -> StressTestConfig:
    """
    创建压力测试配置

    Args:
        target_data_size_gb: 目标数据大小(GB)
        test_duration_minutes: 测试时长(分钟)
        max_memory_mb: 最大内存使用(MB)
        enable_detailed_logging: 启用详细日志

    Returns:
        StressTestConfig: 测试配置
    """
    return StressTestConfig(
        target_data_size_gb=target_data_size_gb,
        test_duration_minutes=test_duration_minutes,
        max_memory_usage_mb=max_memory_mb,
        enable_detailed_logging=enable_detailed_logging,
        generate_reports=True,
    )
