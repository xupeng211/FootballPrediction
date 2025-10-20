#!/bin/bash
# 批量修复跳过测试的脚本

echo "🔧 开始批量修复跳过测试..."

# 找出所有包含pytest.skip的文件
find tests/unit -name "*.py" -exec grep -l "pytest.skip" {} \; > skipped_files.txt

# 统计
TOTAL=$(wc -l < skipped_files.txt)
echo "找到 $TOTAL 个包含pytest.skip的文件"

# 修复每个文件
FIXED=0
while read -r file; do
    if python scripts/fix_skipped_tests.py --single "$file"; then
        echo "✅ 修复: $file"
        ((FIXED++))
    else
        echo "❌ 跳过: $file"
    fi
done < skipped_files.txt

echo ""
echo "✨ 修复完成！"
echo "修复了 $FIXED/$TOTAL 个文件"

# 清理
rm -f skipped_files.txt

# 运行测试验证
echo ""
echo "🧪 运行测试验证..."
python -m pytest tests/unit -x --tb=no -q | head -20
