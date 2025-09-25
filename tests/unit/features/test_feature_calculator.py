"""
特征计算器简单测试
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.features.feature_calculator import FeatureCalculator


class TestFeatureCalculatorSimple:
    """测试特征计算器 - 简化版本"""

    @pytest.fixture
    def calculator(self):
        """创建FeatureCalculator实例"""
        with patch("src.features.feature_calculator.DatabaseManager"):
            return FeatureCalculator()

    def test_init(self, calculator):
        """测试初始化"""
        assert calculator.config == {}
        assert isinstance(calculator.features, list)

    def test_calculate_mean(self, calculator):
        """测试计算均值"""
        assert calculator.calculate_mean([1, 2, 3, 4, 5]) == 3.0
        assert calculator.calculate_mean([]) is None
        assert calculator.calculate_mean([None, 1, 2]) is None

    def test_calculate_std(self, calculator):
        """测试计算标准差"""
        assert calculator.calculate_std([1, 2, 3, 4, 5]) == pytest.approx(1.58, rel=0.1)
        assert calculator.calculate_std([]) is None
        assert calculator.calculate_std([None, 1, 2]) is None
        assert calculator.calculate_std([5, 5, 5]) == 0.0

    def test_calculate_min(self, calculator):
        """测试计算最小值"""
        assert calculator.calculate_min([1, 2, 3, 4, 5]) == 1
        assert calculator.calculate_min([]) is None
        assert calculator.calculate_min([None, 1, 2]) is None

    def test_calculate_max(self, calculator):
        """测试计算最大值"""
        assert calculator.calculate_max([1, 2, 3, 4, 5]) == 5
        assert calculator.calculate_max([]) is None
        assert calculator.calculate_max([None, 1, 2]) is None

    def test_calculate_rolling_mean(self, calculator):
        """测试计算滚动均值"""
        data = [1, 2, 3, 4, 5]
        result = calculator.calculate_rolling_mean(data, window=3)

        assert len(result) == 5  # min_periods=1 所以返回全部数据
        assert result[0] == 1.0  # 第一个窗口只有[1]
        assert result[1] == 1.5  # 第二个窗口[1,2]
        assert result[2] == 2.0  # 第三个窗口[1,2,3]

        # 测试空数据
        result_empty = calculator.calculate_rolling_mean([], window=3)
        assert len(result_empty) == 0

    def test_add_feature(self, calculator):
        """测试添加特征定义"""
        feature_def = {
            "name": "test_feature",
            "type": "numeric",
            "description": "测试特征"
        }
        calculator.add_feature(feature_def)

        assert len(calculator.features) == 1
        assert calculator.features[0] == feature_def

    @pytest.mark.asyncio
    async def test_calculate_odds_features_success(self, calculator):
        """测试成功计算赔率特征"""
        with patch.object(calculator, 'db_manager') as mock_db_manager:
            mock_session = AsyncMock()
            mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            # Mock赔率数据
            mock_odds = Mock()
            mock_odds.home_odds = 2.50
            mock_odds.draw_odds = 3.20
            mock_odds.away_odds = 2.80

            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [mock_odds]
            mock_session.execute.return_value = mock_result

            features = await calculator.calculate_odds_features(
                match_id=1,
                calculation_date=datetime.now(),
                session=mock_session
            )

            assert hasattr(features, 'home_implied_probability')
            assert features.home_implied_probability == pytest.approx(1/2.50, rel=0.01)

    @pytest.mark.asyncio
    async def test_calculate_odds_features_no_odds(self, calculator):
        """测试无赔率数据时的特征计算"""
        with patch.object(calculator, 'db_manager') as mock_db_manager:
            mock_session = AsyncMock()
            mock_db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute.return_value = mock_result

            features = await calculator.calculate_odds_features(
                match_id=1,
                calculation_date=datetime.now(),
                session=mock_session
            )

            assert hasattr(features, 'home_implied_probability')
            assert features.home_implied_probability is None

    def test_edge_cases(self, calculator):
        """测试边界情况"""
        # 测试空值处理
        assert calculator.calculate_mean([None, None, None]) is None
        assert calculator.calculate_std([]) is None
        assert calculator.calculate_min([]) is None
        assert calculator.calculate_max([]) is None

        # 测试单个值
        assert calculator.calculate_mean([5]) == 5.0
        assert calculator.calculate_std([5]) is None  # 单个值的标准差为None
        assert calculator.calculate_min([5]) == 5
        assert calculator.calculate_max([5]) == 5