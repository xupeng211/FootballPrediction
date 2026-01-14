#!/usr/bin/env python3
"""
Fetch sample OddsPortal results page for analysis
"""
import asyncio
import re
from playwright.async_api import async_playwright

async def fetch_results_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        url = 'https://www.oddsportal.com/football/england/premier-league-2023-2024/results/'
        print(f'Fetching: {url}')

        # 等待页面完全加载（包括 JavaScript 执行）
        await page.goto(url, wait_until='networkidle', timeout=60000)

        # 额外等待确保 Vue.js 渲染完成
        print('Waiting for Vue.js rendering to complete...')
        await page.wait_for_timeout(5000)

        # 点击 "Show more" 按钮加载所有比赛
        print('Looking for "Show more" button...')
        try:
            # 首先尝试滚动到底部触发懒加载
            print('Scrolling to bottom to trigger lazy loading...')
            for i in range(5):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(1000)

            # 等待可能的懒加载内容
            await page.wait_for_timeout(3000)

            # 检查是否有 show-more 相关的任何元素
            show_more_selectors = [
                '#show-more-btn',
                '[class*="show-more"]',
                '[class*="load-more"]',
                'button:has-text("Show more")',
                'button:has-text("Load more")',
                'a:has-text("Show more")',
            ]

            btn_found = False
            for selector in show_more_selectors:
                try:
                    btn = await page.query_selector(selector)
                    if btn:
                        print(f'✅ Found button with selector: {selector}')
                        btn_found = True
                        # 点击多次直到没有更多内容
                        max_clicks = 20
                        for click_count in range(1, max_clicks + 1):
                            try:
                                current_btn = await page.query_selector(selector)
                                if current_btn:
                                    is_visible = await current_btn.is_visible()
                                    if is_visible:
                                        await current_btn.click()
                                        print(f'  Clicked ({click_count}/{max_clicks})...')
                                        await page.wait_for_timeout(1500)
                                    else:
                                        break
                                else:
                                    break
                            except:
                                break
                        print(f'✅ Loaded all matches')
                        break
                except:
                    continue

            if not btn_found:
                print('⚠️  No "Show more" button found - might be all content loaded')

        except Exception as e:
            print(f'⚠️  Error with lazy loading: {e}')

        html = await page.content()

        # 保存到文件（渲染后的 HTML）
        with open('logs/premier_league_results_sample.html', 'w', encoding='utf-8') as f:
            f.write(html)

        print(f'Saved {len(html)} bytes to logs/premier_league_results_sample.html')

        # 从渲染的 DOM 中提取比赛链接
        print('\n=== Extracting match links from rendered DOM ===')

        # 方法 2: 查找所有 football 相关链接
        all_football_links = await page.query_selector_all('a[href*="/football/"]')
        football_hrefs = []
        for link in all_football_links:
            href = await link.get_attribute('href')
            if href and 'premier-league-2023-2024' in href:
                football_hrefs.append(href)

        print(f'Found {len(football_hrefs)} total football links for this season')

        # 获取所有唯一链接
        unique_links = sorted(set(football_hrefs))
        # 排除根链接（/football/england/premier-league-2023-2024/）
        # 排除 standings 页面
        # 排除完整 URL（重复的）
        match_links_only = [
            link for link in unique_links
            if link.count('-') > 2  # 至少包含 home-away-hash
            and not link.endswith('/standings/')
            and not link.startswith('https://')
            and not link == '/football/england/premier-league-2023-2024/'
        ]

        print(f'\n✅ Found {len(match_links_only)} unique match links!')

        # 显示所有链接
        for i, link in enumerate(match_links_only, 1):
            # 提取 hash (最后一段)
            hash_part = link.split('/')[-1]
            # 提取队名 (倒数第二段)
            teams_part = '-'.join(link.split('/')[-2].split('-')[:-1]) if len(link.split('/')) > 2 else 'unknown'
            print(f'{i:3d}. {link} (hash: {hash_part})')

        # 保存链接到文件
        with open('logs/premier_league_match_links.txt', 'w', encoding='utf-8') as f:
            for link in match_links_only:
                f.write(f'{link}\n')
        print(f'\n💾 Saved {len(match_links_only)} links to logs/premier_league_match_links.txt')

        await context.close()
        await browser.close()

if __name__ == '__main__':
    asyncio.run(fetch_results_page())
