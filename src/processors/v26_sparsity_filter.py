#!/usr/bin/env python3
"""
V26.5 特征剪枝过滤器 - 维度治理核心模块 (Phase 1.3 + 2.1 + FotMob 优化版)
=========================================================================

核心功能:
    1. 稀疏度检测: 自动剔除全零、全NaN或低方差特征
    2. 维度控制: 强制将特征维度控制在 6000 以内 (Phase 1.3 优化)
    3. 智能降维: 基于特征重要性排序，保留高价值特征
    4. 核心特征保护: 白名单机制保护滚动特征、赛前特征、FotMob 核心特征

V26.5 → V26.2 核心改进:
    - 新增 FotMob 核心特征白名单 (expected_goal, xg, big_chance, shot 等)
    - 保护 FotMob 高价值技术统计特征不被剪枝
    - 确保多数据源特征提取质量一致性

V26.2 → V26.1 核心改进:
    - max_features: 8000 → 6000 (减少 25% 维度)
    - sparsity_threshold: 0.95 → 0.90 (更激进的稀疏特征剪枝)
    - 新增核心特征白名单机制 (保护滚动特征、赛前特征)
    - 目标内存占用减少 40%

Phase 2.1 多进程优化:
    - 使用文件系统同步特征统计 (跨进程安全)
    - 每个进程独立统计，主进程聚合
    - 支持并发环境下的特征剪枝

设计原则:
    - 在线学习: 随着处理比赛增加，动态更新特征统计
    - 增量过滤: 每处理 N 场比赛后触发一次剪枝
    - 内存安全: 确保特征维度不会导致 OOM
    - 多进程安全: 支持 ProcessPoolExecutor 并发环境
    - 数据源感知: 保护多数据源的核心特征

Author: Principal Architect & Performance Expert
Version: V26.5 (FotMob Feature Protection)
Date: 2026-01-06
"""

import gc
import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# Phase 2.1: 多进程安全支持
# ============================================================================

# 特征统计文件路径（用于跨进程同步)
_STATS_FILE_PATH = Path("data/monitoring/feature_stats_registry.pkl")


def save_registry_to_file(registry: "FeatureStatsRegistry", filepath: Path = _STATS_FILE_PATH) -> None:
    """将注册表保存到文件（跨进程安全）"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "wb") as f:
        pickle.dump(registry, f)


def load_registry_from_file(filepath: Path = _STATS_FILE_PATH) -> "FeatureStatsRegistry | None":
    """从文件加载注册表"""
    if not filepath.exists():
        return None
    with open(filepath, "rb") as f:
        return pickle.load(f)


def merge_registries(
    target: "FeatureStatsRegistry",
    *sources: "FeatureStatsRegistry",
) -> None:
    """
    合并多个注册表到一个目标注册表

    Args:
        target: 目标注册表
        *sources: 源注册表（可多个）
    """
    for source in sources:
        for key, source_stat in source.stats.items():
            if key not in target.stats:
                target.stats[key] = source_stat
            else:
                # 合并统计信息
                target_stat = target.stats[key]
                target_stat.count += source_stat.count
                target_stat.nonzero_count += source_stat.nonzero_count
                target_stat.nan_count += source_stat.nan_count
                target_stat.sum_value += source_stat.sum_value
                target_stat.sum_squared += source_stat.sum_squared
                target_stat.min_value = min(target_stat.min_value, source_stat.min_value)
                target_stat.max_value = max(target_stat.max_value, source_stat.max_value)
                target_stat.unique_values.update(source_stat.unique_values)

        target.processed_count += source.processed_count


# ============================================================================
# V26.2 核心特征白名单 (Phase 1.3 新增)
# ============================================================================

# 核心特征白名单：保护高价值特征不被剪枝
CORE_FEATURE_WHITELIST = {
    # 滚动特征 (V17.0 基线)
    "rolling_xg",
    "rolling_xg_std",
    "rolling_shots",
    "rolling_shots_std",
    "rolling_shots_on_target",
    "rolling_shots_on_target_std",
    "rolling_possession",
    "rolling_possession_std",
    "rolling_team_rating",
    "rolling_team_rating_std",
    # 赛前特征 (V18.0)
    "table_position",
    "table_position_diff",
    "points",
    "points_diff",
    "recent_form_points",
    # ELO 评级 (V19.0)
    "elo_gap",
    "adjusted_elo_gap",
    # 疲劳度 (V19.0)
    "fatigue_index",
    "fatigue_diff",
    "rest_days",
    # 战意 (V19.0)
    "relegation_incentive",
    "incentive_diff",
    "desperation",
    # 平局敏感度 (V19.4)
    "table_proximity",
    "low_scoring_tendency",
    # V26.5: FotMob 核心特征保护
    "expected_goal",  # Expected Goals (xG)
    "xg",  # xG 简写
    "big_chance",  # Big Chances Created
    "ballpossesion",  # Ball Possession (FotMob 拼写)
    "ballpossession",  # Ball Possession (标准拼写)
    "shot",  # Shots
    "shotontarget",  # Shots on Target
    "passaccuracy",  # Pass Accuracy
    "aerial",  # Aerial Duels
    "tackle",  # Tackles
    "interception",  # Interceptions
}


def is_core_feature(feature_key: str) -> bool:
    """检查特征是否为核心特征（白名单保护）"""
    key_lower = feature_key.lower()
    for prefix in CORE_FEATURE_WHITELIST:
        if prefix in key_lower:
            return True
    return False


# ============================================================================
# 特征统计类
# ============================================================================


@dataclass
class FeatureStats:
    """单个特征的统计信息"""

    key: str
    count: int = 0  # 出现次数
    nonzero_count: int = 0  # 非零值次数
    nan_count: int = 0  # NaN 次数
    sum_value: float = 0.0  # 累加值
    sum_squared: float = 0.0  # 平方和
    min_value: float = float("inf")
    max_value: float = float("-inf")
    unique_values: set = field(default_factory=set)  # 唯一值集合（采样）

    @property
    def sparsity(self) -> float:
        """稀疏度: 0 = 密集, 1 = 全零"""
        if self.count == 0:
            return 1.0
        return 1.0 - (self.nonzero_count / self.count)

    @property
    def mean(self) -> float:
        """均值"""
        return self.sum_value / self.count if self.count > 0 else 0.0

    @property
    def variance(self) -> float:
        """方差"""
        if self.count <= 1:
            return 0.0
        mean = self.mean
        return (self.sum_squared / self.count) - (mean * mean)

    @property
    def std(self) -> float:
        """标准差"""
        return np.sqrt(self.variance)

    @property
    def unique_ratio(self) -> float:
        """唯一值比例（采样）"""
        if self.count == 0:
            return 0.0
        # 限制唯一值集合大小，避免内存爆炸
        return min(len(self.unique_values), 100) / self.count

    def update(self, value: float) -> None:
        """更新统计信息"""
        self.count += 1

        if np.isnan(value):
            self.nan_count += 1
            return

        if value != 0.0:
            self.nonzero_count += 1

        self.sum_value += value
        self.sum_squared += value * value
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)

        # 采样唯一值（最多保留 100 个）
        if len(self.unique_values) < 100:
            self.unique_values.add(value)


# ============================================================================
# 全局特征统计注册表
# ============================================================================


class FeatureStatsRegistry:
    """
    特征统计注册表 - 跨所有比赛追踪特征统计

    V26.2 优化:
        - max_features: 8000 → 6000 (减少 25% 维度)
        - sparsity_threshold: 0.95 → 0.90 (更激进剪枝)
        - 核心特征白名单保护机制

    设计:
        - 增量更新: 每处理一场比赛，更新统计信息
        - 定期剪枝: 每处理 N 场后触发剪枝
        - 内存安全: 只保留必要的统计信息
    """

    def __init__(
        self,
        prune_interval: int = 100,
        max_features: int = 10000,  # V26.7: 6000 → 10000 (支持 GOLD 标准 6346+ 维)
        sparsity_threshold: float = 0.90,  # V26.2: 0.95 → 0.90
        min_variance: float = 1e-6,
    ):
        """
        初始化特征统计注册表

        Args:
            prune_interval: 剪枝触发间隔（每处理 N 场后触发）
            max_features: 最大特征数（硬限制）V26.2: 6000
            sparsity_threshold: 稀疏度阈值（超过则剔除）V26.2: 0.90
            min_variance: 最小方差阈值（低于则剔除）
        """
        self.prune_interval = prune_interval
        self.max_features = max_features
        self.sparsity_threshold = sparsity_threshold
        self.min_variance = min_variance

        self.stats: dict[str, FeatureStats] = {}
        self.processed_count = 0
        self.pruned_keys: set[str] = set()
        self.core_feature_count = 0  # V26.2: 核心特征计数

    def update(self, features: dict[str, float]) -> None:
        """
        更新特征统计（单场比赛）

        Args:
            features: 特征字典（只包含数值型特征）
        """
        self.processed_count += 1

        for key, value in features.items():
            # 跳过元数据
            if key.startswith("_"):
                continue

            # 获取或创建统计对象
            if key not in self.stats:
                self.stats[key] = FeatureStats(key=key)

            # 更新统计
            self.stats[key].update(value)

    def should_prune(self) -> bool:
        """检查是否应该触发剪枝"""
        return self.processed_count % self.prune_interval == 0 or len(self.stats) > self.max_features * 1.5

    def get_pruned_keys(self) -> set[str]:
        """
        获取需要剪枝的特征键

        V26.2 剪枝策略 (Phase 1.3 优化):
            1. 核心特征保护: 白名单特征永不剪枝
            2. 高稀疏度: sparsity > 0.90 (90% 以上值为零，V26.2 更激进)
            3. 低方差: variance < 1e-6 (几乎常量)
            4. 低唯一值: unique_ratio < 0.01 (变化极小)
            5. 特征数超限: 按方差排序，保留前 max_features 个
        """
        if not self.stats:
            return set()

        pruned = set()
        self.core_feature_count = 0

        for key, stat in self.stats.items():
            # V26.2: 核心特征白名单保护
            if is_core_feature(key):
                self.core_feature_count += 1
                continue

            # 规则 1: 高稀疏度 (V26.2: 0.95 → 0.90)
            if stat.sparsity > self.sparsity_threshold:
                pruned.add(key)
                continue

            # 规则 2: 低方差
            if stat.variance < self.min_variance and stat.count > 10:
                pruned.add(key)
                continue

            # 规则 3: 低唯一值（针对离散特征）
            if stat.unique_ratio < 0.01 and stat.count > 100:
                pruned.add(key)
                continue

        # 规则 4: 特征数超限 - 按方差排序保留高方差特征
        remaining = set(self.stats.keys()) - pruned
        if len(remaining) > self.max_features:
            # 按方差降序排序
            sorted_features = sorted(
                remaining,
                key=lambda k: (self.stats[k].variance, self.stats[k].count),
                reverse=True,
            )
            # 只保留前 max_features 个
            keep = set(sorted_features[: self.max_features])
            pruned.update(remaining - keep)

        self.pruned_keys = pruned
        return pruned

    def prune_features(
        self,
        features: dict[str, Any],
    ) -> dict[str, Any]:
        """
        对单场比赛的特征执行剪枝

        Args:
            features: 原始特征字典

        Returns:
            剪枝后的特征字典
        """
        if not self.pruned_keys:
            return features

        # 移除被剪枝的特征
        pruned = {k: v for k, v in features.items() if k not in self.pruned_keys}

        removed = len(features) - len(pruned)
        if removed > 0:
            logger.debug(f"特征剪枝完成: 原始 {len(features)}, 剪枝 {removed}, 剩余 {len(pruned)}")

        return pruned

    def get_stats_report(self) -> dict[str, Any]:
        """获取统计报告（V26.2 增强版）"""
        if not self.stats:
            return {}

        total_stats = len(self.stats)
        pruned_stats = len(self.pruned_keys)
        active_stats = total_stats - pruned_stats

        # 计算平均稀疏度
        sparsities = [s.sparsity for s in self.stats.values()]
        avg_sparsity = np.mean(sparsities) if sparsities else 0.0

        # 计算平均方差
        variances = [s.variance for s in self.stats.values()]
        avg_variance = np.mean(variances) if variances else 0.0

        return {
            "version": "V26.5",  # V26.5: FotMob 特征保护
            "processed_matches": self.processed_count,
            "total_features": total_stats,
            "pruned_features": pruned_stats,
            "active_features": active_stats,
            "core_features": self.core_feature_count,
            "avg_sparsity": avg_sparsity,
            "avg_variance": avg_variance,
            "max_features_limit": self.max_features,
            "sparsity_threshold": self.sparsity_threshold,
        }

    def reset(self) -> None:
        """重置统计（用于新批次）"""
        self.stats.clear()
        self.processed_count = 0
        self.pruned_keys.clear()


# ============================================================================
# 全局单例
# ============================================================================

_GLOBAL_REGISTRY: FeatureStatsRegistry | None = None


def get_global_registry() -> FeatureStatsRegistry:
    """获取全局特征统计注册表（V26.7 修复版）"""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = FeatureStatsRegistry(
            prune_interval=100,
            max_features=10000,  # V26.7: 6000 → 10000 (支持 GOLD 标准)
            sparsity_threshold=0.90,  # V26.2: 0.95 → 0.90
            min_variance=1e-6,
        )
    return _GLOBAL_REGISTRY


def reset_global_registry() -> None:
    """重置全局注册表（用于新批次）"""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is not None:
        _GLOBAL_REGISTRY.reset()


# ============================================================================
# 辅助函数
# ============================================================================


def apply_sparsity_filter(
    features: dict[str, Any],
    registry: FeatureStatsRegistry | None = None,
) -> dict[str, Any]:
    """
    应用稀疏度过滤器到特征字典

    Args:
        features: 原始特征字典
        registry: 特征统计注册表（默认使用全局注册表）

    Returns:
        剪枝后的特征字典
    """
    if registry is None:
        registry = get_global_registry()

    # 提取数值型特征进行统计更新
    numeric_features = {
        k: v
        for k, v in features.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool) and not k.startswith("_")
    }

    # 更新统计
    registry.update(numeric_features)

    # 检查是否需要触发剪枝
    if registry.should_prune():
        pruned_keys = registry.get_pruned_keys()
        logger.info(
            f"触发特征剪枝: 已处理 {registry.processed_count} 场, "
            f"总特征 {len(registry.stats)}, 剪枝 {len(pruned_keys)} 个"
        )

        # 执行 GC
        gc.collect()

    # 执行剪枝
    return registry.prune_features(features)


# ============================================================================
# 模块测试
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 模拟测试
    registry = FeatureStatsRegistry(
        prune_interval=10,
        max_features=100,
        sparsity_threshold=0.8,
    )

    # 生成测试特征
    for i in range(50):
        features = {f"feature_{j}": np.random.randn() if j < 20 else 0.0 for j in range(150)}
        registry.update(features)

    # 检查是否触发剪枝
    if registry.should_prune():
        pruned = registry.get_pruned_keys()
        logger.info(f"剪枝特征数: {len(pruned)}")

    # 输出报告
    report = registry.get_stats_report()
    logger.info(f"统计报告: {report}")
