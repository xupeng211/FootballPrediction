#!/bin/bash

# API性能测试运行脚本
# Football Prediction Project

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 配置
API_BASE_URL=${API_BASE_URL:-http://localhost:8000}
TEST_DURATION=${TEST_DURATION:-300}  # 5分钟
USERS=${USERS:-100}
SPAWN_RATE=${SPAWN_RATE:-10}
REPORT_DIR="reports/performance"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建报告目录
create_report_dir() {
    log_step "创建报告目录..."
    mkdir -p "$REPORT_DIR"
    mkdir -p "$REPORT_DIR/$TIMESTAMP"
}

# 检查依赖
check_dependencies() {
    log_step "检查依赖..."

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3未安装"
        exit 1
    fi

    # 检查Locust
    if ! python3 -c "import locust" 2>/dev/null; then
        log_warn "Locust未安装，正在安装..."
        pip3 install locust
    fi

    # 检查应用是否运行
    if ! curl -s "$API_BASE_URL/api/health" > /dev/null; then
        log_error "API服务未运行，请先启动应用"
        exit 1
    fi

    log_info "依赖检查通过"
}

# 运行基础性能测试
run_basic_test() {
    log_step "运行基础性能测试..."

    log_info "测试配置: $USERS 用户, $TEST_DURATION 秒"

    # 运行locust测试
    locust \
        -f tests/performance/load_test.py \
        --host="$API_BASE_URL" \
        --users="$USERS" \
        --spawn-rate="$SPAWN_RATE" \
        --run-time="${TEST_DURATION}s" \
        --headless \
        --html="$REPORT_DIR/$TIMESTAMP/basic_test.html" \
        --csv="$REPORT_DIR/$TIMESTAMP/basic_test" \
        --logfile="$REPORT_DIR/$TIMESTAMP/basic_test.log"

    log_info "基础性能测试完成"
}

# 运行压力测试
run_stress_test() {
    log_step "运行压力测试..."

    # 逐步增加用户数
    for user_count in 50 100 200 300 500; do
        log_info "压力测试: $user_count 用户"

        locust \
            -f tests/performance/load_test.py \
            --host="$API_BASE_URL" \
            --users="$user_count" \
            --spawn-rate=20 \
            --run-time=60s \
            --headless \
            --html="$REPORT_DIR/$TIMESTAMP/stress_test_${user_count}u.html" \
            --csv="$REPORT_DIR/$TIMESTAMP/stress_test_${user_count}u" \
            --logfile="$REPORT_DIR/$TIMESTAMP/stress_test_${user_count}u.log"

        # 等待系统恢复
        sleep 30
    done

    log_info "压力测试完成"
}

# 运行峰值测试
run_peak_test() {
    log_step "运行峰值测试..."

    # 突发大量用户
    locust \
        -f tests/performance/load_test.py \
        --host="$API_BASE_URL" \
        --users=1000 \
        --spawn-rate=100 \
        --run-time=120s \
        --headless \
        --html="$REPORT_DIR/$TIMESTAMP/peak_test.html" \
        --csv="$REPORT_DIR/$TIMESTAMP/peak_test" \
        --logfile="$REPORT_DIR/$TIMESTAMP/peak_test.log"

    log_info "峰值测试完成"
}

# 运行耐力测试
run_endurance_test() {
    log_step "运行耐力测试（长期运行）..."

    # 长期运行测试
    locust \
        -f tests/performance/load_test.py \
        --host="$API_BASE_URL" \
        --users=50 \
        --spawn-rate=5 \
        --run-time=3600s \
        --headless \
        --html="$REPORT_DIR/$TIMESTAMP/endurance_test.html" \
        --csv="$REPORT_DIR/$TIMESTAMP/endurance_test" \
        --logfile="$REPORT_DIR/$TIMESTAMP/endurance_test.log"

    log_info "耐力测试完成"
}

# 运行单端点测试
run_endpoint_tests() {
    log_step "运行单端点性能测试..."

    endpoints=(
        "health:/api/health"
        "matches:/api/matches"
        "predictions:/api/predictions"
        "teams:/api/teams"
        "statistics:/api/statistics"
    )

    for endpoint in "${endpoints[@]}"; do
        name=$(echo "$endpoint" | cut -d: -f1)
        path=$(echo "$endpoint" | cut -d: -f2)

        log_info "测试端点: $name ($path)"

        # 创建简单的测试文件
        cat > "tests/performance/test_${name}.py" <<EOF
from locust import HttpUser, task, between

class ${name^}Test(HttpUser):
    wait_time = between(0.5, 1.5)

    @task
    def test_${name}(self):
        self.client.get("$path")
EOF

        # 运行测试
        locust \
            -f "tests/performance/test_${name}.py" \
            --host="$API_BASE_URL" \
            --users=20 \
            --spawn-rate=5 \
            --run-time=60s \
            --headless \
            --html="$REPORT_DIR/$TIMESTAMP/endpoint_${name}.html" \
            --csv="$REPORT_DIR/$TIMESTAMP/endpoint_${name}"

        # 清理测试文件
        rm -f "tests/performance/test_${name}.py"
    done

    log_info "单端点测试完成"
}

# 运行并发测试
run_concurrent_test() {
    log_step "运行并发测试..."

    # 使用ab (Apache Bench) 进行并发测试
    if command -v ab &> /dev/null; then
        log_info "使用Apache Bench进行并发测试..."

        # 测试首页
        ab -n 1000 -c 50 -g "$REPORT_DIR/$TIMESTAMP/concurrent_home.gnuplot" \
            "$API_BASE_URL/api/health" > "$REPORT_DIR/$TIMESTAMP/ab_results.txt"

        # 测试比赛列表
        ab -n 1000 -c 50 -g "$REPORT_DIR/$TIMESTAMP/concurrent_matches.gnuplot" \
            "$API_BASE_URL/api/matches" >> "$REPORT_DIR/$TIMESTAMP/ab_results.txt"

        log_info "Apache Bench测试完成"
    else
        log_warn "Apache Bench未安装，跳过并发测试"
    fi

    # 使用wrk进行测试（如果可用）
    if command -v wrk &> /dev/null; then
        log_info "使用wrk进行并发测试..."

        wrk -t12 -c400 -d30s --latency \
            -s "tests/performance/wrk_script.lua" \
            "$API_BASE_URL" > "$REPORT_DIR/$TIMESTAMP/wrk_results.txt"

        log_info "wrk测试完成"
    fi
}

# 生成综合报告
generate_report() {
    log_step "生成综合性能报告..."

    cat > "$REPORT_DIR/$TIMESTAMP/performance_report.md" <<EOF
# API性能测试报告

## 测试概览

- **测试时间**: $(date)
- **API地址**: $API_BASE_URL
- **测试配置**:
  - 最大用户数: $USERS
  - 孵化率: $SPAWN_RATE 用户/秒
  - 测试时长: $TEST_DURATION 秒

## 测试类型

1. **基础性能测试**: 模拟正常用户负载
2. **压力测试**: 逐步增加负载至极限
3. **峰值测试**: 突发高负载测试
4. **耐力测试**: 长期稳定性测试
5. **端点测试**: 各API端点性能分析
6. **并发测试**: 高并发请求测试

## 测试结果

### 基础性能指标

EOF

    # 提取CSV数据生成报告
    if [[ -f "$REPORT_DIR/$TIMESTAMP/basic_test_stats.csv" ]]; then
        echo "#### 响应时间统计" >> "$REPORT_DIR/$TIMESTAMP/performance_report.md"
        cat "$REPORT_DIR/$TIMESTAMP/basic_test_stats.csv" | \
            awk -F',' 'NR>1 {printf "- %s: 平均 %.2fms, 95%% %.2fms\\n", $2, $5, $12}' \
            >> "$REPORT_DIR/$TIMESTAMP/performance_report.md"
    fi

    cat >> "$REPORT_DIR/$TIMESTAMP/performance_report.md" <<EOF

### 文件清单

- [基础测试报告](basic_test.html)
- [压力测试报告](stress_test_500u.html)
- [峰值测试报告](peak_test.html)
- [端点测试报告]
EOF

    # 添加端点测试链接
    for endpoint in health matches predictions teams statistics; do
        echo "  - [${endpoint^}端点测试](endpoint_${endpoint}.html)" >> "$REPORT_DIR/$TIMESTAMP/performance_report.md"
    done

    cat >> "$REPORT_DIR/$TIMESTAMP/performance_report.md" <<EOF

### 日志文件

- [基础测试日志](basic_test.log)
- [峰值测试日志](peak_test.log)
- [Apache Bench结果](ab_results.txt)
EOF

    log_info "综合报告已生成: $REPORT_DIR/$TIMESTAMP/performance_report.md"
}

# 分析性能瓶颈
analyze_bottlenecks() {
    log_step "分析性能瓶颈..."

    # 分析慢日志
    if [[ -f "$REPORT_DIR/$TIMESTAMP/basic_test.log" ]]; then
        slow_requests=$(grep -c "慢请求" "$REPORT_DIR/$TIMESTAMP/basic_test.log" || echo 0)
        failed_requests=$(grep -c "❌ 请求失败" "$REPORT_DIR/$TIMESTAMP/basic_test.log" || echo 0)

        echo ""
        echo "性能瓶颈分析:"
        echo "=============="
        echo "慢请求数: $slow_requests"
        echo "失败请求数: $failed_requests"

        if [[ $slow_requests -gt 10 ]]; then
            echo "⚠️ 发现较多慢请求，建议优化"
        fi

        if [[ $failed_requests -gt 5 ]]; then
            echo "❌ 发现较多失败请求，需要检查系统稳定性"
        fi
    fi

    # 分析资源使用
    log_info "收集系统资源使用情况..."
    if command -v pidstat &> /dev/null; then
        pidstat -u -r -d -h -p $(pgrep -f "uvicorn") 1 10 > "$REPORT_DIR/$TIMESTAMP/resource_usage.log" &
        PIDSTAT_PID=$!
        sleep 12
        kill $PIDSTAT_PID 2>/dev/null || true
    fi
}

# 清理测试环境
cleanup() {
    log_step "清理测试环境..."

    # 停止可能存在的测试进程
    pkill -f "locust" || true
    pkill -f "ab" || true
    pkill -f "wrk" || true

    # 清理临时文件
    rm -f tests/performance/test_*.py

    log_info "清理完成"
}

# 显示帮助
show_help() {
    echo "API性能测试工具"
    echo ""
    echo "用法: $0 <命令> [选项]"
    echo ""
    echo "命令:"
    echo "  basic        运行基础性能测试"
    echo "  stress       运行压力测试"
    echo "  peak         运行峰值测试"
    echo "  endurance    运行耐力测试"
    echo "  endpoint     运行端点测试"
    echo "  concurrent   运行并发测试"
    echo "  all          运行所有测试"
    echo "  report       生成报告"
    echo "  analyze      分析瓶颈"
    echo "  help         显示帮助"
    echo ""
    echo "环境变量:"
    echo "  API_BASE_URL    API服务地址 (默认: http://localhost:8000)"
    echo "  USERS           用户数量 (默认: 100)"
    echo "  SPAWN_RATE      用户孵化率 (默认: 10)"
    echo "  TEST_DURATION   测试时长(秒) (默认: 300)"
    echo ""
    echo "示例:"
    echo "  $0 basic                    # 基础测试"
    echo "  $0 stress USERS=200         # 200用户压力测试"
    echo "  $0 all TEST_DURATION=600    # 运行所有测试，每个10分钟"
    echo ""
}

# 主函数
main() {
    local command=${1:-help}

    # 捕获中断信号
    trap cleanup EXIT

    case $command in
        basic)
            create_report_dir
            check_dependencies
            cleanup
            run_basic_test
            analyze_bottlenecks
            ;;
        stress)
            create_report_dir
            check_dependencies
            cleanup
            run_stress_test
            ;;
        peak)
            create_report_dir
            check_dependencies
            cleanup
            run_peak_test
            ;;
        endurance)
            create_report_dir
            check_dependencies
            cleanup
            run_endurance_test
            ;;
        endpoint)
            create_report_dir
            check_dependencies
            cleanup
            run_endpoint_tests
            ;;
        concurrent)
            create_report_dir
            check_dependencies
            cleanup
            run_concurrent_test
            ;;
        all)
            create_report_dir
            check_dependencies
            cleanup
            run_basic_test
            run_stress_test
            run_peak_test
            run_endpoint_tests
            run_concurrent_test
            generate_report
            analyze_bottlenecks
            ;;
        report)
            generate_report
            ;;
        analyze)
            analyze_bottlenecks
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac

    log_info "测试完成！报告位置: $REPORT_DIR/$TIMESTAMP"
}

# 执行主函数
main "$@"
