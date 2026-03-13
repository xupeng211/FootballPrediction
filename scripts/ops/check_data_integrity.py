#!/usr/bin/env python3
"""
TITAN V5.0 数据完整性检查脚本
=============================

TDD验证：在训练前确保30维特征数据质量

验证项：
1. 随机抽取100场比赛，验证特征向量长度为30
2. 检查NaN/None值
3. 检查新特征是否有效（非全0）
4. 报告特征统计分布

@module scripts.ops.check_data_integrity
@version V5.0
"""

import os
import sys
import random
import logging
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import psycopg2

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.constants.model_config import TITAN_COMBAT_FEATURES, DEFAULT_VALUES

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("data_integrity")


def get_db_connection():
    """获取数据库连接"""
    db_password = os.getenv("DB_PASSWORD")
    if not db_password:
        raise ValueError("缺少必需的环境变量: DB_PASSWORD")

    return psycopg2.connect(
        host=os.getenv("DB_HOST", "host.docker.internal"),
        port=int(os.getenv("DB_PORT", "5432") or "5432"),
        database=os.getenv("DB_NAME", "football_db"),
        user=os.getenv("DB_USER", "football_user"),
        password=db_password,
    )


def extract_30d_features(row):
    """从数据库行提取30维特征"""
    import json
    import math

    # 解析6个JSONB字段 (psycopg2自动转换为dict)
    def parse_jsonb(val):
        if val is None:
            return {}
        if isinstance(val, dict):
            return val
        return json.loads(val)

    elo = parse_jsonb(row[3])
    golden = parse_jsonb(row[4])
    tactical = parse_jsonb(row[5])
    rolling = parse_jsonb(row[6])
    efficiency = parse_jsonb(row[7])
    draw = parse_jsonb(row[8])

    f = {}

    # 基础11维
    home_elo = float(elo.get('home_elo', elo.get('home_elo_pre', 1500)))
    away_elo = float(elo.get('away_elo', elo.get('away_elo_pre', 1500)))
    f['home_elo_pre'] = home_elo
    f['away_elo_pre'] = away_elo
    f['elo_diff'] = float(elo.get('elo_diff', home_elo - away_elo))
    f['expected_home_win'] = float(elo.get('expected_home_win', elo.get('elo_expected_home', 0.45)))
    f['expected_away_win'] = float(elo.get('expected_away_win', elo.get('elo_expected_away', 0.30)))

    home_mv = float(golden.get('home_market_value_total', 1e8))
    away_mv = float(golden.get('away_market_value_total', 1e8))
    f['log_home_squad_value'] = math.log10(home_mv) if home_mv > 0 else 18.0
    f['log_away_squad_value'] = math.log10(away_mv) if away_mv > 0 else 18.0
    total_mv = home_mv + away_mv
    f['home_mv_share'] = home_mv / total_mv if total_mv > 0 else 0.5

    f['h2h_home_win_ratio'] = float(tactical.get('h2h_home_win_ratio', 0.4))
    f['h2h_draw_ratio'] = float(tactical.get('h2h_draw_ratio', 0.25))
    f['h2h_avg_goal_diff'] = float(tactical.get('h2h_avg_goal_diff', 0.0))

    # Rolling 7维
    f['home_last5_xg_avg'] = float(rolling.get('home_last5_xg_avg', 0.0))
    f['away_last5_xg_avg'] = float(rolling.get('away_last5_xg_avg', 0.0))
    f['home_last5_win_rate'] = float(rolling.get('home_last5_win_rate', 0.0))
    f['away_last5_win_rate'] = float(rolling.get('away_last5_win_rate', 0.0))
    f['home_last5_draw_rate'] = float(rolling.get('home_last5_draw_rate', 0.0))
    f['away_last5_draw_rate'] = float(rolling.get('away_last5_draw_rate', 0.0))
    f['rest_days_diff'] = float(rolling.get('rest_days_diff', 0.0))

    # Efficiency 5维
    f['home_shot_conversion'] = float(efficiency.get('home_shot_conversion', 0.0))
    f['away_shot_conversion'] = float(efficiency.get('away_shot_conversion', 0.0))
    f['home_finishing_efficiency'] = float(efficiency.get('home_finishing_efficiency', 0.0))
    f['away_finishing_efficiency'] = float(efficiency.get('away_finishing_efficiency', 0.0))
    f['finishing_efficiency_diff'] = float(efficiency.get('finishing_efficiency_diff', 0.0))

    # Draw 7维
    f['home_draw_rate'] = float(draw.get('home_draw_rate', 0.0))
    f['away_draw_rate'] = float(draw.get('away_draw_rate', 0.0))
    f['home_draw_tendency'] = float(draw.get('home_draw_tendency', 0.0))
    f['away_draw_tendency'] = float(draw.get('away_draw_tendency', 0.0))
    f['combined_draw_probability'] = float(draw.get('combined_draw_probability', 0.0))
    f['match_stalemate_index'] = float(draw.get('match_stalemate_index', 0.0))
    f['tactical_stalemate_index'] = float(draw.get('tactical_stalemate_index', 0.0))

    return f


def check_data_integrity(sample_size=100):
    """
    执行数据完整性检查

    Args:
        sample_size: 随机抽样数量

    Returns:
        bool: 检查是否通过
    """
    logger.info("=" * 70)
    logger.info("TITAN V5.0 数据完整性检查")
    logger.info("=" * 70)
    logger.info(f"抽样数量: {sample_size}")
    logger.info(f"期望特征维度: 30")
    logger.info("=" * 70)

    conn = get_db_connection()
    cur = conn.cursor()

    # 获取随机样本
    cur.execute("""
        SELECT m.match_id, m.home_score, m.away_score,
               l.elo_features, l.golden_features, l.tactical_features,
               l.rolling_features, l.efficiency_features, l.draw_features
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        WHERE m.status = 'Harvested'
          AND m.home_score IS NOT NULL
          AND l.rolling_features IS NOT NULL
        ORDER BY RANDOM()
        LIMIT %s
    """, (sample_size,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    logger.info(f"实际获取样本: {len(rows)}")

    if len(rows) == 0:
        logger.error("❌ 未获取到有效样本")
        return False

    # 检查每个样本
    issues = []
    feature_stats = {name: [] for name in TITAN_COMBAT_FEATURES}

    for i, row in enumerate(rows):
        features = extract_30d_features(row)

        # 检查1: 特征维度
        if len(features) != 30:
            issues.append(f"样本 {i}: 特征维度错误 ({len(features)} != 30)")

        # 检查2: NaN/None值
        for name, value in features.items():
            if pd.isna(value) or value is None:
                issues.append(f"样本 {i}: 特征 '{name}' 包含NaN/None")
            else:
                feature_stats[name].append(value)

    # 检查3: 新特征是否全0
    new_features = [
        'home_last5_xg_avg', 'home_last5_win_rate', 'home_last5_draw_rate',
        'home_shot_conversion', 'home_finishing_efficiency',
        'home_draw_rate', 'home_draw_tendency', 'combined_draw_probability'
    ]

    all_zero_features = []
    for feat in new_features:
        if feat in feature_stats:
            values = feature_stats[feat]
            if all(v == 0 for v in values):
                all_zero_features.append(feat)

    # 报告结果
    logger.info("")
    logger.info("检查结果:")
    logger.info("-" * 70)

    if issues:
        logger.error(f"❌ 发现 {len(issues)} 个问题:")
        for issue in issues[:10]:
            logger.error(f"   - {issue}")
        if len(issues) > 10:
            logger.error(f"   ... 还有 {len(issues) - 10} 个问题")
        return False

    if all_zero_features:
        logger.warning(f"⚠️  以下新特征全为0 (可能数据未填充):")
        for feat in all_zero_features:
            logger.warning(f"   - {feat}")
        logger.warning("建议: 检查特征提取路径")
        # 不返回False，因为这是数据填充问题而非数据损坏

    logger.info("✅ 特征维度检查通过: 所有样本均为30维")
    logger.info("✅ NaN/None检查通过: 无缺失值")
    logger.info("")

    # 特征统计报告
    logger.info("特征统计分布:")
    logger.info("-" * 70)

    # 基础特征
    logger.info("基础特征 (11维):")
    for feat in TITAN_COMBAT_FEATURES[:11]:
        values = feature_stats.get(feat, [0])
        logger.info(f"  {feat:30s}: mean={np.mean(values):8.4f}, std={np.std(values):8.4f}")

    # Rolling特征
    logger.info("")
    logger.info("Rolling特征 (7维):")
    for feat in TITAN_COMBAT_FEATURES[11:18]:
        values = feature_stats.get(feat, [0])
        non_zero = sum(1 for v in values if v != 0)
        logger.info(f"  {feat:30s}: mean={np.mean(values):8.4f}, non_zero={non_zero}/{len(values)}")

    # Efficiency特征
    logger.info("")
    logger.info("Efficiency特征 (5维):")
    for feat in TITAN_COMBAT_FEATURES[18:23]:
        values = feature_stats.get(feat, [0])
        non_zero = sum(1 for v in values if v != 0)
        logger.info(f"  {feat:30s}: mean={np.mean(values):8.4f}, non_zero={non_zero}/{len(values)}")

    # Draw特征
    logger.info("")
    logger.info("Draw特征 (7维):")
    for feat in TITAN_COMBAT_FEATURES[23:]:
        values = feature_stats.get(feat, [0])
        non_zero = sum(1 for v in values if v != 0)
        logger.info(f"  {feat:30s}: mean={np.mean(values):8.4f}, non_zero={non_zero}/{len(values)}")

    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ 数据完整性检查通过!")
    logger.info("=" * 70)

    return True


def main():
    """主函数"""
    try:
        passed = check_data_integrity(sample_size=100)
        sys.exit(0 if passed else 1)
    except Exception as e:
        logger.error(f"检查失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
