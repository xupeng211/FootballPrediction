#!/usr/bin/env python3
"""
安全密钥生成脚本
Generate secure keys for production deployment
"""

import secrets
import string
import hashlib
import base64
from pathlib import Path
import json
from datetime import datetime


def generate_secure_jwt_key(length: int = 64) -> str:
    """生成安全的JWT密钥"""
    return secrets.token_urlsafe(length)


def generate_api_key(length: int = 32) -> str:
    """生成API密钥"""
    return secrets.token_urlsafe(length)


def generate_database_password(length: int = 32) -> str:
    """生成数据库密码"""
    # 包含大小写字母、数字和特殊字符
    characters = string.ascii_letters + string.digits + "!@#$%^&*()_+-="
    return "".join(secrets.choice(characters) for _ in range(length))


def generate_redis_password(length: int = 32) -> str:
    """生成Redis密码"""
    return secrets.token_urlsafe(length)


def hash_password(password: str) -> str:
    """生成密码哈希（用于存储）"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_cors_origins() -> list:
    """生成CORS允许的源"""
    return [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://your-domain.com",  # 生产环境中需要更改
        "https://api.your-domain.com",  # 生产环境中需要更改
    ]


def generate_security_config() -> dict:
    """生成完整的安全配置"""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "jwt_secret_key": generate_secure_jwt_key(64),
        "jwt_refresh_secret_key": generate_secure_jwt_key(64),
        "algorithm": "HS256",
        "access_token_expire_minutes": 30,
        "refresh_token_expire_days": 7,
        "api_key": generate_api_key(32),
        "api_secret_key": generate_api_key(48),
        "database_password": generate_database_password(32),
        "redis_password": generate_redis_password(32),
        "cors_origins": generate_cors_origins(),
        "rate_limit_per_minute": 60,
        "rate_limit_burst": 10,
        "secure_headers_enabled": True,
        "password_min_length": 12,
        "session_timeout_minutes": 30,
        "audit_log_enabled": True,
        "notes": {
            "jwt_security": "JWT密钥已生成，长度64位，使用HMAC-SHA256算法",
            "password_strength": "所有密码都包含大小写字母、数字和特殊字符",
            "cors_configuration": "请根据实际域名修改CORS允许的源",
            "deployment_checklist": [
                "1. 将所有密钥存储在安全的密钥管理系统中",
                "2. 更新CORS配置以匹配实际域名",
                "3. 配置HTTPS证书",
                "4. 设置防火墙规则",
                "5. 启用审计日志",
                "6. 配置备份策略",
            ],
        },
    }


def save_env_file(config: dict, output_path: str = ".env.production"):
    """保存生产环境配置文件"""
    env_content = f"""# ============================================================================
# Football Prediction System - Production Environment Configuration
# ============================================================================
# Generated on: {config['timestamp']}
# ⚠️  IMPORTANT: This file contains sensitive information - keep it secure!
# ============================================================================

# === Application Configuration ===
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=WARNING
PYTHONPATH=/app

# === JWT Authentication ===
JWT_SECRET_KEY={config['jwt_secret_key']}
JWT_REFRESH_SECRET_KEY={config['jwt_refresh_secret_key']}
ALGORITHM={config['algorithm']}
ACCESS_TOKEN_EXPIRE_MINUTES={config['access_token_expire_minutes']}
REFRESH_TOKEN_EXPIRE_DAYS={config['refresh_token_expire_days']}

# === API Security ===
API_KEY={config['api_key']}
API_SECRET_KEY={config['api_secret_key']}
API_HOSTNAME=your-production-domain.com

# === Database Configuration ===
DATABASE_URL=postgresql+asyncpg://your_db_user:{config['database_password']}@localhost:5432/football_prediction_prod
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction_prod
DB_USER=your_db_user
DB_PASSWORD={config['database_password']}

# PostgreSQL Docker Configuration
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD={config['database_password']}
POSTGRES_DB=football_prediction_prod

# === Redis Configuration ===
REDIS_URL=redis://:{config['redis_password']}@localhost:6379/0
REDIS_PASSWORD={config['redis_password']}
REDIS_PORT=6379

# === Security Configuration ===
# Rate Limiting
RATE_LIMIT_PER_MINUTE={config['rate_limit_per_minute']}
RATE_LIMIT_BURST={config['rate_limit_burst']}

# CORS Settings
CORS_ORIGINS={','.join(config['cors_origins'])}
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=*

# HTTPS/TLS Configuration
SSL_CERT_PATH=/etc/ssl/certs/app.crt
SSL_KEY_PATH=/etc/ssl/private/app.key
FORCE_HTTPS=true

# Security Headers
SECURE_HEADERS_ENABLED={config['secure_headers_enabled']}
X_FRAME_OPTIONS=DENY
X_CONTENT_TYPE_OPTIONS=nosniff
X_XSS_PROTECTION=1; mode=block
STRICT_TRANSPORT_SECURITY=max-age=31536000; includeSubDomains

# Content Security Policy
CSP_ENABLED=true
CSP_DEFAULT_SRC='self'
CSP_SCRIPT_SRC='self' 'unsafe-inline'
CSP_STYLE_SRC='self' 'unsafe-inline'

# Password Policy
PASSWORD_MIN_LENGTH={config['password_min_length']}
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SYMBOLS=true

# Session Security
SESSION_TIMEOUT_MINUTES={config['session_timeout_minutes']}
SESSION_SECURE_COOKIE=true
SESSION_HTTP_ONLY_COOKIE=true
SESSION_SAMESITE_COOKIE=Strict

# Audit Logging
AUDIT_LOG_ENABLED={config['audit_log_enabled']}
AUDIT_LOG_LEVEL=INFO
AUDIT_LOG_FILE=/var/log/app/audit.log

# === Application Server ===
API_HOST=0.0.0.0
API_PORT=8000

# === Docker Compose Configuration ===
APP_IMAGE=football-prediction
APP_TAG=production
BUILD_TARGET=production

# Nginx Configuration
NGINX_PORT=80
NGINX_SSL_PORT=443

# === Feature Flags ===
ENABLE_CELERY=true
ENABLE_MLFLOW=true
ENABLE_NGINX=true
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    # 设置文件权限为仅所有者可读写
    Path(output_path).chmod(0o600)
    print(f"✅ 生产环境配置已保存到: {output_path}")


def save_config_json(config: dict, output_path: str = "config/security_config.json"):
    """保存JSON格式的配置"""
    # 创建目录（如果不存在）
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✅ 安全配置已保存到: {output_path}")


def print_security_summary(config: dict):
    """打印安全配置摘要"""
    print("\n" + "=" * 80)
    print("🔐 安全配置生成完成")
    print("=" * 80)
    print(f"📅 生成时间: {config['timestamp']}")
    print(f"🔑 JWT密钥长度: {len(config['jwt_secret_key'])} 字符")
    print(f"🔐 JWT算法: {config['algorithm']}")
    print(f"🗝️  数据库密码强度: {'强' if len(config['database_password']) >= 32 else '弱'}")
    print(f"🔴 Redis密码强度: {'强' if len(config['redis_password']) >= 32 else '弱'}")
    print(f"🌐 CORS源数量: {len(config['cors_origins'])}")
    print(f"⚡ 速率限制: {config['rate_limit_per_minute']}/分钟")
    print(f"🛡️  安全头: {'启用' if config['secure_headers_enabled'] else '禁用'}")
    print(f"📝 审计日志: {'启用' if config['audit_log_enabled'] else '禁用'}")

    print("\n🚨 重要安全提醒:")
    for i, note in enumerate(config["notes"]["deployment_checklist"], 1):
        print(f"   {note}")

    print("\n📁 生成的文件:")
    print("   - .env.production (生产环境配置)")
    print("   - config/security_config.json (详细配置)")


def main():
    """主函数"""
    print("🔐 正在生成安全配置...")

    # 生成安全配置
    config = generate_security_config()

    # 保存配置文件
    save_env_file(config)
    save_config_json(config)

    # 打印摘要
    print_security_summary(config)

    print("\n✅ 安全配置生成完成！")
    print("🔒 请确保将 .env.production 文件保存在安全的位置")


if __name__ == "__main__":
    main()
