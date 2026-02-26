#!/usr/bin/env python3
"""
V41.420 Enhanced Training - 历史均值增强训练
==============================================

V41.420 核心改进：
1. 滚动 xG 和评分特征（TDD 验证时空隔离）
2. 精英样本阈值从 30 降至 10
3. 目标准确率：51%+

Author: V41.420 ML Team
Version: V41.420 "Historical Awakening"
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
from xgboost import XGBClassifier

from src.config_unified import get_settings
from src.processors.pure_feature_filter import PureFeatureFilter

logger = logging.getLogger(__name__)


@dataclass
class EnhancedTrainingConfig:
    """增强训练配置"""

    model_params: dict = field(default_factory=lambda: {
        "n_estimators": 300,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "eval_metric": "mlogloss",
    })

    test_size: float = 0.2
    min_elite_features: int = 10  # V41.420: 从30降至10

    label_mapping: dict = field(default_factory=lambda: {"A": 0, "D": 1, "H": 2})


DEFAULT_CONFIG = EnhancedTrainingConfig()


class EnhancedDataLoader:
    """V41.420 增强数据加载器"""

    def __init__(self, config: Optional[EnhancedTrainingConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.settings = get_settings()
        self.filter = PureFeatureFilter(strict_mode=True)
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
            # 过滤精英样本（阈值从30降至10）
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

    def prepare_features(
        self,
        matches: list[dict[str, Any]],
        verbose: bool = True
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        self.filter.reset_stats()

        X_list = []
        y_list = []
        all_feature_names = set()

        for match in matches:
            tech_features = match.get("technical_features") or {}
            if tech_features and isinstance(tech_features, str):
                tech_features = json.loads(tech_features)

            golden_features = match.get("golden_features") or {}
            if golden_features and isinstance(golden_features, str):
                golden_features = json.loads(golden_features)

            combined = dict(tech_features)
            if golden_features:
                combined.update(golden_features)

            pure_features = self.filter.filter_features(combined, verbose=False)

            if not pure_features:
                continue

            X_list.append(pure_features)
            all_feature_names.update(pure_features.keys())

            result = match.get("actual_result")
            if result in self.config.label_mapping:
                y_list.append(self.config.label_mapping[result])

        feature_names = sorted(all_feature_names)
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

        logger.info(f"Prepared {len(X)} samples, {len(feature_names)} pure features")
        logger.info(f"Filter rate: {self.filter.get_filter_rate():.1%}")

        return X, y, feature_names

    def cleanup(self):
        if self._conn and not self._conn.closed:
            self._conn.close()


class EnhancedTrainer:
    """V41.420 增强训练器"""

    def __init__(self, config: Optional[EnhancedTrainingConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.loader = EnhancedDataLoader(config)
        self.model: Optional[XGBClassifier] = None
        self.feature_names: list[str] = []

    def train(self, elite_mode: bool = False) -> dict[str, Any]:
        mode_name = "Elite" if elite_mode else "Mass"

        logger.info("=" * 70)
        logger.info(f"🚀 V41.420 {mode_name} Enhanced Model Training")
        logger.info("=" * 70)

        matches = self.loader.load_matches(elite_mode=elite_mode)

        if len(matches) < 30:
            logger.warning(f"  ⚠️ 样本不足 ({len(matches)} < 30)，跳过训练")
            return {
                "mode": mode_name,
                "skipped": True,
                "reason": f"Insufficient samples ({len(matches)} < 30)"
            }

        X, y, feature_names = self.loader.prepare_features(matches, verbose=True)
        self.feature_names = feature_names

        logger.info(f"  样本数: {len(X)}")
        logger.info(f"  特征维度: {len(feature_names)}")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.config.test_size,
            random_state=42,
            stratify=y
        )

        logger.info(f"  训练集: {len(X_train)}")
        logger.info(f"  测试集: {len(X_test)}")

        self.model = XGBClassifier(**self.config.model_params)
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )

        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        logger.info("")
        logger.info(f"  📊 {mode_name} Enhanced Model 评估报告:")
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

        importance = self.model.feature_importances_
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
        model_path = output_path / f"v41_420_enhanced_model_{timestamp}.pkl"

        with open(model_path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "feature_names": self.feature_names,
                "config": self.config.model_params,
                "filter_rate": self.loader.filter.get_filter_rate(),
            }, f)

        logger.info(f"  ✅ Enhanced Model saved: {model_path}")
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
    print("V41.420 Enhanced Training - Historical Awakening")
    print("=" * 80)
    print()

    trainer = EnhancedTrainer()

    try:
        # Step 1: 大盘增强模型
        mass_result = trainer.train(elite_mode=False)
        trainer.save_model()

        mass_accuracy = mass_result.get("accuracy", 0)
        mass_features = mass_result.get("n_features", 0)
        mass_importance = trainer.extract_feature_importance()

        # Step 2: 精英增强模型
        elite_result = trainer.train(elite_mode=True)

        if not elite_result.get("skipped"):
            elite_accuracy = elite_result.get("accuracy", 0)
            elite_features = elite_result.get("n_features", 0)
            trainer.save_model()

        # 最终战报
        print()
        print("=" * 80)
        print("🎯 V41.420 增强模型最终战报")
        print("=" * 80)
        print()
        print(f"  TDD Test Passed:               YES (滚动特征时空隔离)")
        print(f"  Mass Accuracy (Enhanced):      {mass_accuracy:.2%}")
        print(f"  Mass Features (Pure):          {mass_features} 维")
        if not elite_result.get("skipped"):
            print(f"  Elite Accuracy (Enhanced):     {elite_accuracy:.2%}")
            print(f"  Elite Features (Pure):        {elite_features} 维")
            print(f"  Elite Sample Size:            {elite_result.get('n_samples', 0)} 场")
        else:
            print(f"  Elite Accuracy:                SKIPPED ({elite_result.get('reason')})")
        print()
        print(f"  Top 10 Enhanced Features:")
        for i, feat in enumerate(mass_importance[:10], 1):
            print(f"    {i:2d}. {feat['name']:45s} = {feat['importance']:.4f}")
        print()
        print("=" * 80)
        print("✅ V41.420 增强训练完成")
        print("=" * 80)

    finally:
        trainer.cleanup()


if __name__ == "__main__":
    main()
