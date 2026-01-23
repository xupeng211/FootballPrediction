#!/usr/bin/env python3
"""V41.680 实时解密测试 - 从 OddsPortal 获取并解密实时数据."""

import asyncio
import time
import json
import logging
from playwright.async_api import async_playwright
from pathlib import Path

from src.core.oddsportal_decryptor import OddsPortalDecryptor

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


async def fetch_and_decrypt():
    """从 OddsPortal 获取实时加密数据并解密."""

    print("=" * 70)
    print("V41.680 实时解密测试")
    print("=" * 70)

    decryptor = OddsPortalDecryptor()
    print(f"\n密钥配置:")
    print(f"  密码: {decryptor.password.decode()[:20]}...")
    print(f"  盐值: {decryptor.salt.decode()[:20]}...")

    encrypted_responses = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        )

        page = await context.new_page()

        # 拦截 ajax-all-events 响应
        async def handle_response(response):
            url = response.url
            if "ajax-all-events" in url:
                print(f"\n✓ 捕获到加密响应!")
                print(f"  URL: {url[:80]}...")
                print(f"  状态: {response.status}")

                try:
                    text = await response.text()
                    print(f"  响应长度: {len(text)} 字符")
                    print(f"  前 100 字符: {text[:100]}")

                    encrypted_responses.append({
                        "url": url,
                        "body": text,
                        "headers": dict(response.headers),
                    })
                except Exception as e:
                    print(f"  获取响应失败: {e}")

        page.on("response", handle_response)

        print(f"\n访问英超联赛页...")
        await page.goto("https://www.oddsportal.com/football/england/premier-league/", timeout=60000)

        print(f"等待页面加载和加密响应...")
        await page.wait_for_load_state("networkidle", timeout=30000)
        await asyncio.sleep(10)

        await context.close()
        await browser.close()

    # 尝试解密捕获的数据
    print(f"\n{'=' * 70}")
    print(f"解密测试")
    print(f"{'=' * 70}")

    if encrypted_responses:
        for i, response in enumerate(encrypted_responses):
            print(f"\n响应 #{i+1}:")
            print(f"  URL: {response['url'][:60]}...")

            encrypted_data = response['body']

            # 尝试解密
            start = time.time()
            result = decryptor.decrypt_feed(encrypted_data)
            elapsed = (time.time() - start) * 1000

            if result:
                print(f"  ✓ 解密成功!")
                print(f"    延迟: {elapsed:.2f} ms")

                if isinstance(result, dict):
                    print(f"    字段数: {len(result)}")
                    print(f"    顶层键: {list(result.keys())[:10]}")

                    # 查找比赛数据
                    if 'data' in result:
                        data = result['data']
                        print(f"    data 类型: {type(data).__name__}")

                        # 尝试提取比赛信息
                        if isinstance(data, dict):
                            for key in list(data.keys())[:5]:
                                value = data[key]
                                if isinstance(value, dict) and 'name' in value:
                                    print(f"    比赛: {value.get('name', 'N/A')}")

                    # 保存解密结果
                    output_file = Path("config/stealth/v41_680_decrypted_sample.json")
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    output_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
                    print(f"\n  ✓ 解密结果已保存至: {output_file}")

                    return True
            else:
                print(f"  ✗ 解密失败")
                print(f"    响应格式可能需要调整")
                print(f"    前 200 字符: {encrypted_data[:200]}")
    else:
        print("\n未捕获到加密响应")
        print("可能原因:")
        print("  1. 页面加载超时")
        print("  2. 网络连接问题")
        print("  3. OddsPortal 更改了 API 结构")

    return False


if __name__ == "__main__":
    success = asyncio.run(fetch_and_decrypt())
    exit(0 if success else 1)
