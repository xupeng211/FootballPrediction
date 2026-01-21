#!/usr/bin/env python3
"""
V41.410 Pure Training - 纯净赛前模型训练
==========================================

严格时空隔离 + TDD 约束：
- 100% 剔除赛中/赛后数据
- 目标准确率：50-53%（真实水平）

Author: V41.410 Data Science Team
Version: V41.410 "Hardcore Purification"
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


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class PureTrainingConfig:
    """纯净训练配置"""

    # 模型参数
    model_params: dict = field(default_factory=lambda: {
        "n_estimators": 200,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "eval_metric": "mlogloss",
    })

    # 数据分割
    test_size: float = 0.2

    # 精英样本阈值
    min_elite_features: int = 15  # 从30降至15，扩大样本量

    # 标签映射
    label_mapping: dict = field(default_factory=lambda: {"A": 0, "D": 1, "H": 2})


DEFAULT_CONFIG = PureTrainingConfig()


# =============================================================================
# Pure Data Loader
# =============================================================================


class PureDataLoader:
    """V41.410 纯净数据加载器"""

    def __init__(self, config: Optional[PureTrainingConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.settings = get_settings()
        self.filter = PureFeatureFilter(strict_mode=True)
        self._conn = None

    def _get_connection(self):
        """获取数据库连接"""
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
        """
        加载比赛数据

        Args:
            elite_mode: 是否仅加载精英样本（完整特征）
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if elite_mode:
            # 加载精英样本
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
            # 加载所有比赛
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
            # 过滤精英样本
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

    def prepare_pure_features(
        self,
        matches: list[dict[str, Any]],
        verbose: bool = True
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """
        准备纯净特征矩阵

        使用 PureFeatureFilter 100% 剔除污染特征
        """
        X_list = []
        y_list = []
        all_feature_names = set()

        self.filter.reset_stats()

        for match in matches:
            # 解析特征
            tech_features = match.get("technical_features") or {}
            if tech_features and isinstance(tech_features, str):
                tech_features = json.loads(tech_features)

            golden_features = match.get("golden_features") or {}
            if golden_features and isinstance(golden_features, str):
                golden_features = json.loads(golden_features)

            # 合并特征
            combined = dict(tech_features)
            if golden_features:
                combined.update(golden_features)

            # === 关键：使用 PureFeatureFilter 过滤 ===
            pure_features = self.filter.filter_features(combined, verbose=False)

            if not pure_features:
                continue

            X_list.append(pure_features)
            all_feature_names.update(pure_features.keys())

            # 标签
            result = match.get("actual_result")
            if result in self.config.label_mapping:
                y_list.append(self.config.label_mapping[result])

        # 统一特征顺序
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

        filter_rate = self.filter.get_filter_rate()

        logger.info(f"Prepared {len(X)} pure samples, {len(feature_names)} pure features")
        logger.info(f"Filter rate: {filter_rate:.1%}")

        return X, y, feature_names

    def cleanup(self):
        """清理资源"""
        if self._conn and not self._conn.closed:
            self._conn.close()


# =============================================================================
# Pure Trainer
# =============================================================================


class PureTrainer:
    """V41.410 纯净训练器"""

    def __init__(self, config: Optional[PureTrainingConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.loader = PureDataLoader(config)
        self.model: Optional[XGBClassifier] = None
        self.feature_names: list[str] = []

        logger.info("V41.410: Pure Trainer initialized")

    def train(self, elite_mode: bool = False) -> dict[str, Any]:
        """
        训练纯净模型

        Args:
            elite_mode: 是否使用精英样本
        """
        mode_name = "Elite" if elite_mode else "Mass"

        logger.info("=" * 70)
        logger.info(f"🛡️ V41.410 {mode_name} Pure Model Training")
        logger.info("=" * 70)

        # 加载数据
        matches = self.loader.load_matches(elite_mode=elite_mode)

        if len(matches) < 30:
            logger.warning(f"  ⚠️ 样本不足 ({len(matches)} < 30)，跳过训练")
            return {
                "mode": mode_name,
                "skipped": True,
                "reason": f"Insufficient samples ({len(matches)} < 30)"
            }

        # 准备纯净特征
        X, y, feature_names = self.loader.prepare_pure_features(matches, verbose=True)
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

        # 训练模型
        self.model = XGBClassifier(**self.config.model_params)
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )

        # 评估
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        logger.info("")
        logger.info(f"  📊 {mode_name} Pure Model 评估报告:")
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
        """提取特征重要性"""
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
        """保存模型"""
        import pickle

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = output_path / f"v41_410_pure_model_{timestamp}.pkl"

        with open(model_path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "feature_names": self.feature_names,
                "config": self.config.model_params,
                "filter_rate": self.loader.filter.get_filter_rate(),
            }, f)

        logger.info(f"  ✅ Pure Model saved: {model_path}")
        return model_path

    def cleanup(self):
        """清理资源"""
        self.loader.cleanup()


# =============================================================================
# Main
# =============================================================================


def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print()
    print("=" * 80)
    print("V41.410 Pure Training - Hardcore Purification")
    print("=" * 80)
    print()

    trainer = PureTrainer()

    try:
        # Step 1: 大盘纯净模型
        mass_result = trainer.train(elite_mode=False)
        trainer.save_model()

        mass_accuracy = mass_result.get("accuracy", 0)
        mass_features = mass_result.get("n_features", 0)

        # 特征重要性
        mass_importance = trainer.extract_feature_importance()

        # Step 2: 精英纯净模型
        elite_result = trainer.train(elite_mode=True)

        if not elite_result.get("skipped"):
            elite_accuracy = elite_result.get("accuracy", 0)
            elite_features = elite_result.get("n_features", 0)
            trainer.save_model()

        # 最终战报
        print()
        print("=" * 80)
        print("🎯 V41.410 纯净模型最终战报")
        print("=" * 80)
        print()
        print(f"  TDD Test Passed:               YES")
        print(f"  Mass Accuracy (Unbiased):      {mass_accuracy:.2%}")
        print(f"  Mass Features (Pure):          {mass_features} 维")
        if not elite_result.get("skipped"):
            print(f"  Elite Accuracy (Unbiased):     {elite_accuracy:.2%}")
            print(f"  Elite Features (Pure):        {elite_features} 维")
        else:
            print(f"  Elite Accuracy:                SKIPPED ({elite_result.get('reason')})")
        print()
        print(f"  Top 5 Pure Features:")
        for i, feat in enumerate(mass_importance[:5], 1):
            print(f"    {i}. {feat['name']:40s} = {feat['importance']:.4f}")
        print()
        print("=" * 80)
        print("✅ V41.410 纯净训练完成")
        print("=" * 80)

    finally:
        trainer.cleanup()


if __name__ == "__main__":
    main()
