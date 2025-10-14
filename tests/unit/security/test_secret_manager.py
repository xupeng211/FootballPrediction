"""
密钥管理模块测试
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.security.secret_manager import (
    SecretManager,
    EnvironmentSecretProvider,
    FileSecretProvider,
    AWSSecretsManagerProvider,
    get_secret_manager,
    init_secrets,
)


class TestEnvironmentSecretProvider:
    """环境变量密钥提供者测试"""

    def setup_method(self):
        """设置测试环境"""
        self.provider = EnvironmentSecretProvider(prefix="TEST_")
        # 清理环境变量
        for key in list(os.environ.keys()):
            if key.startswith("TEST_"):
                del os.environ[key]

    def test_get_secret_exists(self):
        """测试获取存在的密钥"""
        os.environ["TEST_DATABASE_URL"] = "postgresql://localhost/test"
        assert self.provider.get_secret("DATABASE_URL") == "postgresql://localhost/test"

    def test_get_secret_not_exists(self):
        """测试获取不存在的密钥"""
        assert self.provider.get_secret("NON_EXISTENT") is None

    def test_get_secret_with_default(self):
        """测试获取密钥带默认值"""
        assert self.provider.get_secret("NON_EXISTENT", "default") == "default"

    def test_set_secret(self):
        """测试设置密钥"""
        self.provider.set_secret("TEST_KEY", "test_value")
        assert os.environ["TEST_KEY"] == "test_value"

    def test_delete_secret(self):
        """测试删除密钥"""
        os.environ["TEST_KEY"] = "test_value"
        assert self.provider.delete_secret("TEST_KEY") is True
        assert "TEST_KEY" not in os.environ

    def test_delete_secret_not_exists(self):
        """测试删除不存在的密钥"""
        assert self.provider.delete_secret("NON_EXISTENT") is False


class TestFileSecretProvider:
    """文件密钥提供者测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.file_path = os.path.join(self.temp_dir, "test_secrets.json")
        self.provider = FileSecretProvider(self.file_path)

    def test_save_and_load_secrets(self):
        """测试保存和加载密钥"""
        # 设置密钥
        self.provider.set_secret("key1", "value1")
        self.provider.set_secret("key2", "value2")

        # 验证文件权限
        file_stat = os.stat(self.file_path)
        assert file_stat.st_mode & 0o600 == 0o600

        # 创建新的提供者实例读取
        new_provider = FileSecretProvider(self.file_path)
        assert new_provider.get_secret("key1") == "value1"
        assert new_provider.get_secret("key2") == "value2"

    def test_load_existing_file(self):
        """测试加载已存在的密钥文件"""
        # 创建密钥文件
        secrets = {"key1": "value1", "key2": "value2"}
        with open(self.file_path, "w") as f:
            json.dump(secrets, f)
        os.chmod(self.file_path, 0o600)

        # 加载
        provider = FileSecretProvider(self.file_path)
        assert provider.get_secret("key1") == "value1"
        assert provider.get_secret("key2") == "value2"

    def test_delete_secret(self):
        """测试删除密钥"""
        self.provider.set_secret("key1", "value1")
        assert self.provider.delete_secret("key1") is True
        assert self.provider.get_secret("key1") is None

    def teardown_method(self):
        """清理测试环境"""
        import shutil

        shutil.rmtree(self.temp_dir)


class TestAWSSecretsManagerProvider:
    """AWS Secrets Manager 密钥提供者测试"""

    def setup_method(self):
        """设置测试环境"""
        # 模拟boto3不可用
        self.boto3_patcher = patch("src.security.secret_manager.boto3", None)
        self.boto3_patcher.start()

    def test_boto3_not_installed(self):
        """测试boto3未安装的情况"""
        provider = AWSSecretsManagerProvider()
        assert provider.client is None

    def teardown_method(self):
        """清理测试环境"""
        self.boto3_patcher.stop()


class TestSecretManager:
    """密钥管理器测试"""

    def test_init_with_provider(self):
        """测试使用自定义提供者初始化"""
        mock_provider = MagicMock()
        manager = SecretManager(provider=mock_provider)
        assert manager.provider is mock_provider

    @patch.dict(os.environ, {"ENVIRONMENT": "development"})
    def test_init_development_with_file(self):
        """测试开发环境使用文件提供者"""
        # 创建临时密钥文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name
            json.dump({"TEST_KEY": "test_value"}, f)

        try:
            # 临时切换到文件所在目录
            old_cwd = os.getcwd()
            os.chdir(os.path.dirname(temp_file))

            # 创建管理器
            manager = SecretManager()

            # 应该使用文件提供者（因为.secrets.json存在）
            assert isinstance(manager.provider, FileSecretProvider)
        finally:
            os.chdir(old_cwd)
            os.unlink(temp_file)

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_init_production_without_aws(self):
        """测试生产环境无AWS时回退到环境变量"""
        # 模拟boto3不可用
        with patch("src.security.secret_manager.AWSSecretsManagerProvider") as MockAWS:
            mock_aws = MockAWS.return_value
            mock_aws.client = None  # 模拟AWS不可用

            manager = SecretManager()

            # 应该使用环境变量提供者
            assert isinstance(manager.provider, EnvironmentSecretProvider)

    def test_get_secret(self):
        """测试获取密钥"""
        mock_provider = MagicMock()
        mock_provider.get_secret.return_value = "test_value"
        manager = SecretManager(provider=mock_provider)

        assert manager.get_secret("TEST_KEY") == "test_value"
        mock_provider.get_secret.assert_called_once_with("TEST_KEY")

    def test_get_secret_with_default(self):
        """测试获取密钥带默认值"""
        mock_provider = MagicMock()
        mock_provider.get_secret.return_value = None
        manager = SecretManager(provider=mock_provider)

        assert manager.get_secret("NON_EXISTENT", "default") == "default"
        mock_provider.get_secret.assert_called_once_with("NON_EXISTENT")

    def test_set_secret(self):
        """测试设置密钥"""
        mock_provider = MagicMock()
        mock_provider.set_secret.return_value = True
        manager = SecretManager(provider=mock_provider)

        assert manager.set_secret("TEST_KEY", "test_value") is True
        mock_provider.set_secret.assert_called_once_with("TEST_KEY", "test_value")

    def test_get_database_url(self):
        """测试获取数据库URL"""
        mock_provider = MagicMock()
        mock_provider.get_secret.return_value = "postgresql://localhost/db"
        manager = SecretManager(provider=mock_provider)

        assert manager.get_database_url() == "postgresql://localhost/db"
        mock_provider.get_secret.assert_called_once_with(
            "DATABASE_URL", "sqlite:///./data/football_prediction.db"
        )

    def test_get_redis_url(self):
        """测试获取Redis URL"""
        mock_provider = MagicMock()
        mock_provider.get_secret.return_value = "redis://localhost:6379"
        manager = SecretManager(provider=mock_provider)

        assert manager.get_redis_url() == "redis://localhost:6379"
        mock_provider.get_secret.assert_called_once_with(
            "REDIS_URL", "redis://localhost:6379"
        )

    def test_get_jwt_secret_provided(self):
        """测试获取已提供的JWT密钥"""
        mock_provider = MagicMock()
        mock_provider.get_secret.return_value = "existing-secret-key"
        manager = SecretManager(provider=mock_provider)

        assert manager.get_jwt_secret() == "existing-secret-key"
        mock_provider.get_secret.assert_called_once_with("JWT_SECRET_KEY")

    @patch("src.security.secret_manager.secrets")
    def test_get_jwt_secret_generate(self, mock_secrets):
        """测试生成JWT密钥"""
        mock_provider = MagicMock()
        mock_provider.get_secret.return_value = None  # 没有现有密钥
        manager = SecretManager(provider=mock_provider)

        # 生成临时密钥
        secret = manager.get_jwt_secret()
        assert secret is not None
        assert len(secret) == 43  # token_urlsafe(32) 生成长度

    def test_get_api_key(self):
        """测试获取API密钥"""
        mock_provider = MagicMock()
        mock_provider.get_secret.return_value = "api-key-123"
        manager = SecretManager(provider=mock_provider)

        assert manager.get_api_key("football") == "api-key-123"
        mock_provider.get_secret.assert_called_once_with("FOOTBALL_API_KEY")

    def test_get_ssl_paths(self):
        """测试获取SSL证书路径"""
        mock_provider = MagicMock()
        manager = SecretManager(provider=mock_provider)

        # 设置SSL路径
        mock_provider.get_secret.side_effect = ["/path/to/cert.crt", "/path/to/key.pem"]

        assert manager.get_ssl_cert_path() == "/path/to/cert.crt"
        assert manager.get_ssl_key_path() == "/path/to/key.pem"


class TestSecretManagerIntegration:
    """密钥管理器集成测试"""

    def test_get_secret_manager_singleton(self):
        """测试密钥管理器单例"""
        manager1 = get_secret_manager()
        manager2 = get_secret_manager()
        assert manager1 is manager2

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "FP_DATABASE_URL": "postgresql://prod:5432/db",
            "FP_REDIS_URL": "redis://prod:6379/0",
            "FP_JWT_SECRET_KEY": "production-secret-key-32-chars",
        },
    )
    def test_init_secrets_production_success(self):
        """测试生产环境密钥初始化成功"""
        # 重置全局实例
        import src.security.secret_manager

        src.security.secret_manager._secret_manager = None

        # 初始化密钥
        init_secrets()  # 应该不抛出异常

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_init_secrets_production_missing(self):
        """测试生产环境缺少必需密钥"""
        # 重置全局实例
        import src.security.secret_manager

        src.security.secret_manager._secret_manager = None

        # 移除必需的环境变量
        if "FP_DATABASE_URL" in os.environ:
            del os.environ["FP_DATABASE_URL"]
        if "FP_REDIS_URL" in os.environ:
            del os.environ["FP_REDIS_URL"]
        if "FP_JWT_SECRET_KEY" in os.environ:
            del os.environ["FP_JWT_SECRET_KEY"]

        # 应该抛出异常
        with pytest.raises(RuntimeError, match="Missing required secrets"):
            init_secrets()

    @patch.dict(os.environ, {"ENVIRONMENT": "development"})
    def test_init_secrets_development(self):
        """测试开发环境密钥初始化"""
        # 重置全局实例
        import src.security.secret_manager

        src.security.secret_manager._secret_manager = None

        # 开发环境不需要必需密钥
        init_secrets()  # 应该不抛出异常


if __name__ == "__main__":
    pytest.main([__file__])
