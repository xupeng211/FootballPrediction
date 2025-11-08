#!/bin/bash

# SSL/TLS Setup Script for Football Prediction System
# Author: Claude Code
# Version: 1.0
# Purpose: Automated SSL certificate setup with Let's Encrypt

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="${1:-your-domain.com}"
ADMIN_EMAIL="${2:-admin@your-domain.com}"
NGINX_CONF_DIR="/etc/nginx/sites-available"
SSL_DIR="/etc/letsencrypt/live"

# Functions
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

check_prerequisites() {
    log_info "检查系统依赖..."

    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        exit 1
    fi

    # Check domain format
    if [[ ! "$DOMAIN" =~ ^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$ ]]; then
        log_error "域名格式无效: $DOMAIN"
        exit 1
    fi

    # Check email format
    if [[ ! "$ADMIN_EMAIL" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        log_error "邮箱格式无效: $ADMIN_EMAIL"
        exit 1
    fi

    log_success "系统依赖检查通过"
}

install_certbot() {
    log_info "安装Certbot (Let's Encrypt客户端)..."

    # Detect OS
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        apt-get update
        apt-get install -y snapd
        snap install core
        snap refresh core
        snap install --classic certbot
        ln -sf /snap/bin/certbot /usr/bin/certbot
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        yum install -y epel-release
        yum install -y certbot python3-certbot-nginx
    elif command -v dnf &> /dev/null; then
        # Fedora
        dnf install -y certbot python3-certbot-nginx
    else
        log_error "不支持的操作系统，请手动安装certbot"
        exit 1
    fi

    log_success "Certbot安装完成"
}

setup_nginx_ssl_config() {
    log_info "配置Nginx SSL配置..."

    # Create nginx config directory if not exists
    mkdir -p "$NGINX_CONF_DIR"

    # Generate SSL configuration for the domain
    cat > "/tmp/ssl_${DOMAIN}.conf" << EOF
# SSL configuration for $DOMAIN
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    # SSL certificates (will be updated by certbot)
    ssl_certificate $SSL_DIR/$DOMAIN/fullchain.pem;
    ssl_certificate_key $SSL_DIR/$DOMAIN/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy to application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

    # Copy to nginx config directory
    cp "/tmp/ssl_${DOMAIN}.conf" "$NGINX_CONF_DIR/$DOMAIN.conf"

    # Create symlink to enable site
    mkdir -p /etc/nginx/sites-enabled
    ln -sf "$NGINX_CONF_DIR/$DOMAIN.conf" "/etc/nginx/sites-enabled/$DOMAIN.conf"

    # Create certbot webroot directory
    mkdir -p /var/www/certbot

    log_success "Nginx SSL配置完成"
}

obtain_ssl_certificate() {
    log_info "获取SSL证书..."

    # Test nginx configuration
    nginx -t

    # Stop nginx temporarily to free up port 80
    systemctl stop nginx || true

    # Obtain certificate using webroot method
    certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "$ADMIN_EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" \
        --non-interactive

    local cert_result=$?

    # Start nginx again
    systemctl start nginx

    if [ $cert_result -eq 0 ]; then
        log_success "SSL证书获取成功"
    else
        log_error "SSL证书获取失败"
        exit 1
    fi
}

setup_auto_renewal() {
    log_info "设置SSL证书自动续期..."

    # Create renewal cron job
    cat > /etc/cron.d/certbot-renewal << EOF
# SSL certificate auto-renewal
0 12 * * * root /usr/bin/certbot renew --quiet --deploy-hook "systemctl reload nginx" > /var/log/certbot-renewal.log 2>&1
EOF

    # Test renewal
    certbot renew --dry-run

    log_success "SSL证书自动续期设置完成"
}

create_ssl_monitoring() {
    log_info "创建SSL证书监控脚本..."

    cat > /usr/local/bin/ssl-monitor.sh << 'EOF'
#!/bin/bash

# SSL Certificate Monitoring Script
DOMAINS=("your-domain.com" "www.your-domain.com")
ALERT_EMAIL="admin@your-domain.com"
DAYS_WARNING=30

for domain in "${DOMAINS[@]}"; do
    if [ -f "/etc/letsencrypt/live/$domain/cert.pem" ]; then
        expiry_date=$(openssl x509 -in "/etc/letsencrypt/live/$domain/cert.pem" -noout -enddate | cut -d= -f2)
        expiry_epoch=$(date -d "$expiry_date" +%s)
        current_epoch=$(date +%s)
        days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))

        if [ $days_until_expiry -le $DAYS_WARNING ]; then
            echo "警告: $domain 的SSL证书将在 $days_until_expiry 天后过期" | \
                mail -s "SSL证书过期警告" "$ALERT_EMAIL"
        fi
    fi
done
EOF

    chmod +x /usr/local/bin/ssl-monitor.sh

    # Add monitoring cron job (daily check)
    cat > /etc/cron.d/ssl-monitor << EOF
# SSL certificate monitoring
0 9 * * * root /usr/local/bin/ssl-monitor.sh > /var/log/ssl-monitor.log 2>&1
EOF

    log_success "SSL证书监控设置完成"
}

test_ssl_configuration() {
    log_info "测试SSL配置..."

    # Test nginx configuration
    if nginx -t; then
        log_success "Nginx配置测试通过"
    else
        log_error "Nginx配置测试失败"
        exit 1
    fi

    # Reload nginx
    systemctl reload nginx

    # Wait a moment for nginx to start
    sleep 3

    # Test SSL connection
    if curl -sSf "https://$DOMAIN" > /dev/null; then
        log_success "SSL连接测试通过"
    else
        log_warning "SSL连接测试失败，请检查防火墙和DNS配置"
    fi

    # Test SSL certificate
    if command -v openssl &> /dev/null; then
        echo "=== SSL证书信息 ==="
        openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" < /dev/null 2>/dev/null | \
            openssl x509 -noout -dates -subject -issuer

        echo "=== SSL配置评级 ==="
        if command -v ssllabs-scan &> /dev/null; then
            ssllabs-sscan "$DOMAIN" || true
        else
            echo "ssllabs-scan未安装，跳过外部SSL评级"
        fi
    fi
}

generate_summary() {
    log_info "生成配置摘要..."

    cat > "/root/ssl_setup_summary_${DOMAIN}.txt" << EOF
=== SSL配置摘要 ===
域名: $DOMAIN
邮箱: $ADMIN_EMAIL
配置日期: $(date)

证书文件位置:
- 证书: $SSL_DIR/$DOMAIN/fullchain.pem
- 私钥: $SSL_DIR/$DOMAIN/privkey.pem
- 链式证书: $SSL_DIR/$DOMAIN/chain.pem

Nginx配置:
- 配置文件: $NGINX_CONF_DIR/$DOMAIN.conf
- 启用链接: /etc/nginx/sites-enabled/$DOMAIN.conf

自动续期:
- Cron任务: /etc/cron.d/certbot-renewal
- 续期时间: 每天中午12:00

监控:
- 监控脚本: /usr/local/bin/ssl-monitor.sh
- 监控日志: /var/log/ssl-monitor.log
- 警告阈值: 30天

重要提醒:
1. 确保域名DNS正确指向此服务器
2. 确保防火墙开放80和443端口
3. 定期检查证书续期状态
4. 备份证书文件和配置

测试命令:
- 测试Nginx配置: nginx -t
- 测试证书续期: certbot renew --dry-run
- 检查证书状态: certbot certificates
EOF

    log_success "配置摘要已生成: /root/ssl_setup_summary_${DOMAIN}.txt"
}

# Main execution
main() {
    echo "=== SSL/TLS自动配置脚本 ==="
    echo "域名: $DOMAIN"
    echo "邮箱: $ADMIN_EMAIL"
    echo "=================================="

    check_prerequisites
    install_certbot
    setup_nginx_ssl_config
    obtain_ssl_certificate
    setup_auto_renewal
    create_ssl_monitoring
    test_ssl_configuration
    generate_summary

    log_success "SSL/TLS配置完成！"
    echo ""
    echo "📋 下一步操作:"
    echo "1. 确保域名DNS指向此服务器"
    echo "2. 检查防火墙设置: ufw allow 80/tcp && ufw allow 443/tcp"
    echo "3. 重启Nginx: systemctl restart nginx"
    echo "4. 测试网站访问: curl -I https://$DOMAIN"
    echo "5. 查看配置摘要: cat /root/ssl_setup_summary_${DOMAIN}.txt"
}

# Run main function with all arguments
main "$@"