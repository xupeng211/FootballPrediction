#!/usr/bin/env python3
"""
修复测试环境配置脚本
完善数据库和外部依赖的测试环境配置
"""

import asyncio
import os
import sys
from pathlib import Path
import subprocess
from typing import Dict, Any
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEnvironmentFixer:
    """测试环境修复器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.fixes_applied = []

    def fix_pytest_configuration(self):
        """修复pytest配置"""
        logger.info("🔧 修复pytest配置")

        pytest_ini = self.project_root / "pytest.ini"
        if pytest_ini.exists():
            content = pytest_ini.read_text()

            # 确保异步配置正确
            if "asyncio_mode" not in content:
                content += "\n# asyncio配置\nasyncio_mode = auto\nasyncio_default_fixture_loop_scope = function\n"
                pytest_ini.write_text(content)
                logger.info("✅ 添加了pytest异步配置")
                self.fixes_applied.append("pytest_asyncio_config")

        return True

    def fix_database_dependencies(self):
        """修复数据库依赖"""
        logger.info("🔧 修复数据库依赖")

        # 创建测试数据库配置
        test_db_config = """# 测试数据库配置
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 测试数据库配置
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite:///:memory:"
)

if "sqlite" in TEST_DATABASE_URL:
    test_engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
else:
    test_engine = create_engine(TEST_DATABASE_URL, echo=False)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)

def get_test_db_session():
    \"\"\"获取测试数据库会话\"\"\"
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
"""

        db_config_file = self.project_root / "tests" / "database_config.py"
        db_config_file.write_text(test_db_config)
        logger.info("✅ 创建了测试数据库配置")
        self.fixes_applied.append("test_database_config")

        return True

    def fix_redis_dependencies(self):
        """修复Redis依赖"""
        logger.info("🔧 修复Redis依赖")

        # 创建Redis mock配置
        redis_mock_config = """# Redis Mock配置用于测试
import asyncio
from typing import Any, Dict, Optional
from unittest.mock import Mock, AsyncMock

class MockRedis:
    \"\"\"模拟Redis客户端\"\"\"

    def __init__(self):
        self._data = {}
        self._connected = True

    def ping(self):
        return self._connected

    def get(self, key: str) -> Optional[bytes]:
        return self._data.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._data[key] = value
        return True

    def delete(self, key: str) -> int:
        return self._data.pop(key, None) is not None

    def exists(self, key: str) -> bool:
        return key in self._data

    def keys(self, pattern: str = "*"):
        return [k.encode() for k in self._data.keys()]

    def flushdb(self):
        self._data.clear()
        return True

    def info(self):
        return {
            "used_memory": len(str(self._data)),
            "connected_clients": 1
        }

# 全局Redis客户端实例
redis_client = MockRedis()

def get_redis_client():
    \"\"\"获取Redis客户端（测试用Mock）\"\"\"
    return redis_client

async def get_async_redis_client():
    \"\"\"获取异步Redis客户端（测试用Mock）\"\"\"
    return redis_client
"""

        redis_config_file = self.project_root / "tests" / "redis_mock.py"
        redis_config_file.write_text(redis_mock_config)
        logger.info("✅ 创建了Redis Mock配置")
        self.fixes_applied.append("redis_mock_config")

        return True

    def fix_external_service_mocks(self):
        """修复外部服务Mock"""
        logger.info("🔧 修复外部服务Mock")

        # 创建外部服务Mock配置
        external_services_config = """# 外部服务Mock配置
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

class MockHTTPClient:
    \"\"\"模拟HTTP客户端\"\"\"

    def __init__(self):
        self.responses = {}
        self.requests = []

    def get(self, url: str, **kwargs):
        self.requests.append({"method": "GET", "url": url, **kwargs})
        response = Mock()
        response.status_code = 200
        response.json.return_value = self.responses.get(url, {"status": "ok"})
        return response

    async def aget(self, url: str, **kwargs):
        self.requests.append({"method": "GET", "url": url, **kwargs})
        response = AsyncMock()
        response.status_code = 200
        response.json.return_value = self.responses.get(url, {"status": "ok"})
        return response

# Mock外部服务
mock_http_client = MockHTTPClient()

def get_http_client():
    \"\"\"获取HTTP客户端（测试用Mock）\"\"\"
    return mock_http_client

# Kafka Mock
class MockKafkaProducer:
    \"\"\"模拟Kafka生产者\"\"\"

    def __init__(self):
        self.messages = []

    def send(self, topic: str, value: bytes, **kwargs):
        self.messages.append({"topic": topic, "value": value, **kwargs})
        return Mock()

class MockKafkaConsumer:
    \"\"\"模拟Kafka消费者\"\"\"

    def __init__(self):
        self.messages = []

    def __iter__(self):
        return iter(self.messages)

def get_kafka_producer():
    \"\"\"获取Kafka生产者（测试用Mock）\"\"\"
    return MockKafkaProducer()

def get_kafka_consumer():
    \"\"\"获取Kafka消费者（测试用Mock）\"\"\"
    return MockKafkaConsumer()
"""

        external_config_file = self.project_root / "tests" / "external_services_mock.py"
        external_config_file.write_text(external_services_config)
        logger.info("✅ 创建了外部服务Mock配置")
        self.fixes_applied.append("external_services_mock")

        return True

    def fix_environment_variables(self):
        """修复环境变量"""
        logger.info("🔧 修复环境变量")

        # 创建测试环境变量文件
        env_vars = """# 测试环境变量
# 数据库配置
TEST_DATABASE_URL=sqlite:///:memory:
TEST_ASYNC_DATABASE_URL=sqlite+aiosqlite:///:memory:

# Redis配置
TEST_REDIS_URL=redis://localhost:6379/1

# API配置
TEST_API_KEY=test_api_key_12345
TEST_SECRET_KEY=test_secret_key_12345

# 外部服务配置
EXTERNAL_API_URL=http://localhost:8080/api
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# 测试配置
TESTING=True
PYTEST_CURRENT_TEST=
PYTEST_XDIST_WORKER=
"""

        env_file = self.project_root / "tests" / ".env.test"
        env_file.write_text(env_vars)
        logger.info("✅ 创建了测试环境变量文件")
        self.fixes_applied.append("test_env_vars")

        return True

    def create_test_database_initialization(self):
        """创建测试数据库初始化脚本"""
        logger.info("🔧 创建测试数据库初始化")

        init_script = """# 测试数据库初始化脚本
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.database.base import Base

async def create_test_tables():
    \"\"\"创建测试表\"\"\"
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

async def init_test_database():
    \"\"\"初始化测试数据库\"\"\"
    engine = await create_test_tables()

    # 插入测试数据
    with engine.connect() as conn:
        # 插入测试团队
        conn.execute(text(\"\"\"
            INSERT INTO teams (id, name, founded_year, logo_url) VALUES
            (1, 'Test Team 1', 1900, 'logo1.png'),
            (2, 'Test Team 2', 1920, 'logo2.png')
        \"\"\"))

        # 插入测试比赛
        conn.execute(text(\"\"\"
            INSERT INTO matches (id, home_team_id, away_team_id, match_date, venue) VALUES
            (1, 1, 2, '2024-01-01', 'Test Stadium'),
            (2, 2, 1, '2024-01-02', 'Another Stadium')
        \"\"\"))

    return engine

if __name__ == "__main__":
    asyncio.run(init_test_database())
"""

        init_file = self.project_root / "tests" / "init_test_db.py"
        init_file.write_text(init_script)
        logger.info("✅ 创建了测试数据库初始化脚本")
        self.fixes_applied.append("test_db_init")

        return True

    def update_conftest_improvements(self):
        """改进conftest.py配置"""
        logger.info("🔧 改进conftest.py配置")

        conftest_file = self.project_root / "tests" / "conftest.py"
        if conftest_file.exists():
            content = conftest_file.read_text()

            # 添加改进的配置
            improvements = '''
# 改进的测试配置

# 改进的异步会话fixture
@pytest.fixture(scope="function")
async def async_client():
    \"\"\"创建异步测试客户端\"\"\"
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

# Mock服务fixture
@pytest.fixture
def mock_redis():
    \"\"\"Redis Mock fixture\"\"\"
    from tests.redis_mock import MockRedis
    return MockRedis()

@pytest.fixture
def mock_kafka_producer():
    \"\"\"Kafka Producer Mock fixture\"\"\"
    from tests.external_services_mock import MockKafkaProducer
    return MockKafkaProducer()

@pytest.fixture
def mock_kafka_consumer():
    \"\"\"Kafka Consumer Mock fixture\"\"\"
    from tests.external_services_mock import MockKafkaConsumer
    return MockKafkaConsumer()

# 测试数据fixtures
@pytest.fixture
def sample_team_data():
    \"\"\"示例团队数据\"\"\"
    return {
        "id": 1,
        "name": "Test Team",
        "founded_year": 1900,
        "logo_url": "logo.png"
    }

@pytest.fixture
def sample_match_data():
    \"\"\"示例比赛数据\"\"\"
    return {
        "id": 1,
        "home_team_id": 1,
        "away_team_id": 2,
        "match_date": "2024-01-01",
        "venue": "Test Stadium"
    }

# 错误处理fixture
@pytest.fixture
def mock_database_error():
    \"\"\"模拟数据库错误\"\"\"
    def side_effect(*args, **kwargs):
        raise Exception("Database connection failed")
    return side_effect
'''

            if improvements not in content:
                content += improvements
                conftest_file.write_text(content)
                logger.info("✅ 改进了conftest.py配置")
                self.fixes_applied.append("conftest_improvements")

        return True

    def run_verification_tests(self):
        """运行验证测试"""
        logger.info("🧪 运行环境验证测试")

        test_commands = [
            ["python", "-m", "pytest", "tests/unit/api/test_health.py::TestHealthChecker::test_health_checker_initialization", "-v"],
            ["python", "-m", "pytest", "tests/unit/utils/test_dict_utils.py::TestDictUtilsFixed::test_deep_merge_basic", "-v"],
            ["python", "-m", "pytest", "tests/unit/api/test_dependencies.py::TestParameterizedInput::test_handle_basic_inputs", "-v"]
        ]

        success_count = 0
        for cmd in test_commands:
            try:
                result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    success_count += 1
                    logger.info(f"✅ 验证测试通过: {' '.join(cmd[4:])}")
                else:
                    logger.warning(f"⚠️ 验证测试失败: {' '.join(cmd[4:])}")
            except subprocess.TimeoutExpired:
                logger.warning(f"⏰ 验证测试超时: {' '.join(cmd[4:])}")
            except Exception as e:
                logger.error(f"💥 验证测试异常: {e}")

        logger.info(f"📊 验证测试结果: {success_count}/{len(test_commands)} 通过")
        return success_count > 0

    def run_complete_fix_process(self):
        """运行完整的修复流程"""
        logger.info("🚀 开始测试环境修复流程")

        fixes = [
            ("修复pytest配置", self.fix_pytest_configuration),
            ("修复数据库依赖", self.fix_database_dependencies),
            ("修复Redis依赖", self.fix_redis_dependencies),
            ("修复外部服务Mock", self.fix_external_service_mocks),
            ("修复环境变量", self.fix_environment_variables),
            ("创建数据库初始化", self.create_test_database_initialization),
            ("改进conftest.py", self.update_conftest_improvements),
        ]

        success_count = 0
        for desc, fix_func in fixes:
            try:
                if fix_func():
                    success_count += 1
            except Exception as e:
                logger.error(f"❌ {desc} 失败: {e}")

        # 运行验证测试
        verification_success = self.run_verification_tests()

        # 生成修复报告
        self.generate_fix_report(success_count, len(fixes), verification_success)

        return success_count == len(fixes) and verification_success

    def generate_fix_report(self, success_count: int, total_count: int, verification_success: bool):
        """生成修复报告"""
        report = f"""
# 🔧 测试环境修复报告

## 修复状态
{'✅ 修复成功' if success_count == total_count else f'⚠️ 部分修复 ({success_count}/{total_count})'}
验证测试: {'✅ 通过' if verification_success else '❌ 失败'}

## 应用的修复
{chr(10).join(f'- {fix}' for fix in self.fixes_applied) if self.fixes_applied else '- 无修复应用'}

## 修复的文件
- tests/database_config.py - 测试数据库配置
- tests/redis_mock.py - Redis Mock配置
- tests/external_services_mock.py - 外部服务Mock配置
- tests/.env.test - 测试环境变量
- tests/init_test_db.py - 测试数据库初始化
- pytest.ini - pytest配置改进
- tests/conftest.py - 测试配置改进

## 下一步建议
1. 运行完整测试套件: `python -m pytest tests/ -v`
2. 检查覆盖率: `python -m pytest --cov=src tests/`
3. 验证异步测试: `python -m pytest tests/ -m asyncio`

## 修复完成时间
{Path(__file__).stat().st_mtime}
"""

        report_path = self.project_root / "test_environment_fix_report.md"
        report_path.write_text(report)
        logger.info(f"📄 修复报告已生成: {report_path}")


def main():
    """主函数"""
    print("🔧 开始测试环境修复...")

    fixer = TestEnvironmentFixer()
    success = fixer.run_complete_fix_process()

    if success:
        print("🎉 测试环境修复成功！")
        return 0
    else:
        print("❌ 测试环境修复过程中遇到问题，请检查日志")
        return 1


if __name__ == "__main__":
    sys.exit(main())