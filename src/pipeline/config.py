"""
Pipeline Configuration
训练流水线配置管理

集中管理所有超参数、特征配置和模型设置。
支持配置验证和环境适配。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import dict, list, Optional, Union

from pathlib import Path


@dataclass
class FeatureConfig:
    """特征配置管理."""

    # 必需特征列表
    required_features: list[str] = field(
        default_factory=lambda: [
            "home_team_strength",
            "away_team_strength",
            "home_form",
            "away_form",
            "h2h_win_rate",
            "home_goals_conceded_avg",
            "away_goals_conceded_avg",
        ]
    )

    # 特征映射 (旧列名 -> 新列名)
    feature_mappings: dict[str, str] = field(
        default_factory=lambda: {
            "home_goals": "home_score",
            "away_goals": "away_score",
            "home_team": "home_team_name",
            "away_team": "away_team_name",
        }
    )

    # 数据质量配置
    quality_checks: dict[str, float] = field(
        default_factory=lambda: {
            "missing_threshold": 0.1,  # 允许10%缺失值
            "outlier_threshold": 3.0,  # 3倍标准差
            "min_samples": 100,  # 最小样本数
        }
    )

    # 特征工程配置
    normalize_features: bool = True
    handle_missing: str = "median"  # median, mean, drop
    encode_categorical: bool = True


@dataclass
class ModelConfig:
    """模型配置管理."""

    # 支持的算法
    supported_algorithms: list[str] = field(
        default_factory=lambda: [
            "xgboost",
            "lightgbm",
            "logistic_regression",
            "random_forest",
        ]
    )

    # 默认算法
    default_algorithm: str = "xgboost"

    # XGBoost参数
    xgboost_params: dict[str, Union[int, float, str]] = field(
        default_factory=lambda: {
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "eval_metric": "logloss",
            "use_label_encoder": False,
        }
    )

    # 超参数优化配置
    hyperparameter_tuning: bool = True
    cv_folds: int = 5
    scoring_metric: str = "f1_weighted"
    max_iter: int = 100

    # 早停配置
    early_stopping: bool = True
    early_stopping_rounds: int = 10
    validation_split: float = 0.2


@dataclass
class TrainingConfig:
    """训练配置管理."""

    # 数据分割
    test_size: float = 0.2
    validation_size: float = 0.2
    stratify: bool = True  # 分层采样
    random_state: int = 42

    # 批处理配置
    batch_size: int = 10000
    memory_limit_gb: float = 4.0

    # 并行配置
    n_jobs: int = -1  # 使用所有CPU核心
    gpu_enabled: bool = False

    # 日志配置
    log_level: str = "INFO"
    log_to_file: bool = True
    log_dir: str = "logs"


@dataclass
class EvaluationConfig:
    """评估配置管理."""

    # 评估指标
    metrics: list[str] = field(
        default_factory=lambda: [
            "accuracy",
            "precision",
            "recall",
            "f1_weighted",
            "roc_auc",
            "log_loss",
            "brier_score",
        ]
    )

    # 交叉验证
    cv_folds: int = 5
    cv_scoring: str = "f1_weighted"

    # 混淆矩阵
    plot_confusion_matrix: bool = True
    plot_feature_importance: bool = True
    plot_learning_curve: bool = True

    # SHAP解释
    compute_shap: bool = True
    shap_samples: int = 100

    # 保存配置
    save_predictions: bool = True
    save_probabilities: bool = True
    save_plots: bool = True


@dataclass
class PipelineConfig:
    """主流水线配置."""

    # 基础路径配置
    project_root: Path = field(default_factory=lambda: Path.cwd())
    artifacts_dir: str = "artifacts"
    models_dir: str = "artifacts/models"
    reports_dir: str = "artifacts/reports"

    # 子配置
    features: Union[FeatureConfig, dict] = field(default_factory=FeatureConfig)
    model: Union[ModelConfig, dict] = field(default_factory=ModelConfig)
    training: Union[TrainingConfig, dict] = field(default_factory=TrainingConfig)
    evaluation: Union[EvaluationConfig, dict] = field(default_factory=EvaluationConfig)

    # 环境配置
    environment: str = "development"  # development, staging, production
    debug_mode: bool = False

    # 外部系统集成
    use_mlflow: bool = False
    use_prefect: bool = True
    use_gpu: bool = False

    def __post_init__(self):
        """初始化后配置验证."""
        # 从环境变量读取配置
        self.environment = os.getenv("ENVIRONMENT", self.environment)
        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"

        # 确保子配置是正确的类型
        if isinstance(self.features, dict):
            self.features = FeatureConfig(**self.features)
        if isinstance(self.model, dict):
            self.model = ModelConfig(**self.model)
        if isinstance(self.training, dict):
            self.training = TrainingConfig(**self.training)
        if isinstance(self.evaluation, dict):
            self.evaluation = EvaluationConfig(**self.evaluation)

        # 验证算法配置
        if self.model.default_algorithm not in self.model.supported_algorithms:
            raise ValueError(
                f"Unsupported algorithm: {self.model.default_algorithm}. "
                f"Supported: {self.model.supported_algorithms}"
            )

        # 创建必要的目录
        self.artifacts_dir = self.project_root / self.artifacts_dir
        self.models_dir = self.project_root / self.models_dir
        self.reports_dir = self.project_root / self.reports_dir

        for dir_path in [self.artifacts_dir, self.models_dir, self.reports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)


# 全局配置实例
default_config = PipelineConfig()
