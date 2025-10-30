#!/bin/bash
# 生产环境安全配置脚本
# Production Environment Security Setup Script

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

# 配置系统防火墙
setup_firewall() {
    log_info "配置系统防火墙..."

    # 安装ufw（如果未安装）
    if ! command -v ufw &> /dev/null; then
        apt-get update
        apt-get install -y ufw
    fi

    # 重置防火墙规则
    ufw --force reset

    # 设置默认策略
    ufw default deny incoming
    ufw default allow outgoing

    # 允许SSH（在设置其他规则前）
    ufw allow ssh

    # 允许HTTP和HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp

    # 允许PostgreSQL（仅限内网）
    ufw allow from 10.0.0.0/8 to any port 5432
    ufw allow from 172.16.0.0/12 to any port 5432
    ufw allow from 192.168.0.0/16 to any port 5432

    # 允许Redis（仅限内网）
    ufw allow from 10.0.0.0/8 to any port 6379
    ufw allow from 172.16.0.0/12 to any port 6379
    ufw allow from 192.168.0.0/16 to any port 6379

    # 启用防火墙
    ufw --force enable

    log_success "防火墙配置完成"
}

# 配置fail2ban
setup_fail2ban() {
    log_info "配置fail2ban..."

    # 安装fail2ban
    apt-get update
    apt-get install -y fail2ban

    # 备份原始配置
    cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.conf.backup

    # 创建自定义配置
    cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
backend = systemd
destemail = alerts@football-prediction.com
sendername = Fail2Ban
sender = fail2ban@football-prediction.com
mta = sendmail
protocol = tcp
chain = INPUT
port = 0:65535
fail2banbanaction = iptables-multiport
action = %(action_)s

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
maxretry = 3
bantime = 3600

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 3
bantime = 3600

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 10
findtime = 600
bantime = 7200

[postfix-sasl]
enabled = true
port = smtp,ssmtp,submission
logpath = %(postfix_log)s
maxretry = 3
bantime = 3600

[droplet]
enabled = true
port = ssh
logpath = /var/log/auth.log
filter = digitalocean-droplet-auth
maxretry = 3
bantime = 3600
EOF

    # 重启fail2ban
    systemctl restart fail2ban
    systemctl enable fail2ban

    log_success "fail2ban配置完成"
}

# 配置自动安全更新
setup_security_updates() {
    log_info "配置自动安全更新..."

    # 安装自动更新包
    apt-get update
    apt-get install -y unattended-upgrades apt-listchanges

    # 配置自动更新
    cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Verbose "0";

// 自动重启配置
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-New-Unused-Dependencies "true";

// 邮件通知
Unattended-Upgrade::Mail "alerts@football-prediction.com";
Unattended-Upgrade::MailOnlyOnError "true";

// 安全更新黑名单
Unattended-Upgrade::Package-Blacklist {
    "linux-image-*";
    "linux-headers-*";
};

// 更新时间配置（每天凌晨3点）
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

    # 启用自动更新服务
    systemctl enable unattended-upgrades
    systemctl start unattended-upgrades

    log_success "自动安全更新配置完成"
}

# 配置SSH安全
setup_ssh_security() {
    log_info "配置SSH安全..."

    # 备份SSH配置
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

    # 配置SSH安全设置
    cat > /etc/ssh/sshd_config.d/security.conf << 'EOF'
# SSH安全配置
Port 22
Protocol 2
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
PermitEmptyPasswords no
ChallengeResponseAuthentication no
UsePAM yes

# 连接限制
MaxAuthTries 3
MaxSessions 10
ClientAliveInterval 300
ClientAliveCountMax 2

# 禁用不安全的认证方式
HostbasedAuthentication no
RhostsRSAAuthentication no
RSAAuthentication no

# 日志配置
LogLevel VERBOSE
SyslogFacility AUTHPRIV

# 子系统配置
Subsystem sftp /usr/lib/openssh/sftp-server
EOF

    # 重启SSH服务
    systemctl restart sshd

    log_success "SSH安全配置完成"
}

# 配置Docker安全
setup_docker_security() {
    log_info "配置Docker安全..."

    # 创建Docker用户
    if ! id "docker" &>/dev/null; then
        groupadd docker
        useradd -m -s /bin/bash docker
        usermod -aG docker docker
    fi

    # 配置Docker daemon安全设置
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json << 'EOF'
{
  "live-restore": true,
  "userland-proxy": false,
  "no-new-privileges": true,
  "seccomp-profile": "default",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
EOF

    # 重启Docker服务
    systemctl restart docker
    systemctl enable docker

    log_success "Docker安全配置完成"
}

# 配置系统内核安全参数
setup_kernel_security() {
    log_info "配置内核安全参数..."

    # 配置sysctl安全参数
    cat > /etc/sysctl.d/99-security.conf << 'EOF'
# 网络安全参数
net.ipv4.ip_forward = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# 防止IP欺骗
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# 防止SYN flood攻击
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 4096
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_syn_retries = 5

# 防止TCP连接跟踪表溢出
net.ipv4.netfilter.ip_conntrack_max = 1048576

# 记录可疑数据包
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# 禁用IPv6（如果不使用）
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 0

# 文件系统安全
fs.protected_regular = 1
fs.protected_fifos = 2

# 内核随机化
kernel.randomize_va_space = 2
kernel.kptr_restrict = 1
EOF

    # 应用sysctl配置
    sysctl -p /etc/sysctl.d/99-security.conf

    log_success "内核安全参数配置完成"
}

# 配置文件权限安全
setup_file_permissions() {
    log_info "配置文件权限安全..."

    # 设置关键文件权限
    chmod 600 /etc/ssh/sshd_config
    chmod 600 /etc/ssh/ssh_host_*_key
    chmod 644 /etc/ssh/ssh_host_*_key.pub
    chmod 700 /root/.ssh

    # 设置日志文件权限
    chmod 640 /var/log/auth.log
    chmod 640 /var/log/secure
    chmod 640 /var/log/messages

    # 创建安全目录
    mkdir -p /var/log/secure_logs
    chmod 700 /var/log/secure_logs

    log_success "文件权限安全配置完成"
}

# 配置入侵检测系统
setup_intrusion_detection() {
    log_info "配置入侵检测系统..."

    # 安装aide（高级入侵检测环境）
    apt-get update
    apt-get install -y aide

    # 初始化aide数据库
    aide --init
    cp /var/lib/aide/aide.db.new /var/lib/aide/aide.db

    # 配置aide
    cat > /etc/aide/aide.conf << 'EOF'
# AIDE配置文件
database=file:/var/lib/aide/aide.db
database_out=file:/var/lib/aide/aide.db.new
database_new=file:/var/lib/aide/aide.db.new
verbose=5
report_url=file:///var/log/aide/aide.log
gzip_dbout=yes

# 监控的目录和文件
/bin p+sha256
/sbin p+sha256
/usr/bin p+sha256
/usr/sbin p+sha256
/etc p+sha256
/lib p+sha256
/lib64 p+sha256
/opt p+sha256
/root p+sha256
/var/log p+sha256
/var/www p+sha256
/usr/local p+sha256
EOF

    # 创建aide检查脚本
    cat > /usr/local/bin/aide-check.sh << 'EOF'
#!/bin/bash
# AIDE入侵检测脚本

LOGFILE="/var/log/aide/aide-check.log"
DATE=\$(date +%Y-%m-%d_%H:%M:%S)

echo "[$DATE] 开始AIDE入侵检测..." >> $LOGFILE
aide --check >> $LOGFILE 2>&1

if [ $? -eq 0 ]; then
    echo "[$DATE] AIDE检查完成，未发现异常" >> $LOGFILE
else
    echo "[$DATE] AIDE检查发现异常！" >> $LOGFILE
    # 发送告警邮件
    mail -s "AIDE入侵检测告警" alerts@football-prediction.com < $LOGFILE
fi
EOF

    chmod +x /usr/local/bin/aide-check.sh

    # 设置定时任务
    echo "0 2 * * * /usr/local/bin/aide-check.sh" | crontab -

    log_success "入侵检测系统配置完成"
}

# 创建安全监控脚本
create_security_monitoring() {
    log_info "创建安全监控脚本..."

    cat > /usr/local/bin/security-monitor.sh << 'EOF'
#!/bin/bash
# 安全监控脚本

LOGFILE="/var/log/security-monitor.log"
DATE=\$(date +%Y-%m-%d_%H:%M:%S)

# 检查失败登录
FAILED_LOGINS=\$(grep "Failed password" /var/log/auth.log | grep "$(date '+%b %d')" | wc -l)
if [ $FAILED_LOGINS -gt 10 ]; then
    echo "[$DATE] 警警: 今日失败登录次数过多: $FAILED_LOGINS" >> $LOGFILE
    mail -s "安全告警: 失败登录次数过多" alerts@football-prediction.com << EOF
今日失败登录次数: $FAILED_LOGINS

请检查/var/log/auth.log以获取详细信息。
EOF
fi

# 检查root登录
ROOT_LOGINS=\$(grep "Accepted.*root" /var/log/auth.log | grep "$(date '+%b %d')" | wc -l)
if [ $ROOT_LOGINS -gt 0 ]; then
    echo "[$DATE] 警告: 检测到root登录: $ROOT_LOGINS 次" >> $LOGFILE
    mail -s "安全告警: 检测到root登录" alerts@football-prediction.com << EOF
今日root登录次数: $ROOT_LOGINS

请确认这些登录是否合法。
EOF
fi

# 检查异常进程
SUSPICIOUS_PROCS=\$(ps aux | grep -E "(nc|nmap|tcpdump|wireshark)" | grep -v grep | wc -l)
if [ $SUSPICIOUS_PROCS -gt 0 ]; then
    echo "[$DATE] 警警: 检测到可疑进程: $SUSPICIOUS_PROCS 个" >> $LOGFILE
    ps aux | grep -E "(nc|nmap|tcpdump|wireshark)" | grep -v grep >> $LOGFILE
fi

# 检查网络连接
ESTABLISHED_CONNECTIONS=\$(netstat -an | grep ESTABLISHED | wc -l)
echo "[$DATE] 当前建立的连接数: $ESTABLISHED_CONNECTIONS" >> $LOGFILE

if [ $ESTABLISHED_CONNECTIONS -gt 1000 ]; then
    echo "[$DATE] 警警: 建立连接数过多: $ESTABLISHED_CONNECTIONS" >> $LOGFILE
fi

echo "[$DATE] 安全监控检查完成" >> $LOGFILE
EOF

    chmod +x /usr/local/bin/security-monitor.sh

    # 设置定时任务（每小时检查一次）
    echo "0 * * * * /usr/local/bin/security-monitor.sh" | crontab -

    log_success "安全监控脚本创建完成"
}

# 创建安全检查脚本
create_security_audit() {
    log_info "创建安全审计脚本..."

    cat > /usr/local/bin/security-audit.sh << 'EOF'
#!/bin/bash
# 安全审计脚本

REPORT_DIR="/var/log/security-audit"
DATE=\$(date +%Y-%m-%d_%H:%M:%S)
REPORT_FILE="$REPORT_DIR/security_audit_$DATE.txt"

mkdir -p $REPORT_DIR

echo "==================== 安全审计报告 ====================" > $REPORT_FILE
echo "审计时间: $DATE" >> $REPORT_FILE
echo "主机名: $(hostname)" >> $REPORT_FILE
echo "操作系统: $(uname -a)" >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "==================== 系统信息 ====================" >> $REPORT_FILE
echo "内核版本: $(uname -r)" >> $REPORT_FILE
echo "系统负载: $(uptime)" >> $REPORT_FILE
echo "磁盘使用:" >> $REPORT_FILE
df -h >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "==================== 用户审计 ====================" >> $REPORT_FILE
echo "系统用户:" >> $REPORT_FILE
cat /etc/passwd | awk -F: '$3 == 0 {print $1}' | sort >> $REPORT_FILE
echo "" >> $REPORT_FILE
echo "sudo用户:" >> $REPORT_FILE
grep -E "^sudo|^%sudo" /etc/group | cut -d: -f4 | tr ',' '\n' | sort >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "==================== 网络配置 ====================" >> $REPORT_FILE
echo "监听端口:" >> $REPORT_FILE
netstat -tuln | grep LISTEN >> $REPORT_FILE
echo "" >> $REPORT_FILE
echo "网络连接:" >> $REPORT_FILE
netstat -an | grep ESTABLISHED | head -20 >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "==================== 防火墙状态 ====================" >> $REPORT_FILE
ufw status verbose >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "==================== 服务状态 ====================" >> $REPORT_FILE
systemctl list-units --type=service --state=running | head -20 >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "==================== 最近登录 ====================" >> $REPORT_FILE
last -n 20 >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "==================== 安全更新 ====================" >> $REPORT_FILE
apt list --upgradable 2>/dev/null | grep -v "WARNING" | tail -10 >> $REPORT_FILE
echo "" >> $REPORT_FILE

echo "==================== Docker信息 ====================" >> $REPORT_FILE
if command -v docker &> /dev/null; then
    echo "Docker版本: $(docker --version)" >> $REPORT_FILE
    echo "运行中的容器:" >> $REPORT_FILE
    docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" >> $REPORT_FILE
    echo "" >> $REPORT_FILE
fi

echo "审计完成时间: $(date)" >> $REPORT_FILE

echo "安全审计报告已生成: $REPORT_FILE"
EOF

    chmod +x /usr/local/bin/security-audit.sh

    log_success "安全审计脚本创建完成"
}

# 主函数
main() {
    echo "========================================"
    echo "🔒 生产环境安全配置脚本"
    echo "========================================"
    echo ""
    echo "开始配置生产环境安全..."

    check_root
    setup_firewall
    setup_fail2ban
    setup_security_updates
    setup_ssh_security
    setup_docker_security
    setup_kernel_security
    setup_file_permissions
    setup_intrusion_detection
    create_security_monitoring
    create_security_audit

    echo ""
    echo "========================================"
    echo "✅ 安全配置完成"
    echo "========================================"
    echo ""
    echo "📋 配置摘要:"
    echo "  ✅ 防火墙配置 (UFW)"
    echo "  ✅ 入侵检测 (Fail2ban + AIDE)"
    echo "  ✅ 自动安全更新"
    echo "  ✅ SSH安全加固"
    echo "  ✅ Docker安全配置"
    echo "  ✅ 内核安全参数"
    echo "  ✅ 文件权限安全"
    echo "  ✅ 安全监控脚本"
    echo "  ✅ 安全审计脚本"
    echo ""
    echo "🔗 重要文件位置:"
    echo "  - 防火墙配置: /etc/ufw/"
    echo "  - Fail2ban配置: /etc/fail2ban/"
    echo "  - SSH配置: /etc/ssh/sshd_config.d/"
    echo "  - 安全日志: /var/log/secure_logs/"
    echo "  - 监控脚本: /usr/local/bin/"
    echo ""
    echo "⚠️  重要提醒:"
    echo "  1. 请确保已配置SSH密钥认证"
    echo "  2. 请设置alerts@football-prediction.com邮件通知"
    echo "  3. 请定期检查安全日志"
    echo "  4. 请定期运行安全审计脚本"
    echo ""
    echo "🚀 安全配置完成，系统已加固！"
}

# 执行主函数
main "$@"