#!/usr/bin/env python3
"""V130.0 演示 - 使用已捕获的 payload 展示完整流程."""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer

# V129.2 Decryption
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# V129.2 AES Keys
ODDSPORTAL_PASSWORD = "J*8sQ!p$7aD_fR2yW@gHn*3bVp#sAdLd_k"
ODDSPORTAL_SALT = "5b9a8f2c3e6d1a4b7c8e9d0f1a2b3c4d"


def decrypt_oddsportal_response(encrypted_data: str) -> str | None:
    """V129.2 AES-CBC 解密."""
    try:
        if ':' not in encrypted_data:
            return None

        encrypted_b64, iv_hex = encrypted_data.rsplit(':', 1)
        iv = bytes.fromhex(iv_hex)
        encrypted_bytes = base64.b64decode(encrypted_b64)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=ODDSPORTAL_SALT.encode('utf-8'),
            iterations=1000,
            backend=default_backend()
        )
        key = kdf.derive(ODDSPORTAL_PASSWORD.encode('utf-8'))

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(encrypted_bytes) + decryptor.finalize()

        padding_length = decrypted_padded[-1]
        decrypted = decrypted_padded[:-padding_length]

        return decrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"  ❌ 解密失败: {e}")
        return None


def extract_match_info_from_json(data: str) -> list[dict]:
    """从解密后的 JSON 中提取比赛信息."""
    matches = []
    try:
        data = json.loads(data)
    except:
        return matches

    if not isinstance(data, dict) or 'd' not in data:
        return matches

    rows = data['d'].get('rows', [])
    for row in rows:
        if 'encodeEventId' in row:
            matches.append({
                'url': f"https://www.oddsportal.com/match/{row['encodeEventId']}/",
                'match_id': row.get('id'),
                'encode_event_id': row['encodeEventId'],
                'home_team': row.get('home-name'),
                'away_team': row.get('away-name'),
            })
    return matches


def main():
    logger.info("=" * 80)
    logger.info("V130.0 演示 - 解密 + Fuzzy Matching + 批量更新")
    logger.info("=" * 80)

    # 读取已捕获的 payload
    payload_file = Path("logs/v126_0_decompressed_payload.txt")
    if not payload_file.exists():
        logger.error(f"❌ 文件不存在: {payload_file}")
        logger.info("💡 请先运行 V126.0 捕获数据")
        return

    logger.info(f"📦 读取加密 payload: {payload_file}")
    with open(payload_file, "r") as f:
        encrypted_payload = f.read()

    logger.info(f"  文件大小: {len(encrypted_payload)} 字节")

    # 解密
    logger.info("\n🔓 开始解密...")
    decrypted = decrypt_oddsportal_response(encrypted_payload)

    if not decrypted:
        logger.error("❌ 解密失败")
        return

    logger.info("✅ 解密成功!")

    # 提取比赛
    matches = extract_match_info_from_json(decrypted)
    logger.info(f"\n📊 提取到 {len(matches)} 场比赛")

    if not matches:
        logger.warning("⚠️  未提取到比赛数据")
        return

    logger.info("\n🎯 前 20 场比赛:")
    for i, m in enumerate(matches[:20], 1):
        logger.info(f"  [{i:2d}] {m['home_team']} vs {m['away_team']:20s} -> {m['url']}")

    # 查询数据库中缺失 URL 的比赛
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    cur = conn.cursor()

    league_name = "Premier League"
    season = "23/24"

    cur.execute("""
        SELECT match_id, home_team, away_team
        FROM matches
        WHERE league_name = %s AND season = %s
          AND oddsportal_url IS NULL
    """, (league_name, season))

    db_matches = cur.fetchall()
    logger.info(f"\n🔍 数据库中缺失 URL 的比赛: {len(db_matches)} 场")

    # Fuzzy matching
    normalizer = TeamNameNormalizer()
    update_data = []

    for db_id, db_home, db_away in db_matches:
        best_match = None
        best_score = 0

        for m in matches:
            home_score = normalizer.fuzzy_match(db_home, m['home_team'])
            away_score = normalizer.fuzzy_match(db_away, m['away_team'])
            avg_score = (home_score + away_score) / 2

            if avg_score > best_score and avg_score > 75:
                best_score = avg_score
                best_match = m

        if best_match:
            update_data.append((db_id, best_match['url'], db_home, db_away, best_score))

    # 显示匹配结果
    logger.info(f"\n🎉 成功匹配 {len(update_data)} 场比赛:")
    for i, (db_id, url, home, away, score) in enumerate(update_data[:20], 1):
        logger.info(f"  [{i:2d}] {home:20s} vs {away:20s} -> {url} (分数: {score:.1f})")

    # 批量更新
    if update_data:
        logger.info(f"\n💾 批量更新数据库...")
        cur.executemany("""
            UPDATE matches
            SET oddsportal_url = %s
            WHERE match_id = %s
        """, [(url, match_id) for match_id, url, _, _, _ in update_data])

        conn.commit()
        logger.info(f"  ✅ 更新了 {len(update_data)} 条记录")

    cur.close()
    conn.close()

    logger.info(f"\n✅✅✅ 加密协议已彻底击穿！✅✅✅")
    logger.info(f"🎉 成功匹配并更新 {len(update_data)} 条记录到数据库")
    logger.info(f"\n" + "=" * 80)
    logger.info(f"🏆 V130.0 演示完成")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
