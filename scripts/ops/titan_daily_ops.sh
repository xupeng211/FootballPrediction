#!/bin/bash
#
# TITAN Daily Operations Script
# TITAN 日常运维一键脚本
#
# 功能：环境点火、健康检查、模式选择、收割监控、优雅关机
# 版本：V4.51.4
# 作者：TITAN Engineering Team
#

set -euo pipefail

# =============================================================================
# 颜色定义
# =============================================================================
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color
readonly BOLD='\033[1m'

# =============================================================================
# 配置变量
# =============================================================================
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
readonly COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.dev.yml"
readonly DATA_DIR="${PROJECT_ROOT}/data/matches"
readonly LOG_DIR="${PROJECT_ROOT}/logs"
readonly SESSION_FILE="${PROJECT_ROOT}/manual_session.json"

readonly DB_HOST="${DB_HOST:-localhost}"
readonly DB_PORT="${DB_PORT:-5432}"
readonly DB_NAME="${DB_NAME:-football_db}"
readonly DB_USER="${DB_USER:-football_user}"

readonly MAX_HEALTH_CHECKS=30
readonly HEALTH_CHECK_INTERVAL=2

# =============================================================================
# 日志函数
# =============================================================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "  🔱 TITAN Daily Operations - V4.51.4"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

# =============================================================================
# 检查依赖
# =============================================================================
check_dependencies() {
    local deps=("docker" "docker-compose")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "缺少依赖: $dep"
            exit 1
        fi
    done
    log_success "依赖检查通过"
}

# =============================================================================
# 检查数据目录权限
# =============================================================================
check_data_permissions() {
    log_info "检查数据目录权限..."
    
    if [[ ! -d "$DATA_DIR" ]]; then
        log_warn "数据目录不存在，正在创建: $DATA_DIR"
        mkdir -p "$DATA_DIR"
    fi
    
    # 检查写入权限
    if [[ ! -w "$DATA_DIR" ]]; then
        log_error "数据目录无写入权限: $DATA_DIR"
        log_info "尝试修复权限..."
        chmod 755 "$DATA_DIR" || {
            log_error "权限修复失败，请手动执行: sudo chmod 755 $DATA_DIR"
            exit 1
        }
    fi
    
    # 检查 Docker 卷挂载点
    local test_file="${DATA_DIR}/.permission_test"
    if touch "$test_file" 2>/dev/null; then
        rm -f "$test_file"
        log_success "数据目录权限正常"
    else
        log_error "无法写入数据目录，请检查 Docker 卷权限"
        exit 1
    fi
}

# =============================================================================
# 环境点火
# =============================================================================
start_environment() {
    log_info "启动 TITAN 环境..."
    
    cd "$PROJECT_ROOT"
    
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "找不到编排文件: $COMPOSE_FILE"
        exit 1
    fi
    
    # 启动容器
    docker-compose -f "$COMPOSE_FILE" up -d
    
    if [[ $? -eq 0 ]]; then
        log_success "容器启动成功"
    else
        log_error "容器启动失败"
        exit 1
    fi
}

# =============================================================================
# 数据库健康检查
# =============================================================================
wait_for_database() {
    log_info "等待数据库就绪..."
    
    local attempt=0
    while [[ $attempt -lt $MAX_HEALTH_CHECKS ]]; do
        attempt=$((attempt + 1))
        
        # 使用 pg_isready 检查
        if docker-compose -f "$COMPOSE_FILE" exec -T db pg_isready -U "$DB_USER" -d "$DB_NAME" &>/dev/null; then
            log_success "数据库已就绪 (尝试 $attempt 次)"
            return 0
        fi
        
        # 备选：使用 nc 检查端口
        if nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; then
            # 端口通了，再检查是否能查询
            if docker-compose -f "$COMPOSE_FILE" exec -T db psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &>/dev/null; then
                log_success "数据库已就绪 (尝试 $attempt 次)"
                return 0
            fi
        fi
        
        echo -ne "${YELLOW}  等待数据库... ${attempt}/${MAX_HEALTH_CHECKS}\r${NC}"
        sleep "$HEALTH_CHECK_INTERVAL"
    done
    
    log_error "数据库健康检查超时 (${MAX_HEALTH_CHECKS} 次尝试)"
    log_info "请检查: docker-compose -f $COMPOSE_FILE logs db"
    exit 1
}

# =============================================================================
# 交互式菜单
# =============================================================================
show_menu() {
    echo ""
    echo -e "${CYAN}${BOLD}请选择操作模式:${NC}"
    echo ""
    echo -e "  ${GREEN}[1]${NC} 抓取新赛季 (Seed + Start)"
    echo -e "      执行赛程种子 + 启动收割"
    echo ""
    echo -e "  ${GREEN}[2]${NC} 继续当前任务 (Start)"
    echo -e "      仅启动收割 (跳过种子)"
    echo ""
    echo -e "  ${GREEN}[3]${NC} 仅启动环境"
    echo -e "      启动容器后退出"
    echo ""
    echo -e "  ${RED}[Q]${NC} 退出"
    echo ""
}

get_user_choice() {
    local choice
    while true; do
        read -rp "请输入选项 [1/2/3/Q]: " choice
        case "$choice" in
            1|2|3|q|Q)
                echo "$choice"
                return 0
                ;;
            *)
                log_warn "无效选项，请重新输入"
                ;;
        esac
    done
}

# =============================================================================
# 执行赛程种子
# =============================================================================
run_seed() {
    log_info "执行 L1 Discovery (赛程种子)..."
    
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" exec -T dev npm run seed
    
    if [[ $? -eq 0 ]]; then
        log_success "赛程种子完成"
    else
        log_error "赛程种子失败"
        return 1
    fi
}

# =============================================================================
# 执行收割
# =============================================================================
run_harvest() {
    log_info "启动 TITAN 收割引擎..."
    log_info "会话文件: $SESSION_FILE"
    
    cd "$PROJECT_ROOT"
    
    # 构建命令
    local cmd="docker-compose -f '$COMPOSE_FILE' exec -T dev node scripts/ops/run_production.js --workers 12 --limit 12000"
    
    if [[ -f "$SESSION_FILE" ]]; then
        cmd="$cmd --session-path /app/manual_session.json"
    else
        log_warn "未找到会话文件，将使用匿名模式"
    fi
    
    log_info "执行命令: $cmd"
    echo ""
    
    # 执行收割并捕获退出码
    eval "$cmd"
    local exit_code=$?
    
    return $exit_code
}

# =============================================================================
# 生成日志汇总
# =============================================================================
generate_summary() {
    local exit_code=$1
    local harvest_count
    local db_pending
    
    echo ""
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}  📊 TITAN 运维日志汇总${NC}"
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # 统计数据
    if [[ -d "$DATA_DIR" ]]; then
        harvest_count=$(find "$DATA_DIR" -name "*.json" -type f 2>/dev/null | wc -l)
        echo -e "  物理文件数: ${GREEN}$harvest_count${NC}"
    fi
    
    # 数据库状态
    db_pending=$(docker-compose -f "$COMPOSE_FILE" exec -T db psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(*) FROM matches WHERE is_finished = false;" 2>/dev/null | tail -1 | xargs)
    if [[ -n "$db_pending" ]]; then
        echo -e "  数据库待收割: ${YELLOW}$db_pending${NC}"
    fi
    
    echo ""
    
    if [[ $exit_code -eq 0 ]]; then
        echo -e "  任务状态: ${GREEN}✅ 成功完成${NC}"
    else
        echo -e "  任务状态: ${RED}❌ 异常退出 (Exit Code: $exit_code)${NC}"
    fi
    
    echo -e "  日志目录: ${BLUE}$LOG_DIR${NC}"
    echo ""
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
}

# =============================================================================
# 优雅关机
# =============================================================================
graceful_shutdown() {
    local exit_code=$1
    
    echo ""
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "任务执行成功"
        echo ""
        read -rp "是否关闭环境? [Y/n]: " confirm
        
        if [[ -z "$confirm" || "$confirm" =~ ^[Yy]$ ]]; then
            log_info "执行优雅关机..."
            cd "$PROJECT_ROOT"
            docker-compose -f "$COMPOSE_FILE" down
            log_success "环境已关闭"
        else
            log_info "保持环境运行"
            log_info "手动关闭命令: docker-compose -f $COMPOSE_FILE down"
        fi
    else
        log_error "任务执行失败 (Exit Code: $exit_code)"
        echo ""
        log_warn "容器已保留用于故障排查"
        echo ""
        echo -e "  ${CYAN}排查命令:${NC}"
        echo -e "    docker-compose -f $COMPOSE_FILE logs dev"
        echo -e "    docker-compose -f $COMPOSE_FILE logs db"
        echo ""
        log_info "故障排除后手动关闭: docker-compose -f $COMPOSE_FILE down"
    fi
}

# =============================================================================
# 主函数
# =============================================================================
main() {
    log_banner
    
    # 检查依赖
    check_dependencies
    
    # 检查权限
    check_data_permissions
    
    # 环境点火
    start_environment
    
    # 健康检查
    wait_for_database
    
    # 显示菜单
    show_menu
    local choice
    choice=$(get_user_choice)
    
    case "$choice" in
        1)
            log_info "模式: 抓取新赛季 (Seed + Start)"
            run_seed || {
                log_error "种子失败，是否继续收割? [y/N]: "
                read -r cont
                [[ "$cont" =~ ^[Yy]$ ]] || exit 1
            }
            run_harvest
            local exit_code=$?
            generate_summary "$exit_code"
            graceful_shutdown "$exit_code"
            ;;
        2)
            log_info "模式: 继续当前任务 (Start)"
            run_harvest
            local exit_code=$?
            generate_summary "$exit_code"
            graceful_shutdown "$exit_code"
            ;;
        3)
            log_info "模式: 仅启动环境"
            log_success "环境已启动并保持运行"
            echo ""
            log_info "手动关闭命令:"
            echo -e "  ${CYAN}docker-compose -f $COMPOSE_FILE down${NC}"
            ;;
        q|Q)
            log_info "退出脚本"
            graceful_shutdown 0
            ;;
    esac
    
    echo ""
    log_success "TITAN 运维脚本执行完毕"
    
    return 0
}

# =============================================================================
# 信号处理
# =============================================================================
cleanup() {
    echo ""
    log_warn "收到中断信号"
    log_info "如需关闭环境，请执行:"
    echo -e "  ${CYAN}docker-compose -f $COMPOSE_FILE down${NC}"
    exit 130
}

trap cleanup INT TERM

# =============================================================================
# 入口
# =============================================================================
main "$@"
