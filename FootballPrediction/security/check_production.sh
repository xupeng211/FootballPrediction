#!/bin/bash
# 安全配置检查脚本
# 环境: production

echo "🔍 检查安全配置..."

# 检查环境文件
if [ ! -f ".env.production" ]; then
    echo "❌ 环境文件不存在"
    exit 1
fi

# 检查文件权限
if [ $(stat -c %a .env.production) != "600" ]; then
    echo "❌ 环境文件权限不正确 (应为 600)"
    exit 1
fi

# 检查密钥长度
source .env.production
if [ ${#SECRET_KEY} -lt 32 ]; then
    echo "❌ SECRET_KEY 长度不足"
    exit 1
fi

echo "✅ 安全配置检查通过"
