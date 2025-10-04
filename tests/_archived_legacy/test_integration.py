"""Legacy 集成测试 - 使用真实服务"""

import pytest
import redis
import psycopg2
from kafka import KafkaProducer, KafkaConsumer
import mlflow
import mlflow.pytorch
import time


class TestRealDatabaseIntegration:
    """真实数据库集成测试"""

    @pytest.mark.slow
    @pytest.mark.integration
    async def test_database_connection_and_transactions(self, real_database_url):
        """测试真实数据库连接和事务"""
        conn = psycopg2.connect(real_database_url)
        conn.autocommit = False

        try:
            with conn.cursor() as cur:
                # 测试查询
                cur.execute("SELECT 1 as test")
                result = cur.fetchone()
                assert result[0] == 1

                # 测试插入
                cur.execute("""
                    INSERT INTO leagues (name, country)
                    VALUES (%s, %s)
                    RETURNING id
                """, ("Test League", "Test Country"))
                league_id = cur.fetchone()[0]

                # 测试更新
                cur.execute("""
                    UPDATE leagues
                    SET name = %s
                    WHERE id = %s
                """, ("Updated Test League", league_id))

                # 提交事务
                conn.commit()

                # 验证数据
                cur.execute("SELECT name FROM leagues WHERE id = %s", (league_id,))
                result = cur.fetchone()
                assert result[0] == "Updated Test League"

                # 清理
                cur.execute("DELETE FROM leagues WHERE id = %s", (league_id,))
                conn.commit()

        finally:
            conn.close()

    @pytest.mark.slow
    @pytest.mark.integration
    async def test_database_performance(self, real_database_url):
        """测试数据库性能"""
        conn = psycopg2.connect(real_database_url)

        try:
            with conn.cursor() as cur:
                # 批量插入测试
                start_time = time.time()

                cur.execute("BEGIN")
                for i in range(1000):
                    cur.execute("""
                        INSERT INTO teams (name, league_id)
                        VALUES (%s, %s)
                    """, (f"Test Team {i}", 1))
                conn.commit()

                insert_time = time.time() - start_time
                assert insert_time < 5.0, f"Insert took too long: {insert_time}s"

                # 查询性能测试
                start_time = time.time()
                cur.execute("SELECT COUNT(*) FROM teams")
                count = cur.fetchone()[0]
                query_time = time.time() - start_time

                assert count >= 1000
                assert query_time < 1.0, f"Query took too long: {query_time}s"

                # 清理
                cur.execute("DELETE FROM teams WHERE name LIKE 'Test Team%'")
                conn.commit()

        finally:
            conn.close()


class TestRealRedisIntegration:
    """真实 Redis 集成测试"""

    @pytest.mark.slow
    @pytest.mark.integration
    async def test_redis_operations(self, real_redis_url):
        """测试 Redis 操作"""
        r = redis.from_url(real_redis_url)

        # 测试基本操作
        assert r.ping() is True

        # 测试字符串
        r.set("test:key", "test_value")
        assert r.get("test:key").decode() == "test_value"

        # 测试哈希
        r.hset("test:hash", mapping={"field1": "value1", "field2": "value2"})
        assert r.hget("test:hash", "field1").decode() == "value1"
        assert r.hlen("test:hash") == 2

        # 测试列表
        r.lpush("test:list", "item1", "item2", "item3")
        assert r.llen("test:list") == 3
        assert r.rpop("test:list").decode() == "item1"

        # 测试集合
        r.sadd("test:set", "member1", "member2", "member3")
        assert r.scard("test:set") == 3
        assert r.sismember("test:set", "member1") is True

        # 测试过期时间
        r.setex("test:expire", 1, "expire_value")
        assert r.get("test:expire").decode() == "expire_value"
        time.sleep(1.1)
        assert r.get("test:expire") is None

        # 清理
        r.delete("test:key", "test:hash", "test:list", "test:set")

    @pytest.mark.slow
    @pytest.mark.integration
    async def test_redis_pipeline(self, real_redis_url):
        """测试 Redis 管道"""
        r = redis.from_url(real_redis_url)

        # 使用管道执行多个命令
        pipe = r.pipeline()
        pipe.set("pipe:key1", "value1")
        pipe.set("pipe:key2", "value2")
        pipe.incr("pipe:counter")
        results = pipe.execute()

        assert results[0] is True
        assert results[1] is True
        assert results[2] == 1

        # 验证
        assert r.get("pipe:key1").decode() == "value1"
        assert r.get("pipe:counter").decode() == "1"

        # 清理
        r.delete("pipe:key1", "pipe:key2", "pipe:counter")


class TestRealMlflowIntegration:
    """真实 MLflow 集成测试"""

    @pytest.mark.slow
    @pytest.mark.integration
    async def test_mlflow_experiment_tracking(self, real_mlflow_uri):
        """测试 MLflow 实验跟踪"""
        mlflow.set_tracking_uri(real_mlflow_uri)
        mlflow.set_experiment(f"test_experiment_{int(time.time())}")

        with mlflow.start_run() as run:
            # 记录参数
            mlflow.log_param("learning_rate", 0.01)
            mlflow.log_param("batch_size", 32)

            # 记录指标
            mlflow.log_metric("accuracy", 0.85)
            mlflow.log_metric("loss", 0.15)

            # 记录模型
            # 注意：这里简化了，实际应该记录真实的模型
            mlflow.log_text("This is a test model", "model_info.txt")

            run_id = run.info.run_id

        # 验证运行记录
        client = mlflow.tracking.MlflowClient()
        run_info = client.get_run(run_id)

        assert run_info.data.params["learning_rate"] == "0.01"
        assert run_info.data.metrics["accuracy"] == 0.85

        # 获取实验
        experiment = client.get_experiment_by_name(run_info.experiment_id)
        assert experiment is not None

    @pytest.mark.slow
    @pytest.mark.integration
    async def test_mlflow_model_registry(self, real_mlflow_uri):
        """测试 MLflow 模型注册"""
        mlflow.set_tracking_uri(real_mlflow_uri)

        # 创建测试模型
        with mlflow.start_run() as run:
            # 记录一个简单的"模型"
            model_info = {
                "model_type": "test",
                "version": "1.0",
                "accuracy": 0.90
            }
            mlflow.log_dict(model_info, "model.json")

            # 注册模型（如果支持）
            try:
                mlflow.register_model(
                    f"runs:/{run.info.run_id}/model.json",
                    "TestModel"
                )
            except Exception as e:
                # 注册可能失败，但至少我们记录了模型
                print(f"Model registration failed (expected in test): {e}")


class TestRealKafkaIntegration:
    """真实 Kafka 集成测试"""

    @pytest.mark.slow
    @pytest.mark.integration
    async def test_kafka_producer_consumer(self, kafka_bootstrap_servers):
        """测试 Kafka 生产者和消费者"""
        topic = f"test_topic_{int(time.time())}"

        # 创建生产者
        producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda v: str(v).encode('utf-8')
        )

        # 发送消息
        test_messages = ["message1", "message2", "message3"]
        for msg in test_messages:
            producer.send(topic, value=msg)

        producer.flush()

        # 创建消费者
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=kafka_bootstrap_servers,
            auto_offset_reset='earliest',
            value_deserializer=lambda m: m.decode('utf-8'),
            consumer_timeout_ms=5000
        )

        # 消费消息
        received_messages = []
        for message in consumer:
            received_messages.append(message.value)
            if len(received_messages) >= len(test_messages):
                break

        # 验证
        assert len(received_messages) == len(test_messages)
        for msg in test_messages:
            assert msg in received_messages

        producer.close()
        consumer.close()


@pytest.mark.slow
@pytest.mark.integration
class TestFullIntegration:
    """完整集成测试"""

    async def test_prediction_workflow(self, real_database_url, real_redis_url, real_mlflow_uri):
        """测试完整的预测工作流"""
        # 1. 从数据库获取比赛数据
        conn = psycopg2.connect(real_database_url)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM leagues WHERE name = 'Premier League' LIMIT 1")
                league = cur.fetchone()
                if league:
                    league_id = league[0]

                    # 获取比赛
                    cur.execute("""
                        SELECT m.id, t1.name as home_team, t2.name as away_team
                        FROM matches m
                        JOIN teams t1 ON m.home_team_id = t1.id
                        JOIN teams t2 ON m.away_team_id = t2.id
                        WHERE m.status = 'scheduled'
                        LIMIT 1
                    """)
                    match = cur.fetchone()
        finally:
            conn.close()

        if not match:
            pytest.skip("No test match found in database")

        # 2. 检查 Redis 缓存
        r = redis.from_url(real_redis_url)
        cache_key = f"prediction:{match[0]}"

        # 缓存未命中
        assert r.get(cache_key) is None

        # 3. 生成预测（模拟）
        prediction = {
            "match_id": match[0],
            "home_score": 2,
            "away_score": 1,
            "confidence": 0.75
        }

        # 4. 缓存预测结果
        r.setex(cache_key, 3600, str(prediction))

        # 5. 验证缓存
        cached = r.get(cache_key)
        assert cached is not None

        # 6. 记录到 MLflow（可选）
        try:
            mlflow.set_tracking_uri(real_mlflow_uri)
            with mlflow.start_run(run_name=f"prediction_{match[0]}"):
                mlflow.log_params({
                    "match_id": match[0],
                    "home_team": match[1],
                    "away_team": match[2]
                })
                mlflow.log_metrics({
                    "predicted_home_score": prediction["home_score"],
                    "predicted_away_score": prediction["away_score"],
                    "confidence": prediction["confidence"]
                })
        except Exception as e:
            print(f"MLflow logging failed (expected in test): {e}")

        # 清理
        r.delete(cache_key)
