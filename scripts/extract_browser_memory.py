#!/usr/bin/env python3
"""
浏览器内存数据提取脚本
Browser Memory Data Extraction Script

前端逆向工程师 - Playwright Plan C: 读取浏览器内存中的数据对象
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent))

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ 需要安装 playwright: pip install playwright")
    print("   然后运行: playwright install")
    sys.exit(1)


async def extract_browser_memory():
    """提取浏览器内存数据"""
    print("🎭" + "=" * 70)
    print("🔍 浏览器内存数据提取")
    print("👨‍💻 前端逆向工程师 - Plan C: 读取浏览器内存对象")
    print("=" * 72)

    try:
        # 启动 Playwright
        async with async_playwright() as p:
            print("\n🚀 启动浏览器...")

            # 使用 stealth 插件防止被识别
            browser = await p.chromium.launch(
                headless=False,  # 设置为False以便观察
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ],
            )

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )

            page = await context.new_page()

            # 注入反检测脚本
            await page.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = { runtime: {} };
            """
            )

            # 访问目标页面
            target_url = "https://www.fotmob.com/match/4189362"
            print(f"📡 访问页面: {target_url}")

            await page.goto(target_url, wait_until="networkidle", timeout=60000)
            print("✅ 页面加载完成")

            # 等待JavaScript完全加载
            print("⏳ 等待页面完全渲染...")
            await asyncio.sleep(8)  # 给JS足够时间加载数据

            # 提取内存中的数据
            print("🔍 提取浏览器内存数据...")

            # JavaScript 提取脚本
            extract_script = """
            () => {
                const results = {};

                // 1. 提取 __NEXT_DATA__
                if (window.__NEXT_DATA__) {
                    results.nextData = window.__NEXT_DATA__;
                    console.log('Found __NEXT_DATA__');
                }

                // 2. 提取 __INITIAL_STATE__
                if (window.__INITIAL_STATE__) {
                    results.initialState = window.__INITIAL_STATE__;
                    console.log('Found __INITIAL_STATE__');
                }

                // 3. 查找其他可能的 fotmob 全局变量
                const globalKeys = Object.keys(window).filter(key =>
                    key.toLowerCase().includes('fotmob') ||
                    key.toLowerCase().includes('data') ||
                    key.toLowerCase().includes('state') ||
                    key.toLowerCase().includes('store')
                );

                results.globalVariables = {};
                globalKeys.forEach(key => {
                    try {
                        results.globalVariables[key] = window[key];
                        console.log('Found global variable:', key);
                    } catch (e) {
                        console.log('Cannot access global variable:', key);
                    }
                });

                // 4. 查找 React 相关的数据
                if (window.__NEXT_DATA__ && window.__NEXT_DATA__.props) {
                    const props = window.__NEXT_DATA__.props;

                    // 查找 pageProps
                    if (props.pageProps) {
                        results.pageProps = props.pageProps;
                        console.log('Found pageProps');
                    }

                    // 查找 content
                    for (const key in props) {
                        if (key.includes('content') || key.includes('data') || key.includes('match')) {
                            results[key] = props[key];
                            console.log('Found content data:', key);
                        }
                    }
                }

                // 5. 查找 Redux store (如果存在)
                if (window.__REDUX_STORE__) {
                    results.reduxStore = window.__REDUX_STORE__;
                    console.log('Found Redux store');
                }

                // 6. 尝试查找 React app 状态
                const reactRoot = document.querySelector('#__next');
                if (reactRoot && reactRoot._reactRootContainer) {
                    try {
                        const fiber = reactRoot._reactRootContainer._internalRoot.current;
                        if (fiber && fiber.child && fiber.child.memoizedProps) {
                            results.reactState = fiber.child.memoizedProps;
                            console.log('Found React state');
                        }
                    } catch (e) {
                        console.log('Cannot access React state');
                    }
                }

                // 7. 查找所有可能的 API 数据
                const scripts = document.querySelectorAll('script');
                scripts.forEach(script => {
                    if (script.textContent && script.textContent.includes('match')) {
                        try {
                            // 尝试查找JSON数据
                            const jsonMatches = script.textContent.match(/\\{[^}]*"match"[^}]*\\}/g);
                            if (jsonMatches) {
                                results.embeddedData = results.embeddedData || [];
                                jsonMatches.forEach(match => {
                                    try {
                                        const parsed = JSON.parse(match);
                                        results.embeddedData.push(parsed);
                                    } catch (e) {
                                        // 忽略解析错误
                                    }
                                });
                            }
                        } catch (e) {
                            // 忽略错误
                        }
                    }
                });

                // 8. 检查页面是否包含我们想要的数据
                results.pageContent = {
                    hasShotmap: document.documentElement.outerHTML.toLowerCase().includes('shotmap'),
                    hasStats: document.documentElement.outerHTML.toLowerCase().includes('stats'),
                    hasLineups: document.documentElement.outerHTML.toLowerCase().includes('lineup'),
                    hasOdds: document.documentElement.outerHTML.toLowerCase().includes('odds'),
                    hasXG: document.documentElement.outerHTML.toLowerCase().includes('xg'),
                    hasRating: document.documentElement.outerHTML.toLowerCase().includes('rating')
                };

                return results;
            }
            """

            # 执行提取脚本
            extracted_data = await page.evaluate(extract_script)

            print("\n📊 提取结果分析:")
            print("=" * 60)

            # 分析提取到的数据
            success_count = 0

            # 1. 检查 __NEXT_DATA__
            if "nextData" in extracted_data and extracted_data["nextData"]:
                next_data = extracted_data["nextData"]
                print("\n✅ 1. __NEXT_DATA__ 找到!")
                print(f"   类型: {type(next_data).__name__}")
                print(
                    f"   Keys: {list(next_data.keys()) if isinstance(next_data, dict) else 'N/A'}"
                )

                # 深度分析 nextData
                if isinstance(next_data, dict) and "props" in next_data:
                    props = next_data["props"]
                    print(
                        f"   props Keys: {list(props.keys()) if isinstance(props, dict) else 'N/A'}"
                    )

                    if isinstance(props, dict) and "pageProps" in props:
                        page_props = props["pageProps"]
                        print(
                            f"   pageProps Keys: {list(page_props.keys()) if isinstance(page_props, dict) else 'N/A'}"
                        )

                        if isinstance(page_props, dict) and len(page_props) > 0:
                            print("   pageProps 内容丰富，可能包含比赛数据")
                            success_count += 1

            # 2. 检查 __INITIAL_STATE__
            if "initialState" in extracted_data and extracted_data["initialState"]:
                print("\n✅ 2. __INITIAL_STATE__ 找到!")
                initial_state = extracted_data["initialState"]
                print(f"   类型: {type(initial_state).__name__}")

                if isinstance(initial_state, dict):
                    print(f"   Keys: {list(initial_state.keys())[:10]}...")
                    success_count += 1

            # 3. 检查全局变量
            if (
                "globalVariables" in extracted_data
                and extracted_data["globalVariables"]
            ):
                print("\n✅ 3. 全局变量找到!")
                global_vars = extracted_data["globalVariables"]
                for var_name, var_data in global_vars.items():
                    if var_data and not isinstance(var_data, str):
                        print(f"   {var_name}: {type(var_data).__name__}")
                        if isinstance(var_data, dict):
                            print(f"      Keys: {list(var_data.keys())[:5]}...")
                        elif isinstance(var_data, list):
                            print(f"      Length: {len(var_data)}")
                success_count += 1

            # 4. 检查 pageProps
            if "pageProps" in extracted_data and extracted_data["pageProps"]:
                print("\n✅ 4. pageProps 找到!")
                page_props = extracted_data["pageProps"]
                print(f"   类型: {type(page_props).__name__}")
                print(
                    f"   Keys: {list(page_props.keys()) if isinstance(page_props, dict) else 'N/A'}"
                )
                success_count += 1

            # 5. 检查 React 状态
            if "reactState" in extracted_data and extracted_data["reactState"]:
                print("\n✅ 5. React 状态找到!")
                react_state = extracted_data["reactState"]
                print(f"   类型: {type(react_state).__name__}")
                success_count += 1

            # 6. 检查页面内容
            if "pageContent" in extracted_data:
                page_content = extracted_data["pageContent"]
                print("\n🔍 6. 页面内容分析:")
                indicators = {
                    "shotmap": "射门图数据",
                    "stats": "统计数据",
                    "lineups": "阵容数据",
                    "odds": "赔率数据",
                    "xg": "xG数据",
                    "rating": "评分数据",
                }

                found_indicators = []
                for key, desc in indicators.items():
                    has_key = page_content.get(f"has{key.capitalize()}", False)
                    status = "✅" if has_key else "❌"
                    print(f"   {status} {desc}: {has_key}")
                    if has_key:
                        found_indicators.append(desc)

                if len(found_indicators) >= 4:
                    print("\n🎉 页面包含丰富的比赛数据!")
                    success_count += 1

            # 7. 深度检查某些数据
            print("\n🔬 7. 深度数据检查:")
            for key, data in extracted_data.items():
                if data and key not in ["pageContent"] and not isinstance(data, str):
                    data_str = json.dumps(data, ensure_ascii=False, default=str)
                    shopping_list_items = {
                        "shotmap": ["shotmap", "shotMap", "shot"],
                        "stats": ["stats", "statistics", "possession", "big chances"],
                        "lineups": ["lineup", "player", "rating"],
                        "odds": ["odds", "betting", "1x2"],
                        "xg": ["xg", "expectedGoals", "expected goals"],
                    }

                    for category, keywords in shopping_list_items.items():
                        if any(keyword in data_str.lower() for keyword in keywords):
                            print(f"   ✅ {category.upper()} 数据存在于 {key}")
                            success_count += 1
                            break

            # 保存提取到的数据到文件
            output_file = "extracted_browser_data.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n💾 数据已保存到: {output_file}")

            # 最终结论
            print("\n" + "🎯" * 18)
            print("📊 浏览器内存提取总结报告")
            print("🎯" * 18)

            print("🔍 提取到的数据源:")
            for key, data in extracted_data.items():
                if data:
                    print(f"   ✅ {key}: {type(data).__name__}")
                else:
                    print(f"   ❌ {key}: 空/未找到")

            print(f"\n📈 成功指标: {success_count} 个数据源找到有价值信息")

            if success_count >= 3:
                print("\n🎉 Plan C 成功!")
                print("✅ 浏览器内存包含完整的比赛数据")
                print("🚀 这就是我们的最终解决方案!")

                return True
            elif success_count >= 1:
                print("\n👍 Plan C 部分成功!")
                print("⚠️ 找到一些数据，需要进一步优化")
                return True
            else:
                print("\n❌ Plan C 失败!")
                print("⚠️ 浏览器内存中未找到预期的比赛数据")
                return False

            await browser.close()

    except Exception as e:
        print(f"\n❌ 提取过程失败: {e}")
        import traceback

        print(traceback.format_exc())
        return False


async def main():
    """主函数"""
    print("🚀 浏览器内存数据提取启动...")

    success = await extract_browser_memory()

    if success:
        print("\n✅ Playwright Plan C 可行!")
        print("🚀 下一步: 开发生产环境的浏览器内存采集器")
    else:
        print("\n❌ Plan C 失败，需要考虑其他方案")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
