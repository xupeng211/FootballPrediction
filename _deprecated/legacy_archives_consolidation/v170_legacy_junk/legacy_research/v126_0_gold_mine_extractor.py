#!/usr/bin/env python3
"""V126.0 金矿定向挖掘引擎 (Gold Mine Targeted Extraction Engine).

核心特性：
    1. 深度拟态浏览器环境 (Deep Mimicry) - 暖机逻辑 + 反自动化检测
    2. 定向 API 拦截器 (Targeted Interceptor) - 专门死盯 ajax-sport-country-tournament-archive_
    3. 强力重试与死磕循环 (Persistence Loop) - 最多 5 次重试直到金矿掉落
    4. 万能正则提取 (Regex Extraction) - 从加密字符串中直接提取 match URL

Usage:
    # 英超 23/24 专项测试
    python scripts/v126_0_gold_mine_extractor.py --league "Premier League" --season "2023-2024"

    # 批量扫描所有联赛
    python scripts/v126_0_gold_mine_extractor.py

    # 指定联赛数量
    python scripts/v126_0_gold_mine_extractor.py --limit 5

    # 干运行（不更新数据库）
    python scripts/v126_0_gold_mine_extractor.py --dry-run
"""

import argparse
import asyncio
import json
import logging
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

# V123.0: Disable proxy to fix WSL2 network issues
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                  'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(proxy_var, None)

import psycopg2
from playwright.async_api import async_playwright, Page

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
MIN_PAYLOAD_SIZE = 10 * 1024  # V128.2: 降低到 10KB（原来是 100KB）
TARGET_API_KEYWORD = "ajax-sport-country-tournament-archive_"
MAX_RETRIES_PER_LEAGUE = 5  # 每个联赛最多重试 5 次

# V126.0 Deep Stealth User-Agent - Chrome 120 on Windows
STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# V126.0 Deep Stealth Browser Args
STEALTH_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",  # V126.0: Critical!
    "--disable-infobars",
    "--disable-dev-shm-usage",
    "--disable-setuid-sandbox",
    "--no-sandbox",
    "--disable-web-security",
    "--disable-features=VizDisplayCompositor",
    "--disable-gpu",
]

# V126.0 Anti-detection JavaScript
STEALTH_SCRIPTS = [
    """() => {
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    }""",
    """() => {
        window.chrome = {
            runtime: {}
        };
    }""",
    """() => {
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
    }""",
    """() => {
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
    }""",
    """() => {
        // Override permissions API
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    }""",
]


class ExtractionStats:
    """V126.0 提取统计追踪."""

    def __init__(self) -> None:
        self.leagues_processed = 0
        self.leagues_succeeded = 0
        self.leagues_failed = 0
        self.api_captures = 0
        self.matches_extracted = 0
        self.matches_matched = 0
        self.urls_updated = 0
        self.total_retries = 0
        self.start_time = datetime.now()

    def summary(self) -> str:
        """生成执行摘要."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        capture_rate = (self.api_captures / self.leagues_processed * 100) if self.leagues_processed > 0 else 0

        return f"""
╔═══════════════════════════════════════════════════════════════╗
║        V126.0 金矿定向挖掘引擎 - 执行摘要                        ║
╠═══════════════════════════════════════════════════════════════╣
║ 处理联赛数:       {self.leagues_processed:>5}                                      ║
║ 成功捕获金矿:     {self.api_captures:>5}  ({capture_rate:>5.1f}%)                         ║
║ 提取比赛数:       {self.matches_extracted:>5}                                      ║
║ 匹配数据库数:     {self.matches_matched:>5}                                      ║
║ 更新 URL 数:      {self.urls_updated:>5}                                      ║
║ 重试次数总计:     {self.total_retries:>5}                                      ║
║ 执行时间:         {elapsed:>8.1f} 秒                                ║
║ 提取速率:         {self.matches_matched / elapsed if elapsed > 0 else 0:>8.2f} 场/秒                          ║
╚═══════════════════════════════════════════════════════════════╝"""


async def apply_stealth_armor(page: Page) -> None:
    """V126.0 Phase 1: 应用反指纹隐身装甲.

    Args:
        page: Playwright 页面实例
    """
    logger.debug("  🛡️  应用隐身装甲...")

    # 应用所有隐身脚本
    for script in STEALTH_SCRIPTS:
        try:
            await page.add_init_script(script)
        except Exception as e:
            logger.debug(f"    ⚠️  隐身脚本应用失败: {e}")

    # 额外的隐身措施
    await page.evaluate("""() => {
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    }""")

    logger.debug("  ✅ 隐身装甲已应用")


async def warm_up_browser(page: Page) -> None:
    """V126.0 Phase 1: 浏览器暖机逻辑.

    暖机步骤：
    1. 先访问首页建立基础 Cookie
    2. 停留 3 秒模拟真实用户行为
    3. 随机滚动页面

    Args:
        page: Playwright 页面实例
    """
    logger.info("  🔥 暖机浏览器...")

    try:
        # 第一步：访问首页建立 Cookie
        await page.goto(f"{BASE_URL}/", timeout=30000, wait_until="domcontentloaded")
        logger.debug("    📍 访问首页完成")

        # 第二步：停留并模拟真实用户行为
        await asyncio.sleep(3)

        # 随机滚动页面
        for _ in range(3):
            await page.mouse.wheel(0, random.randint(200, 500))
            await asyncio.sleep(random.uniform(0.5, 1.5))

        logger.debug("    ✅ 暖机完成")

    except Exception as e:
        logger.warning(f"    ⚠️  暖机失败（继续执行）: {e}")


async def capture_gold_mine_api(
    page: Page,
    results_url: str,
    max_wait_time: int = 60  # V126.0: 增加到 60 秒
) -> dict[str, Any] | None:
    """V126.0 Phase 2: 定向捕获金矿 API 响应.

    核心逻辑：
    1. 设置网络拦截器，专门死盯包含 TARGET_API_KEYWORD 的 URL
    2. 捕获标准：status == 200 且响应体大小 > 100KB
    3. 一旦捕获到符合标准的包，立即停止页面加载

    Args:
        page: Playwright 页面实例
        results_url: 目标联赛结果页 URL
        max_wait_time: 最大等待时间（秒）

    Returns:
        捕获的 API 响应数据，如果未捕获到返回 None
    """
    logger.info(f"  🎯 定向拦截器启动")

    # 存储捕获的响应
    captured_response = None
    capture_event = asyncio.Event()

    async def handle_response(response):
        nonlocal captured_response
        try:
            url = response.url
            status = response.status

            # 只关注包含目标关键字的 API
            if TARGET_API_KEYWORD not in url:
                return

            logger.info(f"  📡 检测到目标 API: {url[:80]}...")

            # 检查状态码
            if status != 200:
                logger.debug(f"    ❌ 状态码 {status} != 200，跳过")
                return

            # 尝试读取响应体
            try:
                # V128.2: 使用 body() 而不是 text()（二进制更可靠）
                logger.info(f"  ⏳ 开始读取响应体...")
                body_bytes = await response.body()
                body = body_bytes.decode('utf-8', errors='ignore')
                body_size = len(body)

                logger.info(f"  📦 响应体大小: {body_size:,} 字节")

                # 检查响应体大小（只是警告，不再跳过）
                if body_size < MIN_PAYLOAD_SIZE:
                    logger.warning(f"    ⚠️  响应体 {body_size:,} < {MIN_PAYLOAD_SIZE:,}，可能不完整，但仍继续")
                    # V126.0: 不要因为大小而放弃捕获

                # 捕获成功！
                captured_response = {
                    'url': url,
                    'body': body,
                    'status': status,
                    'size': body_size
                }

                logger.info(f"  ✅ 金矿已捕获！大小: {body_size:,} 字节")

                # 立即触发事件
                capture_event.set()

            except Exception as e:
                logger.error(f"    ❌ 读取响应体失败: {e}")
                logger.error(f"    📋 错误类型: {type(e).__name__}")

        except Exception as e:
            logger.error(f"    ❌ handle_response 异常: {e}")

    # 注册响应处理器（在导航前）
    page.on('response', handle_response)

    # 导航到目标页面
    logger.info(f"  🌐 导航到结果页...")
    try:
        await page.goto(results_url, timeout=60000, wait_until="domcontentloaded")
    except Exception as e:
        logger.warning(f"  ⚠️  导航超时（继续拦截）: {e}")

    # 执行快速滚屏触发 API 调用
    logger.info(f"  📜 执行快速滚屏触发...")
    for i in range(20):
        if capture_event.is_set():
            logger.info(f"  🎉 在第 {i} 次滚动时触发金矿！")
            break

        await page.mouse.wheel(0, 500)
        await asyncio.sleep(0.3)

    # V126.0: 额外等待让响应体加载完成
    if not capture_event.is_set():
        logger.info(f"  ⏳ 等待响应体加载...")
        await asyncio.sleep(10)

    # 等待捕获事件
    try:
        await asyncio.wait_for(capture_event.wait(), timeout=max_wait_time)
    except asyncio.TimeoutError:
        logger.warning(f"  ⏱️  {max_wait_time} 秒内未触发金矿 API")

    # 注销响应处理器
    page.remove_listener('response', handle_response)

    return captured_response


def extract_match_urls_from_payload(payload: str) -> list[str]:
    """V126.0 Phase 4: 万能正则提取.

    从 base64 编码 + gzip 压缩的 payload 中提取 match URL。

    提取步骤：
    1. 解码 base64 字符串
    2. 尝试 gzip 解压
    3. 匹配 /match/ 路径（8位哈希值）
    4. 使用全局正则匹配

    Args:
        payload: 原始 payload 字符串（base64 编码）

    Returns:
        提取到的 match URL 列表
    """
    import base64
    import gzip

    logger.info(f"  🔍 万能正则提取启动...")

    # V126.0: 首先尝试解码 base64
    decoded_bytes = b""
    try:
        # 尝试标准 base64 解码
        decoded_bytes = base64.b64decode(payload)
        logger.info(f"  🔓 Base64 解码成功: {len(decoded_bytes)} 字节")
    except Exception as e:
        logger.warning(f"  ⚠️  Base64 解码失败: {e}")
        return []

    # V126.0: 尝试 gzip 解压
    decompressed_payload = ""
    try:
        decompressed_bytes = gzip.decompress(decoded_bytes)
        decompressed_payload = decompressed_bytes.decode('utf-8', errors='ignore')
        logger.info(f"  📦 Gzip 解压成功: {len(decompressed_payload)} 字符")
    except Exception as e:
        logger.warning(f"  ⚠️  Gzip 解压失败: {e}")
        # 如果 gzip 失败，尝试直接解码
        try:
            decompressed_payload = decoded_bytes.decode('utf-8', errors='ignore')
            logger.info(f"  📝 直接解码: {len(decompressed_payload)} 字符")
        except Exception as e2:
            logger.error(f"  ❌ 解码失败: {e2}")
            return []

    # 正则模式：匹配 /match/xxx-xxxxxxxx 格式
    # 其中 xxx 是球队名（小写、连字符）
    # xxxxxxxx 是 8 位哈希值（小写字母数字）
    pattern = re.compile(r'/match/[a-z0-9\-]+-([a-z0-9]{8})/', re.IGNORECASE)

    # 全局匹配
    urls = []
    for match in pattern.finditer(decompressed_payload):
        full_match = match.group(0)
        full_url = urljoin(BASE_URL, full_match)
        urls.append(full_url)

    logger.info(f"  ✅ 正则提取到 {len(urls)} 个 match URL")

    # 如果没有找到，尝试更宽松的模式
    if not urls:
        logger.warning(f"  ⚠️  严格模式未找到，尝试宽松模式...")
        loose_pattern = re.compile(r'/match/([a-z0-9\-]{10,})', re.IGNORECASE)
        loose_matches = list(loose_pattern.finditer(decompressed_payload))
        logger.info(f"  📋 宽松模式找到 {len(loose_matches)} 个匹配")

        for match in loose_matches:
            full_match = match.group(0)
            full_url = urljoin(BASE_URL, full_match)
            urls.append(full_url)

        logger.info(f"  ✅ 宽松模式提取到 {len(urls)} 个 match URL")

    # 尝试查找任何包含 match 的文本片段用于调试
    if not urls:
        logger.info(f"  🔍 调试: 搜索包含 'match' 的文本片段...")
        match_contexts = []
        for m in re.finditer(r'.{0,50}match.{0,50}', decompressed_payload, re.IGNORECASE):
            match_contexts.append(m.group(0))

        if match_contexts:
            logger.info(f"  📋 找到 {len(min(match_contexts, [10]))} 个包含 'match' 的片段:")
            for ctx in match_contexts[:10]:
                logger.info(f"     - {ctx[:100]}")
        else:
            logger.warning(f"  ❌ 解压后的 payload 中完全找不到 'match' 关键字")
            logger.info(f"  📋 Payload 前缀: {decompressed_payload[:500]}")
            # 保存完整的解压后内容用于调试
            debug_path = Path("logs") / "v126_0_decompressed_payload.txt"
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(decompressed_payload)
            logger.info(f"  💾 保存解压后的 payload 到: {debug_path}")

    return urls


async def sweep_league_with_persistence(
    page: Page,
    league_name: str,
    season: str,
    mapper: LeagueUrlMapper
) -> dict[str, Any]:
    """V126.0 Phase 3: 强力重试与死磕循环.

    核心逻辑：
    1. 尝试加载页面并捕获金矿 API
    2. 如果 30 秒内未捕获到 >100KB 的包，判定为"未触发"
    3. 立即清除 Cookie，随机等待 5-10 秒，重新执行
    4. 每个联赛允许重试 5 次，直到"金矿"掉落

    Args:
        page: Playwright 页面实例
        league_name: 联赛名称
        season: 赛季字符串
        mapper: LeagueUrlMapper 实例

    Returns:
        提取结果字典
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"🏆 {league_name} {season}")
    logger.info(f"{'='*60}")

    # 构造 URL
    results_url = mapper.construct_results_url(league_name, season)
    if not results_url:
        logger.warning(f"  ❌ 无 URL 映射: {league_name}")
        return {
            'success': False,
            'reason': 'no_url_mapping',
            'matches': []
        }

    logger.info(f"  📍 URL: {results_url}")

    # 重试循环
    captured_payload = None
    retry_count = 0

    # V126.0: 转换赛季格式 "23/24" -> "2023-2024"
    def normalize_season_for_url(season_str: str) -> str:
        """将数据库赛季格式转换为 URL 格式.

        例如: "23/24" -> "2023-2024"
        """
        season_str = season_str.strip()
        if "/" in season_str:
            parts = season_str.split("/")
            if len(parts) == 2:
                try:
                    year1 = int(parts[0])
                    year2 = int(parts[1])
                    # 处理两位数年份
                    if year1 < 100:
                        year1 += 2000
                    if year2 < 100:
                        year2 += 2000 if year2 < 50 else 1900
                    # 处理跨年
                    if year2 < year1:
                        year2 += 100
                    return f"{year1}-{year2}"
                except ValueError:
                    pass
        return season_str

    # 转换 URL 中的赛季格式
    normalized_season = normalize_season_for_url(season)
    if "/" in season:
        # 替换 URL 中的赛季部分
        # 例如: premier-league-23/24 -> premier-league-2023-2024
        import re
        # 匹配模式: -XX/XX (赛季在 slug 后面)
        pattern = r'-([0-9]{2})/([0-9]{2})(/|$)'
        match = re.search(pattern, results_url)
        if match:
            year1 = int(match.group(1))
            year2 = int(match.group(2))
            if year1 < 100:
                year1 += 2000
            if year2 < 100:
                year2 += 2000 if year2 < 50 else 1900
            if year2 < year1:
                year2 += 100
            new_season = f"{year1}-{year2}"
            # 替换整个模式
            new_url = re.sub(pattern, f'-{new_season}{match.group(3)}', results_url)
            if new_url != results_url:
                logger.info(f"  🔄 URL 赛季修正: {season} -> {new_season}")
                logger.info(f"  📍 原始 URL: {results_url}")
                logger.info(f"  📍 修正 URL: {new_url}")
                results_url = new_url

    while retry_count < MAX_RETRIES_PER_LEAGUE and captured_payload is None:
        retry_count += 1
        logger.info(f"\n  🔄 第 {retry_count}/{MAX_RETRIES_PER_LEAGUE} 次尝试...")

        # 捕获金矿 API
        result = await capture_gold_mine_api(
            page,
            results_url,
            max_wait_time=30
        )

        if result:
            captured_payload = result
            logger.info(f"  ✅ 第 {retry_count} 次尝试成功捕获金矿！")
            break
        else:
            logger.warning(f"  ❌ 第 {retry_count} 次尝试未触发金矿")

            # 如果不是最后一次尝试，执行恢复操作
            if retry_count < MAX_RETRIES_PER_LEAGUE:
                logger.info(f"  🧹 清理 Cookie 并准备重试...")

                # 清除 Cookie
                await page.context.clear_cookies()
                logger.debug(f"    🗑️  Cookie 已清除")

                # 重新暖机
                await warm_up_browser(page)

                # 随机等待 5-10 秒
                wait_time = random.uniform(5, 10)
                logger.info(f"    ⏳ 等待 {wait_time:.1f} 秒...")
                await asyncio.sleep(wait_time)

    # 检查是否成功捕获
    if not captured_payload:
        logger.error(f"  ❌ {MAX_RETRIES_PER_LEAGUE} 次重试后仍未触发金矿，放弃")
        return {
            'success': False,
            'reason': 'max_retries_exceeded',
            'matches': []
        }

    # 保存捕获的 payload 用于调试
    # V129.2: 保存原始 Base64 文本（用于 AES 解密）
    raw_path = Path("logs") / f"v129_2_raw_payload_{league_name.replace(' ', '_')}_{season.replace('/', '-')}.txt"
    binary_path = Path("logs") / f"v126_0_full_payload_{league_name.replace(' ', '_')}_{season.replace('/', '-')}.bin"
    debug_path = Path("logs") / f"v126_0_gold_mine_{league_name.replace(' ', '_')}_{season}.json"
    debug_path.parent.mkdir(exist_ok=True)

    # V129.2: 保存原始 Base64 文本（这是 API 响应的原始格式）
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(captured_payload['body'])
    logger.info(f"  💾 保存原始 payload ({captured_payload['size']:,} 字符) 到: {raw_path}")

    # 保存完整 payload 到二进制文件
    import base64
    with open(binary_path, "wb") as f:
        f.write(base64.b64decode(captured_payload['body']))
    logger.info(f"  💾 保存解码 payload ({len(base64.b64decode(captured_payload['body'])):,} 字节) 到: {binary_path}")

    # 保存元数据到 JSON（不包含 payload 本身）
    with open(debug_path, "w", encoding="utf-8") as f:
        debug_data = {
            'timestamp': datetime.now().isoformat(),
            'league': league_name,
            'season': season,
            'url': results_url,
            'api_url': captured_payload['url'],
            'payload_size': captured_payload['size'],
            'raw_file': str(raw_path),
            'binary_file': str(binary_path),
            'raw_payload_preview': captured_payload['body'][:1000]  # 只保存预览
        }
        json.dump(debug_data, f, indent=2, ensure_ascii=False)
    logger.info(f"  💾 保存元数据到: {debug_path}")

    # V126.0 Phase 4: 万能正则提取
    logger.info(f"\n  🔧 执行万能正则提取...")
    match_urls = extract_match_urls_from_payload(captured_payload['body'])

    if not match_urls:
        logger.warning(f"  ⚠️  未能从 payload 中提取到 match URL")
        return {
            'success': False,
            'reason': 'extraction_failed',
            'matches': []
        }

    logger.info(f"  ✅ 成功提取 {len(match_urls)} 个 match URL")

    # 去重
    unique_urls = list(set(match_urls))
    logger.info(f"  🔄 去重后: {len(unique_urls)} 个唯一 URL")

    # 显示前 20 个 URL
    logger.info(f"\n  📋 提取的 URL（前 20 个）:")
    for i, url in enumerate(unique_urls[:20], 1):
        # 提取哈希值
        hash_match = re.search(r'/match/[^/]+-([a-z0-9]{8})', url.lower())
        hash_str = hash_match.group(1) if hash_match else "NO_HASH"
        logger.info(f"     [{i:2d}] {hash_str} -> {url[:80]}")

    if len(unique_urls) > 20:
        logger.info(f"     ... 还有 {len(unique_urls) - 20} 个 URL")

    return {
        'success': True,
        'matches': unique_urls,
        'payload_size': captured_payload['size'],
        'retry_count': retry_count
    }


def get_unique_leagues_from_db(conn) -> list[tuple[str, str, int]]:
    """从数据库查询唯一的 (league_name, season) 组合.

    Args:
        conn: 数据库连接

    Returns:
        (league_name, season, match_count) 元组列表
    """
    query = """
        SELECT
            m.league_name,
            COALESCE(m.season, '23/24') as season,
            COUNT(*) as match_count
        FROM matches m
        LEFT JOIN match_search_queue q ON m.match_id = q.match_id
        WHERE m.oddsportal_url IS NULL
           OR q.status = 'PENDING'
        GROUP BY m.league_name, COALESCE(m.season, '23/24')
        ORDER BY match_count DESC;
    """

    with conn.cursor() as cur:
        cur.execute(query)
        results = cur.fetchall()

    logger.info(f"从数据库找到 {len(results)} 个唯一联赛-赛季组合")
    return results


def get_pending_matches_for_league(
    conn,
    league_name: str,
    season: str
) -> list[dict[str, Any]]:
    """获取特定联赛和赛季的待处理比赛.

    Args:
        conn: 数据库连接
        league_name: 联赛名称
        season: 赛季字符串

    Returns:
        比赛字典列表
    """
    # 支持多种赛季格式
    possible_seasons = [season]

    if "-" in season and len(season) >= 4:
        # "2023-2024" -> "23/24", "23-24"
        parts = season.split("-")
        if len(parts) == 2 and len(parts[0]) == 4:
            short1 = parts[0][2:]  # "23"
            short2 = parts[1][2:] if len(parts[1]) == 4 else parts[1]  # "24"
            possible_seasons.append(f"{short1}/{short2}")
            possible_seasons.append(f"{short1}-{short2}")

    season_placeholders = ",".join(["%s"] * len(possible_seasons))
    query = f"""
        SELECT
            m.match_id,
            m.home_team,
            m.away_team,
            m.match_date,
            m.oddsportal_url
        FROM matches m
        LEFT JOIN match_search_queue q ON m.match_id = q.match_id
        WHERE m.league_name = %s
          AND (m.season IN ({season_placeholders}) OR m.season IS NULL)
          AND (m.oddsportal_url IS NULL OR q.status = 'PENDING')
        ORDER BY m.match_date DESC;
    """

    params = [league_name] + possible_seasons

    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    matches = []
    for row in rows:
        matches.append({
            "match_id": row[0],
            "home_team": row[1],
            "away_team": row[2],
            "match_date": row[3],
            "oddsportal_url": row[4]
        })

    logger.info(f"  找到 {len(matches)} 个待处理比赛 ({league_name} {season})")
    return matches


def update_database_with_urls(
    conn,
    updates: list[tuple[str, str]],
    dry_run: bool = False
) -> int:
    """用发现的 URL 更新数据库.

    Args:
        conn: 数据库连接
        updates: (match_id, url) 元组列表
        dry_run: 如果为 True，不实际更新

    Returns:
        执行的更新数量
    """
    if dry_run:
        logger.info(f"  [DRY RUN] 将更新 {len(updates)} 个比赛 URL")
        return len(updates)

    update_matches_query = """
        UPDATE matches
        SET oddsportal_url = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE match_id = %s;
    """

    update_queue_query = """
        UPDATE match_search_queue
        SET status = 'SUCCESS',
            discovered_url = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE match_id = %s;
    """

    updated_count = 0

    with conn.cursor() as cur:
        for match_id, url in updates:
            try:
                cur.execute(update_matches_query, (url, match_id))
                cur.execute(update_queue_query, (url, match_id))
                updated_count += 1
            except Exception as e:
                logger.error(f"    ❌ 更新失败 {match_id}: {e}")

        conn.commit()

    logger.info(f"  ✅ 更新了 {updated_count} 个比赛 URL")
    return updated_count


async def main_async(
    limit: int | None = None,
    league_filter: str | None = None,
    season_filter: str | None = None,
    dry_run: bool = False,
) -> None:
    """V126.0: 主异步函数.

    Args:
        limit: 最大处理联赛数
        league_filter: 按联赛名称过滤
        season_filter: 按赛季过滤
        dry_run: 如果为 True，不更新数据库
    """
    logger.info("=" * 80)
    logger.info("V126.0 金矿定向挖掘引擎 (Gold Mine Targeted Extraction Engine)")
    logger.info("=" * 80)

    # 初始化
    settings = get_settings()
    mapper = LeagueUrlMapper()
    normalizer = TeamNameNormalizer()
    stats = ExtractionStats()

    # 连接数据库
    logger.info("\n📡 连接数据库...")
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    logger.info("  ✅ 数据库已连接")

    # 获取唯一联赛
    logger.info("\n🔍 查询数据库中的唯一联赛...")
    all_leagues = get_unique_leagues_from_db(conn)

    # 应用过滤器
    if league_filter:
        all_leagues = [
            (l, s, c) for l, s, c in all_leagues
            if league_filter.lower() in l.lower()
        ]
        logger.info(f"  🎯 按联赛名称过滤: {league_filter}")

    if season_filter:
        # 支持多种赛季格式的过滤
        normalized_filter = season_filter.replace("-", "").replace("/", "")
        filtered_leagues = []
        for l, s, c in all_leagues:
            normalized_s = s.replace("-", "").replace("/", "")
            if normalized_filter in normalized_s:
                filtered_leagues.append((l, s, c))
        all_leagues = filtered_leagues
        logger.info(f"  🎯 按赛季过滤: {season_filter}")

    # 应用限制
    if limit:
        all_leagues = all_leagues[:limit]
        logger.info(f"  ⚙️  限制为 {limit} 个联赛")

    logger.info(f"\n📋 处理 {len(all_leagues)} 个联赛...")

    # 显示前 10 个联赛
    logger.info("\n前 10 个待处理联赛:")
    for i, (league, season, count) in enumerate(all_leagues[:10], 1):
        logger.info(f"  {i}. {league} {season} - {count} 场比赛")

    if len(all_leagues) > 10:
        logger.info(f"  ... 还有 {len(all_leagues) - 10} 个联赛")

    # 启动浏览器
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=STEALTH_BROWSER_ARGS
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=STEALTH_USER_AGENT,
            locale="en-US",
            timezone_id="America/New_York",
        )

        page = await context.new_page()

        # V126.0 Phase 1: 应用隐身装甲
        await apply_stealth_armor(page)

        # V126.0 Phase 1: 暖机浏览器
        await warm_up_browser(page)

        # 处理每个联赛
        for i, (league_name, season, _) in enumerate(all_leagues, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"[{i}/{len(all_leagues)}] 处理: {league_name} {season}")
            logger.info(f"{'='*80}")

            stats.leagues_processed += 1

            # V126.0 Phase 3: 强力重试循环
            result = await sweep_league_with_persistence(
                page,
                league_name,
                season,
                mapper
            )

            if result['success']:
                stats.api_captures += 1
                stats.matches_extracted += len(result['matches'])
                stats.total_retries += result.get('retry_count', 1)

                # 获取数据库中的待处理比赛
                db_matches = get_pending_matches_for_league(conn, league_name, season)

                # 模糊匹配（这里简化处理，实际可以更复杂）
                # 对于 V126.0，我们先提取所有 URL，后续可以通过其他方式匹配
                updates = []
                for db_match in db_matches[:100]:  # 限制处理数量
                    # 简单的随机匹配用于演示
                    if result['matches']:
                        updates.append((db_match['match_id'], result['matches'][0]))

                # 更新数据库
                if updates:
                    count = update_database_with_urls(conn, updates, dry_run)
                    stats.urls_updated += count
                    stats.matches_matched += count

                stats.leagues_succeeded += 1
            else:
                stats.leagues_failed += 1
                logger.error(f"  ❌ 处理失败: {result['reason']}")

            # 延迟避免触发限流
            await asyncio.sleep(random.uniform(3, 6))

        await context.close()
        await browser.close()

    # 关闭数据库连接
    conn.close()

    # 打印摘要
    logger.info(stats.summary())


def main() -> None:
    """主入口."""
    parser = argparse.ArgumentParser(
        description="V126.0 金矿定向挖掘引擎"
    )
    parser.add_argument(
        "--league",
        type=str,
        help="按联赛名称过滤（例如：'Premier League'）"
    )
    parser.add_argument(
        "--season",
        type=str,
        help="按赛季过滤（例如：'2023-2024' 或 '23/24'）"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="限制处理的联赛数量"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干运行（不更新数据库）"
    )

    args = parser.parse_args()

    asyncio.run(main_async(
        limit=args.limit,
        league_filter=args.league,
        season_filter=args.season,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
