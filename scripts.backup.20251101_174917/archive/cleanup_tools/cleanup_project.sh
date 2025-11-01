#!/bin/bash

# 项目清理脚本
# 用于定期清理临时文件和组织项目结构

set -e

GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
NC='\033[0m'

echo -e "${YELLOW}🧹 开始清理项目...${NC}"

# 1. 清理临时报告
echo -e "${YELLOW}清理临时报告...${NC}"
rm -f bandit*.json 2>/dev/null || true
rm -f coverage*.json 2>/dev/null || true
rm -f coverage_analysis*.json 2>/dev/null || true
rm -f ruff*.json 2>/dev/null || true

# 2. 移动报告到归档
echo -e "${YELLOW}归档报告文件...${NC}"
REPORTS_DIR="docs/_reports/archive/$(date +%Y-%m)"
mkdir -p "$REPORTS_DIR"

# 移动报告文件
find . -maxdepth 1 -name "*REPORT*.md" -not -path "./docs/*" -exec mv {} "$REPORTS_DIR/" \; 2>/dev/null || true
find . -maxdepth 1 -name "*REPORT*.txt" -not -path "./docs/*" -exec mv {} "$REPORTS_DIR/" \; 2>/dev/null || true

# 3. 清理Python缓存
echo -e "${YELLOW}清理Python缓存...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# 4. 清理测试临时文件
echo -e "${YELLOW}清理测试临时文件...${NC}"
rm -f .coverage 2>/dev/null || true
rm -rf htmlcov/ 2>/dev/null || true
rm -rf .pytest_cache/ 2>/dev/null || true
rm -rf .mypy_cache/ 2>/dev/null || true

# 5. 整理根目录文件
echo -e "${YELLOW}检查根目录文件...${NC}"

# 移动临时文档到合适位置
mkdir -p docs/temp
find . -maxdepth 1 -name "TEMP_*.md" -exec mv {} docs/temp/ \; 2>/dev/null || true

# 6. 显示清理结果
echo -e "${GREEN}✅ 清理完成！${NC}"
echo -e "${YELLOW}当前根目录文件数：$(ls -la | grep -E '^-[^.]' | wc -l)${NC}"

# 7. 提示下一步
echo -e "\n${YELLOW}建议：${NC}"
echo "1. 运行 'make test' 验证系统"
echo "2. 运行 'make fmt && make lint' 格式化代码"
echo "3. 提交更改前运行 'make prepush'"

echo -e "\n${GREEN}🎉 项目清理完成！${NC}"
