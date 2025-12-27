#!/usr/bin/env python3
"""
V20.5 流水线压力测试桩
========================

测试目标:
- 模拟连续提取 500 场比赛
- 内存增长需在 ±10% 以内
- 数据库连接数不得超过 max_connections 的 80%

作者: SRE Team
日期: 2025-12-24
版本: V20.5
"""

import logging
import sys
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

import psutil

# 加载环境变量
from dotenv import load_dotenv

load_dotenv(override=True)

from src.config_unified import get_settings
from src.ml.fault_tolerance import CheckpointTracker, CircuitBreaker, ProcessingResult
from src.ml.feature_forge_v20 import FeatureExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class LoadTestConfig:
    """压力测试配置"""

    num_matches: int = 500
    num_workers: int = 4
    memory_threshold_percent: float = 10.0  # 内存波动阈值 ±10%
    db_connection_threshold: float = 0.8  # DB 连接数阈值 80%
    max_memory_mb: int = 2048  # 最大内存 2GB


@dataclass
class LoadTestResult:
    """压力测试结果"""

    success: bool
    total_matches: int
    processed: int
    duration: float
    memory_growth_percent: float
    peak_memory_mb: float
    db_connections_used: int
    db_connections_max: int
    circuit_breaker_trips: int
    errors: list[str]


class MemoryMonitor:
    """内存监控器"""

    def __init__(self, interval_seconds: float = 1.0):
        self.interval = interval_seconds
        self._running = False
        self._thread = None
        self._snapshots: list[tuple] = []  # (timestamp, memory_mb)
        self._lock = threading.Lock()

    def start(self):
        """启动监控"""
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("内存监控器已启动")

    def _monitor_loop(self):
        """监控循环"""
        process = psutil.Process()
        while self._running:
            with self._lock:
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                self._snapshots.append((time.time(), memory_mb))
            time.sleep(self.interval)

    def stop(self) -> list[tuple]:
        """停止监控并返回快照"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info(f"内存监控器已停止，采集 {len(self._snapshots)} 个快照")
        return self._snapshots.copy()

    def get_stats(self) -> dict[str, float]:
        """获取内存统计"""
        with self._lock:
            if not self._snapshots:
                return {}

            memories = [m[1] for m in self._snapshots]
            return {
                "min_mb": min(memories),
                "max_mb": max(memories),
                "avg_mb": sum(memories) / len(memories),
                "initial_mb": memories[0],
                "final_mb": memories[-1],
                "growth_mb": memories[-1] - memories[0],
                "growth_percent": ((memories[-1] - memories[0]) / memories[0] * 100) if memories[0] > 0 else 0,
            }


class DatabaseConnectionMonitor:
    """数据库连接监控器"""

    def __init__(self):
        self.settings = get_settings()
        self.max_connections = self.settings.database.pool_size + self.settings.database.max_overflow
        logger.info(f"DB 连接池配置: max={self.max_connections}")

    def get_active_connections(self) -> int:
        """获取活跃连接数"""
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
            )

            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*) as count
                FROM pg_stat_activity
                WHERE datname = %s
                AND state = 'active'
            """,
                (self.settings.database.name,),
            )

            count = cur.fetchone()[0]
            cur.close()
            conn.close()

            return count
        except Exception as e:
            logger.warning(f"获取 DB 连接数失败: {e}")
            return 0


class MockMatchDataGenerator:
    """模拟比赛数据生成器"""

    def __init__(self):
        self.extractor = FeatureExtractor()

    def generate_match_data(self, match_id: int) -> dict[str, Any]:
        """生成模拟比赛数据"""
        # 基于真实 JSON 结构生成模拟数据
        return {
            "match_id": match_id,
            "league_id": 54,
            "season_id": "2324",
            "home_team": f"HomeTeam_{match_id % 20}",
            "away_team": f"AwayTeam_{match_id % 20}",
            "home_score": (match_id % 5),
            "away_score": (match_id % 4),
            "l2_raw_json": self._generate_mock_l2_json(match_id),
        }

    def _generate_mock_l2_json(self, match_id: int) -> dict[str, Any]:
        """生成模拟 L2 JSON"""
        return {
            "content": {
                "matchStats": {
                    "stats": [
                        {"title": "Total Shots", "stats": [["shots", "12", "8"]]},
                        {"title": "Possession", "stats": [["possession", "55%", "45%"]]},
                    ]
                },
                "lineup": {
                    "homeTeam": {
                        "formation": "4-3-3",
                        "players": [
                            {"id": i, "name": f"Player_{i}", "positionId": 11 + (i % 37)}
                            for i in range(match_id * 11, (match_id + 1) * 11)
                        ],
                    },
                    "awayTeam": {
                        "formation": "4-4-2",
                        "players": [
                            {"id": i, "name": f"Player_{i}", "positionId": 11 + (i % 37)}
                            for i in range((match_id + 1) * 11, (match_id + 2) * 11)
                        ],
                    },
                },
            },
            "header": {"match": {"time": {"utcTime": "2024-01-01T12:00:00.000Z"}}},
        }


def simulate_extraction(extractor: FeatureExtractor, match_data: dict[str, Any]) -> ProcessingResult:
    """模拟特征提取"""
    try:
        # 模拟处理延迟
        time.sleep(0.01)

        # 调用特征提取
        features = extractor.extract_features(
            content=match_data["l2_raw_json"]["content"], header=match_data["l2_raw_json"]["header"]
        )

        if features and features.get("enriched_features"):
            return ProcessingResult(match_id=match_data["match_id"], success=True, duration=0.01)
        else:
            return ProcessingResult(match_id=match_data["match_id"], success=False, error="No features extracted")
    except Exception as e:
        return ProcessingResult(match_id=match_data["match_id"], success=False, error=str(e))


def run_load_test(config: LoadTestConfig = None) -> LoadTestResult:
    """运行压力测试"""
    config = config or LoadTestConfig()
    errors = []

    logger.info(f"{'=' * 60}")
    logger.info("V20.5 压力测试开始")
    logger.info(f"配置: {config.num_matches} 场比赛, {config.num_workers} 个工作线程")
    logger.info(f"{'=' * 60}")

    # 初始化监控器
    memory_monitor = MemoryMonitor(interval_seconds=0.5)
    db_monitor = DatabaseConnectionMonitor()

    # 初始化熔断器和断点追踪
    circuit_breaker = CircuitBreaker()
    checkpoint_tracker = CheckpointTracker("data/backfill_progress_test.json")
    checkpoint_tracker.set_total(config.num_matches)

    # 初始化数据生成器
    generator = MockMatchDataGenerator()

    # 启动内存监控
    tracemalloc.start()
    memory_monitor.start()

    start_time = time.time()

    try:
        # 批量处理
        with ThreadPoolExecutor(max_workers=config.num_workers) as executor:
            futures = []

            for i in range(config.num_matches):
                match_data = generator.generate_match_data(i)

                def process_with_circuit_breaker(md):
                    # 检查熔断器
                    if not circuit_breaker.can_execute():
                        errors.append(f"Circuit breaker OPEN at match {md['match_id']}")
                        return ProcessingResult(
                            match_id=md["match_id"], success=False, error="Circuit breaker is OPEN", error_code=503
                        )

                    # 模拟处理
                    result = simulate_extraction(generator.extractor, md)

                    # 更新熔断器
                    if result.success:
                        circuit_breaker.record_success()
                        checkpoint_tracker.record_success(md["match_id"])
                    else:
                        circuit_breaker.record_failure(error_code=result.error_code)
                        checkpoint_tracker.record_failure(md["match_id"])

                    return result

                future = executor.submit(process_with_circuit_breaker, match_data)
                futures.append(future)

                # 定期检查 DB 连接
                if i % 50 == 0:
                    db_conn = db_monitor.get_active_connections()
                    logger.info(f"进度: {i}/{config.num_matches}, DB连接: {db_conn}/{db_monitor.max_connections}")

            # 等待所有任务完成
            for future in futures:
                try:
                    future.result(timeout=30)
                except Exception as e:
                    errors.append(str(e))

    finally:
        duration = time.time() - start_time

        # 停止监控
        memory_snapshots = memory_monitor.stop()
        tracemalloc.stop()

        # 获取统计
        memory_stats = memory_monitor.get_stats()
        progress = checkpoint_tracker.get_progress()
        db_connections = db_monitor.get_active_connections()

        # 输出结果
        logger.info(f"{'=' * 60}")
        logger.info("压力测试完成")
        logger.info(f"{'=' * 60}")
        logger.info(f"总耗时: {duration:.2f}s")
        logger.info(f"处理速率: {progress['processed'] / duration:.2f} 场/秒")
        logger.info(f"成功: {progress['successful']}/{progress['processed']}")
        logger.info(f"失败: {progress['failed']}")
        logger.info(f"跳过: {progress['skipped']}")
        logger.info(f"成功率: {progress['success_rate'] * 100:.1f}%")
        logger.info(f"熔断次数: {circuit_breaker.trip_count}")
        logger.info(f"{'=' * 60}")
        logger.info("内存统计:")
        logger.info(f"  初始: {memory_stats.get('initial_mb', 0):.2f} MB")
        logger.info(f"  最终: {memory_stats.get('final_mb', 0):.2f} MB")
        logger.info(f"  峰值: {memory_stats.get('max_mb', 0):.2f} MB")
        logger.info(f"  增长: {memory_stats.get('growth_mb', 0):.2f} MB ({memory_stats.get('growth_percent', 0):.2f}%)")
        logger.info(f"{'=' * 60}")
        logger.info(
            f"数据库连接: {db_connections}/{db_monitor.max_connections} ({db_connections / db_monitor.max_connections * 100:.1f}%)"
        )
        logger.info(f"{'=' * 60}")

    # 验证结果
    success = True

    # 内存增长检查
    if abs(memory_stats.get("growth_percent", 0)) > config.memory_threshold_percent:
        success = False
        errors.append(
            f"内存增长 {memory_stats.get('growth_percent', 0):.2f}% 超过阈值 ±{config.memory_threshold_percent}%"
        )

    # DB 连接检查
    if db_connections > db_monitor.max_connections * config.db_connection_threshold:
        success = False
        errors.append(
            f"DB 连接数 {db_connections} 超过阈值 {int(db_monitor.max_connections * config.db_connection_threshold)}"
        )

    # 峰值内存检查
    if memory_stats.get("max_mb", 0) > config.max_memory_mb:
        success = False
        errors.append(f"峰值内存 {memory_stats.get('max_mb', 0):.2f} MB 超过阈值 {config.max_memory_mb} MB")

    return LoadTestResult(
        success=success,
        total_matches=config.num_matches,
        processed=progress["processed"],
        duration=duration,
        memory_growth_percent=memory_stats.get("growth_percent", 0),
        peak_memory_mb=memory_stats.get("max_mb", 0),
        db_connections_used=db_connections,
        db_connections_max=db_monitor.max_connections,
        circuit_breaker_trips=circuit_breaker.trip_count,
        errors=errors,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="V20.5 流水线压力测试")
    parser.add_argument("--matches", type=int, default=500, help="测试比赛数量 (默认: 500)")
    parser.add_argument("--workers", type=int, default=4, help="工作线程数 (默认: 4)")

    args = parser.parse_args()

    config = LoadTestConfig(num_matches=args.matches, num_workers=args.workers)

    result = run_load_test(config)

    # 输出最终结果
    print("\n" + "=" * 60)
    print("最终结果: " + ("✅ 通过" if result.success else "❌ 失败"))
    print("=" * 60)

    if result.errors:
        print("\n错误列表:")
        for error in result.errors:
            print(f"  - {error}")

    # 返回退出码
    sys.exit(0 if result.success else 1)
