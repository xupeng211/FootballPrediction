"""
生产环境密钥管理系统
"""

import os
import json
import logging
from typing import Dict, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class SecretProvider(ABC):
    """密钥提供者抽象基类"""

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """获取密钥"""
        pass

    @abstractmethod
    def set_secret(self, key: str, value: str) -> bool:
        """设置密钥"""
        pass

    @abstractmethod
    def delete_secret(self, key: str) -> bool:
        """删除密钥"""
        pass


class EnvironmentSecretProvider(SecretProvider):
    """环境变量密钥提供者"""

    def __init__(self, prefix: str = "FP_"):
        self.prefix = prefix

    def get_secret(self, key: str) -> Optional[str]:
        """从环境变量获取密钥"""
        env_key = f"{self.prefix}{key}"
        return os.getenv(env_key)

    def set_secret(self, key: str, value: str) -> bool:
        """设置环境变量密钥（仅在当前进程有效）"""
        env_key = f"{self.prefix}{key}"
        os.environ[env_key] = value
        return True

    def delete_secret(self, key: str) -> bool:
        """删除环境变量密钥"""
        env_key = f"{self.prefix}{key}"
        if env_key in os.environ:
            del os.environ[env_key]
            return True
        return False


class FileSecretProvider(SecretProvider):
    """文件密钥提供者（仅用于开发环境）"""

    def __init__(self, file_path: str = ".secrets.json"):
        self.file_path = file_path
        self._secrets = self._load_secrets()

    def _load_secrets(self) -> Dict[str, str]:
        """从文件加载密钥"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load secrets from {self.file_path}: {e}")
        return {}

    def _save_secrets(self) -> bool:
        """保存密钥到文件"""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self._secrets, f, indent=2)
            # 设置文件权限（仅所有者可读写）
            os.chmod(self.file_path, 0o600)
            return True
        except Exception as e:
            logger.error(f"Failed to save secrets to {self.file_path}: {e}")
            return False

    def get_secret(self, key: str) -> Optional[str]:
        """从文件获取密钥"""
        return self._secrets.get(key)

    def set_secret(self, key: str, value: str) -> bool:
        """设置密钥到文件"""
        self._secrets[key] = value
        return self._save_secrets()

    def delete_secret(self, key: str) -> bool:
        """从文件删除密钥"""
        if key in self._secrets:
            del self._secrets[key]
            return self._save_secrets()
        return False


class AWSSecretsManagerProvider(SecretProvider):
    """AWS Secrets Manager 密钥提供者"""

    def __init__(self, region_name: str = None, secret_name: str = None):
        try:
            import boto3
            from botocore.exceptions import ClientError
            self.client = boto3.client('secretsmanager', region_name=region_name)
            self.secret_name = secret_name or os.getenv('AWS_SECRET_NAME')
            self.ClientError = ClientError
        except ImportError:
            logger.error("boto3 not installed. Install with: pip install boto3")
            self.client = None

    def get_secret(self, key: str) -> Optional[str]:
        """从AWS Secrets Manager获取密钥"""
        if not self.client or not self.secret_name:
            return None

        try:
            response = self.client.get_secret_value(SecretId=self.secret_name)
            secrets = json.loads(response['SecretString'])
            return secrets.get(key)
        except self.ClientError as e:
            logger.error(f"Failed to get secret {key} from AWS Secrets Manager: {e}")
            return None

    def set_secret(self, key: str, value: str) -> bool:
        """设置密钥到AWS Secrets Manager"""
        # 实现略 - 需要更复杂的逻辑来更新整个secret
        logger.warning("AWSSecretsManagerProvider.set_secret not implemented")
        return False

    def delete_secret(self, key: str) -> bool:
        """从AWS Secrets Manager删除密钥"""
        # 实现略 - 需要更复杂的逻辑来更新整个secret
        logger.warning("AWSSecretsManagerProvider.delete_secret not implemented")
        return False


class SecretManager:
    """密钥管理器"""

    def __init__(self, provider: SecretProvider = None):
        if provider is None:
            # 根据环境自动选择提供者
            env = os.getenv('ENVIRONMENT', 'development').lower()
            if env == 'production':
                # 生产环境优先使用AWS Secrets Manager
                self.provider = AWSSecretsManagerProvider()
                if not hasattr(self.provider, 'client') or not self.provider.client:
                    logger.warning("AWS Secrets Manager not available, falling back to environment variables")
                    self.provider = EnvironmentSecretProvider()
            elif env == 'staging':
                # 测试环境使用环境变量
                self.provider = EnvironmentSecretProvider()
            else:
                # 开发环境使用文件（如果存在）
                if os.path.exists('.secrets.json'):
                    self.provider = FileSecretProvider()
                else:
                    self.provider = EnvironmentSecretProvider()
        else:
            self.provider = provider

        logger.info(f"Using secret provider: {self.provider.__class__.__name__}")

    def get_secret(self, key: str, default: str = None) -> Optional[str]:
        """获取密钥"""
        value = self.provider.get_secret(key)
        return value if value is not None else default

    def set_secret(self, key: str, value: str) -> bool:
        """设置密钥"""
        return self.provider.set_secret(key, value)

    def delete_secret(self, key: str) -> bool:
        """删除密钥"""
        return self.provider.delete_secret(key)

    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        return self.get_secret('DATABASE_URL', 'sqlite:///./data/football_prediction.db')

    def get_redis_url(self) -> str:
        """获取Redis连接URL"""
        return self.get_secret('REDIS_URL', 'redis://localhost:6379')

    def get_jwt_secret(self) -> str:
        """获取JWT密钥"""
        secret = self.get_secret('JWT_SECRET_KEY')
        if not secret:
            # 生成一个临时的密钥用于开发
            import secrets
            secret = secrets.token_urlsafe(32)
            logger.warning("Generated temporary JWT secret key. Set JWT_SECRET_KEY in production!")
        return secret

    def get_api_key(self, service: str) -> Optional[str]:
        """获取第三方服务API密钥"""
        return self.get_secret(f'{service.upper()}_API_KEY')

    def get_ssl_cert_path(self) -> Optional[str]:
        """获取SSL证书路径"""
        return self.get_secret('SSL_CERT_PATH')

    def get_ssl_key_path(self) -> Optional[str]:
        """获取SSL私钥路径"""
        return self.get_secret('SSL_KEY_PATH')


# 全局密钥管理器实例
_secret_manager: Optional[SecretManager] = None
def get_secret_manager() -> SecretManager:
    """获取全局密钥管理器实例"""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager


def init_secrets():
    """初始化必要的密钥"""
    manager = get_secret_manager()

    # 检查必要的密钥
    required_secrets = []
    env = os.getenv('ENVIRONMENT', 'development').lower()

    if env == 'production':
        required_secrets = [
            'DATABASE_URL',
            'REDIS_URL',
            'JWT_SECRET_KEY',
        ]

    missing_secrets = []
    for secret in required_secrets:
        if not manager.get_secret(secret):
            missing_secrets.append(secret)

    if missing_secrets:
        logger.error(f"Missing required secrets: {missing_secrets}")
        if env == 'production':
            raise RuntimeError(f"Missing required secrets: {missing_secrets}")
    else:
        logger.info("All required secrets are configured")
