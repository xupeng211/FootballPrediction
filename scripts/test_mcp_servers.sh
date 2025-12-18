#!/bin/bash

echo "🔍 测试所有MCP服务器..."

echo ""
echo "1. 测试PostgreSQL服务器..."
timeout 3 python mcp_servers/postgres_server.py 2>/dev/null && echo "✅ PostgreSQL服务器正常" || echo "❌ PostgreSQL服务器异常"

echo ""
echo "2. 测试Redis服务器..."
timeout 3 python mcp_servers/redis_server.py 2>/dev/null && echo "✅ Redis服务器正常" || echo "❌ Redis服务器异常"

echo ""
echo "3. 测试文件系统服务器..."
timeout 3 python mcp_servers/filesystem_server.py 2>/dev/null && echo "✅ 文件系统服务器正常" || echo "❌ 文件系统服务器异常"

echo ""
echo "4. 测试系统监控服务器..."
timeout 3 python mcp_servers/system_monitor_server.py 2>/dev/null && echo "✅ 系统监控服务器正常" || echo "❌ 系统监控服务器异常"

echo ""
echo "📋 MCP配置文件内容："
cat .mcp.json

echo ""
echo "🔧 解决方案："
echo "1. 重启Claude Code: claude --project /home/user/projects/FootballPrediction"
echo "2. 或在Claude Code中使用: /mcp enable"