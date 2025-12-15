"""
ML模块配置 - 企业级机器学习架构配置管理

Phase 2: AI Modeling - 企业级配置管理
"""

from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

import yaml
from pydantic import BaseModel, Field


class ModelType(str, Enum):
    """支持的模型类型"""
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    RANDOM_FOREST = "random_forest"
    LOGISTIC_REGRESSION = "logistic_regression"


class FeatureType(str, Enum):
    """特征工程类型"""
    BASIC = "basic"
    ADVANCED = "advanced"
    TARGET_ENCODING = "target_encoding"
    POLYNOMIAL = "polynomial"


@dataclass
class MLConfig:
    """机器学习配置类 - 企业级配置管理"""

    # 模型配置
    model_type: ModelType = ModelType.XGBOOST
    random_state: int = 42
    n_jobs: int = -1

    # 训练参数
    test_size: float = 0.2
    cv_folds: int = 5
    early_stopping_rounds: int = 50

    # 特征工程
    feature_types: list[FeatureType] = field(default_factory=lambda: [FeatureType.ADVANCED])
    max_features: int = 100
    feature_selection_threshold: float = 0.01

    # XGBoost 特定参数
    xgboost_params: Dict[str, Any] = field(default_factory=lambda: {
        "max_depth": 6,
        "learning_rate": 0.1,
        "n_estimators": 100,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0,
        "reg_lambda": 1,
        "objective": "binary:logistic",
        "eval_metric": "logloss",
    })

    # 数据路径
    data_path: Path = field(default_factory=lambda: Path("data/"))
    model_path: Path = field(default_factory=lambda: Path("models/"))
    mlflow_tracking_uri: str = "http://localhost:5000"
    experiment_name: str = "football-prediction"

    # 质量控制
    min_train_samples: int = 100
    max_train_samples: Optional[int] = None
    validation_split_random_state: int = 123

    # 部署配置
    model_version: str = "1.0.0"
    production_threshold: float = 0.7

    @classmethod
    def from_yaml(cls, config_path: Path) -> "MLConfig":
        """从YAML文件加载配置"""
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        return cls(**config_data)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "model_type": self.model_type.value,
            "random_state": self.random_state,
            "n_jobs": self.n_jobs,
            "test_size": self.test_size,
            "cv_folds": self.cv_folds,
            "early_stopping_rounds": self.early_stopping_rounds,
            "feature_types": [ft.value for ft in self.feature_types],
            "max_features": self.max_features,
            "feature_selection_threshold": self.feature_selection_threshold,
            "xgboost_params": self.xgboost_params,
            "data_path": str(self.data_path),
            "model_path": str(self.model_path),
            "mlflow_tracking_uri": self.mlflow_tracking_uri,
            "experiment_name": self.experiment_name,
            "min_train_samples": self.min_train_samples,
            "max_train_samples": self.max_train_samples,
            "validation_split_random_state": self.validation_split_random_state,
            "model_version": self.model_version,
            "production_threshold": self.production_threshold,
        }

    def save_to_yaml(self, config_path: Path) -> None:
        """保存配置到YAML文件"""
        config_dict = self.to_dict()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)


class MLModelConfig(BaseModel):
    """Pydantic模型配置 - API验证用"""

    model_type: ModelType = Field(default=ModelType.XGBOOST, description="模型类型")
    max_depth: int = Field(default=6, ge=1, le=20, description="XGBoost最大深度")
    learning_rate: float = Field(default=0.1, ge=0.001, le=1.0, description="学习率")
    n_estimators: int = Field(default=100, ge=10, le=1000, description="估计器数量")
    subsample: float = Field(default=0.8, ge=0.1, le=1.0, description="子采样比例")
    colsample_bytree: float = Field(default=0.8, ge=0.1, le=1.0, description="列采样比例")

    class Config:
        """Pydantic配置"""
        use_enum_values = True


# 全局配置实例
DEFAULT_ML_CONFIG = MLConfig()

# 支持的环境配置
ENVIRONMENT_CONFIGS = {
    "development": MLConfig(
        test_size=0.3,
        cv_folds=3,
        n_estimators=50,
        early_stopping_rounds=10,
    ),
    "testing": MLConfig(
        test_size=0.5,
        cv_folds=2,
        n_estimators=10,
        early_stopping_rounds=5,
    ),
    "production": MLConfig(
        test_size=0.2,
        cv_folds=5,
        n_estimators=200,
        early_stopping_rounds=100,
        max_train_samples=10000,  # 生产环境限制样本数量
    ),
}


def get_ml_config(environment: str = "development") -> MLConfig:
    """获取指定环境的ML配置"""
    return ENVIRONMENT_CONFIGS.get(environment, DEFAULT_ML_CONFIG)


def load_config_from_env() -> MLConfig:
    """从环境变量加载配置"""
    import os

    config = DEFAULT_ML_CONFIG

    # 从环境变量覆盖配置
    if os.getenv("ML_MODEL_TYPE"):
        config.model_type = ModelType(os.getenv("ML_MODEL_TYPE"))
    if os.getenv("ML_RANDOM_STATE"):
        config.random_state = int(os.getenv("ML_RANDOM_STATE"))
    if os.getenv("ML_N_JOBS"):
        config.n_jobs = int(os.getenv("ML_N_JOBS"))
    if os.getenv("ML_MLFLOW_URI"):
        config.mlflow_tracking_uri = os.getenv("ML_MLFLOW_URI")
    if os.getenv("ML_EXPERIMENT_NAME"):
        config.experiment_name = os.getenv("ML_EXPERIMENT_NAME")

    return config