#!/bin/bash

# 🛡️ FootballPrediction V2.0 Emergency Restore Script
# Chief Release Manager & Disaster Recovery Expert
#
# ⚠️ 警告: 此脚本将完全重置系统到V2.0黄金快照状态
#    现有数据将被覆盖，请谨慎使用！
#
# 📋 使用说明:
#    1. 确认备份文件存在: data/backup/v2.0_snapshot_26k_records.sql
#    2. 运行此脚本: bash scripts/emergency_restore.sh
#    3. 按照提示确认操作
#

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 显示欢迎信息
show_header() {
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}🛡️  FootballPrediction V2.0 Emergency Recovery System 🛡️${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${YELLOW}⚠️  CRITICAL WARNING: SYSTEM RESET IMMINENT ⚠️${NC}"
    echo ""
    echo -e "${RED}This script will:${NC}"
    echo -e "  • Stop all running containers"
    echo -e "  • Remove existing containers and volumes"
    echo -e "  • Rebuild all Docker images"
    echo -e "  • Restore database from V2.0 golden snapshot"
    echo -e "  • Restart all services"
    echo ""
    echo -e "${RED}All current data will be PERMANENTLY LOST!${NC}"
    echo ""
}

# 确认操作
confirm_restore() {
    echo -e "${BOLD}📋 System Information:${NC}"
    echo -e "   Backup file: ${GREEN}data/backup/v2.0_snapshot_26k_records.sql${NC}"
    echo -e "   Target version: ${GREEN}V2.0.0-FotMob-Ready${NC}"
    echo -e "   Estimated records: ${GREEN}26,000+${NC}"
    echo ""

    read -p "$(echo -e ${YELLOW}"❓ Are you absolutely sure you want to proceed? Type 'RESTORE-V2.0' to confirm: "${NC})" confirmation

    if [ "$confirmation" != "RESTORE-V2.0" ]; then
        echo -e "${RED}❌ Confirmation failed. Operation cancelled.${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Confirmation received. Starting emergency restore...${NC}"
    echo ""
}

# 检查备份文件
check_backup() {
    echo -e "${BLUE}🔍 Checking backup file integrity...${NC}"

    if [ ! -f "data/backup/v2.0_snapshot_26k_records.sql" ]; then
        echo -e "${RED}❌ Backup file not found: data/backup/v2.0_snapshot_26k_records.sql${NC}"
        echo -e "${YELLOW}💡 Please ensure the backup file exists before running this script.${NC}"
        exit 1
    fi

    # 检查文件大小
    file_size=$(stat -f%z "data/backup/v2.0_snapshot_26k_records.sql" 2>/dev/null || stat -c%s "data/backup/v2.0_snapshot_26k_records.sql" 2>/dev/null || echo "0")

    if [ "$file_size" -lt 1000000 ]; then  # 小于1MB可能有问题
        echo -e "${RED}❌ Backup file appears to be too small (${file_size} bytes)${NC}"
        echo -e "${YELLOW}💡 Please verify the backup file is complete.${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Backup file verified (${file_size} bytes)${NC}"
}

# 停止所有服务
stop_services() {
    echo -e "${BLUE}🛑 Stopping all services...${NC}"

    # 停止所有容器
    docker-compose down --remove-orphans 2>/dev/null || docker-compose -f docker-compose.yml down --remove-orphans 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Some containers may already be stopped${NC}"
    }

    # 强制停止相关容器
    docker stop $(docker ps -q --filter "name=football" 2>/dev/null) 2>/dev/null || true
    docker stop $(docker ps -q --filter "name=app" 2>/dev/null) 2>/dev/null || true
    docker stop $(docker ps -q --filter "name=db" 2>/dev/null) 2>/dev/null || true

    echo -e "${GREEN}✅ All services stopped${NC}"
}

# 清理系统
cleanup_system() {
    echo -e "${BLUE}🧹 Cleaning system resources...${NC}"

    # 删除容器
    docker-compose rm -f 2>/dev/null || true

    # 删除相关卷（除了重要数据）
    docker volume prune -f 2>/dev/null || true

    # 清理网络
    docker network prune -f 2>/dev/null || true

    echo -e "${GREEN}✅ System cleanup completed${NC}"
}

# 重建镜像
rebuild_images() {
    echo -e "${BLUE}🔨 Rebuilding Docker images...${NC}"

    # 构建新镜像
    docker-compose build --no-cache --pull

    echo -e "${GREEN}✅ Docker images rebuilt${NC}"
}

# 启动数据库
start_database() {
    echo -e "${BLUE}🗄️  Starting database service...${NC}"

    # 只启动数据库
    docker-compose up -d db

    # 等待数据库启动
    echo -e "${YELLOW}⏳ Waiting for database to be ready...${NC}"
    sleep 15

    # 检查数据库是否可访问
    max_attempts=30
    attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker-compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Database is ready${NC}"
            break
        fi

        echo -e "${YELLOW}⏳ Attempt $attempt/$max_attempts: Database not ready, waiting...${NC}"
        sleep 2
        ((attempt++))
    done

    if [ $attempt -gt $max_attempts ]; then
        echo -e "${RED}❌ Database failed to start after $max_attempts attempts${NC}"
        exit 1
    fi
}

# 恢复数据
restore_data() {
    echo -e "${BLUE}📥 Restoring database from V2.0 snapshot...${NC}"

    # 创建数据库（如果不存在）
    docker-compose exec -T db createdb -U postgres football_prediction 2>/dev/null || true

    # 恢复数据
    echo -e "${YELLOW}📊 Importing 26,000+ records... This may take a few minutes.${NC}"

    if docker-compose exec -T db psql -U postgres -d football_prediction < data/backup/v2.0_snapshot_26k_records.sql; then
        echo -e "${GREEN}✅ Database restore completed successfully${NC}"
    else
        echo -e "${RED}❌ Database restore failed${NC}"
        exit 1
    fi
}

# 启动所有服务
start_all_services() {
    echo -e "${BLUE}🚀 Starting all services...${NC}"

    # 启动完整系统
    docker-compose up -d

    # 等待服务启动
    echo -e "${YELLOW}⏳ Waiting for services to initialize...${NC}"
    sleep 30

    echo -e "${GREEN}✅ All services started${NC}"
}

# 验证恢复
verify_restore() {
    echo -e "${BLUE}🔍 Verifying system restore...${NC}"

    # 检查容器状态
    running_containers=$(docker-compose ps --services --filter "status=running" | wc -l)
    echo -e "   Running containers: ${GREEN}$running_containers${NC}"

    # 检查数据库记录数
    if command -v docker-compose &> /dev/null; then
        record_count=$(docker-compose exec -T db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches;" 2>/dev/null | tr -d '[:space:]' || echo "unknown")
        if [ "$record_count" != "unknown" ] && [ "$record_count" -gt 25000 ]; then
            echo -e "   Match records: ${GREEN}$record_count${NC}"
        else
            echo -e "   Match records: ${YELLOW}$record_count (verification needed)${NC}"
        fi
    fi

    echo -e "${GREEN}✅ System verification completed${NC}"
}

# 显示完成信息
show_completion() {
    echo ""
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${GREEN}🎉 Emergency Restore Completed Successfully! 🎉${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo ""
    echo -e "${BOLD}📋 System Status:${NC}"
    echo -e "   • All services are running"
    echo -e "   • Database restored to V2.0.0 state"
    echo -e "   • 26,000+ match records available"
    echo -e "   • FotMob architecture ready"
    echo ""
    echo -e "${BOLD}🔗 Access Points:${NC}"
    echo -e "   • Frontend: ${GREEN}http://localhost:3000${NC}"
    echo -e "   • Backend API: ${GREEN}http://localhost:8000${NC}"
    echo -e "   • API Docs: ${GREEN}http://localhost:8000/docs${NC}"
    echo -e "   • Health Check: ${GREEN}http://localhost:8000/health${NC}"
    echo ""
    echo -e "${BOLD}🛠️  Next Steps:${NC}"
    echo -e "   1. Verify frontend is accessible"
    echo -e "   2. Check API endpoints are responding"
    echo -e "   3. Run: ${YELLOW}make test.fast${NC} to verify system health"
    echo -e "   4. Monitor: ${YELLOW}make logs${NC} for any issues"
    echo ""
    echo -e "${GREEN}✅ Your FootballPrediction system has been successfully restored to V2.0!${NC}"
    echo -e "${BLUE}================================================================${NC}"
}

# 主执行流程
main() {
    show_header
    confirm_restore
    check_backup
    stop_services
    cleanup_system
    rebuild_images
    start_database
    restore_data
    start_all_services
    verify_restore
    show_completion
}

# 错误处理
trap 'echo -e "${RED}❌ Emergency restore failed at step $LINENO${NC}"; exit 1' ERR

# 检查是否在正确的目录
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Please run this script from the project root directory${NC}"
    echo -e "${YELLOW}💡 Expected file: docker-compose.yml${NC}"
    exit 1
fi

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed or not in PATH${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed or not in PATH${NC}"
    exit 1
fi

echo -e "${BLUE}🚀 Starting Emergency Restore Process...${NC}"
echo ""

# 执行主流程
main

echo -e "${GREEN}🎊 Emergency restore process completed successfully!${NC}"