#!/bin/bash
# ============================================================================
# V171.001 Deployment Verification Script
# ============================================================================
#
# 用途: 一键检查部署环境状态
#
# 检查项:
#   1. Docker 容器状态
#   2. 数据库连接
#   3. 代理池可用性
#   4. Python 桥接器响应
#   5. 核心模块加载
#
# Usage:
#   ./scripts/ops/verify_deployment.sh [--verbose]
#
# Exit codes:
#   0 - All checks passed
#   1 - Some checks failed
#
# ============================================================================

set -e

# ============================================================================
# 配置
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VERBOSE="${1:-}"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 检查结果
PASS=0
FAIL=0
WARN=0

# ============================================================================
# 辅助函数
# ============================================================================

log_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASS++))
}

log_fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAIL++))
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARN++))
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ============================================================================
# 检查函数
# ============================================================================

check_docker() {
    log_section "1. Docker 容器状态"

    # 检查 Docker 是否可用
    if ! command -v docker &> /dev/null; then
        log_fail "Docker 未安装"
        return 1
    fi

    # 检查容器状态
    local containers=("football_prediction_db_dev" "football_prediction_dev" "football_prediction_redis_dev")
    local all_running=true

    for container in "${containers[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            local status=$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
            if [[ "$status" == "healthy" || "$status" == "unknown" ]]; then
                log_pass "$container 运行中"
            else
                log_warn "$container 状态: $status"
            fi
        else
            log_fail "$container 未运行"
            all_running=false
        fi
    done

    if $all_running; then
        return 0
    else
        return 1
    fi
}

check_database() {
    log_section "2. 数据库连接"

    # 检查 PostgreSQL 连接
    if docker exec football_prediction_db_dev pg_isready -U football_user -d football_db &>/dev/null; then
        log_pass "PostgreSQL 连接正常"
    else
        log_fail "PostgreSQL 连接失败"
        return 1
    fi

    # 检查核心表
    local tables=("matches" "predictions" "metrics_multi_source_data" "match_fundamentals")
    local missing_tables=()

    for table in "${tables[@]}"; do
        if docker exec football_prediction_db_dev psql -U football_user -d football_db -c "SELECT 1 FROM $table LIMIT 1" &>/dev/null; then
            log_pass "表 $table 存在"
        else
            missing_tables+=("$table")
            log_warn "表 $table 不存在"
        fi
    done

    # 检查 Redis 连接
    if docker exec football_prediction_redis_dev redis-cli ping &>/dev/null; then
        log_pass "Redis 连接正常"
    else
        log_warn "Redis 连接失败"
    fi

    if [[ ${#missing_tables[@]} -eq 0 ]]; then
        return 0
    else
        return 1
    fi
}

check_proxy_pool() {
    log_section "3. 代理池可用性 (NetworkShield)"

    # 在容器内检查 NetworkShield
    local result=$(docker exec football_prediction_dev node -e "
        const path = require('path');
        try {
            const { getNetworkShield } = require('./src/infrastructure/network/NetworkShield');
            const shield = getNetworkShield();
            const stats = shield.getStats();
            console.log(JSON.stringify({
                totalNodes: stats.totalNodes,
                activeNodes: stats.activeNodes,
                avgHealthScore: stats.avgHealthScore
            }));
        } catch (e) {
            console.log(JSON.stringify({ error: e.message }));
        }
    " 2>&1)

    if echo "$result" | grep -q '"totalNodes"'; then
        local total=$(echo "$result" | node -e "console.log(JSON.parse(require('fs').readFileSync(0)).totalNodes)")
        local active=$(echo "$result" | node -e "console.log(JSON.parse(require('fs').readFileSync(0)).activeNodes)")
        local health=$(echo "$result" | node -e "console.log(JSON.parse(require('fs').readFileSync(0)).avgHealthScore)")

        log_pass "NetworkShield 初始化成功"
        log_info "  总节点: $total"
        log_info "  活跃节点: $active"
        log_info "  平均健康分: $health"

        if [[ "$active" -ge 20 ]]; then
            return 0
        else
            log_warn "代理节点数量不足 (期望 20+)"
            return 1
        fi
    else
        log_fail "NetworkShield 初始化失败: $result"
        return 1
    fi
}

check_python_bridge() {
    log_section "4. Python 桥接器响应"

    # 测试 Python 环境检测
    local result=$(docker exec football_prediction_dev node -e "
        const path = require('path');
        const { PythonBridge } = require('./src/infrastructure/engines/bridge/PythonBridge');

        async function test() {
            const bridge = new PythonBridge({ logLevel: 'error' });
            const result = await bridge.testEnvironment();
            console.log(JSON.stringify(result));
        }
        test().catch(e => console.log(JSON.stringify({ error: e.message })));
    " 2>&1)

    if echo "$result" | grep -q '"success":true'; then
        log_pass "PythonBridge 环境检测通过"

        # 提取依赖信息
        local psycopg2=$(echo "$result" | node -e "console.log(JSON.parse(require('fs').readFileSync(0)).environment.psycopg2)")
        local xgboost=$(echo "$result" | node -e "console.log(JSON.parse(require('fs').readFileSync(0)).environment.xgboost)")
        local pandas=$(echo "$result" | node -e "console.log(JSON.parse(require('fs').readFileSync(0)).environment.pandas)")

        log_info "  psycopg2: $psycopg2"
        log_info "  xgboost: $xgboost"
        log_info "  pandas: $pandas"
        return 0
    else
        log_fail "PythonBridge 测试失败"
        [[ -n "$VERBOSE" ]] && log_info "详细输出: $result"
        return 1
    fi
}

check_modules() {
    log_section "5. 核心模块加载"

    local modules=(
        "QuantHarvester:./src/infrastructure/engines/QuantHarvester"
        "PythonBridge:./src/infrastructure/engines/bridge/PythonBridge"
        "MultiModelValidator:./src/ml/inference/multi_model_validator"
        "GoldenDataMerger:./src/infrastructure/merger/GoldenDataMerger"
    )

    local all_loaded=true

    for module in "${modules[@]}"; do
        local name="${module%%:*}"
        local path="${module#*:}"

        if docker exec football_prediction_dev node -e "require('${path}')" &>/dev/null; then
            log_pass "$name 加载成功"
        else
            log_fail "$name 加载失败"
            all_loaded=false
        fi
    done

    # 检查 Python 模块
    local py_modules=(
        "src.ml.inference.multi_model_validator"
        "src.infrastructure.merger.GoldenDataMerger"
    )

    for module in "${py_modules[@]}"; do
        if docker exec football_prediction_dev python3 -c "import ${module}" &>/dev/null; then
            log_pass "Python $module 加载成功"
        else
            log_warn "Python $module 加载失败"
        fi
    done

    if $all_loaded; then
        return 0
    else
        return 1
    fi
}

check_data_quality() {
    log_section "6. 数据质量检查"

    # 检查比赛数量
    local match_count=$(docker exec football_prediction_db_dev psql -U football_user -d football_db -t -c "SELECT COUNT(*) FROM matches" 2>/dev/null | tr -d ' ')
    log_info "  比赛数量: $match_count"

    # 检查预测数量
    local pred_count=$(docker exec football_prediction_db_dev psql -U football_user -d football_db -t -c "SELECT COUNT(*) FROM predictions" 2>/dev/null | tr -d ' ')
    log_info "  预测数量: $pred_count"

    # 检查赔率数据
    local odds_count=$(docker exec football_prediction_db_dev psql -U football_user -d football_db -t -c "SELECT COUNT(*) FROM metrics_multi_source_data" 2>/dev/null | tr -d ' ')
    log_info "  赔率记录: $odds_count"

    if [[ "$match_count" -gt 0 ]]; then
        log_pass "数据质量检查通过"
        return 0
    else
        log_warn "数据库为空，请先执行数据采集"
        return 1
    fi
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║     V171.001 Deployment Verification Script                  ║"
    echo "║     Production-Ready Quality Audit                           ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""

    cd "$PROJECT_ROOT"

    # 执行检查
    check_docker
    check_database
    check_proxy_pool
    check_python_bridge
    check_modules
    check_data_quality

    # 汇总结果
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                    VERIFICATION SUMMARY                      ║"
    echo "╠═══════════════════════════════════════════════════════════════╣"
    printf "║  %-20s: ${GREEN}%d${NC}                                  ║\n" "Passed" "$PASS"
    printf "║  %-20s: ${RED}%d${NC}                                  ║\n" "Failed" "$FAIL"
    printf "║  %-20s: ${YELLOW}%d${NC}                                  ║\n" "Warnings" "$WARN"
    echo "╚═══════════════════════════════════════════════════════════════╝"

    if [[ "$FAIL" -eq 0 ]]; then
        echo ""
        echo -e "${GREEN}✅ V171.001 部署验证通过！系统已就绪。${NC}"
        echo ""
        echo "下一步操作:"
        echo "  1. 运行收割: node scripts/ops/v171_real_fire.js"
        echo "  2. 查看预测: python scripts/ops/check_daily_bets.py"
        echo ""
        exit 0
    else
        echo ""
        echo -e "${RED}❌ 部署验证失败，请检查上述错误。${NC}"
        echo ""
        exit 1
    fi
}

main
