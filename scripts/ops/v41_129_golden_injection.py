#!/usr/bin/env python3
"""
V41.129 "黄金注浆" - 平博赔率全量入库

核心功能:
- 从 aligned_matches 表提取已对齐的哈希值
- 使用 OddsPortalScraper 批量抓取 Pinnacle 的初盘和终盘赔率
- 将抓取到的赔率 JSON 写入 matches 表的 l3_odds_data 字段
- 支持并发处理（默认 3 Workers）
- 断点续传功能

架构:
  ┌──────────────────────────────────────────────────────────────────┐
  │                    Main Process (调度器)                          │
  │  - 从 aligned_matches 获取待采集队列                              │
  │  - 分配任务给工作线程                                              │
  │  - 汇总统计结果                                                    │
  └──────────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐
    │Worker 1 │     │Worker 2 │     │Worker 3 │
    │:7892    │     │:7893    │     │:7894    │
    └─────────┘     └─────────┘     └─────────┘

使用示例:
    # 3 并发（保守方案）
    python scripts/ops/v41_129_golden_injection.py --workers 3 --limit 100

    # 干跑模式
    python scripts/ops/v41_129_golden_injection.py --workers 3 --dry-run

Author: 高级数据集成工程师
Version: V41.129 (Golden Injection)
Date: 2026-01-17
"""

import argparse
import asyncio
import json
import logging
import multiprocessing as mp
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_config

# V41.121: 从统一配置获取代理端口列表
def get_proxy_ports():
    """V41.121: 从统一配置获取代理端口列表（零硬编码）"""
    config = get_config()
    return config.proxy.proxy_ports

PROXY_PORTS = get_proxy_ports()

# 配置日志轮转
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
    'logs/v41_129_golden_injection.log',
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


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class InjectionConfig:
    """注浆配置"""
    proxy_port: int
    limit: int
    delay_min: float
    delay_max: float
    batch_id: str


@dataclass
class WorkerResult:
    """工作线程结果"""
    worker_id: int
    proxy_port: int
    success: int = 0
    failed: int = 0
    skipped: int = 0
    elapsed: float = 0.0
    error: Optional[str] = None


# =============================================================================
# Worker Thread Function
# =============================================================================

def worker_thread(config: InjectionConfig) -> WorkerResult:
    """
    工作线程 - 独立线程，绑定单个代理端口

    Args:
        config: 注浆配置

    Returns:
        WorkerResult: 执行结果
    """
    # 设置线程专属日志
    thread_logger = logging.getLogger(f"Worker-{config.proxy_port}")
    thread_logger.setLevel(logging.INFO)
    thread_logger.propagate = False  # 防止传播到根日志记录器

    # 使用轮转文件处理器
    worker_file_handler = RotatingFileHandler(
        f'logs/v41_129_worker_{config.proxy_port}.log',
        maxBytes=50*1024*1024,  # 50MB
        backupCount=10,
        encoding='utf-8'
    )
    worker_file_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s'))
    thread_logger.addHandler(worker_file_handler)

    thread_logger.info(f"=" * 60)
    thread_logger.info(f"Worker 启动 (代理端口: {config.proxy_port})")
    thread_logger.info(f"=" * 60)

    result = WorkerResult(
        worker_id=config.proxy_port,
        proxy_port=config.proxy_port
    )

    start_time = time.time()

    try:
        # 设置代理环境变量
        os.environ['PROXY_PORT'] = str(config.proxy_port)

        # 连接数据库
        from src.config_unified import get_settings
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # 获取待采集任务（从 aligned_matches 表）
        cursor.execute("""
            SELECT
                am.fotmob_match_id,
                am.oddsportal_match_id,
                m.home_team,
                m.away_team,
                m.home_score,
                m.away_score,
                m.league_name
            FROM aligned_matches am
            JOIN matches m ON am.fotmob_match_id = m.match_id
            WHERE am.oddsportal_match_id IS NOT NULL
              AND length(am.oddsportal_match_id) > 0
              AND (m.l3_odds_data IS NULL OR m.l3_odds_data = '{}'::jsonb)
            ORDER BY am.aligned_at DESC
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        """, (config.limit,))

        targets = []
        for row in cursor.fetchall():
            targets.append(dict(row))

        thread_logger.info(f"🎯 获取 {len(targets)} 场比赛待注浆")

        if not targets:
            thread_logger.info("无待采集任务，Worker 退出")
            cursor.close()
            conn.close()
            return result

        # 导入采集器（在线程中导入以避免多线程问题）
        from src.api.collectors.odds_l3_extractor import OddsL3Extractor

        # 初始化提取器
        extractor = OddsL3Extractor(enable_ghost=True)

        # 采集循环
        for i, target in enumerate(targets, 1):
            try:
                fotmob_match_id = target['fotmob_match_id']
                oddsportal_id = target['oddsportal_match_id']
                home_team = target['home_team']
                away_team = target['away_team']
                league_name = target['league_name']

                # 构建 OddsPortal URL
                oddsportal_url = f"https://www.oddsportal.com/match/{oddsportal_id}/"

                # 构建 FotMob 比分
                fotmob_score = {
                    "home": target['home_score'] or 0,
                    "away": target['away_score'] or 0
                }

                thread_logger.info(f"[{i}/{len(targets)}] 注浆: {home_team} vs {away_team} ({league_name})")
                thread_logger.info(f"     URL: {oddsportal_url}")

                # 调用提取器（异步）
                extraction_result = asyncio.run(extractor.extract_match(
                    match_id=fotmob_match_id,
                    oddsportal_url=oddsportal_url,
                    home_team=home_team,
                    away_team=away_team,
                    fotmob_score=fotmob_score,
                    enable_debug_screenshot=False
                ))

                # 保存结果
                if extraction_result.success and extraction_result.l3_data:
                    # 直接更新 matches 表（使用提取器内部的 save 函数）
                    from src.api.collectors.odds_l3_extractor import save_l3_data_to_db
                    save_success = save_l3_data_to_db(extraction_result)

                    if save_success:
                        result.success += 1
                        thread_logger.info(f"✅ 成功: {fotmob_match_id}")
                    else:
                        result.failed += 1
                        thread_logger.warning(f"⚠️ 保存失败: {fotmob_match_id}")
                else:
                    result.failed += 1
                    error_msg = extraction_result.error or "Unknown error"
                    thread_logger.error(f"❌ 提取失败: {fotmob_match_id} - {error_msg}")

                # 延迟（除了最后一场）
                if i < len(targets):
                    import random
                    delay = random.uniform(config.delay_min, config.delay_max)
                    thread_logger.debug(f"⏳ 等待 {delay:.1f}s...")
                    time.sleep(delay)

            except Exception as e:
                thread_logger.error(f"❌ 采集异常: {e}")
                result.failed += 1
                continue

        cursor.close()
        conn.close()

    except Exception as e:
        thread_logger.error(f"❌ Worker 异常: {e}")
        result.error = str(e)

    result.elapsed = time.time() - start_time
    thread_logger.info(f"Worker 完成 (耗时: {result.elapsed:.1f}s)")
    thread_logger.info(f"  ✅ {result.success} | ❌ {result.failed} | ⏭️  {result.skipped}")

    return result


# =============================================================================
# Main Scheduler
# =============================================================================

def main():
    """主调度函数"""
    parser = argparse.ArgumentParser(
        description="V41.129 黄金注浆 - 并发赔率采集"
    )
    parser.add_argument('--workers', type=int, default=3,
                        help='工作线程数 (默认: 3, 最大: 10)')
    parser.add_argument('--limit', type=int, default=50,
                        help='每线程采集数量 (默认: 50)')
    parser.add_argument('--delay-min', type=float, default=15.0,
                        help='最小延迟（秒）')
    parser.add_argument('--delay-max', type=float, default=30.0,
                        help='最大延迟（秒）')
    parser.add_argument('--dry-run', action='store_true',
                        help='干跑模式，只检查不执行')

    args = parser.parse_args()

    # 验证参数
    if args.workers > len(PROXY_PORTS):
        logger.error(f"工作线程数不能超过代理端口数 ({len(PROXY_PORTS)})")
        return 1

    if args.workers > 10:
        logger.warning("⚠️ 工作线程数过多可能导致资源耗尽，建议不超过 10")

    # 检查待采集数量
    from src.config_unified import get_settings
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) as total
        FROM aligned_matches am
        JOIN matches m ON am.fotmob_match_id = m.match_id
        WHERE am.oddsportal_match_id IS NOT NULL
          AND length(am.oddsportal_match_id) > 0
          AND (m.l3_odds_data IS NULL OR m.l3_odds_data = '{}'::jsonb)
    """)
    pending_count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    logger.info("=" * 70)
    logger.info("🚀 V41.129 黄金注浆启动")
    logger.info("=" * 70)
    logger.info(f"工作线程数: {args.workers}")
    logger.info(f"每线程采集数: {args.limit}")
    logger.info(f"总预计采集: {min(args.workers * args.limit, pending_count)}")
    logger.info(f"待采集总数: {pending_count}")
    logger.info(f"代理端口: {PROXY_PORTS[:args.workers]}")
    logger.info("")

    if args.dry_run:
        logger.info("🔍 干跑模式 - 检查配置...")
        logger.info(f"✅ 配置验证通过")
        logger.info(f"✅ {args.workers} 个线程可用")
        logger.info(f"✅ {len(PROXY_PORTS)} 个代理端口可用")
        logger.info(f"✅ {pending_count} 场比赛待采集")
        return 0

    # 生成批次 ID
    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 创建工作线程配置
    configs = []
    for i in range(args.workers):
        config = InjectionConfig(
            proxy_port=PROXY_PORTS[i],
            limit=args.limit,
            delay_min=args.delay_min,
            delay_max=args.delay_max,
            batch_id=batch_id
        )
        configs.append(config)

    # 启动线程池
    start_time = time.time()
    results = []

    logger.info("🔧 启动线程池...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # 提交所有任务
        futures = {}
        for config in configs:
            future = executor.submit(worker_thread, config)
            futures[future] = config

        # 收集结果
        logger.info("⏳ 等待工作线程完成...")
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
    logger.info("📊 V41.129 黄金注浆结果报告")
    logger.info("=" * 70)

    # 按线程统计
    for result in results:
        logger.info(f"")
        logger.info(f"Worker-{result.proxy_port}:")
        logger.info(f"  ✅ 成功: {result.success}")
        logger.info(f"  ❌ 失败: {result.failed}")
        logger.info(f"  ⏭️  跳过: {result.skipped}")
        logger.info(f"  ⏱️  耗时: {result.elapsed:.1f}s")

    # 总计
    total_success = sum(r.success for r in results)
    total_failed = sum(r.failed for r in results)
    total_skipped = sum(r.skipped for r in results)
    total_processed = total_success + total_failed + total_skipped

    logger.info("\n" + "-" * 70)
    logger.info("总计:")
    logger.info(f"  总场次: {total_processed}")
    logger.info(f"  ✅ 成功: {total_success} ({total_success/max(total_processed,1)*100:.1f}%)")
    logger.info(f"  ❌ 失败: {total_failed} ({total_failed/max(total_processed,1)*100:.1f}%)")
    logger.info(f"  ⏭️  跳过: {total_skipped}")
    logger.info(f"  总耗时: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")

    if total_processed > 0:
        avg_time = total_elapsed / total_processed
        logger.info(f"  平均: {avg_time:.1f}s/场")

    # 检查最终覆盖率
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total_matches,
            COUNT(l3_odds_data) as with_odds,
            ROUND(COUNT(l3_odds_data) * 100.0 / COUNT(*), 2) as coverage_pct
        FROM matches
    """)
    coverage_row = cursor.fetchone()

    # V41.129: 转换 Decimal 为 float（JSON 序列化兼容）
    total_matches = int(coverage_row[0]) if coverage_row[0] is not None else 0
    with_odds = int(coverage_row[1]) if coverage_row[1] is not None else 0
    coverage_pct = float(coverage_row[2]) if coverage_row[2] is not None else 0.0

    cursor.close()
    conn.close()

    logger.info("\n" + "=" * 70)
    logger.info("📈 覆盖率统计:")
    logger.info(f"  总比赛数: {total_matches}")
    logger.info(f"  有赔率数据: {with_odds}")
    logger.info(f"  覆盖率: {coverage_pct}%")
    logger.info("=" * 70)

    # 保存汇总报告
    report_path = Path('logs/v41_129_golden_injection_report.json')
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
            'failed': total_failed,
            'skipped': total_skipped,
            'total_elapsed_seconds': total_elapsed
        },
        'coverage': {
            'total_matches': total_matches,
            'with_odds': with_odds,
            'coverage_pct': coverage_pct
        },
        'workers': [
            {
                'proxy_port': r.proxy_port,
                'success': r.success,
                'failed': r.failed,
                'skipped': r.skipped,
                'elapsed': r.elapsed,
                'error': r.error
            }
            for r in results
        ]
    }

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"\n📄 汇总报告已保存: {report_path}")
    logger.info("\n✅ V41.129 黄金注浆完成！")

    return 0


if __name__ == "__main__":
    # Load .env first
    from dotenv import load_dotenv
    load_dotenv(override=True)

    sys.exit(main())
