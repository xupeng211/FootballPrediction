#!/usr/bin/env python3
"""
初始化生产环境密钥
"""

import os
import sys
import secrets
import json
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.security.secret_manager import (
    SecretManager,
    EnvironmentSecretProvider,
    FileSecretProvider,
)


def generate_jwt_secret():
    """生成JWT密钥"""
    return secrets.token_urlsafe(32)


def setup_aws_secrets():
    """设置AWS Secrets Manager"""
    print("🔧 设置AWS Secrets Manager...")

    # AWS Secrets Manager配置示例
    secrets = {
        "DATABASE_URL": "postgresql+asyncpg://username:password@host:5432/football_prediction_prod",
        "REDIS_URL": "redis://username:password@host:6379/0",
        "JWT_SECRET_KEY": generate_jwt_secret(),
        "FOOTBALL_API_KEY": "your-football-api-key",
        "WEATHER_API_KEY": "your-weather-api-key",
        "SSL_CERT_PATH": "/etc/ssl/certs/football_prediction.crt",
        "SSL_KEY_PATH": "/etc/ssl/private/football_prediction.key",
    }

    print("\n请将以下JSON内容保存到AWS Secrets Manager：")
    print("Secret Name: football_prediction/secrets")
    print(json.dumps(secrets, indent=2))

    print("\nAWS CLI命令示例：")
    print(
        f"aws secretsmanager create-secret --name football_prediction/secrets --secret-string '{json.dumps(secrets)}'"
    )


def setup_environment_file():
    """设置环境变量文件"""
    print("\n🔧 设置环境变量文件...")

    env_file = Path(".env.production")

    if env_file.exists():
        print(f"⚠️  {env_file} 已存在")
        overwrite = input("是否覆盖？(y/N): ").lower()
        if overwrite != "y":
            return

    # 生成JWT密钥
    jwt_secret = generate_jwt_secret()

    # 写入环境变量
    env_content = f"""# 生产环境配置
ENVIRONMENT=production

# 数据库配置
FP_DATABASE_URL=postgresql+asyncpg://username:password@host:5432/football_prediction_prod

# Redis配置
FP_REDIS_URL=redis://username:password@host:6379/0

# JWT密钥（自动生成）
FP_JWT_SECRET_KEY={jwt_secret}

# SSL证书路径
FP_SSL_CERT_PATH=/etc/ssl/certs/football_prediction.crt
FP_SSL_KEY_PATH=/etc/ssl/private/football_prediction.key

# 第三方API密钥
FP_FOOTBALL_API_KEY=your-football-api-key
FP_WEATHER_API_KEY=your-weather-api-key

# 日志配置
LOG_LEVEL=INFO
"""

    env_file.write_text(env_content)
    print(f"✅ 环境变量文件已创建: {env_file}")
    print(f"✅ JWT密钥已生成: {jwt_secret[:20]}...")

    print("\n⚠️  请更新以下配置项：")
    print("  - DATABASE_URL: 设置实际的数据库连接")
    print("  - REDIS_URL: 设置实际的Redis连接")
    print("  - FOOTBALL_API_KEY: 设置足球数据API密钥")
    print("  - SSL证书路径: 设置实际的SSL证书路径")


def setup_development_secrets():
    """设置开发环境密钥"""
    print("\n🔧 设置开发环境密钥...")

    secrets_file = Path(".secrets.json")

    if secrets_file.exists():
        print(f"⚠️  {secrets_file} 已存在")
        overwrite = input("是否覆盖？(y/N): ").lower()
        if overwrite != "y":
            return

    # 生成开发环境密钥
    secrets = {
        "JWT_SECRET_KEY": generate_jwt_secret(),
        "FOOTBALL_API_KEY": "dev-api-key",
        "WEATHER_API_KEY": "dev-weather-key",
    }

    # 保存到文件
    with open(secrets_file, "w") as f:
        json.dump(secrets, f, indent=2)

    # 设置文件权限
    os.chmod(secrets_file, 0o600)

    print(f"✅ 开发密钥文件已创建: {secrets_file}")
    print("⚠️  文件权限已设置为 600（仅所有者可读写）")


def verify_secrets():
    """验证密钥配置"""
    print("\n🔍 验证密钥配置...")

    try:
        manager = SecretManager()

        # 测试获取密钥
        db_url = manager.get_database_url()
        redis_url = manager.get_redis_url()
        jwt_secret = manager.get_jwt_secret()

        print(f"✅ 数据库URL: {db_url[:50]}...")
        print(f"✅ Redis URL: {redis_url[:30]}...")
        print(f"✅ JWT密钥: {'已配置' if jwt_secret else '未配置'}")

        # 环境特定检查
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production":
            if "username:password" in db_url:
                print("⚠️  警告: 数据库URL包含默认凭据")
            if "localhost" in db_url or "127.0.0.1" in db_url:
                print("⚠️  警告: 生产环境不应使用localhost")
            if len(jwt_secret) < 32:
                print("⚠️  警告: JWT密钥长度应至少32个字符")

        print("\n✅ 密钥配置验证完成")

    except Exception as e:
        print(f"\n❌ 密钥配置验证失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("FootballPrediction 密钥初始化工具")
    print("=" * 60)

    print("\n请选择操作:")
    print("1. 设置生产环境密钥（AWS Secrets Manager）")
    print("2. 设置生产环境密钥（环境变量文件）")
    print("3. 设置开发环境密钥")
    print("4. 验证密钥配置")
    print("5. 生成新的JWT密钥")

    choice = input("\n请输入选项 (1-5): ").strip()

    if choice == "1":
        setup_aws_secrets()
    elif choice == "2":
        setup_environment_file()
    elif choice == "3":
        setup_development_secrets()
    elif choice == "4":
        verify_secrets()
    elif choice == "5":
        print(f"\n✅ 新的JWT密钥: {generate_jwt_secret()}")
    else:
        print("\n❌ 无效选项")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("操作完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
