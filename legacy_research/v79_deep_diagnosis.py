#!/usr/bin/env python3
"""
V79.0 深度诊断 - 使用 Playwright 查看 HTTP 状态码和重定向
"""

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


async def diagnose_url(url: str):
    """深度诊断单个 URL"""
    logger.info(f"\n诊断: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 使用非 headless 模式以便调试
        context = await browser.new_context()
        page = await context.new_page()

        # 监听所有请求
        responses = []

        def log_response(response):
            responses.append({
                'url': response.url,
                'status': response.status,
                'headers': response.headers
            })
            logger.info(f"  响应: {response.status} - {response.url[:100]}")

        page.on('response', log_response)

        try:
            # 访问页面
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            logger.info(f"\n最终 URL: {page.url}")
            logger.info(f"总响应数: {len(responses)}")

            # 等待几秒观察
            await asyncio.sleep(3)

        except Exception as e:
            logger.error(f"访问失败: {e}")

        finally:
            await browser.close()


async def main():
    """测试几个样本 URL"""
    test_urls = [
        "https://www.oddsportal.com/football/england/premier-league-2020-2021/liverpool-west-bromwich/",
        "https://www.oddsportal.com/football/germany/bundesliga-2020-2021/bayer-leverkusen-hoffenheim/",
    ]

    for url in test_urls:
        await diagnose_url(url)


if __name__ == "__main__":
    asyncio.run(main())
