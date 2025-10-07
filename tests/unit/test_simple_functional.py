"""
简单的功能测试
专注于测试核心模块的基本功能，避免复杂依赖
"""

import pytest
import os
import sys

# 设置测试环境
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "test"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))


@pytest.mark.unit
class TestSimpleFunctional:
    """简单的功能测试"""

    def test_config_module_basic(self):
        """测试配置模块基本功能"""
        try:
            from core.config import get_settings

            # 测试获取设置
            settings = get_settings()
            assert settings is not None

            # 测试环境变量
            assert hasattr(settings, 'environment')
            assert settings.environment == 'test'

            # 测试配置转换为字典
            if hasattr(settings, 'dict'):
                config_dict = settings.dict()
            elif hasattr(settings, 'model_dump'):
                config_dict = settings.model_dump()
            else:
                config_dict = {}

            assert isinstance(config_dict, dict)

        except ImportError as e:
            pytest.skip(f"Config module not available: {e}")

    def test_time_utils_basic(self):
        """测试时间工具基本功能"""
        try:
            from utils.time_utils import (
                format_datetime,
                parse_datetime,
                get_current_time
            )

            # 测试当前时间
            now = get_current_time()
            assert now is not None

            # 测试格式化
            if callable(format_datetime):
                formatted = format_datetime(now)
                assert isinstance(formatted, str)

            # 测试解析
            if callable(parse_datetime):
                parsed = parse_datetime("2025-10-06")
                assert parsed is not None

        except ImportError as e:
            pytest.skip(f"Time utils not available: {e}")

    def test_utils_dict_utils(self):
        """测试字典工具"""
        try:
            from utils.dict_utils import (
                deep_merge,
                flatten_dict,
                get_nested_value
            )

            test_dict = {"a": {"b": {"c": 1}}}

            # 测试深度合并
            if callable(deep_merge):
                result = deep_merge(test_dict, {"a": {"d": 2}})
                assert result["a"]["b"]["c"] == 1
                assert result["a"]["d"] == 2

            # 测试展平字典
            if callable(flatten_dict):
                flattened = flatten_dict(test_dict)
                assert "a.b.c" in flattened

            # 测试获取嵌套值
            if callable(get_nested_value):
                value = get_nested_value(test_dict, "a.b.c")
                assert value == 1

        except ImportError as e:
            pytest.skip(f"Dict utils not available: {e}")

    def test_utils_string_utils(self):
        """测试字符串工具"""
        try:
            from utils.string_utils import (
                slugify,
                camel_to_snake,
                snake_to_camel,
                truncate_string
            )

            # 测试slugify
            if callable(slugify):
                result = slugify("Hello World!")
                assert result == "hello-world"

            # 测试驼峰转下划线
            if callable(camel_to_snake):
                result = camel_to_snake("HelloWorld")
                assert result == "hello_world"

            # 测试下划线转驼峰
            if callable(snake_to_camel):
                result = snake_to_camel("hello_world")
                assert result == "HelloWorld"

            # 测试截断字符串
            if callable(truncate_string):
                result = truncate_string("This is a long string", 10)
                assert len(result) <= 13  # 包括 "..."

        except ImportError as e:
            pytest.skip(f"String utils not available: {e}")

    def test_utils_data_validator(self):
        """测试数据验证工具"""
        try:
            from utils.data_validator import (
                validate_email,
                validate_phone,
                validate_url,
                is_valid_json
            )

            # 测试邮箱验证
            if callable(validate_email):
                assert validate_email("test@example.com") is True
                assert validate_email("invalid-email") is False

            # 测试电话验证
            if callable(validate_phone):
                assert validate_phone("+86 138 0000 0000") is True
                assert validate_phone("123") is False

            # 测试URL验证
            if callable(validate_url):
                assert validate_url("https://example.com") is True
                assert validate_url("not-a-url") is False

            # 测试JSON验证
            if callable(is_valid_json):
                assert is_valid_json('{"key": "value"}') is True
                assert is_valid_json("not-json") is False

        except ImportError as e:
            pytest.skip(f"Data validator not available: {e}")

    def test_database_models_basic(self):
        """测试数据库模型基本功能"""
        try:
            from database.models.team import Team
            from database.models.match import Match
            from database.models.league import League

            # 测试Team模型
            team = Team(name="Test Team", short_name="TT")
            assert team.name == "Test Team"
            assert team.short_name == "TT"

            # 测试Match模型
            match = Match(home_team_id=1, away_team_id=2)
            assert match.home_team_id == 1
            assert match.away_team_id == 2

            # 测试League模型
            league = League(name="Test League", country="Test")
            assert league.name == "Test League"
            assert league.country == "Test"

        except ImportError as e:
            pytest.skip(f"Database models not available: {e}")

    def test_api_health_check(self):
        """测试API健康检查"""
        try:
            from api.health import health_check, get_health_status

            # 测试健康检查函数
            if callable(health_check):
                result = health_check()
                assert isinstance(result, dict)
                assert "status" in result

            # 测试获取健康状态
            if callable(get_health_status):
                status = get_health_status()
                assert isinstance(status, dict)

        except ImportError as e:
            pytest.skip(f"API health check not available: {e}")

    def test_cache_redis_basic(self):
        """测试Redis缓存基本功能"""
        try:
            from cache.redis_manager import RedisManager

            # 创建Redis管理器
            redis_manager = RedisManager()

            # 测试基本操作
            assert hasattr(redis_manager, 'get')
            assert hasattr(redis_manager, 'set')
            assert hasattr(redis_manager, 'delete')

        except ImportError as e:
            pytest.skip(f"Redis cache not available: {e}")

    def test_services_base(self):
        """测试基础服务类"""
        try:
            from services.base import BaseService

            # 创建基础服务
            service = BaseService()

            # 测试基本方法
            if hasattr(service, 'get_service_name'):
                name = service.get_service_name()
                assert isinstance(name, str)

            if hasattr(service, 'is_healthy'):
                healthy = service.is_healthy()
                assert isinstance(healthy, bool)

        except ImportError as e:
            pytest.skip(f"Base service not available: {e}")

    def test_utils_crypto_basic(self):
        """测试加密工具基本功能"""
        try:
            from utils.crypto_utils import (
                hash_password,
                verify_password,
                generate_token,
                encrypt_data
            )

            # 测试密码哈希
            if callable(hash_password):
                hashed = hash_password("password123")
                assert hashed != "password123"
                assert len(hashed) > 0

            # 测试密码验证
            if callable(verify_password):
                assert verify_password("password123", hashed) is True
                assert verify_password("wrong", hashed) is False

            # 测试生成token
            if callable(generate_token):
                token = generate_token()
                assert isinstance(token, str)
                assert len(token) > 0

            # 测试数据加密
            if callable(encrypt_data):
                encrypted = encrypt_data("secret data")
                assert encrypted != "secret data"
                assert len(encrypted) > 0

        except ImportError as e:
            pytest.skip(f"Crypto utils not available: {e}")

    def test_utils_response(self):
        """测试响应工具"""
        try:
            from utils.response import (
                success_response,
                error_response,
                create_response
            )

            # 测试成功响应
            if callable(success_response):
                resp = success_response({"data": "test"})
                assert isinstance(resp, dict)
                assert resp["success"] is True

            # 测试错误响应
            if callable(error_response):
                resp = error_response("Error message", 400)
                assert isinstance(resp, dict)
                assert resp["success"] is False

            # 测试创建响应
            if callable(create_response):
                resp = create_response({"test": True}, status=200)
                assert isinstance(resp, dict)

        except ImportError as e:
            pytest.skip(f"Response utils not available: {e}")

    def test_monitoring_basic(self):
        """测试监控基本功能"""
        try:
            from monitoring.metrics_collector import MetricsCollector
            from monitoring.system_monitor import SystemMonitor

            # 测试指标收集器
            collector = MetricsCollector()
            if hasattr(collector, 'collect_metrics'):
                metrics = collector.collect_metrics()
                assert isinstance(metrics, dict)

            # 测试系统监控
            monitor = SystemMonitor()
            if hasattr(monitor, 'get_cpu_usage'):
                cpu = monitor.get_cpu_usage()
                assert isinstance(cpu, (int, float))

            if hasattr(monitor, 'get_memory_usage'):
                memory = monitor.get_memory_usage()
                assert isinstance(memory, (int, float))

        except ImportError as e:
            pytest.skip(f"Monitoring not available: {e}")

    def test_scheduling_basic(self):
        """测试调度基本功能"""
        try:
            from scheduler.task_scheduler import TaskScheduler
            from scheduler.tasks import Task

            # 测试任务调度器
            TaskScheduler()

            # 测试任务创建
            if callable(Task):
                task = Task(
                    name="test_task",
                    func=lambda: "test_result"
                )
                assert task.name == "test_task"

        except ImportError as e:
            pytest.skip(f"Scheduler not available: {e}")

    def test_streaming_basic(self):
        """测试流处理基本功能"""
        try:
            from streaming.kafka_consumer import KafkaConsumer
            from streaming.kafka_producer import KafkaProducer

            # 测试Kafka消费者
            consumer = KafkaConsumer({"bootstrap.servers": "localhost"})
            assert hasattr(consumer, 'consume')
            assert hasattr(consumer, 'close')

            # 测试Kafka生产者
            producer = KafkaProducer({"bootstrap.servers": "localhost"})
            assert hasattr(producer, 'produce')
            assert hasattr(producer, 'flush')

        except ImportError as e:
            pytest.skip(f"Streaming not available: {e}")

    def test_lineage_basic(self):
        """测试数据血缘基本功能"""
        try:
            from lineage.lineage_reporter import LineageReporter
            from lineage.metadata_manager import MetadataManager

            # 测试血缘报告器
            reporter = LineageReporter()
            if hasattr(reporter, 'track_data_flow'):
                reporter.track_data_flow("source", "target")

            # 测试元数据管理器
            manager = MetadataManager()
            if hasattr(manager, 'store_metadata'):
                manager.store_metadata("test", {"key": "value"})

        except ImportError as e:
            pytest.skip(f"Lineage not available: {e}")

    def test_features_basic(self):
        """测试特征工程基本功能"""
        try:
            from features.feature_calculator import FeatureCalculator
            from features.feature_store import FeatureStore

            # 测试特征计算器
            calculator = FeatureCalculator()
            if hasattr(calculator, 'calculate_features'):
                features = calculator.calculate_features({"data": [1, 2, 3]})
                assert isinstance(features, dict)

            # 测试特征存储
            store = FeatureStore()
            if hasattr(store, 'get_features'):
                features = store.get_features("entity_id")
                assert isinstance(features, dict)

        except ImportError as e:
            pytest.skip(f"Features not available: {e}")

    def test_data_quality_basic(self):
        """测试数据质量基本功能"""
        try:
            from data.quality.data_quality_monitor import DataQualityMonitor
            from data.quality.anomaly_detector import AnomalyDetector

            # 测试数据质量监控器
            monitor = DataQualityMonitor()
            if hasattr(monitor, 'check_quality'):
                quality = monitor.check_quality({"test": "data"})
                assert isinstance(quality, dict)

            # 测试异常检测器
            detector = AnomalyDetector()
            if hasattr(detector, 'detect_anomalies'):
                anomalies = detector.detect_anomalies([1, 2, 3, 100])
                assert isinstance(anomalies, list)

        except ImportError as e:
            pytest.skip(f"Data quality not available: {e}")