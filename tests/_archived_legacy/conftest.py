"""Legacy 测试配置 - 使用真实服务"""

import pytest
from pathlib import Path
import os
import sys

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# 标记配置
def pytest_configure(config):
    """配置 pytest 标记"""
    config.addinivalue_line(
        "markers", "legacy: 标记为需要真实服务的遗留测试"
    )
    config.addinivalue_line(
        "markers", "slow: 标记为慢速测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记为集成测试"
    )


@pytest.fixture(scope="session")
def real_database_url():
    """真实数据库 URL"""
    return os.getenv("DATABASE_URL", "postgresql://postgres:testpass@localhost:5432/football_test")


@pytest.fixture(scope="session")
def real_redis_url():
    """真实 Redis URL"""
    return os.getenv("REDIS_URL", "redis://localhost:6379")


@pytest.fixture(scope="session")
def real_mlflow_uri():
    """真实 MLflow URI"""
    return os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")


@pytest.fixture(scope="session")
def kafka_bootstrap_servers():
    """Kafka Bootstrap 服务器"""
    return os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


@pytest.fixture(scope="session", autouse=True)
def check_real_services():
    """检查真实服务是否可用"""
    import redis
    import psycopg2
    import requests

    # 检查 Redis
    try:
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        redis_client.ping()
        print("✅ Redis 连接成功")
    except Exception as e:
        pytest.skip(f"❌ Redis 不可用: {e}")

    # 检查 PostgreSQL
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL", "postgresql://postgres:testpass@localhost:5432/football_test"))
        conn.close()
        print("✅ PostgreSQL 连接成功")
    except Exception as e:
        pytest.skip(f"❌ PostgreSQL 不可用: {e}")

    # 检查 MLflow
    try:
        response = requests.get(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000/health"), timeout=5)
        if response.status_code == 200:
            print("✅ MLflow 连接成功")
        else:
            pytest.skip("❌ MLflow 健康检查失败")
    except Exception:
        pytest.skip("❌ MLflow 不可用")

    # 检查 Kafka（可选）
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
        producer.close()
        print("✅ Kafka 连接成功")
    except Exception:
        print("⚠️ Kafka 不可用，跳过相关测试")


@pytest.fixture
def cleanup_database(real_database_url):
    """清理数据库的 fixture"""
    import psycopg2
    from contextlib import contextmanager

    @contextmanager
    def _cleanup():
        conn = psycopg2.connect(real_database_url)
        try:
            # 清理所有表（除了迁移表）
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name NOT LIKE 'alembic%'
                """)
                tables = cur.fetchall()

                for table in tables:
                    cur.execute(f'TRUNCATE TABLE {table[0]} CASCADE')
            conn.commit()
        finally:
            conn.close()

    return _cleanup


# 为所有 legacy 测试添加标记
pytestmark = pytest.mark.legacy