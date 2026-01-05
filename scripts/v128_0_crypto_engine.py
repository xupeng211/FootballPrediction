#!/usr/bin/env python3
"""V128.0 逆向解密引擎 - 借鉴开源思路重构.

核心策略：
1. 跳过前 2 个字符进行 Base64 解码
2. 尝试多种 zlib 参数（wbits=-15, wbits=15, wbits=31, auto-detect）
3. 提取 match URL 并批量更新数据库

Usage:
    python scripts/v128_0_crypto_engine.py
"""

import base64
import json
import logging
import os
import re
import sys
import zlib
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                  'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(proxy_var, None)

import psycopg2
from thefuzz import fuzz

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.oddsportal.com"


def decode_payload_v1(payload: str) -> bytes | None:
    """V1: 标准 Base64 解码."""
    try:
        return base64.b64decode(payload)
    except Exception:
        return None


def decode_payload_v2(payload: str) -> bytes | None:
    """V2: 跳过前 2 个字符."""
    try:
        return base64.b64decode(payload[2:])
    except Exception:
        return None


def decode_payload_v3(payload: str) -> bytes | None:
    """V3: 跳过前 4 个字符."""
    try:
        return base64.b64decode(payload[4:])
    except Exception:
        return None


def decompress_zlib(data: bytes, wbits: int) -> bytes | None:
    """使用指定 wbits 参数解压."""
    try:
        return zlib.decompress(data, wbits=wbits)
    except Exception:
        return None


def decompress_auto(data: bytes) -> bytes | None:
    """自动检测 zlib 格式."""
    try:
        # 尝试自动检测
        decompressor = zlib.decompressobj(wbits=zlib.MAX_WBITS | 32)
        return decompressor.decompress(data) + decompressor.flush()
    except Exception:
        return None


def extract_match_urls_from_json(data: str | dict) -> list[str]:
    """从 JSON 数据中提取 match URL."""
    urls = []

    # 如果是字符串，转换为 JSON
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            data = {'raw': data}

    # 递归搜索 /match/ URL
    def search_recursive(obj, depth=0):
        if depth > 20:  # 防止无限递归
            return

        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(key, str) and '/match/' in key:
                    # 提取 URL
                    for match in re.finditer(r'/match/[a-z0-9\-]+-([a-z0-9]{8})/', key, re.IGNORECASE):
                        full_url = urljoin(BASE_URL, match.group(0))
                        urls.append(full_url)
                search_recursive(value, depth + 1)

        elif isinstance(obj, list):
            for item in obj:
                search_recursive(item, depth + 1)

        elif isinstance(obj, str):
            # 在字符串中搜索 /match/ URL
            for match in re.finditer(r'/match/[a-z0-9\-]+-([a-z0-9]{8})/', obj, re.IGNORECASE):
                full_url = urljoin(BASE_URL, match.group(0))
                urls.append(full_url)

    search_recursive(data)
    return list(set(urls))  # 去重


def try_all_decoding_strategies(payload: str) -> dict[str, Any] | None:
    """尝试所有解码策略."""
    strategies = [
        ("V1: 标准 Base64", decode_payload_v1),
        ("V2: 跳过 2 字符", decode_payload_v2),
        ("V3: 跳过 4 字符", decode_payload_v3),
    ]

    decompressors = [
        ("Zlib wbits=15 (default)", lambda d: decompress_zlib(d, 15)),
        ("Zlib wbits=-15 (raw)", lambda d: decompress_zlib(d, -15)),
        ("Zlib wbits=31 (gzip)", lambda d: decompress_zlib(d, 31)),
        ("Zlib wbits=47 (auto)", lambda d: decompress_zlib(d, 47)),
        ("Auto detect", decompress_auto),
    ]

    logger.info(f"🔬 尝试 {len(strategies)} 种解码策略 x {len(decompressors)} 种解压算法")

    for decode_name, decode_func in strategies:
        logger.info(f"\n  📝 {decode_name}...")
        decoded = decode_func(payload)

        if decoded is None:
            logger.info(f"     ❌ 解码失败")
            continue

        logger.info(f"     ✅ 解码成功: {len(decoded)} 字节")

        for decomp_name, decomp_func in decompressors:
            logger.info(f"     🧪 {decomp_name}...")
            result = decomp_func(decoded)

            if result:
                logger.info(f"        ✅ 解压成功: {len(result)} 字节")

                # 尝试解析为 UTF-8
                try:
                    text = result.decode('utf-8', errors='ignore')
                    logger.info(f"        📝 UTF-8: {len(text)} 字符")

                    # 检查是否包含 /match/
                    if '/match/' in text:
                        logger.info(f"        🎉 找到 /match/ 关键字!")

                        # 尝试解析为 JSON
                        try:
                            json_data = json.loads(text)
                            logger.info(f"        ✅ JSON 解析成功")
                        except:
                            json_data = text

                        # 提取 URL
                        urls = extract_match_urls_from_json(json_data)
                        if urls:
                            logger.info(f"        ✅✅✅ 提取到 {len(urls)} 个 match URL! ✅✅✅")

                            return {
                                'decode_strategy': decode_name,
                                'decompress_strategy': decomp_name,
                                'urls': urls,
                                'json_data': json_data,
                                'raw_text': text[:1000]  # 保存前 1000 字符用于调试
                            }

                        else:
                            logger.info(f"        ⚠️  未提取到 match URL")

                except Exception as e:
                    logger.info(f"        ⚠️  UTF-8 解码失败: {e}")

    logger.warning(f"❌ 所有策略都失败了")
    return None


def get_pending_matches(conn, league_name: str, season: str) -> list[dict[str, Any]]:
    """获取待处理比赛."""
    possible_seasons = [season]
    if "/" in season:
        parts = season.split("/")
        if len(parts) == 2:
            possible_seasons.append(f"20{parts[0]}-20{parts[1]}")

    season_placeholders = ",".join(["%s"] * len(possible_seasons))
    query = f"""
        SELECT match_id, home_team, away_team, match_date
        FROM matches
        WHERE league_name = %s
          AND (season IN ({season_placeholders}) OR season IS NULL)
          AND oddsportal_url IS NULL
        ORDER BY match_date DESC;
    """

    with conn.cursor() as cur:
        cur.execute(query, [league_name] + possible_seasons)
        rows = cur.fetchall()

    return [
        {"match_id": r[0], "home_team": r[1], "away_team": r[2], "match_date": r[3]}
        for r in rows
    ]


def fuzzy_match_and_update(
    conn,
    extracted_urls: list[str],
    db_matches: list[dict[str, Any]],
    normalizer: TeamNameNormalizer,
) -> int:
    """模糊匹配并更新数据库."""
    updates = []

    # 从 URL 中提取球队信息
    url_data = []
    for url in extracted_urls:
        # 从 URL 中提取球队名
        # 例如: /match/arsenal-chelsea-1a2b3c4d/
        match = re.search(r'/match/([a-z]+)-([a-z]+)-([a-z0-9]{8})/', url, re.IGNORECASE)
        if match:
            url_data.append({
                'url': url,
                'home': match.group(1),
                'away': match.group(2),
                'hash': match.group(3)
            })

    logger.info(f"  📊 从 URL 中解析出 {len(url_data)} 个主客队对")

    for db_match in db_matches:
        match_id = db_match["match_id"]
        home_team = normalizer.normalize(db_match["home_team"])
        away_team = normalizer.normalize(db_match["away_team"])

        best_match = None
        best_score = 0

        for url_info in url_data:
            url_home = normalizer.normalize(url_info['home'])
            url_away = normalizer.normalize(url_info['away'])

            home_sim = fuzz.partial_ratio(home_team, url_home)
            away_sim = fuzz.partial_ratio(away_team, url_away)

            if home_sim >= 65 and away_sim >= 65:
                avg_score = (home_sim + away_sim) / 2
                if avg_score > best_score:
                    best_score = avg_score
                    best_match = url_info

        if best_match:
            updates.append((match_id, best_match['url']))

    # 批量更新
    if updates:
        update_query = """
            UPDATE matches
            SET oddsportal_url = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE match_id = %s;
        """

        with conn.cursor() as cur:
            for match_id, url in updates:
                try:
                    cur.execute(update_query, (url, match_id))
                except Exception as e:
                    logger.error(f"    ❌ 更新失败 {match_id}: {e}")

            conn.commit()

    return len(updates)


def main():
    logger.info("=" * 80)
    logger.info("V128.0 逆向解密引擎 - 借鉴开源思路")
    logger.info("=" * 80)

    # 读取保存的 payload
    debug_file = Path("logs/v126_0_gold_mine_Premier_League_23/24.json")

    # V128.2: 优先读取二进制文件
    binary_file = Path("logs/v126_0_full_payload_Premier_League_23-24.bin")

    if binary_file.exists():
        logger.info(f"\n📦 从二进制文件读取完整 payload...")
        import base64
        with open(binary_file, "rb") as f:
            decoded_bytes = f.read()
        # V128.2: 二进制文件已经是解码后的数据，直接传递给解密引擎
        # 需要重新编码为 Base64 以保持与原始 API 响应一致
        raw_payload = base64.b64encode(decoded_bytes).decode('utf-8')
        logger.info(f"  ✅ 读取成功: {len(raw_payload)} 字符 (Base64)")
        logger.info(f"  📦 解码后大小: {len(decoded_bytes)} 字节")
        logger.info(f"  📋 Payload 前缀: {raw_payload[:100]}...")
    elif debug_file.exists():
        logger.info(f"\n📦 从 JSON 文件读取 payload...")
        with open(debug_file, "r") as f:
            data = json.load(f)
        raw_payload = data.get("raw_payload_preview", "")
        logger.warning(f"  ⚠️  使用预览数据（可能不完整）")
    else:
        logger.error(f"❌ 文件不存在: {debug_file}")
        logger.info(f"\n💡 请先运行 V126.0 捕获金矿数据")
        return

    if not raw_payload:
        logger.error("❌ Payload 为空")
        return

    logger.info(f"\n📦 Payload 信息:")
    logger.info(f"  原始大小: {len(raw_payload)} 字符")

    # V128.0 Phase 1: 尝试所有解码策略
    logger.info(f"\n" + "=" * 80)
    logger.info("Phase 1: 逆向解密逻辑复刻")
    logger.info("=" * 80)

    result = try_all_decoding_strategies(raw_payload)

    if not result:
        logger.error(f"\n❌ 解密失败")
        logger.info(f"\n💡 可能原因:")
        logger.info(f"  1. Payload 被截断了（只有 10,000 字符，完整是 964,796 字节）")
        logger.info(f"  2. 需要特殊的解密密钥")
        logger.info(f"  3. 编码格式不是标准的 Base64 + Zlib")
        return

    # 成功解密！
    logger.info(f"\n✅ 解密成功！")
    logger.info(f"  解码策略: {result['decode_strategy']}")
    logger.info(f"  解压策略: {result['decompress_strategy']}")
    logger.info(f"  提取 URL: {len(result['urls'])} 个")

    # 显示前 20 个 URL
    logger.info(f"\n  📋 提取的 URL（前 20 个）:")
    for i, url in enumerate(result['urls'][:20], 1):
        hash_match = re.search(r'([a-z0-9]{8})', url.lower())
        hash_str = hash_match.group(1) if hash_match else "NO_HASH"
        logger.info(f"     [{i:2d}] {hash_str} -> {url}")

    # 保存完整 URL 列表
    output_file = Path("logs/v128_0_extracted_urls.txt")
    with open(output_file, "w") as f:
        for url in result['urls']:
            f.write(f"{url}\n")
    logger.info(f"\n  💾 保存了 {len(result['urls'])} 个 URL 到: {output_file}")

    # V128.0 Phase 3: 全量映射补全
    logger.info(f"\n" + "=" * 80)
    logger.info("Phase 3: 全量映射补全")
    logger.info("=" * 80)

    # 连接数据库
    settings = get_settings()
    normalizer = TeamNameNormalizer()

    logger.info(f"\n📡 连接数据库...")
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )

    # 获取待处理比赛
    league = "Premier League"
    season = "23/24"
    db_matches = get_pending_matches(conn, league, season)
    logger.info(f"  ✅ 找到 {len(db_matches)} 个待处理比赛")

    # 模糊匹配并更新
    logger.info(f"\n🔄 模糊匹配并更新数据库...")
    updated = fuzzy_match_and_update(
        conn,
        result['urls'],
        db_matches,
        normalizer
    )

    logger.info(f"\n✅ 更新了 {updated} 个比赛 URL")

    # 检查更新后的状态
    query = """
        SELECT COUNT(*) as total, COUNT(oddsportal_url) as has_url
        FROM matches m
        WHERE m.league_name = %s
          AND (m.season = %s OR (m.season IS NULL AND '%s' = %s))
    """

    with conn.cursor() as cur:
        cur.execute(query, (league, season, season, season))
        row = cur.fetchone()

    logger.info(f"\n📊 数据库状态:")
    logger.info(f"  总比赛数: {row[0]}")
    logger.info(f"  有 URL 数: {row[1]}")
    logger.info(f"  缺失 URL 数: {row[0] - row[1]}")

    conn.close()

    logger.info(f"\n" + "=" * 80)
    logger.info("V128.0 执行完成")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
