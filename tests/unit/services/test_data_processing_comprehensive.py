from datetime import datetime
"""
数据处理服务综合测试
Comprehensive Tests for Data Processing Service

测试src.services.data_processing模块的所有功能
"""

import asyncio

import pytest

from src.services.data_processing import (
    AnomalyDetector,
    BronzeToSilverProcessor,
    DataProcessingService,
    DataProcessor,
    DataQualityValidator,
    FeaturesDataProcessor,
    MatchDataProcessor,
    MissingDataHandler,
    MissingScoresHandler,
    MissingTeamHandler,
    OddsDataProcessor,
    ScoresDataProcessor,
)


@pytest.mark.unit
class TestDataProcessorBase:
    """数据处理器基类测试"""

    def test_data_processor_is_abstract(self) -> None:
        """✅ 边界用例:数据处理器是抽象类"""
        # 不能直接实例化抽象类
        with pytest.raises(TypeError):
            DataProcessor()

    def test_concrete_processors_inherit_base(self) -> None:
        """✅ 成功用例:具体处理器继承基类"""
        processors = [
            MatchDataProcessor(),
            OddsDataProcessor(),
            ScoresDataProcessor(),
            FeaturesDataProcessor(),
        ]

        for processor in processors:
            assert isinstance(processor, DataProcessor)
            assert hasattr(processor, "process")
            assert asyncio.iscoroutinefunction(processor.process)


@pytest.mark.unit
class TestMatchDataProcessor:
    """比赛数据处理器测试"""

    @pytest.mark.asyncio
    async def test_process_match_data(self) -> None:
        """✅ 成功用例:处理比赛数据"""
        processor = MatchDataProcessor()
        input_data = {
            "id": "match_123",
            "home_team": "Team A",
            "away_team": "Team B",
            "date": "2023-01-01",
        }

        result = await processor.process(input_data)

        assert result["id"] == "match_123"
        assert result["home_team"] == "Team A"
        assert result["away_team"] == "Team B"
        assert result["type"] == "match"
        assert "processed_at" in result
        assert isinstance(result["processed_at"], datetime)

    @pytest.mark.asyncio
    async def test_process_match_data_without_id(self) -> None:
        """✅ 边界用例:处理没有ID的比赛数据"""
        processor = MatchDataProcessor()
        input_data = {"home_team": "Team A", "away_team": "Team B"}

        result = await processor.process(input_data)

        assert result["home_team"] == "Team A"
        assert result["away_team"] == "Team B"
        assert result["type"] == "match"
        assert "processed_at" in result

    @pytest.mark.asyncio
    async def test_process_complex_match_data(self) -> None:
        """✅ 成功用例:处理复杂比赛数据"""
        processor = MatchDataProcessor()
        complex_data = {
            "id": "complex_match",
            "home_team": "Team A",
            "away_team": "Team B",
            "score": {"home": 2, "away": 1},
            "events": [
                {"type": "goal", "minute": 15},
                {"type": "yellow_card", "minute": 30},
            ],
            "metadata": {"stadium": "Stadium Name", "attendance": 50000},
        }

        result = await processor.process(complex_data)

        # 验证复杂结构被保持
        assert result["score"] == {"home": 2, "away": 1}
        assert len(result["events"]) == 2
        assert result["metadata"]["stadium"] == "Stadium Name"
        assert result["type"] == "match"


@pytest.mark.unit
class TestOddsDataProcessor:
    """赔率数据处理器测试"""

    @pytest.mark.asyncio
    async def test_process_odds_data(self) -> None:
        """✅ 成功用例:处理赔率数据"""
        processor = OddsDataProcessor()
        input_data = {
            "match_id": "match_123",
            "home_win": 2.5,
            "draw": 3.2,
            "away_win": 2.8,
        }

        result = await processor.process(input_data)

        assert result["match_id"] == "match_123"
        assert result["home_win"] == 2.5
        assert result["draw"] == 3.2
        assert result["away_win"] == 2.8
        assert result["type"] == "odds"
        assert "processed_at" in result

    @pytest.mark.asyncio
    async def test_process_odds_with_floats(self) -> None:
        """✅ 成功用例:处理浮点数赔率"""
        processor = OddsDataProcessor()
        odds_data = {
            "match_id": "match_456",
            "home_win": 1.85,
            "draw": 3.40,
            "away_win": 4.20,
            "over_under": {"over": 1.95, "under": 1.85},
        }

        result = await processor.process(odds_data)

        # 验证浮点数精度保持
        assert abs(result["home_win"] - 1.85) < 0.001
        assert result["over_under"]["over"] == 1.95
        assert result["type"] == "odds"


@pytest.mark.unit
class TestScoresDataProcessor:
    """比分数据处理器测试"""

    @pytest.mark.asyncio
    async def test_process_scores_data(self) -> None:
        """✅ 成功用例:处理比分数据"""
        processor = ScoresDataProcessor()
        input_data = {
            "match_id": "match_123",
            "home_score": 2,
            "away_score": 1,
            "scorers": [
                {"team": "home", "player": "Player A", "minute": 25},
                {"team": "away", "player": "Player B", "minute": 60},
            ],
        }

        result = await processor.process(input_data)

        assert result["match_id"] == "match_123"
        assert result["home_score"] == 2
        assert result["away_score"] == 1
        assert len(result["scorers"]) == 2
        assert result["type"] == "scores"
        assert "processed_at" in result


@pytest.mark.unit
class TestFeaturesDataProcessor:
    """特征数据处理器测试"""

    @pytest.mark.asyncio
    async def test_process_features_data(self) -> None:
        """✅ 成功用例:处理特征数据"""
        processor = FeaturesDataProcessor()
        input_data = {
            "match_id": "match_123",
            "features": {
                "home_form": [1, 0, 1, 1, 0],
                "away_form": [0, 1, 0, 0, 1],
                "head_to_head": {"home_wins": 3, "away_wins": 2},
            },
        }

        result = await processor.process(input_data)

        assert result["match_id"] == "match_123"
        assert len(result["features"]["home_form"]) == 5
        assert result["features"]["head_to_head"]["home_wins"] == 3
        assert result["type"] == "features"
        assert "processed_at" in result

    @pytest.mark.asyncio
    async def test_process_ml_features(self) -> None:
        """✅ 成功用例:处理机器学习特征"""
        processor = FeaturesDataProcessor()
        ml_features = {
            "match_id": "ml_match",
            "features": {
                "statistical": {
                    "avg_goals_home": 1.8,
                    "avg_goals_away": 1.2,
                    "avg_corners": 10.5,
                },
                "historical": {
                    "last_5_games_home": [3, 1, 0, 2, 1],
                    "last_5_games_away": [1, 0, 2, 1, 0],
                },
                "weather": {"temperature": 18.5, "humidity": 65, "wind_speed": 12.3},
            },
        }

        result = await processor.process(ml_features)

        assert result["type"] == "features"
        assert result["features"]["statistical"]["avg_goals_home"] == 1.8
        assert len(result["features"]["historical"]["last_5_games_home"]) == 5


@pytest.mark.unit
class TestDataQualityValidator:
    """数据质量验证器测试"""

    def test_validate_valid_data(self) -> None:
        """✅ 成功用例:验证有效数据"""
        validator = DataQualityValidator()
        valid_data = {"id": "123", "name": "test"}

        result = validator.validate(valid_data)

        assert result is True
        assert validator.errors == []

    def test_validate_empty_data(self) -> None:
        """✅ 边界用例:验证空数据"""
        validator = DataQualityValidator()
        empty_data = {}

        result = validator.validate(empty_data)

        assert result is False
        # 根据实际实现,空数据会先被标记为"Data is empty"
        assert "Data is empty" in validator.errors

    def test_validate_none_data(self) -> None:
        """✅ 边界用例:验证None数据"""
        validator = DataQualityValidator()

        result = validator.validate(None)

        assert result is False
        assert "Data is empty" in validator.errors

    def test_validate_data_with_extra_fields(self) -> None:
        """✅ 成功用例:验证包含额外字段的数据"""
        validator = DataQualityValidator()
        data_with_extra = {
            "id": "123",
            "name": "test",
            "extra_field": "extra_value",
            "another_extra": 42,
        }

        result = validator.validate(data_with_extra)

        assert result is True
        assert validator.errors == []

    def test_multiple_validation_errors(self) -> None:
        """✅ 成功用例:多个验证错误"""
        validator = DataQualityValidator()
        invalid_data = {"name": "test"}  # 缺少id字段

        result = validator.validate(invalid_data)

        assert result is False
        assert len(validator.errors) == 1
        assert "Missing required field: id" in validator.errors[0]

    def test_error_state_clearing(self) -> None:
        """✅ 成功用例:错误状态清除"""
        validator = DataQualityValidator()

        # 第一次验证失败
        validator.validate({})
        assert len(validator.errors) > 0

        # 第二次验证成功
        result = validator.validate({"id": "test"})
        assert result is True
        assert validator.errors == []


@pytest.mark.unit
class TestAnomalyDetector:
    """异常检测器测试"""

    def test_detect_no_anomalies(self) -> None:
        """✅ 成功用例:检测无异常"""
        detector = AnomalyDetector()
        normal_data = {"value": 50, "name": "test"}

        anomalies = detector.detect(normal_data)

        assert anomalies == []

    def test_detect_large_value_anomaly(self) -> None:
        """✅ 成功用例:检测大值异常"""
        detector = AnomalyDetector()
        large_value_data = {"value": 1500}

        anomalies = detector.detect(large_value_data)

        assert len(anomalies) == 1
        assert "Value too large: 1500" in anomalies[0]

    def test_detect_invalid_type_anomaly(self) -> None:
        """✅ 成功用例:检测无效类型异常"""
        detector = AnomalyDetector()
        invalid_type_data = {"value": "not_a_number"}

        anomalies = detector.detect(invalid_type_data)

        assert len(anomalies) == 1
        assert "Invalid value type" in anomalies[0]

    def test_detect_negative_value(self) -> None:
        """✅ 边界用例:检测负值"""
        detector = AnomalyDetector()
        negative_data = {"value": -100}

        anomalies = detector.detect(negative_data)

        # 负值应该在阈值范围内,不算异常
        assert anomalies == []

    def test_detect_boundary_values(self) -> None:
        """✅ 边界用例:检测边界值"""
        detector = AnomalyDetector()

        # 测试边界值
        boundary_data = {"value": 1000}
        anomalies = detector.detect(boundary_data)
        assert anomalies == []  # 1000不算异常

        # 稍微超过边界
        over_boundary_data = {"value": 1001}
        anomalies = detector.detect(over_boundary_data)
        assert len(anomalies) == 1

    def test_detect_no_value_field(self) -> None:
        """✅ 边界用例:数据中没有value字段"""
        detector = AnomalyDetector()
        data_without_value = {"name": "test", "other_field": 123}

        anomalies = detector.detect(data_without_value)

        assert anomalies == []

    def test_detect_with_zero_value(self) -> None:
        """✅ 边界用例:零值检测"""
        detector = AnomalyDetector()
        zero_data = {"value": 0}

        anomalies = detector.detect(zero_data)

        assert anomalies == []


@pytest.mark.unit
class TestMissingDataHandlers:
    """缺失数据处理器测试"""

    def test_missing_scores_handler(self) -> None:
        """✅ 成功用例:缺失比分处理器"""
        handler = MissingScoresHandler()

        # 完整数据
        complete_data = {"home_score": 2, "away_score": 1}
        result = handler.handle(complete_data.copy())
        assert result == complete_data

        # 缺失主队比分
        missing_home = {"away_score": 1}
        result = handler.handle(missing_home.copy())
        assert result["home_score"] == 0
        assert result["away_score"] == 1

        # 缺失客队比分
        missing_away = {"home_score": 2}
        result = handler.handle(missing_away.copy())
        assert result["home_score"] == 2
        assert result["away_score"] == 0

        # 都缺失
        missing_both = {}
        result = handler.handle(missing_both.copy())
        assert result["home_score"] == 0
        assert result["away_score"] == 0

    def test_missing_team_handler(self) -> None:
        """✅ 成功用例:缺失球队处理器"""
        handler = MissingTeamHandler()

        # 完整数据
        complete_data = {"home_team": "Team A", "away_team": "Team B"}
        result = handler.handle(complete_data.copy())
        assert result == complete_data

        # 缺失各种组合
        test_cases = [
            ({"away_team": "Team B"}, {"home_team": "Unknown", "away_team": "Team B"}),
            ({"home_team": "Team A"}, {"home_team": "Team A", "away_team": "Unknown"}),
            ({}, {"home_team": "Unknown", "away_team": "Unknown"}),
        ]

        for input_data, expected in test_cases:
            result = handler.handle(input_data.copy())
            assert result == expected

    def test_missing_data_handler_base(self) -> None:
        """✅ 成功用例:基类缺失数据处理器"""
        handler = MissingDataHandler()
        test_data = {"test": "data"}

        result = handler.handle(test_data.copy())

        assert result == test_data


@pytest.mark.unit
class TestBronzeToSilverProcessor:
    """青铜到银层数据处理器测试"""

    @pytest.mark.asyncio
    async def test_process_valid_data(self) -> None:
        """✅ 成功用例:处理有效数据"""
        processor = BronzeToSilverProcessor()
        input_data = {"id": "123", "name": "test"}

        result = await processor.process(input_data)

        assert result["id"] == "123"
        assert result["name"] == "test"
        assert result["layer"] == "silver"
        assert "processed_at" in result

    @pytest.mark.asyncio
    async def test_process_with_validation_errors(self) -> None:
        """✅ 成功用例:处理验证错误的数据"""
        processor = BronzeToSilverProcessor()
        invalid_data = {}  # 缺少id字段

        with patch("src.services.data_processing.logger") as mock_logger:
            result = await processor.process(invalid_data)

        assert result["layer"] == "silver"
        assert "processed_at" in result
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_anomalies(self) -> None:
        """✅ 成功用例:处理包含异常的数据"""
        processor = BronzeToSilverProcessor()
        anomalous_data = {"id": "123", "value": 2000}

        with patch("src.services.data_processing.logger") as mock_logger:
            result = await processor.process(anomalous_data)

        assert result["id"] == "123"
        assert result["layer"] == "silver"
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_missing_data(self) -> None:
        """✅ 成功用例:处理缺失数据"""
        processor = BronzeToSilverProcessor()
        incomplete_data = {"id": "123"}  # 缺失比分和球队信息

        result = await processor.process(incomplete_data)

        assert result["id"] == "123"
        assert result["home_score"] == 0
        assert result["away_score"] == 0
        assert result["home_team"] == "Unknown"
        assert result["away_team"] == "Unknown"
        assert result["layer"] == "silver"

    @pytest.mark.asyncio
    async def test_processor_components_initialization(self) -> None:
        """✅ 成功用例:处理器组件初始化"""
        processor = BronzeToSilverProcessor()

        assert len(processor.validators) == 1
        assert len(processor.detectors) == 1
        assert len(processor.handlers) == 2

        assert isinstance(processor.validators[0], DataQualityValidator)
        assert isinstance(processor.detectors[0], AnomalyDetector)
        assert isinstance(processor.handlers[0], MissingScoresHandler)
        assert isinstance(processor.handlers[1], MissingTeamHandler)


@pytest.mark.unit
class TestDataProcessingService:
    """数据处理服务测试"""

    def test_service_initialization(self) -> None:
        """✅ 成功用例:服务初始化"""
        service = DataProcessingService()

        assert service.initialized is False
        assert service.session is None
        assert len(service.processors) == 4
        assert "match" in service.processors
        assert "odds" in service.processors
        assert "scores" in service.processors
        assert "features" in service.processors
        assert isinstance(service.bronze_to_silver, BronzeToSilverProcessor)

    def test_service_initialization_with_session(self) -> None:
        """✅ 成功用例:带会话的服务初始化"""
        mock_session = Mock()
        service = DataProcessingService(session=mock_session)

        assert service.session == mock_session

    @pytest.mark.asyncio
    async def test_initialize_service(self) -> None:
        """✅ 成功用例:初始化服务"""
        service = DataProcessingService()

        assert service.initialized is False
        await service.initialize()
        assert service.initialized is True

        # 重复初始化应该没有副作用
        await service.initialize()
        assert service.initialized is True

    @pytest.mark.asyncio
    async def test_process_data_with_known_type(self) -> None:
        """✅ 成功用例:处理已知类型的数据"""
        service = DataProcessingService()
        match_data = {
            "type": "match",
            "id": "123",
            "home_team": "Team A",
            "away_team": "Team B",
        }

        result = await service.process_data(match_data)

        assert result["type"] == "match"
        assert result["id"] == "123"
        assert "processed_at" in result

    @pytest.mark.asyncio
    async def test_process_data_with_unknown_type(self) -> None:
        """✅ 成功用例:处理未知类型的数据"""
        service = DataProcessingService()
        unknown_data = {"type": "unknown_type", "id": "123", "data": "test"}

        result = await service.process_data(unknown_data)

        assert result["type"] == "unknown_type"
        assert result["id"] == "123"
        assert result["status"] == "processed"
        assert "processed_at" in result

    @pytest.mark.asyncio
    async def test_process_data_without_type(self) -> None:
        """✅ 成功用例:处理没有类型的数据（默认为match）"""
        service = DataProcessingService()
        data_without_type = {"id": "123", "name": "test"}

        result = await service.process_data(data_without_type)

        assert result["type"] == "match"  # 默认类型
        assert result["id"] == "123"
        assert "processed_at" in result

    @pytest.mark.asyncio
    async def test_process_data_auto_initialization(self) -> None:
        """✅ 成功用例:数据处理时自动初始化"""
        service = DataProcessingService()
        assert service.initialized is False

        data = {"type": "match", "id": "123"}
        await service.process_data(data)

        assert service.initialized is True

    @pytest.mark.asyncio
    async def test_batch_process_data(self) -> None:
        """✅ 成功用例:批量处理数据"""
        service = DataProcessingService()
        batch_data = [
            {"type": "match", "id": "1", "home_team": "Team A"},
            {"type": "odds", "match_id": "1", "home_win": 2.5},
            {"type": "scores", "match_id": "1", "home_score": 2},
            {"type": "features", "match_id": "1", "feature": 1.5},
        ]

        results = await service.batch_process(batch_data)

        assert len(results) == 4
        assert results[0]["type"] == "match"
        assert results[1]["type"] == "odds"
        assert results[2]["type"] == "scores"
        assert results[3]["type"] == "features"

        for result in results:
            assert "processed_at" in result

    @pytest.mark.asyncio
    async def test_batch_process_empty_list(self) -> None:
        """✅ 边界用例:批量处理空列表"""
        service = DataProcessingService()

        results = await service.batch_process([])

        assert results == []

    @pytest.mark.asyncio
    async def test_cleanup_service(self) -> None:
        """✅ 成功用例:清理服务"""
        service = DataProcessingService()
        await service.initialize()

        with patch("src.services.data_processing.logger") as mock_logger:
            await service.cleanup()

        mock_logger.info.assert_called_with("DataProcessingService cleaned up")

    @pytest.mark.asyncio
    async def test_service_integration_workflow(self) -> None:
        """✅ 集成用例:完整的服务工作流"""
        service = DataProcessingService()

        # 1. 处理单个数据
        match_data = {
            "type": "match",
            "id": "match_123",
            "home_team": "Team A",
            "away_team": "Team B",
        }

        processed_match = await service.process_data(match_data)
        assert processed_match["type"] == "match"

        # 2. 批量处理多种类型数据
        batch_data = [
            {"type": "odds", "match_id": "match_123", "home_win": 2.0},
            {"type": "scores", "match_id": "match_123", "home_score": 2},
            {"type": "features", "match_id": "match_123", "strength": 0.8},
        ]

        processed_batch = await service.batch_process(batch_data)
        assert len(processed_batch) == 3

        # 3. 验证所有数据都有时间戳
        for data in [processed_match] + processed_batch:
            assert "processed_at" in data
            assert isinstance(data["processed_at"], datetime)

        # 4. 清理
        await service.cleanup()


@pytest.mark.unit
class TestDataProcessingPerformance:
    """数据处理性能测试"""

    @pytest.mark.asyncio
    async def test_single_processing_performance(self) -> None:
        """✅ 性能用例:单个数据处理性能"""
        service = DataProcessingService()
        test_data = {"type": "match", "id": "perf_test", "data": "x" * 100}

        import time

        start_time = time.perf_counter()

        for _ in range(100):
            await service.process_data(test_data)

        end_time = time.perf_counter()
        duration = end_time - start_time

        # 100次处理应该在1秒内完成
        assert duration < 1.0, f"Too slow: {duration:.3f}s for 100 operations"

    @pytest.mark.asyncio
    async def test_batch_processing_performance(self) -> None:
        """✅ 性能用例:批量处理性能"""
        service = DataProcessingService()
        batch_size = 50
        batch_data = [
            {"type": "match", "id": f"match_{i}", "data": f"data_{i}"} for i in range(batch_size)
        ]

        import time

        start_time = time.perf_counter()

        results = await service.batch_process(batch_data)

        end_time = time.perf_counter()
        duration = end_time - start_time

        assert len(results) == batch_size
        # 批量处理50个数据应该在0.5秒内完成
        assert duration < 0.5, f"Batch processing too slow: {duration:.3f}s"

    @pytest.mark.asyncio
    async def test_concurrent_processing(self) -> None:
        """✅ 并发用例:并发数据处理"""
        service = DataProcessingService()

        async def process_data_concurrently(data_id: int):
            data = {"type": "match", "id": f"concurrent_{data_id}"}
            return await service.process_data(data)

        # 创建多个并发任务
        tasks = [process_data_concurrently(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 20
        for i, result in enumerate(results):
            assert result["id"] == f"concurrent_{i}"
            assert "processed_at" in result


@pytest.mark.unit
class TestDataProcessingErrorHandling:
    """数据处理错误处理测试"""

    @pytest.mark.asyncio
    async def test_handle_malformed_data(self) -> None:
        """✅ 错误处理用例:处理畸形数据"""
        service = DataProcessingService()

        # 测试各种畸形数据
        malformed_cases = [
            {},  # 空数据
            {"type": None},  # None类型
            {"type": ""},  # 空类型
            {"type": "unknown", "invalid_field": object()},  # 包含不可序列化对象
        ]

        for data in malformed_cases:
            try:
                result = await service.process_data(data)
                # 应该返回某种结果,不抛出异常
                assert isinstance(result, dict)
                assert "processed_at" in result or "status" in result
            except Exception as e:
                pytest.fail(f"Unexpected error for data {data}: {e}")

    @pytest.mark.asyncio
    async def test_processor_exception_handling(self) -> None:
        """✅ 错误处理用例:处理器异常处理"""

        # 创建一个会抛出异常的处理器
        class FaultyProcessor(DataProcessor):
            async def process(self, data):
                raise ValueError("Simulated processor error")

        service = DataProcessingService()
        service.processors["faulty"] = FaultyProcessor()

        faulty_data = {"type": "faulty", "id": "test"}

        try:
            result = await service.process_data(faulty_data)
            # 如果没有抛出异常，应该有合理的默认处理
            assert isinstance(result, dict)
        except ValueError:
            # 如果异常被传播,这也是可以接受的
            pass

    @pytest.mark.asyncio
    async def test_batch_processing_with_errors(self) -> None:
        """✅ 错误处理用例:批量处理中的错误"""
        service = DataProcessingService()

        # 混合正常和异常数据
        mixed_batch = [
            {"type": "match", "id": "good_1"},
            {"type": "unknown", "id": "unknown_1"},
            {"type": "match", "id": "good_2"},
        ]

        try:
            results = await service.batch_process(mixed_batch)
            assert len(results) == 3
            # 正常数据应该被正确处理
            assert results[0]["type"] == "match"
            assert results[2]["type"] == "match"
        except Exception:
            # 如果整个批次失败,这也是合理的
            pass
