#!/bin/bash

# 应急响应脚本
# Emergency Response Script

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/emergency-$(date +%Y%m%d-%H%M%S).log"
INCIDENT_REPORT_FILE="$PROJECT_ROOT/logs/incident-$(date +%Y%m%d-%H%M%S).md"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 日志函数
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}" | tee -a "$LOG_FILE"
}

critical() {
    echo -e "${PURPLE}[$(date +'%Y-%m-%d %H:%M:%S')] CRITICAL: $1${NC}" | tee -a "$LOG_FILE"
}

# 创建必要目录
setup_directories() {
    mkdir -p "$PROJECT_ROOT/logs"
    mkdir -p "$PROJECT_ROOT/backups/emergency"
}

# 系统健康检查
system_health_check() {
    info "执行系统健康检查..."

    local issues_found=0

    # 检查Docker服务状态
    info "检查Docker服务状态..."
    local docker_services
    docker_services=$(docker-compose ps --services --filter "status=running")

    if [[ -z "$docker_services" ]]; then
        error "没有运行中的Docker服务"
        ((issues_found++))
    else
        local service_count
        service_count=$(echo "$docker_services" | wc -l)
        log "运行中的Docker服务数量: $service_count"
    fi

    # 检查关键服务
    local critical_services=("app" "db" "redis" "nginx")
    for service in "${critical_services[@]}"; do
        if docker-compose ps | grep -q "$service.*Up"; then
            log "服务 $service 运行正常"
        else
            error "服务 $service 未运行或异常"
            ((issues_found++))
        fi
    done

    # 检查系统资源
    info "检查系统资源..."
    local cpu_usage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    local mem_usage
    mem_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    local disk_usage
    disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

    if (( $(echo "$cpu_usage > 90" | bc -l) )); then
        warn "CPU使用率过高: ${cpu_usage}%"
        ((issues_found++))
    fi

    if (( $(echo "$mem_usage > 90" | bc -l) )); then
        warn "内存使用率过高: ${mem_usage}%"
        ((issues_found++))
    fi

    if [[ $disk_usage -gt 90 ]]; then
        warn "磁盘使用率过高: ${disk_usage}%"
        ((issues_found++))
    fi

    # 检查网络连通性
    info "检查网络连通性..."
    if curl -s -f http://localhost/health/ > /dev/null; then
        log "网络连通性正常"
    else
        error "网络连通性异常"
        ((issues_found++))
    fi

    if [[ $issues_found -gt 0 ]]; then
        warn "系统健康检查发现 $issues_found 个问题"
        return $issues_found
    else
        log "系统健康检查通过"
        return 0
    fi
}

# 紧急服务重启
emergency_restart() {
    local service="${1:-all}"

    warn "开始紧急重启服务: $service"

    # 记录重启前状态
    log "记录重启前状态..."
    docker-compose ps > "$PROJECT_ROOT/logs/pre-restart-status.log"
    docker-compose logs --tail=100 > "$PROJECT_ROOT/logs/pre-restart-logs.log"

    case "$service" in
        "all")
            log "重启所有服务..."
            docker-compose down
            sleep 10
            docker-compose up -d
            ;;
        "app"|"db"|"redis"|"nginx")
            log "重启服务: $service"
            docker-compose restart "$service"
            ;;
        *)
            error "未知服务: $service"
            return 1
            ;;
    esac

    # 等待服务启动
    log "等待服务启动..."
    sleep 30

    # 验证重启结果
    if system_health_check; then
        log "服务重启成功"
        "$SCRIPT_DIR/notify-team.sh" "紧急服务重启完成: $service" success
        return 0
    else
        error "服务重启后仍有问题"
        "$SCRIPT_DIR/notify-team.sh" "紧急服务重启后仍有问题: $service" error
        return 1
    fi
}

# 紧急数据库修复
emergency_database_fix() {
    warn "开始紧急数据库修复..."

    # 检查数据库状态
    if docker-compose ps | grep -q "db.*Up"; then
        log "数据库容器运行中，检查连接..."

        if docker-compose exec -T db pg_isready -U prod_user; then
            log "数据库连接正常"

            # 检查数据库性能
            info "检查数据库性能..."
            docker-compose exec -T db psql -U prod_user -c "
            SELECT datname, numbackends, xact_commit, xact_rollback, blks_read, blks_hit, tup_returned, tup_fetched, tup_inserted, tup_updated, tup_deleted
            FROM pg_stat_database
            WHERE datname = 'football_prediction';"

            # 检查慢查询
            info "检查慢查询..."
            docker-compose exec -T db psql -U prod_user -c "
            SELECT query, mean_time, calls, total_time
            FROM pg_stat_statements
            WHERE mean_time > 1000
            ORDER BY mean_time DESC
            LIMIT 10;" || true

        else
            error "数据库连接失败，尝试重启..."
            docker-compose restart db
            sleep 20

            if docker-compose exec -T db pg_isready -U prod_user; then
                log "数据库重启后连接恢复"
            else
                critical "数据库重启后仍无法连接，需要手动干预"
                "$SCRIPT_DIR/notify-team.sh" "数据库连接失败，需要立即干预" error
                return 1
            fi
        fi
    else
        error "数据库容器未运行，尝试启动..."
        docker-compose up -d db
        sleep 30

        if docker-compose exec -T db pg_isready -U prod_user; then
            log "数据库启动成功"
        else
            critical "数据库启动失败，需要立即干预"
            "$SCRIPT_DIR/notify-team.sh" "数据库启动失败，需要立即干预" error
            return 1
        fi
    fi

    log "数据库修复完成"
    return 0
}

# 紧急资源清理
emergency_resource_cleanup() {
    warn "开始紧急资源清理..."

    # 清理Docker资源
    info "清理Docker资源..."
    docker system prune -f
    docker volume prune -f

    # 清理日志文件
    info "清理日志文件..."
    find /var/lib/docker -name "*.log" -mtime +3 -delete 2>/dev/null || true
    find "$PROJECT_ROOT/logs" -name "*.log" -mtime +7 -delete 2>/dev/null || true

    # 清理临时文件
    info "清理临时文件..."
    find /tmp -name "*" -type f -mtime +1 -delete 2>/dev/null || true

    # 清理应用缓存
    info "清理应用缓存..."
    if docker-compose ps | grep -q "redis.*Up"; then
        docker-compose exec -T redis redis-cli FLUSHDB || true
    fi

    log "资源清理完成"
}

# 紧急备份
emergency_backup() {
    warn "开始紧急备份..."

    local backup_name="emergency-backup-$(date +%Y%m%d-%H%M%S)"
    local backup_dir="$PROJECT_ROOT/backups/emergency/$backup_name"

    mkdir -p "$backup_dir"

    # 备份数据库
    if docker-compose ps | grep -q "db.*Up"; then
        log "紧急备份数据库..."
        docker-compose exec -T db pg_dump -U prod_user football_prediction > "$backup_dir/emergency-database.sql"
    fi

    # 备份配置文件
    log "备份配置文件..."
    cp -r "$PROJECT_ROOT/docker/environments" "$backup_dir/" 2>/dev/null || true
    cp -r "$PROJECT_ROOT/nginx" "$backup_dir/" 2>/dev/null || true

    # 备份关键日志
    log "备份关键日志..."
    docker-compose logs --tail=1000 > "$backup_dir/emergency-logs.log" 2>/dev/null || true

    # 备份系统状态
    log "备份系统状态..."
    docker-compose ps > "$backup_dir/emergency-services.log"
    docker stats --no-stream > "$backup_dir/emergency-resources.log"
    git rev-parse HEAD > "$backup_dir/emergency-git-commit.txt" 2>/dev/null || true

    log "紧急备份完成: $backup_dir"
    echo "$backup_dir"
}

# 安全检查
security_check() {
    warn "开始安全检查..."

    local security_issues=0

    # 检查异常登录
    info "检查异常登录..."
    local auth_failures
    auth_failures=$(docker-compose logs nginx 2>/dev/null | grep -c "401\|403" || echo "0")
    if [[ $auth_failures -gt 100 ]]; then
        warn "发现大量认证失败: $auth_failures 次"
        ((security_issues++))
    fi

    # 检查异常访问模式
    info "检查异常访问模式..."
    local suspicious_ips
    suspicious_ips=$(docker-compose logs nginx 2>/dev/null | grep -E "(POST|PUT)" | awk '{print $1}' | sort | uniq -c | sort -nr | head -5)
    if [[ -n "$suspicious_ips" ]]; then
        warn "发现可疑高频访问IP:"
        echo "$suspicious_ips"
        ((security_issues++))
    fi

    # 检查文件完整性
    info "检查关键文件完整性..."
    local critical_files=("$PROJECT_ROOT/src/main.py" "$PROJECT_ROOT/requirements/requirements.lock")
    for file in "${critical_files[@]}"; do
        if [[ -f "$file" ]]; then
            local file_hash
            file_hash=$(md5sum "$file" | awk '{print $1}')
            log "文件 $file 哈希: $file_hash"
        else
            error "关键文件不存在: $file"
            ((security_issues++))
        fi
    done

    if [[ $security_issues -gt 0 ]]; then
        warn "安全检查发现 $security_issues 个潜在问题"
        return $security_issues
    else
        log "安全检查通过"
        return 0
    fi
}

# 生成事故报告
generate_incident_report() {
    local incident_type="$1"
    local actions_taken="$2"
    local resolution_status="$3"

    cat > "$INCIDENT_REPORT_FILE" << EOF
# 事故报告

## 基本信息
- **事故时间**: $(date)
- **事故类型**: $incident_type
- **处理状态**: $resolution_status
- **处理人员**: $USER

## 事故描述
$(cat "$LOG_FILE" | grep -E "(ERROR|WARNING|CRITICAL)" | head -20)

## 采取的措施
$actions_taken

## 系统状态
### 服务状态
\`\`\`
$(docker-compose ps)
\`\`\`

### 资源使用情况
\`\`\`
$(docker stats --no-stream)
\`\`\`

### 最近错误日志
\`\`\`
$(docker-compose logs --tail=50 | grep -i error | head -20)
\`\`\`

## 解决方案
[描述具体解决方案]

## 预防措施
[描述预防类似问题的措施]

## 后续跟进
- [ ] 根本原因分析
- [ ] 系统改进方案
- [ ] 流程优化
- [ ] 团队培训

---
报告生成时间: $(date)
EOF

    log "事故报告已生成: $INCIDENT_REPORT_FILE"
}

# 主函数
main() {
    local command="${1:-check}"
    local service="${2:-all}"

    setup_directories
    log "启动应急响应系统..."

    case "$command" in
        "check")
            system_health_check
            ;;
        "restart")
            emergency_restart "$service"
            ;;
        "database")
            emergency_database_fix
            ;;
        "cleanup")
            emergency_resource_cleanup
            ;;
        "backup")
            emergency_backup
            ;;
        "security")
            security_check
            ;;
        "full")
            warn "执行完整应急响应流程..."

            # 1. 紧急备份
            backup_dir=$(emergency_backup)

            # 2. 安全检查
            security_check

            # 3. 系统修复
            emergency_restart "$service"

            # 4. 资源清理
            emergency_resource_cleanup

            # 5. 生成报告
            generate_incident_report "完整应急响应" "备份、安全检查、服务重启、资源清理" "已完成"

            log "完整应急响应流程执行完成"
            ;;
        *)
            echo "使用方法: $0 {check|restart|database|cleanup|backup|security|full} [service]"
            echo "  check    - 系统健康检查"
            echo "  restart  - 紧急重启服务 (all|app|db|redis|nginx)"
            echo "  database - 紧急数据库修复"
            echo "  cleanup  - 紧急资源清理"
            echo "  backup   - 紧急备份"
            echo "  security - 安全检查"
            echo "  full     - 完整应急响应流程"
            exit 1
            ;;
    esac
}

# 错误处理
trap 'error "应急响应脚本执行失败，请检查日志: $LOG_FILE"' ERR

# 执行主函数
main "$@"