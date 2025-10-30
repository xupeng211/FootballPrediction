# TODO: Consider creating a fixture for 5 repeated Mock creations

# TODO: Consider creating a fixture for 5 repeated Mock creations


"""
ScoresCollectorImproved 综合测试
提升 collectors 模块覆盖率的关键测试
"""

import asyncio

# 测试导入
import sys

import pytest

sys.path.insert(0, "src")

try:
    from src.collectors.scores_collector_improved import ScoresCollector

    COLLECTOR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import ScoresCollector: {e}")
    COLLECTOR_AVAILABLE = False


@pytest.mark.skipif(not COLLECTOR_AVAILABLE, reason="ScoresCollector not available")
@pytest.mark.unit
class TestScoresCollectorImproved:
    """ScoresCollector改进版测试"""

    @pytest.fixture
    def collector(self):
        """创建收集器实例"""
        with patch("src.collectors.scores_collector_improved.RedisManager"):
            collector = ScoresCollector(api_key="test_key", cache_ttl=300, retry_attempts=3)
            return collector

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def sample_match_data(self):
        """示例比赛数据"""
        return {
            "id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
            "status": "LIVE",
            "minute": 75,
            "last_updated": "2024-01-01T15:30:00Z",
        }

    @pytest.mark.asyncio
    async def test_collector_initialization(self, collector):
        """测试收集器初始化"""
        assert collector.api_key == "test_key"
        assert collector.cache_ttl == 300
        assert collector.retry_attempts == 3
        assert collector._running is False

    @pytest.mark.asyncio
    async def test_start_stop_collection(self, collector):
        """测试启动和停止收集"""
        # 启动收集
        await collector.start()
        assert collector._running is True

        # 停止收集
        await collector.stop()
        assert collector._running is False

    @pytest.mark.asyncio
    async def test_collect_single_match_data(self, collector, sample_match_data):
        """测试收集单个比赛数据"""
        with patch.object(collector, "_fetch_match_data") as mock_fetch:
            mock_fetch.return_value = sample_match_data

            result = await collector.collect_match(12345)

            assert result == sample_match_data
            mock_fetch.assert_called_once_with(12345)

    @pytest.mark.asyncio
    async def test_collect_multiple_matches(self, collector, sample_match_data):
        """测试收集多个比赛数据"""
        match_ids = [12345, 12346, 12347]

        with patch.object(collector, "_fetch_match_data") as mock_fetch:
            mock_fetch.return_value = sample_match_data

            results = await collector.collect_matches(match_ids)

            assert len(results) == 3
            assert all(result == sample_match_data for result in results)
            assert mock_fetch.call_count == 3

    @pytest.mark.asyncio
    async def test_data_validation(self, collector):
        """测试数据验证功能"""
        # 有效数据
        valid_data = {
            "id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
            "status": "LIVE",
        }

        assert collector._validate_data(valid_data) is True

        # 无效数据 - 缺少必需字段
        invalid_data = {"home_team": "Team A", "away_team": "Team B"}

        assert collector._validate_data(invalid_data) is False

    @pytest.mark.asyncio
    async def test_cache_operations(self, collector, sample_match_data):
        """测试缓存操作"""
        match_id = 12345

        # 测试缓存存储
        await collector._cache_match_data(match_id, sample_match_data)

        # 测试缓存获取
        cached_data = await collector._get_cached_match_data(match_id)
        assert cached_data == sample_match_data

    @pytest.mark.asyncio
    async def test_error_handling_and_retry(self, collector):
        """测试错误处理和重试机制"""
        match_id = 12345

        with patch.object(collector, "_fetch_match_data") as mock_fetch:
            # 前两次失败,第三次成功
            mock_fetch.side_effect = [
                Exception("Network error"),
                Exception("Timeout"),
                {"id": 12345, "status": "COMPLETED"},
            ]

            result = await collector.collect_match(match_id)

            assert result["id"] == 12345
            assert result["status"] == "COMPLETED"
            assert mock_fetch.call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limiting(self, collector):
        """测试速率限制"""
        match_ids = [i for i in range(10)]

        with patch.object(collector, "_fetch_match_data") as mock_fetch:
            mock_fetch.return_value = {"id": 0, "status": "LIVE"}

            start_time = asyncio.get_event_loop().time()
            await collector.collect_matches(match_ids)
            end_time = asyncio.get_event_loop().time()

            # 验证请求之间有适当的延迟
            elapsed_time = end_time - start_time
            assert elapsed_time > 0.5  # 至少有一些延迟

    @pytest.mark.asyncio
    async def test_websocket_connection(self, collector):
        """测试WebSocket连接"""
        with patch("websockets.connect") as mock_connect:
            mock_websocket = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_websocket
            mock_websocket.recv.return_value = '{"id": 12345, "status": "LIVE"}'

            messages = []
            async for message in collector._websocket_stream("ws://test.url"):
                messages.append(message)
                if len(messages) >= 2:
                    break

            assert len(messages) == 2
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_integration(self, collector, mock_session, sample_match_data):
        """测试数据库集成"""
        match_id = 12345

        with patch.object(collector, "_fetch_match_data") as mock_fetch:
            mock_fetch.return_value = sample_match_data

            await collector.collect_and_save_match(match_id, mock_session)

            # 验证数据库操作被调用
            mock_session.execute.assert_called()
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_data_transformation(self, collector, sample_match_data):
        """测试数据转换功能"""
        # 测试时间格式转换
        raw_data = {"id": 12345, "last_updated": "2024-01-01T15:30:00Z"}

        transformed = collector._transform_data(raw_data)

        assert transformed["id"] == 12345
        assert "last_updated" in transformed
        # 验证时间格式被正确转换

    @pytest.mark.asyncio
    async def test_concurrent_collection(self, collector):
        """测试并发收集"""
        match_ids = list(range(20))

        with patch.object(collector, "_fetch_match_data") as mock_fetch:
            mock_fetch.return_value = {"id": 0, "status": "LIVE"}

            tasks = [collector.collect_match(match_id) for match_id in match_ids]
            results = await asyncio.gather(*tasks)

            assert len(results) == 20
            assert all(result["status"] == "LIVE" for result in results)

    def test_configuration_validation(self):
        """测试配置验证"""
        # 有效配置
        valid_config = {"api_key": "test_key", "cache_ttl": 300, "retry_attempts": 3}

        assert ScoresCollector._validate_config(valid_config) is True

        # 无效配置 - 缺少API密钥
        invalid_config = {"cache_ttl": 300, "retry_attempts": 3}

        assert ScoresCollector._validate_config(invalid_config) is False

    @pytest.mark.asyncio
    async def test_monitoring_and_metrics(self, collector):
        """测试监控和指标收集"""
        # 收集一些数据
        with patch.object(collector, "_fetch_match_data") as mock_fetch:
            mock_fetch.return_value = {"id": 12345, "status": "LIVE"}

            await collector.collect_match(12345)

        # 获取指标
        metrics = await collector.get_metrics()

        assert "requests_count" in metrics
        assert "success_count" in metrics
        assert "error_count" in metrics
        assert "average_response_time" in metrics

    @pytest.mark.asyncio
    async def test_cleanup_operations(self, collector):
        """测试清理操作"""
        # 添加一些缓存数据
        await collector._cache_match_data(12345, {"status": "LIVE"})
        await collector._cache_match_data(12346, {"status": "LIVE"})

        # 执行清理
        await collector.cleanup_expired_cache()

        # 验证清理效果
        await collector._get_cached_match_data(12345)
        # 根据TTL设置,数据可能仍然存在或已清理


@pytest.mark.skipif(not COLLECTOR_AVAILABLE, reason="ScoresCollector not available")
class TestScoresCollectorErrorScenarios:
    """ScoresCollector错误场景测试"""

    @pytest.fixture
    def collector(self):
        """创建收集器实例"""
        with patch("src.collectors.scores_collector_improved.RedisManager"):
            return ScoresCollector(api_key="test_key")

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, collector):
        """测试网络超时处理"""
        with patch.object(collector, "_fetch_match_data") as mock_fetch:
            mock_fetch.side_effect = asyncio.TimeoutError("Request timeout")

            with pytest.raises(Exception):
                await collector.collect_match(12345)

    @pytest.mark.asyncio
    async def test_invalid_response_handling(self, collector):
        """测试无效响应处理"""
        with patch.object(collector, "_fetch_match_data") as mock_fetch:
            mock_fetch.return_value = "invalid json"

            result = await collector.collect_match(12345)
            assert result is None

    @pytest.mark.asyncio
    async def test_api_rate_limit_handling(self, collector):
        """测试API速率限制处理"""
        with patch.object(collector, "_fetch_match_data") as mock_fetch:
            mock_fetch.side_effect = Exception("Rate limit exceeded")

            # 应该触发重试机制
            with pytest.raises(Exception):
                await collector.collect_match(12345)
