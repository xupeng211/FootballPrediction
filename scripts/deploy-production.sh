#!/bin/bash
# 生产环境部署脚本
# Production Deployment Script

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} \$1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} \$1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} \$1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} \$1"
}

# 检查依赖
check_dependencies() {
    log_info "检查部署依赖..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi

    # 检查Docker服务状态
    if ! docker info &> /dev/null; then
        log_error "Docker 服务未运行"
        exit 1
    fi

    log_success "依赖检查通过"
}

# 环境配置
setup_environment() {
    log_info "配置生产环境..."

    # 创建必要的目录
    mkdir -p logs/nginx logs/app logs/celery data postgres_data redis_data influxdb_data influxdb_config
    mkdir -p monitoring/grafana/dashboards monitoring/grafana/datasources
    mkdir -p nginx/ssl

    # 设置权限
    chmod 755 logs data monitoring nginx

    # 检查环境变量文件
    if [ ! -f .env.production ]; then
        log_warning ".env.production 文件不存在，创建默认配置..."
        cat > .env.production << 'EOFF'
# 生产环境配置
ENV=production

# 数据库配置
POSTGRES_PASSWORD=football_prod_password_2024
REDIS_PASSWORD=redis_prod_password_2024

# InfluxDB配置
INFLUXDB_PASSWORD=influxdb_prod_password_2024
INFLUXDB_TOKEN=influxdb_prod_token_2024_very_secure

# Grafana配置
GRAFANA_PASSWORD=grafana_admin_2024

# SSL证书配置
SSL_CERT_PATH=./nginx/ssl/cert.pem
SSL_KEY_PATH=./nginx/ssl/key.pem
EOFF
        log_info "已创建 .env.production 文件，请根据需要修改配置"
    fi

    # 加载环境变量
    source .env.production

    log_success "环境配置完成"
}

# 构建Docker镜像
build_images() {
    log_info "构建Docker镜像..."

    # 构建主应用镜像
    log_info "构建主应用镜像..."
    docker build -f Dockerfile.production -t football-prediction-app:latest .

    # 构建质量监控镜像
    log_info "构建质量监控镜像..."
    docker build -f Dockerfile.quality-monitor -t football-quality-monitor:latest .

    # 构建前端镜像
    log_info "构建前端监控面板镜像..."
    cd frontend/quality-dashboard
    docker build -t football-quality-dashboard:latest .
    cd ../..

    log_success "Docker镜像构建完成"
}

# 生成SSL证书
generate_ssl_cert() {
    log_info "生成SSL证书..."

    if [ ! -f nginx/ssl/cert.pem ] || [ ! -f nginx/ssl/key.pem ]; then
        # 生成自签名证书（生产环境建议使用Let's Encrypt）
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\
            -keyout nginx/ssl/key.pem \\
            -out nginx/ssl/cert.pem \\
            -subj "/C=CN/ST=State/L=City/O=Organization/CN=football-prediction.com"

        log_success "SSL证书生成完成（自签名）"
        log_warning "生产环境建议使用Let's Encrypt或其他CA证书"
    else
        log_info "SSL证书已存在，跳过生成"
    fi
}

# 创建Nginx配置
create_nginx_config() {
    log_info "创建Nginx配置..."

    cat > nginx/nginx.conf << 'NGINXEOF'
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent" "\$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 100M;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
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

    # 上游服务器
    upstream app_backend {
        server app:8000;
    }

    upstream quality_monitor_backend {
        server quality-monitor:8001;
    }

    upstream dashboard_backend {
        server quality-dashboard:80;
    }

    # HTTP重定向到HTTPS
    server {
        listen 80;
        server_name _;
        return 301 https://\$server_name\$request_uri;
    }

    # HTTPS主服务器
    server {
        listen 443 ssl http2;
        server_name _;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_session_timeout 1d;
        ssl_session_cache shared:MozTLS:10m;
        ssl_session_tickets off;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;

        # 安全头
        add_header Strict-Transport-Security "max-age=63072000" always;
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Referrer-Policy "no-referrer-when-downgrade";

        # API代理
        location /api/ {
            proxy_pass http://app_backend/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # WebSocket代理
        location /ws/ {
            proxy_pass http://quality_monitor_backend/ws/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            proxy_read_timeout 86400s;
        }

        # 质量监控API
        location /quality-api/ {
            proxy_pass http://quality_monitor_backend/api/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        # 监控面板
        location /dashboard/ {
            proxy_pass http://dashboard_backend/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        # 健康检查
        location /health {
            access_log off;
            return 200 "healthy\\n";
            add_header Content-Type text/plain;
        }

        # 静态文件缓存
        location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)\$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # 默认路由
        location / {
            return 301 https://\$server_name/dashboard/;
        }
    }
}
NGINXEOF

    log_success "Nginx配置创建完成"
}

# 启动服务
deploy_services() {
    log_info "部署生产环境服务..."

    # 停止现有服务
    log_info "停止现有服务..."
    docker-compose -f docker-compose.production.yml down || true

    # 清理悬空镜像
    log_info "清理悬空镜像..."
    docker image prune -f

    # 启动数据库服务
    log_info "启动数据库服务..."
    docker-compose -f docker-compose.production.yml up -d postgres redis influxdb

    # 等待数据库启动
    log_info "等待数据库服务启动..."
    sleep 30

    # 运行数据库迁移
    log_info "运行数据库迁移..."
    docker-compose -f docker-compose.production.yml run --rm app python -m alembic upgrade head || true

    # 启动所有服务
    log_info "启动所有服务..."
    docker-compose -f docker-compose.production.yml up -d

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 60

    log_success "服务部署完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    # 检查主应用
    if curl -f http://localhost/api/health > /dev/null 2>&1; then
        log_success "✅ 主应用健康"
    else
        log_error "❌ 主应用不健康"
    fi

    # 检查质量监控
    if curl -f http://localhost/quality-api/health > /dev/null 2>&1; then
        log_success "✅ 质量监控服务健康"
    else
        log_error "❌ 质量监控服务不健康"
    fi

    # 检查监控面板
    if curl -f http://localhost/dashboard/ > /dev/null 2>&1; then
        log_success "✅ 监控面板健康"
    else
        log_error "❌ 监控面板不健康"
    fi

    # 检查数据库连接
    if docker-compose -f docker-compose.production.yml exec postgres pg_isready -U football_user > /dev/null 2>&1; then
        log_success "✅ PostgreSQL健康"
    else
        log_error "❌ PostgreSQL不健康"
    fi

    # 检查Redis
    if docker-compose -f docker-compose.production.yml exec redis redis-cli ping > /dev/null 2>&1; then
        log_success "✅ Redis健康"
    else
        log_error "❌ Redis不健康"
    fi

    # 检查InfluxDB
    if curl -f http://localhost:8086/health > /dev/null 2>&1; then
        log_success "✅ InfluxDB健康"
    else
        log_error "❌ InfluxDB不健康"
    fi
}

# 显示部署信息
show_deployment_info() {
    log_info "🎉 生产环境部署完成！"
    echo ""
    echo "📊 服务访问地址："
    echo "  • 主应用API: http://localhost/api/"
    echo "  • 质量监控API: http://localhost/quality-api/"
    echo "  • 监控面板: http://localhost/dashboard/"
    echo "  • Grafana监控: http://localhost:3001 (admin/\${GRAFANA_PASSWORD})"
    echo "  • Prometheus: http://localhost:9090"
    echo ""
    echo "🔧 管理命令："
    echo "  • 查看日志: docker-compose -f docker-compose.production.yml logs -f"
    echo "  • 重启服务: docker-compose -f docker-compose.production.yml restart"
    echo "  • 停止服务: docker-compose -f docker-compose.production.yml down"
    echo ""
    echo "📋 重要文件："
    echo "  • 环境配置: .env.production"
    echo "  • Nginx配置: nginx/nginx.conf"
    echo "  • 服务配置: docker-compose.production.yml"
    echo ""
    echo "🔐 安全提醒："
    echo "  • 已生成自签名SSL证书，生产环境建议使用CA证书"
    echo "  • 请定期更新密码和密钥"
    echo "  • 建议配置防火墙规则"
    echo ""
}

# 清理函数
cleanup() {
    log_info "清理临时文件..."
    # 这里可以添加清理逻辑
}

# 主函数
main() {
    log_info "🚀 开始生产环境部署..."

    # 记录开始时间
    start_time=\$(date +%s)

    # 执行部署步骤
    check_dependencies
    setup_environment
    generate_ssl_cert
    create_nginx_config
    build_images
    deploy_services
    health_check

    # 计算总耗时
    end_time=\$(date +%s)
    duration=\$((end_time - start_time))

    # 显示部署信息
    show_deployment_info

    log_success "🎉 生产环境部署完成！总耗时: \${duration}秒"

    # 清理
    cleanup
}

# 信号处理
trap cleanup EXIT

# 执行主函数
main "\$@"
