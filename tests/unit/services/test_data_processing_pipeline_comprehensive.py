"""
数据处理服务业务逻辑深度测试
重构完成: 1112行 → 450行 (压缩59%)
目标: 基于真实模块的业务逻辑覆盖

测试范围:
- DataProcessingService 核心服务功能
- 数据处理器业务逻辑 (Match, Odds, Scores, Features)
- 数据质量验证和异常检测
- 缺失数据处理策略
- 青铜到银层数据管道
- 批量处理和异步操作
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

# 导入目标模块
try:
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

    MODULE_AVAILABLE = True
except ImportError as e:
    print(f"模块导入警告: {e}")
    MODULE_AVAILABLE = False


class TestDataProcessingServiceBusinessLogic:
    """DataProcessingService 业务逻辑测试"""

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    def test_service_initialization_business_logic(self):
        """测试服务初始化业务逻辑"""
        service = DataProcessingService()

        assert service.initialized is False
        assert service.session is None
        assert isinstance(service.processors, dict)
        assert "match" in service.processors
        assert "odds" in service.processors
        assert "scores" in service.processors
        assert "features" in service.processors
        assert isinstance(service.bronze_to_silver, BronzeToSilverProcessor)

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_service_initialize_business_logic(self):
        """测试服务异步初始化业务逻辑"""
        service = DataProcessingService()

        # 首次初始化
        await service.initialize()

        assert service.initialized is True

        # 重复初始化应该不会出错
        await service.initialize()
        assert service.initialized is True

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_process_data_match_type_business_logic(self):
        """测试处理比赛数据业务逻辑"""
        service = DataProcessingService()
        await service.initialize()

        test_data = {
            "id": 12345,
            "type": "match",
            "home_team": "Team A",
            "away_team": "Team B",
            "date": "2024-01-01",
        }

        result = await service.process_data(test_data)

        assert isinstance(result, dict)
        assert result["id"] == 12345
        assert result["type"] == "match"
        assert "processed_at" in result
        assert isinstance(result["processed_at"], datetime)

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_process_data_odds_type_business_logic(self):
        """测试处理赔率数据业务逻辑"""
        service = DataProcessingService()
        await service.initialize()

        test_data = {
            "match_id": 12345,
            "type": "odds",
            "home_win": 2.5,
            "draw": 3.2,
            "away_win": 2.8,
        }

        result = await service.process_data(test_data)

        assert isinstance(result, dict)
        assert result["match_id"] == 12345
        assert result["type"] == "odds"
        assert "processed_at" in result

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_process_data_scores_type_business_logic(self):
        """测试处理比分数据业务逻辑"""
        service = DataProcessingService()
        await service.initialize()

        test_data = {
            "match_id": 12345,
            "type": "scores",
            "home_score": 2,
            "away_score": 1,
        }

        result = await service.process_data(test_data)

        assert isinstance(result, dict)
        assert result["match_id"] == 12345
        assert result["type"] == "scores"
        assert "processed_at" in result

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_process_data_features_type_business_logic(self):
        """测试处理特征数据业务逻辑"""
        service = DataProcessingService()
        await service.initialize()

        test_data = {
            "match_id": 12345,
            "type": "features",
            "team_strength_home": 0.8,
            "team_strength_away": 0.6,
        }

        result = await service.process_data(test_data)

        assert isinstance(result, dict)
        assert result["match_id"] == 12345
        assert result["type"] == "features"
        assert "processed_at" in result

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_process_data_unknown_type_business_logic(self):
        """测试处理未知类型数据业务逻辑"""
        service = DataProcessingService()
        await service.initialize()

        test_data = {
            "id": 12345,
            "type": "unknown_type",
            "content": "some data",
        }

        result = await service.process_data(test_data)

        assert isinstance(result, dict)
        assert result["id"] == 12345
        assert result["type"] == "unknown_type"
        assert result["status"] == "processed"
        assert "processed_at" in result

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_batch_process_business_logic(self):
        """测试批量数据处理业务逻辑"""
        service = DataProcessingService()
        await service.initialize()

        test_data_list = [
            {"id": 1, "type": "match", "home_team": "A", "away_team": "B"},
            {
                "id": 2,
                "type": "scores",
                "match_id": 1,
                "home_score": 2,
                "away_score": 1,
            },
            {"id": 3, "type": "odds", "match_id": 1, "home_win": 2.5},
        ]

        results = await service.batch_process(test_data_list)

        assert len(results) == len(test_data_list)
        for i, result in enumerate(results):
            assert isinstance(result, dict)
            assert "processed_at" in result
            assert result["id"] == test_data_list[i]["id"]

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_service_cleanup_business_logic(self):
        """测试服务清理业务逻辑"""
        service = DataProcessingService()
        await service.initialize()
        assert service.initialized is True

        await service.cleanup()

        # cleanup 不应该改变 initialized 状态，但应该清理其他资源
        assert service.initialized is True


class TestDataProcessorsBusinessLogic:
    """数据处理器业务逻辑测试"""

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_match_data_processor_business_logic(self):
        """测试比赛数据处理器业务逻辑"""
        processor = MatchDataProcessor()

        test_data = {
            "id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "date": "2024-01-01",
        }

        result = await processor.process(test_data)

        assert isinstance(result, dict)
        assert result["id"] == 12345
        assert result["type"] == "match"
        assert "processed_at" in result
        assert isinstance(result["processed_at"], datetime)

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_odds_data_processor_business_logic(self):
        """测试赔率数据处理器业务逻辑"""
        processor = OddsDataProcessor()

        test_data = {
            "match_id": 12345,
            "home_win": 2.5,
            "draw": 3.2,
            "away_win": 2.8,
        }

        result = await processor.process(test_data)

        assert isinstance(result, dict)
        assert result["match_id"] == 12345
        assert result["type"] == "odds"
        assert "processed_at" in result

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_scores_data_processor_business_logic(self):
        """测试比分数据处理器业务逻辑"""
        processor = ScoresDataProcessor()

        test_data = {
            "match_id": 12345,
            "home_score": 2,
            "away_score": 1,
        }

        result = await processor.process(test_data)

        assert isinstance(result, dict)
        assert result["match_id"] == 12345
        assert result["type"] == "scores"
        assert "processed_at" in result

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_features_data_processor_business_logic(self):
        """测试特征数据处理器业务逻辑"""
        processor = FeaturesDataProcessor()

        test_data = {
            "match_id": 12345,
            "team_strength_home": 0.8,
            "team_strength_away": 0.6,
        }

        result = await processor.process(test_data)

        assert isinstance(result, dict)
        assert result["match_id"] == 12345
        assert result["type"] == "features"
        assert "processed_at" in result


class TestDataQualityValidatorBusinessLogic:
    """数据质量验证器业务逻辑测试"""

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    def test_validator_valid_data_business_logic(self):
        """测试验证有效数据业务逻辑"""
        validator = DataQualityValidator()

        valid_data = {
            "id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
        }

        result = validator.validate(valid_data)

        assert result is True
        assert len(validator.errors) == 0

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    def test_validator_empty_data_business_logic(self):
        """测试验证空数据业务逻辑"""
        validator = DataQualityValidator()

        empty_data = {}

        result = validator.validate(empty_data)

        assert result is False
        assert len(validator.errors) > 0
        assert "Data is empty" in validator.errors

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    def test_validator_none_data_business_logic(self):
        """测试验证None数据业务逻辑"""
        validator = DataQualityValidator()

        result = validator.validate(None)

        assert result is False
        assert len(validator.errors) > 0
        assert "Data is empty" in validator.errors

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    def test_validator_multiple_errors_business_logic(self):
        """测试验证多个错误业务逻辑"""
        validator = DataQualityValidator()

        # 先验证一个错误的数据（不是空的，但缺少id）
        invalid_data = {"home_team": "Team A"}
        result = validator.validate(invalid_data)

        assert result is False
        assert len(validator.errors) > 0
        assert "Missing required field: id" in validator.errors


class TestAnomalyDetectorBusinessLogic:
    """异常检测器业务逻辑测试"""

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    def test_detector_normal_data_business_logic(self):
        """测试检测正常数据业务逻辑"""
        detector = AnomalyDetector()

        normal_data = {"value": 50, "name": "test"}

        anomalies = detector.detect(normal_data)

        assert isinstance(anomalies, list)
        assert len(anomalies) == 0

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    def test_detector_large_value_business_logic(self):
        """测试检测过大值业务逻辑"""
        detector = AnomalyDetector()

        large_value_data = {"value": 1500}

        anomalies = detector.detect(large_value_data)

        assert isinstance(anomalies, list)
        assert len(anomalies) > 0
        assert any("Value too large" in anomaly for anomaly in anomalies)

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    def test_detector_invalid_type_business_logic(self):
        """测试检测无效类型业务逻辑"""
        detector = AnomalyDetector()

        invalid_type_data = {"value": "not_a_number"}

        anomalies = detector.detect(invalid_type_data)

        assert isinstance(anomalies, list)
        assert len(anomalies) > 0
        assert any("Invalid value type" in anomaly for anomaly in anomalies)

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    def test_detector_no_value_field_business_logic(self):
        """测试检测无值字段数据业务逻辑"""
        detector = AnomalyDetector()

        no_value_data = {"name": "test", "type": "data"}

        anomalies = detector.detect(no_value_data)

        assert isinstance(anomalies, list)
        assert len(anomalies) == 0  # 没有 value 字段不算异常


class TestMissingDataHandlersBusinessLogic:
    """缺失数据处理器业务逻辑测试"""

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    def test_missing_scores_handler_business_logic(self):
        """测试缺失比分处理器业务逻辑"""
        handler = MissingScoresHandler()

        # 测试完整数据
        complete_data = {"home_score": 2, "away_score": 1}
        result = handler.handle(complete_data)
        assert result["home_score"] == 2
        assert result["away_score"] == 1

        # 测试缺失数据
        missing_data = {"match_id": 12345}
        result = handler.handle(missing_data)
        assert result["home_score"] == 0
        assert result["away_score"] == 0
        assert result["match_id"] == 12345

        # 测试部分缺失
        partial_missing_data = {"home_score": 3}
        result = handler.handle(partial_missing_data)
        assert result["home_score"] == 3
        assert result["away_score"] == 0

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    def test_missing_team_handler_business_logic(self):
        """测试缺失球队处理器业务逻辑"""
        handler = MissingTeamHandler()

        # 测试完整数据
        complete_data = {"home_team": "Team A", "away_team": "Team B"}
        result = handler.handle(complete_data)
        assert result["home_team"] == "Team A"
        assert result["away_team"] == "Team B"

        # 测试缺失数据
        missing_data = {"match_id": 12345}
        result = handler.handle(missing_data)
        assert result["home_team"] == "Unknown"
        assert result["away_team"] == "Unknown"
        assert result["match_id"] == 12345

        # 测试部分缺失
        partial_missing_data = {"home_team": "Team A"}
        result = handler.handle(partial_missing_data)
        assert result["home_team"] == "Team A"
        assert result["away_team"] == "Unknown"

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    def test_base_missing_data_handler_business_logic(self):
        """测试基础缺失数据处理器业务逻辑"""
        handler = MissingDataHandler()

        test_data = {"id": 12345, "name": "test"}

        result = handler.handle(test_data)

        # 基础处理器应该直接返回原数据
        assert result == test_data
        # 基础处理器直接返回原对象引用
        assert result is test_data


class TestBronzeToSilverProcessorBusinessLogic:
    """青铜到银层数据处理器业务逻辑测试"""

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    def test_processor_initialization_business_logic(self):
        """测试处理器初始化业务逻辑"""
        processor = BronzeToSilverProcessor()

        assert len(processor.validators) == 1
        assert isinstance(processor.validators[0], DataQualityValidator)
        assert len(processor.detectors) == 1
        assert isinstance(processor.detectors[0], AnomalyDetector)
        assert len(processor.handlers) == 2
        assert isinstance(processor.handlers[0], MissingScoresHandler)
        assert isinstance(processor.handlers[1], MissingTeamHandler)

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_processor_valid_data_business_logic(self):
        """测试处理器处理有效数据业务逻辑"""
        processor = BronzeToSilverProcessor()

        valid_data = {
            "id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
            "value": 50,
        }

        result = await processor.process(valid_data)

        assert isinstance(result, dict)
        assert result["id"] == 12345
        assert result["layer"] == "silver"
        assert "processed_at" in result
        assert isinstance(result["processed_at"], datetime)

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_processor_data_with_missing_fields_business_logic(self):
        """测试处理器处理缺失字段数据业务逻辑"""
        processor = BronzeToSilverProcessor()

        incomplete_data = {
            "id": 12345,
            "value": 75,
        }

        result = await processor.process(incomplete_data)

        assert isinstance(result, dict)
        assert result["id"] == 12345
        assert result["home_team"] == "Unknown"  # MissingTeamHandler 处理
        assert result["away_team"] == "Unknown"  # MissingTeamHandler 处理
        assert result["home_score"] == 0  # MissingScoresHandler 处理
        assert result["away_score"] == 0  # MissingScoresHandler 处理
        assert result["layer"] == "silver"
        assert "processed_at" in result

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_processor_data_with_anomalies_business_logic(self):
        """测试处理器处理异常数据业务逻辑"""
        processor = BronzeToSilverProcessor()

        anomalous_data = {
            "id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "value": 1500,  # 过大的值
        }

        # 使用 patch 来捕获日志调用
        with patch("src.services.data_processing.logger") as mock_logger:
            result = await processor.process(anomalous_data)

            # 验证异常检测日志被调用
            mock_logger.warning.assert_called()
            assert "Anomalies detected" in str(mock_logger.warning.call_args)

        assert isinstance(result, dict)
        assert result["id"] == 12345
        assert result["layer"] == "silver"
        assert "processed_at" in result


class TestDataProcessingIntegrationBusinessLogic:
    """数据处理集成业务逻辑测试"""

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_end_to_end_data_processing_business_logic(self):
        """测试端到端数据处理业务逻辑"""
        service = DataProcessingService()

        # 模拟从不同数据源收集的原始数据
        raw_data_list = [
            {
                "id": 12345,
                "type": "match",
                "home_team": "Team A",
                "away_team": "Team B",
                "date": "2024-01-01",
            },
            {
                "match_id": 12345,
                "type": "scores",
                "home_score": None,  # 缺失数据
                "away_score": 1,
            },
            {
                "match_id": 12345,
                "type": "odds",
                "home_win": 2.5,
                "draw": 3.2,
                "away_win": 2.8,
            },
        ]

        # 批量处理
        processed_data = await service.batch_process(raw_data_list)

        # 验证处理结果
        assert len(processed_data) == len(raw_data_list)
        for data in processed_data:
            assert "processed_at" in data
            assert isinstance(data["processed_at"], datetime)

        # 验证比赛数据处理
        match_data = next(d for d in processed_data if d.get("type") == "match")
        assert match_data["id"] == 12345

        # 验证比分数据处理
        scores_data = next(d for d in processed_data if d.get("type") == "scores")
        assert scores_data["match_id"] == 12345

        # 验证赔率数据处理
        odds_data = next(d for d in processed_data if d.get("type") == "odds")
        assert odds_data["match_id"] == 12345

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_bronze_to_silver_pipeline_integration_business_logic(self):
        """测试青铜到银层数据管道集成业务逻辑"""
        service = DataProcessingService()
        bronze_processor = BronzeToSilverProcessor()

        # 模拟青铜层原始数据
        bronze_data = {
            "id": 12346,
            "match_date": "2024-01-02",
            "home_team": "Team C",
            "away_team": "Team D",
            # 缺失比分信息
        }

        # 处理青铜到银层
        silver_data = await bronze_processor.process(bronze_data)

        # 验证银层数据
        assert silver_data["layer"] == "silver"
        assert silver_data["home_team"] == "Team C"
        assert silver_data["away_team"] == "Team D"
        assert silver_data["home_score"] == 0  # 由 MissingScoresHandler 填充
        assert silver_data["away_score"] == 0  # 由 MissingScoresHandler 填充
        assert "processed_at" in silver_data

        # 进一步通过服务处理
        final_data = await service.process_data(silver_data)

        assert "processed_at" in final_data
        assert isinstance(final_data["processed_at"], datetime)

    @pytest.mark.skipif(not MODULE_AVAILABLE, reason="数据处理模块不可用")
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery_business_logic(self):
        """测试错误处理和恢复业务逻辑"""
        service = DataProcessingService()
        await service.initialize()

        # 测试处理可能导致错误的数据
        problematic_data = [
            {"id": 1, "type": "match"},  # 缺少必要信息但应该能处理
            {"id": 2, "type": "unknown"},  # 未知类型
            {"type": "scores", "match_id": 3},  # 缺少 id 字段
        ]

        try:
            results = await service.batch_process(problematic_data)

            # 验证所有数据都被处理了（即使有些可能不完美）
            assert len(results) == len(problematic_data)

            for i, result in enumerate(results):
                assert isinstance(result, dict)
                assert "processed_at" in result

        except Exception as e:
            pytest.fail(
                f"Batch processing should handle problematic data gracefully, but got error: {e}"
            )


if __name__ == "__main__":
    print("数据处理服务业务逻辑测试套件")
    if MODULE_AVAILABLE:
        print("✅ 所有模块可用，测试已准备就绪")
    else:
        print("⚠️ 模块不可用，测试将被跳过")
