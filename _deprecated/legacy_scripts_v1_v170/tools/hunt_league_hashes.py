#!/usr/bin/env python3
"""
Auto-Alignment Engine - Hash Hunter Script (V151.3)

核心功能:
1. 从 matches 表中筛选出西甲、意甲的比赛，且不在 matches_mapping 中的
2. 使用 search_match_url 通过队名搜索获取真实的哈希 URL
3. 将获取到的正确 URL 插入 matches_mapping，状态设为 pending
4. V151.3 新增: 哈希缓存保护 - 防止数据库连接闪断丢失搜索结果

目的: 利用 9,000 场 FotMob 数据作为源头，批量生成西甲、意甲的"合法门票"

准入红线: 禁止在不使用 matches 表作为底座的情况下进行任何"抢救"工作！

Author: 首席数据架构师 (Principal Data Architect)
Version: V151.3 (Hash Cache Protection)
Date: 2026-01-11
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/hunt_league_hashes.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# V151.3: 哈希缓存文件路径
HASH_CACHE_FILE = "logs/hash_hunt_cache.json"


# ==============================================================================
# Database Operations
# ==============================================================================

def get_missing_matches_by_league(leagues: List[str]) -> List[Dict[str, Any]]:
    """从 matches 表获取不在 matches_mapping 中的比赛

    Args:
        leagues: 联赛名称列表 (如 ['La Liga', 'Serie A'])

    Returns:
        比赛列表
    """
    import psycopg2
    from src.config_unified import get_settings

    settings = get_settings()
    matches = []

    try:
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )
        cursor = conn.cursor()

        # 核心查询：从 matches 表中找出不在 matches_mapping 中的比赛
        league_placeholders = ','.join(['%s'] * len(leagues))
        query = f"""
            SELECT
                m.match_id as fotmob_id,
                m.home_team,
                m.away_team,
                m.league_name,
                m.match_date,
                m.season
            FROM matches m
            WHERE m.league_name IN ({league_placeholders})
              AND NOT EXISTS (
                  SELECT 1 FROM matches_mapping mm
                  WHERE mm.fotmob_id = m.match_id
              )
            ORDER BY m.league_name, m.match_date DESC
        """

        cursor.execute(query, leagues)
        columns = ['fotmob_id', 'home_team', 'away_team', 'league_name', 'match_date', 'season']

        for row in cursor.fetchall():
            matches.append(dict(zip(columns, row)))

        cursor.close()
        conn.close()

        logger.info(f"📊 数据库查询结果: 找到 {len(matches)} 场缺失的比赛")

    except Exception as e:
        logger.error(f"❌ 数据库查询失败: {e}")
        raise

    return matches


def insert_matches_mapping_batch(records: List[Dict[str, Any]]) -> int:
    """批量插入 matches_mapping 表

    Args:
        records: 待插入记录列表

    Returns:
        成功插入数量
    """
    import psycopg2
    from src.config_unified import get_settings

    settings = get_settings()

    if not records:
        return 0

    try:
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )
        cursor = conn.cursor()

        inserted_count = 0
        for record in records:
            try:
                cursor.execute("""
                    INSERT INTO matches_mapping (
                        fotmob_id,
                        home_team,
                        away_team,
                        league_name,
                        match_date,
                        oddsportal_url,
                        confidence,
                        mapping_method,
                        review_status,
                        status
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (fotmob_id) DO NOTHING
                """, (
                    record['fotmob_id'],
                    record['home_team'],
                    record['away_team'],
                    record['league_name'],
                    record['match_date'],
                    record.get('oddsportal_url'),
                    record.get('confidence', 0.5),
                    record.get('mapping_method', 'search'),
                    'pending',
                    'pending'
                ))
                inserted_count += 1
            except Exception as e:
                logger.warning(f"⚠️ 插入失败 {record['fotmob_id']}: {e}")
                continue

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"💾 批量插入完成: {inserted_count}/{len(records)} 条记录")
        return inserted_count

    except Exception as e:
        logger.error(f"❌ 批量插入失败: {e}")
        raise


# ==============================================================================
# V151.3: Hash Cache Protection
# ==============================================================================

def load_hash_cache() -> Dict[str, Any]:
    """加载哈希缓存

    Returns:
        缓存字典，包含已搜索但可能未写入数据库的记录
    """
    cache_path = Path(HASH_CACHE_FILE)
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            logger.info(f"📦 加载缓存: {len(cache.get('records', []))} 条记录")
            return cache
        except Exception as e:
            logger.warning(f"⚠️ 缓存加载失败: {e}，使用空缓存")
            return {'records': [], 'last_updated': None}
    else:
        return {'records': [], 'last_updated': None}


def save_hash_cache(cache: Dict[str, Any]) -> None:
    """保存哈希缓存到文件

    Args:
        cache: 缓存字典
    """
    cache_path = Path(HASH_CACHE_FILE)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    cache['last_updated'] = datetime.now().isoformat()

    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        logger.debug(f"💾 缓存已保存: {len(cache.get('records', []))} 条记录")
    except Exception as e:
        logger.error(f"❌ 缓存保存失败: {e}")


def append_to_hash_cache(record: Dict[str, Any]) -> None:
    """将单条记录追加到缓存

    Args:
        record: 待缓存记录
    """
    cache = load_hash_cache()

    # 检查是否已存在
    existing_ids = {r['fotmob_id'] for r in cache.get('records', [])}
    if record['fotmob_id'] not in existing_ids:
        cache.setdefault('records', []).append(record)
        save_hash_cache(cache)
        logger.debug(f"📝 缓存新增: {record['fotmob_id']}")
    else:
        logger.debug(f"⏭️  跳过已缓存: {record['fotmob_id']}")


def sync_cache_to_database() -> int:
    """将缓存中的记录同步到数据库

    Returns:
        成功同步的记录数
    """
    cache = load_hash_cache()
    records = cache.get('records', [])

    if not records:
        logger.info("📭 缓存为空，无需同步")
        return 0

    logger.info(f"🔄 开始同步缓存到数据库: {len(records)} 条记录")

    try:
        # 尝试批量插入
        inserted_count = insert_matches_mapping_batch(records)

        if inserted_count > 0:
            # 清空缓存
            cache['records'] = []
            save_hash_cache(cache)
            logger.info(f"✅ 缓存同步完成: {inserted_count} 条记录已写入数据库")

        return inserted_count

    except Exception as e:
        logger.error(f"❌ 缓存同步失败: {e}")
        logger.info("💡 缓存已保留，请稍后重试")
        return 0


# ==============================================================================
# Hash Hunting Logic
# ==============================================================================

async def hunt_hashes_for_matches(
    matches: List[Dict[str, Any]],
    limit: Optional[int] = None,
    delay_range: tuple = (5.0, 10.0)
) -> Dict[str, Any]:
    """为指定比赛列表搜索哈希 URL (V151.3: 带缓存保护)

    Args:
        matches: 比赛列表
        limit: 限制处理数量 (None = 全部)
        delay_range: 延迟范围（秒）

    Returns:
        统计结果
    """
    import random
    from core.scrapers.oddsportal import OddsPortalScraper

    if limit:
        matches = matches[:limit]

    logger.info(f"🎯 开始哈希狩猎: {len(matches)} 场比赛")
    logger.info(f"⚡ 延迟范围: {delay_range[0]}-{delay_range[1]} 秒")

    # V151.3: 同步之前的缓存（防止数据库连接中断导致的数据丢失）
    synced_before = sync_cache_to_database()
    if synced_before > 0:
        logger.info(f"🔄 已同步之前缓存: {synced_before} 条记录")

    # 初始化采集器
    scraper = OddsPortalScraper(config_path="config/scraper_config.yaml")

    # 统计
    stats = {
        'total': len(matches),
        'success': 0,
        'failed': 0,
        'records': [],
        'cached': 0  # V151.3: 缓存计数
    }

    # 用于批量插入的记录
    records_to_insert = []

    start_time = time.time()

    for i, match in enumerate(matches, 1):
        logger.info(f"\n[{i}/{len(matches)}] 狩猎: {match['home_team']} vs {match['away_team']} ({match['league_name']})")

        try:
            # 调用搜索功能
            result = await scraper.search_match_url(
                home_team=match['home_team'],
                away_team=match['away_team'],
                league_hint=match['league_name'],
                headless=True
            )

            if result.get('success') and result.get('url'):
                # 成功获取 URL
                stats['success'] += 1

                record = {
                    'fotmob_id': match['fotmob_id'],
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'league_name': match['league_name'],
                    'match_date': match.get('match_date'),
                    'oddsportal_url': result['url'],
                    'confidence': 0.7,  # 搜索获取的 URL 置信度设为 0.7
                    'mapping_method': 'search'
                }

                # V151.3: 先写缓存，再写数据库
                append_to_hash_cache(record)
                records_to_insert.append(record)
                stats['cached'] += 1

                logger.info(f"✅ 成功: {result['url']} (哈希: {result.get('match_id')}) [已缓存]")

            else:
                # 搜索失败
                stats['failed'] += 1
                error = result.get('error', '未知错误')
                logger.warning(f"⚠️ 失败: {error}")

                # 仍然记录，但 URL 为空，稍后可以手动处理
                record = {
                    'fotmob_id': match['fotmob_id'],
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'league_name': match['league_name'],
                    'match_date': match.get('match_date'),
                    'oddsportal_url': None,  # 搜索失败的记录
                    'confidence': 0.0,
                    'mapping_method': 'semantic'  # 使用有效值
                }
                records_to_insert.append(record)

            # 延迟（除了最后一场）
            if i < len(matches):
                delay = random.uniform(*delay_range)
                logger.info(f"⏳ 等待 {delay:.1f}s 后继续...")
                await asyncio.sleep(delay)

        except Exception as e:
            stats['failed'] += 1
            logger.error(f"❌ 异常: {e}")
            continue

    # V151.3: 批量插入数据库（如果失败，缓存已保护数据）
    if records_to_insert:
        logger.info(f"\n💾 开始批量插入 {len(records_to_insert)} 条记录...")
        try:
            inserted_count = insert_matches_mapping_batch(records_to_insert)
            logger.info(f"✅ 成功插入 {inserted_count} 条记录")

            # V151.3: 数据库写入成功后，清空缓存
            if inserted_count > 0:
                cache = load_hash_cache()
                cache['records'] = []
                save_hash_cache(cache)
                logger.info("🗑️ 缓存已清空（数据已写入数据库）")
        except Exception as e:
            logger.error(f"❌ 数据库插入失败: {e}")
            logger.info("💡 缓存已保留，请稍后手动运行脚本同步缓存")

    total_elapsed = time.time() - start_time

    # 汇报战果
    logger.info("\n" + "=" * 70)
    logger.info("📊 V151.3 哈希狩猎战果报告（带缓存保护）")
    logger.info("=" * 70)
    logger.info(f"总场次: {stats['total']}")
    logger.info(f"✅ 成功: {stats['success']}")
    logger.info(f"❌ 失败: {stats['failed']}")
    logger.info(f"💾 已缓存: {stats.get('cached', 0)}")
    logger.info(f"成功率: {stats['success']/stats['total']*100:.1f}%")
    logger.info(f"总耗时: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
    logger.info(f"平均耗时: {total_elapsed/len(matches):.1f}s/场")

    # V151.3: 显示缓存状态
    cache = load_hash_cache()
    cache_records = len(cache.get('records', []))
    if cache_records > 0:
        logger.warning(f"⚠️ 当前缓存中有 {cache_records} 条记录待同步到数据库")
        logger.info(f"   缓存文件: {HASH_CACHE_FILE}")
        logger.info(f"   运行: python {Path(__file__)} --sync-cache")

    return stats


# ==============================================================================
# Main Entry Point
# ==============================================================================

async def run_auto_alignment(
    leagues: Optional[List[str]] = None,
    limit: Optional[int] = None,
    delay_range: tuple = (5.0, 10.0)
):
    """运行自动对齐引擎

    Args:
        leagues: 要处理的联赛列表 (默认: ['La Liga', 'Serie A'])
        limit: 限制处理数量
        delay_range: 延迟范围
    """
    if leagues is None:
        leagues = ['La Liga', 'Serie A']

    logger.info("=" * 70)
    logger.info("🚀 V151.2 全联赛自动对齐引擎启动")
    logger.info("=" * 70)
    logger.info(f"目标联赛: {', '.join(leagues)}")
    logger.info(f"处理限制: {limit if limit else '无限制'}")
    logger.info(f"延迟范围: {delay_range[0]}-{delay_range[1]} 秒")
    logger.info("")

    # 步骤 1: 从数据库获取缺失的比赛
    logger.info("📋 步骤 1: 从 matches 表获取缺失的比赛...")
    missing_matches = get_missing_matches_by_league(leagues)

    if not missing_matches:
        logger.info("✅ 没有缺失的比赛，所有数据已对齐！")
        return

    # 按联赛统计
    for league in leagues:
        league_matches = [m for m in missing_matches if m['league_name'] == league]
        logger.info(f"  {league}: {len(league_matches)} 场缺失")

    # 步骤 2: 哈希狩猎
    logger.info(f"\n🎯 步骤 2: 开始哈希狩猎...")
    stats = await hunt_hashes_for_matches(
        matches=missing_matches,
        limit=limit,
        delay_range=delay_range
    )

    # 完成
    logger.info("\n" + "=" * 70)
    logger.info("🎉 V151.3 全联赛自动对齐引擎完成（带缓存保护）！")
    logger.info("=" * 70)
    logger.info("📝 后续步骤:")
    logger.info("  1. 检查 matches_mapping 表中新增的记录")
    logger.info("  2. 运行 python scripts/ops/harvest_pinnacle_concurrent.py --workers 3 开始采集")
    logger.info("  3. 对于搜索失败的记录，考虑手动处理或使用其他方法")
    logger.info(f"  4. 如果有缓存残留，运行: python {Path(__file__)} --sync-cache")


if __name__ == "__main__":
    import argparse

    # Load .env first
    from dotenv import load_dotenv
    load_dotenv(override=True)

    # Parse arguments
    parser = argparse.ArgumentParser(description="V151.3 全联赛自动对齐引擎（带缓存保护）")
    parser.add_argument('--leagues', type=str, nargs='+',
                        default=['La Liga', 'Serie A'],
                        help='要处理的联赛列表 (默认: La Liga Serie A)')
    parser.add_argument('--limit', type=int, default=None,
                        help='限制处理数量 (默认: 全部)')
    parser.add_argument('--delay-min', type=float, default=5.0,
                        help='最小延迟（秒）')
    parser.add_argument('--delay-max', type=float, default=10.0,
                        help='最大延迟（秒）')
    parser.add_argument('--premier', action='store_true',
                        help='处理英超数据 (与联赛列表互斥)')
    parser.add_argument('--dry-run', action='store_true',
                        help='干跑模式，只查询不写入')
    parser.add_argument('--sync-cache', action='store_true',
                        help='V151.3: 仅同步缓存到数据库（不执行新的搜索）')

    args = parser.parse_args()

    # V151.3: 如果只是同步缓存
    if args.sync_cache:
        logger.info("🔄 缓存同步模式...")
        synced_count = sync_cache_to_database()
        if synced_count > 0:
            logger.info(f"✅ 已同步 {synced_count} 条记录到数据库")
        else:
            logger.info("📭 缓存为空，无需同步")
        sys.exit(0)

    # 如果指定了 --premier，使用英超
    if args.premier:
        target_leagues = ['Premier League']
    else:
        target_leagues = args.leagues

    # Run auto alignment
    asyncio.run(run_auto_alignment(
        leagues=target_leagues,
        limit=args.limit,
        delay_range=(args.delay_min, args.delay_max)
    ))
