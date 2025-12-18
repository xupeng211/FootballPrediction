#!/bin/bash
# 快速清理脚本 - Git推送前使用
set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧹 Football Prediction 快速清理工具${NC}"
echo "=================================="

# 进入项目目录
cd /home/user/projects/FootballPrediction

# 1. 清理Python缓存
echo -e "${YELLOW}清理Python缓存...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true
echo -e "${GREEN}✅ Python缓存清理完成${NC}"

# 2. 清理IDE文件
echo -e "${YELLOW}清理IDE配置文件...${NC}"
rm -rf .vscode .idea 2>/dev/null || true
find . -name "*.swp" -delete 2>/dev/null || true
find . -name "*.swo" -delete 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true
echo -e "${GREEN}✅ IDE文件清理完成${NC}"

# 3. 清理构建产物
echo -e "${YELLOW}清理构建产物...${NC}"
rm -rf build/ dist/ *.egg-info 2>/dev/null || true
rm -rf .pytest_cache .coverage htmlcov/ 2>/dev/null || true
rm -rf .mypy_cache .pytest_cache 2>/dev/null || true
echo -e "${GREEN}✅ 构建产物清理完成${NC}"

# 4. 清理日志和临时文件
echo -e "${YELLOW}清理日志和临时文件...${NC}"
find . -name "*.log" -delete 2>/dev/null || true
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.bak" -delete 2>/dev/null || true
find . -name ".coverage.*" -delete 2>/dev/null || true
echo -e "${GREEN}✅ 临时文件清理完成${NC}"

# 5. 清理文档构建产物
echo -e "${YELLOW}清理文档构建产物...${NC}"
rm -rf docs/_build/ 2>/dev/null || true
rm -rf site/ 2>/dev/null || true
echo -e "${GREEN}✅ 文档构建产物清理完成${NC}"

# 6. 清理测试特定文件
echo -e "${YELLOW}清理测试相关文件...${NC}"
rm -f test_financial_precision.py test_network_robustness.py test_network_simple.py 2>/dev/null || true
rm -f test_transaction_protection.py 2>/dev/null || true
echo -e "${GREEN}✅ 测试文件清理完成${NC}"

# 7. 显示清理后状态
echo ""
echo -e "${BLUE}清理完成！项目状态：${NC}"
echo "=================================="

# 显示剩余的重要文件
echo -e "${YELLOW}重要文件检查：${NC}"
echo "• README.md: $([ -f README.md ] && echo '✅ 存在' || echo '❌ 缺失')"
echo "• .gitignore: $([ -f .gitignore ] && echo '✅ 存在' || echo '❌ 缺失')"
echo "• requirements.txt: $([ -f requirements.txt ] && echo '✅ 存在' || echo '❌ 缺失')"
echo "• Dockerfile: $([ -f Dockerfile ] && echo '✅ 存在' || echo '❌ 缺失')"
echo "• docker-compose.yml: $([ -f docker-compose.yml ] && echo '✅ 存在' || echo '❌ 缺失')"

echo ""
echo -e "${YELLOW}项目统计：${NC}"
echo "• Python文件: $(find . -name "*.py" -type f | wc -l) 个"
echo "• 总文件数: $(find . -type f | wc -l) 个"
echo "• 目录数: $(find . -type d | wc -l) 个"

echo ""
echo -e "${GREEN}🎉 项目清理完成！可以进行Git提交了。${NC}"
echo ""
echo -e "${BLUE}建议下一步操作：${NC}"
echo "1. git status"
echo "2. git add ."
echo "3. git commit -m \"feat: 完成Sprint 9生产环境部署和安全审计\""
echo "4. git push origin main"