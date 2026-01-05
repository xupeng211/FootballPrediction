#!/usr/bin/env python3
"""
V55.1 智能 URL 嗅探器 - 反爬对抗升级版
===========================================================

功能:
1. 访问赛季 Fixtures/Results 页面 (使用 Stealth 模式)
2. 提取带加密 ID 的完整详情页 URL
3. 全路径试错匹配解析队名 (处理多连字符队名)
4. 使用 TeamNameNormalizer 进行 fuzzy matching
5. 去重保护 + 详细日志

V55.1 新增特性:
- 随机延迟逻辑 (避免检测)
- 代理支持 (从环境变量 PROXY_SERVER 读取)
- 页面访问重试机制
- 分批次执行 (--limit, --offset 参数)

Author: Senior Lead Data Engineer
Version: V55.1
Date: 2026-01-05
"""

import argparse
import asyncio
from datetime import datetime
import logging
import os
import random
from pathlib import Path
import re

from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import psycopg2

from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# 持久化上下文目录
USER_DATA_DIR = Path(".playwright_stealth_profile")
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 截图保存目录
ERROR_SCREEN_DIR = Path("logs/error_screens")
ERROR_SCREEN_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# V55.2: 指纹与头部模糊化 (Task A)
# ============================================================================

# 动态 UA 池 (10个主流浏览器标识)
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

# 视口尺寸池 (常见屏幕分辨率)
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
]


def get_random_user_agent() -> str:
    """返回随机 User-Agent"""
    return random.choice(USER_AGENTS)


def get_random_viewport() -> dict[str, int]:
    """返回随机视口尺寸"""
    return random.choice(VIEWPORTS)


# ============================================================================
# V55.2: 人类行为注入 (Task B)
# ============================================================================

async def human_scroll(page, max_scrolls: int = 3):
    """
    模拟人类滚动行为

    Args:
        page: Playwright Page 对象
        max_scrolls: 最大滚动次数 (默认 3 次)
    """
    scroll_count = random.randint(2, max_scrolls)

    for i in range(scroll_count):
        # 随机滚动距离 (300-800 像素)
        scroll_distance = random.randint(300, 800)

        # 随机滚动方向 (80% 向下, 20% 向上)
        if random.random() < 0.8:
            # 向下滚动
            await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
        else:
            # 向上滚动
            await page.evaluate(f"window.scrollBy(0, -{scroll_distance})")

        # 随机停顿 (500-2000ms)
        await asyncio.sleep(random.uniform(0.5, 2.0))

    logger.debug(f"  → 执行了 {scroll_count} 次随机滚动")


async def human_click_noise(page):
    """
    模拟人类随机点击噪声

    点击页面空白区域或边缘，模拟用户误操作
    """
    # 30% 概率执行随机点击
    if random.random() < 0.3:
        try:
            # 获取页面尺寸
            viewport_size = page.viewport_size
            if viewport_size:
                # 在页面边缘随机点击
                x = random.randint(50, viewport_size["width"] - 50)
                y = random.randint(50, viewport_size["height"] - 50)

                # 点击
                await page.mouse.click(x, y)
                logger.debug(f"  → 随机点击噪声: ({x}, {y})")

                # 短暂停顿
                await asyncio.sleep(random.uniform(0.3, 0.8))
        except Exception:
            # 点击失败不影响主流程
            pass


async def save_error_screenshot(page, reason: str):
    """
    保存错误截图

    Args:
        page: Playwright Page 对象
        reason: 错误原因描述
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = ERROR_SCREEN_DIR / f"error_{timestamp}_{reason.replace(' ', '_')}.png"

    try:
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.error(f"  📸 错误截图已保存: {screenshot_path}")
    except Exception as e:
        logger.warning(f"  ⚠️ 截图保存失败: {e}")


# ============================================================================
# 赛季格式转换工具
# ============================================================================

def convert_season_db_to_url(season_db: str) -> str:
    """
    将数据库赛季格式转换为 URL 格式

    Examples:
        23/24 → 2023-2024
        24/25 → 2024-2025
    """
    match = re.match(r"(\d{2})/(\d{2})", season_db)
    if not match:
        raise ValueError(f"Invalid DB season format: {season_db}. Expected: '23/24'")

    century = "20"  # 假设 2000 年后
    return f"{century}{match.group(1)}-{century}{match.group(2)}"


def convert_season_url_to_db(season_url: str) -> str:
    """
    将 URL 赛季格式转换为数据库格式

    Examples:
        2023-2024 → 23/24
        2024-2025 → 24/25
    """
    match = re.match(r"20(\d{2})-20(\d{2})", season_url)
    if not match:
        raise ValueError(f"Invalid URL season format: {season_url}. Expected: '2023-2024'")

    return f"{match.group(1)}/{match.group(2)}"


# ============================================================================
# 全路径试错匹配解析器 (Task A)
# ============================================================================

def parse_team_slug_full_path(
    teams_part: str,
    normalizer: TeamNameNormalizer,
    db_team_names: set[str],
    threshold: float = 85.0,
) -> list[str] | None:
    """
    全路径试错匹配解析器 - 智能分割多连字符队名

    核心算法:
    1. 遍历所有可能的分割点 (A-B-C-D → A|BCD, AB|CD, ABC|D)
    2. 对每个分割点,分别找到最佳的 home_match 和 away_match
    3. 使用 are_same_team 进行预检查(避免子串匹配)
    4. 返回[综合得分最高]且[两队均超过阈值]的分割方案

    Args:
        teams_part: URL 中的球队部分(不含 hash),如 "manchester-united-brentford"
        normalizer: TeamNameNormalizer 实例
        db_team_names: 数据库中的球队名称集合(用于快速查找)
        threshold: 相似度阈值 (0-100),默认 85%

    Returns:
        [home_team_slug, away_team_slug] 或 None(解析失败时)
    """
    parts = teams_part.split("-")

    # 注意:不再有简单的 2 部分快捷方式,所有情况都需要 fuzzy matching 验证

    # 全路径试错匹配
    best_split = None
    best_combined_score = 0.0
    best_home_score = 0.0
    best_away_score = 0.0

    # 遍历所有可能的分割点
    for i in range(1, len(parts)):
        home_slug = "-".join(parts[:i])
        away_slug = "-".join(parts[i:])

        # 转换为显示名称: manchester-united → Manchester United
        home_display = " ".join(word.title() for word in home_slug.split("-"))
        away_display = " ".join(word.title() for word in away_slug.split("-"))

        # 分别为 home 和 away 找到最佳匹配
        max_home_score = 0.0
        max_away_score = 0.0

        for db_name in db_team_names:
            # 首先检查是否是同一队(避免子串匹配问题)
            if normalizer.are_same_team(home_display, db_name):
                max_home_score = 100.0
            else:
                # 使用 fuzzy_match (不使用 partial_ratio)
                from thefuzz import fuzz
                norm_home = normalizer.normalize(home_display)
                norm_db = normalizer.normalize(db_name)
                token_sort_score = fuzz.token_sort_ratio(norm_home, norm_db)
                standard_score = fuzz.ratio(norm_home, norm_db)
                home_score = float(max(token_sort_score, standard_score))
                max_home_score = max(max_home_score, home_score)

            # 同样处理 away
            if normalizer.are_same_team(away_display, db_name):
                max_away_score = 100.0
            else:
                from thefuzz import fuzz
                norm_away = normalizer.normalize(away_display)
                norm_db = normalizer.normalize(db_name)
                token_sort_score = fuzz.token_sort_ratio(norm_away, norm_db)
                standard_score = fuzz.ratio(norm_away, norm_db)
                away_score = float(max(token_sort_score, standard_score))
                max_away_score = max(max_away_score, away_score)

        # 计算综合得分
        combined_score = (max_home_score + max_away_score) / 2

        # 检查是否满足阈值
        if max_home_score >= threshold and max_away_score >= threshold:
            # 平局决胜策略:
            # 1. 更高的综合得分优先
            # 2. 得分相同时,优先选择部件数更平衡的分割 (|i - (len-i)| 更小)
            # 3. 平衡度相同时,优先选择更长的 slug
            if best_split is None:
                is_better = True
            else:
                # 计算平衡度 (两队部件数的差异,越小越平衡)
                current_balance = abs(i - (len(parts) - i))
                best_i = len(best_split[0].split("-"))
                best_balance = abs(best_i - (len(parts) - best_i))

                if combined_score > best_combined_score:
                    is_better = True
                elif combined_score == best_combined_score:
                    if current_balance < best_balance:
                        is_better = True
                    elif current_balance == best_balance:
                        # 平衡度相同时,选择更长的 slug
                        if len(home_slug) + len(away_slug) > len(best_split[0]) + len(best_split[1]):
                            is_better = True
                        else:
                            is_better = False
                    else:
                        is_better = False
                else:
                    is_better = False

            if is_better:
                best_combined_score = combined_score
                best_home_score = max_home_score
                best_away_score = max_away_score
                best_split = [home_slug, away_slug]

    # 记录最佳匹配
    if best_split:
        home_display = " ".join(word.title() for word in best_split[0].split("-"))
        away_display = " ".join(word.title() for word in best_split[1].split("-"))
        logger.info(
            f"  ✨ 识别成功: [{home_display}] vs [{away_display}] "
            f"(主队 {int(best_home_score)}%, 客队 {int(best_away_score)}%)"
        )

    return best_split


# ============================================================================
# Fuzzy Matching 引擎
# ============================================================================

def fuzzy_match_teams(
    unique_urls: dict,
    cursor,
    normalizer: TeamNameNormalizer,
    threshold: float = 85.0,
    check_duplicates: bool = True,
) -> dict[str, dict]:
    """
    使用 fuzzy matching 将 OddsPortal URL 队名匹配到数据库比赛

    Args:
        unique_urls: {key: {"url": str, "teams": [str], "encrypted_id": str}}
        cursor: 数据库游标
        normalizer: TeamNameNormalizer 实例
        threshold: 相似度阈值 (0-100),默认 85%
        check_duplicates: 是否检查去重

    Returns:
        {match_id: {"home": str, "away": str, "league": str, "url": str, "encrypted_id": str}}
    """
    # 步骤 1: 批量加载所有候选比赛(避免 N+1 查询)
    logger.info("  → 步骤 1: 预加载数据库比赛记录...")
    db_matches = cursor.fetchall()
    logger.info(f"     已加载 {len(db_matches)} 场数据库比赛")

    # 步骤 2: 去重检查(可选)
    existing_urls = set()
    if check_duplicates:
        logger.info("  → 步骤 1.5: 检查现有 URL 去重...")
        for row in db_matches:
            if row.get("source_url"):
                existing_urls.add(row["source_url"])
        logger.info(f"     已存在 {len(existing_urls)} 个 URL,将跳过重复")

    # 步骤 3: 遍历每个 URL,计算 fuzzy match scores
    logger.info(f"  → 步骤 2: 计算 fuzzy similarity scores (阈值 >= {threshold}%)...")
    matches = {}
    successful_matches = 0
    failed_matches = 0
    skipped_duplicates = 0

    for url_data in unique_urls.values():
        url = url_data["url"]

        # 去重检查
        if check_duplicates and url in existing_urls:
            skipped_duplicates += 1
            continue

        # URL 中的队伍是 slug 格式: ["manchester-city", "brentford"]
        url_teams = url_data["teams"]

        if len(url_teams) < 2:
            logger.warning(f"     ⚠️ URL 解析异常: {url_teams} (队伍数 < 2)")
            failed_matches += 1
            continue

        # 将 slug 转换为显示名称: manchester-city → Manchester City
        url_home_display = " ".join(word.title() for word in url_teams[0].split("-"))
        url_away_display = " ".join(word.title() for word in url_teams[1].split("-"))

        # 步骤 4: 与所有数据库比赛计算相似度
        best_match = None
        best_score = 0.0

        for db_match in db_matches:
            home_score = normalizer.fuzzy_match(url_home_display, db_match["home_team"])
            away_score = normalizer.fuzzy_match(url_away_display, db_match["away_team"])

            # 计算综合得分 (主客队得分的平均值)
            combined_score = (home_score + away_score) / 2

            if combined_score > best_score:
                best_score = combined_score
                best_match = {
                    "match_id": db_match["match_id"],
                    "home": db_match["home_team"],
                    "away": db_match["away_team"],
                    "league": db_match["league_name"],
                    "home_score": home_score,
                    "away_score": away_score,
                    "combined_score": combined_score,
                }

        # 步骤 5: 检查是否满足阈值
        if best_match:
            home_ok = best_match["home_score"] >= threshold
            away_ok = best_match["away_score"] >= threshold

            if home_ok and away_ok:
                matches[best_match["match_id"]] = {
                    "home": best_match["home"],
                    "away": best_match["away"],
                    "league": best_match["league"],
                    "url": url_data["url"],
                    "encrypted_id": url_data["encrypted_id"],
                }
                successful_matches += 1
                logger.info(
                    f"     ✅ [{int(best_match['combined_score'])}%] "
                    f"匹配成功: OddsPortal({url_home_display} vs {url_away_display}) -> "
                    f"DB({best_match['home']} vs {best_match['away']})"
                )
            else:
                failed_matches += 1
                logger.info(
                    f"     ❌ [{int(best_match['combined_score'])}%] "
                    f"匹配失败: OddsPortal({url_home_display} vs {url_away_display}) -> "
                    f"DB({best_match['home']} [{int(best_match['home_score'])}%] vs "
                    f"{best_match['away']} [{int(best_match['away_score'])}%])"
                )

    logger.info(f"  → 匹配结果: {successful_matches} 成功 / {failed_matches} 失败 / {skipped_duplicates} 跳过重复")
    return matches


# ============================================================================
# 主嗅探流程
# ============================================================================

async def sniff_oddsportal_page(
    league_name: str = "Premier League",
    season_db: str = "23/24",
    page_type: str = "fixtures",
    threshold: float = 85.0,
    limit: int | None = None,
    offset: int = 0,
    clear_session: bool = False,
):
    """
    嗅探 OddsPortal 页面并提取真实 URL (V55.2 Ghost Edition)

    Args:
        league_name: 联赛名称
        season_db: 数据库赛季格式 (如 "23/24")
        page_type: 页面类型 ("fixtures" 或 "results")
        threshold: Fuzzy matching 阈值
        limit: 最多处理 N 场比赛 (None = 无限制)
        offset: 从第 N 场比赛开始处理 (用于断点续传)
        clear_session: 是否清空浏览器会话目录 (V55.2)
    """
    # 转换赛季格式
    season_url = convert_season_db_to_url(season_db)

    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    conn.autocommit = True
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # V55.2: 会话清理
    if clear_session:
        import shutil
        logger.info("🧹 清空浏览器会话目录...")
        try:
            shutil.rmtree(USER_DATA_DIR, ignore_errors=True)
            USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
            logger.info("  ✓ 会话目录已清空")
        except Exception as e:
            logger.warning(f"  ⚠️ 清空会话目录失败: {e}")

    # 读取代理配置
    proxy_server = os.getenv("PROXY_SERVER")
    if proxy_server:
        logger.info(f"使用代理: {proxy_server}")
    else:
        logger.info("未配置代理，使用直连")

    # V55.2: 随机化指纹
    random_ua = get_random_user_agent()
    random_viewport = get_random_viewport()
    logger.info(f"随机UA: {random_ua[:50]}...")
    logger.info(f"随机视口: {random_viewport['width']}x{random_viewport['height']}")

    logger.info("")
    logger.info("=" * 70)
    logger.info("V55.2 幽灵版 URL 嗅探器启动 (Ghost Edition)")
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"目标联赛: {league_name}")
    logger.info(f"目标赛季: {season_db} (DB) → {season_url} (URL)")
    logger.info(f"页面类型: {page_type}")
    logger.info(f"匹配阈值: {threshold}%")
    if limit:
        logger.info(f"批次限制: {offset} → {offset + limit} (最多 {limit} 场)")
    logger.info("")

    # 构造目标 URL
    # 根据 league_name 映射到 URL slug
    league_slug_map = {
        "Premier League": "premier-league",
        "La Liga": "laliga",
        "Bundesliga": "bundesliga",
        "Serie A": "serie-a",
        "Ligue 1": "ligue-1",
    }
    league_slug = league_slug_map.get(league_name, league_name.lower().replace(" ", "-"))
    target_url = f"https://www.oddsportal.com/football/england/{league_slug}-{season_url}/{page_type}/"

    logger.info(f"目标 URL: {target_url}")
    logger.info("")

    # 启动 Stealth 浏览器 (带代理支持)
    playwright = await async_playwright().start()

    # 构建浏览器启动参数
    browser_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
    ]

    # 代理配置
    proxy_config = None
    if proxy_server:
        # 解析代理地址: http://proxy.example.com:8080 or socks5://proxy.example.com:1080
        if proxy_server.startswith("http://"):
            proxy_config = {"server": proxy_server}
        elif proxy_server.startswith("socks5://"):
            browser_args.append("--proxy-server=" + proxy_server)
            proxy_config = {"server": proxy_server}
        else:
            # 默认使用 HTTP 代理
            proxy_config = {"server": f"http://{proxy_server}"}

    browser_context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(USER_DATA_DIR),
        headless=True,
        args=browser_args,
        proxy=proxy_config,
        viewport=random_viewport,  # V55.2: 随机视口
        locale="en-US",
        user_agent=random_ua,  # V55.2: 随机 UA
    )

    stealth = Stealth()
    page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
    await stealth.apply_stealth_async(page)

    # 页面访问重试机制
    max_retries = 3
    retry_delay = 30

    try:
        # 步骤 1: 访问主页建立会话
        logger.info("步骤 1: 访问 OddsPortal 主页...")

        for attempt in range(max_retries):
            try:
                # 随机延迟 (3-8 秒)
                initial_delay = 3 + random.uniform(0, 5)
                await asyncio.sleep(initial_delay)

                await page.goto("https://www.oddsportal.com", wait_until="domcontentloaded", timeout=30000)

                # 随机延迟 (2-5 秒)
                followup_delay = 2 + random.uniform(0, 3)
                await asyncio.sleep(followup_delay)

                page_html = await page.content()
                if len(page_html) > 10000:
                    logger.info("  ✓ 主页访问成功")
                    break
                else:
                    logger.warning(f"  ✗ 主页内容过少 ({len(page_html)} 字节)")
                    if attempt < max_retries - 1:
                        logger.info(f"  → 等待 {retry_delay} 秒后重试...")
                        await asyncio.sleep(retry_delay)
            except Exception as e:
                logger.warning(f"  ✗ 主页访问失败: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"  → 等待 {retry_delay} 秒后重试...")
                    await asyncio.sleep(retry_delay)
                else:
                    raise

        # 步骤 2: 访问目标页面
        logger.info("")
        logger.info(f"步骤 2: 访问赛季 {page_type.title()} 页面...")

        for attempt in range(max_retries):
            try:
                # 随机延迟 (5-12 秒)
                random_delay = 5 + random.uniform(0, 7)
                await asyncio.sleep(random_delay)

                await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)

                # 随机延迟 (3-8 秒)
                parse_delay = 3 + random.uniform(0, 5)
                await asyncio.sleep(parse_delay)

                # 检查页面状态
                page_html = await page.content()
                page_title = await page.title()

                logger.info(f"  页面标题: {page_title}")
                logger.info(f"  HTML 长度: {len(page_html):,} 字节")

                # V55.2: 深度检测 - Cloudflare / 39 bytes / 极小内容
                html_lower = page_html.lower()
                is_cloudflare = "cloudflare" in html_lower or "checking your browser" in html_lower
                is_blocked = len(page_html) < 100 or len(page_html) == 39

                if is_cloudflare or is_blocked:
                    block_reason = "Cloudflare 拦截" if is_cloudflare else f"内容过少 ({len(page_html)} 字节)"
                    logger.error(f"  ✗ 检测到拦截: {block_reason}")

                    # V55.2: 保存错误截图
                    await save_error_screenshot(page, block_reason.replace(" ", "_"))

                    if attempt < max_retries - 1:
                        logger.info(f"  → 等待 {retry_delay} 秒后重试...")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error("  ✗ 达到最大重试次数，拦截未解除")
                        # 优雅退出 (Exit Code 1)
                        import sys
                        logger.error("=" * 70)
                        logger.error("🚫 V55.2 检测到持续拦截，任务终止")
                        logger.error(f"拦截原因: {block_reason}")
                        logger.error(f"错误截图: {ERROR_SCREEN_DIR}")
                        logger.error("=" * 70)
                        sys.exit(1)
                else:
                    logger.info(f"  ✓ {page_type.title()} 页面加载成功")

                    # V55.2: 人类行为注入 - 模拟滚动
                    logger.debug("  → 执行人类行为模拟...")
                    await human_scroll(page, max_scrolls=3)

                    # V55.2: 人类行为注入 - 随机点击噪声
                    await human_click_noise(page)

                    break
            except Exception as e:
                logger.warning(f"  ✗ 目标页面访问失败: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"  → 等待 {retry_delay} 秒后重试...")
                    await asyncio.sleep(retry_delay)
                else:
                    raise

        # 步骤 3: 提取所有比赛链接
        logger.info("")
        logger.info("步骤 3: 提取带加密 ID 的比赛链接...")

        # JavaScript 提取所有比赛详情链接
        match_links = await page.evaluate("""
            () => {
                const results = [];

                // 查找所有指向比赛详情页的链接
                const links = document.querySelectorAll('a[href*="/football/"]');

                links.forEach(link => {
                    const href = link.getAttribute('href');
                    const text = link.textContent.trim();

                    // 过滤: 必须包含完整的比赛路径格式
                    // /football/england/premier-league-2023-2024/team1-team2-xxxxx/
                    if (href && href.includes('/football/') &&
                        href.match(/-\\w{3,}\\/$/) &&  // 以 -xxx/ 结尾(加密 ID)
                        text.length > 5 && text.length < 100) {

                        results.push({
                            href: href,
                            text: text
                        });
                    }
                });

                return results;
            }
        """)

        logger.info(f"  找到 {len(match_links)} 个潜在链接")

        # 步骤 4: 预加载数据库队名
        logger.info("")
        logger.info("步骤 4: 预加载数据库队名...")
        cursor.execute("""
            SELECT DISTINCT home_team FROM matches
            WHERE league_name = %s AND season = %s
            UNION
            SELECT DISTINCT away_team FROM matches
            WHERE league_name = %s AND season = %s
        """, (league_name, season_db, league_name, season_db))
        db_team_names = {row["home_team"] for row in cursor.fetchall()}
        logger.info(f"  → 已加载 {len(db_team_names)} 支球队名称")

        # 步骤 5: 预加载数据库比赛(用于 fuzzy matching)
        logger.info("")
        logger.info("步骤 5: 预加载数据库比赛记录...")
        cursor.execute("""
            SELECT DISTINCT m.match_id, m.home_team, m.away_team, m.league_name, pf.source_url
            FROM matches m
            JOIN prematch_features pf ON m.match_id = pf.match_id
            WHERE m.league_name = %s AND m.season = %s
        """, (league_name, season_db))

        # 步骤 6: 解析并去重
        logger.info("")
        logger.info("步骤 6: 解析 URL(全路径试错匹配)...")

        unique_urls = {}
        parse_warnings = 0
        parse_success = 0

        # 初始化 TeamNameNormalizer
        normalizer = TeamNameNormalizer()

        for link in match_links:
            href = link["href"]

            # 确保是完整 URL
            full_url = f"https://www.oddsportal.com{href}" if href.startswith("/") else href

            # 解析球队名
            # 实际格式: /football/england/premier-league-2023-2024/team1-team2-xxxxx/
            parts = href.split("/")
            if len(parts) >= 5:
                match_part = parts[4] if len(parts) > 4 else parts[3]
                match_part = match_part.rstrip("/")

                # 提取加密 ID(最后一部分)
                id_match = re.search(r"-([a-zA-Z0-9]{3,})$", match_part)
                if id_match:
                    encrypted_id = id_match.group(1)

                    # 提取球队名(移除加密 ID)
                    teams_part = match_part.rsplit("-", 1)[0]

                    # 全路径试错匹配解析
                    url_teams = parse_team_slug_full_path(
                        teams_part,
                        normalizer,
                        db_team_names,
                        threshold=threshold
                    )

                    if url_teams:
                        parse_success += 1
                        key = f"{url_teams[0]}-{url_teams[1]}"
                        if key not in unique_urls:
                            unique_urls[key] = {
                                "url": full_url,
                                "teams": url_teams,
                                "encrypted_id": encrypted_id,
                            }
                    else:
                        parse_warnings += 1
                        if parse_warnings <= 3:
                            logger.warning(f"  ⚠️ 解析失败: teams_part='{teams_part}'")

        logger.info(f"  解析成功: {parse_success} | 解析警告: {parse_warnings}")
        logger.info(f"  去重后: {len(unique_urls)} 场比赛")

        # 步骤 7: 匹配数据库
        logger.info("")
        logger.info(f"步骤 7: 匹配数据库 match_id (fuzzy matching, 阈值 {threshold}%)...")

        match_map = fuzzy_match_teams(
            unique_urls,
            cursor,
            normalizer,
            threshold=threshold,
            check_duplicates=True
        )

        # 步骤 8: 更新数据库 (带 limit 和 offset 支持)
        logger.info("")
        logger.info("步骤 8: 更新数据库 source_url...")

        # 转换为列表以支持切片
        match_items = list(match_map.items())

        # 应用 offset
        if offset > 0:
            match_items = match_items[offset:]
            logger.info(f"  → 跳过前 {offset} 场比赛")

        # 应用 limit
        if limit is not None:
            match_items = match_items[:limit]
            logger.info(f"  → 限制处理 {limit} 场比赛")

        updated_count = 0
        skipped_count = 0
        for match_id, match_info in match_items:
            real_url = match_info["url"]

            # 检查是否已存在
            cursor.execute("""
                SELECT source_url FROM prematch_features WHERE match_id = %s
            """, (match_id,))
            existing = cursor.fetchone()

            if existing and existing["source_url"]:
                skipped_count += 1
                continue

            # 更新数据库
            cursor.execute("""
                UPDATE prematch_features
                SET source_url = %s, is_processed = FALSE
                WHERE match_id = %s
            """, (real_url, match_id))

            if cursor.rowcount > 0:
                updated_count += 1
                if updated_count <= 5:
                    logger.info(f"  ✓ {match_info['home']} vs {match_info['away']}")
                    logger.info(f"    URL: ...{real_url[-60:]}")

        if skipped_count > 0:
            logger.info(f"  ⓘ 跳过 {skipped_count} 个已存在的 URL")

        logger.info("")
        logger.info("=" * 70)
        logger.info("[V55.2 幽灵版嗅探任务完成]")
        logger.info("=" * 70)
        logger.info(f"总扫描链接: {len(match_links)}")
        logger.info(f"去重后比赛: {len(unique_urls)}")
        logger.info(f"数据库匹配: {len(match_map)}")
        logger.info(f"处理范围: {offset} → {offset + len(match_items)}")
        logger.info(f"成功更新: {updated_count}")
        logger.info(f"跳过重复: {skipped_count}")
        logger.info("=" * 70)

        # 保存嗅探报告
        report_path = Path("logs/debug_v54_6") / f"sniff_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("V55.2 URL 嗅探报告 (幽灵版)\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"目标联赛: {league_name}\n")
            f.write(f"目标赛季: {season_db}\n")
            f.write(f"页面类型: {page_type}\n")
            f.write(f"扫描时间: {datetime.now()}\n\n")
            f.write(f"总扫描链接: {len(match_links)}\n")
            f.write(f"去重后比赛: {len(unique_urls)}\n")
            f.write(f"数据库匹配: {len(match_map)}\n")
            f.write(f"处理范围: {offset} → {offset + len(match_items)}\n")
            f.write(f"成功更新: {updated_count}\n")
            f.write(f"跳过重复: {skipped_count}\n\n")
            f.write("更新的 URL 示例:\n")
            f.write("-" * 70 + "\n")

            for match_id, match_info in match_items[:10]:
                f.write(f"{match_info['home']} vs {match_info['away']}\n")
                f.write(f"  {match_info['url']}\n\n")

        logger.info(f"\n报告已保存: {report_path}")

    except Exception as e:
        logger.exception(f"嗅探过程出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser_context.close()
        await playwright.stop()
        cursor.close()
        conn.close()
        logger.info("")
        logger.info("浏览器已关闭,数据库连接已释放")


# ============================================================================
# 命令行入口
# ============================================================================

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="V55.2 URL Sniffer Ghost Edition - Extract match URLs from OddsPortal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan Premier League 23/24 fixtures (default)
  python scripts/exploration/debug_v54_6_url_sniffer.py

  # Scan Premier League 23/24 results
  python scripts/exploration/debug_v54_6_url_sniffer.py --page-type results

  # Scan La Liga 24/25
  python scripts/exploration/debug_v54_6_url_sniffer.py --league "La Liga" --season 24/25

  # Adjust fuzzy matching threshold
  python scripts/exploration/debug_v54_6_url_sniffer.py --threshold 80
        """
    )

    parser.add_argument(
        "--league",
        type=str,
        default="Premier League",
        help="联赛名称 (默认: 'Premier League')"
    )

    parser.add_argument(
        "--season",
        type=str,
        default="23/24",
        help="赛季格式: DB格式 '23/24' 或 URL格式 '2023-2024' (默认: '23/24')"
    )

    parser.add_argument(
        "--page-type",
        type=str,
        choices=["fixtures", "results"],
        default="fixtures",
        help="页面类型: 'fixtures' (覆盖率 80-90%%) 或 'results' (覆盖率 6%%) (默认: 'fixtures')"
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=85.0,
        help="Fuzzy matching 相似度阈值 0-100 (默认: 85.0)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="最多处理 N 场比赛 (默认: 无限制)"
    )

    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="跳过前 N 场比赛 (默认: 0, 用于断点续传)"
    )

    parser.add_argument(
        "--clear-session",
        action="store_true",
        help="清空浏览器会话目录 (V55.2)"
    )

    args = parser.parse_args()

    # 自动转换赛季格式
    season_db = args.season
    if re.match(r"20\d{2}-20\d{2}", args.season):
        # URL 格式 → DB 格式
        season_db = convert_season_url_to_db(args.season)
        logger.info(f"自动转换赛季: {args.season} → {season_db}")

    # 运行嗅探器
    asyncio.run(sniff_oddsportal_page(
        league_name=args.league,
        season_db=season_db,
        page_type=args.page_type,
        threshold=args.threshold,
        limit=args.limit,
        offset=args.offset,
        clear_session=args.clear_session,
    ))


if __name__ == "__main__":
    main()
