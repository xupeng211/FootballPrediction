#!/usr/bin/env python3
"""
V41.300 "Pilot Algorithm" - 特征工程提取器
=====================================================

核心任务: 将三位一体的完美样本（有 L2 数据 + 有赔率数据 + 有比赛结果）
        展开成 AI 可读的张量（Tensor）。

三位一体定义:
    1. L2 数据: matches.l2_raw_json IS NOT NULL (FotMob 技术统计)
    2. 赔率数据: match_odds_intelligence.closing_price IS NOT NULL (Pinnacle 终盘)
    3. 比赛结果: matches.status = 'FT' AND home_score/away_score IS NOT NULL

核心特性:
    - 兼容 V51.0 特征提取引擎（深度脱水版）
    - 提取 xG 差值、阵容平均评分、关键缺阵球员权重
    - 生成 1X2 标签（H/D/A）
    - 输出特征矩阵 + 标签向量 + 元数据

输出规格:
    - Features Extracted: [Count]
    - Baseline Accuracy: [X%] (待 Step 3 计算)
    - Top 5 Important Features: (待 Step 3 计算)

Author: Senior ML Engineer
Version: V41.300 (Pilot Algorithm - Feature Engineering)
Date: 2026-01-21
"""

# ============================================================================
# 标准库导入
# ============================================================================
import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================================
# 第三方库导入
# ============================================================================
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import structlog
from tqdm import tqdm

# ============================================================================
# 本地模块导入
# ============================================================================
from src.config_unified import get_settings
from src.processors.v51_feature_refiner import (
    V51FeatureRefiner,
    FeatureExtractionStats,
    DEFAULT_PRUNING_CONFIG,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# V41.300 数据泄露防护 - 赛后特征黑名单
# ============================================================================

# 这些特征包含比赛结果信息，必须在训练前移除
POST_MATCH_FEATURE_PATTERNS = [
    # 比分相关
    r"score",
    r"newScore",
    r"actual_result",
    r"winner",
    # 比赛状态相关
    r"status.*FT",
    r"is_finished",
    # 赛后统计（这些只有在比赛结束后才有）
    # 注意：保留 xG、shots 等技术统计，因为它们是赛中数据
    # 但是移除 final_score、final_result 等
]

import re
POST_MATCH_REGEX = re.compile("|".join(POST_MATCH_FEATURE_PATTERNS), re.IGNORECASE)


def is_post_match_feature(feature_name: str) -> bool:
    """
    检查特征是否为赛后特征（可能导致数据泄露）

    Args:
        feature_name: 特征名称

    Returns:
        是否为赛后特征
    """
    return bool(POST_MATCH_REGEX.search(feature_name))


def filter_post_match_features(feature_names: list[str]) -> list[str]:
    """
    过滤掉赛后特征

    Args:
        feature_names: 特征名称列表

    Returns:
        过滤后的特征名称列表
    """
    filtered = []
    removed_count = 0

    for name in feature_names:
        if is_post_match_feature(name):
            removed_count += 1
        else:
            filtered.append(name)

    if removed_count > 0:
        logger.warning(
            "过滤掉赛后特征",
            removed_count=removed_count,
            remaining_count=len(filtered),
        )

    return filtered


# ============================================================================
# V41.300 数据类定义
# ============================================================================


@dataclass
class PilotExtractionStats:
    """V41.300 提取统计"""

    # 数据来源统计
    total_matches_db: int = 0
    trio_perfect_samples: int = 0

    # 特征统计
    total_features_extracted: int = 0
    feature_matrix_shape: tuple = (0, 0)

    # 标签统计
    label_distribution: dict[str, int] = field(default_factory=dict)

    # 时间统计
    extraction_time_ms: float = 0.0

    def __str__(self) -> str:
        return (
            f"V41.300 提取统计:\n"
            f"  数据库比赛: {self.total_matches_db} 场\n"
            f"  三位一体样本: {self.trio_perfect_samples} 场\n"
            f"  特征维度: {self.feature_matrix_shape[1]}\n"
            f"  特征矩阵: {self.feature_matrix_shape[0]} x {self.feature_matrix_shape[1]}\n"
            f"  标签分布: H={self.label_distribution.get('H', 0)}, "
            f"D={self.label_distribution.get('D', 0)}, "
            f"A={self.label_distribution.get('A', 0)}\n"
            f"  提取耗时: {self.extraction_time_ms:.0f}ms"
        )


@dataclass
class PilotDataset:
    """V41.300 训练数据集"""

    # 特征矩阵 (numpy array)
    X: np.ndarray

    # 标签向量 (numpy array: 0=H, 1=D, 2=A)
    y: np.ndarray

    # 元数据 (DataFrame)
    metadata: pd.DataFrame

    # 特征名称列表
    feature_names: list[str]

    # 统计信息
    stats: PilotExtractionStats

    def save(self, output_dir: str | Path) -> None:
        """
        保存数据集到文件

        Args:
            output_dir: 输出目录
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存特征矩阵
        np.save(output_dir / "X_features.npy", self.X)

        # 保存标签向量
        np.save(output_dir / "y_labels.npy", self.y)

        # 保存元数据
        self.metadata.to_csv(output_dir / "metadata.csv", index=False)

        # 保存特征名称
        with open(output_dir / "feature_names.json", "w") as f:
            json.dump(self.feature_names, f, indent=2)

        # 保存统计信息
        with open(output_dir / "stats.json", "w") as f:
            stats_dict = {
                "total_matches_db": self.stats.total_matches_db,
                "trio_perfect_samples": self.stats.trio_perfect_samples,
                "total_features_extracted": self.stats.total_features_extracted,
                "feature_matrix_shape": self.stats.feature_matrix_shape,
                "label_distribution": self.stats.label_distribution,
                "extraction_time_ms": self.stats.extraction_time_ms,
            }
            json.dump(stats_dict, f, indent=2)

        logger.info(
            "数据集保存完成",
            output_dir=str(output_dir),
            X_shape=self.X.shape,
            y_shape=self.y.shape,
        )


# ============================================================================
# V41.300 特征工程提取器
# ============================================================================


class PilotFeatureExtractor:
    """
    V41.300 Pilot 特征工程提取器

    核心功能:
        1. 从数据库查询三位一体样本
        2. 使用 V51.0 引擎提取特征
        3. 生成 1X2 标签
        4. 构建训练数据集
    """

    def __init__(
        self,
        max_features: int = 500,
        enable_whitelist: bool = True,
        season_filter: str | None = None,
        league_filter: str | None = None,
    ):
        """
        初始化提取器

        Args:
            max_features: 最大特征维度
            enable_whitelist: 是否启用白名单保护
            season_filter: 赛季过滤 (如 "2023/2024")
            league_filter: 联赛过滤 (如 "Premier League")
        """
        self.max_features = max_features
        self.enable_whitelist = enable_whitelist
        self.season_filter = season_filter
        self.league_filter = league_filter

        # 初始化 V51.0 特征提取引擎
        self.refiner = V51FeatureRefiner(
            pruning_config=DEFAULT_PRUNING_CONFIG,
            max_features=max_features,
            enable_whitelist=enable_whitelist,
        )

        # 统计信息
        self.stats = PilotExtractionStats()

        logger.info(
            "V41.300 Pilot 特征提取器初始化完成",
            max_features=max_features,
            whitelist_enabled=enable_whitelist,
            season_filter=season_filter,
            league_filter=league_filter,
        )

    def _get_db_connection(self):
        """获取数据库连接"""
        settings = get_settings()
        return psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )

    def _query_trio_samples(self) -> list[dict]:
        """
        查询三位一体完美样本

        Returns:
            比赛列表，每个元素包含 {match_id, l2_raw_json, closing_price, ...}
        """
        conn = self._get_db_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # 构建查询
            query = """
                SELECT
                    m.match_id,
                    m.league_name,
                    m.season,
                    m.home_team,
                    m.away_team,
                    m.match_date,
                    m.status,
                    m.home_score,
                    m.away_score,
                    m.l2_raw_json,
                    m.technical_features,
                    moi.closing_price,
                    moi.initial_price,
                    moi.quality_rating
                FROM matches m
                INNER JOIN match_odds_intelligence moi ON m.match_id = moi.match_id
                WHERE m.status = 'FT'
                  AND m.home_score IS NOT NULL
                  AND m.away_score IS NOT NULL
                  AND m.l2_raw_json IS NOT NULL
                  AND moi.closing_price IS NOT NULL
            """

            params = []

            if self.season_filter:
                query += " AND m.season = %s"
                params.append(self.season_filter)

            if self.league_filter:
                query += " AND m.league_name = %s"
                params.append(self.league_filter)

            query += " ORDER BY m.match_date DESC"

            cur.execute(query, params)
            rows = cur.fetchall()

            self.stats.total_matches_db = len(rows)
            self.stats.trio_perfect_samples = len(rows)

            logger.info(
                "三位一体样本查询完成",
                total_samples=len(rows),
                season_filter=self.season_filter,
                league_filter=self.league_filter,
            )

            return rows

        finally:
            conn.close()

    def _extract_label(self, row: dict) -> int:
        """
        提取比赛结果标签

        Args:
            row: 比赛数据行

        Returns:
            标签 (0=H, 1=D, 2=A)
        """
        home_score = row.get("home_score")
        away_score = row.get("away_score")

        if home_score is None or away_score is None:
            raise ValueError(f"比赛 {row.get('match_id')} 缺少比分数据")

        if home_score > away_score:
            return 0  # H (Home Win)
        elif home_score < away_score:
            return 2  # A (Away Win)
        else:
            return 1  # D (Draw)

    def _enrich_features(self, features: dict[str, Any], row: dict) -> dict[str, Any]:
        """
        特征增强：添加 xG 差值、阵容评分等关键特征

        Args:
            features: V51.0 提取的基础特征
            row: 原始比赛数据

        Returns:
            增强后的特征字典
        """
        # 1. 提取 technical_features 中的关键指标
        tech_features = row.get("technical_features") or {}

        # xG 差值 (如果存在)
        if isinstance(tech_features, dict):
            home_xg = tech_features.get("home_xg") or tech_features.get("xG", {}).get("home")
            away_xg = tech_features.get("away_xg") or tech_features.get("xG", {}).get("away")

            if home_xg is not None and away_xg is not None:
                try:
                    features["xg_diff"] = float(home_xg) - float(away_xg)
                except (TypeError, ValueError):
                    pass

        # 2. 添加赔率特征
        closing_price = row.get("closing_price")
        if closing_price:
            try:
                if isinstance(closing_price, str):
                    closing_price = json.loads(closing_price)
                if isinstance(closing_price, list) and len(closing_price) >= 3:
                    features["odds_home"] = float(closing_price[0])
                    features["odds_draw"] = float(closing_price[1])
                    features["odds_away"] = float(closing_price[2])
                    # 赔率隐含概率
                    features["implied_prob_home"] = 1.0 / features["odds_home"]
                    features["implied_prob_draw"] = 1.0 / features["odds_draw"]
                    features["implied_prob_away"] = 1.0 / features["odds_away"]
            except (json.JSONDecodeError, TypeError, ValueError, IndexError) as e:
                logger.debug("赔率解析失败", match_id=row.get("match_id"), error=str(e))

        return features

    def extract(self) -> PilotDataset:
        """
        执行特征提取主流程

        Returns:
            PilotDataset 对象
        """
        start_time = datetime.now()

        logger.info("开始 V41.300 特征提取流程")

        # Step 1: 查询三位一体样本
        logger.info("Step 1/4: 查询三位一体样本")
        rows = self._query_trio_samples()

        if not rows:
            logger.warning("未找到三位一体样本，请检查数据库")
            return PilotDataset(
                X=np.array([]),
                y=np.array([]),
                metadata=pd.DataFrame(),
                feature_names=[],
                stats=self.stats,
            )

        # Step 2: 提取特征和标签
        logger.info("Step 2/4: 提取特征和标签")
        features_list = []
        labels_list = []
        metadata_list = []

        label_counts = {"H": 0, "D": 0, "A": 0}

        for row in tqdm(rows, desc="提取特征"):
            try:
                # 提取 L2 特征（使用 V51.0 引擎）
                l2_data = row.get("l2_raw_json") or {}

                # 处理嵌套结构
                if isinstance(l2_data, str):
                    l2_data = json.loads(l2_data)

                # V51.0 提取
                base_features = self.refiner.extract_single_match(l2_data, row.get("match_id"))

                # 特征增强
                enhanced_features = self._enrich_features(base_features, row)

                features_list.append(enhanced_features)

                # 提取标签
                label = self._extract_label(row)
                labels_list.append(label)

                # 更新标签计数
                label_map = {0: "H", 1: "D", 2: "A"}
                label_counts[label_map[label]] += 1

                # 收集元数据
                metadata_list.append({
                    "match_id": row.get("match_id"),
                    "league_name": row.get("league_name"),
                    "season": row.get("season"),
                    "home_team": row.get("home_team"),
                    "away_team": row.get("away_team"),
                    "match_date": row.get("match_date"),
                    "home_score": row.get("home_score"),
                    "away_score": row.get("away_score"),
                    "label": label,
                    "label_name": label_map[label],
                })

            except Exception as e:
                logger.warning("特征提取失败", match_id=row.get("match_id"), error=str(e))
                continue

        # Step 3: 构建特征矩阵
        logger.info("Step 3/4: 构建特征矩阵")
        df_features = pd.DataFrame(features_list)

        # 填充 NaN 值
        df_features = df_features.fillna(0.0)

        # 移除非数值列（除了 match_id 等元数据）
        numeric_cols = df_features.select_dtypes(include=[np.number]).columns.tolist()
        df_features = df_features[numeric_cols]

        # V41.300 防护: 过滤掉赛后特征（防止数据泄露）
        feature_names_before = df_features.columns.tolist()
        feature_names_filtered = filter_post_match_features(feature_names_before)
        df_features = df_features[feature_names_filtered]

        logger.info(
            "赛后特征过滤完成",
            features_before=len(feature_names_before),
            features_after=len(feature_names_filtered),
            removed=len(feature_names_before) - len(feature_names_filtered),
        )

        # 转换为 numpy array
        X = df_features.values
        y = np.array(labels_list)

        # 特征名称（过滤后）
        feature_names = feature_names_filtered

        # Step 4: 构建元数据
        df_metadata = pd.DataFrame(metadata_list)

        # 更新统计信息
        self.stats.total_features_extracted = len(feature_names)
        self.stats.feature_matrix_shape = X.shape
        self.stats.label_distribution = label_counts
        self.stats.extraction_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            "V41.300 特征提取完成",
            samples=X.shape[0],
            features=X.shape[1],
            label_distribution=label_counts,
            elapsed_ms=f"{self.stats.extraction_time_ms:.0f}",
        )

        return PilotDataset(
            X=X,
            y=y,
            metadata=df_metadata,
            feature_names=feature_names,
            stats=self.stats,
        )


# ============================================================================
# 命令行入口
# ============================================================================


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="V41.300 Pilot 特征工程提取器 - 将三位一体样本展开成 AI 张量",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 提取所有三位一体样本
  python scripts/ai/v41_300_feature_extractor.py

  # 只提取 2023/2024 赛季
  python scripts/ai/v41_300_feature_extractor.py --season "2023/2024"

  # 只提取 Premier League
  python scripts/ai/v41_300_feature_extractor.py --league "Premier League"

  # 自定义特征维度
  python scripts/ai/v41_300_feature_extractor.py --max-features 300

  # 指定输出目录
  python scripts/ai/v41_300_feature_extractor.py --output data/pilot_v1
        """,
    )

    parser.add_argument(
        "--season",
        type=str,
        help="赛季过滤 (如 '2023/2024')",
    )
    parser.add_argument(
        "--league",
        type=str,
        help="联赛过滤 (如 'Premier League')",
    )
    parser.add_argument(
        "--max-features",
        type=int,
        default=500,
        help="最大特征维度 (默认: 500)",
    )
    parser.add_argument(
        "--no-whitelist",
        action="store_true",
        help="禁用白名单保护",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/pilot_v41_300",
        help="输出目录 (默认: data/pilot_v41_300)",
    )

    args = parser.parse_args()

    # 执行特征提取
    extractor = PilotFeatureExtractor(
        max_features=args.max_features,
        enable_whitelist=not args.no_whitelist,
        season_filter=args.season,
        league_filter=args.league,
    )

    dataset = extractor.extract()

    # 输出统计
    print("\n" + "=" * 60)
    print("V41.300 Pilot 特征提取报告")
    print("=" * 60)
    print(dataset.stats)
    print("=" * 60)

    # 保存数据集
    if dataset.X.shape[0] > 0:
        dataset.save(args.output)
        print(f"\n数据集已保存到: {args.output}/")
        print(f"  - X_features.npy: 特征矩阵 {dataset.X.shape}")
        print(f"  - y_labels.npy: 标签向量 {dataset.y.shape}")
        print(f"  - metadata.csv: 元数据")
        print(f"  - feature_names.json: 特征名称列表")
        print(f"  - stats.json: 统计信息")
        print("\n✅ 特征提取完成！准备进入 Step 3: 模型训练")
    else:
        print("\n❌ 未找到有效样本，请检查数据库")


if __name__ == "__main__":
    main()
