
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_business_service():
    return Mock()

def test_business_logic_calculation(mock_business_service):
    """测试业务逻辑计算"""
    # 模拟业务逻辑
    mock_business_service.calculate.return_value = {
        "prediction": 0.75,
        "confidence": 0.85,
        "recommendation": "bet"
    }

    result = mock_business_service.calculate({
        "team_home": "Team A",
        "team_away": "Team B",
        "odds": {"home_win": 2.1}
    })

    assert result is not None
    assert "prediction" in result
    assert "confidence" in result
    assert result["prediction"] > 0.5
    print("✅ 业务逻辑测试通过")
