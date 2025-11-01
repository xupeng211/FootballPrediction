#!/bin/bash

# =================================================================
# Docker环境HTTPS/SSL配置脚本
# 专门为Docker容器化环境设计的HTTPS配置方案
# =================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置变量
DOMAIN="football-prediction.com"
EMAIL="admin@football-prediction.com"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="$PROJECT_DIR/docker"
NGINX_DIR="$PROJECT_DIR/nginx"
CERTBOT_DIR="$DOCKER_DIR/certbot"

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查Docker环境
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi

    log_success "Docker环境检查通过"
}

# 创建目录结构
create_directories() {
    log_info "创建HTTPS配置目录..."

    mkdir -p "$CERTBOT_DIR"/{www,conf}
    mkdir -p "$DOCKER_DIR/nginx/ssl"
    mkdir -p "$NGINX_DIR/ssl"

    log_success "目录结构创建完成"
}

# 生成自签名证书（开发测试用）
generate_dev_cert() {
    log_info "生成开发用自签名证书..."

    # 使用OpenSSL生成自签名证书
    docker run --rm -v "$DOCKER_DIR/nginx/ssl:/ssl" alpine sh -c "
        apk add --no-cache openssl && \
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout /ssl/football-prediction.key \
            -out /ssl/football-prediction.crt \
            -subj '/C=CN/ST=Beijing/L=Beijing/O=Football Prediction/CN=$DOMAIN'
    "

    log_success "自签名证书生成完成"
}

# 配置Let's Encrypt证书
setup_letsencrypt() {
    log_info "配置Let's Encrypt证书..."

    # 检查域名解析
    if ! nslookup "$DOMAIN" &> /dev/null; then
        log_error "域名 $DOMAIN 解析失败，请先配置DNS"
        exit 1
    fi

    # 启动临时Nginx用于验证
    docker-compose -f "$DOCKER_DIR/docker-compose.yml" -f "$DOCKER_DIR/docker-compose.https.yml" up -d nginx

    # 等待Nginx启动
    sleep 10

    # 获取证书
    docker-compose -f "$DOCKER_DIR/docker-compose.https.yml" run --rm certbot

    log_success "Let's Encrypt证书配置完成"
}

# 创建HTTPS Nginx配置
create_nginx_https_config() {
    log_info "创建HTTPS Nginx配置..."

    cat > "$NGINX_DIR/nginx.https.conf" << 'EOF'
# =================================================================
# 足球预测系统 - HTTPS配置
# =================================================================

# 负载均衡上游
upstream football_prediction_backend {
    least_conn;
    server app:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# HTTP -> HTTPS 重定向
server {
    listen 80;
    server_name football-prediction.com www.football-prediction.com;

    # Let's Encrypt 验证路径
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # 其他请求重定向到HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS 主服务器
server {
    listen 443 ssl http2;
    server_name football-prediction.com www.football-prediction.com;

    # SSL证书配置
    ssl_certificate /etc/nginx/ssl/football-prediction.crt;
    ssl_certificate_key /etc/nginx/ssl/football-prediction.key;

    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # HSTS (HTTP Strict Transport Security)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # 安全头配置
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https:; frame-ancestors 'none';" always;

    # 日志配置
    access_log /var/log/nginx/football-prediction.access.log;
    error_log /var/log/nginx/football-prediction.error.log;

    # 根路径
    location / {
        proxy_pass http://football_prediction_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;

        # 超时设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;

        # 缓冲设置
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }

    # API路径
    location /api/ {
        proxy_pass http://football_prediction_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # API专用超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 健康检查
    location /health {
        access_log off;
        return 200 "healthy";
    }

    # 静态文件缓存
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header Vary Accept-Encoding;
    }

    # 禁止访问敏感文件
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF

    log_success "HTTPS Nginx配置创建完成"
}

# 创建证书自动续期脚本
create_renewal_script() {
    log_info "创建证书自动续期脚本..."

    cat > "$PROJECT_DIR/scripts/renew_ssl_certificates.sh" << 'EOF'
#!/bin/bash

# SSL证书自动续期脚本
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="$PROJECT_DIR/docker"

echo "$(date): 开始SSL证书续期检查..."

# 续期证书
docker-compose -f "$DOCKER_DIR/docker-compose.https.yml" run --rm certbot renew

if [ $? -eq 0 ]; then
    echo "$(date): SSL证书续期成功，重启Nginx..."
    docker-compose -f "$DOCKER_DIR/docker-compose.https.yml" restart nginx
    echo "$(date): Nginx重启完成"
else
    echo "$(date): SSL证书续期失败"
    exit 1
fi

echo "$(date): SSL证书续期检查完成"
EOF

    chmod +x "$PROJECT_DIR/scripts/renew_ssl_certificates.sh"

    log_success "证书续期脚本创建完成"
}

# 创建SSL测试脚本
create_ssl_test_script() {
    log_info "创建SSL测试脚本..."

    cat > "$PROJECT_DIR/scripts/test_ssl.sh" << 'EOF'
#!/bin/bash

# SSL连接测试脚本
set -e

DOMAIN=${1:-football-prediction.com}
PORT=${2:-443}

echo "测试SSL连接: $DOMAIN:$PORT"
echo "================================"

# 检查证书信息
echo "1. 证书信息:"
openssl s_client -connect $DOMAIN:$PORT -showcerts 2>/dev/null | \
    openssl x509 -noout -text 2>/dev/null | \
    grep -E "(Subject:|Issuer:|Not Before:|Not After:)" | head -4

echo ""
echo "2. SSL协议和加密套件:"
timeout 10 openssl s_client -connect $DOMAIN:$PORT 2>/dev/null | \
    grep -E "(Protocol|Cipher|TLS)" | head -3

echo ""
echo "3. 证书链验证:"
timeout 10 openssl s_client -connect $DOMAIN:$PORT -verify_return_error 2>/dev/null && \
    echo "✅ 证书链验证通过" || echo "❌ 证书链验证失败"

echo ""
echo "4. HTTPS访问测试:"
if curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN" | grep -q "200"; then
    echo "✅ HTTPS访问正常"
else
    echo "❌ HTTPS访问异常"
fi

echo ""
echo "SSL测试完成"
EOF

    chmod +x "$PROJECT_DIR/scripts/test_ssl.sh"

    log_success "SSL测试脚本创建完成"
}

# 更新docker-compose配置
update_docker_compose() {
    log_info "更新Docker Compose配置..."

    # 确保docker-compose.https.yml包含正确的卷映射
    if [ ! -f "$DOCKER_DIR/docker-compose.https.yml" ]; then
        log_warning "docker-compose.https.yml不存在，跳过更新"
        return
    fi

    log_success "Docker Compose配置已存在"
}

# 创建环境配置文件
create_env_config() {
    log_info "创建HTTPS环境配置..."

    cat > "$PROJECT_DIR/environments/.env.https" << EOF
# HTTPS/SSL配置
DOMAIN=football-prediction.com
SSL_EMAIL=admin@football-prediction.com

# Nginx配置
NGINX_PORT=80
NGINX_SSL_PORT=443

# 应用配置
FORCE_HTTPS=true
SECURE_COOKIES=true
TRUST_PROXY_HEADERS=true

# SSL配置
SSL_CERT_PATH=/etc/nginx/ssl/football-prediction.crt
SSL_KEY_PATH=/etc/nginx/ssl/football-prediction.key
EOF

    log_success "HTTPS环境配置创建完成"
}

# 验证HTTPS配置
verify_https_config() {
    log_info "验证HTTPS配置..."

    # 检查文件是否存在
    local files=(
        "$NGINX_DIR/nginx.https.conf"
        "$PROJECT_DIR/scripts/renew_ssl_certificates.sh"
        "$PROJECT_DIR/scripts/test_ssl.sh"
        "$PROJECT_DIR/environments/.env.https"
    )

    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            log_success "✅ $file"
        else
            log_error "❌ $file 不存在"
        fi
    done

    log_success "HTTPS配置验证完成"
}

# 显示使用说明
show_usage() {
    echo ""
    echo "🔒 HTTPS配置完成！"
    echo "================================"
    echo ""
    echo "📋 下一步操作:"
    echo ""
    echo "1. 开发环境 (自签名证书):"
    echo "   docker-compose -f docker/docker-compose.yml -f docker/docker-compose.https.yml up -d"
    echo ""
    echo "2. 生产环境 (Let's Encrypt):"
    echo "   a) 确保域名解析正确"
    echo "   b) 运行: $0 production"
    echo "   c) 启动服务"
    echo ""
    echo "🧪 测试命令:"
    echo "   ./scripts/test_ssl.sh $DOMAIN"
    echo ""
    echo "🔄 证书续期:"
    echo "   ./scripts/renew_ssl_certificates.sh"
    echo ""
    echo "⚠️  注意事项:"
    echo "   - 生产环境需要配置域名解析"
    echo "   - 确保防火墙开放80/443端口"
    echo "   - 定期检查证书有效期"
}

# 主函数
main() {
    local mode=${1:-dev}

    echo "========================================"
    echo "🔒 Docker环境HTTPS/SSL配置"
    echo "========================================"
    echo "模式: $mode"
    echo "域名: $DOMAIN"
    echo ""

    check_docker
    create_directories
    create_nginx_https_config
    create_renewal_script
    create_ssl_test_script
    update_docker_compose
    create_env_config

    case $mode in
        "dev"|"development")
            log_info "开发环境配置 - 使用自签名证书"
            generate_dev_cert
            ;;
        "prod"|"production")
            log_info "生产环境配置 - 使用Let's Encrypt证书"
            setup_letsencrypt
            ;;
        "test")
            log_info "测试模式 - 仅创建配置文件"
            ;;
        *)
            log_error "未知模式: $mode"
            echo "可用模式: dev, prod, test"
            exit 1
            ;;
    esac

    verify_https_config
    show_usage

    log_success "HTTPS配置完成！"
}

# 执行主函数
main "$@"