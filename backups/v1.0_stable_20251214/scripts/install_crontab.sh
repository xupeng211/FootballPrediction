#!/bin/bash
# 安装每日管道crontab脚本

set -e

echo "🚀 安装MLOps每日数据管道crontab..."

# 创建日志目录
mkdir -p logs

# 安装crontab
crontab crontab_daily_pipeline.conf

echo "✅ Crontab安装完成！"
echo ""
echo "📋 已安装的任务："
echo "   - 每天凌晨4点：执行每日数据管道"
echo "   - 每周一凌晨5点：模型重训练"
echo "   - 每天凌晨6点：清理旧日志"
echo "   - 每月1号凌晨7点：清理旧训练集"
echo ""
echo "🔍 查看crontab: crontab -l"
echo "📝 编辑crontab: crontab -e"
echo "🗑️  删除crontab: crontab -r"