#!/bin/bash
# 全历史数据回填部署脚本
# Deployment Script for Full Historical Data Backfill

set -e

echo "🚀 全历史数据回填部署脚本"
echo "================================"

# 检查项目环境
echo "📋 检查项目环境..."
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ 未找到 docker-compose.yml，请在项目根目录运行"
    exit 1
fi

# 检查脚本文件
echo "📋 检查脚本文件..."
SCRIPTS=(
    "scripts/backfill_full_history.py"
    "scripts/backfill_demo.py"
    "scripts/test_backfill_engine.py"
    "scripts/test_super_greedy.py"
)

for script in "${SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        echo "❌ 未找到脚本文件: $script"
        exit 1
    fi
done

echo "✅ 所有脚本文件检查通过"

# 检查Python依赖
echo "📋 检查Python依赖..."
python -c "import asyncio, json, logging" || {
    echo "❌ Python依赖检查失败"
    exit 1
}
echo "✅ Python依赖检查通过"

# 检查配置文件
echo "📋 检查配置文件..."
if [ ! -f "config/target_leagues.json" ]; then
    echo "❌ 未找到配置文件: config/target_leagues.json"
    exit 1
fi
echo "✅ 配置文件检查通过"

# 检查数据库连接
echo "📋 检查数据库连接..."
if ! make status > /dev/null 2>&1; then
    echo "❌ 数据库服务未运行，正在启动..."
    make dev
    echo "⏳ 等待服务启动..."
    sleep 10
fi

echo "✅ 数据库连接检查通过"

# 运行测试
echo "🧪 运行功能测试..."
echo "--------------------------------"

echo "1. 测试回填引擎核心逻辑..."
python scripts/test_backfill_engine.py
echo ""

echo "2. 运行安全演示..."
python scripts/backfill_demo.py
echo ""

echo "3. 验证 Super Greedy Mode..."
python scripts/test_super_greedy.py
echo ""

# 询问是否执行完整回填
echo "================================"
echo "🎯 所有测试通过！"
echo ""
echo "⚠️  准备执行完整的全历史数据回填"
echo "📊 预计需要处理 7,500+ 场比赛"
echo "⏱️  预计耗时 15+ 小时"
echo ""
read -p "是否继续执行完整回填? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 开始执行完整回填..."
    echo "💡 提示: 可以随时按 Ctrl+C 中断，支持断点续传"
    echo "📋 日志文件: backfill_full_history.log"
    echo "--------------------------------"

    # 备份数据库
    echo "💾 备份数据库..."
    backup_file="backup_before_backfill_$(date +%Y%m%d_%H%M%S).sql"
    docker-compose exec -T db pg_dump -U football_prediction football_prediction > "$backup_file"
    echo "✅ 数据库备份完成: $backup_file"

    # 执行回填
    echo "🚀 启动回填脚本..."
    python scripts/backfill_full_history.py

    echo "🎉 回填脚本执行完成!"
else
    echo "📋 跳过完整回填"
    echo "💡 要手动执行请运行: python scripts/backfill_full_history.py"
fi

echo ""
echo "================================"
echo "✅ 部署脚本执行完成"
echo ""
echo "📚 更多信息请查看:"
echo "   - 使用指南: BACKFULL_HISTORY_GUIDE.md"
echo "   - 测试日志: backfill_full_history.log"
echo "   - 配置文件: config/target_leagues.json"
echo "================================"