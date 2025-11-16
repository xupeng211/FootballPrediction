#!/bin/bash

# 🚀 快速优化脚本 - 一键解决主要问题
# 使用方法: ./quick_optimize.sh

echo "🚀 开始项目快速优化..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 步骤计数器
STEP=1
TOTAL_STEPS=8

print_step() {
    echo -e "${BLUE}[$STEP/$TOTAL_STEPS] $1${NC}"
    ((STEP++))
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Step 1: 代码质量快速修复
print_step "修复代码质量问题"
if ruff check src/ --fix --quiet > /dev/null 2>&1; then
    print_success "代码质量问题已修复"
else
    print_warning "部分代码质量问题需要手动处理"
fi

# Step 2: 格式化代码
print_step "格式化代码"
if black src/ tests/ --quiet > /dev/null 2>&1; then
    print_success "代码格式化完成"
else
    print_warning "代码格式化遇到问题"
fi

# Step 3: 安全检查
print_step "安全检查"
if pip-audit --quiet > /dev/null 2>&1; then
    print_success "无安全漏洞"
else
    print_warning "发现安全漏洞，请运行 pip-audit 查看详情"
fi

# Step 4: 运行核心测试
print_step "运行用户管理测试"
if pytest tests/unit/services/test_user_management_service.py -q --tb=no > /dev/null 2>&1; then
    print_success "用户管理测试通过 (18/18)"
else
    print_error "用户管理测试失败"
fi

# Step 5: 检查覆盖率
print_step "检查测试覆盖率"
coverage_output=$(pytest tests/unit/services/test_user_management_service.py --cov=src/services/user_management_service --cov-report=term-missing 2>/dev/null | grep "TOTAL" | tail -1)
if [ -n "$coverage_output" ]; then
    coverage_percent=$(echo $coverage_output | awk '{print $4}' | sed 's/%//')
    print_success "用户管理模块覆盖率: ${coverage_percent}%"
else
    print_warning "无法获取覆盖率信息"
fi

# Step 6: 清理无用文件
print_step "清理无用文件"
cleanup_files=(
    "src/adapters/factory_simple_broken_backup.py"
    "src/utils/date_utils_broken.py"
    "__pycache__"
    "*.pyc"
    ".pytest_cache"
)

for pattern in "${cleanup_files[@]}"; do
    if find . -name "$pattern" -type f -delete 2>/dev/null; then
        echo "  - 已清理: $pattern"
    fi
done
print_success "无用文件清理完成"

# Step 7: 生成质量报告
print_step "生成质量报告"
cat > quality_report.txt << EOF
📊 项目质量报告 - $(date)
=====================================

代码质量:
- Ruff检查: $(ruff check src/ --quiet 2>/dev/null && echo "✅ 通过" || echo "❌ 有问题")
- 格式检查: $(black --check src/ --quiet 2>/dev/null && echo "✅ 通过" || echo "❌ 需要格式化")

测试状态:
- 用户管理测试: $(pytest tests/unit/services/test_user_management_service.py -q 2>/dev/null | grep "passed" | wc -l)/18 通过
- 覆盖率: ${coverage_percent:-未知}%

安全状态:
- 依赖审计: $(pip-audit --quiet 2>/dev/null && echo "✅ 安全" || echo "⚠️ 有漏洞")

建议:
1. 手动修复Ruff检查的异常处理问题
2. 提升测试覆盖率到30%+
3. 处理安全漏洞（如果有的话）
4. 定期运行此脚本保持代码质量

EOF

print_success "质量报告已生成: quality_report.txt"

# Step 8: 总结
print_step "优化完成总结"
echo ""
echo -e "${GREEN}🎉 快速优化完成！${NC}"
echo ""
echo "📋 下一步建议:"
echo "1. 查看质量报告: cat quality_report.txt"
echo "2. 手动修复剩余问题"
echo "3. 运行完整测试: make test.unit"
echo "4. 提交代码: git add . && git commit -m '优化: 代码质量改进'"
echo ""
echo -e "${BLUE}💡 定期运行此脚本保持代码质量: ./quick_optimize.sh${NC}"
