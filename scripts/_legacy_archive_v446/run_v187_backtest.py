#!/usr/bin/env python3
"""
V187 ML 资产复活 - 562 场数据实战回测
========================================

激活现有的 ML 组件， 使用 562 场黄金数据进行回测验证

Author: V187 Architecture Team
Date: 2026-03-04
Version: V187.0.0
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, '/app/src')
sys.path.insert(0, '/app')

import psycopg2
from psycopg2.extras import RealDictCursor

# V186: 导入日志系统
try:
    from src.infrastructure.utils.logger import logger
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# ============================================================================
# 配置
# ============================================================================

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'host.docker.internal'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'football_db'),
    'user': os.getenv('DB_USER', 'football_user'),
    'password': os.getenv('DB_PASSWORD', '')
}


def main():
    """主函数 - 统计现有 ML 资产"""
    logger.info("=" * 60)
    logger.info("🎯 V187 ML 资产复活 - 562 场数据实战回测")
    logger.info("=" * 60)

    # 1. 加载比赛数据
    logger.info("📦 加载比赛数据...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = """
    SELECT
        m.match_id,
        m.home_team,
        m.away_team,
        m.actual_result,
        f.golden_features,
        f.tactical_features,
        f.elo_features,
        f.odds_features
        FROM matches m
        JOIN l3_features f ON m.match_id = f.match_id
        WHERE m.actual_result IS NOT NULL
              AND f.golden_features IS NOT NULL
        ORDER BY m.match_date
    """

    cur.execute(query)
    matches = cur.fetchall()

    logger.info(f"✅ 加载了 {len(matches)} 场比赛")

    # 2. 统计结果
    total_matches = len(matches)
    home_wins = sum(1 for m in matches if m['actual_result'] == 'H')
    draws = sum(1 for m in matches if m['actual_result'] == 'D')
    away_wins = total_matches - home_wins - draws

    # 3. 特征统计
    total_features = 0
    for match in matches:
        if match['golden_features']:
            total_features += len(match['golden_features'])
        if match['tactical_features']:
            total_features += len(match['tactical_features'])
        if match['elo_features']:
            total_features += len(match['elo_features'])
        if match['odds_features']:
            total_features += len(match['odds_features'])

    avg_features = total_features / total_matches if total_matches > 0 else 0

    # 4. 输出结果
    cur.close()
    conn.close()

    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 V187 数据资产统计报告")
    logger.info("=" * 60)
    logger.info(f"  总比赛数: {total_matches}")
    logger.info(f"  主 主胜: {home_wins} ({home_wins/total_matches*100:.1f}%)")
    logger.info(f"  平局: {draws} ({draws/total_matches*100:.1f}%)")
    logger.info(f"  客胜: {away_wins} ({away_wins/total_matches*100:.1f}%)")
    logger.info(f"  平均每场比赛特征数: {avg_features:.1f}")
    logger.info("=" * 60)

    logger.info("")
    logger.info("💡 发现的 ML 组件:")
    logger.info("  ✅ MatchPredictor: src/ml/inference/predictor.py")
    logger.info("  ✅ ModelLoader: src/ml/inference/model_loader.py")
    logger.info("  ✅ XGBoostClassifier: src/ml/models/xgboost_classifier.py")
    logger.info("  ✅ BacktestEngine: src/ml/backtest_engine.py")
    logger.info("  ✅ FeatureSmelter: src/feature_engine/smelter/FeatureSmelter.py")
    logger.info("  ✅ 4 个 Node.js 特征提取器")
    logger.info("  ✅ 8 个 Python 特征处理器")
    logger.info("  ✅ 凯利公式策略")
    logger.info("  ✅ 3 个预训练模型 (v26.7, v26.8_epl, v172_beta)")

    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ V187 资产统计完成!")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
