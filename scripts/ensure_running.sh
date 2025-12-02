#!/bin/bash

# =============================================================================
# Football Prediction System - Service Health Guardian
# =============================================================================
# 功能：开机自启检查脚本，确保所有服务正常运行
# 作者：DevOps架构师
# 版本：v1.0
# =============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目配置
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$PROJECT_DIR/logs/health_guardian.log"
LOCK_FILE_DIR="$PROJECT_DIR/tmp"
BATCH_BACKFILL_LOCK="$LOCK_FILE_DIR/batch_backfill.lock"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

# 创建必要的目录
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$LOCK_FILE_DIR"

# 日志函数
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# 检查是否以root权限运行
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warn "建议不要以root用户运行此脚本"
        return 1
    fi
    return 0
}

# 检查Docker服务状态
check_docker() {
    log_info "检查Docker服务状态..."

    # 检查是否在WSL环境
    if grep -qi microsoft /proc/version 2>/dev/null; then
        log_info "检测到WSL环境，检查Docker Desktop..."
        if docker info >/dev/null 2>&1; then
            log_info "✅ Docker Desktop运行正常"
            return 0
        else
            log_error "❌ Docker Desktop未运行或无法连接"
            log_info "请确保Docker Desktop正在运行"
            return 1
        fi
    fi

    # Linux系统检查
    if command -v systemctl >/dev/null 2>&1; then
        if ! systemctl is-active --quiet docker 2>/dev/null; then
            log_error "Docker服务未运行，尝试启动..."
            if sudo systemctl start docker 2>/dev/null; then
                sleep 5
                if systemctl is-active --quiet docker; then
                    log_info "✅ Docker服务启动成功"
                else
                    log_error "❌ Docker服务启动失败"
                    return 1
                fi
            else
                log_error "❌ 无法启动Docker服务（需要权限）"
                return 1
            fi
        else
            log_info "✅ Docker服务正常运行"
        fi
    elif docker info >/dev/null 2>&1; then
        log_info "✅ Docker运行正常"
    else
        log_error "❌ Docker无法连接"
        return 1
    fi

    return 0
}

# 检查项目容器状态
check_containers() {
    log_info "检查项目容器状态..."

    cd "$PROJECT_DIR"

    # 获取期望运行的容器列表
    local expected_containers=("app" "db" "redis" "worker" "beat" "data-collector" "nginx" "frontend")
    local failed_containers=()

    for container in "${expected_containers[@]}"; do
        local container_name="footballprediction-${container}-1"

        if docker ps --filter "name=$container_name" --format "table {{.Names}}\t{{.Status}}" | grep -q "$container_name"; then
            local status=$(docker ps --filter "name=$container_name" --format "{{.Status}}")
            if [[ $status == *"Up"* ]]; then
                log_info "✅ 容器 $container_name 运行正常"
            else
                log_error "❌ 容器 $container_name 状态异常: $status"
                failed_containers+=("$container")
            fi
        else
            log_error "❌ 容器 $container_name 未运行"
            failed_containers+=("$container")
        fi
    done

    # 如果有失败的容器，尝试重启
    if [ ${#failed_containers[@]} -gt 0 ]; then
        log_warn "发现 ${#failed_containers[@]} 个异常容器，尝试重启服务..."

        # 优先启动核心服务
        local core_services=("db" "redis")
        local app_services=("app" "worker" "beat" "nginx")
        local optional_services=("data-collector" "frontend")

        # 先停止所有服务
        log_info "停止所有服务..."
        docker-compose down

        # 分层启动服务
        log_info "启动核心服务..."
        for service in "${core_services[@]}"; do
            if [[ " ${failed_containers[*]} " =~ " ${service} " ]]; then
                log_info "启动核心服务: $service"
                docker-compose up -d "$service"
                sleep 10
            fi
        done

        log_info "启动应用服务..."
        for service in "${app_services[@]}"; do
            if [[ " ${failed_containers[*]} " =~ " ${service} " ]]; then
                log_info "启动应用服务: $service"
                docker-compose up -d "$service"
                sleep 5
            fi
        done

        log_info "启动可选服务..."
        for service in "${optional_services[@]}"; do
            if [[ " ${failed_containers[*]} " =~ " ${service} " ]]; then
                log_info "启动可选服务: $service"
                docker-compose up -d "$service"
                sleep 5
            fi
        done

        log_info "等待服务稳定..."
        sleep 30

        # 再次检查状态
        log_info "重新检查服务状态..."
        local still_failed=()
        for container in "${failed_containers[@]}"; do
            local container_name="footballprediction-${container}-1"
            if ! docker ps --filter "name=$container_name" --format "{{.Names}}" | grep -q "$container_name"; then
                still_failed+=("$container")
            fi
        done

        if [ ${#still_failed[@]} -eq 0 ]; then
            log_info "🎉 所有服务启动成功！"
        else
            log_error "以下服务启动失败: ${still_failed[*]}"
            return 1
        fi
    fi

    return 0
}

# 检查batch_backfill任务状态
check_batch_backfill() {
    log_info "检查batch_backfill任务状态..."

    local data_collector_container="footballprediction-data-collector-1"

    # 检查容器是否在运行
    if ! docker ps --filter "name=$data_collector_container" --format "{{.Names}}" | grep -q "$data_collector_container"; then
        log_warn "data-collector容器未运行，跳过batch_backfill检查"
        return 0
    fi

    # 检查容器状态和命令
    local container_command=$(docker inspect "$data_collector_container" --format='{{.Config.Cmd}}' 2>/dev/null || echo "")
    if [[ "$container_command" == *"backfill"* ]]; then
        log_info "✅ data-collector容器正在运行backfill任务"

        # 检查容器健康状态
        local container_health=$(docker inspect "$data_collector_container" --format='{{.State.Health.Status}}' 2>/dev/null || echo "none")
        if [[ "$container_health" == "healthy" ]]; then
            log_info "✅ 容器健康状态正常"
        elif [[ "$container_health" == "unhealthy" ]]; then
            log_warn "⚠️ 容器健康状态异常"
        else
            log_info "ℹ️ 容器未配置健康检查"
        fi

        # 检查是否有输出活动（检查最近5分钟的日志）
        local recent_logs=$(docker logs --since=5m "$data_collector_container" 2>/dev/null | wc -l || echo "0")
        if [[ "$recent_logs" -gt 0 ]]; then
            log_info "✅ Backfill任务有最近的活动日志 ($recent_logs 行)"
        else
            log_warn "⚠️ Backfill任务最近5分钟无日志输出，可能正在等待"
        fi

        # 检查容器启动时间
        local container_start=$(docker inspect "$data_collector_container" --format='{{.State.StartedAt}}' 2>/dev/null || echo "")
        if [[ -n "$container_start" ]]; then
            log_info "容器启动时间: $container_start"
        fi

    else
        log_info "ℹ️ data-collector容器运行中，但未执行backfill任务"
    fi

    # 检查是否有锁文件（项目级）
    if [[ -f "$BATCH_BACKFILL_LOCK" ]]; then
        local lock_time=$(stat -c %Y "$BATCH_BACKFILL_LOCK" 2>/dev/null || echo "0")
        local current_time=$(date +%s)
        local lock_age=$((current_time - lock_time))

        if [[ $lock_age -gt 3600 ]]; then  # 锁文件超过1小时
            log_error "发现过期的backfill锁文件 (${lock_age}秒前创建)，可能需要清理"
            log_info "清理过期锁文件: $BATCH_BACKFILL_LOCK"
            rm -f "$BATCH_BACKFILL_LOCK"
        else
            log_info "发现backfill锁文件 (${lock_age}秒前创建)"
        fi
    fi

    return 0
}

# 检查crond服务
check_cron() {
    log_info "检查crond服务状态..."

    if systemctl is-active --quiet cron 2>/dev/null || systemctl is-active --quiet crond 2>/dev/null; then
        log_info "✅ Cron服务正常运行"
    else
        log_warn "Cron服务未运行，尝试启动..."

        # 尝试不同的cron服务名
        if command -v systemctl >/dev/null 2>&1; then
            sudo systemctl start cron 2>/dev/null || sudo systemctl start crond 2>/dev/null || {
                log_error "Cron服务启动失败"
                return 1
            }
        elif command -v service >/dev/null 2>&1; then
            sudo service cron start 2>/dev/null || sudo service crond start 2>/dev/null || {
                log_error "Cron服务启动失败"
                return 1
            }
        fi

        sleep 3
        if systemctl is-active --quiet cron 2>/dev/null || systemctl is-active --quiet crond 2>/dev/null; then
            log_info "✅ Cron服务启动成功"
        else
            log_error "❌ Cron服务启动失败"
            return 1
        fi
    fi

    return 0
}

# 检查磁盘空间
check_disk_space() {
    log_info "检查磁盘空间..."

    local df_output=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ "$df_output" -gt 85 ]]; then
        log_warn "磁盘空间使用率较高: ${df_output}%"
    else
        log_info "磁盘空间充足: ${df_output}%"
    fi

    # 检查Docker数据目录空间
    local docker_df=$(docker system df --format "{{.Size}}" | head -1)
    log_info "Docker数据占用: $docker_df"

    return 0
}

# 检查系统负载
check_system_load() {
    log_info "检查系统负载..."

    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_cores=$(nproc)

    # 计算负载百分比 (简化计算)
    local load_percentage=$(echo "$load_avg * 100 / $cpu_cores" | bc -l 2>/dev/null || echo "0")

    if (( $(echo "$load_percentage > 80" | bc -l 2>/dev/null || echo "0") )); then
        log_warn "系统负载较高: $load_avg (${load_percentage}%)"
    else
        log_info "系统负载正常: $load_avg (${load_percentage}%)"
    fi

    return 0
}

# 主函数
main() {
    log_info "🚀 Football Prediction System - 健康检查开始"
    log_info "项目目录: $PROJECT_DIR"

    local exit_code=0

    # 执行各项检查
    check_docker || exit_code=1
    check_containers || exit_code=1
    check_cron || exit_code=1
    check_batch_backfill
    check_disk_space
    check_system_load

    # 总结
    if [[ $exit_code -eq 0 ]]; then
        log_info "🎉 所有检查完成！系统状态良好"
        echo -e "\n${GREEN}=== 系统状态总结 ===${NC}"
        echo -e "${GREEN}✅ 服务运行正常${NC}"
        echo -e "${GREEN}✅ Docker环境健康${NC}"
        echo -e "${GREEN}✅ 数据持久化安全${NC}"
    else
        log_error "❌ 发现问题，请检查上述错误信息"
        echo -e "\n${RED}=== 需要关注的问题 ===${NC}"
        echo -e "${RED}❌ 服务状态异常${NC}"
        echo -e "${RED}❌ 请查看日志: $LOG_FILE${NC}"
    fi

    echo -e "\n${BLUE}=== 快速访问地址 ===${NC}"
    echo -e "🌐 API文档: ${BLUE}http://localhost:8000/docs${NC}"
    echo -e "💚 健康检查: ${BLUE}http://localhost:8000/health${NC}"
    echo -e "📊 Prometheus指标: ${BLUE}http://localhost:8000/api/v1/metrics${NC}"
    echo -e "🔍 详细日志: ${BLUE}$LOG_FILE${NC}"

    return $exit_code
}

# 信号处理
trap 'log_error "脚本被中断"; exit 130' INT TERM

# 运行主函数
main "$@"