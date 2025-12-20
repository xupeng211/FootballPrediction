"""
服务层业务逻辑单元测试

测试 src/services/ 模块的核心服务功能：
- InferenceService: 推理服务的业务逻辑、批量预测、统计信息
- CollectionService: 数据收集服务、任务管理、并发执行

Mock策略：
- 完全隔离外部依赖（数据库、文件系统、外部API）
- Mock 底层 ML 组件（MatchPredictor, ModelLoader等）
- Mock 异步操作和并发控制
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 导入被测试的模块
import sys

sys.path.append("/home/user/projects/FootballPrediction/src")

from services.prediction_service import (
    InferenceService,
    PredictionRequest,
    PredictionResponse,
)
from services.collection_service import (
    FotMobCollectionService,
    FotMobCollectionTask,
    CollectionStats,
    CollectionStatus,
)


class TestPredictionRequest(unittest.TestCase):
    """测试 PredictionRequest 数据类"""

    def test_prediction_request_creation(self):
        """测试创建预测请求"""
        request = PredictionRequest(
            match_id=123,
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-01",
            features={"feature1": 1.0, "feature2": 2.0},
        )

        # 验证属性
        self.assertEqual(request.match_id, 123)
        self.assertEqual(request.home_team, "Team A")
        self.assertEqual(request.away_team, "Team B")
        self.assertEqual(request.match_date, "2024-01-01")
        self.assertEqual(request.features, {"feature1": 1.0, "feature2": 2.0})

    def test_to_dict(self):
        """测试转换为字典"""
        request = PredictionRequest(
            match_id=123,
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-01",
        )

        result = request.to_dict()

        # 验证转换结果
        expected = {
            "match_id": 123,
            "home_team": "Team A",
            "away_team": "Team B",
            "match_date": "2024-01-01",
        }
        self.assertEqual(result, expected)


class TestPredictionResponse(unittest.TestCase):
    """测试 PredictionResponse 数据类"""

    def test_prediction_response_creation(self):
        """测试创建预测响应"""
        response = PredictionResponse(
            match_id=123,
            prediction=1,  # Draw
            probabilities=[0.2, 0.5, 0.3],
            confidence=0.8,
            model_version="1.0.0",
        )

        # 验证属性
        self.assertEqual(response.match_id, 123)
        self.assertEqual(response.prediction, 1)
        self.assertEqual(response.probabilities, [0.2, 0.5, 0.3])
        self.assertEqual(response.confidence, 0.8)
        self.assertEqual(response.model_version, "1.0.0")

    def test_to_dict(self):
        """测试转换为字典"""
        response = PredictionResponse(
            match_id=123,
            prediction=1,
            probabilities=[0.2, 0.5, 0.3],
            confidence=0.8,
            model_version="1.0.0",
        )

        result = response.to_dict()

        # 验证转换结果
        expected = {
            "match_id": 123,
            "prediction": 1,
            "probabilities": [0.2, 0.5, 0.3],
            "confidence": 0.8,
            "model_version": "1.0.0",
        }
        self.assertEqual(result, expected)


class TestInferenceService(unittest.TestCase):
    """测试 InferenceService 推理服务"""

    def setUp(self):
        """测试前的设置"""
        # Mock 核心依赖
        self.mock_match_predictor = Mock()
        self.mock_model_loader = Mock()
        self.mock_cache_manager = Mock()
        self.mock_feature_extractor = Mock()

        # 创建服务实例
        with patch(
            "services.inference_service.MatchPredictor"
        ) as mock_predictor_class:
            mock_predictor_class.return_value = self.mock_match_predictor
            self.inference_service = InferenceService("/mock/model/path")

            # 替换内部依赖
            self.inference_service.predictor = self.mock_match_predictor
            self.inference_service.model_loader = self.mock_model_loader
            self.inference_service.cache_manager = self.mock_cache_manager

    def test_initialize_success(self):
        """测试服务初始化成功"""
        # Mock 模型加载器返回模型
        mock_model = Mock()
        self.mock_model_loader.load_model.return_value = mock_model

        # 执行初始化
        self.inference_service.initialize()

        # 验证模型被加载
        self.mock_model_loader.load_model.assert_called()

    def test_predict_match_success(self):
        """测试成功预测比赛"""
        # 准备测试数据
        request = PredictionRequest(
            match_id=123,
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-01",
            features={"feature1": 1.0, "feature2": 2.0},
        )

        # Mock 预测结果
        mock_prediction_result = {
            "prediction": 1,
            "probabilities": [0.2, 0.5, 0.3],
            "timestamp": time.time(),
        }
        self.mock_match_predictor.predict.return_value = mock_prediction_result

        # 执行预测
        response = self.inference_service.predict_match(request)

        # 验证结果
        self.assertIsInstance(response, PredictionResponse)
        self.assertEqual(response.match_id, 123)
        self.assertEqual(response.prediction, 1)
        self.assertEqual(response.probabilities, [0.2, 0.5, 0.3])

        # 验证调用
        self.mock_match_predictor.predict.assert_called_once()

    def test_predict_match_no_features(self):
        """测试没有特征的预测"""
        request = PredictionRequest(
            match_id=123,
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-01",
        )

        # Mock 特征提取
        mock_features = {"feature1": 1.0, "feature2": 2.0}
        with patch.object(self.inference_service, "_extract_features") as mock_extract:
            mock_extract.return_value = mock_features

            # Mock 预测结果
            mock_prediction_result = {
                "prediction": 2,
                "probabilities": [0.1, 0.3, 0.6],
                "timestamp": time.time(),
            }
            self.mock_match_predictor.predict.return_value = mock_prediction_result

            # 执行预测
            response = self.inference_service.predict_match(request)

            # 验证结果
            self.assertIsInstance(response, PredictionResponse)
            self.assertEqual(response.prediction, 2)

            # 验证特征提取被调用
            mock_extract.assert_called_once_with(request)

    def test_predict_match_failure(self):
        """测试预测失败"""
        request = PredictionRequest(
            match_id=123,
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-01",
        )

        # Mock 预测失败
        self.mock_match_predictor.predict.return_value = None

        # 执行预测
        response = self.inference_service.predict_match(request)

        # 验证返回错误响应
        self.assertIsNone(response)

    def test_predict_match_simple(self):
        """测试简化预测接口"""
        # Mock 预测结果
        mock_prediction_result = {
            "prediction": 0,
            "probabilities": [0.6, 0.3, 0.1],
            "timestamp": time.time(),
        }
        self.mock_match_predictor.predict.return_value = mock_prediction_result

        # 执行预测
        response = self.inference_service.predict_match_simple(
            match_id=123,
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-01",
        )

        # 验证结果
        self.assertIsInstance(response, PredictionResponse)
        self.assertEqual(response.match_id, 123)
        self.assertEqual(response.prediction, 0)

    def test_batch_predict_success(self):
        """测试批量预测成功"""
        requests = [
            PredictionRequest(
                match_id=1, home_team="A", away_team="B", match_date="2024-01-01"
            ),
            PredictionRequest(
                match_id=2, home_team="C", away_team="D", match_date="2024-01-02"
            ),
        ]

        # Mock 预测结果
        mock_results = [
            {
                "prediction": 1,
                "probabilities": [0.2, 0.5, 0.3],
                "timestamp": time.time(),
            },
            {
                "prediction": 2,
                "probabilities": [0.1, 0.3, 0.6],
                "timestamp": time.time(),
            },
        ]
        self.mock_match_predictor.predict.side_effect = mock_results

        # 执行批量预测
        responses = self.inference_service.batch_predict(requests)

        # 验证结果
        self.assertEqual(len(responses), 2)
        self.assertIsInstance(responses[0], PredictionResponse)
        self.assertEqual(responses[0].match_id, 1)
        self.assertEqual(responses[1].match_id, 2)

        # 验证调用次数
        self.assertEqual(self.mock_match_predictor.predict.call_count, 2)

    def test_batch_predict_partial_failure(self):
        """测试批量预测部分失败"""
        requests = [
            PredictionRequest(
                match_id=1, home_team="A", away_team="B", match_date="2024-01-01"
            ),
            PredictionRequest(
                match_id=2, home_team="C", away_team="D", match_date="2024-01-02"
            ),
        ]

        # Mock 预测结果（第一个成功，第二个失败）
        self.mock_match_predictor.predict.side_effect = [
            {
                "prediction": 1,
                "probabilities": [0.2, 0.5, 0.3],
                "timestamp": time.time(),
            },
            None,
        ]

        # 执行批量预测
        responses = self.inference_service.batch_predict(requests)

        # 验证结果
        self.assertEqual(len(responses), 2)
        self.assertIsInstance(responses[0], PredictionResponse)
        self.assertIsNone(responses[1])

    def test_get_service_stats(self):
        """测试获取服务统计信息"""
        # Mock 预测器统计信息
        mock_predictor_stats = {
            "total_predictions": 100,
            "cache_hits": 70,
            "cache_misses": 30,
            "cache_hit_rate": 0.7,
        }
        self.mock_match_predictor.get_prediction_stats.return_value = (
            mock_predictor_stats
        )

        # Mock 模型加载器统计信息
        self.mock_model_loader.list_loaded_models.return_value = ["model1", "model2"]

        # 获取服务统计
        stats = self.inference_service.get_service_stats()

        # 验证统计信息
        self.assertIsNotNone(stats)
        self.assertIn("predictor_stats", stats)
        self.assertIn("loaded_models", stats)
        self.assertEqual(len(stats["loaded_models"]), 2)

    def test_load_model(self):
        """测试加载模型"""
        mock_model = Mock()
        self.mock_model_loader.load_model.return_value = mock_model

        # 执行模型加载
        result = self.inference_service.load_model("new_model", "/mock/new_model.pkl")

        # 验证结果
        self.assertTrue(result)
        self.mock_model_loader.load_model.assert_called_once_with(
            "new_model", "/mock/new_model.pkl"
        )

    def test_unload_model(self):
        """测试卸载模型"""
        # 执行模型卸载
        self.inference_service.unload_model("test_model")

        # 验证调用
        self.mock_model_loader.unload_model.assert_called_once_with("test_model")

    def test_list_models(self):
        """测试列出已加载模型"""
        self.mock_model_loader.list_loaded_models.return_value = ["model1", "model2"]

        # 执行测试
        models = self.inference_service.list_models()

        # 验证结果
        self.assertEqual(models, ["model1", "model2"])
        self.mock_model_loader.list_loaded_models.assert_called_once()

    def test_shutdown(self):
        """测试服务关闭"""
        # 执行关闭
        self.inference_service.shutdown()

        # 验证缓存关闭
        self.mock_cache_manager.shutdown.assert_called_once()


class TestCollectionTask(unittest.TestCase):
    """测试 CollectionTask 数据类"""

    def test_collection_task_creation(self):
        """测试创建收集任务"""
        task = CollectionTask(
            task_id="task_123",
            source_type=DataSourceType.FOTMOB,
            source_config={"match_id": 123},
            priority=1,
            created_at=datetime.now(),
        )

        # 验证属性
        self.assertEqual(task.task_id, "task_123")
        self.assertEqual(task.source_type, DataSourceType.FOTMOB)
        self.assertEqual(task.source_config, {"match_id": 123})
        self.assertEqual(task.priority, 1)
        self.assertEqual(task.status, CollectionStatus.PENDING)

    def test_to_dict(self):
        """测试转换为字典"""
        task = CollectionTask(
            task_id="task_123",
            source_type=DataSourceType.ODPORTAL,
            source_config={"match_id": 456},
            priority=2,
        )

        result = task.to_dict()

        # 验证转换结果
        self.assertEqual(result["task_id"], "task_123")
        self.assertEqual(result["source_type"], DataSourceType.ODPORTAL)
        self.assertEqual(result["source_config"], {"match_id": 456})
        self.assertEqual(result["priority"], 2)
        self.assertEqual(result["status"], CollectionStatus.PENDING)


class TestCollectionStats(unittest.TestCase):
    """测试 CollectionStats 统计类"""

    def test_collection_stats_creation(self):
        """测试创建收集统计"""
        stats = CollectionStats()

        # 验证初始值
        self.assertEqual(stats.total_tasks, 0)
        self.assertEqual(stats.completed_tasks, 0)
        self.assertEqual(stats.failed_tasks, 0)
        self.assertEqual(stats.success_rate, 0.0)

    def test_update_stats(self):
        """测试更新统计信息"""
        stats = CollectionStats()

        # 创建一些任务
        tasks = [
            Mock(status=CollectionStatus.SUCCESS),
            Mock(status=CollectionStatus.SUCCESS),
            Mock(status=CollectionStatus.FAILED),
            Mock(status=CollectionStatus.PENDING),
        ]

        # 更新统计
        stats.update(tasks)

        # 验证统计结果
        self.assertEqual(stats.total_tasks, 4)
        self.assertEqual(stats.completed_tasks, 2)
        self.assertEqual(stats.failed_tasks, 1)
        self.assertEqual(stats.success_rate, 0.5)  # 2/4


class TestCollectionService(unittest.TestCase):
    """测试 CollectionService 数据收集服务"""

    def setUp(self):
        """测试前的设置"""
        with patch("services.collection_service.asyncio.create_task"):
            self.collection_service = CollectionService()

    def test_initialize_success(self):
        """测试服务初始化成功"""
        # 执行初始化
        self.collection_service.initialize()

        # 验证服务状态
        self.assertTrue(self.collection_service._initialized)

    def test_create_collection_task(self):
        """测试创建收集任务"""
        # 执行创建任务
        task = self.collection_service.create_collection_task(
            source_type=DataSourceType.FOTMOB,
            source_config={"match_id": 123},
            priority=1,
            task_id="custom_task_id",
        )

        # 验证任务创建
        self.assertIsNotNone(task)
        self.assertEqual(task.task_id, "custom_task_id")
        self.assertEqual(task.source_type, DataSourceType.FOTMOB)
        self.assertEqual(task.source_config, {"match_id": 123})
        self.assertEqual(task.priority, 1)
        self.assertEqual(task.status, CollectionStatus.PENDING)

        # 验证任务被添加到队列
        self.assertIn(task.task_id, self.collection_service._tasks)

    def test_execute_task_success(self):
        """测试执行任务成功"""
        # 创建任务
        task = self.collection_service.create_collection_task(
            source_type=DataSourceType.FOTMOB, source_config={"match_id": 123}
        )

        # Mock 数据收集器
        with patch.object(
            self.collection_service, "_execute_fotmob_collection"
        ) as mock_execute:
            mock_execute.return_value = {"status": "success", "data": "collected_data"}

            # 执行任务
            result = self.collection_service.execute_task(task.task_id)

            # 验证结果
            self.assertTrue(result)
            self.assertEqual(task.status, CollectionStatus.SUCCESS)
            mock_execute.assert_called_once_with(task.source_config)

    def test_execute_task_failure(self):
        """测试执行任务失败"""
        # 创建任务
        task = self.collection_service.create_collection_task(
            source_type=DataSourceType.FOTMOB, source_config={"match_id": 123}
        )

        # Mock 数据收集器抛出异常
        with patch.object(
            self.collection_service, "_execute_fotmob_collection"
        ) as mock_execute:
            mock_execute.side_effect = Exception("Collection failed")

            # 执行任务
            result = self.collection_service.execute_task(task.task_id)

            # 验证结果
            self.assertFalse(result)
            self.assertEqual(task.status, CollectionStatus.FAILED)

    def test_get_tasks(self):
        """测试获取任务列表"""
        # 创建不同状态的任务
        task1 = self.collection_service.create_collection_task(
            source_type=DataSourceType.FOTMOB, source_config={"match_id": 1}
        )
        task1.status = CollectionStatus.SUCCESS

        task2 = self.collection_service.create_collection_task(
            source_type=DataSourceType.ODPORTAL, source_config={"match_id": 2}
        )
        task2.status = CollectionStatus.PENDING

        task3 = self.collection_service.create_collection_task(
            source_type=DataSourceType.FOTMOB, source_config={"match_id": 3}
        )
        task3.status = CollectionStatus.RUNNING

        # 测试获取所有任务
        all_tasks = self.collection_service.get_tasks()
        self.assertEqual(len(all_tasks), 3)

        # 测试按状态筛选
        pending_tasks = self.collection_service.get_tasks(
            status=CollectionStatus.PENDING
        )
        self.assertEqual(len(pending_tasks), 1)
        self.assertEqual(pending_tasks[0].task_id, task2.task_id)

        # 测试按数据源类型筛选
        fotmob_tasks = self.collection_service.get_tasks(
            source_type=DataSourceType.FOTMOB
        )
        self.assertEqual(len(fotmob_tasks), 2)

    def test_get_stats(self):
        """测试获取收集统计信息"""
        # 创建不同状态的任务
        for i in range(3):
            task = self.collection_service.create_collection_task(
                source_type=DataSourceType.FOTMOB, source_config={"match_id": i}
            )
            if i < 2:
                task.status = CollectionStatus.SUCCESS
            else:
                task.status = CollectionStatus.FAILED

        # 获取统计信息
        stats = self.collection_service.get_stats()

        # 验证统计结果
        self.assertEqual(stats.total_tasks, 3)
        self.assertEqual(stats.completed_tasks, 2)
        self.assertEqual(stats.failed_tasks, 1)
        self.assertEqual(stats.success_rate, 2 / 3)

    def test_clear_completed_tasks(self):
        """测试清理已完成任务"""
        # 创建任务
        old_time = datetime.now() - timedelta(hours=25)  # 25小时前
        recent_time = datetime.now() - timedelta(hours=1)  # 1小时前

        # 创建旧任务
        old_task = self.collection_service.create_collection_task(
            source_type=DataSourceType.FOTMOB, source_config={"match_id": 1}
        )
        old_task.status = CollectionStatus.SUCCESS
        old_task.created_at = old_time

        # 创建新任务
        new_task = self.collection_service.create_collection_task(
            source_type=DataSourceType.ODPORTAL, source_config={"match_id": 2}
        )
        new_task.status = CollectionStatus.SUCCESS
        new_task.created_at = recent_time

        # 清理24小时前的已完成任务
        cleared_count = self.collection_service.clear_completed_tasks(
            older_than_hours=24
        )

        # 验证结果
        self.assertEqual(cleared_count, 1)
        self.assertNotIn(old_task.task_id, self.collection_service._tasks)
        self.assertIn(new_task.task_id, self.collection_service._tasks)

    def test_collect_match_data(self):
        """测试收集比赛数据"""
        with patch.object(
            self.collection_service, "create_collection_task"
        ) as mock_create_task:
            mock_create_task.return_value = Mock(task_id="mock_task_id")

            # 执行测试
            task_ids = self.collection_service.collect_match_data(
                match_id=123, sources=[DataSourceType.FOTMOB, DataSourceType.ODPORTAL]
            )

            # 验证结果
            self.assertEqual(len(task_ids), 2)
            self.assertEqual(mock_create_task.call_count, 2)

    def test_collect_fotmob_data(self):
        """测试收集FotMob数据"""
        # Mock 执行任务
        with patch.object(self.collection_service, "execute_task") as mock_execute:
            mock_execute.return_value = True

            # 执行测试
            result = self.collection_service.collect_fotmob_data(match_id=123)

            # 验证结果
            self.assertTrue(result)
            mock_execute.assert_called_once()

    def test_collect_odds_data(self):
        """测试收集赔率数据"""
        # Mock 执行任务
        with patch.object(self.collection_service, "execute_task") as mock_execute:
            mock_execute.return_value = True

            # 执行测试
            result = self.collection_service.collect_odds_data(match_id=456)

            # 验证结果
            self.assertTrue(result)
            mock_execute.assert_called_once()

    def test_shutdown(self):
        """测试服务关闭"""
        # 初始化服务
        self.collection_service.initialize()

        # 执行关闭
        self.collection_service.shutdown()

        # 验证服务状态
        self.assertFalse(self.collection_service._initialized)


class TestServiceIntegration(unittest.TestCase):
    """服务层集成测试"""

    def setUp(self):
        """测试前的设置"""
        # 创建模拟的服务实例
        self.mock_predictor = Mock()
        self.mock_model_loader = Mock()
        self.mock_cache_manager = Mock()

        # 创建推理服务
        with patch("services.inference_service.MatchPredictor"):
            self.inference_service = InferenceService("/mock/model")
            self.inference_service.predictor = self.mock_predictor
            self.inference_service.model_loader = self.mock_model_loader
            self.inference_service.cache_manager = self.mock_cache_manager

        # 创建收集服务
        with patch("services.collection_service.asyncio.create_task"):
            self.collection_service = CollectionService()

    def test_inference_service_end_to_end(self):
        """测试推理服务端到端流程"""
        # Mock 模型
        mock_model = Mock()
        self.mock_model_loader.load_model.return_value = mock_model
        self.mock_model_loader.list_loaded_models.return_value = ["test_model"]

        # Mock 预测结果
        mock_prediction_result = {
            "prediction": 1,
            "probabilities": [0.2, 0.5, 0.3],
            "timestamp": time.time(),
        }
        self.mock_predictor.predict.return_value = mock_prediction_result
        self.mock_predictor.get_prediction_stats.return_value = {
            "total_predictions": 10,
            "cache_hits": 7,
            "cache_misses": 3,
        }

        # 初始化服务
        self.inference_service.initialize()

        # 执行预测
        request = PredictionRequest(
            match_id=123,
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-01",
        )
        response = self.inference_service.predict_match(request)

        # 批量预测
        requests = [request]
        responses = self.inference_service.batch_predict(requests)

        # 获取统计信息
        stats = self.inference_service.get_service_stats()

        # 关闭服务
        self.inference_service.shutdown()

        # 验证结果
        self.assertIsInstance(response, PredictionResponse)
        self.assertEqual(len(responses), 1)
        self.assertIsNotNone(stats)
        self.mock_cache_manager.shutdown.assert_called_once()

    def test_collection_service_end_to_end(self):
        """测试收集服务端到端流程"""
        # 初始化服务
        self.collection_service.initialize()

        # 创建任务
        task_id = self.collection_service.create_collection_task(
            source_type=DataSourceType.FOTMOB, source_config={"match_id": 123}
        )

        # Mock 执行成功
        with patch.object(
            self.collection_service, "_execute_fotmob_collection"
        ) as mock_execute:
            mock_execute.return_value = {"status": "success"}

            # 执行任务
            success = self.collection_service.execute_task(task_id)

            # 获取任务和统计
            tasks = self.collection_service.get_tasks()
            stats = self.collection_service.get_stats()

            # 关闭服务
            self.collection_service.shutdown()

            # 验证结果
            self.assertTrue(success)
            self.assertEqual(len(tasks), 1)
            self.assertIsNotNone(stats)
            self.assertFalse(self.collection_service._initialized)


if __name__ == "__main__":
    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加测试用例
    suite.addTest(unittest.makeSuite(TestPredictionRequest))
    suite.addTest(unittest.makeSuite(TestPredictionResponse))
    suite.addTest(unittest.makeSuite(TestInferenceService))
    suite.addTest(unittest.makeSuite(TestCollectionTask))
    suite.addTest(unittest.makeSuite(TestCollectionStats))
    suite.addTest(unittest.makeSuite(TestCollectionService))
    suite.addTest(unittest.makeSuite(TestServiceIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出结果
    print(f"\n{'='*60}")
    print(f"服务层测试总结:")
    print(f"总测试数: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(
        f"成功率: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%"
    )
    print(f"{'='*60}")
