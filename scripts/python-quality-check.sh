#!/bin/bash
"""
Python代码质量检查脚本
模拟Claude Skills的python-code-quality功能
提供企业级的代码质量自动化检查
"""

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 检查工具安装状态
check_tools() {
    print_header "🔧 检查Python代码质量工具"

    local tools=("black" "flake8" "isort" "mypy" "ruff" "bandit" "pre-commit")
    local missing_tools=()

    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            print_success "$tool 已安装"
        else
            print_error "$tool 未安装"
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo ""
        print_warning "缺失工具: ${missing_tools[*]}"
        print_info "请运行: ./setup-python-quality-tools.sh 安装所需工具"
        return 1
    fi

    return 0
}

# 运行Black格式化检查
check_black_format() {
    print_header "🎨 Black格式化检查"

    if black --check --diff src/ tests/ scripts/ > /dev/null 2>&1; then
        print_success "Black格式化检查通过"
        return 0
    else
        print_error "Black格式化检查失败"
        black --check --diff src/ tests/ scripts/
        echo ""
        print_info "修复建议: 运行 'make format' 自动格式化"
        return 1
    fi
}

# 运行isort导入排序检查
check_isort() {
    print_header "📦 isort导入排序检查"

    if isort --check-only --diff src/ tests/ scripts/ > /dev/null 2>&1; then
        print_success "isort导入排序检查通过"
        return 0
    else
        print_error "isort导入排序检查失败"
        isort --check-only --diff src/ tests/ scripts/
        echo ""
        print_info "修复建议: 运行 'make format' 自动排序导入"
        return 1
    fi
}

# 运行Flake8代码风格检查
check_flake8() {
    print_header "🔍 Flake8代码风格检查"

    local flake8_output
    flake8_output=$(flake8 src/ tests/ scripts/ 2>&1 || true)

    if [ -z "$flake8_output" ]; then
        print_success "Flake8代码风格检查通过"
        return 0
    else
        print_error "Flake8发现风格问题"
        echo "$flake8_output"
        echo ""
        local issue_count=$(echo "$flake8_output" | wc -l)
        print_warning "发现 $issue_count 个风格问题"
        print_info "修复建议: 运行 'make quality-fix' 自动修复部分问题"
        return 1
    fi
}

# 运行Ruff检查（现代化工具）
check_ruff() {
    print_header "⚡ Ruff现代化代码检查"

    if ruff check src/ tests/ scripts/ --output-format=text > /dev/null 2>&1; then
        print_success "Ruff代码检查通过"
        return 0
    else
        print_error "Ruff发现代码问题"
        ruff check src/ tests/ scripts/ --output-format=text
        echo ""
        print_info "修复建议: 运行 'ruff check src/ tests/ scripts/ --fix' 自动修复"
        return 1
    fi
}

# 运行MyPy类型检查
check_mypy() {
    print_header "🔍 MyPy类型检查"

    if mypy src/ --ignore-missing-imports > /dev/null 2>&1; then
        print_success "MyPy类型检查通过"
        return 0
    else
        print_error "MyPy发现类型问题"
        mypy src/ --ignore-missing-imports
        echo ""
        print_info "修复建议: 添加类型注解或使用# type: ignore"
        return 1
    fi
}

# 运行Bandit安全检查
check_bandit() {
    print_header "🔒 Bandit安全检查"

    if bandit -r src/ -f json -o bandit-report.json > /dev/null 2>&1; then
        print_success "Bandit安全检查通过"
        return 0
    else
        print_error "Bandit发现安全问题"
        bandit -r src/
        echo ""
        print_warning "安全报告已生成: bandit-report.json"
        return 1
    fi
}

# 运行Safety依赖检查
check_safety() {
    print_header "🛡️ Safety依赖漏洞检查"

    if safety check > /dev/null 2>&1; then
        print_success "Safety依赖检查通过"
        return 0
    else
        print_error "Safety发现依赖漏洞"
        safety check
        echo ""
        print_info "修复建议: 更新有漏洞的依赖包"
        return 1
    fi
}

# 运行代码复杂度分析
check_complexity() {
    print_header "📊 代码复杂度分析"

    local high_complexity
    high_complexity=$(radon cc src/ --min B --show-complexity | grep "B\|C\|D\|E\|F" | wc -l || true)

    if [ "$high_complexity" -eq 0 ]; then
        print_success "所有函数复杂度都在安全范围内"
        return 0
    else
        print_warning "发现 $high_complexity 个高复杂度函数"
        echo ""
        print_info "高复杂度函数详情:"
        radon cc src/ --min B --show-complexity | grep "B\|C\|D\|E\|F" | head -10
        echo ""
        print_info "建议: 重构高复杂度函数以提高可维护性"
        return 1
    fi
}

# 运行死代码检测
check_dead_code() {
    print_header "🗑️ 死代码检测"

    if vulture src/ --min-confidence 80 > /dev/null 2>&1; then
        print_success "未发现明显的死代码"
        return 0
    else
        print_warning "发现可能的死代码"
        vulture src/ --min-confidence 80
        echo ""
        print_info "建议: 删除未使用的代码以提高代码质量"
        return 1
    fi
}

# 生成质量报告
generate_quality_report() {
    print_header "📋 生成代码质量报告"

    local report_file="quality-report-$(date +%Y%m%d-%H%M%S).md"

    cat > "$report_file" << EOF
# Python代码质量检查报告

**生成时间**: $(date '+%Y-%m-%d %H:%M:%S')
**检查工具**: Black, Flake8, MyPy, Ruff, Bandit, Safety

## 检查结果

### ✅ 通过的检查
$(if check_black_format &>/dev/null; then echo "- ✅ Black格式化"; else echo "- ❌ Black格式化"; fi)
$(if check_isort &>/dev/null; then echo "- ✅ isort导入排序"; else echo "- ❌ isort导入排序"; fi)
$(if check_flake8 &>/dev/null; then echo "- ✅ Flake8代码风格"; else echo "- ❌ Flake8代码风格"; fi)
$(if check_mypy &>/dev/null; then echo "- ✅ MyPy类型检查"; else echo "- ❌ MyPy类型检查"; fi)
$(if bandit -r src/ -f json &>/dev/null; then echo "- ✅ Bandit安全检查"; else echo "- ❌ Bandit安全检查"; fi)
$(if safety check &>/dev/null; then echo "- ✅ Safety依赖检查"; else echo "- ❌ Safety依赖检查"; fi)

### 📊 代码统计
\`\`\`bash
find src/ -name "*.py" | wc -l  # Python文件数量
find src/ -name "*.py" | xargs wc -l  # 总代码行数
\`\`\`

## 修复建议

### 立即修复
1. 运行 \`make format\` 自动格式化代码
2. 运行 \`make quality-fix\` 自动修复部分问题
3. 更新有漏洞的依赖包

### 中期改进
1. 重构高复杂度函数
2. 删除死代码
3. 完善类型注解

### 长期优化
1. 建立代码质量门禁
2. 集成CI/CD质量检查
3. 定期代码审查

---
*报告由Python代码质量Claude Skill生成*
EOF

    print_success "质量报告已生成: $report_file"
}

# 计算质量分数
calculate_quality_score() {
    local score=0
    local max_score=100

    # 每个检查的权重
    local weights=(
        "black:20"
        "isort:10"
        "flake8:15"
        "ruff:15"
        "mypy:20"
        "bandit:15"
        "safety:5"
    )

    for weight_info in "${weights[@]}"; do
        local tool=$(echo "$weight_info" | cut -d: -f1)
        local weight=$(echo "$weight_info" | cut -d: -f2)

        case $tool in
            "black")
                if check_black_format &>/dev/null; then
                    score=$((score + weight))
                fi
                ;;
            "isort")
                if check_isort &>/dev/null; then
                    score=$((score + weight))
                fi
                ;;
            "flake8")
                if check_flake8 &>/dev/null; then
                    score=$((score + weight))
                fi
                ;;
            "ruff")
                if check_ruff &>/dev/null; then
                    score=$((score + weight))
                fi
                ;;
            "mypy")
                if check_mypy &>/dev/null; then
                    score=$((score + weight))
                fi
                ;;
            "bandit")
                if check_bandit &>/dev/null; then
                    score=$((score + weight))
                fi
                ;;
            "safety")
                if check_safety &>/dev/null; then
                    score=$((score + weight))
                fi
                ;;
        esac
    done

    echo "$score"
}

# 显示质量分数
show_quality_score() {
    local score=$(calculate_quality_score)

    print_header "🎯 代码质量分数"

    echo ""
    echo "当前质量分数: $score/100"

    if [ "$score" -ge 90 ]; then
        echo "质量等级: 🥇 优秀"
    elif [ "$score" -ge 80 ]; then
        echo "质量等级: 🥈 良好"
    elif [ "$score" -ge 70 ]; then
        echo "质量等级: 🥉 一般"
    elif [ "$score" -ge 60 ]; then
        echo "质量等级: ⚠️  需改进"
    else
        echo "质量等级: ❌ 差"
    fi

    echo ""
    print_info "质量目标: 85/100 (企业级标准)"
    print_info "当前差距: $((85 - score)) 分"
}

# 主函数
main() {
    local mode="${1:-check}"

    case "$mode" in
        "check")
            print_header "🤖 Python代码质量Claude Skill检查"
            print_info "运行企业级Python代码质量检查..."

            # 检查工具安装
            if ! check_tools; then
                exit 1
            fi

            # 运行各项检查
            local failed_checks=()

            if ! check_black_format; then
                failed_checks+=("Black格式化")
            fi

            if ! check_isort; then
                failed_checks+=("isort导入排序")
            fi

            if ! check_flake8; then
                failed_checks+=("Flake8代码风格")
            fi

            if ! check_ruff; then
                failed_checks+=("Ruff现代化检查")
            fi

            if ! check_mypy; then
                failed_checks+=("MyPy类型检查")
            fi

            if ! check_bandit; then
                failed_checks+=("Bandit安全检查")
            fi

            if ! check_safety; then
                failed_checks+=("Safety依赖检查")
            fi

            # 运行分析检查
            check_complexity
            check_dead_code

            # 生成报告
            generate_quality_report
            show_quality_score

            # 显示结果
            print_header "📋 检查结果汇总"
            if [ ${#failed_checks[@]} -eq 0 ]; then
                print_success "🎉 所有检查都通过了！代码质量优秀！"
                exit 0
            else
                print_error "❌ 以下检查未通过:"
                for check in "${failed_checks[@]}"; do
                    echo "   • $check"
                done
                echo ""
                print_warning "💡 建议运行: make quality-fix 自动修复部分问题"
                exit 1
            fi
            ;;

        "format")
            print_header "🎨 自动格式化代码"
            print_info "运行Black格式化..."
            black src/ tests/ scripts/

            print_info "运行isort导入排序..."
            isort src/ tests/ scripts/

            print_success "✅ 代码格式化完成"
            ;;

        "fix")
            print_header "🔧 自动修复代码质量问题"
            print_info "运行Black格式化..."
            black src/ tests/ scripts/

            print_info "运行isort导入排序..."
            isort src/ tests/ scripts/

            print_info "运行Ruff自动修复..."
            ruff check src/ tests/ scripts/ --fix

            print_success "✅ 自动修复完成"
            ;;

        "score")
            show_quality_score
            ;;

        "help"|"-h"|"--help")
            echo "Python代码质量Claude Skill"
            echo ""
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  check     - 运行完整质量检查 (默认)"
            echo "  format    - 自动格式化代码"
            echo "  fix       - 自动修复质量问题"
            echo "  score     - 显示质量分数"
            echo "  help      - 显示帮助信息"
            ;;

        *)
            echo "未知选项: $1"
            echo "使用 '$0 help' 查看帮助信息"
            exit 1
            ;;
    esac
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi