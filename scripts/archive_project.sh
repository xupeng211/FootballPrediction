#!/bin/bash
#
# 足球预测系统项目归档脚本
#
# 功能:
# 1. 检查所有核心文件是否存在
# 2. 创建包含源代码、文档、测试和模型的归档包
# 3. 自动生成带版本和日期的归档文件名
#
# 使用方法: ./scripts/archive_project.sh
#

set -e  # 遇到错误立即退出

# 配置变量
PROJECT_NAME="football_prediction"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATEstamp=$(date +%Y%m%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 获取Git信息
if git rev-parse --git-dir > /dev/null 2>&1; then
    GIT_HASH=$(git rev-parse --short HEAD)
    GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    GIT_COMMIT_DATE=$(git log -1 --format=%cd --date=short)
else
    GIT_HASH="nogit"
    GIT_BRANCH="unknown"
    GIT_COMMIT_DATE="unknown"
fi

# 版本信息
VERSION="1.0.0"
ARCHIVE_NAME="${PROJECT_NAME}_v${VERSION}_${DATEstamp}_${GIT_HASH}"
ARCHIVE_FILE="${ARCHIVE_NAME}.tar.gz"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "命令 '$1' 未找到，请安装后重试"
        exit 1
    fi
}

# 检查文件或目录是否存在
check_file() {
    if [[ ! -e "$1" ]]; then
        log_error "文件或目录不存在: $1"
        return 1
    fi
    return 0
}

# 创建项目信息文件
create_project_info() {
    local info_file="${PROJECT_ROOT}/PROJECT_INFO.txt"

    log_info "创建项目信息文件..."

    cat > "$info_file" << EOF
==================================================
足球预测系统 - 项目归档信息
==================================================

归档时间: $(date '+%Y-%m-%d %H:%M:%S')
归档版本: $VERSION
Git Hash: $GIT_HASH
Git 分支: $GIT_BRANCH
提交日期: $GIT_COMMIT_DATE

项目结构:
- src/: 源代码目录
- tests/: 测试用例目录
- docs/: 项目文档目录
- models/: 训练好的模型文件
- scripts/: 工具脚本目录
- config/: 配置文件目录
- docker-compose.*: Docker编排文件
- Dockerfile: 容器化文件
- pytest.ini: 测试配置
- requirements.txt: Python依赖
- CLAUDE.md: 项目指导文档

核心功能:
1. 足球比赛1X2结果预测
2. 实时特征工程
3. XGBoost机器学习模型
4. REST API服务
5. SHAP可解释性分析
6. MLOps模型热重载
7. 完整的CI/CD流水线

技术栈:
- FastAPI (Web框架)
- XGBoost (机器学习)
- PostgreSQL (数据库)
- Redis (缓存)
- Docker (容器化)
- GitHub Actions (CI/CD)
- SHAP (模型可解释性)

快速开始:
1. 解压归档文件
2. 安装依赖: pip install -r requirements.txt
3. 启动服务: make dev 或 docker-compose up
4. 访问API: http://localhost:8000/docs

测试:
- 运行所有测试: make test
- 运行覆盖率测试: make coverage
- 查看测试报告: open htmlcov/index.html

部署:
- 开发环境: make dev
- 生产环境: docker-compose -f docker-compose.prod.yml up
- 查看服务状态: make status

维护:
- 代码格式化: make format
- 代码检查: make lint
- 类型检查: make typecheck
- 安全扫描: make security

==================================================
生成时间: $(date)
归档脚本: scripts/archive_project.sh
==================================================
EOF

    log_success "项目信息文件创建完成: $info_file"
}

# 检查核心文件
check_core_files() {
    log_info "检查核心文件..."

    local missing_files=()
    local core_files=(
        "src"
        "tests"
        "docs"
        "requirements.txt"
        "Dockerfile"
        "docker-compose.yml"
        "CLAUDE.md"
        "pytest.ini"
        "README.md"
    )

    for file in "${core_files[@]}"; do
        if ! check_file "${PROJECT_ROOT}/$file"; then
            missing_files+=("$file")
        fi
    done

    if [[ ${#missing_files[@]} -gt 0 ]]; then
        log_error "以下核心文件缺失:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        return 1
    fi

    log_success "所有核心文件检查通过"
}

# 检查重要目录
check_directories() {
    log_info "检查重要目录结构..."

    local dirs=(
        "src/api"
        "src/services"
        "src/ml"
        "src/database"
        "src/core"
        "tests/unit"
        "tests/integration"
        "docs"
        "scripts"
        "config"
    )

    local missing_dirs=()

    for dir in "${dirs[@]}"; do
        if [[ ! -d "${PROJECT_ROOT}/$dir" ]]; then
            missing_dirs+=("$dir")
        fi
    done

    if [[ ${#missing_dirs[@]} -gt 0 ]]; then
        log_warning "以下目录缺失（可能是可选的）:"
        for dir in "${missing_dirs[@]}"; do
            echo "  - $dir"
        done
    else
        log_success "所有目录结构检查通过"
    fi
}

# 检查测试覆盖
check_tests() {
    log_info "检查测试覆盖率..."

    if [[ -f "${PROJECT_ROOT}/.coverage" ]]; then
        log_success "发现测试覆盖率文件"
    else
        log_warning "未发现测试覆盖率文件，建议运行 'make coverage'"
    fi

    # 统计测试文件数量
    local test_count=$(find "${PROJECT_ROOT}/tests" -name "test_*.py" | wc -l)
    log_info "发现 $test_count 个测试文件"
}

# 检查模型文件
check_models() {
    log_info "检查模型文件..."

    local model_count=$(find "${PROJECT_ROOT}/models" -name "*.pkl" 2>/dev/null | wc -l)
    if [[ $model_count -gt 0 ]]; then
        log_success "发现 $model_count 个模型文件"
    else
        log_warning "未发现模型文件，这是正常的（模型文件通常在训练后生成）"
    fi
}

# 创建归档
create_archive() {
    log_info "开始创建归档文件..."

    # 切换到项目根目录
    cd "$PROJECT_ROOT"

    # 创建临时目录用于归档
    local temp_dir="/tmp/${ARCHIVE_NAME}"
    mkdir -p "$temp_dir"

    log_info "复制项目文件到临时目录..."

    # 复制核心目录和文件
    cp -r src "$temp_dir/"
    cp -r tests "$temp_dir/"
    cp -r docs "$temp_dir/"
    cp -r scripts "$temp_dir/"
    cp -r config "$temp_dir/"

    # 复制重要文件（如果存在）
    [[ -d "models" ]] && cp -r models "$temp_dir/"
    [[ -d "microservices" ]] && cp -r microservices "$temp_dir/"
    [[ -d "monitoring" ]] && cp -r monitoring "$temp_dir/"

    # 复制配置文件
    cp requirements.txt "$temp_dir/"
    cp Dockerfile* "$temp_dir/" 2>/dev/null || true
    cp docker-compose*.yml "$temp_dir/"
    cp pytest.ini "$temp_dir/"
    cp CLAUDE.md "$temp_dir/"
    cp README.md "$temp_dir/"
    cp Makefile "$temp_dir/" 2>/dev/null || true

    # 复制项目信息文件
    cp PROJECT_INFO.txt "$temp_dir/"

    # 创建版本信息文件
    cat > "$temp_dir/VERSION.txt" << EOF
Version: $VERSION
Git Hash: $GIT_HASH
Build Date: $(date '+%Y-%m-%d %H:%M:%S')
Branch: $GIT_BRANCH
EOF

    log_info "创建压缩归档..."

    # 创建tar.gz归档
    tar -czf "${ARCHIVE_FILE}" -C "/tmp" "$ARCHIVE_NAME"

    # 清理临时目录
    rm -rf "$temp_dir"

    log_success "归档文件创建完成: ${ARCHIVE_FILE}"
}

# 验证归档
verify_archive() {
    log_info "验证归档文件..."

    if [[ -f "${PROJECT_ROOT}/${ARCHIVE_FILE}" ]]; then
        local file_size=$(du -h "${PROJECT_ROOT}/${ARCHIVE_FILE}" | cut -f1)
        log_success "归档文件验证通过"
        log_info "文件大小: $file_size"
        log_info "文件位置: ${PROJECT_ROOT}/${ARCHIVE_FILE}"

        # 显示归档内容（前20行）
        log_info "归档内容预览:"
        tar -tzf "${PROJECT_ROOT}/${ARCHIVE_FILE}" | head -20

        # 显示归档统计
        local total_files=$(tar -tzf "${PROJECT_ROOT}/${ARCHIVE_FILE}" | wc -l)
        log_info "归档文件总数: $total_files"
    else
        log_error "归档文件验证失败"
        return 1
    fi
}

# 生成归档报告
generate_report() {
    local report_file="${PROJECT_ROOT}/ARCHIVE_REPORT_${TIMESTAMP}.txt"

    log_info "生成归档报告..."

    cat > "$report_file" << EOF
==================================================
足球预测系统 - 项目归档报告
==================================================

归档完成时间: $(date '+%Y-%m-%d %H:%M:%S')
项目版本: $VERSION
Git Hash: $GIT_HASH
Git 分支: $GIT_BRANCH
归档文件: $ARCHIVE_FILE

归档内容:
- 源代码 (src/)
- 测试用例 (tests/)
- 项目文档 (docs/)
- 脚本工具 (scripts/)
- 配置文件 (config/)
- 依赖文件 (requirements.txt, Dockerfile等)
- 项目信息 (PROJECT_INFO.txt, VERSION.txt)

文件统计:
$(tar -tzf "${PROJECT_ROOT}/${ARCHIVE_FILE}" | wc -l | awk '{print "  总文件数: " $1}')

目录结构:
$(tar -tzf "${PROJECT_ROOT}/${ARCHIVE_FILE}" | sed 's/[^\/]*\//│── /' | head -30)

注意事项:
1. 解压后请检查 models/ 目录是否存在模型文件
2. 运行前请确保安装了所有依赖: pip install -r requirements.txt
3. 建议在虚拟环境中运行项目
4. 生产环境部署请使用 docker-compose.prod.yml

快速启动:
1. tar -xzf $ARCHIVE_FILE
2. cd $ARCHIVE_NAME
3. pip install -r requirements.txt
4. python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

验证命令:
- 运行测试: python -m pytest tests/
- 检查代码质量: make quality
- 启动开发环境: make dev

==================================================
报告生成时间: $(date)
归档脚本: scripts/archive_project.sh
==================================================
EOF

    log_success "归档报告生成完成: $report_file"
}

# 主函数
main() {
    log_info "开始足球预测系统项目归档..."
    log_info "项目路径: $PROJECT_ROOT"

    # 检查必要命令
    check_command "tar"
    check_command "git"

    # 执行归档步骤
    create_project_info
    check_core_files || exit 1
    check_directories
    check_tests
    check_models
    create_archive || exit 1
    verify_archive || exit 1
    generate_report

    echo
    echo "=================================================="
    log_success "项目归档完成！"
    echo "=================================================="
    echo "归档文件: $ARCHIVE_FILE"
    echo "项目大小: $(du -h "${PROJECT_ROOT}/${ARCHIVE_FILE}" | cut -f1)"
    echo "Git 信息: $GIT_HASH ($GIT_BRANCH)"
    echo
    echo "下一步:"
    echo "1. 分发归档文件: $ARCHIVE_FILE"
    echo "2. 查看归档报告: ARCHIVE_REPORT_${TIMESTAMP}.txt"
    echo "3. 解压并验证: tar -xzf $ARCHIVE_FILE"
    echo
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi