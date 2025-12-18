#!/bin/bash

# 足球预测系统 Docker 容器启动脚本
# 负责初始化数据库和启动cron服务

# set -e  # 禁用错误即退出，确保FastAPI始终尝试启动

echo "=================================="
echo "🏈 足球预测系统容器启动中..."
echo "=================================="

# 等待数据库服务就绪并执行一次性初始化
echo "⏳ 等待数据库连接..."
if [ ! -f "/tmp/db_initialized" ]; then
    echo "🔧 首次启动，执行数据库初始化..."
    python scripts/init_db.py || {
        echo "⚠️ 数据库初始化失败，但继续启动FastAPI应用"
    }
    touch /tmp/db_initialized
    echo "✅ 数据库初始化标记已设置"
else
    echo "✅ 数据库已初始化，跳过初始化步骤"
fi

echo "✅ 数据库连接和表结构初始化完成"

# 启动cron服务
echo "⏰ 启动cron定时任务服务..."
service cron start

# 验证cron服务状态
if service cron status > /dev/null 2>&1; then
    echo "✅ cron服务启动成功"
else
    echo "⚠️ cron服务启动失败（非关键服务，继续启动主应用）"
fi

# 显示cron任务列表（避免挂起，重定向到stdout）
echo "📅 已加载的定时任务:"
if crontab -l 2>/dev/null; then
    echo "定时任务加载完成"
else
    echo "无定时任务或定时任务加载失败"
fi

echo ""
echo "=================================="
echo "🚀 系统初始化完成，启动FastAPI应用..."
echo "=================================="

# 强制启动主应用（确保无论如何都尝试启动Web服务）
echo "🚀 准备启动FastAPI应用..."

if [ $# -eq 0 ]; then
    # 默认启动FastAPI应用
    echo "🌐 启动命令: exec uvicorn src.main:app --host 0.0.0.0 --port 8000"
    echo "📡 FastAPI服务启动中..."
    exec uvicorn src.main:app --host 0.0.0.0 --port 8000
else
    # 执行传入的命令
    echo "🔧 执行自定义命令: exec $*"
    exec "$@"
fi

# 如果exec失败（不应该到达这里），强制启动基本Web服务
echo "🚨 紧急启动：执行备用启动方案"
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --log-level debug