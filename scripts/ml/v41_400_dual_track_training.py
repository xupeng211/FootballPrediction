#!/usr/bin/env python3
"""
V41.400 Dual Track Training - Elite & Mass Model Validation
============================================================

双轨制模型验证实验：
- Mass Model V2.0: 全部 8,877 场数据（156 维共有特征）
- Elite Model V2.0: 68 场精英样本（196 维完整特征）

Author: V41.400 ML Team
Version: V41.400 "Elite & Mass Training"
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

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================


@dataclass
class DualTrackConfig:
    """双轨训练配置"""

    # Mass Model 配置
    mass_model_params: dict = field(default_factory=lambda: {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "eval_metric": "mlogloss",
        "use_label_encoder": False,
    })

    # Elite Model 配置（小样本，更浅的树）
    elite_model_params: dict = field(default_factory=lambda: {
        "n_estimators": 100,
        "max_depth": 4,
        "learning_rate": 0.03,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "random_state": 42,
        "eval_metric": "mlogloss",
        "use_label_encoder": False,
    })

    # 数据分割比例
    test_size: float = 0.2
    min_elite_features: int = 30  # 精英样本最小特征数

    # 标签映射
    label_mapping: dict = field(default_factory=lambda: {"A": 0, "D": 1, "H": 2})
    reverse_mapping: dict = field(default_factory=lambda: {0: "A", 1: "D", 2: "H"})


DEFAULT_CONFIG = DualTrackConfig()


# =============================================================================
# Data Loader
# =============================================================================


class DualTrackDataLoader:
    """V41.400 双轨数据加载器"""

    def __init__(self, config: Optional[DualTrackConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.settings = get_settings()
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

    def load_all_matches(self) -> list[dict[str, Any]]:
        """加载所有比赛数据（Mass Model）"""
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

        cursor.execute(query)
        matches = cursor.fetchall()
        cursor.close()

        logger.info(f"Loaded {len(matches)} matches with technical features")
        return matches

    def load_elite_matches(self) -> list[dict[str, Any]]:
        """加载精英样本（完整特征）"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 获取golden_features维度 >= min_elite_features的比赛
        # 使用 jsonb_object_keys() 计算特征数量
        query = f"""
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

        cursor.execute(query)
        all_matches = cursor.fetchall()
        cursor.close()

        # 过滤出特征数量足够的比赛
        import json
        elite_matches = []
        for match in all_matches:
            gf = match.get("golden_features")
            if isinstance(gf, str):
                gf = json.loads(gf)
            if gf and len(gf) >= self.config.min_elite_features:
                elite_matches.append(match)

        logger.info(f"Loaded {len(elite_matches)} elite matches with >= {self.config.min_elite_features} golden features")
        return elite_matches

    def prepare_features(
        self,
        matches: list[dict[str, Any]],
        use_golden_features: bool = True
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """
        准备特征矩阵和标签

        Args:
            matches: 比赛数据列表
            use_golden_features: 是否使用黄金特征

        Returns:
            X, y, feature_names
        """
        X_list = []
        y_list = []
        all_feature_names = set()

        for match in matches:
            # 解析技术特征
            tech_features = match.get("technical_features") or {}
            if tech_features and isinstance(tech_features, str):
                tech_features = json.loads(tech_features)

            # 合并特征
            combined_features = dict(tech_features)

            # 添加黄金特征
            if use_golden_features:
                golden_features = match.get("golden_features") or {}
                if golden_features and isinstance(golden_features, str):
                    golden_features = json.loads(golden_features)
                if golden_features:
                    combined_features.update(golden_features)

            # 跳过空特征
            if not combined_features:
                continue

            X_list.append(combined_features)
            all_feature_names.update(combined_features.keys())

            # 标签
            result = match.get("actual_result")
            if result in self.config.label_mapping:
                y_list.append(self.config.label_mapping[result])

        # 统一特征顺序，过滤非数值特征
        feature_names = sorted(all_feature_names)
        X_list_clean = []
        for feat in X_list:
            row = []
            for name in feature_names:
                val = feat.get(name, 0)
                # 跳过嵌套字典和非数值类型
                if isinstance(val, dict):
                    val = 0
                elif isinstance(val, list):
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
        return X, y, feature_names

    def cleanup(self):
        """清理数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()


# =============================================================================
# Dual Track Trainer
# =============================================================================


class DualTrackTrainer:
    """V41.400 双轨训练器"""

    def __init__(self, config: Optional[DualTrackConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.loader = DualTrackDataLoader(config)

        # 模型存储
        self.mass_model: Optional[XGBClassifier] = None
        self.elite_model: Optional[XGBClassifier] = None

        # 特征名称
        self.mass_feature_names: list[str] = []
        self.elite_feature_names: list[str] = []

        logger.info("V41.400: Dual Track Trainer initialized")

    def train_mass_model(self) -> dict[str, Any]:
        """训练大盘模型（Mass Model V2.0）"""
        logger.info("=" * 70)
        logger.info("📊 Step 1: 训练大盘模型 V2.0 (Mass Model)")
        logger.info("=" * 70)

        # 加载所有比赛
        matches = self.loader.load_all_matches()

        # 准备特征（包含黄金特征）
        X, y, feature_names = self.loader.prepare_features(matches, use_golden_features=True)
        self.mass_feature_names = feature_names

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
        self.mass_model = XGBClassifier(**self.config.mass_model_params)
        self.mass_model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )

        # 评估
        y_pred = self.mass_model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        logger.info("")
        logger.info("  📊 Mass Model V2.0 评估报告:")
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
            "model": "Mass Model V2.0",
            "n_samples": len(X),
            "n_features": len(feature_names),
            "accuracy": accuracy,
            "feature_names": feature_names,
        }

    def train_elite_model(self) -> dict[str, Any]:
        """训练精英模型（Elite Model V2.0）"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("⭐ Step 2: 训练精英模型 V2.0 (Elite Model)")
        logger.info("=" * 70)

        # 加载精英样本
        matches = self.loader.load_elite_matches()

        if len(matches) < 30:
            logger.warning(f"  ⚠️ 精英样本不足 ({len(matches)} < 30)，跳过训练")
            return {
                "model": "Elite Model V2.0",
                "skipped": True,
                "reason": f"Insufficient elite samples ({len(matches)} < 30)"
            }

        # 准备特征
        X, y, feature_names = self.loader.prepare_features(matches, use_golden_features=True)
        self.elite_feature_names = feature_names

        logger.info(f"  样本数: {len(X)}")
        logger.info(f"  特征维度: {len(feature_names)}")

        # 小样本：使用更大的训练集比例
        test_size = max(0.2, 10 / len(X))  # 至少保留 10 个测试样本

        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=42,
            stratify=y if len(np.unique(y)) > 1 else None
        )

        logger.info(f"  训练集: {len(X_train)}")
        logger.info(f"  测试集: {len(X_test)}")

        # 训练模型
        self.elite_model = XGBClassifier(**self.config.elite_model_params)
        self.elite_model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )

        # 评估
        y_pred = self.elite_model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        logger.info("")
        logger.info("  ⭐ Elite Model V2.0 评估报告:")
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
            "model": "Elite Model V2.0",
            "n_samples": len(X),
            "n_features": len(feature_names),
            "accuracy": accuracy,
            "feature_names": feature_names,
        }

    def extract_feature_importance(
        self,
        model: XGBClassifier,
        feature_names: list[str],
        top_n: int = 20
    ) -> list[dict[str, Any]]:
        """提取特征重要性"""
        importance = model.feature_importances_
        feature_importance = [
            {"name": name, "importance": float(imp)}
            for name, imp in zip(feature_names, importance)
        ]
        feature_importance.sort(key=lambda x: x["importance"], reverse=True)

        return feature_importance[:top_n]

    def generate_report(self) -> dict[str, Any]:
        """生成综合报告"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("📋 Step 3: V2.0 特征重要性榜单")
        logger.info("=" * 70)

        # 大盘模型特征重要性
        if self.mass_model:
            mass_importance = self.extract_feature_importance(
                self.mass_model, self.mass_feature_names
            )

            logger.info("")
            logger.info("  🥇 Mass Model V2.0 - Top 20 特征:")
            logger.info("-" * 70)
            for i, feat in enumerate(mass_importance[:20], 1):
                logger.info(f"    {i:2d}. {feat['name']:40s} = {feat['importance']:.4f}")

            # 找到新特征中的最高排名
            new_features = [
                f for f in mass_importance
                if any(kw in f["name"] for kw in ["market_value", "injury", "rating"])
            ]

            if new_features:
                logger.info("")
                logger.info("  ⭐ 新黄金特征 Top 10:")
                logger.info("-" * 70)
                for i, feat in enumerate(new_features[:10], 1):
                    rank = mass_importance.index(feat) + 1
                    logger.info(f"    {i:2d}. #{rank:2d} {feat['name']:40s} = {feat['importance']:.4f}")

        # 精英模型特征重要性
        if self.elite_model and len(self.elite_feature_names) > 0:
            elite_importance = self.extract_feature_importance(
                self.elite_model, self.elite_feature_names
            )

            logger.info("")
            logger.info("  🏆 Elite Model V2.0 - Top 15 特征:")
            logger.info("-" * 70)
            for i, feat in enumerate(elite_importance[:15], 1):
                logger.info(f"    {i:2d}. {feat['name']:40s} = {feat['importance']:.4f}")

        return {
            "mass_importance": mass_importance if self.mass_model else [],
            "elite_importance": elite_importance if self.elite_model else [],
            "top_new_feature": new_features[0] if new_features else None,
        }

    def save_models(self, output_dir: str = "model_zoo"):
        """保存模型"""
        import pickle

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存大盘模型
        if self.mass_model:
            mass_path = output_path / f"v41_400_mass_model_v2_{timestamp}.pkl"
            with open(mass_path, "wb") as f:
                pickle.dump({
                    "model": self.mass_model,
                    "feature_names": self.mass_feature_names,
                    "config": self.config.mass_model_params,
                }, f)
            logger.info(f"  ✅ Mass Model saved: {mass_path}")

        # 保存精英模型
        if self.elite_model:
            elite_path = output_path / f"v41_400_elite_model_v2_{timestamp}.pkl"
            with open(elite_path, "wb") as f:
                pickle.dump({
                    "model": self.elite_model,
                    "feature_names": self.elite_feature_names,
                    "config": self.config.elite_model_params,
                }, f)
            logger.info(f"  ✅ Elite Model saved: {elite_path}")

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
    print("V41.400 Dual Track Training - Elite & Mass Model Validation")
    print("=" * 80)
    print()

    trainer = DualTrackTrainer()

    try:
        # Step 1: 大盘模型
        mass_result = trainer.train_mass_model()
        mass_accuracy = mass_result.get("accuracy", 0)

        # Step 2: 精英模型
        elite_result = trainer.train_elite_model()
        elite_accuracy = elite_result.get("accuracy", 0) if not elite_result.get("skipped") else 0

        # Step 3: 特征重要性
        report = trainer.generate_report()

        # 保存模型
        trainer.save_models()

        # 最终战报
        print()
        print("=" * 80)
        print("🎯 V41.400 双轨实验最终战报")
        print("=" * 80)
        print()
        print(f"  Standard Accuracy (Mass):  {mass_accuracy:.2%}")
        if elite_result.get("skipped"):
            print(f"  Elite Accuracy:            SKIPPED (样本不足)")
        else:
            print(f"  Elite Accuracy:            {elite_accuracy:.2%}")
        print()

        if report.get("top_new_feature"):
            top_feat = report["top_new_feature"]
            mass_rank = report["mass_importance"].index(top_feat) + 1
            print(f"  Most Potent New Feature:   #{mass_rank} {top_feat['name']} = {top_feat['importance']:.4f}")
        print()

        print("=" * 80)
        print("✅ V41.400 双轨训练完成")
        print("=" * 80)

    finally:
        trainer.cleanup()


if __name__ == "__main__":
    main()
