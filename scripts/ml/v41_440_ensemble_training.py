#!/usr/bin/env python3
"""
V41.440 Ensemble Training - 众议院投票集成学习
===============================================

V41.440 核心升级：
1. Optuna 自动超参数调优
2. 三剑客集成：XGBoost + CatBoost + LightGBM
3. 多数投票机制：2/3 共识阈值
4. 深度数据泄露审计

目标准确率：50%+

Author: V41.440 ML Team
Version: V41.440 "Ensemble Voting"
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
import optuna
import psycopg2
from catboost import CatBoostClassifier, Pool
from lightgbm import LGBMClassifier
from psycopg2.extras import RealDictCursor
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from src.config_unified import get_settings
from src.processors.feature_interaction_engine import (
    FeatureInteractionEngine,
    create_interaction_features_for_match,
)
from src.processors.pure_feature_filter import PureFeatureFilter

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class EnsembleTrainingConfig:
    """集成训练配置"""

    # 数据分割
    train_ratio: float = 0.6
    val_ratio: float = 0.2
    test_ratio: float = 0.2

    # Optuna 调优参数
    n_trials: int = 30
    optuna_timeout: int = 3600  # 1 hour

    # 集成投票
    consensus_threshold: float = 2 / 3  # 至少 2/3 模型达成共识
    confidence_threshold: float = 0.6  # 置信度阈值

    # 基础模型参数
    xgb_params: dict = field(default_factory=lambda: {
        "max_depth": 6,
        "learning_rate": 0.05,
        "n_estimators": 200,
        "random_state": 42,
        "eval_metric": "mlogloss",
        "use_label_encoder": False,
    })

    lgb_params: dict = field(default_factory=lambda: {
        "max_depth": 7,
        "learning_rate": 0.05,
        "n_estimators": 200,
        "random_state": 42,
        "verbose": -1,
    })

    catboost_params: dict = field(default_factory=lambda: {
        "depth": 7,
        "learning_rate": 0.05,
        "iterations": 500,
        "l2_leaf_reg": 3.0,
        "random_seed": 42,
        "loss_function": "MultiClass",
        "eval_metric": "Accuracy",
        "verbose": False,
    })

    label_mapping: dict = field(default_factory=lambda: {"A": 0, "D": 1, "H": 2})


DEFAULT_CONFIG = EnsembleTrainingConfig()


# =============================================================================
# Data Loader
# =============================================================================

class EnsembleDataLoader:
    """V41.440 集成数据加载器"""

    def __init__(self, config: Optional[EnsembleTrainingConfig] = None):
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
        verbose: bool = True
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """
        准备特征 + 交互特征

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

            # 过滤污染特征
            pure_features = self.filter.filter_features(combined, verbose=False)

            if not pure_features:
                continue

            # === 创建交互特征 ===
            interaction_features = self.interaction_engine.create_all_interactions(pure_features)
            pure_features.update(interaction_features)

            X_list.append(pure_features)
            all_feature_names.update(pure_features.keys())

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
# Optuna Tuner
# =============================================================================

class OptunaCatBoostTuner:
    """Optuna CatBoost 超参数调优器"""

    def __init__(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        feature_names: list[str],
        config: Optional[EnsembleTrainingConfig] = None
    ):
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.feature_names = feature_names
        self.config = config or DEFAULT_CONFIG
        self.best_params = None
        self.best_score = 0.0

    def objective(self, trial: optuna.Trial) -> float:
        """Optuna 目标函数"""
        params = {
            "depth": trial.suggest_int("depth", 4, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 10.0),
            "iterations": 500,
            "random_seed": 42,
            "loss_function": "MultiClass",
            "eval_metric": "Accuracy",
            "verbose": False,
        }

        train_pool = Pool(
            data=self.X_train,
            label=self.y_train,
            feature_names=self.feature_names
        )

        val_pool = Pool(
            data=self.X_val,
            label=self.y_val,
            feature_names=self.feature_names
        )

        model = CatBoostClassifier(**params)
        model.fit(train_pool, eval_set=val_pool, verbose=False)

        preds = model.predict(val_pool)
        score = accuracy_score(self.y_val, preds)

        return score

    def tune(self) -> dict[str, Any]:
        """执行超参数调优"""
        logger.info("=" * 70)
        logger.info("🔍 Optuna Hyperparameter Tuning for CatBoost")
        logger.info("=" * 70)

        study = optuna.create_study(
            direction="maximize",
            study_name="v41_440_catboost_tuning"
        )

        study.optimize(
            self.objective,
            n_trials=self.config.n_trials,
            timeout=self.config.optuna_timeout,
            show_progress_bar=True
        )

        self.best_params = study.best_params
        self.best_score = study.best_value

        logger.info(f"  Best validation accuracy: {self.best_score:.4f}")
        logger.info(f"  Best parameters: {self.best_params}")

        return self.best_params


# =============================================================================
# Ensemble Voter
# =============================================================================

class EnsembleVoter:
    """V41.440 集成投票器 - 三剑客众议院"""

    def __init__(
        self,
        xgb_model: XGBClassifier,
        catboost_model: CatBoostClassifier,
        lgb_model: LGBMClassifier,
        feature_names: list[str],
        config: Optional[EnsembleTrainingConfig] = None
    ):
        self.xgb_model = xgb_model
        self.catboost_model = catboost_model
        self.lgb_model = lgb_model
        self.feature_names = feature_names
        self.config = config or DEFAULT_CONFIG

    def predict(
        self,
        X: np.ndarray,
        confidence_threshold: Optional[float] = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """
        集成预测 - 多数投票

        Returns:
            (predictions, metadata)
        """
        # 获取各模型预测
        xgb_preds = self.xgb_model.predict(X).flatten()
        cat_preds = self.catboost_model.predict(X).flatten()
        lgb_preds = self.lgb_model.predict(X).flatten()

        # 堆叠为 (n_models, n_samples)
        pred_array = np.stack([xgb_preds, cat_preds, lgb_preds], axis=0)

        ensemble_preds = []
        consensus_count = 0
        no_consensus_count = 0

        for i in range(pred_array.shape[1]):
            votes = pred_array[:, i]
            unique, counts = np.unique(votes, return_counts=True)

            max_count = np.max(counts)
            max_vote = unique[np.argmax(counts)]

            # 检查共识阈值
            if max_count >= 2:  # 至少 2/3 模型同意
                ensemble_preds.append(max_vote)
                if max_count == 3:
                    consensus_count += 1
            else:
                # 无共识，标记为 -1
                ensemble_preds.append(-1)
                no_consensus_count += 1

        metadata = {
            "consensus_rate": consensus_count / len(X),
            "no_consensus_rate": no_consensus_count / len(X),
            "total_samples": len(X),
        }

        return np.array(ensemble_preds), metadata

    def predict_with_probabilities(
        self,
        X: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        集成预测 - 概率加权平均

        Returns:
            (predictions, probabilities)
        """
        # 获取各模型概率
        xgb_proba = self.xgb_model.predict_proba(X)
        cat_proba = self.catboost_model.predict_proba(X)
        lgb_proba = self.lgb_model.predict_proba(X)

        # 平均概率
        avg_proba = (xgb_proba + cat_proba + lgb_proba) / 3.0

        # 预测
        predictions = np.argmax(avg_proba, axis=1)

        return predictions, avg_proba


# =============================================================================
# Ensemble Trainer
# =============================================================================

class EnsembleTrainer:
    """V41.440 集成训练器"""

    def __init__(self, config: Optional[EnsembleTrainingConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.loader = EnsembleDataLoader(config)

        # 模型实例
        self.xgb_model: Optional[XGBClassifier] = None
        self.catboost_model: Optional[CatBoostClassifier] = None
        self.lgb_model: Optional[LGBMClassifier] = None
        self.voter: Optional[EnsembleVoter] = None

        # 训练数据
        self.feature_names: list[str] = []
        self.X_train: Optional[np.ndarray] = None
        self.X_val: Optional[np.ndarray] = None
        self.X_test: Optional[np.ndarray] = None
        self.y_train: Optional[np.ndarray] = None
        self.y_val: Optional[np.ndarray] = None
        self.y_test: Optional[np.ndarray] = None

        logger.info("V41.440: Ensemble Trainer initialized")

    def prepare_data(self, limit: Optional[int] = None) -> bool:
        """准备训练数据 - 三路分割"""
        matches = self.loader.load_matches(limit=limit)

        if len(matches) < 100:
            logger.warning(f"样本不足 ({len(matches)} < 100)")
            return False

        X, y, feature_names = self.loader.prepare_features(matches)
        self.feature_names = feature_names

        # 三路分割：60% train / 20% val / 20% test
        # 先分出测试集
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y,
            test_size=self.config.test_ratio,
            random_state=42,
            stratify=y
        )

        # 再分出训练集和验证集
        val_ratio_adjusted = self.config.val_ratio / (self.config.train_ratio + self.config.val_ratio)
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp,
            test_size=val_ratio_adjusted,
            random_state=42,
            stratify=y_temp
        )

        self.X_train, self.X_val, self.X_test = X_train, X_val, X_test
        self.y_train, self.y_val, self.y_test = y_train, y_val, y_test

        total = len(X)
        logger.info(f"  Train: {len(X_train)} ({len(X_train)/total:.1%})")
        logger.info(f"  Val:   {len(X_val)} ({len(X_val)/total:.1%})")
        logger.info(f"  Test:  {len(X_test)} ({len(X_test)/total:.1%})")

        return True

    def train_individual_models(self) -> dict[str, float]:
        """训练各个基础模型"""
        results = {}

        # XGBoost
        logger.info("\n  训练 XGBoost...")
        self.xgb_model = XGBClassifier(**self.config.xgb_params)
        self.xgb_model.fit(
            self.X_train, self.y_train,
            eval_set=[(self.X_val, self.y_val)],
            verbose=False
        )
        xgb_acc = accuracy_score(self.y_test, self.xgb_model.predict(self.X_test))
        results["xgboost"] = xgb_acc
        logger.info(f"    XGBoost Test Accuracy: {xgb_acc:.4f}")

        # LightGBM
        logger.info("\n  训练 LightGBM...")
        self.lgb_model = LGBMClassifier(**self.config.lgb_params)
        self.lgb_model.fit(
            self.X_train, self.y_train,
            eval_set=[(self.X_val, self.y_val)]
        )
        lgb_acc = accuracy_score(self.y_test, self.lgb_model.predict(self.X_test))
        results["lightgbm"] = lgb_acc
        logger.info(f"    LightGBM Test Accuracy: {lgb_acc:.4f}")

        return results

    def tune_catboost(self) -> dict[str, Any]:
        """Optuna 调优 CatBoost"""
        tuner = OptunaCatBoostTuner(
            self.X_train, self.y_train,
            self.X_val, self.y_val,
            self.feature_names,
            self.config
        )
        best_params = tuner.tune()
        self.config.catboost_params.update(best_params)
        return best_params

    def train_catboost(self, use_optuna: bool = True) -> float:
        """训练 CatBoost（可选 Optuna 调优）"""
        if use_optuna:
            logger.info("\n  使用 Optuna 调优参数训练 CatBoost...")
            self.tune_catboost()
        else:
            logger.info("\n  使用默认参数训练 CatBoost...")

        train_pool = Pool(
            data=self.X_train,
            label=self.y_train,
            feature_names=self.feature_names
        )

        val_pool = Pool(
            data=self.X_val,
            label=self.y_val,
            feature_names=self.feature_names
        )

        self.catboost_model = CatBoostClassifier(**self.config.catboost_params)
        self.catboost_model.fit(train_pool, eval_set=val_pool, verbose=False)

        cat_acc = accuracy_score(self.y_test, self.catboost_model.predict(self.X_test))
        logger.info(f"    CatBoost Test Accuracy: {cat_acc:.4f}")

        return cat_acc

    def create_ensemble(self) -> None:
        """创建集成投票器"""
        self.voter = EnsembleVoter(
            self.xgb_model,
            self.catboost_model,
            self.lgb_model,
            self.feature_names,
            self.config
        )
        logger.info("\n  集成投票器创建完成")

    def evaluate_ensemble(self) -> dict[str, Any]:
        """评估集成性能"""
        preds, metadata = self.voter.predict(self.X_test)

        # 过滤无共识的预测
        valid_mask = preds >= 0
        if valid_mask.sum() > 0:
            valid_acc = accuracy_score(self.y_test[valid_mask], preds[valid_mask])
        else:
            valid_acc = 0.0

        # 整体准确率（无共识视为错误）
        overall_acc = accuracy_score(self.y_test, np.where(preds >= 0, preds, 0))

        return {
            "consensus_accuracy": valid_acc,
            "overall_accuracy": overall_acc,
            "consensus_rate": metadata["consensus_rate"],
            "no_consensus_rate": metadata["no_consensus_rate"],
            "valid_samples": valid_mask.sum(),
            "total_samples": len(self.X_test),
        }

    def save_models(self, output_dir: str = "model_zoo") -> list[Path]:
        """保存所有模型"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_paths = []

        # 保存 XGBoost
        xgb_path = output_path / f"v41_440_xgb_model_{timestamp}.pkl"
        with open(xgb_path, "wb") as f:
            pickle.dump({
                "model": self.xgb_model,
                "feature_names": self.feature_names,
            }, f)
        saved_paths.append(xgb_path)

        # 保存 CatBoost
        cat_path = output_path / f"v41_440_catboost_model_{timestamp}.pkl"
        with open(cat_path, "wb") as f:
            pickle.dump({
                "model": self.catboost_model,
                "feature_names": self.feature_names,
            }, f)
        saved_paths.append(cat_path)

        # 保存 LightGBM
        lgb_path = output_path / f"v41_440_lgb_model_{timestamp}.pkl"
        with open(lgb_path, "wb") as f:
            pickle.dump({
                "model": self.lgb_model,
                "feature_names": self.feature_names,
            }, f)
        saved_paths.append(lgb_path)

        logger.info(f"\n  模型已保存:")
        for path in saved_paths:
            logger.info(f"    {path}")

        return saved_paths

    def cleanup(self):
        self.loader.cleanup()


# =============================================================================
# Main
# =============================================================================

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print()
    print("=" * 80)
    print("V41.440 Ensemble Training - 众议院投票集成学习")
    print("=" * 80)
    print()

    trainer = EnsembleTrainer()

    try:
        # Step 1: 准备数据
        if not trainer.prepare_data():
            logger.error("数据准备失败")
            return

        # Step 2: 训练基础模型
        base_results = trainer.train_individual_models()

        # Step 3: Optuna 调优 + CatBoost
        catboost_acc = trainer.train_catboost(use_optuna=True)
        base_results["catboost"] = catboost_acc

        # Step 4: 创建集成
        trainer.create_ensemble()

        # Step 5: 评估集成
        ensemble_results = trainer.evaluate_ensemble()

        # Step 6: 保存模型
        trainer.save_models()

        # 最终战报
        print()
        print("=" * 80)
        print("🎯 V41.440 众议院投票最终战报")
        print("=" * 80)
        print()
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  基础模型准确率                                               │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        for name, acc in base_results.items():
            print(f"  │  {name:12s}: {acc:6.2%}                                        │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  集成投票结果                                                 │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        print(f"  │  共识准确率:         {ensemble_results['consensus_accuracy']:6.2%}                      │")
        print(f"  │  整体准确率:         {ensemble_results['overall_accuracy']:6.2%}                      │")
        print(f"  │  共识率:             {ensemble_results['consensus_rate']:6.2%}                      │")
        print(f"  │  有效样本:           {ensemble_results['valid_samples']:5d} / {ensemble_results['total_samples']:5d}              │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()
        print(f"  目标准确率 (50%+):    {'✅ ACHIEVED' if ensemble_results['consensus_accuracy'] >= 0.50 else '❌ NOT ACHIEVED'}")
        print()
        print("=" * 80)
        print("✅ V41.440 集成训练完成")
        print("=" * 80)

    finally:
        trainer.cleanup()


if __name__ == "__main__":
    main()
