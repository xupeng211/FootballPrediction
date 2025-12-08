#!/bin/bash
# FotMob 令牌注入脚本
# 用法: ./inject_fotmob_tokens.sh "x-mas-token" "x-foo-token"

if [ $# -ne 2 ]; then
    echo "❌ 使用方法: $0 \"<x-mas-token>\" \"<x-foo-token>\""
    echo ""
    echo "📋 获取令牌步骤:"
    echo "1. 访问 https://www.fotmob.com"
    echo "2. F12 -> Network -> 过滤 'api'"
    echo "3. 查找 API 请求中的 x-mas 和 x-foo headers"
    echo ""
    echo "💡 示例: $0 \"eyJib2R5Ijp7InVybCI6...\" \"eyJmb28iOiJwcm9kdWN0aW9u...\""
    exit 1
fi

FOTMOB_TOKEN="$1"
FOTMOB_SECRET="$2"

echo "🔐 注入 FotMob API 令牌..."
echo "📝 x-mas token 长度: ${#FOTMOB_TOKEN}"
echo "📝 x-foo token 长度: ${#FOTMOB_SECRET}"

# 验证令牌格式
if [[ ! "$FOTMOB_TOKEN" =~ ^eyJ ]]; then
    echo "⚠️ 警告: x-mas token 格式可能不正确（应以 eyJ 开头）"
fi

if [[ ! "$FOTMOB_SECRET" =~ ^eyJ ]]; then
    echo "⚠️ 警告: x-foo token 格式可能不正确（应以 eyJ 开头）"
fi

# 创建临时环境文件
cat > .env.fotmob.tmp << EOF
FOTMOB_TOKEN=$FOTMOB_TOKEN
FOTMOB_SECRET=$FOTMOB_SECRET
EOF

echo "✅ 令牌已保存到 .env.fotmob.tmp"
echo ""
echo "🚀 正在重启 L2 容器并注入令牌..."

# 停止现有 L2 容器
docker-compose stop data-collector-l2

# 使用新令牌重启容器
export FOTMOB_TOKEN="$FOTMOB_TOKEN"
export FOTMOB_SECRET="$FOTMOB_SECRET"

# 启动容器并注入环境变量
docker-compose up -d --no-deps \
    -e FOTMOB_TOKEN="$FOTMOB_TOKEN" \
    -e FOTMOB_SECRET="$FOTMOB_SECRET" \
    --scale data-collector-l2=3 \
    data-collector-l2

if [ $? -eq 0 ]; then
    echo "✅ L2 容器重启成功"
    echo ""
    echo "📊 开始监控日志..."
    echo "🔍 寻找关键词: '✅ 成功从页面提取市场概率数据' 或 'Saved odds'"
    echo ""
    echo "实时日志命令: docker-compose logs -f data-collector-l2"
    echo "停止监控: Ctrl+C"

    # 等待容器启动
    sleep 10

    # 开始监控日志
    docker-compose logs -f data-collector-l2 --tail=20
else
    echo "❌ L2 容器重启失败"
    exit 1
fi