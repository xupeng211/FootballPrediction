#!/usr/bin/env python3
"""V127.0 Payload 解码实验 - 多算法暴力破解.

Usage:
    python scripts/v127_0_payload_decoder.py
"""

import base64
import gzip
import json
import logging
import re
import sys
import zlib
import brotli
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def try_standard_zlib(data: bytes) -> bytes | None:
    """尝试标准 zlib 解压."""
    try:
        return zlib.decompress(data)
    except Exception:
        return None


def try_deflate_mode(data: bytes) -> bytes | None:
    """尝试 Deflate 模式 (wbits=-15)."""
    try:
        return zlib.decompress(data, wbits=-15)
    except Exception:
        return None


def try_gzip(data: bytes) -> bytes | None:
    """尝试 gzip 解压."""
    try:
        return gzip.decompress(data)
    except Exception:
        return None


def try_brotli(data: bytes) -> bytes | None:
    """尝试 Brotli 解压."""
    try:
        return brotli.decompress(data)
    except Exception:
        return None


def try_auto_zlib(data: bytes) -> bytes | None:
    """尝试自动检测 zlib 格式."""
    try:
        decompressor = zlib.decompressobj(wbits=zlib.MAX_WBITS | 32)
        return decompressor.decompress(data) + decompressor.flush()
    except Exception:
        return None


def extract_match_urls(text: str) -> list[str]:
    """从文本中提取 match URL."""
    pattern = re.compile(r'/match/[a-z0-9\-]+-([a-z0-9]{8})/', re.IGNORECASE)
    urls = []
    for match in pattern.finditer(text):
        urls.append(match.group(0))
    return urls


def main():
    logger.info("=" * 80)
    logger.info("V127.0 Payload 解码实验")
    logger.info("=" * 80)

    # 读取保存的 payload
    debug_file = Path("logs/v126_0_gold_mine_Premier_League_23/24.json")

    if not debug_file.exists():
        logger.error(f"❌ 文件不存在: {debug_file}")
        return

    with open(debug_file, "r") as f:
        data = json.load(f)

    raw_payload = data.get("raw_payload", "")

    if not raw_payload:
        logger.error("❌ Payload 为空")
        return

    logger.info(f"\n📦 Payload 信息:")
    logger.info(f"  原始大小: {len(raw_payload)} 字符")
    logger.info(f"  API URL: {data.get('api_url', '')[:80]}...")

    # 第一步：Base64 解码
    logger.info(f"\n🔓 第一步：Base64 解码...")
    try:
        decoded_bytes = base64.b64decode(raw_payload)
        logger.info(f"  ✅ Base64 解码成功: {len(decoded_bytes)} 字节")
    except Exception as e:
        logger.error(f"  ❌ Base64 解码失败: {e}")
        return

    # 第二步：尝试多种解压算法
    algorithms = [
        ("Standard Zlib", try_standard_zlib),
        ("Deflate Mode (wbits=-15)", try_deflate_mode),
        ("Gzip", try_gzip),
        ("Brotli", try_brotli),
        ("Auto Zlib", try_auto_zlib),
    ]

    logger.info(f"\n🔧 第二步：尝试 {len(algorithms)} 种解压算法...")

    for name, func in algorithms:
        logger.info(f"\n  🧪 尝试: {name}...")
        result = func(decoded_bytes)

        if result:
            logger.info(f"    ✅ 解压成功！大小: {len(result)} 字节")

            # 尝试解码为 UTF-8
            try:
                text = result.decode('utf-8', errors='ignore')
                logger.info(f"    📝 UTF-8 解码成功: {len(text)} 字符")

                # 检查是否包含 /match/ 关键字
                if '/match/' in text.lower():
                    urls = extract_match_urls(text)
                    logger.info(f"    🎉🎉🎉 找到 {len(urls)} 个 match URL！🎉🎉🎉")

                    # 显示前 20 个 URL
                    logger.info(f"\n    📋 提取的 URL（前 20 个）:")
                    for i, url in enumerate(urls[:20], 1):
                        hash_match = re.search(r'([a-z0-9]{8})', url.lower())
                        hash_str = hash_match.group(1) if hash_match else "NO_HASH"
                        logger.info(f"       [{i:2d}] {hash_str} -> {url}")

                    # 保存完整结果
                    output_file = Path("logs/v127_0_decoded_urls.txt")
                    with open(output_file, "w") as f:
                        for url in urls:
                            f.write(f"{url}\n")
                    logger.info(f"\n    💾 保存了 {len(urls)} 个 URL 到: {output_file}")

                    # 提前退出
                    logger.info(f"\n✅✅✅ 算法 [{name}] 成功解锁金矿！✅✅✅")
                    return
                else:
                    logger.info(f"    ⚠️  未找到 /match/ 关键字")

                    # 显示前 200 字符用于调试
                    preview = text[:200]
                    logger.info(f"    📋 内容预览: {preview}")

            except Exception as e:
                logger.info(f"    ⚠️  UTF-8 解码失败: {e}")
        else:
            logger.info(f"    ❌ 解压失败")

    # 如果所有算法都失败
    logger.error(f"\n❌ 所有解压算法都失败了")
    logger.info(f"\n💡 建议：")
    logger.info(f"  1. 检查原始 payload 格式")
    logger.info(f"  2. 尝试 DOM 截胡策略（V127.0 第二阶段）")


if __name__ == "__main__":
    main()
