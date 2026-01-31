#!/usr/bin/env python3
"""
Concurrent Pinnacle Odds Harvester - V151.3 (Multi-Process)

核心功能:
- 多进程并发采集 (默认 3 进程)
- 进程间代理隔离 (7890-7899)
- 独立数据库连接
- 进程级错误隔离
- 实时统计汇总

架构:
  ┌─────────────────────────────────────────────────────┐
  │              Main Process (调度器)                   │
  │  - 从数据库获取待采集队列                            │
  │  - 分配任务给工作进程                                │
  │  - 汇总统计结果                                      │
  └─────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐
    │Worker 1 │     │Worker 2 │     │Worker 3 │
    │:7890    │     │:7891    │     │:7892    │
    └─────────┘     └─────────┘     └─────────┘

使用示例:
    # 3 进程并发 (保守方案)
    python scripts/ops/harvest_pinnacle_concurrent.py --workers 3 --limit 100

    # 10 进程全速 (激进方案)
    python scripts/ops/harvest_pinnacle_concurrent.py --workers 10 --limit 500

Author: 高级数据运维架构师 (Senior Data Ops Architect)
Version: V151.3 (Concurrent Harvester)
Date: 2026-01-11
"""

import argparse
import asyncio
import json
import logging
import multiprocessing as mp
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# V30.3: 配置日志轮转
from logging.handlers import RotatingFileHandler

# 确保日志目录存在
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

# 创建根日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 日志格式
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(name)s - %(message)s')

# 文件处理器 - 轮转 (50MB x 10)
file_handler = RotatingFileHandler(
    'logs/harvest_pinnacle_concurrent.log',
    maxBytes=50*1024*1024,  # 50MB
    backupCount=10,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 配置根日志记录器（避免重复）
logging.root.setLevel(logging.INFO)
logging.root.handlers = []  # 清除现有处理器
logging.root.addHandler(file_handler)
logging.root.addHandler(console_handler)

# V41.125: 从统一配置获取代理端口列表
from src.config_unified import get_config

def get_proxy_ports():
    """V41.125: 从统一配置获取代理端口（零硬编码）"""
    config = get_config()
    return config.proxy.proxy_ports

PROXY_PORTS = get_proxy_ports()


@dataclass
class HarvestConfig:
    """收割配置"""
    proxy_port: int
    limit: int
    delay_min: float
    delay_max: float
    batch_id: str


@dataclass
class WorkerResult:
    """工作进程结果"""
    worker_id: int
    proxy_port: int
    success: int = 0
    failed: int = 0
    malformed: int = 0
    abandoned: int = 0
    elapsed: float = 0.0
    error: Optional[str] = None


# ==============================================================================
# Worker Process Function
# ==============================================================================

def worker_process(config: HarvestConfig) -> WorkerResult:
    """
    工作进程 - 独立进程，绑定单个代理端口

    Args:
        config: 收割配置

    Returns:
        WorkerResult: 执行结果
    """
    # 设置进程专属日志
    process_logger = logging.getLogger(f"Worker-{config.proxy_port}")
    process_logger.setLevel(logging.INFO)
    process_logger.propagate = False  # 防止传播到根日志记录器

    # V30.3: 使用轮转文件处理器
    worker_file_handler = RotatingFileHandler(
        f'logs/harvest_worker_{config.proxy_port}.log',
        maxBytes=50*1024*1024,  # 50MB
        backupCount=10,
        encoding='utf-8'
    )
    worker_file_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s'))
    process_logger.addHandler(worker_file_handler)

    process_logger.info(f"=" * 60)
    process_logger.info(f"Worker 启动 (代理端口: {config.proxy_port})")
    process_logger.info(f"=" * 60)

    result = WorkerResult(
        worker_id=config.proxy_port,
        proxy_port=config.proxy_port
    )

    start_time = time.time()

    try:
        # 导入必需模块（在子进程中导入）
        import psycopg2
        from src.config_unified import get_settings
        from core.scrapers.oddsportal import OddsPortalScraper

        # 设置代理环境变量
        os.environ['PROXY_PORT'] = str(config.proxy_port)

        # 连接数据库
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # 获取待采集任务
        cursor.execute("""
            SELECT
                id,
                fotmob_id,
                home_team,
                away_team,
                oddsportal_url,
                status,
                retry_count
            FROM matches_mapping
            WHERE oddsportal_url IS NOT NULL
              AND oddsportal_url != ''
              AND l2_raw_json IS NULL
              AND (
                  status != 'abandoned'
                  AND (status != 'malformed' OR retry_count < 3)
              )
            ORDER BY
                CASE WHEN status = 'malformed' THEN 0 ELSE 1 END,
                confidence DESC, id
            LIMIT %s
            FOR UPDATE SKIP LOCKED  -- 跳过已被其他进程锁定的记录
        """, (config.limit,))

        targets = []
        columns = ['id', 'fotmob_id', 'home_team', 'away_team', 'oddsportal_url', 'status', 'retry_count']
        for row in cursor.fetchall():
            targets.append(dict(zip(columns, row)))

        process_logger.info(f"🎯 获取 {len(targets)} 场比赛待采集")

        if not targets:
            process_logger.info("无待采集任务，Worker 退出")
            cursor.close()
            conn.close()
            return result

        # 初始化采集器
        scraper = OddsPortalScraper(config_path="config/scraper_config.yaml")

        # 采集循环
        for i, target in enumerate(targets, 1):
            try:
                match_id = target['oddsportal_url'].rstrip('/').split('/')[-1]
                current_retry_count = target.get('retry_count', 0)

                process_logger.info(f"[{i}/{len(targets)}] 采集: {target['home_team']} vs {target['away_team']}")

                # 调用采集
                harvest_result = asyncio.run(scraper.fetch_snapshot(
                    match_id=match_id,
                    home_team=target['home_team'],
                    away_team=target['away_team'],
                    url=target['oddsportal_url'],
                    headless=True,
                    custom_timeout_ms=30000 if current_retry_count > 0 else 15000
                ))

                # 数据质量验证
                is_valid = True
                if harvest_result.get('success') and harvest_result.get('data'):
                    data = harvest_result['data']
                    has_home = 'home' in data and data['home']
                    has_draw = 'draw' in data and data['draw']
                    has_away = 'away' in data and data['away']
                    is_valid = has_home and has_draw and has_away

                # 保存结果
                if harvest_result.get('success') and is_valid:
                    # 完整数据
                    l2_json = json.dumps(harvest_result['data'], ensure_ascii=False)
                    cursor.execute("""
                        UPDATE matches_mapping
                        SET l2_raw_json = %s,
                            status = 'harvested',
                            is_malformed = FALSE,
                            retry_count = 0,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (l2_json, target['id']))
                    result.success += 1
                    process_logger.info(f"✅ 成功: {target['fotmob_id']}")

                elif harvest_result.get('success') and not is_valid:
                    # V30.3: 残缺数据 - 尝试原地重试一次
                    process_logger.warning(f"⚠️ 检测到残缺数据: {target['fotmob_id']}")
                    process_logger.info(f"   缺失字段: home={has_home}, draw={has_draw}, away={has_away}")

                    # 尝试使用当前代理进行一次原地重试
                    process_logger.info(f"🔄 尝试原地重试 (代理: {config.proxy_port})...")
                    retry_result = asyncio.run(scraper.fetch_snapshot(
                        match_id=target['fotmob_id'],
                        home_team=target['home_team'],
                        away_team=target['away_team'],
                        url=target['oddsportal_url'],
                        headless=True,
                        custom_timeout_ms=30000  # 增加超时时间
                    ))

                    # 验证重试结果
                    retry_is_valid = True
                    if retry_result.get('success') and retry_result.get('data'):
                        retry_data = retry_result['data']
                        has_home_r = 'home' in retry_data and retry_data['home']
                        has_draw_r = 'draw' in retry_data and retry_data['draw']
                        has_away_r = 'away' in retry_data and retry_data['away']
                        retry_is_valid = has_home_r and has_draw_r and has_away_r

                    if retry_result.get('success') and retry_is_valid:
                        # 重试成功
                        l2_json = json.dumps(retry_result['data'], ensure_ascii=False)
                        cursor.execute("""
                            UPDATE matches_mapping
                            SET l2_raw_json = %s,
                                status = 'harvested',
                                is_malformed = FALSE,
                                retry_count = 0,
                                updated_at = NOW()
                            WHERE id = %s
                        """, (l2_json, target['id']))
                        result.success += 1
                        process_logger.info(f"✅ 重试成功: {target['fotmob_id']}")

                    else:
                        # 重试仍然失败，按原有逻辑处理
                        new_retry_count = current_retry_count + 1
                        if new_retry_count >= 3:
                            cursor.execute("""
                                UPDATE matches_mapping
                                SET status = 'abandoned',
                                    retry_count = %s,
                                    updated_at = NOW()
                            """, (new_retry_count, target['id']))
                            result.abandoned += 1
                            process_logger.error(f"🛑 放弃: {target['fotmob_id']} (retry_count={new_retry_count}, 重试失败)")
                        else:
                            # 保存原始残缺数据
                            l2_json = json.dumps(harvest_result['data'], ensure_ascii=False)
                            cursor.execute("""
                                UPDATE matches_mapping
                                SET l2_raw_json = %s,
                                    status = 'malformed',
                                    is_malformed = TRUE,
                                    retry_count = %s,
                                    updated_at = NOW()
                                WHERE id = %s
                            """, (l2_json, new_retry_count, target['id']))
                            result.malformed += 1
                            process_logger.warning(f"⚠️ 残缺: {target['fotmob_id']} (retry_count={new_retry_count}, 重试失败)")

                else:
                    # 采集失败
                    new_retry_count = current_retry_count + 1
                    if new_retry_count >= 3:
                        cursor.execute("""
                            UPDATE matches_mapping
                            SET status = 'abandoned',
                                retry_count = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """, (new_retry_count, target['id']))
                        result.abandoned += 1
                        process_logger.error(f"🛑 放弃: {target['fotmob_id']} (retry_count={new_retry_count})")
                    else:
                        cursor.execute("""
                            UPDATE matches_mapping
                            SET retry_count = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """, (new_retry_count, target['id']))
                        result.failed += 1
                        process_logger.error(f"❌ 失败: {target['fotmob_id']} (retry_count={new_retry_count})")

                # 延迟（除了最后一场）
                if i < len(targets):
                    import random
                    delay = random.uniform(config.delay_min, config.delay_max)
                    process_logger.debug(f"⏳ 等待 {delay:.1f}s...")
                    time.sleep(delay)

            except Exception as e:
                process_logger.error(f"❌ 采集异常: {e}")
                result.failed += 1
                continue

        cursor.close()
        conn.close()

        # 保存审计日志
        scraper.save_audit_log()

    except Exception as e:
        process_logger.error(f"❌ Worker 异常: {e}")
        result.error = str(e)

    result.elapsed = time.time() - start_time
    process_logger.info(f"Worker 完成 (耗时: {result.elapsed:.1f}s)")
    process_logger.info(f"  ✅ {result.success} | ⚠️ {result.malformed} | ❌ {result.failed} | 🛑 {result.abandoned}")

    return result


# ==============================================================================
# Main Scheduler
# ==============================================================================

def main():
    """主调度函数"""
    parser = argparse.ArgumentParser(
        description="V151.3 并发收割器 - 多进程采集"
    )
    parser.add_argument('--workers', type=int, default=8,  # V30.3: 默认 8 Workers
                        help='工作进程数 (默认: 3, 最大: 10)')
    parser.add_argument('--limit', type=int, default=50,
                        help='每个进程采集数量 (默认: 50)')
    parser.add_argument('--delay-min', type=float, default=20.0,
                        help='最小延迟（秒）')
    parser.add_argument('--delay-max', type=float, default=40.0,
                        help='最大延迟（秒）')
    parser.add_argument('--dry-run', action='store_true',
                        help='干跑模式，只检查不执行')

    args = parser.parse_args()

    # 验证参数
    if args.workers > len(PROXY_PORTS):
        logger.error(f"工作进程数不能超过代理端口数 ({len(PROXY_PORTS)})")
        return 1

    if args.workers > 10:
        logger.warning("⚠️ 工作进程数过多可能导致资源耗尽，建议不超过 10")

    logger.info("=" * 70)
    logger.info("🚀 V151.3 并发收割器启动")
    logger.info("=" * 70)
    logger.info(f"工作进程数: {args.workers}")
    logger.info(f"每进程采集数: {args.limit}")
    logger.info(f"总预计采集: {args.workers * args.limit}")
    logger.info(f"代理端口: {PROXY_PORTS[:args.workers]}")
    logger.info("")

    if args.dry_run:
        logger.info("🔍 干跑模式 - 检查配置...")
        logger.info(f"✅ 配置验证通过")
        logger.info(f"✅ {args.workers} 个进程可用")
        logger.info(f"✅ {len(PROXY_PORTS)} 个代理端口可用")
        return 0

    # 生成批次 ID
    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 创建工作进程配置
    configs = []
    for i in range(args.workers):
        config = HarvestConfig(
            proxy_port=PROXY_PORTS[i],
            limit=args.limit,
            delay_min=args.delay_min,
            delay_max=args.delay_max,
            batch_id=batch_id
        )
        configs.append(config)

    # 启动进程池
    start_time = time.time()
    results = []

    logger.info("🔧 启动进程池...")
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        # 提交所有任务
        futures = {}
        for config in configs:
            future = executor.submit(worker_process, config)
            futures[future] = config

        # 收集结果
        logger.info("⏳ 等待工作进程完成...")
        for future in as_completed(futures):
            config = futures[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(f"✅ Worker-{config.proxy_port} 完成")
            except Exception as e:
                logger.error(f"❌ Worker-{config.proxy_port} 异常: {e}")
                results.append(WorkerResult(
                    worker_id=config.proxy_port,
                    proxy_port=config.proxy_port,
                    error=str(e)
                ))

    # 汇总结果
    total_elapsed = time.time() - start_time

    logger.info("\n" + "=" * 70)
    logger.info("📊 V151.3 并发收割战果报告")
    logger.info("=" * 70)

    # 按进程统计
    for result in results:
        logger.info(f"")
        logger.info(f"Worker-{result.proxy_port}:")
        logger.info(f"  ✅ 成功: {result.success}")
        logger.info(f"  ⚠️ 残缺: {result.malformed}")
        logger.info(f"  ❌ 失败: {result.failed}")
        logger.info(f"  🛑 放弃: {result.abandoned}")
        logger.info(f"  ⏱️ 耗时: {result.elapsed:.1f}s")

    # 总计
    total_success = sum(r.success for r in results)
    total_malformed = sum(r.malformed for r in results)
    total_failed = sum(r.failed for r in results)
    total_abandoned = sum(r.abandoned for r in results)
    total_processed = total_success + total_malformed + total_failed + total_abandoned

    logger.info("\n" + "-" * 70)
    logger.info("总计:")
    logger.info(f"  总场次: {total_processed}")
    logger.info(f"  ✅ 成功: {total_success} ({total_success/max(total_processed,1)*100:.1f}%)")
    logger.info(f"  ⚠️ 残缺: {total_malformed} ({total_malformed/max(total_processed,1)*100:.1f}%)")
    logger.info(f"  ❌ 失败: {total_failed} ({total_failed/max(total_processed,1)*100:.1f}%)")
    logger.info(f"  🛑 放弃: {total_abandoned} ({total_abandoned/max(total_processed,1)*100:.1f}%)")
    logger.info(f"  总耗时: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")

    if total_processed > 0:
        avg_time = total_elapsed / total_processed
        logger.info(f"  平均: {avg_time:.1f}s/场")

    # 保存汇总报告
    report_path = Path('logs/concurrent_harvest_report.json')
    report = {
        'batch_id': batch_id,
        'timestamp': datetime.now().isoformat(),
        'config': {
            'workers': args.workers,
            'limit_per_worker': args.limit,
            'total_expected': args.workers * args.limit,
            'delay_range': [args.delay_min, args.delay_max]
        },
        'results': {
            'total_processed': total_processed,
            'success': total_success,
            'malformed': total_malformed,
            'failed': total_failed,
            'abandoned': total_abandoned,
            'total_elapsed_seconds': total_elapsed
        },
        'workers': [
            {
                'proxy_port': r.proxy_port,
                'success': r.success,
                'malformed': r.malformed,
                'failed': r.failed,
                'abandoned': r.abandoned,
                'elapsed': r.elapsed,
                'error': r.error
            }
            for r in results
        ]
    }

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"\n📄 汇总报告已保存: {report_path}")
    logger.info("\n✅ V151.3 并发收割完成！")

    return 0


if __name__ == "__main__":
    # Load .env first
    from dotenv import load_dotenv
    load_dotenv(override=True)

    # Windows multiprocessing fix
    if sys.platform == 'win32':
        mp.set_start_method('spawn', force=True)

    sys.exit(main())
