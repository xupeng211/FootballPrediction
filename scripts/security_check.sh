#!/bin/bash

# Security Configuration Validation Script
# Football Prediction System - Production Security Validator
# Author: Claude Code
# Version: 1.0

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SECURITY_CONFIG_FILE="security/production.env"
MIN_PASSWORD_LENGTH=32
MIN_SECRET_LENGTH=64
MIN_ENCRYPTION_LENGTH=32

# Validation results
SECURITY_SCORE=0
MAX_SCORE=100
FAILURES=()
WARNINGS=()
PASSED=()

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $1"; PASSED+=("$1"); }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; WARNINGS+=("$1"); }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; FAILURES+=("$1"); }
log_critical() { echo -e "${PURPLE}[CRITICAL]${NC} $1"; }

# Check if running as root for system checks
check_root_privileges() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "以root权限运行，将进行系统级安全检查"
        return 0
    else
        log_info "非root权限，跳过系统级检查"
        return 1
    fi
}

# Validate file permissions
validate_file_permissions() {
    log_info "检查配置文件权限..."

    if [[ -f "$SECURITY_CONFIG_FILE" ]]; then
        local permissions=$(stat -c "%a" "$SECURITY_CONFIG_FILE")
        local owner=$(stat -c "%U" "$SECURITY_CONFIG_FILE")

        if [[ "$permissions" == "600" ]]; then
            log_success "配置文件权限正确 (600)"
            SECURITY_SCORE=$((SECURITY_SCORE + 10))
        else
            log_error "配置文件权限不安全 ($permissions)，建议设置为600"
            SECURITY_SCORE=$((SECURITY_SCORE - 10))
        fi

        if [[ "$owner" != "$(whoami)" ]] && [[ $EUID -ne 0 ]]; then
            log_warning "配置文件所有者不是当前用户"
        fi
    else
        log_error "安全配置文件不存在: $SECURITY_CONFIG_FILE"
        SECURITY_SCORE=$((SECURITY_SCORE - 20))
    fi
}

# Check for default/placeholder values
check_placeholder_values() {
    log_info "检查占位符和默认值..."

    if [[ -f "$SECURITY_CONFIG_FILE" ]]; then
        local placeholder_count
        placeholder_count=$(grep -c "CHANGE_THIS" "$SECURITY_CONFIG_FILE" || true)

        if [[ $placeholder_count -eq 0 ]]; then
            log_success "未发现占位符值"
            SECURITY_SCORE=$((SECURITY_SCORE + 20))
        else
            log_error "发现 $placeholder_count 个占位符值需要替换"
            SECURITY_SCORE=$((SECURITY_SCORE - 20))
        fi

        # Check for common default passwords
        if grep -q "password.*password" "$SECURITY_CONFIG_FILE"; then
            log_error "发现默认密码模式"
            SECURITY_SCORE=$((SECURITY_SCORE - 10))
        fi

        if grep -q "secret.*secret" "$SECURITY_CONFIG_FILE"; then
            log_error "发现默认密钥模式"
            SECURITY_SCORE=$((SECURITY_SCORE - 10))
        fi
    fi
}

# Validate secret key strength
validate_secret_keys() {
    log_info "验证密钥强度..."

    if [[ -f "$SECURITY_CONFIG_FILE" ]]; then
        # Check SECRET_KEY
        local secret_key=$(grep "^SECRET_KEY=" "$SECURITY_CONFIG_FILE" | cut -d'=' -f2)
        if [[ ${#secret_key} -ge $MIN_SECRET_LENGTH ]]; then
            log_success "SECRET_KEY 长度符合要求 (${#secret_key} 字符)"
            SECURITY_SCORE=$((SECURITY_SCORE + 10))
        else
            log_error "SECRET_KEY 长度不足 (${#secret_key} 字符，最少需要 $MIN_SECRET_LENGTH 字符)"
            SECURITY_SCORE=$((SECURITY_SCORE - 10))
        fi

        # Check JWT_SECRET_KEY
        local jwt_secret=$(grep "^JWT_SECRET_KEY=" "$SECURITY_CONFIG_FILE" | cut -d'=' -f2)
        if [[ ${#jwt_secret} -ge $MIN_SECRET_LENGTH ]]; then
            log_success "JWT_SECRET_KEY 长度符合要求 (${#jwt_secret} 字符)"
            SECURITY_SCORE=$((SECURITY_SCORE + 10))
        else
            log_error "JWT_SECRET_KEY 长度不足 (${#jwt_secret} 字符，最少需要 $MIN_SECRET_LENGTH 字符)"
            SECURITY_SCORE=$((SECURITY_SCORE - 10))
        fi

        # Check ENCRYPTION_KEY
        local encryption_key=$(grep "^ENCRYPTION_KEY=" "$SECURITY_CONFIG_FILE" | cut -d'=' -f2)
        if [[ ${#encryption_key} -eq $MIN_ENCRYPTION_LENGTH ]]; then
            log_success "ENCRYPTION_KEY 长度正确 (${#encryption_key} 字符)"
            SECURITY_SCORE=$((SECURITY_SCORE + 5))
        else
            log_error "ENCRYPTION_KEY 长度不正确 (${#encryption_key} 字符，需要正好 $MIN_ENCRYPTION_LENGTH 字符)"
            SECURITY_SCORE=$((SECURITY_SCORE - 5))
        fi
    fi
}

# Validate database security
validate_database_security() {
    log_info "验证数据库安全配置..."

    if [[ -f "$SECURITY_CONFIG_FILE" ]]; then
        # Check if using PostgreSQL (recommended)
        if grep -q "postgresql://" "$SECURITY_CONFIG_FILE"; then
            log_success "使用PostgreSQL数据库"
            SECURITY_SCORE=$((SECURITY_SCORE + 5))
        fi

        # Check for SSL in database connection
        if grep -q "sslmode=require" "$SECURITY_CONFIG_FILE"; then
            log_success "数据库连接启用SSL"
            SECURITY_SCORE=$((SECURITY_SCORE + 5))
        else
            log_warning "建议在数据库连接中启用SSL"
        fi

        # Check database password strength
        local db_password=$(grep "^DB_PASSWORD=" "$SECURITY_CONFIG_FILE" | cut -d'=' -f2)
        if [[ ${#db_password} -ge $MIN_PASSWORD_LENGTH ]]; then
            log_success "数据库密码长度符合要求"
            SECURITY_SCORE=$((SECURITY_SCORE + 5))
        else
            log_error "数据库密码长度不足"
            SECURITY_SCORE=$((SECURITY_SCORE - 5))
        fi
    fi
}

# Validate Redis security
validate_redis_security() {
    log_info "验证Redis安全配置..."

    if [[ -f "$SECURITY_CONFIG_FILE" ]]; then
        # Check Redis password
        if grep -q "REDIS_PASSWORD=" "$SECURITY_CONFIG_FILE"; then
            local redis_password=$(grep "^REDIS_PASSWORD=" "$SECURITY_CONFIG_FILE" | cut -d'=' -f2)
            if [[ ${#redis_password} -ge 16 ]]; then
                log_success "Redis密码已配置且长度符合要求"
                SECURITY_SCORE=$((SECURITY_SCORE + 5))
            else
                log_warning "Redis密码建议至少16字符"
            fi
        else
            log_error "Redis未配置密码"
            SECURITY_SCORE=$((SECURITY_SCORE - 5))
        fi
    fi
}

# Check production environment settings
validate_production_settings() {
    log_info "验证生产环境设置..."

    if [[ -f "$SECURITY_CONFIG_FILE" ]]; then
        # Check debug mode
        if grep -q "DEBUG=false" "$SECURITY_CONFIG_FILE"; then
            log_success "生产环境DEBUG已禁用"
            SECURITY_SCORE=$((SECURITY_SCORE + 10))
        else
            log_error "生产环境DEBUG必须设置为false"
            SECURITY_SCORE=$((SECURITY_SCORE - 10))
        fi

        # Check log level
        if grep -q "LOG_LEVEL=WARNING" "$SECURITY_CONFIG_FILE" || grep -q "LOG_LEVEL=ERROR" "$SECURITY_CONFIG_FILE"; then
            log_success "生产环境日志级别设置正确"
            SECURITY_SCORE=$((SECURITY_SCORE + 5))
        else
            log_warning "建议生产环境使用WARNING或ERROR日志级别"
        fi

        # Check environment
        if grep -q "ENV=production" "$SECURITY_CONFIG_FILE"; then
            log_success "环境设置为production"
            SECURITY_SCORE=$((SECURITY_SCORE + 5))
        else
            log_error "环境必须设置为production"
            SECURITY_SCORE=$((SECURITY_SCORE - 5))
        fi
    fi
}

# System-level security checks (root only)
perform_system_security_checks() {
    if ! check_root_privileges; then
        return 0
    fi

    log_info "执行系统级安全检查..."

    # Check firewall status
    if command -v ufw &> /dev/null; then
        if ufw status | grep -q "Status: active"; then
            log_success "防火墙已启用"
            SECURITY_SCORE=$((SECURITY_SCORE + 5))
        else
            log_error "防火墙未启用"
            SECURITY_SCORE=$((SECURITY_SCORE - 5))
        fi
    fi

    # Check SSL certificate validity
    if command -v openssl &> /dev/null && [[ -f "/etc/letsencrypt/live/your-domain.com/cert.pem" ]]; then
        local expiry_date=$(openssl x509 -in "/etc/letsencrypt/live/your-domain.com/cert.pem" -noout -enddate | cut -d= -f2)
        local expiry_epoch=$(date -d "$expiry_date" +%s)
        local current_epoch=$(date +%s)
        local days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))

        if [[ $days_until_expiry -gt 30 ]]; then
            log_success "SSL证书有效期充足 ($days_until_expiry 天)"
            SECURITY_SCORE=$((SECURITY_SCORE + 5))
        elif [[ $days_until_expiry -gt 7 ]]; then
            log_warning "SSL证书将在 $days_until_expiry 天后过期"
        else
            log_error "SSL证书即将过期 ($days_until_expiry 天)"
            SECURITY_SCORE=$((SECURITY_SCORE - 5))
        fi
    fi

    # Check file permissions for sensitive directories
    local sensitive_dirs=("/etc/letsencrypt" "/var/log" "/var/backups")
    for dir in "${sensitive_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            local perms=$(stat -c "%a" "$dir")
            if [[ "$perms" =~ ^[0-7][0-5][0-5]$ ]]; then
                log_success "敏感目录权限安全: $dir ($perms)"
                SECURITY_SCORE=$((SECURITY_SCORE + 2))
            else
                log_warning "敏感目录权限可能过于开放: $dir ($perms)"
            fi
        fi
    done
}

# Check for security headers configuration
validate_security_headers() {
    log_info "验证安全头配置..."

    if [[ -f "$SECURITY_CONFIG_FILE" ]]; then
        local required_headers=(
            "X_FRAME_OPTIONS"
            "X_CONTENT_TYPE_OPTIONS"
            "X_XSS_PROTECTION"
            "STRICT_TRANSPORT_SECURITY"
            "CONTENT_SECURITY_POLICY"
        )

        local headers_found=0
        for header in "${required_headers[@]}"; do
            if grep -q "$header" "$SECURITY_CONFIG_FILE"; then
                ((headers_found++))
            fi
        done

        if [[ $headers_found -eq ${#required_headers[@]} ]]; then
            log_success "所有推荐的安全头都已配置"
            SECURITY_SCORE=$((SECURITY_SCORE + 10))
        else
            log_warning "部分安全头未配置 ($headers_found/${#required_headers[@]})"
            SECURITY_SCORE=$((SECURITY_SCORE + (headers_found * 2)))
        fi
    fi
}

# Generate security recommendations
generate_recommendations() {
    log_info "生成安全建议..."

    cat << EOF

===========================================
🛡️ 安全配置评估报告
===========================================

总体安全评分: $SECURITY_SCORE/$MAX_SCORE
- 通过项目: ${#PASSED[@]}
- 警告项目: ${#WARNINGS[@]}
- 失败项目: ${#FAILURES[@]}

EOF

    # Show detailed results
    if [[ ${#PASSED[@]} -gt 0 ]]; then
        echo -e "${GREEN}✅ 通过的安全检查:${NC}"
        for item in "${PASSED[@]}"; do
            echo "  • $item"
        done
        echo ""
    fi

    if [[ ${#WARNINGS[@]} -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  安全警告:${NC}"
        for item in "${WARNINGS[@]}"; do
            echo "  • $item"
        done
        echo ""
    fi

    if [[ ${#FAILURES[@]} -gt 0 ]]; then
        echo -e "${RED}❌ 安全问题:${NC}"
        for item in "${FAILURES[@]}"; do
            echo "  • $item"
        done
        echo ""
    fi

    # Generate recommendations based on score
    echo -e "${BLUE}📋 安全建议:${NC}"

    if [[ $SECURITY_SCORE -lt 60 ]]; then
        echo -e "${RED}🔴 高风险: 立即解决安全问题后才能上线${NC}"
        echo "  1. 替换所有占位符值为强密钥"
        echo "  2. 设置正确的文件权限 (600)"
        echo "  3. 启用所有安全头配置"
        echo "  4. 配置数据库SSL连接"
    elif [[ $SECURITY_SCORE -lt 80 ]]; then
        echo -e "${YELLOW}🟡 中风险: 建议完善后上线${NC}"
        echo "  1. 加强密钥和密码强度"
        echo "  2. 启用系统防火墙"
        echo "  3. 配置SSL证书监控"
        echo "  4. 完善日志和监控配置"
    else
        echo -e "${GREEN}🟢 低风险: 可以考虑上线${NC}"
        echo "  1. 定期检查和更新安全配置"
        echo "  2. 监控系统安全状态"
        echo "  3. 定期进行安全审计"
    fi

    echo ""
    echo -e "${PURPLE}🔧 下一步操作:${NC}"
    echo "1. 修复所有失败的检查项"
    echo "2. 重新运行此脚本验证"
    echo "3. 配置自动化安全监控"
    echo "4. 建立定期安全审计流程"

    echo ""
    echo -e "${BLUE}📞 安全联系信息:${NC}"
    echo "如发现安全问题，请联系: security@your-domain.com"
}

# Create security monitoring configuration
create_security_monitoring() {
    log_info "创建安全监控配置..."

    cat > scripts/security_monitor.sh << 'EOF'
#!/bin/bash

# Security Monitoring Script
# Run daily to check for security issues

LOG_FILE="/var/log/security-monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Function to log security events
log_security_event() {
    echo "[$DATE] SECURITY: $1" >> "$LOG_FILE"
    # Send alert if needed
    if command -v mail &> /dev/null; then
        echo "$1" | mail -s "Security Alert" admin@your-domain.com
    fi
}

# Check for unauthorized access attempts
check_unauthorized_access() {
    if [[ -f "/var/log/auth.log" ]]; then
        local failed_attempts=$(grep "Failed password" /var/log/auth.log | grep "$(date '+%b %d')" | wc -l)
        if [[ $failed_attempts -gt 100 ]]; then
            log_security_event "High number of failed login attempts: $failed_attempts"
        fi
    fi
}

# Check SSL certificate expiry
check_ssl_expiry() {
    if [[ -f "/etc/letsencrypt/live/your-domain.com/cert.pem" ]]; then
        local expiry_date=$(openssl x509 -in "/etc/letsencrypt/live/your-domain.com/cert.pem" -noout -enddate | cut -d= -f2)
        local expiry_epoch=$(date -d "$expiry_date" +%s)
        local current_epoch=$(date +%s)
        local days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))

        if [[ $days_until_expiry -lt 30 ]]; then
            log_security_event "SSL certificate expiring in $days_until_expiry days"
        fi
    fi
}

# Check disk space
check_disk_space() {
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $disk_usage -gt 90 ]]; then
        log_security_event "Disk usage critical: ${disk_usage}%"
    fi
}

# Run all checks
check_unauthorized_access
check_ssl_expiry
check_disk_space

echo "[$DATE] Security monitoring completed" >> "$LOG_FILE"
EOF

    chmod +x scripts/security_monitor.sh

    # Create cron job for daily security monitoring
    cat > /etc/cron.d/football-security << EOF
# Football Prediction System Security Monitoring
0 6 * * * root /path/to/project/scripts/security_monitor.sh
EOF

    log_success "安全监控配置已创建"
}

# Main execution function
main() {
    echo "=========================================="
    echo "🛡️ 足球预测系统安全配置验证"
    echo "=========================================="
    echo "检查时间: $(date)"
    echo "配置文件: $SECURITY_CONFIG_FILE"
    echo ""

    # Run all security checks
    validate_file_permissions
    check_placeholder_values
    validate_secret_keys
    validate_database_security
    validate_redis_security
    validate_production_settings
    validate_security_headers
    perform_system_security_checks

    # Ensure score doesn't go below 0
    if [[ $SECURITY_SCORE -lt 0 ]]; then
        SECURITY_SCORE=0
    fi

    # Generate comprehensive report
    generate_recommendations

    # Create monitoring if score is acceptable
    if [[ $SECURITY_SCORE -ge 70 ]]; then
        create_security_monitoring
    fi

    echo ""
    echo "=========================================="
    echo "安全配置验证完成"
    echo "=========================================="

    # Exit with appropriate code
    if [[ $SECURITY_SCORE -ge 80 ]]; then
        log_success "安全配置验证通过"
        exit 0
    elif [[ $SECURITY_SCORE -ge 60 ]]; then
        log_warning "安全配置基本通过，建议完善警告项"
        exit 0
    else
        log_error "安全配置验证失败，请修复问题后重试"
        exit 1
    fi
}

# Run main function
main "$@"
