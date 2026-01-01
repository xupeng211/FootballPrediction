#!/usr/bin/env python3
"""
V54.7 HTML 保存器 - 离线分析工具
==============================

Author: V54.7
Date: 2026-01-01
"""

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth


async def save_and_analyze():
    p = await async_playwright().start()
    ctx = await p.chromium.launch_persistent_context(
        user_data_dir=str(Path('.playwright_stealth_profile')),
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    stealth = Stealth()
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await stealth.apply_stealth_async(page)

    print("访问主页...")
    await page.goto("https://www.oddsportal.com", timeout=60000)
    await asyncio.sleep(5)

    print("访问 Results 页面...")
    target_url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"
    await page.goto(target_url, timeout=90000, wait_until="domcontentloaded")
    await asyncio.sleep(8)

    print("滚动触发加载...")
    for i in range(30):
        await page.evaluate("window.scrollBy(0, 400)")
        await asyncio.sleep(0.4)
    await asyncio.sleep(15)

    # 保存完整 HTML
    html = await page.content()
    output_path = Path("logs/debug_v54_7/results_page.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML 已保存: {output_path}")
    print(f"大小: {len(html):,} 字节")
    print()

    # 离线分析
    print("=" * 60)
    print("离线分析")
    print("=" * 60)
    print()

    # 查找球队名
    teams = ['Manchester', 'Liverpool', 'Chelsea', 'Arsenal', 'Tottenham']
    found_teams = []
    for team in teams:
        if team in html:
            count = html.count(team)
            found_teams.append((team, count))
            print(f"✓ {team}: {count} 次")

    if not found_teams:
        print("✗ 未找到知名球队名")
        print()
        print("检查页面内容...")
        # 显示前 2000 字符
        print(html[:2000])

    print()
    print("查找 /football/ 链接...")

    # 查找所有链接
    pattern = r'href=\"(/football/[^\"]+)\"'
    links = re.findall(pattern, html)
    print(f"找到 {len(links)} 个链接")

    # 分类
    categories = {
        "results": [],
        "standings": [],
        "outrights": [],
        "match": [],  # 可能是比赛
    }

    for link in links:
        if "results" in link:
            categories["results"].append(link)
        elif "standings" in link:
            categories["standings"].append(link)
        elif "outrights" in link:
            categories["outrights"].append(link)
        else:
            categories["match"].append(link)

    print()
    print("链接分类:")
    for cat, items in categories.items():
        print(f"  {cat:15s}: {len(items)} 个")

    print()
    if categories["match"]:
        print("可能的比赛链接:")
        for link in categories["match"][:20]:
            print(f"  {link}")

    await ctx.close()
    await p.stop()


if __name__ == "__main__":
    asyncio.run(save_and_analyze())
