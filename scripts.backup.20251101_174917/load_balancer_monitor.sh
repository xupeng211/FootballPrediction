#!/bin/bash
# 负载均衡监控和自动故障转移脚本
# Load Balancer Monitoring and Auto Failover Script

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置参数
LOG_FILE="/var/log/load-balancer-monitor.log"
NGINX_PID_FILE="/var/run/nginx.pid"
HEALTH_CHECK_INTERVAL=30
MAX_FAILURES=3
RECOVERY_CHECK_INTERVAL=60

# 上游服务器列表
UPSTREAM_SERVERS=(
    "football-app-prod:8000"
    # "football-app-prod-2:8000"
    # "football-app-prod-3:8000"
)

# 健康检查端点
HEALTH_ENDPOINT="/health"

# 日志函数
log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

# 检查Nginx是否运行
check_nginx() {
    if [ -f "$NGINX_PID_FILE" ]; then
        local pid=$(cat "$NGINX_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# 启动Nginx
start_nginx() {
    log_info "启动Nginx服务..."
    if systemctl start nginx; then
        log_success "Nginx启动成功"
        return 0
    else
        log_error "Nginx启动失败"
        return 1
    fi
}

# 重启Nginx
restart_nginx() {
    log_info "重启Nginx服务..."
    if systemctl restart nginx; then
        log_success "Nginx重启成功"
        return 0
    else
        log_error "Nginx重启失败"
        return 1
    fi
}

# 重新加载Nginx配置
reload_nginx() {
    log_info "重新加载Nginx配置..."
    if nginx -t; then
        if systemctl reload nginx; then
            log_success "Nginx配置重新加载成功"
            return 0
        else
            log_error "Nginx配置重新加载失败"
            return 1
        fi
    else
        log_error "Nginx配置测试失败"
        return 1
    fi
}

# 检查单个服务器健康状态
check_server_health() {
    local server="$1"
    local host=$(echo "$server" | cut -d: -f1)
    local port=$(echo "$server" | cut -d: -f2)

    # 使用curl进行健康检查
    if curl -f -s --max-time 10 "http://$host:$port$HEALTH_ENDPOINT" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# 检查所有上游服务器
check_upstream_servers() {
    local healthy_servers=0
    local unhealthy_servers=0

    log_info "检查上游服务器健康状态..."

    for server in "${UPSTREAM_SERVERS[@]}"; do
        if check_server_health "$server"; then
            log_success "服务器 $server 健康检查通过"
            ((healthy_servers++))
        else
            log_error "服务器 $server 健康检查失败"
            ((unhealthy_servers++))
        fi
    done

    log_info "健康服务器数量: $healthy_servers, 不健康服务器数量: $unhealthy_servers"

    if [ "$healthy_servers" -eq 0 ]; then
        log_error "所有上游服务器都不可用！"
        return 1
    elif [ "$unhealthy_servers" -gt 0 ]; then
        log_warning "部分上游服务器不可用"
        return 2
    else
        log_success "所有上游服务器都健康"
        return 0
    fi
}

# 检查负载均衡状态
check_load_balancer_status() {
    log_info "检查负载均衡状态..."

    # 检查Nginx状态页面
    if curl -s --max-time 5 "http://localhost/nginx_status" > /dev/null; then
        log_success "Nginx状态页面正常"
    else
        log_warning "Nginx状态页面不可访问"
    fi

    # 检查上游服务器
    check_upstream_servers
}

# 检查SSL证书状态
check_ssl_certificates() {
    log_info "检查SSL证书状态..."

    local cert_file="/etc/nginx/ssl/cert.pem"

    if [ -f "$cert_file" ]; then
        # 检查证书有效期
        local expiry_date=$(openssl x509 -enddate -noout -in "$cert_file" | cut -d= -f2)
        local expiry_timestamp=$(date -d "$expiry_date" +%s)
        local current_timestamp=$(date +%s)
        local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))

        if [ "$days_until_expiry" -le 7 ]; then
            log_error "SSL证书将在 $days_until_expiry 天后过期！"
            return 1
        elif [ "$days_until_expiry" -le 30 ]; then
            log_warning "SSL证书将在 $days_until_expiry 天后过期"
            return 2
        else
            log_success "SSL证书有效期: $days_until_expiry 天"
            return 0
        fi
    else
        log_error "SSL证书文件不存在: $cert_file"
        return 1
    fi
}

# 检查系统资源
check_system_resources() {
    log_info "检查系统资源..."

    # CPU使用率
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d% -f1)
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        log_warning "CPU使用率过高: ${cpu_usage}%"
    else
        log_success "CPU使用率正常: ${cpu_usage}%"
    fi

    # 内存使用率
    local mem_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    if (( $(echo "$mem_usage > 85" | bc -l) )); then
        log_warning "内存使用率过高: ${mem_usage}%"
    else
        log_success "内存使用率正常: ${mem_usage}%"
    fi

    # 磁盘使用率
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | cut -d% -f1)
    if [ "$disk_usage" -gt 85 ]; then
        log_warning "磁盘使用率过高: ${disk_usage}%"
    else
        log_success "磁盘使用率正常: ${disk_usage}%"
    fi

    # 连接数
    local connections=$(netstat -an | grep ESTABLISHED | wc -l)
    if [ "$connections" -gt 1000 ]; then
        log_warning "活跃连接数过多: $connections"
    else
        log_success "活跃连接数正常: $connections"
    fi
}

# 自动故障转移
auto_failover() {
    log_info "执行自动故障转移..."

    # 检查并重启不健康的服务
    if ! check_nginx; then
        log_error "Nginx未运行，尝试启动..."
        start_nginx
    fi

    # 检查上游服务器
    check_upstream_servers

    # 如果需要，重新加载配置
    if ! nginx -t; then
        log_error "Nginx配置有错误，不进行重新加载"
    else
        log_info "Nginx配置正常"
    fi
}

# 生成健康报告
generate_health_report() {
    local report_file="/var/log/load-balancer-health-report-$(date +%Y%m%d_%H%M%S).txt"

    log_info "生成健康报告: $report_file"

    {
        echo "==================== 负载均衡健康报告 ===================="
        echo "报告时间: $(date)"
        echo "主机名: $(hostname)"
        echo ""

        echo "==================== 系统信息 ===================="
        echo "内核版本: $(uname -r)"
        echo "系统负载: $(uptime)"
        echo ""

        echo "==================== Nginx状态 ===================="
        if check_nginx; then
            echo "Nginx状态: 运行中"
            echo "Nginx版本: $(nginx -v 2>&1)"
        else
            echo "Nginx状态: 未运行"
        fi
        echo ""

        echo "==================== 上游服务器状态 ===================="
        for server in "${UPSTREAM_SERVERS[@]}"; do
            if check_server_health "$server"; then
                echo "$server: 健康"
            else
                echo "$server: 不健康"
            fi
        done
        echo ""

        echo "==================== SSL证书状态 ===================="
        check_ssl_certificates
        echo ""

        echo "==================== 系统资源 ===================="
        echo "CPU使用率: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d% -f1)%"
        echo "内存使用率: $(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')%"
        echo "磁盘使用率: $(df / | awk 'NR==2 {print $5}')"
        echo "活跃连接数: $(netstat -an | grep ESTABLISHED | wc -l)"
        echo ""

        echo "报告生成时间: $(date)"
    } > "$report_file"

    log_success "健康报告已生成: $report_file"
}

# 主监控循环
main_monitor_loop() {
    log_info "启动负载均衡监控服务..."

    local failure_count=0

    while true; do
        # 检查Nginx状态
        if ! check_nginx; then
            log_error "Nginx服务异常"
            ((failure_count++))

            if [ "$failure_count" -ge "$MAX_FAILURES" ]; then
                log_error "连续失败 $failure_count 次，执行故障转移"
                auto_failover
                failure_count=0
            fi
        else
            failure_count=0
        fi

        # 检查负载均衡状态
        check_load_balancer_status

        # 检查SSL证书（每小时检查一次）
        if [ $(date +%M) -eq 0 ]; then
            check_ssl_certificates
        fi

        # 检查系统资源（每5分钟检查一次）
        if [ $(date +%M) -eq 0 ] && [ $(date +%S) -lt 30 ]; then
            check_system_resources
        fi

        # 生成每日报告（每天凌晨2点）
        if [ $(date +%H) -eq 02 ] && [ $(date +%M) -eq 00 ]; then
            generate_health_report
        fi

        sleep "$HEALTH_CHECK_INTERVAL"
    done
}

# 健康检查模式
health_check_mode() {
    log_info "执行一次性健康检查..."

    check_nginx
    check_load_balancer_status
    check_ssl_certificates
    check_system_resources

    log_success "健康检查完成"
}

# 状态报告模式
status_mode() {
    echo "==================== 负载均衡器状态 ===================="
    echo "时间: $(date)"
    echo ""

    if check_nginx; then
        echo "Nginx: 运行中 ✓"
    else
        echo "Nginx: 停止 ✗"
    fi

    check_upstream_servers
    check_ssl_certificates
}

# 使用说明
show_usage() {
    echo "负载均衡监控脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  monitor        启动持续监控模式（默认）"
    echo "  health-check   执行一次性健康检查"
    echo "  status         显示当前状态"
    echo "  restart        重启Nginx服务"
    echo "  reload         重新加载Nginx配置"
    echo "  report         生成健康报告"
    echo "  help           显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 monitor     # 启动监控"
    echo "  $0 health-check # 健康检查"
    echo "  $0 status      # 查看状态"
}

# 主函数
main() {
    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"

    case "${1:-monitor}" in
        "monitor")
            main_monitor_loop
            ;;
        "health-check")
            health_check_mode
            ;;
        "status")
            status_mode
            ;;
        "restart")
            restart_nginx
            ;;
        "reload")
            reload_nginx
            ;;
        "report")
            generate_health_report
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            log_error "未知选项: $1"
            show_usage
            exit 1
            ;;
    esac
}

# 信号处理
trap 'log_info "监控服务停止"; exit 0' SIGTERM SIGINT

# 执行主函数
main "$@"