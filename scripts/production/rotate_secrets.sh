#!/bin/bash

# 密钥轮换脚本
# 用于定期轮换生产环境的敏感密钥

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 配置
ENV_FILE=".env.production"
BACKUP_DIR="backups/secrets"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
create_backup_dir() {
    mkdir -p "$BACKUP_DIR"
}

# 备份当前密钥
backup_secrets() {
    log_info "备份当前密钥..."

    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$BACKUP_DIR/env.production.backup.$DATE"
        log_success "密钥已备份到: $BACKUP_DIR/env.production.backup.$DATE"
    else
        log_error "环境文件不存在: $ENV_FILE"
        exit 1
    fi
}

# 生成新的JWT密钥
generate_jwt_secret() {
    log_info "生成新的JWT密钥..."

    NEW_JWT_SECRET=$(openssl rand -base64 64)

    # 更新环境文件
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$NEW_JWT_SECRET/" "$ENV_FILE"
    else
        # Linux
        sed -i "s/^JWT_SECRET_KEY=.*/JWT_SECRET_SECRET_KEY=$NEW_JWT_SECRET/" "$ENV_FILE"
    fi

    log_success "JWT密钥已更新"
}

# 生成新的数据库密码
generate_db_password() {
    log_info "生成新的数据库密码..."

    NEW_DB_PASSWORD=$(openssl rand -base64 32)

    # 更新环境文件
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/^DB_PASSWORD=.*/DB_PASSWORD=$NEW_DB_PASSWORD/" "$ENV_FILE"
        sed -i '' "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$NEW_DB_PASSWORD/" "$ENV_FILE"
    else
        sed -i "s/^DB_PASSWORD=.*/DB_PASSWORD=$NEW_DB_PASSWORD/" "$ENV_FILE"
        sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$NEW_DB_PASSWORD/" "$ENV_FILE"
    fi

    log_success "数据库密码已更新"
}

# 生成新的Redis密码
generate_redis_password() {
    log_info "生成新的Redis密码..."

    NEW_REDIS_PASSWORD=$(openssl rand -base64 32)

    # 更新环境文件
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD=$NEW_REDIS_PASSWORD/" "$ENV_FILE"
    else
        sed -i "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD=$NEW_REDIS_PASSWORD/" "$ENV_FILE"
    fi

    log_success "Redis密码已更新"
}

# 更新数据库密码
update_database_password() {
    log_info "更新数据库密码..."

    # 连接到数据库并更新密码
    docker-compose -f docker-compose.prod.yml exec db psql -U $DB_USER -d $DB_NAME -c "ALTER USER $DB_USER WITH PASSWORD '$NEW_DB_PASSWORD';"

    log_success "数据库密码已更新"
}

# 更新Redis配置
update_redis_config() {
    log_info "更新Redis配置..."

    # 重启Redis服务以应用新密码
    docker-compose -f docker-compose.prod.yml restart redis

    log_success "Redis密码已更新"
}

# 重启应用服务
restart_services() {
    log_info "重启应用服务..."

    # 重启应用
    docker-compose -f docker-compose.prod.yml restart app

    log_success "服务已重启"
}

# 验证服务
verify_services() {
    log_info "验证服务状态..."

    # 等待服务启动
    sleep 10

    # 检查应用
    if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
        log_success "应用运行正常"
    else
        log_error "应用异常"
        return 1
    fi

    # 检查数据库
    if docker-compose -f docker-compose.prod.yml exec db pg_isready -U $DB_USER > /dev/null 2>&1; then
        log_success "数据库运行正常"
    else
        log_error "数据库异常"
        return 1
    fi

    # 检查Redis
    if docker-compose -f docker-compose.prod.yml exec redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis运行正常"
    else
        log_error "Redis异常"
        return 1
    fi

    log_success "所有服务验证通过"
}

# 清理旧备份
cleanup_old_backups() {
    log_info "清理旧备份（保留30天）..."

    find "$BACKUP_DIR" -name "env.production.backup.*" -mtime +30 -delete

    log_success "旧备份已清理"
}

# 记录密钥轮换
log_rotation() {
    log_info "记录密钥轮换..."

    echo "$(date): 密钥轮换完成" >> "$BACKUP_DIR/rotation.log"
    echo "  - JWT密钥已更新"
    echo "  - 数据库密码已更新"
    echo "  - Redis密码已更新" >> "$BACKUP_DIR/rotation.log"
    echo "" >> "$BACKUP_DIR/rotation.log"

    log_success "密钥轮换已记录"
}

# 主函数
main() {
    log_info "开始密钥轮换..."

    # 检查是否在正确的目录
    if [ ! -f "docker-compose.prod.yml" ]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi

    # 创建备份目录
    create_backup_dir

    # 备份当前密钥
    backup_secrets

    # 生成新密钥
    generate_jwt_secret
    generate_db_password
    generate_redis_password

    # 更新配置
    update_database_password
    update_redis_config

    # 重启服务
    restart_services

    # 验证服务
    if verify_services; then
        # 记录轮换
        log_rotation

        # 清理旧备份
        cleanup_old_backups

        log_success "密钥轮换完成！"
    else
        log_error "服务验证失败，请检查配置"
        log_info "恢复备份的密钥..."
        cp "$BACKUP_DIR/env.production.backup.$DATE" "$ENV_FILE"
        log_error "密钥轮换已回滚"
        exit 1
    fi
}

# 处理命令行参数
case "${1:-all}" in
    jwt)
        create_backup_dir
        backup_secrets
        generate_jwt_secret
        restart_services
        log_success "JWT密钥轮换完成"
        ;;
    db)
        create_backup_dir
        backup_secrets
        generate_db_password
        update_database_password
        restart_services
        log_success "数据库密码轮换完成"
        ;;
    redis)
        create_backup_dir
        backup_secrets
        generate_redis_password
        update_redis_config
        restart_services
        log_success "Redis密码轮换完成"
        ;;
    all)
        main
        ;;
    *)
        echo "用法: $0 {jwt|db|redis|all}"
        echo "  jwt   - 轮换JWT密钥"
        echo "  db    - 轮换数据库密码"
        echo "  redis - 轮换Redis密码"
        echo "  all   - 轮换所有密钥"
        exit 1
        ;;
esac
