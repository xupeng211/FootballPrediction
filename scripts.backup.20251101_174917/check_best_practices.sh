#!/bin/bash

# 检查最佳实践实施情况脚本
# Check Best Practices Implementation Script

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印函数
print_header() {
    echo -e "\n${CYAN}=== $1 ===${NC}\n"
}

print_section() {
    echo -e "\n${BLUE}📊 $1${NC}"
}

print_item() {
    local status=$1
    local message=$2

    if [ "$status" = "pass" ]; then
        echo -e "  ${GREEN}✅ $message${NC}"
    elif [ "$status" = "warn" ]; then
        echo -e "  ${YELLOW}⚠️  $message${NC}"
    elif [ "$status" = "fail" ]; then
        echo -e "  ${RED}❌ $message${NC}"
    else
        echo -e "  ℹ️  $message"
    fi
}

print_header "🏗️ 代码最佳实践质量检查"

# 创建报告目录
mkdir -p reports

# 初始化统计
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

# 检查 1: 架构清晰度
print_section "架构清晰度检查"

# 检查是否有重复的基础服务类
if [ -f "src/services/base.py" ] && [ -f "src/services/base_service.py" ]; then
    print_item "fail" "发现重复的基础服务类 (src/services/base.py 和 src/services/base_service.py)"
    ((FAIL_COUNT++))
elif [ -f "src/services/base.py" ] || [ -f "src/services/base_service.py" ]; then
    print_item "pass" "基础服务类已统一"
    ((PASS_COUNT++))
else
    print_item "warn" "未找到基础服务类"
    ((WARN_COUNT++))
fi

# 检查目录结构是否清晰
if [ -d "src/api" ] && [ -d "src/services" ] && [ -d "src/database" ] && [ -d "src/core" ]; then
    print_item "pass" "目录结构清晰 (api, services, database, core)"
    ((PASS_COUNT++))
else
    print_item "fail" "目录结构不完整"
    ((FAIL_COUNT++))
fi

# 检查 2: 仓储模式
print_section "仓储模式检查"

if [ -d "src/database/repositories" ]; then
    REPO_COUNT=$(find src/database/repositories -name "*.py" -type f | wc -l)
    if [ $REPO_COUNT -gt 0 ]; then
        print_item "pass" "仓储模式已实现 ($REPO_COUNT 个仓储文件)"
        ((PASS_COUNT++))

        # 检查基础仓储接口
        if [ -f "src/database/repositories/base.py" ]; then
            print_item "pass" "发现基础仓储接口"
            ((PASS_COUNT++))
        else
            print_item "warn" "缺少基础仓储接口"
            ((WARN_COUNT++))
        fi
    else
        print_item "warn" "仓储目录存在但为空"
        ((WARN_COUNT++))
    fi
else
    print_item "fail" "未实现仓储模式"
    ((FAIL_COUNT++))
fi

# 检查 3: 领域模型
print_section "领域模型检查"

if [ -d "src/domain" ]; then
    DOMAIN_COUNT=$(find src/domain -name "*.py" -type f | wc -l)
    if [ $DOMAIN_COUNT -gt 0 ]; then
        print_item "pass" "领域模型已实现 ($DOMAIN_COUNT 个领域模型文件)"
        ((PASS_COUNT++))
    else
        print_item "warn" "领域目录存在但为空"
        ((WARN_COUNT++))
    fi
else
    print_item "fail" "未实现领域模型"
    ((FAIL_COUNT++))
fi

# 检查 4: 设计模式使用
print_section "设计模式检查"

# 统计设计模式
FACTORY_COUNT=$(grep -r "class.*Factory" src --include="*.py" 2>/dev/null | wc -l)
STRATEGY_COUNT=$(grep -r "class.*Strategy" src --include="*.py" 2>/dev/null | wc -l)
SINGLETON_COUNT=$(grep -r "class.*Singleton\|@singleton" src --include="*.py" 2>/dev/null | wc -l)
OBSERVER_COUNT=$(grep -r "class.*Observer\|class.*Subject" src --include="*.py" 2>/dev/null | wc -l)
DECORATOR_COUNT=$(grep -r "def.*decorator\|@.*decorator" src --include="*.py" 2>/dev/null | wc -l)

TOTAL_PATTERNS=$((FACTORY_COUNT + STRATEGY_COUNT + SINGLETON_COUNT + OBSERVER_COUNT))

if [ $TOTAL_PATTERNS -gt 0 ]; then
    print_item "pass" "使用了 $TOTAL_PATTERNS 种设计模式"
    ((PASS_COUNT++))

    [ $FACTORY_COUNT -gt 0 ] && print_item "pass" "  - 工厂模式 ($FACTORY_COUNT)"
    [ $STRATEGY_COUNT -gt 0 ] && print_item "pass" "  - 策略模式 ($STRATEGY_COUNT)"
    [ $SINGLETON_COUNT -gt 0 ] && print_item "pass" "  - 单例模式 ($SINGLETON_COUNT)"
    [ $OBSERVER_COUNT -gt 0 ] && print_item "pass" "  - 观察者模式 ($OBSERVER_COUNT)"
    [ $DECORATOR_COUNT -gt 0 ] && print_item "pass" "  - 装饰器模式相关 ($DECORATOR_COUNT)"
else
    print_item "warn" "未检测到明确的设计模式使用"
    ((WARN_COUNT++))
fi

# 检查 5: 依赖注入
print_section "依赖注入检查"

if grep -q "Depends\|DependencyInjector\|inject" src/api/*.py 2>/dev/null; then
    print_item "pass" "使用了依赖注入"
    ((PASS_COUNT++))
else
    print_item "warn" "未检测到依赖注入使用"
    ((WARN_COUNT++))
fi

# 检查 6: 缓存装饰器
print_section "缓存装饰器检查"

if grep -r "@cache\|@cache_result\|@lru_cache" src --include="*.py" 2>/dev/null | grep -q .; then
    CACHE_COUNT=$(grep -r "@cache\|@cache_result\|@lru_cache" src --include="*.py" 2>/dev/null | wc -l)
    print_item "pass" "使用了缓存装饰器 ($CACHE_COUNT 处)"
    ((PASS_COUNT++))
else
    print_item "warn" "未检测到缓存装饰器使用"
    ((WARN_COUNT++))
fi

# 检查 7: 事件系统
print_section "事件系统检查"

if grep -r "Event\|EventBus\|publish\|subscribe" src --include="*.py" 2>/dev/null | grep -q .; then
    print_item "pass" "实现了事件系统"
    ((PASS_COUNT++))
else
    print_item "warn" "未检测到事件系统"
    ((WARN_COUNT++))
fi

# 检查 8: 测试覆盖率
print_section "测试覆盖率检查"

if command -v pytest &> /dev/null; then
    COVERAGE_OUTPUT=$(make coverage-local 2>&1 || echo "0%")
    COVERAGE_PERCENT=$(echo "$COVERAGE_OUTPUT" | grep -o '[0-9]*\%' | tail -1 || echo "0%")
    COVERAGE_NUM=$(echo "$COVERAGE_PERCENT" | sed 's/%//')

    if [ $COVERAGE_NUM -ge 80 ]; then
        print_item "pass" "测试覆盖率优秀 ($COVERAGE_PERCENT)"
        ((PASS_COUNT++))
    elif [ $COVERAGE_NUM -ge 50 ]; then
        print_item "warn" "测试覆盖率一般 ($COVERAGE_PERCENT)"
        ((WARN_COUNT++))
    else
        print_item "fail" "测试覆盖率过低 ($COVERAGE_PERCENT)"
        ((FAIL_COUNT++))
    fi
else
    print_item "warn" "pytest 未安装，无法检查测试覆盖率"
    ((WARN_COUNT++))
fi

# 检查 9: 代码复杂度
print_section "代码复杂度检查"

# 统计大文件（超过200行）
LARGE_FILES=$(find src -name "*.py" -exec wc -l {} + 2>/dev/null | awk '$1 > 200 { print $2 }' | wc -l)
if [ $LARGE_FILES -eq 0 ]; then
    print_item "pass" "没有超大文件 (>200行)"
    ((PASS_COUNT++))
elif [ $LARGE_FILES -le 3 ]; then
    print_item "warn" "有 $LARGE_FILES 个大文件 (>200行)"
    ((WARN_COUNT++))
else
    print_item "fail" "有太多大文件 ($LARGE_FILES 个 >200行)"
    ((FAIL_COUNT++))
fi

# 生成质量评分
TOTAL_CHECKS=$((PASS_COUNT + WARN_COUNT + FAIL_COUNT))
PASS_RATE=$((PASS_COUNT * 100 / TOTAL_CHECKS))
QUALITY_SCORE=$((PASS_RATE - (WARN_COUNT * 5) - (FAIL_COUNT * 10)))

if [ $QUALITY_SCORE -lt 0 ]; then
    QUALITY_SCORE=0
elif [ $QUALITY_SCORE -gt 100 ]; then
    QUALITY_SCORE=100
fi

# 打印总结
print_header "📊 质量检查总结"

echo -e "检查项目: $TOTAL_CHECKS"
echo -e "${GREEN}✅ 通过: $PASS_COUNT${NC}"
echo -e "${YELLOW}⚠️  警告: $WARN_COUNT${NC}"
echo -e "${RED}❌ 失败: $FAIL_COUNT${NC}"
echo -e "\n通过率: $PASS_RATE%"
echo -e "质量评分: $QUALITY_SCORE/100"

# 评级
if [ $QUALITY_SCORE -ge 85 ]; then
    echo -e "\n${GREEN}🏆 代码质量：优秀${NC}"
    echo -e "您的代码遵循了大部分最佳实践！"
elif [ $QUALITY_SCORE -ge 70 ]; then
    echo -e "\n${YELLOW}🌟 代码质量：良好${NC}"
    echo -e "代码质量不错，还有一些改进空间。"
elif [ $QUALITY_SCORE -ge 50 ]; then
    echo -e "\n${YELLOW}📈 代码质量：中等${NC}"
    echo -e "需要关注一些最佳实践的实施。"
else
    echo -e "\n${RED}⚠️ 代码质量：需要改进${NC}"
    echo -e "建议优先关注标记为失败的项目。"
fi

# 生成报告文件
REPORT_FILE="reports/best_practices_report_$(date +%Y%m%d_%H%M%S).md"
cat > "$REPORT_FILE" << EOF
# 代码最佳实践检查报告

**检查时间**: $(date)
**质量评分**: $QUALITY_SCORE/100

## 检查结果

| 类别 | 状态 | 数量 |
|------|------|------|
| ✅ 通过 | $PASS_COUNT |
| ⚠️ 警告 | $WARN_COUNT |
| ❌ 失败 | $FAIL_COUNT |
| **总计** | **$TOTAL_CHECKS** | |
| **通过率** | **$PASS_RATE%** | |

## 改进建议

1. 查看详细的任务列表: [BEST_PRACTICES_KANBAN.md](BEST_PRACTICES_KANBAN.md)
2. 使用 \`make best-practices-start TASK=X.X\` 开始特定任务
3. 定期运行 \`make best-practices-check\` 跟踪进度

EOF

echo -e "\n${CYAN}📄 详细报告已生成: $REPORT_FILE${NC}"
echo -e "\n${BLUE}💡 下一步操作:${NC}"
echo -e "  运行 'make best-practices-plan' 查看今天的优化任务"
echo -e "  运行 'make best-practices-start TASK=1.1' 开始第一个任务"
echo -e "  查看 BEST_PRACTICES_KANBAN.md 了解完整的优化路线图"
