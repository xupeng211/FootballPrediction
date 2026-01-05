#!/usr/bin/env python3
"""V130.0 全量收割流水线 (Grand Harvest Pipeline).

整合 V129.2 AES-CBC 解密引擎，批量补全缺失的 OddsPortal 链接。

核心特性：
    1. 任务聚类 - 按 (league_name, season) 分组
    2. 多页采集 - 自动获取所有分页数据
    3. 即时解密 - 使用 V129.2 解密引擎实时解密
    4. Fuzzy Matching - 高精度队伍名匹配
    5. 批量入库 - 更新 matches 和 match_search_queue

Usage:
    # 测试英超 23/24
    python scripts/v130_0_grand_harvest.py --league "Premier League" --season "23/24"

    # 批量处理所有联赛
    python scripts/v130_0_grand_harvest.py

    # 指定联赛数量
    python scripts/v130_0_grand_harvest.py --limit 3

    # 干运行（不更新数据库）
    python scripts/v130_0_grand_harvest.py --dry-run
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import random
import sys
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

# V129.2 AES Keys
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
    """V130.0 收割统计."""

    def __init__(self) -> None:
        self.leagues_processed = 0
        self.leagues_succeeded = 0
        self.leagues_failed = 0
        self.pages_captured = 0
        self.matches_extracted = 0
        self.matches_matched = 0
        self.urls_updated = 0
        self.start_time = datetime.now()

    def summary(self) -> str:
        """生成执行摘要."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        success_rate = (self.leagues_succeeded / self.leagues_processed * 100) if self.leagues_processed > 0 else 0

        return f"""
╔═══════════════════════════════════════════════════════════════╗
║              V130.0 全量收割流水线 - 执行摘要                   ║
╠═══════════════════════════════════════════════════════════════╣
║ 处理联赛数:       {self.leagues_processed:>5}                                      ║
║ 成功联赛数:       {self.leagues_succeeded:>5}  ({success_rate:>5.1f}%)                         ║
║ 失败联赛数:       {self.leagues_failed:>5}                                      ║
║ 捕获页面数:       {self.pages_captured:>5}                                      ║
║ 提取比赛数:       {self.matches_extracted:>5}                                      ║
║ 匹配数据库数:     {self.matches_matched:>5}                                      ║
║ 更新 URL 数:      {self.urls_updated:>5}                                      ║
║ 执行时间:         {elapsed:>8.1f} 秒                                ║
║ 匹配速率:         {self.matches_matched / elapsed if elapsed > 0 else 0:>8.2f} 场/秒                          ║
╚═══════════════════════════════════════════════════════════════╝"""


async def decrypt_oddsportal_response(encrypted_data: str) -> str | None:
    """V129.2 AES-CBC 解密引擎.

    Args:
        encrypted_data: 加密的数据 (格式: {base64_encrypted_data}:{hex_iv})

    Returns:
        解密后的 JSON 字符串，失败返回 None
    """
    try:
        # 按格式解析: "EncryptedData:IV"
        if ':' not in encrypted_data:
            return None

        encrypted_b64, iv_hex = encrypted_data.rsplit(':', 1)

        # IV 是 hex 字符串，转换为 bytes
        iv = bytes.fromhex(iv_hex)
        # 加密数据是 Base64 编码
        encrypted_bytes = base64.b64decode(encrypted_b64)

        # 使用 PBKDF2 派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=ODDSPORTAL_SALT.encode('utf-8'),
            iterations=1000,
            backend=default_backend()
        )
        key = kdf.derive(ODDSPORTAL_PASSWORD.encode('utf-8'))

        # AES-CBC 解密
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
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
        比赛信息列表，每项包含: url, home_team, away_team, match_id
    """
    matches = []

    try:
        data = json.loads(data)
    except:
        return matches

    # OddsPortal API 返回格式: {"s": 1, "d": {"total": 380, "rows": [...]}}
    if not isinstance(data, dict) or 'd' not in data:
        return matches

    rows = data['d'].get('rows', [])
    for row in rows:
        if 'encodeEventId' in row:
            match_info = {
                'url': f"https://www.oddsportal.com/match/{row['encodeEventId']}/",
                'match_id': row.get('id'),
                'encode_event_id': row['encodeEventId'],
                'home_team': row.get('home-name'),
                'away_team': row.get('away-name'),
                'status': row.get('event-stage-name'),
                'timestamp': row.get('colClassName', '')
            }
            matches.append(match_info)

    return matches


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
    except Exception as e:
        logger.debug(f"    ⚠️  暖机超时（继续执行）: {e}")


async def capture_all_pages(
    page: Page,
    results_url: str,
    max_wait_time: int = 45
) -> list[dict]:
    """捕获联赛的所有分页数据.

    Args:
        page: Playwright 页面实例
        results_url: 目标联赛结果页 URL
        max_wait_time: 每页最大等待时间

    Returns:
        所有页面的比赛数据列表
    """
    all_matches = []
    page_num = 1
    max_pages = 10  # 最多 10 页（通常够用）

    logger.info(f"  📍 目标 URL: {results_url}")

    while page_num <= max_pages:
        logger.info(f"  📄 采集第 {page_num} 页...")

        # 存储捕获的响应
        captured_response = None
        capture_event = asyncio.Event()
        api_detected = False

        async def handle_response(response):
            nonlocal captured_response, api_detected
            try:
                url = response.url

                # 记录所有 ajax 响应用于调试
                if 'ajax' in url.lower():
                    logger.debug(f"    📡 AJAX 响应: {url[:80]}...")

                if TARGET_API_KEYWORD in url:
                    api_detected = True
                    logger.info(f"    🎯 检测到目标 API: {url[:80]}...")

                if TARGET_API_KEYWORD not in url:
                    return

                if response.status != 200:
                    logger.warning(f"    ❌ 状态码: {response.status}")
                    return

                body_bytes = await response.body()
                body = body_bytes.decode('utf-8', errors='ignore')

                logger.info(f"    📦 响应体大小: {len(body)} 字节")

                if len(body) < MIN_PAYLOAD_SIZE:
                    logger.warning(f"    ⚠️  响应体太小: {len(body)} < {MIN_PAYLOAD_SIZE}")
                    # V130.0: 不要因为大小而放弃

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
            # 添加分页参数
            target_url = f"{results_url}#/page/{page_num}/"

        # 导航到目标页面
        try:
            logger.debug(f"    🌐 导航到: {target_url[:100]}...")
            await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
        except Exception as e:
            logger.debug(f"    ⚠️  导航异常: {e}")

        # 滚动触发 API
        for i in range(20):
            if capture_event.is_set():
                break
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(0.3)

        # 等待捕获
        try:
            await asyncio.wait_for(capture_event.wait(), timeout=max_wait_time)
        except asyncio.TimeoutError:
            logger.debug(f"    ⏱️  等待超时")

        # 注销响应处理器
        page.remove_listener('response', handle_response)

        # 调试信息
        if not api_detected:
            logger.warning(f"    ⚠️  未检测到目标 API 关键字: {TARGET_API_KEYWORD}")

        # 检查是否捕获成功
        if captured_response:
            # 解密
            decrypted = await decrypt_oddsportal_response(captured_response['body'])
            if decrypted:
                matches = extract_match_info_from_json(decrypted)
                if matches:
                    logger.info(f"    ✅ 第 {page_num} 页: {len(matches)} 场比赛")
                    all_matches.extend(matches)

                    # 检查是否是最后一页
                    try:
                        json_data = json.loads(decrypted)
                        total = json_data['d'].get('total', 0)
                        per_page = json_data['d'].get('onePage', 50)
                        expected_pages = (total + per_page - 1) // per_page

                        if page_num >= expected_pages:
                            logger.info(f"    📋 已采集全部 {expected_pages} 页")
                            break
                    except:
                        pass
                else:
                    logger.warning(f"    ⚠️  第 {page_num} 页解密成功但无数据")
                    # 可能是最后一页后的空页
                    break
            else:
                logger.warning(f"    ⚠️  第 {page_num} 页解密失败")
                # 连续失败则停止
                break
        else:
            logger.warning(f"    ⚠️  第 {page_num} 页未捕获到数据")
            break

        page_num += 1
        # 页间延迟
        await asyncio.sleep(random.uniform(3, 6))

    return all_matches


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
        'success': False
    }

    try:
        # 捕获所有页面
        matches = await capture_all_pages(page, results_url)

        if not matches:
            logger.warning(f"  ⚠️  未提取到比赛数据")
            return result

        result['matches_found'] = len(matches)
        logger.info(f"  📦 共提取 {len(matches)} 场比赛")

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
            SELECT id, home_team, away_team, match_date
            FROM matches
            WHERE league_name = %s AND season = %s
              AND oddsportal_url IS NULL
        """, (league_name, season))

        db_matches = cur.fetchall()

        # Fuzzy matching
        normalizer = TeamNameNormalizer()
        update_data = []

        for db_id, db_home, db_away, db_date in db_matches:
            best_match = None
            best_score = 0

            for m in matches:
                # 计算主队相似度
                home_score = normalizer.fuzzy_match(db_home, m['home_team'])
                # 计算客队相似度
                away_score = normalizer.fuzzy_match(db_away, m['away_team'])

                # 平均分数
                avg_score = (home_score + away_score) / 2

                if avg_score > best_score and avg_score > 75:  # 阈值 75%
                    best_score = avg_score
                    best_match = m

            if best_match:
                update_data.append((db_id, best_match['url'], best_match['url']))
                logger.debug(f"    ✅ 匹配: {db_home} vs {db_away} -> {best_match['url']} (分数: {best_score:.1f})")

        # 批量更新
        if update_data and not dry_run:
            cur.executemany("""
                UPDATE matches
                SET oddsportal_url = %s
                WHERE id = %s
            """, [(url, match_id) for match_id, url, _ in update_data])

            # 更新 match_search_queue
            cur.executemany("""
                UPDATE match_search_queue
                SET status = 'SUCCESS',
                    oddsportal_url = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE match_id = %s
            """, [(url, match_id) for match_id, _, url in update_data])

            conn.commit()
            logger.info(f"  💾 批量更新 {len(update_data)} 条记录")

        result['matches_matched'] = len(update_data)
        result['urls_updated'] = len(update_data)
        result['success'] = True

        cur.close()
        conn.close()

    except Exception as e:
        logger.error(f"  ❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()

    return result


async def main():
    parser = argparse.ArgumentParser(description="V130.0 全量收割流水线")
    parser.add_argument("--league", help="指定联赛名称")
    parser.add_argument("--season", help="指定赛季")
    parser.add_argument("--limit", type=int, help="处理联赛数量限制")
    parser.add_argument("--dry-run", action="store_true", help="干运行（不更新数据库）")
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("V130.0 全量收割流水线")
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
        """, (args.limit or 20,))

    tasks = cur.fetchall()
    cur.close()
    conn.close()

    logger.info(f"\n📋 待处理任务: {len(tasks)} 个联赛/赛季")

    # 启动浏览器
    stats = HarvestStats()
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
        for league_name, season in tasks:
            stats.leagues_processed += 1

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

            if result['success']:
                stats.leagues_succeeded += 1
                stats.matches_extracted += result['matches_found']
                stats.matches_matched += result['matches_matched']
                stats.urls_updated += result['urls_updated']
            else:
                stats.leagues_failed += 1

            # 联赛间延迟
            await asyncio.sleep(random.uniform(15, 30))

        await context.close()
        await browser.close()

    # 打印摘要
    logger.info(stats.summary())


if __name__ == "__main__":
    asyncio.run(main())
