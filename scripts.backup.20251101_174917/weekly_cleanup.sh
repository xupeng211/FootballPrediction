#!/bin/bash
# 每周清理脚本
# 使用方法: ./scripts/weekly_cleanup.sh

set -e

echo "🧹 开始每周项目清理..."

# 1. 创建本周归档目录
WEEK_DIR="archive/$(date +%Y-%W)"
mkdir -p "$WEEK_DIR"/{reports,coverage,temp}

# 2. 移动本周临时报告
echo "📝 归档本周临时报告..."
find . -maxdepth 1 -name "*_REPORT.md" -mtime -7 -exec mv {} "$WEEK_DIR/reports/" \; 2>/dev/null || true
find . -maxdepth 1 -name "*_SUMMARY.md" -mtime -7 -exec mv {} "$WEEK_DIR/reports/" \; 2>/dev/null || true
find . -maxdepth 1 -name "*_ANALYSIS.md" -mtime -7 -exec mv {} "$WEEK_DIR/reports/" \; 2>/dev/null || true

# 3. 移动覆盖率数据
echo "📊 归档本周覆盖率数据..."
find . -maxdepth 1 -name "coverage*.json" -mtime -7 -exec mv {} "$WEEK_DIR/coverage/" \; 2>/dev/null || true
find . -maxdepth 1 -name "coverage*.xml" -mtime -7 -exec mv {} "$WEEK_DIR/coverage/" \; 2>/dev/null || true
find . -maxdepth 1 -name ".coverage" -mtime -7 -exec mv {} "$WEEK_DIR/coverage/" \; 2>/dev/null || true

# 4. 清理缓存
echo "🗄️ 清理缓存目录..."
rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/ .cache/ 2>/dev/null || true

# 5. 删除临时文件
echo "🗑️ 删除临时文件..."
find . -maxdepth 1 -name "*_temp*" -mtime -7 -delete 2>/dev/null || true
find . -maxdepth 1 -name "*_backup*" -mtime -7 -delete 2>/dev/null || true
find . -maxdepth 1 -name "*.log" -mtime -7 -delete 2>/dev/null || true
find . -maxdepth 1 -name "improvement-report-*.md" -mtime -7 -delete 2>/dev/null || true

# 6. 整理临时Python脚本
echo "🐍 整理Python脚本..."
mkdir -p scripts/temp/
find . -maxdepth 1 -name "add_*.py" -exec mv {} scripts/temp/ \; 2>/dev/null || true
find . -maxdepth 1 -name "fix_*.py" -exec mv {} scripts/temp/ \; 2>/dev/null || true
find . -maxdepth 1 -name "optimize_*.py" -exec mv {} scripts/temp/ \; 2>/dev/null || true

# 7. 统计清理结果
echo "✅ 每周清理完成！"
echo "📋 清理统计："
echo "   - 归档报告文件: $(find "$WEEK_DIR/reports/" -type f 2>/dev/null | wc -l) 个"
echo "   - 归档覆盖率文件: $(find "$WEEK_DIR/coverage/" -type f 2>/dev/null | wc -l) 个"
echo "   - 清理缓存目录: 4 个"
echo "   - 当前根目录文件数: $(find . -maxdepth 1 -type f | wc -l) 个"