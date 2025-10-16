#!/bin/bash
# TDD分享会启动脚本
# 一键准备并启动TDD分享会

echo "🚀 启动TDD分享会准备流程..."
echo "=================================="

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. 检查Python环境
echo -e "\n${YELLOW}1. 检查Python环境...${NC}"
python --version
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Python环境正常${NC}"
else
    echo -e "${RED}❌ Python环境异常${NC}"
    exit 1
fi

# 2. 检查依赖
echo -e "\n${YELLOW}2. 检查依赖包...${NC}"
pip list | grep -E "pytest|pytest-mock"
echo -e "${GREEN}✅ 依赖检查完成${NC}"

# 3. 运行准备检查
echo -e "\n${YELLOW}3. 运行准备检查...${NC}"
python scripts/check_tdd_session_prep.py

# 4. 测试演示代码
echo -e "\n${YELLOW}4. 测试演示代码...${NC}"
cd docs/tdd_presentations
python -m pytest workshop_solutions.py -v --tb=short
cd ../..

# 5. 打开重要文件
echo -e "\n${YELLOW}5. 打开重要文件...${NC}"

# 检查操作系统
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "在macOS上运行，使用open命令..."
    open docs/tdd_presentations/first_tdd_sharing_session.md
    open docs/tdd_presentations/organizing_checklist.md
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "在Linux上运行，请手动打开以下文件："
    echo "  - docs/tdd_presentations/first_tdd_sharing_session.md"
    echo "  - docs/tdd_presentations/organizing_checklist.md"
fi

# 6. 显示下一步行动
echo -e "\n${GREEN}=================================="
echo -e "🎉 TDD分享会准备完成！${NC}"
echo -e "=================================="

echo -e "\n${YELLOW}下一步行动：${NC}"
echo "1. 发送会议通知："
echo "   cat ANNOUNCEMENT_First_TDD_Sharing_Session.md"
echo ""
echo "2. 启动执行助手："
echo "   python scripts/run_tdd_sharing_session.py"
echo ""
echo "3. 准备开始分享会！"

# 7. 创建快速启动别名
echo -e "\n${YELLOW}创建快速启动命令...${NC}"
echo 'alias tdd-session="python scripts/run_tdd_sharing_session.py"' >> ~/.bashrc
echo -e "${GREEN}✅ 已创建别名：tdd-session${NC}"

echo -e "\n${GREEN}准备完成！祝分享会成功！🎉${NC}"
