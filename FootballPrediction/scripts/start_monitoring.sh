#!/bin/bash
# 启动监控面板服务

echo "🚀 启动FootballPrediction监控面板..."

# 检查Python是否可用
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查端口是否被占用
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ 端口8080已被占用，尝试使用端口8081"
    PORT=8081
else
    PORT=8080
fi

echo "📊 启动监控面板在端口 $PORT..."
echo "🌐 访问地址: http://localhost:$PORT/monitoring/dashboard.html"
echo "🛑 按 Ctrl+C 停止服务"

# 启动简单的HTTP服务器
cd "$(dirname "$0")/.."
python3 -m http.server $PORT
