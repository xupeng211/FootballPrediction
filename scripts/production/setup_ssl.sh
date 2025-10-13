#!/bin/bash

# SSL证书配置脚本
# 使用Let's Encrypt自动获取和配置SSL证书

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

# 配置变量
DOMAIN_NAME=""
EMAIL=""
SSL_DIR="./ssl"
NGINX_DIR="./nginx"

# 显示帮助信息
show_help() {
    echo "SSL证书配置脚本"
    echo ""
    echo "用法: $0 -d <domain> -e <email> [--staging]"
    echo ""
    echo "参数:"
    echo "  -d, --domain    域名（必需）"
    echo "  -e, --email     邮箱地址（必需）"
    echo "  -s, --staging   使用Let's Encrypt测试环境"
    echo "  -h, --help      显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -d yourdomain.com -e admin@yourdomain.com"
    echo "  $0 -d yourdomain.com -e admin@yourdomain.com --staging"
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--domain)
                DOMAIN_NAME="$2"
                shift 2
                ;;
            -e|--email)
                EMAIL="$2"
                shift 2
                ;;
            -s|--staging)
                STAGING="--staging"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # 检查必需参数
    if [ -z "$DOMAIN_NAME" ]; then
        log_error "请提供域名参数"
        show_help
        exit 1
    fi

    if [ -z "$EMAIL" ]; then
        log_error "请提供邮箱参数"
        show_help
        exit 1
    fi
}

# 检查系统要求
check_requirements() {
    log_info "检查系统要求..."

    # 检查是否为root用户
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用root权限运行此脚本"
        exit 1
    fi

    # 检查操作系统
    if ! command -v apt &> /dev/null && ! command -v yum &> /dev/null; then
        log_error "不支持的操作系统"
        exit 1
    fi

    # 检查域名是否可解析
    if ! nslookup "$DOMAIN_NAME" > /dev/null 2>&1; then
        log_error "域名无法解析: $DOMAIN_NAME"
        log_info "请确保域名已正确指向此服务器"
        exit 1
    fi

    log_success "系统要求检查通过"
}

# 安装必要软件
install_dependencies() {
    log_info "安装必要软件..."

    # 安装certbot
    if ! command -v certbot &> /dev/null; then
        if command -v apt &> /dev/null; then
            apt update
            apt install -y certbot python3-certbot-nginx
        elif command -v yum &> /dev/null; then
            yum install -y epel-release
            yum install -y certbot python3-certbot-nginx
        fi
        log_success "Certbot已安装"
    else
        log_info "Certbot已存在"
    fi

    # 安装openssl
    if ! command -v openssl &> /dev/null; then
        if command -v apt &> /dev/null; then
            apt install -y openssl
        elif command -v yum &> /dev/null; then
            yum install -y openssl
        fi
        log_success "OpenSSL已安装"
    else
        log_info "OpenSSL已存在"
    fi
}

# 创建必要的目录
create_directories() {
    log_info "创建SSL目录..."

    mkdir -p "$SSL_DIR"
    mkdir -p "$NGINX_DIR/conf.d"

    log_success "目录创建完成"
}

# 生成自签名证书（用于测试）
generate_self_signed_cert() {
    log_info "生成自签名证书（测试用）..."

    # 生成私钥
    openssl genrsa -out "$SSL_DIR/key.pem" 2048

    # 生成证书签名请求
    openssl req -new -key "$SSL_DIR/key.pem" \
        -out "$SSL_DIR/cert.csr" \
        -subj "/C=CN/ST=Beijing/L=Beijing/O=Football Prediction/OU=IT/CN=$DOMAIN_NAME"

    # 生成自签名证书
    openssl x509 -req -days 365 \
        -in "$SSL_DIR/cert.csr" \
        -signkey "$SSL_DIR/key.pem" \
        -out "$SSL_DIR/cert.pem"

    # 删除CSR文件
    rm "$SSL_DIR/cert.csr"

    log_success "自签名证书生成完成"
    log_warning "注意：这是自签名证书，仅用于测试"
}

# 获取Let's Encrypt证书
obtain_letsencrypt_cert() {
    log_info "获取Let's Encrypt证书..."

    # 创建临时Nginx配置
    cat > "$NGINX_DIR/temp-nginx.conf" << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://\$server_name\$request_uri;
    }
}
EOF

    # 创建验证目录
    mkdir -p /var/www/html/.well-known/acme-challenge

    # 停止可能运行的Nginx
    systemctl stop nginx 2>/dev/null || docker-compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true

    # 获取证书
    if certbot certonly \
        --webroot \
        --webroot-path=/var/www/html \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$DOMAIN_NAME" \
        $STAGING; then

        # 复制证书到SSL目录
        cp "/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem" "$SSL_DIR/cert.pem"
        cp "/etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem" "$SSL_DIR/key.pem"

        log_success "Let's Encrypt证书获取成功"
    else
        log_error "Let's Encrypt证书获取失败"
        log_info "尝试使用自签名证书..."
        generate_self_signed_cert
    fi

    # 清理临时文件
    rm -f "$NGINX_DIR/temp-nginx.conf"
}

# 配置Nginx
configure_nginx() {
    log_info "配置Nginx..."

    # 创建Nginx配置
    cat > "$NGINX_DIR/conf.d/ssl.conf" << EOF
# SSL configuration for $DOMAIN_NAME
server {
    listen 80;
    server_name $DOMAIN_NAME;

    # Redirect all HTTP traffic to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN_NAME;

    # SSL configuration
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/certs/key.pem;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Other security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # Client body size
    client_max_body_size 10M;

    # Proxy settings
    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://app:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    log_success "Nginx配置完成"
}

# 设置自动续期
setup_auto_renewal() {
    log_info "设置证书自动续期..."

    # 创建续期脚本
    cat > /usr/local/bin/renew-ssl.sh << 'EOF'
#!/bin/bash

# SSL证书自动续期脚本

DOMAIN=$(grep -E "server_name\s+" /etc/nginx/conf.d/ssl.conf | awk '{print $2}' | head -1)
EMAIL=$(grep -E "email\s+" /etc/letsencrypt/renewal/$DOMAIN.conf | awk '{print $2}' | head -1)

# 续期证书
certbot renew --quiet --post-hook "docker-compose -f /path/to/football-prediction/docker-compose.prod.yml restart nginx"

# 记录日志
echo "$(date): SSL certificate renewed for $DOMAIN" >> /var/log/ssl-renewal.log
EOF

    chmod +x /usr/local/bin/renew-ssl.sh

    # 添加到crontab
    (crontab -l 2>/dev/null; echo "0 3 * * * /usr/local/bin/renew-ssl.sh") | crontab -

    log_success "自动续期设置完成（每天凌晨3点检查）"
}

# 测试SSL配置
test_ssl() {
    log_info "测试SSL配置..."

    # 启动Nginx
    if command -v docker-compose &> /dev/null; then
        docker-compose -f docker-compose.prod.yml up -d nginx
    else
        systemctl start nginx
    fi

    # 等待Nginx启动
    sleep 5

    # 测试HTTPS访问
    if curl -s -f "https://$DOMAIN_NAME/api/health" > /dev/null; then
        log_success "HTTPS访问测试通过"
    else
        log_warning "HTTPS访问测试失败，请检查配置"
    fi

    # 使用ssllabs测试（可选）
    log_info "SSL Labs测试地址: https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN_NAME&hideResults=on"
}

# 显示信息
show_info() {
    log_success "SSL证书配置完成！"
    echo ""
    echo "证书信息："
    echo "  - 域名：$DOMAIN_NAME"
    echo "  - 证书路径：$SSL_DIR/cert.pem"
    echo "  - 私钥路径：$SSL_DIR/key.pem"
    echo "  - Nginx配置：$NGINX_DIR/conf.d/ssl.conf"
    echo ""
    echo "后续操作："
    echo "  1. 更新docker-compose.prod.yml中的SSL挂载路径"
    echo "  2. 重启服务：docker-compose -f docker-compose.prod.yml restart"
    echo "  3. 测试访问：https://$DOMAIN_NAME"
    echo ""
    log_warning "如果使用自签名证书，浏览器会显示安全警告，这是正常的"
}

# 主函数
main() {
    log_info "开始配置SSL证书..."

    # 解析参数
    parse_args "$@"

    # 检查要求
    check_requirements

    # 安装依赖
    install_dependencies

    # 创建目录
    create_directories

    # 获取证书
    if [ -z "$STAGING" ]; then
        obtain_letsencrypt_cert
    else
        log_info "使用Let's Encrypt测试环境"
        obtain_letsencrypt_cert
    fi

    # 配置Nginx
    configure_nginx

    # 设置自动续期
    setup_auto_renewal

    # 测试SSL
    test_ssl

    # 显示信息
    show_info
}

# 运行主函数
main "$@"
