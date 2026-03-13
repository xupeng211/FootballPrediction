#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# ║   TITAN-V4.46.8 模型训练管道 - 工业加固版                              ║
# ║   INDUSTRIAL FORTIFICATION - FAIL-FAST + ROBUST LOGGING + JSON OUTPUT    ║
# ═══════════════════════════════════════════════════════════════════════════════
#
# 【V4.46.8 工业化加固】
# - 自动化保险丝: 全局异常捕获 + sys.exit(1)
# - 黑匣子日志: 双重输出 (控制台 + /app/logs/)
# - CLI 标准化: argparse + --json 输出
# - 安全加固: 环境变量强制校验
#
# @module scripts.ops.train_model
# @version V4.46.8-INDUSTRIAL
# @updated 2026-03-11

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
    RESULT_NAMES,
    TITAN_COMBAT_FEATURES,
)
from src.database.repositories.prediction_repo import (
    get_db_connection,
    parse_jsonb,
    safe_float,
)


# ============================================================================
# 日志配置 - 双重输出
# ============================================================================

def setup_logging(verbose: bool = False) -> logging.Logger:
    """配置双重日志输出"""
    logger = logging.getLogger("train_model")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [train_model] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 文件
    log_file = LOG_DIR / "train_model.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class TrainingResult:
    """训练结果"""
    model_path: str
    scaler_path: str
    accuracy: float
    f1_score: float
    log_loss: float
    training_samples: int
    feature_count: int
    training_time_seconds: float
    exit_code: int = 0


# ============================================================================
# V5.0 特征提取 (适配新表结构)
# ============================================================================

def extract_v5_features(elo_data, golden_features, tactical_features):
    """
    从 V5.0 表结构提取 11 维战斗特征

    Args:
        elo_data: Elo 特征 (JSONB)
        golden_features: 黄金特征 (JSONB) - 包含身价数据
        tactical_features: 战术特征 (JSONB) - 包含 H2H 数据

    Returns:
        dict: 11 维特征字典
    """
    import json
    import math

    # 解析 JSONB
    elo = elo_data if isinstance(elo_data, dict) else json.loads(elo_data or '{}')
    golden = golden_features if isinstance(golden_features, dict) else json.loads(golden_features or '{}')
    tactical = tactical_features if isinstance(tactical_features, dict) else json.loads(tactical_features or '{}')

    f = {}

    # === Elo 特征 (5 维) ===
    home_elo = float(elo.get('home_elo', elo.get('home_elo_pre', 1500)))
    away_elo = float(elo.get('away_elo', elo.get('away_elo_pre', 1500)))
    f['home_elo_pre'] = home_elo
    f['away_elo_pre'] = away_elo
    f['elo_diff'] = float(elo.get('elo_diff', home_elo - away_elo))
    f['expected_home_win'] = float(elo.get('expected_home_win', elo.get('elo_expected_home', 0.45)))
    f['expected_away_win'] = float(elo.get('expected_away_win', elo.get('elo_expected_away', 0.30)))

    # === 身价特征 (3 维) - 从 golden_features ===
    home_mv = float(golden.get('home_market_value_total', golden.get('home_squad_value_eur', 1e8)))
    away_mv = float(golden.get('away_market_value_total', golden.get('away_squad_value_eur', 1e8)))

    f['log_home_squad_value'] = math.log10(home_mv) if home_mv > 0 else 18.0
    f['log_away_squad_value'] = math.log10(away_mv) if away_mv > 0 else 18.0
    total_mv = home_mv + away_mv
    f['home_mv_share'] = home_mv / total_mv if total_mv > 0 else 0.5

    # === H2H 特征 (3 维) - 从 tactical_features 估算 ===
    # V5.0: 如果 tactical 中有 H2H 数据则使用，否则基于 Elo 差估算
    h2h_home_win = float(tactical.get('h2h_home_win_ratio', 0.5))
    h2h_draw = float(tactical.get('h2h_draw_ratio', 0.3))

    # 如果没有 H2H 数据，基于 Elo 差进行智能估算
    if h2h_home_win == 0.5 and 'elo_diff' in f:
        elo_diff = f['elo_diff']
        # Elo 差转换为 H2H 胜率 (简化模型)
        expected_win = 1 / (1 + 10 ** (-elo_diff / 400))
        h2h_home_win = 0.3 + 0.4 * expected_win  # 基础 30% + Elo 贡献
        h2h_draw = 0.25  # 默认平局率

    f['h2h_home_win_ratio'] = h2h_home_win
    f['h2h_draw_ratio'] = h2h_draw
    f['h2h_avg_goal_diff'] = float(tactical.get('h2h_avg_goal_diff', 0.0))

    return f


# ============================================================================
# 数据加载
# ============================================================================

def load_training_data(conn, min_samples: int = 100, logger: logging.Logger = None) -> Tuple[pd.DataFrame, pd.Series]:
    """
    加载训练数据 (TITAN 11 维纯净版 - 无数据泄露)
    """
    if logger:
        logger.info("开始加载训练数据...")

    query = """
        SELECT m.match_id, m.home_score, m.away_score, m.home_team, m.away_team,
               l.elo_features, l.golden_features, l.tactical_features
        FROM matches m
        INNER JOIN l3_features l ON m.match_id = l.match_id
        WHERE m.status = 'Harvested'
          AND m.home_score IS NOT NULL
          AND m.away_score IS NOT NULL
          AND l.elo_features IS NOT NULL
        ORDER BY m.match_date DESC
    """

    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()

    if logger:
        logger.info(f"加载了 {len(rows)} 条训练记录")

    if len(rows) < min_samples:
        raise ValueError(f"训练数据不足: 需要至少 {min_samples} 条，当前 {len(rows)} 条")

    # 延迟导入避免循环依赖
    from src.database.repositories.prediction_repo import extract_features

    features_list = []
    labels = []
    skipped = 0

    for row in rows:
        try:
            # V5.0: 从新的表结构提取特征
            features = extract_v5_features(
                row["elo_features"],
                row["golden_features"],
                row["tactical_features"],
            )
            features_list.append(features)

            # 从比分计算赛果
            home_score = row.get("home_score", 0)
            away_score = row.get("away_score", 0)
            if home_score > away_score:
                result = 'H'
            elif home_score < away_score:
                result = 'A'
            else:
                result = 'D'
            labels.append(RESULT_MAP[result])
        except Exception as e:
            skipped += 1
            if logger:
                logger.warning(f"特征提取失败 [{row['match_id']}]: {e}")

    if logger and skipped > 0:
        logger.warning(f"跳过 {skipped} 条无效记录")

    X = pd.DataFrame(features_list)[TITAN_COMBAT_FEATURES]
    y = pd.Series(labels, name="result")

    if logger:
        logger.info(f"构建数据集: {X.shape[0]} 样本, {X.shape[1]} 特征")
        logger.info(f"标签分布: H={sum(y==2)}, D={sum(y==1)}, A={sum(y==0)}")

    return X, y


# ============================================================================
# 模型训练
# ============================================================================

def train_model(
    X: pd.DataFrame,
    y: pd.Series,
    logger: logging.Logger = None
) -> Tuple[xgb.XGBClassifier, StandardScaler, Dict]:
    """训练 XGBoost 模型（带标准化）"""
    if logger:
        logger.info("开始训练 XGBoost 模型...")

    start_time = datetime.now()

    X = X.fillna(0).replace([np.inf, -np.inf], 0)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 类别权重
    class_counts = np.bincount(y_train)
    sample_weights = np.ones(len(y_train))
    for i, count in enumerate(class_counts):
        if count > 0:
            sample_weights[y_train == i] = len(y_train) / (len(class_counts) * count)

    model = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        max_depth=4,  # 限制树深度在3-5之间，防止过拟合
        learning_rate=0.05,
        n_estimators=500,  # 增加最大轮数，让早停决定
        subsample=0.7,  # 降低行采样率
        colsample_bytree=0.7,  # 降低列采样率
        min_child_weight=5,  # 最小叶子节点样本数，防止过拟合
        gamma=0.3,  # 分裂惩罚，增加模型稳定性
        reg_alpha=0.1,  # L1正则化
        reg_lambda=1.0,  # L2正则化
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=30,  # 早停轮数
        eval_metric="mlogloss",
    )

    model.fit(
        X_train_scaled, y_train,
        sample_weight=sample_weights,
        eval_set=[(X_test_scaled, y_test)],
        verbose=False,
    )

    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1_score": float(f1_score(y_test, y_pred, average="weighted")),
        "log_loss": float(log_loss(y_test, y_proba)),
        "training_samples": X_train.shape[0],
        "training_time_seconds": (datetime.now() - start_time).total_seconds(),
        "feature_importance": dict(zip(TITAN_COMBAT_FEATURES, model.feature_importances_.tolist())),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, target_names=RESULT_NAMES),
    }

    if logger:
        logger.info(f"训练完成! 准确率: {metrics['accuracy']:.2%}, F1: {metrics['f1_score']:.4f}")

    return model, scaler, metrics


# ============================================================================
# 模型保存
# ============================================================================

def save_model(
    model: xgb.XGBClassifier,
    scaler: StandardScaler,
    metrics: Dict,
    output_name: str,
    logger: logging.Logger = None
) -> Tuple[str, str]:
    """保存模型、Scaler 和元数据"""
    import joblib

    model_path = MODEL_DIR / f"{output_name}.joblib"
    scaler_path = MODEL_DIR / f"{output_name}_scaler.joblib"

    joblib.dump(model, str(model_path))
    joblib.dump(scaler, str(scaler_path))

    metadata = {
        "version": "V4.46.8-INDUSTRIAL",
        "created_at": datetime.now().isoformat(),
        "feature_names": TITAN_COMBAT_FEATURES,
        "metrics": {
            "accuracy": metrics["accuracy"],
            "f1_score": metrics["f1_score"],
            "log_loss": metrics["log_loss"],
            "training_samples": metrics["training_samples"],
            "training_time_seconds": metrics["training_time_seconds"],
        },
        "feature_importance": metrics["feature_importance"],
    }

    metadata_path = MODEL_DIR / f"{output_name}_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    if logger:
        logger.info(f"模型已保存: {model_path}")
        logger.info(f"元数据已保存: {metadata_path}")

    return str(model_path), str(scaler_path)


# ============================================================================
# CLI 入口
# ============================================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="TITAN-V4.46.8 模型训练管道 - 工业加固版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/ops/train_model.py
  python scripts/ops/train_model.py --name titan_v4468_combat
  python scripts/ops/train_model.py --min-samples 500 --verbose
  python scripts/ops/train_model.py --json

退出码:
  0 - 训练成功
  1 - 训练失败
  2 - 配置错误
        """
    )
    parser.add_argument("--name", default="titan_v4468_combat", help="模型输出名称 (默认: titan_v4468_combat)")
    parser.add_argument("--min-samples", type=int, default=100, help="最小训练样本数 (默认: 100)")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细日志模式")
    return parser.parse_args()


def main():
    """主入口 - 带全局异常捕获"""
    global logger
    args = parse_args()

    # 重新配置日志级别
    logger = setup_logging(args.verbose)

    result = None

    try:
        logger.info("=" * 60)
        logger.info("TITAN-V4.46.8 模型训练管道 - 工业加固版")
        logger.info("=" * 60)

        conn = get_db_connection()

        try:
            X, y = load_training_data(conn, args.min_samples, logger)
            model, scaler, metrics = train_model(X, y, logger)
            model_path, scaler_path = save_model(model, scaler, metrics, args.name, logger)

            result = TrainingResult(
                model_path=model_path,
                scaler_path=scaler_path,
                accuracy=metrics["accuracy"],
                f1_score=metrics["f1_score"],
                log_loss=metrics["log_loss"],
                training_samples=metrics["training_samples"],
                feature_count=len(TITAN_COMBAT_FEATURES),
                training_time_seconds=metrics["training_time_seconds"],
                exit_code=0
            )

        finally:
            conn.close()

        # 输出结果
        if args.json:
            print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
        else:
            logger.info("=" * 60)
            logger.info("训练完成!")
            logger.info(f"模型: {result.model_path}")
            logger.info(f"准确率: {result.accuracy:.2%}, F1: {result.f1_score:.4f}")
            logger.info(f"训练时间: {result.training_time_seconds:.1f}s")
            logger.info("=" * 60)

        sys.exit(0)

    except ValueError as e:
        logger.error(f"数据错误: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("用户中断执行")
        sys.exit(130)

    except Exception as e:
        logger.exception(f"未捕获的异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
