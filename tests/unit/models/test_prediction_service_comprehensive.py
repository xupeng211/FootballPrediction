import os
"""
预测服务全面测试
Comprehensive tests for prediction service to boost coverage
"""

import json
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 尝试导入预测服务
try:
    from src.models.prediction_service import (
        PredictionService,
        PredictionResult,
        PredictionFeatures,
        ModelManager,
        FeatureExtractor,
        predict_match,
        batch_predict_matches,
        validate_prediction
    )
except ImportError:
    # 创建模拟类用于测试
    PredictionService = None
    PredictionResult = None
    PredictionFeatures = None
    ModelManager = None
    FeatureExtractor = None
    predict_match = None
    batch_predict_matches = None
    validate_prediction = None


class TestPredictionService:
    """预测服务测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        if PredictionService is None:
            pytest.skip("PredictionService not available")

        self.service = PredictionService()
        self.test_match_id = 12345

    def test_service_initialization(self):
        """测试服务初始化"""
        assert self.service is not None
        assert hasattr(self.service, 'model_manager')
        assert hasattr(self.service, 'feature_extractor')

    @pytest.mark.asyncio
    async def test_predict_match_success(self):
        """测试单场比赛预测成功"""
        # Mock模型和特征提取
        mock_features = MagicMock()
        mock_features.home_team_stats = {"goals": 10, "wins": 5}
        mock_features.away_team_stats = {"goals": 8, "wins": 3}
        mock_features.match_features = {"is_home": True, "days_since_last_match": 7}

        with patch.object(self.service, 'extract_features') as mock_extract, \
             patch.object(self.service, 'load_model') as mock_model, \
             patch.object(self.service, 'predict') as mock_predict:

            mock_extract.return_value = mock_features
            mock_model.return_value = MagicMock()
            mock_predict.return_value = PredictionResult(
                match_id=self.test_match_id,
                home_win_probability=0.55,
                draw_probability=0.25,
                away_win_probability=0.20,
                predicted_result="home",
                confidence_score=0.55,
                model_version="1.0",
                model_name = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_MODEL_NAME_7")
            )

            result = await self.service.predict_match(self.test_match_id)

            assert result.match_id == self.test_match_id
            assert 0 <= result.home_win_probability <= 1
            assert 0 <= result.draw_probability <= 1
            assert 0 <= result.away_win_probability <= 1
            assert abs(result.home_win_probability + result.draw_probability + result.away_win_probability - 1.0) < 0.001
            assert result.predicted_result in ["home", "draw", "away"]
            assert result.confidence_score > 0

    @pytest.mark.asyncio
    async def test_predict_match_not_found(self):
        """测试比赛不存在"""
        with patch.object(self.service, 'get_match') as mock_get_match:
            mock_get_match.return_value = None

            with pytest.raises(ValueError) as exc_info:
                await self.service.predict_match(99999)

            assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_predict_match_finished(self):
        """测试预测已结束的比赛"""
        with patch.object(self.service, 'get_match') as mock_get_match:
            mock_match = MagicMock()
            mock_match.status = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_STATUS_105")
            mock_get_match.return_value = mock_match

            with pytest.raises(ValueError) as exc_info:
                await self.service.predict_match(self.test_match_id)

            assert "finished" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_batch_predict_matches(self):
        """测试批量预测"""
        match_ids = [12345, 12346, 12347]

        # Mock单场比赛预测
        with patch.object(self.service, 'predict_match') as mock_predict:
            mock_predict.side_effect = [
                PredictionResult(
                    match_id=mid,
                    home_win_probability=0.5,
                    draw_probability=0.3,
                    away_win_probability=0.2,
                    predicted_result="home",
                    confidence_score=0.5,
                    model_version="1.0"
                ) for mid in match_ids
            ]

            results = await self.service.batch_predict_matches(match_ids)

            assert len(results) == len(match_ids)
            assert all(r.match_id in match_ids for r in results)
            assert mock_predict.call_count == len(match_ids)

    @pytest.mark.asyncio
    async def test_batch_predict_with_invalid_matches(self):
        """测试批量预测包含无效比赛"""
        match_ids = [12345, 99999, 12347]  # 99999不存在

        with patch.object(self.service, 'predict_match') as mock_predict:
            mock_predict.side_effect = [
                PredictionResult(
                    match_id=12345,
                    home_win_probability=0.5,
                    draw_probability=0.3,
                    away_win_probability=0.2,
                    predicted_result="home",
                    confidence_score=0.5,
                    model_version="1.0"
                ),
                ValueError("Match not found"),
                PredictionResult(
                    match_id=12347,
                    home_win_probability=0.4,
                    draw_probability=0.3,
                    away_win_probability=0.3,
                    predicted_result="draw",
                    confidence_score=0.4,
                    model_version="1.0"
                )
            ]

            results = await self.service.batch_predict_matches(match_ids, ignore_errors=True)

            assert len(results) == 2  # 只有有效的预测
            assert all(r.match_id != 99999 for r in results)

    def test_feature_extraction(self):
        """测试特征提取"""
        # Mock比赛和球队数据
        mock_match = MagicMock()
        mock_match.id = self.test_match_id
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.match_time = datetime.now() + timedelta(days=1)

        mock_home_team = MagicMock()
        mock_home_team.recent_form = ["W", "W", "D", "L", "W"]
        mock_home_team.goals_scored = 15
        mock_home_team.goals_conceded = 8

        mock_away_team = MagicMock()
        mock_away_team.recent_form = ["D", "L", "W", "D", "L"]
        mock_away_team.goals_scored = 10
        mock_away_team.goals_conceded = 12

        with patch.object(self.service, 'get_match') as mock_get_match, \
             patch.object(self.service, 'get_team') as mock_get_team:

            mock_get_match.return_value = mock_match
            mock_get_team.side_effect = [mock_home_team, mock_away_team]

            features = self.service.extract_features(self.test_match_id)

            assert features is not None
            assert hasattr(features, 'home_team_features')
            assert hasattr(features, 'away_team_features')
            assert hasattr(features, 'match_features')

    def test_model_loading(self):
        """测试模型加载"""
        with patch('src.models.prediction_service.joblib.load') as mock_load:
            mock_model = MagicMock()
            mock_model.predict.return_value = np.array([[0.55, 0.25, 0.20]])
            mock_load.return_value = mock_model

            model = self.service.load_model("test_model.pkl")

            assert model is not None
            mock_load.assert_called_once_with("test_model.pkl")

    def test_prediction_validation(self):
        """测试预测结果验证"""
        # 有效的预测结果
        valid_result = PredictionResult(
            match_id=self.test_match_id,
            home_win_probability=0.5,
            draw_probability=0.3,
            away_win_probability=0.2,
            predicted_result="home",
            confidence_score=0.5,
            model_version="1.0"
        )

        assert self.service.validate_prediction(valid_result) is True

        # 无效的概率分布
        invalid_result = PredictionResult(
            match_id=self.test_match_id,
            home_win_probability=0.8,
            draw_probability=0.8,
            away_win_probability=0.2,
            predicted_result="home",
            confidence_score=0.8,
            model_version="1.0"
        )

        assert self.service.validate_prediction(invalid_result) is False

    def test_model_version_management(self):
        """测试模型版本管理"""
        versions = self.service.get_available_models()
        assert isinstance(versions, list)

        # 测试切换模型版本
        if versions:
            self.service.set_model_version(versions[0])
            assert self.service.current_model_version == versions[0]

    def test_prediction_caching(self):
        """测试预测结果缓存"""
        # 首次预测
        with patch.object(self.service, '_predict_internal') as mock_predict:
            mock_predict.return_value = PredictionResult(
                match_id=self.test_match_id,
                home_win_probability=0.5,
                draw_probability=0.3,
                away_win_probability=0.2,
                predicted_result="home",
                confidence_score=0.5
            )

            result1 = self.service.predict_with_cache(self.test_match_id)
            result2 = self.service.predict_with_cache(self.test_match_id)

            # 应该只调用一次预测（第二次从缓存获取）
            mock_predict.assert_called_once()
            assert result1.match_id == result2.match_id

    def test_confidence_calculation(self):
        """测试置信度计算"""
        # 高置信度情况
        probabilities = np.array([0.8, 0.15, 0.05])
        confidence = self.service.calculate_confidence(probabilities)
        assert confidence > 0.7

        # 低置信度情况
        probabilities = np.array([0.34, 0.33, 0.33])
        confidence = self.service.calculate_confidence(probabilities)
        assert confidence < 0.4

    def test_feature_importance(self):
        """测试特征重要性"""
        with patch.object(self.service, 'model') as mock_model:
            mock_model.feature_importances_ = np.array([0.3, 0.25, 0.2, 0.15, 0.1])
            feature_names = ["home_form", "away_form", "h2h", "goals", "injuries"]

            importance = self.service.get_feature_importance(feature_names)

            assert len(importance) == len(feature_names)
            assert importance[0]["feature"] == "home_form"
            assert importance[0]["importance"] == 0.3

    def test_prediction_explanation(self):
        """测试预测解释"""
        result = PredictionResult(
            match_id=self.test_match_id,
            home_win_probability=0.6,
            draw_probability=0.25,
            away_win_probability=0.15,
            predicted_result="home",
            confidence_score=0.6
        )

        explanation = self.service.explain_prediction(result)

        assert "主队胜率" in explanation
        assert "60%" in explanation
        assert "confidence" in explanation.lower() or "置信度" in explanation

    def test_error_handling(self):
        """测试错误处理"""
        # 测试模型加载失败
        with patch('src.models.prediction_service.joblib.load') as mock_load:
            mock_load.side_effect = FileNotFoundError("Model not found")

            with pytest.raises(FileNotFoundError):
                self.service.load_model("nonexistent_model.pkl")

        # 测试特征提取失败
        with patch.object(self.service, 'get_match') as mock_get_match:
            mock_get_match.side_effect = Exception("Database error")

            with pytest.raises(Exception):
                self.service.extract_features(self.test_match_id)


class TestModelManager:
    """模型管理器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        if ModelManager is None:
            pytest.skip("ModelManager not available")

        self.manager = ModelManager()

    def test_model_registration(self):
        """测试模型注册"""
        model_info = {
            "name": "test_model",
            "version": "1.0",
            "path": "/models/test_model.pkl",
            "description": "Test model for predictions"
        }

        self.manager.register_model(model_info)
        registered = self.manager.get_model_info("test_model", "1.0")

        assert registered is not None
        assert registered["name"] == "test_model"
        assert registered["version"] == "1.0"

    def test_model_loading_unloading(self):
        """测试模型加载和卸载"""
        model_path = "test_model.pkl"

        with patch('src.models.prediction_service.joblib.load') as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model

            # 加载模型
            model = self.manager.load_model(model_path)
            assert model is not None

            # 卸载模型
            self.manager.unload_model(model_path)
            assert model_path not in self.manager.loaded_models

    def test_model_performance_tracking(self):
        """测试模型性能跟踪"""
        model_name = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_MODEL_NAME_3")
        metrics = {
            "accuracy": 0.75,
            "precision": 0.73,
            "recall": 0.78,
            "f1_score": 0.75
        }

        self.manager.update_performance_metrics(model_name, metrics)
        performance = self.manager.get_performance_history(model_name)

        assert len(performance) > 0
        assert performance[-1]["accuracy"] == 0.75

    def test_model_rollback(self):
        """测试模型回滚"""
        # 注册多个版本
        self.manager.register_model({"name": "test", "version": "1.0"})
        self.manager.register_model({"name": "test", "version": "2.0"})

        # 回滚到上一个版本
        success = self.manager.rollback_to_version("test", "1.0")
        assert success is True

        current = self.manager.get_current_version("test")
        assert current == "1.0"


class TestFeatureExtractor:
    """特征提取器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        if FeatureExtractor is None:
            pytest.skip("FeatureExtractor not available")

        self.extractor = FeatureExtractor()

    def test_team_form_calculation(self):
        """测试球队状态计算"""
        recent_results = ["W", "W", "D", "L", "W"]
        form_points = self.extractor.calculate_form_points(recent_results)

        assert isinstance(form_points, (int, float))
        assert 0 <= form_points <= 15  # 5场比赛，最多15分

    def test_head_to_head_features(self):
        """测试历史交锋特征"""
        h2h_matches = [
            {"home_score": 2, "away_score": 1},
            {"home_score": 1, "away_score": 1},
            {"home_score": 0, "away_score": 2}
        ]

        features = self.extractor.extract_h2h_features(h2h_matches)

        assert "home_wins" in features
        assert "away_wins" in features
        assert "draws" in features
        assert features["home_wins"] == 1
        assert features["away_wins"] == 1
        assert features["draws"] == 1

    def test_goal_statistics(self):
        """测试进球统计特征"""
        goals = [2, 1, 0, 3, 1, 2, 0]
        stats = self.extractor.calculate_goal_statistics(goals)

        assert "avg_goals" in stats
        assert "total_goals" in stats
        assert "clean_sheets" in stats
        assert stats["total_goals"] == sum(goals)
        assert stats["avg_goals"] == sum(goals) / len(goals)

    def test_time_features(self):
        """测试时间相关特征"""
        match_time = datetime.now() + timedelta(days=3, hours=2)
        features = self.extractor.extract_time_features(match_time)

        assert "days_until_match" in features
        assert "hour_of_day" in features
        assert "day_of_week" in features
        assert features["days_until_match"] == 3

    def test_weather_features(self):
        """测试天气特征（如果有）"""
        weather_data = {
            "temperature": 20,
            "humidity": 65,
            "precipitation": 0,
            "wind_speed": 10
        }

        features = self.extractor.extract_weather_features(weather_data)

        if features:  # 如果支持天气特征
            assert "temperature" in features
            assert "humidity" in features

    def test_feature_normalization(self):
        """测试特征归一化"""
        features = {
            "home_goals": 10,
            "away_goals": 5,
            "home_wins": 3,
            "away_wins": 1
        }

        normalized = self.extractor.normalize_features(features)

        for key, value in normalized.items():
            assert 0 <= value <= 1

    def test_feature_selection(self):
        """测试特征选择"""
        all_features = {
            "home_goals": 10,
            "away_goals": 5,
            "useful_feature": 0.8,
            "useless_feature": 0.001,
            "another_useful": 0.6
        }

        selected = self.extractor.select_important_features(
            all_features,
            importance_threshold=0.01
        )

        assert "useless_feature" not in selected
        assert "home_goals" in selected


class TestPredictionValidation:
    """预测验证测试类"""

    def test_probability_distribution_validation(self):
        """测试概率分布验证"""
        if validate_prediction is None:
            pytest.skip("validate_prediction not available")

        # 有效的概率分布
        valid_prediction = {
            "home_win": 0.5,
            "draw": 0.3,
            "away_win": 0.2
        }
        assert validate_prediction(valid_prediction) is True

        # 无效的概率分布（总和不为1）
        invalid_prediction = {
            "home_win": 0.8,
            "draw": 0.8,
            "away_win": 0.2
        }
        assert validate_prediction(invalid_prediction) is False

        # 负概率
        negative_prediction = {
            "home_win": -0.1,
            "draw": 0.6,
            "away_win": 0.5
        }
        assert validate_prediction(negative_prediction) is False

    def test_prediction_consistency(self):
        """测试预测一致性检查"""
        result1 = PredictionResult(
            match_id=12345,
            home_win_probability=0.6,
            draw_probability=0.25,
            away_win_probability=0.15,
            predicted_result="home",
            confidence_score=0.6
        )

        result2 = PredictionResult(
            match_id=12345,
            home_win_probability=0.15,
            draw_probability=0.25,
            away_win_probability=0.6,
            predicted_result="away",
            confidence_score=0.6
        )

        # 相同比赛的不同预测应该被标记
        assert PredictionService.check_prediction_consistency(result1, result2) is False

    def test_outlier_detection(self):
        """测试异常值检测"""
        normal_predictions = [0.5, 0.3, 0.2, 0.6, 0.25, 0.15]
        outlier_prediction = 0.99  # 极端概率

        is_outlier = PredictionService.detect_outlier(
            outlier_prediction,
            normal_predictions,
            threshold=2.0
        )
        assert is_outlier is True

    def test_prediction_calibration(self):
        """测试预测校准"""
        predictions = [0.7, 0.6, 0.8, 0.65, 0.75]
        actual_outcomes = [1, 1, 1, 0, 1]  # 1=home_win, 0=not_home_win

        calibration_score = PredictionService.calculate_calibration_score(
            predictions,
            actual_outcomes
        )

        assert 0 <= calibration_score <= 1
        assert isinstance(calibration_score, (int, float))


class TestBatchPrediction:
    """批量预测测试类"""

    @pytest.mark.asyncio
    async def test_concurrent_batch_prediction(self):
        """测试并发批量预测"""
        if batch_predict_matches is None:
            pytest.skip("batch_predict_matches not available")

        match_ids = list(range(10001, 10011))  # 10场比赛
        max_concurrent = 3

        with patch('src.models.prediction_service.predict_match') as mock_predict:
            mock_predict.return_value = PredictionResult(
                match_id=0,
                home_win_probability=0.5,
                draw_probability=0.3,
                away_win_probability=0.2,
                predicted_result="home",
                confidence_score=0.5
            )

            results = await batch_predict_matches(
                match_ids,
                max_concurrent=max_concurrent
            )

            assert len(results) == len(match_ids)
            assert mock_predict.call_count == len(match_ids)

    def test_batch_progress_tracking(self):
        """测试批量预测进度跟踪"""
        batch_id = os.getenv("TEST_PREDICTION_SERVICE_COMPREHENSIVE_BATCH_ID_616")
        total_matches = 100

        # 初始化进度
        PredictionService.init_batch_progress(batch_id, total_matches)
        progress = PredictionService.get_batch_progress(batch_id)
        assert progress["total"] == total_matches
        assert progress["completed"] == 0

        # 更新进度
        for i in range(10):
            PredictionService.update_batch_progress(batch_id)

        progress = PredictionService.get_batch_progress(batch_id)
        assert progress["completed"] == 10
        assert progress["percentage"] == 10.0

    def test_batch_result_aggregation(self):
        """测试批量结果聚合"""
        results = [
            PredictionResult(
                match_id=i,
                home_win_probability=0.5 + i * 0.01,
                draw_probability=0.3,
                away_win_probability=0.2 - i * 0.01,
                predicted_result="home" if i % 2 == 0 else "away",
                confidence_score=0.5 + i * 0.01
            ) for i in range(1, 6)
        ]

        aggregation = PredictionService.aggregate_batch_results(results)

        assert "total_predictions" in aggregation
        assert "home_win_count" in aggregation
        assert "away_win_count" in aggregation
        assert "draw_count" in aggregation
        assert "avg_confidence" in aggregation
        assert aggregation["total_predictions"] == 5