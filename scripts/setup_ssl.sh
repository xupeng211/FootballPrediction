#!/bin/bash
# SSL证书配置脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."

    if ! command -v openssl &> /dev/null; then
        log_error "OpenSSL 未安装"
        exit 1
    fi

    if ! command -v certbot &> /dev/null; then
        log_warn "Certbot 未安装，将使用自签名证书"
        USE_SELFSIGNED=true
    else
        USE_SELFSIGNED=false
    fi
}

# 生成自签名证书
generate_selfsigned_cert() {
    local domain=$1
    local cert_dir="${2:-./ssl}"

    log_info "生成自签名证书..."

    # 创建证书目录
    mkdir -p "$cert_dir"

    # 生成私钥
    openssl genrsa -out "$cert_dir/private.key" 2048

    # 生成证书签名请求
    openssl req -new -key "$cert_dir/private.key" -out "$cert_dir/cert.csr" -subj "/C=CN/ST=State/L=City/O=Organization/CN=$domain"

    # 生成自签名证书
    openssl x509 -req -days 365 -in "$cert_dir/cert.csr" -signkey "$cert_dir/private.key" -out "$cert_dir/certificate.crt"

    # 清理CSR文件
    rm "$cert_dir/cert.csr"

    log_info "自签名证书已生成:"
    log_info "  私钥: $cert_dir/private.key"
    log_info "  证书: $cert_dir/certificate.crt"

    # 设置权限
    chmod 600 "$cert_dir/private.key"
    chmod 644 "$cert_dir/certificate.crt"
}

# 使用Let's Encrypt获取证书
obtain_letsencrypt_cert() {
    local domain=$1
    local email=$2
    local cert_dir="${3:-/etc/ssl/certs}"

    log_info "使用Let's Encrypt获取证书..."

    # 创建临时目录
    local temp_dir="/tmp/letsencrypt"
    mkdir -p "$temp_dir"

    # 获取证书
    certbot certonly \
        --standalone \
        --email "$email" \
        --agree-tos \
        --no-eff-email \
        -d "$domain" \
        --cert-name "$domain" \
        --staple-ocsp \
        --must-staple

    # 复制证书到目标目录
    sudo mkdir -p "$cert_dir"
    sudo cp "/etc/letsencrypt/live/$domain/fullchain.pem" "$cert_dir/certificate.crt"
    sudo cp "/etc/letsencrypt/live/$domain/privkey.pem" "$cert_dir/private.key"

    log_info "Let's Encrypt证书已获取:"
    log_info "  私钥: $cert_dir/private.key"
    log_info "  证书: $cert_dir/certificate.crt"
}

# 配置自动续期
setup_auto_renewal() {
    local domain=$1

    log_info "配置证书自动续期..."

    # 创建cron任务
    local cron_job="0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'"

    # 检查是否已存在
    if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
        (crontab -l 2>/dev/null; echo "$cron_job") | crontab -
        log_info "自动续期任务已添加到cron"
    else
        log_warn "自动续期任务已存在"
    fi
}

# 生成Nginx配置
generate_nginx_config() {
    local domain=$1
    local cert_dir="${2:-./ssl}"
    local config_file="nginx.conf"

    log_info "生成Nginx配置..."

    cat > "$config_file" << EOF
server {
    listen 80;
    server_name $domain;

    # 重定向到HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $domain;

    # SSL配置
    ssl_certificate $cert_dir/certificate.crt;
    ssl_certificate_key $cert_dir/private.key;

    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # 其他安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # 代理到FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    log_info "Nginx配置已生成: $config_file"
}

# 测试SSL配置
test_ssl_config() {
    local domain=$1
    local cert_dir="${2:-./ssl}"

    log_info "测试SSL配置..."

    # 检查证书有效期
    if [ -f "$cert_dir/certificate.crt" ]; then
        local exp_date=$(openssl x509 -enddate -noout -in "$cert_dir/certificate.crt" | cut -d= -f2)
        log_info "证书有效期至: $exp_date"

        # 检查证书是否即将过期
        local exp_timestamp=$(date -d "$exp_date" +%s)
        local current_timestamp=$(date +%s)
        local days_until_expiry=$(( (exp_timestamp - current_timestamp) / 86400 ))

        if [ $days_until_expiry -lt 30 ]; then
            log_warn "证书将在 $days_until_expiry 天后过期"
        else
            log_info "证书有效期为 $days_until_expiry 天"
        fi
    fi

    # 检查SSL Labs评分（如果有域名）
    if [ "$domain" != "localhost" ]; then
        log_info "可以通过 https://www.ssllabs.com/ssltest/ 测试SSL配置"
    fi
}

# 主函数
main() {
    echo "=========================================="
    echo "FootballPrediction SSL配置工具"
    echo "=========================================="

    # 获取域名
    echo
    read -p "请输入域名 (默认: localhost): " DOMAIN
    DOMAIN=${DOMAIN:-localhost}

    # 获取邮箱（用于Let's Encrypt）
    if [ "$DOMAIN" != "localhost" ]; then
        read -p "请输入邮箱地址: " EMAIL
        if [ -z "$EMAIL" ]; then
            log_error "Let's Encrypt需要邮箱地址"
            exit 1
        fi
    fi

    # 选择证书类型
    echo
    echo "请选择证书类型:"
    echo "1. Let's Encrypt证书 (生产环境推荐)"
    echo "2. 自签名证书 (开发/测试)"
    read -p "请选择 (1/2): " CHOICE

    # 检查依赖
    check_dependencies

    # 创建证书目录
    CERT_DIR="./ssl"
    mkdir -p "$CERT_DIR"

    # 获取证书
    if [ "$CHOICE" = "1" ] && [ "$DOMAIN" != "localhost" ] && [ "$USE_SELFSIGNED" = false ]; then
        obtain_letsencrypt_cert "$DOMAIN" "$EMAIL" "$CERT_DIR"
        setup_auto_renewal "$DOMAIN"
    else
        generate_selfsigned_cert "$DOMAIN" "$CERT_DIR"
        if [ "$DOMAIN" != "localhost" ]; then
            log_warn "使用自签名证书，浏览器会显示安全警告"
        fi
    fi

    # 生成Nginx配置
    generate_nginx_config "$DOMAIN" "$CERT_DIR"

    # 测试配置
    test_ssl_config "$DOMAIN" "$CERT_DIR"

    # 完成
    echo
    echo "=========================================="
    log_info "SSL配置完成!"
    echo
    echo "下一步:"
    echo "1. 将证书部署到服务器"
    echo "2. 安装并配置Nginx"
    echo "3. 更新环境变量"
    echo "   SSL_CERT_PATH=$CERT_DIR/certificate.crt"
    echo "   SSL_KEY_PATH=$CERT_DIR/private.key"
    echo "=========================================="
}

# 运行主函数
main "$@"
