#!/usr/bin/env python3
"""V41.670 "The Decipher Run" - 提取最新解密密钥与算法对齐.

核心理念：
    OddsPortal 的加密密钥和盐值存储在 JavaScript 资产中。
    通过捕获和分析 JS 文件，提取当前的解密参数。

任务流程：
    1. 访问目标站点，捕获所有加载的 .js 文件
    2. 下载 JS 内容，进行密码指纹搜索
    3. 提取新密码和盐值
    4. 更新解密器并验证

Usage:
    python scripts/ops/v41_670_decipher_run.py
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any
import base64

import click
from playwright.async_api import async_playwright, Page, Browser
import requests

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration & Constants
# ============================================================================

# 旧密码指纹（用于搜索附近的新密码）
OLD_SALT_FINGERPRINT = "orieC_jQQWRmhkPvR6u2kzXeTube6aYupiOddsPortal"
OLD_PASSWORD_FINGERPRINT = "%RtR8AB&\\nWsh=AQC+v!=pgAe@dSQG3kQ"

# 加密库特征词
CRYPTO_KEYWORDS = [
    "CryptoJS",
    "AES",
    "enc.Base64",
    "Pbkdf2",
    "pbkdf2",
    "decrypt",
    "encrypt",
    "cipher",
    "iv",
    "salt",
    "password",
]

# OddsPortal 基础 URL
ODDSPORTAL_BASE = "https://www.oddsportal.com"

# ============================================================================
# Core Implementation
# ============================================================================


class JSAssetHunter:
    """V41.670 JS 资产猎人.

    核心功能：
        1. 捕获页面加载的所有 JS 文件
        2. 下载并分析 JS 内容
        3. 搜索密码和盐值指纹
    """

    def __init__(self):
        self.captured_js_urls = []
        self.downloaded_js_content = {}

    async def capture_js_assets(
        self,
        page: Page,
    ) -> list[str]:
        """捕获页面加载的所有 JS 资产.

        Args:
            page: Playwright 页面对象

        Returns:
            JS 文件 URL 列表
        """
        logger.info("[Hunter] 开始捕获 JS 资产...")

        captured_urls = []

        # 设置请求拦截
        async def capture_js(route):
            """拦截 JS 文件请求."""
            request = route.request
            url = request.url

            # 捕获 .js 文件
            if url.endswith(".js") or ".js?" in url:
                # 过滤掉第三方库
                skip_patterns = [
                    "google",
                    "facebook",
                    "doubleclick",
                    "googletagmanager",
                    "gstatic",
                    "cookielaw",
                ]

                if not any(pattern in url.lower() for pattern in skip_patterns):
                    captured_urls.append(url)
                    logger.debug(f"[Hunter] 捕获 JS: {url.split('/')[-1]}")

            await route.continue_()

        await page.route("**/*", capture_js)

        return captured_urls

    async def download_js_content(
        self,
        js_urls: list[str],
    ) -> dict[str, str]:
        """下载 JS 文件内容.

        Args:
            js_urls: JS 文件 URL 列表

        Returns:
            URL 到内容的映射
        """
        logger.info(f"[Hunter] 下载 {len(js_urls)} 个 JS 文件...")

        content_map = {}
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

        # 创建保存目录
        save_dir = Path("logs/js_assets")
        save_dir.mkdir(parents=True, exist_ok=True)

        for url in js_urls:
            try:
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    content = response.text
                    content_map[url] = content

                    # 保存 JS 文件
                    filename = url.split('/')[-1].split('?')[0]
                    if not filename.endswith('.js'):
                        filename += '.js'
                    save_path = save_dir / filename

                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                    logger.debug(f"[Hunter] ✓ 下载成功: {filename} ({len(content)} chars)")
                else:
                    logger.debug(f"[Hunter] ✗ HTTP {response.status_code}: {url}")
            except Exception as e:
                logger.debug(f"[Hunter] ✗ 下载失败: {e}")

        logger.info(f"[Hunter] 成功下载 {len(content_map)} 个 JS 文件，已保存到 {save_dir}")
        return content_map

    def scan_for_crypto_fingerprints(
        self,
        js_content: str,
        url: str,
    ) -> dict[str, Any] | None:
        """扫描 JS 内容中的加密指纹.

        Args:
            js_content: JS 文件内容
            url: JS 文件 URL

        Returns:
            找到的指纹信息
        """
        findings = {
            "url": url,
            "has_crypto_keywords": False,
            "password_candidates": [],
            "salt_candidates": [],
            "crypto_calls": [],
            "base64_candidates": [],
        }

        # 检查加密关键词
        for keyword in CRYPTO_KEYWORDS:
            if keyword in js_content:
                findings["has_crypto_keywords"] = True
                logger.info(f"[Hunter] 找到关键词 '{keyword}': {url.split('/')[-1]}")
                # 找到关键词的位置
                lines = js_content.split('\n')
                for i, line in enumerate(lines):
                    if keyword in line and len(findings["crypto_calls"]) < 5:
                        findings["crypto_calls"].append({
                            "keyword": keyword,
                            "line": i + 1,
                            "snippet": line.strip()[:200],
                        })

        # 搜索旧盐值（可能在新盐值附近）
        if OLD_SALT_FINGERPRINT in js_content:
            logger.info(f"[Hunter] ✓ 找到旧盐值指纹: {url}")
            # 提取附近的字符串
            idx = js_content.find(OLD_SALT_FINGERPRINT)
            context = js_content[max(0, idx - 500):idx + 500]

            # 搜索类似格式的字符串
            # OddsPortal 盐值格式: 长字符串包含 "OddsPortal"
            salt_pattern = re.compile(r'["\']([a-zA-Z0-9_]{30,100}OddsPortal[a-zA-Z0-9_]*)["\']')
            salts = salt_pattern.findall(context)
            findings["salt_candidates"].extend(salts)

        # 搜索所有包含 "OddsPortal" 的字符串
        oddsportal_pattern = re.compile(r'["\']([^"\']{20,150}OddsPortal[^"\']*)["\']')
        oddsportal_strings = oddsportal_pattern.findall(js_content)
        if oddsportal_strings:
            logger.info(f"[Hunter] 找到 {len(oddsportal_strings)} 个包含 'OddsPortal' 的字符串")
            findings["oddsportal_strings"] = oddsportal_strings[:10]

        # 搜索长字符串常量（可能是密码）
        # 密码通常是特殊字符组合的字符串
        password_pattern = re.compile(r'["\']([^\w\s]{15,80})["\']')
        passwords = password_pattern.findall(js_content[:100000])  # 搜索前 100KB
        if passwords:
            logger.info(f"[Hunter] 找到 {len(passwords)} 个可能的密码候选")
            findings["password_candidates"] = passwords[:30]

        # 搜索 Base64 字符串（可能是盐值）
        base64_pattern = re.compile(r'["\']([A-Za-z0-9+/]{40,100}={0,2})["\']')
        base64_strings = base64_pattern.findall(js_content[:100000])
        if base64_strings:
            logger.info(f"[Hunter] 找到 {len(base64_strings)} 个 Base64 字符串")
            findings["base64_candidates"] = base64_strings[:30]

        return findings if findings["has_crypto_keywords"] else None


class DecryptionKeyExtractor:
    """V41.670 解密密钥提取器.

    核心功能：
        1. 从 JS 资产中提取密码和盐值
        2. 验证提取的密钥
        3. 生成更新后的解密器配置
    """

    def __init__(self):
        self.extracted_password = None
        self.extracted_salt = None

    def extract_keys_from_findings(
        self,
        all_findings: list[dict[str, Any]],
    ) -> dict[str, str] | None:
        """从所有发现中提取密码和盐值.

        Args:
            all_findings: 所有扫描发现

        Returns:
            提取的密码和盐值
        """
        logger.info("[Extractor] 分析扫描结果...")

        # 优先级 1: 找到包含 "OddsPortal" 的字符串（盐值）
        for finding in all_findings:
            if finding.get("oddsportal_strings"):
                for candidate in finding["oddsportal_strings"]:
                    if len(candidate) > 40 and "OddsPortal" in candidate:
                        logger.info(f"[Extractor] 盐值候选: {candidate[:50]}...")
                        self.extracted_salt = candidate
                        break
            if self.extracted_salt:
                break

        # 优先级 2: 找到旧盐值的文件
        if not self.extracted_salt:
            for finding in all_findings:
                if finding.get("salt_candidates"):
                    logger.info(f"[Extractor] 找到盐值候选: {finding['url']}")
                    self.extracted_salt = finding["salt_candidates"][0]
                    break

        # 优先级 3: 搜索 Base64 字符串（可能是盐值）
        if not self.extracted_salt:
            for finding in all_findings:
                if finding.get("base64_candidates"):
                    for candidate in finding["base64_candidates"]:
                        if len(candidate) > 40:
                            logger.info(f"[Extractor] 盐值候选: {candidate[:30]}...")
                            self.extracted_salt = candidate
                            break
                if self.extracted_salt:
                    break

        # 搜索密码 - 特殊字符组成的字符串
        for finding in all_findings:
            if finding.get("password_candidates"):
                # 密码通常是特殊字符组合
                for candidate in finding["password_candidates"]:
                    # 密码应该包含多种特殊字符
                    special_count = sum(1 for c in candidate if not c.isalnum())
                    if special_count >= 5:
                        logger.info(f"[Extractor] 密码候选: {candidate[:20]}...")
                        self.extracted_password = candidate
                        break
            if self.extracted_password:
                break

        if self.extracted_password and self.extracted_salt:
            return {
                "password": self.extracted_password,
                "salt": self.extracted_salt,
            }

        return None


async def main():
    """主执行函数."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("=" * 80)
    logger.info("V41.670 'The Decipher Run' - 启动")
    logger.info("=" * 80)

    hunter = JSAssetHunter()
    extractor = DecryptionKeyExtractor()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 创建页面
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )

        page = await context.new_page()

        # Step 1: 访问联赛页面
        logger.info("[Hunter] 访问目标站点...")
        league_url = "https://www.oddsportal.com/football/england/premier-league-2025-2026/"

        # 先设置拦截，再访问页面
        captured_urls_future = asyncio.create_task(hunter.capture_js_assets(page))

        await page.goto(league_url, timeout=60000, wait_until="domcontentloaded")

        # 等待 JS 加载
        await page.wait_for_load_state("networkidle", timeout=30000)

        # 额外等待动态内容
        await asyncio.sleep(5)

        # 获取捕获的 URL
        js_urls = await captured_urls_future

        # 关闭页面
        await context.close()

        logger.info(f"[Hunter] 捕获到 {len(js_urls)} 个 JS 文件")

        # Step 2: 下载 JS 内容
        content_map = await hunter.download_js_content(js_urls)

        # Step 3: 扫描加密指纹
        logger.info("[Hunter] 扫描加密指纹...")

        all_findings = []
        for url, content in content_map.items():
            findings = hunter.scan_for_crypto_fingerprints(content, url)
            if findings:
                all_findings.append(findings)

        logger.info(f"[Hunter] 找到 {len(all_findings)} 个包含加密特征的文件")

        # Step 4: 提取密钥
        keys = extractor.extract_keys_from_findings(all_findings)

        if keys:
            logger.info("")
            logger.info("=" * 80)
            logger.info("🎯 提取成功！")
            logger.info("=" * 80)
            logger.info(f"密码 (前 20 位): {keys['password'][:20]}...")
            logger.info(f"盐值 (前 30 位): {keys['salt'][:30]}...")
            logger.info("=" * 80)
            logger.info("")

            # 保存到文件
            output_dir = Path("config/stealth")
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / "v41_670_extracted_keys.txt"
            with open(output_file, "w") as f:
                f.write(f"# V41.670 提取的解密密钥\n")
                f.write(f"# 提取时间: {asyncio.get_event_loop().time()}\n\n")
                f.write(f"ODDSPORTAL_PASSWORD = {repr(keys['password'])}\n")
                f.write(f"ODDSPORTAL_SALT = {repr(keys['salt'])}\n")

            logger.info(f"✓ 密钥已保存到: {output_file}")
        else:
            logger.warning("")
            logger.warning("=" * 80)
            logger.warning("⚠️ 未能提取到密钥")
            logger.warning("=" * 80)
            logger.warning("建议:")
            logger.warning("  1. 手动检查下载的 JS 文件")
            logger.warning("  2. 使用浏览器开发者工具分析网络请求")
            logger.warning("  3. 检查是否有新的加密方法")
            logger.warning("")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
