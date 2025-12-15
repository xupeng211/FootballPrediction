"""
Model Trainer - ML模型训练指挥官

Phase 2.3: Training Pipeline - 训练管道建设 (TDD Green Phase)

实现企业级的ML训练管道，严格遵循时间序列切分原则。
负责协调数据加载、特征工程、数据集切分和模型训练全流程。

核心设计原则：
1. 时间序列安全: 严格的时间切分，禁止随机打乱
2. 组件化设计: 组合DataLoader和BaseFeatureTransformer
3. 防数据泄露: 确保训练数据在测试数据之前
4. 企业级指标: Accuracy, Precision, ROI等业务指标
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score

# Imports for type hinting
from src.ml.data.loader import DataLoader
from src.ml.features.base import BaseFeatureTransformer

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    ML 模型训练指挥官。

    负责协调数据加载、特征工程、数据集切分和模型训练全流程。
    实现严格的时间序列切分，防止数据泄露。

    设计重点：
    1. Temporal Splitting: 严格基于时间的切分，禁止随机打乱
    2. Composition: 组合DataLoader和BaseFeatureTransformer
    3. Output Metrics: 返回Accuracy, Precision, ROI等业务指标
    4. 时间序列安全: 确保训练数据在测试数据之前

    使用示例:
        >>> trainer = ModelTrainer(
        ...     data_loader=DataLoader(),
        ...     feature_transformers=[RollingAverageTransformer(...)],
        ...     model_params={'n_estimators': 100}
        ... )
        >>> metrics = trainer.run(test_size=0.2)
        >>> print(f"Accuracy: {metrics['accuracy']:.3f}")
    """

    def __init__(self,
                 data_loader: DataLoader,
                 feature_transformers: List[BaseFeatureTransformer],
                 model_params: Dict[str, Any] = None):
        """
        初始化模型训练器。

        Args:
            data_loader: 数据加载器，负责从数据库加载数据
            feature_transformers: 特征工程转换器列表
            model_params: 模型参数配置字典
        """
        self.data_loader = data_loader
        self.feature_transformers = feature_transformers
        self.model_params = model_params or {'n_estimators': 100, 'max_depth': 3}
        self.model = XGBClassifier(**self.model_params)

        # 训练状态
        self.is_trained_ = False
        self.feature_names_ = []
        self.training_metrics_ = {}

        logger.info(f"初始化模型训练器: {len(feature_transformers)}个特征转换器")
        logger.debug(f"模型参数: {self.model_params}")

    async def run(self, test_size: float = 0.2) -> Dict[str, float]:
        """
        执行完整的训练管道。

        训练流程：
        1. Load Data - 从数据源加载原始数据
        2. Generate Features - 应用特征工程转换器
        3. Split Data - 严格基于时间切分（禁止随机打乱）
        4. Train Model - 在训练集上训练模型
        5. Evaluate - 在测试集上评估性能

        Args:
            test_size: 测试集比例，默认为0.2

        Returns:
            包含评估指标的字典:
            - accuracy: 准确率
            - precision: 精确率
            - recall: 召回率
            - roi: 投资回报率
            - train_size: 训练集大小
            - test_size: 测试集大小
        """
        logger.info(f"开始执行训练管道，测试集比例: {test_size}")

        # 1. Load Data
        df = await self.data_loader.load_data()
        if df.empty:
            raise ValueError("数据加载为空")

        logger.info(f"数据加载完成，共 {len(df)} 条记录")

        # 2. Generate Features
        for i, transformer in enumerate(self.feature_transformers):
            logger.debug(f"应用特征转换器 {i+1}/{len(self.feature_transformers)}")
            df = transformer.fit_transform(df)

        # Drop rows with NaN (due to rolling windows)
        initial_count = len(df)
        df = df.dropna()
        logger.info(f"特征工程完成，删除NaN后保留 {len(df)} 条记录 (删除 {initial_count - len(df)} 条)")

        # 3. Split Data (Time-based!)
        X_train, X_test, y_train, y_test = self._split_data(df, test_size)

        # 4. Train Model
        logger.info(f"开始训练模型 (Train size: {len(X_train)}, Test size: {len(X_test)})")
        self.model.fit(X_train, y_train)
        self.is_trained_ = True
        self.feature_names_ = list(X_train.columns)

        # 5. Evaluate
        y_pred = self.model.predict(X_test)
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "train_samples": len(X_train),
            "test_samples": len(X_test)
        }

        self.training_metrics_ = metrics
        logger.info(f"训练完成. Metrics: {metrics}")

        return metrics

    def _split_data(self, df: pd.DataFrame, test_size: float) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        严格的时间序列切分。

        核心原则：
        1. 时间单调性: 测试集时间必须严格在训练集之后
        2. 禁止随机打乱: 严禁使用shuffle=True
        3. 时间顺序: 保持数据的时间序列特性
        4. 防泄露边界: 确保训练和测试数据无时间重叠

        Args:
            df: 包含时间列的DataFrame
            test_size: 测试集比例

        Returns:
            (X_train, X_test, y_train, y_test): 训练和测试数据
        """
        logger.debug(f"执行时间序列切分，测试集比例: {test_size}")

        # 确保按时间排序
        if 'match_date' in df.columns:
            df = df.sort_values('match_date').reset_index(drop=True)
            logger.debug(f"数据已按match_date排序，时间范围: {df['match_date'].min()} 到 {df['match_date'].max()}")
        else:
            logger.warning("数据中缺少match_date列，使用原始顺序")

        # 定义目标变量：主队获胜 (home_score > away_score)
        # 处理可能的列名差异
        home_score_col = 'home_score' if 'home_score' in df.columns else 'home_goals'
        away_score_col = 'away_score' if 'away_score' in df.columns else 'away_goals'

        if home_score_col not in df.columns or away_score_col not in df.columns:
            raise ValueError(f"数据中缺少得分列: {home_score_col}, {away_score_col}")

        # 创建目标变量：1=主队获胜，0=其他（平局或客队获胜）
        y = (df[home_score_col] > df[away_score_col]).astype(int)
        logger.info(f"目标变量分布 - 主队获胜: {y.sum()}/{len(y)} ({y.mean():.2%})")

        # 选择特征列（排除元数据）
        # 优先选择滚动特征，如果不存在则选择其他数值特征
        feature_cols = [c for c in df.columns if c.startswith('rolling_')]

        if not feature_cols:
            # 回退方案：选择数值列（排除明显的非特征列）
            exclude_cols = [
                'id', 'match_date', home_score_col, away_score_col, 'status',
                'home_team_name', 'away_team_name', 'home_team_id', 'away_team_id',
                'league_id', 'season', 'result'
            ]
            feature_cols = [c for c in df.columns if c not in exclude_cols and df[c].dtype in ['int64', 'float64']]

        if not feature_cols:
            raise ValueError("无法找到合适的特征列进行训练")

        X = df[feature_cols]
        logger.info(f"选择了 {len(feature_cols)} 个特征列: {feature_cols[:5]}...")

        # 基于时间的切分索引
        split_idx = int(len(df) * (1 - test_size))

        X_train = X.iloc[:split_idx]
        X_test = X.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_test = y.iloc[split_idx:]

        # 验证时间序列安全性
        if 'match_date' in df.columns:
            train_dates = df['match_date'].iloc[:split_idx]
            test_dates = df['match_date'].iloc[split_idx:]

            if not self._validate_time_splitting(train_dates, test_dates):
                raise RuntimeError("时间序列切分安全性验证失败")

        logger.info(f"时间序列切分完成 - 训练集: {len(X_train)}, 测试集: {len(X_test)}")

        return X_train, X_test, y_train, y_test

    def _validate_time_splitting(self,
                                train_dates: pd.DatetimeIndex,
                                test_dates: pd.DatetimeIndex) -> bool:
        """
        验证时间序列切分的安全性。

        检查：
        1. 时间边界无重叠
        2. 测试集时间严格在训练集之后
        3. 无时间倒流现象

        Args:
            train_dates: 训练集日期索引
            test_dates: 测试集日期索引

        Returns:
            bool: 时间切分是否安全
        """
        # 验证时间边界
        if train_dates.max() >= test_dates.min():
            logger.error("时间序列切分不安全：训练集和测试集时间重叠")
            return False

        logger.info("✅ 时间序列切分安全验证通过")
        return True

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """
        获取特征重要性。

        Returns:
            特征重要性DataFrame，如果模型未训练则返回None
        """
        if not self.is_trained_:
            logger.warning("模型尚未训练，无法获取特征重要性")
            return None

        # 获取XGBoost特征重要性
        importance = self.model.feature_importances_
        feature_names = self.feature_names_

        # 创建重要性DataFrame
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)

        logger.info(f"特征重要性获取完成，共 {len(importance_df)} 个特征")
        return importance_df

    def save_model(self, filepath: str) -> None:
        """
        保存训练好的模型。

        Args:
            filepath: 模型文件路径
        """
        if not self.is_trained_:
            raise RuntimeError("模型尚未训练，无法保存")

        raise NotImplementedError("TDD Red Phase: Method not implemented")

    def __repr__(self) -> str:
        """字符串表示。"""
        return (
            f"ModelTrainer("
            f"data_loader={type(self.data_loader).__name__}, "
            f"transformers={len(self.feature_transformers)}, "
            f"trained={self.is_trained_})"
        )