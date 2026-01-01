#!/usr/bin/env python3
"""
V54.6 链接格式调试
==================

检查实际提取到的链接格式
"""

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

USER_DATA_DIR = Path(".playwright_stealth_profile")


async def debug_links():
    playwright = await async_playwright().start()

    browser_context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(USER_DATA_DIR),
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1920, "height": 1080},
    )

    stealth = Stealth()
    page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
    await stealth.apply_stealth_async(page)

    # 访问 Results 页面
    await page.goto("https://www.oddsportal.com", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(2)

    target_url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"
    await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(5)

    # 提取所有链接
    all_links = await page.evaluate("""
        () => {
            const results = [];
            const links = document.querySelectorAll('a[href]');

            links.forEach(link => {
                const href = link.getAttribute('href');
                if (href && href.includes('football')) {
                    results.push({
                        href: href,
                        text: link.textContent.trim().substring(0, 50)
                    });
                }
            });

            return results.slice(0, 200);  // 增加到 200 个
        }
    """)

    # 查找包含对阵信息的行
    match_rows = await page.evaluate("""
        () => {
            const results = [];
            // 查找包含球队对阵的 div 或 tr
            const rows = document.querySelectorAll('div[class*="match"], tr[class*="match"], div[class*="row"]');

            for (const row of rows) {
                const text = row.textContent;
                // 查找包含 "vs" 或 "-" 的对阵文本
                if (text.includes(' vs ') || (text.match(/\\d\\s*-\\s*\\d/) && text.length < 200)) {
                    const links = row.querySelectorAll('a[href]');
                    links.forEach(link => {
                        results.push({
                            href: link.getAttribute('href'),
                            text: link.textContent.trim().substring(0, 60),
                            rowText: text.substring(0, 100)
                        });
                    });
                }
                if (results.length > 50) break;
            }

            return results;
        }
    """)

    print("=" * 60)
    print("V54.6 链接格式调试")
    print("=" * 60)
    print(f"\n找到 {len(all_links)} 个 football 链接")
    print(f"找到 {len(match_rows)} 个比赛行\n")

    if match_rows:
        print("比赛行示例:")
        print("-" * 60)
        for i, row in enumerate(match_rows[:10], 1):
            print(f"{i}. {row['href']}")
            print(f"   Text: {row['text']}")
            print(f"   Row: {row['rowText'][:80]}")
            print()
    else:
        print("未找到比赛行，显示前 20 个链接:\n")
        for i, link in enumerate(all_links[:20], 1):
            print(f"{i}. {link['href']}")
            print(f"   Text: {link['text'][:60]}")
            print()

    # 分析 URL 模式
    print("\n" + "=" * 60)
    print("URL 模式分析")
    print("=" * 60 + "\n")

    patterns = {
        "加密 ID (短)": r'/-([a-zA-Z0-9]{3,6})/',
        "加密 ID (长)": r'/-([a-zA-Z0-9]{7,})/',
        "纯数字 ID": r'/-(\\d+)/',
        "包含 /match/": r'/match/',
    }

    for pattern_name, pattern in patterns.items():
        count = sum(1 for link in all_links if re.search(pattern, link['href']))
        print(f"{pattern_name:20s}: {count} 个")

    # 显示可能的详情页链接
    print("\n" + "=" * 60)
    print("可能的详情页链接（包含加密 ID）")
    print("=" * 60 + "\n")

    # 从比赛行中查找
    detail_links = []
    if match_rows:
        for row in match_rows:
            href = row['href']
            if re.search(r'-[a-zA-Z0-9]{3,}/', href) and 'football' in href:
                detail_links.append(row)
    else:
        # 从所有链接中查找
        for link in all_links:
            href = link['href']
            if re.search(r'-[a-zA-Z0-9]{3,}/', href) and 'football' in href:
                detail_links.append(link)

    for link in detail_links[:10]:
        print(f"  {link['href']}")
        if 'rowText' in link:
            print(f"  Row: {link['rowText'][:60]}")
        else:
            print(f"  Text: {link.get('text', 'N/A')[:50]}")
        print()

    if not detail_links:
        print("  (未找到包含加密 ID 的链接)")
        print()
        print("检查页面 HTML 结构...")
        # 尝试查找任何包含球队名的元素
        sample_text = await page.evaluate("""
            () => {
                // 获取页面 body 的前 2000 个字符
                return document.body.textContent.substring(0, 2000);
            }
        """)
        print(f"\n页面文本预览:\n{sample_text[:500]}")

    await browser_context.close()
    await playwright.stop()


if __name__ == "__main__":
    asyncio.run(debug_links())
