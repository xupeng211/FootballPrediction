#!/bin/bash
# GitHub Issues 同步工具环境配置脚本
# 使用方法: source github_sync_config.sh

export GITHUB_TOKEN="${GITHUB_TOKEN:-your_github_token_here}"
export GITHUB_REPO="xupeng211/FootballPrediction"

echo "✅ GitHub Issues 同步环境已加载"
echo "📁 仓库: $GITHUB_REPO"
echo "🔑 Token: ${GITHUB_TOKEN:0:8}..."
echo ""
echo "🚀 可用命令:"
echo "  python scripts/sync_issues.py pull   # 从GitHub拉取"
echo "  python scripts/sync_issues.py push   # 推送到GitHub"
echo "  python scripts/sync_issues.py sync   # 双向同步"
echo "  make sync-issues                      # 使用Makefile"
