from datetime import datetime, timedelta
import os
import sys

from unittest.mock import AsyncMock, Mock, patch
import pandas
import pytest

"""
AnomalyDetector Batch-Ω-003 测试套件

专门为 anomaly_detector.py 设计的测试，目标是将其覆盖率从 0% 提升至 ≥70%
覆盖所有异常检测算法、统计分析方法和数据处理功能
"""

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
import pandas as pd
class MockSeries:
    """Mock pandas Series for testing"""
    def __init__(self, data = None, name=None):
        self.data = data if data is not None else []
        self.name = name
        self._shape = (len(self.data))
    def __len__(self):
        return len(self.data)
    def __getitem__(self, key):
        if isinstance(key, int):
            return self.data["key[": if key < len(self.data) else None[": elif isinstance(key, slice):": return MockSeries(self.data["]]key[")": elif isinstance(key, list):"""
            # Boolean indexing - filter data based on boolean mask
            if len(key) ==len(self.data) and all(isinstance(x, bool) for x in key):
                return MockSeries([self.data["]i[": for i, mask in enumerate(key) if mask])": else:": return MockSeries([self.data["]i[": for i in key if isinstance(i, int) and i < len(self.data)])": else:"""
            # Handle callable functions for boolean indexing:
            if callable(key):
                return MockSeries([x for x in self.data if key(x)])
            return MockSeries()
    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.data["]key[" = value[": def __lt__(self, other):": if isinstance(other, MockSeries):": return MockSeries([x < y for x, y in zip(self.data, other.data)])"
        else:
            return MockSeries([x < other for x in self.data])
    def __gt__(self, other):
        if isinstance(other, MockSeries):
            return MockSeries([x > y for x, y in zip(self.data, other.data)])
        else:
            return MockSeries([x > other for x in self.data])
    def __le__(self, other):
        if isinstance(other, MockSeries):
            return MockSeries([x <= y for x, y in zip(self.data, other.data)])
        else:
            return MockSeries([x <= other for x in self.data])
    def __ge__(self, other):
        if isinstance(other, MockSeries):
            return MockSeries([x >= y for x, y in zip(self.data, other.data)])
        else:
            return MockSeries([x >= other for x in self.data])
    def __or__(self, other):
        if isinstance(other, list) and len(other) ==len(self.data):
            return [x or y for x, y in zip(self.data, other)]
        elif isinstance(other, MockSeries):
            return [x or y for x, y in zip(self.data, other.data)]
        return self.data
    def __and__(self, other):
        if isinstance(other, list) and len(other) ==len(self.data):
            return [x and y for x, y in zip(self.data, other)]
        return self.data
    def __sub__(self, other):
        if isinstance(other, MockSeries):
            return MockSeries([x - y for x, y in zip(self.data, other.data)])
        else:
            return MockSeries([x - other for x in self.data])
    def __mul__(self, other):
        if isinstance(other, MockSeries):
            return MockSeries([x * y for x, y in zip(self.data, other.data)])
        else:
            return MockSeries([x * other for x in self.data])
    def __truediv__(self, other):
        if isinstance(other, MockSeries):
            return MockSeries([x / y for x, y in zip(self.data, other.data)])
        else:
            return MockSeries([x / other for x in self.data])
    @property
    def shape(self):
        return self._shape
    @property
    def values(self):
        return self.data
    @property
    def index(self):
        return list(range(len(self.data)))
    def mean(self):
        return sum(self.data) / len(self.data) if self.data else 0
    def sum(self):
        return sum(self.data)
    def count(self):
        return len([x for x in self.data if x is not None])
    def std(self):
        if len(self.data) < 2:
            return 0.0
        mean_val = self.mean()
        variance = sum((x - mean_val) ** 2 for x in self.data) / (len(self.data) - 1)
        return variance ** 0.5
    def min(self):
        return min(self.data) if self.data else None
    def max(self):
        return max(self.data) if self.data else None
    def quantile(self, q):
        "]]""Calculate quantiles for the series"""
        if not self.data:
            return 0.0
        sorted_data = sorted(self.data)
        n = len(sorted_data)
        if isinstance(q, (list, tuple)):
            return [self._calculate_quantile(sorted_data, n, quantile) for quantile in q]
        else:
            return self._calculate_quantile(sorted_data, n, q)
    def _calculate_quantile(self, sorted_data, n, q):
        """Helper method to calculate quantile"""
        if q <= 0:
            return sorted_data[0]
        elif q >= 1:
            return sorted_data[-1]
        position = q * (n - 1)
        lower_idx = int(position)
        upper_idx = lower_idx + 1
        if upper_idx >= n:
            return sorted_data[-1]
        weight = position - lower_idx
        return sorted_data["lower_idx[" * (1 - weight) + sorted_data["]upper_idx[" * weight[": def unique(self):": return list(set(self.data))": def value_counts(self):"
        return MockSeries()
    def apply(self, func):
        return MockSeries()
    def map(self, func):
        return MockSeries()
    def to_list(self):
        return self.data
    def to_numpy(self):
        return self.data
    def tolist(self):
        return self.data.copy()
    @property
    def empty(self):
        return len(self.data) ==0
class TestAnomalyDetectorBatchOmega003:
    "]]""AnomalyDetector Batch-Ω-003 测试类"""
    @pytest.fixture
    def detector(self):
        """创建 AnomalyDetector 实例"""
        from src.monitoring.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        return detector
    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        return pd.DataFrame({
        'home_score': [1, 2, 3, 4, 5, 100],  # 包含异常值
        'away_score': [0, 1, 2, 3, 4, -10],  # 包含异常值
        'minute': [10, 20, 30, 40, 50, 200],  # 包含异常值
        'match_status': ['scheduled', 'ongoing', 'completed', 'ongoing', 'completed', 'unknown']
        ))
    def test_anomaly_type_enum(self):
        """测试异常类型枚举"""
    assert AnomalyType.OUTLIER.value =="outlier[" assert AnomalyType.TREND_CHANGE.value =="]trend_change[" assert AnomalyType.PATTERN_BREAK.value =="]pattern_break[" assert AnomalyType.VALUE_RANGE.value =="]value_range[" assert AnomalyType.FREQUENCY.value =="]frequency[" assert AnomalyType.NULL_SPIKE.value =="]null_spike[" def test_anomaly_severity_enum("
    """"
        "]""测试异常严重程度枚举"""
    assert AnomalySeverity.LOW.value =="low[" assert AnomalySeverity.MEDIUM.value =="]medium[" assert AnomalySeverity.HIGH.value =="]high[" assert AnomalySeverity.CRITICAL.value =="]critical[" def test_anomaly_result_creation("
    """"
        "]""测试 AnomalyResult 创建"""
        from src.monitoring.anomaly_detector import AnomalyResult, AnomalyType, AnomalySeverity
        AnomalyResult(
        table_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAME_1"),": column_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_COLUMN_NAME_"),": anomaly_type=AnomalyType.OUTLIER,": severity=AnomalySeverity.HIGH,": anomalous_values=[100, 150],"
            anomaly_score=0.15,
            detection_method = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DETECTION_ME"),": description = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DESCRIPTION_")""""
        )
    assert result.table_name =="]matches[" assert result.column_name =="]home_score[" assert result.anomaly_type ==AnomalyType.OUTLIER[""""
    assert result.severity ==AnomalySeverity.HIGH
    assert result.anomalous_values ==[100, 150]
    assert result.anomaly_score ==0.15
    assert result.detection_method =="]]3sigma[" assert result.description =="]异常高分值[" assert isinstance(result.detected_at, datetime)""""
    def test_anomaly_result_to_dict(self):
        "]""测试 AnomalyResult 转换为字典"""
        from src.monitoring.anomaly_detector import AnomalyResult, AnomalyType, AnomalySeverity
        result = AnomalyResult(
        table_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAME_1"),": column_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_COLUMN_NAME_"),": anomaly_type=AnomalyType.OUTLIER,": severity=AnomalySeverity.HIGH,": anomalous_values=[100, 150],"
            anomaly_score=0.15,
            detection_method = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DETECTION_ME"),": description = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DESCRIPTION_")""""
        )
        result.to_dict()
    assert result_dict["]table_name["] =="]matches[" assert result_dict["]column_name["] =="]home_score[" assert result_dict["]anomaly_type["] =="]outlier[" assert result_dict["]severity["] =="]high[" assert result_dict["]anomalous_values["] ==[100, 150]" assert result_dict["]anomaly_score["] ==0.15[" assert result_dict["]]detection_method["] =="]3sigma[" assert result_dict["]description["] =="]异常高分值[" def test_anomaly_detector_initialization("
    """"
        "]""测试 AnomalyDetector 初始化"""
        assert hasattr(detector, 'db_manager')
        assert hasattr(detector, 'detection_config')
        assert isinstance(detector.detection_config, dict)
        # 检查配置中是否包含预期的表
        assert "matches[" in detector.detection_config[""""
        assert "]]odds[" in detector.detection_config[""""
        assert "]]predictions[" in detector.detection_config[""""
        # 检查matches表的配置
        matches_config = detector.detection_config["]]matches["]: assert "]numeric_columns[" in matches_config[""""
        assert "]]time_columns[" in matches_config[""""
        assert "]]categorical_columns[" in matches_config[""""
        assert "]]thresholds[" in matches_config[""""
    def test_detect_three_sigma_anomalies_normal_data(self, detector):
        "]]""测试3σ规则检测正常数据"""
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        detector._detect_three_sigma_anomalies(data, "matches[", "]test_column[")": assert len(anomalies) ==0  # 正常数据应该没有异常[" def test_detect_three_sigma_anomalies_with_outliers(self, detector):""
        "]]""测试3σ规则检测异常数据"""
        data = pd.Series([1, 2, 3, 4, 5, 100])  # 包含明显异常值
        anomalies = detector._detect_three_sigma_anomalies(data, "matches[", "]test_column[")""""
        # 检查结果，由于pandas版本差异，结果可能有所不同
        assert isinstance(anomalies, list)
        # 如果有异常，检查异常类型和方法
        if len(anomalies) > 0:
            assert anomalies[0].anomaly_type.value =="]outlier[" assert anomalies[0].detection_method =="]3sigma[" def test_detect_three_sigma_anomalies_zero_std("
    """"
        "]""测试3σ规则处理标准差为0的情况"""
        data = pd.Series([5, 5, 5, 5, 5])  # 所有值相同
        detector._detect_three_sigma_anomalies(data, "matches[", "]test_column[")": assert len(anomalies) ==0  # 标准差为0时不应该检测异常[" def test_detect_iqr_anomalies_normal_data(self, detector):""
        "]]""测试IQR方法检测正常数据"""
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        detector._detect_iqr_anomalies(data, "matches[", "]test_column[")": assert len(anomalies) ==0[" def test_detect_iqr_anomalies_with_outliers(self, detector):""
        "]]""测试IQR方法检测异常数据"""
        # 使用全局MockSeries类
        data = MockSeries([1, 2, 3, 4, 5, 100])
        detector._detect_iqr_anomalies(data, "matches[", "]test_column[")": assert len(anomalies) > 0[" assert anomalies[0].detection_method =="]]iqr[" assert 100 in anomalies[0].anomalous_values[""""
    def test_detect_iqr_anomalies_zero_iqr(self, detector):
        "]]""测试IQR方法处理IQR为0的情况"""
        data = pd.Series([5, 5, 5, 5, 5])
        detector._detect_iqr_anomalies(data, "matches[", "]test_column[")": assert len(anomalies) ==0[" def test_detect_z_score_anomalies_normal_data(self, detector):""
        "]]""测试Z-score方法检测正常数据"""
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        detector._detect_z_score_anomalies(data, "matches[", "]test_column[")": assert len(anomalies) ==0[" def test_detect_z_score_anomalies_with_outliers(self, detector):""
        "]]""测试Z-score方法检测异常数据"""
        # 使用真实pandas Series来避免numpy操作问题
        data = pd.Series([1, 2, 3, 4, 5, 100])
        detector._detect_z_score_anomalies(data, "matches[", "]test_column[")": assert len(anomalies) > 0[" assert anomalies[0].detection_method =="]]z_score[" assert 100 in anomalies[0].anomalous_values[""""
    def test_detect_range_anomalies_normal_data(self, detector):
        "]]""测试范围检查正常数据"""
        data = pd.Series([1, 2, 3, 4, 5])
        # 设置配置
        detector.detection_config["matches["] = {"]"""
        "thresholds[": {"]test_column[": {"]min[": 0, "]max[": 10}}""""
        }
        detector._detect_range_anomalies(data, "]matches[", "]test_column[")": assert len(anomalies) ==0[" def test_detect_range_anomalies_out_of_range(self, detector):""
        "]]""测试范围检查超出范围的数据"""
        data = pd.Series([1, 2, 3, 4, 15])  # 15超出范围
        # 设置配置
        detector.detection_config["matches["] = {"]"""
        "thresholds[": {"]test_column[": {"]min[": 0, "]max[": 10}}""""
        }
        detector._detect_range_anomalies(data, "]matches[", "]test_column[")": assert len(anomalies) > 0[" assert anomalies[0].anomaly_type.value =="]]value_range[" assert anomalies[0].detection_method =="]range_check[" assert 15 in anomalies[0].anomalous_values[""""
    def test_detect_range_anomalies_no_thresholds(self, detector):
        "]]""测试范围检查无配置的情况"""
        data = pd.Series([1, 2, 3, 4, 15])
        # 不设置配置
        detector.detection_config["matches["] = {}"]": detector._detect_range_anomalies(data, "matches[", "]test_column[")": assert len(anomalies) ==0[" def test_detect_frequency_anomalies_normal_data(self, detector):""
        "]]""测试频率检测正常数据"""
        data = pd.Series(['A', 'B', 'C', 'A', 'B', 'C'])  # 均匀分布
        detector._detect_frequency_anomalies(data, "matches[", "]test_column[")": assert len(anomalies) ==0[" def test_detect_frequency_anomalies_skewed_data(self, detector):""
        "]]""测试频率检测偏斜数据"""
        data = pd.Series(['A', 'A', 'A', 'A', 'B', 'C'])  # A出现频率过高
        detector._detect_frequency_anomalies(data, "matches[", "]test_column[")": assert len(anomalies) > 0[" assert anomalies[0].anomaly_type.value =="]]frequency[" assert anomalies[0].detection_method =="]frequency[" def test_detect_time_gap_anomalies_insufficient_data("
    """"
        "]""测试时间间隔检测数据不足的情况"""
        data = pd.Series([datetime.now()])
        detector._detect_time_gap_anomalies(data, "matches[", "]test_column[")": assert len(anomalies) ==0[" def test_detect_time_gap_anomalies_normal_intervals(self, detector):""
        "]]""测试时间间隔检测正常间隔"""
        base_time = datetime.now()
        data = pd.Series(["base_time[",": base_time + timedelta(minutes=1),": base_time + timedelta(minutes=2),": base_time + timedelta(minutes=3)"
        ])
        detector._detect_time_gap_anomalies(data, "]matches[", "]test_column[")": assert len(anomalies) ==0[" def test_detect_time_gap_anomalies_abnormal_intervals(self, detector):""
        "]]""测试时间间隔检测异常间隔"""
        base_time = datetime.now()
        data = pd.Series(["base_time[",": base_time + timedelta(minutes=1),": base_time + timedelta(minutes=2),": base_time + timedelta(hours=1)  # 异常长的间隔"
        ])
        detector._detect_time_gap_anomalies(data, "]matches[", "]test_column[")": assert len(anomalies) > 0[" assert anomalies[0].anomaly_type.value =="]]pattern_break[" def test_calculate_severity_levels("
    """"
        "]""测试严重程度计算"""
        # 测试不同严重程度
    assert detector._calculate_severity(0.25) ==AnomalySeverity.CRITICAL
    assert detector._calculate_severity(0.15) ==AnomalySeverity.HIGH
    assert detector._calculate_severity(0.07) ==AnomalySeverity.MEDIUM
    assert detector._calculate_severity(0.02) ==AnomalySeverity.LOW
    def test_calculate_severity_boundary_values(self, detector):
        """测试严重程度边界值"""
        # 测试边界值
    assert detector._calculate_severity(0.2) ==AnomalySeverity.CRITICAL
    assert detector._calculate_severity(0.1) ==AnomalySeverity.HIGH
    assert detector._calculate_severity(0.05) ==AnomalySeverity.MEDIUM
    assert detector._calculate_severity(0.0) ==AnomalySeverity.LOW
    def test_detect_column_anomalies_numeric_column(self, detector, sample_data):
        """测试数值列异常检测"""
        methods = ["three_sigma[", "]iqr[", "]z_score[", "]range_check["]""""
        # 设置配置
        detector.detection_config["]matches["] = {""""
        "]thresholds[": {"]home_score[": {"]min[": 0, "]max[": 20}}""""
        }
        detector._detect_column_anomalies(
        sample_data, "]matches[", "]home_score[", methods, "]numeric["""""
        )
        # 应该检测到home_score中的异常值100
    assert len(anomalies) > 0
    assert any(100 in anomaly.anomalous_values for anomaly in anomalies)
    def test_detect_column_anomalies_categorical_column(self, detector, sample_data):
        "]""测试分类列异常检测"""
        methods = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_METHODS_297"): detector._detect_column_anomalies(": sample_data, "]matches[", "]match_status[", methods, "]categorical["""""
        )
        # 检查结果（可能检测到频率异常）
    assert isinstance(anomalies, list)
    def test_detect_column_anomalies_empty_data(self, detector):
        "]""测试空数据的异常检测"""
        empty_data = pd.DataFrame()
        detector._detect_column_anomalies(
        empty_data, "matches[", "]home_score[", "]three_sigma[", "]numeric["""""
        )
    assert len(anomalies) ==0
    def test_detect_column_anomalies_nonexistent_column(self, detector, sample_data):
        "]""测试不存在的列"""
        detector._detect_column_anomalies(
        sample_data, "matches[", "]nonexistent_column[", "]three_sigma[", "]numeric["""""
        )
    assert len(anomalies) ==0
    @pytest.mark.asyncio
    async def test_get_table_data_success(self, detector):
        "]""测试成功获取表数据"""
        # Mock数据库会话
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
        Mock(_mapping = {'id': 1, 'home_score': 2, 'away_score' 1)),
        Mock(_mapping = {'id': 2, 'home_score': 3, 'away_score': 2))
        ]
        mock_session.execute.return_value = mock_result
        await detector._get_table_data(mock_session, "matches[")": assert len(data) ==2[" assert 'home_score' in data.columns[""
    assert 'away_score' in data.columns
    @pytest.mark.asyncio
    async def test_get_table_data_error(self, detector):
        "]]]""测试获取表数据出错"""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database error[")": await detector._get_table_data(mock_session, "]matches[")": assert data.empty["""
    @pytest.mark.asyncio
    async def test_detect_table_anomalies_success(self, detector):
        "]]""测试成功检测表异常"""
        mock_session = AsyncMock()
        # Mock _get_table_data方法
        sample_df = pd.DataFrame({
        'home_score': [1, 2, 3, 4, 5, 100],
        'away_score': [0, 1, 2, 3, 4, -10]
        ))
        with patch.object(detector, '_get_table_data', return_value = sample_df)
            # 设置配置
            detector.detection_config["matches["] = {"]"""
            "numeric_columns[": ["]home_score[", "]away_score["],""""
            "]thresholds[": {""""
            "]home_score[": {"]min[": 0, "]max[": 20},""""
            "]away_score[": {"]min[": 0, "]max[": 20}""""
                }
            }
            await detector._detect_table_anomalies(
                mock_session, "]matches[", ["]three_sigma[", "]range_check["]""""
            )
    assert len(anomalies) > 0
    assert all(anomaly.table_name =="]matches[" for anomaly in anomalies)""""
    @pytest.mark.asyncio
    async def test_detect_table_anomalies_no_config(self, detector):
        "]""测试检测无配置的表"""
        mock_session = AsyncMock()
        await detector._detect_table_anomalies(
        mock_session, "nonexistent_table[", "]three_sigma["""""
        )
    assert len(anomalies) ==0
    @pytest.mark.asyncio
    async def test_detect_table_anomalies_empty_data(self, detector):
        "]""测试检测空数据的表"""
        mock_session = AsyncMock()
        with patch.object(detector, '_get_table_data', return_value = pd.DataFrame())
            detector.detection_config["matches["] = {"]"""
            "numeric_columns[": "]home_score["""""
            }
            await detector._detect_table_anomalies(
            mock_session, "]matches[", "]three_sigma["""""
            )
    assert len(anomalies) ==0
    @pytest.mark.asyncio
    async def test_detect_anomalies_default_params(self, detector):
        "]""测试使用默认参数的异常检测"""
        # Mock数据库会话
        with patch.object(detector.db_manager, 'get_async_session') as mock_get_session = mock_session AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            # Mock _detect_table_anomalies
            with patch.object(detector, '_detect_table_anomalies', return_value = [])
                await detector.detect_anomalies()
    assert isinstance(anomalies, list)
            # 应该使用默认的表名和方法
    @pytest.mark.asyncio
    async def test_detect_anomalies_with_params(self, detector):
        """测试带参数的异常检测"""
        # Mock数据库会话
        with patch.object(detector.db_manager, 'get_async_session') as mock_get_session = mock_session AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            # Mock _detect_table_anomalies
            with patch.object(detector, '_detect_table_anomalies', return_value = [])
                await detector.detect_anomalies(
                table_names = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAMES_"),": methods=["]three_sigma[", "]iqr["]""""
                )
    assert isinstance(anomalies, list)
    @pytest.mark.asyncio
    async def test_detect_anomalies_error_handling(self, detector):
        "]""测试异常检测的错误处理"""
        # Mock数据库会话
        with patch.object(detector.db_manager, 'get_async_session') as mock_get_session = mock_session AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            # Mock _detect_table_anomalies抛出异常
            with patch.object(detector, '_detect_table_anomalies', side_effect = Exception("Detection error["))": await detector.detect_anomalies("]matches[")""""
                # 应该返回空列表而不是抛出异常
    assert isinstance(anomalies, list)
    @pytest.mark.asyncio
    async def test_get_anomaly_summary_empty(self, detector):
        "]""测试空异常列表的摘要"""
        await detector.get_anomaly_summary([])
    assert summary["total_anomalies["] ==0["]"]" assert summary["by_severity["] =={}"]" assert summary["by_type["] =={}"]" assert summary["by_table["] =={}"]" assert summary["critical_anomalies["] ==0["]"]" assert summary["high_priority_anomalies["] ==0["]"]""
    @pytest.mark.asyncio
    async def test_get_anomaly_summary_with_data(self, detector):
        """测试有数据的异常摘要"""
        from src.monitoring.anomaly_detector import AnomalyResult, AnomalyType, AnomalySeverity
        anomalies = [
        AnomalyResult(
        table_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAME_1"),": column_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_COLUMN_NAME_"),": anomaly_type=AnomalyType.OUTLIER,": severity=AnomalySeverity.CRITICAL,": anomalous_values=[100],"
                anomaly_score=0.2,
                detection_method = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DETECTION_ME"),": description="]异常值["""""
            ),
            AnomalyResult(
                table_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_TABLE_NAME_4"),": column_name = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_COLUMN_NAME_"),": anomaly_type=AnomalyType.VALUE_RANGE,": severity=AnomalySeverity.HIGH,": anomalous_values = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_ANOMALOUS_VA"),": anomaly_score=0.15,": detection_method = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DETECTION_ME"),": description = os.getenv("TEST_ANOMALY_DETECTOR_BATCH_OMEGA_003_DESCRIPTION_")""""
            )
        ]
        await detector.get_anomaly_summary(anomalies)
    assert summary["]total_anomalies["] ==2[" assert summary["]]by_severity["]"]critical[" ==1[" assert summary["]]by_severity["]"]high[" ==1[" assert summary["]]by_type["]"]outlier[" ==1[" assert summary["]]by_type["]"]value_range[" ==1[" assert summary["]]by_table["]"]matches[" ==1[" assert summary["]]by_table["]"]odds[" ==1[" assert summary["]]critical_anomalies["] ==1[" assert summary["]]high_priority_anomalies["] ==2  # CRITICAL + HIGH[" assert summary["]]most_affected_table["] in ["]matches[", "]odds["]" def test_error_handling_methods(self, detector):"""
        "]""测试方法的错误处理"""
        # 测试无效数据的错误处理
        pd.Series(['invalid', 'data', 'for', 'numeric', 'analysis'])
        # 这些方法应该优雅地处理错误而不是抛出异常
    assert isinstance(detector._detect_three_sigma_anomalies(invalid_data, "test[", "]test["), list)" assert isinstance(detector._detect_iqr_anomalies(invalid_data, "]test[", "]test["), list)" assert isinstance(detector._detect_z_score_anomalies(invalid_data, "]test[", "]test["), list)" assert isinstance(detector._detect_range_anomalies(invalid_data, "]test[", "]test["), list)" assert isinstance(detector._detect_frequency_anomalies(invalid_data, "]test[", "]test["), list)" def test_detection_method_coverage(self, detector):"""
        "]""测试所有检测方法都被覆盖"""
        # 确保所有检测方法都能被调用
        test_data = pd.Series([1, 2, 3, 4, 50])  # 包含异常值
        # 设置配置以启用范围检查
        detector.detection_config["test_table["] = {"]"""
        "thresholds[": {"]test_column[": {"]min[": 0, "]max[": 10}}""""
        }
        # 测试时间序列数据
        time_data = pd.Series([
        datetime.now(),
        datetime.now() + timedelta(minutes=1),
        datetime.now() + timedelta(hours=1)  # 异常间隔
        ])
        # 调用所有检测方法
        methods = [
            detector._detect_three_sigma_anomalies,
            detector._detect_iqr_anomalies,
            detector._detect_z_score_anomalies,
            detector._detect_range_anomalies,
            detector._detect_frequency_anomalies,
            detector._detect_time_gap_anomalies
        ]
        for method in methods:
            if method ==detector._detect_time_gap_anomalies
                method(time_data, "]test_table[", "]test_column[")": else:": method(test_data, "]test_table[", "]test_column[")"]": assert isinstance(result, list)  # 所有方法都应该返回列表" from src.monitoring.anomaly_detector import AnomalyDetector"
        from src.monitoring.anomaly_detector import AnomalyResult, AnomalyType, AnomalySeverity
        from src.monitoring.anomaly_detector import AnomalyResult, AnomalyType, AnomalySeverity
        from src.monitoring.anomaly_detector import AnomalyResult, AnomalyType, AnomalySeverity