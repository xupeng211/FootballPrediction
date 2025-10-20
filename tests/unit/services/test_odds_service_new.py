"""
赔率服务测试
Odds Service Tests

使用新的测试模板和最佳实践编写。

功能描述：
- 从外部API获取赔率数据
- 转换赔率为概率
- 缓存赔率数据
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime, timedelta
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

# 假设这是我们要测试的模块
# from src.services.odds_service import OddsService


# 为了演示，我们创建一个简单的实现
class OddsService:
    """赔率服务"""

    def __init__(self, cache=None):
        self.cache = cache or {}
        self.api_base_url = "https://api.football-data.org/v4"

    def get_odds(self, match_id: int) -> dict:
        """获取比赛赔率"""
        # 检查缓存
        cache_key = f"odds_{match_id}"
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            # 检查缓存是否过期（5分钟）
            if datetime.now() - cached_data["cached_at"] < timedelta(minutes=5):
                return cached_data["data"]

        # 模拟API调用
        try:
            import requests

            response = requests.get(f"{self.api_base_url}/odds/{match_id}")
            response.raise_for_status()
            odds_data = response.json()

            # 转换赔率为概率
            probabilities = self._convert_odds_to_probability(odds_data)

            # 缓存结果
            self.cache[cache_key] = {"data": probabilities, "cached_at": datetime.now()}

            return probabilities
        except Exception as e:
            raise ValueError(f"Failed to fetch odds for match {match_id}: {e}")

    def _convert_odds_to_probability(self, odds_data: dict) -> dict:
        """转换赔率为概率"""
        if "odds" not in odds_data:
            raise ValueError("No odds data found")

        odds = odds_data["odds"]
        # 计算隐含概率
        total_implied = 1 / odds["home_win"] + 1 / odds["draw"] + 1 / odds["away_win"]
        margin = total_implied - 1.0

        return {
            "match_id": odds_data.get("match_id"),
            "probabilities": {
                "home_win": round(1 / odds["home_win"] / (1 + margin), 4),
                "draw": round(1 / odds["draw"] / (1 + margin), 4),
                "away_win": round(1 / odds["away_win"] / (1 + margin), 4),
            },
            "odds": odds,
            "margin": round(margin, 4),
            "timestamp": datetime.now().isoformat(),
        }

    def get_multiple_odds(self, match_ids: list[int]) -> dict:
        """批量获取赔率"""
        results = {}
        errors = {}

        for match_id in match_ids:
            try:
                results[match_id] = self.get_odds(match_id)
            except ValueError as e:
                errors[match_id] = str(e)

        return {
            "results": results,
            "errors": errors,
            "total": len(match_ids),
            "success_count": len(results),
            "failed_count": len(errors),
        }


@pytest.mark.unit
class TestOddsService:
    """赔率服务测试类"""

    # ======== Fixtures ========

    @pytest.fixture
    def mock_cache(self):
        """模拟缓存fixture"""
        return {}

    @pytest.fixture
    def odds_service(self, mock_cache):
        """赔率服务fixture"""
        return OddsService(cache=mock_cache)

    @pytest.fixture
    def sample_odds_data(self):
        """示例赔率数据"""
        return {
            "match_id": 123,
            "odds": {"home_win": 2.50, "draw": 3.20, "away_win": 2.80},
        }

    @pytest.fixture
    def sample_response(self):
        """模拟API响应"""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "match_id": 123,
            "odds": {"home_win": 2.50, "draw": 3.20, "away_win": 2.80},
        }
        response.raise_for_status.return_value = None
        return response

    # ======== 基本功能测试 ========

    def test_get_odds_with_valid_match_id_returns_probabilities(
        self, odds_service, sample_response
    ):
        """
        测试：使用有效match_id获取赔率返回概率数据

        测试场景：
        - 输入：有效的match_id（123）
        - 期望：返回计算出的概率
        """
        # Arrange
        match_id = 123

        # Act
        with patch(
            "src.services.odds_service.requests.get", return_value=sample_response
        ) as mock_get:
            result = odds_service.get_odds(match_id)

        # Assert
        assert result["match_id"] == match_id
        assert "probabilities" in result
        assert "home_win" in result["probabilities"]
        assert "draw" in result["probabilities"]
        assert "away_win" in result["probabilities"]

        # 验证概率计算（赔率2.50 -> 概率约0.40）
        assert 0.35 < result["probabilities"]["home_win"] < 0.45

        # 验证API调用
        mock_get.assert_called_once_with(
            f"https://api.football-data.org/v4/odds/{match_id}"
        )

    def test_get_odds_with_cached_data_returns_cached_result(self, odds_service):
        """
        测试：缓存中有数据时返回缓存结果

        测试场景：
        - 输入：缓存中存在有效数据
        - 期望：返回缓存数据，不调用API
        """
        # Arrange
        match_id = 123
        cached_data = {
            "probabilities": {"home_win": 0.4},
            "cached_at": datetime.now() - timedelta(minutes=2),  # 2分钟前
        }
        odds_service.cache[f"odds_{match_id}"] = {"data": cached_data}

        # Act
        with patch("src.services.odds_service.requests.get") as mock_get:
            result = odds_service.get_odds(match_id)

        # Assert
        assert result == cached_data
        mock_get.assert_not_called()  # 不应该调用API

    def test_get_odds_with_expired_cache_calls_api(self, odds_service, sample_response):
        """
        测试：缓存过期时调用API更新数据

        测试场景：
        - 输入：缓存中存在过期数据（6分钟前）
        - 期望：调用API并更新缓存
        """
        # Arrange
        match_id = 123
        old_cached_data = {
            "probabilities": {"home_win": 0.3},
            "cached_at": datetime.now() - timedelta(minutes=6),  # 6分钟前，已过期
        }
        odds_service.cache[f"odds_{match_id}"] = {"data": old_cached_data}

        # Act
        with patch(
            "src.services.odds_service.requests.get", return_value=sample_response
        ) as mock_get:
            result = odds_service.get_odds(match_id)

        # Assert
        assert result != old_cached_data  # 应该返回新数据
        mock_get.assert_called_once()  # 应该调用API

        # 验证缓存已更新
        cached = odds_service.cache[f"odds_{match_id}"]
        assert cached["data"] == result

    def test_convert_odds_to_probability_with_valid_odds_returns_correct_probabilities(
        self, odds_service, sample_odds_data
    ):
        """
        测试：转换有效赔率数据返回正确的概率

        测试场景：
        - 输入：赔率 [2.50, 3.20, 2.80]
        - 期望：概率总和约等于1（考虑庄家抽水）
        """
        # Act
        result = odds_service._convert_odds_to_probability(sample_odds_data)

        # Assert
        assert result["match_id"] == 123
        assert "probabilities" in result
        assert "margin" in result

        # 验证概率
        probs = result["probabilities"]
        prob_sum = probs["home_win"] + probs["draw"] + probs["away_win"]
        assert abs(prob_sum - 1.0) < 0.01  # 允许小数精度误差

        # 验证概率值合理
        for outcome, prob in probs.items():
            assert 0 < prob < 1
            assert 0.2 < prob < 0.8  # 足球概率通常在这个范围

    def test_get_multiple_odds_with_all_valid_ids_returns_all_results(
        self, odds_service
    ):
        """
        测试：所有有效ID返回全部结果

        测试场景：
        - 输入：3个有效的match_id
        - 期望：返回3个结果，0个错误
        """
        # Arrange
        match_ids = [123, 456, 789]

        # Act
        with patch("src.services.odds_service.requests.get") as mock_get:
            # 设置返回值
            mock_get.return_value.json.return_value = {
                "match_id": mock_get.call_args[0][0].split("/")[-1],
                "odds": {"home_win": 2.0, "draw": 3.0, "away_win": 4.0},
            }

            result = odds_service.get_multiple_odds(match_ids)

        # Assert
        assert result["total"] == 3
        assert result["success_count"] == 3
        assert result["failed_count"] == 0
        assert len(result["results"]) == 3
        assert len(result["errors"]) == 0

    # ======== 错误处理测试 ========

    def test_get_odds_with_invalid_match_id_returns_error(self, odds_service):
        """
        测试：无效match_id返回错误

        测试场景：
        - 输入：无效的match_id
        - 期望：抛出ValueError
        """
        # Arrange
        invalid_match_id = -1

        # Act & Assert
        with patch("src.services.odds_service.requests.get") as mock_get:
            mock_get.return_value.json.return_value = {"error": "Invalid match ID"}
            mock_get.raise_for_status.side_effect = ValueError("Invalid match ID")

            with pytest.raises(ValueError, match="Failed to fetch odds"):
                odds_service.get_odds(invalid_match_id)

    def test_get_odds_with_network_error_returns_error(self, odds_service):
        """
        测试：网络错误返回错误

        测试场景：
        - 模拟网络连接错误
        - 期望：抛出ValueError
        """
        # Arrange
        match_id = 123

        # Act & Assert
        with patch("src.services.odds_service.requests.get") as mock_get:
            mock_get.side_effect = ConnectionError("Network error")

            with pytest.raises(ValueError, match="Failed to fetch odds"):
                odds_service.get_odds(match_id)

    def test_convert_odds_with_missing_odds_data_returns_error(self, odds_service):
        """
        测试：缺少odds数据返回错误

        测试场景：
        - 输入：不包含odds字段的数据
        - 期望：抛出ValueError
        """
        # Arrange
        invalid_data = {"match_id": 123}

        # Act & Assert
        with pytest.raises(ValueError, match="No odds data found"):
            odds_service._convert_odds_to_probability(invalid_data)

    # ======== 边界条件测试 ========

    @pytest.mark.parametrize(
        "home_odds,draw_odds,away_odds",
        [
            (1.10, 1.50, 8.00),  # 强势主队
            (6.00, 4.00, 1.25),  # 强势客队
            (2.00, 2.00, 2.00),  # 均势
            (10.00, 15.00, 20.00),  # 防守型比赛
        ],
    )
    def test_convert_odds_with_various_odds_returns_valid_probabilities(
        self, odds_service, home_odds, draw_odds, away_odds
    ):
        """
        测试：各种赔率组合返回有效概率

        参数化测试覆盖多种赔率场景
        """
        # Arrange
        odds_data = {
            "match_id": 123,
            "odds": {"home_win": home_odds, "draw": draw_odds, "away_win": away_odds},
        }

        # Act
        result = odds_service._convert_odds_to_probability(odds_data)

        # Assert
        probs = result["probabilities"]
        assert all(0 < p < 1 for p in probs.values())
        prob_sum = sum(probs.values())
        assert abs(prob_sum - 1.0) < 0.01

    def test_get_odds_with_zero_match_id_returns_error(self, odds_service):
        """
        测试：match_id为0返回错误

        测试场景：
        - 输入：match_id = 0
        - 期望：API返回错误或抛出异常
        """
        # Act & Assert
        with patch("src.services.odds_service.requests.get") as mock_get:
            mock_get.return_value.json.return_value = {"error": "Invalid match ID"}
            mock_get.raise_for_status.side_effect = ValueError("Invalid match ID")

            with pytest.raises(ValueError):
                odds_service.get_odds(0)

    # ======== 缓存测试 ========

    def test_cache_ttl_is_5_minutes(self, odds_service, sample_response):
        """
        测试：缓存TTL是5分钟

        测试场景：
        - 缓存5分钟内有效
        - 5分钟后过期
        """
        # Arrange
        match_id = 123

        # Act & Assert - 第一次调用
        with patch(
            "src.services.odds_service.requests.get", return_value=sample_response
        ) as mock_get:
            result1 = odds_service.get_odds(match_id)
            mock_get.assert_called_once()

        # 缓存命中
        with patch("src.services.odds_service.requests.get") as mock_get:
            result2 = odds_service.get_odds(match_id)
            mock_get.assert_not_called()
            assert result1 == result2

        # 缓存过期
        odds_service.cache[f"odds_{match_id}"]["cached_at"] = (
            datetime.now() - timedelta(minutes=6)
        )

        with patch(
            "src.services.odds_service.requests.get", return_value=sample_response
        ) as mock_get:
            result3 = odds_service.get_odds(match_id)
            mock_get.assert_called_once()
            assert result3 != result1

    # ======== 性能测试（示例） ========

    def test_get_odds_performance_under_100ms(self, odds_service, sample_response):
        """
        测试：获取赔率性能在100ms内

        性能要求：包括缓存检查和API调用
        """
        import time

        # Arrange
        match_id = 123

        # Act
        start_time = time.time()
        with patch(
            "src.services.odds_service.requests.get", return_value=sample_response
        ):
            result = odds_service.get_odds(match_id)
        end_time = time.time()

        # Assert
        execution_time = end_time - start_time
        assert (
            execution_time < 0.1
        ), f"Too slow: {execution_time:.3f}s (should be < 0.1s)"
        assert result is not None


@pytest.mark.integration
class TestOddsServiceIntegration:
    """赔率服务集成测试"""

    def test_odds_service_with_real_api(self):
        """
        测试：使用真实API（如果可用）

        注意：这是一个可选测试，可能因为网络或API限制而跳过
        """
        # 这是一个示例，实际使用时需要真实的API
        pytest.skip("真实API测试需要有效的API密钥")

        # Arrange
        service = OddsService()
        match_id = 123

        # Act
        try:
            result = service.get_odds(match_id)
            # Assert
            assert "probabilities" in result
            print(f"获取到赔率数据: {result}")
        except Exception as e:
            pytest.skip(f"API不可用: {e}")


# ======== 配置 ========


def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")


# ======== 辅助函数 ========


def create_odds_data(match_id, home_odds, draw_odds, away_odds):
    """创建赔率数据的辅助函数"""
    return {
        "match_id": match_id,
        "odds": {"home_win": home_odds, "draw": draw_odds, "away_win": away_odds},
    }


def assert_valid_probabilities(probabilities, tolerance=0.01):
    """验证概率数据的有效性"""
    assert isinstance(probabilities, dict)
    assert all(0 < p < 1 for p in probabilities.values())

    prob_sum = sum(probabilities.values())
    assert abs(prob_sum - 1.0) <= tolerance


if __name__ == "__main__":
    # 运行测试
    print("使用命令：")
    print("  pytest tests/unit/services/test_odds_service_new.py -v")
    print("  pytest tests/unit/services/test_odds_service_new.py -k 'cache'")
    print("  pytest tests/unit/services/test_odds_service_new.py -m 'not slow'")
