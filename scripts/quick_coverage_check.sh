#!/bin/bash
# 快速覆盖率检查脚本
# 用于日常开发中快速查看测试覆盖率

set -e

echo "🔍 快速覆盖率检查"
echo "=================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查是否在项目根目录
if [ ! -f "pyproject.toml" ] || [ ! -d "src/api" ]; then
    echo -e "${RED}❌ 请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 运行覆盖率分析
echo "📊 分析当前覆盖率..."
if python simple_coverage_check.py; then
    echo -e "${GREEN}✅ 覆盖率分析完成${NC}"
else
    echo -e "${YELLOW}⚠️ 覆盖率分析遇到问题${NC}"
fi

# 检查是否有测试失败
echo ""
echo "🧪 检查测试状态..."
if python -m pytest tests/unit/api/test_*.py --tb=no -q > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 所有测试通过${NC}"
else
    echo -e "${RED}❌ 部分测试失败${NC}"
    echo "运行 'python -m pytest tests/unit/api/ -v' 查看详情"
fi

# 检查0覆盖率模块
echo ""
echo "🔍 检查0覆盖率模块..."
ZERO_COVERAGE=$(python -c "
import json
try:
    with open('coverage_data.json', 'r') as f:
        data = json.load(f)
    if data:
        last = data[-1]
        zero_modules = [m for m, c in last['modules'].items() if c == 0.0]
        if zero_modules:
            print('🔴 0覆盖率模块:', ', '.join(zero_modules))
        else:
            print('✅ 没有覆盖率为0的模块')
except:
    print('⚠️ 无法获取历史数据')
" 2>/dev/null)

# 提供快速操作建议
echo ""
echo "💡 快速操作:"
echo "1. 运行完整监控: python scripts/coverage_monitor.py"
echo "2. 自动提升覆盖率: python scripts/auto_boost_coverage.py"
echo "3. 运行所有测试: python -m pytest tests/unit/api/ -v"
echo "4. 持续监控模式: python scripts/coverage_monitor.py --continuous"

# 检查是否需要提交
echo ""
if [[ -n $(git status --porcelain tests/unit/api/ 2>/dev/null) ]]; then
    echo -e "${YELLOW}⚠️ 有未提交的测试文件${NC}"
    echo "   运行 'git status' 查看详情"
fi

echo ""
echo "完成时间: $(date)"
echo "=================="