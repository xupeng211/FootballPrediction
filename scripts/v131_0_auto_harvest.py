#!/usr/bin/env python3
"""V131.0 全自动化收割流水线 (Auto Harvest Pipeline).

核心特性：
    1. 多页自动探测 - 动态计算页数，自动抓取所有页面
    2. 二段式匹配 - 严格规范化 + Fuzzy Matching，目标 >85% 匹配率
    3. 断点续传 - 自动跳过已完成的联赛
    4. 风控规避 - 随机延迟，模拟真实用户行为
    5. 原子化更新 - 每个联赛独立提交，确保数据一致性

Usage:
    # 英超 23/24 专项测试
    python scripts/v131_0_auto_harvest.py --league "Premier League" --season "23/24"

    # 批量处理所有联赛
    python scripts/v131_0_auto_harvest.py

    # 指定联赛数量
    python scripts/v131_0_auto_harvest.py --limit 3

    # 干运行（不更新数据库）
    python scripts/v131_0_auto_harvest.py --dry-run
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
    """V131.0 收割统计."""

    def __init__(self) -> None:
        self.leagues_total = 0
        self.leagues_skipped = 0
        self.leagues_succeeded = 0
        self.leagues_failed = 0
        self.pages_captured = 0
        self.matches_extracted = 0
        self.matches_matched = 0
        self.urls_updated = 0
        self.matching_failures = []
        self.start_time = datetime.now()

    def summary(self) -> str:
        """生成执行摘要."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        success_rate = (self.leagues_succeeded / self.leagues_total * 100) if self.leagues_total > 0 else 0
        match_rate = (self.matches_matched / self.matches_extracted * 100) if self.matches_extracted > 0 else 0

        return f"""
╔═══════════════════════════════════════════════════════════════╗
║              V131.0 全自动化收割流水线 - 执行摘要               ║
╠═══════════════════════════════════════════════════════════════╣
║ 总联赛数:         {self.leagues_total:>5}                                      ║
║ 已完成(跳过):     {self.leagues_skipped:>5}                                      ║
║ 成功处理:         {self.leagues_succeeded:>5}  ({success_rate:>5.1f}%)                         ║
║ 失败:             {self.leagues_failed:>5}                                      ║
║ 捕获页面数:       {self.pages_captured:>5}                                      ║
║ 提取比赛数:       {self.matches_extracted:>5}                                      ║
║ 匹配成功数:       {self.matches_matched:>5}  ({match_rate:>5.1f}%)                         ║
║ 更新 URL 数:      {self.urls_updated:>5}                                      ║
║ 匹配失败数:       {len(self.matching_failures):>5}                                      ║
║ 执行时间:         {elapsed:>8.1f} 秒                                ║
║ 匹配速率:         {self.matches_matched / elapsed if elapsed > 0 else 0:>8.2f} 场/秒                          ║
╚═══════════════════════════════════════════════════════════════╝"""


# =============================================================================
# V129.2: AES-CBC 解密引擎
# =============================================================================

async def decrypt_oddsportal_response(encrypted_data: str) -> str | None:
    """V129.2 AES-CBC 解密引擎.

    Args:
        encrypted_data: 加密的数据 (格式: {base64_encrypted_data}:{hex_iv})

    Returns:
        解密后的 JSON 字符串，失败返回 None
    """
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


def extract_match_info_from_json(data: str) -> list[dict]:
    """从解密后的 JSON 中提取比赛信息.

    Returns:
        比赛信息列表
    """
    matches = []
    try:
        data = json.loads(data)
    except:
        return matches

    if not isinstance(data, dict) or 'd' not in data:
        return matches

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
    return matches


# =============================================================================
# V131.1: 多页自动探测引擎
# =============================================================================

async def capture_all_pages(
    page: Page,
    results_url: str,
    max_wait_time: int = 45
) -> tuple[list[dict], int]:
    """V131.1 多页自动探测引擎.

    核心逻辑：
    1. 捕获第 1 页并解密
    2. 从 JSON 中读取 total 字段
    3. 计算总页数 = ceil(total / 50)
    4. 迭代捕获所有页面

    Args:
        page: Playwright 页面实例
        results_url: 目标联赛结果页 URL
        max_wait_time: 每页最大等待时间

    Returns:
        (所有页面的比赛数据列表, 总比赛数)
    """
    all_matches = []
    page_num = 1
    total_matches = 0
    max_pages = 15  # 最多 15 页（足够了）

    logger.info(f"  📍 目标 URL: {results_url[:80]}...")

    while page_num <= max_pages:
        logger.info(f"  📄 捕获第 {page_num} 页...")

        # 存储捕获的响应
        captured_response = None
        capture_event = asyncio.Event()

        async def handle_response(response):
            nonlocal captured_response
            try:
                url = response.url
                if TARGET_API_KEYWORD not in url:
                    return

                logger.info(f"    🎯 检测到目标 API")

                if response.status != 200:
                    return

                body_bytes = await response.body()
                body = body_bytes.decode('utf-8', errors='ignore')

                logger.info(f"    📦 响应体大小: {len(body)} 字节")

                if len(body) < MIN_PAYLOAD_SIZE:
                    logger.warning(f"    ⚠️  响应体较小，但仍尝试")

                captured_response = {'body': body, 'size': len(body)}
                capture_event.set()

            except Exception as e:
                logger.debug(f"    ⚠️  响应处理异常: {e}")

        # 注册响应处理器
        page.on('response', handle_response)

        # 构造带页码的 URL
        if page_num == 1:
            target_url = results_url
        else:
            # 使用 URL hash 来切换页面
            target_url = f"{results_url}#/page/{page_num}/"

        # 导航到目标页面
        try:
            await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
        except Exception:
            pass

        # 滚动触发 API
        for _ in range(20):
            if capture_event.is_set():
                break
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(0.3)

        # 等待捕获
        try:
            await asyncio.wait_for(capture_event.wait(), timeout=max_wait_time)
        except asyncio.TimeoutError:
            pass

        # 注销响应处理器
        page.remove_listener('response', handle_response)

        # 检查是否捕获成功
        if captured_response:
            # 解密
            decrypted = await decrypt_oddsportal_response(captured_response['body'])
            if decrypted:
                matches = extract_match_info_from_json(decrypted)
                if matches:
                    logger.info(f"    ✅ 第 {page_num} 页: {len(matches)} 场比赛")
                    all_matches.extend(matches)

                    # 第一页时，读取 total 并计算总页数
                    if page_num == 1:
                        try:
                            json_data = json.loads(decrypted)
                            total_matches = json_data['d'].get('total', 0)
                            per_page = json_data['d'].get('onePage', 50)
                            expected_pages = (total_matches + per_page - 1) // per_page
                            logger.info(f"    📊 联赛总比赛数: {total_matches}")
                            logger.info(f"    📊 预计总页数: {expected_pages}")
                            max_pages = expected_pages
                        except:
                            pass

                    # 检查是否已到最后一页
                    if page_num >= max_pages:
                        logger.info(f"    📋 已采集全部 {max_pages} 页")
                        break
                else:
                    logger.warning(f"    ⚠️  第 {page_num} 页解密成功但无数据")
                    break
            else:
                logger.warning(f"    ⚠️  第 {page_num} 页解密失败")
                break
        else:
            logger.warning(f"    ⚠️  第 {page_num} 页未捕获到数据")
            break

        page_num += 1
        # 页间延迟
        await asyncio.sleep(random.uniform(3, 6))

    return all_matches, total_matches


# =============================================================================
# V131.2: 二段式高精度匹配
# =============================================================================

def two_stage_matching(
    oddsportal_matches: list[dict],
    db_matches: list[tuple],
    normalizer: TeamNameNormalizer,
    threshold: float = 75.0
) -> tuple[list[tuple], list[dict]]:
    """V131.2 二段式高精度匹配.

    逻辑：
    1. 第一段：严格规范化匹配（完全匹配规范化后的队名）
    2. 第二段：对剩余的孤儿使用 fuzzy_match

    Args:
        oddsportal_matches: 从 OddsPortal 提取的比赛列表
        db_matches: 数据库中缺失 URL 的比赛列表 (match_id, home_team, away_team)
        normalizer: TeamNameNormalizer 实例
        threshold: fuzzy_match 阈值（默认 75%）

    Returns:
        (匹配成功的列表 [(match_id, url), ...], 匹配失败的列表)
    """
    matched = []
    unmatched = []
    failures = []

    # 创建规范化后的查找字典
    normalized_op_matches = {}
    for m in oddsportal_matches:
        norm_home = normalizer.normalize(m['home_team'])
        norm_away = normalizer.normalize(m['away_team'])
        key = (norm_home, norm_away)
        normalized_op_matches[key] = m

    # 第一段：严格规范化匹配
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

    logger.info(f"    第一段（严格匹配）: {len(matched)} 场")

    # 第二段：Fuzzy Matching
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
        else:
            # 记录匹配失败的
            unmatched.append({
                'match_id': db_id,
                'home_team': db_home,
                'away_team': db_away,
                'reason': 'no_match_above_threshold'
            })

    logger.info(f"    第二段（Fuzzy Matching）: {len(matched) - len(db_remaining) + len(db_remaining)} 场")

    # 记录低分匹配（< 60%）
    low_score_matches = [m for m in matched if m[4] < 60]
    if low_score_matches:
        logger.warning(f"    ⚠️  低分匹配（< 60%）: {len(low_score_matches)} 场")
        for m in low_score_matches[:5]:
            failures.append({
                'match_id': m[0],
                'home_team': m[2],
                'away_team': m[3],
                'url': m[1],
                'score': m[4],
                'reason': 'low_score'
            })

    return matched, failures


# =============================================================================
# V131.3: 全自动巡航与风控
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
        await page.goto(f"{BASE_URL}/", timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        for _ in range(2):
            await page.mouse.wheel(0, random.randint(200, 500))
            await asyncio.sleep(random.uniform(0.5, 1.0))
    except Exception:
        logger.debug("    暖机超时（继续执行）")


def check_league_status(league_name: str, season: str) -> bool:
    """检查联赛是否已完成（断点续传）.

    Args:
        league_name: 联赛名称
        season: 赛季

    Returns:
        True 如果已完成，False 如果需要处理
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    cur = conn.cursor()

    # 检查 match_search_queue 中是否有 SUCCESS 状态
    cur.execute("""
        SELECT COUNT(*) FROM match_search_queue
        WHERE league_name = %s AND season = %s
          AND status = 'SUCCESS'
    """, (league_name, season))

    count = cur.fetchone()[0]
    cur.close()
    conn.close()

    # 如果有 SUCCESS 记录，说明已完成
    return count > 0


async def harvest_league(
    page: Page,
    league_name: str,
    season: str,
    results_url: str,
    dry_run: bool = False
) -> dict[str, Any]:
    """收割单个联赛.

    Args:
        page: Playwright 页面实例
        league_name: 联赛名称
        season: 赛季
        results_url: 结果页 URL
        dry_run: 是否干运行

    Returns:
        收割结果统计
    """
    logger.info(f"\n{'=' * 60}")
    logger.info(f"🏆 处理: {league_name} {season}")
    logger.info(f"{'=' * 60}")

    result = {
        'league': league_name,
        'season': season,
        'matches_found': 0,
        'matches_matched': 0,
        'urls_updated': 0,
        'success': False,
        'skipped': False
    }

    # 检查是否已完成（断点续传）
    if check_league_status(league_name, season):
        logger.info(f"  ⏭️  联赛已完成，跳过")
        result['skipped'] = True
        result['success'] = True
        return result

    try:
        # 捕获所有页面
        matches, total = await capture_all_pages(page, results_url)

        if not matches:
            logger.warning(f"  ⚠️  未提取到比赛数据")
            return result

        result['matches_found'] = len(matches)
        logger.info(f"  📦 共提取 {len(matches)} 场比赛（总联赛应有 {total} 场）")

        # 获取数据库中该联赛的比赛
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )
        cur = conn.cursor()

        # 查询缺失 URL 的比赛
        cur.execute("""
            SELECT match_id, home_team, away_team
            FROM matches
            WHERE league_name = %s AND season = %s
              AND oddsportal_url IS NULL
        """, (league_name, season))

        db_matches = cur.fetchall()
        logger.info(f"  🔍 数据库中缺失 URL: {len(db_matches)} 场")

        # 二段式匹配
        normalizer = TeamNameNormalizer()
        matched, failures = two_stage_matching(matches, db_matches, normalizer)

        result['matches_matched'] = len(matched)

        if matched:
            # 显示匹配统计
            high_quality = [m for m in matched if m[4] >= 90]
            medium_quality = [m for m in matched if 75 <= m[4] < 90]
            low_quality = [m for m in matched if m[4] < 75]

            logger.info(f"  📊 匹配质量分布:")
            logger.info(f"     高质量（≥90%）: {len(high_quality)} 场")
            logger.info(f"     中质量（75-90%）: {len(medium_quality)} 场")
            logger.info(f"     低质量（<75%）: {len(low_quality)} 场")

            match_rate = len(matched) / len(db_matches) * 100 if db_matches else 0
            logger.info(f"  📈 匹配率: {match_rate:.1f}%")

        # 批量更新
        if matched and not dry_run:
            # 更新 matches 表
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
            logger.info(f"  💾 批量更新 {len(matched)} 条记录")

        result['urls_updated'] = len(matched)
        result['success'] = True

        cur.close()
        conn.close()

    except Exception as e:
        logger.error(f"  ❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()

    return result


# =============================================================================
# V131.4: 主流程
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="V131.0 全自动化收割流水线")
    parser.add_argument("--league", help="指定联赛名称")
    parser.add_argument("--season", help="指定赛季")
    parser.add_argument("--limit", type=int, help="处理联赛数量限制")
    parser.add_argument("--dry-run", action="store_true", help="干运行（不更新数据库）")
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("V131.0 全自动化收割流水线")
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
        """, (args.limit or 50,))

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
            logger.info(f"\n{'#' * 60}")
            logger.info(f"# 进度: {idx}/{len(tasks)}")
            logger.info(f"{'#' * 60}")

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

            result = await harvest_league(
                page,
                league_name,
                season,
                url,
                args.dry_run
            )

            if result['skipped']:
                stats.leagues_skipped += 1
                stats.leagues_succeeded += 1
            elif result['success']:
                stats.leagues_succeeded += 1
                stats.pages_captured += 1  # 实际应该是页数，这里简化
                stats.matches_extracted += result['matches_found']
                stats.matches_matched += result['matches_matched']
                stats.urls_updated += result['urls_updated']
            else:
                stats.leagues_failed += 1

            # 联赛间延迟（关键：防止被封 IP）
            if idx < len(tasks):
                delay = random.uniform(20, 40)
                logger.info(f"\n  ⏸️  等待 {delay:.1f} 秒后处理下一联赛...")
                await asyncio.sleep(delay)

        await context.close()
        await browser.close()

    # 打印摘要
    logger.info(stats.summary())

    # 保存匹配失败记录
    if stats.matching_failures:
        failure_file = Path("logs/v131_0_matching_failures.json")
        with open(failure_file, "w") as f:
            json.dump(stats.matching_failures, f, indent=2, ensure_ascii=False)
        logger.info(f"\n  💾 匹配失败记录已保存到: {failure_file}")


if __name__ == "__main__":
    asyncio.run(main())
