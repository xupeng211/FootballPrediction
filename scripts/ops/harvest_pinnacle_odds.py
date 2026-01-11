#!/usr/bin/env python3
"""
Pinnacle Odds Incremental Harvester - V151.1 (Retry + Hash Hunting)

核心改进:
- 抓一场存一场 (增量入库，保护代理成本)
- 严格数据质量判定 (残缺数据标记为malformed)
- 代理强制轮换 (每场比赛前随机选择)
- 预计完成时间倒计时显示
- 断点续传保护
- V151.1: Malformed 重试机制 (1小时后可重新采集)
- V151.1: 哈希搜索模式 (通过搜索获取真实URL)

Author: 高级后端架构师 (Staff Engineer)
Version: V151.1 (Retry + Hash Hunting Edition)
Date: 2026-01-11
"""

import asyncio
import json
import logging
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

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

        # V151.1: 获取未采集 l2_raw_json 的比赛 + 可重试的 malformed 记录
        # 允许重新采集 1 小时前的 malformed 记录（给因超时变"残废"的记录改过自新的机会）
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
              AND (
                  -- 未采集的比赛
                  l2_raw_json IS NULL
                  OR
                  -- 可重试的 malformed 记录（1小时前，给因超时变"残废"的记录一次改过自新的机会）
                  (status = 'malformed' AND updated_at < NOW() - INTERVAL '1 hour')
              )
            ORDER BY
                CASE WHEN status = 'malformed' THEN 0 ELSE 1 END,  -- 优先重试 malformed
                confidence DESC, id
            LIMIT %s
        """, (limit,))

        columns = ['id', 'fotmob_id', 'home_team', 'away_team', 'league_name', 'match_date', 'oddsportal_url']

        for row in cursor.fetchall():
            targets.append(dict(zip(columns, row)))

        cursor.close()
        conn.close()

        retry_count = sum(1 for t in targets if t.get('status') == 'malformed')
        logger.info(f"🎯 从数据库获取 {len(targets)} 场比赛 (含 {retry_count} 场可重试 malformed)")

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


def validate_data_quality(data: Dict[str, Any]) -> tuple[bool, str]:
    """严格验证数据质量

    V151.0: 任意核心赔率字段为空，则视为残缺数据

    Args:
        data: 采集数据

    Returns:
        (is_valid, error_message)
    """
    if not data:
        return False, "数据为空"

    # 检查核心赔率字段
    has_home = 'home' in data and data['home']
    has_draw = 'draw' in data and data['draw']
    has_away = 'away' in data and data['away']

    missing_fields = []
    if not has_home:
        missing_fields.append('home')
    if not has_draw:
        missing_fields.append('draw')
    if not has_away:
        missing_fields.append('away')

    if missing_fields:
        return False, f"残缺数据: 缺少 {', '.join(missing_fields)}"

    return True, ""


async def save_single_match_to_database(
    target_id: int,
    fotmob_id: str,
    data: Optional[Dict[str, Any]],
    error: Optional[str],
    is_malformed: bool = False
) -> Dict[str, int]:
    """立即保存单场比赛到数据库（V151.0 增量入库）

    Args:
        target_id: 目标ID
        fotmob_id: FotMob比赛ID
        data: 采集数据
        error: 错误信息
        is_malformed: 是否为残缺数据

    Returns:
        保存统计
    """
    import psycopg2
    from src.config_unified import get_settings

    settings = get_settings()

    try:
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )
        cursor = conn.cursor()

        if data and not is_malformed:
            # 完整数据 - 正常保存
            l2_json = json.dumps(data, ensure_ascii=False)

            cursor.execute("""
                UPDATE matches_mapping
                SET l2_raw_json = %s,
                    status = 'harvested',
                    is_malformed = FALSE,
                    updated_at = NOW()
                WHERE id = %s
            """, (l2_json, target_id))

            logger.info(f"💾 数据已入库: {fotmob_id} (完整数据)")
            stats = {'success': 1, 'failed': 0, 'malformed': 0}

        elif is_malformed:
            # 残缺数据 - 标记为 malformed
            l2_json = json.dumps(data, ensure_ascii=False) if data else None

            cursor.execute("""
                UPDATE matches_mapping
                SET l2_raw_json = %s,
                    status = 'malformed',
                    is_malformed = TRUE,
                    updated_at = NOW()
                WHERE id = %s
            """, (l2_json, target_id))

            logger.warning(f"⚠️ 残缺数据已入库: {fotmob_id} (标记为malformed)")
            stats = {'success': 0, 'failed': 0, 'malformed': 1}

        else:
            # 采集失败 - 不更新数据，只更新时间戳
            cursor.execute("""
                UPDATE matches_mapping
                SET updated_at = NOW()
                WHERE id = %s
            """, (target_id,))

            logger.error(f"❌ 采集失败: {fotmob_id} - {error}")
            stats = {'success': 0, 'failed': 1, 'malformed': 0}

        conn.commit()
        cursor.close()
        conn.close()

        return stats

    except Exception as e:
        logger.error(f"❌ 数据库保存异常: {e}")
        # 记录到失败日志
        failed_log_path = Path('logs/harvest_pinnacle_failed.json')
        failed_log_path.parent.mkdir(parents=True, exist_ok=True)

        failed_record = {
            'fotmob_id': fotmob_id,
            'target_id': target_id,
            'error': str(e),
            'is_malformed': is_malformed,
            'timestamp': datetime.now().isoformat()
        }

        if failed_log_path.exists():
            with open(failed_log_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        else:
            existing = []

        existing.append(failed_record)

        with open(failed_log_path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

        return {'success': 0, 'failed': 1, 'malformed': 0}


async def harvest_single_match_with_proxy_rotation(
    scraper,
    target: Dict[str, Any],
    match_index: int,
    total_matches: int
) -> Dict[str, Any]:
    """采集单场比赛（V151.0: 代理强制轮换）

    Args:
        scraper: OddsPortalScraper 实例
        target: 比赛信息
        match_index: 当前比赛索引
        total_matches: 总比赛数

    Returns:
        采集结果
    """
    from core.scrapers.oddsportal import fetch_single_match

    match_id = extract_match_id_from_url(target['oddsportal_url'])

    # V151.0: 每场比赛前强制轮换代理（分散压力）
    scraper.rotate_proxy() if hasattr(scraper, 'rotate_proxy') else None

    logger.info(f"\n[{match_index}/{total_matches}] 采集: {target['home_team']} vs {target['away_team']}")
    logger.info(f"🔄 代理轮换: 每场比赛前随机选择")

    result = await fetch_single_match(
        match_id=match_id,
        home_team=target['home_team'],
        away_team=target['away_team'],
        url=target['oddsportal_url'],
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


def calculate_estimated_finish_time(
    completed: int,
    total: int,
    avg_time_seconds: float,
    start_time: float
) -> str:
    """计算预计完成时间

    Args:
        completed: 已完成数量
        total: 总数量
        avg_time_seconds: 平均每场耗时
        start_time: 开始时间

    Returns:
        预计完成时间字符串
    """
    if completed == 0:
        return "计算中..."

    remaining = total - completed
    estimated_seconds = remaining * avg_time_seconds
    finish_time = datetime.now() + timedelta(seconds=estimated_seconds)

    # 格式化输出
    hours = int(estimated_seconds // 3600)
    minutes = int((estimated_seconds % 3600) // 60)

    return f"{finish_time.strftime('%Y-%m-%d %H:%M:%S')} (约 {hours}h {minutes}min 后)"


async def run_incremental_harvest_persistence(
    limit: int = 50,
    delay_range: tuple = (20.0, 40.0)
):
    """运行增量收割（V151.0: 抓一场存一场）

    Args:
        limit: 采集比赛数量
        delay_range: 延迟范围（秒）
    """
    logger.info("=" * 70)
    logger.info("V151.0 增量收割启动 - 抓一场存一场模式")
    logger.info("=" * 70)

    # 统计变量
    stats = {'success': 0, 'failed': 0, 'malformed': 0}
    elapsed_times = []

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

    # 步骤 3: 增量采集（抓一场存一场）
    logger.info(f"🚀 步骤 3: 开始增量采集 {len(targets)} 场比赛...")
    logger.info(f"⚡ V151.0 模式: 抓一场存一场 + 代理轮换 + 数据质量校验")
    logger.info("")

    start_time = time.time()

    for i, target in enumerate(targets, 1):
        match_start = time.time()

        try:
            # V151.0: 采集单场（带代理轮换）
            result = await harvest_single_match_with_proxy_rotation(
                scraper,
                target,
                i,
                len(targets)
            )

            match_elapsed = time.time() - match_start
            elapsed_times.append(match_elapsed)

            # V151.0: 严格数据质量判定
            is_valid, error_msg = validate_data_quality(result.get('data'))
            is_malformed = not is_valid

            if result['success'] and is_malformed:
                logger.warning(f"⚠️ 数据质量检查失败: {error_msg}")

            # V151.0: 立即保存到数据库（增量入库）
            save_stats = await save_single_match_to_database(
                target_id=result['target_id'],
                fotmob_id=result['fotmob_id'],
                data=result.get('data'),
                error=result.get('error'),
                is_malformed=is_malformed
            )

            # 更新统计
            stats['success'] += save_stats['success']
            stats['failed'] += save_stats['failed']
            stats['malformed'] += save_stats['malformed']

            # 状态图标
            if result['success'] and not is_malformed:
                status_icon = "✅"
            elif result['success'] and is_malformed:
                status_icon = "⚠️"
            else:
                status_icon = "❌"

            logger.info(f"{status_icon} 耗时: {match_elapsed:.1f}s")

            # V151.0: 预计完成时间倒计时
            if elapsed_times:
                avg_time = sum(elapsed_times) / len(elapsed_times)
                estimated_finish = calculate_estimated_finish_time(
                    i, len(targets), avg_time, start_time
                )
                logger.info(f"⏱️  预计完成: {estimated_finish}")

            # 最后一场不需要延迟
            if i < len(targets):
                delay = random.uniform(*delay_range)
                logger.info(f"⏳ 等待 {delay:.1f}s 后继续（抖动: {delay_range[0]}-{delay_range[1]}s）...")
                await asyncio.sleep(delay)

        except Exception as e:
            logger.error(f"❌ 采集异常: {e}")
            elapsed_times.append(0)
            # 即使异常也尝试保存失败记录
            await save_single_match_to_database(
                target_id=target['id'],
                fotmob_id=target['fotmob_id'],
                data=None,
                error=str(e),
                is_malformed=False
            )
            stats['failed'] += 1
            continue

    total_elapsed = time.time() - start_time

    # 步骤 4: 汇报战果
    logger.info("\n" + "=" * 70)
    logger.info("📊 V151.0 采集战果报告（增量入库模式）")
    logger.info("=" * 70)
    logger.info(f"总场次: {len(targets)}")
    logger.info(f"✅ 成功: {stats['success']}")
    logger.info(f"⚠️ 残缺: {stats['malformed']}")
    logger.info(f"❌ 失败: {stats['failed']}")
    logger.info(f"总耗时: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
    logger.info(f"平均耗时: {sum(elapsed_times)/len(elapsed_times):.1f}s/场")
    logger.info(f"最快: {min(elapsed_times):.1f}s")
    logger.info(f"最慢: {max(elapsed_times):.1f}s")

    # 保存审计日志
    scraper.save_audit_log()
    logger.info("\n✅ V151.0 增量收割完成！")
    logger.info("🎉 所有数据已实时入库，断点续传保护生效")


if __name__ == "__main__":
    import argparse

    # Load .env first
    from dotenv import load_dotenv
    load_dotenv(override=True)

    # Parse arguments
    parser = argparse.ArgumentParser(description="V151.0 增量收割（抓一场存一场）")
    parser.add_argument('--limit', type=int, default=50, help='采集比赛数量')
    parser.add_argument('--delay-min', type=float, default=20.0, help='最小延迟（秒）')
    parser.add_argument('--delay-max', type=float, default=40.0, help='最大延迟（秒）')

    args = parser.parse_args()

    # Run harvest
    asyncio.run(run_incremental_harvest_persistence(
        limit=args.limit,
        delay_range=(args.delay_min, args.delay_max)
    ))
