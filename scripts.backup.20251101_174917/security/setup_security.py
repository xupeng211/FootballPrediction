#!/usr/bin/env python3
"""
安全配置自动化脚本
生成和管理所有必需的安全密钥
"""

import secrets
import json
import hashlib
import math
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet


class SecurityManager:
    """安全管理器"""

    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.keys = {}
        self.policies = {}
        self._init()

    def _init(self):
        """初始化安全管理器"""
        self.security_dir = Path("security")
        self.keys_dir = self.security_dir / "keys"
        self.policies_dir = self.security_dir / "policies"

        # 创建目录
        self.security_dir.mkdir(exist_ok=True)
        self.keys_dir.mkdir(exist_ok=True)
        self.policies_dir.mkdir(exist_ok=True)

    def generate_secure_keys(self) -> Dict[str, str]:
        """生成所有必需的安全密钥"""
        print(f"🔐 生成环境 '{self.environment}' 的安全密钥...")

        keys = {
            # 应用密钥
            "SECRET_KEY": secrets.token_urlsafe(64),
            "JWT_SECRET_KEY": secrets.token_urlsafe(64),
            "JWT_REFRESH_SECRET_KEY": secrets.token_urlsafe(64),
            # API密钥
            "API_KEY": secrets.token_urlsafe(48),
            "API_SECRET_KEY": secrets.token_urlsafe(64),
            # 数据库加密
            "DB_ENCRYPTION_KEY": secrets.token_bytes(32).hex(),
            "DB_SALT": secrets.token_hex(16),
            # Redis
            "REDIS_PASSWORD": secrets.token_urlsafe(32),
            # MLflow
            "MLFLOW_TRACKING_PASSWORD": secrets.token_urlsafe(32),
            "MLFLOW_ARTIFACT_KEY": secrets.token_bytes(32).hex(),
            # 外部服务
            "EXTERNAL_API_KEY": secrets.token_urlsafe(48),
            "WEBHOOK_SECRET": secrets.token_urlsafe(64),
            # 加密相关
            "ENCRYPTION_KEY": Fernet.generate_key().decode(),
            "HASH_SALT": secrets.token_hex(32),
            # 会话安全
            "SESSION_SECRET": secrets.token_urlsafe(64),
            "CSRF_SECRET": secrets.token_urlsafe(64),
        }

        # 验证密钥强度
        self._validate_keys(keys)

        return keys

    def _validate_keys(self, keys: Dict[str, str]):
        """验证密钥强度"""
        print("\n🔍 验证密钥强度...")

        for key_name, key_value in keys.items():
            # 基本验证
            if len(key_value) < 32:
                raise ValueError(f"密钥 {key_name} 长度不足")

            # 熵值检查（跳过十六进制字符串）
            entropy = "N/A"
            if not all(c in "0123456789abcdefABCDEF" for c in key_value):
                entropy = self._calculate_entropy(key_value)
                if entropy < 3.5:  # 最小熵值要求
                    raise ValueError(f"密钥 {key_name} 熵值过低: {entropy:.2f}")

            print(f"  ✅ {key_name}: OK (熵值: {entropy})")

    def _calculate_entropy(self, s: str) -> float:
        """计算字符串的熵值"""
        if not s:
            return 0

        # 计算字符频率
        prob = [float(s.count(c)) / len(s) for c in dict.fromkeys(s)]

        # 计算熵值
        entropy = -sum(p * (p and math.log(p) / math.log(2.0)) for p in prob)

        return entropy

    def generate_env_file(self, keys: Dict[str, str], output_path: Optional[str] = None):
        """生成环境配置文件"""
        print(f"\n📝 生成 .env.{self.environment} 文件...")

        env_content = f"""# === 生产环境安全配置 ===
# 自动生成时间: {datetime.now().isoformat()}
# ⚠️  此文件包含敏感信息，请妥善保管！

# === 应用基础配置 ===
ENVIRONMENT={self.environment}
DEBUG=False
LOG_LEVEL=INFO
SECRET_KEY={keys['SECRET_KEY']}

# === JWT配置 ===
JWT_SECRET_KEY={keys['JWT_SECRET_KEY']}
JWT_REFRESH_SECRET_KEY={keys['JWT_REFRESH_SECRET_KEY']}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# === API安全 ===
API_KEY={keys['API_KEY']}
API_SECRET_KEY={keys['API_SECRET_KEY']}
CORS_ORIGINS=["https://api.footballprediction.com"]

# === 数据库安全配置 ===
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/football_prediction_prod
DB_ENCRYPTION_KEY={keys['DB_ENCRYPTION_KEY']}
DB_SALT={keys['DB_SALT']}

# === Redis安全 ===
REDIS_URL=redis://:{keys['REDIS_PASSWORD']}@localhost:6379/0
REDIS_PASSWORD={keys['REDIS_PASSWORD']}

# === MLflow安全 ===
MLFLOW_TRACKING_URI=https://mlflow.footballprediction.com
MLFLOW_TRACKING_USERNAME=admin
MLFLOW_TRACKING_PASSWORD={keys['MLFLOW_TRACKING_PASSWORD']}
MLFLOW_ARTIFACT_KEY={keys['MLFLOW_ARTIFACT_KEY']}

# === 外部服务 ===
EXTERNAL_API_KEY={keys['EXTERNAL_API_KEY']}
WEBHOOK_SECRET={keys['WEBHOOK_SECRET']}

# === 加密配置 ===
ENCRYPTION_KEY={keys['ENCRYPTION_KEY']}
HASH_SALT={keys['HASH_SALT']}

# === 会话安全 ===
SESSION_SECRET={keys['SESSION_SECRET']}
CSRF_SECRET={keys['CSRF_SECRET']}
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Strict

# === 安全头配置 ===
SECURITY_HEADERS={{
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'"
}}
"""

        if output_path:
            env_path = Path(output_path)
        else:
            env_path = Path(f".env.{self.environment}")

        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env_content)

        print(f"✅ 环境文件已生成: {env_path}")

        # 设置文件权限
        env_path.chmod(0o600)
        print("✅ 文件权限已设置为 600")

    def generate_key_manifest(self, keys: Dict[str, str]):
        """生成密钥清单（不包含实际密钥值）"""
        print("\n📋 生成密钥清单...")

        manifest = {
            "environment": self.environment,
            "generated_at": datetime.now().isoformat(),
            "keys": {
                name: {
                    "length": len(value),
                    "type": "urlsafe" if "-" in value else "hex",
                    "purpose": self._get_key_purpose(name),
                    "rotation_period_days": self._get_rotation_period(name),
                    "checksum": hashlib.sha256(value.encode()).hexdigest()[:16],
                }
                for name, value in keys.items()
            },
            "security_policies": self._get_security_policies(),
        }

        manifest_path = self.keys_dir / f"manifest_{self.environment}.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        print(f"✅ 密钥清单已生成: {manifest_path}")

        return manifest

    def _get_key_purpose(self, key_name: str) -> str:
        """获取密钥用途"""
        purposes = {
            "SECRET_KEY": "应用签名密钥",
            "JWT_SECRET_KEY": "JWT访问令牌签名",
            "JWT_REFRESH_SECRET_KEY": "JWT刷新令牌签名",
            "API_KEY": "API访问密钥",
            "DB_ENCRYPTION_KEY": "数据库加密",
            "REDIS_PASSWORD": "Redis认证",
            "ENCRYPTION_KEY": "通用加密",
        }
        return purposes.get(key_name, "其他用途")

    def _get_rotation_period(self, key_name: str) -> int:
        """获取密钥轮换周期（天）"""
        rotation_periods = {
            "SECRET_KEY": 365,
            "JWT_SECRET_KEY": 90,
            "API_KEY": 180,
            "DB_ENCRYPTION_KEY": 365,
            "REDIS_PASSWORD": 90,
            "ENCRYPTION_KEY": 365,
        }
        return rotation_periods.get(key_name, 180)

    def _get_security_policies(self) -> Dict[str, Any]:
        """获取安全策略"""
        return {
            "password_policy": {
                "min_length": 32,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_numbers": True,
                "require_symbols": True,
            },
            "key_rotation": {
                "automatic": True,
                "notification_days_before": 30,
                "grace_period_days": 7,
            },
            "access_control": {
                "principle": "least_privilege",
                "audit_log": True,
                "mfa_required": True,
            },
        }

    def generate_encryption_keypair(self):
        """生成加密密钥对（用于API认证）"""
        print("\n🔑 生成RSA密钥对...")

        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        # 生成私钥
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)

        # 序列化私钥
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # 获取公钥
        public_key = private_key.public_key()

        # 序列化公钥
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        # 保存密钥
        private_path = self.keys_dir / f"private_{self.environment}.pem"
        public_path = self.keys_dir / f"public_{self.environment}.pem"

        with open(private_path, "wb") as f:
            f.write(private_pem)
        with open(public_path, "wb") as f:
            f.write(public_pem)

        # 设置权限
        private_path.chmod(0o600)
        public_path.chmod(0o644)

        print(f"✅ 私钥已保存: {private_path}")
        print(f"✅ 公钥已保存: {public_path}")

        return private_path, public_path

    def create_backup_encryption(self, env_file: Path):
        """创建备份加密文件"""
        print("\n💾 创建环境文件备份...")

        # 生成备份密钥
        backup_key = Fernet.generate_key()
        fernet = Fernet(backup_key)

        # 读取环境文件
        with open(env_file, "rb") as f:
            env_data = f.read()

        # 加密数据
        encrypted_data = fernet.encrypt(env_data)

        # 保存加密备份
        backup_path = self.keys_dir / f"env_{self.environment}.encrypted"
        with open(backup_path, "wb") as f:
            f.write(encrypted_data)

        # 保存备份密钥（应该单独存储）
        key_path = self.keys_dir / f"backup_key_{self.environment}.key"
        with open(key_path, "wb") as f:
            f.write(backup_key)

        backup_path.chmod(0o600)
        key_path.chmod(0o600)

        print(f"✅ 加密备份已创建: {backup_path}")
        print(f"⚠️  备份密钥已保存: {key_path} (请安全保管!)")

    def setup_complete_security(self):
        """执行完整的安全设置流程"""
        print(f"\n🚀 开始环境 '{self.environment}' 的完整安全设置...")
        print("=" * 60)

        # 1. 生成密钥
        keys = self.generate_secure_keys()

        # 2. 生成环境文件
        env_file = Path(f".env.{self.environment}")
        self.generate_env_file(keys)

        # 3. 生成密钥清单
        manifest = self.generate_key_manifest(keys)

        # 4. 生成RSA密钥对
        self.generate_encryption_keypair()

        # 5. 创建备份
        self.create_backup_encryption(env_file)

        # 6. 生成安全检查脚本
        self._generate_security_check_script()

        print("\n" + "=" * 60)
        print("✅ 安全设置完成!")
        print("\n📌 重要提醒:")
        print("1. 请妥善保管所有密钥文件")
        print("2. 不要将密钥文件提交到版本控制系统")
        print("3. 定期轮换密钥")
        print("4. 监控密钥使用情况")
        print(f"\n📊 密钥清单已生成在: {self.keys_dir}/manifest_{self.environment}.json")

        return keys, manifest

    def _generate_security_check_script(self):
        """生成安全检查脚本"""
        script_content = f"""#!/bin/bash
# 安全配置检查脚本
# 环境: {self.environment}

echo "🔍 检查安全配置..."

# 检查环境文件
if [ ! -f ".env.{self.environment}" ]; then
    echo "❌ 环境文件不存在"
    exit 1
fi

# 检查文件权限
if [ $(stat -c %a .env.{self.environment}) != "600" ]; then
    echo "❌ 环境文件权限不正确 (应为 600)"
    exit 1
fi

# 检查密钥长度
source .env.{self.environment}
if [ ${{#SECRET_KEY}} -lt 32 ]; then
    echo "❌ SECRET_KEY 长度不足"
    exit 1
fi

echo "✅ 安全配置检查通过"
"""

        script_path = self.security_dir / f"check_{self.environment}.sh"
        with open(script_path, "w") as f:
            f.write(script_content)

        script_path.chmod(0o755)
        print(f"✅ 安全检查脚本已生成: {script_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="安全配置自动化工具")
    parser.add_argument(
        "--env",
        choices=["development", "testing", "staging", "production"],
        default="production",
        help="目标环境",
    )
    parser.add_argument("--output", help="环境文件输出路径")
    parser.add_argument("--validate-only", action="store_true", help="仅验证现有配置")

    args = parser.parse_args()

    # 导入math模块（用于熵值计算）

    # 创建安全管理器
    manager = SecurityManager(args.env)

    if args.validate_only:
        # 仅验证模式
        print(f"🔍 验证环境 '{args.env}' 的安全配置...")
        # TODO: 实现验证逻辑
    else:
        # 完整设置模式
        manager.setup_complete_security()


if __name__ == "__main__":
    main()
