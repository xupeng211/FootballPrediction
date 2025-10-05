#!/usr/bin/env python3
"""
密钥轮换工具 - 生成安全的新密钥
Security Key Rotation Tool

用途：生成新的安全密钥替换泄露的密钥
Usage: Generate new secure keys to replace leaked credentials
"""

import secrets
from datetime import datetime
from cryptography.fernet import Fernet


def generate_secret_key(length: int = 64) -> str:
    """生成URL安全的密钥"""
    return secrets.token_urlsafe(length)


def generate_hex_key(length: int = 32) -> str:
    """生成十六进制密钥"""
    return secrets.token_hex(length)


def generate_fernet_key() -> str:
    """生成Fernet加密密钥"""
    return Fernet.generate_key().decode()


def generate_all_keys():
    """生成所有需要的密钥"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    keys = {
        "SECRET_KEY": generate_secret_key(64),
        "JWT_SECRET_KEY": generate_secret_key(64),
        "JWT_REFRESH_SECRET_KEY": generate_secret_key(64),
        "API_KEY": generate_secret_key(64),
        "API_SECRET_KEY": generate_secret_key(64),
        "DB_ENCRYPTION_KEY": generate_hex_key(32),
        "DB_SALT": generate_hex_key(16),
        "REDIS_PASSWORD": generate_secret_key(32),
        "MLFLOW_TRACKING_PASSWORD": generate_secret_key(48),
        "MLFLOW_ARTIFACT_KEY": generate_hex_key(32),
        "EXTERNAL_API_KEY": generate_secret_key(64),
        "WEBHOOK_SECRET": generate_secret_key(64),
        "ENCRYPTION_KEY": generate_fernet_key(),
        "HASH_SALT": generate_hex_key(32),
        "SESSION_SECRET": generate_secret_key(64),
        "CSRF_SECRET": generate_secret_key(64),
        "S3_SECRET_KEY": generate_secret_key(32),
    }

    return keys, timestamp


def main():
    """主函数"""
    print("🔐 正在生成新的安全密钥...")
    print()

    keys, timestamp = generate_all_keys()

    # 打印密钥
    print(f"# 新生成的安全密钥 - 生成时间: {timestamp}")
    print("# ⚠️  请立即更新到生产环境并妥善保管！")
    print()
    print(f"SECRET_KEY={keys['SECRET_KEY']}")
    print(f"JWT_SECRET_KEY={keys['JWT_SECRET_KEY']}")
    print(f"JWT_REFRESH_SECRET_KEY={keys['JWT_REFRESH_SECRET_KEY']}")
    print(f"API_KEY={keys['API_KEY']}")
    print(f"API_SECRET_KEY={keys['API_SECRET_KEY']}")
    print(f"DB_ENCRYPTION_KEY={keys['DB_ENCRYPTION_KEY']}")
    print(f"DB_SALT={keys['DB_SALT']}")
    print(f"REDIS_PASSWORD={keys['REDIS_PASSWORD']}")
    print(f"MLFLOW_TRACKING_PASSWORD={keys['MLFLOW_TRACKING_PASSWORD']}")
    print(f"ENCRYPTION_KEY={keys['ENCRYPTION_KEY']}")
    print(f"HASH_SALT={keys['HASH_SALT']}")
    print(f"SESSION_SECRET={keys['SESSION_SECRET']}")
    print(f"CSRF_SECRET={keys['CSRF_SECRET']}")
    print()

    # 保存到文件
    output_file = f".env.production.new_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    env_content = f"""# 新生成的安全密钥 - {timestamp}
# ⚠️  此文件包含敏感信息，切勿提交到Git！

ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO

SECRET_KEY={keys['SECRET_KEY']}
JWT_SECRET_KEY={keys['JWT_SECRET_KEY']}
JWT_REFRESH_SECRET_KEY={keys['JWT_REFRESH_SECRET_KEY']}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

API_KEY={keys['API_KEY']}
API_SECRET_KEY={keys['API_SECRET_KEY']}

DB_ENCRYPTION_KEY={keys['DB_ENCRYPTION_KEY']}
DB_SALT={keys['DB_SALT']}

REDIS_PASSWORD={keys['REDIS_PASSWORD']}

MLFLOW_TRACKING_PASSWORD={keys['MLFLOW_TRACKING_PASSWORD']}
MLFLOW_ARTIFACT_KEY={keys['MLFLOW_ARTIFACT_KEY']}

EXTERNAL_API_KEY={keys['EXTERNAL_API_KEY']}
WEBHOOK_SECRET={keys['WEBHOOK_SECRET']}

ENCRYPTION_KEY={keys['ENCRYPTION_KEY']}
HASH_SALT={keys['HASH_SALT']}

SESSION_SECRET={keys['SESSION_SECRET']}
CSRF_SECRET={keys['CSRF_SECRET']}
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Strict

S3_SECRET_KEY={keys['S3_SECRET_KEY']}
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(env_content)

    print(f"✅ 新密钥已保存到: {output_file}")
    print("⚠️  请勿将此文件提交到Git！")
    print()
    print("📋 后续步骤：")
    print("   1. 备份当前生产环境配置")
    print("   2. 将新密钥更新到生产环境")
    print("   3. 重启所有服务")
    print("   4. 验证功能正常")
    print("   5. 安全删除旧密钥文件")


if __name__ == "__main__":
    main()
