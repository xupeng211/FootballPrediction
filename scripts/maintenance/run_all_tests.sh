#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# ║   TITAN V4.46.8 一键测试运行器                                         ║
# ║   The Runner - Execute All Tests in Sequence                          ║
# ═══════════════════════════════════════════════════════════════════════════════
#
# 执行顺序:
# 1. 单元测试 (Logic check)
# 2. 数据冒烟测试 (Data audit)
# 3. 回归测试 (Performance guard)
#
# @module scripts.maintenance.run_all_tests
# @version V4.46.8
# ═══════════════════════════════════════════════════════════════════════════════

set -e  # 任何命令失败立即退出

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 结果统计
PASS_COUNT=0
FAIL_COUNT=0

print_header() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo -e "  ${BLUE}TITAN V4.46.8 测试运行器${NC}"
    echo "═══════════════════════════════════════════════════════════════════════════════"
    echo ""
}

print_section() {
    echo ""
    echo "───────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${YELLOW}[$1]${NC} $2"
    echo "───────────────────────────────────────────────────────────────────────────────"
}

print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "  ${GREEN}✅ PASS${NC}: $2"
        ((PASS_COUNT++))
    else
        echo -e "  ${RED}❌ FAIL${NC}: $2"
        ((FAIL_COUNT++))
    fi
}

# ============================================================================
# 主程序
# ============================================================================

print_header

# 检查是否在 Docker 容器内
if [ -f /.dockerenv ]; then
    IN_DOCKER=1
    PYTHON="python"
    PYTEST="pytest"
else
    IN_DOCKER=0
    PYTHON="docker-compose -f docker-compose.dev.yml exec -T dev python"
    PYTEST="docker-compose -f docker-compose.dev.yml exec -T dev pytest"
fi

cd "$PROJECT_ROOT"

# ============================================================================
# Phase 1: 单元测试 (Logic Check)
# ============================================================================

print_section "1/3" "单元测试 - 核心逻辑验证"

# 运行核心逻辑测试
echo "  执行: pytest tests/test_core_logic.py tests/integrity/test_edge_cases.py -v --tb=short"
$PYTEST tests/test_core_logic.py tests/integrity/test_edge_cases.py -v --tb=short 2>&1 | tail -20
LOGIC_RESULT=${PIPESTATUS[0]}
print_result $LOGIC_RESULT "核心逻辑测试"

# ============================================================================
# Phase 2: 数据冒烟测试 (Data Audit)
# ============================================================================

print_section "2/3" "数据冒烟测试 - 数据库健康检查"

echo "  执行: python scripts/ops/smoke_test_features.py"
$PYTHON scripts/ops/smoke_test_features.py 2>&1 | tail -15
SMOKE_RESULT=$?
print_result $SMOKE_RESULT "数据冒烟测试"

# ============================================================================
# Phase 3: 回归测试 (Performance Guard)
# ============================================================================

print_section "3/3" "回归测试 - 模型性能守卫"

echo "  执行: python scripts/ops/regression_test.py"
$PYTHON scripts/ops/regression_test.py 2>&1 | tail -15
REGRESSION_RESULT=$?
print_result $REGRESSION_RESULT "回归测试"

# ============================================================================
# 汇总报告
# ============================================================================

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo -e "  ${BLUE}测试汇总报告${NC}"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "  测试项目                    │ 状态"
echo "  ────────────────────────────────────────────────────────────────────────"
echo -e "  核心逻辑测试                │ $( [ $LOGIC_RESULT -eq 0 ] && echo -e "${GREEN}✅ PASS${NC}" || echo -e "${RED}❌ FAIL${NC}" )"
echo -e "  数据冒烟测试                │ $( [ $SMOKE_RESULT -eq 0 ] && echo -e "${GREEN}✅ PASS${NC}" || echo -e "${RED}❌ FAIL${NC}" )"
echo -e "  回归测试                    │ $( [ $REGRESSION_RESULT -eq 0 ] && echo -e "${GREEN}✅ PASS${NC}" || echo -e "${RED}❌ FAIL${NC}" )"
echo ""

TOTAL_RESULT=$((LOGIC_RESULT + SMOKE_RESULT + REGRESSION_RESULT))

if [ $TOTAL_RESULT -eq 0 ]; then
    echo -e "  ${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "  ${GREEN}  🎉 全部测试通过! TITAN 已准备好部署。${NC}"
    echo -e "  ${GREEN}════════════════════════════════════════════════════════════════${NC}"
    exit 0
else
    echo -e "  ${RED}════════════════════════════════════════════════════════════════${NC}"
    echo -e "  ${RED}  ⚠️ 有测试失败! 请检查上述错误并修复。${NC}"
    echo -e "  ${RED}════════════════════════════════════════════════════════════════${NC}"
    exit 1
fi
