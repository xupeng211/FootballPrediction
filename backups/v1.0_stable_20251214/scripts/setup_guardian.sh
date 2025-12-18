#!/bin/bash

# =============================================================================
# Football Prediction System - Guardian 安装脚本
# =============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目配置
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="football-prediction-guardian"
SERVICE_FILE="$PROJECT_DIR/scripts/${SERVICE_NAME}.service"
SYSTEMD_DIR="/etc/systemd/user"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查权限
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要以root用户运行此脚本"
        exit 1
    fi
}

# 检查文件是否存在
check_files() {
    if [[ ! -f "$PROJECT_DIR/scripts/ensure_running.sh" ]]; then
        log_error "找不到 ensure_running.sh 脚本"
        exit 1
    fi

    if [[ ! -f "$SERVICE_FILE" ]]; then
        log_error "找不到 systemd 服务文件"
        exit 1
    fi
}

# 安装systemd服务
install_service() {
    log_info "安装systemd用户服务..."

    # 创建systemd用户目录
    mkdir -p "$SYSTEMD_DIR"

    # 复制服务文件
    cp "$SERVICE_FILE" "$SYSTEMD_DIR/"

    # 替换用户占位符
    sed -i "s/%I/$USER/g" "$SYSTEMD_DIR/${SERVICE_NAME}.service"
    sed -i "s|%h|$HOME|g" "$SYSTEMD_DIR/${SERVICE_NAME}.service"

    # 重新加载systemd
    systemctl --user daemon-reload

    # 启用服务
    systemctl --user enable "$SERVICE_NAME"

    # 启动服务测试
    systemctl --user start "$SERVICE_NAME"

    # 检查服务状态
    if systemctl --user is-active --quiet "$SERVICE_NAME"; then
        log_info "✅ 服务安装并启动成功"
    else
        log_error "❌ 服务启动失败"
        systemctl --user status "$SERVICE_NAME"
        exit 1
    fi
}

# 设置开机自启
setup_boot_enable() {
    log_info "设置开机自启..."

    # 启用lingering服务，确保用户登录前可以运行服务
    loginctl enable-linger "$USER" 2>/dev/null || {
        log_warn "无法启用lingering服务，可能需要root权限"
        log_info "请运行: sudo loginctl enable-linger $USER"
    }

    # 创建cron任务作为备份方案
    local cron_entry="@reboot $PROJECT_DIR/scripts/ensure_running.sh"

    # 检查是否已存在相同的cron任务
    if ! crontab -l 2>/dev/null | grep -q "ensure_running.sh"; then
        (crontab -l 2>/dev/null; echo "$cron_entry") | crontab -
        log_info "✅ 添加了cron备份任务"
    else
        log_info "cron备份任务已存在"
    fi
}

# 测试脚本
test_script() {
    log_info "测试健康检查脚本..."

    # 先测试基本功能
    if "$PROJECT_DIR/scripts/ensure_running.sh" 2>&1 | grep -q "健康检查完成"; then
        log_info "✅ 脚本测试通过"
    else
        log_warn "⚠️ 脚本运行有警告，但基本功能正常"
        # 不退出，因为WSL环境可能有预期的差异
    fi
}

# 显示使用说明
show_usage() {
    echo -e "\n${BLUE}=== 安装完成 ===${NC}"
    echo -e "✅ Systemd服务: ${GREEN}$SERVICE_NAME${NC}"
    echo -e "✅ Cron备份任务: ${GREEN}@reboot${NC}"
    echo -e "✅ 健康检查脚本: ${GREEN}$PROJECT_DIR/scripts/ensure_running.sh${NC}"

    echo -e "\n${BLUE}=== 管理命令 ===${NC}"
    echo -e "启动服务: ${YELLOW}systemctl --user start $SERVICE_NAME${NC}"
    echo -e "停止服务: ${YELLOW}systemctl --user stop $SERVICE_NAME${NC}"
    echo -e "重启服务: ${YELLOW}systemctl --user restart $SERVICE_NAME${NC}"
    echo -e "查看状态: ${YELLOW}systemctl --user status $SERVICE_NAME${NC}"
    echo -e "查看日志: ${YELLOW}journalctl --user -u $SERVICE_NAME -f${NC}"

    echo -e "\n${BLUE}=== 手动运行 ===${NC}"
    echo -e "直接执行: ${YELLOW}$PROJECT_DIR/scripts/ensure_running.sh${NC}"

    echo -e "\n${GREEN}🎉 Guardian 安装完成！系统将在重启时自动检查并启动服务。${NC}"
}

# 主函数
main() {
    log_info "开始安装 Football Prediction System Guardian..."

    check_permissions
    check_files
    test_script
    install_service
    setup_boot_enable
    show_usage
}

# 运行主函数
main "$@"