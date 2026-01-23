#!/usr/bin/env python3
"""V41.680 Master Key Integration - OddsPortal 解密模块.

基于 V41.670 "The Decipher Run" 提取的最新密钥:
    从 app-OS_SrwcY.js 逆向工程提取

核心机制:
    1. AES-256-CBC 加密
    2. PBKDF2 密钥派生 (SHA256, 1000 迭代)
    3. Base64 编码传输

Usage:
    >>> from src.core.oddsportal_decryptor import OddsPortalDecryptor
    >>> decryptor = OddsPortalDecryptor()
    >>> json_data = decryptor.decrypt_feed(b64_data)
"""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration (V41.670 "The Decipher Run" 提取)
# ============================================================================

# V41.670 从 app-OS_SrwcY.js 逆向工程提取的最新密钥
# 提取时间: 2026-01-22
# 来源: V41.670 密钥猎手脚本分析
ODDSPORTAL_PASSWORD = b"1354255sbicjR!p$7aD_commongHn*3brawLd_k"
ODDSPORTAL_SALT = b"5b9adecrypt3e6ddata7c8e9d0f180091rjhVYpmap"

# 备用密钥（条件使用）
ODDSPORTAL_FALLBACK_PASSWORD = b"AES-CBC"
ODDSPORTAL_FALLBACK_SALT = b"1a4b"

# 加密参数
PBKDF2_ITERATIONS = 1000
AES_KEY_LENGTH = 32  # 256 bits


# ============================================================================
# Main Implementation
# ============================================================================


class OddsPortalDecryptor:
    """OddsPortal 解密器 - 处理加密的 .dat 文件.

    解密流程:
        1. Base64 解码响应数据
        2. 分离加密数据和密钥
        3. 使用 PBKDF2 派生 AES 密钥
        4. AES-CBC 解密
        5. 解析 JSON
    """

    def __init__(
        self,
        password: bytes | None = None,
        salt: bytes | None = None,
    ):
        """初始化解密器.

        Args:
            password: 解密密码（如果为 None，使用默认值）
            salt: 解密盐值（如果为 None，使用默认值）
        """
        self.password = password or ODDSPORTAL_PASSWORD
        self.salt = salt or ODDSPORTAL_SALT

    def decrypt_feed(self, encoded_data: str) -> dict[str, Any] | None:
        """解密 OddsPortal feed 数据.

        Args:
            encoded_data: Base64 编码的加密数据

        Returns:
            解密后的 JSON 数据，如果解密失败则返回 None
        """
        try:
            # Step 1: Base64 解码
            decoded_data = base64.b64decode(encoded_data).decode()

            # Step 2: 分离加密数据和密钥
            # 格式: "encrypted:key"
            if ":" not in decoded_data:
                logger.error(f"[Decryptor] 数据格式错误，缺少冒号分隔符")
                return None

            encrypted_part, key_part = decoded_data.split(":", 1)

            # Step 3: 解码加密数据和密钥
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_part)
            key_bytes = bytes.fromhex(key_part)

            # Step 4: 派生 AES 密钥
            aes_key = self._derive_aes_key()

            # Step 5: 解密数据
            decrypted_bytes = self._decrypt_aes_cbc(
                encrypted_bytes,
                aes_key,
                key_bytes,
            )

            # Step 6: 转换为字符串并解析 JSON
            decrypted_text = decrypted_bytes.decode("utf-8")

            # Step 7: 修剪到有效的 JSON 结尾
            end_of_json = decrypted_text.rfind("}")
            if end_of_json != -1:
                decrypted_text = decrypted_text[: end_of_json + 1]

            # Step 8: 解析 JSON
            json_data = json.loads(decrypted_text)

            logger.debug(f"[Decryptor] 解密成功: {len(json_data)} 个字段")
            return json_data

        except Exception as e:
            logger.error(f"[Decryptor] 解密失败: {e}")
            return None

    def _derive_aes_key(self) -> bytes:
        """使用 PBKDF2 派生 AES 密钥.

        Returns:
            256 位 AES 密钥
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=AES_KEY_LENGTH,
            salt=self.salt,
            iterations=PBKDF2_ITERATIONS,
            backend=default_backend(),
        )
        return kdf.derive(self.password)

    def _decrypt_aes_cbc(
        self,
        encrypted_data: bytes,
        aes_key: bytes,
        iv: bytes,
    ) -> bytes:
        """使用 AES-CBC 解密数据.

        Args:
            encrypted_data: 加密的数据
            aes_key: AES 密钥
            iv: 初始化向量 (IV)

        Returns:
            解密后的数据
        """
        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.CBC(iv),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_data) + decryptor.finalize()


# ============================================================================
# Feed URL Extractor
# ============================================================================


class FeedURLExtractor:
    """从页面中提取 OddsPortal feed URL.

    核心思路:
        不再扫描 <a> 标签，而是搜索 <script> 中的 feed URL 模式
    """

    # Feed URL 正则模式
    # 匹配: /feed/match-event/{version_id}-{sport_id}-{unique_id}-1-2-{xhash}.dat
    FEED_URL_PATTERN = re.compile(
        r'/feed/match-event/\d+-\d+-([a-zA-Z0-9]+)-1-2-([a-zA-Z0-9]+)\.dat'
    )

    def extract_from_script_content(self, html_content: str) -> list[str]:
        """从 HTML 的 script 内容中提取 feed URL.

        Args:
            html_content: 页面 HTML 内容

        Returns:
            找到的 feed URL 列表
        """
        # 提取所有 <script> 标签内容
        script_pattern = re.compile(r'<script[^>]*>(.*?)</script>', re.DOTALL)
        scripts = script_pattern.findall(html_content)

        feed_urls = []

        for script in scripts:
            # 搜索 feed URL 模式
            matches = self.FEED_URL_PATTERN.findall(script)
            for match in matches:
                unique_id, xhash = match
                # 构造完整的 feed URL
                feed_url = f"/feed/match-event/1-1-{unique_id}-1-2-{xhash}.dat"
                feed_urls.append(feed_url)

        logger.info(f"[FeedExtractor] 从 script 中找到 {len(feed_urls)} 个 feed URL")
        return feed_urls

    def extract_unique_id_from_url(self, feed_url: str) -> str | None:
        """从 feed URL 中提取 unique_id (即 8 位哈希).

        Args:
            feed_url: Feed URL

        Returns:
            unique_id (8 位哈希码)
        """
        match = self.FEED_URL_PATTERN.search(feed_url)
        if match:
            return match.group(1)  # unique_id
        return None


# ============================================================================
# Convenience Functions
# ============================================================================


def decrypt_oddsportal_feed(encoded_data: str) -> dict[str, Any] | None:
    """便捷函数：解密 OddsPortal feed 数据.

    Args:
        encoded_data: Base64 编码的加密数据

    Returns:
        解密后的 JSON 数据

    Example:
        >>> data = "NFBSamc0SmVBREJnQVgwMm9Ld0IwMll1..."
        >>> json_data = decrypt_oddsportal_feed(data)
        >>> print(json_data)
    """
    decryptor = OddsPortalDecryptor()
    return decryptor.decrypt_feed(encoded_data)


def extract_feed_urls_from_page(html_content: str) -> list[str]:
    """便捷函数：从页面中提取 feed URL.

    Args:
        html_content: 页面 HTML 内容

    Returns:
        找到的 feed URL 列表
    """
    extractor = FeedURLExtractor()
    return extractor.extract_from_script_content(html_content)


# ============================================================================
# Export
# ============================================================================

__all__ = [
    "OddsPortalDecryptor",
    "FeedURLExtractor",
    "decrypt_oddsportal_feed",
    "extract_feed_urls_from_page",
]
