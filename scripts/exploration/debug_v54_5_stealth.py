#!/usr/bin/env python3
"""
V54.5 Stealth 取证脚本 - 潜行模式
====================================

功能:
1. 使用 playwright-stealth 插件绕过检测
2. 持久化上下文（User-Data-Dir）
3. 真实指纹伪装（分辨率、语言、硬件并发）
4. 重新获取 OddsPortal 真实页面

Author: Senior Anti-Bot Security Expert
Version: V54.5
Date: 2026-01-01
"""

import asyncio
import logging
import random
from datetime import datetime
from pathlib import Path

import psycopg2
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# 持久化上下文目录
USER_DATA_DIR = Path(".playwright_stealth_profile")
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 输出目录
DEBUG_DIR = Path("logs/debug_v54_5")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


async def stealth_evidence_collection():
    """V54.5 潜行模式取证"""

    # 数据库连接
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cursor = conn.cursor()

    # 随机选取一条历史记录（带完整 URL 的优先）
    logger.info("正在获取历史测试样本...")
    cursor.execute("""
        SELECT pf.match_id, m.home_team, m.away_team, m.league_name
        FROM prematch_features pf
        JOIN matches m ON pf.match_id = m.match_id
        WHERE pf.closing_home_odds IS NULL
        ORDER BY RANDOM()
        LIMIT 1
    """)

    row = cursor.fetchone()
    if not row:
        logger.warning("没有找到可用样本")
        conn.close()
        return

    match_id, home_team, away_team, league = row
    logger.info(f"测试样本: {home_team} vs {away_team} ({league})")

    conn.close()

    # 构建 OddsPortal URL
    league_map = {
        "Premier League": "england/premier-league",
        "La Liga": "spain/la-liga",
        "Bundesliga": "germany/bundesliga",
        "Serie A": "italy/serie-a",
        "Ligue 1": "france/ligue-1",
    }

    league_path = league_map.get(league, "england/premier-league")
    # 构建 URL 格式: team1-team2 (简单的 vs 格式)
    home_slug = home_team.lower().replace(" ", "-").replace(".", "")
    away_slug = away_team.lower().replace(" ", "-").replace(".", "")
    url = f"https://www.oddsportal.com/football/{league_path}/{home_slug}-{away_slug}/"

    logger.info(f"目标 URL: {url}")

    # ============================================================
    # V54.5 Stealth 浏览器启动
    # ============================================================
    logger.info("")
    logger.info("=" * 60)
    logger.info("V54.5 潜行模式启动")
    logger.info("=" * 60)

    playwright = await async_playwright().start()

    # 使用持久化上下文（带真实浏览器指纹）
    browser_context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(USER_DATA_DIR),
        headless=True,  # WSL 环境需要 headless
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-infobars",
            "--disable-extensions",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--ignore-certificate-errors",
        ],
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/New_York",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        accept_downloads=False,
        ignore_https_errors=True,
    )

    # 应用 stealth 插件
    # 方式：应用到页面（异步版本）
    stealth = Stealth()
    page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
    await stealth.apply_stealth_async(page)

    logger.info("✓ Stealth 环境已加载")
    logger.info(f"✓ User-Data-Dir: {USER_DATA_DIR}")
    logger.info(f"✓ Locale: en-US")
    logger.info(f"✓ Viewport: 1920x1080")
    logger.info("")

    try:
        # 策略：先访问主页建立会话（模拟真实用户行为）
        logger.info("步骤 1: 访问 OddsPortal 主页建立会话...")
        await page.goto("https://www.oddsportal.com", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # 策略：模拟用户滚动
        await page.evaluate("window.scrollBy(0, 500)")
        await asyncio.sleep(2)

        # 访问目标页面
        logger.info(f"步骤 2: 访问目标页面...")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)  # 额外等待，确保 JavaScript 执行完成

        # 获取页面内容
        html_content = await page.content()
        page_title = await page.title()
        page_text = await page.evaluate("() => document.body.innerText")

        logger.info("")
        logger.info("=" * 60)
        logger.info("【Stealth 模式取证报告】")
        logger.info("=" * 60)
        logger.info(f"页面标题: {page_title}")
        logger.info(f"HTML 长度: {len(html_content):,} 字节")
        logger.info(f"Body 文本长度: {len(page_text):,} 字节")
        logger.info("")

        # 检查关键选择器
        selectors = {
            "a.odds-link": "赔率链接",
            "div[class*='odds']": "赔率容器",
            "table": "表格",
        }

        logger.info("【选择器探测】")
        for selector, desc in selectors.items():
            count = await page.locator(selector).count()
            logger.info(f"  {selector:30s} ({desc:10s}): {count} 个")

        logger.info("")

        # 检查球队名称
        logger.info("【球队名称探测】")
        home_found = home_team.lower() in page_title.lower() or home_team.lower() in page_text.lower()
        away_found = away_team.lower() in page_title.lower() or away_team.lower() in page_text.lower()
        logger.info(f"  主队 ({home_team:20s}): {'找到' if home_found else '未找到'}")
        logger.info(f"  客队 ({away_team:20s}): {'找到' if away_found else '未找到'}")

        logger.info("")

        # 检查机构
        providers = ["bet365", "Pinnacle", "William Hill"]
        logger.info("【机构探测】")
        for provider in providers:
            found = provider.lower() in page_text.lower()
            logger.info(f"  {provider:15s}: {'找到' if found else '未找到'}")

        logger.info("")
        logger.info("=" * 60)
        logger.info("【审计结论】")
        logger.info("=" * 60)

        # 判断是否成功
        has_selectors = False
        for s in selectors.keys():
            if await page.locator(s).count() > 0:
                has_selectors = True
                break

        success_indicators = [
            len(html_content) > 50000,
            len(page_text) > 1000,
            home_found or away_found,
            has_selectors,
        ]

        if all(success_indicators):
            logger.info("✓ Stealth 模式成功 - 已获取真实页面数据")
            logger.info(f"  HTML 长度: {len(html_content):,} 字节 (目标 > 50,000)")
            logger.info(f"  页面标题: {page_title}")
        else:
            logger.warning("✗ Stealth 模式失败 - 可能仍被检测")
            logger.warning(f"  成功指标: {sum(success_indicators)}/{len(success_indicators)}")

        logger.info("=" * 60)

        # 保存完整 HTML（用于分析）
        html_path = DEBUG_DIR / f"stealth_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"HTML 已保存: {html_path}")

    except Exception as e:
        logger.error(f"Stealth 取证过程出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser_context.close()
        await playwright.stop()
        logger.info("")
        logger.info("Stealth 浏览器已关闭")


if __name__ == "__main__":
    asyncio.run(stealth_evidence_collection())
