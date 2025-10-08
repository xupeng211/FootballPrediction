#!/bin/bash
# ==================================================
# 足球预测系统生产环境部署脚本
#
# 功能：自动化生产环境部署流程
# 使用方法：./scripts/deploy-production.sh [environment]
# ==================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 默认环境
ENVIRONMENT=${1:-production}

# 配置文件路径
ENV_FILE="$PROJECT_ROOT/.env.$ENVIRONMENT"
ENV_EXAMPLE="$PROJECT_ROOT/.env.production.example"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
DOCKER_COMPOSE_PROD_FILE="$PROJECT_ROOT/docker-compose.prod.yml"

# 检查必要文件
check_required_files() {
    log_info "检查必要文件..."

    if [[ ! -f "$ENV_EXAMPLE" ]]; then
        log_error "环境配置模板文件不存在: $ENV_EXAMPLE"
        exit 1
    fi

    if [[ ! -f "$DOCKER_COMPOSE_FILE" ]]; then
        log_error "Docker Compose文件不存在: $DOCKER_COMPOSE_FILE"
        exit 1
    fi

    log_success "必要文件检查通过"
}

# 检查环境配置文件
check_environment_config() {
    log_info "检查环境配置文件..."

    if [[ ! -f "$ENV_FILE" ]]; then
        log_warning "环境配置文件不存在: $ENV_FILE"
        log_info "创建环境配置文件..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        log_success "环境配置文件已创建: $ENV_FILE"
        log_warning "请编辑 $ENV_FILE 文件，设置正确的配置值"
        exit 1
    fi

    # 检查配置文件中的占位符
    PLACEHOLDERS=$(grep -n "HERE" "$ENV_FILE" | wc -l)
    if [[ $PLACEHOLDERS -gt 0 ]]; then
        log_error "环境配置文件中仍有 $PLACEHOLDERS 个占位符需要设置"
        log_info "请编辑 $ENV_FILE 文件，替换所有 'HERE' 占位符"
        grep -n "HERE" "$ENV_FILE"
        exit 1
    fi

    log_success "环境配置文件检查通过"
}

# 检查系统资源
check_system_resources() {
    log_info "检查系统资源..."

    # 检查内存
    TOTAL_MEMORY=$(free -m | awk 'NR==2{printf "%.1f", $2/1024}')
    log_info "系统内存: ${TOTAL_MEMORY}GB"

    if (( $(echo "$TOTAL_MEMORY < 4.0" | bc -l) )); then
        log_warning "系统内存不足4GB，建议至少8GB"
    fi

    # 检查磁盘空间
    AVAILABLE_DISK=$(df -h . | awk 'NR==2{print $4}')
    log_info "可用磁盘空间: $AVAILABLE_DISK"

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi

    log_success "系统资源检查通过"
}

# 创建生产环境Docker Compose文件
create_production_compose() {
    log_info "创建生产环境Docker Compose配置..."

    cat > "$DOCKER_COMPOSE_PROD_FILE" << 'EOF'
version: '3.8'

services:
  app:
    image: football-prediction:${VERSION:-latest}
    build:
      context: .
      target: production
      args:
        - APP_VERSION=${VERSION:-latest}
    ports:
      - "8000:8000"
      - "8080:8080"  # 指标端口
    env_file:
      - .env.production
    environment:
      - ENVIRONMENT=production
      - DB_HOST=${DB_HOST:-db}
      - DB_PORT=${DB_PORT:-5432}
      - DB_NAME=${DB_NAME:-football_prediction_prod}
      - DB_USER=${DB_USER:-football_user}
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs:rw
      - /var/log/football_prediction:/var/log/football_prediction:rw
    networks:
      - football-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=${POSTGRES_DB:-football_prediction_prod}
      - POSTGRES_USER=${POSTGRES_USER:-football_user}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
      - ./backups:/backups:rw
    ports:
      - "5432:5432"
    networks:
      - football-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-football_user}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.2'

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes --appendfsync everysec --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - football-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.1'

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx:rw
    depends_on:
      - app
    networks:
      - football-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 128M
          cpus: '0.1'

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

networks:
  football-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
EOF

    log_success "生产环境Docker Compose配置已创建: $DOCKER_COMPOSE_PROD_FILE"
}

# 创建SSL证书目录
create_ssl_directory() {
    log_info "创建SSL证书目录..."

    mkdir -p "$PROJECT_ROOT/nginx/ssl"

    # 创建自签名证书（仅用于测试）
    if [[ ! -f "$PROJECT_ROOT/nginx/ssl/cert.pem" ]] || [[ ! -f "$PROJECT_ROOT/nginx/ssl/key.pem" ]]; then
        log_warning "SSL证书不存在，创建自签名证书（仅用于测试）"

        openssl req -x509 -newkey rsa:4096 -nodes -days 365 \
            -keyout "$PROJECT_ROOT/nginx/ssl/key.pem" \
            -out "$PROJECT_ROOT/nginx/ssl/cert.pem" \
            -subj "/C=CN/ST=Beijing/L=Beijing/O=Football Prediction/CN=localhost"

        log_success "自签名SSL证书已创建"
    fi
}

# 创建生产环境Nginx配置
create_nginx_config() {
    log_info "创建生产环境Nginx配置..."

    mkdir -p "$PROJECT_ROOT/nginx"

    cat > "$PROJECT_ROOT/nginx/nginx.prod.conf" << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # 性能优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # 限流配置
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # 上传限制
    client_max_body_size 10M;

    # 上游服务器
    upstream app {
        server app:8000;
        keepalive 32;
    }

    # HTTP重定向到HTTPS
    server {
        listen 80;
        server_name _;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS服务器
    server {
        listen 443 ssl http2;
        server_name _;

        # SSL配置
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # 安全头
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # 健康检查
        location /health {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 健康检查不记录日志
            access_log off;
            log_not_found off;
        }

        # API请求
        location / {
            limit_req zone=api burst=20 nodelay;

            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 超时设置
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;

            # 缓冲设置
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
        }

        # 静态文件
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # 隐藏敏感信息
        location ~ /\. {
            deny all;
        }

        # 隐藏版本信息
        location ~ /(\.env|\.git|\.svn) {
            deny all;
            return 404;
        }
    }
}
EOF

    log_success "生产环境Nginx配置已创建"
}

# 创建日志目录
create_log_directories() {
    log_info "创建日志目录..."

    mkdir -p "$PROJECT_ROOT/logs/nginx"
    mkdir -p "$PROJECT_ROOT/logs/app"
    mkdir -p "$PROJECT_ROOT/backups"
    mkdir -p "$PROJECT_ROOT/data"

    log_success "日志目录已创建"
}

# 验证配置
validate_configuration() {
    log_info "验证配置..."

    # 验证环境变量
    source "$ENV_FILE"

    # 检查必要的环境变量
    REQUIRED_VARS=(
        "SECRET_KEY"
        "DB_PASSWORD"
        "REDIS_PASSWORD"
        "MINIO_ROOT_PASSWORD"
        "JWT_SECRET_KEY"
    )

    for var in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "必要的环境变量未设置: $var"
            exit 1
        fi
    done

    # 验证密码强度
    if [[ ${#SECRET_KEY} -lt 32 ]]; then
        log_error "SECRET_KEY必须至少32个字符"
        exit 1
    fi

    if [[ ${#DB_PASSWORD} -lt 16 ]]; then
        log_error "DB_PASSWORD必须至少16个字符"
        exit 1
    fi

    log_success "配置验证通过"
}

# 部署应用
deploy_application() {
    log_info "开始部署应用..."

    # 构建Docker镜像
    log_info "构建Docker镜像..."
    docker-compose -f "$DOCKER_COMPOSE_PROD_FILE" build --no-cache

    # 启动服务
    log_info "启动服务..."
    docker-compose -f "$DOCKER_COMPOSE_PROD_FILE" up -d

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30

    # 检查服务状态
    log_info "检查服务状态..."
    docker-compose -f "$DOCKER_COMPOSE_PROD_FILE" ps

    # 健康检查
    log_info "执行健康检查..."
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "应用健康检查通过"
    else
        log_error "应用健康检查失败"
        exit 1
    fi

    log_success "应用部署完成"
}

# 主函数
main() {
    log_info "开始生产环境部署..."
    log_info "环境: $ENVIRONMENT"
    log_info "项目目录: $PROJECT_ROOT"

    check_required_files
    check_environment_config
    check_system_resources
    create_production_compose
    create_nginx_config
    create_ssl_directory
    create_log_directories
    validate_configuration
    deploy_application

    log_success "生产环境部署完成！"
    log_info "访问地址: https://localhost"
    log_info "健康检查: https://localhost/health"
    log_info "日志目录: $PROJECT_ROOT/logs"

    # 显示部署信息
    echo -e "\n${GREEN}===========================================${NC}"
    echo -e "${GREEN}  部署成功！${NC}"
    echo -e "${GREEN}===========================================${NC}"
    echo -e "${BLUE}服务状态:${NC}"
    docker-compose -f "$DOCKER_COMPOSE_PROD_FILE" ps
    echo -e "\n${BLUE}常用命令:${NC}"
    echo -e "  查看日志: docker-compose -f $DOCKER_COMPOSE_PROD_FILE logs -f"
    echo -e "  停止服务: docker-compose -f $DOCKER_COMPOSE_PROD_FILE down"
    echo -e "  重启服务: docker-compose -f $DOCKER_COMPOSE_PROD_FILE restart"
    echo -e "  更新服务: docker-compose -f $DOCKER_COMPOSE_PROD_FILE pull && docker-compose -f $DOCKER_COMPOSE_PROD_FILE up -d"
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"' ERR

# 运行主函数
main "$@"
