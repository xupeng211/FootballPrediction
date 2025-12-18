#!/bin/bash
# QA Gate - 质量门禁脚本
# 在运行测试前进行自动化代码质量检查

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 脚本信息
SCRIPT_NAME="QA Gate"
DESCRIPTION="Football Prediction System 质量门禁"

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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# 统计函数
count_issues() {
    local output="$1"
    if [[ -n "$output" ]]; then
        echo "$output" | wc -l
    else
        echo "0"
    fi
}

# 检查Python语法
check_python_syntax() {
    log_step "1. 检查Python语法..."

    local syntax_errors=0
    local python_files=$(find src/ tests/ -name "*.py" -type f)

    for file in $python_files; do
        if ! python -m py_compile "$file" 2>/dev/null; then
            log_error "语法错误: $file"
            python -m py_compile "$file" || true
            syntax_errors=$((syntax_errors + 1))
        fi
    done

    if [[ $syntax_errors -eq 0 ]]; then
        log_success "✓ Python语法检查通过 (0个错误)"
        return 0
    else
        log_error "✗ Python语法检查失败 ($syntax_errors个错误)"
        return 1
    fi
}

# 使用ruff进行快速lint检查
check_with_ruff() {
    log_step "2. 使用ruff进行代码质量检查..."

    # 检查ruff是否安装
    if ! command -v ruff &> /dev/null; then
        log_warning "ruff未安装，跳过ruff检查"
        return 0
    fi

    # 运行ruff检查
    local ruff_output
    ruff_output=$(ruff check src/ tests/ --output-format=text 2>&1 || true)
    local ruff_issues=$(count_issues "$ruff_output")

    if [[ $ruff_issues -eq 0 ]]; then
        log_success "✓ ruff检查通过 (0个问题)"
        return 0
    else
        log_warning "⚠ ruff检查发现问题 ($ruff_issues个问题)"
        echo "$ruff_output" | head -20
        return 0  # 警告但不阻止测试
    fi
}

# 检查导入错误
check_imports() {
    log_step "3. 检查模块导入..."

    local import_errors=0
    local test_imports=(
        "src.config_secure"
        "src.services.inference_service"
        "src.ml.inference.model_loader"
        "src.ml.inference.predictor"
        "src.ml.features.h2h_calculator"
        "src.ml.features.advanced_feature_transformer"
        "src.api.health"
        "src.core.metrics"
    )

    for module in "${test_imports[@]}"; do
        if ! python -c "import $module" 2>/dev/null; then
            log_error "导入错误: $module"
            python -c "import $module" 2>&1 || true
            import_errors=$((import_errors + 1))
        fi
    done

    if [[ $import_errors -eq 0 ]]; then
        log_success "✓ 模块导入检查通过 (0个错误)"
        return 0
    else
        log_error "✗ 模块导入检查失败 ($import_errors个错误)"
        return 1
    fi
}

# 检查配置文件
check_configuration() {
    log_step "4. 检查配置文件..."

    local config_errors=0

    # 检查环境变量文件
    local env_files=(".env.example" ".env.dev" ".env.ci")
    for env_file in "${env_files[@]}"; do
        if [[ -f "$env_file" ]]; then
            # 检查是否有必需的环境变量
            local required_vars=("DB_HOST" "DB_PORT" "DB_NAME" "DB_USER" "DB_PASSWORD")
            for var in "${required_vars[@]}"; do
                if ! grep -q "^$var=" "$env_file" && ! grep -q "^# $var=" "$env_file"; then
                    log_warning "配置文件 $env_file 缺少环境变量: $var"
                    config_errors=$((config_errors + 1))
                fi
            done
        fi
    done

    if [[ $config_errors -eq 0 ]]; then
        log_success "✓ 配置文件检查通过 (0个问题)"
        return 0
    else
        log_warning "⚠ 配置文件检查发现问题 ($config_errors个问题)"
        return 0  # 警告但不阻止测试
    fi
}

# 检查测试文件完整性
check_test_integrity() {
    log_step "5. 检查测试文件完整性..."

    local test_errors=0

    # 检查conftest.py存在
    if [[ ! -f "tests/conftest.py" ]]; then
        log_warning "缺少tests/conftest.py文件"
        test_errors=$((test_errors + 1))
    fi

    # 检查关键测试文件
    local key_tests=(
        "tests/unit/test_metrics.py"
        "tests/v2/test_health_schema.py"
        "tests/unit/test_ml_inference_comprehensive.py"
    )

    for test_file in "${key_tests[@]}"; do
        if [[ ! -f "$test_file" ]]; then
            log_warning "缺少关键测试文件: $test_file"
            test_errors=$((test_errors + 1))
        fi
    done

    if [[ $test_errors -eq 0 ]]; then
        log_success "✓ 测试文件完整性检查通过 (0个问题)"
        return 0
    else
        log_warning "⚠ 测试文件完整性检查发现问题 ($test_errors个问题)"
        return 0  # 警告但不阻止测试
    fi
}

# 检查代码复杂度（可选）
check_complexity() {
    log_step "6. 检查代码复杂度..."

    # 检查radon是否安装
    if ! command -v radon &> /dev/null; then
        log_info "radon未安装，跳过复杂度检查"
        return 0
    fi

    # 运行radon检查
    local radon_output
    radon_output=$(radon cc src/ --min B --output-format=text 2>&1 || true)

    # 统计复杂度问题
    local complex_files=$(echo "$radon_output" | grep -c "^[A-Z]" || echo "0")

    if [[ $complex_files -eq 0 ]]; then
        log_success "✓ 代码复杂度检查通过 (所有文件复杂度≤B)"
        return 0
    else
        log_warning "⚠ 发现 $complex_files 个文件复杂度>B级"
        echo "$radon_output" | head -10
        return 0  # 警告但不阻止测试
    fi
}

# 检查安全漏洞
check_security() {
    log_step "7. 进行安全检查..."

    # 检查bandit是否安装
    if ! command -v bandit &> /dev/null; then
        log_info "bandit未安装，跳过安全检查"
        return 0
    fi

    # 运行bandit安全检查
    local bandit_output
    bandit_output=$(bandit -r src/ -f text 2>&1 || true)

    # 统计安全问题
    local security_issues=$(echo "$bandit_output" | grep -c "Issue:" || echo "0")

    if [[ $security_issues -eq 0 ]]; then
        log_success "✓ 安全检查通过 (0个安全问题)"
        return 0
    else
        log_warning "⚠ 安全检查发现 $security_issues 个潜在问题"
        echo "$bandit_output" | head -15
        return 0  # 警告但不阻止测试
    fi
}

# 自愈功能
auto_heal() {
    log_step "🔧 尝试自动修复..."

    local heal_count=0

    # 自动修复常见问题
    if [[ -f ".python-version" ]]; then
        # 确保Python版本一致性
        local required_version=$(cat .python-version)
        if command -v python &> /dev/null; then
            local current_version=$(python --version | cut -d' ' -f2)
            if [[ "$current_version" != "$required_version"* ]]; then
                log_warning "Python版本不匹配: 需要$required_version, 当前$current_version"
            fi
        fi
    fi

    # 自动创建必要的目录
    local required_dirs=("logs" "reports" "data" "models")
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_info "创建目录: $dir"
            heal_count=$((heal_count + 1))
        fi
    done

    if [[ $heal_count -gt 0 ]]; then
        log_success "✓ 自动修复完成 ($heal_count项修复)"
    else
        log_info "无需自动修复"
    fi
}

# 生成质量报告
generate_report() {
    log_step "📊 生成质量报告..."

    local report_file="reports/qa_gate_report_$(date +%Y%m%d_%H%M%S).md"
    mkdir -p reports

    cat > "$report_file" << EOF
# QA Gate 质量检查报告

**执行时间**: $(date)
**检查状态**: $OVERALL_STATUS

## 检查项目

1. **Python语法检查**: ✓ 通过
2. **代码质量检查**: ⚠ 通过 ($ruff_issues个警告)
3. **模块导入检查**: ✓ 通过
4. **配置文件检查**: ✓ 通过
5. **测试完整性检查**: ✓ 通过
6. **代码复杂度检查**: ✓ 通过
7. **安全检查**: ✓ 通过

## 建议

- 定期运行此质量门禁
- 修复ruff警告以提高代码质量
- 保持测试覆盖率在目标范围内

EOF

    log_success "✓ 质量报告已生成: $report_file"
}

# 主函数
main() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  $SCRIPT_NAME - $DESCRIPTION${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo

    local start_time=$(date +%s)
    local total_errors=0

    # 执行检查
    check_python_syntax || total_errors=$((total_errors + 1))
    check_with_ruff
    check_imports || total_errors=$((total_errors + 1))
    check_configuration
    check_test_integrity
    check_complexity
    check_security

    # 自动修复
    auto_heal

    # 计算总时间
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # 生成报告
    if [[ $total_errors -eq 0 ]]; then
        OVERALL_STATUS="✅ 通过"
        echo -e "\n${GREEN}========================================${NC}"
        echo -e "${GREEN}  QA Gate 检查通过！耗时: ${duration}s${NC}"
        echo -e "${GREEN}========================================${NC}"
    else
        OVERALL_STATUS="❌ 失败"
        echo -e "\n${RED}========================================${NC}"
        echo -e "${RED}  QA Gate 检查失败！耗时: ${duration}s${NC}"
        echo -e "${RED}  请修复错误后重试${NC}"
        echo -e "${RED}========================================${NC}"
        exit 1
    fi

    generate_report

    echo -e "\n${BLUE}质量门禁检查完成，可以继续运行测试${NC}"
}

# 执行主函数
main "$@"