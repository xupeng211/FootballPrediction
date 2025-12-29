#!/usr/bin/env python3
"""
V1.1 ML 配置中心 - 消除硬编码，工业级配置管理
=================================================

功能:
1. 联赛配置 (League IDs, 赛季范围)
2. 特征工程参数 (EWMA alpha, 滑动窗口大小)
3. 模型训练参数 (XGBoost 超参数)
4. 数据质量阈值 (最低特征数, 质量等级)

作者: Senior DevOps & SRE
日期: 2025-12-29
Phase: V1.1 Production Hardening
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ============================================
# 枚举定义
# ============================================


class ExtractionQuality(str, Enum):
    """数据提取质量等级"""

    FULL = "full"  # 完整提取 (≥10 特征)
    PARTIAL = "partial"  # 部分提取 (5-9 特征)
    FAILED = "failed"  # 提取失败 (<5 特征)


class MatchResult(str, Enum):
    """比赛结果"""

    AWAY_WIN = "away_win"  # 0
    DRAW = "draw"  # 1
    HOME_WIN = "home_win"  # 2


# ============================================
# 联赛配置
# ============================================


@dataclass(frozen=True)
class LeagueConfig:
    """联赛配置 (不可变)"""

    league_id: int
    fotmob_id: int
    name: str
    country: str
    active: bool = True
    priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "league_id": self.league_id,
            "fotmob_id": self.fotmob_id,
            "name": self.name,
            "country": self.country,
            "active": self.active,
            "priority": self.priority,
        }


class LeagueRegistry:
    """联赛注册表 (单例)"""

    # 五大联赛配置
    _LEAGUES: dict[str, LeagueConfig] = {
        "epl": LeagueConfig(
            league_id=47,
            fotmob_id=47,
            name="Premier League",
            country="England",
            active=True,
            priority=1,
        ),
        "serie_a": LeagueConfig(
            league_id=55,
            fotmob_id=55,
            name="Serie A",
            country="Italy",
            active=True,
            priority=2,
        ),
        "la_liga": LeagueConfig(
            league_id=87,
            fotmob_id=87,
            name="La Liga",
            country="Spain",
            active=True,
            priority=3,
        ),
        "bundesliga": LeagueConfig(
            league_id=53,
            fotmob_id=53,
            name="Bundesliga",
            country="Germany",
            active=True,
            priority=4,
        ),
        "ligue1": LeagueConfig(
            league_id=54,
            fotmob_id=54,
            name="Ligue 1",
            country="France",
            active=True,
            priority=5,
        ),
    }

    # FotMob League ID 映射
    _FOTMOB_IDS: dict[int, str] = {
        47: "epl",
        55: "serie_a",
        87: "la_liga",
        53: "bundesliga",
        54: "ligue1",
    }

    @classmethod
    def get_by_name(cls, name: str) -> LeagueConfig | None:
        """通过名称获取联赛配置"""
        return cls._LEAGUES.get(name.lower())

    @classmethod
    def get_by_id(cls, league_id: int) -> LeagueConfig | None:
        """通过 ID 获取联赛配置"""
        for league in cls._LEAGUES.values():
            if league.league_id == league_id:
                return league
        return None

    @classmethod
    def get_by_fotmob_id(cls, fotmob_id: int) -> LeagueConfig | None:
        """通过 FotMob ID 获取联赛配置"""
        name = cls._FOTMOB_IDS.get(fotmob_id)
        return cls._LEAGUES.get(name) if name else None

    @classmethod
    def get_active_leagues(cls) -> list[LeagueConfig]:
        """获取所有活跃联赛"""
        return [lg for lg in cls._LEAGUES.values() if lg.active]

    @classmethod
    def get_all_ids(cls) -> list[int]:
        """获取所有联赛 ID"""
        return [lg.league_id for lg in cls._LEAGUES.values()]

    @classmethod
    def get_season_range(cls) -> tuple[str, str]:
        """获取赛季范围"""
        return ("20/21", "24/25")


# ============================================
# 特征工程配置
# ============================================


@dataclass(frozen=True)
class FeatureEngineeringConfig:
    """特征工程参数配置"""

    # EWMA 参数
    ewma_alpha: float = 0.3  # 指数加权移动平均的 alpha 参数

    # 滑动窗口参数
    rolling_window_size: int = 5  # 滚动窗口大小 (比赛场数)

    # 最小数据要求
    min_matches_for_stats: int = 3  # 计算统计所需的最少比赛数

    # 特征质量阈值
    min_valid_features: int = 10  # FULL 质量要求的最低特征数
    partial_min_features: int = 5  # PARTIAL 质量要求的最低特征数

    # 数据源配置
    primary_data_source: str = "match_features_v1"

    def __post_init__(self):
        """验证参数"""
        if not 0 < self.ewma_alpha <= 1:
            raise ValueError("ewma_alpha 必须在 (0, 1] 范围内")
        if self.rolling_window_size < 1:
            raise ValueError("rolling_window_size 必须大于 0")


# ============================================
# 模型训练配置
# ============================================


@dataclass(frozen=True)
class ModelTrainingConfig:
    """XGBoost 模型训练参数配置"""

    # 数据划分
    train_seasons: list[str] = field(default_factory=lambda: ["20/21", "21/22", "22/23", "23/24"])
    test_season: str = "24/25"

    # XGBoost 超参数
    n_estimators: int = 200
    max_depth: int = 6
    learning_rate: float = 0.1
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    random_state: int = 42

    # 训练参数
    early_stopping_rounds: int | None = None
    eval_metric: list[str] = field(default_factory=lambda: ["mlogloss", "merror"])

    # 目标配置
    objective: str = "multi:softprob"
    num_class: int = 3

    # 评估指标
    metrics: list[str] = field(default_factory=lambda: ["accuracy", "log_loss", "roc_auc"])


# ============================================
# 统一 ML 配置
# ============================================


class MLSettings(BaseModel):
    """统一 ML 配置类"""

    # 特征工程
    feature_engineering: FeatureEngineeringConfig = Field(
        default_factory=FeatureEngineeringConfig, description="特征工程参数"
    )

    # 模型训练
    model_training: ModelTrainingConfig = Field(default_factory=ModelTrainingConfig, description="模型训练参数")

    # 默认联赛
    default_league: str = Field(default="epl", description="默认联赛")

    # 批量处理
    batch_size: int = Field(default=100, description="批量处理大小")

    # 并发控制
    max_workers: int = Field(default=4, description="最大工作线程数")

    # 路径配置
    model_dir: Path = Field(default=Path("models"), description="模型目录")
    log_dir: Path = Field(default=Path("logs"), description="日志目录")
    data_dir: Path = Field(default=Path("data"), description="数据目录")

    # 验证器
    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        """验证批量大小"""
        if not 1 <= v <= 1000:
            raise ValueError("batch_size 必须在 1-1000 之间")
        return v

    @field_validator("max_workers")
    @classmethod
    def validate_max_workers(cls, v: int) -> int:
        """验证最大工作线程数"""
        if v < 1:
            raise ValueError("max_workers 必须大于 0")
        return v

    # 便捷方法
    def get_league_config(self, league: str | None = None) -> LeagueConfig:
        """获取联赛配置"""
        name = league or self.default_league
        config = LeagueRegistry.get_by_name(name)
        if config is None:
            raise ValueError(f"未知联赛: {name}")
        return config

    def get_season_range(self) -> tuple[str, str]:
        """获取赛季范围"""
        return LeagueRegistry.get_season_range()

    def ensure_dirs(self) -> None:
        """确保必要目录存在"""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)


# ============================================
# 全局单例
# ============================================


_ml_settings: MLSettings | None = None


def get_ml_settings(**kwargs) -> MLSettings:
    """获取 ML 配置单例"""
    global _ml_settings
    if _ml_settings is None:
        _ml_settings = MLSettings(**kwargs)
        _ml_settings.ensure_dirs()
    return _ml_settings


def reload_ml_settings() -> MLSettings:
    """重新加载 ML 配置"""
    global _ml_settings
    _ml_settings = None
    return get_ml_settings()


# ============================================
# 配置导出 (用于调试)
# ============================================


def export_config_to_json(output_path: Path | None = None) -> str:
    """导出配置为 JSON (用于调试)"""
    settings = get_ml_settings()

    config_dict = {
        "feature_engineering": {
            "ewma_alpha": settings.feature_engineering.ewma_alpha,
            "rolling_window_size": settings.feature_engineering.rolling_window_size,
            "min_valid_features": settings.feature_engineering.min_valid_features,
        },
        "model_training": {
            "train_seasons": settings.model_training.train_seasons,
            "test_season": settings.model_training.test_season,
            "n_estimators": settings.model_training.n_estimators,
            "max_depth": settings.model_training.max_depth,
            "learning_rate": settings.model_training.learning_rate,
        },
        "leagues": {name: league.to_dict() for name, league in LeagueRegistry._LEAGUES.items()},
    }

    json_str = json.dumps(config_dict, indent=2, ensure_ascii=False)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_str, encoding="utf-8")

    return json_str


# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":
    # 展示配置
    settings = get_ml_settings()

    print("=== V1.1 ML 配置中心 ===\n")

    print("特征工程配置:")
    print(f"  EWMA Alpha: {settings.feature_engineering.ewma_alpha}")
    print(f"  滚动窗口: {settings.feature_engineering.rolling_window_size}")
    print(f"  最低特征数: {settings.feature_engineering.min_valid_features}")

    print("\n模型训练配置:")
    print(f"  训练赛季: {settings.model_training.train_seasons}")
    print(f"  测试赛季: {settings.model_training.test_season}")
    print(f"  N Estimators: {settings.model_training.n_estimators}")
    print(f"  Max Depth: {settings.model_training.max_depth}")

    print("\n联赛配置:")
    for league in LeagueRegistry.get_active_leagues():
        print(f"  {league.name}: ID={league.league_id}, Priority={league.priority}")

    print("\n导出配置:")
    print(export_config_to_json())
