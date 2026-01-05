#!/usr/bin/env python3
"""V64.0 URL 诊断脚本 - 检查测试 URL 有效性."""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))


TEST_URLS = [
    ("Chelsea vs Arsenal", "https://www.oddsportal.com/football/england/premier-league-2024-2025/chelsea-arsenal-CEnSxfJ0/"),
    ("Liverpool vs Man City", "https://www.oddsportal.com/football/england/premier-league-2024-2025/liverpool-manchester-city-gB8rQ2Z0/"),
    ("Tottenham vs Newcastle", "https://www.oddsportal.com/football/england/premier-league-2024-2025/tottenham-hotspur-newcastle-9sK5xP8/"),
]


async def diagnose_url(name: str, url: str):
    """诊断单个 URL 的页面内容."""
    print(f"\n{'='*70}")
    print(f"诊断: {name}")
    print(f"URL: {url}")
    print('='*70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            # 访问页面
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            print(f"✓ 页面加载成功")

            # 检查页面标题
            title = await page.title()
            print(f"✓ 页面标题: {title}")

            # 检查是否有 odd-container
            containers = page.locator("div[data-testid='odd-container']")
            count = await containers.count()
            print(f"✓ odd-container 数量: {count}")

            if count == 0:
                print("⚠️  未找到 odd-container 元素")
                print("正在检查页面内容...")

                # 检查是否有登录提示
                content = await page.content()

                if 'login' in content.lower():
                    print("⚠️  页面可能需要登录")
                if '404' in content or 'not found' in content.lower():
                    print("⚠️  页面可能返回 404")

                # 检查是否有赔率数据
                if 'odds' in content.lower() or 'pinnacle' in content.lower():
                    print("✓ 页面包含 odds/pinnacle 关键词")

                # 保存 HTML 用于调试
                import time
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"logs/v64_debug/diagnose_{timestamp}.html"
                Path(filename).parent.mkdir(parents=True, exist_ok=True)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✓ HTML 已保存到: {filename}")
            else:
                print(f"✓ 找到 {count} 个 odd-container")

                # 检查是否有 Pinnacle
                try:
                    bookmakers = await page.evaluate("""
                        () => {
                            const containers = document.querySelectorAll('div[data-testid="odd-container"]');
                            const results = [];
                            for (let i = 0; i < Math.min(5, containers.length); i++) {
                                let elem = containers[i];
                                for (let j = 0; j < 10; j++) {
                                    if (elem && elem.parentElement) {
                                        elem = elem.parentElement;
                                        const nameElem = elem.querySelector('[data-testid="outrights-expanded-bookmaker-name"]');
                                        if (nameElem) {
                                            results.push(nameElem.textContent);
                                            break;
                                        }
                                    } else {
                                        break;
                                    }
                                }
                            }
                            return results;
                        }
                    """)
                    print(f"✓ 找到的博彩公司: {bookmakers}")
                except Exception as e:
                    print(f"⚠️  无法获取博彩公司列表: {e}")

            # 截图
            screenshot = f"logs/v64_debug/screenshot_{name.replace(' ', '_')}.png"
            await page.screenshot(path=screenshot)
            print(f"✓ 截图已保存: {screenshot}")

        except Exception as e:
            print(f"✗ 访问失败: {e}")

        finally:
            await context.close()
            await browser.close()


async def main():
    """主函数."""
    print("="*70)
    print("V64.0 URL 诊断")
    print("="*70)

    for name, url in TEST_URLS:
        await diagnose_url(name, url)
        await asyncio.sleep(2)


if __name__ == '__main__':
    asyncio.run(main())
