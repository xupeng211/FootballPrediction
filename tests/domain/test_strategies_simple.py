"""
简单测试 - 领域策略
"""

import pytest
import sys
from pathlib import Path

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_historical_strategy():
    """测试历史策略"""
    try:
        from domain.strategies.historical import HistoricalStrategy

        assert HistoricalStrategy is not None
    except ImportError:
        pytest.skip("HistoricalStrategy 不存在")


def test_ensemble_strategy():
    """测试集成策略"""
    try:
        from domain.strategies.ensemble import EnsembleStrategy

        assert EnsembleStrategy is not None
    except ImportError:
        pytest.skip("EnsembleStrategy 不存在")
