#!/usr/bin/env python3
"""
V54.7 Vue 数据提取器 - 简化版
===============================

Author: V54.7
Date: 2026-01-01
"""

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth


async def simple_extract():
    p = await async_playwright().start()
    ctx = await p.chromium.launch_persistent_context(
        user_data_dir=str(Path('.playwright_stealth_profile')),
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    stealth = Stealth()
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await stealth.apply_stealth_async(page)

    await page.goto("https://www.oddsportal.com", wait_until="domcontentloaded")
    await asyncio.sleep(3)

    target_url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"
    await page.goto(target_url, wait_until="domcontentloaded")
    await asyncio.sleep(5)

    for i in range(30):
        await page.evaluate("window.scrollBy(0, 400)")
        await asyncio.sleep(0.3)
    await asyncio.sleep(10)

    print("=" * 60)
    print("V54.7 比赛数据提取")
    print("=" * 60)
    print()

    # 查找包含比分的链接
    match_data = await page.evaluate("""
        () => {
            const results = [];
            const links = document.querySelectorAll('a[href]');
            const scorePattern = /\\d\\s*-\\s*\\d/;

            for (var i = 0; i < links.length; i++) {
                const link = links[i];
                const href = link.getAttribute('href');
                const text = link.textContent.trim();

                if (href && href.includes('/football/') && scorePattern.test(text)) {
                    // 查找父元素中的完整信息
                    const parent = link.closest('div, tr, td');
                    const parentText = parent ? parent.textContent : '';

                    results.push({
                        href: href,
                        linkText: text.substring(0, 50),
                        parentText: parentText.substring(0, 100),
                        hasId: href.includes('-') && href.match(/-\\w{3,}\\//)
                    });
                }

                if (results.length > 100) break;
            }

            return results;
        }
    """)

    print(f"找到包含比分的链接: {len(match_data)}")
    print()

    if match_data:
        # 去重
        unique = {}
        for item in match_data:
            key = item['href']
            if key not in unique:
                unique[key] = item

        print(f"去重后: {len(unique)} 个链接")
        print()

        print("链接样例:")
        for i, (href, item) in enumerate(list(unique.items())[:15]):
            print(f"{i+1}. {href}")
            print(f"   Text: {item['linkText']}")
            print(f"   Parent: {item['parentText'][:80]}")
            print()

        # 检查是否有加密 ID
        with_id = [item for item in unique.values() if item['hasId']]
        print(f"包含加密 ID: {len(with_id)} 个")

        if with_id:
            print()
            print("带加密 ID 的链接:")
            for item in with_id[:10]:
                print(f"  {item['href']}")

    # 保存结果
    output_path = Path("logs/debug_v54_7/match_links.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump({
            "total": len(match_data),
            "unique": len(unique) if match_data else 0,
            "with_id": len([m for m in (unique.values() if match_data else []) if m['hasId']]),
            "samples": list(unique.values())[:20] if match_data else []
        }, f, indent=2)

    print()
    print(f"数据已保存: {output_path}")

    await ctx.close()
    await p.stop()


if __name__ == "__main__":
    asyncio.run(simple_extract())
