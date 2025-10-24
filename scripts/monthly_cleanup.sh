#!/bin/bash
# 每月深度清理脚本
# 使用方法: ./scripts/monthly_cleanup.sh

set -e

echo "🧹 开始每月深度清理..."

# 1. 执行每周清理
echo "🔄 先执行每周清理..."
if [ -f "./scripts/weekly_cleanup.sh" ]; then
    ./scripts/weekly_cleanup.sh
fi

# 2. 创建月度归档
MONTH_DIR="archive/$(date +%Y-%m)"
mkdir -p "$MONTH_DIR"/{reports,coverage,temp,old}

# 3. 移动所有剩余的临时报告
echo "📝 归档所有剩余报告..."
find . -maxdepth 1 -name "*REPORT*.md" -exec mv {} "$MONTH_DIR/reports/" \; 2>/dev/null || true
find . -maxdepth 1 -name "*SUMMARY*.md" -exec mv {} "$MONTH_DIR/reports/" \; 2>/dev/null || true
find . -maxdepth 1 -name "*ANALYSIS*.md" -exec mv {} "$MONTH_DIR/reports/" \; 2>/dev/null || true
find . -maxdepth 1 -name "*PROGRESS*.md" -exec mv {} "$MONTH_DIR/reports/" \; 2>/dev/null || true

# 4. 移动中文报告
echo "📝 归档中文报告..."
find . -maxdepth 1 -name "*报告*.md" -exec mv {} "$MONTH_DIR/reports/" \; 2>/dev/null || true
find . -maxdepth 1 -name "*总结*.md" -exec mv {} "$MONTH_DIR/reports/" \; 2>/dev/null || true
find . -maxdepth 1 -name "*日志*.md" -exec mv {} "$MONTH_DIR/reports/" \; 2>/dev/null || true
find . -maxdepth 1 -name "*改进*.md" -exec mv {} "$MONTH_DIR/reports/" \; 2>/dev/null || true

# 5. 移动所有覆盖率数据
echo "📊 归档所有覆盖率数据..."
find . -maxdepth 1 -name "coverage*" -exec mv {} "$MONTH_DIR/coverage/" \; 2>/dev/null || true
find . -maxdepth 1 -name "*coverage*" -exec mv {} "$MONTH_DIR/coverage/" \; 2>/dev/null || true

# 6. 清理旧的归档（保留最近3个月）
echo "🗃️ 整理旧归档..."
find archive/ -maxdepth 1 -type d -name "20*" -mtime +90 -exec mv {} "$MONTH_DIR/old/" \; 2>/dev/null || true

# 7. 清理Docker（可选）
if command -v docker &> /dev/null; then
    echo "🐳 清理Docker资源..."
    docker system prune -f
fi

# 8. 生成清理报告
echo "📊 生成清理报告..."
REPORT_FILE="$MONTH_DIR/cleanup_report_$(date +%Y%m%d).md"
cat > "$REPORT_FILE" << EOF
# 月度清理报告

**清理时间**: $(date)
**清理脚本**: monthly_cleanup.sh

## 清理统计

- 归档报告文件: $(find "$MONTH_DIR/reports/" -type f 2>/dev/null | wc -l) 个
- 归档覆盖率文件: $(find "$MONTH_DIR/coverage/" -type f 2>/dev/null | wc -l) 个
- 清理缓存目录: 4 个
- 清理Docker资源: $(docker system df --format "table {{.Type}}\t{{.Count}}\t{{.Size}}" | tail -n +2 | wc -l) 个类型

## 清理后的项目状态

- 根目录文件数: $(find . -maxdepth 1 -type f | wc -l) 个
- 主要目录: src/, tests/, docs/, scripts/, config/, archive/

## 下次清理建议

建议下次清理时间: $(date -d "+1 month" "+%Y-%m-%d")

EOF

echo "✅ 每月深度清理完成！"
echo "📋 清理统计："
echo "   - 归档报告文件: $(find "$MONTH_DIR/reports/" -type f 2>/dev/null | wc -l) 个"
echo "   - 归档覆盖率文件: $(find "$MONTH_DIR/coverage/" -type f 2>/dev/null | wc -l) 个"
echo "   - 清理缓存目录: 4 个"
echo "   - 当前根目录文件数: $(find . -maxdepth 1 -type f | wc -l) 个"
echo "   - 清理报告: $REPORT_FILE"