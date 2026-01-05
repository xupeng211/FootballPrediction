#!/usr/bin/env python3
"""V129.2 AES-CBC 解密引擎 - 击穿 OddsPortal 加密协议.

密钥信息：
- Password: J*8sQ!p$7aD_fR2yW@gHn*3bVp#sAdLd_k
- Salt: 5b9a8f2c3e6d1a4b7c8e9d0f1a2b3c4d

解密流程：
1. PBKDF2 密钥派生 (1000 iterations, SHA-256)
2. AES-CBC 解密
"""

import base64
import json
import logging
import re
import sys
from pathlib import Path

# 密码学库
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# 从 OddsPortal app.js 中提取的密钥
ODDSPORTAL_PASSWORD = "J*8sQ!p$7aD_fR2yW@gHn*3bVp#sAdLd_k"
ODDSPORTAL_SALT = "5b9a8f2c3e6d1a4b7c8e9d0f1a2b3c4d"


async def decrypt_oddsportal_response(encrypted_data: str | bytes) -> str | None:
    """解密 OddsPortal API 响应.

    Args:
        encrypted_data: 加密的数据 (格式: {base64_encrypted_data}:{hex_iv})

    Returns:
        解密后的 JSON 字符串，失败返回 None
    """
    try:
        # 转换为字符串
        if isinstance(encrypted_data, bytes):
            encrypted_str = encrypted_data.decode('utf-8')
        else:
            encrypted_str = encrypted_data

        # 按格式解析: "EncryptedData:IV"
        # 注意：格式是 {大量base64加密数据}:{hex_iv}
        if ':' not in encrypted_str:
            logger.warning("  ⚠️  数据格式不正确（缺少 ':' 分隔符）")
            return None

        encrypted_b64, iv_hex = encrypted_str.rsplit(':', 1)

        # IV 是 hex 字符串，转换为 bytes
        iv = bytes.fromhex(iv_hex)
        # 加密数据是 Base64 编码
        encrypted_bytes = base64.b64decode(encrypted_b64)

        logger.info(f"  📦 IV (hex): {iv_hex}")
        logger.info(f"  📦 IV 长度: {len(iv)} 字节")
        logger.info(f"  📦 加密数据长度: {len(encrypted_bytes)} 字节")

        # 使用 PBKDF2 派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=ODDSPORTAL_SALT.encode('utf-8'),
            iterations=1000,
            backend=default_backend()
        )
        key = kdf.derive(ODDSPORTAL_PASSWORD.encode('utf-8'))
        logger.info(f"  🔑 派生密钥长度: {len(key)} 字节")

        # AES-CBC 解密
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(encrypted_bytes) + decryptor.finalize()

        # 移除 PKCS7 padding
        padding_length = decrypted_padded[-1]
        decrypted = decrypted_padded[:-padding_length]

        # 转换为字符串
        result = decrypted.decode('utf-8')
        logger.info(f"  ✅ 解密成功: {len(result)} 字符")

        return result

    except Exception as e:
        logger.error(f"  ❌ 解密失败: {e}")
        return None


def extract_match_urls_from_json(data: str | dict) -> list[dict]:
    """从 JSON 数据中提取 match 信息.

    Returns:
        比赛信息列表，每项包含: url, home_team, away_team, match_id
    """
    matches = []

    # 如果是字符串，转换为 JSON
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            return matches

    # OddsPortal API 返回格式: {"s": 1, "d": {"total": 380, "rows": [...]}}
    if not isinstance(data, dict) or 'd' not in data:
        return matches

    rows = data['d'].get('rows', [])
    for row in rows:
        if 'encodeEventId' in row:
            match_info = {
                'url': f"https://www.oddsportal.com/match/{row['encodeEventId']}/",
                'match_id': row.get('id'),
                'encode_event_id': row['encodeEventId'],
                'home_team': row.get('home-name'),
                'away_team': row.get('away-name'),
                'status': row.get('event-stage-name'),
                'timestamp': row.get('colClassName', '')  # 包含时间戳信息
            }
            matches.append(match_info)

    return matches


async def main():
    logger.info("=" * 80)
    logger.info("V129.2 AES-CBC 解密引擎")
    logger.info("=" * 80)

    logger.info(f"\n🔑 使用密钥:")
    logger.info(f"  Password: {ODDSPORTAL_PASSWORD}")
    logger.info(f"  Salt: {ODDSPORTAL_SALT}")

    # 读取保存的 payload
    binary_file = Path("logs/v126_0_full_payload_Premier_League_23-24.bin")

    if not binary_file.exists():
        logger.error(f"\n❌ 文件不存在: {binary_file}")
        logger.info(f"\n💡 请先运行 V126.0 捕获数据")
        return

    logger.info(f"\n📦 读取加密 payload: {binary_file}")

    with open(binary_file, "rb") as f:
        encrypted_data = f.read()

    logger.info(f"  文件大小: {len(encrypted_data)} 字节")
    logger.info(f"  前 100 字符: {encrypted_data[:100]}")

    # 尝试解密
    logger.info(f"\n🔓 开始解密...")
    decrypted = await decrypt_oddsportal_response(encrypted_data)

    if not decrypted:
        logger.error(f"\n❌ 解密失败")
        return

    # 检查是否是有效的 JSON
    logger.info(f"\n📋 验证解密结果...")
    if decrypted.startswith('{') or decrypted.startswith('['):
        logger.info(f"  ✅ 检测到 JSON 格式")

        try:
            json_data = json.loads(decrypted)
            logger.info(f"  ✅ JSON 解析成功")
            logger.info(f"  📊 数据类型: {type(json_data)}")
            if isinstance(json_data, dict):
                logger.info(f"  📊 顶层键: {list(json_data.keys())[:20]}")
        except:
            logger.warning(f"  ⚠️  JSON 解析失败，但以 '{{' 开头")
    else:
        logger.warning(f"  ⚠️  不以 JSON 开头")
        logger.info(f"  📝 前 500 字符:")
        logger.info(f"     {decrypted[:500]}")

    # 提取 match URL
    logger.info(f"\n🎯 提取 match URL...")
    matches = extract_match_urls_from_json(decrypted)

    if matches:
        logger.info(f"  ✅ 提取到 {len(matches)} 场比赛信息")

        logger.info(f"\n  📋 提取的比赛（前 20 场）:")
        for i, m in enumerate(matches[:20], 1):
            logger.info(f"     [{i:2d}] {m['home_team']} vs {m['away_team']:20s} -> {m['url']}")

        # 保存完整 URL 列表
        output_file = Path("logs/v129_2_extracted_urls.txt")
        with open(output_file, "w") as f:
            for m in matches:
                f.write(f"{m['url']}\n")
        logger.info(f"\n  💾 保存了 {len(matches)} 个 URL 到: {output_file}")

        # 保存详细信息到 JSON
        detail_file = Path("logs/v129_2_matches_detail.json")
        with open(detail_file, "w") as f:
            json.dump(matches, f, indent=2, ensure_ascii=False)
        logger.info(f"  💾 保存了详细信息到: {detail_file}")

        logger.info(f"\n✅✅✅ 加密协议已彻底击穿！✅✅✅")
        logger.info(f"🎉 成功提取 {len(matches)} 场比赛 URL")
        logger.info(f"\n⚠️  注意: 当前仅第 1 页（{len(matches)}/380 场）")
        logger.info(f"    需要使用 V130.0 获取全部 8 页数据")
    else:
        logger.warning(f"  ⚠️  未提取到比赛 URL")
        logger.info(f"  📝 解密后的数据（前 1000 字符）:")
        logger.info(f"     {decrypted[:1000]}")

    # 保存解密后的数据
    output_file = Path("logs/v129_2_decrypted.json")
    with open(output_file, "w", encoding='utf-8') as f:
        f.write(decrypted)
    logger.info(f"\n  💾 解密数据已保存到: {output_file}")

    logger.info(f"\n" + "=" * 80)
    logger.info(f"🏆 V129.2 执行完成")
    logger.info("=" * 80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
