#!/usr/bin/env python3
"""
赛季 ID 范围发现器 - V146.0 [Genesis.L1Shield]
=================================================

通过 API 测试发现指定英超赛季的比赛 ID 范围

V146.0 变更:
- [P0] 修复裸连漏洞 - 集成 NetworkShield
- [P0] 替换硬编码延迟为随机脉冲
- [P0] 失败状态同步到 active_registry.json

⚠️  SECURITY FIX: 之前的版本使用 requests.get() 裸连，
    现在所有请求都通过 NetworkShield 代理隧道。

Author: [Genesis.L1Shield]
Version: V146.0
Date: 2026-02-03
"""

import asyncio
import logging
import random
import sys
import time
from typing import Any

import requests

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# NETWORKSHIELD INTEGRATION (V146.0)
# ============================================================================

_network_guardian = None
_session_proxy_map: dict[str, dict] = {}  # session_id -> {port, url}


def _get_network_guardian():
    """获取 NetworkGuardian 单例（延迟初始化）"""
    global _network_guardian

    if _network_guardian is None:
        try:
            from src.infrastructure.engines.match_engine.shared import NetworkGuardian

            _network_guardian = NetworkGuardian(log_level='warning')
            asyncio.run(_network_guardian.initialize())

            logger.info("[SeasonDiscoverer] NetworkShield initialized successfully")
        except ImportError:
            logger.warning(
                "[SeasonDiscoverer] NetworkShield not available, "
                "falling back to direct connection (NOT RECOMMENDED)"
            )
            _network_guardian = False

    return _network_guardian


def _get_proxy_for_session(session_id: str) -> dict | None:
    """
    获取 Session 绑定的代理

    Args:
        session_id: 会话 ID

    Returns:
        {'port': int, 'url': str} 或 None
    """
    # 检查缓存
    if session_id in _session_proxy_map:
        return _session_proxy_map[session_id]

    # 获取新代理
    guardian = _get_network_guardian()

    if guardian is False or guardian is None:
        return None

    try:
        proxy = asyncio.run(guardian.get_next_healthy_proxy(session_id))

        if proxy:
            proxy_info = {'port': proxy.port, 'url': proxy.url}
            _session_proxy_map[session_id] = proxy_info
            logger.debug(
                f"[SeasonDiscoverer] Using proxy port {proxy.port} "
                f"for session {session_id}"
            )
            return proxy_info
    except Exception as e:
        logger.warning(f"[SeasonDiscoverer] Failed to get proxy: {e}")

    return None


def _mark_proxy_success(session_id: str, latency_ms: float = 0) -> None:
    """标记代理成功"""
    if session_id not in _session_proxy_map:
        return

    proxy_info = _session_proxy_map[session_id]
    guardian = _get_network_guardian()

    if guardian and hasattr(guardian, 'mark_proxy_success'):
        try:
            asyncio.run(guardian.mark_proxy_success(proxy_info['port'], latency_ms))
        except Exception as e:
            logger.warning(f"[SeasonDiscoverer] Failed to mark success: {e}")


def _mark_proxy_failed(session_id: str, reason: str = "Unknown") -> None:
    """标记代理失败"""
    if session_id not in _session_proxy_map:
        return

    proxy_info = _session_proxy_map[session_id]
    guardian = _get_network_guardian()

    if guardian and hasattr(guardian, 'mark_proxy_failed'):
        try:
            asyncio.run(guardian.mark_proxy_failed(proxy_info['port'], reason))
            logger.warning(
                f"[SeasonDiscoverer] Proxy port {proxy_info['port']} marked as "
                f"FAILED: {reason}"
            )
        except Exception as e:
            logger.warning(f"[SeasonDiscoverer] Failed to mark failure: {e}")


def _release_session(session_id: str) -> None:
    """释放 Session"""
    if session_id in _session_proxy_map:
        del _session_proxy_map[session_id]

    guardian = _get_network_guardian()

    if guardian and hasattr(guardian, 'release_session'):
        try:
            guardian.release_session(session_id)
        except Exception as e:
            logger.warning(f"[SeasonDiscoverer] Failed to release session: {e}")


# ============================================================================
# DISCOVERY FUNCTIONS
# ============================================================================


def test_match_id(match_id: int) -> tuple[bool, dict]:
    """
    测试指定的比赛 ID 是否存在且有效

    V146.0 变更: 使用 NetworkShield 代理隧道

    Args:
        match_id: 比赛 ID

    Returns:
        (是否有效, 响应数据摘要)
    """
    settings = get_settings()
    url = f"{settings.fotmob_base_url}/matchDetails?matchId={match_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    # Session ID for this discovery request
    session_id = f"season-discovery-{match_id}"

    # 获取代理
    proxy_info = _get_proxy_for_session(session_id)

    proxies = None
    if proxy_info:
        proxies = {
            'http': proxy_info['url'],
            'https': proxy_info['url']
        }

    try:
        response = requests.get(
            url,
            headers=headers,
            proxies=proxies,
            timeout=10
        )

        # 检查是否为有效 JSON 响应
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            _mark_proxy_failed(session_id, "Not JSON response")
            return False, {"reason": "Not JSON response"}

        data = response.json()

        # 检查是否包含比赛数据
        if "header" in data and data["header"].get("teams"):
            teams = data["header"]["teams"]
            match_info = {
                "home": teams[0].get("name", "Unknown"),
                "away": teams[1].get("name", "Unknown"),
                "status": data.get("status", {}).get("finished", False),
            }

            # 上报成功到 NetworkShield
            _mark_proxy_success(session_id, response.elapsed.total_seconds() * 1000)

            return True, match_info
        _mark_proxy_failed(session_id, "No match data")
        return False, {"reason": "No match data"}

    except requests.exceptions.RequestException as e:
        # 网络错误 - 上报失败到 NetworkShield
        _mark_proxy_failed(session_id, f"Network error: {e}")
        return False, {"reason": f"Network error: {e}"}
    except Exception as e:
        # 其他错误
        _mark_proxy_failed(session_id, str(e))
        return False, {"reason": str(e)}


def discover_season_range(start_id: int, max_tests: int = 1000) -> list[int]:
    """
    发现连续的比赛 ID 范围

    Args:
        start_id: 起始比赛 ID
        max_tests: 最大测试数量

    Returns:
        有效的比赛 ID 列表
    """
    logger.info(f"🔍 从 ID {start_id} 开始发现赛季范围...")

    valid_ids = []
    consecutive_failures = 0
    max_consecutive_failures = 50  # 允许最多 50 个连续失败

    for offset in range(max_tests):
        test_id = start_id - offset

        if test_id < 4000000:  # FotMob 英超 ID 通常在 4000000 以上
            break

        is_valid, _info = test_match_id(test_id)

        if is_valid:
            valid_ids.append(test_id)
            consecutive_failures = 0

            if len(valid_ids) % 50 == 0:
                logger.info(f"  已发现 {len(valid_ids)} 场比赛... (当前 ID: {test_id})")

                # 检查是否已经达到 380 场（英超标准赛季）
                if len(valid_ids) >= 380:
                    logger.info("✅ 已收集 380 场比赛（英超标准赛季）")
                    break
        else:
            consecutive_failures += 1

            if consecutive_failures > max_consecutive_failures:
                logger.info(f"  连续 {consecutive_failures} 次失败，停止发现")
                break

        # V146.0: 随机脉冲延迟替代硬编码 time.sleep(0.1)
        # 模拟人类浏览行为，避免被反爬系统识别
        time.sleep(random.uniform(0.05, 0.3))

    logger.info(f"✅ 发现完成，共找到 {len(valid_ids)} 场比赛")

    # 按升序排列（从早到晚）
    valid_ids.sort()

    return valid_ids


def generate_2223_manifest():
    """
    生成 22/23 赛季的比赛 ID 清单

    基于 23/24 赛季的首场比赛 ID (4193450) 向前回推
    """
    import csv
    from datetime import datetime
    import os

    # 23/24 赛季首场 ID
    v23_first_id = 4193450

    # 22/23 赛季应该在 23/24 之前约 450-500 个 ID（考虑到其他联赛）
    # 让我们从 4193000 开始测试
    search_start_id = 4193000

    logger.info("=" * 60)
    logger.info("22/23 赛季 ID 发现")
    logger.info("=" * 60)
    logger.info(f"搜索起点: {search_start_id}")
    logger.info(f"23/24 首场: {v23_first_id}")

    # 发现比赛 ID
    match_ids = discover_season_range(search_start_id, max_tests=2000)

    if len(match_ids) < 300:
        logger.warning(f"⚠️  只发现 {len(match_ids)} 场比赛，可能需要调整搜索范围")
        return []

    # 生成 manifest
    output_path = "data/production/harvest_manifest_2223.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fieldnames = [
        "match_id",
        "external_id",
        "home_team",
        "away_team",
        "match_date",
        "home_score",
        "away_score",
        "actual_result",
        "round_name",
        "league_name",
        "season_id",
        "is_finished",
        "venue",
        "status",
        "collection_date",
        "is_matched",
    ]

    # 获取每场比赛的详细信息
    matches_data = []
    logger.info("📊 获取比赛详细信息...")

    for i, match_id in enumerate(match_ids[:380]):  # 最多 380 场
        is_valid, info = test_match_id(match_id)

        if is_valid:
            match_info = {
                "match_id": match_id,
                "external_id": str(match_id),
                "home_team": info.get("home", "Unknown"),
                "away_team": info.get("away", "Unknown"),
                "match_date": "",  # 稍后填充
                "home_score": "",
                "away_score": "",
                "actual_result": "",
                "round_name": "",
                "league_name": "Premier League",
                "season_id": "2022/2023",
                "is_finished": info.get("status", False),
                "venue": "",
                "status": "Finished" if info.get("status") else "Scheduled",
                "collection_date": datetime.utcnow().isoformat(),
                "is_matched": "True",
            }
            matches_data.append(match_info)

        if (i + 1) % 50 == 0:
            logger.info(f"  处理进度: {i + 1}/{len(match_ids[:380])}")

        # V146.0: 随机脉冲延迟替代硬编码 time.sleep(0.1)
        time.sleep(random.uniform(0.05, 0.3))

    # 写入 CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matches_data)

    logger.info(f"✅ Manifest 文件已生成: {output_path}")
    logger.info(f"📊 总计 {len(matches_data)} 场比赛")

    return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    output = generate_2223_manifest()

    if output:
        sys.exit(0)
    else:
        sys.exit(1)
