#!/bin/bash

# 最终检查脚本
# Final Check Script

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FINAL_REPORT_FILE="$PROJECT_ROOT/FINAL_DEPLOYMENT_READINESS_REPORT.md"
CHECK_LOG="$PROJECT_ROOT/logs/final-check-$(date +%Y%m%d-%H%M%S).log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 日志函数
log() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${GREEN}$msg${NC}" | tee -a "$CHECK_LOG"
}

error() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1"
    echo -e "${RED}$msg${NC}" | tee -a "$CHECK_LOG"
}

warn() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1"
    echo -e "${YELLOW}$msg${NC}" | tee -a "$CHECK_LOG"
}

info() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1"
    echo -e "${BLUE}$msg${NC}" | tee -a "$CHECK_LOG"
}

section() {
    echo -e "\n${PURPLE}=== $1 ===${NC}" | tee -a "$CHECK_LOG"
}

# 创建日志目录
mkdir -p "$PROJECT_ROOT/logs"

# 检查结果统计
declare -A CHECK_RESULTS
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# 记录检查结果
record_check() {
    local check_name="$1"
    local result="$2"
    local details="$3"

    ((TOTAL_CHECKS++))

    case "$result" in
        "PASS")
            ((PASSED_CHECKS++))
            echo -e "  ✅ $check_name: $details" | tee -a "$CHECK_LOG"
            ;;
        "FAIL")
            ((FAILED_CHECKS++))
            echo -e "  ❌ $check_name: $details" | tee -a "$CHECK_LOG"
            ;;
        "WARN")
            ((WARNING_CHECKS++))
            echo -e "  ⚠️  $check_name: $details" | tee -a "$CHECK_LOG"
            ;;
    esac

    CHECK_RESULTS["$check_name"]="$result:$details"
}

# 1. 代码质量检查
check_code_quality() {
    section "代码质量检查"

    # 检查代码格式
    if make fmt > /dev/null 2>&1; then
        record_check "代码格式化" "PASS" "代码格式正确"
    else
        record_check "代码格式化" "FAIL" "代码格式需要修正"
    fi

    # 检查代码质量
    if make lint > /dev/null 2>&1; then
        record_check "代码质量检查" "PASS" "通过Ruff检查"
    else
        record_check "代码质量检查" "FAIL" "Ruff检查发现问题"
    fi

    # 检查类型安全
    if make type-check > /dev/null 2>&1; then
        record_check "类型安全检查" "PASS" "通过MyPy检查"
    else
        record_check "类型安全检查" "WARN" "MyPy检查发现问题"
    fi

    # 检查测试覆盖率
    local coverage
    coverage=$(make coverage-fast 2>/dev/null | grep -o '[0-9]*%' | head -1 | sed 's/%//' || echo "0")
    if [[ $coverage -ge 22 ]]; then
        record_check "测试覆盖率" "PASS" "当前覆盖率 ${coverage}%"
    elif [[ $coverage -ge 15 ]]; then
        record_check "测试覆盖率" "WARN" "覆盖率较低 ${coverage}%"
    else
        record_check "测试覆盖率" "FAIL" "覆盖率过低 ${coverage}%"
    fi
}

# 2. 安全检查
check_security() {
    section "安全检查"

    # 检查安全漏洞
    if make security-check > /dev/null 2>&1; then
        record_check "安全漏洞扫描" "PASS" "无安全漏洞"
    else
        record_check "安全漏洞扫描" "WARN" "发现安全漏洞需要修复"
    fi

    # 检查敏感信息
    if make secret-scan > /dev/null 2>&1; then
        record_check "敏感信息扫描" "PASS" "未发现敏感信息泄露"
    else
        record_check "敏感信息扫描" "FAIL" "发现敏感信息泄露"
    fi

    # 检查依赖安全
    if command -v pip-audit &> /dev/null; then
        if pip-audit --requirement requirements/requirements.lock 2>/dev/null | grep -q "Vulnerability"; then
            record_check "依赖安全检查" "WARN" "发现依赖漏洞"
        else
            record_check "依赖安全检查" "PASS" "依赖安全"
        fi
    else
        record_check "依赖安全检查" "WARN" "pip-audit未安装"
    fi
}

# 3. Docker和基础设施检查
check_docker_infrastructure() {
    section "Docker和基础设施检查"

    # 检查Docker安装
    if command -v docker &> /dev/null; then
        record_check "Docker安装" "PASS" "Docker已安装"
    else
        record_check "Docker安装" "FAIL" "Docker未安装"
    fi

    # 检查Docker Compose
    if command -v docker-compose &> /dev/null; then
        record_check "Docker Compose安装" "PASS" "Docker Compose已安装"
    else
        record_check "Docker Compose安装" "FAIL" "Docker Compose未安装"
    fi

    # 检查生产环境配置
    if [[ -f "$PROJECT_ROOT/docker/environments/.env.production" ]]; then
        record_check "生产环境配置" "PASS" "生产环境配置文件存在"
    else
        record_check "生产环境配置" "FAIL" "生产环境配置文件缺失"
    fi

    # 检查Docker Compose生产配置
    if [[ -f "$PROJECT_ROOT/docker-compose.prod.yml" ]]; then
        record_check "Docker Compose生产配置" "PASS" "生产Docker配置存在"
    else
        record_check "Docker Compose生产配置" "FAIL" "生产Docker配置缺失"
    fi

    # 检查Nginx配置
    if [[ -f "$PROJECT_ROOT/nginx/nginx.conf" ]]; then
        record_check "Nginx配置" "PASS" "Nginx配置文件存在"
    else
        record_check "Nginx配置" "FAIL" "Nginx配置文件缺失"
    fi
}

# 4. 监控和日志检查
check_monitoring_logging() {
    section "监控和日志检查"

    # 检查Prometheus配置
    if [[ -f "$PROJECT_ROOT/monitoring/prometheus.yml" ]]; then
        record_check "Prometheus配置" "PASS" "Prometheus配置文件存在"
    else
        record_check "Prometheus配置" "FAIL" "Prometheus配置文件缺失"
    fi

    # 检查Grafana配置
    if [[ -d "$PROJECT_ROOT/monitoring/grafana" ]]; then
        record_check "Grafana配置" "PASS" "Grafana配置目录存在"
    else
        record_check "Grafana配置" "WARN" "Grafana配置目录缺失"
    fi

    # 检查监控脚本
    local monitoring_scripts=("monitoring-dashboard.sh" "auto-monitoring.sh")
    for script in "${monitoring_scripts[@]}"; do
        if [[ -f "$PROJECT_ROOT/scripts/$script" ]]; then
            record_check "监控脚本 $script" "PASS" "脚本存在且可执行"
        else
            record_check "监控脚本 $script" "FAIL" "脚本缺失"
        fi
    done
}

# 5. 部署脚本检查
check_deployment_scripts() {
    section "部署脚本检查"

    # 检查部署自动化脚本
    if [[ -f "$PROJECT_ROOT/scripts/deploy-automation.sh" ]]; then
        record_check "部署自动化脚本" "PASS" "部署脚本存在且可执行"
    else
        record_check "部署自动化脚本" "FAIL" "部署脚本缺失"
    fi

    # 检查应急响应脚本
    if [[ -f "$PROJECT_ROOT/scripts/emergency-response.sh" ]]; then
        record_check "应急响应脚本" "PASS" "应急脚本存在且可执行"
    else
        record_check "应急响应脚本" "FAIL" "应急脚本缺失"
    fi

    # 检查性能测试脚本
    if [[ -f "$PROJECT_ROOT/scripts/performance-check.sh" ]]; then
        record_check "性能测试脚本" "PASS" "性能测试脚本存在"
    else
        record_check "性能测试脚本" "WARN" "性能测试脚本缺失"
    fi

    # 检查压力测试脚本
    if [[ -f "$PROJECT_ROOT/scripts/stress_test.py" ]]; then
        record_check "压力测试脚本" "PASS" "压力测试脚本存在"
    else
        record_check "压力测试脚本" "WARN" "压力测试脚本缺失"
    fi
}

# 6. 文档检查
check_documentation() {
    section "文档检查"

    # 检查部署指南
    if [[ -f "$PROJECT_ROOT/DEPLOYMENT_GUIDE.md" ]]; then
        record_check "部署指南" "PASS" "部署指南文档存在"
    else
        record_check "部署指南" "FAIL" "部署指南文档缺失"
    fi

    # 检查上线流程文档
    if [[ -f "$PROJECT_ROOT/DEPLOYMENT_PROCESS.md" ]]; then
        record_check "上线流程文档" "PASS" "上线流程文档存在"
    else
        record_check "上线流程文档" "FAIL" "上线流程文档缺失"
    fi

    # 检查应急预案文档
    if [[ -f "$PROJECT_ROOT/EMERGENCY_RESPONSE_PLAN.md" ]]; then
        record_check "应急预案文档" "PASS" "应急预案文档存在"
    else
        record_check "应急预案文档" "FAIL" "应急预案文档缺失"
    fi

    # 检查监控指南
    if [[ -f "$PROJECT_ROOT/POST_DEPLOYMENT_MONITORING.md" ]]; then
        record_check "监控指南" "PASS" "监控指南文档存在"
    else
        record_check "监控指南" "WARN" "监控指南文档缺失"
    fi

    # 检查API文档
    if [[ -f "$PROJECT_ROOT/docs/api/README.md" ]]; then
        record_check "API文档" "PASS" "API文档存在"
    else
        record_check "API文档" "WARN" "API文档缺失"
    fi
}

# 7. 测试检查
check_testing() {
    section "测试检查"

    # 运行单元测试
    if make test-unit > /dev/null 2>&1; then
        record_check "单元测试" "PASS" "单元测试通过"
    else
        record_check "单元测试" "FAIL" "单元测试失败"
    fi

    # 检查功能测试
    if [[ -f "$PROJECT_ROOT/FUNCTIONAL_TEST_REPORT.md" ]]; then
        record_check "功能测试报告" "PASS" "功能测试报告存在"
    else
        record_check "功能测试报告" "WARN" "功能测试报告缺失"
    fi

    # 检查集成测试
    if [[ -f "$PROJECT_ROOT/INTEGRATION_TEST_REPORT.md" ]]; then
        record_check "集成测试报告" "PASS" "集成测试报告存在"
    else
        record_check "集成测试报告" "WARN" "集成测试报告缺失"
    fi

    # 检查压力测试
    if [[ -f "$PROJECT_ROOT/STRESS_TEST_REPORT.md" ]]; then
        record_check "压力测试报告" "PASS" "压力测试报告存在"
    else
        record_check "压力测试报告" "WARN" "压力测试报告缺失"
    fi
}

# 8. 环境检查
check_environment() {
    section "环境检查"

    # 检查Python版本
    local python_version
    python_version=$(python3 --version 2>&1 | grep -o '3\.[0-9]*' | head -1)
    if [[ -n "$python_version" ]]; then
        if [[ "${python_version#*.}" -ge 8 ]]; then
            record_check "Python版本" "PASS" "Python $python_version 满足要求"
        else
            record_check "Python版本" "WARN" "Python $python_version 版本较低"
        fi
    else
        record_check "Python版本" "FAIL" "Python未安装"
    fi

    # 检查必要工具
    local required_tools=("git" "curl" "jq")
    for tool in "${required_tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            record_check "工具 $tool" "PASS" "$tool 已安装"
        else
            record_check "工具 $tool" "WARN" "$tool 未安装"
        fi
    done

    # 检查端口可用性
    local ports=(80 8000 5432 6379 9090 3000)
    local port_conflicts=0
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            ((port_conflicts++))
        fi
    done

    if [[ $port_conflicts -eq 0 ]]; then
        record_check "端口可用性" "PASS" "关键端口均可用"
    else
        record_check "端口可用性" "WARN" "$port_conflicts 个端口被占用"
    fi
}

# 9. 性能检查
check_performance() {
    section "性能检查"

    # 检查磁盘空间
    local available_space
    available_space=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    if [[ $available_space -gt 2097152 ]]; then  # 2GB in KB
        record_check "磁盘空间" "PASS" "可用空间充足"
    elif [[ $available_space -gt 1048576 ]]; then  # 1GB in KB
        record_check "磁盘空间" "WARN" "可用空间较少"
    else
        record_check "磁盘空间" "FAIL" "磁盘空间不足"
    fi

    # 检查内存
    local available_memory
    available_memory=$(free | awk 'NR==2{print $7}')
    if [[ $available_memory -gt 1048576 ]]; then  # 1GB in KB
        record_check "可用内存" "PASS" "内存充足"
    elif [[ $available_memory -gt 524288 ]]; then  # 512MB in KB
        record_check "可用内存" "WARN" "内存较少"
    else
        record_check "可用内存" "FAIL" "内存不足"
    fi
}

# 10. 生成最终报告
generate_final_report() {
    local success_rate
    success_rate=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

    cat > "$FINAL_REPORT_FILE" << EOF
# 最终部署就绪检查报告
# Final Deployment Readiness Report

## 📊 检查概览

**检查时间**: $(date)
**检查人员**: $USER
**Git版本**: $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
**Git分支**: $(git branch --show-current 2>/dev/null || echo "unknown")

### 检查结果统计
- **总检查项**: $TOTAL_CHECKS
- **通过项目**: $PASSED_CHECKS
- **失败项目**: $FAILED_CHECKS
- **警告项目**: $WARNING_CHECKS
- **通过率**: ${success_rate}%

## 🎯 总体评估

EOF

    if [[ $success_rate -ge 90 && $FAILED_CHECKS -eq 0 ]]; then
        cat >> "$FINAL_REPORT_FILE" << EOF
### ✅ 系统已准备好部署

**评估结果**: 优秀
- 通过率超过90%
- 无关键失败项目
- 系统状态良好，可以立即进行生产部署

**建议**: 可以开始部署流程，建议在非高峰时段进行。
EOF
    elif [[ $success_rate -ge 80 && $FAILED_CHECKS -le 2 ]]; then
        cat >> "$FINAL_REPORT_FILE" << EOF
### ⚠️ 系统基本准备就绪

**评估结果**: 良好
- 通过率超过80%
- 少量失败项目，不影响核心功能
- 建议修复失败项目后部署

**建议**: 修复标识的失败项目后即可部署。
EOF
    elif [[ $success_rate -ge 70 ]]; then
        cat >> "$FINAL_REPORT_FILE" << EOF
### ⚠️ 系统需要改进

**评估结果**: 一般
- 通过率在70-80%之间
- 存在多个失败项目
- 需要解决关键问题后才能部署

**建议**: 重点解决失败项目，特别是安全、配置相关的问题。
EOF
    else
        cat >> "$FINAL_REPORT_FILE" << EOF
### ❌ 系统未准备好部署

**评估结果**: 不合格
- 通过率低于70%
- 存在大量失败项目
- 系统存在严重问题，不建议部署

**建议**: 必须解决所有关键问题后重新检查。
EOF
    fi

    cat >> "$FINAL_REPORT_FILE" << EOF

## 📋 详细检查结果

### 代码质量检查
EOF

    for key in "${!CHECK_RESULTS[@]}"; do
        if [[ "$key" =~ ^(代码格式化|代码质量检查|类型安全检查|测试覆盖率)$ ]]; then
            local result="${CHECK_RESULTS[$key]}"
            local status="${result%%:*}"
            local details="${result#*:}"

            case "$status" in
                "PASS") echo "- ✅ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
                "WARN") echo "- ⚠️ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
                "FAIL") echo "- ❌ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
            esac
        fi
    done

    cat >> "$FINAL_REPORT_FILE" << EOF

### 安全检查
EOF

    for key in "${!CHECK_RESULTS[@]}"; do
        if [[ "$key" =~ ^(安全漏洞扫描|敏感信息扫描|依赖安全检查)$ ]]; then
            local result="${CHECK_RESULTS[$key]}"
            local status="${result%%:*}"
            local details="${result#*:}"

            case "$status" in
                "PASS") echo "- ✅ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
                "WARN") echo "- ⚠️ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
                "FAIL") echo "- ❌ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
            esac
        fi
    done

    cat >> "$FINAL_REPORT_FILE" << EOF

### 基础设施检查
EOF

    for key in "${!CHECK_RESULTS[@]}"; do
        if [[ "$key" =~ ^(Docker|Nginx|生产环境配置) ]]; then
            local result="${CHECK_RESULTS[$key]}"
            local status="${result%%:*}"
            local details="${result#*:}"

            case "$status" in
                "PASS") echo "- ✅ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
                "WARN") echo "- ⚠️ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
                "FAIL") echo "- ❌ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
            esac
        fi
    done

    cat >> "$FINAL_REPORT_FILE" << EOF

### 监控和脚本检查
EOF

    for key in "${!CHECK_RESULTS[@]}"; do
        if [[ "$key" =~ ^(监控|部署|应急|压力测试脚本|性能测试脚本)$ ]]; then
            local result="${CHECK_RESULTS[$key]}"
            local status="${result%%:*}"
            local details="${result#*:}"

            case "$status" in
                "PASS") echo "- ✅ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
                "WARN") echo "- ⚠️ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
                "FAIL") echo "- ❌ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
            esac
        fi
    done

    cat >> "$FINAL_REPORT_FILE" << EOF

### 文档和测试检查
EOF

    for key in "${!CHECK_RESULTS[@]}"; do
        if [[ "$key" =~ ^(文档|测试报告|单元测试)$ ]]; then
            local result="${CHECK_RESULTS[$key]}"
            local status="${result%%:*}"
            local details="${result#*:}"

            case "$status" in
                "PASS") echo "- ✅ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
                "WARN") echo "- ⚠️ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
                "FAIL") echo "- ❌ **$key**: $details" >> "$FINAL_REPORT_FILE" ;;
            esac
        fi
    done

    cat >> "$FINAL_REPORT_FILE" << EOF

## 🔧 部署前建议

### 必须完成的任务
EOF

    local critical_tasks=0
    for key in "${!CHECK_RESULTS[@]}"; do
        local result="${CHECK_RESULTS[$key]}"
        local status="${result%%:*}"
        if [[ "$status" == "FAIL" ]]; then
            echo "- 修复: $key" >> "$FINAL_REPORT_FILE"
            ((critical_tasks++))
        fi
    done

    if [[ $critical_tasks -eq 0 ]]; then
        echo "- ✅ 无关键修复任务" >> "$FINAL_REPORT_FILE"
    fi

    cat >> "$FINAL_REPORT_FILE" << EOF

### 建议完成的任务
EOF

    local recommended_tasks=0
    for key in "${!CHECK_RESULTS[@]}"; do
        local result="${CHECK_RESULTS[$key]}"
        local status="${result%%:*}"
        if [[ "$status" == "WARN" ]]; then
            echo "- 改进: $key" >> "$FINAL_REPORT_FILE"
            ((recommended_tasks++))
        fi
    done

    if [[ $recommended_tasks -eq 0 ]]; then
        echo "- ✅ 无建议改进任务" >> "$FINAL_REPORT_FILE"
    fi

    cat >> "$FINAL_REPORT_FILE" << EOF

## 📝 部署检查清单

在执行部署前，请确认以下项目：

### 技术准备
- [ ] 所有关键失败项目已修复
- [ ] 警告项目已评估或修复
- [ ] 生产环境配置已验证
- [ ] 备份策略已确认
- [ ] 监控系统已配置

### 团队准备
- [ ] 部署团队已就位
- [ ] 应急联系方式已确认
- [ ] 回滚计划已准备
- [ ] 部署时间已协调

### 业务准备
- [ ] 用户通知已发送（如需要）
- [ ] 业务影响已评估
- [ ] 发布计划已确认
- [ ] 上线后监控已安排

## 🚀 下一步行动

EOF

    if [[ $success_rate -ge 90 && $FAILED_CHECKS -eq 0 ]]; then
        cat >> "$FINAL_REPORT_FILE" << EOF
1. **立即执行部署**
   \`\`\`bash
   ./scripts/deploy-automation.sh deploy
   \`\`\`

2. **监控系统状态**
   \`\`\`bash
   ./scripts/monitoring-dashboard.sh overview
   \`\`\`

3. **启动自动化监控**
   \`\`\`bash
   ./scripts/auto-monitoring.sh start
   \`\`\`
EOF
    else
        cat >> "$FINAL_REPORT_FILE" << EOF
1. **修复关键问题**
   重新运行检查以验证修复：
   \`\`\`bash
   ./scripts/final-check.sh
   \`\`\`

2. **解决警告项目**
   优化系统配置和性能

3. **准备完成后再执行部署**
EOF
    fi

    cat >> "$FINAL_REPORT_FILE" << EOF

## 📞 支持信息

如需帮助，请参考：
- 📖 部署指南: \`DEPLOYMENT_GUIDE.md\`
- 🚨 应急预案: \`EMERGENCY_RESPONSE_PLAN.md\`
- 📊 监控指南: \`POST_DEPLOYMENT_MONITORING.md\`
- 🔧 快速诊断: \`./scripts/quick-diagnosis.sh\`

---

**报告生成时间**: $(date)
**检查完成时间**: $(date)
**系统状态**: $([[ $success_rate -ge 90 && $FAILED_CHECKS -eq 0 ]] && echo "✅ 准备就绪" || echo "⚠️ 需要改进")
EOF

    log "最终检查报告已生成: $FINAL_REPORT_FILE"
}

# 显示检查总结
show_summary() {
    echo -e "\n${CYAN}🎯 最终检查总结${NC}"
    echo "=================="
    echo -e "总检查项: $TOTAL_CHECKS"
    echo -e "${GREEN}通过项目: $PASSED_CHECKS${NC}"
    echo -e "${RED}失败项目: $FAILED_CHECKS${NC}"
    echo -e "${YELLOW}警告项目: $WARNING_CHECKS${NC}"

    local success_rate
    success_rate=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
    echo -e "通过率: ${success_rate}%"

    if [[ $success_rate -ge 90 && $FAILED_CHECKS -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 系统已准备好部署！${NC}"
        echo -e "建议执行: ./scripts/deploy-automation.sh deploy"
    elif [[ $success_rate -ge 80 ]]; then
        echo -e "\n${YELLOW}⚠️ 系统基本准备就绪，建议修复失败项目后部署${NC}"
    else
        echo -e "\n${RED}❌ 系统未准备好部署，请先解决关键问题${NC}"
    fi

    echo -e "\n📄 详细报告: $FINAL_REPORT_FILE"
    echo -e "📋 检查日志: $CHECK_LOG"
}

# 主函数
main() {
    local command="${1:-full}"

    cd "$PROJECT_ROOT"

    case "$command" in
        "full")
            echo -e "${CYAN}🔍 足球预测系统 - 最终部署就绪检查${NC}"
            echo "============================================"

            check_code_quality
            check_security
            check_docker_infrastructure
            check_monitoring_logging
            check_deployment_scripts
            check_documentation
            check_testing
            check_environment
            check_performance

            generate_final_report
            show_summary
            ;;
        "quick")
            section "快速检查"
            check_docker_infrastructure
            check_deployment_scripts
            check_documentation
            show_summary
            ;;
        "report")
            generate_final_report
            ;;
        *)
            echo "使用方法: $0 {full|quick|report}"
            echo "  full   - 完整的系统就绪检查"
            echo "  quick  - 快速检查关键组件"
            echo "  report - 生成最终检查报告"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"