#!/usr/bin/env python3
"""V130.0 简化测试 - 使用 V126.0 捕获 + V129.2 解密."""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                  'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(proxy_var, None)

import psycopg2
from playwright.async_api import async_playwright, Page

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer, LeagueUrlMapper

# V129.2 Decryption
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://www.oddsportal.com"
MIN_PAYLOAD_SIZE = 10 * 1024
TARGET_API_KEYWORD = "ajax-sport-country-tournament-archive_"

# V129.2 AES Keys
ODDSPORTAL_PASSWORD = "J*8sQ!p$7aD_fR2yW@gHn*3bVp#sAdLd_k"
ODDSPORTAL_SALT = "5b9a8f2c3e6d1a4b7c8e9d0f1a2b3c4d"

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


async def decrypt_oddsportal_response(encrypted_data: str) -> str | None:
    """V129.2 AES-CBC 解密."""
    try:
        if ':' not in encrypted_data:
            return None

        encrypted_b64, iv_hex = encrypted_data.rsplit(':', 1)
        iv = bytes.fromhex(iv_hex)
        encrypted_bytes = base64.b64decode(encrypted_b64)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=ODDSPORTAL_SALT.encode('utf-8'),
            iterations=1000,
            backend=default_backend()
        )
        key = kdf.derive(ODDSPORTAL_PASSWORD.encode('utf-8'))

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(encrypted_bytes) + decryptor.finalize()

        padding_length = decrypted_padded[-1]
        decrypted = decrypted_padded[:-padding_length]

        return decrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"  ❌ 解密失败: {e}")
        return None


def extract_match_info_from_json(data: str) -> list[dict]:
    """从解密后的 JSON 中提取比赛信息."""
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
            })
    return matches


async def capture_api(page: Page, results_url: str) -> dict | None:
    """捕获 API 响应."""
    captured_response = None
    capture_event = asyncio.Event()

    async def handle_response(response):
        nonlocal captured_response
        try:
            url = response.url
            if TARGET_API_KEYWORD not in url:
                return
            if response.status != 200:
                return

            body_bytes = await response.body()
            body = body_bytes.decode('utf-8', errors='ignore')

            if len(body) < MIN_PAYLOAD_SIZE:
                return

            captured_response = {'body': body, 'size': len(body)}
            logger.info(f"  🎯 检测到目标 API: {url[:60]}...")
            logger.info(f"  📦 响应体大小: {len(body)} 字节")
            capture_event.set()
        except:
            pass

    page.on('response', handle_response)

    try:
        await page.goto(results_url, timeout=30000, wait_until="domcontentloaded")
    except:
        pass

    for _ in range(20):
        if capture_event.is_set():
            break
        await page.mouse.wheel(0, 500)
        await asyncio.sleep(0.3)

    try:
        await asyncio.wait_for(capture_event.wait(), timeout=30)
    except asyncio.TimeoutError:
        pass

    page.remove_listener('response', handle_response)
    return captured_response


async def main():
    logger.info("=" * 60)
    logger.info("V130.0 简化测试 - V126.0 捕获 + V129.2 解密")
    logger.info("=" * 60)

    mapper = LeagueUrlMapper()
    normalizer = TeamNameNormalizer()

    # 转换赛季格式
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

    league_name = "Premier League"
    season = "23/24"
    normalized_season = normalize_season(season)

    results_url = mapper.construct_results_url(league_name, normalized_season)
    logger.info(f"📍 目标 URL: {results_url}")

    # 启动浏览器
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=STEALTH_BROWSER_ARGS
        )

        context = await browser.new_context(
            user_agent=STEALTH_USER_AGENT,
            viewport={"width": 1920, "height": 1080}
        )

        page = await context.new_page()

        # 捕获 API
        captured = await capture_api(page, results_url)

        await context.close()
        await browser.close()

    if not captured:
        logger.error("❌ 未捕获到数据")
        return

    # 解密
    logger.info("🔓 开始解密...")
    decrypted = await decrypt_oddsportal_response(captured['body'])

    if not decrypted:
        logger.error("❌ 解密失败")
        return

    logger.info("✅ 解密成功!")

    # 提取比赛
    matches = extract_match_info_from_json(decrypted)
    logger.info(f"📊 提取到 {len(matches)} 场比赛")

    if matches:
        logger.info("\n🎯 前 10 场比赛:")
        for i, m in enumerate(matches[:10], 1):
            logger.info(f"  [{i:2d}] {m['home_team']} vs {m['away_team']:20s} -> {m['url']}")

        # 查询数据库中缺失 URL 的比赛
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
            SELECT id, home_team, away_team
            FROM matches
            WHERE league_name = %s AND season = %s
              AND oddsportal_url IS NULL
            LIMIT 50
        """, (league_name, season))

        db_matches = cur.fetchall()

        # Fuzzy matching
        update_data = []
        for db_id, db_home, db_away in db_matches:
            best_match = None
            best_score = 0

            for m in matches:
                home_score = normalizer.fuzzy_match(db_home, m['home_team'])
                away_score = normalizer.fuzzy_match(db_away, m['away_team'])
                avg_score = (home_score + away_score) / 2

                if avg_score > best_score and avg_score > 75:
                    best_score = avg_score
                    best_match = m

            if best_match:
                update_data.append((db_id, best_match['url'], db_home, db_away, best_score))

        # 显示匹配结果
        if update_data:
            logger.info(f"\n🎉 成功匹配 {len(update_data)} 场比赛:")
            for i, (db_id, url, home, away, score) in enumerate(update_data[:10], 1):
                logger.info(f"  [{i:2d}] {home} vs {away:20s} -> {url} (分数: {score:.1f})")

            logger.info(f"\n✅✅✅ 加密协议已彻底击穿！✅✅✅")
            logger.info(f"🎉 成功匹配 {len(update_data)} 场比赛，准备批量更新数据库")
        else:
            logger.warning("⚠️  未匹配到任何比赛")

        cur.close()
        conn.close()

    logger.info("\n" + "=" * 60)
    logger.info("🏆 V130.0 测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
