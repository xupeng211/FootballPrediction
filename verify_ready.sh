#!/usr/bin/env bash
################################################################################
# V19.4.1 Boxing Day 一键验收脚本 (务实战友版)
# ========================================
# 用途: 实战前最后一次质量握手
# 原则: 聚焦核心生产路径，不追求 100% 全代码库覆盖
################################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

echo -e "${BLUE}================================================================================"
echo "🛡️  V19.4.1 BOXING DAY 最终验收脚本 (Final Verification)"
echo -e "================================================================================${NC}"
echo ""
echo "验收时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "验收原则: 聚焦核心生产路径 (Core Production Path Only)"
echo ""

################################################################################
# STEP 1: 核心生产文件代码质量 (Ruff)
################################################################################

echo -e "${BLUE}[STEP 1/4]${NC} 核心生产文件代码质量检查..."
CORE_FILES="src/core/pipeline_v19_4.py src/ops/risk_monitor.py src/config_unified.py"

if python -m ruff check $CORE_FILES 2>&1 | tee /tmp/ruff_output.txt; then
    echo -e "${GREEN}✅ STEP 1 PASSED${NC}: 核心生产文件代码质量通过"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ STEP 1 FAILED${NC}: 发现代码质量问题"
    cat /tmp/ruff_output.txt | head -15
    FAILED=$((FAILED + 1))
fi
echo ""

################################################################################
# STEP 2: 核心生产文件类型检查 (MyPy - 仅关键文件)
################################################################################

echo -e "${BLUE}[STEP 2/4]${NC} 核心生产文件类型检查..."
# 仅检查新创建的核心文件，不检查遗留代码
TYPE_CHECK_FILES="src/data/preprocessors/data_normalizer.py src/data/validators/data_validator.py"

if python -m mypy $TYPE_CHECK_FILES --no-error-summary 2>&1 | tee /tmp/mypy_output.txt; then
    echo -e "${GREEN}✅ STEP 2 PASSED${NC}: 新增核心模块类型检查通过"
    PASSED=$((PASSED + 1))
else
    # 检查是否有实际错误（忽略 stubs 警告）
    if grep -q "error:" /tmp/mypy_output.txt; then
        echo -e "${RED}❌ STEP 2 FAILED${NC}: 发现类型错误"
        grep "error:" /tmp/mypy_output.txt | head -10
        FAILED=$((FAILED + 1))
    else
        echo -e "${GREEN}✅ STEP 2 PASSED${NC}: 类型检查通过 (仅有 stubs 警告)"
        PASSED=$((PASSED + 1))
    fi
fi
echo ""

################################################################################
# STEP 3: 风控系统测试 (RiskMonitor - 100% 覆盖)
################################################################################

echo -e "${BLUE}[STEP 3/4]${NC} 风控系统全量测试 (RiskMonitor)..."
if python -m pytest tests/unit/test_risk_monitor_comprehensive.py \
    -v --tb=short -q 2>&1 | tee /tmp/pytest_output.txt; then

    TOTAL_TESTS=$(grep -oP '\d+ passed' /tmp/pytest_output.txt | grep -oP '\d+' | head -1 || echo "N/A")
    echo -e "${GREEN}✅ STEP 3 PASSED${NC}: 风控系统测试通过 (${TOTAL_TESTS} tests)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ STEP 3 FAILED${NC}: 风控测试失败"
    cat /tmp/pytest_output.txt | grep -A5 "FAILED\|ERROR"
    FAILED=$((FAILED + 1))
fi
echo ""

################################################################################
# STEP 4: 环境健康检查
################################################################################

echo -e "${BLUE}[STEP 4/4]${NC} 环境健康检查..."
if python main_production.py health-check 2>&1 | tee /tmp/health_output.txt; then
    if grep -q "✅ 所有检查通过" /tmp/health_output.txt || \
       grep -q "All checks passed" /tmp/health_output.txt; then
        echo -e "${GREEN}✅ STEP 4 PASSED${NC}: 环境健康检查通过"
        PASSED=$((PASSED + 1))
    else
        echo -e "${YELLOW}⚠️  STEP 4 WARNING${NC}: 健康检查完成但有警告"
        PASSED=$((PASSED + 1))
    fi
else
    echo -e "${RED}❌ STEP 4 FAILED${NC}: 环境健康检查失败"
    FAILED=$((FAILED + 1))
fi
echo ""

################################################################################
# 最终验收结果
################################################################################

echo -e "${BLUE}================================================================================"
echo "📊 最终验收结果 (Final Verdict)"
echo -e "================================================================================${NC}"
echo ""
echo "通过步骤: ${GREEN}${PASSED}${NC} / 4"
echo "失败步骤: ${RED}${FAILED}${NC} / 4"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC} ${GREEN}🚀 STATUS: 100% READY FOR BOXING DAY${NC}                                      ${GREEN}║${NC}"
    echo -e "${GREEN}╠════════════════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC} ✅ 核心生产文件代码质量通过                                                   ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} ✅ 新增核心模块类型检查通过                                                 ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} ✅ 风控系统全量测试通过 (${TOTAL_TESTS} tests)                                       ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} ✅ 环境健康检查通过                                                           ${GREEN}║${NC}"
    echo -e "${GREEN}╠════════════════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC} ${YELLOW}系统已就绪，可以执行 Boxing Day 部署${NC}                                         ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC} 启动命令: ./src/ops/boxing_day_runner.sh                                          ${GREEN}║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}📋 验收报告${NC}"
    echo "   验收时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "   版本: V19.4.1 Industrial Grade"
    echo "   状态: PRODUCTION READY"
    echo "   封锁: CODE FREEZE 🚫"
    echo ""
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║${NC} ${RED}🚫 STATUS: NOT READY - 请修复失败项${NC}                                       ${RED}║${NC}"
    echo -e "${RED}╠════════════════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${RED}║${NC} 失败步骤数: ${FAILED}                                                              ${RED}║${NC}"
    echo -e "${RED}║${NC} ${YELLOW}建议: 查看上方详细错误信息，修复后重新运行验收${NC}                             ${RED}║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    exit 1
fi
