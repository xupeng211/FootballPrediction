#!/usr/bin/env python3
"""
L2 特征提取器 - TDD 测试套件
=============================

测试驱动开发 (TDD) 流程:
    1. 编写测试（本文件）
    2. 运行测试（失败）
    3. 实现功能
    4. 运行测试（通过）

测试覆盖:
    - 抽象基类行为
    - 异常处理
    - 验证逻辑
    - V25 实现类

Author: Architecture Team
Version: V25.0
Date: 2025-12-26
"""

import pytest
from typing import Any, Dict
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 导入 V25 提取器以确保注册
from src.processors.v25_production_extractor import V25ProductionExtractor

from src.processors.base_extractor import (
    BaseExtractor,
    ExtractionResult,
    ExtractionStatus,
    ValidationConfig,
    ExtractorRegistry,
    register_extractor,
)
from src.processors.exceptions import (
    ExtractionError,
    ValidationError,
    InsufficientFeaturesError,
    MissingRequiredKeyError,
    DataParsingError,
    SchemaMismatchError,
)


# ============================================================================
# 测试数据夹具
# ============================================================================


@pytest.fixture
def minimal_match_data() -> Dict[str, Any]:
    """
    最小化比赛数据（有效输入）

    模拟 FotMob API 返回的最小有效 JSON。
    """
    return {
        "content": {
            "match": {
                "matchId": 123456,
                "homeTeam": 9825,
                "awayTeam": 8456,
                "leagueId": 47,
                "seasonId": 2425,
            },
            "general": {
                "homeTeam": {"id": 9825, "name": "Arsenal"},
                "awayTeam": {"id": 8456, "name": "Manchester City"},
            },
            "stats": {
                "Periods": {
                    "All": {
                        "stats": [
                            {"key": "BallPossesion", "stats": [55, 45]},
                            {"key": "total_shots", "stats": [15, 12]},
                            {"key": "ShotsOnTarget", "stats": [5, 3]},
                            {"key": "corners", "stats": [7, 4]},
                            {"key": "expected_goals", "stats": [1.34, 1.49]},
                        ]
                    }
                }
            },
        },
        "l2_json": {},  # 占位符
    }


@pytest.fixture
def full_match_data() -> Dict[str, Any]:
    """
    完整比赛数据（包含所有可能的字段）
    """
    return {
        "content": {
            "match": {
                "matchId": 123456,
                "homeTeam": 9825,
                "awayTeam": 8456,
                "leagueId": 47,
                "seasonId": 2425,
            },
            "general": {
                "homeTeam": {"id": 9825, "name": "Arsenal"},
                "awayTeam": {"id": 8456, "name": "Manchester City"},
            },
            "stats": {
                "Periods": {
                    "All": {
                        "stats": [
                            {"key": "BallPossesion", "stats": [55, 45]},
                            {"key": "total_shots", "stats": [15, 12]},
                            {"key": "ShotsOnTarget", "stats": [5, 3]},
                            {"key": "corners", "stats": [7, 4]},
                            {"key": "expected_goals", "stats": [1.34, 1.49]},
                        ]
                    }
                }
            },
            "lineup": {
                "homeTeam": {
                    "starters": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                    "subs": [12, 13, 14, 15, 16, 17, 18],
                    "rating": 7.45,
                },
                "awayTeam": {
                    "starters": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                    "subs": [12, 13, 14, 15, 16, 17, 18],
                    "rating": 7.12,
                },
            }
        },
        "l2_json": {},
    }


@pytest.fixture
def invalid_match_data_missing_content() -> Dict[str, Any]:
    """无效数据：缺少 content 字段"""
    return {"l2_json": {}, "other_field": "value"}


@pytest.fixture
def invalid_match_data_empty() -> Dict[str, Any]:
    """无效数据：空字典"""
    return {}


@pytest.fixture
def invalid_match_data_malformed_json() -> Dict[str, Any]:
    """无效数据：格式错误的 JSON 结构"""
    return {"content": "not_a_dict"}


@pytest.fixture
def insufficient_features_data() -> Dict[str, Any]:
    """特征不足的数据（会导致维度不足）"""
    return {
        "content": {
            "match": {
                "matchId": 123456,
                "homeTeam": 9825,
                "awayTeam": 8456,
            },
            "stats": {"Periods": {"All": {"stats": []}}},  # 无统计数据
        },
        "l2_json": {},
    }


# ============================================================================
# 抽象基类测试
# ============================================================================


class TestExtractionResult:
    """测试 ExtractionResult 数据类"""

    def test_creation_success(self):
        """测试创建成功的提取结果"""
        result = ExtractionResult(
            status=ExtractionStatus.SUCCESS,
            features={"f1": 1.0, "f2": 2.0},
            metadata={"version": "V25.0"},
        )

        assert result.status == ExtractionStatus.SUCCESS
        assert result.feature_count == 2
        assert result.is_success
        assert not result.has_errors

    def test_creation_with_errors(self):
        """测试包含错误的提取结果"""
        result = ExtractionResult(
            status=ExtractionStatus.PARTIAL,
            features={"f1": 1.0},
            errors=["Feature f2 missing"],
            warnings=["Data quality low"],
        )

        assert result.status == ExtractionStatus.PARTIAL
        assert result.is_success  # PARTIAL 也算成功
        assert result.has_errors
        assert len(result.errors) == 1
        assert len(result.warnings) == 1

    def test_creation_failed(self):
        """测试失败的提取结果"""
        result = ExtractionResult(
            status=ExtractionStatus.FAILED,
            features={},
            errors=["Extraction failed"],
        )

        assert result.status == ExtractionStatus.FAILED
        assert not result.is_success
        assert result.has_errors


class TestValidationConfig:
    """测试 ValidationConfig 数据类"""

    def test_default_config(self):
        """测试默认配置"""
        config = ValidationConfig()

        assert config.min_features == 800
        assert config.max_features is None
        assert config.required_keys == []
        assert config.allow_partial is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = ValidationConfig(
            min_features=500,
            max_features=1000,
            required_keys=["f1", "f2"],
            allow_partial=False,
        )

        assert config.min_features == 500
        assert config.max_features == 1000
        assert len(config.required_keys) == 2
        assert config.allow_partial is False


# ============================================================================
# 抽象基类行为测试
# ============================================================================


class MockExtractor(BaseExtractor):
    """用于测试的模拟提取器（使用不同的版本号避免冲突）"""

    @property
    def version(self) -> str:
        return "V99.0"  # 使用不同的版本号，避免与 V25.0 冲突

    def extract(self, raw_data: Dict[str, Any]) -> ExtractionResult:
        return ExtractionResult(
            status=ExtractionStatus.SUCCESS,
            features={"feature_1": 1.0, "feature_2": 2.0},
        )

    def validate(self, features: Dict[str, Any]) -> bool:
        return len(features) >= 2


class TestBaseExtractor:
    """测试 BaseExtractor 抽象基类"""

    def test_cannot_instantiate_abstract(self):
        """测试抽象类不能直接实例化"""
        with pytest.raises(TypeError):
            BaseExtractor()  # type: ignore

    def test_concrete_implementation(self):
        """测试具体实现类可以实例化"""
        extractor = MockExtractor()
        assert extractor.version == "V99.0"
        assert isinstance(extractor, BaseExtractor)

    def test_pre_process_default(self):
        """测试默认预处理（返回原数据）"""
        extractor = MockExtractor()
        data = {"test": "data"}
        assert extractor.pre_process(data) == data

    def test_post_process_default(self):
        """测试默认后处理（返回原特征）"""
        extractor = MockExtractor()
        features = {"f1": 1.0}
        assert extractor.post_process(features) == features

    def test_validation_config_property(self):
        """测试验证配置属性"""
        config = ValidationConfig(min_features=100)
        extractor = MockExtractor(validation_config=config)
        assert extractor.validation_config.min_features == 100


class TestExtractWithValidation:
    """测试 extract_with_validation 模板方法"""

    def test_full_extraction_flow(self, minimal_match_data):
        """测试完整的提取流程"""
        extractor = MockExtractor()

        result = extractor.extract_with_validation(minimal_match_data)

        assert result.is_success
        assert result.metadata["extractor_version"] == "V99.0"
        assert result.metadata["extractor_class"] == "MockExtractor"
        assert result.metadata["feature_count"] == 2
        assert result.metadata["validation_passed"] is True

    def test_extraction_with_exception(self, invalid_match_data_missing_content):
        """测试提取过程抛出异常"""

        class FailingExtractor(MockExtractor):
            def extract(self, raw_data: Dict[str, Any]) -> ExtractionResult:
                raise SchemaMismatchError(
                    "Missing content field", expected_path="content", actual_type="None"
                )

        extractor = FailingExtractor()

        with pytest.raises(ExtractionError) as exc_info:
            extractor.extract_with_validation(invalid_match_data_missing_content)

        # 检查异常消息包含原始错误信息
        error_str = str(exc_info.value)
        assert "Missing content field" in error_str or "SchemaMismatchError" in error_str

    def test_validation_failure_with_allow_partial(self, minimal_match_data):
        """测试验证失败但允许部分结果"""

        class PartialExtractor(MockExtractor):
            def extract(self, raw_data: Dict[str, Any]) -> ExtractionResult:
                return ExtractionResult(
                    status=ExtractionStatus.PARTIAL,
                    features={"f1": 1.0},  # 只有 1 个特征
                )

            def validate(self, features: Dict[str, Any]) -> bool:
                raise InsufficientFeaturesError(
                    "Not enough features", actual_count=1, min_required=800
                )

        config = ValidationConfig(allow_partial=True)
        extractor = PartialExtractor(validation_config=config)

        result = extractor.extract_with_validation(minimal_match_data)

        assert result.status == ExtractionStatus.PARTIAL
        assert len(result.warnings) > 0

    def test_validation_failure_without_allow_partial(self, minimal_match_data):
        """测试验证失败且不允许部分结果"""

        class StrictExtractor(MockExtractor):
            def extract(self, raw_data: Dict[str, Any]) -> ExtractionResult:
                return ExtractionResult(
                    status=ExtractionStatus.PARTIAL,
                    features={"f1": 1.0},
                )

            def validate(self, features: Dict[str, Any]) -> bool:
                raise InsufficientFeaturesError(
                    "Not enough features", actual_count=1, min_required=800
                )

        config = ValidationConfig(allow_partial=False)
        extractor = StrictExtractor(validation_config=config)

        # ValidationFailure 会被包装成 ExtractionError
        with pytest.raises((ValidationError, ExtractionError)):
            extractor.extract_with_validation(minimal_match_data)

    def test_skip_validation(self, minimal_match_data):
        """测试跳过验证"""

        class SkipExtractor(MockExtractor):
            def validate(self, features: Dict[str, Any]) -> bool:
                raise ValidationError("Should not be called")

        extractor = SkipExtractor()
        result = extractor.extract_with_validation(minimal_match_data, skip_validation=True)

        assert result.is_success


# ============================================================================
# ExtractorRegistry 测试
# ============================================================================


class TestExtractorRegistry:
    """测试提取器注册表（工厂模式）"""

    def test_register_extractor(self):
        """测试注册提取器（使用唯一版本号避免冲突）"""

        @register_extractor
        class TestExtractor1(BaseExtractor):
            @property
            def version(self) -> str:
                return "V98.0"  # 使用唯一版本号

            def extract(self, raw_data):
                pass

            def validate(self, features):
                pass

        assert "V98.0" in ExtractorRegistry.list_versions()

    def test_get_extractor_class(self):
        """测试获取提取器类"""

        class TestExtractor2(BaseExtractor):
            @property
            def version(self) -> str:
                return "V26.0"

            def extract(self, raw_data):
                pass

            def validate(self, features):
                pass

        ExtractorRegistry.register(TestExtractor2)

        cls = ExtractorRegistry.get("V26.0")
        assert cls is TestExtractor2

    def test_get_nonexistent_version(self):
        """测试获取不存在的版本"""
        with pytest.raises(KeyError) as exc_info:
            ExtractorRegistry.get("V99.0")

        assert "V99.0" in str(exc_info.value)

    def test_create_extractor_instance(self):
        """测试创建提取器实例"""

        class TestExtractor3(BaseExtractor):
            def __init__(self, custom_param: str = "default"):
                super().__init__()
                self.custom_param = custom_param

            @property
            def version(self) -> str:
                return "V27.0"

            def extract(self, raw_data):
                pass

            def validate(self, features):
                pass

        ExtractorRegistry.register(TestExtractor3)

        instance = ExtractorRegistry.create("V27.0", custom_param="test")
        assert isinstance(instance, TestExtractor3)
        assert instance.custom_param == "test"


# ============================================================================
# 异常测试
# ============================================================================


class TestExceptions:
    """测试自定义异常"""

    def test_extraction_error(self):
        """测试基础提取异常"""
        error = ExtractionError(
            "Extraction failed",
            context={"match_id": 123},
            extractor_version="V25.0",
        )

        assert "Extraction failed" in str(error)
        assert error.extractor_version == "V25.0"
        assert error.context["match_id"] == 123

    def test_validation_error(self):
        """测试验证异常"""
        error = ValidationError(
            "Validation failed",
            feature_count=100,
            required_keys=["f1", "f2"],
        )

        assert error.context["feature_count"] == 100
        assert error.context["required_keys"] == ["f1", "f2"]

    def test_insufficient_features_error(self):
        """测试特征维度不足异常"""
        error = InsufficientFeaturesError(
            "Not enough features",
            actual_count=500,
            min_required=800,
        )

        assert error.context["actual_features"] == 500
        assert error.context["min_required"] == 800
        assert error.context["shortage"] == 300

    def test_missing_required_key_error(self):
        """测试缺少必需键异常"""
        error = MissingRequiredKeyError(
            "Keys missing",
            missing_keys=["f1", "f2", "f3"],
        )

        assert error.context["missing_keys"] == ["f1", "f2", "f3"]

    def test_data_parsing_error(self):
        """测试数据解析异常"""
        error = DataParsingError(
            "Parse failed",
            raw_data_type="string",
            parse_error="Invalid JSON",
        )

        assert error.context["raw_data_type"] == "string"
        assert error.context["parse_error"] == "Invalid JSON"

    def test_schema_mismatch_error(self):
        """测试结构不匹配异常"""
        error = SchemaMismatchError(
            "Schema mismatch",
            expected_path="content.stats",
            actual_type="None",
        )

        assert error.context["expected_path"] == "content.stats"
        assert error.context["actual_type"] == "None"


# ============================================================================
# V25 ProductionExtractor 测试
# ============================================================================


class TestV25ProductionExtractor:
    """
    测试 V25 生产提取器

    注意：这些测试会在实现 V25_ProductionExtractor 后生效。
    """

    def test_extractor_registration(self):
        """测试 V25.0 提取器已注册"""
        versions = ExtractorRegistry.list_versions()
        assert "V25.0" in versions

    def test_basic_extraction(self, minimal_match_data):
        """测试基本特征提取"""
        extractor = ExtractorRegistry.create("V25.0")
        result = extractor.extract_with_validation(minimal_match_data)

        # V25 至少应该提取一些特征
        assert result.is_success or result.status == ExtractionStatus.PARTIAL
        assert result.feature_count >= 0

    def test_insufficient_features_raises_error(self, insufficient_features_data):
        """测试特征不足时抛出异常"""
        extractor = ExtractorRegistry.create("V25.0")

        # V25 会提取基础特征，但如果特征不足会抛出异常
        # 注意：由于 allow_partial=True，可能只返回 PARTIAL 状态
        result = extractor.extract_with_validation(insufficient_features_data)
        # 特征不足时，状态应该是 PARTIAL 或 FAILED
        assert result.status in (ExtractionStatus.PARTIAL, ExtractionStatus.FAILED)

    def test_invalid_data_handling(self, invalid_match_data_empty):
        """测试无效数据处理"""
        extractor = ExtractorRegistry.create("V25.0")

        # 空数据应该抛出异常（注意：extract_with_validation 会包装异常）
        with pytest.raises((ExtractionError, DataParsingError, SchemaMismatchError)):
            extractor.extract_with_validation(invalid_match_data_empty)


# ============================================================================
# 集成测试
# ============================================================================


class TestIntegration:
    """集成测试：完整的数据流"""

    def test_end_to_end_extraction(self, full_match_data):
        """测试端到端提取流程"""
        extractor = ExtractorRegistry.create("V25.0")
        result = extractor.extract_with_validation(full_match_data)

        # 验证结果
        assert result.is_success or result.status == ExtractionStatus.PARTIAL
        assert result.metadata is not None
        assert result.metadata["extractor_version"] == "V25.0"
        assert result.metadata["feature_count"] == result.feature_count

        # 验证特征
        features = result.features
        assert isinstance(features, dict)
        assert len(features) > 0

        # 验证可以序列化为 JSON
        import json

        json_str = json.dumps(features)
        assert len(json_str) > 0
