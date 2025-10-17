#!/bin/bash
# 测试环境启动脚本

echo "🚀 启动测试环境..."

# 启动Docker服务
docker-compose -f docker-compose.test.yml up -d

# 等待服务就绪
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
docker-compose -f docker-compose.test.yml ps

echo ""
echo "✅ 测试环境已启动！"
echo ""
echo "运行测试："
echo "  pytest tests/unit/                    # 单元测试"
echo "  pytest tests/integration/             # 集成测试"
echo "  pytest --cov=src --cov-report=html   # 覆盖率测试"
echo ""
echo "停止环境："
echo "  docker-compose -f docker-compose.test.yml down"
