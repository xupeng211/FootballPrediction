#!/bin/bash
#!/bin/bash
"""
QA门禁脚本 - 工业级代码质量验证
确保重构过程中不引入新的语法错误和质量问题
"""

set -e  # 遇到错误立即退出

echo "🚪 QA门禁检查开始..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查计数器
ERRORS=0
WARNINGS=0

# === 1. Python语法检查 ===
echo "🔍 检查Python语法..."
if python -m py_compile src/config_unified.py; then
    echo -e "${GREEN}✅ config_unified.py 语法正确${NC}"
else
    echo -e "${RED}❌ config_unified.py 语法错误${NC}"
    ((ERRORS++))
fi

if python -m py_compile src/services/core_inference.py; then
    echo -e "${GREEN}✅ core_inference.py 语法正确${NC}"
else
    echo -e "${RED}❌ core_inference.py 语法错误${NC}"
    ((ERRORS++))
fi

# === 2. 导入检查 ===
echo "🔍 检查模块导入..."
if python -c "from src.config_unified import get_settings; print('✅ config_unified 导入成功')"; then
    echo -e "${GREEN}✅ config_unified 导入正常${NC}"
else
    echo -e "${RED}❌ config_unified 导入失败${NC}"
    ((ERRORS++))
fi

if python -c "
import sys
sys.path.insert(0, '.')
try:
    from src.services.core_inference import CoreInferenceService
    print('✅ core_inference 导入成功')
except Exception as e:
    print(f'❌ core_inference 导入失败: {e}')
    exit(1)
"; then
    echo -e "${GREEN}✅ core_inference 导入正常${NC}"
else
    echo -e "${RED}❌ core_inference 导入失败${NC}"
    ((ERRORS++))
fi

# === 3. 类型检查（基础） ===
echo "🔍 基础类型检查..."
if python -c "
import sys
sys.path.insert(0, '.')
try:
    from src.config_unified import UnifiedSettings
    # 测试基本类型注解
    settings = UnifiedSettings()
    assert isinstance(settings.environment, str)
    assert isinstance(settings.port, int)
    print('✅ 配置类型注解正确')
except Exception as e:
    print(f'❌ 配置类型注解错误: {e}')
    exit(1)
"; then
    echo -e "${GREEN}✅ 基础类型检查通过${NC}"
else
    echo -e "${RED}❌ 基础类型检查失败${NC}"
    ((ERRORS++))
fi

# === 结果汇总 ===
echo
echo "🏁 QA门禁检查结果:"
echo "==================="

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有检查通过，代码质量合格${NC}"
    echo -e "${GREEN}🎉 可以继续下一步重构${NC}"
    exit 0
elif [ $ERRORS -lt 3 ]; then
    echo -e "${YELLOW}⚠️  发现 $ERRORS 个错误和 $WARNINGS 个警告${NC}"
    echo -e "${YELLOW}🔧 请修复错误后继续${NC}"
    exit 1
else
    echo -e "${RED}❌ 发现 $ERRORS 个错误和 $WARNINGS 个警告${NC}"
    echo -e "${RED}🛑 必须修复错误后才能继续${NC}"
    exit 2
fi
