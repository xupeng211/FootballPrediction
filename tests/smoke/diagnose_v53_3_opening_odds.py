#!/usr/bin/env python3
"""
V53.3 诊断脚本 V3: 精准分析机构行结构
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.async_api import async_playwright

TARGET_URL = (
    "https://www.oddsportal.com/football/england/premier-league/liverpool-leeds-UJhOUJJM/#1X2;2"
)


async def analyze_provider_rows():
    """分析机构行结构"""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    )
    page = await context.new_page()

    print("=" * 60)
    print("[V53.3 诊断 V3] 精准分析机构行结构")
    print("=" * 60)

    await page.goto(TARGET_URL, wait_until="networkidle", timeout=30000)
    await asyncio.sleep(5)

    # 查找包含机构名称和赔率的行
    print("\n" + "=" * 60)
    print("[分析] 查找机构-赔率组合")
    print("=" * 60)

    provider_rows = await page.evaluate("""
        () => {
            const results = [];

            // 查找所有包含机构名称和赔率的容器
            // 从诊断结果看，可能是 flex 布局的行
            const rows = document.querySelectorAll('div.flex, div[class*="border"]');

            for (const row of rows) {
                const text = row.textContent.trim();

                // 匹配机构名称 + 多个赔率的模式
                // 如: "10bet 1.53 4.40 5.60 94.4%"
                const pattern = /^([a-zA-Z0-9]+).*?(\d+\.\d{2}).*?(\d+\.\d{2}).*?(\d+\.\d{2})/;
                const match = text.match(pattern);

                if (match) {
                    const oddsLinks = row.querySelectorAll('a.odds-link');

                    results.push({
                        provider: match[1],
                        fullText: text.substring(0, 80),
                        oddsCount: oddsLinks.length,
                        oddsValues: Array.from(oddsLinks).map(l => l.textContent.trim()),
                        className: row.className,
                        innerHTML: row.innerHTML.substring(0, 300)
                    });
                }
            }

            return results.slice(0, 10);
        }
    """)

    if provider_rows:
        print(f"找到 {len(provider_rows)} 个机构行:\n")
        for i, row in enumerate(provider_rows):
            print(f"[{i + 1}] 机构: {row['provider']}")
            print(f"    完整文本: {row['fullText']}")
            print(f"    赔率数量: {row['oddsCount']}")
            print(f"    赔率值: {row['oddsValues']}")
            print(f"    类名: {row['className'][:60]}")
            print()
    else:
        print("未找到机构行结构")

    # 检查是否有不同类型的赔率（如 opening/closing）
    print("\n" + "=" * 60)
    print("[分析] 检查赔率数据类型")
    print("=" * 60)

    odds_analysis = await page.evaluate("""
        () => {
            // 获取所有赔率链接的详细信息
            const oddsLinks = document.querySelectorAll('a.odds-link');
            const results = [];

            for (let i = 0; i < Math.min(15, oddsLinks.length); i++) {
                const link = oddsLinks[i];

                // 检查链接的完整上下文
                const parent = link.parentElement;
                const grandParent = parent ? parent.parentElement : null;

                // 获取兄弟元素（可能是其他赔率）
                const siblings = parent ? Array.from(parent.children).map(el => ({
                    tag: el.tagName,
                    text: el.textContent.trim().substring(0, 20),
                    className: el.className
                })) : [];

                results.push({
                    index: i,
                    text: link.textContent.trim(),
                    parentClass: parent ? parent.className : '',
                    grandParentClass: grandParent ? grandParent.className : '',
                    siblings: siblings.slice(0, 5)
                });
            }

            return results;
        }
    """)

    print(f"前 {len(odds_analysis)} 个赔率链接的上下文:")
    for item in odds_analysis[:5]:
        print(f"\n  [{item['index']}] {item['text']}")
        print(f"    父元素: {item['parentClass'][:60]}")
        if item["siblings"]:
            print(f"    兄弟元素: {len(item['siblings'])} 个")

    # 检查页面上是否有任何表示 "opening" 或 "closing" 的文本
    print("\n" + "=" * 60)
    print("[分析] 检查时间标识")
    print("=" * 60)

    time_markers = await page.evaluate("""
        () => {
            const results = [];

            // 搜索所有可能表示时间的文本
            const allElements = document.querySelectorAll('*');

            for (const el of allElements) {
                const text = el.textContent.trim();
                if (text.length < 50 && text.length > 2) {
                    const lower = text.toLowerCase();
                    if (lower.includes('open') || lower.includes('close') ||
                        lower.includes('start') || lower.includes('end') ||
                        lower.includes('initial') || lower.includes('final')) {
                        results.push({
                            tag: el.tagName,
                            text: text,
                            className: el.className
                        });
                    }
                }
            }

            return results.slice(0, 10);
        }
    """)

    if time_markers:
        print(f"找到 {len(time_markers)} 个可能的时间标识:")
        for item in time_markers[:5]:
            print(f"  {item['text']}")
    else:
        print("未找到时间标识")

    await browser.close()
    await playwright.stop()

    print("\n" + "=" * 60)
    print("[V53.3 诊断 V3] 完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(analyze_provider_rows())
