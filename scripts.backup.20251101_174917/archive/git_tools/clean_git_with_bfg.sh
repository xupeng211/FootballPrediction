#!/bin/bash
# ============================================================================
# 使用 BFG Repo-Cleaner 清理 Git 历史
# Clean Git History with BFG Repo-Cleaner
# ============================================================================
#
# BFG 是比 git filter-branch 更快的替代方案
# BFG is a faster alternative to git filter-branch
#
# 安装方法:
# 1. 下载: https://rtyley.github.io/bfg-repo-cleaner/
# 2. 或使用包管理器:
#    - macOS: brew install bfg
#    - Linux: 下载 bfg.jar
#
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}         使用 BFG Repo-Cleaner 清理 Git 历史${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# 检查BFG是否可用
if ! command -v bfg &> /dev/null; then
    if [ ! -f "bfg.jar" ]; then
        echo -e "${RED}❌ BFG Repo-Cleaner 未安装${NC}"
        echo ""
        echo "安装方法："
        echo "  1. 下载: wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar"
        echo "     重命名: mv bfg-1.14.0.jar bfg.jar"
        echo "  2. 或访问: https://rtyley.github.io/bfg-repo-cleaner/"
        echo ""
        exit 1
    else
        BFG_CMD="java -jar bfg.jar"
    fi
else
    BFG_CMD="bfg"
fi

# 创建备份
echo -e "${BLUE}📦 创建备份...${NC}"
BACKUP_DIR="git_backup_bfg_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
git bundle create "$BACKUP_DIR/repo_backup.bundle" --all
echo -e "${GREEN}✓ 备份已创建${NC}"
echo ""

# 确认操作
echo -e "${YELLOW}⚠️  此操作将删除 .env.production 的所有历史记录${NC}"
echo -n "继续? (yes/no): "
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${BLUE}操作已取消${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}🚀 运行 BFG Repo-Cleaner...${NC}"
$BFG_CMD --delete-files .env.production

echo ""
echo -e "${BLUE}🧹 清理和压缩仓库...${NC}"
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo -e "${GREEN}✅ 清理完成！${NC}"
echo ""
echo -e "${YELLOW}后续步骤：${NC}"
echo "  1. 检查结果: git log --all -- .env.production"
echo "  2. 强制推送: git push origin --force --all"
echo "  3. 强制推送标签: git push origin --force --tags"
echo ""
echo -e "${RED}⚠️  推送后所有协作者需要重新克隆仓库！${NC}"
