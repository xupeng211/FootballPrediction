#!/usr/bin/env python3
"""
L2 特征提取器 - TDD 测试套件 (V25.1 自适应版)
===============================================

测试驱动开发 (TDD) 流程:
    1. 编写测试（本文件）
    2. 运行测试（失败）
    3. 实现功能
    4. 运行测试（通过）

V25.1 测试策略:
    - 不再验证固定特征键（如 home_possession）
    - 验证自适应提取能力（元数据、特征维度、递归打平）
    - 验证全局特征对齐机制
    - 验证类型转换智能性

Author: Architecture Team
Version: V25.1
Date: 2025-12-26
"""

from typing import Any

import pytest

# V4.13: 更新为 legacy 路径
from src.ml.feature_engine.legacy.base_extractor import (
    BaseExtractor,
    ExtractionResult,
    ExtractionStatus,
    ExtractorRegistry,
    ValidationConfig,
    register_extractor,
)
from src.ml.feature_engine.legacy.exceptions import (
    DataParsingError,
    ExtractionError,
    InsufficientFeaturesError,
    SchemaMismatchError,
    ValidationError,
)

# 导入 V25.1 提取器以确保注册
from src.ml.feature_engine.legacy.v25_production_extractor import (
    V25ProductionExtractor,
    _fully_flatten,
    _parse_value,
    _sanitize_key,
    get_global_feature_keys,
)

# ============================================================================
# 测试数据夹具
# ============================================================================


@pytest.fixture
def minimal_match_data() -> dict[str, Any]:
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
def complex_nested_data() -> dict[str, Any]:
    """
    复杂嵌套数据（测试递归打平能力）
    """
    return {
        "level1": {
            "level2": {
                "level3": {
                    "numeric": 42,
                    "string": "test",
                    "boolean": True,
                    "percentage": "75%",
                    "nested_list": [1, 2, 3, 4, 5],
                }
            },
            "array": [{"id": 1, "value": "a"}, {"id": 2, "value": "b"}, {"id": 3, "value": "c"}],
        },
        "simple_list": [10, 20, 30, 40, 50],
        "mixed_types": {
            "int": 100,
            "float": 3.14,
            "bool": False,
            "percent": "61%",
            "parenthesized": "1.34 (79%)",
            "empty": None,
            "dash": "-",
        },
    }


@pytest.fixture
def full_match_data() -> dict[str, Any]:
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
            },
        },
        "l2_json": {},
    }


@pytest.fixture
def invalid_match_data_missing_content() -> dict[str, Any]:
    """无效数据：缺少 content 字段"""
    return {"l2_json": {}, "other_field": "value"}


@pytest.fixture
def invalid_match_data_empty() -> dict[str, Any]:
    """无效数据：空字典"""
    return {}


@pytest.fixture
def invalid_match_data_malformed_json() -> dict[str, Any]:
    """无效数据：格式错误的 JSON 结构"""
    return {"content": "not_a_dict"}


# ============================================================================
# 核心工具函数测试
# ============================================================================


class TestParseValue:
    """测试 _parse_value 智能类型转换"""

    def test_integer(self):
        """测试整数转换"""
        assert _parse_value(42) == 42.0
        assert _parse_value(0) == 0.0
        assert _parse_value(-100) == -100.0

    def test_float(self):
        """测试浮点数转换"""
        assert _parse_value(3.14) == 3.14
        assert _parse_value(0.0) == 0.0
        assert _parse_value(-2.5) == -2.5

    def test_nan(self):
        """测试 NaN 处理"""

        assert _parse_value(float("nan")) is None

    def test_boolean(self):
        """测试布尔值转换"""
        assert _parse_value(True) == 1.0
        assert _parse_value(False) == 0.0

    def test_percentage_string(self):
        """测试百分比字符串转换"""
        assert _parse_value("61%") == 0.61
        assert _parse_value("100%") == 1.0
        assert _parse_value("0%") == 0.0
        assert _parse_value("75.5%") == 0.755

    def test_parenthesized_percentage(self):
        """测试带括号的百分比"""
        assert _parse_value("1.34 (79%)") == 1.34
        assert _parse_value("61 (79%)") == 61.0

    def test_numeric_string(self):
        """测试纯数字字符串"""
        assert _parse_value("42") == 42.0
        assert _parse_value("3.14") == 3.14
        assert _parse_value("-100") == -100.0

    def test_none_and_empty(self):
        """测试 None 和空值"""
        assert _parse_value(None) is None
        assert _parse_value("") is None
        assert _parse_value("-") is None

    def test_invalid_string(self):
        """测试无效字符串"""
        assert _parse_value("not_a_number") is None
        # 注意：abc123def 会被清理为 123（这是设计意图 - 从混合字符串提取数字）
        assert _parse_value("abc123def") == 123.0


class TestSanitizeKey:
    """测试 _sanitize_key 键名清理"""

    def test_basic_sanitize(self):
        """测试基本清理"""
        assert _sanitize_key("BallPossesion") == "ballpossesion"
        assert _sanitize_key("home_team") == "home_team"
        assert _sanitize_key("Away-Team") == "away_team"

    def test_special_characters(self):
        """测试特殊字符处理"""
        assert _sanitize_key("test.key") == "test.key"
        assert _sanitize_key("test key") == "test_key"
        assert _sanitize_key("test-key") == "test_key"
        assert _sanitize_key("test@key") == "test_key"

    def test_multiple_underscores(self):
        """测试多个下划线合并"""
        assert _sanitize_key("test__key") == "test_key"
        assert _sanitize_key("test___key") == "test_key"
        assert _sanitize_key("test - key") == "test_key"

    def test_leading_trailing_underscores(self):
        """测试首尾下划线去除"""
        assert _sanitize_key("_test") == "test"
        assert _sanitize_key("test_") == "test"
        assert _sanitize_key("__test__") == "test"


class TestFullyFlatten:
    """测试 _fully_flatten 递归打平算法"""

    def test_flat_dict(self):
        """测试扁平字典"""
        data = {"a": 1, "b": 2, "c": 3}
        result = _fully_flatten(data)
        assert result == {"a": 1.0, "b": 2.0, "c": 3.0}

    def test_nested_dict(self):
        """测试嵌套字典"""
        data = {"level1": {"level2": {"level3": 42}}}
        result = _fully_flatten(data)
        assert "level1_level2_level3" in result
        assert result["level1_level2_level3"] == 42.0

    def test_numeric_list(self):
        """测试纯数值列表（自动计算统计特征）"""
        data = {"values": [1, 2, 3, 4, 5]}
        result = _fully_flatten(data)

        # 验证统计特征
        assert "values_mean" in result
        assert "values_std" in result
        assert "values_min" in result
        assert "values_max" in result
        assert "values_sum" in result
        assert "values_len" in result

        assert result["values_mean"] == 3.0
        assert result["values_min"] == 1.0
        assert result["values_max"] == 5.0
        assert result["values_sum"] == 15.0
        assert result["values_len"] == 5

    def test_dict_list(self):
        """测试字典列表"""
        data = {"items": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]}
        result = _fully_flatten(data)

        # 验证路径命名
        assert "items_0_id" in result
        assert "items_0_name" in result
        assert "items_1_id" in result
        assert "items_1_name" in result

    def test_complex_nesting(self, complex_nested_data):
        """测试复杂嵌套结构"""
        result = _fully_flatten(complex_nested_data)

        # 验证深度嵌套
        assert "level1_level2_level3_numeric" in result
        assert result["level1_level2_level3_numeric"] == 42.0

        # 验证布尔转换
        assert "level1_level2_level3_boolean" in result
        assert result["level1_level2_level3_boolean"] == 1.0

        # 验证百分比转换
        assert "level1_level2_level3_percentage" in result
        assert result["level1_level2_level3_percentage"] == 0.75

        # 验证列表统计
        assert "level1_level2_level3_nested_list_mean" in result
        assert "level1_level2_level3_nested_list_len" in result

    def test_max_depth_protection(self):
        """测试最大递归深度保护"""
        # 创建深度嵌套结构
        data = {}
        current = data
        for i in range(30):
            current[f"level{i}"] = {}
            current = current[f"level{i}"]
        current["value"] = 42

        # 限制深度为 10
        result = _fully_flatten(data, max_depth=10)
        # 超过深度的数据应该不会被提取
        assert len(result) < 30

    def test_type_conversion(self):
        """测试类型转换集成"""
        data = {
            "int_val": 42,
            "float_val": 3.14,
            "bool_val": True,
            "percent_val": "75%",
            "nested": {"bool_false": False},
        }
        result = _fully_flatten(data)

        assert result["int_val"] == 42.0
        assert result["float_val"] == 3.14
        assert result["bool_val"] == 1.0
        assert result["percent_val"] == 0.75
        assert result["nested_bool_false"] == 0.0


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
            metadata={"version": "V25.1"},
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
        return "V99.0"  # 使用不同的版本号，避免与 V25.1 冲突

    def extract(self, raw_data: dict[str, Any]) -> ExtractionResult:
        return ExtractionResult(
            status=ExtractionStatus.SUCCESS,
            features={"feature_1": 1.0, "feature_2": 2.0},
        )

    def validate(self, features: dict[str, Any]) -> bool:
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
            def extract(self, raw_data: dict[str, Any]) -> ExtractionResult:
                raise SchemaMismatchError(
                    "Missing content field", expected_path="content", actual_type="None"
                )

        extractor = FailingExtractor()

        with pytest.raises(ExtractionError) as exc_info:
            extractor.extract_with_validation(invalid_match_data_missing_content)

        # 检查异常消息包含原始错误信息
        error_str = str(exc_info.value)
        assert "Missing content field" in error_str or "SchemaMismatchError" in error_str

    def test_skip_validation(self, minimal_match_data):
        """测试跳过验证"""

        class SkipExtractor(MockExtractor):
            def validate(self, features: dict[str, Any]) -> bool:
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
            extractor_version="V25.1",
        )

        assert "Extraction failed" in str(error)
        assert error.extractor_version == "V25.1"
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


# ============================================================================
# V25.1 ProductionExtractor 测试
# ============================================================================


class TestV25ProductionExtractor:
    """
    测试 V25.1 生产提取器（自适应版本）

    V25.1 核心能力验证:
        1. 递归打平 - 自动处理任意深度嵌套
        2. 全量吞噬 - 提取所有数值型因子
        3. 元数据完整 - 包含 extraction_version, feature_count 等
        4. 特征维度 - 应该远超 V25.0 的 48 维
    """

    def test_extractor_registration(self):
        """测试 V25.1 提取器已注册"""
        versions = ExtractorRegistry.list_versions()
        assert "V25.1" in versions

    def test_extractor_version(self):
        """测试提取器版本号"""
        extractor = V25ProductionExtractor()
        assert extractor.version == "V25.1"

    def test_adaptive_extraction(self, minimal_match_data):
        """测试自适应特征提取（不依赖固定键）"""
        extractor = V25ProductionExtractor()
        result = extractor.extract_with_validation(minimal_match_data)

        # V25.1 应该成功提取特征
        assert result.is_success or result.status == ExtractionStatus.PARTIAL

        # V25.1 应该提取大量特征（远超 V25.0 的 48 维）
        assert result.feature_count >= 20  # 最小数据也应有 20+ 特征

    def test_metadata_present(self, minimal_match_data):
        """测试元数据存在性"""
        extractor = V25ProductionExtractor()
        result = extractor.extract_with_validation(minimal_match_data)

        # 验证元数据键存在
        assert "_meta" in result.features
        meta = result.features["_meta"]

        # 验证元数据字段
        assert "extraction_version" in meta
        assert "extraction_timestamp" in meta
        assert "feature_count" in meta
        assert "numeric_count" in meta
        assert "string_count" in meta

        # 验证版本号
        assert meta["extraction_version"] == "V25.1"

    def test_recursive_flatten_complex_data(self, complex_nested_data):
        """测试复杂数据的递归打平"""
        extractor = V25ProductionExtractor()
        result = extractor.extract_with_validation(complex_nested_data)

        # 验证成功提取
        assert result.is_success

        # 验证特征数量（复杂数据应该产生大量特征）
        assert result.feature_count >= 30  # 复杂嵌套应该产生 30+ 特征

        # 验证路径式命名
        features = result.features
        assert "level1_level2_level3_numeric" in features
        assert "level1_level2_level3_percentage" in features

    def test_global_feature_alignment(self, minimal_match_data):
        """测试全局特征对齐机制"""
        # 清空全局注册表
        from src.processors.v25_production_extractor import _GLOBAL_FEATURE_KEYS

        _GLOBAL_FEATURE_KEYS.clear()

        # 第一次提取
        extractor1 = V25ProductionExtractor()
        result1 = extractor1.extract_with_validation(minimal_match_data)
        set(k for k in result1.features.keys() if not k.startswith("_"))

        # 第二次提取（不同数据）
        different_data = {
            "content": {
                "match": {"matchId": 999},
                "stats": {"Periods": {"All": {"stats": [{"key": "custom_stat", "stats": [1, 2]}]}}},
            }
        }
        extractor2 = V25ProductionExtractor()
        extractor2.extract_with_validation(different_data)

        # 验证全局注册表增长
        global_keys = get_global_feature_keys()
        assert len(global_keys) > 0

    def test_insufficient_features_handling(self, invalid_match_data_empty):
        """测试特征不足处理"""
        extractor = V25ProductionExtractor()

        # 空数据应该抛出异常
        with pytest.raises((ExtractionError, DataParsingError)):
            extractor.extract_with_validation(invalid_match_data_empty)

    def test_numeric_string_features_count(self, minimal_match_data):
        """测试数值特征和字符串特征分类"""
        extractor = V25ProductionExtractor()
        result = extractor.extract_with_validation(minimal_match_data)

        meta = result.features.get("_meta", {})
        numeric_count = meta.get("numeric_count", 0)
        string_count = meta.get("string_count", 0)

        # 验证分类统计
        assert numeric_count > 0
        assert string_count >= 0
        assert numeric_count + string_count <= result.feature_count


# ============================================================================
# 集成测试
# ============================================================================


class TestIntegration:
    """集成测试：完整的数据流"""

    def test_end_to_end_extraction(self, full_match_data):
        """测试端到端提取流程"""
        extractor = ExtractorRegistry.create("V25.1")
        result = extractor.extract_with_validation(full_match_data)

        # 验证结果
        assert result.is_success or result.status == ExtractionStatus.PARTIAL
        assert result.metadata is not None
        assert result.metadata["extractor_version"] == "V25.1"
        assert result.metadata["feature_count"] == result.feature_count

        # 验证特征
        features = result.features
        assert isinstance(features, dict)
        assert len(features) > 0

        # 验证元数据
        assert "_meta" in features
        assert features["_meta"]["extraction_version"] == "V25.1"

        # 验证可以序列化为 JSON
        import json

        json_str = json.dumps(features)
        assert len(json_str) > 0

    def test_adaptive_dimension_scaling(self, full_match_data):
        """测试自适应维度扩展能力"""
        extractor = V25ProductionExtractor()
        result = extractor.extract_with_validation(full_match_data)

        # V25.1 应该提取大量特征（自适应吞噬）
        # 完整数据应该产生 100+ 特征
        assert result.feature_count >= 50, (
            f"V25.1 自适应引擎应该提取至少 50 个特征，实际: {result.feature_count}"
        )

    def test_feature_key_consistency(self, minimal_match_data):
        """测试特征键一致性（路径命名规范）"""
        extractor = V25ProductionExtractor()
        result = extractor.extract_with_validation(minimal_match_data)

        # 所有特征键应该是小写、只包含字母数字下划线和点
        import re

        for key in result.features.keys():
            # 元数据键可以包含下划线和点
            if key.startswith("_"):
                continue
            # 验证键名格式
            assert re.match(r"^[a-z0-9._]+$", key), f"特征键 '{key}' 不符合命名规范"
