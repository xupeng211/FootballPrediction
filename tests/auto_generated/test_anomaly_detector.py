"""
Auto-generated tests for src.monitoring.anomaly_detector module
"""

import pytest
from src.monitoring.anomaly_detector import AnomalyType, AnomalySeverity


class TestAnomalyType:
    """测试异常类型枚举"""

    def test_anomaly_type_values(self):
        """测试异常类型值"""
        assert AnomalyType.OUTLIER.value == "outlier"
        assert AnomalyType.TREND_CHANGE.value == "trend_change"
        assert AnomalyType.PATTERN_BREAK.value == "pattern_break"
        assert AnomalyType.VALUE_RANGE.value == "value_range"
        assert AnomalyType.FREQUENCY.value == "frequency"
        assert AnomalyType.NULL_SPIKE.value == "null_spike"

    def test_anomaly_type_iterable(self):
        """测试异常类型可迭代"""
        types = list(AnomalyType)
        assert len(types) == 6
        assert AnomalyType.OUTLIER in types
        assert AnomalyType.TREND_CHANGE in types
        assert AnomalyType.PATTERN_BREAK in types
        assert AnomalyType.VALUE_RANGE in types
        assert AnomalyType.FREQUENCY in types
        assert AnomalyType.NULL_SPIKE in types

    def test_anomaly_type_uniqueness(self):
        """测试异常类型值唯一性"""
        values = [t.value for t in AnomalyType]
        assert len(values) == len(set(values)), "AnomalyType values should be unique"

    @pytest.mark.parametrize("anomaly_type,expected_value", [
        (AnomalyType.OUTLIER, "outlier"),
        (AnomalyType.TREND_CHANGE, "trend_change"),
        (AnomalyType.PATTERN_BREAK, "pattern_break"),
        (AnomalyType.VALUE_RANGE, "value_range"),
        (AnomalyType.FREQUENCY, "frequency"),
        (AnomalyType.NULL_SPIKE, "null_spike"),
    ])
    def test_anomaly_type_parametrized(self, anomaly_type, expected_value):
        """测试异常类型参数化"""
        assert anomaly_type.value == expected_value


class TestAnomalySeverity:
    """测试异常严重程度枚举"""

    def test_anomaly_severity_values(self):
        """测试异常严重程度值"""
        assert AnomalySeverity.LOW.value == "low"
        assert AnomalySeverity.MEDIUM.value == "medium"
        assert AnomalySeverity.HIGH.value == "high"
        assert AnomalySeverity.CRITICAL.value == "critical"

    def test_anomaly_severity_iterable(self):
        """测试异常严重程度可迭代"""
        severities = list(AnomalySeverity)
        assert len(severities) == 4
        assert AnomalySeverity.LOW in severities
        assert AnomalySeverity.MEDIUM in severities
        assert AnomalySeverity.HIGH in severities
        assert AnomalySeverity.CRITICAL in severities

    def test_anomaly_severity_ordering(self):
        """测试异常严重程度逻辑顺序"""
        # 严重程度应该有逻辑顺序
        severities = list(AnomalySeverity)
        # 确保所有预期的严重程度都存在
        expected_severities = [AnomalySeverity.LOW, AnomalySeverity.MEDIUM,
                              AnomalySeverity.HIGH, AnomalySeverity.CRITICAL]
        for severity in expected_severities:
            assert severity in severities

    def test_anomaly_severity_uniqueness(self):
        """测试异常严重程度值唯一性"""
        values = [s.value for s in AnomalySeverity]
        assert len(values) == len(set(values)), "AnomalySeverity values should be unique"

    @pytest.mark.parametrize("severity,expected_value", [
        (AnomalySeverity.LOW, "low"),
        (AnomalySeverity.MEDIUM, "medium"),
        (AnomalySeverity.HIGH, "high"),
        (AnomalySeverity.CRITICAL, "critical"),
    ])
    def test_anomaly_severity_parametrized(self, severity, expected_value):
        """测试异常严重程度参数化"""
        assert severity.value == expected_value


class TestAnomalyEnumsIntegration:
    """测试异常枚举集成"""

    def test_enum_instantiation(self):
        """测试枚举实例化"""
        # 测试可以创建枚举实例
        outlier_type = AnomalyType.OUTLIER
        critical_severity = AnomalySeverity.CRITICAL

        assert isinstance(outlier_type, AnomalyType)
        assert isinstance(critical_severity, AnomalySeverity)

    def test_enum_comparison(self):
        """测试枚举比较"""
        # 测试枚举比较
        assert AnomalyType.OUTLIER == AnomalyType.OUTLIER
        assert AnomalyType.OUTLIER != AnomalyType.TREND_CHANGE
        assert AnomalySeverity.LOW != AnomalySeverity.HIGH

    def test_enum_usage_in_collections(self):
        """测试枚举在集合中的使用"""
        # 测试在集合中使用枚举
        types_set = {AnomalyType.OUTLIER, AnomalyType.TREND_CHANGE}
        severities_list = [AnomalySeverity.LOW, AnomalySeverity.MEDIUM, AnomalySeverity.HIGH]

        assert AnomalyType.OUTLIER in types_set
        assert AnomalyType.PATTERN_BREAK not in types_set
        assert AnomalySeverity.MEDIUM in severities_list
        assert AnomalySeverity.CRITICAL not in severities_list

    def test_enum_string_representation(self):
        """测试枚举字符串表示"""
        # 测试枚举的字符串表示
        assert str(AnomalyType.OUTLIER) == "AnomalyType.OUTLIER"
        assert repr(AnomalySeverity.CRITICAL) == "<AnomalySeverity.CRITICAL: 'critical'>"
        assert f"Type: {AnomalyType.FREQUENCY}" == "Type: AnomalyType.FREQUENCY"

    def test_enum_access_patterns(self):
        """测试枚举访问模式"""
        # 测试不同的枚举访问方式
        # 通过成员访问
        type1 = AnomalyType.OUTLIER
        # 通过值访问
        type2 = AnomalyType("outlier")

        assert type1 == type2

        # 测试迭代访问
        all_types = []
        for severity in AnomalySeverity:
            all_types.append(severity.value)

        assert len(all_types) == 4
        assert "low" in all_types
        assert "critical" in all_types

    def test_enum_with_real_world_scenarios(self):
        """测试枚举的实际使用场景"""
        # 模拟实际使用场景
        anomaly_config = {
            "detection_types": [
                AnomalyType.OUTLIER,
                AnomalyType.TREND_CHANGE,
                AnomalyType.VALUE_RANGE
            ],
            "severity_threshold": AnomalySeverity.HIGH,
            "alert_severities": [
                AnomalySeverity.MEDIUM,
                AnomalySeverity.HIGH,
                AnomalySeverity.CRITICAL
            ]
        }

        assert len(anomaly_config["detection_types"]) == 3
        assert anomaly_config["severity_threshold"] == AnomalySeverity.HIGH
        assert len(anomaly_config["alert_severities"]) == 3
        assert AnomalySeverity.LOW not in anomaly_config["alert_severities"]

    def test_enum_error_handling(self):
        """测试枚举错误处理"""
        # 测试无效值处理
        with pytest.raises(ValueError):
            AnomalyType("invalid_type")

        with pytest.raises(ValueError):
            AnomalySeverity("invalid_severity")

    def test_enum_attribute_access(self):
        """测试枚举属性访问"""
        # 测试枚举属性
        outlier = AnomalyType.OUTLIER
        assert outlier.name == "OUTLIER"
        assert outlier.value == "outlier"

        critical = AnomalySeverity.CRITICAL
        assert critical.name == "CRITICAL"
        assert critical.value == "critical"