#!/bin/bash
###############################################################################
# V36.3 Pre-Morning Report Test - 晨报前全量测试验证
#
# 职责：在运行 morning_report.py 之前，确保没有任何"逻辑漂移"
#
# 准入红线：
# - 禁止在测试未通过的情况下运行晨报
# - 禁止跳过单元测试直接进入生产环境
#
# Author: SRE Team
# Version: V36.3
# Date: 2026-01-12
###############################################################################

set -euo pipefail

# ============================================================================
# 配置
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/pre_morning_report_test.log"

# 时间戳函数
ts() {
    date '+%Y-%m-%d %H:%M:%S'
}

log() {
    echo "[$(ts)] $*" | tee -a "$LOG_FILE"
}

# ============================================================================
# 测试函数
# ============================================================================

run_unit_tests() {
    log "🧪 [Step 1/3] 运行全量单元测试..."

    cd "$PROJECT_ROOT"

    if python -m pytest tests/unit/ -v --tb=short 2>&1 | tee -a "$LOG_FILE"; then
        log "✅ 全量单元测试通过"
        return 0
    else
        log "❌ 全量单元测试失败"
        return 1
    fi
}

check_failed_features() {
    log "📋 [Step 2/3] 检查失败特征记录..."

    local failed_count=$(jq '. | length' logs/failed_features.json 2>/dev/null || echo "0")

    if [ "$failed_count" -gt 0 ]; then
        log "⚠️  发现 $failed_count 条失败记录"
        log "   文件: logs/failed_features.json"
        log "   建议: 运行 python scripts/ops/tdd_guardian.py --once 处理"
        return 0  # 警告但不阻塞
    else
        log "✅ 没有失败记录"
        return 0
    fi
}

run_morning_report() {
    log "🌅 [Step 3/3] 运行晨报..."

    cd "$PROJECT_ROOT"

    if python scripts/ops/morning_report.py 2>&1 | tee -a "$LOG_FILE"; then
        log "✅ 晨报生成成功"
        return 0
    else
        log "❌ 晨报生成失败"
        return 1
    fi
}

# ============================================================================
# 主流程
# ============================================================================

main() {
    log "══════════════════════════════════════════════════════════════════"
    log "🛡️  V36.3 Pre-Morning Report Test"
    log "══════════════════════════════════════════════════════════════════"

    local unit_test_success=0
    local morning_report_success=0

    # Step 1: 运行单元测试
    if run_unit_tests; then
        unit_test_success=1
    else
        log "❌ 单元测试失败，禁止运行晨报"
        log "══════════════════════════════════════════════════════════════════"
        exit 1
    fi

    # Step 2: 检查失败记录
    check_failed_features

    # Step 3: 运行晨报
    if run_morning_report; then
        morning_report_success=1
    fi

    # 总结
    log "══════════════════════════════════════════════════════════════════"
    log "📊 执行总结:"
    log "   单元测试: $([ "$unit_test_success" -eq 1 ] && echo '✅ 通过' || echo '❌ 失败')"
    log "   晨报生成: $([ "$morning_report_success" -eq 1 ] && echo '✅ 成功' || echo '❌ 失败')"
    log "══════════════════════════════════════════════════════════════════"

    if [ "$unit_test_success" -eq 1 ] && [ "$morning_report_success" -eq 1 ]; then
        log "🎉 Pre-Morning Report Test 完成"
        exit 0
    else
        log "⚠️  存在异常，请检查日志"
        exit 1
    fi
}

# 运行主流程
main "$@"
