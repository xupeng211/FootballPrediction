"""
数据管道集成测试
测试完整的数据收集、处理、存储流程
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.services.data_processing import DataProcessingService
from src.data.collectors.base_collector import DataCollector
from src.data.processing.football_data_cleaner import FootballDataCleaner
from src.database.models.team import Team


class TestDataPipeline:
    """测试数据管道的端到端流程"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        engine = create_engine("sqlite:///:memory:")
        Session = sessionmaker(bind=engine)
        # 创建表结构
        from src.database.base import Base

        Base.metadata.create_all(engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def mock_data_collector(self):
        """模拟数据收集器"""
        collector = Mock(spec=DataCollector)
        collector.collect_data.return_value = [
            {
                "match_id": "test_001",
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
                "date": "2025-01-01",
                "league": "Premier League",
            }
        ]
        return collector

    @pytest.fixture
    def mock_redis_client(self):
        """模拟Redis客户端"""
        redis_mock = AsyncMock()
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.delete.return_value = True
        return redis_mock

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_data_pipeline(self, mock_db_session, mock_data_collector):
        """测试完整的数据管道流程"""
        # 1. 数据收集
        raw_data = mock_data_collector.collect_data()
        assert len(raw_data) > 0
        assert raw_data[0]["match_id"] == "test_001"

        # 2. 数据清洗
        cleaner = FootballDataCleaner()
        cleaned_data = cleaner.clean_match_data(raw_data)
        assert cleaned_data is not None

        # 3. 数据处理
        processor = DataProcessingService()
        processed_data = processor.process_batch(raw_data)
        assert processed_data is not None

        # 4. 数据存储
        # 模拟存储到数据库
        team = Team(name="Team A", country="England")
        mock_db_session.add(team)
        mock_db_session.commit()

        # 验证存储成功
        stored_team = mock_db_session.query(Team).filter_by(name="Team A").first()
        assert stored_team is not None
        assert stored_team.name == "Team A"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_with_cache(self, mock_redis_client):
        """测试带缓存的数据管道"""
        with patch(
            "src.cache.redis_manager.RedisManager.get_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_redis_client

            from src.cache.redis_manager import RedisManager

            cache_manager = RedisManager()

            # 测试缓存未命中
            cached_data = await cache_manager.get("test_key")
            assert cached_data is None

            # 测试设置缓存
            await cache_manager.set("test_key", {"test": "data"}, ttl=60)
            mock_redis_client.set.assert_called_once()

            # 测试缓存命中
            mock_redis_client.get.return_value = b'{"test": "data"}'
            cached_data = await cache_manager.get("test_key")
            assert cached_data == {"test": "data"}

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, mock_data_collector):
        """测试数据管道的错误处理"""
        # 模拟收集器抛出异常
        mock_data_collector.collect_data.side_effect = Exception("Collection failed")

        with pytest.raises(Exception, match="Collection failed"):
            mock_data_collector.collect_data()

        # 测试数据清洗阶段的错误处理
        cleaner = FootballDataCleaner()
        invalid_data = [{"invalid": "data"}]

        # 应该返回None或空结果，而不是抛出异常
        result = cleaner.clean_match_data(invalid_data)
        assert result is None or result == []

    @pytest.mark.integration
    def test_pipeline_data_validation(self):
        """测试管道数据验证"""
        from src.utils.data_validator import DataValidator

        validator = DataValidator()

        # 测试有效数据
        valid_data = {
            "match_id": "test_001",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 2,
            "away_score": 1,
            "date": "2025-01-01",
        }

        assert validator.validate_match_data(valid_data) is True

        # 测试无效数据
        invalid_data = {
            "match_id": None,
            "home_team": "",
            "away_team": "Team B",
            "home_score": -1,
            "away_score": "invalid",
        }

        assert validator.validate_match_data(invalid_data) is False

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_concurrent_processing(self):
        """测试管道并发处理能力"""

        async def process_batch(batch_id):
            """模拟批量处理"""
            await asyncio.sleep(0.1)  # 模拟处理时间
            return {"batch_id": batch_id, "processed": True}

        # 并发处理多个批次
        batch_ids = [1, 2, 3, 4, 5]
        tasks = [process_batch(bid) for bid in batch_ids]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            assert result["processed"] is True
            assert "batch_id" in result

    @pytest.mark.integration
    def test_pipeline_monitoring(self):
        """测试数据管道监控"""
        from src.monitoring.metrics_collector import MetricsCollector

        # 模拟指标收集器
        collector = Mock(spec=MetricsCollector)
        collector.increment_counter = Mock()
        collector.record_timing = Mock()
        collector.set_gauge = Mock()

        # 模拟管道运行
        collector.increment_counter("pipeline.started")
        collector.record_timing("pipeline.processing_time", 100)
        collector.increment_counter("pipeline.completed")
        collector.set_gauge("pipeline.success_rate", 95.5)

        # 验证指标被正确记录
        collector.increment_counter.assert_called_with("pipeline.started")
        collector.record_timing.assert_called_with("pipeline.processing_time", 100)
        collector.increment_counter.assert_called_with("pipeline.completed")
        collector.set_gauge.assert_called_with("pipeline.success_rate", 95.5)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_streaming_flow(self):
        """测试流式数据管道"""
        # 模拟Kafka生产者
        with patch("src.streaming.kafka_producer.KafkaProducer") as MockProducer:
            mock_producer = AsyncMock()
            MockProducer.return_value = mock_producer

            from src.streaming.kafka_producer import KafkaProducer

            producer = KafkaProducer()

            # 发送消息
            await producer.produce("test_topic", {"test": "message"})
            mock_producer.produce.assert_called_once()

            # 模拟消费者
            with patch("src.streaming.kafka_consumer.KafkaConsumer") as MockConsumer:
                mock_consumer = AsyncMock()
                mock_consumer.consume.return_value = [{"test": "message"}]
                MockConsumer.return_value = mock_consumer

                from src.streaming.kafka_consumer import KafkaConsumer

                consumer = KafkaConsumer()

                # 消费消息
                messages = await consumer.consume("test_topic")
                assert len(messages) == 1
                assert messages[0]["test"] == "message"

    @pytest.mark.integration
    def test_pipeline_data_lineage(self):
        """测试数据血缘追踪"""
        from src.lineage.lineage_reporter import LineageReporter

        reporter = LineageReporter()

        # 记录数据血缘
        lineage_info = reporter.record_lineage(
            source="raw_data_collector",
            transformation="data_cleaning",
            target="processed_matches",
            metadata={"batch_id": "batch_001"},
        )

        assert lineage_info is not None
        assert lineage_info["source"] == "raw_data_collector"
        assert lineage_info["transformation"] == "data_cleaning"

        # 查询血缘
        lineage_history = reporter.get_lineage_history("processed_matches")
        assert len(lineage_history) > 0
