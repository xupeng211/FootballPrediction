#!/usr/bin/env python3
"""
快速ML验证脚本 - Issue #120核心验证
验证XGBoost/LightGBM环境配置与性能

基于SRS成功经验进行快速验证：
- SRS XGBoost训练：68%准确率，1500个SRS兼容数据点
- 45个特征工程，48个原始特征
"""

import json
import logging
import time
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 检查ML库可用性
try:
    import xgboost as xgb

    XGB_AVAILABLE = True
    logger.info("✅ XGBoost可用")
except ImportError:
    XGB_AVAILABLE = False
    logger.warning("❌ XGBoost不可用")

try:
    import lightgbm as lgb

    LGB_AVAILABLE = True
    logger.info("✅ LightGBM可用")
except ImportError:
    LGB_AVAILABLE = False
    logger.warning("❌ LightGBM不可用")

# SRS基准数据
SRS_BASELINE = {
    "accuracy": 0.68,
    "data_points": 1500,
    "features": 45,
    "distribution": {"draw": 791, "home_win": 480, "away_win": 229},
}


def generate_test_data(n_samples: int = 1000) -> tuple[pd.DataFrame, pd.Series]:
    """生成测试数据，基于SRS经验"""
    logger.info(f"生成测试数据，样本数: {n_samples}")

    np.random.seed(42)

    # 基于SRS的特征工程
    feature_names = [
        "home_team_strength",
        "away_team_strength",
        "home_form",
        "away_form",
        "head_to_head_home",
        "head_to_head_away",
        "home_goals_scored",
        "away_goals_scored",
        "home_goals_conceded",
        "away_goals_conceded",
        "home_win_rate",
        "away_win_rate",
        "home_draw_rate",
        "away_draw_rate",
        "home_loss_rate",
        "away_loss_rate",
        "home_clean_sheets",
        "away_clean_sheets",
        "home_failed_to_score",
        "away_failed_to_score",
        "avg_total_goals",
        "avg_home_goals",
        "avg_away_goals",
        "home_shots_on_target",
        "away_shots_on_target",
        "home_corners",
        "away_corners",
        "home_fouls",
        "away_fouls",
        "home_yellow_cards",
        "away_yellow_cards",
        "home_red_cards",
        "away_red_cards",
        "home_possession",
        "away_possession",
        "travel_distance",
        "rest_days",
        "weather_impact",
        "referee_tendency",
        "stadium_advantage",
        "season_phase",
        "motivation_factor",
        "injury_impact",
        "market_odds_home",
        "market_odds_draw",
        "market_odds_away",
        "betting_volume",
        "momentum_home",
        "momentum_away",
        "xg_home",
        "xg_away",
        "xga_home",
        "xga_away",
    ]

    X = np.random.randn(n_samples, len(feature_names))
    X_df = pd.DataFrame(X, columns=feature_names)

    # 基于SRS分布生成结果
    probabilities = [0.53, 0.32, 0.15]  # draw, home_win, away_win
    results = np.random.choice(["draw",
    "home_win",
    "away_win"],
    size=n_samples,
    p=probabilities)
    y = pd.Series(results)

    logger.info(f"数据分布: {y.value_counts().to_dict()}")
    return X_df, y


def test_xgboost(
    X_train: pd.DataFrame, X_test: pd.DataFrame, y_train: pd.Series, y_test: pd.Series
) -> dict[str, Any]:
    """测试XGBoost模型"""
    if not XGB_AVAILABLE:
        return {"error": "XGBoost不可用"}

    logger.info("🚀 测试XGBoost模型...")

    start_time = time.time()

    # 数据预处理
    scaler = StandardScaler()
    label_encoder = LabelEncoder()

    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    y_train_encoded = label_encoder.fit_transform(y_train)
    y_test_encoded = label_encoder.transform(y_test)

    # XGBoost模型
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        eval_metric="mlogloss",
        use_label_encoder=False,
    )

    model.fit(X_train_scaled, y_train_encoded)
    training_time = time.time() - start_time

    # 预测
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test_encoded, y_pred)

    # 特征重要性
    feature_importance = dict(zip(X_train.columns, model.feature_importances_, strict=False))
    top_features = sorted(feature_importance.items(),
    key=lambda x: x[1],
    reverse=True)[:10]

    result = {
        "model": "XGBoost",
        "accuracy": accuracy,
        "training_time": training_time,
        "feature_importance": top_features,
        "improvement_over_srs": (accuracy - SRS_BASELINE["accuracy"])
        / SRS_BASELINE["accuracy"]
        * 100,
    }

    logger.info(f"  XGBoost准确率: {accuracy:.4f} (训练时间: {training_time:.2f}s)")
    logger.info(f"  相对SRS改进: {result['improvement_over_srs']:+.2f}%")

    return result


def test_lightgbm(
    X_train: pd.DataFrame, X_test: pd.DataFrame, y_train: pd.Series, y_test: pd.Series
) -> dict[str, Any]:
    """测试LightGBM模型"""
    if not LGB_AVAILABLE:
        return {"error": "LightGBM不可用"}

    logger.info("🚀 测试LightGBM模型...")

    start_time = time.time()

    # 数据预处理
    scaler = StandardScaler()
    label_encoder = LabelEncoder()

    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    y_train_encoded = label_encoder.fit_transform(y_train)
    y_test_encoded = label_encoder.transform(y_test)

    # LightGBM模型
    model = lgb.LGBMClassifier(
        n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42, verbose=-1
    )

    model.fit(X_train_scaled, y_train_encoded)
    training_time = time.time() - start_time

    # 预测
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test_encoded, y_pred)

    # 特征重要性
    feature_importance = dict(zip(X_train.columns, model.feature_importances_, strict=False))
    top_features = sorted(feature_importance.items(),
    key=lambda x: x[1],
    reverse=True)[:10]

    result = {
        "model": "LightGBM",
        "accuracy": accuracy,
        "training_time": training_time,
        "feature_importance": top_features,
        "improvement_over_srs": (accuracy - SRS_BASELINE["accuracy"])
        / SRS_BASELINE["accuracy"]
        * 100,
    }

    logger.info(f"  LightGBM准确率: {accuracy:.4f} (训练时间: {training_time:.2f}s)")
    logger.info(f"  相对SRS改进: {result['improvement_over_srs']:+.2f}%")

    return result


def main():
    """主验证函数"""
    logger.info("=" * 60)
    logger.info("🚀 快速ML验证开始")
    logger.info("Issue #120: ML模型训练和真实数据集成")
    logger.info("=" * 60)

    # 环境检查
    logger.info("📊 环境状态检查:")
    logger.info(f"  XGBoost: {'✅ 可用' if XGB_AVAILABLE else '❌ 不可用'}")
    logger.info(f"  LightGBM: {'✅ 可用' if LGB_AVAILABLE else '❌ 不可用'}")

    if not XGB_AVAILABLE and not LGB_AVAILABLE:
        logger.error("❌ 没有可用的ML库，验证失败")
        return

    # 生成测试数据
    logger.info("📊 生成测试数据...")
    X, y = generate_test_data(n_samples=1000)

    # 数据分割
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    logger.info(f"训练集: {len(X_train)} 样本, 测试集: {len(X_test)} 样本")

    # 测试模型
    results = []

    if XGB_AVAILABLE:
        xgb_result = test_xgboost(X_train, X_test, y_train, y_test)
        results.append(xgb_result)

    if LGB_AVAILABLE:
        lgb_result = test_lightgbm(X_train, X_test, y_train, y_test)
        results.append(lgb_result)

    # 生成报告
    logger.info("=" * 60)
    logger.info("📋 验证结果汇总")
    logger.info("=" * 60)

    validation_report = {
        "timestamp": datetime.now().isoformat(),
        "environment": {"xgboost_available": XGB_AVAILABLE, "lightgbm_available": LGB_AVAILABLE},
        "data_info": {
            "total_samples": len(X),
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "features": len(X.columns),
            "distribution": y.value_counts().to_dict(),
        },
        "srs_baseline": SRS_BASELINE,
        "results": results,
        "summary": {},
    }

    # 找出最佳模型
    if results:
        best_result = max(results, key=lambda x: x.get("accuracy", 0))
        validation_report["summary"] = {
            "best_model": best_result["model"],
            "best_accuracy": best_result["accuracy"],
            "improvement_over_srs": best_result["improvement_over_srs"],
            "models_tested": len(results),
        }

        logger.info(f"🏆 最佳模型: {best_result['model']}")
        logger.info(f"📊 最佳准确率: {best_result['accuracy']:.4f}")
        logger.info(f"📈 相对SRS改进: {best_result['improvement_over_srs']:+.2f}%")

    # 保存结果
    try:
        with open("quick_ml_validation_results.json", "w", encoding="utf-8") as f:
            json.dump(validation_report, f, indent=2, ensure_ascii=False, default=str)
        logger.info("📄 验证结果已保存到 quick_ml_validation_results.json")
    except Exception as e:
        logger.error(f"保存验证结果失败: {e}")

    logger.info("=" * 60)
    logger.info("🎉 快速ML验证完成!")
    logger.info("=" * 60)

    return validation_report


if __name__ == "__main__":
    results = main()
