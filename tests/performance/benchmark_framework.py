#!/usr/bin/env python3
"""
性能基准测试框架 - Sprint 7 性能测试封装

基于Sprint 4压力测试框架，封装为可定期运行的基准测试系统。
提供标准化的性能基准测试、回归检测和性能趋势分析。

核心功能：
1. 标准化性能基准测试
2. 自动化性能回归检测
3. 性能趋势分析和报告
4. CI/CD集成支持
5. 性能数据持久化
6. 资源使用监控
7. 多环境性能对比

Author: Football Prediction Team
Version: 1.0.0 (Sprint 7 Performance Testing)
"""

import asyncio
import json
import logging
import time
import statistics
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import numpy as np
import pandas as pd
import psutil
import sys
import traceback
import subprocess
import tempfile
import gc
import sqlite3
from contextlib import asynccontextmanager

# 导入项目模块
from src.testing.stress_test_framework import (
    StressTestFramework, StressTestConfig, ResourceUsage, PerformanceMetrics
)
from src.services.prediction_service import PredictionService
from src.services.collection_service import FotMobCollectionService
from src.ml.inference.predictor import Predictor

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfig:
    """基准测试配置"""
    # 测试标识
    benchmark_name: str
    benchmark_version: str = "1.0.0"
    environment: str = "development"  # development, staging, production

    # 测试规模
    small_dataset_size: int = 1000      # 小数据集：1K记录
    medium_dataset_size: int = 10000   # 中数据集：10K记录
    large_dataset_size: int = 100000   # 大数据集：100K记录

    # 性能目标（毫秒）
    target_prediction_time_ms: float = 50.0
    target_batch_prediction_time_ms: float = 100.0
    target_collection_time_ms: float = 2000.0
    target_end_to_end_time_ms: float = 5000.0

    # 资源限制
    max_memory_mb: float = 2048.0
    max_cpu_percent: float = 80.0
    max_disk_io_mb: float = 100.0

    # 测试参数
    concurrent_users: int = 10
    test_duration_seconds: int = 300  # 5分钟
    warmup_iterations: int = 10

    # 输出配置
    output_dir: str = "benchmark_results"
    enable_comparison: bool = True
    enable_regression_detection: bool = True
    regression_threshold_percent: float = 10.0

    # 报告配置
    generate_html_report: bool = True
    generate_json_report: bool = True
    enable_detailed_metrics: bool = True
    save_raw_data: bool = False


@dataclass
class BenchmarkResult:
    """单次基准测试结果"""
    benchmark_name: str
    test_name: str
    timestamp: datetime
    environment: str
    dataset_size: int

    # 性能指标
    execution_time_ms: float
    throughput_ops_per_sec: float
    memory_peak_mb: float
    cpu_peak_percent: float

    # 错误信息
    success: bool
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None

    # 附加指标
    additional_metrics: Dict[str, Any] = field(default_factory=dict)

    # 元数据
    python_version: str = sys.version
    platform: str = sys.platform
    hostname: str = field(default_factory=lambda: psutil.os.uname().nodename)


@dataclass
class BenchmarkReport:
    """基准测试报告"""
    report_id: str
    benchmark_name: str
    timestamp: datetime
    environment: str
    config: BenchmarkConfig

    # 测试结果汇总
    total_tests: int
    passed_tests: int
    failed_tests: int
    success_rate: float

    # 性能指标汇总
    avg_execution_time_ms: float
    min_execution_time_ms: float
    max_execution_time_ms: float
    median_execution_time_ms: float
    p95_execution_time_ms: float
    p99_execution_time_ms: float

    # 详细结果
    test_results: List[BenchmarkResult] = field(default_factory=list)

    # 回归检测结果
    regression_detected: bool = False
    regression_details: List[Dict[str, Any]] = field(default_factory=list)

    # 趋势分析
    performance_trend: str = "stable"  # improving, degrading, stable
    trend_change_percent: float = 0.0

    # 系统信息
    system_info: Dict[str, Any] = field(default_factory=dict)


class BenchmarkDatabase:
    """基准测试数据库"""

    def __init__(self, db_path: str = "benchmark_results.db"):
        self.db_path = Path(db_path)
        self.conn = None
        self._initialize_database()

    def _initialize_database(self):
        """初始化数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_name TEXT NOT NULL,
                test_name TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                environment TEXT NOT NULL,
                dataset_size INTEGER NOT NULL,
                execution_time_ms REAL NOT NULL,
                throughput_ops_per_sec REAL NOT NULL,
                memory_peak_mb REAL NOT NULL,
                cpu_peak_percent REAL NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                additional_metrics TEXT,
                python_version TEXT,
                platform TEXT,
                hostname TEXT
            )
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_benchmark_name
            ON benchmark_results(benchmark_name, timestamp DESC)
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_environment
            ON benchmark_results(environment, timestamp DESC)
        """)

        self.conn.commit()

    def save_result(self, result: BenchmarkResult):
        """保存测试结果"""
        additional_metrics_json = json.dumps(result.additional_metrics) if result.additional_metrics else None

        self.conn.execute("""
            INSERT INTO benchmark_results (
                benchmark_name, test_name, timestamp, environment, dataset_size,
                execution_time_ms, throughput_ops_per_sec, memory_peak_mb, cpu_peak_percent,
                success, error_message, additional_metrics, python_version, platform, hostname
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.benchmark_name, result.test_name, result.timestamp, result.environment,
            result.dataset_size, result.execution_time_ms, result.throughput_ops_per_sec,
            result.memory_peak_mb, result.cpu_peak_percent, result.success,
            result.error_message, additional_metrics_json, result.python_version,
            result.platform, result.hostname
        ))

        self.conn.commit()

    def get_historical_results(
        self,
        benchmark_name: str,
        test_name: Optional[str] = None,
        environment: Optional[str] = None,
        days_back: int = 30
    ) -> List[BenchmarkResult]:
        """获取历史结果"""
        query = """
            SELECT * FROM benchmark_results
            WHERE benchmark_name = ? AND timestamp >= datetime('now', '-{} days')
        """.format(days_back)

        params = [benchmark_name]

        if test_name:
            query += " AND test_name = ?"
            params.append(test_name)

        if environment:
            query += " AND environment = ?"
            params.append(environment)

        query += " ORDER BY timestamp DESC"

        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            additional_metrics = json.loads(row[11]) if row[11] else {}
            result = BenchmarkResult(
                benchmark_name=row[1],
                test_name=row[2],
                timestamp=datetime.fromisoformat(row[3]),
                environment=row[4],
                dataset_size=row[5],
                execution_time_ms=row[6],
                throughput_ops_per_sec=row[7],
                memory_peak_mb=row[8],
                cpu_peak_percent=row[9],
                success=bool(row[10]),
                error_message=row[11],
                additional_metrics=additional_metrics,
                python_version=row[13],
                platform=row[14],
                hostname=row[15]
            )
            results.append(result)

        return results

    def get_performance_stats(
        self,
        benchmark_name: str,
        test_name: str,
        environment: Optional[str] = None,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """获取性能统计"""
        results = self.get_historical_results(benchmark_name, test_name, environment, days_back)

        if not results:
            return {}

        execution_times = [r.execution_time_ms for r in results if r.success]

        if not execution_times:
            return {}

        return {
            'count': len(execution_times),
            'mean_ms': statistics.mean(execution_times),
            'median_ms': statistics.median(execution_times),
            'min_ms': min(execution_times),
            'max_ms': max(execution_times),
            'std_ms': statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
            'p95_ms': np.percentile(execution_times, 95),
            'p99_ms': np.percentile(execution_times, 99)
        }


class PerformanceBenchmarkFramework:
    """性能基准测试框架"""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # 初始化组件
        self.db = BenchmarkDatabase()
        self.results: List[BenchmarkResult] = []
        self.start_time = None

        # 创建输出目录
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # 初始化服务（用于测试）
        self.prediction_service = None
        self.collection_service = None
        self.predictor = None

    async def run_comprehensive_benchmark(self) -> BenchmarkReport:
        """运行综合基准测试"""
        self.logger.info(f"🚀 开始基准测试: {self.config.benchmark_name}")
        self.start_time = datetime.now()

        try:
            # 1. 环境准备
            await self._prepare_environment()

            # 2. 运行各项基准测试
            test_tasks = [
                self._benchmark_prediction_performance(),
                self._benchmark_batch_prediction_performance(),
                self._benchmark_data_collection_performance(),
                self._benchmark_end_to_end_workflow(),
                self._benchmark_concurrent_load(),
                self._benchmark_memory_usage(),
                self._benchmark_scalability()
            ]

            # 并发执行测试
            test_results = await asyncio.gather(*test_tasks, return_exceptions=True)

            # 处理结果
            for i, result in enumerate(test_results):
                if isinstance(result, Exception):
                    self.logger.error(f"测试任务 {i} 失败: {result}")
                    # 创建错误结果
                    error_result = BenchmarkResult(
                        benchmark_name=self.config.benchmark_name,
                        test_name=f"task_{i}",
                        timestamp=datetime.now(),
                        environment=self.config.environment,
                        dataset_size=0,
                        execution_time_ms=0,
                        throughput_ops_per_sec=0,
                        memory_peak_mb=0,
                        cpu_peak_percent=0,
                        success=False,
                        error_message=str(result),
                        error_traceback=traceback.format_exc()
                    )
                    self.results.append(error_result)
                else:
                    if isinstance(result, list):
                        self.results.extend(result)
                    else:
                        self.results.append(result)

            # 3. 生成报告
            report = await self._generate_report()

            # 4. 检测回归
            if self.config.enable_regression_detection:
                await self._detect_regressions(report)

            # 5. 保存结果
            await self._save_results(report)

            return report

        except Exception as e:
            self.logger.error(f"基准测试失败: {e}")
            raise
        finally:
            await self._cleanup()

    async def _prepare_environment(self):
        """准备测试环境"""
        self.logger.info("🔧 准备测试环境")

        # 收集系统信息
        system_info = {
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
            'disk_total_gb': psutil.disk_usage('/').total / 1024 / 1024 / 1024,
            'python_version': sys.version,
            'platform': sys.platform,
            'hostname': psutil.os.uname().nodename
        }

        self.logger.info(f"系统信息: {system_info}")

        # 初始化服务（如果需要）
        try:
            # 这里可以初始化实际的服务实例进行测试
            # prediction_service = PredictionService()
            # await prediction_service.initialize()
            pass
        except Exception as e:
            self.logger.warning(f"服务初始化失败（将使用模拟）: {e}")

    async def _benchmark_prediction_performance(self) -> List[BenchmarkResult]:
        """基准测试：预测性能"""
        self.logger.info("🤖 测试预测性能")
        results = []

        # 测试不同数据规模的预测性能
        dataset_sizes = [
            (self.config.small_dataset_size, "small"),
            (self.config.medium_dataset_size, "medium"),
            (self.config.large_dataset_size, "large")
        ]

        for size, size_label in dataset_sizes:
            try:
                result = await self._run_prediction_benchmark(size, size_label)
                results.append(result)

                # 检查是否达到性能目标
                if result.execution_time_ms > self.config.target_prediction_time_ms:
                    self.logger.warning(
                        f"预测性能未达标: {result.execution_time_ms:.2f}ms > "
                        f"{self.config.target_prediction_time_ms}ms"
                    )

            except Exception as e:
                self.logger.error(f"预测性能测试失败 ({size_label}): {e}")
                results.append(BenchmarkResult(
                    benchmark_name=self.config.benchmark_name,
                    test_name=f"prediction_performance_{size_label}",
                    timestamp=datetime.now(),
                    environment=self.config.environment,
                    dataset_size=size,
                    execution_time_ms=0,
                    throughput_ops_per_sec=0,
                    memory_peak_mb=0,
                    cpu_peak_percent=0,
                    success=False,
                    error_message=str(e)
                ))

        return results

    async def _run_prediction_benchmark(self, dataset_size: int, size_label: str) -> BenchmarkResult:
        """运行单个预测基准测试"""
        # 预热
        for _ in range(self.config.warmup_iterations):
            await self._simulate_prediction(100)

        # 实际测试
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        peak_memory = start_memory

        # 执行预测
        operations = 0
        test_duration = 60  # 60秒测试
        end_time = start_time + test_duration

        while time.time() < end_time:
            await self._simulate_prediction(dataset_size // 100)  # 分批执行
            operations += 1

            # 监控内存使用
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            peak_memory = max(peak_memory, current_memory)

        execution_time = (time.time() - start_time) * 1000  # 转换为毫秒
        throughput = (dataset_size * operations) / (execution_time / 1000)
        cpu_usage = psutil.cpu_percent(interval=1)

        return BenchmarkResult(
            benchmark_name=self.config.benchmark_name,
            test_name=f"prediction_performance_{size_label}",
            timestamp=datetime.now(),
            environment=self.config.environment,
            dataset_size=dataset_size,
            execution_time_ms=execution_time,
            throughput_ops_per_sec=throughput,
            memory_peak_mb=peak_memory - start_memory,
            cpu_peak_percent=cpu_usage,
            success=True,
            additional_metrics={
                'operations': operations,
                'test_duration_s': test_duration,
                'dataset_size_per_operation': dataset_size // 100
            }
        )

    async def _simulate_prediction(self, data_size: int):
        """模拟预测操作"""
        # 生成模拟特征数据
        features = np.random.rand(data_size, 13)

        # 模拟预测计算
        probabilities = 1.0 / (1.0 + np.exp(-features))
        probabilities = probabilities / np.sum(probabilities, axis=1, keepdims=True)
        predictions = np.argmax(probabilities, axis=1)

        # 模拟少量处理时间
        await asyncio.sleep(0.001)

        return predictions

    async def _benchmark_batch_prediction_performance(self) -> List[BenchmarkResult]:
        """基准测试：批量预测性能"""
        self.logger.info("📦 测试批量预测性能")
        results = []

        batch_sizes = [10, 50, 100, 500, 1000]

        for batch_size in batch_sizes:
            try:
                # 预热
                for _ in range(self.config.warmup_iterations):
                    await self._simulate_batch_prediction(batch_size, 10)

                # 实际测试
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024

                # 执行批量预测
                predictions = await self._simulate_batch_prediction(batch_size, 100)

                execution_time = (time.time() - start_time) * 1000
                memory_usage = psutil.Process().memory_info().rss / 1024 / 1024 - start_memory
                throughput = (batch_size * 100) / (execution_time / 1000)

                result = BenchmarkResult(
                    benchmark_name=self.config.benchmark_name,
                    test_name=f"batch_prediction_batch_size_{batch_size}",
                    timestamp=datetime.now(),
                    environment=self.config.environment,
                    dataset_size=batch_size * 100,
                    execution_time_ms=execution_time,
                    throughput_ops_per_sec=throughput,
                    memory_peak_mb=memory_usage,
                    cpu_peak_percent=psutil.cpu_percent(interval=1),
                    success=True,
                    additional_metrics={
                        'batch_size': batch_size,
                        'total_predictions': len(predictions),
                        'predictions_per_batch': batch_size
                    }
                )

                results.append(result)

                # 检查性能目标
                if execution_time > self.config.target_batch_prediction_time_ms:
                    self.logger.warning(
                        f"批量预测性能未达标: {execution_time:.2f}ms > "
                        f"{self.config.target_batch_prediction_time_ms}ms"
                    )

            except Exception as e:
                self.logger.error(f"批量预测测试失败 (batch_size={batch_size}): {e}")
                results.append(BenchmarkResult(
                    benchmark_name=self.config.benchmark_name,
                    test_name=f"batch_prediction_batch_size_{batch_size}",
                    timestamp=datetime.now(),
                    environment=self.config.environment,
                    dataset_size=batch_size * 100,
                    execution_time_ms=0,
                    throughput_ops_per_sec=0,
                    memory_peak_mb=0,
                    cpu_peak_percent=0,
                    success=False,
                    error_message=str(e)
                ))

        return results

    async def _simulate_batch_prediction(self, batch_size: int, num_batches: int) -> List[np.ndarray]:
        """模拟批量预测"""
        results = []

        for _ in range(num_batches):
            # 生成批量特征数据
            features = np.random.rand(batch_size, 13)

            # 批量预测计算
            probabilities = 1.0 / (1.0 + np.exp(-features))
            probabilities = probabilities / np.sum(probabilities, axis=1, keepdims=True)
            predictions = np.argmax(probabilities, axis=1)

            results.append(predictions)

            # 模拟处理时间
            await asyncio.sleep(0.005)

        return results

    async def _benchmark_data_collection_performance(self) -> List[BenchmarkResult]:
        """基准测试：数据收集性能"""
        self.logger.info("📊 测试数据收集性能")
        results = []

        # 测试不同数据规模的收集性能
        test_scenarios = [
            ("single_match", 1, "单场比赛数据收集"),
            ("multiple_matches", 10, "多场比赛数据收集"),
            ("league_data", 50, "联赛数据收集")
        ]

        for scenario_name, match_count, description in test_scenarios:
            try:
                result = await self._run_collection_benchmark(scenario_name, match_count, description)
                results.append(result)

                # 检查性能目标
                if result.execution_time_ms > self.config.target_collection_time_ms:
                    self.logger.warning(
                        f"数据收集性能未达标: {result.execution_time_ms:.2f}ms > "
                        f"{self.config.target_collection_time_ms}ms"
                    )

            except Exception as e:
                self.logger.error(f"数据收集测试失败 ({scenario_name}): {e}")
                results.append(BenchmarkResult(
                    benchmark_name=self.config.benchmark_name,
                    test_name=f"data_collection_{scenario_name}",
                    timestamp=datetime.now(),
                    environment=self.config.environment,
                    dataset_size=match_count,
                    execution_time_ms=0,
                    throughput_ops_per_sec=0,
                    memory_peak_mb=0,
                    cpu_peak_percent=0,
                    success=False,
                    error_message=str(e)
                ))

        return results

    async def _run_collection_benchmark(self, scenario_name: str, match_count: int, description: str) -> BenchmarkResult:
        """运行数据收集基准测试"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # 模拟数据收集
        collected_data = []
        for i in range(match_count):
            # 模拟单场比赛数据收集
            match_data = {
                'match_id': f"match_{i:06d}",
                'home_team': f"Team_{i % 100}",
                'away_team': f"Team_{(i + 1) % 100}",
                'league': f"League_{i % 20}",
                'timestamp': datetime.now().isoformat(),
                'features': np.random.rand(13).tolist(),
                'odds': {
                    'home_win': round(np.random.uniform(1.5, 5.0), 2),
                    'draw': round(np.random.uniform(2.5, 4.0), 2),
                    'away_win': round(np.random.uniform(2.0, 6.0), 2)
                }
            }

            # 模拟网络延迟
            await asyncio.sleep(0.01)
            collected_data.append(match_data)

        execution_time = (time.time() - start_time) * 1000
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024 - start_memory
        throughput = match_count / (execution_time / 1000)

        return BenchmarkResult(
            benchmark_name=self.config.benchmark_name,
            test_name=f"data_collection_{scenario_name}",
            timestamp=datetime.now(),
            environment=self.config.environment,
            dataset_size=match_count,
            execution_time_ms=execution_time,
            throughput_ops_per_sec=throughput,
            memory_peak_mb=memory_usage,
            cpu_peak_percent=psutil.cpu_percent(interval=1),
            success=True,
            additional_metrics={
                'description': description,
                'data_points_collected': len(collected_data),
                'avg_time_per_match_ms': execution_time / match_count
            }
        )

    async def _benchmark_end_to_end_workflow(self) -> List[BenchmarkResult]:
        """基准测试：端到端工作流性能"""
        self.logger.info("🔄 测试端到端工作流性能")
        results = []

        # 测试场景
        workflow_scenarios = [
            ("real_time_prediction", 1, "实时预测工作流"),
            ("batch_analysis", 100, "批量分析工作流"),
            ("historical_backtest", 1000, "历史回测工作流")
        ]

        for scenario_name, data_points, description in workflow_scenarios:
            try:
                result = await self._run_end_to_end_benchmark(scenario_name, data_points, description)
                results.append(result)

                # 检查端到端性能目标
                if result.execution_time_ms > self.config.target_end_to_end_time_ms:
                    self.logger.warning(
                        f"端到端工作流性能未达标: {result.execution_time_ms:.2f}ms > "
                        f"{self.config.target_end_to_end_time_ms}ms"
                    )

            except Exception as e:
                self.logger.error(f"端到端工作流测试失败 ({scenario_name}): {e}")
                results.append(BenchmarkResult(
                    benchmark_name=self.config.benchmark_name,
                    test_name=f"end_to_end_{scenario_name}",
                    timestamp=datetime.now(),
                    environment=self.config.environment,
                    dataset_size=data_points,
                    execution_time_ms=0,
                    throughput_ops_per_sec=0,
                    memory_peak_mb=0,
                    cpu_peak_percent=0,
                    success=False,
                    error_message=str(e)
                ))

        return results

    async def _run_end_to_end_benchmark(self, scenario_name: str, data_points: int, description: str) -> BenchmarkResult:
        """运行端到端工作流基准测试"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1022
        peak_memory = start_memory

        # 模拟端到端工作流
        workflow_stages = [
            ("data_collection", 0.2),  # 20%的时间
            ("feature_extraction", 0.3),  # 30%的时间
            ("model_prediction", 0.4),  # 40%的时间
            ("result_processing", 0.1)   # 10%的时间
        ]

        processed_data = []
        for i in range(data_points):
            workflow_data = {
                'id': f"workflow_{i:06d}",
                'stages': {}
            }

            for stage_name, time_ratio in workflow_stages:
                stage_start = time.time()

                # 模拟阶段处理
                if stage_name == "data_collection":
                    await asyncio.sleep(0.001 * time_ratio)
                    workflow_data['stages'][stage_name] = {'data_collected': True}

                elif stage_name == "feature_extraction":
                    features = np.random.rand(13)
                    workflow_data['stages'][stage_name] = {'features': features.tolist()}
                    await asyncio.sleep(0.002 * time_ratio)

                elif stage_name == "model_prediction":
                    prediction = np.random.randint(0, 3)
                    probabilities = np.random.rand(3)
                    probabilities = probabilities / np.sum(probabilities)
                    workflow_data['stages'][stage_name] = {
                        'prediction': int(prediction),
                        'probabilities': probabilities.tolist()
                    }
                    await asyncio.sleep(0.003 * time_ratio)

                elif stage_name == "result_processing":
                    result = {
                        'success': True,
                        'confidence': np.random.rand()
                    }
                    workflow_data['stages'][stage_name] = result
                    await asyncio.sleep(0.0005 * time_ratio)

                # 监控内存使用
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)

            processed_data.append(workflow_data)

        execution_time = (time.time() - start_time) * 1000
        memory_usage = peak_memory - start_memory
        throughput = data_points / (execution_time / 1000)

        return BenchmarkResult(
            benchmark_name=self.config.benchmark_name,
            test_name=f"end_to_end_{scenario_name}",
            timestamp=datetime.now(),
            environment=self.config.environment,
            dataset_size=data_points,
            execution_time_ms=execution_time,
            throughput_ops_per_sec=throughput,
            memory_peak_mb=memory_usage,
            cpu_peak_percent=psutil.cpu_percent(interval=1),
            success=True,
            additional_metrics={
                'description': description,
                'workflows_completed': len(processed_data),
                'avg_time_per_workflow_ms': execution_time / data_points,
                'stages_per_workflow': len(workflow_stages)
            }
        )

    async def _benchmark_concurrent_load(self) -> List[BenchmarkResult]:
        """基准测试：并发负载性能"""
        self.logger.info("⚡ 测试并发负载性能")
        results = []

        # 测试不同并发级别
        concurrency_levels = [1, 5, 10, 20, 50]

        for concurrency in concurrency_levels:
            try:
                result = await self._run_concurrent_benchmark(concurrency)
                results.append(result)

            except Exception as e:
                self.logger.error(f"并发负载测试失败 (concurrency={concurrency}): {e}")
                results.append(BenchmarkResult(
                    benchmark_name=self.config.benchmark_name,
                    test_name=f"concurrent_load_level_{concurrency}",
                    timestamp=datetime.now(),
                    environment=self.config.environment,
                    dataset_size=concurrency,
                    execution_time_ms=0,
                    throughput_ops_per_sec=0,
                    memory_peak_mb=0,
                    cpu_peak_percent=0,
                    success=False,
                    error_message=str(e)
                ))

        return results

    async def _run_concurrent_benchmark(self, concurrency: int) -> BenchmarkResult:
        """运行并发负载基准测试"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # 创建并发任务
        async def concurrent_task(task_id: int):
            """单个并发任务"""
            task_start = time.time()

            # 模拟预测工作
            for i in range(10):
                features = np.random.rand(13)
                probabilities = 1.0 / (1.0 + np.exp(-features))
                predictions = np.argmax(probabilities)
                await asyncio.sleep(0.001)

            return time.time() - task_start

        # 执行并发任务
        tasks = [concurrent_task(i) for i in range(concurrency)]
        task_results = await asyncio.gather(*tasks)

        execution_time = (time.time() - start_time) * 1000
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024 - start_memory

        # 计算统计指标
        total_operations = sum(10 for _ in range(concurrency))  # 每个任务10次操作
        avg_task_time = statistics.mean(task_results) * 1000  # 转换为毫秒

        return BenchmarkResult(
            benchmark_name=self.config.benchmark_name,
            test_name=f"concurrent_load_level_{concurrency}",
            timestamp=datetime.now(),
            environment=self.config.environment,
            dataset_size=concurrency,
            execution_time_ms=execution_time,
            throughput_ops_per_sec=total_operations / (execution_time / 1000),
            memory_peak_mb=memory_usage,
            cpu_peak_percent=psutil.cpu_percent(interval=1),
            success=True,
            additional_metrics={
                'concurrency_level': concurrency,
                'total_operations': total_operations,
                'avg_task_time_ms': avg_task_time,
                'max_task_time_ms': max(t * 1000 for t in task_results),
                'min_task_time_ms': min(t * 1000 for t in task_results)
            }
        )

    async def _benchmark_memory_usage(self) -> List[BenchmarkResult]:
        """基准测试：内存使用性能"""
        self.logger.info("💾 测试内存使用性能")
        results = []

        # 测试不同数据规模的内存使用
        memory_test_sizes = [
            (1000, "1K records"),
            (10000, "10K records"),
            (100000, "100K records"),
            (1000000, "1M records")
        ]

        for size, size_label in memory_test_sizes:
            try:
                result = await self._run_memory_benchmark(size, size_label)
                results.append(result)

                # 检查内存限制
                if result.memory_peak_mb > self.config.max_memory_mb:
                    self.logger.warning(
                        f"内存使用超限: {result.memory_peak_mb:.2f}MB > "
                        f"{self.config.max_memory_mb}MB"
                    )

            except Exception as e:
                self.logger.error(f"内存使用测试失败 ({size_label}): {e}")
                results.append(BenchmarkResult(
                    benchmark_name=self.config.benchmark_name,
                    test_name=f"memory_usage_{size_label.replace(' ', '_')}",
                    timestamp=datetime.now(),
                    environment=self.config.environment,
                    dataset_size=size,
                    execution_time_ms=0,
                    throughput_ops_per_sec=0,
                    memory_peak_mb=0,
                    cpu_peak_percent=0,
                    success=False,
                    error_message=str(e)
                ))

        return results

    async def _run_memory_benchmark(self, size: int, size_label: str) -> BenchmarkResult:
        """运行内存使用基准测试"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # 创建大型数据结构
        data_chunks = []
        chunk_size = 1000

        for i in range(size // chunk_size):
            # 创建数据块
            chunk = {
                'features': np.random.rand(chunk_size, 13),
                'predictions': np.random.randint(0, 3, chunk_size),
                'probabilities': np.random.rand(chunk_size, 3),
                'metadata': {
                    'batch_id': i,
                    'created_at': datetime.now().isoformat(),
                    'size': chunk_size
                }
            }
            data_chunks.append(chunk)

            # 模拟处理时间
            await asyncio.sleep(0.001)

        # 测量峰值内存
        peak_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_usage = peak_memory - start_memory

        # 计算操作
        total_operations = len(data_chunks) * chunk_size
        execution_time = (time.time() - start_time) * 1000

        # 清理内存
        del data_chunks
        gc.collect()

        return BenchmarkResult(
            benchmark_name=self.config.benchmark_name,
            test_name=f"memory_usage_{size_label.replace(' ', '_')}",
            timestamp=datetime.now(),
            environment=self.config.environment,
            dataset_size=size,
            execution_time_ms=execution_time,
            throughput_ops_per_sec=total_operations / (execution_time / 1000),
            memory_peak_mb=memory_usage,
            cpu_peak_percent=psutil.cpu_percent(interval=1),
            success=True,
            additional_metrics={
                'size_label': size_label,
                'data_chunks': len(data_chunks),
                'chunk_size': chunk_size,
                'memory_per_record_bytes': (memory_usage * 1024 * 1024) / size
            }
        )

    async def _benchmark_scalability(self) -> List[BenchmarkResult]:
        """基准测试：可扩展性性能"""
        self.logger.info("📈 测试可扩展性性能")
        results = []

        # 测试线性扩展性
        scaling_factors = [1, 2, 5, 10]

        for factor in scaling_factors:
            try:
                base_size = self.config.medium_dataset_size
                test_size = base_size * factor

                result = await self._run_scalability_benchmark(factor, test_size)
                results.append(result)

            except Exception as e:
                self.logger.error(f"可扩展性测试失败 (factor={factor}): {e}")
                results.append(BenchmarkResult(
                    benchmark_name=self.config.benchmark_name,
                    test_name=f"scalability_factor_{factor}",
                    timestamp=datetime.now(),
                    environment=self.config.environment,
                    dataset_size=test_size,
                    execution_time_ms=0,
                    throughput_ops_per_sec=0,
                    memory_peak_mb=0,
                    cpu_peak_percent=0,
                    success=False,
                    error_message=str(e)
                ))

        return results

    async def _run_scalability_benchmark(self, factor: int, test_size: int) -> BenchmarkResult:
        """运行可扩展性基准测试"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # 执行扩展性测试
        processed_count = 0
        batch_size = 1000

        while processed_count < test_size:
            # 处理批次
            batch_data = np.random.rand(min(batch_size, test_size - processed_count), 13)

            # 模拟预测计算
            probabilities = 1.0 / (1.0 + np.exp(-batch_data))
            predictions = np.argmax(probabilities, axis=1)

            processed_count += len(batch_data)
            await asyncio.sleep(0.001)

        execution_time = (time.time() - start_time) * 1000
        memory_usage = psutil.Process().memory_info().rss / 1024 / 1024 - start_memory
        throughput = test_size / (execution_time / 1000)

        # 计算扩展性指标
        efficiency = (1.0 / factor) * (throughput / (self.config.medium_dataset_size / 100))  # 相对效率

        return BenchmarkResult(
            benchmark_name=self.config.benchmark_name,
            test_name=f"scalability_factor_{factor}",
            timestamp=datetime.now(),
            environment=self.config.environment,
            dataset_size=test_size,
            execution_time_ms=execution_time,
            throughput_ops_per_sec=throughput,
            memory_peak_mb=memory_usage,
            cpu_peak_percent=psutil.cpu_percent(interval=1),
            success=True,
            additional_metrics={
                'scaling_factor': factor,
                'efficiency_score': efficiency,
                'linear_scaling_expected': factor,
                'actual_throughput_ratio': throughput / (self.config.medium_dataset_size / 100)
            }
        )

    async def _generate_report(self) -> BenchmarkReport:
        """生成基准测试报告"""
        self.logger.info("📊 生成基准测试报告")

        # 计算基本统计
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.success])
        failed_tests = total_tests - passed_tests
        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        # 计算性能指标
        execution_times = [r.execution_time_ms for r in self.results if r.success]

        if execution_times:
            avg_execution_time = statistics.mean(execution_times)
            min_execution_time = min(execution_times)
            max_execution_time = max(execution_times)
            median_execution_time = statistics.median(execution_times)
            p95_execution_time = np.percentile(execution_times, 95)
            p99_execution_time = np.percentile(execution_times, 99)
        else:
            avg_execution_time = min_execution_time = max_execution_time = 0
            median_execution_time = p95_execution_time = p99_execution_time = 0

        # 收集系统信息
        system_info = {
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
            'disk_total_gb': psutil.disk_usage('/').total / 1024 / 1024 / 1024,
            'python_version': sys.version,
            'platform': sys.platform,
            'hostname': psutil.os.uname().nodename,
            'benchmark_duration_s': (datetime.now() - self.start_time).total_seconds()
        }

        # 生成报告ID
        report_id = hashlib.md5(
            f"{self.config.benchmark_name}_{self.config.environment}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]

        report = BenchmarkReport(
            report_id=report_id,
            benchmark_name=self.config.benchmark_name,
            timestamp=datetime.now(),
            environment=self.config.environment,
            config=self.config,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            success_rate=success_rate,
            avg_execution_time_ms=avg_execution_time,
            min_execution_time_ms=min_execution_time,
            max_execution_time_ms=max_execution_time,
            median_execution_time_ms=median_execution_time,
            p95_execution_time_ms=p95_execution_time,
            p99_execution_time_ms=p99_execution_time,
            test_results=self.results,
            system_info=system_info
        )

        return report

    async def _detect_regressions(self, report: BenchmarkReport):
        """检测性能回归"""
        self.logger.info("🔍 检测性能回归")

        regressions = []

        for result in report.test_results:
            if not result.success:
                continue

            # 获取历史性能数据
            historical_stats = self.db.get_performance_stats(
                result.benchmark_name,
                result.test_name,
                result.environment,
                days_back=7
            )

            if historical_stats:
                # 计算回归
                historical_avg = historical_stats['mean_ms']
                current_time = result.execution_time_ms

                if historical_avg > 0:
                    regression_percent = ((current_time - historical_avg) / historical_avg) * 100

                    if regression_percent > self.config.regression_threshold_percent:
                        regressions.append({
                            'test_name': result.test_name,
                            'current_time_ms': current_time,
                            'historical_avg_ms': historical_avg,
                            'regression_percent': regression_percent,
                            'severity': 'high' if regression_percent > 50 else 'medium'
                        })

        report.regression_detected = len(regressions) > 0
        report.regression_details = regressions

        if report.regression_detected:
            self.logger.warning(f"检测到 {len(regressions)} 个性能回归")
            for regression in regressions:
                self.logger.warning(
                    f"  - {regression['test_name']}: {regression['regression_percent']:.1f}% 回归"
                )

    async def _save_results(self, report: BenchmarkReport):
        """保存测试结果"""
        self.logger.info("💾 保存测试结果")

        # 保存到数据库
        for result in report.test_results:
            self.db.save_result(result)

        # 保存JSON报告
        if self.config.generate_json_report:
            json_file = self.output_dir / f"benchmark_report_{report.report_id}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(report), f, indent=2, default=str)

            self.logger.info(f"JSON报告已保存: {json_file}")

        # 保存HTML报告
        if self.config.generate_html_report:
            html_file = self.output_dir / f"benchmark_report_{report.report_id}.html"
            await self._generate_html_report(report, html_file)

            self.logger.info(f"HTML报告已保存: {html_file}")

        # 保存原始数据（如果启用）
        if self.config.save_raw_data:
            raw_data_file = self.output_dir / f"benchmark_raw_data_{report.report_id}.json"
            with open(raw_data_file, 'w', encoding='utf-8') as f:
                raw_data = {
                    'config': asdict(self.config),
                    'results': [asdict(r) for r in self.results],
                    'system_info': report.system_info
                }
                json.dump(raw_data, f, indent=2, default=str)

            self.logger.info(f"原始数据已保存: {raw_data_file}")

    async def _generate_html_report(self, report: BenchmarkReport, output_file: Path):
        """生成HTML报告"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>基准测试报告 - {benchmark_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .test-result {{ border: 1px solid #ddd; margin: 10px 0; padding: 10px; }}
                .success {{ border-left: 5px solid #28a745; }}
                .failure {{ border-left: 5px solid #dc3545; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .metric {{ display: inline-block; margin: 5px 10px; padding: 5px; background-color: #e9ecef; border-radius: 3px; }}
                .regression {{ color: #dc3545; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>基准测试报告</h1>
                <p><strong>基准名称:</strong> {benchmark_name}</p>
                <p><strong>环境:</strong> {environment}</p>
                <p><strong>时间:</strong> {timestamp}</p>
                <p><strong>报告ID:</strong> {report_id}</p>
            </div>

            <div class="summary">
                <h2>测试摘要</h2>
                <div class="metric">总测试数: {total_tests}</div>
                <div class="metric">通过测试: {passed_tests}</div>
                <div class="metric">失败测试: {failed_tests}</div>
                <div class="metric">成功率: {success_rate:.1%}</div>

                <h3>性能指标</h3>
                <div class="metric">平均执行时间: {avg_execution_time_ms:.2f}ms</div>
                <div class="metric">中位数执行时间: {median_execution_time_ms:.2f}ms</div>
                <div class="metric">P95执行时间: {p95_execution_time_ms:.2f}ms</div>
                <div class="metric">P99执行时间: {p99_execution_time_ms:.2f}ms</div>

                {regression_section}
            </div>

            <h2>详细测试结果</h2>
            {test_results_table}
        </body>
        </html>
        """

        # 生成回归检测部分
        regression_section = ""
        if report.regression_detected:
            regression_html = "<h3 class='regression'>⚠️ 检测到性能回归</h3><ul>"
            for regression in report.regression_details:
                regression_html += f"<li><strong>{regression['test_name']}</strong>: {regression['regression_percent']:.1f}% 回归</li>"
            regression_html += "</ul>"
            regression_section = regression_html

        # 生成测试结果表格
        test_results_table = "<table><tr><th>测试名称</th><th>数据规模</th><th>执行时间(ms)</th><th>吞吐量(ops/s)</th><th>内存峰值(MB)</th><th>CPU峰值(%)</th><th>状态</th></tr>"

        for result in report.test_results:
            status_class = "success" if result.success else "failure"
            status_text = "✅ 通过" if result.success else "❌ 失败"

            test_results_table += f"""
            <tr class="{status_class}">
                <td>{result.test_name}</td>
                <td>{result.dataset_size:,}</td>
                <td>{result.execution_time_ms:.2f}</td>
                <td>{result.throughput_ops_per_sec:.1f}</td>
                <td>{result.memory_peak_mb:.1f}</td>
                <td>{result.cpu_peak_percent:.1f}</td>
                <td>{status_text}</td>
            </tr>
            """

        test_results_table += "</table>"

        # 生成HTML内容
        html_content = html_template.format(
            benchmark_name=report.benchmark_name,
            environment=report.environment,
            timestamp=report.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            report_id=report.report_id,
            total_tests=report.total_tests,
            passed_tests=report.passed_tests,
            failed_tests=report.failed_tests,
            success_rate=report.success_rate,
            avg_execution_time_ms=report.avg_execution_time_ms,
            median_execution_time_ms=report.median_execution_time_ms,
            p95_execution_time_ms=report.p95_execution_time_ms,
            p99_execution_time_ms=report.p99_execution_time_ms,
            regression_section=regression_section,
            test_results_table=test_results_table
        )

        # 写入HTML文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

    async def _cleanup(self):
        """清理资源"""
        self.logger.info("🧹 清理测试环境")

        # 清理服务
        if self.prediction_service:
            try:
                await self.prediction_service.shutdown()
            except:
                pass

        if self.collection_service:
            try:
                await self.collection_service.shutdown()
            except:
                pass

        # 强制垃圾回收
        gc.collect()


# 便捷函数
async def run_performance_benchmark(config: Optional[BenchmarkConfig] = None) -> BenchmarkReport:
    """
    运行性能基准测试

    Args:
        config: 基准测试配置

    Returns:
        BenchmarkReport: 基准测试报告
    """
    if config is None:
        config = BenchmarkConfig(
            benchmark_name="football_prediction_system",
            environment="development",
            enable_regression_detection=True,
            generate_html_report=True,
            generate_json_report=True
        )

    framework = PerformanceBenchmarkFramework(config)
    return await framework.run_comprehensive_benchmark()


def create_benchmark_config(
    benchmark_name: str,
    environment: str = "development",
    **kwargs
) -> BenchmarkConfig:
    """
    创建基准测试配置

    Args:
        benchmark_name: 基准测试名称
        environment: 测试环境
        **kwargs: 其他配置参数

    Returns:
        BenchmarkConfig: 基准测试配置
    """
    return BenchmarkConfig(
        benchmark_name=benchmark_name,
        environment=environment,
        **kwargs
    )


# CLI入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="足球预测系统性能基准测试")
    parser.add_argument("--benchmark-name", default="football_prediction_system", help="基准测试名称")
    parser.add_argument("--environment", default="development", help="测试环境")
    parser.add_argument("--output-dir", default="benchmark_results", help="输出目录")
    parser.add_argument("--enable-regression-detection", action="store_true", help="启用回归检测")
    parser.add_argument("--generate-html", action="store_true", help="生成HTML报告")

    args = parser.parse_args()

    # 创建配置
    config = create_benchmark_config(
        benchmark_name=args.benchmark_name,
        environment=args.environment,
        output_dir=args.output_dir,
        enable_regression_detection=args.enable_regression_detection,
        generate_html_report=args.generate_html
    )

    # 运行基准测试
    async def main():
        report = await run_performance_benchmark(config)
        print(f"\n基准测试完成!")
        print(f"报告ID: {report.report_id}")
        print(f"成功率: {report.success_rate:.1%}")
        print(f"平均执行时间: {report.avg_execution_time_ms:.2f}ms")

        if report.regression_detected:
            print(f"⚠️ 检测到 {len(report.regression_details)} 个性能回归")

        return report

    # 运行
    import asyncio
    asyncio.run(main())