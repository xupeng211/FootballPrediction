#!/bin/bash

# 环境设置脚本
# Environment Setup Script

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 检查操作系统
check_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        DISTRO=$(lsb_release -si 2>/dev/null || echo "Unknown")
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi

    log_info "检测到操作系统: $OS ($DISTRO)"
}

# 安装Docker
install_docker() {
    if command -v docker &> /dev/null; then
        log_success "Docker已安装"
        return 0
    fi

    log_info "安装Docker..."

    if [[ "$OS" == "linux" ]]; then
        # 安装Docker (Ubuntu/Debian)
        if [[ "$DISTRO" == "Ubuntu" ]] || [[ "$DISTRO" == "Debian" ]]; then
            sudo apt-get update
            sudo apt-get install -y ca-certificates curl gnupg lsb-release

            # 添加Docker官方GPG密钥
            sudo mkdir -p /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

            # 添加Docker仓库
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

            # 安装Docker Engine
            sudo apt-get update
            sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

        elif [[ "$DISTRO" == "CentOS" ]] || [[ "$DISTRO" == "RedHat" ]]; then
            # CentOS/RHEL安装
            sudo yum install -y yum-utils
            sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        fi

    elif [[ "$OS" == "macos" ]]; then
        log_warning "请手动安装Docker Desktop for Mac"
        log_info "下载地址: https://docs.docker.com/docker-for-mac/install/"
        return 1
    fi

    # 启动Docker服务
    sudo systemctl start docker
    sudo systemctl enable docker

    # 添加用户到docker组
    sudo usermod -aG docker $USER

    log_success "Docker安装完成"
    log_warning "请重新登录以使docker组权限生效"
}

# 安装Docker Compose
install_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        log_success "Docker Compose已安装"
        return 0
    fi

    log_info "安装Docker Compose..."

    if [[ "$OS" == "linux" ]]; then
        # 下载Docker Compose
        sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    elif [[ "$OS" == "macos" ]]; then
        log_info "Docker Compose已包含在Docker Desktop中"
    fi

    log_success "Docker Compose安装完成"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."

    local dirs=(
        "logs"
        "logs/app"
        "logs/nginx"
        "backups"
        "data"
        "data/exports"
        "docker/nginx"
        "docker/nginx/ssl"
        "docker/postgresql"
        "docker/redis"
        "docker/prometheus"
        "docker/grafana/provisioning"
        "docker/grafana/provisioning/datasources"
        "docker/grafana/provisioning/dashboards"
        "docker/loki"
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log_info "创建目录: $dir"
    done

    log_success "目录创建完成"
}

# 生成环境配置文件
generate_env_files() {
    log_info "生成环境配置文件..."

    # 生产环境配置
    if [[ ! -f ".env.production" ]]; then
        cat > .env.production << EOF
# 生产环境配置
# Production Environment Configuration

# 应用配置
APP_VERSION=1.0.0
ENV=production
LOG_LEVEL=INFO
SECRET_KEY=$(openssl rand -hex 32)

# 数据库配置
POSTGRES_DB=football_prediction
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$(openssl rand -base64 32)
DATABASE_URL=postgresql://postgres:\${POSTGRES_PASSWORD}@db:5432/football_prediction

# Redis配置
REDIS_PASSWORD=$(openssl rand -base64 32)
REDIS_URL=redis://redis:6379/0

# JWT配置
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 监控配置
GRAFANA_USER=admin
GRAFANA_PASSWORD=$(openssl rand -base64 16)

# 外部服务配置
# SLACK_WEBHOOK_URL=your_slack_webhook_url
# EMAIL_SMTP_HOST=smtp.gmail.com
# EMAIL_SMTP_PORT=587
# EMAIL_USERNAME=your_email@gmail.com
# EMAIL_PASSWORD=your_app_password
EOF
        log_success "创建 .env.production 文件"
    else
        log_warning ".env.production 文件已存在，跳过创建"
    fi

    # 开发环境配置
    if [[ ! -f ".env.development" ]]; then
        cat > .env.development << EOF
# 开发环境配置
# Development Environment Configuration

APP_VERSION=1.0.0-dev
ENV=development
LOG_LEVEL=DEBUG
SECRET_KEY=dev_secret_key_change_in_production

POSTGRES_DB=football_prediction_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=dev_password
DATABASE_URL=postgresql://postgres:dev_password@localhost:5432/football_prediction_dev

REDIS_PASSWORD=dev_redis_password
REDIS_URL=redis://localhost:6379/0

JWT_SECRET_KEY=dev_jwt_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

GRAFANA_USER=admin
GRAFANA_PASSWORD=admin123
EOF
        log_success "创建 .env.development 文件"
    else
        log_warning ".env.development 文件已存在，跳过创建"
    fi
}

# 生成SSL证书（自签名，生产环境请使用正式证书）
generate_ssl_certificates() {
    log_info "生成SSL证书..."

    local ssl_dir="docker/nginx/ssl"

    if [[ ! -f "$ssl_dir/cert.pem" ]] || [[ ! -f "$ssl_dir/key.pem" ]]; then
        # 生成私钥
        openssl genrsa -out "$ssl_dir/key.pem" 2048

        # 生成证书签名请求
        openssl req -new -key "$ssl_dir/key.pem" -out "$ssl_dir/cert.csr" -subj "/C=CN/ST=State/L=City/O=Organization/CN=localhost"

        # 生成自签名证书
        openssl x509 -req -days 365 -in "$ssl_dir/cert.csr" -signkey "$ssl_dir/key.pem" -out "$ssl_dir/cert.pem"

        # 清理临时文件
        rm "$ssl_dir/cert.csr"

        log_success "SSL证书生成完成"
        log_warning "这是自签名证书，生产环境请使用正式SSL证书"
    else
        log_warning "SSL证书已存在，跳过生成"
    fi
}

# 生成Nginx配置
generate_nginx_config() {
    log_info "生成Nginx配置..."

    if [[ ! -f "docker/nginx/nginx.conf" ]]; then
        cat > docker/nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # 基本设置
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # 上游服务器
    upstream app {
        server app:8000;
    }

    # HTTP服务器
    server {
        listen 80;
        server_name localhost;

        # 重定向到HTTPS
        return 301 https://$server_name$request_uri;
    }

    # HTTPS服务器
    server {
        listen 443 ssl http2;
        server_name localhost;

        # SSL配置
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # 安全头
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # API代理
        location /api/ {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 超时设置
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # 健康检查
        location /health {
            proxy_pass http://app/api/v1/health;
            proxy_set_header Host $host;
            access_log off;
        }

        # 静态文件
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # WebSocket支持
        location /ws/ {
            proxy_pass http://app;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF
        log_success "Nginx配置生成完成"
    else
        log_warning "Nginx配置已存在，跳过生成"
    fi
}

# 设置防火墙规则
setup_firewall() {
    log_info "设置防火墙规则..."

    if command -v ufw &> /dev/null; then
        # Ubuntu/Debian使用ufw
        sudo ufw allow 22/tcp    # SSH
        sudo ufw allow 80/tcp    # HTTP
        sudo ufw allow 443/tcp   # HTTPS
        sudo ufw --force enable
        log_success "防火墙规则设置完成 (ufw)"
    elif command -v firewall-cmd &> /dev/null; then
        # CentOS/RHEL使用firewalld
        sudo firewall-cmd --permanent --add-service=ssh
        sudo firewall-cmd --permanent --add-service=http
        sudo firewall-cmd --permanent --add-service=https
        sudo firewall-cmd --reload
        log_success "防火墙规则设置完成 (firewalld)"
    else
        log_warning "未检测到防火墙管理工具，请手动配置防火墙规则"
    fi
}

# 创建systemd服务
create_systemd_service() {
    log_info "创建systemd服务..."

    local service_content="[Unit]
Description=Football Prediction Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$(pwd)
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target"

    echo "$service_content" | sudo tee /etc/systemd/system/football-prediction.service > /dev/null

    # 重新加载systemd并启用服务
    sudo systemctl daemon-reload
    sudo systemctl enable football-prediction.service

    log_success "systemd服务创建完成"
}

# 验证安装
verify_installation() {
    log_info "验证安装..."

    local errors=0

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未正确安装"
        ((errors++))
    else
        log_success "Docker已安装: $(docker --version)"
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未正确安装"
        ((errors++))
    else
        log_success "Docker Compose已安装: $(docker-compose --version)"
    fi

    # 检查配置文件
    local config_files=(
        ".env.production"
        "docker-compose.prod.yml"
        "docker/nginx/nginx.conf"
    )

    for file in "${config_files[@]}"; do
        if [[ -f "$file" ]]; then
            log_success "配置文件存在: $file"
        else
            log_error "配置文件缺失: $file"
            ((errors++))
        fi
    done

    if [[ $errors -eq 0 ]]; then
        log_success "安装验证通过"
        return 0
    else
        log_error "安装验证失败，发现 $errors 个问题"
        return 1
    fi
}

# 显示安装后信息
show_post_install_info() {
    log_success "环境设置完成！"
    echo
    echo "下一步操作："
    echo "1. 编辑 .env.production 文件，配置数据库密码等敏感信息"
    echo "2. 运行生产部署: ./scripts/deployment/production_deploy.sh"
    echo "3. 配置SSL证书（生产环境）"
    echo "4. 设置监控和日志收集"
    echo "5. 配置备份策略"
    echo
    echo "服务管理命令："
    echo "启动服务: sudo systemctl start football-prediction"
    echo "停止服务: sudo systemctl stop football-prediction"
    echo "查看状态: sudo systemctl status football-prediction"
    echo "查看日志: sudo journalctl -u football-prediction -f"
    echo
    echo "重要文件位置："
    echo "环境配置: .env.production"
    echo "Docker配置: docker-compose.prod.yml"
    echo "Nginx配置: docker/nginx/nginx.conf"
    echo "备份目录: backups/"
    echo "日志目录: logs/"
}

# 主函数
main() {
    log_info "开始环境设置..."

    # 解析命令行参数
    SKIP_DOCKER=false
    SKIP_FIREWALL=false
    DEV_MODE=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-docker)
                SKIP_DOCKER=true
                shift
                ;;
            --skip-firewall)
                SKIP_FIREWALL=true
                shift
                ;;
            --dev)
                DEV_MODE=true
                shift
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done

    # 检查操作系统
    check_os

    # 安装Docker（如果未跳过）
    if [[ "$SKIP_DOCKER" != true ]]; then
        install_docker
        install_docker_compose
    fi

    # 创建目录
    create_directories

    # 生成配置文件
    generate_env_files
    generate_nginx_config

    # 生成SSL证书
    if [[ "$DEV_MODE" != true ]]; then
        generate_ssl_certificates
    fi

    # 设置防火墙（如果未跳过）
    if [[ "$SKIP_FIREWALL" != true ]] && [[ "$DEV_MODE" != true ]]; then
        setup_firewall
    fi

    # 创建systemd服务（生产环境）
    if [[ "$DEV_MODE" != true ]]; then
        create_systemd_service
    fi

    # 验证安装
    if verify_installation; then
        show_post_install_info
    else
        log_error "环境设置失败，请检查错误信息"
        exit 1
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi