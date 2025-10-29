#!/bin/bash

# =================================================================
# 足球预测系统 - 生产环境镜像构建脚本
# =================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

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

# 检查是否安装了必要的工具
check_prerequisites() {
    log_step "检查构建依赖..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi

    # 检查 Docker 是否运行
    if ! docker info &> /dev/null; then
        log_error "Docker 服务未运行"
        exit 1
    fi

    # 检查 Git
    if ! command -v git &> /dev/null; then
        log_error "Git 未安装"
        exit 1
    fi

    log_success "构建依赖检查通过"
}

# 获取构建信息
get_build_info() {
    log_step "获取构建信息..."

    # 获取 Git 信息
    export GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    export GIT_URL=$(git config --get remote.origin.url 2>/dev/null || echo "https://github.com/xupeng211/FootballPrediction")

    # 获取时间戳
    export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # 获取版本信息
    export APP_VERSION=$(cat pyproject.toml | grep version | head -1 | cut -d'"' -f2 2>/dev/null || echo "1.0.0")

    # 生成镜像标签
    export IMAGE_TAG="${APP_VERSION}-${GIT_COMMIT:0:8}"
    export IMAGE_NAME="football-prediction"
    export FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
    export LATEST_IMAGE_NAME="${IMAGE_NAME}:latest"
    export PRODUCTION_IMAGE_NAME="${IMAGE_NAME}:production"

    log_info "构建信息:"
    echo "  - 应用版本: ${APP_VERSION}"
    echo "  - Git 提交: ${GIT_COMMIT}"
    echo "  - Git 分支: ${GIT_BRANCH}"
    echo "  - 构建时间: ${BUILD_DATE}"
    echo "  - 镜像标签: ${IMAGE_TAG}"
    echo "  - 镜像名称: ${FULL_IMAGE_NAME}"
}

# 清理旧的构建缓存
cleanup_build_cache() {
    log_step "清理构建缓存..."

    # 清理 Docker 构建缓存
    docker builder prune -f --filter "until=24h" || true

    # 清理悬空镜像
    docker image prune -f --filter "dangling=true" || true

    log_success "构建缓存清理完成"
}

# 构建生产镜像
build_production_image() {
    log_step "构建生产环境镜像..."

    # 构建参数
    local build_args=(
        "--build-arg" "APP_VERSION=${APP_VERSION}"
        "--build-arg" "BUILD_DATE=${BUILD_DATE}"
        "--build-arg" "GIT_COMMIT=${GIT_COMMIT}"
        "--build-arg" "GIT_BRANCH=${GIT_BRANCH}"
        "--build-arg" "VCS_URL=${GIT_URL}"
        "--tag" "${FULL_IMAGE_NAME}"
        "--tag" "${LATEST_IMAGE_NAME}"
        "--tag" "${PRODUCTION_IMAGE_NAME}"
        "--file" "Dockerfile.prod"
        "--progress" "plain"
        "."
    )

    log_info "执行构建命令: docker build ${build_args[*]}"

    # 开始构建
    if docker build "${build_args[@]}"; then
        log_success "生产镜像构建完成"
    else
        log_error "生产镜像构建失败"
        exit 1
    fi
}

# 验证镜像
validate_image() {
    log_step "验证构建的镜像..."

    # 检查镜像是否存在
    if ! docker image inspect "${FULL_IMAGE_NAME}" &> /dev/null; then
        log_error "镜像不存在: ${FULL_IMAGE_NAME}"
        exit 1
    fi

    # 获取镜像信息
    local image_size=$(docker image inspect "${FULL_IMAGE_NAME}" --format='{{.Size}}' | awk '{print $1/1024/1024 " MB"}')
    local image_id=$(docker image inspect "${FULL_IMAGE_NAME}" --format='{{.Id}}')

    log_info "镜像验证结果:"
    echo "  - 镜像 ID: ${image_id}"
    echo "  - 镜像大小: ${image_size}"
    echo "  - 创建时间: $(docker image inspect "${FULL_IMAGE_NAME}" --format='{{.Created}}')"

    # 运行基础功能测试
    log_info "运行镜像功能测试..."

    # 创建临时容器测试
    local container_id=$(docker run --rm -d "${FULL_IMAGE_NAME}" --help)

    if [ $? -eq 0 ]; then
        docker stop "${container_id}" 2>/dev/null || true
        log_success "镜像功能测试通过"
    else
        log_error "镜像功能测试失败"
        exit 1
    fi
}

# 安全扫描
security_scan() {
    log_step "执行安全扫描..."

    # 检查是否安装了 Trivy
    if command -v trivy &> /dev/null; then
        log_info "运行 Trivy 漏洞扫描..."

        # 创建扫描报告目录
        mkdir -p reports/security

        # 扫描镜像
        if trivy image --format json --output "reports/security/trivy-$(date +%Y%m%d-%H%M%S).json" "${FULL_IMAGE_NAME}"; then
            log_success "Trivy 扫描完成"
        else
            log_warning "Trivy 扫描失败，但构建继续"
        fi

        # 显示扫描结果摘要
        log_info "扫描结果摘要:"
        trivy image --quiet "${FULL_IMAGE_NAME}" || true
    else
        log_warning "Trivy 未安装，跳过安全扫描"
        log_info "安装 Trivy: https://github.com/aquasecurity/trivy"
    fi
}

# 运行容器测试
test_container() {
    log_step "运行容器测试..."

    # 创建测试网络
    local network_name="football-prediction-test"
    docker network create "${network_name}" 2>/dev/null || true

    # 启动基础服务 (PostgreSQL 和 Redis)
    log_info "启动测试服务..."

    # 启动测试数据库
    local postgres_container=$(docker run -d \
        --network "${network_name}" \
        -e POSTGRES_DB=test_football_prediction \
        -e POSTGRES_USER=test_user \
        -e POSTGRES_PASSWORD=test_password \
        --name test-postgres \
        postgres:15-alpine)

    # 启动测试 Redis
    local redis_container=$(docker run -d \
        --network "${network_name}" \
        --name test-redis \
        redis:7-alpine)

    # 等待服务启动
    sleep 10

    # 启动应用容器
    local app_container=$(docker run -d \
        --network "${network_name}" \
        -e DATABASE_URL=postgresql://test_user:test_password@test-postgres:5432/test_football_prediction \
        -e REDIS_URL=redis://test-redis:6379/0 \
        -e DEBUG=false \
        -e LOG_LEVEL=INFO \
        --name test-app \
        -p 8000:8000 \
        "${FULL_IMAGE_NAME}")

    # 等待应用启动
    log_info "等待应用启动..."
    sleep 30

    # 健康检查
    local health_check_passed=false
    for i in {1..10}; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            health_check_passed=true
            break
        fi
        log_info "健康检查尝试 $i/10..."
        sleep 5
    done

    if [ "$health_check_passed" = true ]; then
        log_success "容器健康检查通过"
    else
        log_error "容器健康检查失败"
    fi

    # 清理测试容器和网络
    log_info "清理测试资源..."
    docker stop test-app test-postgres test-redis 2>/dev/null || true
    docker rm test-app test-postgres test-redis 2>/dev/null || true
    docker network rm "${network_name}" 2>/dev/null || true

    log_success "容器测试完成"
}

# 推送镜像到仓库 (可选)
push_to_registry() {
    if [ "$PUSH_TO_REGISTRY" = "true" ]; then
        log_step "推送镜像到仓库..."

        # 检查是否登录
        if ! docker info | grep -q "Username"; then
            log_error "未登录到 Docker 镜像仓库"
            log_info "请先运行: docker login"
            exit 1
        fi

        # 推送镜像
        local registry="${REGISTRY_URL:-docker.io/$(docker info | grep Username | awk '{print $2}')}"
        local registry_image="${registry}/${IMAGE_NAME}"

        # 标记镜像
        docker tag "${FULL_IMAGE_NAME}" "${registry_image}:${IMAGE_TAG}"
        docker tag "${FULL_IMAGE_NAME}" "${registry_image}:latest"
        docker tag "${FULL_IMAGE_NAME}" "${registry_image}:production"

        # 推送镜像
        docker push "${registry_image}:${IMAGE_TAG}"
        docker push "${registry_image}:latest"
        docker push "${registry_image}:production"

        log_success "镜像推送完成: ${registry_image}"
    fi
}

# 生成构建报告
generate_build_report() {
    log_step "生成构建报告..."

    # 创建报告目录
    mkdir -p reports/build

    # 生成报告文件
    local report_file="reports/build/build-$(date +%Y%m%d-%H%M%S).json"

    cat > "${report_file}" << EOF
{
    "build_info": {
        "app_version": "${APP_VERSION}",
        "git_commit": "${GIT_COMMIT}",
        "git_branch": "${GIT_BRANCH}",
        "build_date": "${BUILD_DATE}",
        "image_name": "${FULL_IMAGE_NAME}",
        "image_tag": "${IMAGE_TAG}",
        "build_status": "success"
    },
    "image_details": {
        "image_id": "$(docker image inspect "${FULL_IMAGE_NAME}" --format='{{.Id}}')",
        "size": "$(docker image inspect "${FULL_IMAGE_NAME}" --format='{{.Size}}')",
        "created": "$(docker image inspect "${FULL_IMAGE_NAME}" --format='{{.Created}}')"
    },
    "build_timestamp": "$(date -Iseconds)",
    "build_environment": {
        "docker_version": "$(docker --version)",
        "git_version": "$(git --version)",
        "host_os": "$(uname -s)",
        "host_arch": "$(uname -m)"
    }
}
EOF

    log_success "构建报告生成: ${report_file}"
}

# 显示帮助信息
show_help() {
    echo "足球预测系统 - 生产环境镜像构建脚本"
    echo
    echo "使用方法:"
    echo "  $0 [选项]"
    echo
    echo "选项:"
    echo "  -h, --help              显示帮助信息"
    echo "  -c, --cleanup           清理构建缓存"
    echo "  -s, --skip-tests        跳过容器测试"
    echo "  -p, --push              推送到镜像仓库"
    echo "  --registry URL          指定镜像仓库地址"
    echo "  --no-security-scan      跳过安全扫描"
    echo
    echo "环境变量:"
    echo "  PUSH_TO_REGISTRY        设置为 'true' 启用镜像推送"
    echo "  REGISTRY_URL            镜像仓库地址"
    echo
    echo "示例:"
    echo "  $0                      # 基本构建"
    echo "  $0 -c -p               # 清理缓存并推送镜像"
    echo "  $0 --registry my-registry.com --push  # 推送到指定仓库"
}

# 主函数
main() {
    local skip_tests=false
    local no_security_scan=false

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -c|--cleanup)
                cleanup_build_cache
                shift
                ;;
            -s|--skip-tests)
                skip_tests=true
                shift
                ;;
            -p|--push)
                export PUSH_TO_REGISTRY=true
                shift
                ;;
            --registry)
                export REGISTRY_URL="$2"
                shift 2
                ;;
            --no-security-scan)
                no_security_scan=true
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    log_info "开始生产环境镜像构建..."
    echo "=================================="

    # 执行构建流程
    check_prerequisites
    get_build_info
    cleanup_build_cache
    build_production_image
    validate_image

    if [ "$no_security_scan" = false ]; then
        security_scan
    fi

    if [ "$skip_tests" = false ]; then
        test_container
    fi

    push_to_registry
    generate_build_report

    echo "=================================="
    log_success "生产环境镜像构建完成!"
    echo
    echo "镜像信息:"
    echo "  - 主要标签: ${FULL_IMAGE_NAME}"
    echo "  - 最新标签: ${LATEST_IMAGE_NAME}"
    echo "  - 生产标签: ${PRODUCTION_IMAGE_NAME}"
    echo
    echo "使用命令:"
    echo "  docker run -p 8000:8000 ${FULL_IMAGE_NAME}"
    echo "  docker-compose -f docker-compose.prod.yml up -d"
    echo
    if [ "$skip_tests" = true ]; then
        log_warning "跳过了容器测试，建议在部署前进行完整测试"
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi