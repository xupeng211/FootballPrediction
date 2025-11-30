#!/bin/bash
# 🚀 本地CI模拟器 V5.0 - 拒绝等待
# 完全复现GitHub Actions环境，让你在本地就能跑CI！

set -euo pipefail  # 严格模式：遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_header() {
    echo -e "${BLUE}=== 🏗️ 本地CI模拟器 V5.0 ===${NC}"
    echo -e "${BLUE}=== 拒绝等待，本地跑CI！ ===${NC}"
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
    echo -e "${CYAN}ℹ️ $1${NC}"
}

# 显示帮助信息
show_help() {
    echo -e "${PURPLE}📖 本地CI模拟器使用指南${NC}"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  -c, --clean    仅清理容器和数据"
    echo "  -b, --build    强制重新构建镜像"
    echo "  -v, --verbose  详细输出模式"
    echo "  -f, --fast     快速模式（跳过代码检查）"
    echo
    echo "示例:"
    echo "  $0              # 标准CI运行"
    echo "  $0 --fast       # 快速模式（仅测试）"
    echo "  $0 --clean      # 清理环境"
    echo
    echo "📊 CI报告输出："
    echo "  - 覆盖率报告: htmlcov/index.html"
    echo "  - 测试结果: test-results.xml"
    echo "  - 安全扫描: bandit-report.json"
    echo
}

# 检查Docker和Docker Compose是否安装
check_dependencies() {
    print_info "检查系统依赖..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi

    # 检查Docker是否运行
    if ! docker info &> /dev/null; then
        print_error "Docker服务未启动，请启动Docker服务"
        exit 1
    fi

    print_success "依赖检查通过"
}

# 清理CI环境
clean_environment() {
    print_info "🧹 清理本地CI环境..."

    # 停止并删除CI相关容器
    if docker-compose -f docker-compose.ci.yml ps -q &> /dev/null; then
        docker-compose -f docker-compose.ci.yml down -v --remove-orphans
    fi

    # 删除CI相关镜像（可选）
    if docker images -q football-prediction-ci-runner &> /dev/null; then
        read -p "是否删除CI镜像？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker rmi football-prediction-ci-runner 2>/dev/null || true
            print_success "CI镜像已删除"
        fi
    fi

    # 清理生成的文件
    rm -f test-results-full.xml ci-report.txt bandit-report.json
    rm -rf htmlcov/ htmlcov-full/

    print_success "环境清理完成"
}

# 运行本地CI
run_local_ci() {
    local build_flag=""
    local fast_mode=false

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -c|--clean)
                clean_environment
                exit 0
                ;;
            -b|--build)
                build_flag="--build"
                shift
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            -f|--fast)
                fast_mode=true
                shift
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done

    print_header

    # 检查依赖
    check_dependencies

    # 确保配置文件存在
    if [[ ! -f "docker-compose.ci.yml" ]]; then
        print_error "未找到 docker-compose.ci.yml 配置文件"
        exit 1
    fi

    if [[ ! -f "Dockerfile.ci" ]]; then
        print_error "未找到 Dockerfile.ci 配置文件"
        exit 1
    fi

    # 清理之前的运行
    print_info "🧹 清理之前的CI运行..."
    docker-compose -f docker-compose.ci.yml down -v --remove-orphans 2>/dev/null || true

    print_info "🚀 启动本地CI模拟器..."
    echo

    # 如果是快速模式，修改CI运行器命令
    if [[ "$fast_mode" == "true" ]]; then
        print_warning "⚡ 快速模式：跳过代码检查和安全扫描"

        # 创建临时的快速模式配置
        temp_compose="docker-compose.ci.fast.yml"
        sed 's/ruff check src\/ tests\/ || echo/echo "快速模式：跳过代码检查"/g' docker-compose.ci.yml > "$temp_compose"
        sed -i 's/bandit -r src\/ -f json -o bandit-report.json || echo/echo "快速模式：跳过安全扫描"/g' "$temp_compose"

        # 运行快速模式CI
        if docker-compose -f "$temp_compose" up $build_flag --abort-on-container-exit --exit-code-from ci-runner; then
            CI_EXIT_CODE=0
        else
            CI_EXIT_CODE=$?
        fi

        # 清理临时文件
        rm -f "$temp_compose"
    else
        # 标准CI运行
        if docker-compose -f docker-compose.ci.yml up $build_flag --abort-on-container-exit --exit-code-from ci-runner; then
            CI_EXIT_CODE=0
        else
            CI_EXIT_CODE=$?
        fi
    fi

    echo
    print_info "📋 CI运行完成，生成报告..."

    # 显示CI报告
    if [[ -f "ci-report.txt" ]]; then
        echo
        print_info "📊 CI报告摘要:"
        cat ci-report.txt
    fi

    # 显示输出文件
    echo
    print_info "📁 生成的文件:"

    if [[ -f "test-results-full.xml" ]]; then
        print_success "测试结果: test-results-full.xml"
    fi

    if [[ -d "htmlcov-full" ]]; then
        print_success "覆盖率报告: htmlcov-full/index.html"
        print_info "💡 在浏览器中打开查看: file://$(pwd)/htmlcov-full/index.html"
    fi

    if [[ -f "bandit-report.json" ]]; then
        print_success "安全扫描报告: bandit-report.json"
    fi

    # 显示日志信息
    echo
    print_info "📝 查看详细日志:"
    echo "  docker-compose -f docker-compose.ci.yml logs ci-runner"
    echo

    if [[ $CI_EXIT_CODE -eq 0 ]]; then
        print_success "🎉 本地CI测试通过！可以放心提交代码了！"
        echo
        print_info "💡 提示:"
        echo "  - 查看覆盖率报告: open htmlcov/index.html"
        echo "  - 查看测试详情: cat test-results.xml"
        echo "  - 下次可以使用 --fast 选项快速验证"
    else
        print_error "❌ 本地CI测试失败！请检查日志并修复问题"
        echo
        print_info "🔧 故障排除:"
        echo "  1. 查看详细日志: docker-compose -f docker-compose.ci.yml logs ci-runner"
        echo "  2. 重新构建: $0 --build"
        echo "  3. 清理环境: $0 --clean"
        echo "  4. 查看容器状态: docker-compose -f docker-compose.ci.yml ps"
        echo "  5. 查看测试结果: cat test-results-full.xml"
        echo "  6. 查看覆盖率报告: open htmlcov-full/index.html"
    fi

    exit $CI_EXIT_CODE
}

# 主函数
main() {
    # 如果没有参数，运行标准CI
    if [[ $# -eq 0 ]]; then
        run_local_ci
    else
        run_local_ci "$@"
    fi
}

# 脚本入口点
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi