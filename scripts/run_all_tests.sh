#!/usr/bin/env bash
# V37.1 自动化质量门禁脚本
# ==========================
# 用途: 一键运行 L1/L2 采集器的所有测试并输出质量审计分数
#
# 执行: bash scripts/run_all_tests.sh
#
# 作者: ML Architect
# 日期: 2025-12-29
# Phase: Production-Grade
# Version: V37.1

set -euo pipefail

# ============================================
# 颜色定义
# ============================================
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly BOLD='\033[1m'
readonly RESET='\033[0m'

# ============================================
# 配置
# ============================================
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
readonly TESTS_DIR="$PROJECT_ROOT/tests"
readonly REPORTS_DIR="$PROJECT_ROOT/test_reports"

# 创建报告目录
mkdir -p "$REPORTS_DIR"

# ============================================
# 日志函数
# ============================================
log_header() {
    echo -e "\n${BLUE}${BOLD}═══════════════════════════════════════════════════════${RESET}"
    echo -e "${BLUE}${BOLD}  $1${RESET}"
    echo -e "${BLUE}${BOLD}═══════════════════════════════════════════════════════${RESET}\n"
}

log_success() { echo -e "${GREEN}✅ $1${RESET}"; }
log_error() { echo -e "${RED}❌ $1${RESET}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${RESET}"; }
log_info() { echo -e "ℹ️  $1${RESET}"; }

# ============================================
# 测试计数器
# ============================================
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# ============================================
# 1. 环境检查
# ============================================
check_environment() {
    log_header "环境检查"

    local env_ok=true

    # 检查 Python 版本
    if command -v python3 &> /dev/null; then
        local py_version=$(python3 --version | awk '{print $2}')
        local major=$(echo $py_version | cut -d. -f1)
        local minor=$(echo $py_version | cut -d. -f2)

        if [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; then
            log_success "Python 版本: $py_version"
        else
            log_error "Python 版本过低: $py_version (需要 >= 3.11)"
            env_ok=false
        fi
    else
        log_error "未找到 Python3"
        env_ok=false
    fi

    # 检查 pytest
    if command -v pytest &> /dev/null; then
        log_success "pytest 已安装"
    else
        log_error "pytest 未安装"
        env_ok=false
    fi

    # 检查虚拟环境
    if [[ "${VIRTUAL_ENV:-}" != "" ]]; then
        log_success "虚拟环境已激活: $VIRTUAL_ENV"
    else
        log_warning "虚拟环境未激活"
    fi

    # 检查 .env 文件
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        log_success ".env 文件存在"
    else
        log_warning ".env 文件不存在（数据库测试可能失败）"
    fi

    if [[ "$env_ok" == false ]]; then
        log_error "环境检查失败，退出"
        exit 1
    fi
}

# ============================================
# 2. 代码质量检查
# ============================================
run_code_quality() {
    log_header "代码质量检查 (L1/L2 采集器)" >&2

    local quality_score=0

    # Ruff 格式检查（仅检查采集器核心文件）
    if command -v ruff &> /dev/null; then
        log_info "运行 Ruff 格式检查 (L1/L2 采集器)..." >&2
        local collector_files=(
            "$PROJECT_ROOT/src/api/collectors/production_l1_collector.py"
            "$PROJECT_ROOT/src/api/collectors/production_l2_collector.py"
            "$PROJECT_ROOT/src/api/collectors/schemas/l1_match_schema.py"
            "$PROJECT_ROOT/src/api/collectors/schemas/l2_match_schema.py"
            "$PROJECT_ROOT/src/api/collectors/resilience.py"
        )

        if ruff check "${collector_files[@]}" --output-format=concise > "$REPORTS_DIR/ruff_report.txt" 2>&1; then
            log_success "Ruff 检查通过 (采集器)" >&2
            ((quality_score+=30))
        else
            log_error "Ruff 检查失败" >&2
            cat "$REPORTS_DIR/ruff_report.txt" >&2
        fi
    else
        log_warning "ruff 未安装，跳过格式检查" >&2
    fi

    echo "$quality_score"
}

# ============================================
# 3. 运行单元测试
# ============================================
run_unit_tests() {
    log_header "单元测试 - L1/L2 采集器"

    local test_files=(
        "$TESTS_DIR/api/collectors/test_production_l1_collector.py"
        "$TESTS_DIR/api/collectors/test_production_l2_collector.py"
        "$TESTS_DIR/api/collectors/schemas/test_l1_match_schema.py"
        "$TESTS_DIR/api/collectors/schemas/test_l2_match_schema.py"
    )

    local total=0
    local passed=0
    local failed=0

    for test_file in "${test_files[@]}"; do
        if [[ ! -f "$test_file" ]]; then
            log_warning "测试文件不存在: $test_file"
            continue
        fi

        log_info "运行: $(basename "$test_file")"

        # 运行测试并解析输出
        local output
        output=$(pytest "$test_file" -v --tb=short 2>&1)
        local exit_code=$?

        echo "$output" >> "$REPORTS_DIR/unit_tests.log"

        if [[ $exit_code -eq 0 ]]; then
            log_success "$(basename "$test_file") 通过"
            ((passed++))
        else
            log_error "$(basename "$test_file") 失败"
            ((failed++))
        fi
        ((total++))
    done

    echo "$passed,$failed,$total"
}

# ============================================
# 4. 运行集成测试
# ============================================
run_integration_tests() {
    log_header "集成测试 - 数据库交互"

    local test_files=(
        "$TESTS_DIR/integration/api/collectors/test_l2_batch_upsert.py"
    )

    local total=0
    local passed=0
    local failed=0

    for test_file in "${test_files[@]}"; do
        if [[ ! -f "$test_file" ]]; then
            log_warning "集成测试文件不存在: $test_file"
            continue
        fi

        log_info "运行: $(basename "$test_file")"

        local output
        output=$(pytest "$test_file" -v --tb=short 2>&1)
        local exit_code=$?

        echo "$output" >> "$REPORTS_DIR/integration_tests.log"

        if [[ $exit_code -eq 0 ]]; then
            log_success "$(basename "$test_file") 通过"
            ((passed++))
        else
            log_error "$(basename "$test_file") 失败"
            ((failed++))
        fi
        ((total++))
    done

    echo "$passed,$failed,$total"
}

# ============================================
# 5. 测试覆盖率分析
# ============================================
run_coverage_analysis() {
    log_header "测试覆盖率分析 (L1/L2 采集器)" >&2

    local coverage_file="$REPORTS_DIR/coverage.xml"

    if pytest "$TESTS_DIR/api/collectors/test_l1_collector.py" "$TESTS_DIR/api/collectors/test_production_l2_collector.py" \
        --cov=src/api/collectors/production_l1_collector \
        --cov=src/api/collectors/production_l2_collector \
        --cov=src/api/collectors/schemas/l1_match_schema \
        --cov=src/api/collectors/schemas/l2_match_schema \
        --cov=src/api/collectors/resilience \
        --cov-report=xml:"$coverage_file" \
        --cov-report=term-missing \
        --quiet; then

        # 提取覆盖率百分比
        if [[ -f "$coverage_file" ]]; then
            local coverage=$(grep -oP 'line-rate="\K[0-9.]+' "$coverage_file")
            local percentage=$(echo "$coverage * 100" | bc)
            log_success "测试覆盖率: ${percentage}%" >&2

            # 评分 (满分 20 分)
            local score=$(echo "$percentage / 5" | bc)
            echo "${score%%.*}"
        else
            log_warning "无法生成覆盖率报告" >&2
            echo "0"
        fi
    else
        log_error "覆盖率分析失败" >&2
        echo "0"
    fi
}

# ============================================
# 6. Pydantic Schema 兼容性测试
# ============================================
run_pydantic_compatibility() {
    log_header "Pydantic Schema 兼容性测试"

    local test_script="$PROJECT_ROOT/scripts/pre_harvest_final_check.py"

    if [[ -f "$test_script" ]]; then
        if python3 "$test_script" > "$REPORTS_DIR/pydantic_check.log" 2>&1; then
            log_success "Pydantic 兼容性检查通过"
            echo "10"
        else
            log_error "Pydantic 兼容性检查失败"
            cat "$REPORTS_DIR/pydantic_check.log"
            echo "0"
        fi
    else
        log_warning "预检脚本不存在: $test_script"
        echo "0"
    fi
}

# ============================================
# 7. 生成质量审计报告
# ============================================
generate_quality_report() {
    local quality_score=$1
    local unit_passed=$2
    local unit_failed=$3
    local int_passed=$4
    local int_failed=$5
    local coverage_score=$6
    local pydantic_score=$7

    # 计算总分 (100 分制)
    # 代码质量: 30分 | 覆盖率: 20分 | Pydantic: 10分 | 测试通过: 40分
    local test_score=0
    local total_tests=$((unit_passed + unit_failed + int_passed + int_failed))
    if [[ $total_tests -gt 0 ]]; then
        test_score=$(( (unit_passed + int_passed) * 40 / total_tests ))
    fi
    local total_score=$((quality_score + coverage_score + pydantic_score + test_score))

    log_header "质量审计报告"

    echo -e "\n╔════════════════════════════════════════════════════════════╗"
    echo -e "║     V37.1 采集器质量审计报告                                ║"
    echo -e "╚════════════════════════════════════════════════════════════╝"

    echo -e "\n📊 测试结果:"
    echo -e "   单元测试: ${GREEN}$unit_passed 通过${RESET} / ${YELLOW}$unit_failed 失败${RESET}"
    echo -e "   集成测试: ${GREEN}$int_passed 通过${RESET} / ${YELLOW}$int_failed 失败${RESET}"

    echo -e "\n🎯 质量评分 (100 分制):"
    echo -e "   代码质量: $quality_score/30"
    echo -e "   测试覆盖率: $coverage_score/20"
    echo -e "   Pydantic 兼容性: $pydantic_score/10"
    echo -e "   测试通过率: $test_score/40"
    echo -e "   ─────────────────"
    echo -e "   ${BOLD}总分: $total_score/100${RESET}"

    # 质量等级
    local grade=""
    local color=""

    if [[ $total_score -ge 90 ]]; then
        grade="A+ (优秀)"
        color=$GREEN
    elif [[ $total_score -ge 80 ]]; then
        grade="A (良好)"
        color=$GREEN
    elif [[ $total_score -ge 70 ]]; then
        grade="B (合格)"
        color=$YELLOW
    elif [[ $total_score -ge 60 ]]; then
        grade="C (需改进)"
        color=$YELLOW
    else
        grade="D (不合格)"
        color=$RED
    fi

    echo -e "\n${color}${BOLD}质量等级: $grade${RESET}"

    # 保存报告
    local report_file="$REPORTS_DIR/quality_audit_$(date +%Y%m%d_%H%M%S).txt"
    {
        echo "V37.3 采集器质量审计报告"
        echo "生成时间: $(date)"
        echo ""
        echo "测试结果:"
        echo "  单元测试: $unit_passed 通过 / $unit_failed 失败"
        echo "  集成测试: $int_passed 通过 / $int_failed 失败"
        echo ""
        echo "质量评分 (100 分制):"
        echo "  代码质量: $quality_score/30"
        echo "  测试覆盖率: $coverage_score/20"
        echo "  Pydantic 兼容性: $pydantic_score/10"
        echo "  测试通过率: $test_score/40"
        echo "  总分: $total_score/100"
        echo ""
        echo "质量等级: $grade"
    } > "$report_file"

    echo -e "\n📝 详细报告已保存至: $report_file"

    # 返回是否通过 (>= 70 分)
    if [[ $total_score -ge 70 ]]; then
        return 0
    else
        return 1
    fi
}

# ============================================
# 主流程
# ============================================
main() {
    log_header "V37.1 采集器自动化质量门禁"
    echo -e "执行时间: $(date)"
    echo -e "项目路径: $PROJECT_ROOT\n"

    # 1. 环境检查
    check_environment

    # 2. 代码质量检查
    local quality_score=$(run_code_quality)

    # 3. 单元测试
    local unit_result=$(run_unit_tests)
    IFS=',' read -r unit_passed unit_failed unit_total <<< "$unit_result"

    # 4. 集成测试
    local int_result=$(run_integration_tests)
    IFS=',' read -r int_passed int_failed int_total <<< "$int_result"

    # 5. 覆盖率分析
    local coverage_score=$(run_coverage_analysis)

    # 6. Pydantic 兼容性
    local pydantic_score=$(run_pydantic_compatibility)

    # 7. 生成报告
    if generate_quality_report \
        "$quality_score" \
        "$unit_passed" "$unit_failed" \
        "$int_passed" "$int_failed" \
        "$coverage_score" \
        "$pydantic_score"; then

        log_success "质量门禁通过"
        exit 0
    else
        log_error "质量门禁失败"
        exit 1
    fi
}

# 执行主流程
main
