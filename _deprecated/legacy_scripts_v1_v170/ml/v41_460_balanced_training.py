#!/usr/bin/env python3
"""
V41.460 Adversarial Ensemble Training - 特征恢复与平局逻辑修正
================================================================

V41.460 核心升级：
1. 特征恢复：放行 rolling/last_5/h2h 历史特征 (150+ 维)
2. 平局模型微调：class_weight 2.0→1.3, threshold 0.4→0.33
3. 联赛等级特征：排名差、积分差
4. 目标准确率：51%+

Author: V41.460 ML Team
Version: V41.460 "Balanced Calibration"
Date: 2026-01-21
"""

from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
import psycopg2
from catboost import CatBoostClassifier, Pool
from lightgbm import LGBMClassifier
from psycopg2.extras import RealDictCursor
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
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
class V41_460Config:
    """V41.460 配置"""

    # 数据分割
    train_ratio: float = 0.6
    val_ratio: float = 0.2
    test_ratio: float = 0.2

    # Draw Specialist 参数 (V41.460 微调)
    draw_class_weight: float = 1.3  # V41.460: 2.0 → 1.3
    draw_threshold: float = 0.33     # V41.460: 0.40 → 0.33

    # 集成投票
    draw_specialist_weight: float = 1.5

    # 标签映射
    label_mapping: dict = field(default_factory=lambda: {"A": 0, "D": 1, "H": 2})


DEFAULT_CONFIG = V41_460Config()


# =============================================================================
# Draw Specialist Model (V41.460 更新)
# =============================================================================

class DrawSpecialistModel:
    """
    V41.460 平局专项模型

    策略：
    - 使用 class_weight 让模型更关注平局（适度加权 1.3x）
    - 降低平局阈值到 0.33（更容易触发平局预测）
    - 优化 F1-Draw 分数而非整体准确率
    """

    def __init__(
        self,
        model: Optional[CatBoostClassifier] = None,
        draw_threshold: float = 0.33  # V41.460: 降低阈值
    ):
        self.model = model
        self.draw_threshold = draw_threshold
        self.feature_names: list[str] = []

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        feature_names: list[str],
        class_weight: float = 1.3  # V41.460: 降低权重
    ) -> dict[str, float]:
        """训练平局专项模型"""
        # 计算 class weight
        unique, counts = np.unique(y_train, return_counts=True)
        class_weights = {}
        total = len(y_train)
        for cls, count in zip(unique, counts):
            weight = total / (len(unique) * count)
            # V41.460: 平局适度加权（1.3x）
            if cls == 1:  # Draw
                weight *= class_weight
            class_weights[cls] = int(weight)

        # 创建 CatBoost 模型
        train_pool = Pool(
            data=X_train,
            label=y_train,
            feature_names=feature_names,
            weight=[class_weights.get(y, 1) for y in y_train]
        )

        val_pool = Pool(
            data=X_val,
            label=y_val,
            feature_names=feature_names
        )

        self.model = CatBoostClassifier(
            depth=6,
            learning_rate=0.05,
            iterations=500,
            random_seed=42,
            loss_function="MultiClass",
            eval_metric="Accuracy",
            verbose=False,
            class_weights=class_weights,
        )

        self.model.fit(train_pool, eval_set=val_pool, verbose=False)
        self.feature_names = feature_names

        # 评估
        y_pred = self.model.predict(val_pool)
        y_proba = self.model.predict_proba(val_pool)

        # 计算各项指标
        accuracy = accuracy_score(y_val, y_pred)
        f1_draw = f1_score(y_val, y_pred, labels=[1], average='macro')
        f1_macro = f1_score(y_val, y_pred, average='macro')

        # 计算平局预测率
        draw_rate = np.sum(y_pred == 1) / len(y_pred)

        return {
            "accuracy": accuracy,
            "f1_draw": f1_draw,
            "f1_macro": f1_macro,
            "draw_rate": draw_rate,
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        """预测（应用平局阈值）"""
        proba = self.model.predict_proba(X)

        # 找出平局（类别1）的概率
        if proba.shape[1] > 1:
            draw_proba = proba[:, 1]
        else:
            draw_proba = np.zeros(len(X))

        # 当平局概率超过阈值时，强制预测平局
        normal_pred = self.model.predict(X).flatten()

        forced_draw_pred = np.where(
            draw_proba >= self.draw_threshold,
            1,  # 强制平局
            normal_pred
        )

        return forced_draw_pred


# =============================================================================
# Data Loader (使用 PureFeatureFilter)
# =============================================================================

class V41_460DataLoader:
    """V41.460 数据加载器 - 使用更新后的 PureFeatureFilter"""

    def __init__(self, config: Optional[V41_460Config] = None):
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
        准备特征 - 使用更新后的 PureFeatureFilter

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

            # 使用 PureFeatureFilter 过滤（V41.460 更新版）
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
# Adversarial Ensemble Voter
# =============================================================================

class AdversarialEnsembleVoter:
    """V41.460 对抗性集成投票器"""

    def __init__(
        self,
        xgb_model: XGBClassifier,
        catboost_model: CatBoostClassifier,
        lgb_model: LGBMClassifier,
        draw_specialist: DrawSpecialistModel,
        config: Optional[V41_460Config] = None
    ):
        self.xgb_model = xgb_model
        self.catboost_model = catboost_model
        self.lgb_model = lgb_model
        self.draw_specialist = draw_specialist
        self.config = config or DEFAULT_CONFIG

    def predict(self, X: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        """对抗性集成预测"""
        # 获取各模型预测
        xgb_preds = self.xgb_model.predict(X).flatten()
        cat_preds = self.catboost_model.predict(X).flatten()
        lgb_preds = self.lgb_model.predict(X).flatten()
        draw_preds = self.draw_specialist.predict(X).flatten()

        ensemble_preds = []
        consensus_count = 0
        no_consensus_count = 0
        draw_forced_count = 0

        for i in range(len(X)):
            # 收集投票
            votes = {
                "A": 0,  # Away
                "D": 0,  # Draw
                "H": 0,  # Home
            }

            votes["A"] += (xgb_preds[i] == 0)
            votes["D"] += (xgb_preds[i] == 1)
            votes["H"] += (xgb_preds[i] == 2)

            votes["A"] += (cat_preds[i] == 0)
            votes["D"] += (cat_preds[i] == 1)
            votes["H"] += (cat_preds[i] == 2)

            votes["A"] += (lgb_preds[i] == 0)
            votes["D"] += (lgb_preds[i] == 1)
            votes["H"] += (lgb_preds[i] == 2)

            # V41.460: 平局专项模型权重 x1.5
            votes["D"] += self.config.draw_specialist_weight * (draw_preds[i] == 1)
            votes["A"] += self.config.draw_specialist_weight * (draw_preds[i] == 0)
            votes["H"] += self.config.draw_specialist_weight * (draw_preds[i] == 2)

            # 找出最高票
            max_vote = max(votes.values())
            max_label = max(votes, key=votes.get)

            # 检查共识（需要至少 2.5 票）
            if max_vote >= 2.5:
                ensemble_preds.append(max_label)
                if max_vote >= 3:
                    consensus_count += 1
            else:
                # 无共识，使用平局专项模型的预测
                ensemble_preds.append(draw_preds[i])
                no_consensus_count += 1

            if draw_preds[i] == 1:
                draw_forced_count += 1

        # 转换为数字标签
        label_to_num = {"A": 0, "D": 1, "H": 2}
        ensemble_preds_num = np.array([label_to_num.get(p, 1) for p in ensemble_preds])

        metadata = {
            "consensus_rate": consensus_count / len(X),
            "no_consensus_rate": no_consensus_count / len(X),
            "draw_forced_rate": draw_forced_count / len(X),
        }

        return ensemble_preds_num, metadata


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
    print("V41.460 Adversarial Ensemble Training - 特征恢复与平局逻辑修正")
    print("=" * 80)
    print()

    loader = V41_460DataLoader()

    try:
        # 加载数据
        matches = loader.load_matches(limit=8000)

        if len(matches) < 100:
            logger.error(f"样本不足 ({len(matches)} < 100)")
            return

        X, y, feature_names = loader.prepare_features(matches)

        logger.info(f"  样本数: {len(X)}, 特征维度: {len(feature_names)}")

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

        # Step 2: 训练平局专项模型（V41.460 微调参数）
        print("\n  训练 Draw Specialist (V41.460 微调)...")
        draw_specialist = DrawSpecialistModel(draw_threshold=0.33)
        draw_metrics = draw_specialist.fit(
            X_train, y_train,
            X_val, y_val,
            feature_names,
            class_weight=1.3  # V41.460: 降低权重
        )

        # Step 3: 创建对抗性集成
        print("\n  创建 Adversarial Ensemble...")
        voter = AdversarialEnsembleVoter(
            xgb_model, cat_model, lgb_model, draw_specialist
        )

        # Step 4: 评估
        print("\n  评估集成模型...")
        y_pred, metadata = voter.predict(X_test)

        # 计算各项指标
        accuracy = accuracy_score(y_test, y_pred)
        f1_macro = f1_score(y_test, y_pred, average='macro')
        f1_draw = f1_score(y_test, y_pred, labels=[1], average='macro')

        # 分类报告
        report = classification_report(
            y_test, y_pred,
            target_names=["A (客胜)", "D (平局)", "H (主胜)"],
            zero_division=0
        )

        # 最终战报
        print()
        print("=" * 80)
        print("🎯 V41.460 特征恢复与平局逻辑修正最终战报")
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
        print("  │  平局专项模型 (V41.460 微调)                                    │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        print(f"  │  Accuracy:         {draw_metrics['accuracy']:6.2%}                                        │")
        print(f"  │  F1-Draw:          {draw_metrics['f1_draw']:6.2%}                                        │")
        print(f"  │  F1-Macro:         {draw_metrics['f1_macro']:6.2%}                                        │")
        print(f"  │  Draw Rate:        {draw_metrics['draw_rate']:6.2%}                                        │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  对抗性集成结果                                               │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        print(f"  │  整体准确率:         {accuracy:6.2%}                                        │")
        print(f"  │  F1-Macro:         {f1_macro:6.2%}                                        │")
        print(f"  │  F1-Draw:          {f1_draw:6.2%}                                        │")
        print(f"  │  共识率:             {metadata['consensus_rate']:6.2%}                                        │")
        print(f"  │  强制平局率:         {metadata['draw_forced_rate']:6.2%}                                        │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()
        print(f"  特征维度: {len(feature_names)} 维")
        print(f"  目标准确率 (51%+):    {'✅ ACHIEVED' if accuracy >= 0.51 else '❌ NOT ACHIEVED'}")
        print()
        print("  分类报告:")
        for line in report.split("\n"):
            if line.strip():
                print(f"    {line}")
        print()
        print("=" * 80)
        print("✅ V41.460 对抗性集成训练完成")
        print("=" * 80)

    finally:
        loader.cleanup()


if __name__ == "__main__":
    main()
