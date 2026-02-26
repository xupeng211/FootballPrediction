#!/usr/bin/env python3
"""V129.0 静态源码嗅探 - 从 OddsPortal app.js 中提取 AES 密钥.

目标：提取用于 AES-CBC 解密的 Password 和 Salt
"""

import asyncio
import logging
import os
import re
import sys
from pathlib import Path

for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                  'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(proxy_var, None)

from playwright.async_api import async_playwright, Page

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

STEALTH_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
]


async def sniff_js_keys(page: Page, output_dir: Path) -> dict[str, str]:
    """从 JavaScript 文件中嗅探密钥."""

    keys = {}

    # 模式 1: JSON.parse(r.data, "password", "salt")
    pattern1 = rb'JSON\.parse\([^,]+,\s*["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']\)'

    # 模式 2: h(r.data, "password", "salt")
    pattern2 = rb'h\([^,]+,\s*["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']\)'

    # 模式 3: decrypt(.*, "password", "salt")
    pattern3 = rb'decrypt\([^,]+,\s*["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']\)'

    # 模式 4: CryptoJS.AES.decrypt(.*, "password", {salt: "salt"})
    pattern4 = rb'CryptoJS\.AES\.decrypt\([^,]+,\s*["\']([^"\']+)["\']'

    all_patterns = [
        ("JSON.parse with 2 strings", pattern1),
        ("h() function", pattern2),
        ("decrypt() function", pattern3),
        ("CryptoJS.AES.decrypt", pattern4),
    ]

    # 获取所有 script 标签的 src
    script_urls = await page.evaluate("""() => {
        const scripts = Array.from(document.querySelectorAll('script[src]'));
        return scripts.map(s => s.src).filter(src => src.includes('app-'));
    }""")

    logger.info(f"\n  📜 找到 {len(script_urls)} 个 app-*.js 文件")

    for idx, script_url in enumerate(script_urls, 1):
        logger.info(f"\n  [{idx}] 下载: {script_url}")

        try:
            # 下载 JS 文件
            response = await page.request.get(script_url)
            js_content = await response.body()

            logger.info(f"    📦 大小: {len(js_content)} 字节")

            # 保存原始 JS 文件
            js_filename = output_dir / f"app_{idx}.js"
            with open(js_filename, "wb") as f:
                f.write(js_content)
            logger.info(f"    💾 保存到: {js_filename}")

            # 搜索所有模式
            for pattern_name, pattern in all_patterns:
                matches = re.findall(pattern, js_content)
                if matches:
                    logger.info(f"    ✅ [{pattern_name}] 找到 {len(matches)} 个匹配")
                    for password, salt in matches[:5]:  # 只显示前 5 个
                        logger.info(f"       Password: {password.decode('utf-8', errors='ignore')}")
                        logger.info(f"       Salt: {salt.decode('utf-8', errors='ignore')}")

                        # 保存第一个匹配的密钥
                        if 'password' not in keys:
                            keys['password'] = password.decode('utf-8', errors='ignore')
                            keys['salt'] = salt.decode('utf-8', errors='ignore')

        except Exception as e:
            logger.error(f"    ❌ 下载失败: {e}")

    return keys


async def main():
    logger.info("=" * 80)
    logger.info("V129.0 静态源码嗅探 - AES 密钥提取")
    logger.info("=" * 80)

    # 创建输出目录
    output_dir = Path("logs/v129_0_js_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=STEALTH_BROWSER_ARGS
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=STEALTH_USER_AGENT,
        )

        page = await context.new_page()

        # 访问 OddsPortal 首页
        logger.info("\n🌐 访问 OddsPortal 首页...")
        try:
            await page.goto("https://www.oddsportal.com/", timeout=60000, wait_until="domcontentloaded")
            logger.info("  ✅ 页面加载成功")

            # 等待 JS 加载
            await asyncio.sleep(5)

        except Exception as e:
            logger.warning(f"  ⚠️  页面加载失败: {e}")
            # 继续尝试

        # 嗅探密钥
        logger.info("\n🔍 开始嗅探 JavaScript 密钥...")
        keys = await sniff_js_keys(page, output_dir)

        await context.close()
        await browser.close()

    # 显示结果
    logger.info("\n" + "=" * 80)
    logger.info("🎯 密钥提取结果")
    logger.info("=" * 80)

    if keys:
        logger.info(f"\n  ✅ 成功提取密钥:")
        logger.info(f"     Password: {keys.get('password', 'N/A')}")
        logger.info(f"     Salt: {keys.get('salt', 'N/A')}")

        # 保存到文件
        keys_file = output_dir / "extracted_keys.json"
        import json
        with open(keys_file, "w") as f:
            json.dump(keys, f, indent=2)
        logger.info(f"\n  💾 密钥已保存到: {keys_file}")

    else:
        logger.error(f"\n  ❌ 未能提取到密钥")
        logger.info(f"\n  💡 可能需要:")
        logger.info(f"     1. 手动访问 https://www.oddsportal.com/")
        logger.info(f"     2. 在开发者工具中查看 Network 标签")
        logger.info(f"     3. 找到 app-*.js 文件并搜索上述模式")

    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
