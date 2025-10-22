#!/bin/bash

# 团队通知脚本
# Team Notification Script

set -euo pipefail

# 配置变量
MESSAGE="${1:-}"
NOTIFICATION_TYPE="${2:-info}" # info, warning, error, success
WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
EMAIL_RECIPIENTS="${TEAM_EMAIL:-}"
LOG_FILE="logs/notifications-$(date +%Y%m%d).log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${GREEN}$msg${NC}"
    echo "$msg" >> "$LOG_FILE"
}

error() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1"
    echo -e "${RED}$msg${NC}"
    echo "$msg" >> "$LOG_FILE"
}

warn() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1"
    echo -e "${YELLOW}$msg${NC}"
    echo "$msg" >> "$LOG_FILE"
}

info() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1"
    echo -e "${BLUE}$msg${NC}"
    echo "$msg" >> "$LOG_FILE"
}

# 创建日志目录
mkdir -p logs

# 检查消息参数
if [[ -z "$MESSAGE" ]]; then
    echo "使用方法: $0 <message> [notification_type]"
    echo "示例: $0 \"系统部署成功\" success"
    exit 1
fi

# 获取系统信息
get_system_info() {
    local hostname
    hostname=$(hostname)
    local timestamp
    timestamp=$(date)
    local git_commit
    git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    local git_branch
    git_branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    local uptime
    uptime=$(uptime -p 2>/dev/null || echo "unknown")

    echo "主机: $hostname"
    echo "时间: $timestamp"
    echo "Git版本: $git_commit ($git_branch)"
    echo "系统运行时间: $uptime"
}

# 构建Slack消息
build_slack_message() {
    local color="good"
    local emoji=":information_source:"

    case "$NOTIFICATION_TYPE" in
        "success")
            color="good"
            emoji=":white_check_mark:"
            ;;
        "warning")
            color="warning"
            emoji=":warning:"
            ;;
        "error")
            color="danger"
            emoji=":x:"
            ;;
        "info"|*)
            color="good"
            emoji=":information_source:"
            ;;
    esac

    cat << EOF
{
    "attachments": [
        {
            "color": "$color",
            "title": "$emoji 足球预测系统通知",
            "text": "$MESSAGE",
            "fields": [
                {
                    "title": "系统信息",
                    "value": "$(get_system_info | tr '\n' '\\n')",
                    "short": false
                }
            ],
            "footer": "部署通知系统",
            "ts": $(date +%s)
        }
    ]
}
EOF
}

# 发送Slack通知
send_slack_notification() {
    if [[ -n "$WEBHOOK_URL" ]]; then
        info "发送Slack通知..."

        local slack_message
        slack_message=$(build_slack_message)

        local response
        response=$(curl -s -X POST -H 'Content-type: application/json' \
            --data "$slack_message" \
            "$WEBHOOK_URL" 2>/dev/null || echo "failed")

        if [[ "$response" == "ok" ]]; then
            log "Slack通知发送成功"
        else
            warn "Slack通知发送失败: $response"
        fi
    else
        info "未配置Slack Webhook，跳过Slack通知"
    fi
}

# 构建邮件内容
build_email_content() {
    local subject="足球预测系统通知 - $NOTIFICATION_TYPE"

    case "$NOTIFICATION_TYPE" in
        "success")
            subject="✅ 足球预测系统 - 部署成功"
            ;;
        "warning")
            subject="⚠️ 足球预测系统 - 警告通知"
            ;;
        "error")
            subject="❌ 足球预测系统 - 错误通知"
            ;;
        "info"|*)
            subject="ℹ️ 足球预测系统 - 信息通知"
            ;;
    esac

    cat << EOF
Subject: $subject
Content-Type: text/html; charset=UTF-8

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>足球预测系统通知</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f8f9fa; padding: 20px; border-radius: 5px; }
        .content { margin: 20px 0; }
        .system-info { background-color: #e9ecef; padding: 15px; border-radius: 5px; }
        .footer { margin-top: 30px; color: #6c757d; }
        .success { color: #28a745; }
        .warning { color: #ffc107; }
        .error { color: #dc3545; }
        .info { color: #17a2b8; }
    </style>
</head>
<body>
    <div class="header">
        <h1 class="$NOTIFICATION_TYPE">足球预测系统通知</h1>
        <p><strong>消息类型:</strong> $NOTIFICATION_TYPE</p>
        <p><strong>消息内容:</strong> $MESSAGE</p>
    </div>

    <div class="content">
        <h2>系统信息</h2>
        <div class="system-info">
            <pre>$(get_system_info)</pre>
        </div>
    </div>

    <div class="footer">
        <p>此邮件由足球预测系统自动发送。</p>
        <p>发送时间: $(date)</p>
    </div>
</body>
</html>
EOF
}

# 发送邮件通知
send_email_notification() {
    if [[ -n "$EMAIL_RECIPIENTS" ]]; then
        info "发送邮件通知..."

        local email_content
        email_content=$(build_email_content)

        # 使用sendmail发送邮件（需要系统配置）
        if command -v sendmail &> /dev/null; then
            echo "$email_content" | sendmail -t "$EMAIL_RECIPIENTS"
            log "邮件通知发送成功"
        else
            warn "系统未安装sendmail，无法发送邮件通知"
        fi
    else
        info "未配置邮件收件人，跳过邮件通知"
    fi
}

# 发送系统日志通知
send_log_notification() {
    local log_entry="[$(date +'%Y-%m-%d %H:%M:%S')] [$NOTIFICATION_TYPE] $MESSAGE"
    echo "$log_entry" >> "logs/system-notifications.log"
    log "系统日志记录完成"
}

# 显示本地通知
show_local_notification() {
    case "$NOTIFICATION_TYPE" in
        "success")
            echo -e "${GREEN}✅ $MESSAGE${NC}"
            ;;
        "warning")
            echo -e "${YELLOW}⚠️ $MESSAGE${NC}"
            ;;
        "error")
            echo -e "${RED}❌ $MESSAGE${NC}"
            ;;
        "info"|*)
            echo -e "${BLUE}ℹ️ $MESSAGE${NC}"
            ;;
    esac

    echo "系统信息:"
    get_system_info | sed 's/^/  /'
}

# 主函数
main() {
    info "开始发送团队通知..."
    info "通知类型: $NOTIFICATION_TYPE"
    info "通知内容: $MESSAGE"

    # 显示本地通知
    show_local_notification

    # 记录系统日志
    send_log_notification

    # 发送Slack通知
    send_slack_notification

    # 发送邮件通知
    send_email_notification

    log "团队通知发送完成"
}

# 执行主函数
main "$@"