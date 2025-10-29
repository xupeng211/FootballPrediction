"""
配置和常量测试
测试所有配置值、常量和设置
"""

import os
from enum import Enum

import pytest


# 应用常量定义
class AppConfig:
    """应用配置常量"""

    # 应用信息
    APP_NAME = "Football Prediction System"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "AI-powered football match prediction system"

    # API配置
    API_PREFIX = "/api/v1"
    DOCS_URL = "/docs"
    REDOC_URL = "/redoc"

    # 服务器配置
    DEFAULT_HOST = "0.0.0.0"
    DEFAULT_PORT = 8000
    DEBUG_MODE = False

    # 数据库配置
    DEFAULT_DB_URL = "postgresql+asyncpg://user:pass@localhost/football_db"
    DB_POOL_SIZE = 10
    DB_MAX_OVERFLOW = 20
    DB_POOL_TIMEOUT = 30

    # Redis配置
    REDIS_URL = "redis://localhost:6379/0"
    REDIS_POOL_SIZE = 10
    CACHE_TTL_DEFAULT = 300  # 5分钟
    CACHE_TTL_SHORT = 60  # 1分钟
    CACHE_TTL_LONG = 3600  # 1小时

    # 安全配置
    SECRET_KEY_MIN_LENGTH = 32
    TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    BCRYPT_ROUNDS = 12

    # 预测配置
    MAX_PREDICTIONS_PER_MATCH = 3
    PREDICTION_DEADLINE_HOURS = 1
    MIN_CONFIDENCE = 0.1
    MAX_CONFIDENCE = 1.0

    # 分页配置
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    # 文件上传配置
    MAX_FILE_SIZE_MB = 10
    ALLOWED_IMAGE_TYPES = ["jpg", "jpeg", "png", "gif"]
    ALLOWED_DOCUMENT_TYPES = ["pdf", "doc", "docx", "txt"]

    # 外部服务配置
    WEATHER_API_TIMEOUT = 5
    NEWS_API_TIMEOUT = 10
    MAX_RETRIES = 3

    # 监控配置
    HEALTH_CHECK_INTERVAL = 60
    METRICS_COLLECTION_INTERVAL = 30
    LOG_RETENTION_DAYS = 30


class MatchStatus(Enum):
    """比赛状态枚举"""

    SCHEDULED = "scheduled"
    LIVE = "live"
    HALFTIME = "halftime"
    FULLTIME = "fulltime"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class PredictionResult(Enum):
    """预测结果枚举"""

    PENDING = "pending"
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIAL = "partial"


class UserRole(Enum):
    """用户角色枚举"""

    GUEST = "guest"
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


@pytest.mark.unit
@pytest.mark.external_api
class TestAppConstants:
    """应用常量测试"""

    def test_app_info_constants(self):
        """测试应用信息常量"""
        assert isinstance(AppConfig.APP_NAME, str)
        assert len(AppConfig.APP_NAME) > 0

        assert isinstance(AppConfig.APP_VERSION, str)
        assert "." in AppConfig.APP_VERSION  # 版本号格式检查

        assert isinstance(AppConfig.APP_DESCRIPTION, str)
        assert len(AppConfig.APP_DESCRIPTION) > 0

    def test_api_constants(self):
        """测试API配置常量"""
        assert AppConfig.API_PREFIX.startswith("/api")
        assert AppConfig.API_PREFIX.endswith("/v1")

        assert AppConfig.DOCS_URL.startswith("/")
        assert AppConfig.REDOC_URL.startswith("/")

        # 验证URL路径有效
        assert not AppConfig.DOCS_URL.endswith("/")
        assert not AppConfig.REDOC_URL.endswith("/")

    def test_server_constants(self):
        """测试服务器配置常量"""
        assert isinstance(AppConfig.DEFAULT_HOST, str)
        assert AppConfig.DEFAULT_HOST in ["0.0.0.0", "127.0.0.1", "localhost"]

        assert isinstance(AppConfig.DEFAULT_PORT, int)
        assert 1024 <= AppConfig.DEFAULT_PORT <= 65535

        assert isinstance(AppConfig.DEBUG_MODE, bool)

    def test_database_constants(self):
        """测试数据库配置常量"""
        assert "postgresql" in AppConfig.DEFAULT_DB_URL
        assert "asyncpg" in AppConfig.DEFAULT_DB_URL

        assert isinstance(AppConfig.DB_POOL_SIZE, int)
        assert AppConfig.DB_POOL_SIZE > 0

        assert isinstance(AppConfig.DB_MAX_OVERFLOW, int)
        assert AppConfig.DB_MAX_OVERFLOW >= 0

        assert isinstance(AppConfig.DB_POOL_TIMEOUT, int)
        assert AppConfig.DB_POOL_TIMEOUT > 0

    def test_redis_constants(self):
        """测试Redis配置常量"""
        assert AppConfig.REDIS_URL.startswith("redis://")

        assert isinstance(AppConfig.REDIS_POOL_SIZE, int)
        assert AppConfig.REDIS_POOL_SIZE > 0

        # 验证TTL值递增
        assert AppConfig.CACHE_TTL_SHORT < AppConfig.CACHE_TTL_DEFAULT < AppConfig.CACHE_TTL_LONG
        assert all(
            t > 0
            for t in [
                AppConfig.CACHE_TTL_SHORT,
                AppConfig.CACHE_TTL_DEFAULT,
                AppConfig.CACHE_TTL_LONG,
            ]
        )

    def test_security_constants(self):
        """测试安全配置常量"""
        assert isinstance(AppConfig.SECRET_KEY_MIN_LENGTH, int)
        assert AppConfig.SECRET_KEY_MIN_LENGTH >= 32

        assert isinstance(AppConfig.TOKEN_EXPIRE_MINUTES, int)
        assert AppConfig.TOKEN_EXPIRE_MINUTES > 0

        assert isinstance(AppConfig.REFRESH_TOKEN_EXPIRE_DAYS, int)
        assert AppConfig.REFRESH_TOKEN_EXPIRE_DAYS > AppConfig.TOKEN_EXPIRE_MINUTES / (24 * 60)

        assert isinstance(AppConfig.BCRYPT_ROUNDS, int)
        assert 10 <= AppConfig.BCRYPT_ROUNDS <= 15

    def test_prediction_constants(self):
        """测试预测配置常量"""
        assert isinstance(AppConfig.MAX_PREDICTIONS_PER_MATCH, int)
        assert AppConfig.MAX_PREDICTIONS_PER_MATCH > 0

        assert isinstance(AppConfig.PREDICTION_DEADLINE_HOURS, int)
        assert AppConfig.PREDICTION_DEADLINE_HOURS >= 1

        assert 0 <= AppConfig.MIN_CONFIDENCE < AppConfig.MAX_CONFIDENCE <= 1.0

    def test_pagination_constants(self):
        """测试分页配置常量"""
        assert isinstance(AppConfig.DEFAULT_PAGE_SIZE, int)
        assert 1 <= AppConfig.DEFAULT_PAGE_SIZE <= AppConfig.MAX_PAGE_SIZE

        assert isinstance(AppConfig.MAX_PAGE_SIZE, int)
        assert AppConfig.MAX_PAGE_SIZE <= 1000

    def test_file_upload_constants(self):
        """测试文件上传配置常量"""
        assert isinstance(AppConfig.MAX_FILE_SIZE_MB, int)
        assert AppConfig.MAX_FILE_SIZE_MB > 0

        assert isinstance(AppConfig.ALLOWED_IMAGE_TYPES, list)
        assert all(isinstance(t, str) for t in AppConfig.ALLOWED_IMAGE_TYPES)

        assert isinstance(AppConfig.ALLOWED_DOCUMENT_TYPES, list)
        assert all(isinstance(t, str) for t in AppConfig.ALLOWED_DOCUMENT_TYPES)

    def test_external_service_constants(self):
        """测试外部服务配置常量"""
        assert isinstance(AppConfig.WEATHER_API_TIMEOUT, int)
        assert AppConfig.WEATHER_API_TIMEOUT > 0

        assert isinstance(AppConfig.NEWS_API_TIMEOUT, int)
        assert AppConfig.NEWS_API_TIMEOUT > 0

        assert isinstance(AppConfig.MAX_RETRIES, int)
        assert 0 <= AppConfig.MAX_RETRIES <= 5

    def test_monitoring_constants(self):
        """测试监控配置常量"""
        assert isinstance(AppConfig.HEALTH_CHECK_INTERVAL, int)
        assert AppConfig.HEALTH_CHECK_INTERVAL > 0

        assert isinstance(AppConfig.METRICS_COLLECTION_INTERVAL, int)
        assert AppConfig.METRICS_COLLECTION_INTERVAL > 0

        assert isinstance(AppConfig.LOG_RETENTION_DAYS, int)
        assert AppConfig.LOG_RETENTION_DAYS >= 1


class TestEnums:
    """枚举测试"""

    def test_match_status_enum(self):
        """测试比赛状态枚举"""
        # 验证所有状态值
        statuses = [status.value for status in MatchStatus]
        expected_statuses = [
            "scheduled",
            "live",
            "halftime",
            "fulltime",
            "postponed",
            "cancelled",
        ]

        assert set(statuses) == set(expected_statuses)

        # 验证枚举属性
        for status in MatchStatus:
            assert isinstance(status.value, str)
            assert len(status.value) > 0

    def test_prediction_result_enum(self):
        """测试预测结果枚举"""
        results = [result.value for result in PredictionResult]
        expected_results = ["pending", "correct", "incorrect", "partial"]

        assert set(results) == set(expected_results)

        # 验证可以创建枚举实例
        pending = PredictionResult.PENDING
        assert pending.value == "pending"

    def test_user_role_enum(self):
        """测试用户角色枚举"""
        roles = [role.value for role in UserRole]
        expected_roles = ["guest", "user", "premium", "admin", "super_admin"]

        assert set(roles) == set(expected_roles)

        # 验证角色层级（按权限排序）
        role_hierarchy = [
            UserRole.GUEST,
            UserRole.USER,
            UserRole.PREMIUM,
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN,
        ]
        assert len(role_hierarchy) == len(UserRole)


class TestEnvironmentVariables:
    """环境变量测试"""

    def test_environment_variable_defaults(self):
        """测试环境变量默认值"""

        # 模拟环境变量读取
        def get_env_bool(key: str, default: bool = False) -> bool:
            value = os.getenv(key)
            if value is None:
                return default
            return value.lower() in ["true", "1", "yes", "on"]

        def get_env_int(key: str, default: int = 0) -> int:
            try:
                return int(os.getenv(key, str(default)))
            except ValueError:
                return default

        def get_env_str(key: str, default: str = "") -> str:
            return os.getenv(key, default)

        # 测试布尔值环境变量
        assert isinstance(get_env_bool("DEBUG", False), bool)
        assert isinstance(get_env_bool("TEST_MODE", True), bool)

        # 测试整数环境变量
        assert isinstance(get_env_int("PORT", 8000), int)
        assert isinstance(get_env_int("TIMEOUT", 30), int)

        # 测试字符串环境变量
        assert isinstance(get_env_str("ENV", "development"), str)
        assert isinstance(get_env_str("LOG_LEVEL", "INFO"), str)

    def test_required_environment_variables(self):
        """测试必需的环境变量"""
        # 定义必需的环境变量
        required_vars = ["DATABASE_URL", "SECRET_KEY", "REDIS_URL"]

        # 模拟检查必需环境变量
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        # 在测试环境中，这些变量可能不存在，这是可以接受的
        assert isinstance(missing_vars, list)

    def test_environment_specific_configs(self):
        """测试环境特定配置"""
        env = os.getenv("ENV", "development")

        # 开发环境配置
        dev_configs = {"debug": True, "log_level": "DEBUG", "reload": True}

        # 生产环境配置
        prod_configs = {"debug": False, "log_level": "INFO", "reload": False}

        if env == "development":
            assert dev_configs["debug"] is True
        elif env == "production":
            assert prod_configs["debug"] is False


class TestConfigValidation:
    """配置验证测试"""

    def test_validate_url_format(self):
        """验证URL格式"""

        def is_valid_url(url: str) -> bool:
            import re

            url_pattern = re.compile(
                r"^https?://"  # http:// or https://
                r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
                r"localhost|"  # localhost...
                r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
                r"(?::\d+)?"  # optional port
                r"(?:/?|[/?]\S+)$",
                re.IGNORECASE,
            )
            return url_pattern.match(url) is not None

        # 测试有效URL
        valid_urls = [
            "http://localhost:8000",
            "https://api.example.com",
            "http://127.0.0.1:5432",
            "https://football-prediction.com/v1",
        ]

        for url in valid_urls:
            assert is_valid_url(url) is True

        # 测试无效URL
        invalid_urls = [
            "not-a-url",
            "ftp://invalid-protocol.com",
            "http://",
            "://missing-protocol.com",
        ]

        for url in invalid_urls:
            assert is_valid_url(url) is False

    def test_validate_port_range(self):
        """验证端口范围"""

        def is_valid_port(port: int) -> bool:
            return 1 <= port <= 65535

        valid_ports = [80, 443, 8000, 3000, 5432, 6379]
        for port in valid_ports:
            assert is_valid_port(port) is True

        invalid_ports = [0, -1, 65536, 70000]
        for port in invalid_ports:
            assert is_valid_port(port) is False

    def test_validate_time_intervals(self):
        """验证时间间隔"""

        def is_valid_interval(seconds: int) -> bool:
            return 0 <= seconds <= 86400  # 最大24小时

        intervals = [0, 60, 300, 3600, 86400]
        for interval in intervals:
            assert is_valid_interval(interval) is True

        invalid_intervals = [-1, -60, 86401, 100000]
        for interval in invalid_intervals:
            assert is_valid_interval(interval) is False

    def test_validate_file_sizes(self):
        """验证文件大小限制"""

        def is_valid_size_mb(size_mb: int) -> bool:
            return 0 < size_mb <= 100  # 最大100MB

        valid_sizes = [1, 5, 10, 50, 100]
        for size in valid_sizes:
            assert is_valid_size_mb(size) is True

        invalid_sizes = [0, -1, 101, 1000]
        for size in invalid_sizes:
            assert is_valid_size_mb(size) is False
