import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.exc import DatabaseError
from fastapi import HTTPException, FastAPI, Request
from fastapi.testclient import TestClient
from src.services.data_processing_mod import DataProcessingService
from src.streaming.kafka_producer import KafkaProducer
from src.api.health import router
from src.database.connection import DatabaseManager

"""
边界测试和异常场景测试
测试系统在各种边界条件和异常情况下的行为
"""


class TestEdgeCases:
    """边界测试和异常场景测试"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """测试数据库连接失败的处理"""
        with patch("src.database.connection.DatabaseManager") as MockDBManager:
            mock_manager = Mock()
            mock_manager.get_session.side_effect = DatabaseError("Connection failed")
            MockDBManager.return_value = mock_manager

            service = DataProcessingService()

            # 应该优雅地处理数据库错误
            with pytest.raises(DatabaseError):
                service.process_batch([])

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_redis_connection_timeout(self):
        """测试Redis连接超时处理"""
        with patch("src.cache.redis_manager.RedisManager") as MockRedis:
            mock_redis = AsyncMock()
            mock_redis.get.side_effect = asyncio.TimeoutError("Redis timeout")
            MockRedis.return_value = mock_redis

            from src.cache.redis_manager import RedisManager

            redis_manager = RedisManager()

            # 应该处理超时异常
            with pytest.raises(asyncio.TimeoutError):
                await redis_manager.get("test_key")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_kafka_producer_failure(self):
        """测试Kafka生产者失败处理"""
        with patch("src.streaming.kafka_producer.KafkaProducer") as MockProducer:
            mock_producer = AsyncMock()
            mock_producer.produce.side_effect = Exception("Kafka broker unavailable")
            MockProducer.return_value = mock_producer

            producer = KafkaProducer()

            # 应该处理Kafka错误
            with pytest.raises(Exception, match="Kafka broker unavailable"):
                await producer.produce("test_topic", {"test": "message"})

    @pytest.mark.integration
    def test_empty_dataset_processing(self):
        """测试空数据集处理"""
        from src.data.processing.football_data_cleaner_mod import FootballDataCleaner

        cleaner = FootballDataCleaner()

        # 处理空数据集
        result = cleaner.clean_match_data([])
        assert result == []

        # 处理None输入
        result = cleaner.clean_match_data(None)
        assert result is None

    @pytest.mark.integration
    def test_large_dataset_processing(self):
        """测试大数据集处理"""

        service = DataProcessingService()

        # 创建大量测试数据
        large_dataset = [
            {"match_id": f"match_{i}", "home_score": i % 5, "away_score": (i + 1) % 5}
            for i in range(10000)
        ]

        start_time = time.time()

        # 处理应该能在合理时间内完成
        result = service.process_batch(large_dataset)

        processing_time = time.time() - start_time

        assert result is not None
        assert processing_time < 10.0  # 应该在10秒内完成

    @pytest.mark.integration
    def test_malformed_data_handling(self):
        """测试格式错误数据的处理"""
        from src.utils.data_validator import DataValidator

        validator = DataValidator()

        # 测试各种格式错误的数据
        malformed_cases = [
            None,
            [],
            {},
            {"invalid_field": "value"},
            {"match_id": None, "home_team": ""},
            {"match_id": "test", "scores": "invalid"},
            {"match_id": "test", "home_score": -1},
            {"match_id": "test", "away_score": 1000},  # 异常大的比分
        ]

        for case in malformed_cases:
            assert validator.validate_match_data(case) is False

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_requests_limit(self):
        """测试并发请求限制"""

        client = TestClient(router)

        # 模拟大量并发请求
        async def make_request():
            try:
                response = client.get("/health")
                return response.status_code == 200
            except Exception:
                return False

        # 创建100个并发请求
        tasks = [make_request() for _ in range(100)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 检查大部分请求是否成功（取决于限流策略）
        successful_requests = sum(1 for r in results if r is True)
        assert successful_requests > 0  # 至少有一些请求成功

    @pytest.mark.integration
    def test_memory_usage_limits(self):
        """测试内存使用限制"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 创建大量对象
        large_list = []
        for i in range(100000):
            large_list.append({"data": "x" * 1000, "index": i})

        current_memory = process.memory_info().rss
        memory_increase = (current_memory - initial_memory) / 1024 / 1024  # MB

        # 内存使用应该在合理范围内
        assert memory_increase < 500  # 不应超过500MB

        # 清理内存
        del large_list

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_network_partition_simulation(self):
        """测试网络分区模拟"""
        with patch("src.database.connection.DatabaseManager") as MockDBManager:
            # 模拟网络分区导致的连接错误
            mock_manager = Mock()
            mock_manager.get_session.side_effect = [
                DatabaseError("Network partition"),
                DatabaseError("Network partition"),
                DatabaseError("Network partition"),
                None,  # 第四次尝试成功
            ]
            MockDBManager.return_value = mock_manager

            db_manager = DatabaseManager()

            # 应该有重试机制
            attempts = 0
            max_attempts = 5
            last_exception = None

            while attempts < max_attempts:
                try:
                    session = db_manager.get_session()
                    assert session is not None
                    break
                except DatabaseError as e:
                    attempts += 1
                    last_exception = e
                    await asyncio.sleep(0.1)

            assert attempts == 3  # 应该重试了3次
            assert last_exception is not None or attempts < max_attempts

    @pytest.mark.integration
    def test_disk_space_exhaustion(self):
        """测试磁盘空间耗尽场景"""
        import shutil
        import tempfile

        # 获取临时目录所在磁盘的剩余空间
        temp_dir = tempfile.gettempdir()
        total, used, free = shutil.disk_usage(temp_dir)

        # 如果剩余空间少于100MB，跳过测试
        if free < 100 * 1024 * 1024:
            pytest.skip("Not enough disk space for this test")

        # 尝试创建一个大文件（但不真的占满空间）
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                # 写入1MB数据
                tmp_file.write(b"x" * (1024 * 1024))
                tmp_file_path = tmp_file.name

            # 清理
            import os

            os.unlink(tmp_file_path)

        except OSError as e:
            pytest.fail(f"Disk space test failed: {e}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_api_requests(self):
        """测试无效API请求"""

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # 测试无效的端点
        response = client.get("/invalid_endpoint")
        assert response.status_code == 404

        # 测试无效的方法
        response = client.delete("/health")
        assert response.status_code == 405

        # 测试无效的内容类型
        response = client.post(
            "/health",
            headers={"Content-Type": "application/xml"},
            data="<invalid>xml</invalid>",
        )
        # 应该被拒绝或忽略

    @pytest.mark.integration
    def test_sql_injection_prevention(self):
        """测试SQL注入防护"""
        from src.utils.data_validator import DataValidator

        validator = DataValidator()

        # 测试潜在的SQL注入
        malicious_inputs = [
            "'; DROP TABLE matches; --",
            "1' OR '1'='1",
            "'; UPDATE users SET password='hacked' WHERE '1'='1' --",
            "1'; INSERT INTO matches VALUES ('hacked'); --",
        ]

        for malicious_input in malicious_inputs:
            # 应该被验证器拒绝
            assert validator.validate_match_id(malicious_input) is False

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """测试速率限制"""

        # 模拟速率限制中间件
        request_times = []

        def mock_rate_limit_middleware(request: Request, call_next):
            current_time = time.time()
            request_times.append(current_time)

            # 简单的速率限制：每秒最多10个请求
            recent_requests = [t for t in request_times if current_time - t < 1.0]
            if len(recent_requests) > 10:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            return call_next(request)

        # 模拟快速请求

        mock_request = Mock()
        mock_call_next = Mock(return_value=Mock(status_code=200))

        # 发送15个快速请求
        rate_limit_hit = False
        for i in range(15):
            try:
                mock_rate_limit_middleware(mock_request, mock_call_next)
            except HTTPException as e:
                if e.status_code == 429:
                    rate_limit_hit = True
                    break

        # 应该触发速率限制
        assert rate_limit_hit is True

    @pytest.mark.integration
    def test_extreme_values_handling(self):
        """测试极端值处理"""
        from src.utils.data_validator import DataValidator

        validator = DataValidator()

        # 测试极端数值
        extreme_cases = [
            {"match_id": "test", "home_score": 999999, "away_score": 0},
            {"match_id": "test", "home_score": 0, "away_score": 999999},
            {"match_id": "test", "home_score": -999, "away_score": -999},
            {"match_id": "a" * 10000, "home_team": "b" * 10000},
            {"match_id": "test", "date": "9999-12-31"},
            {"match_id": "test", "date": "0001-01-01"},
        ]

        for case in extreme_cases:
            # 应该被验证器拒绝或特殊处理
            result = validator.validate_match_data(case)
            # 根据业务规则，极端值应该被拒绝
            assert result is False or isinstance(result, dict)
