"""
增强的模型API测试
专注于提升models.py的覆盖率（12% → 25%+）
使用正确的Mock配置和具体的断言
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from datetime import datetime, timedelta
import json

from tests.unit.api.conftest import (
    mock_async_session,
    TestDataFactory,
    create_mock_query_result,
    assert_valid_response,
    assert_pagination_info
)


class TestModelManagement:
    """模型管理测试"""

    @pytest.mark.asyncio
    async def test_list_models_success(self, mock_async_session):
        """测试成功列出模型"""
        models_data = [
            {
                "id": "model_001",
                "name": "FootballPredictorV1",
                "version": "v1.0",
                "type": "classification",
                "status": "active",
                "created_at": datetime.now() - timedelta(days=30),
                "updated_at": datetime.now(),
                "accuracy": 0.75,
                "description": "基础预测模型"
            },
            {
                "id": "model_002",
                "name": "FootballPredictorV2",
                "version": "v2.0",
                "type": "regression",
                "status": "staging",
                "created_at": datetime.now() - timedelta(days=10),
                "updated_at": datetime.now(),
                "accuracy": 0.82,
                "description": "改进版预测模型"
            }
        ]

        mock_result = create_mock_query_result(models_data, total_count=2)
        mock_async_session.execute.return_value = mock_result

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import list_models

            result = await list_models(
                limit=10,
                offset=0,
                status="active",
                session=mock_async_session
            )

            # 验证响应结构
            result_dict = assert_valid_response(result, ["items", "pagination"])

            # 验证分页信息
            assert_pagination_info(result_dict["pagination"])
            assert result_dict["pagination"]["total"] == 2

            # 验证模型列表
            assert len(result_dict["items"]) == 2
            for model in result_dict["items"]:
                assert_valid_response(model, [
                    "id", "name", "version", "type", "status", "accuracy"
                ])
                assert model["status"] in ["active", "staging", "deprecated"]
                assert 0 <= model["accuracy"] <= 1

    @pytest.mark.asyncio
    async def test_get_model_details_success(self, mock_async_session):
        """测试成功获取模型详情"""
        model_details = {
            "id": "model_001",
            "name": "FootballPredictorV1",
            "version": "v1.0",
            "type": "classification",
            "status": "active",
            "description": "基础预测模型",
            "parameters": {
                "learning_rate": 0.001,
                "batch_size": 32,
                "epochs": 100
            },
            "performance_metrics": {
                "accuracy": 0.75,
                "precision": 0.73,
                "recall": 0.78,
                "f1_score": 0.75
            },
            "training_data": {
                "total_samples": 10000,
                "train_split": 0.8,
                "validation_split": 0.1,
                "test_split": 0.1
            },
            "created_at": datetime.now() - timedelta(days=30),
            "updated_at": datetime.now()
        }

        mock_result = create_mock_query_result([model_details])
        mock_async_session.execute.return_value = mock_result

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import get_model_details

            result = await get_model_details(
                model_id="model_001",
                session=mock_async_session
            )

            # 验证模型详情
            result_dict = assert_valid_response(result, [
                "id", "name", "version", "type", "status",
                "parameters", "performance_metrics", "training_data"
            ])

            # 验证性能指标
            metrics = result_dict["performance_metrics"]
            assert 0 <= metrics["accuracy"] <= 1
            assert 0 <= metrics["precision"] <= 1
            assert 0 <= metrics["recall"] <= 1
            assert 0 <= metrics["f1_score"] <= 1

            # 验证训练参数
            params = result_dict["parameters"]
            assert isinstance(params["learning_rate"], float)
            assert isinstance(params["batch_size"], int)
            assert isinstance(params["epochs"], int)

    @pytest.mark.asyncio
    async def test_get_model_details_not_found(self, mock_async_session):
        """测试获取不存在的模型详情"""
        mock_result = create_mock_query_result([])
        mock_async_session.execute.return_value = mock_result

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import get_model_details

            result = await get_model_details(
                model_id="nonexistent_model",
                session=mock_async_session
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_create_model_success(self, mock_async_session):
        """测试成功创建模型"""
        model_request = {
            "name": "NewFootballPredictor",
            "version": "v3.0",
            "type": "classification",
            "description": "新一代预测模型",
            "parameters": {
                "learning_rate": 0.0005,
                "batch_size": 64,
                "epochs": 200
            },
            "training_config": {
                "early_stopping": True,
                "patience": 10,
                "min_delta": 0.001
            }
        }

        # Mock数据库返回创建的模型
        created_model = {
            "id": "model_003",
            **model_request,
            "status": "training",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        mock_result = create_mock_query_result([created_model])
        mock_async_session.execute.return_value = mock_result
        mock_async_session.add = AsyncMock()
        mock_async_session.commit = AsyncMock()

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import create_model

            result = await create_model(
                model_data=model_request,
                session=mock_async_session
            )

            # 验证创建的模型
            result_dict = assert_valid_response(result, ["id", "name", "version", "status"])
            assert result_dict["name"] == "NewFootballPredictor"
            assert result_dict["version"] == "v3.0"
            assert result_dict["status"] == "training"

            # 验证数据库操作
            mock_async_session.add.assert_called_once()
            mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_model_success(self, mock_async_session):
        """测试成功更新模型"""
        # 原始模型数据
        original_model = {
            "id": "model_001",
            "name": "FootballPredictorV1",
            "version": "v1.0",
            "status": "active",
            "accuracy": 0.75
        }

        # 更新数据
        update_data = {
            "status": "deprecated",
            "accuracy": 0.78,
            "description": "已弃用的基础模型"
        }

        # 模拟更新后的模型
        updated_model = {
            **original_model,
            **update_data,
            "updated_at": datetime.now()
        }

        mock_async_session.execute.side_effect = [
            create_mock_query_result([original_model]),
            create_mock_query_result([updated_model])
        ]
        mock_async_session.commit = AsyncMock()

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import update_model

            result = await update_model(
                model_id="model_001",
                update_data=update_data,
                session=mock_async_session
            )

            # 验证更新结果
            result_dict = assert_valid_response(result, ["id", "status", "accuracy"])
            assert result_dict["status"] == "deprecated"
            assert result_dict["accuracy"] == 0.78

            # 验证数据库操作
            mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_model_success(self, mock_async_session):
        """测试成功删除模型"""
        model_to_delete = {
            "id": "model_001",
            "name": "FootballPredictorV1",
            "status": "deprecated"
        }

        mock_result = create_mock_query_result([model_to_delete])
        mock_async_session.execute.return_value = mock_result
        mock_async_session.delete = AsyncMock()
        mock_async_session.commit = AsyncMock()

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import delete_model

            result = await delete_model(
                model_id="model_001",
                session=mock_async_session
            )

            # 验证删除结果
            assert result is True

            # 验证数据库操作
            mock_async_session.delete.assert_called_once()
            mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_model_not_found(self, mock_async_session):
        """测试删除不存在的模型"""
        mock_result = create_mock_query_result([])
        mock_async_session.execute.return_value = mock_result

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import delete_model

            result = await delete_model(
                model_id="nonexistent_model",
                session=mock_async_session
            )

            assert result is False


class TestModelDeployment:
    """模型部署测试"""

    @pytest.mark.asyncio
    async def test_deploy_model_success(self, mock_async_session):
        """测试成功部署模型"""
        model_to_deploy = {
            "id": "model_002",
            "name": "FootballPredictorV2",
            "version": "v2.0",
            "status": "staging"
        }

        # Mock部署后的模型
        deployed_model = {
            **model_to_deploy,
            "status": "active",
            "deployed_at": datetime.now(),
            "deployment_config": {
                "endpoint": "/api/v1/predict",
                "max_concurrent_requests": 100,
                "timeout_seconds": 30
            }
        }

        mock_async_session.execute.side_effect = [
            create_mock_query_result([model_to_deploy]),
            create_mock_query_result([deployed_model])
        ]
        mock_async_session.commit = AsyncMock()

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import deploy_model

            deployment_config = {
                "endpoint": "/api/v1/predict",
                "max_concurrent_requests": 100,
                "timeout_seconds": 30
            }

            result = await deploy_model(
                model_id="model_002",
                deployment_config=deployment_config,
                session=mock_async_session
            )

            # 验证部署结果
            result_dict = assert_valid_response(result, ["id", "status", "deployed_at", "deployment_config"])
            assert result_dict["status"] == "active"
            assert result_dict["deployment_config"]["endpoint"] == "/api/v1/predict"

            # 验证数据库操作
            mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_undeploy_model_success(self, mock_async_session):
        """测试成功取消部署模型"""
        deployed_model = {
            "id": "model_002",
            "name": "FootballPredictorV2",
            "status": "active",
            "deployed_at": datetime.now() - timedelta(days=1)
        }

        # Mock取消部署后的模型
        undeployed_model = {
            **deployed_model,
            "status": "staging",
            "deployed_at": None,
            "undeployed_at": datetime.now()
        }

        mock_async_session.execute.side_effect = [
            create_mock_query_result([deployed_model]),
            create_mock_query_result([undeployed_model])
        ]
        mock_async_session.commit = AsyncMock()

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import undeploy_model

            result = await undeploy_model(
                model_id="model_002",
                session=mock_async_session
            )

            # 验证取消部署结果
            result_dict = assert_valid_response(result, ["id", "status", "undeployed_at"])
            assert result_dict["status"] == "staging"
            assert result_dict["undeployed_at"] is not None

            # 验证数据库操作
            mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_deployment_status(self, mock_async_session):
        """测试获取部署状态"""
        deployment_info = {
            "model_id": "model_002",
            "status": "active",
            "deployed_at": datetime.now() - timedelta(days=1),
            "endpoint": "/api/v1/predict",
            "health_status": "healthy",
            "last_health_check": datetime.now() - timedelta(minutes=30),
            "metrics": {
                "requests_per_second": 10.5,
                "average_response_time": 150.5,
                "error_rate": 0.02
            }
        }

        mock_result = create_mock_query_result([deployment_info])
        mock_async_session.execute.return_value = mock_result

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import get_deployment_status

            result = await get_deployment_status(
                model_id="model_002",
                session=mock_async_session
            )

            # 验证部署状态
            result_dict = assert_valid_response(result, [
                "model_id", "status", "deployed_at", "health_status",
                "endpoint", "metrics"
            ])

            assert result_dict["health_status"] in ["healthy", "unhealthy", "degraded"]
            assert result_dict["metrics"]["requests_per_second"] > 0
            assert result_dict["metrics"]["average_response_time"] > 0
            assert 0 <= result_dict["metrics"]["error_rate"] <= 1


class TestModelVersioning:
    """模型版本管理测试"""

    @pytest.mark.asyncio
    async def test_create_model_version_success(self, mock_async_session):
        """测试成功创建模型版本"""
        version_request = {
            "model_id": "model_001",
            "version": "v1.1",
            "parent_version": "v1.0",
            "changes": [
                "改进了特征工程",
                "调整了学习率",
                "增加了早停机制"
            ],
            "performance_metrics": {
                "accuracy": 0.78,
                "precision": 0.76,
                "recall": 0.80
            }
        }

        # Mock创建的版本
        new_version = {
            "id": "model_001_v1_1",
            **version_request,
            "created_at": datetime.now(),
            "status": "staging"
        }

        mock_result = create_mock_query_result([new_version])
        mock_async_session.execute.return_value = mock_result
        mock_async_session.add = AsyncMock()
        mock_async_session.commit = AsyncMock()

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import create_model_version

            result = await create_model_version(
                version_data=version_request,
                session=mock_async_session
            )

            # 验证创建的版本
            result_dict = assert_valid_response(result, ["id", "model_id", "version", "status"])
            assert result_dict["model_id"] == "model_001"
            assert result_dict["version"] == "v1.1"
            assert result_dict["status"] == "staging"

            # 验证数据库操作
            mock_async_session.add.assert_called_once()
            mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_model_version_history(self, mock_async_session):
        """测试获取模型版本历史"""
        versions = [
            {
                "id": "model_001_v1_2",
                "model_id": "model_001",
                "version": "v1.2",
                "parent_version": "v1.1",
                "status": "active",
                "created_at": datetime.now() - timedelta(days=1),
                "performance_metrics": {"accuracy": 0.80}
            },
            {
                "id": "model_001_v1_1",
                "model_id": "model_001",
                "version": "v1.1",
                "parent_version": "v1.0",
                "status": "deprecated",
                "created_at": datetime.now() - timedelta(days=5),
                "performance_metrics": {"accuracy": 0.78}
            },
            {
                "id": "model_001_v1_0",
                "model_id": "model_001",
                "version": "v1.0",
                "parent_version": None,
                "status": "deprecated",
                "created_at": datetime.now() - timedelta(days=30),
                "performance_metrics": {"accuracy": 0.75}
            }
        ]

        mock_result = create_mock_query_result(versions, total_count=3)
        mock_async_session.execute.return_value = mock_result

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import get_model_version_history

            result = await get_model_version_history(
                model_id="model_001",
                limit=10,
                offset=0,
                session=mock_async_session
            )

            # 验证版本历史
            result_dict = assert_valid_response(result, ["items", "pagination"])

            # 验证分页
            assert_pagination_info(result_dict["pagination"])
            assert result_dict["pagination"]["total"] == 3

            # 验证版本按时间排序
            versions_list = result_dict["items"]
            assert len(versions_list) == 3
            for i in range(len(versions_list) - 1):
                assert versions_list[i]["created_at"] >= versions_list[i + 1]["created_at"]

    @pytest.mark.asyncio
    async def test_compare_model_versions(self, mock_async_session):
        """测试比较模型版本"""
        versions_to_compare = [
            {
                "id": "model_001_v1_0",
                "version": "v1.0",
                "performance_metrics": {
                    "accuracy": 0.75,
                    "precision": 0.73,
                    "recall": 0.78
                }
            },
            {
                "id": "model_001_v1_1",
                "version": "v1.1",
                "performance_metrics": {
                    "accuracy": 0.78,
                    "precision": 0.76,
                    "recall": 0.80
                }
            },
            {
                "id": "model_001_v1_2",
                "version": "v1.2",
                "performance_metrics": {
                    "accuracy": 0.80,
                    "precision": 0.79,
                    "recall": 0.81
                }
            }
        ]

        mock_result = create_mock_query_result(versions_to_compare)
        mock_async_session.execute.return_value = mock_result

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import compare_model_versions

            result = await compare_model_versions(
                model_id="model_001",
                versions=["v1.0", "v1.1", "v1.2"],
                session=mock_async_session
            )

            # 验证比较结果
            result_dict = assert_valid_response(result, ["model_id", "versions", "comparison"])

            assert result_dict["model_id"] == "model_001"
            assert len(result_dict["versions"]) == 3

            # 验证比较数据
            comparison = result_dict["comparison"]
            assert "performance_improvement" in comparison
            assert "best_version" in comparison
            assert "metrics_comparison" in comparison


class TestModelMonitoring:
    """模型监控测试"""

    @pytest.mark.asyncio
    async def test_get_model_metrics(self, mock_async_session):
        """测试获取模型指标"""
        metrics_data = {
            "model_id": "model_001",
            "version": "v1.0",
            "metrics": {
                "accuracy": 0.75,
                "precision": 0.73,
                "recall": 0.78,
                "f1_score": 0.75,
                "auc": 0.82
            },
            "timestamp": datetime.now(),
            "data_points": 1000
        }

        mock_result = create_mock_query_result([metrics_data])
        mock_async_session.execute.return_value = mock_result

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import get_model_metrics

            result = await get_model_metrics(
                model_id="model_001",
                version="v1.0",
                start_date=datetime.now() - timedelta(days=7),
                end_date=datetime.now(),
                session=mock_async_session
            )

            # 验证指标数据
            result_dict = assert_valid_response(result, ["model_id", "version", "metrics", "timestamp"])

            metrics = result_dict["metrics"]
            assert 0 <= metrics["accuracy"] <= 1
            assert 0 <= metrics["auc"] <= 1
            assert result_dict["data_points"] > 0

    @pytest.mark.asyncio
    async def test_get_model_performance_trend(self, mock_async_session):
        """测试获取模型性能趋势"""
        trend_data = [
            {
                "date": datetime.now() - timedelta(days=6),
                "accuracy": 0.74,
                "error_rate": 0.26
            },
            {
                "date": datetime.now() - timedelta(days=5),
                "accuracy": 0.75,
                "error_rate": 0.25
            },
            {
                "date": datetime.now() - timedelta(days=4),
                "accuracy": 0.76,
                "error_rate": 0.24
            },
            {
                "date": datetime.now() - timedelta(days=3),
                "accuracy": 0.75,
                "error_rate": 0.25
            },
            {
                "date": datetime.now() - timedelta(days=2),
                "accuracy": 0.77,
                "error_rate": 0.23
            },
            {
                "date": datetime.now() - timedelta(days=1),
                "accuracy": 0.78,
                "error_rate": 0.22
            },
            {
                "date": datetime.now(),
                "accuracy": 0.79,
                "error_rate": 0.21
            }
        ]

        mock_result = create_mock_query_result(trend_data)
        mock_async_session.execute.return_value = mock_result

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import get_model_performance_trend

            result = await get_model_performance_trend(
                model_id="model_001",
                version="v1.0",
                days=7,
                session=mock_async_session
            )

            # 验证趋势数据
            result_dict = assert_valid_response(result, ["model_id", "version", "trend", "summary"])

            # 验证趋势数据点
            trend = result_dict["trend"]
            assert len(trend) == 7
            for data_point in trend:
                assert "date" in data_point
                assert "accuracy" in data_point
                assert "error_rate" in data_point
                assert 0 <= data_point["accuracy"] <= 1
                assert 0 <= data_point["error_rate"] <= 1

            # 验证汇总信息
            summary = result_dict["summary"]
            assert "improvement_trend" in summary
            assert "average_accuracy" in summary
            assert "stability_score" in summary


class TestModelValidation:
    """模型验证测试"""

    @pytest.mark.asyncio
    async def test_validate_model_input(self, mock_async_session):
        """测试验证模型输入"""
        from src.api.models import validate_model_input

        # 有效输入
        valid_input = {
            "home_team_id": 101,
            "away_team_id": 102,
            "league_id": 1,
            "home_form": [1, 1, 0, 1, 0],
            "away_form": [0, 1, 0, 0, 1],
            "head_to_head_goals": [2, 1, 0, 1, 2]
        }

        result = validate_model_input(valid_input, "v1.0")
        assert result is True

        # 无效输入
        invalid_inputs = [
            {},  # 空输入
            {"home_team_id": -1},  # 负ID
            {"home_team_id": 101},  # 缺少必要字段
            {"home_team_id": 101, "away_team_id": 101},  # 相同球队
            {"home_team_id": 101, "away_team_id": 102, "league_id": -1}  # 负联赛ID
        ]

        for invalid_input in invalid_inputs:
            result = validate_model_input(invalid_input, "v1.0")
            assert result is False

    @pytest.mark.asyncio
    async def test_check_model_health(self, mock_async_session):
        """测试检查模型健康状态"""
        health_data = {
            "model_id": "model_001",
            "status": "healthy",
            "checks": {
                "model_file_exists": True,
                "model_loaded": True,
                "prediction_latency_ms": 45.2,
                "memory_usage_mb": 256,
                "error_rate_24h": 0.01
            },
            "last_check": datetime.now()
        }

        mock_result = create_mock_query_result([health_data])
        mock_async_session.execute.return_value = mock_result

        with patch('src.api.models.get_async_session', return_value=mock_async_session):
            from src.api.models import check_model_health

            result = await check_model_health(
                model_id="model_001",
                session=mock_async_session
            )

            # 验证健康状态
            result_dict = assert_valid_response(result, ["model_id", "status", "checks", "last_check"])

            assert result_dict["status"] in ["healthy", "unhealthy", "degraded"]

            # 验证检查项
            checks = result_dict["checks"]
            assert checks["model_file_exists"] is True
            assert checks["model_loaded"] is True
            assert checks["prediction_latency_ms"] > 0
            assert checks["memory_usage_mb"] > 0
            assert 0 <= checks["error_rate_24h"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])