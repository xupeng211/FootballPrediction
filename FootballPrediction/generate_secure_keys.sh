#!/bin/bash

echo "🔒 生成安全密钥..."

# 检查是否安装了secrets模块
if ! python3 -c "import secrets" 2>/dev/null; then
    echo "❌ Python secrets模块不可用"
    exit 1
fi

# 生成应用密钥
APP_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
echo "SECRET_KEY=${APP_SECRET}" >> .env.production

# 生成JWT密钥
JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
echo "JWT_SECRET_KEY=${JWT_SECRET}" >> .env.production

# 生成刷新密钥
REFRESH_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')
echo "JWT_REFRESH_SECRET_KEY=${REFRESH_SECRET}" >> .env.production

# 生成随机数据库密码
DB_PASSWORD=$(python3 -c 'import secrets; import string; import random; chars = string.ascii_letters + string.digits + "!@#$%^&*"; print("".join(random.choice(chars) for _ in range(16)))')
echo "POSTGRES_PASSWORD=${DB_PASSWORD}" >> .env.production

echo "✅ 安全密钥已生成并保存到 .env.production"
echo "⚠️  请检查 .env.production 文件并完善其他配置"
echo "🔐 请将 .env.production 添加到 .gitignore 中"
echo ""
echo "🔑 生成的密钥摘要:"
echo "  SECRET_KEY: ${APP_SECRET:0:10}... (64 chars)"
echo "  JWT_SECRET_KEY: ${JWT_SECRET:0:10}... (64 chars)"
echo "  REFRESH_SECRET: ${REFRESH_SECRET:0:10}... (64 chars)"
echo "  DB_PASSWORD: ${DB_PASSWORD} (16 chars)"
