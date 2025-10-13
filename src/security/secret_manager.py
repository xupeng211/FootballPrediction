"""
生产环境密钥管理模块
支持环境变量、AWS Secrets Manager、Azure Key Vault等
"""

import os
import json
import logging
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class SecretProvider(ABC):
    """密钥提供者抽象基类"""

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """获取密钥"""
        pass

    @abstractmethod
    def get_all_secrets(self) -> Dict[str, str]:
        """获取所有密钥"""
        pass


class EnvironmentSecretProvider(SecretProvider):
    """环境变量密钥提供者"""

    def get_secret(self, key: str) -> Optional[str]:
        """从环境变量获取密钥"""
        return os.getenv(key)

    def get_all_secrets(self) -> Dict[str, str]:
        """获取所有环境变量中的密钥"""
        return dict(os.environ)


class AWSSecretsManagerProvider(SecretProvider):
    """AWS Secrets Manager密钥提供者"""

    def __init__(
        self, region_name: str = "us-east-1", secret_name: Optional[str] = None
    ):
        try:
            import boto3
            from botocore.exceptions import ClientError

            self.client = boto3.client("secretsmanager", region_name=region_name)
            self.secret_name = secret_name or os.getenv("AWS_SECRET_NAME")
            self.ClientError = ClientError
        except ImportError:
            logger.error("boto3 not installed. Install with: pip install boto3")
            raise

    def get_secret(self, key: str) -> Optional[str]:
        """从AWS Secrets Manager获取密钥"""
        if not self.secret_name:
            logger.warning("AWS_SECRET_NAME not configured")
            return None

        try:
            response = self.client.get_secret_value(SecretId=self.secret_name)
            secrets = json.loads(response["SecretString"])
            return secrets.get(key)
        except self.ClientError as e:
            logger.error(f"Failed to get secret from AWS: {e}")
            return None

    def get_all_secrets(self) -> Dict[str, str]:
        """从AWS Secrets Manager获取所有密钥"""
        if not self.secret_name:
            logger.warning("AWS_SECRET_NAME not configured")
            return {}

        try:
            response = self.client.get_secret_value(SecretId=self.secret_name)
            return json.loads(response["SecretString"])
        except self.ClientError as e:
            logger.error(f"Failed to get secrets from AWS: {e}")
            return {}


class AzureKeyVaultProvider(SecretProvider):
    """Azure Key Vault密钥提供者"""

    def __init__(self, vault_url: Optional[str] = None):
        try:
            from azure.keyvault.secrets import SecretClient
            from azure.identity import DefaultAzureCredential

            self.vault_url = vault_url or os.getenv("AZURE_VAULT_URL")
            if not self.vault_url:
                raise ValueError("AZURE_VAULT_URL not configured")

            credential = DefaultAzureCredential()
            self.client = SecretClient(vault_url=self.vault_url, credential=credential)
        except ImportError:
            logger.error(
                "Azure SDK not installed. Install with: pip install azure-keyvault-secrets azure-identity"
            )
            raise

    def get_secret(self, key: str) -> Optional[str]:
        """从Azure Key Vault获取密钥"""
        try:
            secret = self.client.get_secret(key)
            return secret.value
        except Exception as e:
            logger.error(f"Failed to get secret from Azure Key Vault: {e}")
            return None

    def get_all_secrets(self) -> Dict[str, str]:
        """从Azure Key Vault获取所有密钥（需要列出所有密钥）"""
        secrets = {}
        try:
            secret_properties = self.client.list_properties_of_secrets()
            for secret_prop in secret_properties:
                if secret_prop.enabled:
                    secret = self.client.get_secret(secret_prop.name)
                    secrets[secret_prop.name] = secret.value
        except Exception as e:
            logger.error(f"Failed to list secrets from Azure Key Vault: {e}")
        return secrets


class HashiCorpVaultProvider(SecretProvider):
    """HashiCorp Vault密钥提供者"""

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        secret_path: str = "secret",
    ):
        try:
            import hvac

            self.url = url or os.getenv("VAULT_URL", "https://vault.example.com")
            self.token = token or os.getenv("VAULT_TOKEN")
            self.secret_path = secret_path

            if not self.token:
                raise ValueError("VAULT_TOKEN not configured")

            self.client = hvac.Client(url=self.url, token=self.token)
        except ImportError:
            logger.error("hvac not installed. Install with: pip install hvac")
            raise

    def get_secret(self, key: str) -> Optional[str]:
        """从HashiCorp Vault获取密钥"""
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=f"{self.secret_path}/{key}"
            )
            return response["data"]["data"].get(key)
        except Exception as e:
            logger.error(f"Failed to get secret from Vault: {e}")
            return None

    def get_all_secrets(self) -> Dict[str, str]:
        """从HashiCorp Vault获取所有密钥"""
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=self.secret_path
            )
            return response["data"]["data"]
        except Exception as e:
            logger.error(f"Failed to get secrets from Vault: {e}")
            return {}


class SecretManager:
    """密钥管理器"""

    def __init__(self, provider: Optional[SecretProvider] = None):
        """初始化密钥管理器"""
        if provider is None:
            # 根据环境自动选择提供者
            self.provider = self._get_default_provider()
        else:
            self.provider = provider

    def _get_default_provider(self) -> SecretProvider:
        """根据环境获取默认的密钥提供者"""
        env = os.getenv("ENVIRONMENT", "development").lower()

        # 生产环境优先使用云密钥管理服务
        if env == "production":
            # 检查AWS配置
            if os.getenv("AWS_SECRET_NAME") or os.getenv("AWS_ACCESS_KEY_ID"):
                try:
                    return AWSSecretsManagerProvider()
                except Exception:
                    logger.warning(
                        "Failed to initialize AWS Secrets Manager, falling back to environment variables"
                    )

            # 检查Azure配置
            if os.getenv("AZURE_VAULT_URL"):
                try:
                    return AzureKeyVaultProvider()
                except Exception:
                    logger.warning(
                        "Failed to initialize Azure Key Vault, falling back to environment variables"
                    )

            # 检查Vault配置
            if os.getenv("VAULT_TOKEN"):
                try:
                    return HashiCorpVaultProvider()
                except Exception:
                    logger.warning(
                        "Failed to initialize HashiCorp Vault, falling back to environment variables"
                    )

        # 默认使用环境变量
        return EnvironmentSecretProvider()

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取密钥"""
        value = self.provider.get_secret(key)
        if value is None:
            value = default
            if value is None:
                logger.warning(f"Secret not found: {key}")
        return value

    def get_required_secret(self, key: str) -> str:
        """获取必需的密钥，如果不存在则抛出异常"""
        value = self.get_secret(key)
        if value is None:
            raise ValueError(f"Required secret not found: {key}")
        return value

    def get_all_secrets(self) -> Dict[str, str]:
        """获取所有密钥"""
        return self.provider.get_all_secrets()

    def verify_required_secrets(self, required_keys: list) -> Dict[str, bool]:
        """验证必需的密钥是否存在"""
        results = {}
        for key in required_keys:
            try:
                self.get_required_secret(key)
                results[key] = True
            except ValueError:
                results[key] = False
        return results


# 全局密钥管理器实例
_secret_manager: Optional[SecretManager] = None


def get_secret_manager() -> SecretManager:
    """获取全局密钥管理器实例"""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """便捷函数：获取密钥"""
    return get_secret_manager().get_secret(key, default)


def get_required_secret(key: str) -> str:
    """便捷函数：获取必需的密钥"""
    return get_secret_manager().get_required_secret(key)
