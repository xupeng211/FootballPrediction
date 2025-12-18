"""
Train Flow 集成测试

测试Prefect训练工作流的端到端功能，包括：
- 完整训练流程
- 数据加载和特征工程
- 模型训练和保存
- 错误处理和重试
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

import pandas as pd

from src.pipeline.config import PipelineConfig
from src.pipeline.flows.train_flow import (
    load_training_data_task,
    quick_train_flow,
    save_model_task,
    train_flow,
    train_model_task,
)


class TestTrainFlowIntegration:
    """Train Flow集成测试."""

    @pytest.fixture
    def config(self):
        """测试配置."""
        return PipelineConfig(
            debug_mode=True,
            environment="test",
        )

    @pytest.fixture
    def sample_training_data(self):
        """样本训练数据."""
        X = pd.DataFrame(
            {
                "feature1": [1.0, 1.5, 2.0, 2.5, 3.0],
                "feature2": [2.0, 2.5, 3.0, 3.5, 4.0],
                "feature3": [0.1, 0.2, 0.3, 0.4, 0.5],
            }
        )
        y = pd.Series([0, 1, 0, 1, 0])
        return X, y

    @pytest.fixture
    def sample_feature_loader(self):
        """样本FeatureLoader."""
        mock_loader = MagicMock()
        mock_loader.load_training_data.return_value = (
            pd.DataFrame(
                {
                    "feature1": [1.0, 1.5, 2.0, 2.5, 3.0],
                    "feature2": [2.0, 2.5, 3.0, 3.5, 4.0],
                }
            ),
            pd.Series([0, 1, 0, 1, 0]),
        )
        return mock_loader

    @pytest.mark.asyncio
    async def test_load_training_data_task_success(self, config):
        """测试加载训练数据任务成功."""
        match_ids = [1, 2, 3]

        # 模拟FeatureStore和FeatureLoader
        with patch(
            "src.pipeline.flows.train_flow.FootballFeatureStore"
        ) as mock_store_class:
            with patch(
                "src.pipeline.flows.train_flow.FeatureLoader"
            ) as mock_loader_class:
                mock_store = MagicMock()
                mock_loader = MagicMock()
                mock_store_class.return_value = mock_store
                mock_loader_class.return_value = mock_loader

                # 设置返回数据
                X, y = pd.DataFrame({"feature1": [1, 2]}), pd.Series([0, 1])
                mock_loader.load_training_data.return_value = (X, y)

                # 执行任务
                result = await load_training_data_task(match_ids, config)

                X_result, y_result, loader_result = result

                assert isinstance(X_result, pd.DataFrame)
                assert isinstance(y_result, pd.Series)
                assert loader_result == mock_loader

    @pytest.mark.asyncio
    async def test_load_training_data_task_with_retry(self, config):
        """测试加载训练数据任务重试机制."""
        match_ids = [1, 2, 3]

        with patch(
            "src.pipeline.flows.train_flow.FootballFeatureStore"
        ) as mock_store_class:
            with patch(
                "src.pipeline.flows.train_flow.FeatureLoader"
            ) as mock_loader_class:
                mock_store = MagicMock()
                mock_loader = MagicMock()
                mock_store_class.return_value = mock_store
                mock_loader_class.return_value = mock_loader

                # 模拟前两次失败，第三次成功
                mock_loader.load_training_data.side_effect = [
                    Exception("First failure"),
                    Exception("Second failure"),
                    (pd.DataFrame({"feature1": [1, 2]}), pd.Series([0, 1])),
                ]

                # 执行任务 (应该重试)
                result = await load_training_data_task(match_ids, config)

                assert mock_loader.load_training_data.call_count == 3

                X_result, y_result, loader_result = result
                assert isinstance(X_result, pd.DataFrame)
                assert isinstance(y_result, pd.Series)

    @pytest.mark.asyncio
    async def test_train_model_task_success(self, config, sample_training_data):
        """测试模型训练任务成功."""
        X, y = sample_training_data

        # 模拟Trainer和ModelRegistry
        with patch("src.pipeline.flows.train_flow.Trainer") as mock_trainer_class:
            with patch(
                "src.pipeline.flows.train_flow.ModelRegistry"
            ) as mock_registry_class:
                mock_trainer = MagicMock()
                mock_registry = MagicMock()
                mock_trainer_class.return_value = mock_trainer
                mock_registry_class.return_value = mock_registry

                # 设置训练结果
                training_result = {
                    "model": MagicMock(),
                    "metrics": {"accuracy": 0.85},
                    "training_record": {"algorithm": "xgboost"},
                    "algorithm": "xgboost",
                }
                mock_trainer.train.return_value = training_result

                # 执行任务
                result = await train_model_task(X, y, config, "xgboost")

                assert result["algorithm"] == "xgboost"
                assert "model" in result
                assert "metrics" in result
                assert "training_record" in result

                # 验证Trainer被正确初始化
                mock_trainer_class.assert_called_once_with(config, mock_registry)

                # 验证train方法被调用
                mock_trainer.train.assert_called_once_with(X, y, algorithm="xgboost")

    @pytest.mark.asyncio
    async def test_train_model_task_with_different_algorithms(
        self, config, sample_training_data
    ):
        """测试不同算法的训练任务."""
        X, y = sample_training_data

        with patch("src.pipeline.flows.train_flow.Trainer") as mock_trainer_class:
            mock_trainer = MagicMock()
            mock_trainer_class.return_value = mock_trainer

            training_result = {
                "model": MagicMock(),
                "metrics": {"accuracy": 0.80},
                "algorithm": "logistic_regression",
            }
            mock_trainer.train.return_value = training_result

            # 测试不同算法
            algorithms = ["xgboost", "logistic_regression", "random_forest"]

            for algorithm in algorithms:
                mock_trainer.train.return_value = {
                    **training_result,
                    "algorithm": algorithm,
                }

                result = await train_model_task(X, y, config, algorithm)

                assert result["algorithm"] == algorithm
                mock_trainer.train.assert_called_with(X, y, algorithm=algorithm)

    @pytest.mark.asyncio
    async def test_save_model_task_success(self, config):
        """测试保存模型任务成功."""
        training_result = {
            "model": MagicMock(),
            "metrics": {"accuracy": 0.85},
            "training_record": {"algorithm": "xgboost"},
            "algorithm": "xgboost",
        }
        model_name = "test_model"

        with patch(
            "src.pipeline.flows.train_flow.ModelRegistry"
        ) as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry_class.return_value = mock_registry

            # 设置保存路径
            mock_path = "/path/to/model.joblib"
            mock_registry.save_model.return_value = mock_path

            # 执行任务
            result = await save_model_task(training_result, model_name, config)

            assert result == mock_path

            # 验证save_model被调用
            expected_metadata = {
                "algorithm": "xgboost",
                "metrics": {"accuracy": 0.85},
                "training_record": {"algorithm": "xgboost"},
            }
            mock_registry.save_model.assert_called_once_with(
                model=training_result["model"],
                name=model_name,
                metadata=expected_metadata,
            )

    @pytest.mark.asyncio
    async def test_train_flow_full_success(self, config):
        """测试完整训练流程成功."""
        season = "2023-2024"
        match_ids = [1, 2, 3, 4, 5]
        model_name = "integration_test_model"

        # 模拟各个组件
        with patch(
            "src.pipeline.flows.train_flow._get_season_matches"
        ) as mock_get_matches:
            with patch(
                "src.pipeline.flows.train_flow.load_training_data_task"
            ) as mock_load:
                with patch(
                    "src.pipeline.flows.train_flow.train_model_task"
                ) as mock_train:
                    with patch(
                        "src.pipeline.flows.train_flow.save_model_task"
                    ) as mock_save:

                        # 设置返回值
                        mock_get_matches.return_value = match_ids

                        X, y = pd.DataFrame({"feature1": [1, 2, 3]}), pd.Series(
                            [0, 1, 0]
                        )
                        mock_load.return_value = (X, y, MagicMock())

                        training_result = {
                            "model": MagicMock(),
                            "metrics": {"accuracy": 0.85},
                            "training_record": {"algorithm": "xgboost"},
                            "algorithm": "xgboost",
                        }
                        mock_train.return_value = training_result

                        mock_save.return_value = "/path/to/saved_model.joblib"

                        # 执行完整流程
                        result = await train_flow(
                            season=season,
                            match_ids=match_ids,
                            model_name=model_name,
                            algorithm="xgboost",
                            config=config,
                        )

                        # 验证结果
                        assert result["status"] == "success"
                        assert result["model_name"] == model_name
                        assert result["algorithm"] == "xgboost"
                        assert result["season"] == season
                        assert result["match_count"] == len(match_ids)
                        assert result["model_path"] == "/path/to/saved_model.joblib"

                        # 验证各个任务被调用
                        mock_load.assert_called_once()
                        mock_train.assert_called_once()
                        mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_train_flow_with_auto_match_ids(self, config):
        """测试自动获取比赛ID的训练流程."""
        season = "2023-2024"
        match_ids = [1, 2, 3]

        with patch(
            "src.pipeline.flows.train_flow._get_season_matches"
        ) as mock_get_matches:
            with patch(
                "src.pipeline.flows.train_flow.load_training_data_task"
            ) as mock_load:
                with patch(
                    "src.pipeline.flows.train_flow.train_model_task"
                ) as mock_train:
                    with patch(
                        "src.pipeline.flows.train_flow.save_model_task"
                    ) as mock_save:

                        mock_get_matches.return_value = match_ids
                        mock_load.return_value = (
                            pd.DataFrame(),
                            pd.Series(),
                            MagicMock(),
                        )
                        mock_train.return_value = {
                            "model": MagicMock(),
                            "metrics": {},
                            "algorithm": "xgboost",
                        }
                        mock_save.return_value = "/path/to/model.joblib"

                        # 不提供match_ids，应该自动获取
                        result = await train_flow(season=season, config=config)

                        assert result["status"] == "success"
                        assert result["match_count"] == len(match_ids)
                        mock_get_matches.assert_called_once_with(season, None)

    @pytest.mark.asyncio
    async def test_train_flow_no_matches_found(self, config):
        """测试没有找到比赛的情况."""
        season = "2023-2024"

        with patch(
            "src.pipeline.flows.train_flow._get_season_matches"
        ) as mock_get_matches:
            mock_get_matches.return_value = []  # 没有比赛

            result = await train_flow(season=season, config=config)

            assert result["status"] == "failed"
            assert "No matches found" in result["error"]

    @pytest.mark.asyncio
    async def test_train_flow_training_failure(self, config):
        """测试训练失败的处理."""
        season = "2023-2024"
        match_ids = [1, 2, 3]

        with patch(
            "src.pipeline.flows.train_flow._get_season_matches"
        ) as mock_get_matches:
            with patch(
                "src.pipeline.flows.train_flow.load_training_data_task"
            ) as mock_load:

                mock_get_matches.return_value = match_ids
                mock_load.side_effect = Exception("Data loading failed")

                result = await train_flow(
                    season=season, match_ids=match_ids, config=config
                )

                assert result["status"] == "failed"
                assert "Data loading failed" in result["error"]

    def test_quick_train_flow_sync(self, config):
        """测试快速训练流程同步版本."""
        match_ids = [1, 2, 3]

        with patch("src.pipeline.flows.train_flow.train_flow") as mock_train_flow:
            mock_train_flow.return_value = {
                "status": "success",
                "model_name": "quick_model",
                "model_path": "/path/to/model.joblib",
            }

            # 使用同步调用
            result = quick_train_flow(
                match_ids, algorithm="xgboost", model_name="quick_model"
            )

            assert result["status"] == "success"
            assert result["model_name"] == "quick_model"

            # 验证train_flow被调用
            mock_train_flow.assert_called_once()

    def test_get_season_matches_placeholder(self):
        """测试获取赛季比赛ID的占位符实现."""
        # 当前的实现只是返回空列表和警告
        result = _get_season_matches("2023-2024")

        assert result == []


class TestTrainFlowErrorHandling:
    """Train Flow错误处理测试."""

    @pytest.mark.asyncio
    async def test_load_training_data_task_permanent_failure(self, config):
        """测试加载训练数据任务的永久失败."""
        match_ids = [1, 2, 3]

        with patch("src.pipeline.flows.train_flow.FootballFeatureStore"):
            with patch(
                "src.pipeline.flows.train_flow.FeatureLoader"
            ) as mock_loader_class:
                mock_loader = MagicMock()
                mock_loader_class.return_value = mock_loader

                # 始终失败
                mock_loader.load_training_data.side_effect = Exception(
                    "Permanent failure"
                )

                # 由于Prefect的重试机制，这个测试可能需要调整
                # 在实际测试中，我们可能需要模拟重试耗尽的情况
                with pytest.raises(Exception):
                    await load_training_data_task(match_ids, config)

    @pytest.mark.asyncio
    async def test_train_model_task_unsupported_algorithm(self, config):
        """测试不支持的算法."""
        X, y = pd.DataFrame({"feature1": [1]}), pd.Series([0])

        with patch("src.pipeline.flows.train_flow.Trainer") as mock_trainer_class:
            mock_trainer = MagicMock()
            mock_trainer_class.return_value = mock_trainer

            # 模拟不支持算法的异常
            mock_trainer.train.side_effect = ValueError(
                "Unsupported algorithm: unknown_algo"
            )

            with pytest.raises(ValueError, match="Unsupported algorithm"):
                await train_model_task(X, y, config, "unknown_algo")

    @pytest.mark.asyncio
    async def test_save_model_task_registry_failure(self, config):
        """测试模型注册表保存失败."""
        training_result = {"model": MagicMock(), "algorithm": "xgboost"}

        with patch(
            "src.pipeline.flows.train_flow.ModelRegistry"
        ) as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry_class.return_value = mock_registry

            # 模拟保存失败
            mock_registry.save_model.side_effect = Exception("Save failed")

            with pytest.raises(Exception, match="Save failed"):
                await save_model_task(training_result, "test_model", config)

    @pytest.mark.asyncio
    async def test_train_flow_partial_failure(self, config):
        """测试部分失败的训练流程."""
        season = "2023-2024"
        match_ids = [1, 2, 3]

        with patch(
            "src.pipeline.flows.train_flow._get_season_matches"
        ) as mock_get_matches:
            with patch(
                "src.pipeline.flows.train_flow.load_training_data_task"
            ) as mock_load:
                with patch(
                    "src.pipeline.flows.train_flow.train_model_task"
                ) as mock_train:

                    mock_get_matches.return_value = match_ids

                    # 数据加载成功，但训练失败
                    X, y = pd.DataFrame({"feature1": [1, 2]}), pd.Series([0, 1])
                    mock_load.return_value = (X, y, MagicMock())

                    mock_train.side_effect = Exception("Training failed")

                    result = await train_flow(
                        season=season, match_ids=match_ids, config=config
                    )

                    assert result["status"] == "failed"
                    assert "Training failed" in result["error"]
                    assert result["season"] == season
                    assert result["model_name"] is not None  # 默认生成的模型名


class TestTrainFlowPerformance:
    """Train Flow性能测试."""

    @pytest.mark.asyncio
    async def test_train_flow_with_large_dataset(self, config):
        """测试大数据集训练流程性能."""
        # 创建较大的数据集
        import numpy as np

        n_samples = 10000
        n_features = 20

        X = pd.DataFrame(
            np.random.random((n_samples, n_features)),
            columns=[f"feature_{i}" for i in range(n_features)],
        )
        y = pd.Series(np.random.randint(0, 2, n_samples))

        season = "2023-2024"
        match_ids = list(range(1, n_samples + 1))

        with patch(
            "src.pipeline.flows.train_flow._get_season_matches"
        ) as mock_get_matches:
            with patch(
                "src.pipeline.flows.train_flow.load_training_data_task"
            ) as mock_load:
                with patch(
                    "src.pipeline.flows.train_flow.train_model_task"
                ) as mock_train:
                    with patch(
                        "src.pipeline.flows.train_flow.save_model_task"
                    ) as mock_save:

                        mock_get_matches.return_value = match_ids
                        mock_load.return_value = (X, y, MagicMock())

                        # 模拟较长时间的训练
                        import time

                        def slow_train(*args, **kwargs):
                            time.sleep(0.1)  # 模拟100ms训练时间
                            return {
                                "model": MagicMock(),
                                "metrics": {"accuracy": 0.85},
                                "training_record": {"training_time": 0.1},
                                "algorithm": "xgboost",
                            }

                        mock_train.side_effect = slow_train
                        mock_save.return_value = "/path/to/model.joblib"

                        start_time = time.time()

                        result = await train_flow(
                            season=season,
                            match_ids=match_ids,
                            config=config,
                        )

                        end_time = time.time()
                        execution_time = end_time - start_time

                        assert result["status"] == "success"
                        assert result["match_count"] == n_samples
                        assert result["feature_count"] == n_features

                        # 验证执行时间合理 (应该大于模拟的训练时间)
                        assert execution_time > 0.1
