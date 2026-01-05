#!/usr/bin/env python3
"""V61.0 Hover API Monitor - 监控悬停时的 API 调用."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

async def hover_api_monitor():
    """监控悬停时的 API 调用"""
    url = 'https://www.oddsportal.com/football/england/premier-league-2024-2025/chelsea-arsenal-CEnSxfJ0/'

    print('🎯 V61.0 Hover API Monitor')
    print('=' * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        # 监控所有请求
        requests_before = []
        requests_during_hover = []
        requests_after = []

        def log_request(request):
            url = request.url
            # 忽略静态资源
            if any(ext in url for ext in ['.js', '.css', '.png', '.svg', '.jpg', '.woff', '.gif']):
                return

            req_info = {
                'method': request.method,
                'url': url,
                'resource_type': request.resource_type
            }

            if len(requests_during_hover) == 0:
                requests_before.append(req_info)
            else:
                requests_after.append(req_info)

        page.on('request', log_request)

        # 监控响应
        responses_with_odds = []

        async def log_response(response):
            try:
                url = response.url
                url_lower = url.lower()
                if any(keyword in url_lower for keyword in ['odds', 'pinnacle', 'entity', 'api', 'ajax']):
                    content_type = await response.header_value('content-type') or ''
                    if 'json' in content_type.lower():
                        try:
                            data = await response.json()
                            data_str = json.dumps(data)
                            if any(kw in data_str.lower() for kw in ['odds', 'pinnacle', 'entity', 'opening']):
                                responses_with_odds.append({
                                    'url': url,
                                    'status': response.status,
                                    'data': data
                                })
                        except:
                            pass
            except:
                pass

        page.on('response', log_response)

        print(f'\n[1/4] Loading page...')
        await page.goto(url, wait_until='networkidle', timeout=60000)
        await asyncio.sleep(3)

        print(f'[2/4] Waiting for odd-container...')
        try:
            await page.wait_for_selector('div[data-testid="odd-container"]', timeout=30000)
        except:
            pass

        print(f'[3/4] Finding Pinnacle element...')
        containers = page.locator('div[data-testid="odd-container"]')
        count = await containers.count()
        print(f'   Found {count} odd-container elements')

        pinnacle_found = False

        for i in range(min(count, 50)):
            try:
                # 修改后的 evaluate 调用
                bookmaker = await containers.nth(i).evaluate("""(elem) => {
                    let parent = elem;
                    for (let i = 0; i < 10; i++) {
                        if (parent && parent.parentElement) {
                            parent = parent.parentElement;
                            const nameElem = parent.querySelector('[data-testid="outrights-expanded-bookmaker-name"]');
                            if (nameElem) {
                                return nameElem.textContent;
                            }
                        }
                    }
                    return null;
                }""")

                if bookmaker and 'pinnacle' in bookmaker.lower():
                    print(f'   ✓ Found Pinnacle at index {i}')
                    pinnacle_found = True

                    # 悬停并监控
                    print(f'[4/4] Hovering and monitoring API calls...')

                    await containers.nth(i).hover()

                    # 等待 tooltip 出现
                    for j in range(20):  # 10秒，每500ms检查
                        await asyncio.sleep(0.5)

                        tooltip = await page.evaluate("""() => {
                            const all = document.querySelectorAll('*');
                            for (let el of all) {
                                if (el.textContent && el.textContent.includes('Opening odds:')) {
                                    return true;
                                }
                            }
                            return false;
                        }""")

                        if tooltip:
                            print(f'   ✓ Tooltip appeared at {j * 500}ms')
                            break

                    # 再等待5秒捕获后续API
                    await asyncio.sleep(5)
                    break
            except Exception as e:
                continue

        # 分析结果
        print('\n' + '=' * 60)
        print('API CALL ANALYSIS')
        print('=' * 60)

        print(f'\n📊 Requests BEFORE hover: {len(requests_before)}')
        for req in requests_before[:10]:
            print(f'   {req.get("method")} {req.get("url")[:100]}')

        print(f'\n🎯 Requests DURING/AFTER hover: {len(requests_after)}')

        # 找出新增的请求
        before_urls = {req.get('url') for req in requests_before}
        new_requests = [req for req in requests_after if req.get('url') not in before_urls]

        print(f'   NEW requests: {len(new_requests)}')

        for req in new_requests[:10]:
            url = req.get('url', '')
            print(f'   {req.get("method")} {url[:100]}')

            url_lower = url.lower()
            if any(kw in url_lower for kw in ['odds', 'pinnacle', 'entity', 'ajax', 'api']):
                print(f'     ⭐ POTENTIAL ODDS API!')

        print(f'\n📦 Responses with odds data: {len(responses_with_odds)}')
        for resp in responses_with_odds[:3]:
            print(f'   URL: {resp.get("url", "?")[:100]}')
            print(f'   Status: {resp.get("status", "?")}')
            if isinstance(resp.get('data'), dict):
                print(f'   Data keys: {list(resp.get("data", {}).keys())[:10]}')

        # 保存结果
        output_dir = Path('logs/v61_hover_monitor')
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result = {
            'requests_before': requests_before[:20],
            'new_requests_after_hover': new_requests,
            'responses_with_odds': responses_with_odds,
            'pinnacle_found': pinnacle_found
        }

        output_file = output_dir / f'hover_monitor_{timestamp}.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f'\n💾 Results saved to: {output_file}')

        await browser.close()

        return len(new_requests) > 0 or len(responses_with_odds) > 0


if __name__ == '__main__':
    has_api = asyncio.run(hover_api_monitor())

    print('\n' + '=' * 60)
    if has_api:
        print('✅ API CALLS DETECTED: Data loaded on hover!')
        print('   → Strategy: Intercept these APIs')
    else:
        print('⚠️  NO API CALLS: Data generated client-side')
        print('   → Strategy: Analyze tooltip generation mechanism')
    print('=' * 60)
