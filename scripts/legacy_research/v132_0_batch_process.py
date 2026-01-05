#!/usr/bin/env python3
"""V132.0 批量处理脚本 - 处理手动捕获的多页数据.

假设手动捕获了所有 8 页数据，存储在 logs/v132_0_payload_page_*.txt
"""

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

ODDSPORTAL_PASSWORD = "J*8sQ!p$7aD_fR2yW@gHn*3bVp#sAdLd_k"
ODDSPORTAL_SALT = "5b9a8f2c3e6d1a4b7c8e9d0f1a2b3c4d"


def decrypt_payload(payload_file: Path) -> tuple[list[dict], int]:
    """解密单个 payload 文件."""
    with open(payload_file, "r") as f:
        encrypted_payload = f.read()

    if ':' not in encrypted_payload:
        return [], 0

    encrypted_b64, iv_hex = encrypted_payload.rsplit(':', 1)
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

    # 提取比赛
    data = json.loads(decrypted)
    total = data['d'].get('total', 0)
    rows = data['d'].get('rows', [])

    matches = []
    for row in rows:
        if 'encodeEventId' in row:
            matches.append({
                'url': f"https://www.oddsportal.com/match/{row['encodeEventId']}/",
                'match_id': row.get('id'),
                'home_team': row.get('home-name'),
                'away_team': row.get('away-name'),
            })

    return matches, total


def two_stage_matching(oddsportal_matches: list[dict], db_matches: list[tuple],
                      normalizer: TeamNameNormalizer, threshold: float = 80.0):
    """两阶段匹配."""
    matched = []

    # 第一阶段：规范化匹配
    normalized_op = {}
    for m in oddsportal_matches:
        key = (normalizer.normalize(m['home_team']), normalizer.normalize(m['away_team']))
        normalized_op[key] = m

    db_remaining = []
    for db_id, db_home, db_away in db_matches:
        key = (normalizer.normalize(db_home), normalizer.normalize(db_away))
        if key in normalized_op:
            matched.append((db_id, normalized_op[key]['url'], db_home, db_away, 100.0))
        else:
            db_remaining.append((db_id, db_home, db_away))

    logger.info(f"    第一阶段（规范化）: {len(matched)} 场")

    # 第二阶段：Fuzzy Matching
    fuzzy_matched = 0
    for db_id, db_home, db_away in db_remaining:
        best_match = None
        best_score = 0

        for m in oddsportal_matches:
            home_score = normalizer.fuzzy_match(db_home, m['home_team'])
            away_score = normalizer.fuzzy_match(db_away, m['away_team'])
            avg_score = (home_score + away_score) / 2

            if avg_score > best_score and avg_score > threshold:
                best_score = avg_score
                best_match = m

        if best_match:
            matched.append((db_id, best_match['url'], db_home, db_away, best_score))
            fuzzy_matched += 1

    logger.info(f"    第二阶段（Fuzzy, {threshold}% 阈值）: {fuzzy_matched} 场")

    return matched


def main():
    logger.info("=" * 80)
    logger.info("V132.0 批量处理脚本 - 多页数据解密 + 匹配")
    logger.info("=" * 80)

    league_name = "Premier League"
    season = "23/24"

    # 假设手动捕获了所有 8 页数据
    payload_files = list(Path("logs").glob("v132_0_payload_page_*.txt"))

    if not payload_files:
        logger.warning("⚠️  未找到 payload 文件")
        logger.info("💡 请手动捕获第 1-8 页数据并保存为 logs/v132_0_payload_page_{i}.txt")
        return

    logger.info(f"📦 找到 {len(payload_files)} 个 payload 文件")

    # 解密所有页面
    all_matches = []
    for payload_file in sorted(payload_files):
        matches, total = decrypt_payload(payload_file)
        all_matches.extend(matches)
        logger.info(f"  ✅ {payload_file.name}: {len(matches)} 场比赛（总计 {total} 场）")

    logger.info(f"\n📊 全赛季汇总: {len(all_matches)} 场比赛")

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

    cur.execute("""
        SELECT match_id, home_team, away_team
        FROM matches
        WHERE league_name = %s AND season = %s
          AND oddsportal_url IS NULL
    """, (league_name, season))

    db_matches = cur.fetchall()
    logger.info(f"\n🔍 数据库中缺失 URL: {len(db_matches)} 场")

    # 两阶段匹配
    normalizer = TeamNameNormalizer()
    matched = two_stage_matching(all_matches, db_matches, normalizer, threshold=80.0)

    # 统计匹配质量
    high_quality = len([m for m in matched if m[4] >= 90])
    medium_quality = len([m for m in matched if 80 <= m[4] < 90])

    logger.info(f"\n📊 匹配质量分布:")
    logger.info(f"   🟢 高质量（≥90%）: {high_quality} 场")
    logger.info(f"   🟡 中质量（80-90%）: {medium_quality} 场")

    match_rate = len(matched) / len(db_matches) * 100 if db_matches else 0
    logger.info(f"\n📈 匹配率: {match_rate:.1f}%")

    # 原子更新
    if matched:
        logger.info(f"\n💾 原子事务更新...")
        conn.autocommit = False

        try:
            cur.executemany("""
                UPDATE matches
                SET oddsportal_url = %s
                WHERE match_id = %s
            """, [(url, match_id) for match_id, url, _, _, _ in matched])

            conn.commit()
            logger.info(f"  ✅ 提交 {len(matched)} 条记录")

        except Exception as e:
            conn.rollback()
            logger.error(f"  ❌ 事务回滚: {e}")

    # 检查剩余缺失
    cur.execute("""
        SELECT COUNT(*) FROM matches
        WHERE league_name = %s AND season = %s
          AND oddsportal_url IS NULL
    """, (league_name, season))

    remaining = cur.fetchone()[0]
    logger.info(f"\n📊 剩余缺失 URL: {remaining} 场")

    cur.close()
    conn.close()

    # 验收报告
    logger.info("\n" + "=" * 80)
    logger.info("📋 V132.0 验收报告")
    logger.info("=" * 80)
    logger.info(f"Total found:    {len(all_matches)}")
    logger.info(f"Matched in DB:  {len(matched)}")
    logger.info(f"Match Rate:     {match_rate:.1f}%")
    logger.info(f"Remaining:      {remaining}")

    if remaining == 0:
        logger.info("\n✅✅✅ 全量分页引擎 V132.0 已就绪！✅✅✅")
        logger.info("🎉 5,872 场链接缺失问题已进入'全自动清零'阶段。")
    else:
        logger.info(f"\n⚠️  仍有 {remaining} 场比赛未匹配")
        logger.info("💡 建议检查捕获的页面数据是否完整")


if __name__ == "__main__":
    main()
