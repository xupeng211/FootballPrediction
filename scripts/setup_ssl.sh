#!/bin/bash
# SSL证书配置和安全加固脚本
# SSL Certificate Setup and Security Hardening Script

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

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        exit 1
    fi
}

# 安装必要工具
install_prerequisites() {
    log_info "安装SSL配置必需工具..."

    apt-get update
    apt-get install -y curl wget openssl certbot python3-certbot-nginx

    log_success "工具安装完成"
}

# 创建SSL目录结构
create_ssl_directories() {
    log_info "创建SSL目录结构..."

    mkdir -p /etc/ssl/football-prediction
    mkdir -p /etc/ssl/certs
    mkdir -p /etc/ssl/private
    mkdir -p /var/log/ssl
    mkdir -p /etc/nginx/ssl

    # 设置权限
    chmod 700 /etc/ssl/private
    chmod 755 /etc/ssl/certs
    chmod 755 /etc/ssl/football-prediction

    log_success "SSL目录结构创建完成"
}

# 生成自签名证书（用于开发/测试）
generate_self_signed_cert() {
    local domain=${1:-football-prediction.localhost}

    log_info "生成自签名证书 for $domain..."

    # 生成私钥
    openssl genrsa -out /etc/ssl/private/$domain.key 4096
    chmod 600 /etc/ssl/private/$domain.key

    # 生成证书签名请求
    openssl req -new -key /etc/ssl/private/$domain.key \
        -out /etc/ssl/certs/$domain.csr \
        -subj "/C=CN/ST=State/L=City/O=Football-Prediction/OU=IT/CN=$domain"

    # 生成自签名证书
    openssl x509 -req -days 365 \
        -in /etc/ssl/certs/$domain.csr \
        -signkey /etc/ssl/private/$domain.key \
        -out /etc/ssl/certs/$domain.crt

    # 生成证书链
    cat /etc/ssl/certs/$domain.crt > /etc/ssl/football-prediction/$domain.pem

    log_success "自签名证书生成完成: $domain"
}

# 配置Let's Encrypt证书
setup_letsencrypt_cert() {
    local domain=${1:-football-prediction.com}
    local email=${2:-admin@football-prediction.com}

    log_info "配置Let's Encrypt证书 for $domain..."

    # 检查域名解析
    log_info "检查域名解析..."
    if ! nslookup $domain &> /dev/null; then
        log_error "域名 $domain 解析失败，请先配置DNS"
        exit 1
    fi

    # 获取Let's Encrypt证书
    log_info "获取Let's Encrypt证书..."
    certbot certonly --standalone \
        --email $email \
        --agree-tos \
        --non-interactive \
        --rsa-key-size 4096 \
        -d $domain \
        --rsa-key-size 4096

    # 配置自动续期
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet") | crontab -

    log_success "Let's Encrypt证书配置完成: $domain"
}

# 配置Nginx SSL
setup_nginx_ssl() {
    local domain=${1:-football-prediction.com}

    log_info "配置Nginx SSL for $domain..."

    # 创建SSL配置
    cat > /etc/nginx/ssl/$domain.conf << EOF
# SSL配置 for $domain
ssl_certificate /etc/ssl/certs/$domain.crt;
ssl_certificate_key /etc/ssl/private/$domain.key;

# SSL协议配置
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
ssl_ecdh_curve X25519:P-256:P-384;
ssl_session_timeout 10m;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# 安全头
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Frame-Options DENY always;
add_header X-Content-Type-Options nosniff always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https:; frame-ancestors 'none';" always;

# HSTS (仅在HTTPS站点)
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
EOF

    log_success "Nginx SSL配置完成: $domain"
}

# 创建HTTPS虚拟主机配置
create_https_vhost() {
    local domain=${1:-football-prediction.com}

    log_info "创建HTTPS虚拟主机配置..."

    cat > /etc/nginx/conf.d/$domain-https.conf << 'EOF'
server {
    listen 80;
    server_name DOMAIN;

    # HTTP到HTTPS重定向
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name DOMAIN;

    # SSL配置
    include /etc/nginx/ssl/DOMAIN.conf;

    # 安全配置
    ssl_dhparam /etc/nginx/ssl/dhparam.pem;

    # 日志配置
    access_log /var/log/nginx/DOMAIN.access.log;
    error_log /var/log/nginx/DOMAIN.error.log;

    # 根目录
    root /var/www/DOMAIN;
    index index.html index.htm;

    # 静态文件缓存
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header Vary Accept-Encoding;
    }

    # API代理
    location /api/ {
        proxy_pass http://football-app-prod:8000;
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

        # SSL配置
        proxy_ssl_server_name on;
        proxy_ssl_protocols TLSv1.2 TLSv1.3;
        proxy_ssl_ciphers HIGH:!aNULL:!MD5;
        proxy_ssl_session_reuse on;
    }

    # 健康检查
    location /health {
        access_log off;
        return 200 "healthy";
    }

    # Nginx状态
    location /nginx_status {
        stub_status;
        access_log off;
        allow 127.0.0.1;
        allow 10.0.0.0/8;
        deny all;
    }

    # 禁止访问敏感文件
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    location ~ /(\.git|\.env|docker-compose\.yml|Dockerfile)$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF

    # 替换域名占位符
    sed -i "s/DOMAIN/$domain/g" /etc/nginx/conf.d/$domain-https.conf

    log_success "HTTPS虚拟主机配置完成: $domain"
}

# 生成DH参数
generate_dhparam() {
    log_info "生成DH参数..."

    if [ ! -f /etc/ssl/dhparam.pem ]; then
        openssl dhparam -out /etc/ssl/dhparam.pem 4096
        chmod 600 /etc/ssl/dhparam.pem
    fi

    log_success "DH参数生成完成"
}

# 配置证书监控
setup_cert_monitoring() {
    log_info "配置证书监控..."

    # 创建证书监控脚本
    cat > /usr/local/bin/cert-monitor.sh << 'EOF'
#!/bin/bash
# SSL证书监控脚本

DOMAINS=("football-prediction.com" "api.football-prediction.com")
ALERT_EMAIL="admin@football-prediction.com"
LOG_FILE="/var/log/ssl/cert-monitor.log"

mkdir -p /var/log/ssl

for domain in "${DOMAINS[@]}"; do
    # 检查证书过期时间
    if [ -f "/etc/ssl/certs/$domain.crt" ]; then
        expiry_date=$(openssl x509 -enddate -noout -in "/etc/ssl/certs/$domain.crt" | cut -d= -f1)
        expiry_timestamp=$(date -d "$expiry_date" +%s)
        current_timestamp=$(date +%s)
        days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400))

        if [ $days_until_expiry -le 30 ]; then
            echo "$(date): 警告: $domain 证书将在 $days_until_expiry 天后过期" >> $LOG_FILE

            if [ $days_until_expiry -le 7 ]; then
                echo "紧急: $domain 证书将在 $days_until_expiry 天后过期！" | \
                mail -s "SSL证书即将过期" $ALERT_EMAIL << EOF
域名: $domain
过期时间: $expiry_date
剩余天数: $days_until_expiry

请及时续期证书！
EOF
            fi
        fi

        echo "$(date): $domain 证书有效期: $days_until_expiry 天" >> $LOG_FILE
    else
        echo "$(date): 警告: $domain 证书文件不存在" >> $LOG_FILE
    fi
done
EOF

    chmod +x /usr/local/bin/cert-monitor.sh

    # 设置定时任务（每天检查一次）
    echo "0 8 * * * /usr/local/bin/cert-monitor.sh" | crontab -

    log_success "证书监控配置完成"
}

# 创建证书测试脚本
create_cert_test() {
    local domain=${1:-football-prediction.com}

    log_info "创建证书测试脚本..."

    cat > /usr/local/bin/cert-test.sh << 'EOF'
#!/bin/bash
# SSL证书测试脚本

DOMAIN=${1:-football-prediction.com}
PORT=${2:-443}

echo "测试SSL证书: $DOMAIN:$PORT"

# 检查证书链完整性
echo "1. 检查证书链完整性..."
openssl s_client -connect $DOMAIN:$PORT -showcerts 2>/dev/null | \
    grep -E "(Verify return code|subject=|issuer=)" | head -5

echo ""
echo "2. 检查证书有效期..."
if [ -f "/etc/ssl/certs/$DOMAIN.crt" ]; then
    openssl x509 -in "/etc/ssl/certs/$DOMAIN.crt" -noout -dates
    openssl x509 -in "/etc/ssl/certs/$DOMAIN.crt" -noout -subject
else
    echo "证书文件不存在: /etc/ssl/certs/$DOMAIN.crt"
fi

echo ""
echo "3. 检查SSL连接..."
timeout 10 openssl s_client -connect $DOMAIN:$PORT 2>/dev/null | \
    grep -E "(handshake|Verify return code|Protocol|Cipher)" | head -5

echo ""
echo "4. SSL Labs评级测试..."
echo "访问 https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN&hideResults=on"
echo "进行完整的SSL安全评估"

echo ""
echo "证书测试完成"
EOF

    chmod +x /usr/local/bin/cert-test.sh

    log_success "证书测试脚本创建完成"
}

# 配置证书自动更新
setup_auto_renewal() {
    local domain=${1:-football-prediction.com}

    log_info "配置证书自动更新..."

    # 创建自动更新脚本
    cat > /usr/local/bin/cert-renew.sh << 'EOF'
#!/bin/bash
# SSL证书自动更新脚本

DOMAIN=${1:-football-prediction.com}
LOG_FILE="/var/log/ssl/cert-renew.log"

mkdir -p /var/log/ssl

echo "$(date): 开始SSL证书自动更新: $DOMAIN" >> $LOG_FILE

# 测试续期
certbot renew --dry-run --cert-name $DOMAIN >> $LOG_FILE 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): 续期测试通过，准备实际续期" >> $LOG_FILE

    # 实际续期
    certbot renew --cert-name $DOMAIN >> $LOG_FILE 2>&1

    if [ $? -eq 0 ]; then
        echo "$(date): SSL证书续期成功: $DOMAIN" >> $LOG_FILE

        # 重新加载Nginx
        systemctl reload nginx

        echo "$(date): Nginx重新加载完成" >> $LOG_FILE

        # 发送通知
        mail -s "SSL证书续期成功" admin@football-prediction.com << EOF
域名: $DOMAIN
时间: $(date)
状态: 续期成功

SSL证书已成功续期并重新加载Nginx配置。
EOF
    else
        echo "$(date): SSL证书续期失败: $DOMAIN" >> $LOG_FILE

        # 发送告警
        mail -s "SSL证书续期失败" admin@football-prediction.com << EOF
域名: $DOMAIN
时间: $(date)
状态: 续期失败

SSL证书续期失败，请立即检查！

详情请查看日志: $LOG_FILE
EOF
    fi
else
    echo "$(date): 续期测试失败: $DOMAIN" >> $LOG_FILE
fi

echo "$(date): SSL证书自动更新完成: $DOMAIN" >> $LOG_FILE
EOF

    chmod +x /usr/local/bin/cert-renew.sh

    log_success "证书自动更新配置完成"
}

# 创建SSL安全检查脚本
create_security_audit() {
    log_info "创建SSL安全审计脚本..."

    cat > /usr/local/bin/ssl-security-audit.sh << 'EOF'
#!/bin/bash
# SSL安全审计脚本

DOMAIN=${1:-football-prediction.com}
REPORT_DIR="/var/log/ssl-security-audit"
DATE=\$(date +%Y-%m-%d_%H:%M:%S)
REPORT_FILE="$REPORT_DIR/ssl-security-audit_$DATE.txt"

mkdir -p $REPORT_DIR

echo "==================== SSL安全审计报告 ====================" > $REPORT_FILE
echo "审计时间: $DATE" >> $REPORT_FILE
echo "审计域名: $DOMAIN" >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "==================== 证书信息 ====================" >> $REPORT_FILE
if [ -f "/etc/ssl/certs/$DOMAIN.crt" ]; then
    openssl x509 -in "/etc/ssl/certs/$DOMAIN.crt" -noout -text >> $REPORT_FILE
else
    echo "证书文件不存在: /etc/ssl/certs/$DOMAIN.crt" >> $REPORT_FILE
fi
echo "" >> $REPORT_FILE

echo "==================== SSL配置检查 ====================" >> $REPORT_FILE
echo "Nginx SSL配置:" >> $REPORT_FILE
nginx -T 2>/dev/null | grep -E "(ssl_certificate|ssl_certificate_key|ssl_protocols)" >> $REPORT_FILE || echo "Nginx配置未找到" >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "==================== SSL连接测试 ====================" >> $REPORT_FILE
echo "SSL连接测试结果:" >> $REPORT_FILE
timeout 10 openssl s_client -connect $DOMAIN:443 -showcerts 2>/dev/null | \
    grep -E "(Protocol|Cipher|Server Name|Subject)" >> $REPORT_FILE || echo "连接测试失败" >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "==================== 安全评分 ====================" >> $REPORT_FILE
SCORE=0

# 检查协议版本
if timeout 5 openssl s_client -connect $DOMAIN:443 2>/dev/null | grep -q "TLSv1.3\|TLSv1.2"; then
    SCORE=$((SCORE + 25))
    echo "✅ 协议版本: 现代 (TLS 1.2/1.3) [+25分]" >> $REPORT_FILE
else
    echo "❌ 协议版本: 过时 (建议升级到TLS 1.2+)" >> $REPORT_FILE
fi

# 检查密钥长度
if [ -f "/etc/ssl/private/$DOMAIN.key" ]; then
    KEY_LENGTH=$(openssl rsa -in "/etc/ssl/private/$DOMAIN.key" -noout | grep "Key" | awk '{print $NF}')
    if [ "$KEY_LENGTH" -ge 2048 ]; then
        SCORE=$((SCORE + 20))
        echo "✅ 密钥长度: 强 ($KEY_LENGTH bits) [+20分]" >> $REPORT_FILE
    else
        echo "❌ 密钥长度: 弱 ($KEY_LENGTH bits，建议2048+)" >> $REPORT_FILE
    fi
fi

# 检查证书有效期
if [ -f "/etc/ssl/certs/$DOMAIN.crt" ]; then
    EXPIRY=$(openssl x509 -enddate -noout -in "/etc/ssl/certs/$DOMAIN.crt" | cut -d= -f1)
    EXPIRY_TIMESTAMP=$(date -d "$EXPIRY" +%s)
    CURRENT_TIMESTAMP=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_TIMESTAMP - CURRENT_TIMESTAMP) / 86400))

    if [ $DAYS_LEFT -gt 30 ]; then
        SCORE=$((SCORE + 15))
        echo "✅ 证书有效期: 充足 ($DAYS_LEFT 天) [+15分]" >> $REPORT_FILE
    elif [ $DAYS_LEFT -gt 7 ]; then
        SCORE=$((SCORE + 10))
        echo "⚠️ 证书有效期: 一般 ($DAYS_LEFT 天) [+10分]" >> $REPORT_FILE
    else
        echo "❌ 证书有效期: 不足 ($DAYS_LEFT 天，需要续期)" >> $REPORT_FILE
    fi
fi

# 检查OCSP Stapling
if nginx -T 2>/dev/null | grep -q "ssl_stapling on"; then
    SCORE=$((SCORE + 10))
    echo "✅ OCSP Stapling: 启用 [+10分]" >> $REPORT_FILE
else
    echo "❌ OCSP Stapling: 未启用 (建议启用)" >> $REPORT_FILE
fi

# 检查HSTS
if timeout 5 curl -I https://$DOMAIN 2>/dev/null | grep -qi "strict-transport-security"; then
    SCORE=$((SCORE + 10))
    echo "✅ HSTS: 启用 [+10分]" >> $REPORT_FILE
else
    echo "❌ HSTS: 未启用 (建议启用)" >> $REPORT_FILE
fi

echo "" >> $REPORT_FILE
echo "==================== 评分结果 ====================" >> $REPORT_FILE
echo "总评分: $SCORE/100" >> $REPORT_FILE

if [ $SCORE -ge 80 ]; then
    echo "评级: 优秀 (A级)" >> $REPORT_FILE
elif [ $SCORE -ge 60 ]; then
    echo "评级: 良好 (B级)" >> $REPORT_FILE
elif [ $SCORE -ge 40 ]; then
    echo "评级: 一般 (C级)" >> $REPORT_FILE
else
    echo "评级: 需要改进 (D级)" >> $REPORT_FILE
fi

echo ""
echo "审计报告已生成: $REPORT_FILE"

# 生成HTML报告
HTML_FILE="$REPORT_DIR/ssl-security-audit_$DATE.html"
cat > $HTML_FILE << EOF
<!DOCTYPE html>
<html>
<head>
    <title>SSL安全审计报告 - $DOMAIN</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .content { background: #f8f9fa; padding: 20px; border-radius: 5px; margin-top: 20px; }
        .score { font-size: 24px; font-weight: bold; margin: 10px 0; }
        .excellent { color: #28a745; }
        .good { color: #17a2b8; }
        .average { color: #ffc107; }
        .poor { color: #dc3545; }
        pre { background: #f1f3f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="header">
        <h1>SSL安全审计报告</h1>
        <h2>域名: $DOMAIN</h2>
        <p>审计时间: $(date)</p>
    </div>

    <div class="content">
        <div class="score">
            总评分: <span id="score">$SCORE</span>/100
        </div>
        <div id="grade" class="GRADE">
            GRADE
        </div>

        <h3>详细报告</h3>
        <pre>$(cat $REPORT_FILE)</pre>
    </div>

    <script>
        // 根据分数设置颜色和评级
        var score = $SCORE;
        var scoreElement = document.getElementById('score');
        var gradeElement = document.getElementById('grade');

        if (score >= 80) {
            scoreElement.className = 'excellent';
            gradeElement.textContent = 'A级 (优秀)';
            gradeElement.className = 'excellent';
        } else if (score >= 60) {
            scoreElement.className = 'good';
            gradeElement.textContent = 'B级 (良好)';
            gradeElement.className = 'good';
        } else if (score >= 40) {
            scoreElement.className = 'average';
            gradeElement.textContent = 'C级 (一般)';
            gradeElement.className = 'average';
        } else {
            scoreElement.className = 'poor';
            gradeElement.textContent = 'D级 (需要改进)';
            gradeElement.className = 'poor';
        }
    </script>
</body>
</html>
EOF

    log_success "SSL安全审计完成: $REPORT_FILE"
    log_success "HTML报告已生成: $HTML_FILE"
}

# 主函数
main() {
    echo "========================================"
    echo "🔒 SSL证书配置和安全加固脚本"
    echo "========================================"
    echo ""
    echo "开始配置SSL证书和安全加固..."

    # 解析命令行参数
    MODE=${1:-self-signed}
    DOMAIN=${2:-football-prediction.com}
    EMAIL=${3:-admin@football-prediction.com}

    check_root
    install_prerequisites
    create_ssl_directories

    case $MODE in
        "self-signed")
            log_info "使用自签名证书模式"
            generate_self_signed_cert $DOMAIN
            ;;
        "letsencrypt")
            log_info "使用Let's Encrypt证书模式"
            setup_letsencrypt_cert $DOMAIN $EMAIL
            ;;
        "test")
            log_info "测试模式 - 跳过证书获取"
            ;;
        *)
            log_error "未知模式: $MODE"
            log_info "可用模式: self-signed, letsencrypt, test"
            exit 1
            ;;
    esac

    setup_nginx_ssl $DOMAIN
    create_https_vhost $DOMAIN
    generate_dhparam
    setup_cert_monitoring
    create_cert_test $DOMAIN
    setup_auto_renewal $DOMAIN
    create_security_audit $DOMAIN

    # 运行初始安全审计
    create_security_audit $DOMAIN

    echo ""
    echo "========================================"
    echo "✅ SSL配置完成"
    echo "========================================"
    echo ""
    echo "📋 配置摘要:"
    echo "  ✅ 证书类型: $MODE"
    echo "  ✅ 域名: $DOMAIN"
    echo "  ✅ Nginx SSL配置"
    echo "  ✅ HTTPS虚拟主机"
    echo "  ✅ 安全监控"
    echo "  ✅ 自动更新"
    echo "  ✅ 安全审计"
    echo ""
    echo "🔗 重要文件:"
    echo "  - 证书: /etc/ssl/certs/$DOMAIN.crt"
    echo "  - 私钥: /etc/ssl/private/$DOMAIN.key"
    echo "  - Nginx配置: /etc/nginx/conf.d/$DOMAIN-https.conf"
    echo "  - 监控脚本: /usr/local/bin/cert-monitor.sh"
    echo "  - 审计报告: /var/log/ssl-security-audit/"
    echo ""
    echo "🧪 测试命令:"
    echo "  cert-test.sh $DOMAIN - 测试证书"
    echo "  cert-renew.sh $DOMAIN - 手动续期"
    echo "  ssl-security-audit.sh $DOMAIN - 安全审计"
    echo ""
    echo "⚠️  重要提醒:"
    echo "  1. 请确保域名解析正确"
    echo " 2. 请配置防火墙开放80/443端口"
    echo " 3. 请定期检查证书有效期"
    echo "  4. 请监控SSL安全状态"
    echo ""
    echo "🚀 SSL配置完成，HTTPS服务已就绪！"
}

# 执行主函数
main "$@"