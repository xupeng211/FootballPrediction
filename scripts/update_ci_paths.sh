#!/bin/bash
# 批量更新 CI 配置文件中的脚本路径
# 用途：将重组后的脚本路径更新到 CI 配置
# 日期：2025-10-05

set -e

CI_DIR="/home/user/projects/FootballPrediction/.github/workflows"

echo "🔄 开始更新 CI 配置文件中的脚本路径..."
echo "================================================"

# 备份原始文件
echo "📦 备份原始 CI 配置..."
tar -czf ci_config_backup_$(date +%Y%m%d_%H%M%S).tar.gz .github/workflows/*.yml

# 更新 MLOps 流水线
echo "📝 更新 MLOps 流水线..."
sed -i 's|python scripts/update_predictions_results\.py|python scripts/ml/update_predictions.py|g' "$CI_DIR/MLOps机器学习流水线.yml"
sed -i 's|python scripts/retrain_pipeline\.py|python scripts/ml/retrain_pipeline.py|g' "$CI_DIR/MLOps机器学习流水线.yml"

# 更新项目同步流水线
echo "📝 更新项目同步流水线..."
sed -i 's|python scripts/sync_issues\.py|python scripts/analysis/sync_issues.py|g' "$CI_DIR/项目同步流水线.yml" 2>/dev/null || true

echo ""
echo "✅ CI 配置路径更新完成！"
echo "================================================"
echo ""
echo "📊 更新的文件："
echo "  - MLOps机器学习流水线.yml"
echo "  - 项目同步流水线.yml"
echo ""
echo "⚠️  请注意："
echo "  1. 备份文件已保存到 ci_config_backup_*.tar.gz"
echo "  2. 运行 'git diff .github/workflows/' 查看更改"
echo "  3. 测试 CI 流水线是否正常工作"
echo ""
