#!/usr/bin/env python3
"""
V64.0 智能发现 - 使用截图诊断 + 更灵活的选择器
"""

import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


async def discover_with_diagnosis():
    """带诊断的 URL 发现"""
    screenshot_dir = Path("logs/v64_discovery_debug")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    results_url = "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/"

    logger.info(f"[Discovery] 访问: {results_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )

        page = await context.new_page()

        try:
            # 访问页面
            await page.goto(results_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(5)

            # 保存初始截图
            await page.screenshot(path=str(screenshot_dir / "01_initial.png"), full_page=True)
            logger.info("[Discovery] 截图保存: 01_initial.png")

            # 尝试多种选择器
            selectors = [
                'a[href*="/football/"]',
                'a[href*="bundesliga"]',
                '[data-testid]',
                '.odd',
                'a[href]',
            ]

            for selector in selectors:
                try:
                    count = await page.locator(selector).count()
                    logger.info(f"[Discovery] 选择器 '{selector}': 找到 {count} 个元素")
                except:
                    pass

            # 获取所有链接
            all_links = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.map(a => ({
                        href: a.getAttribute('href'),
                        text: a.textContent?.trim().slice(0, 50)
                    })).filter(l => l.href && (
                        l.href.includes('/football/') ||
                        l.href.includes('bundesliga')
                    )).slice(0, 30);
                }
            """)

            logger.info(f"\n[Discovery] 找到 {len(all_links)} 个相关链接:\n")
            for i, link in enumerate(all_links[:10], 1):
                logger.info(f"  {i}. {link['text']}")
                logger.info(f"     URL: {link['href']}")

            # 保存结果
            import json
            with open(screenshot_dir / 'discovered_links.json', 'w') as f:
                json.dump(all_links, f, indent=2)

            # 等待用户查看
            logger.info("\n[Discovery] 浏览器将保持 30 秒，请手动检查页面...")
            await asyncio.sleep(30)

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(discover_with_diagnosis())
