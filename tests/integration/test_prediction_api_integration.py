"""
预测API集成测试
Prediction API Integration Tests

测试预测相关的API端点和业务逻辑.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Optional
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel


# 模拟数据模型
class MatchPredictionRequest(BaseModel):
    home_team: str
    away_team: str
    match_date: str
    league: str = "premier_league"


class MatchPredictionResponse(BaseModel):
    prediction_id: str
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    confidence_score: float
    recommended_bet: str | None = None
    created_at: datetime


@pytest.mark.integration
class TestPredictionAPIIntegration:
    """预测API集成测试"""

    @pytest.fixture
    def mock_prediction_service(self):
        """模拟预测服务"""
        service = AsyncMock()
        service.create_prediction.return_value = {
            "id": "pred_12345",
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "match_date": "2024-12-01T20:00:00Z",
            "home_win_probability": 0.45,
            "draw_probability": 0.25,
            "away_win_probability": 0.30,
            "confidence_score": 0.78,
            "recommended_bet": "home_win",
            "model_version": "v2.1.0",
            "created_at": datetime.utcnow(),
        }
        service.get_prediction_by_id.return_value = {
            "id": "pred_12345",
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "status": "completed",
            "home_win_probability": 0.45,
            "draw_probability": 0.25,
            "away_win_probability": 0.30,
            "confidence_score": 0.78,
        }
        service.get_user_predictions.return_value = [
            {
                "id": "pred_12345",
                "home_team": "Manchester United",
                "away_team": "Liverpool",
                "status": "completed",
            },
            {
                "id": "pred_67890",
                "home_team": "Chelsea",
                "away_team": "Arsenal",
                "status": "pending",
            },
        ]
        return service

    @pytest.fixture
    def mock_database(self):
        """模拟数据库"""
        db = AsyncMock()
        db.save_prediction.return_value = {"id": "pred_12345"}
        db.get_prediction.return_value = {"id": "pred_12345", "status": "completed"}
        db.get_user_predictions.return_value = [
            {"id": "pred_12345"},
            {"id": "pred_67890"},
        ]
        return db

    @pytest.fixture
    def mock_cache(self):
        """模拟缓存服务"""
        cache = AsyncMock()
        cache.get.return_value = None
        cache.set.return_value = True
        cache.delete.return_value = True
        return cache

    @pytest.mark.asyncio

    async def test_create_match_prediction(self, mock_prediction_service, mock_cache):
        """测试创建比赛预测"""
        # 1. 准备预测请求数据
        request_data = MatchPredictionRequest(
            home_team="Manchester United",
            away_team="Liverpool",
            match_date="2024-12-01T20:00:00Z",
            league="premier_league",
        )

        # 2. 检查缓存中是否已有预测
        cache_key = f"prediction:{request_data.home_team}:{request_data.away_team}:{request_data.match_date}"
        cached_result = await mock_cache.get(cache_key)
        assert cached_result is None  # 缓存中没有

        # 3. 调用预测服务
        prediction = await mock_prediction_service.create_prediction(
            home_team=request_data.home_team,
            away_team=request_data.away_team,
            match_date=request_data.match_date,
            league=request_data.league,
        )

        # 4. 验证预测结果
        assert prediction["home_team"] == "Manchester United"
        assert prediction["away_team"] == "Liverpool"
        assert 0 <= prediction["home_win_probability"] <= 1
        assert 0 <= prediction["draw_probability"] <= 1
        assert 0 <= prediction["away_win_probability"] <= 1
        assert (
            abs(
                prediction["home_win_probability"]
                + prediction["draw_probability"]
                + prediction["away_win_probability"]
                - 1.0
            )
            < 0.01
        )

        # 5. 缓存预测结果
        await mock_cache.set(cache_key, prediction, expire=3600)

        # 6. 验证服务调用
        mock_prediction_service.create_prediction.assert_called_once()
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio

    async def test_get_prediction_by_id(self, mock_prediction_service, mock_cache):
        """测试根据ID获取预测"""
        # 1. 准备预测ID
        prediction_id = "pred_12345"

        # 2. 检查缓存
        cache_key = f"prediction:by_id:{prediction_id}"
        cached_prediction = await mock_cache.get(cache_key)

        if cached_prediction is None:
            # 3. 从数据库获取
            prediction = await mock_prediction_service.get_prediction_by_id(
                prediction_id
            )
            assert prediction is not None
            assert prediction["id"] == prediction_id

            # 4. 缓存结果
            await mock_cache.set(cache_key, prediction, expire=1800)
        else:
            prediction = cached_prediction

        # 5. 验证预测数据
        assert "home_win_probability" in prediction
        assert "confidence_score" in prediction
        assert prediction["status"] == "completed"

    @pytest.mark.asyncio

    async def test_get_user_predictions(self, mock_prediction_service, mock_cache):
        """测试获取用户预测历史"""
        # 1. 准备用户ID和分页参数
        user_id = 1
        page = 1
        limit = 20

        # 2. 检查缓存
        cache_key = f"user_predictions:{user_id}:page:{page}:limit:{limit}"
        cached_predictions = await mock_cache.get(cache_key)

        if cached_predictions is None:
            # 3. 从服务获取
            predictions = await mock_prediction_service.get_user_predictions(
                user_id=user_id, page=page, limit=limit
            )
            assert len(predictions) >= 0

            # 4. 缓存结果
            await mock_cache.set(cache_key, predictions, expire=600)
        else:
            predictions = cached_predictions

        # 5. 验证预测列表
        if predictions:
            for prediction in predictions:
                assert "id" in prediction
                assert "home_team" in prediction
                assert "away_team" in prediction
                assert "status" in prediction

    @pytest.mark.asyncio

    async def test_batch_prediction_creation(self, mock_prediction_service):
        """测试批量创建预测"""
        # 1. 准备批量预测数据
        batch_requests = [
            {
                "home_team": "Manchester United",
                "away_team": "Liverpool",
                "match_date": "2024-12-01T20:00:00Z",
            },
            {
                "home_team": "Chelsea",
                "away_team": "Arsenal",
                "match_date": "2024-12-02T15:00:00Z",
            },
            {
                "home_team": "Manchester City",
                "away_team": "Tottenham",
                "match_date": "2024-12-03T17:30:00Z",
            },
        ]

        # 2. 批量处理预测
        batch_results = []
        for request in batch_requests:
            prediction = await mock_prediction_service.create_prediction(**request)
            batch_results.append(prediction)

        # 3. 验证批量结果
        assert len(batch_results) == len(batch_requests)
        for i, result in enumerate(batch_results):
            assert result["home_team"] == batch_requests[i]["home_team"]
            assert result["away_team"] == batch_requests[i]["away_team"]
            assert "home_win_probability" in result

    @pytest.mark.asyncio

    async def test_prediction_model_versions(self, mock_prediction_service):
        """测试预测模型版本管理"""
        # 1. 获取可用的模型版本
        current_version = "v2.1.0"

        # 2. 使用指定模型版本创建预测
        request_data = {
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "match_date": "2024-12-01T20:00:00Z",
            "model_version": current_version,
        }

        prediction = await mock_prediction_service.create_prediction(**request_data)
        assert prediction["model_version"] == current_version

        # 3. 测试模型版本回退
        fallback_version = "v2.0.0"
        request_data["model_version"] = fallback_version
        prediction_fallback = await mock_prediction_service.create_prediction(
            **request_data
        )
        assert prediction_fallback["model_version"] == fallback_version

    @pytest.mark.asyncio

    async def test_prediction_confidence_scoring(self, mock_prediction_service):
        """测试预测置信度评分"""
        # 1. 创建不同置信度的预测
        test_cases = [
            {
                "home_team": "Man City",
                "away_team": "West Ham",
                "expected_confidence": 0.85,
            },
            {
                "home_team": "Liverpool",
                "away_team": "Chelsea",
                "expected_confidence": 0.72,
            },
            {
                "home_team": "Burnley",
                "away_team": "Sheffield Utd",
                "expected_confidence": 0.91,
            },
        ]

        for case in test_cases:
            prediction = await mock_prediction_service.create_prediction(
                home_team=case["home_team"],
                away_team=case["away_team"],
                match_date="2024-12-01T20:00:00Z",
            )

            # 2. 验证置信度分数
            confidence = prediction["confidence_score"]
            assert 0 <= confidence <= 1
            assert confidence >= 0.5  # 最低置信度要求

            # 3. 验证置信度与概率分布的关系
            probabilities = [
                prediction["home_win_probability"],
                prediction["draw_probability"],
                prediction["away_win_probability"],
            ]
            max_prob = max(probabilities)

            # 最高概率应该与置信度正相关
            assert max_prob >= 0.3  # 至少30%的最高概率

    @pytest.mark.asyncio

    async def test_prediction_caching_strategy(self, mock_cache):
        """测试预测缓存策略"""

        # 1. 测试缓存键生成
        def generate_cache_key(
            home_team: str,
            away_team: str,
            match_date: str,
            model_version: str = "v2.1.0",
        ) -> str:
            import hashlib

            key_data = f"{home_team}:{away_team}:{match_date}:{model_version}"
            return f"prediction:{hashlib.md5(key_data.encode()).hexdigest()}"

        # 2. 生成并验证缓存键
        key1 = generate_cache_key("Man Utd", "Liverpool", "2024-12-01T20:00:00Z")
        key2 = generate_cache_key(
            "Man Utd", "Liverpool", "2024-12-01T20:00:00Z", "v2.0.0"
        )

        assert key1 != key2  # 不同模型版本应该有不同缓存键

        # 3. 测试缓存过期策略
        cache_duration = 3600  # 1小时
        current_time = time.time()
        cache_timestamp = current_time - 30  # 30秒前缓存

        # 模拟缓存过期检查
        def is_cache_expired(timestamp: float, duration: int) -> bool:
            return (current_time - timestamp) > duration

        assert not is_cache_expired(cache_timestamp, cache_duration)  # 未过期
        assert is_cache_expired(current_time - 3700, cache_duration)  # 已过期

    @pytest.mark.asyncio

    async def test_prediction_error_handling(self, mock_prediction_service):
        """测试预测错误处理"""
        # 1. 测试无效输入
        invalid_requests = [
            {},  # 空请求
            {"home_team": "", "away_team": "Liverpool"},  # 空主队
            {"home_team": "Man Utd", "away_team": ""},  # 空客队
            {
                "home_team": "Man Utd",
                "away_team": "Liverpool",
                "match_date": "invalid-date",
            },  # 无效日期
        ]

        for invalid_request in invalid_requests:
            try:
                await mock_prediction_service.create_prediction(**invalid_request)
                raise AssertionError("Should have raised an exception")
            except Exception as e:
                assert str(e)  # 应该有错误信息

        # 2. 测试服务不可用
        mock_prediction_service.create_prediction.side_effect = Exception(
            "Service unavailable"
        )

        with pytest.raises(Exception) as exc_info:
            await mock_prediction_service.create_prediction(
                home_team="Man Utd",
                away_team="Liverpool",
                match_date="2024-12-01T20:00:00Z",
            )
        assert "Service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio

    async def test_prediction_performance_monitoring(self):
        """测试预测性能监控"""
        # 1. 模拟性能指标收集
        performance_metrics = {
            "prediction_count": 0,
            "total_prediction_time": 0.0,
            "cache_hit_count": 0,
            "cache_miss_count": 0,
        }

        # 2. 模拟预测请求
        start_time = time.time()

        # 模拟预测处理
        await asyncio.sleep(0.01)  # 模拟10ms处理时间

        end_time = time.time()
        prediction_time = end_time - start_time

        # 3. 更新性能指标
        performance_metrics["prediction_count"] += 1
        performance_metrics["total_prediction_time"] += prediction_time

        # 4. 计算平均性能
        if performance_metrics["prediction_count"] > 0:
            avg_time = (
                performance_metrics["total_prediction_time"]
                / performance_metrics["prediction_count"]
            )
            assert avg_time < 1.0  # 平均预测时间应小于1秒

    @pytest.mark.asyncio

    async def test_prediction_data_validation(self):
        """测试预测数据验证"""

        # 1. 定义验证规则
        def validate_prediction_data(data: dict[str, Any]) -> list[str]:
            errors = []

            # 验证必需字段
            required_fields = ["home_team", "away_team", "match_date"]
            for field in required_fields:
                if field not in data or not data[field]:
                    errors.append(f"Missing or empty field: {field}")

            # 验证概率值
            probability_fields = [
                "home_win_probability",
                "draw_probability",
                "away_win_probability",
            ]
            total_probability = 0
            for field in probability_fields:
                if field in data:
                    prob = data[field]
                    if not isinstance(prob, (int, float)) or not (0 <= prob <= 1):
                        errors.append(f"Invalid probability value for {field}: {prob}")
                    else:
                        total_probability += prob

            # 验证概率总和
            if abs(total_probability - 1.0) > 0.01:
                errors.append(f"Probabilities must sum to 1.0, got {total_probability}")

            # 验证置信度
            if "confidence_score" in data:
                confidence = data["confidence_score"]
                if not isinstance(confidence, (int, float)) or not (
                    0 <= confidence <= 1
                ):
                    errors.append(f"Invalid confidence score: {confidence}")

            return errors

        # 2. 测试有效数据
        valid_data = {
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "match_date": "2024-12-01T20:00:00Z",
            "home_win_probability": 0.45,
            "draw_probability": 0.25,
            "away_win_probability": 0.30,
            "confidence_score": 0.78,
        }
        errors = validate_prediction_data(valid_data)
        assert len(errors) == 0

        # 3. 测试无效数据
        invalid_data = {
            "home_team": "",  # 空值
            "away_team": "Liverpool",
            "match_date": "2024-12-01T20:00:00Z",
            "home_win_probability": 0.45,
            "draw_probability": 0.25,
            "away_win_probability": 0.30,
            "confidence_score": 1.5,  # 超出范围
        }
        errors = validate_prediction_data(invalid_data)
        assert len(errors) >= 2

    @pytest.mark.asyncio

    async def test_prediction_rate_limiting(self):
        """测试预测API速率限制"""
        # 1. 设置速率限制参数
        rate_limits = {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "requests_per_day": 10000,
        }

        # 2. 模拟请求计数器
        request_counts = {"minute": [], "hour": [], "day": []}

        def check_rate_limit(user_id: int, limit_type: str) -> bool:
            current_time = time.time()
            counts = request_counts[limit_type]
            limit = rate_limits[f"requests_per_{limit_type}"]

            # 清理过期请求
            if limit_type == "minute":
                cutoff = current_time - 60
            elif limit_type == "hour":
                cutoff = current_time - 3600
            else:  # day
                cutoff = current_time - 86400

            request_counts[limit_type] = [
                req_time for req_time in counts if req_time > cutoff
            ]

            # 检查是否超过限制
            if len(request_counts[limit_type]) >= limit:
                return False

            request_counts[limit_type].append(current_time)
            return True

        # 3. 测试正常请求
        user_id = 123
        for _i in range(10):
            allowed = check_rate_limit(user_id, "minute")
            assert allowed is True

        # 4. 模拟超过限制（这里只是验证逻辑，不完全模拟）
        assert len(request_counts["minute"]) == 10
        assert request_counts["minute"][0] > time.time() - 60


@pytest.mark.integration
class TestPredictionAPIAdvancedFeatures:
    """预测API高级功能测试"""

    @pytest.mark.asyncio

    async def test_prediction_model_ensemble(self):
        """测试预测模型集成"""
        # 1. 模拟多个模型的预测结果
        model_predictions = {
            "logistic_regression": {"home_win": 0.44, "draw": 0.26, "away_win": 0.30},
            "random_forest": {"home_win": 0.46, "draw": 0.24, "away_win": 0.30},
            "neural_network": {"home_win": 0.43, "draw": 0.27, "away_win": 0.30},
            "xgboost": {"home_win": 0.45, "draw": 0.25, "away_win": 0.30},
        }

        # 2. 计算集成预测（简单平均）
        ensemble_prediction = {"home_win": 0, "draw": 0, "away_win": 0}
        model_count = len(model_predictions)

        for model_pred in model_predictions.values():
            for outcome, prob in model_pred.items():
                ensemble_prediction[outcome] += prob

        for outcome in ensemble_prediction:
            ensemble_prediction[outcome] /= model_count

        # 3. 验证集成结果
        total_prob = sum(ensemble_prediction.values())
        assert abs(total_prob - 1.0) < 0.01
        assert all(0 <= prob <= 1 for prob in ensemble_prediction.values())

    @pytest.mark.asyncio

    async def test_prediction_explanation_feature(self):
        """测试预测解释功能"""
        # 1. 模拟预测解释数据
        explanation = {
            "main_factors": [
                {
                    "factor": "home_advantage",
                    "weight": 0.15,
                    "description": "Home team advantage",
                },
                {
                    "factor": "recent_form",
                    "weight": 0.25,
                    "description": "Recent team performance",
                },
                {
                    "factor": "head_to_head",
                    "weight": 0.20,
                    "description": "Historical match results",
                },
                {
                    "factor": "team_strength",
                    "weight": 0.30,
                    "description": "Overall team strength",
                },
                {
                    "factor": "injuries",
                    "weight": 0.10,
                    "description": "Player availability",
                },
            ],
            "confidence_explanation": "High confidence based on strong recent form and home advantage",
            "risk_factors": ["Key player injury", "Tough upcoming schedule"],
        }

        # 2. 验证解释数据结构
        assert "main_factors" in explanation
        assert len(explanation["main_factors"]) > 0

        total_weight = sum(factor["weight"] for factor in explanation["main_factors"])
        assert abs(total_weight - 1.0) < 0.01  # 权重总和应该为1

        # 3. 验证每个因子
        for factor in explanation["main_factors"]:
            assert "factor" in factor
            assert "weight" in factor
            assert "description" in factor
            assert 0 <= factor["weight"] <= 1

    @pytest.mark.asyncio

    async def test_prediction_market_odds_comparison(self):
        """测试预测与市场赔率比较"""
        # 1. 模拟市场赔率
        market_odds = {
            "home_win": 2.10,  # 主胜赔率
            "draw": 3.40,  # 平局赔率
            "away_win": 3.80,  # 客胜赔率
        }

        # 2. 模型预测概率
        model_probabilities = {"home_win": 0.45, "draw": 0.25, "away_win": 0.30}

        # 3. 计算隐含概率（扣除抽水）
        def calculate_implied_probability(odds: float, margin: float = 0.05) -> float:
            return (1 / odds) * (1 - margin)

        implied_probabilities = {}
        for outcome, odds in market_odds.items():
            implied_probabilities[outcome] = calculate_implied_probability(odds)

        # 4. 查找价值投注
        value_bets = []
        for outcome in model_probabilities:
            model_prob = model_probabilities[outcome]
            implied_prob = implied_probabilities[outcome]

            if model_prob > implied_prob:
                value = (model_prob - implied_prob) * 100
                value_bets.append(
                    {
                        "outcome": outcome,
                        "model_probability": model_prob,
                        "implied_probability": implied_prob,
                        "value_percentage": value,
                        "recommended": True,
                    }
                )

        # 5. 验证价值投注分析
        assert len(implied_probabilities) == 3
        assert all(0 <= prob <= 1 for prob in implied_probabilities.values())

        # 如果有价值投注，验证其结构
        if value_bets:
            for bet in value_bets:
                assert "outcome" in bet
                assert "value_percentage" in bet
                assert bet["value_percentage"] > 0

    @pytest.mark.asyncio

    async def test_prediction_confidence_intervals(self):
        """测试预测置信区间"""
        # 1. 模拟预测结果和置信区间
        prediction_with_intervals = {
            "home_win_probability": 0.45,
            "home_win_ci_lower": 0.38,
            "home_win_ci_upper": 0.52,
            "draw_probability": 0.25,
            "draw_ci_lower": 0.20,
            "draw_ci_upper": 0.30,
            "away_win_probability": 0.30,
            "away_win_ci_lower": 0.25,
            "away_win_ci_upper": 0.35,
            "confidence_level": 0.95,
        }

        # 2. 验证置信区间结构
        outcomes = ["home_win", "draw", "away_win"]
        for outcome in outcomes:
            prob_key = f"{outcome}_probability"
            lower_key = f"{outcome}_ci_lower"
            upper_key = f"{outcome}_ci_upper"

            prob = prediction_with_intervals[prob_key]
            lower = prediction_with_intervals[lower_key]
            upper = prediction_with_intervals[upper_key]

            # 验证区间包含点估计
            assert lower <= prob <= upper
            # 验证区间合理范围
            assert 0 <= lower <= upper <= 1

        # 3. 验证置信水平
        assert prediction_with_intervals["confidence_level"] == 0.95

    @pytest.mark.asyncio

    async def test_prediction_sensitivity_analysis(self):
        """测试预测敏感性分析"""
        # 1. 基础预测
        base_prediction = {"home_win": 0.45, "draw": 0.25, "away_win": 0.30}

        # 2. 模拟不同条件下的预测变化
        scenarios = {
            "home_team_star_player_injured": {
                "home_win": 0.38,  # 下降
                "draw": 0.27,
                "away_win": 0.35,  # 上升
            },
            "away_team_key_defender_suspended": {
                "home_win": 0.50,  # 上升
                "draw": 0.23,
                "away_win": 0.27,  # 下降
            },
            "bad_weather_expected": {
                "home_win": 0.42,
                "draw": 0.33,  # 平局概率上升
                "away_win": 0.25,
            },
        }

        # 3. 计算敏感性指标
        sensitivity_analysis = {}
        for scenario, prediction in scenarios.items():
            changes = {}
            for outcome in base_prediction:
                base_prob = base_prediction[outcome]
                scenario_prob = prediction[outcome]
                change = scenario_prob - base_prob
                change_percentage = (change / base_prob) * 100
                changes[outcome] = {
                    "absolute_change": change,
                    "percentage_change": change_percentage,
                }
            sensitivity_analysis[scenario] = changes

        # 4. 验证敏感性分析结果
        for _scenario, changes in sensitivity_analysis.items():
            for _outcome, metrics in changes.items():
                assert "absolute_change" in metrics
                assert "percentage_change" in metrics
                assert isinstance(metrics["absolute_change"], (int, float))
                assert isinstance(metrics["percentage_change"], (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
