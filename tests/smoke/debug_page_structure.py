#!/usr/bin/env python3
"""
调试脚本 V2: 深度分析 OddsPortal 页面
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.async_api import async_playwright

TARGET_URL = "https://www.oddsportal.com/football/england/premier-league/liverpool-leeds-UJhOUJJM/#1X2;2"

async def analyze_page_deep():
    """深度分析页面结构"""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    )
    page = await context.new_page()

    print("=" * 60)
    print("[诊断 V2] 访问目标页面")
    print("=" * 60)

    await page.goto(TARGET_URL, wait_until="networkidle", timeout=30000)
    print("✓ 页面加载完成")

    # 等待 JavaScript 渲染
    await asyncio.sleep(5)

    print("\n" + "=" * 60)
    print("[诊断 V2] 检查页面渲染")
    print("=" * 60)

    # 检查是否为单页应用
    is_spa = await page.evaluate("() => !!window.__NUXT__ || !!window.__INITIAL_STATE__ || !!window.React")
    print(f"单页应用: {'是' if is_spa else '否'}")

    # 检查页面主要内容区域
    main_content = await page.query_selector("main, #app, [class*='content'], [class*='container']")
    print(f"主要内容区域: {'存在' if main_content else '不存在'}")

    # 获取所有 div 元素
    all_divs = await page.query_selector_all("div")
    print(f"Div 元素数量: {len(all_divs)}")

    # 检查包含数字的元素（可能包含赔率）
    print("\n" + "=" * 60)
    print("[诊断 V2] 搜索赔率数值")
    print("=" * 60)

    # 查找所有包含纯数字或小数的文本节点
    odds_values = await page.evaluate("""
        () => {
            const results = [];
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null
            );

            let node;
            let count = 0;
            while ((node = walker.nextNode()) && count < 50) {
                const text = node.textContent.trim();
                // 匹配赔率格式 (如 2.50, 1.85, 3.20)
                if (/^\\d+\\.\\d{2}$/.test(text)) {
                    results.push({
                        text: text,
                        parent: node.parentElement?.tagName || '',
                        class: node.parentElement?.className || ''
                    });
                    count++;
                }
            }
            return results;
        }
    """)

    print(f"找到 {len(odds_values)} 个可能的赔率数值:")
    for i, odd in enumerate(odds_values[:10]):
        print(f"  [{i+1}] {odd['text']} (标签={odd['parent']}, 类={odd['class'][:30]})")

    # 检查特定的 data 属性
    print("\n" + "=" * 60)
    print("[诊断 V2] 检查 data 属性")
    print("=" * 60)

    data_attrs = await page.evaluate("""
        () => {
            const all = document.querySelectorAll('*');
            const attrs = new Set();
            all.forEach(el => {
                el.getAttributeNames().forEach(attr => {
                    if (attr.startsWith('data-')) {
                        attrs.add(attr);
                    }
                });
            });
            return Array.from(attrs).sort();
        }
    """)

    print(f"找到 {len(data_attrs)} 个 data-* 属性:")
    for attr in data_attrs[:15]:
        print(f"  - {attr}")

    # 检查是否有 Next.js/Nuxt.js 的数据
    print("\n" + "=" * 60)
    print("[诊断 V2] 检查框架数据")
    print("=" * 60)

    nuxt_data = await page.evaluate("() => window.__NUXT__")
    print(f"NUXT 数据: {'存在' if nuxt_data else '不存在'}")

    # 获取页面完整 HTML（限制长度）
    print("\n" + "=" * 60)
    print("[诊断 V2] 页面 HTML 结构")
    print("=" * 60)

    body_html = await page.evaluate("() => document.body.innerHTML")
    print(f"HTML 长度: {len(body_html)} 字符")

    # 查找关键结构模式
    if "table" in body_html.lower():
        print("✓ 包含 'table' 关键字")
    if "bet365" in body_html.lower():
        print("✓ 包含 'bet365' 关键字")
    if "odds" in body_html.lower():
        print("✓ 包含 'odds' 关键字")

    # 检查是否有 shadow DOM
    has_shadow = await page.evaluate("""
        () => {
            const all = document.querySelectorAll('*');
            for (let el of all) {
                if (el.shadowRoot) return true;
            }
            return false;
        }
    """)
    print(f"Shadow DOM: {'存在' if has_shadow else '不存在'}")

    # 检查 iframe
    iframes = await page.query_selector_all("iframe")
    print(f"iframe 数量: {len(iframes)}")

    # 尝试截图（如果需要）
    print("\n" + "=" * 60)
    print("[诊断 V2] 页面快照")
    print("=" * 60)

    # 获取页面标题
    title = await page.title()
    print(f"页面标题: {title}")

    # 获取 URL
    current_url = page.url
    print(f"当前 URL: {current_url}")

    # 检查是否被重定向
    if current_url != TARGET_URL:
        print("⚠ 页面被重定向")

    # 检查 body 类名
    body_class = await page.evaluate("() => document.body.className")
    print(f"Body 类名: {body_class}")

    await browser.close()
    await playwright.stop()

    print("\n" + "=" * 60)
    print("[诊断 V2] 完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(analyze_page_deep())
