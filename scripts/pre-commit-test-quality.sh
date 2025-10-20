#!/bin/bash
# 预提交测试质量检查脚本
# Pre-commit test quality check script

# 设置颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 运行预提交测试质量检查..."
echo "=================================="

# 1. 检查是否有Python文件需要检查
echo -e "\n${YELLOW}步骤 1/6${NC} 检查待提交的文件..."
PYTHON_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' | grep -E '^tests/')

if [ -z "$PYTHON_FILES" ]; then
    echo -e "${GREEN}✅ 没有测试文件需要检查${NC}"
else
    echo "发现以下测试文件："
    echo "$PYTHON_FILES"
fi

# 2. 运行测试质量检查
echo -e "\n${YELLOW}步骤 2/6${NC} 运行测试质量检查..."
QUALITY_CHECK=$(python scripts/check_test_quality.py tests/ 2>&1)
QUALITY_SCORE=$(echo "$QUALITY_CHECK" | grep "总分:" | sed 's/.*总分: \([0-9]*\)\/100.*/\1/')

if [ -z "$QUALITY_SCORE" ]; then
    QUALITY_SCORE=0
fi

if [ "$QUALITY_SCORE" -lt 70 ]; then
    echo -e "${RED}❌ 测试质量评分过低 ($QUALITY_SCORE/100)${NC}"
    echo "请修复问题后重试"
    echo ""
    echo "详细问题："
    echo "$QUALITY_CHECK" | grep -A 20 "发现的问题"
    exit 1
else
    echo -e "${GREEN}✅ 测试质量评分: $QUALITY_SCORE/100${NC}"
fi

# 3. 检查新测试是否使用模板
echo -e "\n${YELLOW}步骤 3/6${NC} 检查新测试使用模板..."
if [ -n "$PYTHON_FILES" ]; then
    echo "检查新测试是否遵循模板规范..."

    # 检查命名规范
    for file in $PYTHON_FILES; do
        # 检查是否包含必要的导入
        if ! grep -q "from unittest.mock import" "$file" && grep -q "@patch\|Mock\|AsyncMock" "$file"; then
            echo -e "${YELLOW}⚠️  $file: 可能使用了Mock但未导入${NC}"
        fi

        # 检查是否有docstring
        FUNCTION_COUNT=$(grep -c "def test_" "$file" || echo 0)
        DOCSTRING_COUNT=$(grep -c '"""' "$file" || echo 0)

        if [ "$FUNCTION_COUNT" -gt 0 ] && [ "$DOCSTRING_COUNT" -lt "$FUNCTION_COUNT" ]; then
            echo -e "${YELLOW}⚠️  $file: 部分测试缺少文档字符串${NC}"
        fi
    done
else
    echo -e "${GREEN}✅ 没有新测试文件需要检查${NC}"
fi

# 4. 快速语法检查
echo -e "\n${YELLOW}步骤 4/6${NC} 语法检查..."
if [ -n "$PYTHON_FILES" ]; then
    SYNTAX_ERRORS=0
    for file in $PYTHON_FILES; do
        if ! python -m py_compile "$file" 2>/dev/null; then
            echo -e "${RED}❌ $file: 语法错误${NC}"
            SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
        fi
    done

    if [ "$SYNTAX_ERRORS" -gt 0 ]; then
        echo -e "${RED}发现 $SYNTAX_ERRORS 个语法错误${NC}"
        exit 1
    else
        echo -e "${GREEN}✅ 所有文件语法正确${NC}"
    fi
else
    echo -e "${GREEN}✅ 没有文件需要语法检查${NC}"
fi

# 5. 运行快速测试（如果可能）
echo -e "\n${YELLOW}步骤 5/6${NC} 运行快速测试..."
if command -v pytest &> /dev/null; then
    # 只运行新修改的测试文件
    QUICK_TESTS=""
    for file in $PYTHON_FILES; do
        # 转换路径格式
        TEST_PATH=$(echo "$file" | sed 's/^tests\///' | sed 's/\.py$//')
        if [ -n "$QUICK_TESTS" ]; then
            QUICK_TESTS="$QUICK_TESTS or $TEST_PATH"
        else
            QUICK_TESTS="$TEST_PATH"
        fi
    done

    if [ -n "$QUICK_TESTS" ]; then
        echo "运行新测试: $QUICK_TESTS"
        if pytest -k "$QUICK_TESTS" --tb=short -x --disable-warnings -q; then
            echo -e "${GREEN}✅ 快速测试通过${NC}"
        else
            echo -e "${RED}❌ 快速测试失败${NC}"
            echo "请修复测试后重试"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  跳过快速测试（没有匹配的测试）${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  pytest未安装，跳过快速测试${NC}"
fi

# 6. 生成简要报告
echo -e "\n${YELLOW}步骤 6/6${NC} 生成报告..."
REPORT_FILE=".test_quality_report.txt"
cat > "$REPORT_FILE" << EOF
测试质量检查报告
==================
检查时间: $(date)
质量评分: $QUALITY_SCORE/100
检查文件数: $(echo "$PYTHON_FILES" | wc -l | xargs)
状态: 通过

建议：
1. 保持测试质量评分在70分以上
2. 新测试请使用提供的模板
3. 定期运行完整检查: python scripts/check_test_quality.py
EOF

echo -e "${GREEN}✅ 报告已生成: $REPORT_FILE${NC}"

# 完成
echo -e "\n${GREEN}=================================="
echo "🎉 预提交检查完成！${NC}"
echo -e "${GREEN}质量评分: $QUALITY_SCORE/100${NC}"
echo "您可以安全地提交代码了。"

# 可选：如果质量评分很高，可以显示额外信息
if [ "$QUALITY_SCORE" -ge 90 ]; then
    echo -e "\n${GREEN}🏆 太棒了！您的测试质量很高。${NC}"
elif [ "$QUALITY_SCORE" -ge 80 ]; then
    echo -e "\n${YELLOW}👍 做得好！测试质量良好。${NC}"
fi

exit 0
