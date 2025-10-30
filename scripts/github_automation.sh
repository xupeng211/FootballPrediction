#!/bin/bash
#
# GitHub Issues自动化管理脚本
# 用于自动化GitHub仓库的日常管理任务
#
# 功能:
# - 标签管理自动化
# - Issues状态检查
# - 报告生成
# - 持续监控设置
#

set -e  # 出错时退出

# 配置
REPO="xupeng211/FootballPrediction"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs/github"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 日志文件
LOG_FILE="$LOG_DIR/automation_$(date +%Y%m%d_%H%M%S).log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查GitHub CLI
check_gh_cli() {
    if ! command -v gh &> /dev/null; then
        log "❌ GitHub CLI (gh) 未安装"
        log "安装方法: https://cli.github.com/manual/installation"
        exit 1
    fi

    # 检查认证状态
    if ! gh auth status &> /dev/null; then
        log "❌ GitHub CLI 未认证"
        log "运行: gh auth login"
        exit 1
    fi

    log "✅ GitHub CLI 检查通过"
}

# 检查仓库连接
check_repo_access() {
    log "🔍 检查仓库访问权限..."

    if gh repo view "$REPO" &> /dev/null; then
        log "✅ 仓库访问正常: $REPO"
    else
        log "❌ 无法访问仓库: $REPO"
        exit 1
    fi
}

# 标签管理
manage_labels() {
    log "🏷️ 开始标签管理..."

    # 检查必要标签是否存在，不存在则创建
    local labels=(
        "resolved:Issues that have been successfully resolved and verified:0E8A16"
        "priority-high:High priority issues requiring immediate attention:FF0000"
        "priority-medium:Medium priority issues for normal processing:FFA500"
        "priority-low:Low priority issues for future consideration:808080"
        "bug:Bug reports and issues:B60205"
        "enhancement:Feature requests and improvements:84B6EB"
        "documentation:Documentation related issues:0075CA"
        "good-first-issue:Good first issues for new contributors:7057FF"
        "help-wanted:Issues where help is wanted:008672"
        "wont-fix:Issues that will not be fixed:FFFFFF"
        "duplicate:Duplicate issues:000000"
        "question:Questions and general inquiries:d876e3"
        "test:Test related issues:5319E7"
    )

    for label_def in "${labels[@]}"; do
        IFS=':' read -r name description color <<< "$label_def"

        if gh label list --repo "$REPO" --search "$name" --limit 1 | grep -q "$name"; then
            log "  ✓ 标签已存在: $name"
        else
            log "  ➕ 创建标签: $name"
            gh label create "$name" \
                --repo "$REPO" \
                --description "$description" \
                --color "$color" || log "  ⚠️ 标签创建失败: $name"
        fi
    done

    log "✅ 标签管理完成"
}

# Issues状态分析
analyze_issues() {
    log "📊 分析Issues状态..."

    # 获取开放Issues数量
    local open_count=$(gh issue list --repo "$REPO" --limit 1000 --state open | wc -l)
    local closed_count=$(gh issue list --repo "$REPO" --limit 1000 --state closed | wc -l)

    log "  🔓 开放Issues: $open_count个"
    log "  🔒 关闭Issues: $closed_count个"

    # 获取本周新增和关闭
    local week_ago=$(date -d '7 days ago' --iso-8601)
    local recent_open=$(gh issue list --repo "$REPO" --since "$week_ago" --limit 1000 --state open | wc -l)
    local recent_closed=$(gh issue list --repo "$REPO" --since "$week_ago" --limit 1000 --state closed | wc -l)

    log "  📅 本周新增: $recent_open个"
    log "  ✅ 本周关闭: $recent_closed个"

    # 分析标签使用情况
    log "  🏷️ 分析标签使用..."
    local unlabeled_issues=$(gh issue list --repo "$REPO" --limit 1000 --state open --label '' | wc -l)
    if [ "$unlabeled_issues" -gt 0 ]; then
        log "  ⚠️ 发现 $unlabeled_issues 个未标记的开放Issues"
    else
        log "  ✅ 所有开放Issues都有标签"
    fi

    log "✅ Issues状态分析完成"
}

# 生成监控报告
generate_report() {
    log "📄 生成监控报告..."

    # 检查Python监控脚本
    local monitor_script="$SCRIPT_DIR/github_monitor.py"
    if [ ! -f "$monitor_script" ]; then
        log "❌ 监控脚本不存在: $monitor_script"
        return 1
    fi

    # 检查Python依赖
    if ! python3 -c "import requests" 2>/dev/null; then
        log "⚠️ 缺少requests依赖，尝试安装..."
        pip3 install requests || log "  ⚠️ 自动安装失败，请手动安装"
    fi

    # 生成报告
    local report_file="$PROJECT_ROOT/github_monitoring_report_$(date +%Y%m%d_%H%M%S).md"

    if python3 "$monitor_script" --repo "$REPO" --output "$report_file"; then
        log "✅ 报告生成成功: $report_file"
    else
        log "❌ 报告生成失败"
        return 1
    fi
}

# 检查Issue模板
check_issue_templates() {
    log "📋 检查Issue模板..."

    local template_dir="$PROJECT_ROOT/.github/ISSUE_TEMPLATE"
    local required_templates=("bug_report.md" "feature_request.md" "test_improvement.md")
    local missing_templates=()

    for template in "${required_templates[@]}"; do
        if [ ! -f "$template_dir/$template" ]; then
            missing_templates+=("$template")
        else
            log "  ✓ 模板存在: $template"
        fi
    done

    if [ ${#missing_templates[@]} -gt 0 ]; then
        log "  ⚠️ 缺失模板: ${missing_templates[*]}"
        log "  💡 建议运行模板创建命令"
    else
        log "  ✅ 所有必需模板都存在"
    fi

    # 检查配置文件
    local config_file="$PROJECT_ROOT/.github/config.yml"
    if [ -f "$config_file" ]; then
        log "  ✓ GitHub配置存在: config.yml"
    else
        log "  ⚠️ 缺失GitHub配置文件"
    fi

    log "✅ Issue模板检查完成"
}

# 清理旧的日志
cleanup_logs() {
    log "🧹 清理旧日志文件..."

    # 保留最近7天的日志
    find "$LOG_DIR" -name "automation_*.log" -mtime +7 -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -name "github_monitoring_report_*.md" -mtime +7 -delete 2>/dev/null || true

    log "  ✅ 清理完成"
}

# 设置持续监控（可选）
setup_continuous_monitoring() {
    log "⏰ 设置持续监控..."

    # 创建cron任务示例（不实际安装，只是展示）
    local cron_example="0 9 * * * cd $PROJECT_ROOT && ./scripts/github_automation.sh --report-only"

    log "📝 建议的cron任务（每日9点执行）:"
    log "  $cron_example"
    log ""
    log "🔧 手动安装方法:"
    log "  1. 运行: crontab -e"
    log "  2. 添加上述cron任务"
    log "  3. 保存退出"
    log ""
    log "📊 或使用GitHub Actions进行自动化监控"
}

# 主要功能函数
main_menu() {
    echo "🔧 GitHub Issues自动化管理工具"
    echo "================================"
    echo "1. 完整检查和报告"
    echo "2. 仅标签管理"
    echo "3. 仅状态分析"
    echo "4. 仅生成报告"
    echo "5. 检查模板"
    echo "6. 设置持续监控"
    echo "7. 退出"
    echo ""
    read -p "请选择操作 (1-7): " choice

    case $choice in
        1)
            full_check_and_report
            ;;
        2)
            manage_labels
            ;;
        3)
            analyze_issues
            ;;
        4)
            generate_report
            ;;
        5)
            check_issue_templates
            ;;
        6)
            setup_continuous_monitoring
            ;;
        7)
            log "👋 退出"
            exit 0
            ;;
        *)
            log "❌ 无效选择"
            main_menu
            ;;
    esac
}

# 完整检查和报告
full_check_and_report() {
    log "🚀 开始完整GitHub管理检查..."
    echo ""

    check_gh_cli
    check_repo_access
    manage_labels
    analyze_issues
    generate_report
    check_issue_templates
    cleanup_logs

    echo ""
    log "🎉 完整检查完成!"
    log "📊 详细报告请查看生成的markdown文件"
}

# 解析命令行参数
case "${1:-}" in
    --full|--all)
        full_check_and_report
        ;;
    --labels)
        manage_labels
        ;;
    --analyze)
        analyze_issues
        ;;
    --report|--report-only)
        generate_report
        ;;
    --templates)
        check_issue_templates
        ;;
    --monitoring)
        setup_continuous_monitoring
        ;;
    --help|-h)
        echo "GitHub Issues自动化管理工具"
        echo ""
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  --full, --all      完整检查和报告"
        echo "  --labels           仅标签管理"
        echo "  --analyze          仅状态分析"
        echo "  --report, --report-only  仅生成报告"
        echo "  --templates        检查Issue模板"
        echo "  --monitoring       设置持续监控"
        echo "  --help, -h         显示帮助信息"
        echo ""
        echo "不带参数运行将显示交互菜单"
        ;;
    "")
        main_menu
        ;;
    *)
        log "❌ 未知选项: $1"
        log "运行 --help 查看帮助信息"
        exit 1
        ;;
esac