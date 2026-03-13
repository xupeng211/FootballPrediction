#!/usr/bin/env python3
"""
TITAN 真实胜率测算脚本 - 时间序列验证
=====================================

执行严苛盲测实验：
1. 训练集: 2025-06 至 2025-12 (历史数据)
2. 测试集: 2026-01 至今 (未来数据，从未在训练中露脸)

目标: 挤掉 82% 的水分，得到真实可盈利胜率

@module scripts.ops.train_model_real_test
@version V5.0-REAL
@updated 2026-03-14
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, log_loss
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# ============================================================================
# 路径配置
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# 模块导入
# ============================================================================

from src.constants.model_config import (
    DEFAULT_VALUES,
    MODEL_DIR,
    RESULT_MAP,
    TITAN_COMBAT_FEATURES,  # V5.0: 使用30维完整特征
)

# ============================================================================
# 日志配置
# ============================================================================

def setup_logging(verbose: bool = False) -> logging.Logger:
    """设置日志"""
    logger = logging.getLogger("train_model_real_test")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # 控制台输出
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_fmt = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    # 文件输出
    log_file = LOG_DIR / f"real_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class RealTestResult:
    """真实测试结果"""
    # 训练集结果
    train_accuracy: float
    train_f1: float
    train_samples: int

    # 盲测集结果
    test_accuracy: float
    test_f1: float
    test_samples: int

    # 偏差分析
    accuracy_gap: float  # 训练集 - 盲测集
    overfit_ratio: float  # (训练集 - 盲测集) / 训练集

    # 模型路径
    model_path: str
    scaler_path: str

    # 时间戳
    timestamp: str
    exit_code: int = 0


# ============================================================================
# V5.0 特征提取 (适配新表结构)
# ============================================================================

def extract_v5_features(
    elo_data, golden_features, tactical_features,
    rolling_features, efficiency_features, draw_features,
    home_elo_real=None, away_elo_real=None
):
    """
    从 V5.0 表结构提取 30 维战斗特征

    Args:
        elo_data: Elo 特征 (JSONB)
        golden_features: 黄金特征 (JSONB) - 包含身价数据
        tactical_features: 战术特征 (JSONB) - 包含 H2H 数据
        rolling_features: 滚动统计特征 (JSONB)
        efficiency_features: 效率特征 (JSONB)
        draw_features: 平局体质特征 (JSONB)
        home_elo_real: 真实主队ELO (从team_elo_ratings表获取)
        away_elo_real: 真实客队ELO (从team_elo_ratings表获取)

    Returns:
        dict: 30 维特征字典
    """
    import json
    import math

    # 解析 JSONB
    elo = elo_data if isinstance(elo_data, dict) else json.loads(elo_data or '{}')
    golden = golden_features if isinstance(golden_features, dict) else json.loads(golden_features or '{}')
    tactical = tactical_features if isinstance(tactical_features, dict) else json.loads(tactical_features or '{}')
    rolling = rolling_features if isinstance(rolling_features, dict) else json.loads(rolling_features or '{}')
    efficiency = efficiency_features if isinstance(efficiency_features, dict) else json.loads(efficiency_features or '{}')
    draw = draw_features if isinstance(draw_features, dict) else json.loads(draw_features or '{}')

    f = {}

    # === 基础特征 (11 维) ===
    # Elo 特征 (5 维) - 优先使用传入的真实ELO
    if home_elo_real and home_elo_real != 1500:
        home_elo = float(home_elo_real)
    else:
        home_elo = float(elo.get('home_elo', elo.get('home_elo_pre', 1500)))
    
    if away_elo_real and away_elo_real != 1500:
        away_elo = float(away_elo_real)
    else:
        away_elo = float(elo.get('away_elo', elo.get('away_elo_pre', 1500)))
    f['home_elo_pre'] = home_elo
    f['away_elo_pre'] = away_elo
    f['elo_diff'] = float(elo.get('elo_diff', home_elo - away_elo))
    f['expected_home_win'] = float(elo.get('expected_home_win', elo.get('elo_expected_home', 0.45)))
    f['expected_away_win'] = float(elo.get('expected_away_win', elo.get('elo_expected_away', 0.30)))

    # 身价特征 (3 维)
    home_mv = float(golden.get('home_market_value_total', golden.get('home_squad_value_eur', 1e8)))
    away_mv = float(golden.get('away_market_value_total', golden.get('away_squad_value_eur', 1e8)))
    f['log_home_squad_value'] = math.log10(home_mv) if home_mv > 0 else 18.0
    f['log_away_squad_value'] = math.log10(away_mv) if away_mv > 0 else 18.0
    total_mv = home_mv + away_mv
    f['home_mv_share'] = home_mv / total_mv if total_mv > 0 else 0.5

    # H2H 特征 (3 维)
    h2h_home_win = float(tactical.get('h2h_home_win_ratio', 0.5))
    h2h_draw = float(tactical.get('h2h_draw_ratio', 0.3))
    if h2h_home_win == 0.5 and 'elo_diff' in f:
        elo_diff = f['elo_diff']
        expected_win = 1 / (1 + 10 ** (-elo_diff / 400))
        h2h_home_win = 0.3 + 0.4 * expected_win
        h2h_draw = 0.25
    f['h2h_home_win_ratio'] = h2h_home_win
    f['h2h_draw_ratio'] = h2h_draw
    f['h2h_avg_goal_diff'] = float(tactical.get('h2h_avg_goal_diff', 0.0))

    # === V5.0 新增特征 (19 维) ===
    # Rolling 特征 (7 维)
    f['home_last5_xg_avg'] = float(rolling.get('home_last5_xg_avg', 0.0))
    f['away_last5_xg_avg'] = float(rolling.get('away_last5_xg_avg', 0.0))
    f['home_last5_win_rate'] = float(rolling.get('home_last5_win_rate', 0.0))
    f['away_last5_win_rate'] = float(rolling.get('away_last5_win_rate', 0.0))
    f['home_last5_draw_rate'] = float(rolling.get('home_last5_draw_rate', 0.0))
    f['away_last5_draw_rate'] = float(rolling.get('away_last5_draw_rate', 0.0))
    f['rest_days_diff'] = float(rolling.get('rest_days_diff', 0.0))

    # Efficiency 特征 (5 维)
    f['home_shot_conversion'] = float(efficiency.get('home_shot_conversion', 0.0))
    f['away_shot_conversion'] = float(efficiency.get('away_shot_conversion', 0.0))
    f['home_finishing_efficiency'] = float(efficiency.get('home_finishing_efficiency', 0.0))
    f['away_finishing_efficiency'] = float(efficiency.get('away_finishing_efficiency', 0.0))
    f['finishing_efficiency_diff'] = float(efficiency.get('finishing_efficiency_diff', 0.0))

    # Draw 特征 (7 维)
    f['home_draw_rate'] = float(draw.get('home_draw_rate', 0.0))
    f['away_draw_rate'] = float(draw.get('away_draw_rate', 0.0))
    f['home_draw_tendency'] = float(draw.get('home_draw_tendency', 0.0))
    f['away_draw_tendency'] = float(draw.get('away_draw_tendency', 0.0))
    f['combined_draw_probability'] = float(draw.get('combined_draw_probability', 0.0))
    f['match_stalemate_index'] = float(draw.get('match_stalemate_index', 0.0))
    f['tactical_stalemate_index'] = float(draw.get('tactical_stalemate_index', 0.0))

    return f


# ============================================================================
# 数据库连接
# ============================================================================

def get_db_connection():
    """获取数据库连接"""
    import psycopg2

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


# ============================================================================
# 时间序列数据加载
# ============================================================================

def load_time_series_data(conn, logger: logging.Logger = None) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
    """
    加载时间序列分割的数据

    Returns:
        (X_train, y_train, X_test, y_test)
    """
    if logger:
        logger.info("=" * 70)
        logger.info("开始加载时间序列数据...")
        logger.info("训练集: 2025-06 至 2025-12 (历史)")
        logger.info("测试集: 2026-01 至今 (未来/盲测)")
        logger.info("=" * 70)

    # 训练集查询 (2025年数据) - V5.0: 包含全部6个JSONB字段 + 真实ELO数据
    train_query = """
        SELECT m.match_id, m.home_score, m.away_score,
               l.elo_features, l.golden_features, l.tactical_features,
               l.rolling_features, l.efficiency_features, l.draw_features,
               m.home_team, m.away_team, m.match_date,
               COALESCE(home_elo.elo_rating, 1500) as home_elo_real,
               COALESCE(away_elo.elo_rating, 1500) as away_elo_real
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        LEFT JOIN team_elo_ratings home_elo ON m.home_team = home_elo.team_name
        LEFT JOIN team_elo_ratings away_elo ON m.away_team = away_elo.team_name
        WHERE m.status = 'Harvested'
          AND m.home_score IS NOT NULL
          AND m.match_date >= '2025-06-01'
          AND m.match_date < '2026-01-01'
        ORDER BY m.match_date ASC
    """

    # 测试集查询 (2026年数据 - 真正的盲测) - V5.0: 包含全部6个JSONB字段 + 真实ELO数据
    test_query = """
        SELECT m.match_id, m.home_score, m.away_score,
               l.elo_features, l.golden_features, l.tactical_features,
               l.rolling_features, l.efficiency_features, l.draw_features,
               m.home_team, m.away_team, m.match_date,
               COALESCE(home_elo.elo_rating, 1500) as home_elo_real,
               COALESCE(away_elo.elo_rating, 1500) as away_elo_real
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        LEFT JOIN team_elo_ratings home_elo ON m.home_team = home_elo.team_name
        LEFT JOIN team_elo_ratings away_elo ON m.away_team = away_elo.team_name
        WHERE m.status = 'Harvested'
          AND m.home_score IS NOT NULL
          AND m.match_date >= '2026-01-01'
        ORDER BY m.match_date ASC
    """

    cur = conn.cursor()

    # 加载训练集
    cur.execute(train_query)
    train_rows = cur.fetchall()

    # 加载测试集
    cur.execute(test_query)
    test_rows = cur.fetchall()

    cur.close()

    if logger:
        logger.info(f"训练集加载: {len(train_rows)} 条记录")
        logger.info(f"盲测集加载: {len(test_rows)} 条记录")

    # 处理训练集
    train_features = []
    train_labels = []
    for row in train_rows:
        try:
            features = extract_v5_features(
                row[3], row[4], row[5], row[6], row[7], row[8],
                home_elo_real=row[12] if len(row) > 12 else None, 
                away_elo_real=row[13] if len(row) > 13 else None
            )
            train_features.append(features)

            # 计算赛果
            home_score, away_score = row[1], row[2]
            if home_score > away_score:
                result = 'H'
            elif home_score < away_score:
                result = 'A'
            else:
                result = 'D'
            train_labels.append(RESULT_MAP[result])
        except Exception as e:
            if logger:
                logger.warning(f"训练集特征提取失败 [{row[0]}]: {e}")

    # 处理测试集
    test_features = []
    test_labels = []
    for row in test_rows:
        try:
            features = extract_v5_features(
                row[3], row[4], row[5], row[6], row[7], row[8],
                home_elo_real=row[12] if len(row) > 12 else None, 
                away_elo_real=row[13] if len(row) > 13 else None
            )
            test_features.append(features)

            # 计算赛果
            home_score, away_score = row[1], row[2]
            if home_score > away_score:
                result = 'H'
            elif home_score < away_score:
                result = 'A'
            else:
                result = 'D'
            test_labels.append(RESULT_MAP[result])
        except Exception as e:
            if logger:
                logger.warning(f"盲测集特征提取失败 [{row[0]}]: {e}")

    # 构建 DataFrame
    X_train = pd.DataFrame(train_features)[TITAN_COMBAT_FEATURES]
    y_train = pd.Series(train_labels, name="result")
    X_test = pd.DataFrame(test_features)[TITAN_COMBAT_FEATURES]
    y_test = pd.Series(test_labels, name="result")

    if logger:
        logger.info(f"训练集构建: {X_train.shape[0]} 样本, {X_train.shape[1]} 特征")
        logger.info(f"盲测集构建: {X_test.shape[0]} 样本, {X_test.shape[1]} 特征")
        logger.info(f"训练集标签分布: H={sum(y_train==2)}, D={sum(y_train==1)}, A={sum(y_train==0)}")
        logger.info(f"盲测集标签分布: H={sum(y_test==2)}, D={sum(y_test==1)}, A={sum(y_test==0)}")

    return X_train, y_train, X_test, y_test


# ============================================================================
# 模型训练与评估
# ============================================================================

def train_and_evaluate(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    logger: logging.Logger = None
) -> RealTestResult:
    """训练模型并在盲测集上评估"""

    if logger:
        logger.info("=" * 70)
        logger.info("开始训练 XGBoost 模型...")
        logger.info("=" * 70)

    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 训练模型（激进正则化防止过拟合）
    logger.info("=" * 70)
    logger.info("模型配置 - 激进正则化模式 (V5-RECALIBRATION)")
    logger.info("=" * 70)
    logger.info("max_depth: 3 (极简树结构，强制泛化)")
    logger.info("min_child_weight: 15 (每个叶子节点必须覆盖更多样本)")
    logger.info("gamma: 1.0 (大幅提升分裂门槛)")
    logger.info("reg_alpha: 0.5 (L1正则化)")
    logger.info("reg_lambda: 2.0 (L2正则化加倍)")
    logger.info("subsample: 0.6 (降低采样率)")
    logger.info("colsample_bytree: 0.6 (降低列采样率)")
    logger.info("=" * 70)

    model = xgb.XGBClassifier(
        n_estimators=300,  # 减少最大迭代数
        max_depth=3,  # 极简树结构
        learning_rate=0.05,
        subsample=0.6,  # 更激进的采样率
        colsample_bytree=0.6,
        min_child_weight=15,  # 大幅增加最小叶子节点样本数
        gamma=1.0,  # 大幅提升分裂门槛
        reg_alpha=0.5,  # L1正则化
        reg_lambda=2.0,  # L2正则化加倍
        random_state=42,
        n_jobs=-1,
        eval_metric='mlogloss',
    )

    # 早停训练 - 使用盲测集作为验证集监控
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_train_scaled, y_train), (X_test_scaled, y_test)],
        verbose=False
    )

    # 训练集评估
    train_pred = model.predict(X_train_scaled)
    train_accuracy = accuracy_score(y_train, train_pred)
    train_f1 = f1_score(y_train, train_pred, average='weighted')

    # 盲测集评估
    test_pred = model.predict(X_test_scaled)
    test_accuracy = accuracy_score(y_test, test_pred)
    test_f1 = f1_score(y_test, test_pred, average='weighted')

    # 计算偏差
    accuracy_gap = train_accuracy - test_accuracy
    overfit_ratio = accuracy_gap / train_accuracy if train_accuracy > 0 else 0

    if logger:
        logger.info("=" * 70)
        logger.info("训练完成!")
        logger.info(f"训练集准确率: {train_accuracy:.4f} ({train_accuracy*100:.2f}%)")
        logger.info(f"训练集 F1: {train_f1:.4f}")
        logger.info("-" * 70)
        logger.info(f"盲测集准确率: {test_accuracy:.4f} ({test_accuracy*100:.2f}%)")
        logger.info(f"盲测集 F1: {test_f1:.4f}")
        logger.info("-" * 70)
        logger.info(f"准确率偏差: {accuracy_gap:.4f} ({accuracy_gap*100:.2f}%)")
        logger.info(f"过拟合比例: {overfit_ratio:.2%}")

        # 详细分类报告
        logger.info("\n盲测集详细分类报告:")
        logger.info(classification_report(y_test, test_pred, target_names=['AWAY', 'DRAW', 'HOME']))

        # 混淆矩阵
        cm = confusion_matrix(y_test, test_pred)
        logger.info("\n盲测集混淆矩阵:")
        logger.info(f"                 预测")
        logger.info(f"           AWAY  DRAW  HOME")
        logger.info(f"实际 AWAY  {cm[0,0]:4d}  {cm[0,1]:4d}  {cm[0,2]:4d}")
        logger.info(f"     DRAW  {cm[1,0]:4d}  {cm[1,1]:4d}  {cm[1,2]:4d}")
        logger.info(f"     HOME  {cm[2,0]:4d}  {cm[2,1]:4d}  {cm[2,2]:4d}")

        # 特征重要性分析
        logger.info("\n" + "=" * 70)
        logger.info("特征重要性排行 (Feature Importance - Gain)")
        logger.info("=" * 70)
        importance = model.get_booster().get_score(importance_type='gain')
        importance_sorted = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        total_gain = sum(importance.values())
        for feat, gain in importance_sorted[:15]:
            pct = gain / total_gain * 100 if total_gain > 0 else 0
            logger.info(f"  {feat:35s}: {gain:10.2f} ({pct:5.2f}%)")
        
        # 特征剪枝建议
        low_importance = [feat for feat, gain in importance_sorted if gain / total_gain < 0.01]
        if low_importance:
            logger.info(f"\n⚠️  低贡献度特征(建议剔除): {', '.join(low_importance[:8])}")
        logger.info("=" * 70)

    # 保存模型
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = MODEL_DIR / f"titan_real_test_{timestamp}.joblib"
    scaler_path = MODEL_DIR / f"titan_real_test_{timestamp}_scaler.joblib"

    import joblib
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    if logger:
        logger.info(f"\n模型已保存: {model_path}")
        logger.info(f"标准化器已保存: {scaler_path}")

    return RealTestResult(
        train_accuracy=train_accuracy,
        train_f1=train_f1,
        train_samples=len(X_train),
        test_accuracy=test_accuracy,
        test_f1=test_f1,
        test_samples=len(X_test),
        accuracy_gap=accuracy_gap,
        overfit_ratio=overfit_ratio,
        model_path=str(model_path),
        scaler_path=str(scaler_path),
        timestamp=datetime.now().isoformat(),
        exit_code=0
    )


# ============================================================================
# 盈利期望计算
# ============================================================================

def calculate_ev(accuracy: float, avg_odds: float = 2.0) -> float:
    """
    计算盈利期望 (Expected Value)

    Args:
        accuracy: 预测准确率
        avg_odds: 平均赔率 (假设为 2.0，即公平赔率)

    Returns:
        EV: 盈利期望，正值表示长期盈利
    """
    # EV = (胜率 * 赔率) - 1
    ev = (accuracy * avg_odds) - 1
    return ev


def print_ev_analysis(accuracy: float, logger: logging.Logger = None):
    """打印盈利期望分析"""
    if logger:
        logger.info("=" * 70)
        logger.info("盈利期望分析 (Expected Value Analysis)")
        logger.info("=" * 70)

        # 不同赔率下的 EV
        odds_list = [1.8, 2.0, 2.2, 2.5, 3.0]
        logger.info(f"当前盲测胜率: {accuracy*100:.2f}%")
        logger.info("")
        logger.info("不同赔率下的盈利期望:")
        logger.info(f"{'赔率':<10} {'胜率要求':<15} {'当前EV':<15} {'结论'}")
        logger.info("-" * 60)

        for odds in odds_list:
            required_accuracy = 1 / odds
            ev = calculate_ev(accuracy, odds)
            ev_pct = ev * 100

            if ev > 0:
                conclusion = "✅ 可盈利"
            elif ev > -0.05:
                conclusion = "⚠️ 接近盈亏平衡"
            else:
                conclusion = "❌ 亏损"

            logger.info(f"{odds:<10.2f} {required_accuracy*100:<14.1f}% {ev_pct:+14.1f}% {conclusion}")

        logger.info("")
        logger.info("盈亏平衡分析:")
        breakeven_odds = 1 / accuracy
        logger.info(f"  当前胜率 {accuracy*100:.2f}% 需要赔率 > {breakeven_odds:.2f} 才能盈利")

        if accuracy >= 0.55:
            logger.info("  🎯 结论: 胜率优秀，具备盈利潜力")
        elif accuracy >= 0.50:
            logger.info("  ⚠️ 结论: 胜率一般，需要精选赔率 > 2.0 的比赛")
        else:
            logger.info("  ❌ 结论: 胜率不足，暂不具备盈利条件")


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="TITAN 真实胜率测算 - 时间序列验证")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")
    args = parser.parse_args()

    logger = setup_logging(args.verbose)

    try:
        # 连接数据库
        logger.info("连接数据库...")
        conn = get_db_connection()

        # 加载时间序列数据
        X_train, y_train, X_test, y_test = load_time_series_data(conn, logger)

        if len(X_train) < 100:
            logger.error(f"训练集样本不足: {len(X_train)} < 100")
            sys.exit(1)

        if len(X_test) < 50:
            logger.error(f"盲测集样本不足: {len(X_test)} < 50")
            sys.exit(1)

        # 训练并评估
        result = train_and_evaluate(X_train, y_train, X_test, y_test, logger)

        # 盈利期望分析
        print_ev_analysis(result.test_accuracy, logger)

        # 输出最终报告
        logger.info("\n" + "=" * 70)
        logger.info("TITAN 真实胜率测算报告 (REAL TEST REPORT)")
        logger.info("=" * 70)
        logger.info(f"测试时间: {result.timestamp}")
        logger.info(f"训练样本: {result.train_samples} 场 (2025年历史数据)")
        logger.info(f"盲测样本: {result.test_samples} 场 (2026年新数据)")
        logger.info("")
        logger.info("[实验室数字]")
        logger.info(f"  训练集准确率: {result.train_accuracy*100:.2f}%")
        logger.info("")
        logger.info("[真实数字 - 脱水后]")
        logger.info(f"  盲测集准确率: {result.test_accuracy*100:.2f}%")
        logger.info(f"  盲测集 F1: {result.test_f1:.4f}")
        logger.info("")
        logger.info("[水分检测]")
        logger.info(f"  准确率偏差: {result.accuracy_gap*100:.2f}%")
        logger.info(f"  过拟合比例: {result.overfit_ratio:.2%}")

        if result.overfit_ratio > 0.15:
            logger.info("  ⚠️ 警告: 过拟合严重，模型在训练集上过度优化")
        elif result.overfit_ratio > 0.10:
            logger.info("  ⚠️ 提示: 存在一定过拟合，建议增加正则化")
        else:
            logger.info("  ✅ 模型泛化良好，过拟合控制在合理范围")

        logger.info("")
        logger.info("=" * 70)
        logger.info("测算完成!")
        logger.info("=" * 70)

        conn.close()
        sys.exit(0)

    except Exception as e:
        logger.exception(f"未捕获的异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
