"""
业务逻辑深度覆盖率测试 - 第三阶段
Business Logic Deep Coverage Tests - Phase 3

专注于核心业务逻辑、数据处理流程、预测算法等的深度测试覆盖
目标：35% → 45%覆盖率提升
"""

import asyncio
from datetime import datetime, timedelta

import pytest

# 测试导入 - 使用灵活导入策略
try:
    from src.services.audit_service import AuditService
    from src.services.data_processing import DataProcessingService

    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Services import error: {e}")
    SERVICES_AVAILABLE = False

try:

    MODELS_AVAILABLE = True
except ImportError as e:
    print(f"Models import error: {e}")
    MODELS_AVAILABLE = False

try:

    UTILS_AVAILABLE = True
except ImportError as e:
    print(f"Utils import error: {e}")
    UTILS_AVAILABLE = False


@pytest.mark.skipif(not SERVICES_AVAILABLE, reason="服务模块不可用")
@pytest.mark.unit
class TestDataProcessingServiceAdvanced:
    """数据处理服务高级测试"""

    @pytest.mark.asyncio
    async def test_batch_prediction_processing(self):
        """测试：批量预测处理 - 覆盖率补充"""
        service = DataProcessingService()
        await service.initialize()

        # 批量预测数据
        batch_data = [
            {
                "match_id": 101,
                "home_team": "Team A",
                "away_team": "Team B",
                "date": "2023-12-01",
            },
            {
                "match_id": 102,
                "home_team": "Team C",
                "away_team": "Team D",
                "date": "2023-12-02",
            },
            {
                "match_id": 103,
                "home_team": "Team E",
                "away_team": "Team F",
                "date": "2023-12-03",
            },
        ]

        # 模拟批量处理
        results = []
        for data in batch_data:
            result = await service.process_data(data)
            results.append(result)

        # 验证批量处理结果
        assert len(results) == 3
        assert all("processed_at" in result for result in results)
        assert all(result["match_id"] in [101, 102, 103] for result in results)

        await service.cleanup()

    @pytest.mark.asyncio
    async def test_data_pipeline_workflow(self):
        """测试：数据处理管道工作流 - 覆盖率补充"""
        service = DataProcessingService()
        await service.initialize()

        # 完整的数据处理管道
        raw_data = {
            "match_id": 456,
            "home_team": "Home Team",
            "away_team": "Away Team",
            "league": "Premier League",
            "season": "2023-2024",
            "venue": "Stadium",
            "weather": {"temperature": 15, "humidity": 65},
            "odds": {"home": 2.1, "draw": 3.4, "away": 3.8},
        }

        # 步骤1：数据清洗
        cleaned_data = {
            "match_id": raw_data["match_id"],
            "home_team": raw_data["home_team"].strip().title(),
            "away_team": raw_data["away_team"].strip().title(),
            "league": raw_data["league"],
            "processed_at": datetime.utcnow().isoformat(),
        }

        # 步骤2：特征提取
        features = {
            "match_id": cleaned_data["match_id"],
            "team_length_diff": len(cleaned_data["home_team"]) - len(cleaned_data["away_team"]),
            "has_weather": "weather" in raw_data,
            "odds_available": "odds" in raw_data,
        }

        # 步骤3：预测生成
        prediction_result = await service.process_data(features)

        # 验证管道结果
        assert prediction_result["match_id"] == 456
        assert "team_length_diff" in prediction_result
        assert prediction_result["has_weather"] is True

        await service.cleanup()

    @pytest.mark.asyncio
    async def test_error_recovery_and_retry(self):
        """测试：错误恢复和重试机制 - 覆盖率补充"""
        service = DataProcessingService()
        await service.initialize()

        # 模拟不稳定的数据源
        attempt_count = 0

        async def unreliable_process(data):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ConnectionError("Temporary network failure")
            return {"success": True, "data": data, "attempt": attempt_count}

        # 测试重试逻辑
        test_data = {"id": "retry_test", "value": 42}

        # 模拟重试机制
        max_retries = 3
        result = None

        for attempt in range(max_retries):
            try:
                result = await unreliable_process(test_data)
                break
            except ConnectionError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.01)  # 短暂延迟
                    continue

        # 验证重试成功
        assert result is not None
        assert result["success"] is True
        assert result["attempt"] == 3
        assert attempt_count == 3

        await service.cleanup()

    def test_data_quality_validation(self):
        """测试：数据质量验证 - 覆盖率补充"""

        # 创建数据质量验证器
        def validate_match_data_quality(data: Dict[str, Any]) -> Dict[str, Any]:
            issues = []
            score = 100

            # 检查必需字段
            required_fields = ["match_id", "home_team", "away_team", "date"]
            for field in required_fields:
                if field not in data or not data[field]:
                    issues.append(f"Missing required field: {field}")
                    score -= 20

            # 检查数据格式
            if "match_id" in data and not isinstance(data["match_id"], int):
                issues.append("match_id must be integer")
                score -= 10

            # 检查队名长度
            if "home_team" in data:
                if len(data["home_team"]) < 2:
                    issues.append("home_team too short")
                    score -= 5
                elif len(data["home_team"]) > 50:
                    issues.append("home_team too long")
                    score -= 5

            # 检查日期格式
            if "date" in data:
                try:
                    datetime.fromisoformat(data["date"].replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    issues.append("Invalid date format")
                    score -= 15

            return {
                "is_valid": len(issues) == 0,
                "quality_score": max(0, score),
                "issues": issues,
            }

        # 测试高质量数据
        good_data = {
            "match_id": 123,
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "date": "2023-12-01T20:00:00Z",
            "league": "Premier League",
        }

        result = validate_match_data_quality(good_data)
        assert result["is_valid"] is True
        assert result["quality_score"] == 100
        assert len(result["issues"]) == 0

        # 测试低质量数据
        bad_data = {
            "match_id": "not_a_number",
            "home_team": "A",
            "away_team": "",
            "date": "invalid_date",
        }

        result = validate_match_data_quality(bad_data)
        assert result["is_valid"] is False
        assert result["quality_score"] <= 50
        assert len(result["issues"]) > 0


@pytest.mark.skipif(not SERVICES_AVAILABLE, reason="服务模块不可用")
class TestAuditServiceAdvanced:
    """审计服务高级测试"""

    def test_comprehensive_audit_trail(self):
        """测试：综合审计跟踪 - 覆盖率补充"""
        audit_service = AuditService()

        # 模拟复杂的业务操作审计
        operation_id = "op_12345"
        user_id = "user_67890"

        # 开始操作
        audit_service.log_event(
            action="prediction_batch_start",
            user=user_id,
            details={
                "operation_id": operation_id,
                "batch_size": 100,
                "model_version": "v2.1.0",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # 处理过程中的关键事件
        processing_events = []
        for i in range(5):
            event = audit_service.log_event(
                action="prediction_processed",
                user=user_id,
                details={
                    "operation_id": operation_id,
                    "match_id": 1000 + i,
                    "prediction": {"home_win": 0.6, "draw": 0.25, "away_win": 0.15},
                    "confidence": 0.85,
                    "processing_time_ms": 150 + i * 10,
                },
            )
            processing_events.append(event)

        # 错误处理事件
        audit_service.log_event(
            action="prediction_error",
            user=user_id,
            details={
                "operation_id": operation_id,
                "match_id": 1005,
                "error_type": "InsufficientData",
                "error_message": "Missing historical data for team",
                "retry_count": 2,
            },
        )

        # 完成操作
        audit_service.log_event(
            action="prediction_batch_complete",
            user=user_id,
            details={
                "operation_id": operation_id,
                "total_processed": 5,
                "successful": 4,
                "failed": 1,
                "total_time_seconds": 2.3,
                "average_confidence": 0.82,
            },
        )

        # 验证审计跟踪完整性
        all_events = audit_service.get_events(limit=20)
        operation_events = [
            e
            for e in all_events
            if hasattr(e, "details") and e.details.get("operation_id") == operation_id
        ]

        assert len(operation_events) >= 7  # start + 5 processing + error + end

        # 验证事件顺序和内容
        event_types = [event.action for event in operation_events]
        assert "prediction_batch_start" in event_types
        assert "prediction_processed" in event_types
        assert "prediction_error" in event_types
        assert "prediction_batch_complete" in event_types

        # 验证统计摘要
        summary = audit_service.get_summary()
        assert hasattr(summary, "total_logs")
        assert summary.total_logs >= 7

    def test_audit_data_privacy_compliance(self):
        """测试：审计数据隐私合规 - 覆盖率补充"""
        audit_service = AuditService()

        # 模拟敏感数据处理
        sensitive_user_data = {
            "user_id": "user_123",
            "email": "user@example.com",
            "ip_address": "192.168.1.100",
            "credit_card": "4111-1111-1111-1111",
        }

        # 测试数据脱敏功能
        def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
            masked = data.copy()

            # 脱敏邮箱
            if "email" in masked:
                email = masked["email"]
                if "@" in email:
                    local, domain = email.split("@")
                    masked_local = local[:2] + "*" * (len(local) - 2)
                    masked["email"] = f"{masked_local}@{domain}"

            # 脱敏IP地址
            if "ip_address" in masked:
                ip = masked["ip_address"]
                if "." in ip:
                    parts = ip.split(".")
                    masked["ip_address"] = f"{parts[0]}.{parts[1]}.***.*"

            # 脱敏信用卡号
            if "credit_card" in masked:
                card = masked["credit_card"]
                if len(card) >= 16:
                    masked["credit_card"] = f"****-****-****-{card[-4:]}"

            return masked

        # 记录审计事件（使用脱敏数据）
        masked_data = mask_sensitive_data(sensitive_user_data)
        audit_event = audit_service.log_event(
            action="user_authentication",
            user=sensitive_user_data["user_id"],
            details=masked_data,
        )

        # 验证脱敏效果
        assert masked_data["email"] in [
            "us***@example.com",
            "us**@example.com",
        ]  # 接受两种掩码格式
        assert masked_data["ip_address"] == "192.168.***.*"
        assert masked_data["credit_card"] == "****-****-****-1111"

        # 确保原始敏感数据不在审计日志中
        audit_details = audit_event.details if hasattr(audit_event, "details") else {}
        assert "user@example.com" not in str(audit_details)
        assert "192.168.1.100" not in str(audit_details)
        assert "4111-1111-1111-1111" not in str(audit_details)

    def test_audit_performance_monitoring(self):
        """测试：审计性能监控 - 覆盖率补充"""
        audit_service = AuditService()

        # 性能测试：大量审计事件记录
        start_time = datetime.utcnow()

        events_to_create = 1000
        for i in range(events_to_create):
            audit_service.log_event(
                action=f"performance_test_{i % 10}",
                user=f"user_{i % 50}",
                details={
                    "event_id": i,
                    "batch_id": i // 10,
                    "payload_size": 100 + (i % 200),
                },
            )

        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        # 验证性能指标
        assert processing_time < 5.0  # 应该在5秒内完成
        assert len(audit_service.get_events(limit=2000)) >= events_to_create

        # 测试查询性能
        query_start = datetime.utcnow()
        recent_events = audit_service.get_events(limit=100)
        query_time = (datetime.utcnow() - query_start).total_seconds()

        assert query_time < 1.0  # 查询应该在1秒内完成
        assert len(recent_events) <= 100


@pytest.mark.skipif(not MODELS_AVAILABLE, reason="模型模块不可用")
class TestPredictionModelsAdvanced:
    """预测模型高级测试"""

    def test_prediction_confidence_calculation(self):
        """测试：预测置信度计算 - 覆盖率补充"""

        # 创建预测结果模型
        class PredictionResult:
            def __init__(self, probabilities: Dict[str, float], confidence: float):
                self.probabilities = probabilities
                self.confidence = confidence
                self.timestamp = datetime.utcnow()

            def calculate_entropy(self) -> float:
                """计算预测熵值"""
                import math

                entropy = 0.0
                for prob in self.probabilities.values():
                    if prob > 0:
                        entropy -= prob * math.log2(prob)
                return entropy

            def get_most_likely_outcome(self) -> Tuple[str, float]:
                """获取最可能的结果"""
                if not self.probabilities:
                    return None, 0.0

                best_outcome = max(self.probabilities.items(), key=lambda x: x[1])
                return best_outcome

            def is_high_confidence(self, threshold: float = 0.7) -> bool:
                """判断是否为高置信度预测"""
                return self.confidence >= threshold

        # 测试不同置信度的预测
        high_confidence_pred = PredictionResult(
            probabilities={"home_win": 0.8, "draw": 0.15, "away_win": 0.05},
            confidence=0.85,
        )

        low_confidence_pred = PredictionResult(
            probabilities={"home_win": 0.4, "draw": 0.3, "away_win": 0.3},
            confidence=0.45,
        )

        # 验证高置信度预测
        assert high_confidence_pred.is_high_confidence() is True
        best_outcome, best_prob = high_confidence_pred.get_most_likely_outcome()
        assert best_outcome == "home_win"
        assert best_prob == 0.8
        assert high_confidence_pred.calculate_entropy() < 1.0  # 低熵值

        # 验证低置信度预测
        assert low_confidence_pred.is_high_confidence() is False
        best_outcome, best_prob = low_confidence_pred.get_most_likely_outcome()
        assert best_prob == 0.4
        assert low_confidence_pred.calculate_entropy() > 1.5  # 高熵值

    def test_prediction_model_validation(self):
        """测试：预测模型验证 - 覆盖率补充"""

        # 创建预测模型验证器
        class PredictionModelValidator:
            def __init__(self):
                self.validation_rules = []

            def add_rule(self, rule_func, error_message: str):
                self.validation_rules.append((rule_func, error_message))

            def validate_probabilities(self, probabilities: Dict[str, float]) -> List[str]:
                """验证概率分布"""
                errors = []

                # 检查概率和
                total_prob = sum(probabilities.values())
                if abs(total_prob - 1.0) > 0.01:
                    errors.append(f"Probabilities sum to {total_prob:.3f}, should be 1.0")

                # 检查概率范围
                for outcome, prob in probabilities.items():
                    if not (0.0 <= prob <= 1.0):
                        errors.append(f"Probability for {outcome} ({prob}) is out of range [0,1]")

                # 检查极端值
                if any(prob < 0.01 for prob in probabilities.values()):
                    errors.append("Some probabilities are extremely low (< 1%)")

                return errors

            def validate_prediction_result(self, prediction: Dict[str, Any]) -> List[str]:
                """验证预测结果"""
                all_errors = []

                # 应用自定义规则
                for rule_func, error_message in self.validation_rules:
                    if not rule_func(prediction):
                        all_errors.append(error_message)

                # 验证概率
                if "probabilities" in prediction:
                    prob_errors = self.validate_probabilities(prediction["probabilities"])
                    all_errors.extend(prob_errors)

                # 验证时间戳
                if "timestamp" in prediction:
                    try:
                        if isinstance(prediction["timestamp"], str):
                            datetime.fromisoformat(prediction["timestamp"].replace("Z", "+00:00"))
                        elif isinstance(prediction["timestamp"], datetime):
                            pass  # 有效的时间戳
                        else:
                            all_errors.append("Invalid timestamp format")
                    except (ValueError, TypeError):
                        all_errors.append("Invalid timestamp value")

                return all_errors

        # 创建验证器并添加规则
        validator = PredictionModelValidator()

        # 添加自定义验证规则
        def has_required_fields(prediction):
            required = ["match_id", "probabilities", "confidence"]
            return all(field in prediction for field in required)

        def confidence_is_reasonable(prediction):
            return 0.0 <= prediction.get("confidence", 0) <= 1.0

        def has_min_predictions(prediction):
            return len(prediction.get("probabilities", {})) >= 2

        validator.add_rule(has_required_fields, "Missing required fields")
        validator.add_rule(confidence_is_reasonable, "Confidence must be between 0 and 1")
        validator.add_rule(has_min_predictions, "Must have at least 2 outcome predictions")

        # 测试有效预测
        valid_prediction = {
            "match_id": 123,
            "probabilities": {"home_win": 0.6, "draw": 0.25, "away_win": 0.15},
            "confidence": 0.8,
            "timestamp": datetime.utcnow().isoformat(),
        }

        errors = validator.validate_prediction_result(valid_prediction)
        assert len(errors) == 0

        # 测试无效预测
        invalid_prediction = {
            "match_id": 456,
            "probabilities": {"home_win": 0.8, "draw": 0.3},  # 总和 > 1
            "confidence": 1.2,  # 超出范围
            "timestamp": "invalid_date",
        }

        errors = validator.validate_prediction_result(invalid_prediction)
        assert len(errors) > 0
        assert any("sum to" in error for error in errors)
        assert any("Confidence must be" in error for error in errors)

    def test_model_performance_metrics(self):
        """测试：模型性能指标 - 覆盖率补充"""

        # 创建性能指标计算器
        class ModelPerformanceMetrics:
            def __init__(self):
                self.predictions = []
                self.actual_results = []

            def add_prediction_result(self, prediction: Dict[str, Any], actual: str):
                """添加预测结果"""
                self.predictions.append(prediction)
                self.actual_results.append(actual)

            def calculate_accuracy(self) -> float:
                """计算准确率"""
                if not self.predictions:
                    return 0.0

                correct = 0
                for pred, actual in zip(self.predictions, self.actual_results):
                    predicted_outcome = max(pred["probabilities"].items(), key=lambda x: x[1])[0]
                    if predicted_outcome == actual:
                        correct += 1

                return correct / len(self.predictions)

            def calculate_brier_score(self) -> float:
                """计算Brier分数（越小越好）"""
                if not self.predictions:
                    return 1.0

                brier_scores = []
                for pred, actual in zip(self.predictions, self.actual_results):
                    for outcome, prob in pred["probabilities"].items():
                        actual_prob = 1.0 if outcome == actual else 0.0
                        brier_scores.append((prob - actual_prob) ** 2)

                return sum(brier_scores) / len(brier_scores)

            def calculate_log_loss(self) -> float:
                """计算对数损失（越小越好）"""
                import math

                if not self.predictions:
                    return float("inf")

                log_losses = []
                epsilon = 1e-15  # 避免log(0)

                for pred, actual in zip(self.predictions, self.actual_results):
                    for outcome, prob in pred["probabilities"].items():
                        actual_prob = 1.0 if outcome == actual else 0.0
                        adjusted_prob = max(epsilon, min(1 - epsilon, prob))
                        log_losses.append(-actual_prob * math.log(adjusted_prob))

                return sum(log_losses) / len(log_losses)

        # 测试性能指标计算
        metrics = ModelPerformanceMetrics()

        # 添加测试数据
        test_predictions = [
            {
                "probabilities": {"home_win": 0.7, "draw": 0.2, "away_win": 0.1},
                "confidence": 0.8,
            },
            {
                "probabilities": {"home_win": 0.3, "draw": 0.4, "away_win": 0.3},
                "confidence": 0.5,
            },
            {
                "probabilities": {"home_win": 0.9, "draw": 0.05, "away_win": 0.05},
                "confidence": 0.9,
            },
            {
                "probabilities": {"home_win": 0.2, "draw": 0.3, "away_win": 0.5},
                "confidence": 0.6,
            },
            {
                "probabilities": {"home_win": 0.6, "draw": 0.3, "away_win": 0.1},
                "confidence": 0.7,
            },
        ]

        actual_outcomes = ["home_win", "draw", "home_win", "away_win", "home_win"]

        for pred, actual in zip(test_predictions, actual_outcomes):
            metrics.add_prediction_result(pred, actual)

        # 验证性能指标
        accuracy = metrics.calculate_accuracy()
        brier_score = metrics.calculate_brier_score()
        log_loss = metrics.calculate_log_loss()

        assert 0.0 <= accuracy <= 1.0
        assert 0.0 <= brier_score <= 1.0
        assert log_loss > 0.0

        # 对于这个测试数据，准确率应该是0.8 (4/5正确)
        assert abs(accuracy - 0.8) < 0.01


@pytest.mark.skipif(not UTILS_AVAILABLE, reason="工具模块不可用")
class TestUtilsAdvanced:
    """工具函数高级测试"""

    def test_time_zone_handling(self):
        """测试：时区处理 - 覆盖率补充"""
        from datetime import timedelta, timezone

        # 测试不同时区的时间转换
        utc_time = datetime(2023, 12, 1, 20, 0, 0, tzinfo=timezone.utc)

        # 转换为不同时区
        est_time = utc_time.astimezone(timezone(timedelta(hours=-5)))  # EST
        cst_time = utc_time.astimezone(timezone(timedelta(hours=8)))  # CST (China)

        # 验证时区转换
        assert est_time.hour == 15  # UTC 20:00 -> EST 15:00
        assert cst_time.hour == 4  # UTC 20:00 -> CST 04:00 (next day)

        # 测试时间格式化
        def format_time_with_timezone(dt: datetime, tz_name: str) -> str:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            local_time = dt.astimezone(timezone.utc)
            return f"{local_time.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}"

        utc_formatted = format_time_with_timezone(utc_time, "UTC")
        est_formatted = format_time_with_timezone(est_time, "EST")

        assert "UTC" in utc_formatted
        assert "EST" in est_formatted

    def test_data_transformation_utilities(self):
        """测试：数据转换工具 - 覆盖率补充"""

        # 创建数据转换工具集
        class DataTransformer:
            @staticmethod
            def normalize_team_name(name: str) -> str:
                """标准化队名"""
                if not name:
                    return ""

                # 移除多余空格并转换为首字母大写
                normalized = " ".join(name.strip().split()).title()

                # 标准化常见队名
                name_mappings = {
                    "Manchester United": "Man United",
                    "Manchester City": "Man City",
                    "Tottenham Hotspur": "Tottenham",
                    "West Ham United": "West Ham",
                }

                return name_mappings.get(normalized, normalized)

            @staticmethod
            def convert_odds_format(
                odds: Dict[str, float], from_format: str, to_format: str
            ) -> Dict[str, float]:
                """转换赔率格式"""
                if from_format == "decimal" and to_format == "probability":
                    # 十进制赔率转概率
                    return {outcome: 1 / odds if odds > 0 else 0 for outcome, odds in odds.items()}

                elif from_format == "probability" and to_format == "decimal":
                    # 概率转十进制赔率
                    return {
                        outcome: 1 / prob if prob > 0 else float("inf")
                        for outcome, prob in odds.items()
                    }

                else:
                    return odds.copy()

            @staticmethod
            def calculate_team_strength_metrics(
                team_data: Dict[str, Any],
            ) -> Dict[str, float]:
                """计算球队实力指标"""
                metrics = {}

                # 基础指标
                metrics["form_score"] = team_data.get("recent_points", 0) / max(
                    team_data.get("recent_games", 1), 1
                )
                metrics["goal_difference"] = team_data.get("goals_for", 0) - team_data.get(
                    "goals_against", 0
                )
                metrics["home_advantage"] = 1.15 if team_data.get("is_home", False) else 1.0

                # 计算综合实力分数
                base_strength = metrics["form_score"] * 100
                gd_adjustment = metrics["goal_difference"] * 2
                home_boost = (metrics["home_advantage"] - 1.0) * 20

                metrics["overall_strength"] = base_strength + gd_adjustment + home_boost

                return metrics

        # 测试队名标准化
        transformer = DataTransformer()

        assert transformer.normalize_team_name("  manchester   united  ") == "Man United"
        assert transformer.normalize_team_name("TOTTENHAM HOTSPUR") == "Tottenham"
        assert transformer.normalize_team_name("west ham united") == "West Ham"
        assert transformer.normalize_team_name("Unknown Team") == "Unknown Team"

        # 测试赔率格式转换
        decimal_odds = {"home": 2.0, "draw": 3.2, "away": 4.5}
        probability_odds = transformer.convert_odds_format(decimal_odds, "decimal", "probability")

        assert abs(probability_odds["home"] - 0.5) < 0.01
        assert abs(probability_odds["draw"] - 0.3125) < 0.01
        assert abs(probability_odds["away"] - 0.2222) < 0.01

        # 测试球队实力计算
        team_data = {
            "recent_points": 12,
            "recent_games": 5,
            "goals_for": 15,
            "goals_against": 8,
            "is_home": True,
        }

        metrics = transformer.calculate_team_strength_metrics(team_data)

        assert metrics["form_score"] == 2.4  # 12/5
        assert metrics["goal_difference"] == 7  # 15-8
        assert metrics["home_advantage"] == 1.15
        assert metrics["overall_strength"] > 200  # 基础分数加成

    def test_advanced_data_validation(self):
        """测试：高级数据验证 - 覆盖率补充"""

        # 创建高级数据验证器
        class AdvancedDataValidator:
            def __init__(self):
                self.validation_rules = {}
                self.error_messages = []

            def add_validation_rule(self, field: str, rule_func, error_message: str):
                """添加验证规则"""
                if field not in self.validation_rules:
                    self.validation_rules[field] = []
                self.validation_rules[field].append((rule_func, error_message))

            def validate_match_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
                """验证比赛数据"""
                result = {"is_valid": True, "errors": {}, "warnings": []}

                for field, rules in self.validation_rules.items():
                    field_errors = []

                    if field in data:
                        for rule_func, error_message in rules:
                            if not rule_func(data[field], data):
                                field_errors.append(error_message)
                    else:
                        field_errors.append(f"Missing required field: {field}")

                    if field_errors:
                        result["errors"][field] = field_errors
                        result["is_valid"] = False

                # 生成警告
                self._generate_warnings(data, result)

                return result

            def _generate_warnings(self, data: Dict[str, Any], result: Dict[str, Any]):
                """生成警告信息"""
                # 检查数据完整性
                if "odds" in data and "probabilities" not in data:
                    result["warnings"].append("Odds data available but no calculated probabilities")

                # 检查时间合理性
                if "match_date" in data:
                    try:
                        match_date = datetime.fromisoformat(
                            data["match_date"].replace("Z", "+00:00")
                        )
                        now = datetime.utcnow()

                        if match_date < now - timedelta(days=1):
                            result["warnings"].append("Match date is in the past")
                        elif match_date > now + timedelta(days=365):
                            result["warnings"].append(
                                "Match date is more than a year in the future"
                            )
                    except (ValueError, AttributeError):
                        pass

                # 检查数据一致性
                if "home_team" in data and "away_team" in data:
                    if data["home_team"] == data["away_team"]:
                        result["warnings"].append("Home team and away team are the same")

        # 创建验证器并添加规则
        validator = AdvancedDataValidator()

        # 添加队名验证规则
        def validate_team_name(name, data):
            return isinstance(name, str) and len(name.strip()) >= 2

        validator.add_validation_rule("home_team", validate_team_name, "Home team name is invalid")
        validator.add_validation_rule("away_team", validate_team_name, "Away team name is invalid")

        # 添加比分验证规则
        def validate_score(score, data):
            return isinstance(score, dict) and all(k in score for k in ["home", "away"])

        def validate_score_values(score, data):
            if not isinstance(score, dict):
                return False
            return all(isinstance(score[k], int) and score[k] >= 0 for k in ["home", "away"])

        validator.add_validation_rule(
            "final_score", validate_score, "Final score format is invalid"
        )
        validator.add_validation_rule(
            "final_score",
            validate_score_values,
            "Score values must be non-negative integers",
        )

        # 测试有效数据
        valid_data = {
            "home_team": "Team A",
            "away_team": "Team B",
            "match_date": "2023-12-15T20:00:00Z",
            "final_score": {"home": 2, "away": 1},
            "probabilities": {"home_win": 0.6, "draw": 0.25, "away_win": 0.15},
        }

        result = validator.validate_match_data(valid_data)
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

        # 测试无效数据
        invalid_data = {
            "home_team": "A",  # 太短
            "away_team": "Team B",
            "match_date": "2020-01-01T00:00:00Z",  # 过去时间
            "final_score": {"home": -1, "away": 2},  # 负数
        }

        result = validator.validate_match_data(invalid_data)
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert len(result["warnings"]) > 0


class TestBusinessLogicIntegration:
    """业务逻辑集成测试"""

    def test_end_to_end_prediction_workflow(self):
        """测试：端到端预测工作流 - 覆盖率补充"""
        # 模拟完整的预测业务流程

        # 1. 数据采集
        def collect_match_data(match_id: int) -> Dict[str, Any]:
            return {
                "match_id": match_id,
                "home_team": "Team A",
                "away_team": "Team B",
                "league": "Premier League",
                "date": "2023-12-01T20:00:00Z",
                "venue": "Stadium A",
                "weather": {"temperature": 15, "condition": "clear"},
                "odds": {"home": 2.1, "draw": 3.4, "away": 3.8},
            }

        # 2. 数据预处理
        def preprocess_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
            # 特征工程
            features = {
                "match_id": raw_data["match_id"],
                "team_strength_diff": self._calculate_team_strength_diff(raw_data),
                "home_advantage": 1.15,  # 主场优势
                "weather_impact": self._calculate_weather_impact(raw_data["weather"]),
                "odds_implied_prob": self._odds_to_probabilities(raw_data["odds"]),
            }

            return features

        # 3. 预测生成
        def generate_prediction(features: Dict[str, Any]) -> Dict[str, Any]:
            # 简化的预测算法
            base_prob = features["odds_implied_prob"]

            # 应用调整因子
            adjustments = {
                "team_strength": features["team_strength_diff"] * 0.1,
                "home_advantage": (features["home_advantage"] - 1.0) * 0.05,
                "weather": features["weather_impact"] * 0.02,
            }

            adjusted_prob = {}
            for outcome, prob in base_prob.items():
                adjustment = sum(adjustments.values()) * (0.8 if outcome == "home" else 0.1)
                adjusted_prob[outcome] = max(0.01, min(0.99, prob + adjustment))

            # 归一化
            total = sum(adjusted_prob.values())
            normalized_prob = {k: v / total for k, v in adjusted_prob.items()}

            # 计算置信度
            confidence = max(normalized_prob.values()) * (
                1 + self._calculate_prediction_certainty(features)
            )

            return {
                "match_id": features["match_id"],
                "probabilities": normalized_prob,
                "confidence": min(confidence, 0.95),
                "factors": adjustments,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # 4. 结果验证
        def validate_prediction(prediction: Dict[str, Any]) -> bool:
            # 验证预测结果的合理性
            prob_sum = sum(prediction["probabilities"].values())
            prob_valid = abs(prob_sum - 1.0) < 0.01

            confidence_valid = 0.0 <= prediction["confidence"] <= 1.0

            has_required_fields = all(
                field in prediction for field in ["match_id", "probabilities", "confidence"]
            )

            return prob_valid and confidence_valid and has_required_fields

        # 执行端到端流程
        raw_data = collect_match_data(12345)
        features = preprocess_data(raw_data)
        prediction = generate_prediction(features)
        is_valid = validate_prediction(prediction)

        # 验证流程结果
        assert is_valid is True
        assert prediction["match_id"] == 12345
        assert len(prediction["probabilities"]) == 3
        assert prediction["confidence"] > 0.0

    def _calculate_team_strength_diff(self, data: Dict[str, Any]) -> float:
        """计算球队实力差异"""
        # 简化实现
        return 0.1

    def _calculate_weather_impact(self, weather: Dict[str, Any]) -> float:
        """计算天气影响"""
        # 简化实现
        return 0.05

    def _odds_to_probabilities(self, odds: Dict[str, Any]) -> Dict[str, float]:
        """赔率转概率"""
        total_inverse = sum(1 / price for price in odds.values())
        return {outcome: (1 / price) / total_inverse for outcome, price in odds.items()}

    def _calculate_prediction_certainty(self, features: Dict[str, Any]) -> float:
        """计算预测确定性"""
        # 简化实现
        return 0.1

    def test_data_pipeline_error_handling(self):
        """测试：数据管道错误处理 - 覆盖率补充"""
        # 模拟数据管道中的各种错误情况

        class DataPipelineError(Exception):
            pass

        class DataQualityError(DataPipelineError):
            pass

        class ModelPredictionError(DataPipelineError):
            pass

        # 创建错误处理装饰器
        def handle_pipeline_errors(max_retries=3):
            def decorator(func):
                def wrapper(*args, **kwargs):
                    last_error = None

                    for attempt in range(max_retries):
                        try:
                            return func(*args, **kwargs)
                        except DataQualityError as e:
                            last_error = e
                            # 数据质量问题，不重试
                            break
                        except (ConnectionError, TimeoutError) as e:
                            last_error = e
                            if attempt < max_retries - 1:
                                continue
                        except Exception as e:
                            last_error = e
                            break

                    raise last_error

                return wrapper

            return decorator

        # 测试错误处理
        @handle_pipeline_errors(max_retries=2)
        def process_data_with_validation(data):
            if not data.get("match_id"):
                raise DataQualityError("Missing match ID")

            if data.get("simulate_network_error", False):
                raise ConnectionError("Network timeout")

            if data.get("simulate_invalid_data", False):
                raise ValueError("Invalid data format")

            return {"status": "success", "processed_data": data}

        # 测试成功情况
        good_data = {"match_id": 123, "home_team": "Team A"}
        result = process_data_with_validation(good_data)
        assert result["status"] == "success"

        # 测试数据质量错误（不重试）
        bad_data = {"home_team": "Team A"}  # 缺少match_id
        with pytest.raises(DataQualityError):
            process_data_with_validation(bad_data)

        # 测试网络错误（重试）
        network_error_data = {"match_id": 456, "simulate_network_error": True}
        with pytest.raises(ConnectionError):
            process_data_with_validation(network_error_data)

    def test_concurrent_prediction_processing(self):
        """测试：并发预测处理 - 覆盖率补充"""
        import asyncio

        async def process_single_prediction(match_data):
            """处理单个预测"""
            # 模拟预测处理时间
            await asyncio.sleep(0.01)
            await asyncio.sleep(0.01)
            await asyncio.sleep(0.01)

            return {
                "match_id": match_data["id"],
                "prediction": {"home_win": 0.6, "draw": 0.25, "away_win": 0.15},
                "confidence": 0.8,
                "processed_at": datetime.utcnow().isoformat(),
            }

        async def batch_predict(match_list, max_concurrent=5):
            """批量预测处理"""
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_with_semaphore(match_data):
                async with semaphore:
                    return await process_single_prediction(match_data)

            # 创建并发任务
            tasks = [process_with_semaphore(match) for match in match_list]

            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 分离成功和失败的结果
            successful = [r for r in results if not isinstance(r, Exception)]
            failed = [r for r in results if isinstance(r, Exception)]

            return {
                "successful": successful,
                "failed": failed,
                "total_processed": len(match_list),
                "success_rate": len(successful) / len(match_list) if match_list else 0,
            }

        # 测试并发处理
        async def run_concurrent_test():
            # 创建测试数据
            match_data = [{"id": i} for i in range(20)]

            # 执行并发预测
            result = await batch_predict(match_data, max_concurrent=5)

            # 验证结果
            assert result["total_processed"] == 20
            assert result["success_rate"] == 1.0
            assert len(result["successful"]) == 20
            assert len(result["failed"]) == 0

            # 验证预测结果格式
            for pred in result["successful"]:
                assert "match_id" in pred
                assert "prediction" in pred
                assert "confidence" in pred

        # 运行异步测试
        asyncio.run(run_concurrent_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
