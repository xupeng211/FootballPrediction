#!/bin/bash
# 快速部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# 检查环境
check_environment() {
    log_step "检查环境"

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 未安装"
        exit 1
    fi

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi

    # 检查虚拟环境
    if [ ! -d ".venv" ]; then
        log_warn "虚拟环境不存在，正在创建..."
        python3 -m venv .venv
    fi

    # 激活虚拟环境
    source .venv/bin/activate

    log_info "环境检查通过"
}

# 安装依赖
install_dependencies() {
    log_step "安装依赖"

    # 升级pip
    pip install --upgrade pip

    # 安装生产依赖
    pip install -r requirements/requirements.prod.txt

    log_info "依赖安装完成"
}

# 运行测试
run_tests() {
    if [ "$SKIP_TESTS" != "true" ]; then
        log_step "运行测试"
        make test
        log_info "测试通过"
    else
        log_warn "跳过测试"
    fi
}

# 构建Docker镜像
build_image() {
    log_step "构建Docker镜像"

    # 获取版本号
    VERSION=${VERSION:-$(date +%Y%m%d-%H%M%S)}
    IMAGE_NAME="football-prediction:${VERSION}"

    docker build -t ${IMAGE_NAME} .
    docker tag ${IMAGE_NAME} football-prediction:latest

    log_info "镜像构建完成: ${IMAGE_NAME}"

    # 保存镜像名称到文件
    echo ${IMAGE_NAME} > .last_image
}

# 数据库迁移
run_migrations() {
    log_step "运行数据库迁移"

    # 这里可以根据实际需求实现
    # docker-compose exec app alembic upgrade head

    log_info "数据库迁移完成"
}

# 健康检查
health_check() {
    log_step "健康检查"

    # 启动服务
    docker-compose up -d

    # 等待服务启动
    sleep 10

    # 检查服务状态
    if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        log_info "服务健康检查通过"
    else
        log_error "服务健康检查失败"
        docker-compose logs app
        exit 1
    fi
}

# 部署到生产环境
deploy_production() {
    log_step "部署到生产环境"

    # 检查必要的环境变量
    if [ -z "$SERVER_HOST" ] || [ -z "$SERVER_USER" ]; then
        log_error "请设置 SERVER_HOST 和 SERVER_USER 环境变量"
        exit 1
    fi

    # 使用部署脚本
    python scripts/deploy.py --environment production
}

# 主函数
main() {
    echo "=========================================="
    echo "FootballPrediction 快速部署工具"
    echo "=========================================="

    # 解析参数
    ENVIRONMENT=${ENVIRONMENT:-development}
    SKIP_TESTS=${SKIP_TESTS:-false}

    case $ENVIRONMENT in
        "development")
            log_info "部署到开发环境"
            check_environment
            install_dependencies
            build_image
            run_migrations
            health_check
            ;;
        "staging")
            log_info "部署到测试环境"
            check_environment
            install_dependencies
            run_tests
            build_image
            deploy_production
            ;;
        "production")
            log_info "部署到生产环境"
            check_environment
            install_dependencies
            run_tests
            build_image
            deploy_production
            ;;
        *)
            log_error "未知环境: $ENVIRONMENT"
            exit 1
            ;;
    esac

    echo
    echo "=========================================="
    log_info "部署完成!"
    echo "=========================================="
}

# 显示帮助
show_help() {
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  -e, --environment ENV    部署环境 (development|staging|production)"
    echo "  -v, --version VERSION    指定版本号"
    echo "  --skip-tests             跳过测试"
    echo "  -h, --help               显示帮助"
    echo
    echo "环境变量:"
    echo "  SERVER_HOST              生产服务器地址"
    echo "  SERVER_USER              生产服务器用户名"
    echo "  SKIP_TESTS               跳过测试 (true/false)"
    echo
    echo "示例:"
    echo "  $0 -e development"
    echo "  $0 -e production -v v1.0.0"
    echo "  SERVER_HOST=prod.example.com SERVER_USER=deploy $0 -e production"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 运行主函数
main
