#!/bin/bash
# ============================================================================
# Git 历史清理脚本 - 移除敏感文件
# Git History Cleanup Script - Remove Sensitive Files
# ============================================================================
#
# ⚠️  警告：这是一个破坏性操作！
# WARNING: This is a DESTRUCTIVE operation!
#
# 此脚本将从整个Git历史中永久删除 .env.production 文件
# This script will permanently remove .env.production from entire Git history
#
# 影响：
# - 所有提交的SHA会改变
# - 所有协作者需要重新克隆仓库
# - 不可逆转
#
# ============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 需要清理的文件
SENSITIVE_FILE=".env.production"

echo -e "${RED}============================================================================${NC}"
echo -e "${RED}           ⚠️  Git 历史清理脚本 - 破坏性操作警告 ⚠️${NC}"
echo -e "${RED}============================================================================${NC}"
echo ""
echo -e "${YELLOW}此操作将：${NC}"
echo "  1. 从Git历史中永久删除 ${SENSITIVE_FILE}"
echo "  2. 重写所有提交历史（SHA会改变）"
echo "  3. 需要所有协作者重新克隆仓库"
echo "  4. 无法撤销"
echo ""
echo -e "${YELLOW}建议在执行前：${NC}"
echo "  1. 确保有完整的备份"
echo "  2. 通知所有协作者"
echo "  3. 在测试分支上先试运行"
echo ""

# 检查是否在Git仓库中
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ 错误：当前目录不是Git仓库${NC}"
    exit 1
fi

# 检查是否有未提交的更改
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}❌ 错误：存在未提交的更改，请先提交或暂存${NC}"
    exit 1
fi

# 确认操作
echo -e "${YELLOW}是否继续执行清理？(yes/no):${NC} "
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${BLUE}操作已取消${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}🔍 检查文件是否存在于Git历史中...${NC}"
if git log --all --full-history --oneline -- "$SENSITIVE_FILE" | head -5; then
    echo -e "${YELLOW}✓ 找到 ${SENSITIVE_FILE} 的历史记录${NC}"
else
    echo -e "${GREEN}✓ 文件不在Git历史中，无需清理${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}📦 创建备份...${NC}"
BACKUP_DIR="git_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
git bundle create "$BACKUP_DIR/repo_backup.bundle" --all
echo -e "${GREEN}✓ 备份已创建：${BACKUP_DIR}/repo_backup.bundle${NC}"

echo ""
echo -e "${YELLOW}⚠️  最后确认：即将开始清理Git历史，输入仓库名称以确认：${NC}"
REPO_NAME=$(basename $(git rev-parse --show-toplevel))
echo -e "当前仓库名称: ${BLUE}${REPO_NAME}${NC}"
echo -n "请输入仓库名称以确认: "
read -r CONFIRM_REPO

if [ "$CONFIRM_REPO" != "$REPO_NAME" ]; then
    echo -e "${RED}❌ 仓库名称不匹配，操作已取消${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}🚀 开始清理Git历史...${NC}"
echo ""

# 方法1: 使用 git filter-branch (经典方法)
echo -e "${YELLOW}使用 git filter-branch 清理历史...${NC}"
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch $SENSITIVE_FILE" \
  --prune-empty --tag-name-filter cat -- --all

echo ""
echo -e "${BLUE}🧹 清理引用和垃圾...${NC}"
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo -e "${GREEN}✅ Git历史清理完成！${NC}"
echo ""
echo -e "${YELLOW}📋 后续步骤：${NC}"
echo "  1. 检查仓库状态: git log --all -- $SENSITIVE_FILE"
echo "  2. 测试仓库功能是否正常"
echo "  3. 如果确认无误，执行强制推送:"
echo -e "     ${RED}git push origin --force --all${NC}"
echo -e "     ${RED}git push origin --force --tags${NC}"
echo "  4. 通知所有协作者重新克隆仓库"
echo "  5. 备份文件位于: $BACKUP_DIR"
echo ""
echo -e "${RED}⚠️  注意：推送后旧的Git历史将无法恢复！${NC}"
