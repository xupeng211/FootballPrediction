"""
Feature Builder
在线特征计算器

确保训练和推理特征的一致性（Feature Parity）。
提供特征构建、验证和转换功能。
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Union
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.impute import SimpleImputer

from src.features.feature_definitions import (
    FEATURE_DEFINITIONS,
    FeatureType
)
from .errors import FeatureBuilderError, ErrorCode

logger = logging.getLogger(__name__)


class FeatureBuilder:
    """
    在线特征构建器

    确保与训练时完全一致的特征处理流程：
    1. 特征选择和过滤
    2. 缺失值处理
    3. 特征编码和标准化
    4. 时间特征工程
    5. 特征验证
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化特征构建器

        Args:
            config_path: 特征配置文件路径
        """
        self.feature_definitions = FEATURE_DEFINITIONS
        self.feature_encoders = {}
        self.feature_scalers = {}
        self.feature_imputers = {}
        self.feature_columns = []
        self.numeric_features = []
        self.categorical_features = []
        self.time_features = []

        # 统计信息（从训练时加载）
        self.feature_stats = {}

        # 初始化编码器
        self._initialize_encoders()

        if config_path:
            self._load_config(config_path)

    def _initialize_encoders(self):
        """初始化特征编码器和标准化器"""
        # 按特征类型分组
        for name, definition in self.feature_definitions.items():
            self.feature_columns.append(name)

            if definition.type == FeatureType.NUMERIC:
                self.numeric_features.append(name)
                # 初始化数值特征的标准化器
                self.feature_scalers[name] = StandardScaler()
                self.feature_imputers[name] = SimpleImputer(strategy='mean')

            elif definition.type == FeatureType.CATEGORICAL:
                self.categorical_features.append(name)
                # 初始化分类特征的编码器
                self.feature_encoders[name] = OneHotEncoder(
                    handle_unknown='ignore',
                    sparse_output=False
                )
                self.feature_imputers[name] = SimpleImputer(strategy='most_frequent')

            elif definition.type == FeatureType.TIME:
                self.time_features.append(name)

    def _load_config(self, config_path: str):
        """加载特征配置（从训练时保存的配置）"""
        try:
            with open(config_path) as f:
                config = json.load(f)

            # 加载特征统计信息
            self.feature_stats = config.get('feature_stats', {})

            # 加载编码器参数
            if 'encoders' in config:
                self._load_encoders(config['encoders'])

            # 加载标准化器参数
            if 'scalers' in config:
                self._load_scalers(config['scalers'])

            logger.info(f"Feature configuration loaded from {config_path}")

        except Exception as e:
            raise FeatureBuilderError(f"Failed to load feature config: {str(e)}")

    def _load_encoders(self, encoder_configs: dict[str, dict]):
        """加载编码器配置"""
        for feature_name, config in encoder_configs.items():
            if feature_name in self.categorical_features:
                # 重建OneHotEncoder
                categories = config.get('categories', [])
                if categories:
                    self.feature_encoders[feature_name] = OneHotEncoder(
                        categories=categories,
                        handle_unknown='ignore',
                        sparse_output=False
                    )

    def _load_scalers(self, scaler_configs: dict[str, dict]):
        """加载标准化器配置"""
        for feature_name, config in scaler_configs.items():
            if feature_name in self.numeric_features:
                # 重建StandardScaler
                mean = np.array(config.get('mean', [0]))
                scale = np.array(config.get('scale', [1]))

                scaler = StandardScaler()
                scaler.mean_ = mean
                scaler.scale_ = scale
                self.feature_scalers[feature_name] = scaler

    async def build_features(
        self,
        raw_data: dict[str, Any],
        match_info: Optional[dict[str, Any]] = None,
        historical_data: Optional[dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        构建特征DataFrame

        Args:
            raw_data: 原始数据字典
            match_info: 比赛信息
            historical_data: 历史数据

        Returns:
            pd.DataFrame: 构建的特征DataFrame

        Raises:
            FeatureBuilderError: 特征构建失败
        """
        try:
            # 1. 基础特征提取
            features = await self._extract_base_features(raw_data, match_info)

            # 2. 时间特征工程
            time_features = self._build_time_features(features)
            features.update(time_features)

            # 3. 滚动窗口特征（如果有历史数据）
            if historical_data:
                rolling_features = await self._build_rolling_features(
                    features, historical_data
                )
                features.update(rolling_features)

            # 4. 转换为DataFrame
            df = pd.DataFrame([features])

            # 5. 特征验证
            self._validate_features(df)

            # 6. 特征预处理
            df = self._preprocess_features(df)

            # 7. 特征编码
            df = self._encode_features(df)

            logger.info(f"Features built successfully: {len(df.columns)} features")
            return df

        except Exception as e:
            raise FeatureBuilderError(
                f"Failed to build features: {str(e)}",
                details={"raw_data_keys": list(raw_data.keys()) if raw_data else []}
            )

    async def _extract_base_features(
        self,
        raw_data: dict[str, Any],
        match_info: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """提取基础特征"""
        features = {}

        # 从原始数据中提取
        for feature_name in self.feature_columns:
            if feature_name in raw_data:
                features[feature_name] = raw_data[feature_name]

        # 从比赛信息中提取
        if match_info:
            # 主客队信息
            if 'home_team' in match_info:
                features['home_team'] = match_info['home_team']
            if 'away_team' in match_info:
                features['away_team'] = match_info['away_team']

            # 比赛时间信息
            if 'match_date' in match_info:
                features['match_date'] = match_info['match_date']
            if 'league_id' in match_info:
                features['league_id'] = match_info['league_id']

        # 计算衍生特征
        features = self._calculate_derived_features(features)

        return features

    def _calculate_derived_features(self, features: dict[str, Any]) -> dict[str, Any]:
        """计算衍生特征"""
        derived = {}

        # 进球差
        if 'home_goals' in features and 'away_goals' in features:
            derived['goal_difference'] = features['home_goals'] - features['away_goals']
            derived['total_goals'] = features['home_goals'] + features['away_goals']

        # 控球率差
        if 'home_possession' in features and 'away_possession' in features:
            derived['possession_difference'] = (
                features['home_possession'] - features['away_possession']
            )

        # 射门效率
        if 'home_shots' in features and 'home_goals' in features:
            if features['home_shots'] > 0:
                derived['home_shot_efficiency'] = (
                    features['home_goals'] / features['home_shots']
                )
            else:
                derived['home_shot_efficiency'] = 0.0

        if 'away_shots' in features and 'away_goals' in features:
            if features['away_shots'] > 0:
                derived['away_shot_efficiency'] = (
                    features['away_goals'] / features['away_shots']
                )
            else:
                derived['away_shot_efficiency'] = 0.0

        return derived

    def _build_time_features(self, features: dict[str, Any]) -> dict[str, Any]:
        """构建时间特征"""
        time_features = {}

        if 'match_date' in features:
            match_date = features['match_date']

            # 处理不同格式的时间
            if isinstance(match_date, str):
                try:
                    match_date = pd.to_datetime(match_date)
                except Exception:
                    match_date = datetime.now()
            elif isinstance(match_date, (int, float)):
                match_date = datetime.fromtimestamp(match_date)

            # 提取时间特征
            time_features.update({
                'match_day_of_week': match_date.dayofweek,
                'match_month': match_date.month,
                'match_hour': match_date.hour,
                'match_weekend': 1 if match_date.dayofweek >= 5 else 0,
                'match_season': self._get_season(match_date.month)
            })

        return time_features

    def _get_season(self, month: int) -> str:
        """获取季节"""
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'autumn'

    async def _build_rolling_features(
        self,
        current_features: dict[str, Any],
        historical_data: dict[str, Any]
    ) -> dict[str, Any]:
        """构建滚动窗口特征"""
        rolling_features = {}

        try:
            # 获取历史数据
            team_history = historical_data.get('team_history', {})

            if 'home_team' in current_features:
                home_team = current_features['home_team']
                if home_team in team_history:
                    home_history = team_history[home_team]
                    rolling_features.update(self._calculate_rolling_stats(
                        home_history, prefix='home_'
                    ))

            if 'away_team' in current_features:
                away_team = current_features['away_team']
                if away_team in team_history:
                    away_history = team_history[away_team]
                    rolling_features.update(self._calculate_rolling_stats(
                        away_history, prefix='away_'
                    ))

        except Exception as e:
            logger.warning(f"Failed to build rolling features: {e}")

        return rolling_features

    def _calculate_rolling_stats(
        self,
        history: list[dict[str, Any]],
        prefix: str,
        window: int = 5
    ) -> dict[str, Any]:
        """计算滚动统计特征"""
        if not history or len(history) < window:
            return {}

        # 获取最近的窗口数据
        recent_history = history[-window:]

        rolling_stats = {}

        # 计算各种统计量
        numeric_fields = ['goals', 'shots', 'possession', 'corners']

        for field in numeric_fields:
            values = [match.get(field, 0) for match in recent_history]
            if values:
                rolling_stats.update({
                    f'{prefix}{field}_rolling_{window}_mean': np.mean(values),
                    f'{prefix}{field}_rolling_{window}_std': np.std(values),
                    f'{prefix}{field}_rolling_{window}_max': np.max(values),
                    f'{prefix}{field}_rolling_{window}_min': np.min(values),
                    f'{prefix}{field}_rolling_{window}_sum': np.sum(values)
                })

        return rolling_stats

    def _validate_features(self, df: pd.DataFrame):
        """验证特征数据"""
        try:
            # TODO: 实现特征验证逻辑
            # 临时注释掉validate_feature_data调用
            # validate_feature_data(df)

            # 基础验证
            required_columns = ['home_goals', 'away_goals']
            for col in required_columns:
                if col not in df.columns:
                    raise FeatureBuilderError(f"Missing required feature: {col}")

        except Exception as e:
            raise FeatureBuilderError(
                f"Feature validation failed: {str(e)}",
                details={"features": list(df.columns)}
            )

    def _preprocess_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """特征预处理"""
        processed_df = df.copy()

        # 处理数值特征
        for feature in self.numeric_features:
            if feature in processed_df.columns:
                # 缺失值填充
                if feature in self.feature_imputers:
                    # 如果有训练时的统计信息，使用训练时的均值
                    if feature in self.feature_stats:
                        mean_value = self.feature_stats[feature].get('mean', 0)
                        processed_df[feature].fillna(mean_value, inplace=True)
                    else:
                        # 使用imputer
                        values = processed_df[[feature]].values
                        filled_values = self.feature_imputers[feature].fit_transform(values)
                        processed_df[feature] = filled_values.flatten()

                # 转换数据类型
                processed_df[feature] = pd.to_numeric(processed_df[feature], errors='coerce')

        # 处理分类特征
        for feature in self.categorical_features:
            if feature in processed_df.columns:
                # 缺失值填充
                if feature in self.feature_imputers:
                    # 如果有训练时的统计信息，使用训练时的众数
                    if feature in self.feature_stats:
                        mode_value = self.feature_stats[feature].get('mode', 'unknown')
                        processed_df[feature].fillna(mode_value, inplace=True)
                    else:
                        # 使用imputer
                        values = processed_df[[feature]].values
                        filled_values = self.feature_imputers[feature].fit_transform(values)
                        processed_df[feature] = filled_values.flatten()

                # 转换为字符串类型
                processed_df[feature] = processed_df[feature].astype(str)

        return processed_df

    def _encode_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """特征编码"""
        encoded_df = df.copy()

        # 编码分类特征
        for feature in self.categorical_features:
            if feature in encoded_df.columns:
                try:
                    if feature in self.feature_encoders:
                        # 使用训练时的编码器
                        encoder = self.feature_encoders[feature]
                        encoded = encoder.transform(encoded_df[[feature]])

                        # 创建OneHot编码列名
                        if hasattr(encoder, 'categories_'):
                            category_names = encoder.categories_[0]
                            feature_names = [f"{feature}_{cat}" for cat in category_names]
                        else:
                            feature_names = [f"{feature}_{i}" for i in range(encoded.shape[1])]

                        # 添加编码后的特征
                        for i, name in enumerate(feature_names):
                            encoded_df[name] = encoded[:, i]

                        # 删除原始特征
                        encoded_df.drop(columns=[feature], inplace=True)
                    else:
                        # 如果没有编码器，使用Label编码
                        le = LabelEncoder()
                        encoded_df[feature] = le.fit_transform(encoded_df[feature].astype(str))

                except Exception as e:
                    logger.warning(f"Failed to encode feature {feature}: {e}")

        # 标准化数值特征
        for feature in self.numeric_features:
            if feature in encoded_df.columns:
                try:
                    if feature in self.feature_scalers:
                        # 使用训练时的标准化器
                        scaler = self.feature_scalers[feature]
                        encoded_df[feature] = scaler.transform(encoded_df[[feature]]).flatten()
                except Exception as e:
                    logger.warning(f"Failed to scale feature {feature}: {e}")

        return encoded_df

    async def get_feature_importance(self) -> dict[str, float]:
        """获取特征重要性（如果可用）"""
        importance = {}

        # 基于特征类型分配重要性
        for feature in self.feature_columns:
            if feature in self.numeric_features:
                importance[feature] = 0.7  # 数值特征重要性较高
            elif feature in self.categorical_features:
                importance[feature] = 0.5  # 分类特征重要性中等
            else:
                importance[feature] = 0.3  # 其他特征重要性较低

        # 归一化
        total_importance = sum(importance.values())
        if total_importance > 0:
            importance = {k: v / total_importance for k, v in importance.items()}

        return importance

    def get_feature_info(self) -> dict[str, Any]:
        """获取特征信息"""
        return {
            "total_features": len(self.feature_columns),
            "numeric_features": len(self.numeric_features),
            "categorical_features": len(self.categorical_features),
            "time_features": len(self.time_features),
            "feature_columns": self.feature_columns,
            "feature_stats": self.feature_stats
        }

    def save_config(self, config_path: str):
        """保存特征配置"""
        config = {
            "feature_columns": self.feature_columns,
            "numeric_features": self.numeric_features,
            "categorical_features": self.categorical_features,
            "time_features": self.time_features,
            "feature_stats": self.feature_stats,
            "encoders": self._save_encoders(),
            "scalers": self._save_scalers(),
            "timestamp": datetime.now().isoformat()
        }

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2, default=str)

        logger.info(f"Feature configuration saved to {config_path}")

    def _save_encoders(self) -> dict[str, dict]:
        """保存编码器配置"""
        encoder_configs = {}

        for feature, encoder in self.feature_encoders.items():
            config = {}
            if hasattr(encoder, 'categories_'):
                config['categories'] = [cat.tolist() for cat in encoder.categories_]
            encoder_configs[feature] = config

        return encoder_configs

    def _save_scalers(self) -> dict[str, dict]:
        """保存标准化器配置"""
        scaler_configs = {}

        for feature, scaler in self.feature_scalers.items():
            config = {}
            if hasattr(scaler, 'mean_'):
                config['mean'] = scaler.mean_.tolist()
            if hasattr(scaler, 'scale_'):
                config['scale'] = scaler.scale_.tolist()
            scaler_configs[feature] = config

        return scaler_configs


# 全局实例
_feature_builder: Optional[FeatureBuilder] = None


async def get_feature_builder() -> FeatureBuilder:
    """获取全局特征构建器实例"""
    global _feature_builder

    if _feature_builder is None:
        _feature_builder = FeatureBuilder()

        # 尝试加载配置文件
        config_path = Path("config/feature_builder_config.json")
        if config_path.exists():
            _feature_builder._load_config(str(config_path))

    return _feature_builder
