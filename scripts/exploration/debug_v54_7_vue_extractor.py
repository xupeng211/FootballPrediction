#!/usr/bin/env python3
"""
V54.7 Vue 数据提取器 - 从 Vue 组件中提取比赛数据
==================================================

Author: Senior Network Protocol & API Reverse Engineer
Version: V54.7 Vue Extractor
Date: 2026-01-01
"""

import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth


async def extract_vue_data():
    """从 Vue 应用中提取数据"""

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

    # 充分滚动
    for i in range(30):
        await page.evaluate("window.scrollBy(0, 400)")
        await asyncio.sleep(0.3)
    await asyncio.sleep(10)

    print("=" * 60)
    print("V54.7 Vue 数据提取")
    print("=" * 60)
    print()

    # 提取 Vue 组件数据
    vue_extraction = await page.evaluate("""
        () => {
            const results = {
                vue_instances: [],
                data_attributes: [],
                text_matches: []
            };

            // 1. 查找所有 Vue 相关的元素
            const allElements = document.querySelectorAll('*');
            for (const el of allElements) {
                // 检查 Vue 相关属性
                if (el.__vue__) {
                    const data = el.__vue__.$data || el.__vue__.data;
                    if (data) {
                        results.vue_instances.push({
                            tag: el.tagName,
                            class: el.className,
                            dataKeys: Object.keys(data).slice(0, 20)
                        });
                    }
                }

                // 检查 data- 属性
                for (const attr of el.attributes) {
                    if (attr.name.startsWith('data-') && attr.name.includes('match')) {
                        results.data_attributes.push({
                            attr: attr.name,
                            value: attr.value[:100]
                        });
                    }
                }
            }

            // 2. 查找包含球队名的文本节点
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null
            );

            let node;
            const teamNames = ['manchester', 'liverpool', 'chelsea', 'arsenal', 'tottenham',
                              'city', 'united', 'vs', ' - ', ':'];
            while (node = walker.nextNode()) {
                const text = node.textContent.trim();
                if (text.length > 5 && text.length < 200) {
                    const lower = text.toLowerCase();
                    if (teamNames.some(t => lower.includes(t))) {
                        // 获取父元素信息
                        const parent = node.parentElement;
                        results.text_matches.push({
                            text: text,
                            tag: parent.tagName,
                            class: parent.className,
                            href: parent.querySelector('a')?.getAttribute('href') || ''
                        });
                    }
                }
                if (results.text_matches.length > 100) break;
            }

            return results;
        }
    """)

    print(f"Vue 实例: {len(vue_extraction['vue_instances'])}")
    print(f"data- 属性: {len(vue_extraction['data_attributes'])}")
    print(f"包含球队名的文本: {len(vue_extraction['text_matches'])}")
    print()

    if vue_extraction["text_matches"]:
        print("球队名文本样例:")
        for i, match in enumerate(vue_extraction["text_matches"][:15]):
            print(f"{i+1}. <{match['tag']}> class=\"{match['class'][:40]}\"")
            print(f"   Text: {match['text'][:80]}")
            if match['href']:
                print(f"   Href: {match['href']}")
            print()

    # 尝试查找特定的比赛行
    print("=" * 60)
    print("查找比赛数据结构...")
    print("=" * 60)
    print()

    match_structure = await page.evaluate("""
        () => {
            const results = [];

            // 查找包含比分的行
            const scorePattern = /\\d\\s*-\\s*\\d/;
            const allDivs = document.querySelectorAll('div, tr, td');

            for (const el of allDivs) {
                const text = el.textContent || '';
                if (scorePattern.test(text) && text.length < 300 && text.length > 20) {
                    const links = el.querySelectorAll('a[href]');
                    const hrefs = Array.from(links).map(l => l.getAttribute('href')).filter(h => h);

                    results.push({
                        text: text.substring(0, 120),
                        tag: el.tagName,
                        class: el.className,
                        links: hrefs.slice(0, 5)
                    });

                    if (results.length > 30) break;
                }
            }

            return results;
        }
    """)

    print(f"找到包含比分的元素: {len(match_structure)}")
    print()

    if match_structure:
        print("比赛数据样例:")
        for i, item in enumerate(match_structure[:10]):
            print(f"{i+1}. <{item['tag']}>")
            if item['class']:
                print(f"   class: {item['class'][:60]}")
            print(f"   content: {item['text'][:100]}")
            if item['links']:
                print(f"   links: {item['links']}")
            print()

    # 保存完整数据
    output = {
        "vue_instances": vue_extraction["vue_instances"],
        "text_matches": vue_extraction["text_matches"][:50],
        "match_structure": match_structure[:20],
    }

    output_path = Path("logs/debug_v54_7/vue_data.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"完整数据已保存: {output_path}")

    await ctx.close()
    await p.stop()


if __name__ == "__main__":
    asyncio.run(extract_vue_data())
