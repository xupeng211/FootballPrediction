#!/usr/bin/env python3
"""
V41.470 Expert Heterogeneity - 软投票集成训练
================================================

V41.470 核心升级：
1. 软投票机制：弃用 Hard Voting，使用概率加权平均
   - CatBoost (0.5) + XGBoost (0.3) + LightGBM (0.2)
2. 信心指数过滤：熵值高时放弃预测
3. 联赛等级特征：is_top_5_league
4. 目标准确率：50%+

Author: V41.470 ML Team
Version: V41.470 "Expert Heterogeneity"
Date: 2026-01-21
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import psycopg2
from catboost import CatBoostClassifier, Pool
from lightgbm import LGBMClassifier
from psycopg2.extras import RealDictCursor
from scipy.stats import entropy as scipy_entropy
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from src.config_unified import get_settings
from src.processors.feature_interaction_engine import FeatureInteractionEngine
from src.processors.pure_feature_filter import PureFeatureFilter

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class V41_470Config:
    """V41.470 配置"""

    # 数据分割
    train_ratio: float = 0.6
    val_ratio: float = 0.2
    test_ratio: float = 0.2

    # 软投票权重
    catboost_weight: float = 0.5
    xgboost_weight: float = 0.3
    lightgbm_weight: float = 0.2

    # 信心指数过滤（熵值阈值）
    entropy_threshold: float = 0.8  # 熵值 >= 0.8 时放弃预测
    min_confidence_ratio: float = 0.7  # 至少 70% 的比赛要有信心预测

    # 标签映射
    label_mapping: dict = field(default_factory=lambda: {"A": 0, "D": 1, "H": 2})

    # Top 5 联赛（欧足联排名）
    TOP_5_LEAGUES = {
        "Premier League",
        "La Liga",
        "Bundesliga",
        "Serie A",
        "Ligue 1",
    }


DEFAULT_CONFIG = V41_470Config()


# =============================================================================
# Soft Voting Ensemble
# =============================================================================

class SoftVotingEnsemble:
    """
    V41.470 软投票集成

    策略：
    - 概率加权平均：CatBoost(0.5) + XGBoost(0.3) + LightGBM(0.2)
    - 信心指数过滤：熵值高时放弃预测
    - 只对有信心的预测做最终决策
    """

    def __init__(
        self,
        xgb_model: XGBClassifier,
        catboost_model: CatBoostClassifier,
        lgb_model: LGBMClassifier,
        config: Optional[V41_470Config] = None
    ):
        self.xgb_model = xgb_model
        self.catboost_model = catboost_model
        self.lgb_model = lgb_model
        self.config = config or DEFAULT_CONFIG

        # 验证权重和为 1
        total_weight = (
            self.config.catboost_weight +
            self.config.xgboost_weight +
            self.config.lightgbm_weight
        )
        if not np.isclose(total_weight, 1.0, atol=0.01):
            logger.warning(f"Weights sum to {total_weight:.3f}, normalizing...")
            self.config.catboost_weight /= total_weight
            self.config.xgboost_weight /= total_weight
            self.config.lightgbm_weight /= total_weight

    def predict(self, X: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        """
        软投票预测（带信心过滤）

        Returns:
            (predictions, metadata)
        """
        # 获取各模型概率预测
        xgb_proba = self.xgb_model.predict_proba(X)
        cat_proba = self.catboost_model.predict_proba(X)
        lgb_proba = self.lgb_model.predict_proba(X)

        # 加权平均
        weighted_proba = (
            self.config.catboost_weight * cat_proba +
            self.config.xgboost_weight * xgb_proba +
            self.config.lightgbm_weight * lgb_proba
        )

        # 计算熵值（不确定性度量）
        entropies = np.array([
            scipy_entropy(proba) for proba in weighted_proba
        ])

        # 找出有信心的预测（熵值 < 阈值）
        confident_mask = entropies < self.config.entropy_threshold

        # 对有信心的样本，取 argmax
        predictions = np.full(len(X), -1, dtype=np.int32)  # -1 表示无信心
        predictions[confident_mask] = np.argmax(weighted_proba[confident_mask], axis=1)

        metadata = {
            "confidence_ratio": np.mean(confident_mask),
            "mean_entropy": np.mean(entropies),
            "std_entropy": np.std(entropies),
            "no_confidence_count": np.sum(~confident_mask),
        }

        return predictions, metadata

    def predict_with_fallback(
        self,
        X: np.ndarray,
        fallback_pred: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """
        软投票预测（带回退策略）

        对于无信心的样本，使用 fallback_pred
        """
        predictions, metadata = self.predict(X)

        # 应用回退策略
        no_confidence = (predictions == -1)
        predictions[no_confidence] = fallback_pred[no_confidence]

        metadata["fallback_used"] = np.sum(no_confidence) / len(X)

        return predictions, metadata


# =============================================================================
# Data Loader (with League Tiering)
# =============================================================================

class V41_470DataLoader:
    """V41.470 数据加载器 - 带联赛等级特征"""

    def __init__(self, config: Optional[V41_470Config] = None):
        self.config = config or DEFAULT_CONFIG
        self.settings = get_settings()
        self.filter = PureFeatureFilter(strict_mode=True)
        self.interaction_engine = FeatureInteractionEngine()
        self._conn = None

    def _get_connection(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.settings.database.host,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._conn

    def load_matches(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        """加载比赛数据"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                m.match_id,
                m.league_name,
                m.season,
                m.home_team,
                m.away_team,
                m.actual_result,
                m.technical_features,
                m.golden_features
            FROM matches m
            WHERE m.actual_result IS NOT NULL
              AND m.technical_features IS NOT NULL
            ORDER BY m.match_date DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        matches = cursor.fetchall()
        cursor.close()

        logger.info(f"Loaded {len(matches)} matches")
        return matches

    def prepare_features(
        self,
        matches: list[dict[str, Any]],
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """
        准备特征 - 添加联赛等级特征

        Returns:
            X, y, feature_names
        """
        self.filter.reset_stats()

        X_list = []
        y_list = []
        all_feature_names = set()

        for match in matches:
            # 解析原始特征
            tech_features = match.get("technical_features") or {}
            if tech_features and isinstance(tech_features, str):
                tech_features = json.loads(tech_features)

            golden_features = match.get("golden_features") or {}
            if golden_features and isinstance(golden_features, str):
                golden_features = json.loads(golden_features)

            # 合并基础特征
            combined = dict(tech_features)
            if golden_features:
                combined.update(golden_features)

            # V41.470: 添加联赛等级特征
            league_name = match.get("league_name", "")
            combined["is_top_5_league"] = 1.0 if league_name in self.config.TOP_5_LEAGUES else 0.0

            # 使用 PureFeatureFilter 过滤
            filtered_features = self.filter.filter_features(combined, verbose=False)

            if not filtered_features:
                continue

            # 创建交互特征
            interaction_features = self.interaction_engine.create_all_interactions(filtered_features)
            filtered_features.update(interaction_features)

            X_list.append(filtered_features)
            all_feature_names.update(filtered_features.keys())

            result = match.get("actual_result")
            if result in self.config.label_mapping:
                y_list.append(self.config.label_mapping[result])

        # 统一特征顺序
        feature_names = sorted(all_feature_names)

        # 构建特征矩阵
        X_list_clean = []
        for feat in X_list:
            row = []
            for name in feature_names:
                val = feat.get(name, 0)
                if isinstance(val, (dict, list)):
                    val = 0
                elif val is None:
                    val = 0
                else:
                    try:
                        val = float(val)
                    except (TypeError, ValueError):
                        val = 0
                row.append(val)
            X_list_clean.append(row)

        X = np.array(X_list_clean, dtype=np.float32)
        y = np.array(y_list, dtype=np.int32)

        logger.info(f"Prepared {len(X)} samples, {len(feature_names)} features")
        logger.info(f"Filter rate: {self.filter.get_filter_rate():.1%}")

        return X, y, feature_names

    def cleanup(self):
        if self._conn and not self._conn.closed:
            self._conn.close()


# =============================================================================
# Main Trainer
# =============================================================================

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print()
    print("=" * 80)
    print("V41.470 Expert Heterogeneity - 软投票集成训练")
    print("=" * 80)
    print()

    loader = V41_470DataLoader()

    try:
        # 加载数据
        matches = loader.load_matches(limit=8000)

        if len(matches) < 100:
            logger.error(f"样本不足 ({len(matches)} < 100)")
            return

        X, y, feature_names = loader.prepare_features(matches)

        logger.info(f"  样本数: {len(X)}, 特征维度: {len(feature_names)}")

        # 检查 is_top_5_league 特征
        if "is_top_5_league" in feature_names:
            idx = feature_names.index("is_top_5_league")
            top_5_ratio = np.sum(X[:, idx]) / len(X)
            logger.info(f"  Top 5 联赛占比: {top_5_ratio:.1%}")

        # 三路分割
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=0.25, random_state=42, stratify=y_temp
        )

        logger.info(f"  Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

        # Step 1: 训练基础模型
        print("\n  训练 XGBoost...")
        xgb_model = XGBClassifier(
            max_depth=6, learning_rate=0.05, n_estimators=200,
            random_state=42, eval_metric="mlogloss", use_label_encoder=False
        )
        xgb_model.fit(X_train, y_train)
        xgb_acc = accuracy_score(y_test, xgb_model.predict(X_test))

        print("  训练 CatBoost...")
        train_pool = Pool(X_train, y_train, feature_names=feature_names)
        val_pool = Pool(X_val, y_val, feature_names=feature_names)
        cat_model = CatBoostClassifier(
            depth=7, learning_rate=0.05, iterations=500,
            random_seed=42, loss_function="MultiClass",
            eval_metric="Accuracy", verbose=False
        )
        cat_model.fit(train_pool, eval_set=val_pool, verbose=False)
        cat_acc = accuracy_score(y_test, cat_model.predict(X_test))

        print("  训练 LightGBM...")
        lgb_model = LGBMClassifier(
            max_depth=7, learning_rate=0.05, n_estimators=200,
            random_state=42, verbose=-1
        )
        lgb_model.fit(X_train, y_train)
        lgb_acc = accuracy_score(y_test, lgb_model.predict(X_test))

        # Step 2: 创建软投票集成
        print("\n  创建 Soft Voting Ensemble...")
        ensemble = SoftVotingEnsemble(xgb_model, cat_model, lgb_model)

        # Step 3: 评估软投票（无回退）
        print("\n  评估软投票（无回退）...")
        y_pred_soft, metadata_soft = ensemble.predict(X_test)

        # 只计算有信心的预测
        confident_mask = y_pred_soft != -1
        if np.sum(confident_mask) > 0:
            accuracy_soft = accuracy_score(y_test[confident_mask], y_pred_soft[confident_mask])
        else:
            accuracy_soft = 0.0

        # Step 4: 评估软投票（带回退 - 使用 CatBoost）
        print("\n  评估软投票（带回退策略）...")
        cat_fallback = cat_model.predict(X_test).flatten()
        y_pred_fallback, metadata_fallback = ensemble.predict_with_fallback(X_test, cat_fallback)
        accuracy_fallback = accuracy_score(y_test, y_pred_fallback)

        # 计算各项指标
        f1_macro = f1_score(y_test, y_pred_fallback, average='macro')
        f1_draw = f1_score(y_test, y_pred_fallback, labels=[1], average='macro')

        # 分类报告
        report = classification_report(
            y_test, y_pred_fallback,
            target_names=["A (客胜)", "D (平局)", "H (主胜)"],
            zero_division=0
        )

        # 最终战报
        print()
        print("=" * 80)
        print("V41.470 Expert Heterogeneity 最终战报")
        print("=" * 80)
        print()
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  基础模型准确率                                               │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        print(f"  │  XGBoost:          {xgb_acc:6.2%}                                        │")
        print(f"  │  CatBoost:         {cat_acc:6.2%}                                        │")
        print(f"  │  LightGBM:         {lgb_acc:6.2%}                                        │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  软投票配置                                                    │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        print(f"  │  CatBoost 权重:   {loader.config.catboost_weight:4.1f}                                   │")
        print(f"  │  XGBoost 权重:    {loader.config.xgboost_weight:4.1f}                                   │")
        print(f"  │  LightGBM 权重:   {loader.config.lightgbm_weight:4.1f}                                   │")
        print(f"  │  熵值阈值:         {loader.config.entropy_threshold:4.2f}                                   │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  软投票（无回退）                                              │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        print(f"  │  信心占比:         {metadata_soft['confidence_ratio']:6.2%}                                        │")
        print(f"  │  平均熵值:         {metadata_soft['mean_entropy']:6.3f}                                        │")
        print(f"  │  有信心预测准确率:   {accuracy_soft:6.2%}                                        │")
        print(f"  │  无信心样本数:       {metadata_soft['no_confidence_count']:6d}                                        │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  软投票（带回退 - CatBoost）                                  │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        print(f"  │  整体准确率:         {accuracy_fallback:6.2%}                                        │")
        print(f"  │  F1-Macro:         {f1_macro:6.2%}                                        │")
        print(f"  │  F1-Draw:          {f1_draw:6.2%}                                        │")
        print(f"  │  回退使用率:         {metadata_fallback['fallback_used']:6.2%}                                        │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()
        print(f"  特征维度: {len(feature_names)} 维")
        print(f"  目标准确率 (50%+):    {'✅ ACHIEVED' if accuracy_fallback >= 0.50 else '❌ NOT ACHIEVED'}")
        print()
        print("  分类报告:")
        for line in report.split("\n"):
            if line.strip():
                print(f"    {line}")
        print()
        print("=" * 80)
        print("✅ V41.470 软投票集成训练完成")
        print("=" * 80)

    finally:
        loader.cleanup()


if __name__ == "__main__":
    main()
