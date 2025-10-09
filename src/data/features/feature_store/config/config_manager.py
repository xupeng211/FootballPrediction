"""
特征仓库配置管理模块
Feature Store Configuration Management Module
"""

from src.database.models.config import RepoConfig
from typing import Dict
from typing import Optional
from dataclasses import dataclass
from typing import Any, Dict, Optional
import os
from pathlib import Path


@dataclass
class FeatureStoreConfig:
    """特征仓库配置"""

    project_name: str = "football_prediction"
    repo_path: Optional[str] = None
    postgres_config: Optional[Dict[str, Any]] = None
    redis_config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化后处理"""
        # 设置默认仓库路径
        if self.repo_path is None:
            self.repo_path = str(Path.cwd() / "feature_repo")

        # 设置默认PostgreSQL配置
        if self.postgres_config is None:
            self.postgres_config = {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", 5432)),
                "database": os.getenv("DB_NAME", "football_prediction_dev"),
                "user": os.getenv("DB_READER_USER", "football_reader"),
                "password": os.getenv("DB_READER_PASSWORD", ""),
            }

        # 设置默认Redis配置
        if self.redis_config is None:
            self.redis_config = {
                "connection_string": os.getenv("REDIS_URL", "redis://localhost:6379/1")
            }


class FeatureStoreConfigManager:
    """特征仓库配置管理器"""

    def __init__(self, config: Optional[FeatureStoreConfig] = None):
        """
        初始化配置管理器

        Args:
            config: 特征仓库配置
        """
        self.config = config or FeatureStoreConfig()
        self.repo_path = Path(self.config.repo_path)
        self._temp_dir = None
        self._temp_dir_cleaned = False

    @property
    def is_temp_repo(self) -> bool:
        """是否为临时仓库"""
        return self._temp_dir is not None

    def create_temp_repo(self) -> Path:
        """创建临时仓库目录"""
        if self._temp_dir is None:
            import tempfile

            self._temp_dir = tempfile.TemporaryDirectory(prefix="feast_repo_")
            self._temp_dir_cleaned = False
            self.repo_path = Path(self._temp_dir.name)
            self.config.repo_path = str(self.repo_path)
        return self.repo_path

    def cleanup_temp_repo(self) -> None:
        """清理临时仓库"""
        if self._temp_dir and not self._temp_dir_cleaned:
            self._temp_dir.cleanup()
            self._temp_dir_cleaned = True

    def get_feast_config(self) -> "RepoConfig":
        """获取Feast配置对象"""
        try:
            from feast import RepoConfig
            from feast.infra.offline_stores.postgres import PostgreSQLOfflineStoreConfig
            from feast.infra.online_stores.redis import RedisOnlineStoreConfig
        except ImportError:
            raise ImportError("Feast 未安装，请安装 feast 以启用完整功能")

        # 确保仓库目录存在
        self.repo_path.mkdir(parents=True, exist_ok=True)

        return RepoConfig(
            registry=str(self.repo_path / "registry.db"),
            project=self.config.project_name,
            provider="local",
            offline_store=PostgreSQLOfflineStoreConfig(
                type="postgres",
                host=self.config.postgres_config["host"],
                port=self.config.postgres_config["port"],
                database=self.config.postgres_config["database"],
                user=self.config.postgres_config["user"],
                password=self.config.postgres_config["password"],
            ),
            online_store=RedisOnlineStoreConfig(
                type="redis",
                connection_string=self.config.redis_config["connection_string"],
            ),
            entity_key_serialization_version=2,
        )

    def save_feast_config(self) -> Path:
        """保存Feast配置到文件"""
        config = self.get_feast_config()
        config_path = self.repo_path / "feature_store.yaml"

        with open(config_path, "w") as f:
            f.write(config.to_yaml())

        return config_path
