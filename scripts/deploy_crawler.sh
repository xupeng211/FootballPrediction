#!/bin/bash
# FotMob爬虫部署脚本

set -e

echo "🚀 开始部署FotMob爬虫服务..."

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: Docker Compose未安装"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要目录..."
mkdir -p data/fotmob/historical
mkdir -p logs
mkdir -p monitoring

# 设置权限
chmod 755 scripts/*.py
chmod +x scripts/deploy_crawler.sh

# 构建爬虫镜像
echo "🔨 构建爬虫Docker镜像..."
docker-compose -f docker-compose.crawler.yml build fotmob-crawler

# 启动服务
echo "🚀 启动爬虫服务..."
docker-compose -f docker-compose.crawler.yml up -d

echo "✅ 部署完成！"
echo
echo "📊 服务状态检查:"
echo "  docker-compose -f docker-compose.crawler.yml ps"
echo
echo "📝 查看爬虫日志:"
echo "  docker-compose -f docker-compose.crawler.yml logs -f fotmob-crawler"
echo
echo "🔧 进入爬虫容器:"
echo "  docker-compose -f docker-compose.crawler.yml exec fotmob-crawler bash"
echo
echo "🛑 停止服务:"
echo "  docker-compose -f docker-compose.crawler.yml down"
echo
echo "📈 监控面板:"
echo "  Prometheus: http://localhost:9090"
echo "  Grafana: http://localhost:3001 (admin/admin123)"
echo
echo "⚠️  提醒: 爬虫会自动运行智能休眠，保护IP避免被封锁"