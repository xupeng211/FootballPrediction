"""
外部依赖Mock测试

验证所有外部依赖mock是否正常工作
"""

import pytest

from tests.external_mocks import (
    MockCounter,
    MockDatabaseManager,
    MockFeatureStore,
    MockGauge,
    MockHistogram,
    MockKafkaConsumer,
    MockKafkaProducer,
    MockMLflowClient,
    MockRedisManager,
    create_mock_async_session,
    create_mock_sync_session,
)


class TestRedisMocks:
    """Redis Mock测试"""

    @pytest.mark.asyncio
    async def test_mock_redis_manager(self):
        """测试Redis管理器Mock"""
        redis = MockRedisManager()

        # 测试基本操作
        await redis.aset("test_key", "test_value")
        value = await redis.aget("test_key")
    assert value == "test_value"

        # 测试存在性检查
        exists = await redis.aexists("test_key")
    assert exists is True

        # 测试删除
        await redis.adelete("test_key")
        value = await redis.aget("test_key")
    assert value is None

    @pytest.mark.asyncio
    async def test_mock_redis_ttl(self):
        """测试Redis TTL功能"""
        redis = MockRedisManager()

        # Mock版本的TTL实际上不会过期，但可以验证功能
        await redis.aset("ttl_key", "ttl_value", expire=60)
        value = await redis.aget("ttl_key")
    assert value == "ttl_value"


class TestMLflowMocks:
    """MLflow Mock测试"""

    def test_mock_mlflow_client(self):
        """测试MLflow客户端Mock"""
        client = MockMLflowClient()

        # 创建实验
        exp_id = client.create_experiment("test_experiment")
    assert exp_id is not None

        # 创建运行
        run_id = client.create_run(exp_id, "test_run")
    assert run_id is not None

        # 记录参数和指标
        client.log_param(run_id, "param1", "value1")
        client.log_metric(run_id, "metric1", 0.95)

        # 完成运行
        client.set_terminated(run_id)

        # 验证数据
    assert run_id in client.runs
    assert client.runs[run_id]["params"]["param1"] == "value1"
    assert client.runs[run_id]["metrics"]["metric1"] == 0.95


class TestKafkaMocks:
    """Kafka Mock测试"""

    @pytest.mark.asyncio
    async def test_mock_kafka_producer(self):
        """测试Kafka生产者Mock"""
        producer = MockKafkaProducer()

        # 发送消息
        await producer.start()
        await producer.send("test_topic", {"data": "test"}, key="test_key")

        # 验证消息
    assert len(producer.messages) == 1
    assert producer.messages[0]["topic"] == "test_topic"
    assert producer.messages[0]["value"] == {"data": "test"}
    assert producer.messages[0]["key"] == "test_key"

        await producer.stop()

    @pytest.mark.asyncio
    async def test_mock_kafka_consumer(self):
        """测试Kafka消费者Mock"""
        consumer = MockKafkaConsumer()

        # 添加测试消息
        consumer.add_message({"topic": "test_topic", "value": "test_data"})

        # 获取消息（简化版本）
        await consumer.start()
        messages = await consumer.getmany()
        await consumer.stop()

        # 验证消息结构
    assert len(messages) > 0


class TestFeatureStoreMocks:
    """Feature Store Mock测试"""

    def test_mock_feature_store(self):
        """测试特征存储Mock"""
        store = MockFeatureStore()

        # 测试在线特征获取
        features = ["feature1", "feature2", "feature3"]
        entity_rows = [{"entity_id": 1}]

        result = store.get_online_features(features, entity_rows)

        # 验证结果格式
        feature_dict = result.to_dict()
    assert "feature1" in feature_dict
    assert "feature2" in feature_dict
    assert "feature3" in feature_dict

    def test_mock_feature_store_operations(self):
        """测试特征存储操作"""
        store = MockFeatureStore()

        # 测试写入和物化
        success = store.write_to_online_store("test_view", {"data": "test"})
    assert success is True

        success = store.materialize_incremental("2025-01-01")
    assert success is True


class TestPrometheusMocks:
    """Prometheus Mock测试"""

    def test_mock_counter(self):
        """测试计数器Mock"""
        counter = MockCounter("test_counter", "Test counter")

        # 基本计数
        counter.inc()
    assert counter.get_value() == 1.0

        # 带标签计数
        counter.labels(method="get", endpoint="_api").inc()
        counter.labels(method="post", endpoint="/api").inc()

    assert len(counter._values) == 2

    def test_mock_gauge(self):
        """测试仪表Mock"""
        gauge = MockGauge("test_gauge", "Test gauge")

        # 设置值
        gauge.set(10.5)
    assert gauge.get_value() == 10.5

        # 增减值
        gauge.inc(2.5)
    assert gauge.get_value() == 13.0

        gauge.dec(1.0)
    assert gauge.get_value() == 12.0

    def test_mock_histogram(self):
        """测试直方图Mock"""
        histogram = MockHistogram("test_histogram", "Test histogram")

        # 观察值
        histogram.observe(1.0)
        histogram.observe(2.0)
        histogram.observe(3.0)

    assert len(histogram._observations) == 3


class TestDatabaseMocks:
    """数据库Mock测试"""

    def test_mock_database_manager(self):
        """测试数据库管理器Mock"""
        manager = MockDatabaseManager()

        # 测试会话获取
        sync_session = manager.get_session()
        async_session = manager.get_async_session()

    assert sync_session is not None
    assert async_session is not None

    def test_mock_session_creation(self):
        """测试模拟会话创建"""
        sync_session = create_mock_sync_session()
        async_session = create_mock_async_session()

        # 验证基本方法存在
    assert hasattr(sync_session, "execute")
    assert hasattr(sync_session, "commit")
    assert hasattr(sync_session, "rollback")

    assert hasattr(async_session, "execute")
    assert hasattr(async_session, "commit")
    assert hasattr(async_session, "rollback")

    def test_mock_session_queries(self):
        """测试模拟会话查询"""
        session = create_mock_sync_session()

        # 测试标量查询
        result = session.execute("SELECT 1")
        scalar = result.scalar()
    assert scalar == 1

        # 测试列表查询
        result = session.execute("SELECT * FROM test")
        rows = result.fetchall()
    assert rows == []


class TestMockIntegration:
    """Mock集成测试"""

    @pytest.mark.asyncio
    async def test_combined_mock_usage(self):
        """测试组合使用多个Mock"""
        # 创建各种Mock
        redis = MockRedisManager()
        mlflow = MockMLflowClient()
        kafka = MockKafkaProducer()

        # 模拟一个完整的工作流
        # 1. 缓存数据
        await redis.aset("workflow_data", {"processed": True})

        # 2. 记录MLflow指标
        run_id = mlflow.create_run(1, "workflow_run")
        mlflow.log_metric(run_id, "accuracy", 0.95)

        # 3. 发送Kafka消息
        await kafka.send("workflow_topic", {"status": "completed"})

        # 验证结果
        cached_data = await redis.aget("workflow_data")
    assert cached_data == {"processed": True}

    assert run_id in mlflow.runs
    assert len(kafka.messages) == 1

    def test_sync_workflow_mocks(self):
        """测试同步工作流Mock"""
        # 创建同步Mock
        counter = MockCounter("workflow_counter", "Workflow counter")
        gauge = MockGauge("workflow_gauge", "Workflow gauge")

        # 模拟工作流指标
        counter.inc()
        gauge.set(100)

    assert counter.get_value() == 1.0
    assert gauge.get_value() == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
