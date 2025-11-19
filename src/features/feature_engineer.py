"""
特征工程管道构建器
Feature Engineering Pipeline Builder

基于 Scikit-learn Pipeline 理念构建的特征工程模块，用于足球预测模型。
"""

import logging
from typing import Any, Dict, List, Tuple, Union

# 尝试导入科学计算库，如果失败则使用模拟
try:
    import numpy as np
    import pandas as pd
    from sklearn.base import BaseEstimator, TransformerMixin
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import (
        OneHotEncoder,
        StandardScaler,
        MinMaxScaler,
        RobustScaler,
    )

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

    # 创建模拟模块
    class MockTransformer:
        """Mock transformer for environments without sklearn."""

        def __init__(self, **kwargs):
            pass

        def fit(self, X, y=None):
            return self

        def transform(self, X):
            return X

        def fit_transform(self, X, y=None):
            return X

    class MockPipeline:
        """Mock Pipeline for environments without sklearn."""

        def __init__(self, steps, **kwargs):
            self.steps = steps
            self.named_steps = dict(steps)

        def fit(self, X, y=None):
            return self

        def transform(self, X):
            return X

        def fit_transform(self, X, y=None):
            return X

        def predict(self, X):
            return [0] * len(X) if hasattr(X, '__len__') else [0]

    class MockColumnTransformer:
        """Mock ColumnTransformer for environments without sklearn."""

        def __init__(self, transformers, **kwargs):
            self.transformers = transformers
            self.named_transformers_ = dict(transformers)

        def fit(self, X, y=None):
            return self

        def transform(self, X):
            return X

        def fit_transform(self, X, y=None):
            return X

    # 分配模拟类
    Pipeline = MockPipeline
    ColumnTransformer = MockColumnTransformer
    StandardScaler = MockTransformer
    MinMaxScaler = MockTransformer
    RobustScaler = MockTransformer
    SimpleImputer = MockTransformer
    OneHotEncoder = MockTransformer
    BaseEstimator = object
    TransformerMixin = object

    np = None
    pd = None

logger = logging.getLogger(__name__)


class FootballFeatureTransformer(BaseEstimator, TransformerMixin):
    """
    足球特征自定义转换器

    专门用于处理足球预测相关的特征工程：
    - 球队历史对战记录
    - 主客场优势计算
    - 近期状态评估
    - 伤病情况影响
    """

    def __init__(self,
                 include_head_to_head: bool = True,
                 include_home_advantage: bool = True,
                 include_recent_form: bool = True,
                 recent_form_window: int = 5):
        """
        初始化足球特征转换器

        Args:
            include_head_to_head: 是否包含历史对战特征
            include_home_advantage: 是否包含主客场优势
            include_recent_form: 是否包含近期状态
            recent_form_window: 近期状态计算窗口期
        """
        self.include_head_to_head = include_head_to_head
        self.include_home_advantage = include_home_advantage
        self.include_recent_form = include_recent_form
        self.recent_form_window = recent_form_window
        self.team_stats = {}
        self.head_to_head_cache = {}

    def fit(self, X: pd.DataFrame, y: pd.Series = None) -> 'FootballFeatureTransformer':
        """拟合转换器，计算球队统计信息"""
        if not HAS_SCIPY:
            logger.warning("Scikit-learn not available, using mock implementation")
            return self

        # 这里应该根据历史数据计算球队统计信息
        # 实际实现中会从数据库加载历史比赛数据
        self._compute_team_statistics(X)
        self._compute_head_to_head_stats(X)

        logger.info("FootballFeatureTransformer fitted successfully")
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """转换特征数据"""
        if not HAS_SCIPY:
            logger.warning("Scikit-learn not available, returning original data")
            return X

        X_transformed = X.copy()

        # 添加主客场优势特征
        if self.include_home_advantage:
            X_transformed = self._add_home_advantage_features(X_transformed)

        # 添加近期状态特征
        if self.include_recent_form:
            X_transformed = self._add_recent_form_features(X_transformed)

        # 添加历史对战特征
        if self.include_head_to_head:
            X_transformed = self._add_head_to_head_features(X_transformed)

        return X_transformed

    def _compute_team_statistics(self, X: pd.DataFrame) -> None:
        """计算球队基础统计信息"""
        if not hasattr(X, 'columns'):
            return

        # 简化实现，实际中应该从历史数据计算
        team_columns = [col for col in X.columns if 'team' in col.lower()]

        for col in team_columns:
            if col in X.columns:
                unique_teams = X[col].unique()
                for team in unique_teams:
                    if team not in self.team_stats:
                        self.team_stats[team] = {
                            'matches_played': 0,
                            'wins': 0,
                            'draws': 0,
                            'losses': 0,
                            'goals_scored': 0,
                            'goals_conceded': 0
                        }

    def _compute_head_to_head_stats(self, X: pd.DataFrame) -> None:
        """计算历史对战统计信息"""
        # 简化实现，实际中应该从历史数据计算
        self.head_to_head_cache = {}

    def _add_home_advantage_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """添加主客场优势特征"""
        # 简化实现，添加主客场标识
        if hasattr(X, 'assign'):
            X = X.assign(is_home_match=1)  # 假设都是主场
        return X

    def _add_recent_form_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """添加近期状态特征"""
        # 简化实现，添加近期得分趋势
        if hasattr(X, 'assign'):
            X = X.assign(recent_form_score=0.5)  # 默认中性状态
        return X

    def _add_head_to_head_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """添加历史对战特征"""
        # 简化实现，添加历史对战优势
        if hasattr(X, 'assign'):
            X = X.assign(head_to_head_advantage=0.0)  # 默认无优势
        return X


class FeaturePipelineBuilder:
    """
    特征管道构建器

    使用 Scikit-learn Pipeline 和 ColumnTransformer 构建完整的特征工程管道。
    支持数值特征、类别特征和自定义足球特征的组合处理。
    """

    def __init__(self):
        """初始化特征管道构建器"""
        self.numeric_features: List[str] = []
        self.categorical_features: List[str] = []
        self.custom_features: List[str] = []
        self.pipeline: Pipeline = None

        # 默认特征分类
        self._default_feature_classification()

    def _default_feature_classification(self) -> None:
        """默认特征分类"""
        # 常见的数值特征
        self.numeric_features = [
            'home_team_score', 'away_team_score',
            'home_team_goals', 'away_team_goals',
            'home_team_shots', 'away_team_shots',
            'home_team_possession', 'away_team_possession',
            'home_team_passes', 'away_team_passes',
            'home_team_fouls', 'away_team_fouls',
            'home_team_corners', 'away_team_corners',
            'home_team_yellow_cards', 'away_team_yellow_cards',
            'home_team_red_cards', 'away_team_red_cards',
            'odds_home_win', 'odds_draw', 'odds_away_win',
            'recent_form_score', 'head_to_head_advantage'
        ]

        # 常见的类别特征
        self.categorical_features = [
            'home_team', 'away_team',
            'league', 'season', 'venue',
            'weather_condition', 'referee',
            'match_day', 'match_month',
            'is_home_match', 'is_derby'
        ]

        # 自定义特征（需要特殊处理）
        self.custom_features = [
            'team_history', 'player_injuries',
            'transfer_activity', 'manager_changes'
        ]

    def add_numeric_feature(self, feature_name: str) -> 'FeaturePipelineBuilder':
        """添加数值特征"""
        if feature_name not in self.numeric_features:
            self.numeric_features.append(feature_name)
        return self

    def add_categorical_feature(self, feature_name: str) -> 'FeaturePipelineBuilder':
        """添加类别特征"""
        if feature_name not in self.categorical_features:
            self.categorical_features.append(feature_name)
        return self

    def add_custom_feature(self, feature_name: str) -> 'FeaturePipelineBuilder':
        """添加自定义特征"""
        if feature_name not in self.custom_features:
            self.custom_features.append(feature_name)
        return self

    def remove_feature(self, feature_name: str) -> 'FeaturePipelineBuilder':
        """移除特征"""
        self.numeric_features = [f for f in self.numeric_features if f != feature_name]
        self.categorical_features = [f for f in self.categorical_features if f != feature_name]
        self.custom_features = [f for f in self.custom_features if f != feature_name]
        return self

    def build_pipeline(self,
                      numeric_strategy: str = 'standard',
                      categorical_strategy: str = 'onehot',
                      include_football_features: bool = True,
                      handle_missing: bool = True) -> Pipeline:
        """
        构建特征工程管道

        Args:
            numeric_strategy: 数值特征处理策略 ('standard', 'minmax', 'robust')
            categorical_strategy: 类别特征处理策略 ('onehot', 'ordinal')
            include_football_features: 是否包含足球特定特征
            handle_missing: 是否处理缺失值

        Returns:
            构建好的 Pipeline 对象
        """
        if not HAS_SCIPY:
            logger.warning("Scikit-learn not available, creating mock pipeline")
            return MockPipeline([
                ('football_features', FootballFeatureTransformer()),
                ('mock_processor', MockTransformer())
            ])

        # 构建转换器列表
        transformers = []

        # 1. 数值特征处理
        if self.numeric_features:
            numeric_transformer = self._build_numeric_transformer(numeric_strategy, handle_missing)
            transformers.append(('numeric', numeric_transformer, self.numeric_features))

        # 2. 类别特征处理
        if self.categorical_features:
            categorical_transformer = self._build_categorical_transformer(categorical_strategy, handle_missing)
            transformers.append(('categorical', categorical_transformer, self.categorical_features))

        # 3. 预处理管道
        preprocessor = ColumnTransformer(
            transformers=transformers,
            remainder='drop'  # 忽略未指定的列
        )

        # 4. 完整管道
        pipeline_steps = []

        # 添加足球特征转换器
        if include_football_features:
            pipeline_steps.append(('football_features', FootballFeatureTransformer()))

        # 添加预处理器
        pipeline_steps.append(('preprocessor', preprocessor))

        # 创建最终管道
        self.pipeline = Pipeline(pipeline_steps)

        logger.info(f"Feature pipeline built with {len(transformers)} transformers")
        logger.info(f"Numeric features: {len(self.numeric_features)}")
        logger.info(f"Categorical features: {len(self.categorical_features)}")

        return self.pipeline

    def _build_numeric_transformer(self, strategy: str, handle_missing: bool) -> Pipeline:
        """构建数值特征转换器"""
        steps = []

        # 缺失值处理
        if handle_missing:
            steps.append(('imputer', SimpleImputer(strategy='median')))

        # 标准化
        if strategy == 'standard':
            steps.append(('scaler', StandardScaler()))
        elif strategy == 'minmax':
            steps.append(('scaler', MinMaxScaler()))
        elif strategy == 'robust':
            steps.append(('scaler', RobustScaler()))

        return Pipeline(steps)

    def _build_categorical_transformer(self, strategy: str, handle_missing: bool) -> Pipeline:
        """构建类别特征转换器"""
        steps = []

        # 缺失值处理
        if handle_missing:
            steps.append(('imputer', SimpleImputer(strategy='most_frequent')))

        # 编码
        if strategy == 'onehot':
            steps.append(('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False)))
        elif strategy == 'ordinal':
            steps.append(('encoder', OneHotEncoder(handle_unknown='ignore')))  # 暂时用OneHot替代

        return Pipeline(steps)

    def get_feature_names(self) -> List[str]:
        """获取处理后的特征名称"""
        if self.pipeline is None:
            return self.numeric_features + self.categorical_features + self.custom_features

        # 如果管道已拟合，可以获取转换后的特征名称
        if hasattr(self.pipeline, 'named_steps') and 'preprocessor' in self.pipeline.named_steps:
            try:
                preprocessor = self.pipeline.named_steps['preprocessor']
                if hasattr(preprocessor, 'get_feature_names_out'):
                    return preprocessor.get_feature_names_out().tolist()
            except Exception as e:
                logger.warning(f"Could not get feature names: {e}")

        return self.numeric_features + self.categorical_features + self.custom_features

    def validate_features(self, X: pd.DataFrame) -> Tuple[bool, List[str]]:
        """验证数据中的特征"""
        missing_features = []

        all_expected_features = self.numeric_features + self.categorical_features + self.custom_features
        available_features = list(X.columns) if hasattr(X, 'columns') else []

        for feature in all_expected_features:
            if feature not in available_features:
                missing_features.append(feature)

        is_valid = len(missing_features) == 0

        if not is_valid:
            logger.warning(f"Missing features: {missing_features}")

        return is_valid, missing_features

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """获取管道摘要信息"""
        return {
            'numeric_features_count': len(self.numeric_features),
            'categorical_features_count': len(self.categorical_features),
            'custom_features_count': len(self.custom_features),
            'total_features': len(self.numeric_features) + len(self.categorical_features) + len(self.custom_features),
            'pipeline_built': self.pipeline is not None,
            'numeric_features': self.numeric_features,
            'categorical_features': self.categorical_features,
            'custom_features': self.custom_features
        }


# 便捷函数
def create_default_football_pipeline() -> Pipeline:
    """创建默认的足球特征工程管道"""
    builder = FeaturePipelineBuilder()
    return builder.build_pipeline(
        numeric_strategy='standard',
        categorical_strategy='onehot',
        include_football_features=True,
        handle_missing=True
    )


def create_simple_pipeline(features: List[str]) -> Pipeline:
    """创建简单的特征管道"""
    builder = FeaturePipelineBuilder()

    # 自动分类特征
    for feature in features:
        if any(keyword in feature.lower() for keyword in ['team', 'league', 'venue', 'weather']):
            builder.add_categorical_feature(feature)
        else:
            builder.add_numeric_feature(feature)

    return builder.build_pipeline()