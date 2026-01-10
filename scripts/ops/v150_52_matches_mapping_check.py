#!/usr/bin/env python3
"""
V150.52 matches_mapping 表健康检查

验证 V150.35 收割机的实际目标表中的 URL 健康状况
"""

import asyncio
import subprocess
import sys
from playwright.async_api import async_playwright


async def verify_urls(sample_size: int = 20):
    """验证 matches_mapping 表中的 URL"""
    print("=" * 80)
    print("🔬 V150.52 matches_mapping 表健康检查")
    print("=" * 80)

    # 抽取 matches_mapping 表中的 URL
    cmd = [
        "docker", "exec", "football_prediction_db",
        "psql", "-U", "football_user", "-d", "football_db",
        "-t", "-c",
        f"COPY (SELECT oddsportal_url FROM matches_mapping "
        f"WHERE oddsportal_url IS NOT NULL "
        f"AND oddsportal_url LIKE '%-202%' "
        f"ORDER BY RANDOM() LIMIT {sample_size}) TO STDOUT;"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    urls = []
    for line in result.stdout.strip().split('\n'):
        url = line.strip()
        if url and url.startswith('http') and len(url) > 50:
            urls.append(url)

    if len(urls) < sample_size:
        print(f"⚠️  警告：只抽取到 {len(urls)} 个 URL")

    print(f"\n📋 抽取到 {len(urls)} 个 matches_mapping 表中的 URL")
    print(f"🌐 使用 Playwright 浏览器检查...\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        results = []
        for i, url in enumerate(urls, 1):
            page = await context.new_page()
            try:
                response = await page.goto(url, timeout=15000)
                status_emoji = "✅" if response.status == 200 else "❌"
                print(f"   [{i}/{len(urls)}] {status_emoji} [{response.status}] {url[:70]}...")
                results.append({
                    'url': url,
                    'status': response.status,
                    'healthy': response.status == 200,
                    'error': None
                })
            except Exception as e:
                print(f"   [{i}/{len(urls)}] ❌ [Error] {url[:70]}...")
                results.append({
                    'url': url,
                    'status': 0,
                    'healthy': False,
                    'error': str(e)[:100]
                })
            finally:
                await page.close()

        await browser.close()

    # 统计结果
    healthy_count = sum(1 for r in results if r['healthy'])

    print(f"\n{'=' * 80}")
    print("📊 V150.52 验证报告")
    print(f"{'=' * 80}")
    print(f"\n总检查: {len(results)} 个 URL")
    print(f"✅ 健康有效 (200 OK): {healthy_count} ({healthy_count/len(results)*100:.1f}%)")
    print(f"❌ 失效不可用: {len(results) - healthy_count} ({(len(results)-healthy_count)/len(results)*100:.1f}%)")

    # 显示健康的 URL 样本
    healthy_urls = [r for r in results if r['healthy']]
    if healthy_urls:
        print(f"\n✅ 健康 URL 样本 (前 3 个):")
        for r in healthy_urls[:3]:
            print(f"   [{r['status']}] {r['url']}")

    # 失效的 URL
    unhealthy = [r for r in results if not r['healthy']]
    if unhealthy:
        print(f"\n⚠️  失效 URL 样本 (前 3 个):")
        for r in unhealthy[:3]:
            print(f"   - {r['url'][:80]}...")
            print(f"     Status: {r['status']}, Error: {r['error']}")

    return healthy_count / len(results) if results else 0


if __name__ == "__main__":
    exit_code = asyncio.run(verify_urls())
    sys.exit(0 if exit_code >= 0.8 else 1)
