#!/usr/bin/env python3
"""
V65.0 URL Diagnosis - 诊断 URL 格式和球队名称
"""

import asyncio
import logging
import re
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

TARGET_URL = "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/"

TEAM_MAPPINGS = {
    "Dortmund": "Borussia Dortmund",
    "Bayern": "Bayern München",
    "Munchen": "Bayern München",
    "Monchengladbach": "Borussia Mönchengladbach",
    "Koln": "1. FC Köln",
    "Köln": "1. FC Köln",
    "Leverkusen": "Bayer Leverkusen",
}

async def diagnose_urls():
    """诊断 URL 格式"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )

        page = await context.new_page()

        print(f"\n访问: {TARGET_URL}\n")

        await page.goto(TARGET_URL, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(5)

        # 保存截图
        await page.screenshot(path="logs/v65_diagnosis.png", full_page=True)
        print("截图已保存: logs/v65_diagnosis.png")

        # 提取所有链接
        links_data = await page.evaluate("""
            () => {
                const results = [];
                const links = document.querySelectorAll('a[href]');

                for (const link of links) {
                    const href = link.getAttribute('href');
                    const text = link.textContent || '';

                    if (href && href.includes('bundesliga-2023-2024') &&
                        !href.includes('/standings') && !href.includes('/outrights') &&
                        text.match(/\\d+\\s*[–:-]\\s*\\d+/)) {

                        const parts = href.split('/');
                        const matchPart = parts[parts.length - 2] || href;

                        results.push({
                            urlPath: href,
                            fullUrl: 'https://www.oddsportal.com' + href,
                            matchPart: matchPart,
                            text: text.trim()
                        });
                    }
                }

                return results.slice(0, 20);
            }
        """)

        print(f"\n找到 {len(links_data)} 个比赛链接:\n")

        for i, item in enumerate(links_data, 1):
            print(f"{i}. {item['text']}")
            print(f"   URL: {item['fullUrl']}")

            # 解析球队名称
            match_part = item['matchPart']
            teams_part = re.sub(r'-[A-Z]{7,}$', '', match_part)
            teams = teams_part.split('-')

            if len(teams) >= 2:
                home_raw = teams[0]
                away_raw = '-'.join(teams[1:])

                # 尝试映射
                home_mapped = TEAM_MAPPINGS.get(home_raw.title(), home_raw.title())
                away_mapped = TEAM_MAPPINGS.get(away_raw.title(), away_raw.title())

                print(f"   解析: {home_raw} vs {away_raw}")
                print(f"   映射: {home_mapped} vs {away_mapped}")

            print()

        await browser.close()

        return links_data


if __name__ == "__main__":
    asyncio.run(diagnose_urls())
