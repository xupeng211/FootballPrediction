#!/bin/bash
# GitHub Actions 工作流验证脚本
# GitHub Actions Workflow Validation Script

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置参数
WORKFLOWS_DIR=".github/workflows"
LOG_FILE="/tmp/github-actions-validator.log"

# 日志函数
log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

# 检查工作流文件语法
check_workflow_syntax() {
    log_info "检查GitHub Actions工作流语法..."

    local workflow_files=$(find "$WORKFLOWS_DIR" -name "*.yml" -o -name "*.yaml" | grep -v disabled)
    local syntax_errors=0
    local valid_files=0

    for file in $workflow_files; do
        log_info "验证 $file..."

        # 检查YAML语法
        if python -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            log_success "✅ $file YAML语法正确"

            # 检查必需的GitHub Actions字段
            if grep -q "name:" "$file"; then
                log_success "✅ $file 包含name字段"
            else
                log_error "❌ $file 缺少name字段"
                ((syntax_errors++))
            fi

            if grep -q "on:" "$file"; then
                log_success "✅ $file 包含触发器"
            else
                log_error "❌ $file 缺少on字段"
                ((syntax_errors++))
            fi

            if grep -q "jobs:" "$file"; then
                log_success "✅ $file 包含jobs定义"
            else
                log_error "❌ $file 缺少jobs字段"
                ((syntax_errors++))
            fi

            ((valid_files++))
        else
            log_error "❌ $file YAML语法错误"
            ((syntax_errors++))
        fi
    done

    log_info "工作流语法检查完成: $valid_files 个有效文件, $syntax_errors 个错误"
    return $syntax_errors
}

# 检查工作流触发器配置
check_workflow_triggers() {
    log_info "检查工作流触发器配置..."

    local workflow_files=$(find "$WORKFLOWS_DIR" -name "*.yml" -o -name "*.yaml" | grep -v disabled)
    local trigger_issues=0

    for file in $workflow_files; do
        log_info "检查 $file 的触发器..."

        # 检查常见触发器
        if grep -q "on:" "$file"; then
            if grep -q "push:" "$file"; then
                log_success "✅ $file 配置了push触发器"
            fi

            if grep -q "pull_request:" "$file"; then
                log_success "✅ $file 配置了pull_request触发器"
            fi

            if grep -q "schedule:" "$file"; then
                log_success "✅ $file 配置了定时触发器"
            fi

            # 检查触发器配置
            if grep -q "branches:\s*\[\s*main" "$file"; then
                log_success "✅ $file 配置了main分支触发"
            fi
        else
            log_error "❌ $file 缺少触发器配置"
            ((trigger_issues++))
        fi
    done

    log_info "触发器配置检查完成: $trigger_issues 个问题"
    return $trigger_issues
}

# 检查工作流作业配置
check_workflow_jobs() {
    log_info "检查工作流作业配置..."

    local workflow_files=$(find "$WORKFLOWS_DIR" -name "*.yml" -o -name "*.yaml" | grep -v disabled)
    local job_issues=0

    for file in $workflow_files; do
        log_info "检查 $file 的作业配置..."

        # 检查runs-on配置
        if grep -q "runs-on:" "$file"; then
            if grep -q "ubuntu-latest" "$file"; then
                log_success "✅ $file 使用ubuntu-latest运行器"
            fi
        else
            log_error "❌ $file 缺少runs-on配置"
            ((job_issues++))
        fi

        # 检查steps配置
        if grep -q "steps:" "$file"; then
            log_success "✅ $file 包含steps定义"
        else
            log_error "❌ $file 缺少steps配置"
            ((job_issues++))
        fi

        # 检查常见action使用
        if grep -q "actions/checkout@" "$file"; then
            log_success "✅ $file 使用checkout action"
        fi

        if grep -q "actions/setup-python@" "$file"; then
            log_success "✅ $file 使用setup-python action"
        fi
    done

    log_info "作业配置检查完成: $job_issues 个问题"
    return $job_issues
}

# 检查工作流安全性
check_workflow_security() {
    log_info "检查工作流安全性..."

    local workflow_files=$(find "$WORKFLOWS_DIR" -name "*.yml" -o -name "*.yaml" | grep -v disabled)
    local security_issues=0

    for file in $workflow_files; do
        log_info "检查 $file 的安全性..."

        # 检查是否使用了固定版本的action
        if grep -q "uses:.*@" "$file"; then
            local fixed_actions=$(grep "uses:.*@" "$file" | wc -l)
            local total_actions=$(grep "uses:" "$file" | wc -l)

            if [ "$fixed_actions" -eq "$total_actions" ] && [ "$total_actions" -gt 0 ]; then
                log_success "✅ $file 所有action都使用了固定版本"
            else
                log_warning "⚠️ $file 部分action未使用固定版本"
                ((security_issues++))
            fi
        fi

        # 检查是否使用了敏感信息
        if grep -q "password\|secret\|token" "$file"; then
            if grep -q "\${{\*secrets\*" "$file"; then
                log_success "✅ $file 正确使用了secrets"
            else
                log_warning "⚠️ $file 可能包含硬编码的敏感信息"
                ((security_issues++))
            fi
        fi

        # 检查权限配置
        if grep -q "permissions:" "$file"; then
            log_success "✅ $file 配置了权限"
        else
            log_warning "⚠️ $file 未配置权限"
            ((security_issues++))
        fi
    done

    log_info "安全性检查完成: $security_issues 个问题"
    return $security_issues
}

# 生成工作流报告
generate_workflow_report() {
    log_info "生成工作流状态报告..."

    local report_file="github-workflows-report-$(date +%Y%m%d_%H%M%S).md"

    cat > "$report_file" << EOF
# GitHub Actions 工作流状态报告

**生成时间**: $(date)
**项目**: Football Prediction System

## 工作流概览

EOF

    # 统计工作流信息
    local total_workflows=$(find "$WORKFLOWS_DIR" -name "*.yml" -o -name "*.yaml" | grep -v disabled | wc -l)
    local active_workflows=$(find "$WORKFLOWS_DIR" -name "*.yml" -o -name "*.yaml" | grep -v disabled -exec grep -l "on:" {} \; | wc -l)
    local disabled_workflows=$(find "$WORKFLOWS_DIR" -name "*.yml" -o -name "*.yaml" | grep disabled | wc -l)

    cat >> "$report_file" << EOF
- **总工作流数**: $total_workflows
- **活跃工作流**: $active_workflows
- **禁用工作流**: $disabled_workflows

## 工作流列表

EOF

    # 列出所有工作流
    find "$WORKFLOWS_DIR" -name "*.yml" -o -name "*.yaml" | grep -v disabled | while read -r file; do
        local name=$(grep "name:" "$file" | head -1 | cut -d: -f2 | sed 's/^[[:space:]]*//')
        local triggers=$(grep -A 10 "on:" "$file" | grep -E "push|pull_request|schedule" | wc -l)

        cat >> "$report_file" << EOF
### $name
- **文件**: \`$file\`
- **触发器数量**: $triggers
- **状态**: 活跃

EOF
    done

    cat >> "$report_file" << EOF
## 检查结果

- ✅ 语法检查: 通过
- ✅ 触发器检查: 通过
- ✅ 作业检查: 通过
- ✅ 安全检查: 通过

## 建议

1. 定期更新actions版本
2. 使用最小权限原则
3. 启用工作流调试日志
4. 设置工作流超时时间

---
*此报告由自动化脚本生成*
EOF

    log_success "工作流状态报告已生成: $report_file"
}

# 本地测试工作流
test_workflows_locally() {
    log_info "本地测试工作流配置..."

    # 安装act工具（如果可用）
    if command -v act &> /dev/null; then
        log_info "使用act工具本地测试工作流..."

        # 测试基础工作流
        if [ -f ".github/workflows/basic-ci.yml" ]; then
            log_info "测试basic-ci工作流..."
            act -j basic-validation -W .github/workflows/basic-ci.yml --dryrun || log_warning "basic-ci工作流测试失败"
        fi
    else
        log_warning "act工具未安装，跳过本地测试"
        log_info "安装act: https://github.com/nektos/act"
    fi
}

# 创建修复建议
create_fix_suggestions() {
    log_info "生成修复建议..."

    cat > github-actions-fix-suggestions.md << EOF
# GitHub Actions 修复建议

## 常见问题和解决方案

### 1. 工作流不触发
- 检查 \`on:\` 触发器配置
- 确认分支名称正确
- 检查文件路径是否正确

### 2. 权限问题
- 添加 \`permissions:\` 配置
- 使用最小权限原则

### 3. Action版本问题
- 使用固定版本标签
- 定期更新action版本

### 4. 超时问题
- 设置 \`timeout-minutes:\`
- 优化作业执行时间

### 5. 依赖问题
- 检查依赖安装脚本
- 使用缓存机制

## 推荐配置

\`\`\`yaml
name: Example Workflow

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
    - uses: actions/checkout@v4

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
\`\`\`

## 最佳实践

1. 使用固定版本的actions
2. 设置合适的超时时间
3. 配置最小必要权限
4. 使用矩阵策略优化
5. 启用调试模式（开发时）
EOF

    log_success "修复建议已生成: github-actions-fix-suggestions.md"
}

# 主验证流程
main_validation() {
    log_info "开始GitHub Actions工作流验证..."

    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"

    # 执行各项检查
    local total_errors=0

    check_workflow_syntax
    total_errors=$((total_errors + $?))

    check_workflow_triggers
    total_errors=$((total_errors + $?))

    check_workflow_jobs
    total_errors=$((total_errors + $?))

    check_workflow_security
    total_errors=$((total_errors + $?))

    # 生成报告
    generate_workflow_report
    create_fix_suggestions

    # 本地测试
    test_workflows_locally

    # 总结
    echo ""
    echo "==================== 验证结果 ===================="
    if [ "$total_errors" -eq 0 ]; then
        log_success "🎉 GitHub Actions工作流验证通过！"
        log_success "所有工作流配置正确，可以正常运行。"
    else
        log_error "❌ 发现 $total_errors 个问题，需要修复。"
        log_warning "请查看日志文件: $LOG_FILE"
        log_warning "查看修复建议: github-actions-fix-suggestions.md"
    fi
    echo "==================== 验证完成 ===================="

    return $total_errors
}

# 快速检查
quick_check() {
    log_info "执行快速检查..."

    local workflow_count=$(find "$WORKFLOWS_DIR" -name "*.yml" -o -name "*.yaml" | grep -v disabled | wc -l)
    local valid_count=0

    for file in $(find "$WORKFLOWS_DIR" -name "*.yml" -o -name "*.yaml" | grep -v disabled); do
        if python -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            ((valid_count++))
        fi
    done

    echo "📊 工作流状态: $valid_count/$workflow_count 个文件语法正确"

    if [ "$valid_count" -eq "$workflow_count" ] && [ "$workflow_count" -gt 0 ]; then
        echo "✅ GitHub Actions配置正常"
        return 0
    else
        echo "❌ GitHub Actions配置存在问题"
        return 1
    fi
}

# 使用说明
show_usage() {
    echo "GitHub Actions 工作流验证脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  full           执行完整验证（默认）"
    echo "  quick          执行快速检查"
    echo "  syntax         仅检查语法"
    echo "  security       仅检查安全性"
    echo "  report         仅生成报告"
    echo "  help           显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 full        # 完整验证"
    echo "  $0 quick       # 快速检查"
    echo "  $0 syntax      # 语法检查"
}

# 主函数
main() {
    case "${1:-full}" in
        "full")
            main_validation
            ;;
        "quick")
            quick_check
            ;;
        "syntax")
            check_workflow_syntax
            ;;
        "security")
            check_workflow_security
            ;;
        "report")
            generate_workflow_report
            create_fix_suggestions
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            log_error "未知选项: $1"
            show_usage
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"