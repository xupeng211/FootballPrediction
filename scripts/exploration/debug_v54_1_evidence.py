#!/usr/bin/env python3
"""
V54.1 深度采集引擎 - 现场取证脚本
====================================

功能:
1. 随机选取一条 is_processed=FALSE 的记录
2. 使用 Playwright 访问 source_url
3. 截图保存为 debug_failure.png
4. 保存页面 HTML 为 debug_page.html
5. 分析失败原因（404 vs 选择器失效）

Author: Senior Automation Test Engineer
Date: 2025-12-31
"""

import asyncio
import logging
import random
from datetime import datetime
from pathlib import Path

import psycopg2
from playwright.async_api import async_playwright

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# 输出目录
DEBUG_DIR = Path("logs/debug_v54_1")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


async def collect_evidence():
    """执行现场取证"""

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

    # 1. 随机选取一条未处理的记录
    logger.info("正在获取测试样本...")
    cursor.execute("""
        SELECT match_id, home_team, away_team, source_url
        FROM prematch_features
        WHERE is_processed = FALSE
          AND source_url IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 1
    """)

    row = cursor.fetchone()
    if not row:
        logger.warning("没有找到未处理的记录")
        conn.close()
        return

    match_id, home_team, away_team, source_url = row
    logger.info(f"测试样本: {home_team} vs {away_team} (ID: {match_id})")
    logger.info(f"目标 URL: {source_url}")

    conn.close()

    # 2. 启动 Playwright 访问页面
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        viewport={"width": 1920, "height": 1080},
    )
    page = await context.new_page()

    try:
        # 拼接完整 URL（source_url 可能是相对路径）
        full_url = source_url if source_url.startswith("http") else f"https://www.oddsportal.com{source_url}"
        logger.info(f"完整 URL: {full_url}")

        logger.info("正在访问目标页面...")
        await page.goto(full_url, wait_until="networkidle", timeout=30000)

        # 3. 截图
        screenshot_path = DEBUG_DIR / f"debug_failure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"截图已保存: {screenshot_path}")

        # 4. 获取页面信息
        page_title = await page.title()
        page_text = await page.evaluate("() => document.body.innerText")
        html_content = await page.content()

        # 5. 保存完整页面 HTML
        html_path = DEBUG_DIR / f"debug_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"HTML 已保存: {html_path} (大小: {len(html_content)} 字节)")

        # 5.1 额外保存页面状态
        status_path = DEBUG_DIR / f"debug_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(status_path, "w", encoding="utf-8") as f:
            f.write(f"URL: {full_url}\n")
            f.write(f"Title: {page_title}\n")
            f.write(f"HTML Length: {len(html_content)}\n")
            f.write(f"Body Text Length: {len(page_text)}\n")
            f.write(f"\nFirst 500 chars of body:\n{page_text[:500]}\n")
        logger.info(f"状态已保存: {status_path}")

        # 6. 分析页面状态
        logger.info("")
        logger.info("=" * 60)
        logger.info("【页面现场分析】")
        logger.info("=" * 60)

        # 检查是否 404
        logger.info(f"页面标题: {page_title}")

        # 检查是否有 404 关键词
        is_404 = any(keyword in page_text.lower() for keyword in ["404", "not found", "page not found"])
        if is_404:
            logger.warning(">> 检测到 404 错误页")
        else:
            logger.info(">> 非 404 错误页")

        # 检查关键选择器
        selectors_to_check = {
            "a.odds-link": "赔率链接",
            "div[class*='odds']": "赔率容器",
            "tr": "表格行",
        }

        logger.info("")
        logger.info("【选择器探测】")
        for selector, desc in selectors_to_check.items():
            count = await page.locator(selector).count()
            logger.info(f"  {selector:30s} ({desc:10s}): {count} 个")

        # 检查是否有 PREFERRED_PROVIDERS
        providers = ["bet365", "Pinnacle", "William Hill", "Unibet"]
        logger.info("")
        logger.info("【机构探测】")
        for provider in providers:
            found = provider.lower() in page_text.lower()
            logger.info(f"  {provider:15s}: {'找到' if found else '未找到'}")

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"审计结论:")
        logger.info(f"  - 截图位置: {screenshot_path}")
        logger.info(f"  - HTML 位置: {html_path}")
        logger.info(f"  - 是否 404: {'是' if is_404 else '否'}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"取证过程出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await context.close()
        await browser.close()
        await playwright.stop()


if __name__ == "__main__":
    asyncio.run(collect_evidence())
