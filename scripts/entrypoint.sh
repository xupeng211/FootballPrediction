#!/bin/bash

# 足球预测系统 Docker 容器启动脚本
# 负责初始化数据库和启动cron服务

set -e  # 遇到错误立即退出

echo "=================================="
echo "🏈 足球预测系统容器启动中..."
echo "=================================="

# 等待数据库服务就绪
echo "⏳ 等待数据库连接..."
until python -c "
import asyncio
import sys
import os
from src.database.connection import initialize_database, get_async_session

async def check_db():
    try:
        # 设置环境变量
        os.environ.setdefault('DB_HOST', 'db')
        os.environ.setdefault('DB_PORT', '5432')
        os.environ.setdefault('DB_NAME', 'football_prediction')
        os.environ.setdefault('DB_USER', 'postgres')
        os.environ.setdefault('DB_PASSWORD', 'football_prediction_2024')

        # 初始化数据库连接
        database_url = f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        initialize_database(database_url)

        # 测试连接
        from sqlalchemy import text
        async with get_async_session() as session:
            await session.execute(text('SELECT 1'))
        return True
    except Exception as e:
        print(f'数据库连接失败: {e}')
        return False

if asyncio.run(check_db()):
    print('✅ 数据库连接成功')
    sys.exit(0)
else:
    sys.exit(1)
" 2>/dev/null; do
    echo "🔄 数据库尚未就绪，等待5秒后重试..."
    sleep 5
done

# 初始化数据库表
echo "🔧 初始化数据库表结构..."
cd /app && python -c "
import asyncio
import os
from src.database.connection import initialize_database, engine
from src.database.models import Base

async def init_db():
    try:
        # 设置环境变量
        os.environ.setdefault('DB_HOST', 'db')
        os.environ.setdefault('DB_PORT', '5432')
        os.environ.setdefault('DB_NAME', 'football_prediction')
        os.environ.setdefault('DB_USER', 'postgres')
        os.environ.setdefault('DB_PASSWORD', 'football_prediction_2024')

        # 初始化数据库连接
        database_url = f'postgresql+asyncpg://{os.getenv(\"DB_USER\")}:{os.getenv(\"DB_PASSWORD\")}@{os.getenv(\"DB_HOST\")}:{os.getenv(\"DB_PORT\")}/{os.getenv(\"DB_NAME\")}'
        initialize_database(database_url)

        # 创建表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print('✅ 数据库表创建成功')
    except Exception as e:
        print(f'❌ 数据库表创建失败: {e}')
        raise

asyncio.run(init_db())
"

# 启动cron服务
echo "⏰ 启动cron定时任务服务..."
service cron start

# 验证cron服务状态
if service cron status > /dev/null 2>&1; then
    echo "✅ cron服务启动成功"
else
    echo "❌ cron服务启动失败"
    exit 1
fi

# 显示cron任务列表
echo "📅 已加载的定时任务:"
crontab -l

echo ""
echo "=================================="
echo "🚀 系统初始化完成，启动FastAPI应用..."
echo "=================================="

# 启动主应用（如果传入参数则执行，否则默认启动uvicorn）
if [ $# -eq 0 ]; then
    # 默认启动FastAPI应用
    exec uvicorn src.main:app --host 0.0.0.0 --port 8000
else
    # 执行传入的命令
    exec "$@"
fi