#!/usr/bin/env python3
"""
V41.430 CatBoost Training - 非线性突破训练
==========================================

V41.430 核心升级：
1. 特征交叉：discipline_adjusted_value, momentum_xg 等
2. 战力阶梯：rating_acceleration（评分加速度）
3. 算法升级：CatBoost（处理混合离散/连续特征）

目标准确率：52%+

Author: V41.430 ML Team
Version: V41.430 "Non-linear Breakthrough"
Date: 2026-01-21
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from catboost import CatBoostClassifier, Pool

from src.config_unified import get_settings
from src.processors.pure_feature_filter import PureFeatureFilter
from src.processors.feature_interaction_engine import (
    FeatureInteractionEngine,
    create_interaction_features_for_match,
)

logger = logging.getLogger(__name__)


@dataclass
class CatBoostTrainingConfig:
    """CatBoost 训练配置"""

    model_params: dict = field(default_factory=lambda: {
        "depth": 7,
        "learning_rate": 0.05,
        "iterations": 500,
        "l2_leaf_reg": 3.0,
        "random_seed": 42,
        "loss_function": "MultiClass",
        "eval_metric": "Accuracy",
        "verbose": False,
    })

    test_size: float = 0.2
    min_elite_features: int = 10

    label_mapping: dict = field(default_factory=lambda: {"A": 0, "D": 1, "H": 2})


DEFAULT_CONFIG = CatBoostTrainingConfig()


class CatBoostDataLoader:
    """V41.430 CatBoost 数据加载器"""

    def __init__(self, config: Optional[CatBoostTrainingConfig] = None):
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

    def load_matches(self, elite_mode: bool = False) -> list[dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()

        if elite_mode:
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
                  AND m.golden_features IS NOT NULL
                ORDER BY m.match_date DESC
            """
        else:
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

        cursor.execute(query)
        matches = cursor.fetchall()
        cursor.close()

        if elite_mode:
            import json
            elite_matches = []
            for match in matches:
                gf = match.get("golden_features")
                if isinstance(gf, str):
                    gf = json.loads(gf)
                if gf and len(gf) >= self.config.min_elite_features:
                    elite_matches.append(match)
            matches = elite_matches

        logger.info(f"Loaded {len(matches)} matches ({'elite' if elite_mode else 'all'})")
        return matches

    def prepare_features_with_interactions(
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

            # === V41.430: 创建交互特征 ===
            interaction_features = self.interaction_engine.create_all_interactions(pure_features)
            pure_features.update(interaction_features)

            X_list.append(pure_features)
            all_feature_names.update(pure_features.keys())

            result = match.get("actual_result")
            if result in self.config.label_mapping:
                y_list.append(self.config.label_mapping[result])

        # 统一特征顺序
        feature_names = sorted(all_feature_names)

        # 构建 CatBoost 特征矩阵
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

        logger.info(f"Prepared {len(X)} samples, {len(feature_names)} features (including interactions)")
        logger.info(f"Filter rate: {self.filter.get_filter_rate():.1%}")

        return X, y, feature_names

    def cleanup(self):
        if self._conn and not self._conn.closed:
            self._conn.close()


class CatBoostTrainer:
    """V41.430 CatBoost 训练器"""

    def __init__(self, config: Optional[CatBoostTrainingConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.loader = CatBoostDataLoader(config)
        self.model: Optional[CatBoostClassifier] = None
        self.feature_names: list[str] = []

        logger.info("V41.430: CatBoost Trainer initialized")

    def train(self, elite_mode: bool = False) -> dict[str, Any]:
        mode_name = "Elite" if elite_mode else "Mass"

        logger.info("=" * 70)
        logger.info(f"🚀 V41.430 {mode_name} CatBoost Training")
        logger.info("=" * 70)

        matches = self.loader.load_matches(elite_mode=elite_mode)

        if len(matches) < 30:
            logger.warning(f"  ⚠️ 样本不足 ({len(matches)} < 30)，跳过训练")
            return {
                "mode": mode_name,
                "skipped": True,
                "reason": f"Insufficient samples ({len(matches)} < 30)"
            }

        X, y, feature_names = self.loader.prepare_features_with_interactions(matches)
        self.feature_names = feature_names

        logger.info(f"  样本数: {len(X)}")
        logger.info(f"  特征维度: {len(feature_names)}")

        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.config.test_size,
            random_state=42,
            stratify=y
        )

        logger.info(f"  训练集: {len(X_train)}")
        logger.info(f"  测试集: {len(X_test)}")

        # 创建 CatBoost Pool
        train_pool = Pool(
            data=X_train,
            label=y_train,
            feature_names=feature_names
        )

        test_pool = Pool(
            data=X_test,
            label=y_test,
            feature_names=feature_names
        )

        # 训练 CatBoost 模型
        self.model = CatBoostClassifier(**self.config.model_params)

        self.model.fit(
            train_pool,
            eval_set=test_pool,
            verbose=False,
            plot=False
        )

        # 评估
        y_pred = self.model.predict(test_pool)
        accuracy = accuracy_score(y_test, y_pred)

        logger.info("")
        logger.info(f"  📊 {mode_name} CatBoost 评估报告:")
        logger.info("-" * 70)
        logger.info(f"  准确率: {accuracy:.2%}")
        logger.info("")
        logger.info("  分类报告:")
        report = classification_report(
            y_test, y_pred,
            target_names=["A (客胜)", "D (平局)", "H (主胜)"],
            zero_division=0
        )
        for line in report.split("\n"):
            if line.strip():
                logger.info(f"    {line}")

        return {
            "mode": mode_name,
            "n_samples": len(X),
            "n_features": len(feature_names),
            "accuracy": accuracy,
            "feature_names": feature_names,
        }

    def extract_feature_importance(self, top_n: int = 15) -> list[dict[str, Any]]:
        if self.model is None:
            return []

        # CatBoost 特征重要性
        importance = self.model.get_feature_importance()
        feature_importance = [
            {"name": name, "importance": float(imp)}
            for name, imp in zip(self.feature_names, importance)
        ]
        feature_importance.sort(key=lambda x: x["importance"], reverse=True)

        return feature_importance[:top_n]

    def save_model(self, output_dir: str = "model_zoo"):
        import pickle

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = output_path / f"v41_430_catboost_model_{timestamp}.pkl"

        with open(model_path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "feature_names": self.feature_names,
                "config": self.config.model_params,
            }, f)

        # 同时保存 CatBoost 原生格式
        cbm_path = output_path / f"v41_430_catboost_model_{timestamp}.cbm"
        self.model.save_model(cbm_path)

        logger.info(f"  ✅ CatBoost Model saved: {model_path}")
        logger.info(f"  ✅ CatBoost Native: {cbm_path}")
        return model_path

    def cleanup(self):
        self.loader.cleanup()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print()
    print("=" * 80)
    print("V41.430 CatBoost Training - Non-linear Breakthrough")
    print("=" * 80)
    print()

    trainer = CatBoostTrainer()

    try:
        # Step 1: 大盘 CatBoost 模型
        mass_result = trainer.train(elite_mode=False)
        trainer.save_model()

        mass_accuracy = mass_result.get("accuracy", 0)
        mass_features = mass_result.get("n_features", 0)
        mass_importance = trainer.extract_feature_importance()

        # Step 2: 精英 CatBoost 模型
        elite_result = trainer.train(elite_mode=True)

        if not elite_result.get("skipped"):
            elite_accuracy = elite_result.get("accuracy", 0)
            elite_features = elite_result.get("n_features", 0)
            trainer.save_model()

        # 最终战报
        print()
        print("=" * 80)
        print("🎯 V41.430 非线性突破最终战报")
        print("=" * 80)
        print()
        print(f"  Algorithm:                   CatBoost")
        print(f"  Feature Interactions:        23+ (discipline_adjusted_value, momentum_xg, etc.)")
        print(f"  Mass Accuracy (CatBoost):     {mass_accuracy:.2%}")
        print(f"  Mass Features (Enhanced):    {mass_features} 维")
        if not elite_result.get("skipped"):
            print(f"  Elite Accuracy (CatBoost):    {elite_accuracy:.2%}")
            print(f"  Elite Features (Enhanced):   {elite_features} 维")
            print(f"  Elite Sample Size:           {elite_result.get('n_samples', 0)} 场")
        else:
            print(f"  Elite Accuracy:              SKIPPED ({elite_result.get('reason')})")
        print()
        print(f"  Target Accuracy (52%+):       {'✅ ACHIEVED' if mass_accuracy >= 0.52 else '❌ NOT ACHIEVED'}")
        print()
        print(f"  Top 10 CatBoost Features:")
        for i, feat in enumerate(mass_importance[:10], 1):
            print(f"    {i:2d}. {feat['name']:45s} = {feat['importance']:.4f}")
        print()
        print("=" * 80)
        print("✅ V41.430 CatBoost 训练完成")
        print("=" * 80)

    finally:
        trainer.cleanup()


if __name__ == "__main__":
    main()
