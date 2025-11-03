#!/bin/bash
# SSL证书自动化管理脚本
# Generated for staging-api.footballprediction.com

set -e

DOMAIN="staging-api.footballprediction.com"
SSL_DIR="./nginx/ssl"
CERT_FILE="$SSL_DIR/$DOMAIN.crt"
KEY_FILE="$SSL_DIR/$DOMAIN.key"
ACME_CHALLENGE_DIR="./nginx/.well-known/acme-challenge"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

# 检查证书是否即将过期
check_certificate_expiry() {
    if [[ -f "$CERT_FILE" ]]; then
        expiry_date=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
        expiry_timestamp=$(date -d "$expiry_date" +%s)
        current_timestamp=$(date +%s)
        days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))

        log "证书将在 $days_until_expiry 天后过期"

        if [[ $days_until_expiry -lt 30 ]]; then
            log "证书将在30天内过期，需要续期"
            return 0
        else
            log "证书仍然有效"
            return 1
        fi
    else
        log "证书文件不存在，需要生成新证书"
        return 0
    fi
}

# 生成自签名证书（用于开发环境）
generate_self_signed_cert() {
    log "生成自签名SSL证书..."

    mkdir -p "$SSL_DIR"

    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/C=CN/ST=Beijing/L=Beijing/O=FootballPrediction/CN=$DOMAIN" \
        -config <(cat /etc/ssl/openssl.cnf <(printf "[SAN]\nsubjectAltName=DNS:$DOMAIN,DNS:www.$DNS,DNS:localhost"))

    log "自签名证书生成完成"
}

# 申请Let's Encrypt证书
request_letsencrypt_cert() {
    log "申请Let's Encrypt证书..."

    # 确保acme-challenge目录存在
    mkdir -p "$ACME_CHALLENGE_DIR"

    # 使用certbot申请证书
    certbot certonly --webroot \
        -w "$ACME_CHALLENGE_DIR" \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" \
        --email admin@$DOMAIN \
        --agree-tos \
        --non-interactive \
        --force-renewal

    # 复制证书到nginx目录
    cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$CERT_FILE"
    cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$KEY_FILE"

    log "Let's Encrypt证书申请完成"
}

# 设置自动续期
setup_auto_renewal() {
    log "设置SSL证书自动续期..."

    # 创建续期脚本
    cat > ./scripts/ssl_renewal.sh << 'EOF'
#!/bin/bash
DOMAIN="staging-api.footballprediction.com"
CERT_FILE="./nginx/ssl/$DOMAIN.crt"

# 检查证书是否需要续期
if openssl x509 -checkend 2592000 -noout -in "$CERT_FILE"; then
    echo "证书仍然有效，无需续期"
    exit 0
fi

echo "证书即将过期，开始续期..."

# 续期证书
certbot renew --quiet

# 重启nginx
docker-compose restart nginx

echo "证书续期完成"
EOF

    chmod +x ./scripts/ssl_renewal.sh

    # 添加到crontab（每天检查一次）
    (crontab -l 2>/dev/null; echo "0 2 * * * $(pwd)/scripts/ssl_renewal.sh") | crontab -

    log "自动续期设置完成"
}

# 验证证书
verify_certificate() {
    log "验证SSL证书..."

    if [[ ! -f "$CERT_FILE" || ! -f "$KEY_FILE" ]]; then
        error_exit "证书文件不存在"
    fi

    # 检查证书有效性
    if openssl x509 -in "$CERT_FILE" -noout -dates; then
        log "证书验证通过"

        # 显示证书信息
        log "证书信息:"
        openssl x509 -in "$CERT_FILE" -noout -subject -issuer -dates

        return 0
    else
        error_exit "证书验证失败"
    fi
}

# 主函数
main() {
    log "开始SSL证书管理流程..."

    case "${1:-check}" in
        "check")
            if check_certificate_expiry; then
                log "需要更新证书"
                request_letsencrypt_cert
                setup_auto_renewal
            fi
            ;;
        "generate")
            generate_self_signed_cert
            ;;
        "renew")
            request_letsencrypt_cert
            ;;
        "verify")
            verify_certificate
            ;;
        "setup")
            setup_auto_renewal
            ;;
        *)
            echo "用法: $0 {check|generate|renew|verify|setup}"
            echo "  check   - 检查证书是否需要续期"
            echo "  generate - 生成自签名证书（开发环境）"
            echo "  renew   - 续期Let's Encrypt证书"
            echo "  verify  - 验证证书"
            echo "  setup   - 设置自动续期"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
