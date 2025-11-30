#!/bin/bash
# 🚨 V5.3 - 妥协但诚实：在开发容器中模拟 CI
# ⚠️ 警告：这将在当前容器中完全重置Python环境，模拟真正的CI行为

set -euo pipefail  # 严格模式

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_header() {
    echo -e "${BLUE}=== 🚨 CI模拟脚本 V5.3 ===${NC}"
    echo -e "${BLUE}=== 妥协但诚实：真实模拟CI环境 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# 主函数
main() {
    print_header

    print_warning "⚠️ 警告：这将在当前容器中重置 Python 环境，模拟真正的CI行为"
    print_warning "⚠️ 所有已安装的Python包将被卸载并重新安装"
    print_warning "⚠️ 这是一个破坏性操作，仅用于CI模拟"

    echo
    read -p "确认继续吗？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "用户取消操作"
        exit 0
    fi

    print_info "🔄 开始真实CI环境模拟..."
    echo

    # 1. 设置CI环境变量（完全复现GitHub Actions）
    print_info "📋 设置CI环境变量..."
    export DATABASE_URL="postgresql://postgres:postgres@db:5432/football_prediction"
    export REDIS_URL="redis://redis:6379/0"
    export ENV="testing"
    export CI="true"
    export TESTING="true"
    export DEBUG="false"
    export LOG_LEVEL="WARNING"
    export PYTHONPATH="/app:$PYTHONPATH"
    export PYTEST_CURRENT_TEST="1"
    export MALLOC_ARENA_MAX="2"
    export FOOTBALL_PREDICTION_ML_MODE="mock"
    export INFERENCE_SERVICE_MOCK="true"
    export SKIP_ML_MODEL_LOADING="true"
    export XGBOOST_MOCK="true"
    export JOBLIB_MOCK="true"

    print_success "环境变量设置完成"

    # 2. 创建测试数据文件（复现CI数据准备步骤）
    print_info "📁 创建测试数据文件..."
    mkdir -p /app/data /app/logs

    # 创建 dataset_v1.csv 示例数据
    cat > /app/data/dataset_v1.csv << 'EOF'
date,home_team,away_team,home_score,away_score,result
2024-01-01,Manchester United,Liverpool,2,1,H
2024-01-02,Arsenal,Chelsea,1,1,D
2024-01-03,Manchester City,Tottenham,3,0,H
2024-01-04,Newcastle,Everton,1,2,A
2024-01-05,Leicester,West Ham,2,2,D
EOF

    # 创建必要的日志文件
    touch /app/logs/enhanced_ev_test.log

    print_success "测试数据文件创建完成"

    # 3. 卸载所有已安装的包（模拟CI的纯净环境）
    print_info "🧹 清理现有Python环境..."
    print_warning "正在卸载所有已安装的包..."

    # 获取所有已安装的包并卸载（排除系统必需包）
    pip list --format=freeze | grep -v "^pip=" | grep -v "^setuptools=" | grep -v "^wheel=" | cut -d'=' -f1 > /tmp/packages_to_remove.txt

    if [ -s /tmp/packages_to_remove.txt ]; then
        print_info "发现以下包将被卸载："
        cat /tmp/packages_to_remove.txt | head -10
        if [ $(wc -l < /tmp/packages_to_remove.txt) -gt 10 ]; then
            echo "... 还有 $(($(wc -l < /tmp/packages_to_remove.txt) - 10)) 个包"
        fi

        # 批量卸载
        xargs pip uninstall -y < /tmp/packages_to_remove.txt || true
        print_success "包卸载完成"
    else
        print_info "没有发现需要卸载的包"
    fi

    # 4. 升级pip并安装核心工具（模拟CI初始步骤）
    print_info "📦 安装核心工具..."
    python -m pip install --upgrade pip
    pip install pip-tools
    print_success "核心工具安装完成"

    # 5. 安装CI依赖（完全复现CI安装过程）
    print_info "📚 安装CI依赖..."
    print_info "正在安装 requirements-ci.txt..."
    pip install -r /app/requirements-ci.txt
    print_success "CI依赖安装完成"

    # 6. 验证环境（模拟CI环境检查）
    print_info "🔍 验证CI环境..."
    python -c "
import sys
print(f'✅ Python版本: {sys.version}')
print('✅ 核心模块导入测试...')
import pytest
import fastapi
import sqlalchemy
import redis
import pandas
print('✅ 核心模块导入成功')
"

    # 7. 运行代码检查（复现CI代码检查步骤）
    print_info "🔍 运行代码检查..."
    if command -v ruff &> /dev/null; then
        ruff check src/ tests/ || print_warning "代码检查发现问题，继续执行测试"
    else
        print_warning "ruff未安装，跳过代码检查"
    fi

    # 8. 运行安全扫描（复现CI安全检查）
    print_info "🛡️ 运行安全扫描..."
    if command -v bandit &> /dev/null; then
        bandit -r src/ -f json -o bandit-report.json || print_warning "安全扫描完成，可能发现问题"
    else
        print_warning "bandit未安装，跳过安全扫描"
    fi

    # 9. 运行测试套件（完全复现CI测试命令）
    print_info "🧪 运行完整测试套件..."
    print_info "使用与CI完全相同的测试参数..."

    # 设置测试超时
    timeout 600s python -m pytest tests/unit/ \
        --ignore=tests/unit/ml/ \
        --ignore=tests/unit/scripts/ \
        --ignore=tests/unit/collectors/ \
        --timeout=30 \
        --timeout-method=thread \
        --cov=src \
        --cov-report=xml:test-results-full.xml \
        --cov-report=html:htmlcov-full \
        --cov-report=term-missing \
        --maxfail=5 \
        -x \
        -v \
        --tb=short

    TEST_EXIT_CODE=$?

    echo
    print_info "📋 生成CI模拟报告..."
    echo "=== CI模拟报告 ===" > ci-simulation-report.txt
    echo "模拟时间: $(date)" >> ci-simulation-report.txt
    echo "测试状态: $([ $TEST_EXIT_CODE -eq 0 ] && echo '✅ 通过' || echo '❌ 失败')" >> ci-simulation-report.txt
    echo "覆盖率报告: htmlcov-full/index.html" >> ci-simulation-report.txt
    echo "测试结果: test-results-full.xml" >> ci-simulation-report.txt
    echo "安全扫描: bandit-report.json" >> ci-simulation-report.txt
    cat ci-simulation-report.txt

    # 10. 显示结果
    echo
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        print_success "🎉 CI模拟测试通过！"
        print_success "代码已准备好推送到远程仓库！"
        echo
        print_info "📊 生成的报告："
        if [ -f "test-results-full.xml" ]; then
            print_success "测试结果: test-results-full.xml"
        fi
        if [ -d "htmlcov-full" ]; then
            print_success "覆盖率报告: htmlcov-full/index.html"
        fi
        if [ -f "bandit-report.json" ]; then
            print_success "安全扫描报告: bandit-report.json"
        fi
    else
        print_error "❌ CI模拟测试失败！"
        print_error "请检查日志并修复问题后再提交代码"
        echo
        print_info "🔧 故障排除："
        echo "1. 查看详细测试日志"
        echo "2. 检查依赖安装是否成功"
        echo "3. 验证环境变量设置"
    fi

    echo
    print_info "📋 CI模拟完成报告："
    cat ci-simulation-report.txt

    exit $TEST_EXIT_CODE
}

# 脚本入口点
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi