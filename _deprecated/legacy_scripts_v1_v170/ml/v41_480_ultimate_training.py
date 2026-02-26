#!/usr/bin/env python3
"""
V41.480 Ultimate Training - 五大联赛深度特征训练
===============================================

V41.480 核心升级：
1. 伤病/禁赛战力损失 - 从 l2_raw_json unavailable 提取 marketValue
2. 赛程疲劳度 (Fatigue Index) - rest_days 和 is_busy_week
3. 赔率动向捕捉 - odds_drop_ratio
4. 联赛等级特征 - is_top_5_league
5. 目标特征维度：300+ 维
6. 目标准确率：48%+

Author: V41.480 ML Team
Version: V41.480 "Ultimate Pre-Match Mine"
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
from psycopg2.extras import RealDictCursor
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
)
from sklearn.model_selection import train_test_split

from src.config_unified import get_settings
from src.processors.feature_interaction_engine import FeatureInteractionEngine
from src.processors.ultimate_extractor import UltimateFeatureExtractor

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class V41_480Config:
    """V41.480 配置"""

    # 数据分割
    train_ratio: float = 0.6
    val_ratio: float = 0.2
    test_ratio: float = 0.2

    # 标签映射
    label_mapping: dict = field(default_factory=lambda: {"A": 0, "D": 1, "H": 2})


DEFAULT_CONFIG = V41_480Config()


# =============================================================================
# Data Loader (with Ultimate Features)
# =============================================================================

class V41_480DataLoader:
    """V41.480 数据加载器 - 使用终极特征提取器"""

    def __init__(self, config: Optional[V41_480Config] = None):
        self.config = config or DEFAULT_CONFIG
        self.settings = get_settings()
        self.extractor = UltimateFeatureExtractor()
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
                m.match_date,
                m.actual_result,
                m.technical_features,
                m.golden_features,
                m.l2_raw_json
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
        准备特征 - 使用终极特征提取器

        Returns:
            X, y, feature_names
        """
        X_list = []
        y_list = []
        all_feature_names = set()

        # 特征覆盖统计
        coverage_stats = {
            "total_matches": len(matches),
            "unavailable_data": 0,
            "odds_data": 0,
            "fatigue_data": 0,
        }

        for i, match in enumerate(matches):
            # 使用终极特征提取器
            features = self.extractor.extract_ultimate_features(
                match, verbose=False
            )

            if not features:
                continue

            # 统计特征覆盖
            if features.get("home_unavailable_total_count", 0) > 0 or \
               features.get("away_unavailable_total_count", 0) > 0:
                coverage_stats["unavailable_data"] += 1

            if features.get("home_drop_ratio", 0) != 0 or \
               features.get("total_movement", 0) != 0:
                coverage_stats["odds_data"] += 1

            if features.get("home_rest_days", 0) > 0:
                coverage_stats["fatigue_data"] += 1

            # 创建交互特征
            interaction_features = self.interaction_engine.create_all_interactions(features)
            features.update(interaction_features)

            X_list.append(features)
            all_feature_names.update(features.keys())

            result = match.get("actual_result")
            if result in self.config.label_mapping:
                y_list.append(self.config.label_mapping[result])

            if (i + 1) % 500 == 0:
                logger.info(f"  Processed {i + 1}/{len(matches)} matches...")

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

        # 打印覆盖统计
        print()
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  特征覆盖统计                                                 │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        print(f"  │  总样本数:           {coverage_stats['total_matches']:6d}                                  │")
        print(f"  │  伤病/禁赛数据:       {coverage_stats['unavailable_data']:6d} ({coverage_stats['unavailable_data']/coverage_stats['total_matches']*100:5.1%})                          │")
        print(f"  │  赔率数据:           {coverage_stats['odds_data']:6d} ({coverage_stats['odds_data']/coverage_stats['total_matches']*100:5.1%})                          │")
        print(f"  │  疲劳度数据:         {coverage_stats['fatigue_data']:6d} ({coverage_stats['fatigue_data']/coverage_stats['total_matches']*100:5.1%})                          │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()

        # 打印新增特征
        new_features = [
            "home_unavailable_total_count", "away_unavailable_total_count",
            "home_unavailable_total_market_value", "away_unavailable_total_market_value",
            "home_rest_days", "away_rest_days", "home_is_busy_week", "away_is_busy_week",
            "home_drop_ratio", "total_movement", "is_top_5_league",
        ]
        found_new = [f for f in new_features if f in feature_names]
        if found_new:
            print(f"  V41.480 新增特征 ({len(found_new)} 个):")
            for f in found_new:
                print(f"    - {f}")
            print()

        return X, y, feature_names

    def cleanup(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
        self.extractor.cleanup()


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
    print("V41.480 Ultimate Training - 五大联赛深度特征挖掘")
    print("=" * 80)
    print()

    loader = V41_480DataLoader()

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

        # 训练 CatBoost
        print("\n  训练 CatBoost...")
        train_pool = Pool(X_train, y_train, feature_names=feature_names)
        val_pool = Pool(X_val, y_val, feature_names=feature_names)
        cat_model = CatBoostClassifier(
            depth=7, learning_rate=0.05, iterations=500,
            random_seed=42, loss_function="MultiClass",
            eval_metric="Accuracy", verbose=False
        )
        cat_model.fit(train_pool, eval_set=val_pool, verbose=False)
        cat_acc = accuracy_score(y_test, cat_model.predict(X_test))

        # 计算各项指标
        y_pred = cat_model.predict(X_test)
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
        print("V41.480 Ultimate Training 最终战报")
        print("=" * 80)
        print()
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │  CatBoost 单模型结果                                          │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        print(f"  │  准确率:             {cat_acc:6.2%}                                        │")
        print(f"  │  F1-Macro:           {f1_macro:6.2%}                                        │")
        print(f"  │  F1-Draw:            {f1_draw:6.2%}                                        │")
        print("  └─────────────────────────────────────────────────────────────┘")
        print()
        print(f"  特征维度: {len(feature_names)} 维")
        print(f"  目标维度 (300+):     {'✅ ACHIEVED' if len(feature_names) >= 300 else '❌ NOT ACHIEVED'}")
        print(f"  目标准确率 (48%+):    {'✅ ACHIEVED' if cat_acc >= 0.48 else '❌ NOT ACHIEVED'}")
        print()
        print("  分类报告:")
        for line in report.split("\n"):
            if line.strip():
                print(f"    {line}")
        print()
        print("=" * 80)
        print("✅ V41.480 Ultimate Training 完成")
        print("=" * 80)

    finally:
        loader.cleanup()


if __name__ == "__main__":
    main()
