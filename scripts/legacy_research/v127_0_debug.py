#!/usr/bin/env python3
"""V127.0 调试版本 - 非 headless 模式 + 详细日志."""

import asyncio
import logging
import os
import re
import sys
from pathlib import Path

for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                  'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(proxy_var, None)

from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("=" * 80)
    logger.info("V127.0 调试版本 - DOM 截胡")
    logger.info("=" * 80)

    target_url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"

    async with async_playwright() as p:
        # 使用非 headless 模式
        browser = await p.chromium.launch(
            headless=False,  # 显示浏览器窗口
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )

        page = await context.new_page()

        # 监听所有响应
        all_responses = []

        def handle_response(response):
            url = response.url
            status = response.status

            all_responses.append({
                'url': url,
                'status': status
            })

            if 'ajax-sport-country-tournament-archive' in url:
                logger.info(f"  🎯 检测到金矿 API!")
                logger.info(f"     URL: {url[:100]}")
                logger.info(f"     状态: {status}")

        page.on('response', handle_response)

        # 导航到目标页面
        logger.info(f"\n🌐 导航到: {target_url}")
        try:
            await page.goto(target_url, timeout=120000, wait_until="networkidle")
            logger.info(f"  ✅ 导航完成")
        except Exception as e:
            logger.warning(f"  ⚠️  导航超时（继续）: {e}")

        # 等待页面加载
        logger.info(f"\n⏳ 等待页面加载...")
        await asyncio.sleep(10)

        # 执行滚屏
        logger.info(f"\n📜 执行滚屏...")
        for i in range(30):
            await page.mouse.wheel(0, 600)
            await asyncio.sleep(0.5)
            if i % 5 == 0:
                logger.info(f"  滚动 {i+1}/30")

        # 等待 DOM 渲染
        logger.info(f"\n⏳ 等待 DOM 渲染...")
        await asyncio.sleep(15)

        # 分析响应
        logger.info(f"\n📊 响应分析:")
        logger.info(f"  总响应数: {len(all_responses)}")

        archive_responses = [r for r in all_responses if 'ajax-sport-country-tournament-archive' in r['url']]
        logger.info(f"  金矿 API 响应数: {len(archive_responses)}")

        # 提取 match 链接
        logger.info(f"\n🎯 提取 match 链接...")
        try:
            # 等待链接出现
            await page.wait_for_selector("a[href*='/match/']", timeout=30000)

            match_links = await page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a[href*="/match/"]'));
                return links.map(a => ({
                    href: a.href,
                    text: a.textContent?.trim() || ''
                })).filter(l => /[a-z0-9]{8}/.test(l.href));
            }""")

            logger.info(f"  找到 {len(match_links)} 个 match 链接")

            if match_links:
                logger.info(f"\n  📋 前 30 个链接:")
                for i, link in enumerate(match_links[:30], 1):
                    hash_match = re.search(r'([a-z0-9]{8})', link['href'].lower())
                    hash_str = hash_match.group(1) if hash_match else "NO_HASH"
                    logger.info(f"     [{i:2d}] {hash_str} -> {link['text'][:50]}")

                # 保存完整列表
                output_file = Path("logs/v127_0_extracted_urls.txt")
                output_file.parent.mkdir(exist_ok=True)
                with open(output_file, "w") as f:
                    for link in match_links:
                        f.write(f"{link['href']}\n")

                logger.info(f"\n  💾 保存了 {len(match_links)} 个 URL 到: {output_file}")

        except Exception as e:
            logger.error(f"  ❌ 提取失败: {e}")

        # 截图
        screenshot_path = Path("logs/v127_0_screenshot.png")
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"\n📸 截图已保存: {screenshot_path}")

        # 等待观察
        logger.info(f"\n⏳ 等待 30 秒以便观察...")
        await asyncio.sleep(30)

        await context.close()
        await browser.close()

    logger.info("\n" + "=" * 80)
    logger.info("调试完成")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
