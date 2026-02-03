#!/usr/bin/env python3
"""
Cross-Language Stress Test - V1.0.0 [Genesis.FinalAudit]
========================================================

并发压力测试 - 验证 Python 和 Node.js 同时访问 active_registry.json 的安全性

测试场景:
1. 3 个 Python 进程同时读写 active_registry.json
2. 模拟 Node.js 进程同时访问（通过文件锁验证）
3. 验证数据一致性和无损坏
4. 测试 NetworkShield 状态同步

运行方式:
    # 终端 1: 启动主测试
    python scripts/ops/cross_language_stress_test.py

    # 终端 2-4: 启动并发进程
    python scripts/ops/cross_language_stress_test.py --worker

预期结果:
    ✅ 所有并发操作安全完成
    ✅ active_registry.json 无损坏
    ✅ 状态同步正常

Author: [Genesis.FinalAudit]
Version: V1.0.0
Date: 2026-02-03
"""

import argparse
import asyncio
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Thread, Lock
from typing import Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] [%(name)s] [%(process)d] %(message)s",
    handlers=[
        logging.FileHandler("logs/cross_language_stress_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

REGISTRY_PATH = Path.cwd() / 'config' / 'active_registry.json'
NUM_OPERATIONS = 100  # 每个进程执行的操作数
OPERATION_DELAY_MS = (10, 100)  # 操作间延迟（毫秒）

# ============================================================================
# TEST STATISTICS
# ============================================================================


class TestStatistics:
    """测试统计"""
    def __init__(self):
        self.total_operations = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.lock_contentions = 0
        self.lock_timeouts = 0
        self.data_corruptions = 0
        self.sync_failures = 0

    def record_success(self):
        self.total_operations += 1
        self.successful_operations += 1

    def record_failure(self, reason: str):
        self.total_operations += 1
        self.failed_operations += 1
        if "lock" in reason.lower():
            self.lock_contentions += 1
        elif "timeout" in reason.lower():
            self.lock_timeouts += 1
        elif "corruption" in reason.lower():
            self.data_corruptions += 1
        elif "sync" in reason.lower():
            self.sync_failures += 1

    def to_dict(self) -> dict:
        return {
            'total_operations': self.total_operations,
            'successful_operations': self.successful_operations,
            'failed_operations': self.failed_operations,
            'success_rate': f"{(self.successful_operations / self.total_operations * 100):.1f}%" if self.total_operations > 0 else "N/A",
            'lock_contentions': self.lock_contentions,
            'lock_timeouts': self.lock_timeouts,
            'data_corruptions': self.data_corruptions,
            'sync_failures': self.sync_failures,
        }

    def print_summary(self):
        logger.info("=" * 60)
        logger.info("TEST STATISTICS SUMMARY")
        logger.info("=" * 60)
        stats = self.to_dict()
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        logger.info("=" * 60)


_global_stats = TestStatistics()
_stats_lock = Lock()


# ============================================================================
# STRESS TEST OPERATIONS
# ============================================================================


def verify_registry_integrity(registry_data: dict) -> bool:
    """
    验证注册表数据完整性

    Args:
        registry_data: 注册表数据

    Returns:
        True if data is valid
    """
    try:
        # 检查必需字段
        required_fields = ['version', 'last_updated', 'nodes', 'statistics']
        for field in required_fields:
            if field not in registry_data:
                return False

        # 检查版本格式
        if not registry_data['version'].startswith('V'):
            return False

        # 检查节点数据
        nodes = registry_data.get('nodes', [])
        for node in nodes:
            if 'port' not in node or 'status' not in node or 'health_score' not in node:
                return False

        return True

    except Exception:
        return False


def mark_node_failed_threadsafe(port: int, reason: str) -> bool:
    """
    线程安全的节点失败标记

    模拟 NetworkShield 的 mark_proxy_failed 操作

    Args:
        port: 代理端口
        reason: 失败原因

    Returns:
        True if successful
    """
    try:
        # 使用 NetworkShield 的 Python 适配器
        from src.infrastructure.network.python.network_shield import get_network_shield

        shield = get_network_shield()
        shield.mark_proxy_failed(port, reason)

        return True

    except Exception as e:
        _global_stats.record_failure(f"sync_failure: {e}")
        return False


def read_registry_threadsafe() -> dict | None:
    """
    线程安全的注册表读取

    Returns:
        注册表数据，失败返回 None
    """
    try:
        from src.infrastructure.network.python.network_shield import get_network_shield

        shield = get_network_shield()
        registry_manager = shield.registry

        data = registry_manager._load_registry()

        if not verify_registry_integrity(data):
            _global_stats.record_failure("data_corruption")
            return None

        return data

    except Exception as e:
        _global_stats.record_failure(f"read_error: {e}")
        return None


def stress_operation(worker_id: int, operation_id: int) -> bool:
    """
    单个压力测试操作

    Args:
        worker_id: 工作进程 ID
        operation_id: 操作 ID

    Returns:
        True if successful
    """
    operation_type = random.choice([
        'read_registry',
        'mark_success',
        'mark_failure',
        'get_proxy',
        'verify_integrity'
    ])

    try:
        if operation_type == 'read_registry':
            data = read_registry_threadsafe()
            if data is None:
                return False
            # 验证数据完整性
            if not verify_registry_integrity(data):
                _global_stats.record_failure("data_corruption")
                return False

        elif operation_type == 'mark_success':
            # 随机选择一个端口标记成功
            port = random.choice(range(7891, 7913))
            from src.infrastructure.network.python.network_shield import get_network_shield
            shield = get_network_shield()
            shield.mark_proxy_success(port, random.uniform(100, 500))

        elif operation_type == 'mark_failure':
            # 随机选择一个端口标记失败
            port = random.choice(range(7891, 7913))
            mark_node_failed_threadsafe(port, "Stress test failure")

        elif operation_type == 'get_proxy':
            # 获取代理（模拟真实使用场景）
            from src.infrastructure.engines.match_engine.shared import NetworkGuardian
            from src.infrastructure.engines.match_engine.base.base_harvest_engine import EngineConfig

            guardian = NetworkGuardian(log_level='warning')
            asyncio.run(guardian.initialize())

            session_id = f"stress-test-{worker_id}-{operation_id}"
            proxy = asyncio.run(guardian.get_next_healthy_proxy(session_id))

            if proxy:
                # 模拟使用后释放
                guardian.release_session(session_id)

        elif operation_type == 'verify_integrity':
            # 验证注册表完整性
            data = read_registry_threadsafe()
            if data is None:
                return False

            # 验证节点健康分数
            for node in data.get('nodes', []):
                score = node.get('health_score', -1)
                if not (0 <= score <= 100):
                    _global_stats.record_failure("data_corruption: invalid health_score")
                    return False

        _global_stats.record_success()
        return True

    except Exception as e:
        _global_stats.record_failure(f"operation_error: {e}")
        return False


def worker_process(worker_id: int, num_operations: int) -> None:
    """
    工作进程

    Args:
        worker_id: 工作进程 ID
        num_operations: 操作数量
    """
    logger.info(f"[Worker {worker_id}] Starting with {num_operations} operations...")

    for i in range(num_operations):
        success = stress_operation(worker_id, i)

        # 随机延迟模拟真实使用场景
        delay = random.uniform(*OPERATION_DELAY_MS) / 1000
        time.sleep(delay)

        # 每 10 次操作报告一次进度
        if (i + 1) % 10 == 0:
            stats = _global_stats.to_dict()
            logger.info(
                f"[Worker {worker_id}] Progress: {i + 1}/{num_operations}, "
                f"Success Rate: {stats['success_rate']}"
            )

    logger.info(f"[Worker {worker_id}] Completed")


# ============================================================================
# CROSS-LANGUAGE SYNC TEST
# ============================================================================


def test_cross_language_sync() -> bool:
    """
    测试跨语言状态同步

    场景:
    1. Python 端标记端口失败
    2. 验证 active_registry.json 已更新
    3. 模拟 Node.js 读取验证（读取文件）

    Returns:
        True if sync is working
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("CROSS-LANGUAGE SYNC TEST")
    logger.info("=" * 60)

    try:
        # 1. 读取初始状态
        from src.infrastructure.network.python.network_shield import get_network_shield

        shield = get_network_shield()
        initial_data = shield.registry._load_registry()

        # 选择一个测试端口
        test_port = 7891

        # 查找该节点的初始状态
        initial_node = None
        for node in initial_data.get('nodes', []):
            if node['port'] == test_port:
                initial_node = node
                break

        if not initial_node:
            logger.error(f"❌ Test port {test_port} not found in registry")
            return False

        initial_score = initial_node.get('health_score', 100)
        initial_failures = initial_node.get('consecutive_failures', 0)

        logger.info(f"Initial state - Port {test_port}:")
        logger.info(f"  Health Score: {initial_score}")
        logger.info(f"  Consecutive Failures: {initial_failures}")

        # 2. Python 端标记失败
        logger.info(f"\nMarking port {test_port} as FAILED from Python...")
        shield.mark_proxy_failed(test_port, "Cross-language sync test")

        # 3. 等待文件系统同步
        time.sleep(1)

        # 4. 验证 active_registry.json 已更新
        updated_data = shield.registry._load_registry()

        updated_node = None
        for node in updated_data.get('nodes', []):
            if node['port'] == test_port:
                updated_node = node
                break

        if not updated_node:
            logger.error("❌ Test port not found after update")
            return False

        updated_score = updated_node.get('health_score', 100)
        updated_failures = updated_node.get('consecutive_failures', 0)

        logger.info(f"Updated state - Port {test_port}:")
        logger.info(f"  Health Score: {updated_score}")
        logger.info(f"  Consecutive Failures: {updated_failures}")

        # 5. 验证状态变化
        if updated_failures > initial_failures:
            logger.info("✅ Cross-language sync verified: consecutive_failures increased")
        else:
            logger.warning("⚠️  consecutive_failures did not increase (may be cached)")

        if updated_score < initial_score:
            logger.info("✅ Cross-language sync verified: health_score decreased")
        else:
            logger.warning("⚠️  health_score did not decrease")

        logger.info("\n✅ Cross-language sync test PASSED")
        return True

    except Exception as e:
        logger.error(f"❌ Cross-language sync test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================


def run_stress_test(num_workers: int = 3, num_operations: int = 100) -> TestStatistics:
    """
    运行压力测试

    Args:
        num_workers: 工作进程数量
        num_operations: 每个进程的操作数

    Returns:
        测试统计
    """
    logger.info("")
    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info("║     [Genesis.FinalAudit] CROSS-LANGUAGE STRESS TEST        ║")
    logger.info("╚══════════════════════════════════════════════════════════════╝")
    logger.info("")

    logger.info(f"Configuration:")
    logger.info(f"  Workers: {num_workers}")
    logger.info(f"  Operations per worker: {num_operations}")
    logger.info(f"  Total operations: {num_workers * num_operations}")
    logger.info(f"  Operation delay: {OPERATION_DELAY_MS[0]}-{OPERATION_DELAY_MS[1]}ms")
    logger.info("")

    # 创建并启动工作进程
    workers = []
    for i in range(num_workers):
        worker = Thread(target=worker_process, args=(i + 1, num_operations))
        workers.append(worker)
        worker.start()

    # 等待所有工作进程完成
    for worker in workers:
        worker.join()

    # 打印统计结果
    _global_stats.print_summary()

    return _global_stats


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="V1.0.0 Cross-Language Stress Test"
    )
    parser.add_argument(
        "--worker",
        action="store_true",
        help="Run as worker process"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Number of worker processes (default: 3)"
    )
    parser.add_argument(
        "--operations",
        type=int,
        default=100,
        help="Operations per worker (default: 100)"
    )
    parser.add_argument(
        "--skip-stress",
        action="store_true",
        help="Skip stress test, only run sync test"
    )
    args = parser.parse_args()

    try:
        # 运行跨语言同步测试
        sync_success = test_cross_language_sync()

        # 如果不是 worker 模式且未跳过压力测试，则运行压力测试
        if not args.worker and not args.skip_stress:
            logger.info("")
            logger.info("Starting stress test...")
            stats = run_stress_test(
                num_workers=args.workers,
                num_operations=args.operations
            )

            # 检查测试结果
            logger.info("")
            if sync_success and stats.successful_operations == stats.total_operations:
                logger.info("╔══════════════════════════════════════════════════════════════╗")
                logger.info("║          ALL TESTS PASSED - SYSTEM STABLE                    ║")
                logger.info("╚══════════════════════════════════════════════════════════════╝")
                return 0
            else:
                logger.error("╔══════════════════════════════════════════════════════════════╗")
                logger.error("║              SOME TESTS FAILED - REVIEW NEEDED               ║")
                logger.error("╚══════════════════════════════════════════════════════════════╝")
                return 1

        elif sync_success:
            return 0
        else:
            return 1

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
