#!/bin/bash
################################################################################
# 总攻一键启动脚本 - Operation '总攻' Master Launch Script
#
# V147.5 生产环境最终部署
#
# 功能：
#   Step 0: 检查 Docker 数据库容器健康状态
#   Step 1: 执行 alembic upgrade head（Schema 强制同步）
#   Step 2: 网络心跳检查（10个代理端口）
#   Step 3: 启动监控仪表盘后台进程
#   Step 4: 引导用户选择数据源开始收割
#
# Usage:
#   ./start_operation.sh
#
# Author: Senior SRE (War Room Commander)
# Date: 2026-01-06
################################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_step() {
    echo -e "\n${BLUE}📋 Step $1: $2${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

################################################################################
# Step 0: 检查 Docker 数据库容器健康状态
################################################################################
check_docker_health() {
    print_step "0" "检查 Docker 容器健康状态"

    # 检查 Docker 是否运行
    if ! docker info &> /dev/null; then
        print_error "Docker 未运行，请先启动 Docker"
        exit 1
    fi
    print_success "Docker 运行正常"

    # 检查数据库容器
    if docker-compose ps db | grep -q "Up"; then
        print_success "数据库容器运行中"
    else
        print_warning "数据库容器未运行，尝试启动..."
        docker-compose up -d db
        sleep 5
        print_success "数据库容器已启动"
    fi

    # 检查 Redis 容器
    if docker-compose ps redis | grep -q "Up"; then
        print_success "Redis 容器运行中"
    else
        print_warning "Redis 容器未运行，尝试启动..."
        docker-compose up -d redis
        sleep 3
        print_success "Redis 容器已启动"
    fi

    # 测试数据库连接
    if docker-compose exec -T db pg_isready -U football_user -d football_db &> /dev/null; then
        print_success "数据库连接正常"
    else
        print_error "数据库连接失败"
        exit 1
    fi
}

################################################################################
# Step 1: 执行 SchemaManager.initialize_schema() - V149.0 统一入口
################################################################################
upgrade_database_schema() {
    print_step "1" "数据库 Schema 初始化/升级 (V149.0)"

    print_info "调用 SchemaManager.initialize_schema()..."

    if python3 -c "from src.database.schema_manager import SchemaManager; SchemaManager().initialize_schema()" 2>&1 | tee /tmp/schema_upgrade.log; then
        print_success "Schema 初始化/升级完成"
    else
        print_error "Schema 初始化/升级失败"
        print_info "查看详细日志: cat /tmp/schema_upgrade.log"
        exit 1
    fi
}

################################################################################
# Step 2: 网络心跳检查（10个代理端口）
################################################################################
check_network_heartbeat() {
    print_step "2" "网络心跳检查"

    # 定义检查的端口
    PROXY_PORTS=(8000 8001 8002 8003 8004 8005 8006 8007 8008 8009)
    TOTAL_PORTS=${#PROXY_PORTS[@]}
    OPEN_PORTS=0

    print_info "检查 ${TOTAL_PORTS} 个代理端口..."

    for port in "${PROXY_PORTS[@]}"; do
        if nc -z localhost $port 2>/dev/null; then
            print_success "端口 $port: 开放"
            ((OPEN_PORTS++))
        else
            print_warning "端口 $port: 关闭（非必需）"
        fi
    done

    echo ""
    print_info "代理端口状态: ${OPEN_PORTS}/${TOTAL_PORTS} 开放"

    # 检查数据库连接（WSL2 桥接）
    if ping -c 1 -W 2 172.25.16.1 &> /dev/null; then
        print_success "WSL2 桥接连接正常 (172.25.16.1)"
    else
        print_warning "WSL2 桥接不可达（可能不在 WSL2 环境）"
    fi

    # 检查外网连接
    if ping -c 1 -W 2 8.8.8.8 &> /dev/null; then
        print_success "外网连接正常"
    else
        print_error "外网连接失败"
        exit 1
    fi
}

################################################################################
# Step 3: 启动监控仪表盘
################################################################################
start_monitoring() {
    print_step "3" "启动监控仪表盘"

    # 检查依赖
    if ! python -c "import rich" &> /dev/null; then
        print_warning "Rich 库未安装，使用基础输出模式"
        print_info "安装: pip install rich"
    fi

    print_info "在后台启动监控脚本..."

    # 创建日志目录
    mkdir -p logs

    # 启动监控（后台）
    nohup python scripts/maintenance/monitor_war_room.py > logs/monitor_war_room.log 2>&1 &
    MONITOR_PID=$!

    # 保存 PID
    echo $MONITOR_PID > .monitor_war_room.pid

    sleep 2

    if ps -p $MONITOR_PID > /dev/null; then
        print_success "监控仪表盘已启动 (PID: $MONITOR_PID)"
        print_info "日志文件: logs/monitor_war_room.log"
        print_info "停止监控: kill $MONITOR_PID"
    else
        print_error "监控仪表盘启动失败"
        return 1
    fi
}

################################################################################
# Step 4: 引导用户选择数据源
################################################################################
select_data_source() {
    print_step "4" "选择数据源并开始收割"

    echo ""
    echo "请选择数据源："
    echo "  1) OddsPortal (终盘赔率)"
    echo "  2) FotMob L2 (详情数据)"
    echo "  3) 全部巡航模式"
    echo "  4) 仅启动监控（暂不收割）"
    echo ""
    read -p "请输入选项 [1-4]: " choice

    case $choice in
        1)
            print_info "启动 OddsPortal 收割..."
            python -m src.api.collectors.odds_production_extractor \
                --source oddsportal \
                --mode cruise \
                --circuit-breaker-enabled
            ;;
        2)
            print_info "启动 FotMob L2 收割..."
            python -m src.api.collectors.fotmob_core \
                --source fotmob \
                --mode cruise \
                --l2-version V145.1
            ;;
        3)
            print_info "启动全部巡航模式..."
            python scripts/production_harvester.py \
                --mode cruise \
                --source all \
                --circuit-breaker-enabled
            ;;
        4)
            print_info "仅监控模式，不启动收割"
            print_info "使用以下命令手动启动收割:"
            echo "  python scripts/production_harvester.py --mode cruise --source all"
            ;;
        *)
            print_error "无效选项"
            return 1
            ;;
    esac
}

################################################################################
# 主函数
################################################################################
main() {
    clear

    print_header "总攻作战室 - Operation '总攻' 启动序列"
    echo ""
    echo -e "${CYAN}版本:${NC} V147.5 Final War Room Ready"
    echo -e "${CYAN}时间:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${CYAN}目标:${NC} 收割 5884 场比赛"
    echo ""

    # 确认启动
    read -p "确认启动总攻作战室？[y/N] " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_warning "启动已取消"
        exit 0
    fi

    # 执行启动步骤
    check_docker_health
    upgrade_database_schema
    check_network_heartbeat
    start_monitoring

    echo ""
    print_header "总攻作战室已准备就绪"

    echo ""
    print_success "✓ Docker 容器健康"
    print_success "✓ Schema 已同步"
    print_success "✓ 网络连接正常"
    print_success "✓ 监控仪表盘运行中"

    echo ""
    print_info "下一步操作:"

    # 询问是否立即开始收割
    read -p "是否立即开始数据收割？[y/N] " start_harvest
    if [[ $start_harvest =~ ^[Yy]$ ]]; then
        select_data_source
    else
        print_info "稍后可使用以下命令手动启动:"
        echo "  python scripts/production_harvester.py --mode cruise --source all"
    fi

    echo ""
    print_header "祝总攻成功！🎯"

    print_info "监控日志: tail -f logs/monitor_war_room.log"
    print_info "停止监控: kill \$(cat .monitor_war_room.pid)"
}

# 执行主函数
main "$@"
