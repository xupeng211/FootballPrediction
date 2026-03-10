#!/usr/bin/env python3
"""
TITAN-V4.46.6 终极模型训练管道 (数据泄露修复版)
================================================

【紧急修复】2026-03-10
- 修复: 控球率改为历史平均值，禁止使用本场比赛数据
- 修复: H2H 数据正确填充
- 移除: 所有赛后统计特征 (xG, shots, possession 等)

基于 XGBoost 的足球比赛预测模型训练系统
- 使用 10 个"纯净"赛前特征 (Elo + 身价 + H2H)
- 线性标准化防止模型退化
- 300 轮深度迭代

@version V4.46.6-TITAN-LEAK-FIX
@updated 2026-03-10
"""

import argparse
import json
import logging
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, log_loss
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# 配置常量
# ============================================================================

MODEL_DIR = Path(__file__).parent.parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

# 结果编码
RESULT_MAP = {"H": 2, "D": 1, "A": 0}
RESULT_NAMES = ["AWAY", "DRAW", "HOME"]
RESULT_MAP_REVERSE = {2: "H", 1: "D", 0: "A"}

# ============================================================================
# TITAN 终极特征集 (10维纯净版 - 移除所有赛后数据)
# ============================================================================

# 【修复】移除控球率特征 - 数据泄露风险
# 只保留 Elo (5) + 身价 (3) + H2H (3) = 11 维
TITAN_ULTIMATE_FEATURES = [
    # === Elo 组 (5) - 核心实力指标 ===
    "home_elo_pre",
    "away_elo_pre",
    "elo_diff",
    "expected_home_win",
    "expected_away_win",
    # === 身价组 (3) - 金钱力量 ===
    "log_home_squad_value",
    "log_away_squad_value",
    "home_mv_share",
    # === 交锋组 (3) - 历史克制 (从 h2h_features 提取) ===
    "h2h_home_win_ratio",
    "h2h_draw_ratio",
    "h2h_avg_goal_diff",
]

# 默认值映射
DEFAULT_FEATURE_VALUES = {
    # Elo 组
    "home_elo_pre": 1500.0,
    "away_elo_pre": 1500.0,
    "elo_diff": 0.0,
    "expected_home_win": 0.45,
    "expected_away_win": 0.30,
    # 身价组 (对数化后的默认值)
    "log_home_squad_value": 18.0,
    "log_away_squad_value": 18.0,
    "home_mv_share": 0.50,
    # 交锋组
    "h2h_home_win_ratio": 0.40,
    "h2h_draw_ratio": 0.25,
    "h2h_avg_goal_diff": 0.0,
}


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class TrainingConfig:
    """训练配置"""
    test_size: float = 0.2
    cv_folds: int = 5
    early_stopping_rounds: int = 50
    random_state: int = 42
    min_samples: int = 100


@dataclass
class TrainingResult:
    """训练结果"""
    model_path: str
    scaler_path: str
    accuracy: float
    f1_score: float
    log_loss: float
    cv_mean_accuracy: float
    cv_std_accuracy: float
    training_samples: int
    feature_count: int
    training_time_seconds: float
    feature_importance: Dict[str, float]
    confusion_matrix: List[List[int]]
    classification_report: str


# ============================================================================
# 数据库连接
# ============================================================================

def get_db_connection():
    """获取数据库连接"""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'host.docker.internal'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'football_db'),
        user=os.getenv('DB_USER', 'football_user'),
        password=os.getenv('DB_PASSWORD', 'football_pass'),
        cursor_factory=RealDictCursor
    )


# ============================================================================
# 特征提取工具函数
# ============================================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_log10(value: float, default: float = 0.0) -> float:
    """安全计算 log10，避免 log(0)"""
    try:
        if value is not None and value > 0:
            return math.log10(value)
        return default
    except (ValueError, TypeError):
        return default


def parse_jsonb(data: Any) -> Dict:
    """解析 JSONB 数据"""
    if data is None:
        return {}
    if isinstance(data, str):
        try:
            return json.loads(data)
        except:
            return {}
    if isinstance(data, dict):
        return data
    return {}


# ============================================================================
# TITAN 终极特征提取 (10维纯净版 - 无数据泄露)
# ============================================================================

def extract_elo_features(elo_data: Any) -> Dict[str, float]:
    """
    从 elo_features JSONB 提取 Elo 特征 (5维)
    """
    features = {}
    elo = parse_jsonb(elo_data)

    home_elo = safe_float(elo.get('home_elo_pre', elo.get('home_elo', 1500)), 1500.0)
    away_elo = safe_float(elo.get('away_elo_pre', elo.get('away_elo', 1500)), 1500.0)

    features['home_elo_pre'] = home_elo
    features['away_elo_pre'] = away_elo
    features['elo_diff'] = safe_float(elo.get('elo_diff', home_elo - away_elo))
    features['expected_home_win'] = safe_float(elo.get('expected_home_win', 0.45))
    features['expected_away_win'] = safe_float(elo.get('expected_away_win', 0.30))

    return features


def extract_market_value_features(golden_data: Any) -> Dict[str, float]:
    """
    从 golden_features JSONB 提取身价特征 (3维)

    身价对数化处理: log10(market_value)
    """
    features = {}
    golden = parse_jsonb(golden_data)

    # 提取原始身价 (单位: 欧元)
    home_mv = safe_float(golden.get('home_market_value_total', 0), 0.0)
    away_mv = safe_float(golden.get('away_market_value_total', 0), 0.0)

    # 对数化处理 (防止大身价主导)
    features['log_home_squad_value'] = safe_log10(home_mv, 18.0) if home_mv > 0 else 18.0
    features['log_away_squad_value'] = safe_log10(away_mv, 18.0) if away_mv > 0 else 18.0

    # 身价份额 (主队占比)
    total_mv = home_mv + away_mv
    features['home_mv_share'] = home_mv / total_mv if total_mv > 0 else 0.5

    return features


def extract_h2h_features(h2h_data: Any) -> Dict[str, float]:
    """
    从 h2h_features JSONB 提取交锋特征 (3维)

    【修复】正确从 h2h_features 提取，而不是 tactical_features
    """
    features = {}
    h2h = parse_jsonb(h2h_data)

    # H2H 胜率 - 从 h2h_features 提取
    features['h2h_home_win_ratio'] = safe_float(
        h2h.get('h2h_home_win_ratio',
        h2h.get('home_win_ratio', 0.4)), 0.4
    )
    features['h2h_draw_ratio'] = safe_float(
        h2h.get('h2h_draw_ratio',
        h2h.get('draw_ratio', 0.25)), 0.25
    )
    features['h2h_avg_goal_diff'] = safe_float(
        h2h.get('h2h_avg_goal_diff',
        h2h.get('avg_goal_diff', 0.0)), 0.0
    )

    return features


def extract_titan_ultimate_features(
    elo_data: Any,
    golden_data: Any,
    h2h_data: Any
) -> Dict[str, float]:
    """
    提取完整的 TITAN 终极特征向量 (10维纯净版)

    【数据泄露修复】
    - 移除所有赛后统计 (xG, shots, possession 等)
    - 只使用赛前可用特征 (Elo + 身价 + H2H)
    """
    features = {}

    # 1. Elo 组 (5维)
    features.update(extract_elo_features(elo_data))

    # 2. 身价组 (3维)
    features.update(extract_market_value_features(golden_data))

    # 3. 交锋组 (3维)
    features.update(extract_h2h_features(h2h_data))

    # 确保特征顺序和完整性
    result = {}
    for feat_name in TITAN_ULTIMATE_FEATURES:
        result[feat_name] = features.get(feat_name, DEFAULT_FEATURE_VALUES.get(feat_name, 0.0))

    return result


# ============================================================================
# 数据加载
# ============================================================================

def load_training_data(conn, min_samples: int = 100) -> Tuple[pd.DataFrame, pd.Series]:
    """
    加载训练数据 (TITAN 终极版 - 数据泄露修复)

    【修复】
    - 从 h2h_features 正确提取 H2H 数据
    - 不再使用 tactical_features (包含赛后数据)
    """
    logger.info("开始加载训练数据 (TITAN 终极 10 维纯净版 - 无数据泄露)...")

    # 【修复】使用 h2h_features 而不是 tactical_features
    query = """
    SELECT
        m.match_id,
        m.home_score,
        m.away_score,
        m.actual_result,
        l.elo_features,
        l.golden_features,
        l.h2h_features
    FROM matches m
    INNER JOIN l3_features l ON m.match_id = l.match_id
    WHERE m.status = 'finished'
      AND m.home_score IS NOT NULL
      AND m.away_score IS NOT NULL
      AND m.actual_result IN ('H', 'D', 'A')
      AND l.elo_features IS NOT NULL
      AND l.golden_features IS NOT NULL
    ORDER BY m.match_date DESC
    """

    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()

    logger.info(f"加载了 {len(rows)} 条训练记录")

    if len(rows) < min_samples:
        raise ValueError(f"训练数据不足: 需要至少 {min_samples} 条，当前 {len(rows)} 条")

    # 提取特征和标签
    features_list = []
    labels = []
    h2h_valid_count = 0
    h2h_missing_count = 0

    for row in rows:
        try:
            # 提取 TITAN 终极特征 (10维纯净版)
            features = extract_titan_ultimate_features(
                row.get('elo_features'),
                row.get('golden_features'),
                row.get('h2h_features')  # 【修复】使用正确的 h2h_features
            )

            # 检查 H2H 数据有效性
            h2h_data = parse_jsonb(row.get('h2h_features'))
            if h2h_data:
                h2h_valid_count += 1
            else:
                h2h_missing_count += 1

            # 检查特征有效性 (至少需要 Elo 或身价数据)
            has_elo = features.get('home_elo_pre', 1500) != 1500
            has_mv = features.get('log_home_squad_value', 18.0) != 18.0

            if has_elo or has_mv:
                features_list.append(features)
                labels.append(RESULT_MAP[row['actual_result']])
        except Exception as e:
            logger.warning(f"特征提取失败 [{row['match_id']}]: {e}")
            continue

    logger.info(f"H2H 数据统计: 有效={h2h_valid_count}, 缺失={h2h_missing_count}")

    # 构建 DataFrame
    X = pd.DataFrame(features_list)
    y = pd.Series(labels, name='result')

    # 确保特征列顺序一致
    X = X[TITAN_ULTIMATE_FEATURES]

    logger.info(f"构建数据集: {X.shape[0]} 样本, {X.shape[1]} 特征")
    logger.info(f"标签分布: H={sum(y==2)}, D={sum(y==1)}, A={sum(y==0)}")
    logger.info(f"特征列: {list(X.columns)}")

    # 打印 5 条 H2H 数据样本
    logger.info("=== H2H 数据样本 (前5条) ===")
    for i in range(min(5, len(X))):
        logger.info(f"  样本 {i+1}: h2h_home_win_ratio={X.iloc[i]['h2h_home_win_ratio']:.3f}, "
                   f"h2h_draw_ratio={X.iloc[i]['h2h_draw_ratio']:.3f}, "
                   f"h2h_avg_goal_diff={X.iloc[i]['h2h_avg_goal_diff']:.3f}")

    return X, y


# ============================================================================
# 模型训练
# ============================================================================

def train_xgboost_model(
    X: pd.DataFrame,
    y: pd.Series,
    config: TrainingConfig
) -> Tuple[xgb.XGBClassifier, StandardScaler, Dict[str, Any]]:
    """
    训练 XGBoost 模型（带标准化）

    【修复】
    - 移除过度的 class_weight，使用温和的权重调整
    """
    logger.info("开始训练 XGBoost 终极模型...")
    start_time = datetime.now()

    # 处理缺失值
    X = X.fillna(0).replace([np.inf, -np.inf], 0)

    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=config.test_size,
        stratify=y,
        random_state=config.random_state
    )

    logger.info(f"训练集: {X_train.shape[0]} 样本")
    logger.info(f"测试集: {X_test.shape[0]} 样本")

    # 标准化特征
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    logger.info("特征已标准化 (StandardScaler)")

    # 【修复】温和的类别权重调整，避免过度补偿
    class_counts = np.bincount(y_train)
    n_home = class_counts[2] if len(class_counts) > 2 else 1
    n_draw = class_counts[1] if len(class_counts) > 1 else 1
    n_away = class_counts[0] if len(class_counts) > 0 else 1
    n_total = len(y_train)

    # 使用更温和的权重 (1.2 而不是 1.73)
    sample_weights = np.ones(n_total)
    for i in range(n_total):
        if y_train.iloc[i] == 2:  # HOME
            sample_weights[i] = 1.0
        elif y_train.iloc[i] == 1:  # DRAW
            sample_weights[i] = 1.2  # 【修复】降低平局权重
        else:  # AWAY
            sample_weights[i] = 1.1  # 【修复】降低客胜权重

    logger.info(f"类别分布: HOME={n_home}, DRAW={n_draw}, AWAY={n_away}")
    logger.info(f"类别权重: 平局 x1.2, 客胜 x1.1 (温和调整)")

    # 创建模型
    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=3,
        eval_metric=['mlogloss', 'merror'],
        max_depth=6,
        min_child_weight=3,
        subsample=0.8,
        colsample_bytree=0.8,
        learning_rate=0.05,
        n_estimators=300,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=config.random_state,
        n_jobs=-1,
        verbosity=1,
        early_stopping_rounds=config.early_stopping_rounds
    )

    # 训练
    model.fit(
        X_train_scaled, y_train,
        sample_weight=sample_weights,
        eval_set=[(X_train_scaled, y_train), (X_test_scaled, y_test)],
        verbose=True
    )

    # 交叉验证评估
    cv_scores = cross_validate_model(model, scaler, X, y, config)

    # 在测试集上评估
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)

    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')
    logloss = log_loss(y_test, y_pred_proba)

    training_time = (datetime.now() - start_time).total_seconds()

    # 特征重要性
    feature_importance = dict(zip(
        TITAN_ULTIMATE_FEATURES,
        model.feature_importances_.tolist()
    ))
    feature_importance = dict(sorted(
        feature_importance.items(),
        key=lambda x: x[1],
        reverse=True
    ))

    # 混淆矩阵
    cm = confusion_matrix(y_test, y_pred).tolist()

    # 分类报告
    report = classification_report(y_test, y_pred, target_names=RESULT_NAMES)

    metrics = {
        'accuracy': accuracy,
        'f1_score': f1,
        'log_loss': logloss,
        'cv_mean_accuracy': cv_scores['mean'],
        'cv_std_accuracy': cv_scores['std'],
        'training_samples': X_train.shape[0],
        'feature_count': X.shape[1],
        'training_time_seconds': training_time,
        'feature_importance': feature_importance,
        'confusion_matrix': cm,
        'classification_report': report,
        'best_iteration': getattr(model, 'best_iteration', -1),
    }

    logger.info(f"训练完成! 耗时: {training_time:.1f}s")
    logger.info(f"准确率: {accuracy:.4f}")
    logger.info(f"F1 Score: {f1:.4f}")
    logger.info(f"Log Loss: {logloss:.4f}")
    logger.info(f"CV 准确率: {cv_scores['mean']:.4f} (+/- {cv_scores['std']:.4f})")

    return model, scaler, metrics


def cross_validate_model(
    model_template: xgb.XGBClassifier,
    scaler_template: StandardScaler,
    X: pd.DataFrame,
    y: pd.Series,
    config: TrainingConfig
) -> Dict[str, float]:
    """交叉验证评估"""
    logger.info(f"执行 {config.cv_folds} 折交叉验证...")

    X = X.fillna(0).replace([np.inf, -np.inf], 0)

    skf = StratifiedKFold(
        n_splits=config.cv_folds,
        shuffle=True,
        random_state=config.random_state
    )

    scores = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        # 标准化
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)

        # 克隆模型
        fold_model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=3,
            max_depth=6,
            learning_rate=0.05,
            n_estimators=300,
            random_state=config.random_state,
            n_jobs=-1,
            verbosity=0,
        )

        fold_model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_val_scaled, y_val)],
            verbose=False
        )

        y_pred = fold_model.predict(X_val_scaled)
        acc = accuracy_score(y_val, y_pred)
        scores.append(acc)

        logger.info(f"  Fold {fold + 1}: {acc:.4f}")

    return {
        'mean': np.mean(scores),
        'std': np.std(scores),
        'scores': scores
    }


# ============================================================================
# 模型保存
# ============================================================================

def save_model(
    model: xgb.XGBClassifier,
    scaler: StandardScaler,
    metrics: Dict[str, Any],
    feature_names: List[str],
    output_dir: Path = MODEL_DIR,
    model_name: str = "titan_v4466_ultimate"
) -> Tuple[str, str]:
    """
    保存模型、Scaler 和元数据
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存模型文件
    model_path = output_dir / f"{model_name}.joblib"
    joblib.dump(model, str(model_path))

    # 保存 Scaler
    scaler_path = output_dir / f"{model_name}_scaler.joblib"
    joblib.dump(scaler, str(scaler_path))

    logger.info(f"Scaler 已保存: {scaler_path}")

    # 保存元数据
    metadata = {
        'version': 'V4.46.6-TITAN-LEAK-FIX',
        'created_at': datetime.now().isoformat(),
        'model_type': 'XGBClassifier',
        'feature_names': feature_names,
        'feature_count': len(feature_names),
        'scaler_path': str(scaler_path),
        'result_mapping': RESULT_MAP,
        'result_names': RESULT_NAMES,
        'metrics': {
            'accuracy': metrics['accuracy'],
            'f1_score': metrics['f1_score'],
            'log_loss': metrics['log_loss'],
            'cv_mean_accuracy': metrics['cv_mean_accuracy'],
            'cv_std_accuracy': metrics['cv_std_accuracy'],
            'training_samples': metrics['training_samples'],
            'best_iteration': metrics.get('best_iteration', -1),
        },
        'feature_importance': metrics['feature_importance'],
        'confusion_matrix': metrics['confusion_matrix'],
        'xgb_params': {
            'objective': 'multi:softprob',
            'num_class': 3,
            'max_depth': 6,
            'learning_rate': 0.05,
            'n_estimators': 300,
        },
        'preprocessing': {
            'scaler': 'StandardScaler',
            'missing_value_handling': 'fillna(0)',
            'inf_handling': 'replace with 0',
        },
        'data_leak_fix': {
            'possession_removed': True,
            'h2h_source': 'h2h_features',
            'post_match_stats_removed': True,
        }
    }

    metadata_path = output_dir / f"{model_name}_metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # 保存分类报告
    report_path = output_dir / f"{model_name}_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"TITAN-V4.46.6 终极模型训练报告 (数据泄露修复版)\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"【数据泄露修复】\n")
        f.write(f"  - 移除控球率特征 (赛后数据)\n")
        f.write(f"  - H2H 数据从 h2h_features 正确提取\n")
        f.write(f"  - 移除所有赛后统计 (xG, shots 等)\n\n")
        f.write(f"训练时间: {datetime.now().isoformat()}\n")
        f.write(f"训练样本: {metrics['training_samples']}\n")
        f.write(f"特征数量: {metrics['feature_count']}\n")
        f.write(f"特征列表: {', '.join(feature_names)}\n")
        f.write(f"最佳迭代: {metrics.get('best_iteration', 'N/A')}\n\n")
        f.write(f"性能指标:\n")
        f.write(f"  准确率: {metrics['accuracy']:.4f}\n")
        f.write(f"  F1 Score: {metrics['f1_score']:.4f}\n")
        f.write(f"  Log Loss: {metrics['log_loss']:.4f}\n")
        f.write(f"  CV 准确率: {metrics['cv_mean_accuracy']:.4f} (+/- {metrics['cv_std_accuracy']:.4f})\n\n")
        f.write(f"分类报告:\n")
        f.write(metrics['classification_report'])
        f.write(f"\n混淆矩阵:\n")
        for row in metrics['confusion_matrix']:
            f.write(f"  {row}\n")
        f.write(f"\n特征重要性:\n")
        for i, (name, importance) in enumerate(metrics['feature_importance'].items(), 1):
            f.write(f"  {i:2d}. {name}: {importance:.4f}\n")

    logger.info(f"模型已保存: {model_path}")
    logger.info(f"元数据已保存: {metadata_path}")
    logger.info(f"报告已保存: {report_path}")

    return str(model_path), str(scaler_path)


# ============================================================================
# 实战试射
# ============================================================================

def predict_upcoming_matches(conn, model: xgb.XGBClassifier, scaler: StandardScaler, limit: int = 5) -> List[Dict]:
    """
    预测即将开始的比赛
    """
    logger.info(f"开始实战试射 (预测 {limit} 场即将开始的比赛)...")

    query = """
    SELECT
        m.match_id,
        m.home_team,
        m.away_team,
        m.league_name,
        m.match_date,
        l.elo_features,
        l.golden_features,
        l.h2h_features
    FROM matches m
    INNER JOIN l3_features l ON m.match_id = l.match_id
    WHERE m.match_date > NOW()
      AND m.match_date < NOW() + INTERVAL '7 days'
      AND l.elo_features IS NOT NULL
    ORDER BY m.match_date ASC
    LIMIT %s
    """ % limit

    cursor = conn.cursor()
    cursor.execute(query)
    matches = cursor.fetchall()
    cursor.close()

    if not matches:
        logger.info("无即将开始的比赛")
        return []

    predictions = []
    for match in matches:
        try:
            # 提取特征
            features = extract_titan_ultimate_features(
                match.get('elo_features'),
                match.get('golden_features'),
                match.get('h2h_features')
            )

            # 构建特征向量
            feature_vector = np.array([[features.get(name, 0.0) for name in TITAN_ULTIMATE_FEATURES]])

            # 标准化
            feature_vector_scaled = scaler.transform(feature_vector)

            # 预测
            probs = model.predict_proba(feature_vector_scaled)[0]

            away_prob = float(probs[0])
            draw_prob = float(probs[1])
            home_prob = float(probs[2])

            # 确定推荐
            if home_prob >= draw_prob and home_prob >= away_prob:
                recommendation = "HOME"
                confidence = home_prob
            elif draw_prob >= home_prob and draw_prob >= away_prob:
                recommendation = "DRAW"
                confidence = draw_prob
            else:
                recommendation = "AWAY"
                confidence = away_prob

            predictions.append({
                'match_id': match['match_id'],
                'home_team': match['home_team'],
                'away_team': match['away_team'],
                'league': match['league_name'],
                'match_time': str(match['match_date']),
                'home_prob': f"{home_prob*100:.1f}%",
                'draw_prob': f"{draw_prob*100:.1f}%",
                'away_prob': f"{away_prob*100:.1f}%",
                'recommendation': recommendation,
                'confidence': f"{confidence*100:.1f}%"
            })

        except Exception as e:
            logger.warning(f"预测失败 [{match['match_id']}]: {e}")
            continue

    return predictions


def print_prediction_report(predictions: List[Dict]):
    """打印预测报告"""
    print("\n")
    print("=" * 70)
    print("  TITAN-V4.46.6 终极模型 - 实战试射报告 (数据泄露修复版)")
    print("=" * 70)

    if not predictions:
        print("  无即将开始的比赛")
        return

    for i, pred in enumerate(predictions, 1):
        print(f"\n  {i}. {pred['home_team']} vs {pred['away_team']}")
        print(f"     联赛: {pred['league']}")
        print(f"     时间: {pred['match_time'][:16]}")
        print(f"     概率: 主 {pred['home_prob']} | 平 {pred['draw_prob']} | 客 {pred['away_prob']}")
        print(f"     推荐: {pred['recommendation']} (置信度: {pred['confidence']})")

    print("\n" + "=" * 70)


# ============================================================================
# 主流程
# ============================================================================

def run_training_pipeline(
    config: Optional[TrainingConfig] = None,
    output_name: str = "titan_v4466_ultimate"
) -> TrainingResult:
    """执行完整训练管道"""
    config = config or TrainingConfig()

    logger.info("=" * 60)
    logger.info("TITAN-V4.46.6 终极模型训练管道启动 (数据泄露修复版)")
    logger.info("=" * 60)

    # 1. 连接数据库
    conn = get_db_connection()

    try:
        # 2. 加载数据
        X, y = load_training_data(conn, config.min_samples)

        # 3. 训练模型
        model, scaler, metrics = train_xgboost_model(X, y, config)

        # 4. 保存模型和 Scaler
        model_path, scaler_path = save_model(
            model,
            scaler,
            metrics,
            TITAN_ULTIMATE_FEATURES,
            MODEL_DIR,
            output_name
        )

        # 5. 实战试射
        predictions = predict_upcoming_matches(conn, model, scaler, limit=5)
        print_prediction_report(predictions)

        # 6. 打印特征排名
        print("\n")
        print("=" * 60)
        print("  特征重要性排名")
        print("=" * 60)
        for i, (name, importance) in enumerate(metrics['feature_importance'].items(), 1):
            print(f"  {i:2d}. {name}: {importance:.4f}")

        # 7. 返回结果
        result = TrainingResult(
            model_path=model_path,
            scaler_path=scaler_path,
            accuracy=metrics['accuracy'],
            f1_score=metrics['f1_score'],
            log_loss=metrics['log_loss'],
            cv_mean_accuracy=metrics['cv_mean_accuracy'],
            cv_std_accuracy=metrics['cv_std_accuracy'],
            training_samples=metrics['training_samples'],
            feature_count=metrics['feature_count'],
            training_time_seconds=metrics['training_time_seconds'],
            feature_importance=metrics['feature_importance'],
            confusion_matrix=metrics['confusion_matrix'],
            classification_report=metrics['classification_report']
        )

        logger.info("=" * 60)
        logger.info("训练管道完成!")
        logger.info(f"模型路径: {model_path}")
        logger.info(f"Scaler 路径: {scaler_path}")
        logger.info(f"准确率: {result.accuracy:.2%}")
        logger.info("=" * 60)

        return result

    finally:
        conn.close()


# ============================================================================
# CLI 入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='TITAN-V4.46.6 终极模型训练管道 (数据泄露修复版)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python scripts/ops/train_model.py
  python scripts/ops/train_model.py --name titan_v4466_ultimate
        '''
    )

    parser.add_argument('--name', type=str, default='titan_v4466_ultimate',
                        help='模型输出名称')
    parser.add_argument('--test-size', type=float, default=0.2,
                        help='测试集比例')
    parser.add_argument('--cv-folds', type=int, default=5,
                        help='交叉验证折数')
    parser.add_argument('--min-samples', type=int, default=100,
                        help='最小训练样本数')

    args = parser.parse_args()

    # 构建配置
    config = TrainingConfig(
        test_size=args.test_size,
        cv_folds=args.cv_folds,
        min_samples=args.min_samples
    )

    # 执行训练
    result = run_training_pipeline(
        config=config,
        output_name=args.name
    )

    # 输出结果摘要
    print("\n")
    print("=" * 60)
    print("训练完成!")
    print("=" * 60)
    print(f"模型路径: {result.model_path}")
    print(f"Scaler 路径: {result.scaler_path}")
    print(f"准确率: {result.accuracy:.2%}")
    print(f"F1 Score: {result.f1_score:.4f}")
    print(f"Log Loss: {result.log_loss:.4f}")
    print(f"CV 准确率: {result.cv_mean_accuracy:.2%} (+/- {result.cv_std_accuracy:.2%})")
    print(f"训练样本: {result.training_samples}")
    print(f"特征数量: {result.feature_count}")
    print(f"训练耗时: {result.training_time_seconds:.1f}s")
    print("=" * 60)


if __name__ == '__main__':
    main()
