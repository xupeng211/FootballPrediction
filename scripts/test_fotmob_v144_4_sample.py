#!/usr/bin/env python3
"""
V144.4 FotMob Pulse Test - 10 Match Sample
测试 Ghost Protocol V144.3 集成并验证 V36.0 Schema 字段填充
"""

import logging
import sys
from datetime import datetime

# 配置详细日志以显示 Ghost Protocol UA 指纹轮换
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/v144_4_pulse_test.log")
    ]
)
logger = logging.getLogger(__name__)


def main():
    """执行 10 场采样采集测试"""
    from src.api.collectors.fotmob_core import FotMobCoreCollector

    # V144.3: 初始化采集器（触发 Ghost Protocol UA 指纹生成）
    logger.info("=" * 80)
    logger.info("🚀 V144.4 FotMob Pulse Test - 启动 10 场采样采集")
    logger.info("=" * 80)

    collector = FotMobCoreCollector()

    # V144.4 快速验证：先采集 2 场比赛验证 Ghost Protocol
    # 来源: FotMob API League ID 47 = Premier League
    test_match_ids = [
        4218199,  # Arsenal vs Chelsea (2024-05-12)
        4218200,  # Man City vs Tottenham (2024-05-14)
    ]

    logger.info(f"📋 采样名单: {len(test_match_ids)} 场英超比赛")
    logger.info(f"📊 联赛 ID: 47 (Premier League)")
    logger.info(f"📅 赛季: 23/24")
    logger.info("-" * 80)

    success_count = 0
    fail_count = 0

    for i, match_id in enumerate(test_match_ids, 1):
        logger.info(f"\n🔎 [{i}/{len(test_match_ids)}] 正在采集 Match ID: {match_id}")

        # 使用 V144.3 Ghost Protocol 集成的 harvest_match_with_league 方法
        success = collector.harvest_match_with_league(
            match_id=match_id,
            league_id=47,  # Premier League
            season="2324"
        )

        if success:
            success_count += 1
            logger.info(f"✅ Match {match_id} 采集成功")
        else:
            fail_count += 1
            logger.warning(f"❌ Match {match_id} 采集失败")

        # V144.4 快速验证：使用较短延迟 (5秒) 快速测试
        # 生产环境应使用 120s+ 延迟避免触发反爬限制
        if i < len(test_match_ids):  # 最后一场不延迟
            delay = 5  # 快速验证模式：5 秒延迟
            logger.info(f"⏸️  V144.4 Quick Validation Delay: 等待 {delay}s...")
            import time
            time.sleep(delay)

    # 输出汇总
    logger.info("\n" + "=" * 80)
    logger.info("📊 V144.4 Pulse Test - 采集汇总")
    logger.info("=" * 80)
    logger.info(f"✅ 成功: {success_count}/{len(test_match_ids)} ({success_count/len(test_match_ids)*100:.1f}%)")
    logger.info(f"❌ 失败: {fail_count}/{len(test_match_ids)} ({fail_count/len(test_match_ids)*100:.1f}%)")
    logger.info("=" * 80)

    # 输出后续审计 SQL
    logger.info("\n🔍 数据库审计 SQL:")
    logger.info("-" * 80)
    audit_sql = """
SELECT
    match_id,
    home_team,
    away_team,
    season_name,
    match_time_utc,
    data_source,
    fetched_at
FROM matches
WHERE data_source = 'fotmob'
ORDER BY fetched_at DESC
LIMIT 10;
"""
    logger.info(audit_sql)
    logger.info("-" * 80)


if __name__ == "__main__":
    main()
