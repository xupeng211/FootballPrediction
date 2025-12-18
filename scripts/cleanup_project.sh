#!/bin/bash
# ==================== Football Prediction Project Cleanup Script ====================
# 🔧 项目清理脚本 - 清理所有临时文件、缓存和备份
# 用途: Git推送前的"大扫除"，确保代码库纯净
# 作者: Senior DevOps Engineer
# 版本: 1.0.0
# 日期: 2024-12-18

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  INFO: $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ SUCCESS: $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
}

log_error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
}

log_clean() {
    echo -e "${PURPLE}🧹 CLEAN: $1${NC}"
}

log_file() {
    echo -e "${CYAN}📁 FILE: $1${NC}"
}

# 计数器
TOTAL_FILES_REMOVED=0
TOTAL_DIRS_REMOVED=0
TOTAL_SIZE_FREED=0

# 检查当前目录
PROJECT_DIR="/home/user/projects/FootballPrediction"
if [[ ! -d "$PROJECT_DIR" ]]; then
    log_error "项目目录不存在: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"
log_info "开始清理项目目录: $(pwd)"

# 显示清理横幅
echo -e "${BLUE}"
echo "=========================================="
echo "🧹 Football Prediction 项目清理工具"
echo "=========================================="
echo "📋 清理范围:"
echo "   • Python缓存文件 (__pycache__, *.pyc)"
echo "   • IDE配置文件 (.vscode, .idea, *.swp)"
echo "   • 系统临时文件 (.DS_Store, Thumbs.db)"
echo "   • 构建产物 (build/, dist/, *.egg-info)"
echo "   • 测试缓存 (.pytest_cache, .coverage)"
echo "   • 日志文件 (*.log, logs/)"
echo "   • 备份文件 (*.bak, *.backup, *.old)"
echo "   • Docker临时文件"
echo "   • 文档构建产物"
echo "=========================================="
echo -e "${NC}"

# 安全确认
echo -e "${YELLOW}⚠️  清理操作将删除以下类型的文件:"
echo "   - 所有Python缓存和临时文件"
echo "   - IDE配置和编辑器临时文件"
echo "   - 系统生成的临时文件"
echo "   - 构建和测试产物"
echo "   - 日志和备份文件"
echo ""
echo -e "${RED}注意: 这个操作不可逆！请确认没有重要的未保存工作。${NC}"
echo ""

read -p "是否继续执行清理? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "清理操作已取消"
    exit 0
fi

# 开始清理
log_info "开始执行项目清理..."

# 1. 清理Python缓存文件
log_clean "清理Python缓存文件..."

# __pycache__ 目录
if find . -name "__pycache__" -type d | grep -q .; then
    log_file "找到 __pycache__ 目录"
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    count=$(find . -name "__pycache__" -type d 2>/dev/null | wc -l)
    if [ "$count" -eq 0 ]; then
        log_success "已清理所有 __pycache__ 目录"
    fi
fi

# *.pyc 文件
if find . -name "*.pyc" | grep -q .; then
    pyc_files=$(find . -name "*.pyc" -type f)
    pyc_count=$(echo "$pyc_files" | wc -l)
    if [ "$pyc_count" -gt 0 ]; then
        log_file "找到 $pyc_count 个 .pyc 文件"
        find . -name "*.pyc" -type f -delete
        TOTAL_FILES_REMOVED=$((TOTAL_FILES_REMOVED + pyc_count))
        log_success "已删除所有 .pyc 文件"
    fi
fi

# *.pyo 文件 (优化编译文件)
if find . -name "*.pyo" | grep -q .; then
    pyo_files=$(find . -name "*.pyo" -type f)
    pyo_count=$(echo "$pyo_files" | wc -l)
    if [ "$pyo_count" -gt 0 ]; then
        log_file "找到 $pyo_count 个 .pyo 文件"
        find . -name "*.pyo" -type f -delete
        TOTAL_FILES_REMOVED=$((TOTAL_FILES_REMOVED + pyo_count))
        log_success "已删除所有 .pyo 文件"
    fi
fi

# 2. 清理IDE和编辑器文件
log_clean "清理IDE和编辑器配置文件..."

# .vscode 目录
if [ -d ".vscode" ]; then
    log_file "找到 .vscode 目录"
    rm -rf .vscode
    TOTAL_DIRS_REMOVED=$((TOTAL_DIRS_REMOVED + 1))
    log_success "已删除 .vscode 目录"
fi

# .idea 目录
if find . -name ".idea" -type d | grep -q .; then
    log_file "找到 .idea 目录"
    find . -name ".idea" -type d -exec rm -rf {} + 2>/dev/null || true
    log_success "已删除 .idea 目录"
fi

# Vim临时文件
if find . -name "*.swp" -o -name "*.swo" -o -name "*~" | grep -q .; then
    log_file "找到 Vim 临时文件"
    find . \( -name "*.swp" -o -name "*.swo" -o -name "*~" \) -type f -delete
    log_success "已删除 Vim 临时文件"
fi

# 3. 清理系统临时文件
log_clean "清理系统临时文件..."

# .DS_Store (macOS)
if find . -name ".DS_Store" | grep -q .; then
    log_file "找到 .DS_Store 文件"
    find . -name ".DS_Store" -type f -delete
    log_success "已删除 .DS_Store 文件"
fi

# ._* (macOS资源文件)
if find . -name "._*" | grep -q .; then
    log_file "找到 ._*
[truncated by the tool]