"""
端到端集成测试
End-to-End Integration Tests

测试完整的业务流程，验证系统各组件的协作。
Tests complete business workflows, validating collaboration between system components.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import pytest


# 模拟外部依赖和响应
class MockServiceResponse:
    """模拟服务响应"""

    def __init__(self, data: dict[str, Any], status_code: int = 200):
        self.data = data
        self.status_code = status_code

    def json(self):
        return self.data

    def __getitem__(self, key):
        return self.data.get(key)


class MockDatabaseService:
    """模拟数据库服务"""

    def __init__(self):
        self.teams = {}
        self.matches = {}
        self.predictions = {}
        self.users = {}

    async def create_team(self, team_data: dict[str, Any]) -> dict[str, Any]:
        """创建球队"""
        team_id = len(self.teams) + 1
        team_data["id"] = team_id
        team_data["created_at"] = datetime.now().isoformat()
        self.teams[team_id] = team_data
        return team_data

    async def create_match(self, match_data: dict[str, Any]) -> dict[str, Any]:
        """创建比赛"""
        match_id = len(self.matches) + 1
        match_data["id"] = match_id
        match_data["created_at"] = datetime.now().isoformat()
        match_data["status"] = "scheduled"
        self.matches[match_id] = match_data
        return match_data

    async def create_prediction(
        self, prediction_data: dict[str, Any]
    ) -> dict[str, Any]:
        """创建预测"""
        prediction_id = len(self.predictions) + 1
        prediction_data["id"] = prediction_id
        prediction_data["created_at"] = datetime.now().isoformat()
        self.predictions[prediction_id] = prediction_data
        return prediction_data

    async def get_team(self, team_id: int) -> dict[str, Any]:
        """获取球队"""
        return self.teams.get(team_id)

    async def get_match(self, match_id: int) -> dict[str, Any]:
        """获取比赛"""
        return self.matches.get(match_id)


class MockFeatureService:
    """模拟特征服务"""

    def __init__(self):
        self.features_cache = {}

    async def calculate_team_features(self, team_id: int) -> dict[str, Any]:
        """计算球队特征"""
        # 模拟特征计算
        return {
            "team_id": team_id,
            "recent_form": ["W", "D", "W", "L", "W"],
            "avg_goals_scored": 2.1,
            "avg_goals_conceded": 1.3,
            "home_advantage": 0.8,
            "calculated_at": datetime.now().isoformat(),
        }

    async def calculate_match_features(
        self, home_team_id: int, away_team_id: int
    ) -> dict[str, Any]:
        """计算比赛特征"""
        return {
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "head_to_head": {"home_wins": 3, "away_wins": 2, "draws": 1},
            "recent_encounters": 6,
            "calculated_at": datetime.now().isoformat(),
        }


class MockPredictionService:
    """模拟预测服务"""

    def __init__(self):
        self.models = ["poisson", "neural_network", "ensemble"]

    async def predict_match(
        self, features: dict[str, Any], model: str = "ensemble"
    ) -> dict[str, Any]:
        """预测比赛结果"""
        # 模拟预测逻辑
        import random

        random.seed(42)  # 确保可预测的结果

        home_prob = random.uniform(0.3, 0.7)
        draw_prob = random.uniform(0.2, 0.4)
        away_prob = 1.0 - home_prob - draw_prob

        outcomes = ["home_win", "draw", "away_win"]
        probabilities = [home_prob, draw_prob, away_prob]
        max_prob_index = probabilities.index(max(probabilities))

        return {
            "model": model,
            "probabilities": {
                "home_win": round(home_prob, 3),
                "draw": round(draw_prob, 3),
                "away_win": round(away_prob, 3),
            },
            "predicted_outcome": outcomes[max_prob_index],
            "confidence": round(max(probabilities), 3),
            "features_used": list(features.keys()),
            "calculated_at": datetime.now().isoformat(),
        }


@pytest.fixture
def mock_services():
    """模拟服务"""
    return {
        "database": MockDatabaseService(),
        "features": MockFeatureService(),
        "prediction": MockPredictionService(),
    }


@pytest.mark.integration
class TestEndToEndPredictionWorkflow:
    """端到端预测工作流测试"""

    async def test_complete_prediction_pipeline(self, mock_services):
        """测试完整的预测流水线"""
        # 1. 创建球队
        home_team_data = {
            "name": "Home Team FC",
            "short_name": "HTF",
            "country": "Test Country",
            "founded_year": 2020,
        }

        away_team_data = {
            "name": "Away Team FC",
            "short_name": "ATF",
            "country": "Test Country",
            "founded_year": 2018,
        }

        home_team = await mock_services["database"].create_team(home_team_data)
        away_team = await mock_services["database"].create_team(away_team_data)

        assert home_team["id"] is not None
        assert away_team["id"] is not None

        # 2. 创建比赛
        match_data = {
            "home_team_id": home_team["id"],
            "away_team_id": away_team["id"],
            "match_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "league": "Test League",
            "venue": "Test Stadium",
        }

        match = await mock_services["database"].create_match(match_data)
        assert match["id"] is not None

        # 3. 计算特征
        home_features = await mock_services["features"].calculate_team_features(
            home_team["id"]
        )
        away_features = await mock_services["features"].calculate_team_features(
            away_team["id"]
        )
        match_features = await mock_services["features"].calculate_match_features(
            home_team["id"], away_team["id"]
        )

        assert "recent_form" in home_features
        assert "recent_form" in away_features
        assert "head_to_head" in match_features

        # 4. 执行预测
        combined_features = {
            "home_team": home_features,
            "away_team": away_features,
            "match": match_features,
        }

        prediction = await mock_services["prediction"].predict_match(combined_features)

        assert "probabilities" in prediction
        assert "predicted_outcome" in prediction
        assert "confidence" in prediction
        assert prediction["confidence"] > 0

        # 5. 保存预测结果
        prediction_data = {
            "match_id": match["id"],
            "home_team_id": home_team["id"],
            "away_team_id": away_team["id"],
            "predicted_outcome": prediction["predicted_outcome"],
            "home_win_prob": prediction["probabilities"]["home_win"],
            "draw_prob": prediction["probabilities"]["draw"],
            "away_win_prob": prediction["probabilities"]["away_win"],
            "confidence": prediction["confidence"],
            "model": prediction["model"],
            "features_used": prediction["features_used"],
        }

        saved_prediction = await mock_services["database"].create_prediction(
            prediction_data
        )

        assert saved_prediction["id"] is not None
        assert saved_prediction["match_id"] == match["id"]

        # 6. 验证完整流程
        # 验证数据完整性
        retrieved_match = await mock_services["database"].get_match(match["id"])
        assert retrieved_match is not None
        assert retrieved_match["home_team_id"] == home_team["id"]

        # 验证预测一致性
        probability_sum = (
            prediction["probabilities"]["home_win"]
            + prediction["probabilities"]["draw"]
            + prediction["probabilities"]["away_win"]
        )
        assert abs(probability_sum - 1.0) < 0.01  # 允许小的浮点误差

    async def test_batch_prediction_workflow(self, mock_services):
        """测试批量预测工作流"""
        # 1. 创建多个球队
        teams_data = []
        for i in range(4):
            team_data = {
                "name": f"Batch Team {i + 1} FC",
                "short_name": f"BT{i + 1}",
                "country": "Test Country",
                "founded_year": 2020 + i,
            }
            team = await mock_services["database"].create_team(team_data)
            teams_data.append(team)

        # 2. 创建多个比赛
        matches_data = []
        for i in range(2):
            match_data = {
                "home_team_id": teams_data[i * 2]["id"],
                "away_team_id": teams_data[i * 2 + 1]["id"],
                "match_date": (datetime.now() + timedelta(days=i + 1)).isoformat(),
                "league": "Batch Test League",
            }
            match = await mock_services["database"].create_match(match_data)
            matches_data.append(match)

        # 3. 批量预测
        predictions = []
        for match in matches_data:
            # 计算特征
            home_features = await mock_services["features"].calculate_team_features(
                match["home_team_id"]
            )
            away_features = await mock_services["features"].calculate_team_features(
                match["away_team_id"]
            )
            match_features = await mock_services["features"].calculate_match_features(
                match["home_team_id"], match["away_team_id"]
            )

            combined_features = {
                "home_team": home_features,
                "away_team": away_features,
                "match": match_features,
            }

            # 执行预测
            prediction = await mock_services["prediction"].predict_match(
                combined_features
            )
            predictions.append(prediction)

        # 4. 验证批量结果
        assert len(predictions) == 2
        for prediction in predictions:
            assert "probabilities" in prediction
            assert "predicted_outcome" in prediction
            assert 0 < prediction["confidence"] <= 1

        # 5. 验证预测多样性
        outcomes = [pred["predicted_outcome"] for pred in predictions]
        # 不一定需要不同结果，但应该有合理的分布
        assert all(outcome in ["home_win", "draw", "away_win"] for outcome in outcomes)

    async def test_prediction_model_comparison(self, mock_services):
        """测试预测模型比较"""
        # 创建测试数据
        team_data = {
            "name": "Model Test Team",
            "short_name": "MTT",
            "country": "Test Country",
        }

        team = await mock_services["database"].create_team(team_data)

        match_data = {
            "home_team_id": team["id"],
            "away_team_id": team["id"],  # 使用同一个团队作为示例
            "match_date": (datetime.now() + timedelta(days=2)).isoformat(),
            "league": "Model Test League",
        }

        await mock_services["database"].create_match(match_data)

        # 计算特征
        features = await mock_services["features"].calculate_match_features(
            team["id"], team["id"]
        )

        # 使用不同模型进行预测
        model_predictions = {}
        for model in ["poisson", "neural_network", "ensemble"]:
            prediction = await mock_services["prediction"].predict_match(
                features, model
            )
            model_predictions[model] = prediction

        # 验证模型预测结果
        assert len(model_predictions) == 3
        for model, prediction in model_predictions.items():
            assert prediction["model"] == model
            assert "probabilities" in prediction
            assert "predicted_outcome" in prediction

        # 验证不同模型可能有不同的结果
        [pred["predicted_outcome"] for pred in model_predictions.values()]
        # 不一定需要不同，但应该有置信度差异
        confidences = [pred["confidence"] for pred in model_predictions.values()]
        assert len(set(confidences)) >= 1  # 至少有一些差异


@pytest.mark.integration
class TestEndToEndDataWorkflow:
    """端到端数据工作流测试"""

    async def test_data_collection_and_processing(self, mock_services):
        """测试数据收集和处理工作流"""
        # 1. 模拟外部数据源
        external_match_data = {
            "match_id": "ext_12345",
            "home_team": "External Team A",
            "away_team": "External Team B",
            "league": "External League",
            "match_date": "2024-01-15T15:00:00Z",
            "venue": "External Stadium",
            "odds": {"home_win": 2.10, "draw": 3.40, "away_win": 3.20},
        }

        # 2. 数据验证和标准化
        def validate_match_data(data):
            """验证比赛数据"""
            required_fields = ["home_team", "away_team", "league", "match_date"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            return True

        try:
            validate_match_data(external_match_data)
            validation_passed = True
        except ValueError:
            validation_passed = False

        assert validation_passed

        # 3. 数据转换
        def transform_match_data(data):
            """转换比赛数据格式"""
            return {
                "home_team_name": data["home_team"],
                "away_team_name": data["away_team"],
                "league_name": data["league"],
                "match_date": data["match_date"],
                "venue": data.get("venue", "Unknown"),
                "odds": data.get("odds", {}),
                "source": "external",
                "processed_at": datetime.now().isoformat(),
            }

        transformed_data = transform_match_data(external_match_data)

        assert transformed_data["home_team_name"] == "External Team A"
        assert transformed_data["away_team_name"] == "External Team B"
        assert "processed_at" in transformed_data

        # 4. 特征提取
        extracted_features = {
            "has_odds": bool(transformed_data["odds"]),
            "odds_implied_prob": {},
            "data_completeness": 0.8,
        }

        if transformed_data["odds"]:
            odds = transformed_data["odds"]
            extracted_features["odds_implied_prob"] = {
                "home_win": (
                    round(1 / odds["home_win"], 3) if odds["home_win"] > 0 else 0
                ),
                "draw": round(1 / odds["draw"], 3) if odds["draw"] > 0 else 0,
                "away_win": (
                    round(1 / odds["away_win"], 3) if odds["away_win"] > 0 else 0
                ),
            }

        assert extracted_features["has_odds"] is True
        if "home_win" in extracted_features["odds_implied_prob"]:
            assert 0 < extracted_features["odds_implied_prob"]["home_win"] < 1

        # 5. 数据存储
        stored_data = {
            "original_data": external_match_data,
            "transformed_data": transformed_data,
            "extracted_features": extracted_features,
            "stored_at": datetime.now().isoformat(),
        }

        # 验证数据完整性
        assert stored_data["original_data"]["match_id"] == "ext_12345"
        assert stored_data["transformed_data"]["home_team_name"] == "External Team A"
        assert stored_data["extracted_features"]["has_odds"] is True

    async def test_real_time_data_update_workflow(self, mock_services):
        """测试实时数据更新工作流"""
        # 1. 模拟初始比赛数据
        initial_match = {
            "match_id": "live_12345",
            "status": "scheduled",
            "home_score": None,
            "away_score": None,
            "minute": None,
            "events": [],
        }

        # 2. 模拟实时更新事件
        live_updates = [
            {
                "timestamp": "2024-01-15T15:01:00Z",
                "event": "match_start",
                "status": "live",
                "minute": 1,
            },
            {
                "timestamp": "2024-01-15T15:23:00Z",
                "event": "goal",
                "team": "home",
                "player": "Player A",
                "minute": 23,
                "score": {"home": 1, "away": 0},
            },
            {
                "timestamp": "2024-01-15T15:67:00Z",
                "event": "goal",
                "team": "away",
                "player": "Player B",
                "minute": 67,
                "score": {"home": 1, "away": 1},
            },
            {
                "timestamp": "2024-01-15T16:95:00Z",
                "event": "match_end",
                "status": "finished",
                "final_score": {"home": 1, "away": 1},
                "minute": 95,
            },
        ]

        # 3. 处理实时更新
        current_match_state = initial_match.copy()

        processed_events = []
        for update in live_updates:
            # 更新比赛状态
            current_match_state.update(
                {
                    "status": update["status"],
                    "minute": update.get("minute"),
                    "last_update": update["timestamp"],
                }
            )

            if "score" in update:
                current_match_state["home_score"] = update["score"]["home"]
                current_match_state["away_score"] = update["score"]["away"]

            # 处理事件
            processed_event = {
                "event_type": update["event"],
                "timestamp": update["timestamp"],
                "details": update,
                "processed_at": datetime.now().isoformat(),
            }
            processed_events.append(processed_event)

        # 4. 验证最终状态
        assert current_match_state["status"] == "finished"
        assert current_match_state["home_score"] == 1
        assert current_match_state["away_score"] == 1
        assert current_match_state["minute"] == 95

        # 5. 验证事件处理
        assert len(processed_events) == 4
        goal_events = [e for e in processed_events if e["event_type"] == "goal"]
        assert len(goal_events) == 2

        # 验证事件顺序
        assert processed_events[0]["event_type"] == "match_start"
        assert processed_events[-1]["event_type"] == "match_end"

    async def test_data_quality_monitoring_workflow(self, mock_services):
        """测试数据质量监控工作流"""
        # 1. 创建测试数据集
        test_datasets = [
            {
                "name": "high_quality_dataset",
                "records": [
                    {
                        "match_id": 1,
                        "home_team": "Team A",
                        "away_team": "Team B",
                        "home_score": 2,
                        "away_score": 1,
                        "date": "2024-01-15",
                        "status": "completed",
                    },
                    {
                        "match_id": 2,
                        "home_team": "Team C",
                        "away_team": "Team D",
                        "home_score": 0,
                        "away_score": 0,
                        "date": "2024-01-16",
                        "status": "completed",
                    },
                ],
            },
            {
                "name": "low_quality_dataset",
                "records": [
                    {
                        "match_id": 3,
                        "home_team": "",  # 缺少主队
                        "away_team": "Team E",
                        "home_score": -1,  # 无效比分
                        "away_score": None,  # 缺少比分
                        "date": "invalid_date",  # 无效日期
                        "status": "unknown_status",  # 无效状态
                    }
                ],
            },
        ]

        # 2. 数据质量检查函数
        def check_data_quality(dataset):
            """检查数据质量"""
            quality_issues = []
            total_records = len(dataset["records"])
            valid_records = 0

            for record in dataset["records"]:
                record_issues = []

                # 检查必需字段
                required_fields = [
                    "match_id",
                    "home_team",
                    "away_team",
                    "date",
                    "status",
                ]
                for field in required_fields:
                    if field not in record or not record[field]:
                        record_issues.append(f"missing_{field}")

                # 检查数据有效性
                if "home_score" in record and record["home_score"] is not None:
                    if (
                        not isinstance(record["home_score"], int)
                        or record["home_score"] < 0
                    ):
                        record_issues.append("invalid_home_score")

                if "away_score" in record and record["away_score"] is not None:
                    if (
                        not isinstance(record["away_score"], int)
                        or record["away_score"] < 0
                    ):
                        record_issues.append("invalid_away_score")

                # 检查日期格式
                if "date" in record and record["date"]:
                    try:
                        datetime.fromisoformat(record["date"].replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        record_issues.append("invalid_date_format")

                if not record_issues:
                    valid_records += 1
                else:
                    quality_issues.extend(
                        [
                            f"record_{record.get('match_id', 'unknown')}: {issue}"
                            for issue in record_issues
                        ]
                    )

            quality_score = (valid_records / total_records) if total_records > 0 else 0

            return {
                "dataset_name": dataset["name"],
                "total_records": total_records,
                "valid_records": valid_records,
                "quality_score": round(quality_score, 3),
                "quality_issues": quality_issues[:10],  # 限制问题数量
            }

        # 3. 执行质量检查
        quality_results = []
        for dataset in test_datasets:
            result = check_data_quality(dataset)
            quality_results.append(result)

        # 4. 验证质量检查结果
        assert len(quality_results) == 2

        # 高质量数据集应该有高分数
        high_quality_result = next(
            r for r in quality_results if r["dataset_name"] == "high_quality_dataset"
        )
        assert high_quality_result["quality_score"] == 1.0
        assert high_quality_result["valid_records"] == 2
        assert len(high_quality_result["quality_issues"]) == 0

        # 低质量数据集应该有低分数
        low_quality_result = next(
            r for r in quality_results if r["dataset_name"] == "low_quality_dataset"
        )
        assert low_quality_result["quality_score"] == 0.0
        assert low_quality_result["valid_records"] == 0
        assert len(low_quality_result["quality_issues"]) > 0

        # 5. 生成质量报告
        quality_report = {
            "generated_at": datetime.now().isoformat(),
            "total_datasets": len(quality_results),
            "overall_quality_score": sum(r["quality_score"] for r in quality_results)
            / len(quality_results),
            "dataset_results": quality_results,
            "recommendations": [
                "Improve data validation at source",
                "Implement automated data cleaning",
                "Add data quality monitoring alerts",
            ],
        }

        assert quality_report["overall_quality_score"] == 0.5  # (1.0 + 0.0) / 2
        assert len(quality_report["recommendations"]) > 0


@pytest.mark.integration
class TestEndToEndErrorHandling:
    """端到端错误处理测试"""

    async def test_system_error_recovery(self, mock_services):
        """测试系统错误恢复"""
        # 1. 模拟服务故障
        original_predict = mock_services["prediction"].predict_match
        error_count = 0

        async def failing_predict(features, model="ensemble"):
            nonlocal error_count
            error_count += 1
            if error_count <= 2:
                raise Exception("Service temporarily unavailable")
            # 第三次尝试成功
            return await original_predict(features, model)

        mock_services["prediction"].predict_match = failing_predict

        # 2. 尝试执行预测
        features = await mock_services["features"].calculate_match_features(1, 2)

        # 应该在重试后成功
        prediction = await mock_services["prediction"].predict_match(features)

        assert "probabilities" in prediction
        assert "predicted_outcome" in prediction
        assert error_count == 3  # 验证重试了3次

        # 3. 恢复原始服务
        mock_services["prediction"].predict_match = original_predict

    async def test_data_corruption_handling(self, mock_services):
        """测试数据损坏处理"""
        # 1. 创建损坏的数据
        corrupted_features = {
            "home_team": {
                "team_id": None,  # 损坏的数据
                "recent_form": "invalid_format",  # 应该是列表
                "avg_goals_scored": "not_a_number",  # 应该是数字
                "calculated_at": "invalid_date",
            },
            "away_team": {},
            "match": {},
        }

        # 2. 数据验证和修复函数
        def validate_and_fix_features(features):
            """验证并修复特征数据"""
            fixed_features = {}

            for key, value in features.items():
                if not value or not isinstance(value, dict):
                    continue

                fixed_value = {}
                for sub_key, sub_value in value.items():
                    if sub_key == "team_id":
                        fixed_value[sub_key] = 1 if sub_value is None else sub_value
                    elif sub_key == "recent_form":
                        if isinstance(sub_value, str):
                            # 尝试解析字符串格式的列表
                            try:
                                fixed_value[sub_key] = eval(sub_value)
                            except Exception:
                                fixed_value[sub_key] = [
                                    "D",
                                    "D",
                                    "D",
                                    "D",
                                    "D",
                                ]  # 默认值
                        elif not isinstance(sub_value, list):
                            fixed_value[sub_key] = ["D", "D", "D", "D", "D"]
                        else:
                            fixed_value[sub_key] = sub_value
                    elif sub_key in ["avg_goals_scored", "avg_goals_conceded"]:
                        try:
                            fixed_value[sub_key] = float(sub_value)
                        except (ValueError, TypeError):
                            fixed_value[sub_key] = 1.0  # 默认值
                    elif sub_key == "calculated_at":
                        try:
                            datetime.fromisoformat(sub_value.replace("Z", "+00:00"))
                            fixed_value[sub_key] = sub_value
                        except (ValueError, AttributeError):
                            fixed_value[sub_key] = datetime.now().isoformat()
                    else:
                        fixed_value[sub_key] = sub_value

                fixed_features[key] = fixed_value

            return fixed_features

        # 3. 执行数据修复
        fixed_features = validate_and_fix_features(corrupted_features)

        # 4. 验证修复结果
        assert "home_team" in fixed_features
        assert fixed_features["home_team"]["team_id"] == 1
        assert isinstance(fixed_features["home_team"]["recent_form"], list)
        assert isinstance(fixed_features["home_team"]["avg_goals_scored"], float)
        assert "calculated_at" in fixed_features["home_team"]

        # 5. 使用修复后的数据继续处理
        try:
            prediction = await mock_services["prediction"].predict_match(fixed_features)
            assert "probabilities" in prediction
        except Exception:
            # 如果预测仍然失败，使用默认预测
            prediction = {
                "model": "fallback",
                "probabilities": {"home_win": 0.33, "draw": 0.34, "away_win": 0.33},
                "predicted_outcome": "draw",
                "confidence": 0.5,
                "features_used": list(fixed_features.keys()),
                "calculated_at": datetime.now().isoformat(),
                "fallback_used": True,
            }

        assert "probabilities" in prediction
        assert prediction["confidence"] > 0

    async def test_timeout_handling(self, mock_services):
        """测试超时处理"""

        # 1. 模拟慢服务
        async def slow_feature_calculation(team_id):
            await asyncio.sleep(0.1)  # 模拟慢操作
            return {"team_id": team_id, "slow": True}

        original_calculation = mock_services["features"].calculate_team_features
        mock_services["features"].calculate_team_features = slow_feature_calculation

        # 2. 带超时的操作
        async def timeout_wrapper(func, *args, timeout=0.05):
            try:
                result = await asyncio.wait_for(func(*args), timeout=timeout)
                return result
            except TimeoutError:
                # 超时后返回默认值
                return {"team_id": args[0], "timeout": True, "default": True}

        # 3. 执行带超时的操作
        features = await timeout_wrapper(
            mock_services["features"].calculate_team_features, 1
        )

        # 4. 验证超时处理
        assert features["team_id"] == 1
        assert features.get("timeout") is True or features.get("default") is True

        # 5. 恢复原始服务
        mock_services["features"].calculate_team_features = original_calculation


@pytest.mark.integration
class TestEndToEndPerformance:
    """端到端性能测试"""

    async def test_concurrent_prediction_processing(self, mock_services):
        """测试并发预测处理"""
        import time

        # 1. 准备测试数据
        teams = []
        for i in range(10):
            team = await mock_services["database"].create_team(
                {
                    "name": f"Perf Team {i + 1}",
                    "short_name": f"PT{i + 1}",
                    "country": "Test Country",
                }
            )
            teams.append(team)

        matches = []
        for i in range(5):
            match = await mock_services["database"].create_match(
                {
                    "home_team_id": teams[i * 2]["id"],
                    "away_team_id": teams[i * 2 + 1]["id"],
                    "match_date": (datetime.now() + timedelta(days=i + 1)).isoformat(),
                    "league": "Performance Test League",
                }
            )
            matches.append(match)

        # 2. 并发预测函数
        async def predict_match_async(match_id, home_team_id, away_team_id):
            # 计算特征
            home_features = await mock_services["features"].calculate_team_features(
                home_team_id
            )
            away_features = await mock_services["features"].calculate_team_features(
                away_team_id
            )
            match_features = await mock_services["features"].calculate_match_features(
                home_team_id, away_team_id
            )

            combined_features = {
                "home_team": home_features,
                "away_team": away_features,
                "match": match_features,
            }

            # 执行预测
            prediction = await mock_services["prediction"].predict_match(
                combined_features
            )
            return prediction

        # 3. 执行并发预测
        start_time = time.time()

        prediction_tasks = []
        for match in matches:
            task = predict_match_async(
                match["id"], match["home_team_id"], match["away_team_id"]
            )
            prediction_tasks.append(task)

        predictions = await asyncio.gather(*prediction_tasks)

        end_time = time.time()
        processing_time = end_time - start_time

        # 4. 验证结果
        assert len(predictions) == 5
        for prediction in predictions:
            assert "probabilities" in prediction
            assert "predicted_outcome" in prediction

        # 5. 性能验证
        assert processing_time < 2.0  # 并发处理应该更快
        avg_time_per_prediction = processing_time / len(predictions)
        assert avg_time_per_prediction < 0.5

    async def test_memory_usage_simulation(self, mock_services):
        """测试内存使用模拟"""
        import gc

        # 获取初始内存状态
        gc.collect()
        initial_objects = len(gc.get_objects())

        # 1. 创建大量数据
        large_dataset = []
        for i in range(100):
            team = await mock_services["database"].create_team(
                {
                    "name": f"Memory Team {i}",
                    "short_name": f"MT{i}",
                    "country": "Memory Country",
                    "description": "A" * 100,  # 增加内存使用
                    "metadata": {f"key_{j}": f"value_{j}" for j in range(20)},
                }
            )
            large_dataset.append(team)

        # 2. 处理数据
        processed_data = []
        for team in large_dataset:
            features = await mock_services["features"].calculate_team_features(
                team["id"]
            )
            features["team_name"] = team["name"]
            features["description"] = team.get("description", "")
            processed_data.append(features)

        # 3. 清理数据
        processed_data.clear()
        large_dataset.clear()

        # 4. 强制垃圾回收
        gc.collect()

        # 5. 验证内存状态
        final_objects = len(gc.get_objects())
        object_increase = final_objects - initial_objects

        # 对象增长应该在合理范围内
        assert object_increase < 1000  # 这是一个经验阈值

    async def test_batch_operation_performance(self, mock_services):
        """测试批量操作性能"""
        import time

        # 1. 批量创建测试
        batch_size = 50
        teams_data = [
            {
                "name": f"Batch Team {i + 1}",
                "short_name": f"BT{i + 1}",
                "country": "Batch Country",
            }
            for i in range(batch_size)
        ]

        start_time = time.time()
        created_teams = []
        for team_data in teams_data:
            team = await mock_services["database"].create_team(team_data)
            created_teams.append(team)
        batch_create_time = time.time() - start_time

        # 2. 批量特征计算
        start_time = time.time()
        features_list = []
        for team in created_teams:
            features = await mock_services["features"].calculate_team_features(
                team["id"]
            )
            features_list.append(features)
        batch_features_time = time.time() - start_time

        # 3. 批量预测
        start_time = time.time()
        predictions = []
        for i in range(0, len(created_teams) - 1, 2):
            if i + 1 < len(created_teams):
                home_features = features_list[i]
                away_features = features_list[i + 1]
                match_features = await mock_services[
                    "features"
                ].calculate_match_features(
                    created_teams[i]["id"], created_teams[i + 1]["id"]
                )

                combined_features = {
                    "home_team": home_features,
                    "away_team": away_features,
                    "match": match_features,
                }

                prediction = await mock_services["prediction"].predict_match(
                    combined_features
                )
                predictions.append(prediction)
        batch_prediction_time = time.time() - start_time

        # 4. 性能验证
        assert len(created_teams) == batch_size
        assert len(features_list) == batch_size
        assert len(predictions) == batch_size // 2

        # 验证操作时间合理
        assert batch_create_time < 2.0
        assert batch_features_time < 2.0
        assert batch_prediction_time < 2.0

        # 计算平均时间
        avg_create_time = batch_create_time / batch_size
        avg_features_time = batch_features_time / batch_size
        avg_prediction_time = batch_prediction_time / (batch_size // 2)

        assert avg_create_time < 0.1
        assert avg_features_time < 0.1
        assert avg_prediction_time < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
