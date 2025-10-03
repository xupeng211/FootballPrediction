#!/bin/bash
# 单元测试执行脚本
# 独立运行，不依赖外部服务

set -e

# 激活虚拟环境
source .venv/bin/activate

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
COVERAGE_THRESHOLD=80
COVERAGE_FILE="coverage.json"
HTML_COVERAGE_DIR="htmlcov"
REPORT_DIR="docs/_reports"

echo -e "${BLUE}🔬 单元测试执行器${NC}"
echo -e "${YELLOW}====================${NC}"

# 创建报告目录
mkdir -p $REPORT_DIR

# 记录开始时间
START_TIME=$(date +%s)

echo -e "${BLUE}📋 运行参数:${NC}"
echo -e "  覆盖率阈值: ${COVERAGE_THRESHOLD}%"
echo -e "  测试路径: tests/unit/"
echo -e "  输出格式: JSON + Terminal"

# 清理旧的覆盖率数据
rm -f $COVERAGE_FILE
rm -rf $HTML_COVERAGE_DIR

echo -e "\n${YELLOW}🚀 开始执行单元测试...${NC}"

# 运行单元测试并生成覆盖率报告
if pytest tests/unit/ \
    -v \
    --tb=short \
    --maxfail=10 \
    --timeout=120 \
    --disable-warnings \
    --cov=src \
    --cov-report=json:$COVERAGE_FILE \
    --cov-report=term-missing \
    --cov-report=html:$HTML_COVERAGE_DIR \
    --cov-fail-under=$COVERAGE_THRESHOLD \
    --junit-xml=$REPORT_DIR/unit-tests.xml; then

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo -e "\n${GREEN}✅ 单元测试通过！${NC}"
    echo -e "⏱️  执行时间: ${DURATION}秒"

    # 解析覆盖率
    if [ -f "$COVERAGE_FILE" ]; then
        COVERAGE=$(python -c "import json; print(json.load(open('$COVERAGE_FILE')).get('totals', {}).get('percent_covered', 0))")
        echo -e "📊 覆盖率: ${COVERAGE}%"

        # 生成覆盖率徽章
        COVERAGE_INT=$(echo "$COVERAGE" | cut -d. -f1)
        if [ $COVERAGE_INT -ge 80 ]; then
            BADGE_COLOR="brightgreen"
        elif [ $COVERAGE_INT -ge 60 ]; then
            BADGE_COLOR="yellow"
        else
            BADGE_COLOR="red"
        fi

        echo -e "📈 HTML报告: file://$(pwd)/$HTML_COVERAGE_DIR/index.html"
    fi

    # 生成简要报告
    REPORT_FILE="$REPORT_DIR/unit_test_report_$(date +%Y%m%d_%H%M%S).md"
    cat > $REPORT_FILE << EOF
# 单元测试报告

## 执行结果
- **状态**: ✅ 通过
- **时间**: $(date)
- **执行时长**: ${DURATION}秒
- **覆盖率**: ${COVERAGE}%
- **阈值**: ${COVERAGE_THRESHOLD}%

## 测试统计
$(pytest tests/unit/ --collect-only -q | tail -n 1)

## 覆盖率详情
- HTML报告: [查看详情]($HTML_COVERAGE_DIR/index.html)
- JSON数据: [原始数据]($COVERAGE_FILE)

---
Generated at $(date)
EOF

    echo -e "\n📄 报告已生成: $REPORT_FILE"

else
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo -e "\n${RED}❌ 单元测试失败！${NC}"
    echo -e "⏱️  执行时间: ${DURATION}秒"

    # 即使失败也生成报告
    if [ -f "$COVERAGE_FILE" ]; then
        COVERAGE=$(python -c "import json; print(json.load(open('$COVERAGE_FILE')).get('totals', {}).get('percent_covered', 0))")
        echo -e "📊 覆盖率: ${COVERAGE}% (低于阈值 $COVERAGE_THRESHOLD%)"
    fi

    # 生成失败报告
    REPORT_FILE="$REPORT_DIR/unit_test_failure_$(date +%Y%m%d_%H%M%S).md"
    cat > $REPORT_FILE << EOF
# 单元测试失败报告

## 执行结果
- **状态**: ❌ 失败
- **时间**: $(date)
- **执行时长**: ${DURATION}秒
- **覆盖率**: ${COVERAGE:-未生成}%
- **阈值**: ${COVERAGE_THRESHOLD}%

## 失败原因
运行 \`pytest tests/unit/\` 失败，请检查测试日志。

## 建议修复
1. 检查失败的测试用例
2. 查看错误日志
3. 修复代码或更新测试

---
Generated at $(date)
EOF

    echo -e "\n📄 失败报告已生成: $REPORT_FILE"

    exit 1
fi

echo -e "\n${GREEN}🎉 单元测试执行完成！${NC}"