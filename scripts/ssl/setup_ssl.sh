#!/bin/bash

# =================================================================
# 足球预测系统 - SSL 证书自动化设置脚本
# =================================================================

set -e

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

# 检查是否以 root 权限运行
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要 root 权限运行"
        log_info "请使用: sudo $0"
        exit 1
    fi
}

# 检查域名是否配置
check_domain() {
    if [[ -z "$DOMAIN" ]]; then
        log_error "请设置域名环境变量"
        log_info "使用方法: DOMAIN=your-domain.com $0"
        exit 1
    fi

    log_info "使用域名: $DOMAIN"
}

# 安装依赖
install_dependencies() {
    log_info "安装 SSL 证书相关依赖..."

    # 更新包列表
    apt update

    # 安装必要软件包
    apt install -y \
        certbot \
        python3-certbot-nginx \
        openssl \
        curl \
        dnsutils \
        socat

    log_success "依赖安装完成"
}

# 创建必要的目录
create_directories() {
    log_info "创建 SSL 证书目录..."

    mkdir -p /etc/letsencrypt/live/$DOMAIN
    mkdir -p /etc/letsencrypt/archive/$DOMAIN
    mkdir -p /var/lib/letsencrypt
    mkdir -p /var/www/certbot

    log_success "目录创建完成"
}

# 检查 DNS 解析
check_dns() {
    log_info "检查域名 DNS 解析..."

    # 检查 A 记录
    if nslookup $DOMAIN > /dev/null 2>&1; then
        local ip=$(nslookup $DOMAIN | grep -A1 "Name:" | grep "Address:" | awk '{print $2}' | head -1)
        log_success "域名 $DOMAIN 解析到 IP: $ip"
    else
        log_error "域名 $DNS 解析失败"
        log_info "请确保域名已正确配置 A 记录指向此服务器"
        exit 1
    fi
}

# 生成自签名证书 (开发/测试环境)
generate_self_signed_cert() {
    log_info "生成自签名 SSL 证书..."

    local ssl_dir="/home/user/projects/FootballPrediction/nginx/ssl"

    # 生成私钥
    openssl genrsa -out "$ssl_dir/football-prediction.key" 2048

    # 生成证书签名请求
    openssl req -new -key "$ssl_dir/football-prediction.key" -out "$ssl_dir/football-prediction.csr" -subj "/C=CN/ST=Beijing/L=Beijing/O=Football Prediction/CN=$DOMAIN"

    # 生成自签名证书
    openssl x509 -req -days 365 -in "$ssl_dir/football-prediction.csr" -signkey "$ssl_dir/football-prediction.key" -out "$ssl_dir/football-prediction.crt"

    # 设置权限
    chmod 600 "$ssl_dir/football-prediction.key"
    chmod 644 "$ssl_dir/football-prediction.crt"

    # 清理临时文件
    rm -f "$ssl_dir/football-prediction.csr"

    log_success "自签名证书生成完成"
    log_warning "注意: 自签名证书会被浏览器显示为不安全，仅适用于开发测试"
}

# 申请 Let's Encrypt 证书 (生产环境)
request_letsencrypt_cert() {
    log_info "申请 Let's Encrypt SSL 证书..."

    # 检查 Nginx 配置
    if ! pgrep nginx > /dev/null; then
        log_info "启动 Nginx 以进行域名验证..."
        systemctl start nginx || nginx -c /home/user/projects/FootballPrediction/nginx/nginx.prod.conf
    fi

    # 申请证书
    certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email admin@$DOMAIN \
        --agree-tos \
        --no-eff-email \
        --force-renewal \
        -d $DOMAIN \
        -d www.$DOMAIN

    # 复制证书到项目目录
    cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem /home/user/projects/FootballPrediction/nginx/ssl/football-prediction.crt
    cp /etc/letsencrypt/live/$DOMAIN/privkey.pem /home/user/projects/FootballPrediction/nginx/ssl/football-prediction.key

    # 设置权限
    chmod 600 /home/user/projects/FootballPrediction/nginx/ssl/football-prediction.key
    chmod 644 /home/user/projects/FootballPrediction/nginx/ssl/football-prediction.crt

    log_success "Let's Encrypt 证书申请完成"
}

# 设置自动续期
setup_auto_renewal() {
    log_info "设置 SSL 证书自动续期..."

    # 创建续期脚本
    cat > /etc/cron.daily/certbot-renewal << 'EOF'
#!/bin/bash
# SSL 证书自动续期脚本

/usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"

# 检查续期是否成功
if [ $? -eq 0 ]; then
    logger "SSL certificate renewal successful"
else
    logger "SSL certificate renewal failed"
fi
EOF

    # 设置执行权限
    chmod +x /etc/cron.daily/certbot-renewal

    # 添加到 crontab (每天凌晨2点检查)
    (crontab -l 2>/dev/null; echo "0 2 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -

    log_success "自动续期设置完成"
}

# 测试 SSL 配置
test_ssl_config() {
    log_info "测试 SSL 配置..."

    local ssl_dir="/home/user/projects/FootballPrediction/nginx/ssl"

    # 检查证书文件
    if [[ -f "$ssl_dir/football-prediction.crt" && -f "$ssl_dir/football-prediction.key" ]]; then
        log_success "SSL 证书文件存在"

        # 检查证书有效期
        local expiry_date=$(openssl x509 -enddate -noout -in "$ssl_dir/football-prediction.crt" | cut -d= -f2)
        log_info "证书有效期至: $expiry_date"

        # 验证证书和私钥匹配
        local cert_modulus=$(openssl x509 -noout -modulus -in "$ssl_dir/football-prediction.crt" | openssl md5)
        local key_modulus=$(openssl rsa -noout -modulus -in "$ssl_dir/football-prediction.key" | openssl md5)

        if [[ "$cert_modulus" == "$key_modulus" ]]; then
            log_success "证书和私钥匹配"
        else
            log_error "证书和私钥不匹配"
            return 1
        fi
    else
        log_error "SSL 证书文件不存在"
        return 1
    fi
}

# 更新 Nginx 配置中的域名
update_nginx_config() {
    log_info "更新 Nginx 配置中的域名..."

    local nginx_conf="/home/user/projects/FootballPrediction/nginx/nginx.prod.conf"

    # 替换域名配置
    sed -i "s/your-domain.com/$DOMAIN/g" "$nginx_conf"

    log_success "Nginx 配置更新完成"
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙规则..."

    # 检查 UFW 是否安装
    if command -v ufw > /dev/null; then
        # 允许 HTTP 和 HTTPS
        ufw allow 80/tcp
        ufw allow 443/tcp

        # 允许 SSH (如果尚未允许)
        ufw allow ssh

        log_info "UFW 防火墙规则已更新"
    else
        log_warning "UFW 未安装，请手动配置防火墙允许 80 和 443 端口"
    fi
}

# 创建 SSL 验证脚本
create_ssl_check_script() {
    log_info "创建 SSL 证书检查脚本..."

    cat > /usr/local/bin/check-ssl.sh << 'EOF'
#!/bin/bash

# SSL 证书状态检查脚本

DOMAIN=$1
if [[ -z "$DOMAIN" ]]; then
    echo "使用方法: $0 domain.com"
    exit 1
fi

echo "检查 $DOMAIN 的 SSL 证书状态..."

# 检查证书有效期
if echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -dates; then
    echo "SSL 证书检查完成"
else
    echo "SSL 证书检查失败"
    exit 1
fi
EOF

    chmod +x /usr/local/bin/check-ssl.sh

    log_success "SSL 检查脚本创建完成"
}

# 主函数
main() {
    log_info "开始 SSL 证书设置流程..."

    # 检查参数和权限
    check_root
    check_domain

    # 显示菜单
    echo "请选择 SSL 证书类型:"
    echo "1) Let's Encrypt 证书 (生产环境推荐)"
    echo "2) 自签名证书 (开发测试环境)"
    read -p "请输入选择 [1-2]: " choice

    case $choice in
        1)
            log_info "选择 Let's Encrypt 证书"
            install_dependencies
            create_directories
            check_dns
            update_nginx_config
            request_letsencrypt_cert
            setup_auto_renewal
            ;;
        2)
            log_info "选择自签名证书"
            generate_self_signed_cert
            update_nginx_config
            ;;
        *)
            log_error "无效选择"
            exit 1
            ;;
    esac

    # 后续配置
    configure_firewall
    create_ssl_check_script
    test_ssl_config

    # 重启 Nginx
    if pgrep nginx > /dev/null; then
        systemctl reload nginx
        log_info "Nginx 已重新加载配置"
    fi

    log_success "SSL 证书设置完成!"
    echo
    echo "证书信息:"
    echo "- 域名: $DOMAIN"
    echo "- 证书文件: /home/user/projects/FootballPrediction/nginx/ssl/football-prediction.crt"
    echo "- 私钥文件: /home/user/projects/FootballPrediction/nginx/ssl/football-prediction.key"
    echo
    echo "下一步:"
    echo "1. 启动生产环境: docker-compose -f docker-compose.prod.yml up -d"
    echo "2. 测试 HTTPS 访问: https://$DOMAIN"
    echo "3. 检查证书状态: check-ssl.sh $DOMAIN"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi