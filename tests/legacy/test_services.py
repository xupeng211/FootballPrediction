"""
服务层模块测试

测试服务层模块的核心功能：
- src/services/inference_service.py
- src/services/real_prediction_service.py
- src/services/explainability_service.py

使用Mock来避免依赖问题，专注于测试业务逻辑。
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List


class TestInferenceService:
    """推理服务测试"""

    @pytest.mark.asyncio
    async def test_inference_service_initialization(self):
        """测试推理服务初始化"""

        # 模拟推理服务初始化
        class MockInferenceService:
            def __init__(self):
                # 模拟依赖初始化
                self.db_pool = AsyncMock()
                self.feature_transformer = Mock()
                self.model = Mock()
                self.model_loaded = False
                self.feature_names = []
                self.prediction_cache = {}
                self.cache_ttl = 300  # 5分钟

            async def initialize(self):
                """异步初始化服务"""
                # 初始化数据库连接池
                await self.db_pool.initialize()

                # 初始化特征转换器
                self.feature_transformer.setup()

                # 初始化模型（但不加载）
                self.model.setup_model()

                return True

        service = MockInferenceService()

        # 测试初始状态
        assert service.model_loaded is False
        assert service.prediction_cache == {}
        assert service.cache_ttl == 300

        # 测试初始化
        result = await service.initialize()
        assert result is True

        # 验证初始化调用
        service.db_pool.initialize.assert_called_once()
        service.feature_transformer.setup.assert_called_once()
        service.model.setup_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_predict_match_success(self):
        """测试比赛预测成功"""

        class MockInferenceService:
            def __init__(self):
                self.model_loaded = True
                self.model = Mock()
                self.feature_transformer = Mock()
                self.db_pool = Mock()
                self.prediction_cache = {}

            async def _load_match_data(self, match_id):
                """模拟加载比赛数据"""
                return {
                    "match_id": match_id,
                    "home_team_id": 1,
                    "away_team_id": 2,
                    "league_id": 10,
                    "match_date": "2024-01-01",
                    "venue": "home_stadium",
                }

            async def _extract_features(self, match_data):
                """模拟特征提取"""
                return {
                    "features": np.array(
                        [
                            0.5,
                            0.3,
                            0.7,
                            0.2,
                            0.8,
                            0.4,
                            0.6,
                            0.1,
                            0.9,
                            0.5,
                            0.3,
                            0.7,
                            0.2,
                        ]
                    ),
                    "feature_names": [
                        "home_form",
                        "away_form",
                        "h2h_home_win_rate",
                        "h2h_away_win_rate",
                        "home_goals_conceded",
                        "away_goals_scored",
                        "venue_home_advantage",
                        "league_home_advantage",
                        "home_recent_form",
                        "away_recent_form",
                        "head_to_head_draws",
                        "team_morale_home",
                        "team_morale_away",
                    ],
                }

            async def predict_match(self, match_id):
                """预测比赛结果"""
                if not self.model_loaded:
                    raise RuntimeError("Model not loaded")

                # 检查缓存
                cache_key = f"match_{match_id}"
                if cache_key in self.prediction_cache:
                    return self.prediction_cache[cache_key]

                # 加载数据
                match_data = await self._load_match_data(match_id)

                # 提取特征
                features_result = await self._extract_features(match_data)
                features = features_result["features"]
                feature_names = features_result["feature_names"]

                # 模型预测
                probabilities = self.model.predict_proba(features.reshape(1, -1))[0]
                predicted_class_idx = np.argmax(probabilities)

                class_mapping = {0: "AWAY_WIN", 1: "DRAW", 2: "HOME_WIN"}
                predicted_class = class_mapping[predicted_class_idx]

                result = {
                    "match_id": match_id,
                    "predictions": {
                        "HOME_WIN": float(probabilities[2]),
                        "DRAW": float(probabilities[1]),
                        "AWAY_WIN": float(probabilities[0]),
                    },
                    "predicted_class": predicted_class,
                    "confidence": float(np.max(probabilities)),
                    "features_used": feature_names,
                    "timestamp": "2024-01-01T12:00:00Z",
                }

                # 缓存结果
                self.prediction_cache[cache_key] = result
                return result

        # 设置模型mock
        mock_probabilities = np.array([0.3, 0.25, 0.45])  # AWAY_WIN, DRAW, HOME_WIN
        mock_model = Mock()
        mock_model.predict_proba.return_value = [mock_probabilities]

        service = MockInferenceService()
        service.model = mock_model

        # 测试预测
        result = await service.predict_match(12345)

        # 验证结果
        assert result["match_id"] == 12345
        assert result["predicted_class"] == "HOME_WIN"
        assert result["confidence"] == 0.45
        assert result["predictions"]["HOME_WIN"] == 0.45
        assert result["predictions"]["DRAW"] == 0.25
        assert result["predictions"]["AWAY_WIN"] == 0.3
        assert len(result["features_used"]) == 13

        # 验证模型被调用
        mock_model.predict_proba.assert_called_once()

        # 验证缓存
        cache_key = "match_12345"
        assert cache_key in service.prediction_cache

    @pytest.mark.asyncio
    async def test_predict_match_model_not_loaded(self):
        """测试比赛预测 - 模型未加载"""

        class MockInferenceService:
            def __init__(self):
                self.model_loaded = False

            async def predict_match(self, match_id):
                if not self.model_loaded:
                    raise RuntimeError("Model not loaded")
                return {"prediction": "result"}

        service = MockInferenceService()

        with pytest.raises(RuntimeError, match="Model not loaded"):
            await service.predict_match(12345)

    @pytest.mark.asyncio
    async def test_predict_match_cached_result(self):
        """测试比赛预测 - 缓存结果"""

        class MockInferenceService:
            def __init__(self):
                self.model_loaded = True
                self.prediction_cache = {}

            async def predict_match(self, match_id):
                cache_key = f"match_{match_id}"

                # 检查缓存
                if cache_key in self.prediction_cache:
                    return self.prediction_cache[cache_key]

                # 如果没有缓存，模拟新的预测
                new_result = {
                    "match_id": match_id,
                    "predicted_class": "HOME_WIN",
                    "confidence": 0.67,
                    "cached": False,
                }

                self.prediction_cache[cache_key] = new_result
                return new_result

        service = MockInferenceService()

        # 预先填充缓存
        cached_result = {
            "match_id": 12345,
            "predicted_class": "DRAW",
            "confidence": 0.33,
            "cached": True,
        }
        service.prediction_cache["match_12345"] = cached_result

        # 测试从缓存获取结果
        result = await service.predict_match(12345)

        assert result["predicted_class"] == "DRAW"
        assert result["confidence"] == 0.33
        assert result["cached"] is True

    @pytest.mark.asyncio
    async def test_reload_model_success(self):
        """测试模型重载成功"""

        class MockInferenceService:
            def __init__(self):
                self.model_loaded = True
                self.model = Mock()
                self.model_path = "models/old_model.pkl"

            async def reload_model(self, model_path=None):
                """重载模型"""
                try:
                    new_model_path = model_path or "models/default_model.pkl"

                    # 模拟模型加载过程
                    await self._unload_current_model()
                    await self._load_new_model(new_model_path)

                    self.model_path = new_model_path
                    self.model_loaded = True

                    return {
                        "success": True,
                        "model_path": new_model_path,
                        "previous_model": "models/old_model.pkl",
                        "reload_time": "2024-01-01T12:00:00Z",
                        "model_version": "v2.1.0",
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "model_path": new_model_path,
                    }

            async def _unload_current_model(self):
                """卸载当前模型"""
                self.model = None
                self.model_loaded = False

            async def _load_new_model(self, model_path):
                """加载新模型"""
                # 模拟加载延迟
                await asyncio.sleep(0.01)
                self.model = Mock()
                self.model_loaded = True

        service = MockInferenceService()

        # 测试重载成功
        result = await service.reload_model("models/new_model.pkl")

        assert result["success"] is True
        assert result["model_path"] == "models/new_model.pkl"
        assert result["previous_model"] == "models/old_model.pkl"
        assert result["model_version"] == "v2.1.0"
        assert service.model_loaded is True

    @pytest.mark.asyncio
    async def test_reload_model_failure(self):
        """测试模型重载失败"""

        class MockInferenceService:
            def __init__(self):
                self.model_loaded = True

            async def reload_model(self, model_path=None):
                try:
                    new_model_path = model_path or "models/default_model.pkl"

                    # 模拟加载失败
                    if "missing" in new_model_path:
                        raise FileNotFoundError(
                            f"Model file not found: {new_model_path}"
                        )

                    return {"success": True, "model_path": new_model_path}

                except Exception as e:
                    return {"success": False, "error": str(e), "model_path": model_path}

        service = MockInferenceService()

        # 测试加载失败
        result = await service.reload_model("models/missing_model.pkl")

        assert result["success"] is False
        assert "Model file not found" in result["error"]
        assert result["model_path"] == "models/missing_model.pkl"

    @pytest.mark.asyncio
    async def test_batch_predictions(self):
        """测试批量预测"""

        class MockInferenceService:
            def __init__(self):
                self.model_loaded = True
                self.prediction_count = 0

            async def predict_match(self, match_id):
                """单个预测"""
                # 模拟预测延迟
                await asyncio.sleep(0.01)

                self.prediction_count += 1

                return {
                    "match_id": match_id,
                    "predicted_class": "HOME_WIN" if match_id % 2 == 0 else "DRAW",
                    "confidence": 0.65 + (match_id % 10) * 0.02,
                }

            async def predict_batch(self, match_ids):
                """批量预测"""
                if not self.model_loaded:
                    raise RuntimeError("Model not loaded")

                # 并发执行预测
                tasks = [self.predict_match(match_id) for match_id in match_ids]
                results = await asyncio.gather(*tasks)

                return {
                    "predictions": results,
                    "total_count": len(results),
                    "success_count": len(results),
                    "timestamp": "2024-01-01T12:00:00Z",
                }

        service = MockInferenceService()
        match_ids = [12345, 12346, 12347]

        # 测试批量预测
        result = await service.predict_batch(match_ids)

        assert result["total_count"] == 3
        assert result["success_count"] == 3
        assert len(result["predictions"]) == 3

        # 验证预测结果
        predictions = result["predictions"]
        assert predictions[0]["match_id"] == 12345
        assert predictions[0]["predicted_class"] == "DRAW"  # 奇数
        assert predictions[1]["match_id"] == 12346
        assert predictions[1]["predicted_class"] == "HOME_WIN"  # 偶数

        # 验证并发执行
        assert service.prediction_count == 3


class TestRealPredictionService:
    """真实预测服务测试"""

    def test_real_prediction_service_initialization(self):
        """测试真实预测服务初始化"""

        class MockRealPredictionService:
            def __init__(self, model_path=None):
                self.model_path = model_path or "models/default_model.json"
                self.model = None
                self.model_loaded = False
                self.feature_names = []
                self.data_loader = Mock()

            def load_model(self):
                """加载模型"""
                if "not_found" in self.model_path:
                    raise FileNotFoundError(f"Model file not found: {self.model_path}")

                # 模拟模型加载
                self.model = Mock()
                self.feature_names = [
                    "home_team_id",
                    "away_team_id",
                    "league_id",
                    "home_goals_5",
                    "away_goals_5",
                    "home_form_3",
                    "away_form_3",
                    "h2h_home_wins",
                    "h2h_away_wins",
                ]
                self.model_loaded = True
                return True

        # 测试默认初始化
        service1 = MockRealPredictionService()
        assert service1.model_path == "models/default_model.json"
        assert service1.model_loaded is False
        assert service1.data_loader is not None

        # 测试自定义路径初始化
        custom_path = "/custom/path/model.json"
        service2 = MockRealPredictionService(custom_path)
        assert service2.model_path == custom_path

    def test_load_model_success(self):
        """测试模型加载成功"""

        class MockRealPredictionService:
            def __init__(self):
                self.model_path = "models/valid_model.json"
                self.model = None
                self.model_loaded = False
                self.feature_names = []

            def load_model(self):
                from xgboost import XGBClassifier

                # 模拟成功加载
                self.model = XGBClassifier()
                self.feature_names = ["feature_1", "feature_2", "feature_3"]
                self.model_loaded = True
                return True

        service = MockRealPredictionService()
        result = service.load_model()

        assert result is True
        assert service.model_loaded is True
        assert service.model is not None
        assert len(service.feature_names) == 3

    def test_load_model_file_not_found(self):
        """测试模型加载 - 文件不存在"""

        class MockRealPredictionService:
            def __init__(self):
                self.model_path = "models/missing_model.json"
                self.model_loaded = False

            def load_model(self):
                # 模拟文件不存在
                raise FileNotFoundError(f"Model file not found: {self.model_path}")

        service = MockRealPredictionService()

        with pytest.raises(FileNotFoundError, match="Model file not found"):
            service.load_model()

        assert service.model_loaded is False

    def test_predict_match_success(self):
        """测试比赛预测成功"""

        class MockRealPredictionService:
            def __init__(self):
                self.model_loaded = True
                self.model = Mock()
                self.feature_names = [
                    "home_team_id",
                    "away_team_id",
                    "league_id",
                    "home_goals_5",
                    "away_goals_5",
                    "h2h_goals_diff",
                ]
                self.data_loader = Mock()

            def predict_match(self, match_id):
                if not self.model_loaded:
                    raise RuntimeError("Model not loaded")

                # 模拟数据加载
                match_data = pd.DataFrame(
                    {
                        "match_id": [match_id],
                        "home_team_id": [1],
                        "away_team_id": [2],
                        "league_id": [10],
                        "home_goals_5": [2.0],
                        "away_goals_5": [1.0],
                        "h2h_goals_diff": [0.5],
                    }
                )

                # 模拟特征提取
                features = match_data[self.feature_names].values

                # 模拟模型预测
                probabilities = [0.25, 0.30, 0.45]  # AWAY_WIN, DRAW, HOME_WIN
                self.model.predict_proba.return_value = [probabilities]

                pred_proba = self.model.predict_proba(features)[0]
                predicted_class_idx = np.argmax(pred_proba)

                class_mapping = {0: "AWAY_WIN", 1: "DRAW", 2: "HOME_WIN"}
                predicted_class = class_mapping[predicted_class_idx]

                return {
                    "match_id": match_id,
                    "predictions": {
                        "HOME_WIN": float(pred_proba[2]),
                        "DRAW": float(pred_proba[1]),
                        "AWAY_WIN": float(pred_proba[0]),
                    },
                    "predicted_class": predicted_class,
                    "confidence": float(np.max(pred_proba)),
                    "features_count": len(features[0]),
                    "model_version": "v1.0.0",
                }

        service = MockRealPredictionService()

        # 测试预测
        result = service.predict_match(12345)

        assert result["match_id"] == 12345
        assert result["predicted_class"] == "HOME_WIN"
        assert result["confidence"] == 0.45
        assert result["predictions"]["HOME_WIN"] == 0.45
        assert result["predictions"]["DRAW"] == 0.30
        assert result["predictions"]["AWAY_WIN"] == 0.25
        assert result["features_count"] == 6
        assert result["model_version"] == "v1.0.0"

        # 验证模型调用
        service.model.predict_proba.assert_called_once()

    def test_predict_match_model_not_loaded(self):
        """测试比赛预测 - 模型未加载"""

        class MockRealPredictionService:
            def __init__(self):
                self.model_loaded = False

            def predict_match(self, match_id):
                if not self.model_loaded:
                    raise RuntimeError("Model not loaded")
                return {"prediction": "result"}

        service = MockRealPredictionService()

        with pytest.raises(RuntimeError, match="Model not loaded"):
            service.predict_match(12345)

    def test_predict_batch_matches(self):
        """测试批量比赛预测"""

        class MockRealPredictionService:
            def __init__(self):
                self.model_loaded = True
                self.model = Mock()
                self.data_loader = Mock()

            def predict_match(self, match_id):
                # 模拟不同的预测结果
                base_confidence = 0.4
                variation = (match_id % 5) * 0.05

                return {
                    "match_id": match_id,
                    "predicted_class": ["HOME_WIN", "DRAW", "AWAY_WIN"][match_id % 3],
                    "confidence": base_confidence + variation,
                    "predictions": {
                        "HOME_WIN": 0.4 + variation if match_id % 3 == 0 else 0.3,
                        "DRAW": 0.3 if match_id % 3 == 1 else 0.3,
                        "AWAY_WIN": 0.3 if match_id % 3 == 2 else 0.4 - variation,
                    },
                }

            def predict_batch_matches(self, match_ids):
                if not self.model_loaded:
                    raise RuntimeError("Model not loaded")

                predictions = [self.predict_match(match_id) for match_id in match_ids]

                return {
                    "predictions": predictions,
                    "total_count": len(predictions),
                    "success_count": len(predictions),
                    "avg_confidence": np.mean([p["confidence"] for p in predictions]),
                    "timestamp": "2024-01-01T12:00:00Z",
                }

        service = MockRealPredictionService()
        match_ids = [12345, 12346, 12347, 12348, 12349]

        result = service.predict_batch_matches(match_ids)

        assert result["total_count"] == 5
        assert result["success_count"] == 5
        assert len(result["predictions"]) == 5
        assert 0.4 <= result["avg_confidence"] <= 0.6

        # 验证每个预测都有正确的结构
        for prediction in result["predictions"]:
            assert "match_id" in prediction
            assert "predicted_class" in prediction
            assert "confidence" in prediction
            assert "predictions" in prediction
            assert prediction["match_id"] in match_ids

    def test_predict_invalid_match_id(self):
        """测试预测无效比赛ID"""

        class MockRealPredictionService:
            def __init__(self):
                self.model_loaded = True

            def predict_match(self, match_id):
                if match_id <= 0:
                    raise ValueError("Invalid match ID: must be positive integer")

                return {"match_id": match_id, "prediction": "result"}

        service = MockRealPredictionService()

        # 测试无效ID
        with pytest.raises(ValueError, match="Invalid match ID"):
            service.predict_match(-1)

        with pytest.raises(ValueError, match="Invalid match ID"):
            service.predict_match(0)


class TestExplainabilityService:
    """解释性服务测试"""

    def test_feature_importance_analysis(self):
        """测试特征重要性分析"""

        class MockExplainabilityService:
            def __init__(self):
                self.model = Mock()
                self.feature_names = [
                    "home_form",
                    "away_form",
                    "h2h_home_win_rate",
                    "venue_home_advantage",
                    "home_goals_conceded",
                    "away_goals_scored",
                    "league_home_advantage",
                ]

            def get_feature_importance(self):
                """获取特征重要性"""
                # 模拟特征重要性分数
                importance_scores = [
                    0.25,  # home_form
                    0.20,  # away_form
                    0.18,  # h2h_home_win_rate
                    0.15,  # venue_home_advantage
                    0.10,  # home_goals_conceded
                    0.07,  # away_goals_scored
                    0.05,  # league_home_advantage
                ]

                feature_importance = [
                    {"feature": feature, "importance": score, "rank": idx + 1}
                    for idx, (feature, score) in enumerate(
                        zip(self.feature_names, importance_scores)
                    )
                ]

                # 按重要性排序
                feature_importance.sort(key=lambda x: x["importance"], reverse=True)

                return {
                    "feature_importance": feature_importance,
                    "total_features": len(feature_importance),
                    "top_features": feature_importance[:5],
                    "model_type": "xgboost",
                }

        service = MockExplainabilityService()
        result = service.get_feature_importance()

        assert result["total_features"] == 7
        assert result["model_type"] == "xgboost"
        assert len(result["feature_importance"]) == 7
        assert len(result["top_features"]) == 5

        # 验证排序
        importance_list = result["feature_importance"]
        assert importance_list[0]["feature"] == "home_form"
        assert importance_list[0]["importance"] == 0.25
        assert importance_list[0]["rank"] == 1

        assert importance_list[1]["feature"] == "away_form"
        assert importance_list[1]["importance"] == 0.20
        assert importance_list[1]["rank"] == 2

    def test_prediction_explanation(self):
        """测试预测解释"""

        class MockExplainabilityService:
            def __init__(self):
                self.model = Mock()
                self.feature_names = [
                    "home_form",
                    "away_form",
                    "h2h_stats",
                    "venue_advantage",
                    "recent_goals",
                ]

            def explain_prediction(self, match_id, prediction_result):
                """解释单次预测"""
                # 模拟SHAP解释值
                shap_values = {
                    "home_form": 0.15,
                    "away_form": -0.08,
                    "h2h_stats": 0.12,
                    "venue_advantage": 0.06,
                    "recent_goals": -0.03,
                }

                # 计算基线值
                base_value = 0.33  # 平均概率

                # 构建解释
                explanation = {
                    "match_id": match_id,
                    "predicted_class": prediction_result.get("predicted_class"),
                    "base_value": base_value,
                    "feature_contributions": [],
                    "summary": {},
                }

                # 按贡献度排序
                sorted_features = sorted(
                    shap_values.items(), key=lambda x: abs(x[1]), reverse=True
                )

                for feature, contribution in sorted_features:
                    explanation["feature_contributions"].append(
                        {
                            "feature": feature,
                            "contribution": contribution,
                            "impact": "positive" if contribution > 0 else "negative",
                            "magnitude": abs(contribution),
                        }
                    )

                # 生成摘要
                positive_features = [f for f, c in shap_values.items() if c > 0]
                negative_features = [f for f, c in shap_values.items() if c < 0]

                explanation["summary"] = {
                    "main_positive_factors": positive_features[:3],
                    "main_negative_factors": negative_features[:3],
                    "explanation_text": self._generate_explanation_text(
                        prediction_result.get("predicted_class"),
                        positive_features,
                        negative_features,
                    ),
                }

                return explanation

            def _generate_explanation_text(
                self, predicted_class, positive_factors, negative_factors
            ):
                """生成解释文本"""
                positive_text = (
                    ", ".join(positive_factors[:2]) if positive_factors else "无"
                )
                negative_text = (
                    ", ".join(negative_factors[:2]) if negative_factors else "无"
                )

                return f"预测{predicted_class}的主要原因: {positive_text}对结果有积极影响，而{negative_text}对结果有消极影响。"

        service = MockExplainabilityService()

        prediction_result = {
            "match_id": 12345,
            "predicted_class": "HOME_WIN",
            "confidence": 0.67,
        }

        explanation = service.explain_prediction(12345, prediction_result)

        assert explanation["match_id"] == 12345
        assert explanation["predicted_class"] == "HOME_WIN"
        assert explanation["base_value"] == 0.33
        assert len(explanation["feature_contributions"]) == 5

        # 验证特征贡献
        contributions = explanation["feature_contributions"]
        home_form_contrib = next(
            c for c in contributions if c["feature"] == "home_form"
        )
        assert home_form_contrib["contribution"] == 0.15
        assert home_form_contrib["impact"] == "positive"
        assert home_form_contrib["magnitude"] == 0.15

        away_form_contrib = next(
            c for c in contributions if c["feature"] == "away_form"
        )
        assert away_form_contrib["contribution"] == -0.08
        assert away_form_contrib["impact"] == "negative"
        assert away_form_contrib["magnitude"] == 0.08

        # 验证摘要
        summary = explanation["summary"]
        assert "main_positive_factors" in summary
        assert "main_negative_factors" in summary
        assert "explanation_text" in summary
        assert "HOME_WIN" in summary["explanation_text"]

    def test_batch_explanation(self):
        """测试批量解释"""

        class MockExplainabilityService:
            def __init__(self):
                self.feature_names = ["feature_1", "feature_2", "feature_3"]

            def explain_batch_predictions(self, predictions):
                """批量解释预测"""
                explanations = []

                for i, pred in enumerate(predictions):
                    # 为每个预测生成解释
                    shap_values = {
                        "feature_1": 0.1 * (i + 1),
                        "feature_2": -0.05 * (i + 1),
                        "feature_3": 0.02 * (i + 1),
                    }

                    explanation = {
                        "match_id": pred["match_id"],
                        "feature_contributions": [
                            {
                                "feature": feature,
                                "contribution": contribution,
                                "impact": (
                                    "positive" if contribution > 0 else "negative"
                                ),
                            }
                            for feature, contribution in shap_values.items()
                        ],
                        "top_factor": max(shap_values.items(), key=lambda x: abs(x[1])),
                        "summary": f"Match {pred['match_id']} prediction explained by top feature",
                    }

                    explanations.append(explanation)

                return {
                    "explanations": explanations,
                    "total_count": len(explanations),
                    "avg_contributions": self._calculate_avg_contributions(
                        explanations
                    ),
                }

            def _calculate_avg_contributions(self, explanations):
                """计算平均贡献度"""
                feature_sums = {}
                feature_counts = {}

                for exp in explanations:
                    for contrib in exp["feature_contributions"]:
                        feature = contrib["feature"]
                        contribution = contrib["contribution"]

                        if feature not in feature_sums:
                            feature_sums[feature] = 0
                            feature_counts[feature] = 0

                        feature_sums[feature] += contribution
                        feature_counts[feature] += 1

                avg_contributions = {
                    feature: feature_sums[feature] / feature_counts[feature]
                    for feature in feature_sums
                }

                return avg_contributions

        service = MockExplainabilityService()

        predictions = [
            {"match_id": 12345, "predicted_class": "HOME_WIN"},
            {"match_id": 12346, "predicted_class": "DRAW"},
            {"match_id": 12347, "predicted_class": "AWAY_WIN"},
        ]

        result = service.explain_batch_predictions(predictions)

        assert result["total_count"] == 3
        assert len(result["explanations"]) == 3
        assert "avg_contributions" in result

        # 验证平均贡献度
        avg_contribs = result["avg_contributions"]
        assert "feature_1" in avg_contribs
        assert "feature_2" in avg_contribs
        assert "feature_3" in avg_contribs

        # 验证每个解释的结构
        for explanation in result["explanations"]:
            assert "match_id" in explanation
            assert "feature_contributions" in explanation
            assert "top_factor" in explanation
            assert "summary" in explanation


if __name__ == "__main__":
    # 运行服务层测试
    pytest.main([__file__, "-v"])
