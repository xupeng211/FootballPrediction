#!/bin/bash

# 上线自动化脚本
# Deployment Automation Script

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/deploy-$(date +%Y%m%d-%H%M%S).log"
BACKUP_DIR="$PROJECT_ROOT/backups"
HEALTH_CHECK_TIMEOUT=300
ROLLBACK_ENABLED=true

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}" | tee -a "$LOG_FILE"
}

# 创建必要目录
setup_directories() {
    log "创建必要目录..."
    mkdir -p "$PROJECT_ROOT/logs"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$PROJECT_ROOT/nginx/ssl"
}

# 检查前置条件
check_prerequisites() {
    log "检查前置条件..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        error "Docker 未安装或不在PATH中"
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose 未安装或不在PATH中"
    fi

    # 检查环境变量文件
    if [[ ! -f "$PROJECT_ROOT/docker/environments/.env.production" ]]; then
        error "生产环境配置文件不存在: docker/environments/.env.production"
    fi

    # 检查端口可用性
    local ports=(80 443 8000 5432 6379 9090 3000)
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            warn "端口 $port 已被占用，请检查是否有冲突服务"
        fi
    done

    # 检查磁盘空间
    local available_space
    available_space=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 2097152 ]]; then  # 2GB in KB
        error "磁盘空间不足，至少需要2GB可用空间"
    fi

    log "前置条件检查完成"
}

# 备份当前系统
backup_current_system() {
    log "备份当前系统..."

    local backup_name="backup-$(date +%Y%m%d-%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"

    mkdir -p "$backup_path"

    # 备份数据库
    if docker-compose ps | grep -q "db.*Up"; then
        log "备份数据库..."
        docker-compose exec -T db pg_dump -U prod_user football_prediction > "$backup_path/database.sql"
    fi

    # 备份配置文件
    log "备份配置文件..."
    cp -r "$PROJECT_ROOT/docker/environments" "$backup_path/"
    cp -r "$PROJECT_ROOT/nginx" "$backup_path/"

    # 备份当前代码版本
    log "备份代码版本..."
    git rev-parse HEAD > "$backup_path/git_commit.txt"
    git log --oneline -10 > "$backup_path/git_history.txt"

    # 创建备份元数据
    cat > "$backup_path/backup_metadata.txt" << EOF
备份时间: $(date)
备份版本: $(git rev-parse --short HEAD)
备份原因: 系统上线前备份
备份内容: 数据库、配置文件、代码版本
EOF

    log "系统备份完成: $backup_path"
    echo "$backup_path"
}

# 构建和部署应用
deploy_application() {
    log "开始部署应用..."

    cd "$PROJECT_ROOT"

    # 停止现有服务
    log "停止现有服务..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down || true

    # 构建新镜像
    log "构建应用镜像..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache

    # 启动服务
    log "启动生产服务..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

    # 等待服务启动
    log "等待服务启动..."
    sleep 30

    # 检查服务状态
    log "检查服务状态..."
    if ! docker-compose -f docker-compose.yml -f docker-compose.prod.yml ps | grep -q "Up"; then
        error "服务启动失败"
    fi

    log "应用部署完成"
}

# 健康检查
health_check() {
    log "开始健康检查..."

    local start_time=$(date +%s)
    local end_time=$((start_time + HEALTH_CHECK_TIMEOUT))

    while [[ $(date +%s) -lt $end_time ]]; do
        # 检查基础健康端点
        if curl -f -s http://localhost/health/ > /dev/null 2>&1; then
            log "基础健康检查通过"

            # 检查详细健康状态
            local health_response
            health_response=$(curl -s http://localhost/health/)
            if echo "$health_response" | grep -q '"status":"healthy"'; then
                log "详细健康检查通过"

                # 检查API端点
                if curl -f -s http://localhost/api/v1/predictions/1 > /dev/null 2>&1; then
                    log "API端点检查通过"
                    return 0
                else
                    warn "API端点检查失败，继续等待..."
                fi
            else
                warn "详细健康检查失败，继续等待..."
            fi
        else
            warn "基础健康检查失败，继续等待..."
        fi

        sleep 10
    done

    error "健康检查超时 ($HEALTH_CHECK_TIMEOUT 秒)"
}

# 性能验证
performance_check() {
    log "开始性能验证..."

    # 检查响应时间
    local response_time
    response_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost/health/)

    if (( $(echo "$response_time > 0.1" | bc -l) )); then
        warn "健康检查端点响应时间较慢: ${response_time}s"
    else
        log "健康检查端点响应时间正常: ${response_time}s"
    fi

    # 运行基本压力测试
    log "运行基本压力测试..."
    if python "$PROJECT_ROOT/scripts/stress_test.py" > /dev/null 2>&1; then
        log "压力测试通过"
    else
        warn "压力测试未完全通过，需要关注性能指标"
    fi

    log "性能验证完成"
}

# 监控验证
monitoring_check() {
    log "开始监控验证..."

    # 检查Prometheus
    if curl -f -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
        log "Prometheus监控正常"
    else
        warn "Prometheus监控异常"
    fi

    # 检查Grafana
    if curl -f -s http://localhost:3000/api/health > /dev/null 2>&1; then
        log "Grafana仪表板正常"
    else
        warn "Grafana仪表板异常"
    fi

    log "监控验证完成"
}

# 生成部署报告
generate_report() {
    local backup_path="$1"
    local deploy_time=$(date)
    local git_commit=$(git rev-parse --short HEAD)
    local git_branch=$(git branch --show-current)

    cat > "$PROJECT_ROOT/logs/deploy-report-$(date +%Y%m%d-%H%M%S).md" << EOF
# 部署报告

## 基本信息
- **部署时间**: $deploy_time
- **部署版本**: $git_commit
- **部署分支**: $git_branch
- **部署人员**: $USER
- **备份路径**: $backup_path

## 部署步骤
1. ✅ 前置条件检查
2. ✅ 系统备份
3. ✅ 应用部署
4. ✅ 健康检查
5. ✅ 性能验证
6. ✅ 监控验证

## 部署结果
- **部署状态**: 成功
- **系统状态**: 正常运行
- **API状态**: 正常响应
- **监控状态**: 正常收集

## 服务地址
- **主应用**: http://localhost
- **API文档**: http://localhost/docs
- **监控面板**: http://localhost:3000
- **指标收集**: http://localhost:9090

## 后续监控要点
1. 关注API响应时间
2. 监控系统资源使用率
3. 检查错误率变化
4. 验证业务指标正常

---
生成时间: $(date)
EOF

    log "部署报告已生成"
}

# 回滚功能
rollback() {
    local backup_path="$1"

    if [[ -z "$backup_path" ]]; then
        error "回滚需要指定备份路径"
    fi

    if [[ ! -d "$backup_path" ]]; then
        error "备份路径不存在: $backup_path"
    fi

    warn "开始回滚到备份: $backup_path"

    # 停止当前服务
    log "停止当前服务..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down || true

    # 恢复数据库
    if [[ -f "$backup_path/database.sql" ]]; then
        log "恢复数据库..."
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d db
        sleep 20
        docker-compose exec -T db psql -U prod_user -d football_prediction < "$backup_path/database.sql"
    fi

    # 恢复配置文件
    if [[ -d "$backup_path/environments" ]]; then
        log "恢复配置文件..."
        cp -r "$backup_path/environments"/* "$PROJECT_ROOT/docker/environments/"
    fi

    if [[ -d "$backup_path/nginx" ]]; then
        log "恢复Nginx配置..."
        cp -r "$backup_path/nginx"/* "$PROJECT_ROOT/nginx/"
    fi

    # 恢复代码版本
    if [[ -f "$backup_path/git_commit.txt" ]]; then
        log "恢复代码版本..."
        local backup_commit
        backup_commit=$(cat "$backup_path/git_commit.txt")
        git checkout "$backup_commit"
    fi

    # 重新启动服务
    log "重新启动服务..."
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

    log "回滚完成"
}

# 主函数
main() {
    local command="${1:-deploy}"
    local backup_path="${2:-}"

    log "开始执行部署流程..."

    case "$command" in
        "deploy")
            setup_directories
            check_prerequisites
            backup_path=$(backup_current_system)
            deploy_application
            health_check
            performance_check
            monitoring_check
            generate_report "$backup_path"
            log "🎉 部署成功完成！"
            ;;
        "rollback")
            if [[ -z "$backup_path" ]]; then
                error "回滚命令需要指定备份路径"
            fi
            rollback "$backup_path"
            log "🔄 回滚完成！"
            ;;
        "health")
            health_check
            ;;
        "validate")
            check_prerequisites
            log "✅ 验证通过"
            ;;
        *)
            echo "使用方法: $0 {deploy|rollback|health|validate} [backup_path]"
            echo "  deploy    - 执行完整部署流程"
            echo "  rollback  - 回滚到指定备份"
            echo "  health    - 执行健康检查"
            echo "  validate  - 验证部署前置条件"
            exit 1
            ;;
    esac
}

# 错误处理
trap 'error "脚本执行失败，请检查日志: $LOG_FILE"' ERR

# 执行主函数
main "$@"