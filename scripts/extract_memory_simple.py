#!/usr/bin/env python3
"""
简化版浏览器内存提取脚本
Simplified Browser Memory Extraction

前端逆向工程师 - 简化版Playwright Plan C
"""

import asyncio
import json
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ 需要安装 playwright: pip install playwright")
    sys.exit(1)

async def extract_memory_simple():
    """简化版内存提取"""
    print("🎭" + "="*60)
    print("🔍 简化版浏览器内存提取")
    print("👨‍💻 前端逆向工程师 - headless模式")
    print("="*62)

    try:
        async with async_playwright() as p:
            print("\n🚀 启动无头浏览器...")

            # 使用 headless 模式，更简单的配置
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-setuid-sandbox',
                    '--disable-gpu',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-default-apps'
                ]
            )

            page = await browser.new_page()

            # 设置简单的用户代理
            await page.set_user_agent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

            # 访问页面
            target_url = "https://www.fotmob.com/match/4189362"
            print(f"📡 访问页面: {target_url}")

            try:
                await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
                print("✅ 页面加载完成")
            except Exception as e:
                print(f"⚠️ 页面加载问题: {e}")
                print("尝试继续分析...")

            # 等待一段时间让页面渲染
            print("⏳ 等待页面渲染...")
            await asyncio.sleep(5)

            # 简化的提取脚本
            extract_script = """
            () => {
                const results = {};

                // 检查 __NEXT_DATA__
                if (typeof window !== 'undefined' && window.__NEXT_DATA__) {
                    results.nextData = {
                        exists: true,
                        keys: Object.keys(window.__NEXT_DATA__),
                        hasProps: !!(window.__NEXT_DATA__.props),
                        propsKeys: window.__NEXT_DATA__.props ? Object.keys(window.__NEXT_DATA__.props) : []
                    };
                }

                // 检查页面内容中的数据指示器
                if (typeof document !== 'undefined') {
                    const content = document.documentElement.outerHTML;
                    results.pageContent = {
                        hasShotmap: content.toLowerCase().includes('shotmap') || content.toLowerCase().includes('shot_map'),
                        hasStats: content.toLowerCase().includes('stats') || content.toLowerCase().includes('possession'),
                        hasLineups: content.toLowerCase().includes('lineup') || content.toLowerCase().includes('player'),
                        hasOdds: content.toLowerCase().includes('odds') || content.toLowerCase().includes('betting'),
                        hasXG: content.toLowerCase().includes('xg') || content.toLowerCase().includes('expected'),
                        hasRating: content.toLowerCase().includes('rating'),
                        hasBigChances: content.toLowerCase().includes('big chances'),
                        htmlLength: content.length
                    };
                }

                // 查找所有脚本标签
                if (typeof document !== 'undefined') {
                    const scripts = document.querySelectorAll('script[type="application/json"], script[type="application/ld+json"]');
                    results.jsonScripts = scripts.length;

                    const textScripts = Array.from(document.querySelectorAll('script')).filter(script => {
                        return script.textContent && (
                            script.textContent.includes('match') ||
                            script.textContent.includes('stats') ||
                            script.textContent.includes('shotmap')
                        );
                    });
                    results.matchScripts = textScripts.length;
                }

                return results;
            }
            """

            # 执行提取
            print("🔍 提取页面数据...")
            results = await page.evaluate(extract_script)

            print("\n📊 提取结果:")
            print("="*50)

            success_count = 0

            # 分析结果
            if 'nextData' in results and results['nextData']['exists']:
                print("✅ 找到 __NEXT_DATA__")
                next_data = results['nextData']
                print(f"   Keys: {next_data['keys']}")
                if next_data['hasProps']:
                    print(f"   Props Keys: {next_data['propsKeys']}")
                    if 'pageProps' in next_data['propsKeys']:
                        print("   ✅ 发现 pageProps - 这可能包含比赛数据!")
                        success_count += 1

            if 'pageContent' in results:
                content = results['pageContent']
                print("\n🔍 页面内容分析:")
                indicators = {
                    'hasShotmap': '射门图',
                    'hasStats': '统计数据',
                    'hasLineups': '阵容数据',
                    'hasOdds': '赔率数据',
                    'hasXG': 'xG数据',
                    'hasRating': '评分数据',
                    'hasBigChances': '绝佳机会'
                }

                found_indicators = []
                for key, desc in indicators.items():
                    if content.get(key, False):
                        print(f"   ✅ {desc}")
                        found_indicators.append(desc)
                        success_count += 1
                    else:
                        print(f"   ❌ {desc}")

                print(f"\n   HTML内容长度: {content['htmlLength']:,} 字符")

                if len(found_indicators) >= 4:
                    print("   🎉 页面包含丰富的比赛数据指示器!")

            if 'jsonScripts' in results:
                print("\n📋 脚本分析:")
                print(f"   JSON脚本: {results['jsonScripts']}")
                print(f"   匹配脚本: {results['matchScripts']}")
                if results['matchScripts'] > 0:
                    print("   ✅ 找到可能包含比赛数据的脚本!")
                    success_count += 1

            # 保存结果
            with open("memory_extract_simple.json", 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            print("\n💾 结果已保存到: memory_extract_simple.json")

            await browser.close()

            # 结论
            print("\n" + "🎯"*15)
            print("📊 简化版提取总结")
            print("🎯"*15)

            print(f"🔍 成功指标: {success_count} 个数据源找到")

            if success_count >= 3:
                print("\n🎉 Plan C 基本成功!")
                print("✅ 浏览器内存包含比赛数据指示器")
                print("🚀 建议进一步开发完整的内存采集器")
                return True
            elif success_count >= 1:
                print("\n👍 Plan C 有希望!")
                print("⚠️ 找到一些数据，需要优化提取逻辑")
                return True
            else:
                print("\n❌ Plan C 困难较大")
                print("⚠️ 浏览器内存中数据较少")
                return False

    except Exception as e:
        print(f"\n❌ 提取失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

async def main():
    """主函数"""
    print("🚀 简化版浏览器内存提取启动...")

    success = await extract_memory_simple()

    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
