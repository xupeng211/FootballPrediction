#!/bin/bash
# ============================================
# 生产自动化调度器 - 状态验证脚本
# ============================================
# 用于检查 production_cron 服务运行状态
#
# 使用方法:
#   ./scripts/verify_automation.sh
#   ./scripts/verify_automation.sh --logs    # 查看最近日志
#   ./scripts/verify_automation.sh --summary  # 查看执行摘要
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# 检查容器状态
check_container_status() {
    print_header "1. 容器状态检查"

    if docker ps --format '{{.Names}}' | grep -q "^football_prediction_cron$"; then
        print_success "production_cron 容器正在运行"

        # 显示容器详情
        docker inspect football_prediction_cron --format='   重启次数: {{.RestartCount}}' 2>/dev/null || true
        docker inspect football_prediction_cron --format='   运行时间: {{.State.StartedAt}}' 2>/dev/null || true

        # 检查重启次数
        restart_count=$(docker inspect football_prediction_cron --format='{{.RestartCount}}' 2>/dev/null || echo "0")
        if [ "$restart_count" -gt 3 ]; then
            print_warning "容器已重启 $restart_count 次，可能存在问题"
        fi
    else
        print_error "production_cron 容器未运行"
        echo ""
        echo "启动命令:"
        echo "  docker-compose --profile automation up -d production_cron"
        return 1
    fi
    echo ""
}

# 检查最近执行日志
check_recent_logs() {
    print_header "2. 最近执行日志 (最近 20 行)"

    if docker ps --format '{{.Names}}' | grep -q "^football_prediction_cron$"; then
        docker logs --tail 20 football_prediction_cron 2>&1 || true
    else
        print_error "容器未运行，无法获取日志"
    fi
    echo ""
}

# 查看完整日志
show_full_logs() {
    print_header "完整日志输出"

    if docker ps --format '{{.Names}}' | grep -q "^football_prediction_cron$"; then
        docker logs football_prediction_cron 2>&1 | tail -100 || true
    else
        print_error "容器未运行，无法获取日志"
    fi
    echo ""
}

# 检查生成的预测报告
check_predictions() {
    print_header "3. 预测报告检查"

    # 检查容器内的预测目录
    if docker ps --format '{{.Names}}' | grep -q "^football_prediction_cron$"; then
        prediction_count=$(docker exec football_prediction_cron sh -c "ls -1 /app/predictions/*.csv 2>/dev/null | wc -l" || echo "0")

        if [ "$prediction_count" -gt 0 ]; then
            print_success "找到 $prediction_count 个预测报告文件"

            echo ""
            echo "最近的报告:"
            docker exec football_prediction_cron sh -c "ls -lt /app/predictions/*.csv 2>/dev/null | head -5" || true
        else
            print_warning "未找到预测报告文件"
        fi
    else
        print_warning "容器未运行"
    fi
    echo ""
}

# 检查执行摘要
check_execution_summary() {
    print_header "4. 执行摘要检查"

    if docker ps --format '{{.Names}}' | grep -q "^football_prediction_cron$"; then
        # 查找最新的摘要文件
        latest_summary=$(docker exec football_prediction_cron sh -c "ls -t /app/logs/flow_summary_*.json 2>/dev/null | head -1" || echo "")

        if [ -n "$latest_summary" ]; then
            print_success "找到执行摘要文件"

            echo ""
            echo "最新摘要内容:"
            docker exec football_prediction_cron cat "$latest_summary" 2>/dev/null || true
        else
            print_warning "未找到执行摘要文件"
        fi
    else
        print_warning "容器未运行"
    fi
    echo ""
}

# 检查日志文件
check_log_files() {
    print_header "5. 日志文件检查"

    if docker ps --format '{{.Names}}' | grep -q "^football_prediction_cron$"; then
        log_size=$(docker exec football_prediction_cron sh -c "du -sh /app/logs/production_flow.log 2>/dev/null | cut -f1" || echo "0")

        if [ "$log_size" != "0" ]; then
            print_success "日志文件大小: $log_size"
        else
            print_warning "日志文件不存在或为空"
        fi
    else
        print_warning "容器未运行"
    fi
    echo ""
}

# 显示调度配置
show_schedule_config() {
    print_header "6. 调度配置"

    if docker ps --format '{{.Names}}' | grep -q "^football_prediction_cron$"; then
        schedule=$(docker exec football_prediction_cron sh -c 'echo $CRON_SCHEDULE' 2>/dev/null || echo "未配置")
        target_count=$(docker exec football_prediction_cron sh -c 'echo $TARGET_MATCH_COUNT' 2>/dev/null || echo "未配置")

        echo "   调度计划: $schedule (默认: 0 3 * * *)"
        echo "   目标采集: $target_count 场 (默认: 50)"
        echo ""
        echo "   说明: cron 格式为 '分 时 日 月 周'"
        echo "   0 3 * * * = 每天凌晨 3:00"
    else
        print_warning "容器未运行"
    fi
    echo ""
}

# ============================================
# 主函数
# ============================================

main() {
    case "${1:-status}" in
        --logs|-l)
            show_full_logs
            ;;
        --summary|-s)
            check_execution_summary
            ;;
        --predictions|-p)
            check_predictions
            ;;
        --config|-c)
            show_schedule_config
            ;;
        status|"")
            check_container_status
            check_predictions
            check_execution_summary
            check_log_files
            show_schedule_config

            print_header "健康检查完成"
            print_success "所有检查已执行，请查看上方结果"
            echo ""
            echo "更多选项:"
            echo "  $0 --logs       查看完整日志"
            echo "  $0 --summary    查看执行摘要"
            echo "  $0 --predictions 查看预测报告"
            echo "  $0 --config     查看调度配置"
            ;;
        *)
            echo "用法: $0 [status|logs|summary|predictions|config]"
            exit 1
            ;;
    esac
}

main "$@"
