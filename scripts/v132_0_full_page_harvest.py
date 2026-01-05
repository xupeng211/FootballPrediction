#!/usr/bin/env python3
"""V132.0 全页码收割引擎 (Full Page Harvest Engine).

核心特性：
    1. 显式分页循环捕获 - 强制跳转 URL，深度触发滚动
    2. 全赛季数据脱水 - 解密所有分页，汇总到全局列表
    3. 高精度原子对账 - 两阶段匹配（规范化 + fuzzy 80% 阈值）
    4. 巡航大盘 - 实时输出进度仪表盘

Usage:
    # 英超 23/24 全量收割
    python scripts/v132_0_full_page_harvest.py --league "Premier League" --season "23/24"

    # 批量处理所有联赛
    python scripts/v132_0_full_page_harvest.py

    # 指定联赛数量
    python scripts/v132_0_full_page_harvest.py --limit 3

    # 干运行（不更新数据库）
    python scripts/v132_0_full_page_harvest.py --dry-run
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

# Disable proxy
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                  'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(proxy_var, None)

import psycopg2
from playwright.async_api import async_playwright, Page

# V129.2: 密码学库
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer, LeagueUrlMapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://www.oddsportal.com"
MIN_PAYLOAD_SIZE = 10 * 1024
TARGET_API_KEYWORD = "ajax-sport-country-tournament-archive_"
MAX_RETRIES_PER_PAGE = 3  # 每页最多重试 3 次

# V129.2: AES Keys
ODDSPORTAL_PASSWORD = "J*8sQ!p$7aD_fR2yW@gHn*3bVp#sAdLd_k"
ODDSPORTAL_SALT = "5b9a8f2c3e6d1a4b7c8e9d0f1a2b3c4d"

# Stealth configuration
STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

STEALTH_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--disable-dev-shm-usage",
    "--disable-setuid-sandbox",
    "--no-sandbox",
]


class HarvestStats:
    """V132.0 收割统计."""

    def __init__(self) -> None:
        self.leagues_total = 0
        self.leagues_succeeded = 0
        self.leagues_failed = 0
        self.leagues_skipped = 0
        self.pages_attempted = 0
        self.pages_succeeded = 0
        self.pages_failed = 0
        self.matches_extracted = 0
        self.matches_matched = 0
        self.urls_updated = 0
        self.matching_failures = []
        self.start_time = datetime.now()

    def summary(self) -> str:
        """生成执行摘要."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        success_rate = (self.leagues_succeeded / self.leagues_total * 100) if self.leagues_total > 0 else 0
        page_success_rate = (self.pages_succeeded / self.pages_attempted * 100) if self.pages_attempted > 0 else 0
        match_rate = (self.matches_matched / self.matches_extracted * 100) if self.matches_extracted > 0 else 0

        return f"""
╔═══════════════════════════════════════════════════════════════╗
║              V132.0 全页码收割引擎 - 执行摘要                   ║
╠═══════════════════════════════════════════════════════════════╣
║ 总联赛数:         {self.leagues_total:>5}                                      ║
║ 已完成(跳过):     {self.leagues_skipped:>5}                                      ║
║ 成功处理:         {self.leagues_succeeded:>5}  ({success_rate:>5.1f}%)                         ║
║ 失败:             {self.leagues_failed:>5}                                      ║
║ ─────────────────────────────────────────────────────────── ║
║ 页面尝试:         {self.pages_attempted:>5}                                      ║
║ 页面成功:         {self.pages_succeeded:>5}  ({page_success_rate:>5.1f}%)                         ║
║ 页面失败:         {self.pages_failed:>5}                                      ║
║ ─────────────────────────────────────────────────────────── ║
║ 提取比赛数:       {self.matches_extracted:>5}                                      ║
║ 匹配成功数:       {self.matches_matched:>5}  ({match_rate:>5.1f}%)                         ║
║ 更新 URL 数:      {self.urls_updated:>5}                                      ║
║ ─────────────────────────────────────────────────────────── ║
║ 执行时间:         {elapsed:>8.1f} 秒                                ║
║ 处理速率:         {self.matches_matched / elapsed if elapsed > 0 else 0:>8.2f} 场/秒                          ║
╚═══════════════════════════════════════════════════════════════╝"""


# =============================================================================
# V129.2: AES-CBC 解密引擎
# =============================================================================

async def decrypt_oddsportal_response(encrypted_data: str) -> str | None:
    """V129.2 AES-CBC 解密引擎."""
    try:
        if ':' not in encrypted_data:
            return None

        encrypted_b64, iv_hex = encrypted_data.rsplit(':', 1)
        iv = bytes.fromhex(iv_hex)
        encrypted_bytes = base64.b64decode(encrypted_b64)

        # PBKDF2 密钥派生
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=ODDSPORTAL_SALT.encode('utf-8'),
            iterations=1000,
            backend=default_backend()
        )
        key = kdf.derive(ODDSPORTAL_PASSWORD.encode('utf-8'))

        # AES-CBC 解密
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(encrypted_bytes) + decryptor.finalize()

        # 移除 PKCS7 padding
        padding_length = decrypted_padded[-1]
        decrypted = decrypted_padded[:-padding_length]

        return decrypted.decode('utf-8')

    except Exception as e:
        logger.error(f"  ❌ 解密失败: {e}")
        return None


def extract_match_info_from_json(data: str) -> tuple[list[dict], int]:
    """从解密后的 JSON 中提取比赛信息.

    Returns:
        (比赛列表, 总比赛数)
    """
    matches = []
    try:
        data = json.loads(data)
    except:
        return matches, 0

    if not isinstance(data, dict) or 'd' not in data:
        return matches, 0

    total = data['d'].get('total', 0)
    rows = data['d'].get('rows', [])

    for row in rows:
        if 'encodeEventId' in row:
            matches.append({
                'url': f"https://www.oddsportal.com/match/{row['encodeEventId']}/",
                'match_id': row.get('id'),
                'encode_event_id': row['encodeEventId'],
                'home_team': row.get('home-name'),
                'away_team': row.get('away-name'),
                'status': row.get('event-stage-name'),
            })
    return matches, total


# =============================================================================
# V132.1: 显式分页循环捕获
# =============================================================================

async def capture_single_page(
    page: Page,
    base_url: str,
    page_num: int,
    max_wait_time: int = 60
) -> dict | None:
    """V132.1 捕获单个分页.

    Args:
        page: Playwright 页面实例
        base_url: 基础结果页 URL
        page_num: 页码（从 1 开始）
        max_wait_time: 最大等待时间

    Returns:
        捕获的响应数据，失败返回 None
    """
    # 构造带页码的 URL
    if page_num == 1:
        target_url = base_url
    else:
        target_url = f"{base_url}#/page/{page_num}/"

    logger.debug(f"    📍 目标 URL: {target_url[:80]}...")

    # 存储捕获的响应
    captured_response = None
    capture_event = asyncio.Event()

    async def handle_response(response):
        nonlocal captured_response
        try:
            url = response.url

            if TARGET_API_KEYWORD in url:
                logger.debug(f"    🎯 检测到目标 API")

            if TARGET_API_KEYWORD not in url:
                return

            if response.status != 200:
                logger.warning(f"    ❌ 状态码: {response.status}")
                return

            body_bytes = await response.body()
            body = body_bytes.decode('utf-8', errors='ignore')

            logger.info(f"    📦 API 响应大小: {len(body)} 字节")

            if len(body) < MIN_PAYLOAD_SIZE:
                logger.warning(f"    ⚠️  响应体较小: {len(body)} < {MIN_PAYLOAD_SIZE}")
                # V132.0: 继续尝试，不放弃

            captured_response = {'body': body, 'size': len(body), 'url': url}
            capture_event.set()

        except Exception as e:
            logger.debug(f"    ⚠️  响应处理异常: {e}")

    # 注册响应处理器
    page.on('response', handle_response)

    # V132.1: 强制跳转 + networkidle 等待
    try:
        await page.goto(target_url, timeout=60000, wait_until="networkidle")
    except Exception as e:
        logger.debug(f"    ⚠️  导航超时: {e}")
        # 继续尝试，networkidle 可能会超时

    # V132.1: 深度触发 - 15 次大步长滚动
    logger.debug(f"    📜 执行深度滚动触发...")
    for i in range(15):
        if capture_event.is_set():
            logger.debug(f"    ✅ 在第 {i} 次滚动时触发 API")
            break
        await page.mouse.wheel(0, 800)
        await asyncio.sleep(0.2)

    # 额外等待让响应加载
    if not capture_event.is_set():
        await asyncio.sleep(5)

    # 等待捕获
    try:
        await asyncio.wait_for(capture_event.wait(), timeout=max_wait_time)
    except asyncio.TimeoutError:
        logger.debug(f"    ⏱️  等待超时")

    # 注销响应处理器
    page.remove_listener('response', handle_response)

    return captured_response


async def capture_all_pages_with_retry(
    page: Page,
    base_url: str,
    max_pages: int = 15
) -> tuple[list[dict], int, list[int]]:
    """V132.1 显式分页循环捕获（带重试）.

    核心逻辑：
    1. 强制跳转 URL: .../results/#/page/{i}/
    2. 深度触发: 15 次 mouse.wheel(0, 800)
    3. 强制拦截: 必须捕获到 API 包且大小 > 10KB
    4. 断点保护: 3 次重试失败则跳过该页

    Args:
        page: Playwright 页面实例
        base_url: 基础结果页 URL
        max_pages: 最大页数限制

    Returns:
        (所有比赛数据列表, 总比赛数, 成功的页码列表)
    """
    all_matches = []
    successful_pages = []
    total_matches = 0

    logger.info(f"  🚀 启动显式分页循环捕获")

    for page_num in range(1, max_pages + 1):
        logger.info(f"  📄 捕获第 {page_num} 页...")

        # V132.1: 断点保护 - 3 次重试
        captured = None
        for attempt in range(1, MAX_RETRIES_PER_PAGE + 1):
            if attempt > 1:
                logger.info(f"    🔄 第 {attempt}/{MAX_RETRIES_PER_PAGE} 次重试...")

            captured = await capture_single_page(page, base_url, page_num)

            if captured:
                break

            # 重试间延迟
            if attempt < MAX_RETRIES_PER_PAGE:
                await asyncio.sleep(random.uniform(2, 4))

        # 检查是否捕获成功
        if captured:
            # 解密
            decrypted = await decrypt_oddsportal_response(captured['body'])
            if decrypted:
                matches, total = extract_match_info_from_json(decrypted)
                if matches:
                    logger.info(f"    ✅ 第 {page_num} 页: {len(matches)} 场比赛")
                    all_matches.extend(matches)
                    successful_pages.append(page_num)

                    # 第一页时记录总数
                    if page_num == 1:
                        total_matches = total
                        per_page = len(matches)
                        expected_pages = (total + per_page - 1) // per_page
                        logger.info(f"    📊 联赛总比赛数: {total_matches}")
                        logger.info(f"    📊 预计总页数: {expected_pages}")
                        max_pages = expected_pages

                    # 检查是否已到最后一页
                    if page_num >= max_pages:
                        logger.info(f"    📋 已采集全部 {max_pages} 页")
                        break
                else:
                    logger.warning(f"    ⚠️  第 {page_num} 页解密成功但无数据（可能是最后一页）")
                    break
            else:
                logger.warning(f"    ❌ 第 {page_num} 页解密失败")
        else:
            logger.warning(f"    ❌ 第 {page_num} 页 {MAX_RETRIES_PER_PAGE} 次重试后仍未捕获")
            # 断点保护：记录失败但继续下一页
            continue

        # 页间延迟
        if page_num < max_pages:
            await asyncio.sleep(random.uniform(2, 4))

    logger.info(f"  🎉 分页捕获完成: {len(successful_pages)}/{max_pages} 页成功")

    return all_matches, total_matches, successful_pages


# =============================================================================
# V132.2: 全赛季数据脱水
# =============================================================================

async def decrypt_and_flatten_all_pages(
    captured_pages: list[dict]
) -> tuple[list[dict], int]:
    """V132.2 全赛季数据脱水.

    将所有捕获到的分页 API 包顺序解密并汇总到全局列表.

    Args:
        captured_pages: 捕获的页面数据列表

    Returns:
        (全赛季比赛列表, 总比赛数)
    """
    full_season_matches = []

    logger.info(f"  🔓 开始解密 {len(captured_pages)} 个页面...")

    for idx, page_data in enumerate(captured_pages, 1):
        decrypted = await decrypt_oddsportal_response(page_data['body'])
        if decrypted:
            matches, total = extract_match_info_from_json(decrypted)
            if matches:
                full_season_matches.extend(matches)
                logger.info(f"    ✅ 第 {idx} 页解密: {len(matches)} 场比赛")

    logger.info(f"  📊 全赛季数据脱水完成: {len(full_season_matches)} 场比赛")

    return full_season_matches, len(full_season_matches)


# =============================================================================
# V132.3: 高精度原子对账
# =============================================================================

def two_stage_precision_matching(
    oddsportal_matches: list[dict],
    db_matches: list[tuple],
    normalizer: TeamNameNormalizer,
    threshold: float = 80.0
) -> tuple[list[tuple], list[dict]]:
    """V132.3 高精度原子对账.

    两阶段匹配：
    1. 优先通过标准规范化进行 1:1 匹配
    2. 对剩余项使用 fuzzy_match（80% 阈值）

    Args:
        oddsportal_matches: 从 OddsPortal 提取的比赛列表
        db_matches: 数据库中缺失 URL 的比赛列表
        normalizer: TeamNameNormalizer 实例
        threshold: fuzzy_match 阈值（默认 80%）

    Returns:
        (匹配成功的列表, 匹配失败的列表)
    """
    matched = []
    failures = []

    # 创建规范化后的查找字典
    normalized_op_matches = {}
    for m in oddsportal_matches:
        norm_home = normalizer.normalize(m['home_team'])
        norm_away = normalizer.normalize(m['away_team'])
        key = (norm_home, norm_away)
        normalized_op_matches[key] = m

    # 第一阶段：标准规范化匹配（1:1 精确匹配）
    db_remaining = []
    for db_id, db_home, db_away in db_matches:
        norm_home = normalizer.normalize(db_home)
        norm_away = normalizer.normalize(db_away)
        key = (norm_home, norm_away)

        if key in normalized_op_matches:
            op_match = normalized_op_matches[key]
            matched.append((db_id, op_match['url'], db_home, db_away, 100.0))
        else:
            db_remaining.append((db_id, db_home, db_away))

    logger.info(f"    📊 第一阶段（规范化匹配）: {len(matched)} 场")

    # 第二阶段：Fuzzy Matching（80% 阈值）
    fuzzy_matched = 0
    for db_id, db_home, db_away in db_remaining:
        best_match = None
        best_score = 0

        for m in oddsportal_matches:
            home_score = normalizer.fuzzy_match(db_home, m['home_team'])
            away_score = normalizer.fuzzy_match(db_away, m['away_team'])
            avg_score = (home_score + away_score) / 2

            if avg_score > best_score and avg_score > threshold:
                best_score = avg_score
                best_match = m

        if best_match:
            matched.append((db_id, best_match['url'], db_home, db_away, best_score))
            fuzzy_matched += 1
        else:
            # 记录匹配失败
            failures.append({
                'match_id': db_id,
                'home_team': db_home,
                'away_team': db_away,
                'reason': 'no_match_above_threshold'
            })

    logger.info(f"    📊 第二阶段（Fuzzy Matching, 80% 阈值）: {fuzzy_matched} 场")

    # 统计匹配质量
    high_quality = len([m for m in matched if m[4] >= 90])
    medium_quality = len([m for m in matched if 80 <= m[4] < 90])
    low_quality = len([m for m in matched if m[4] < 80])

    logger.info(f"    📊 匹配质量分布:")
    logger.info(f"       🟢 高质量（≥90%）: {high_quality} 场")
    logger.info(f"       🟡 中质量（80-90%）: {medium_quality} 场")
    logger.info(f"       🔴 低质量（<80%）: {low_quality} 场")

    return matched, failures


# =============================================================================
# V132.4: 巡航大盘
# =============================================================================

def print_dashboard(league_name: str, season: str, stats: dict):
    """V132.4 巡航大盘 - 实时进度输出.

    格式: 联赛: Premier League 23/24 | 补完数: 342/380 | 状态: SUCCESS
    """
    total = stats.get('total', 0)
    matched = stats.get('matched', 0)
    status = stats.get('status', 'UNKNOWN')

    # 状态图标
    status_icon = {
        'SUCCESS': '✅',
        'FAILED': '❌',
        'SKIPPED': '⏭️',
        'PARTIAL': '⚠️'
    }.get(status, '❓')

    match_rate = (matched / total * 100) if total > 0 else 0

    logger.info(f"")
    logger.info(f"  ╔═══════════════════════════════════════════════════════════╗")
    logger.info(f"  ║  V132.0 巡航大盘                                           ║")
    logger.info(f"  ╠═══════════════════════════════════════════════════════════╣")
    logger.info(f"  ║  联赛: {league_name:40s}   ║")
    logger.info(f"  ║  赛季: {season:40s}   ║")
    logger.info(f"  ║  ───────────────────────────────────────────────────────   ║")
    logger.info(f"  ║  理论总数: {total:45d}   ║")
    logger.info(f"  ║  实际提取: {stats.get('extracted', 0):45d}   ║")
    logger.info(f"  ║  补完数:   {matched:45d}   ║")
    logger.info(f"  ║  匹配率:   {match_rate:43.1f}%   ║")
    logger.info(f"  ║  状态:     {status_icon} {status:41s}   ║")
    logger.info(f"  ╚═══════════════════════════════════════════════════════════╝")


# =============================================================================
# 主流程
# =============================================================================

async def apply_stealth_armor(page: Page) -> None:
    """应用反指纹隐身装甲."""
    await page.add_init_script("""() => {
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = {runtime: {}};
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
    }""")


async def warm_up_browser(page: Page) -> None:
    """浏览器暖机."""
    logger.info("  🔥 暖机浏览器...")
    try:
        await page.goto(f"{BASE_URL}/", timeout=60000, wait_until="networkidle")
        await asyncio.sleep(2)
        for _ in range(2):
            await page.mouse.wheel(0, random.randint(200, 500))
            await asyncio.sleep(random.uniform(0.5, 1.0))
    except Exception:
        logger.debug("    暖机超时（继续执行）")


def check_league_status(league_name: str, season: str) -> bool:
    """检查联赛是否已完成（断点续传）."""
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    cur = conn.cursor()

    # 检查是否还有缺失 URL 的比赛
    cur.execute("""
        SELECT COUNT(*) FROM matches
        WHERE league_name = %s AND season = %s
          AND oddsportal_url IS NULL
    """, (league_name, season))

    missing_count = cur.fetchone()[0]
    cur.close()
    conn.close()

    # 如果没有缺失，说明已完成
    return missing_count == 0


async def harvest_league_full(
    page: Page,
    league_name: str,
    season: str,
    results_url: str,
    dry_run: bool = False
) -> dict[str, Any]:
    """V132.0 收割单个联赛（全量分页）.

    Args:
        page: Playwright 页面实例
        league_name: 联赛名称
        season: 赛季
        results_url: 结果页 URL
        dry_run: 是否干运行

    Returns:
        收割结果统计
    """
    logger.info(f"\n{'=' * 70}")
    logger.info(f"🏆 V132.0 全页码收割: {league_name} {season}")
    logger.info(f"{'=' * 70}")

    result = {
        'league': league_name,
        'season': season,
        'total': 0,
        'extracted': 0,
        'matched': 0,
        'updated': 0,
        'pages_success': [],
        'pages_failed': [],
        'status': 'UNKNOWN',
        'skipped': False
    }

    # 检查是否已完成
    if check_league_status(league_name, season):
        logger.info(f"  ⏭️  联赛已完成，跳过")
        result['skipped'] = True
        result['status'] = 'SKIPPED'
        return result

    try:
        # V132.1: 显式分页循环捕获
        all_matches, total_matches, successful_pages = await capture_all_pages_with_retry(
            page, results_url, max_pages=15
        )

        result['total'] = total_matches
        result['extracted'] = len(all_matches)
        result['pages_success'] = successful_pages
        result['pages_failed'] = list(range(1, len(successful_pages) + 1))

        if not all_matches:
            logger.warning(f"  ⚠️  未提取到比赛数据")
            result['status'] = 'FAILED'
            return result

        logger.info(f"  📦 全赛季提取: {len(all_matches)} 场比赛（理论 {total_matches} 场）")
        logger.info(f"  📄 成功页面: {successful_pages}")

        # 获取数据库中该联赛缺失 URL 的比赛
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )
        cur = conn.cursor()

        cur.execute("""
            SELECT match_id, home_team, away_team
            FROM matches
            WHERE league_name = %s AND season = %s
              AND oddsportal_url IS NULL
        """, (league_name, season))

        db_matches = cur.fetchall()
        logger.info(f"  🔍 数据库中缺失 URL: {len(db_matches)} 场")

        # V132.3: 高精度原子对账
        normalizer = TeamNameNormalizer()
        matched, failures = two_stage_precision_matching(
            all_matches, db_matches, normalizer, threshold=80.0
        )

        result['matched'] = len(matched)

        # V132.3: 原子更新
        if matched and not dry_run:
            # 开启事务
            conn.autocommit = False

            try:
                # 批量更新 matches 表
                cur.executemany("""
                    UPDATE matches
                    SET oddsportal_url = %s
                    WHERE match_id = %s
                """, [(url, match_id) for match_id, url, _, _, _ in matched])

                # 更新 match_search_queue 表
                cur.executemany("""
                    UPDATE match_search_queue
                    SET status = 'SUCCESS',
                        oddsportal_url = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE match_id = %s
                """, [(url, match_id) for match_id, _, url, _, _ in [(m[0], m[2], m[1], m[3], m[4]) for m in matched]])

                conn.commit()
                logger.info(f"  💾 原子事务提交: {len(matched)} 条记录")

            except Exception as e:
                conn.rollback()
                logger.error(f"  ❌ 事务回滚: {e}")
                raise

        result['updated'] = len(matched)

        # 计算状态
        missing_after = len(db_matches) - len(matched)
        if missing_after == 0:
            result['status'] = 'SUCCESS'
        elif len(matched) > 0:
            result['status'] = 'PARTIAL'
        else:
            result['status'] = 'FAILED'

        cur.close()
        conn.close()

        # 保存匹配失败记录
        if failures:
            result['failures'] = failures

    except Exception as e:
        logger.error(f"  ❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        result['status'] = 'FAILED'

    # V132.4: 巡航大盘
    print_dashboard(league_name, season, result)

    return result


# =============================================================================
# 主入口
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="V132.0 全页码收割引擎")
    parser.add_argument("--league", help="指定联赛名称")
    parser.add_argument("--season", help="指定赛季")
    parser.add_argument("--limit", type=int, help="处理联赛数量限制")
    parser.add_argument("--dry-run", action="store_true", help="干运行（不更新数据库）")
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("V132.0 全页码收割引擎 (Full Page Harvest Engine)")
    logger.info("=" * 80)

    if args.dry_run:
        logger.info("⚠️  干运行模式 - 不会更新数据库")

    # 获取待处理的联赛
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    cur = conn.cursor()

    if args.league and args.season:
        cur.execute("""
            SELECT DISTINCT league_name, season
            FROM matches
            WHERE league_name = %s AND season = %s
              AND oddsportal_url IS NULL
            LIMIT 1
        """, (args.league, args.season))
    else:
        cur.execute("""
            SELECT league_name, season
            FROM matches
            WHERE oddsportal_url IS NULL
            GROUP BY league_name, season
            ORDER BY COUNT(*) - COUNT(oddsportal_url) DESC
            LIMIT %s
        """, (args.limit or 10,))

    tasks = cur.fetchall()
    cur.close()
    conn.close()

    logger.info(f"\n📋 待处理任务: {len(tasks)} 个联赛/赛季")

    # 启动浏览器
    stats = HarvestStats()
    stats.leagues_total = len(tasks)
    mapper = LeagueUrlMapper()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=STEALTH_BROWSER_ARGS
        )

        context = await browser.new_context(
            user_agent=STEALTH_USER_AGENT,
            viewport={"width": 1920, "height": 1080}
        )

        await apply_stealth_armor(context.pages[0] if context.pages else await context.new_page())
        await warm_up_browser(context.pages[0] if context.pages else await context.new_page())

        page = context.pages[0] if context.pages else await context.new_page()

        # 处理每个联赛
        for idx, (league_name, season) in enumerate(tasks, 1):
            logger.info(f"\n{'#' * 70}")
            logger.info(f"# 进度: {idx}/{len(tasks)}")
            logger.info(f"{'#' * 70}")

            # 转换赛季格式 "23/24" -> "2023-2024"
            def normalize_season(season_str: str) -> str:
                parts = season_str.split('/')
                if len(parts) == 2:
                    y1, y2 = parts
                    if len(y1) == 2:
                        y1 = "20" + y1
                    if len(y2) == 2:
                        y2 = "20" + y2
                    return f"{y1}-{y2}"
                return season_str

            normalized_season = normalize_season(season)

            # 构造结果页 URL
            url = mapper.construct_results_url(league_name, normalized_season)

            if not url:
                logger.warning(f"  ⚠️  无法构造 URL: {league_name} {season}")
                stats.leagues_failed += 1
                continue

            result = await harvest_league_full(
                page,
                league_name,
                season,
                url,
                args.dry_run
            )

            stats.pages_attempted += result['total'] / 50  # 估算
            stats.pages_succeeded += len(result.get('pages_success', []))
            stats.pages_failed += len(result.get('pages_failed', []))
            stats.matches_extracted += result['extracted']
            stats.matches_matched += result['matched']
            stats.urls_updated += result['updated']

            if result['skipped']:
                stats.leagues_skipped += 1
                stats.leagues_succeeded += 1
            elif result['status'] in ['SUCCESS', 'PARTIAL']:
                stats.leagues_succeeded += 1
            else:
                stats.leagues_failed += 1

            # 记录匹配失败
            if 'failures' in result:
                stats.matching_failures.extend(result['failures'])

            # 联赛间延迟（关键：防止被封 IP）
            if idx < len(tasks):
                delay = random.uniform(15, 30)
                logger.info(f"\n  ⏸️  等待 {delay:.1f} 秒后处理下一联赛...")
                await asyncio.sleep(delay)

        await context.close()
        await browser.close()

    # 打印摘要
    logger.info(stats.summary())

    # 保存匹配失败记录
    if stats.matching_failures:
        failure_file = Path("logs/v132_0_matching_failures.json")
        failure_file.parent.mkdir(parents=True, exist_ok=True)
        with open(failure_file, "w") as f:
            json.dump(stats.matching_failures, f, indent=2, ensure_ascii=False)
        logger.info(f"\n  💾 匹配失败记录已保存到: {failure_file}")


if __name__ == "__main__":
    asyncio.run(main())
