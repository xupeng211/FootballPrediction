#!/usr/bin/env python3
"""V126.0 诊断探针 - 调试金矿 API 捕获问题.

Usage:
    python scripts/v126_0_diagnostic_probe.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# V123.0: Disable proxy to fix WSL2 network issues
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                  'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(proxy_var, None)

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

STEALTH_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--disable-dev-shm-usage",
    "--disable-setuid-sandbox",
    "--no-sandbox",
]

STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def main():
    logger.info("=" * 80)
    logger.info("V126.0 诊断探针")
    logger.info("=" * 80)

    # 目标 URL
    target_url = "https://www.oddsportal.com/football/england/premier-league-23/24/results/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # 显示浏览器以便观察
            args=STEALTH_BROWSER_ARGS
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=STEALTH_USER_AGENT,
        )

        page = await context.new_page()

        # 存储所有响应
        all_responses = []
        api_responses = []

        async def handle_response(response):
            url = response.url
            status = response.status

            all_responses.append({
                'url': url,
                'status': status,
                'type': response.request.resource_type
            })

            # 记录所有响应
            logger.debug(f"  📡 [{status}] {url[:100]}")

            # 特别关注 API 响应
            if any(keyword in url.lower() for keyword in ['ajax', 'api', 'data', 'json']):
                try:
                    body = await response.text()
                    api_responses.append({
                        'url': url,
                        'status': status,
                        'body': body[:5000],  # 只保存前 5KB
                        'size': len(body)
                    })
                    logger.info(f"  🎣 API 响应: {url[:80]} ({len(body)} 字节)")
                except Exception as e:
                    logger.warning(f"    ⚠️  无法读取响应体: {e}")

        # 注册响应处理器
        page.on('response', handle_response)

        # 导航到目标页面
        logger.info(f"\n🌐 导航到: {target_url}")
        try:
            await page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
            logger.info("  ✅ 导航完成")
        except Exception as e:
            logger.warning(f"  ⚠️  导航超时: {e}")

        # 等待页面加载
        await asyncio.sleep(5)

        # 执行滚屏
        logger.info(f"\n📜 执行滚屏...")
        for i in range(20):
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(0.5)
            logger.debug(f"    滚动 {i+1}/20")

        # 等待 API 调用
        await asyncio.sleep(10)

        # 注销响应处理器
        page.remove_listener('response', handle_response)

        # 分析结果
        logger.info(f"\n📊 响应统计:")
        logger.info(f"  总响应数: {len(all_responses)}")
        logger.info(f"  API 响应数: {len(api_responses)}")

        # 显示所有 API 响应
        if api_responses:
            logger.info(f"\n🎯 捕获的 API 响应:")
            for i, resp in enumerate(api_responses, 1):
                logger.info(f"  [{i}] {resp['url'][:100]}")
                logger.info(f"       状态: {resp['status']}, 大小: {resp['size']} 字节")

                # 检查是否包含金矿关键字
                if 'ajax-sport-country-tournament-archive' in resp['url']:
                    logger.info(f"  ✅✅✅ 金矿 API 发现！✅✅✅")

                    # 保存完整响应
                    debug_path = Path("logs") / "v126_0_gold_mine_discovered.json"
                    debug_path.parent.mkdir(exist_ok=True)

                    # 获取完整响应体
                    full_body = await page.evaluate("""async (url) => {
                        const response = await fetch(url);
                        return await response.text();
                    }""", resp['url'])

                    with open(debug_path, "w", encoding="utf-8") as f:
                        f.write(full_body)

                    logger.info(f"  💾 保存完整响应到: {debug_path}")
                    logger.info(f"  📦 响应大小: {len(full_body)} 字节")

        # 显示前 20 个响应
        logger.info(f"\n📋 前 20 个响应:")
        for i, resp in enumerate(all_responses[:20], 1):
            logger.info(f"  [{i}] [{resp['status']}] {resp['url'][:80]}")

        # 截图
        screenshot_path = Path("logs") / "v126_0_diagnostic_screenshot.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"\n📸 截图已保存: {screenshot_path}")

        # 等待用户查看
        logger.info(f"\n⏳ 等待 30 秒以便观察...")
        await asyncio.sleep(30)

        await context.close()
        await browser.close()

    logger.info("\n" + "=" * 80)
    logger.info("诊断完成")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
