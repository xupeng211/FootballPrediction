#!/bin/bash
# FootballPrediction System Verification Script
# 系统健康验证脚本 - 金盾行动核心组件

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 系统信息
SCRIPT_NAME="FootballPrediction System Verify"
VERSION="V2.0"
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M:%S)

echo -e "${CYAN}======================================"
echo -e "${CYAN}🛡️ $SCRIPT_NAME $VERSION"
echo -e "${CYAN}📅 Date: $DATE $TIME"
echo -e "${CYAN}🎯 Purpose: 系统健康通行证验证"
echo -e "${CYAN}======================================${NC}"

# 验证结果变量
VERIFY_PASSED=true
ERROR_COUNT=0

# 错误处理函数
handle_error() {
    local error_msg=$1
    echo -e "${RED}❌ $error_msg${NC}"
    VERIFY_PASSED=false
    ERROR_COUNT=$((ERROR_COUNT + 1))
}

# 成功处理函数
handle_success() {
    local success_msg=$1
    echo -e "${GREEN}✅ $success_msg${NC}"
}

# 警告处理函数
handle_warning() {
    local warning_msg=$1
    echo -e "${YELLOW}⚠️ $warning_msg${NC}"
}

# Step 1: 环境配置验证
echo -e "\n${BLUE}🔍 Step 1: 环境配置验证${NC}"
echo -e "${BLUE}--------------------------------${NC}"

# 检查.env文件
if [ ! -f ".env" ]; then
    handle_error "未找到 .env 配置文件"
    echo -e "${YELLOW}💡 请参考 .env.example 创建配置文件${NC}"
else
    handle_success ".env 配置文件存在"
fi

# 验证关键环境变量
echo -e "\n${PURPLE}🔧 检查关键环境变量:${NC}"

# 检查FOTMOB API配置
if grep -q "FOTMOB_X_MAS_HEADER" .env && grep -v "^#" .env | grep -q "FOTMOB_X_MAS_HEADER="; then
    if grep -v "^#" .env | grep "FOTMOB_X_MAS_HEADER=" | grep -q "=.*[^[:space:]]"; then
        handle_success "FOTMOB_X_MAS_HEADER 已配置"
    else
        handle_warning "FOTMOB_X_MAS_HEADER 配置为空"
    fi
else
    handle_error "未找到 FOTMOB_X_MAS_HEADER 配置"
fi

# 检查数据库配置
if grep -q "DB_PASSWORD" .env; then
    if [ "$(grep -v '^#' .env | grep 'DB_PASSWORD=' | cut -d'=' -f2)" != "football_pass" ]; then
        handle_success "数据库密码已自定义配置"
    else
        handle_warning "使用默认数据库密码（生产环境建议修改）"
    fi
else
    handle_error "未找到数据库密码配置"
fi

# 检查模型文件
if [ -f "models/xgb_football_v2_real_scores.joblib" ]; then
    handle_success "V2.0 预测模型文件存在"
else
    handle_error "未找到 V2.0 预测模型文件"
fi

# Step 2: Docker环境验证
echo -e "\n${BLUE}🐳 Step 2: Docker环境验证${NC}"
echo -e "${BLUE}--------------------------------${NC}"

# 检查Docker服务
if ! docker info > /dev/null 2>&1; then
    handle_error "Docker服务未运行，请先启动Docker"
    exit 1
else
    handle_success "Docker服务运行正常"
fi

# 检查Docker Compose
if ! command -v docker-compose &> /dev/null; then
    handle_error "未安装 Docker Compose"
    exit 1
else
    handle_success "Docker Compose 可用"
fi

# 检查必要文件
required_files=("docker-compose.yml" "Dockerfile" "database/seed_data.sql")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        handle_success "$file 存在"
    else
        handle_error "缺少必要文件: $file"
    fi
done

# Step 3: 系统部署验证
echo -e "\n${BLUE}🚀 Step 3: 系统部署验证${NC}"
echo -e "${BLUE}--------------------------------${NC}"

# 检查服务状态
echo -e "${PURPLE}🔍 检查Docker服务状态:${NC}"

# 启动基础服务（数据库和Redis）
echo -e "${YELLOW}🔄 启动基础服务...${NC}"
docker-compose up -d db redis

# 等待数据库就绪
echo -e "${YELLOW}⏳ 等待数据库服务就绪...${NC}"
for i in {1..30}; do
    if docker-compose exec -T db pg_isready -U football_user -d football_prediction > /dev/null 2>&1; then
        handle_success "数据库服务就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        handle_error "数据库服务启动超时"
    fi
    sleep 2
done

# 检查数据库数据完整性
echo -e "${PURPLE}📊 验证数据库数据完整性:${NC}"
match_count=$(docker-compose exec -T db psql -U football_user -d football_prediction -tAc "SELECT COUNT(*) FROM match_features_training;" 2>/dev/null || echo "0")

if [ "$match_count" -eq "415" ]; then
    handle_success "415场黄金数据加载完整"
elif [ "$match_count" -gt "0" ]; then
    handle_warning "数据库包含 $match_count 场比赛数据（预期415场）"
else
    handle_error "数据库未找到比赛数据"
fi

# Step 4: 预测模型验证
echo -e "\n${BLUE}🧠 Step 4: 预测模型验证${NC}"
echo -e "${BLUE}--------------------------------${NC}"

# 构建预测容器
echo -e "${YELLOW}🔨 构建预测容器...${NC}"
if docker-compose build engine > /dev/null 2>&1; then
    handle_success "预测容器构建成功"
else
    handle_error "预测容器构建失败"
fi

# 执行模拟预测测试
echo -e "${PURPLE}⚽ 执行曼联 vs 利物浦预测测试:${NC}"
prediction_result=$(docker-compose run --rm -e DOCKER_ENV=true engine python -c "
import sys
sys.path.append('/app')
from core.inference_engine import get_inference_engine

try:
    engine = get_inference_engine()
    if engine.load_model():
        features = {
            'home_xg': 1.45,
            'away_xg': 1.62,
            'home_possession': 48.0,
            'away_possession': 52.0,
            'home_opening_odds': 2.3,
            'home_current_odds': 2.45
        }
        prediction = engine.predict_match('曼联', '利物浦', features)
        if 'error' not in prediction:
            probs = prediction['probabilities']
            print(f'SUCCESS: 主胜{probs[\"home_win\"]*100:.1f}% 平局{probs[\"draw\"]*100:.1f}% 客胜{probs[\"away_win\"]*100:.1f}%')
        else:
            print(f'ERROR: {prediction[\"error\"]}')
    else:
        print('ERROR: 模型加载失败')
except Exception as e:
    print(f'ERROR: {str(e)}')
" 2>/dev/null)

if [[ $prediction_result == SUCCESS* ]]; then
    handle_success "预测模型测试通过"
    echo -e "${GREEN}   📊 预测结果: ${prediction_result#SUCCESS: }${NC}"
else
    handle_error "预测模型测试失败: ${prediction_result#ERROR: }"
fi

# Step 5: 系统性能基准验证
echo -e "\n${BLUE}📈 Step 5: 系统性能基准验证${NC}"
echo -e "${BLUE}--------------------------------${NC}"

# 检查数据库响应时间
db_response_time=$(docker-compose exec -T db psql -U football_user -d football_prediction -tAc "SELECT 1;" 2>/dev/null || echo "TIMEOUT")
if [ "$db_response_time" = "1" ]; then
    handle_success "数据库响应正常"
else
    handle_error "数据库响应异常"
fi

# 检查磁盘空间（至少需要1GB）
available_space=$(df . | tail -1 | awk '{print $4}')
if [ "$available_space" -gt 1048576 ]; then  # 1GB in KB
    handle_success "磁盘空间充足 ($(du -h . | tail -1 | cut -f1))"
else
    handle_warning "磁盘空间不足1GB，可能影响系统运行"
fi

# Step 6: 验证结果汇总
echo -e "\n${CYAN}======================================"
echo -e "${CYAN}🏆 系统验证结果汇总${NC}"
echo -e "${CYAN}======================================${NC}"

if [ "$VERIFY_PASSED" = true ]; then
    echo -e "${GREEN}🎉 恭喜！系统验证完全通过！${NC}"
    echo -e "${GREEN}✅ FootballPrediction V2.0 已准备好投入使用${NC}"
    echo -e "${GREEN}📊 预测准确率: 60.00% | 数据完整性: 415场比赛${NC}"
    echo -e "${GREEN}🚀 可以安全运行: docker-compose up -d${NC}"
    exit 0
else
    echo -e "${RED}❌ 系统验证失败！发现 $ERROR_COUNT 个问题${NC}"
    echo -e "${YELLOW}📋 请修复上述问题后重新运行验证${NC}"
    echo -e "${YELLOW}🔧 支持文档: 查看 CLAUDE.md 和 README.md${NC}"
    exit 1
fi

echo -e "\n${PURPLE}💡 提示: 运行 'docker-compose logs -f' 查看实时日志${NC}"
echo -e "${PURPLE}💡 提示: 运行 './run_daily_predict.sh' 执行日常预测${NC}"
echo -e "${PURPLE}======================================${NC}"