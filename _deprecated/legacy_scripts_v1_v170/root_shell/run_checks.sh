#!/bin/bash
# ============================================
# FootballPrediction V29.0 - CI 质量门禁
# ============================================
# 自动化测试与代码质量检查
# 生成时间: 2025-12-30
# 状态: V29.1 CI Ready (含模型性能回归测试)
# ============================================
# 功能:
#   1. 代码格式化 (black/ruff)
#   2. 导入排序 (isort)
#   3. Lint 检查 (flake8/ruff)
#   4. 类型检查 (mypy)
#   5. 单元测试 (pytest)
#   6. 模型性能回归测试 (baseline accuracy gate)
#   7. 安全扫描 (bandit)
# ============================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# ============================================
# 1. 导入排序检查
# ============================================
print_header "Step 1/7: 导入排序检查 (isort)"
if command -v isort &> /dev/null; then
    isort --check-only --diff src/ tests/ || {
        print_error "导入排序检查失败"
        print_warning "运行 'isort src/ tests/' 修复"
        exit 1
    }
    print_success "导入排序检查通过"
else
    print_warning "isort 未安装，跳过"
fi

# ============================================
# 2. 代码格式化检查
# ============================================
print_header "Step 2/7: 代码格式化检查"
if command -v ruff &> /dev/null; then
    ruff format --check src/ tests/ || {
        print_error "代码格式化检查失败"
        print_warning "运行 'ruff format src/ tests/' 修复"
        exit 1
    }
    print_success "代码格式化检查通过"
elif command -v black &> /dev/null; then
    black --check src/ tests/ || {
        print_error "代码格式化检查失败"
        print_warning "运行 'black src/ tests/' 修复"
        exit 1
    }
    print_success "代码格式化检查通过"
else
    print_warning "ruff/black 未安装，跳过"
fi

# ============================================
# 3. Lint 检查
# ============================================
print_header "Step 3/7: Lint 检查"
if command -v ruff &> /dev/null; then
    ruff check src/ tests/ || {
        print_error "Lint 检查失败"
        print_warning "运行 'ruff check src/ tests/ --fix' 修复"
        exit 1
    }
    print_success "Lint 检查通过"
elif command -v flake8 &> /dev/null; then
    flake8 src/ tests/ --max-line-length=120 --extend-ignore=E203,W503 || {
        print_error "Lint 检查失败"
        exit 1
    }
    print_success "Lint 检查通过"
else
    print_warning "ruff/flake8 未安装，跳过"
fi

# ============================================
# 4. 类型检查
# ============================================
print_header "Step 4/7: 类型检查 (mypy)"
if command -v mypy &> /dev/null; then
    mypy src/ --ignore-missing-imports --no-error-summary || {
        print_error "类型检查失败"
        exit 1
    }
    print_success "类型检查通过"
else
    print_warning "mypy 未安装，跳过"
fi

# ============================================
# 5. 单元测试
# ============================================
print_header "Step 5/7: 单元测试 (pytest)"
if command -v pytest &> /dev/null; then
    # 运行核心测试套件
    pytest tests/ml/test_backtest_engine.py tests/ops/test_signal_generator.py -v --tb=short || {
        print_error "单元测试失败"
        exit 1
    }
    print_success "单元测试通过"
else
    print_warning "pytest 未安装，跳过"
fi

# ============================================
# 6. 模型性能回归测试
# ============================================
print_header "Step 6/7: 模型性能回归测试"
if command -v python &> /dev/null; then
    # 运行模型性能测试（含自动门禁）
    python tests/ml/test_model_performance.py || {
        print_error "模型性能回归测试失败"
        print_warning "已生成报告: logs/performance_report.json"
        print_warning "模型精度低于红线 (55%)，已发送 CRITICAL 告警"
        print_warning "部署已被阻止！请检查模型或数据质量"
        exit 1
    }
    print_success "模型性能回归测试通过"
else
    print_warning "Python 未安装，跳过"
fi

# ============================================
# 7. 安全扫描
# ============================================
print_header "Step 7/7: 安全扫描 (bandit)"
if command -v bandit &> /dev/null; then
    bandit -r src/ -f screen -ll || {
        print_error "安全扫描发现高危问题"
        exit 1
    }
    print_success "安全扫描通过"
else
    print_warning "bandit 未安装，跳过"
fi

# ============================================
# 全部通过
# ============================================
print_header "CI 质量门禁: 全部通过 ✓"
echo ""
echo -e "${GREEN}所有检查已通过，可以部署到生产环境！${NC}"
echo ""
echo "下一步操作:"
echo "  1. 构建镜像: docker build -f Dockerfile.production -t footballprediction:v29.0 ."
echo "  2. 启动服务: docker-compose -f docker-compose.production.yml up -d"
echo ""
exit 0
