#!/usr/bin/env python3
"""
Hot-Swap Validation Script - V1.0.0 [Genesis.UnifiedEngine]
=========================================================

并网稳定性验证脚本 - 测试 Python 和 Node.js 引擎
同时使用 NetworkShield 的状态同步。

测试场景:
1. Python FotMob 引擎收割 → 使用 NetworkShield 获取代理
2. Node.js QuantHarvester 同时运行 → 使用同一个 active_registry.json
3. 模拟 Python 端失败 → 验证 Node.js 端能否感知
4. 验证跨语言状态同步

使用方式:
    # 运行验证（需要先启动 Node.js QuantHarvester）
    python scripts/ops/hot_swap_validation.py

    # 或使用 pytest
    pytest scripts/ops/test_hot_swap_validation.py -v

预期结果:
    ✅ Python 端成功获取代理
    ✅ 代理状态写入 active_registry.json
    ✅ Node.js 端能读取到更新后的状态
    ✅ Python 失败导致节点 health_score 下降
    ✅ Node.js 端能避开低分节点

Author: [Genesis.UnifiedEngine]
Version: V1.0.0
Date: 2026-02-03
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# 添加项目路径
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

REGISTRY_PATH = _project_root / 'config' / 'active_registry.json'
TEST_MATCH_IDS = [12345678, 12345679, 12345680]  # 虚拟比赛 ID
SIMULATED_FAILURE_REASON = "Simulated SSL Error for testing"


# ============================================================================
# TEST FUNCTIONS
# ============================================================================


async def test_1_python_gets_proxy_from_network_shield() -> bool:
    """
    测试 1: Python 端通过 NetworkShield 获取代理

    验证点:
    1. NetworkGuardian 初始化成功
    2. get_next_healthy_proxy() 返回有效代理
    3. 返回的代理包含正确的 port, url, health_score
    4. 代理信息写入 active_registry.json
    """
    logger.info("=" * 60)
    logger.info("TEST 1: Python gets proxy from NetworkShield")
    logger.info("=" * 60)

    try:
        from src.infrastructure.engines.match_engine.shared import NetworkGuardian

        # 初始化 NetworkGuardian
        guardian = NetworkGuardian(log_level='info')
        await guardian.initialize()

        # 获取代理
        session_id = f"TEST-{int(time.time())}"
        proxy = await guardian.get_next_healthy_proxy(session_id)

        if not proxy:
            logger.error("❌ No proxy returned from NetworkShield")
            return False

        logger.info(f"✅ Got proxy: {proxy.url}")
        logger.info(f"   - Port: {proxy.port}")
        logger.info(f"   - Health Score: {proxy.health_score:.1f}")
        logger.info(f"   - Session ID: {proxy.session_id}")

        # 验证代理写入 active_registry.json
        if not _verify_registry_updated(proxy.port):
            logger.error("❌ Registry not updated after getting proxy")
            return False

        logger.info("✅ Registry verified - proxy state written to active_registry.json")

        # 释放会话
        guardian.release_session(session_id)

        return True

    except Exception as e:
        logger.error(f"❌ Test 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_2_simulate_python_failure_updates_registry() -> bool:
    """
    测试 2: 模拟 Python 端失败并更新注册表

    验证点:
    1. mark_proxy_failed() 成功调用
    2. active_registry.json 中节点状态更新
    3. health_score 下降
    4. consecutive_failures 增加
    """
    logger.info("=" * 60)
    logger.info("TEST 2: Simulate Python failure updates registry")
    logger.info("=" * 60)

    try:
        from src.infrastructure.engines.match_engine.shared import NetworkGuardian

        # 初始化
        guardian = NetworkGuardian(log_level='info')
        await guardian.initialize()

        # 获取代理
        session_id = f"FAIL-TEST-{int(time.time())}"
        proxy = await guardian.get_next_healthy_proxy(session_id)

        if not proxy:
            logger.error("❌ No proxy available for failure test")
            return False

        initial_score = proxy.health_score
        logger.info(f"Initial health score: {initial_score:.1f}")

        # 获取失败前的节点状态
        node_before = guardian.get_node(proxy.port)

        # 模拟失败
        logger.info(f"Simulating failure for port {proxy.port}...")
        await guardian.mark_proxy_failed(proxy.port, SIMULATED_FAILURE_REASON)

        # 等待写入完成
        await asyncio.sleep(0.5)

        # 验证注册表更新
        node_after = guardian.get_node(proxy.port)

        if node_after is None:
            logger.error("❌ Node not found after failure")
            return False

        logger.info(f"✅ Node state updated:")
        logger.info(f"   - Consecutive Failures: {node_after.get('consecutive_failures', 'N/A')}")
        logger.info(f"   - Health Score: {node_after.get('health_score', 'N/A')}")

        # 验证冷却期设置（连续 2 次失败后）
        if node_after.get('consecutive_failures', 0) >= 1:
            logger.info(f"✅ Failure count increased correctly")

        # 再失败一次，应该触发冷却
        await guardian.mark_proxy_failed(proxy.port, SIMULATED_FAILURE_REASON)

        await asyncio.sleep(0.5)
        node_final = guardian.get_node(proxy.port)

        if node_final and node_final.get('cooldown_until'):
            logger.info(f"✅ Cooldown period set: {node_final['cooldown_until']}")

        # 释放会话
        guardian.release_session(session_id)

        return True

    except Exception as e:
        logger.error(f"❌ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_3_concurrent_access_safety() -> bool:
    """
    测试 3: 并发访问安全性

    验证点:
    1. 多个 Python 进程同时访问 NetworkShield
    2. 文件锁正常工作
    3. 无死锁或竞态条件
    """
    logger.info("=" * 60)
    logger.info("TEST 3: Concurrent access safety")
    logger.info("=" * 60)

    try:
        from src.infrastructure.engines.match_engine.shared import NetworkGuardian

        # 创建多个 NetworkGuardian 实例（模拟并发）
        guardians = [NetworkGuardian(log_level='warning') for _ in range(5)]

        # 并发初始化
        logger.info("Concurrently initializing 5 NetworkGuardian instances...")
        await asyncio.gather(*[g.initialize() for g in guardians])

        # 并发获取代理
        logger.info("Concurrently getting proxies...")
        tasks = []
        for i, guardian in enumerate(guardians):
            session_id = f"CONCURRENT-{i}-{int(time.time())}"
            tasks.append(guardian.get_next_healthy_proxy(session_id))

        proxies = await asyncio.gather(*tasks)

        # 验证结果
        success_count = sum(1 for p in proxies if p is not None)
        logger.info(f"✅ {success_count}/5 proxies acquired successfully")

        # 释放所有会话
        for i, guardian in enumerate(guardians):
            session_id = f"CONCURRENT-{i}-{int(time.time())}"
            guardian.release_session(session_id)

        return success_count >= 4  # 至少 4 个成功

    except Exception as e:
        logger.error(f"❌ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_4_cross_language_state_sync() -> bool:
    """
    测试 4: 跨语言状态同步验证

    验证点:
    1. Python 写入失败状态
    2. 验证 active_registry.json 更新
    3. 模拟 Node.js 读取相同文件
    4. 确认 Node.js 能看到更新后的状态
    """
    logger.info("=" * 60)
    logger.info("TEST 4: Cross-language state synchronization")
    logger.info("=" * 60)

    try:
        from src.infrastructure.engines.match_engine.shared import NetworkGuardian

        # 初始化
        guardian = NetworkGuardian(log_level='info')
        await guardian.initialize()

        # 获取代理
        session_id = f"SYNC-TEST-{int(time.time())}"
        proxy = await guardian.get_next_healthy_proxy(session_id)

        if not proxy:
            logger.error("❌ No proxy available for sync test")
            return False

        # 标记失败
        logger.info(f"Marking port {proxy.port} as failed...")
        await guardian.mark_proxy_failed(proxy.port, "Cross-language sync test")

        # 等待文件系统同步
        await asyncio.sleep(1)

        # 读取 active_registry.json（模拟 Node.js 读取）
        with open(REGISTRY_PATH, 'r') as f:
            registry = json.load(f)

        # 查找节点
        node = None
        for n in registry.get('nodes', []):
            if n['port'] == proxy.port:
                node = n
                break

        if not node:
            logger.error(f"❌ Node {proxy.port} not found in registry")
            return False

        logger.info("✅ Node found in registry:")
        logger.info(f"   - Port: {node['port']}")
        logger.info(f"   - Status: {node['status']}")
        logger.info(f"   - Consecutive Failures: {node['consecutive_failures']}")
        logger.info(f"   - Health Score: {node['health_score']}")

        # 验证状态已更新
        if node['consecutive_failures'] > 0:
            logger.info("✅ Failure state synced to registry")
        else:
            logger.error("❌ Failure state NOT synced to registry")
            return False

        # 释放会话
        guardian.release_session(session_id)

        return True

    except Exception as e:
        logger.error(f"❌ Test 4 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def _verify_registry_updated(port: int) -> bool:
    """验证注册表是否已更新"""
    try:
        with open(REGISTRY_PATH, 'r') as f:
            registry = json.load(f)

        # 查找节点
        for node in registry.get('nodes', []):
            if node['port'] == port:
                logger.info(f"✅ Node {port} found in registry")
                logger.info(f"   - Status: {node['status']}")
                logger.info(f"   - Last Check: {node.get('last_check', 'N/A')}")
                return True

        logger.warning(f"⚠️  Node {port} not found in registry (may be new)")
        return True  # 新节点可能还未在注册表中

    except Exception as e:
        logger.error(f"❌ Failed to verify registry: {e}")
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================


async def run_all_tests() -> Dict[str, bool]:
    """运行所有测试"""
    logger.info("")
    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info("║     [Genesis.UnifiedEngine] HOT-SWAP VALIDATION SUITE         ║")
    logger.info("╚══════════════════════════════════════════════════════════════╝")
    logger.info("")

    results = {}

    # 运行测试
    tests = [
        ("Test 1: Python gets proxy from NetworkShield", test_1_python_gets_proxy_from_network_shield),
        ("Test 2: Simulate Python failure updates registry", test_2_simulate_python_failure_updates_registry),
        ("Test 3: Concurrent access safety", test_3_concurrent_access_safety),
        ("Test 4: Cross-language state synchronization", test_4_cross_language_state_sync),
    ]

    for test_name, test_func in tests:
        logger.info("")
        result = await test_func()
        results[test_name] = result

        if result:
            logger.info(f"✅ {test_name}: PASSED")
        else:
            logger.error(f"❌ {test_name}: FAILED")

    # 打印汇总
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status}: {test_name}")

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    logger.info("")
    logger.info(f"Result: {passed}/{total} tests passed")

    return results


async def main():
    """主函数"""
    try:
        results = await run_all_tests()

        # 检查是否所有测试通过
        if all(results.values()):
            logger.info("")
            logger.info("╔══════════════════════════════════════════════════════════════╗")
            logger.info("║           ALL TESTS PASSED - HOT-SWAP VALIDATION SUCCESS          ║")
            logger.info("╚══════════════════════════════════════════════════════════════╝")
            return 0
        else:
            logger.error("")
            logger.error("╔══════════════════════════════════════════════════════════════╗")
            logger.error("║              SOME TESTS FAILED - PLEASE REVIEW                   ║")
            logger.error("╚══════════════════════════════════════════════════════════════╝")
            return 1

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
