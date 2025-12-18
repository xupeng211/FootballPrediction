"""
Feature Loader - 统一特征加载器

桥接异步FeatureStore与同步训练脚本，提供统一的数据加载和质量检查接口。

主要功能:
- 从FeatureStore异步加载特征数据
- 自动执行数据质量检查
- 处理缺失值和异常值
- 特征工程和数据转换
- 批量数据加载优化

P0-4 核心组件 - 解决异步/同步不兼容问题
"""

from __future__ import annotations

import asyncio
import logging
import warnings
from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler

from src.features.feature_store_interface import (
    FeatureData,
    FeatureNotFoundError,
    FeatureStoreProtocol,
    FeatureValidationError,
)
from src.quality.data_quality_monitor import DataQualityMonitor
from src.quality.quality_protocol import DataQualityResult

from .config import PipelineConfig

logger = logging.getLogger(__name__)

# 禁用不必要的警告
warnings.filterwarnings("ignore", category=FutureWarning)


class FeatureLoader:
    """
    统一特征加载器.

    桥接异步FeatureStore与同步训练世界，提供:
    - 异步到同步的桥接
    - 数据质量监控
    - 特征工程和预处理
    - 批量数据加载
    """

    def __init__(
        self,
        store: FeatureStoreProtocol,
        config: Optional[PipelineConfig] = None,
    ):
        """初始化特征加载器.

        Args:
            store: 异步FeatureStore实例
            config: 流水线配置
        """
        self.store = store
        self.config = config or PipelineConfig()
        self.feature_config = self.config.features

        # 数据质量监控器
        self.quality_monitor = DataQualityMonitor(
            store=store,
            rules=[
                # 可以在这里添加特定的数据质量规则
            ],
        )

        # 特征工程组件
        self.scalers: dict[str, StandardScaler] = {}
        self.encoders: dict[str, LabelEncoder] = {}

        # 缓存
        self._feature_cache: dict[str, pd.DataFrame] = {}

    def load_training_data(
        self,
        match_ids: list[int],
        target_column: str = "result",
        validate_quality: bool = True,
    ) -> tuple[pd.DataFrame, pd.Series]:
        """
        同步特征加载接口 (桥接异步FeatureStore).

        Args:
            match_ids: 比赛ID列表
            target_column: 目标列名
            validate_quality: 是否执行数据质量检查

        Returns:
            tuple[pd.DataFrame, pd.Series]: 特征数据和目标变量

        Raises:
            FeatureValidationError: 数据质量检查失败
            FeatureNotFoundError: 特征不存在
        """
        logger.info(f"Loading training data for {len(match_ids)} matches")

        # 运行异步加载
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self._load_training_data_async(
                    match_ids, target_column, validate_quality
                )
            )
        finally:
            loop.close()

    async def _load_training_data_async(
        self,
        match_ids: list[int],
        target_column: str,
        validate_quality: bool,
    ) -> tuple[pd.DataFrame, pd.Series]:
        """异步训练数据加载实现."""
        # 1. 批量加载特征
        feature_data = await self._load_features_batch(match_ids)

        # 2. 转换为DataFrame
        df = self._convert_to_dataframe(feature_data, match_ids)

        # 3. 特征工程和预处理
        df = self._preprocess_features(df)

        # 4. 数据质量检查
        if validate_quality:
            quality_result = await self._validate_data_quality(df)
            if not quality_result.is_healthy():
                logger.warning(
                    f"Data quality issues detected: {quality_result.get_summary()}"
                )
                # 根据严重程度决定是否继续
                if quality_result.has_errors():
                    raise FeatureValidationError(
                        f"Critical data quality issues: {quality_result.get_summary()}"
                    )

        # 5. 分离特征和目标变量
        if target_column not in df.columns:
            raise FeatureNotFoundError(
                f"Target column '{target_column}' not found in data"
            )

        X = df.drop(columns=[target_column])
        y = df[target_column]

        logger.info(f"Loaded {len(X)} samples with {len(X.columns)} features")
        return X, y

    async def _load_features_batch(self, match_ids: list[int]) -> list[FeatureData]:
        """批量加载特征数据."""
        logger.debug(f"Loading features for {len(match_ids)} matches")

        feature_data_list = []
        batch_size = 1000  # 批量大小

        for i in range(0, len(match_ids), batch_size):
            batch_ids = match_ids[i : i + batch_size]
            logger.debug(
                f"Loading batch {i // batch_size + 1}: {len(batch_ids)} matches"
            )

            # 并行加载特征
            tasks = [self.store.load_features(match_id) for match_id in batch_ids]
            batch_features = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理加载结果
            for j, feature_result in enumerate(batch_features):
                if isinstance(feature_result, Exception):
                    logger.warning(
                        f"Failed to load features for match {batch_ids[j]}: {feature_result}"
                    )
                    continue
                if feature_result:  # 只添加非空结果
                    feature_data_list.append(feature_result)

        logger.info(f"Successfully loaded {len(feature_data_list)} feature records")
        return feature_data_list

    def _convert_to_dataframe(
        self, feature_data_list: list[FeatureData], match_ids: list[int]
    ) -> pd.DataFrame:
        """将特征数据转换为DataFrame."""
        if not feature_data_list:
            raise ValueError("No feature data loaded")

        # 展平特征数据
        records = []
        for feature_data in feature_data_list:
            record = {"match_id": feature_data.match_id}
            record.update(feature_data.features)
            records.append(record)

        df = pd.DataFrame(records)

        # 应用特征映射
        if self.feature_config.feature_mappings:
            df = df.rename(columns=self.feature_config.feature_mappings)

        # 确保所有必需特征都存在
        missing_features = set(self.feature_config.required_features) - set(df.columns)
        if missing_features:
            logger.warning(f"Missing features: {missing_features}")
            # 填充缺失特征为0
            for feature in missing_features:
                df[feature] = 0

        # 选择必需特征
        df = df[["match_id"] + self.feature_config.required_features]

        return df

    def _preprocess_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """特征工程和预处理."""
        logger.debug("Preprocessing features")

        df_processed = df.copy()

        # 1. 处理缺失值
        df_processed = self._handle_missing_values(df_processed)

        # 2. 特征标准化
        if self.feature_config.normalize_features:
            df_processed = self._normalize_features(df_processed)

        # 3. 分类变量编码
        if self.feature_config.encode_categorical:
            df_processed = self._encode_categorical(df_processed)

        logger.debug(f"Preprocessed {len(df_processed)} samples")
        return df_processed

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值."""
        numeric_columns = df.select_dtypes(include=[np.number]).columns

        if self.feature_config.handle_missing == "median":
            df[numeric_columns] = df[numeric_columns].fillna(
                df[numeric_columns].median()
            )
        elif self.feature_config.handle_missing == "mean":
            df[numeric_columns] = df[numeric_columns].fillna(df[numeric_columns].mean())
        elif self.feature_config.handle_missing == "drop":
            df = df.dropna(subset=numeric_columns)

        return df

    def _normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """特征标准化."""
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        numeric_columns = numeric_columns.drop("match_id", errors="ignore")

        for col in numeric_columns:
            if col not in self.scalers:
                self.scalers[col] = StandardScaler()
                df[col] = self.scalers[col].fit_transform(df[[col]])
            else:
                df[col] = self.scalers[col].transform(df[[col]])

        return df

    def _encode_categorical(self, df: pd.DataFrame) -> pd.DataFrame:
        """分类变量编码."""
        categorical_columns = df.select_dtypes(include=["object", "category"]).columns

        for col in categorical_columns:
            if col == "match_id":
                continue

            if col not in self.encoders:
                self.encoders[col] = LabelEncoder()
                df[col] = self.encoders[col].fit_transform(df[col].astype(str))
            else:
                # 处理未见过的类别
                unique_values = set(df[col].astype(str).unique())
                known_values = set(self.encoders[col].classes_)
                unknown_values = unique_values - known_values

                if unknown_values:
                    logger.warning(f"Unknown categories in {col}: {unknown_values}")
                    # 将未知类别映射到已知类别或特殊值
                    df[col] = (
                        df[col]
                        .astype(str)
                        .map(
                            lambda x: x if x in known_values else list(known_values)[0]
                        )
                    )

                df[col] = self.encoders[col].transform(df[col].astype(str))

        return df

    async def _validate_data_quality(self, df: pd.DataFrame) -> DataQualityResult:
        """数据质量检查."""
        logger.debug("Validating data quality")

        # 使用DataQualityMonitor检查
        quality_result = await self.quality_monitor.check_data_quality(df)

        # 额外的自定义检查
        custom_checks = {
            "missing_threshold": df.isnull().sum().sum() / len(df),
            "duplicates": df.duplicated().sum(),
            "numeric_range": self._check_numeric_ranges(df),
        }

        # 记录质量统计
        logger.info(f"Data quality summary: {custom_checks}")

        return quality_result

    def _check_numeric_ranges(self, df: pd.DataFrame) -> dict[str, Any]:
        """检查数值范围."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        range_info = {}

        for col in numeric_cols:
            if col == "match_id":
                continue

            col_data = df[col].dropna()
            if len(col_data) > 0:
                range_info[col] = {
                    "min": float(col_data.min()),
                    "max": float(col_data.max()),
                    "mean": float(col_data.mean()),
                    "std": float(col_data.std()),
                }

        return range_info

    def get_feature_stats(self, df: pd.DataFrame) -> dict[str, Any]:
        """获取特征统计信息."""
        stats = {
            "shape": df.shape,
            "dtypes": df.dtypes.to_dict(),
            "missing_values": df.isnull().sum().to_dict(),
            "numeric_summary": df.describe().to_dict(),
        }

        return stats

    def save_preprocessors(self, path: str) -> None:
        """保存预处理器（用于推理时复用）."""
        import joblib
        from pathlib import Path

        save_path = Path(path)
        save_path.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.scalers, save_path / "scalers.joblib")
        joblib.dump(self.encoders, save_path / "encoders.joblib")
        joblib.dump(self.feature_config, save_path / "feature_config.joblib")

        logger.info(f"Preprocessors saved to {save_path}")

    def load_preprocessors(self, path: str) -> None:
        """加载预处理器."""
        import joblib
        from pathlib import Path

        load_path = Path(path)

        self.scalers = joblib.load(load_path / "scalers.joblib")
        self.encoders = joblib.load(load_path / "encoders.joblib")
        self.feature_config = joblib.load(load_path / "feature_config.joblib")

        logger.info(f"Preprocessors loaded from {load_path}")


# 便捷函数
def create_feature_loader(
    store: FeatureStoreProtocol, config: Optional[PipelineConfig] = None
) -> FeatureLoader:
    """创建特征加载器的便捷函数."""
    return FeatureLoader(store, config)
