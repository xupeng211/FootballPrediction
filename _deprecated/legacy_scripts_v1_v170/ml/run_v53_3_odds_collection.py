#!/usr/bin/env python3
"""
V53.3 赔率采集验证脚本
=====================

功能:
1. 运行 2025 年赔率采集
2. 计算 Drift 特征
3. 输出审计总结

Author: Senior Data Engineer
Version: V53.3
Date: 2026-01-01
"""

import asyncio
import sys
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.collectors.odds_scraper_playwright import quick_collect_odds_by_year
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """主采集流程"""
    logger.info("=" * 60)
    logger.info("【V53.3 赔率采集服务】")
    logger.info("=" * 60)
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")

    # 运行 2025 年采集（2026 年暂无数据）
    result = await quick_collect_odds_by_year(2025)

    print()
    print("=" * 60)
    print("【V53.3 采集审计报告】")
    print("=" * 60)
    print()
    print(f"状态: {result['status']}")
    print(f"目标年份: {result['year']}")
    print(f"总采集场数: {result['total_matches']}")
    print(f"初盘+终赔双全: {result['with_opening_closing']} ({result['with_opening_closing']/result['total_matches']*100:.1f}%)")
    print(f"成功保存: {result['saved_records']}")
    print(f"跳过（校验失败）: {result['skipped_invalid']}")
    print(f"跳过（无初盘）: {result['skipped_no_opening']}")
    print()
    print("=" * 60)
    print()

    # 数据库统计：Margin 和 Drift
    import psycopg2
    from src.config_unified import get_settings

    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cursor = conn.cursor()

    # Margin 统计
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            AVG((1.0/closing_home_odds + 1.0/closing_draw_odds + 1.0/closing_away_odds)) as avg_margin,
            MIN((1.0/closing_home_odds + 1.0/closing_draw_odds + 1.0/closing_away_odds)) as min_margin,
            MAX((1.0/closing_home_odds + 1.0/closing_draw_odds + 1.0/closing_away_odds)) as max_margin
        FROM prematch_features
        WHERE closing_home_odds IS NOT NULL
          AND closing_draw_odds IS NOT NULL
          AND closing_away_odds IS NOT NULL
          AND match_date >= '2025-01-01'
    """)

    margin_stats = cursor.fetchone()

    print()
    print("=" * 60)
    print("【2025 赛季市场抽水统计】")
    print("=" * 60)
    print()
    print(f"样本数: {margin_stats[0]}")
    print(f"平均 Margin: {margin_stats[1]*100:.2f}%")
    print(f"最小 Margin: {margin_stats[2]*100:.2f}%")
    print(f"最大 Margin: {margin_stats[3]*100:.2f}%")
    print()

    # Drift 统计
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            AVG(home_odds_drift) as avg_home_drift,
            AVG(draw_odds_drift) as avg_draw_drift,
            AVG(away_odds_drift) as avg_away_drift
        FROM prematch_features
        WHERE home_odds_drift IS NOT NULL
          AND match_date >= '2025-01-01'
    """)

    drift_stats = cursor.fetchone()

    print("=" * 60)
    print("【V53.3 赔率走势统计】")
    print("=" * 60)
    print()
    print(f"样本数: {drift_stats[0]}")
    print(f"平均主胜 Drift: {drift_stats[1]*100:.2f}%")
    print(f"平均平局 Drift: {drift_stats[2]*100:.2f}%")
    print(f"平均客胜 Drift: {drift_stats[3]*100:.2f}%")
    print()
    print("注: Drift > 0 表示赔率上升（热度下降）")
    print("    Drift < 0 表示赔率下降（热度上升）")
    print()
    print("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
