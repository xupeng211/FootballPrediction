"""src.config 包稳定覆盖率测试。"""

from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path
import sys
import types

from pydantic import SecretStr

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def _seed_namespace_package(name: str, package_path: Path) -> None:
    """为 CI 提供轻量命名空间包，避免导入根包副作用。"""
    if name in sys.modules:
        return

    module = types.ModuleType(name)
    module.__path__ = [str(package_path)]  # type: ignore[attr-defined]
    sys.modules[name] = module


def _load_package_module(name: str, init_path: Path, package_path: Path):
    """按文件路径加载包入口，绕过 src/__init__.py 的全量导入。"""
    spec = importlib.util.spec_from_file_location(
        name,
        init_path,
        submodule_search_locations=[str(package_path)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载包模块: {name}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_seed_namespace_package("src", SRC_ROOT)
_seed_namespace_package("src.core", SRC_ROOT / "core")
config_package = _load_package_module(
    "src.config", SRC_ROOT / "config" / "__init__.py", SRC_ROOT / "config"
)

common = importlib.import_module("src.config.common")
config_loader = importlib.import_module("src.config.config_loader")
db_settings = importlib.import_module("src.config.db_settings")
proxy_settings = importlib.import_module("src.config.proxy_settings")
settings_module = importlib.import_module("src.config.settings")

ConfigAccessor = config_package.ConfigAccessor
ProxyConfig = config_package.ProxyConfig
get_config = config_package.get_config
get_database_url = config_package.get_database_url
get_redis_url = config_package.get_redis_url
get_settings = config_package.get_settings
get_shared_proxy_pool_config = config_package.get_shared_proxy_pool_config
reload_settings = config_package.reload_settings

VALID_INT_VALUE = 12
MISSING_INT_DEFAULT = 9
INVALID_INT_DEFAULT = 7
TEMPLATE_PORT = 8123
BUSY_WEEK_THRESHOLD = 5
CORE_PLAYER_THRESHOLD = 0.8
EXCELLENT_CONFIDENCE_MIN = 97
MIN_PAYOUT = 1.03
DEFAULT_MIN_PAYOUT = 1.02


def test_common_env_helpers(monkeypatch):
    """环境变量工具函数应稳定处理真假值与非法整数。"""
    monkeypatch.setenv("FLAG_TRUE", "YeS")
    monkeypatch.setenv("FLAG_FALSE", "off")
    monkeypatch.setenv("VALID_INT", "12")
    monkeypatch.setenv("INVALID_INT", "oops")

    assert common.env_flag("FLAG_TRUE") is True
    assert common.env_flag("FLAG_FALSE") is False
    assert common.env_int("VALID_INT", 3) == VALID_INT_VALUE
    assert common.env_int("MISSING_INT", MISSING_INT_DEFAULT) == MISSING_INT_DEFAULT
    assert common.env_int("INVALID_INT", INVALID_INT_DEFAULT) == INVALID_INT_DEFAULT


def test_proxy_pool_resolution_prefers_environment(monkeypatch, tmp_path):
    """共享代理配置应优先读取环境变量并可构建代理 URL。"""
    pool_file = tmp_path / "proxy_pool.json"
    pool_file.write_text(
        json.dumps(
            {
                "host": "172.25.16.1",
                "protocol": "http",
                "ports": [7890, 7891],
                "defaultPort": 7890,
                "serverTemplate": "http://172.25.16.1:{port}",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(proxy_settings, "PROXY_POOL_CONFIG_PATH", pool_file)
    monkeypatch.setenv("PROXY_HOST", "proxy.local")
    monkeypatch.setenv("PROXY_PORTS", "8100,8101")
    monkeypatch.setenv("PROXY_PROTOCOL", "https")
    monkeypatch.delenv("PROXY_SERVER", raising=False)

    resolved = proxy_settings.resolve_shared_proxy_pool_config()
    assert resolved["host"] == "proxy.local"
    assert resolved["ports"] == [8100, 8101]
    assert resolved["protocol"] == "https"
    assert resolved["server_template"] == "https://proxy.local:{port}"

    snapshot = get_shared_proxy_pool_config()
    assert snapshot["host"] == "proxy.local"

    proxy = ProxyConfig(proxy_ports=[8100, 8101], deprecated_proxy_ports=[8101])
    assert proxy.get_proxy_url(8100) == "https://proxy.local:8100"
    assert proxy.get_all_proxy_urls() == [
        "https://proxy.local:8100",
        "https://proxy.local:8101",
    ]
    assert proxy.validate_port(8100) is True
    assert proxy.validate_port(8101) is False


def test_proxy_pool_resolution_supports_server_template(monkeypatch, tmp_path):
    """serverTemplate 应能反推出主机与默认端口且不污染端口池。"""
    pool_file = tmp_path / "proxy_pool.json"
    pool_file.write_text(
        json.dumps(
            {
                "host": "legacy.local",
                "protocol": "http",
                "ports": [9000],
                "defaultPort": 9000,
                "serverTemplate": "http://legacy.local:{port}",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(proxy_settings, "PROXY_POOL_CONFIG_PATH", pool_file)
    monkeypatch.delenv("PROXY_HOST", raising=False)
    monkeypatch.setenv("PROXY_SERVER", "https://template.local:{port}")
    monkeypatch.delenv("PROXY_PORTS", raising=False)
    monkeypatch.delenv("PROXY_PORT_START", raising=False)
    monkeypatch.delenv("PROXY_PORT_END", raising=False)
    monkeypatch.setenv("PROXY_PORT", str(TEMPLATE_PORT))

    resolved = proxy_settings.resolve_shared_proxy_pool_config()
    assert resolved["host"] == "template.local"
    assert resolved["default_port"] == TEMPLATE_PORT
    assert resolved["ports"] == [9000]
    assert TEMPLATE_PORT not in resolved["ports"]


def test_config_loader_reads_files_and_defaults(tmp_path):
    """Legacy 配置加载器应能读取配置文件并在缺失时回退默认值。"""
    aliases_path = tmp_path / "team_aliases.json"
    aliases_path.write_text(
        json.dumps(
            {
                "team_name_mappings": {"Man Utd": "Manchester United"},
                "suffixes_to_strip": [" FC"],
                "prefixes_to_strip": ["The "],
                "youth_keywords": {"u19": ["u19"]},
                "youth_patterns": ["U19"],
                "common_suffixes": {"city": ["City"]},
            }
        ),
        encoding="utf-8",
    )
    alias_config = config_loader.TeamAliasesConfig.from_json(aliases_path)
    assert alias_config.team_name_mappings["Man Utd"] == "Manchester United"
    assert alias_config.suffixes_to_strip == [" FC"]

    hyper_path = tmp_path / "hyper_parameters.yaml"
    hyper_path.write_text(
        """
fatigue:
  busy_week_threshold: 5
feature_extraction:
  core_player_threshold: 0.8
  feature_richness:
    excellent_threshold: 120
similarity:
  team_match_threshold: 90.0
  bridge_confidence:
    excellent_min: 97
odds_integrity:
  min_payout: 1.03
""".strip(),
        encoding="utf-8",
    )
    hyper_config = config_loader.HyperParametersConfig.from_yaml(hyper_path)
    assert hyper_config.busy_week_threshold == BUSY_WEEK_THRESHOLD
    assert hyper_config.core_player_threshold == CORE_PLAYER_THRESHOLD
    assert hyper_config.excellent_confidence_min == EXCELLENT_CONFIDENCE_MIN
    assert hyper_config.min_payout == MIN_PAYOUT

    assert (
        config_loader.TeamAliasesConfig.from_json(tmp_path / "missing.json").team_name_mappings
        == {}
    )
    assert (
        config_loader.HyperParametersConfig.from_yaml(tmp_path / "missing.yaml").min_payout
        == DEFAULT_MIN_PAYOUT
    )


def test_database_and_redis_config_urls():
    """数据库与 Redis 连接串应正确生成。"""
    database = db_settings.DatabaseConfig(
        host="db",
        port=5432,
        name="football_db",
        user="football_user",
        password=SecretStr("secret-pass"),
        ssl_mode=True,
    )
    assert database.get_connection_string().endswith("?sslmode=require")
    assert database.get_async_url().startswith("postgresql+asyncpg://")

    redis_config = db_settings.RedisConfig(
        host="redis",
        port=6379,
        password=SecretStr("redis-pass"),
    )
    assert redis_config.get_connection_string() == "redis://:redis-pass@redis:6379/0"


def test_database_settings_auto_inject_env_branches(monkeypatch):
    """数据库自动注入逻辑应覆盖 Docker、WSL2 和本地分支。"""
    monkeypatch.setattr(db_settings, "load_dotenv_if_available", lambda: None)
    fake_env_type = type(
        "FakeEnvironmentType",
        (),
        {"DOCKER": "docker", "WSL2": "wsl2", "LOCAL": "local"},
    )
    monkeypatch.setattr(db_settings, "EnvironmentType", fake_env_type)
    monkeypatch.setattr(
        db_settings,
        "get_optimal_db_host",
        lambda current, fallback: current or fallback or "auto-db",
    )
    monkeypatch.setenv("DB_PASSWORD", "docker-secret")
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("REDIS_HOST", raising=False)

    monkeypatch.setattr(db_settings, "detect_environment", lambda: fake_env_type.DOCKER)
    docker_env = db_settings.DatabaseSettingsMixin.auto_inject_env_vars()
    assert docker_env["db_host"] == "db"
    assert docker_env["redis_host"] == "redis"

    monkeypatch.setattr(db_settings, "detect_environment", lambda: fake_env_type.WSL2)
    monkeypatch.setenv("DB_HOST", "wsl-db")
    wsl_env = db_settings.DatabaseSettingsMixin.auto_inject_env_vars()
    assert wsl_env["db_host"] == "wsl-db"
    assert wsl_env["environment"] == "development"

    monkeypatch.setattr(db_settings, "detect_environment", lambda: fake_env_type.LOCAL)
    local_env = db_settings.DatabaseSettingsMixin.auto_inject_env_vars()
    assert local_env["db_host"] == "wsl-db"


def test_unified_settings_urls_and_accessors(monkeypatch, tmp_path):
    """统一配置入口应暴露数据库、Redis 和代理视图。"""
    pool_file = tmp_path / "proxy_pool.json"
    pool_file.write_text(
        json.dumps(
            {
                "host": "172.25.16.1",
                "protocol": "http",
                "ports": [7890, 7891],
                "defaultPort": 7890,
                "serverTemplate": "http://172.25.16.1:{port}",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(proxy_settings, "PROXY_POOL_CONFIG_PATH", pool_file)
    monkeypatch.setattr(settings_module, "_validate_database_environment", lambda _: None)
    monkeypatch.setenv("SKIP_ENV_VALIDATION", "1")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("DB_PASSWORD", "db-password")
    monkeypatch.setenv("DB_NAME", "football_db")
    monkeypatch.setenv("DB_HOST", "db")
    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.delenv("PROXY_HOST", raising=False)
    monkeypatch.delenv("PROXY_SERVER", raising=False)
    monkeypatch.delenv("PROXY_PROTOCOL", raising=False)
    monkeypatch.delenv("PROXY_PORTS", raising=False)
    monkeypatch.delenv("PROXY_PORT", raising=False)

    settings = reload_settings()
    accessor = get_config()

    assert settings.database.host == accessor.database.host
    assert get_settings().database.name == "football_db"
    assert get_database_url().startswith("postgresql://")
    assert get_redis_url().startswith("redis://")
    assert accessor.proxy.get_proxy_url(7890) == "http://172.25.16.1:7890"
    assert ConfigAccessor().proxy.get_proxy_url(7891) == "http://172.25.16.1:7891"
    accessor.reload()
    assert accessor.database.name == "football_db"


def test_proxy_pool_default_host_prefers_loopback_gateway(monkeypatch, tmp_path):
    """未显式指定 PROXY_HOST 时，应优先回退到 127.0.0.1。"""
    pool_file = tmp_path / "proxy_pool.json"
    pool_file.write_text(
        json.dumps(
            {
                "host": "172.25.16.1",
                "protocol": "http",
                "ports": [7891, 7892],
                "defaultPort": 7891,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(proxy_settings, "PROXY_POOL_CONFIG_PATH", pool_file)
    monkeypatch.delenv("WSL2_PROXY_HOST", raising=False)
    monkeypatch.delenv("PROXY_HOST", raising=False)
    monkeypatch.delenv("PROXY_SERVER", raising=False)
    monkeypatch.delenv("PROXY_PROTOCOL", raising=False)
    monkeypatch.delenv("PROXY_PORTS", raising=False)
    monkeypatch.delenv("PROXY_PORT", raising=False)

    resolved = proxy_settings.resolve_shared_proxy_pool_config()
    assert resolved["host"] == "127.0.0.1"
    assert resolved["server_template"] == "http://127.0.0.1:{port}"
