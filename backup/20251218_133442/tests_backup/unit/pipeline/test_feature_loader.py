"""
FeatureLoader 单元测试

测试特征加载器的核心功能，包括：
- 异步FeatureStore桥接
- 数据质量检查
- 特征工程和预处理
- 错误处理
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import numpy as np
import pandas as pd

from src.features.feature_store_interface import (
    FeatureData,
    FeatureNotFoundError,
    FeatureStoreProtocol,
    FeatureValidationError,
)
from src.quality.data_quality_monitor import DataQualityMonitor
from src.quality.quality_protocol import DataQualityResult, RuleSeverity

from src.pipeline.config import PipelineConfig, FeatureConfig
from src.pipeline.feature_loader import FeatureLoader


class TestFeatureLoader:
    """FeatureLoader单元测试."""

    @pytest.fixture
    def mock_store(self):
        """模拟FeatureStore."""
        store = AsyncMock(spec=FeatureStoreProtocol)
        return store

    @pytest.fixture
    def config(self):
        """测试配置."""
        return PipelineConfig(
            debug_mode=True,
            features=FeatureConfig(
                required_features=["feature1", "feature2", "feature3"],
                handle_missing="median",
                normalize_features=True,
            ),
        )

    @pytest.fixture
    def feature_loader(self, mock_store, config):
        """FeatureLoader实例."""
        return FeatureLoader(mock_store, config)

    @pytest.fixture
    def sample_feature_data(self):
        """样本特征数据."""
        return [
            FeatureData(
                match_id=1,
                features={
                    "feature1": 1.0,
                    "feature2": 2.0,
                    "feature3": "A",
                    "home_score": 2,
                    "away_score": 1,
                    "result": "home_win",
                },
                version="1.0",
                created_at=datetime.now(),
            ),
            FeatureData(
                match_id=2,
                features={
                    "feature1": 1.5,
                    "feature2": 2.5,
                    "feature3": "B",
                    "home_score": 1,
                    "away_score": 1,
                    "result": "draw",
                },
                version="1.0",
                created_at=datetime.now(),
            ),
        ]

    @pytest.fixture
    def sample_dataframe(self):
        """样本DataFrame."""
        return pd.DataFrame(
            {
                "match_id": [1, 2],
                "feature1": [1.0, 1.5],
                "feature2": [2.0, 2.5],
                "feature3": ["A", "B"],
                "result": ["home_win", "draw"],
            }
        )

    def test_init(self, mock_store, config):
        """测试初始化."""
        loader = FeatureLoader(mock_store, config)

        assert loader.store == mock_store
        assert loader.config == config
        assert loader.feature_config == config.features
        assert isinstance(loader.quality_monitor, DataQualityMonitor)

    @patch("src.pipeline.feature_loader.asyncio.new_event_loop")
    @patch("src.pipeline.feature_loader.asyncio.set_event_loop")
    def test_load_training_data_success(
        self,
        mock_set_loop,
        mock_new_loop,
        feature_loader,
        sample_feature_data,
        sample_dataframe,
    ):
        """测试成功加载训练数据."""
        # 设置异步mock
        mock_loop = MagicMock()
        mock_new_loop.return_value = mock_loop

        # 模拟异步方法返回
        mock_loop.run_until_complete.return_value = (
            sample_dataframe.drop(columns=["result"]),
            sample_dataframe["result"],
        )

        # 执行测试
        X, y = feature_loader.load_training_data([1, 2])

        # 验证结果
        assert isinstance(X, pd.DataFrame)
        assert isinstance(y, pd.Series)
        assert len(X) == 2
        assert "result" not in X.columns
        assert len(y) == 2

    def test_load_training_data_async_success(
        self, feature_loader, sample_feature_data
    ):
        """测试异步加载训练数据成功."""
        # 设置mock返回
        feature_loader.store.load_features.return_value = asyncio.Future()
        feature_loader.store.load_features.return_value.set_result(
            sample_feature_data[0]
        )

        # 模拟其他异步调用
        with patch.object(feature_loader, "_load_features_batch") as mock_batch:
            mock_batch.return_value = asyncio.Future()
            mock_batch.return_value.set_result(sample_feature_data)

            with patch.object(feature_loader, "_validate_data_quality") as mock_quality:
                mock_quality.return_value = asyncio.Future()
                mock_quality.return_value.set_result(
                    DataQualityResult(
                        rule_name="test",
                        severity=RuleSeverity.INFO,
                        passed=True,
                        message="Test passed",
                    )
                )

                # 执行测试
                result = asyncio.run(
                    feature_loader._load_training_data_async([1, 2], "result", True)
                )

                X, y = result
                assert isinstance(X, pd.DataFrame)
                assert isinstance(y, pd.Series)

    def test_load_features_batch(self, feature_loader, sample_feature_data):
        """测试批量特征加载."""
        # 设置mock
        feature_loader.store.load_features.return_value = asyncio.Future()
        feature_loader.store.load_features.return_value.set_result(
            sample_feature_data[0]
        )

        # 执行测试
        result = asyncio.run(feature_loader._load_features_batch([1, 2]))

        assert len(result) == 2  # 两个match_id
        assert all(isinstance(data, FeatureData) for data in result)

    def test_convert_to_dataframe(self, feature_loader, sample_feature_data):
        """测试转换为DataFrame."""
        df = feature_loader._convert_to_dataframe(sample_feature_data, [1, 2])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "match_id" in df.columns
        assert "feature1" in df.columns
        assert all(
            feature in df.columns
            for feature in feature_loader.feature_config.required_features
        )

    def test_convert_to_dataframe_with_missing_features(self, feature_loader):
        """测试缺少特征时的DataFrame转换."""
        incomplete_data = [
            FeatureData(
                match_id=1,
                features={"feature1": 1.0},  # 缺少其他特征
                version="1.0",
                created_at=datetime.now(),
            )
        ]

        df = feature_loader._convert_to_dataframe(incomplete_data, [1])

        assert len(df) == 1
        assert "feature1" in df.columns
        # 缺失特征应该被填充为0
        assert "feature2" in df.columns
        assert "feature3" in df.columns

    def test_preprocess_features(self, feature_loader, sample_dataframe):
        """测试特征预处理."""
        processed = feature_loader._preprocess_features(sample_dataframe.copy())

        assert isinstance(processed, pd.DataFrame)
        assert len(processed) == len(sample_dataframe)
        # 应该包含标准化后的数值特征
        assert "feature1" in processed.columns
        assert "feature2" in processed.columns

    def test_handle_missing_values_median(self, feature_loader):
        """测试缺失值处理 - 中位数填充."""
        df_with_missing = pd.DataFrame(
            {
                "feature1": [1.0, np.nan, 3.0],
                "feature2": [2.0, 2.5, np.nan],
            }
        )

        processed = feature_loader._handle_missing_values(df_with_missing)

        assert not processed.isnull().any().any()
        assert processed["feature1"].iloc[1] == 2.0  # 中位数
        assert processed["feature2"].iloc[2] == 2.5  # 中位数

    def test_handle_missing_values_drop(self, feature_loader):
        """测试缺失值处理 - 删除."""
        feature_loader.feature_config.handle_missing = "drop"

        df_with_missing = pd.DataFrame(
            {
                "feature1": [1.0, np.nan, 3.0],
                "feature2": [2.0, 2.5, 2.0],
            }
        )

        processed = feature_loader._handle_missing_values(df_with_missing)

        assert len(processed) == 2  # 删除了一行

    def test_normalize_features(self, feature_loader, sample_dataframe):
        """测试特征标准化."""
        # 只测试数值特征
        numeric_df = sample_dataframe[["feature1", "feature2"]].copy()

        processed = feature_loader._normalize_features(numeric_df)

        assert isinstance(processed, pd.DataFrame)
        # 标准化后的均值应该接近0，标准差接近1
        assert abs(processed["feature1"].mean()) < 1e-10
        assert abs(processed["feature1"].std() - 1.0) < 1e-10

    def test_encode_categorical(self, feature_loader):
        """测试分类变量编码."""
        df_categorical = pd.DataFrame(
            {
                "category1": ["A", "B", "A", "C"],
                "category2": ["X", "X", "Y", "Y"],
            }
        )

        processed = feature_loader._encode_categorical(df_categorical)

        assert processed["category1"].dtype in [np.int32, np.int64]
        assert processed["category2"].dtype in [np.int32, np.int64]

    def test_validate_input_data_success(self, feature_loader, sample_dataframe):
        """测试输入数据验证成功."""
        y = pd.Series(["home_win", "draw"])

        # 不应该抛出异常
        feature_loader._validate_input_data(sample_dataframe, y)

    def test_validate_input_data_length_mismatch(
        self, feature_loader, sample_dataframe
    ):
        """测试输入数据长度不匹配."""
        y = pd.Series(["home_win"])  # 长度不匹配

        with pytest.raises(ValueError, match="Feature data length .* != target length"):
            feature_loader._validate_input_data(sample_dataframe, y)

    def test_validate_input_data_small_dataset(self, feature_loader):
        """测试小数据集警告."""
        small_df = pd.DataFrame({"feature1": [1.0]})
        y = pd.Series(["home_win"])

        # 应该发出警告但不抛出异常
        with pytest.warns(UserWarning):
            feature_loader._validate_input_data(small_df, y)

    def test_get_feature_stats(self, feature_loader, sample_dataframe):
        """测试特征统计信息."""
        stats = feature_loader.get_feature_stats(sample_dataframe)

        assert "shape" in stats
        assert "dtypes" in stats
        assert "missing_values" in stats
        assert stats["shape"] == (2, 5)

    @pytest.mark.asyncio
    async def test_validate_data_quality(self, feature_loader, sample_dataframe):
        """测试数据质量检查."""
        with patch.object(
            feature_loader.quality_monitor, "check_data_quality"
        ) as mock_check:
            mock_result = DataQualityResult(
                rule_name="test",
                severity=RuleSeverity.INFO,
                passed=True,
                message="Test passed",
            )
            mock_check.return_value = mock_result

            result = await feature_loader._validate_data_quality(sample_dataframe)

            assert result == mock_result

    @pytest.mark.asyncio
    async def test_load_training_data_target_column_missing(self, feature_loader):
        """测试目标列缺失."""
        # 设置mock返回没有目标列的DataFrame
        with patch.object(feature_loader, "_load_training_data_async") as mock_async:
            df_no_target = pd.DataFrame({"feature1": [1.0], "feature2": [2.0]})
            y_no_target = pd.Series([1])
            mock_async.return_value = (df_no_target, y_no_target)

            with pytest.raises(
                FeatureNotFoundError, match="Target column 'missing_target' not found"
            ):
                feature_loader.load_training_data([1], target_column="missing_target")

    @pytest.mark.asyncio
    async def test_load_training_data_quality_error(self, feature_loader):
        """测试数据质量错误."""
        # 设置mock返回质量检查失败
        with patch.object(feature_loader, "_load_training_data_async") as mock_async:
            # 创建质量检查失败的结果
            error_result = DataQualityResult(
                rule_name="test",
                severity=RuleSeverity.ERROR,
                passed=False,
                message="Critical quality issue",
            )

            # 模拟_data_quality_check抛出异常
            with patch.object(feature_loader, "_validate_data_quality") as mock_quality:
                mock_quality.return_value = error_result

                df = pd.DataFrame({"feature1": [1.0], "result": [1]})
                y = pd.Series([1])
                mock_async.return_value = (df, y)

                with pytest.raises(
                    FeatureValidationError, match="Critical data quality issues"
                ):
                    feature_loader.load_training_data([1], validate_quality=True)

    def test_save_and_load_preprocessors(self, feature_loader, tmp_path):
        """测试预处理器保存和加载."""
        # 添加一些预处理器
        feature_loader.scalers["test"] = MagicMock()
        feature_loader.encoders["test"] = MagicMock()

        # 保存
        save_path = tmp_path / "preprocessors"
        feature_loader.save_preprocessors(str(save_path))

        # 验证文件存在
        assert (save_path / "scalers.joblib").exists()
        assert (save_path / "encoders.joblib").exists()
        assert (save_path / "feature_config.joblib").exists()

        # 创建新的FeatureLoader并加载
        new_loader = FeatureLoader(MagicMock(), feature_loader.config)
        new_loader.load_preprocessors(str(save_path))

        assert "test" in new_loader.scalers
        assert "test" in new_loader.encoders


class TestFeatureLoaderIntegration:
    """FeatureLoader集成测试."""

    @pytest.mark.asyncio
    async def test_end_to_end_loading(self, config):
        """端到端测试数据加载."""
        # 创建真实的模拟数据
        sample_data = [
            FeatureData(
                match_id=i,
                features={
                    "feature1": float(i),
                    "feature2": float(i * 2),
                    "feature3": f"category_{i % 3}",
                    "result": "home_win" if i % 2 == 0 else "away_win",
                },
                version="1.0",
                created_at=datetime.now(),
            )
            for i in range(1, 101)  # 100个样本
        ]

        # 创建模拟Store
        mock_store = AsyncMock(spec=FeatureStoreProtocol)
        mock_store.load_features.return_value = sample_data[
            0
        ]  # 模拟返回单个FeatureData

        # 创建FeatureLoader
        feature_loader = FeatureLoader(mock_store, config)

        # 模拟批量加载
        with patch.object(feature_loader, "_load_features_batch") as mock_batch:
            mock_batch.return_value = sample_data

            with patch.object(feature_loader, "_validate_data_quality") as mock_quality:
                mock_quality.return_value = DataQualityResult(
                    rule_name="test",
                    severity=RuleSeverity.INFO,
                    passed=True,
                    message="Test passed",
                )

                # 执行加载
                X, y = feature_loader.load_training_data(list(range(1, 101)))

                # 验证结果
                assert len(X) == 100
                assert len(y) == 100
                assert all(
                    feature in X.columns
                    for feature in config.features.required_features
                )
                assert X.dtypes.apply(lambda x: x.kind in "biufc").all()  # 数值类型
