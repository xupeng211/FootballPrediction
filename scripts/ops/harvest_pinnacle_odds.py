#!/usr/bin/env python3
"""Pinnacle Odds Incremental Harvester - Fast-Fail Edition

核心改进:
- Timeout 从 10s 降至 3s（快进快出）
- 随机滚动行为（增强隐蔽性）
- 等待抖动 20-40s（躲避频率检测）
- 失败记录日志（logs/harvest_pinnacle_failed.json）

Author: 高级反爬虫专家 & 性能优化工程师
Version: V150.53 (标准化为功能导向命名)
Date: 2026-01-11
"""

import asyncio
import json
import logging
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/harvest_pinnacle.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def fetch_harvest_targets(limit: int = 50) -> List[Dict[str, Any]]:
    """从数据库获取收割目标

    Args:
        limit: 获取比赛数量

    Returns:
        比赛列表
    """
    import psycopg2
    from src.config_unified import get_settings

    settings = get_settings()
    targets = []

    try:
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )
        cursor = conn.cursor()

        # V150.53: 获取未采集 l2_raw_json 的比赛（优先级更高）
        cursor.execute("""
            SELECT
                id,
                fotmob_id,
                home_team,
                away_team,
                league_name,
                match_date,
                oddsportal_url
            FROM matches_mapping
            WHERE oddsportal_url IS NOT NULL
              AND oddsportal_url != ''
              AND l2_raw_json IS NULL
            ORDER BY confidence DESC, id
            LIMIT %s
        """, (limit,))

        columns = ['id', 'fotmob_id', 'home_team', 'away_team', 'league_name', 'match_date', 'oddsportal_url']

        for row in cursor.fetchall():
            targets.append(dict(zip(columns, row)))

        cursor.close()
        conn.close()

        logger.info(f"🎯 从数据库获取 {len(targets)} 场未采集比赛")

    except Exception as e:
        logger.error(f"❌ 获取收割目标失败: {e}")
        raise

    return targets


def extract_match_id_from_url(url: str) -> str:
    """从 URL 中提取 match_id

    Args:
        url: OddsPortal URL

    Returns:
        match_id (8位短ID)
    """
    # URL 格式: /football/.../.../{match_id}/
    parts = url.rstrip('/').split('/')
    if parts:
        return parts[-1]
    return ""


async def harvest_single_match(scraper, target: Dict[str, Any]) -> Dict[str, Any]:
    """采集单场比赛

    Args:
        scraper: OddsPortalScraper 实例
        target: 比赛信息

    Returns:
        采集结果
    """
    from core.scrapers.oddsportal import fetch_single_match

    match_id = extract_match_id_from_url(target['oddsportal_url'])

    result = await fetch_single_match(
        match_id=match_id,
        home_team=target['home_team'],
        away_team=target['away_team'],
        url=target['oddsportal_url'],  # 传递完整 URL
        headless=True
    )

    return {
        'target_id': target['id'],
        'fotmob_id': target['fotmob_id'],
        'match_id': match_id,
        'success': result['success'],
        'data': result.get('data'),
        'error': result.get('error'),
        'stats': {
            'url': target['oddsportal_url'],
            **result.get('stats', {})
        }
    }


async def save_to_database(results: List[Dict[str, Any]]) -> Dict[str, int]:
    """将采集结果保存到数据库

    V150.53: 新增失败记录日志功能
    """
    import psycopg2
    from src.config_unified import get_settings

    settings = get_settings()
    stats = {'success': 0, 'failed': 0, 'total': len(results)}

    # V150.53: 准备失败记录日志
    failed_matches = []

    try:
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )
        cursor = conn.cursor()

        for result in results:
            try:
                if result['success'] and result.get('data'):
                    # 将数据转为 JSON 存入 l2_raw_json
                    l2_json = json.dumps(result['data'], ensure_ascii=False)

                    cursor.execute("""
                        UPDATE matches_mapping
                        SET l2_raw_json = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (l2_json, result['target_id']))

                    stats['success'] += 1
                else:
                    stats['failed'] += 1
                    logger.warning(f"⚠️ 比赛失败: fotmob_id={result['fotmob_id']}, error={result.get('error')}")

                    # V150.53: 记录失败信息
                    failed_matches.append({
                        'fotmob_id': result['fotmob_id'],
                        'match_id': result.get('match_id'),
                        'url': result.get('stats', {}).get('url', 'N/A'),
                        'error': result.get('error', 'Unknown'),
                        'timestamp': datetime.now().isoformat()
                    })

            except Exception as e:
                logger.error(f"❌ 保存失败: {e}")
                stats['failed'] += 1

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"💾 数据库保存完成: {stats['success']}/{stats['total']}")

    except Exception as e:
        logger.error(f"❌ 数据库操作失败: {e}")
        raise

    # 保存失败记录日志
    if failed_matches:
        failed_log_path = Path('logs/harvest_pinnacle_failed.json')
        failed_log_path.parent.mkdir(parents=True, exist_ok=True)

        # 追加模式保存
        if failed_log_path.exists():
            with open(failed_log_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        else:
            existing = []

        existing.extend(failed_matches)

        with open(failed_log_path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

        logger.info(f"📝 失败记录已保存: {len(failed_matches)} 条 → {failed_log_path}")

    return stats


async def run_incremental_harvest(limit: int = 50, delay_range: tuple = (20.0, 40.0)):
    """运行增量收割

    V150.53: 等待抖动增加到 20-40 秒

    Args:
        limit: 采集比赛数量
        delay_range: 延迟范围（秒）
    """
    logger.info("=" * 70)
    logger.info("V150.53 增量收割启动 - 快进快出版本")
    logger.info("=" * 70)

    # 步骤 1: 获取收割目标
    logger.info("📋 步骤 1: 获取收割目标...")
    targets = await fetch_harvest_targets(limit)
    if not targets:
        logger.error("❌ 没有可用的收割目标")
        return

    # 步骤 2: 初始化采集器
    logger.info("🔧 步骤 2: 初始化采集器...")
    from core.scrapers.oddsportal import OddsPortalScraper
    scraper = OddsPortalScraper(config_path="config/scraper_config.yaml")

    # 显示熔断器状态
    status = scraper.get_circuit_breaker_status()
    logger.info(f"🛡️ 熔断器状态: {status['active_proxies']}/{status['total_proxies']} 代理可用")

    # 步骤 3: 批量采集
    logger.info(f"🚀 步骤 3: 开始采集 {len(targets)} 场比赛...")
    logger.info(f"⚡ V150.53 优化: 3s 超时 + 20-40s 等待抖动")
    results = []
    elapsed_times = []

    start_time = time.time()

    for i, target in enumerate(targets, 1):
        match_start = time.time()
        logger.info(f"\n[{i}/{len(targets)}] 采集: {target['home_team']} vs {target['away_team']}")

        try:
            result = await harvest_single_match(scraper, target)
            results.append(result)

            match_elapsed = time.time() - match_start
            elapsed_times.append(match_elapsed)

            status_icon = "✅" if result['success'] else "❌"
            logger.info(f"{status_icon} 耗时: {match_elapsed:.1f}s")

            # V150.53: 最后一场不需要延迟
            if i < len(targets):
                delay = random.uniform(*delay_range)
                logger.info(f"⏳ 等待 {delay:.1f}s 后继续（抖动: {delay_range[0]}-{delay_range[1]}s）...")
                await asyncio.sleep(delay)

        except Exception as e:
            logger.error(f"❌ 采集异常: {e}")
            elapsed_times.append(0)
            continue

    total_elapsed = time.time() - start_time

    # 步骤 4: 保存到数据库
    logger.info("\n💾 步骤 4: 保存到数据库...")
    save_stats = await save_to_database(results)

    # 步骤 5: 汇报战果
    logger.info("\n" + "=" * 70)
    logger.info("📊 V150.53 采集战果报告")
    logger.info("=" * 70)
    logger.info(f"总场次: {len(targets)}")
    logger.info(f"成功: {save_stats['success']}")
    logger.info(f"失败: {save_stats['failed']}")
    logger.info(f"总耗时: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
    logger.info(f"平均耗时: {sum(elapsed_times)/len(elapsed_times):.1f}s/场")
    logger.info(f"最快: {min(elapsed_times):.1f}s")
    logger.info(f"最慢: {max(elapsed_times):.1f}s")

    # 步骤 6: 展示数据样本
    logger.info("\n" + "=" * 70)
    logger.info("📋 数据样本（前 3 场成功采集的比赛）")
    logger.info("=" * 70)

    sample_count = 0
    for result in results:
        if result['success'] and result.get('data'):
            data = result['data']
            home_odds = data.get('home', [])
            away_odds = data.get('away', [])

            logger.info(f"\n🏟️ {result['fotmob_id']}: {result.get('match_id', 'N/A')}")
            logger.info(f"主队赔率: {len(home_odds)} 条")
            if home_odds:
                logger.info(f"  最新: {home_odds[0].get('beijing_time', 'N/A')} -> {home_odds[0].get('odds', 'N/A')}")
            logger.info(f"客队赔率: {len(away_odds)} 条")
            if away_odds:
                logger.info(f"  最新: {away_odds[0].get('beijing_time', 'N/A')} -> {away_odds[0].get('odds', 'N/A')}")

            sample_count += 1
            if sample_count >= 3:
                break

    # 保存审计日志
    scraper.save_audit_log()
    logger.info("\n✅ V150.53 增量收割完成！")


if __name__ == "__main__":
    # Load .env first
    from dotenv import load_dotenv
    load_dotenv(override=True)

    # Run harvest
    asyncio.run(run_incremental_harvest(limit=50, delay_range=(20.0, 40.0)))
