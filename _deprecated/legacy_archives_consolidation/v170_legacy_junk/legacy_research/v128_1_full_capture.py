#!/usr/bin/env python3
"""V128.1 完整 Payload 捕获引擎 - 直接保存到文件.

关键改进：
1. 不使用 JSON 保存（避免截断）
2. 直接将完整响应体保存到二进制文件
3. 使用流式处理避免内存问题

Usage:
    python scripts/v128_1_full_capture.py
"""

import asyncio
import json
import logging
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path

for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                  'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(proxy_var, None)

from playwright.async_api import async_playwright, Page

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.oddsportal.com"
TARGET_API_KEYWORD = "ajax-sport-country-tournament-archive_"
MIN_PAYLOAD_SIZE = 500 * 1024

STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

STEALTH_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
]


async def capture_full_payload(page: Page, results_url: str, output_file: Path) -> bool:
    """捕获完整的 payload 到文件."""
    logger.info(f"  🎯 开始捕获完整 payload...")

    captured = False
    capture_event = asyncio.Event()

    async def handle_response(response):
        nonlocal captured
        try:
            url = response.url

            if TARGET_API_KEYWORD not in url:
                return

            logger.info(f"  📡 检测到金矿 API")

            if response.status != 200:
                return

            # 直接将响应体写入文件
            logger.info(f"  💾 开始下载响应体到文件...")

            try:
                # 使用超时时间获取大响应体
                body = await response.body(timeout=120000)  # 120 秒超时
                body_size = len(body)

                logger.info(f"  📦 响应体大小: {body_size:,} 字节")

                if body_size >= MIN_PAYLOAD_SIZE:
                    # 直接写入二进制文件
                    with open(output_file, "wb") as f:
                        f.write(body)

                    logger.info(f"  ✅ 完整 payload 已保存: {output_file}")
                    captured = True
                    capture_event.set()
                else:
                    logger.warning(f"  ⚠️  响应体太小: {body_size:,} < {MIN_PAYLOAD_SIZE:,}")

            except Exception as e:
                logger.error(f"  ❌ 下载响应体失败: {e}")

        except Exception:
            pass

    # 注册响应处理器
    page.on('response', handle_response)

    # 导航
    logger.info(f"  🌐 导航到: {results_url}")
    try:
        await page.goto(results_url, timeout=90000, wait_until="domcontentloaded")
    except Exception as e:
        logger.warning(f"  ⚠️  导航超时: {e}")

    # 滚动触发 API
    logger.info(f"  📜 执行滚屏...")
    for i in range(30):
        if capture_event.is_set():
            logger.info(f"  🎉 在第 {i} 次滚动时完成捕获!")
            break

        await page.mouse.wheel(0, 600)
        await asyncio.sleep(0.5)

    # 额外等待
    if not capture_event.is_set():
        logger.info(f"  ⏳ 等待响应加载...")
        await asyncio.sleep(20)

    page.remove_listener('response', handle_response)

    return captured


async def main():
    logger.info("=" * 80)
    logger.info("V128.1 完整 Payload 捕获引擎")
    logger.info("=" * 80)

    results_url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"

    # 创建输出文件
    output_dir = Path("logs")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"v128_1_full_payload_{timestamp}.bin"

    logger.info(f"\n📋 配置:")
    logger.info(f"  目标 URL: {results_url}")
    logger.info(f"  输出文件: {output_file}")

    # 启动浏览器
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=STEALTH_BROWSER_ARGS
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=STEALTH_USER_AGENT,
        )

        # 添加隐身脚本
        stealth_script = """() => {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        }"""

        page = await context.new_page()
        await page.add_init_script(stealth_script)

        # 捕获完整 payload
        success = await capture_full_payload(page, results_url, output_file)

        await context.close()
        await browser.close()

    if success:
        logger.info(f"\n✅ 捕获成功！")
        logger.info(f"📁 文件: {output_file}")
        logger.info(f"\n💡 下一步: 运行 V128.0 解密引擎处理此文件")
    else:
        logger.error(f"\n❌ 捕获失败")

    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
