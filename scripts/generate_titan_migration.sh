#!/bin/bash
# Titan007 双表架构迁移文件生成脚本

echo "🚀 开始生成 Titan007 双表架构迁移文件..."

# 1. 进入项目根目录
cd /home/user/projects/FootballPrediction

# 2. 确保虚拟环境激活
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️ 请先激活虚拟环境: source venv/bin/activate"
    exit 1
fi

# 3. 导出环境变量（使用测试数据库）
export ENVIRONMENT=test
export DATABASE_URL="postgresql+asyncpg://test_user:test_pass@localhost:5432/football_prediction_test"

# 4. 生成迁移文件
echo "📝 生成双表架构迁移文件..."
alembic revision --autogenerate -m "implement_titan_dual_table_architecture"

echo "✅ 迁移文件已生成: src/database/migrations/versions/xxxx_implement_titan_dual_table_architecture.py"
echo ""
echo "📋 下一步操作:"
echo "1. 检查生成的迁移文件是否包含所有新表"
echo "2. 测试迁移: alembic upgrade head"
echo "3. 回滚测试: alembic downgrade -1"
echo "4. 部署到生产环境"