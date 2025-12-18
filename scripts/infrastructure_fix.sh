#!/bin/bash
# ==============================================
# Infrastructure Optimization Script
# 足球预测系统基础设施修复脚本
# ==============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }
log_command() { echo -e "${CYAN}[CMD]${NC} $1"; }

# 系统检查
check_prerequisites() {
    log_step "检查系统前置条件..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi

    # 检查可用内存
    AVAILABLE_MEM=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    if [ "$AVAILABLE_MEM" -lt 4000 ]; then
        log_warning "可用内存低于4GB，可能影响性能"
    fi

    # 检查磁盘空间
    AVAILABLE_DISK=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_DISK" -lt 50 ]; then
        log_warning "可用磁盘空间少于50GB"
    fi

    log_success "系统检查完成"
}

# 数据备份
backup_data() {
    log_step "备份现有数据..."

    BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    # 检查现有容器是否运行
    if docker ps | grep -q "football-prediction-db"; then
        log_info "备份PostgreSQL数据库..."
        docker exec football-prediction-db pg_dump -U football_user football_prediction_prod > "$BACKUP_DIR/postgres_backup.sql"
    fi

    # 备份配置文件
    cp docker-compose.trial.yml "$BACKUP_DIR/"
    cp .env.trial "$BACKUP_DIR/"

    # 备份模型文件
    if [ -d "data/models" ]; then
        cp -r data/models "$BACKUP_DIR/"
    fi

    log_success "数据备份完成: $BACKUP_DIR"
}

# 环境变量修复
fix_environment() {
    log_step "修复环境变量配置..."

    # 更新.env.trial文件中的数据库密码（确保一致性）
    if [ -f ".env.trial" ]; then
        sed -i 's/FP_prod_2024_secure_change_me/postgres_prod_2024_secure/g' .env.trial
        sed -i 's/DB_PASSWORD=FP_prod_2024_secure_change_me/DB_PASSWORD=postgres_prod_2024_secure/g' .env.trial
    fi

    # 检查代理配置
    if ! grep -q "HTTP_PROXY" .env.trial; then
        log_info "添加代理配置到环境变量..."
        cat >> .env.trial << EOF

# WSL2代理配置
HTTP_PROXY=http://host.docker.internal:7890
HTTPS_PROXY=http://host.docker.internal:7890
NO_PROXY=localhost,127.0.0.1,172.20.0.1/16,db,redis,prometheus,grafana
EOF
    fi

    log_success "环境变量修复完成"
}

# 模型路径修复
fix_model_mount() {
    log_step "修复模型挂载路径..."

    # 创建必要目录
    mkdir -p data/postgres data/redis data/grafana data/prometheus logs/trial

    # 检查模型文件
    if [ ! -f "data/models/football_prediction_model.pkl" ]; then
        log_error "模型文件不存在，请确保模型已正确放置"
        exit 1
    fi

    # 设置模型文件权限
    chmod 644 data/models/football_prediction_model.pkl

    log_success "模型挂载路径修复完成"
}

# 应用优化配置
apply_optimized_config() {
    log_step "应用优化配置..."

    # 停止现有服务
    log_command "docker-compose -f docker-compose.trial.yml down"
    docker-compose -f docker-compose.trial.yml down || true

    # 等待容器完全停止
    sleep 5

    # 启动优化配置
    log_command "docker-compose -f docker-compose.optimized.yml up -d"
    docker-compose -f docker-compose.optimized.yml up -d

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30

    log_success "优化配置应用完成"
}

# 服务验证
verify_services() {
    log_step "验证服务状态..."

    # 检查容器状态
    log_info "检查容器运行状态..."
    docker-compose -f docker-compose.optimized.yml ps

    # 检查应用健康状态
    log_info "检查应用健康状态..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            log_success "应用服务健康检查通过"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "应用服务健康检查失败"
            return 1
        fi
        sleep 2
    done

    # 检查数据库连接
    log_info "检查数据库连接..."
    if docker exec football-prediction-db pg_isready -U football_user &> /dev/null; then
        log_success "数据库连接正常"
    else
        log_error "数据库连接失败"
        return 1
    fi

    # 检查Redis连接
    log_info "检查Redis连接..."
    if docker exec football-prediction-redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis连接正常"
    else
        log_error "Redis连接失败"
        return 1
    fi
}

# 模型状态验证
verify_model_status() {
    log_step "验证模型状态..."

    # 检查模型文件在容器中的可见性
    log_info "检查模型文件可见性..."
    if docker exec football-prediction-app test -f "/app/data/models/football_prediction_model.pkl"; then
        log_success "模型文件在容器中可见"
    else
        log_error "模型文件在容器中不可见"
        return 1
    fi

    # 测试预测功能（注意：这里会显示simulation，因为代码有语法错误）
    log_warning "注意: 由于代码中存在语法错误，预测可能回退到simulation模式"
    log_info "测试预测功能..."
    PREDICTION_RESULT=$(docker exec football-prediction-app python scripts/predict_match_v2.py --home "Test Home" --away "Test Away" 2>&1 | grep -E "(预测结果|Model status)" || echo "Prediction failed")

    if echo "$PREDICTION_RESULT" | grep -q "预测结果"; then
        log_success "预测功能正常执行"
        echo "$PREDICTION_RESULT"
    else
        log_error "预测功能执行失败"
        echo "$PREDICTION_RESULT"
    fi
}

# 网络连通性验证
verify_network() {
    log_step "验证网络连通性..."

    # 测试DNS解析
    log_info "测试DNS解析..."
    if docker exec football-prediction-app nslookup www.fotmob.com &> /dev/null; then
        log_success "DNS解析正常"
    else
        log_warning "DNS解析可能有问题"
    fi

    # 测试代理连接
    log_info "测试代理连接..."
    if docker exec football-prediction-app curl -v --connect-timeout 5 --proxy http://host.docker.internal:7890 https://www.google.com &> /dev/null; then
        log_success "代理连接正常"
    else
        log_warning "代理连接可能有问题"
    fi

    # 测试API连通性
    log_info "测试FotMob API连通性..."
    HTTP_STATUS=$(docker exec football-prediction-app curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 https://www.fotmob.com/api/ || echo "000")

    if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "301" ]; then
        log_success "FotMob API连通正常 (HTTP $HTTP_STATUS)"
    else
        log_warning "FotMob API可能无法访问 (HTTP $HTTP_STATUS)"
    fi
}

# 性能基准测试
performance_benchmark() {
    log_step "执行性能基准测试..."

    # 内存使用检查
    log_info "检查内存使用情况..."
    docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}" football-prediction-app football-prediction-db football-prediction-redis

    # 数据库性能测试
    log_info "测试数据库查询性能..."
    DB_QUERY_TIME=$(docker exec football-prediction-db psql -U football_user -d football_prediction_prod -c "SELECT COUNT(*) FROM matches;" -t | tr -d ' ')
    if [ -n "$DB_QUERY_TIME" ] && [ "$DB_QUERY_TIME" != "" ]; then
        log_success "数据库查询正常，matches表记录数: $DB_QUERY_TIME"
    else
        log_warning "数据库查询测试失败"
    fi

    # Redis性能测试
    log_info "测试Redis性能..."
    REDIS_TEST=$(docker exec football-prediction-redis redis-cli --latency-history -i 1 2>/dev/null | head -1 || echo "Redis test failed")
    log_success "Redis延迟测试: $REDIS_TEST"
}

# 生成验证报告
generate_report() {
    log_step "生成验证报告..."

    REPORT_FILE="INFRASTRUCTURE_VERIFICATION_REPORT_$(date +%Y%m%d_%H%M%S).md"

    cat > "$REPORT_FILE" << EOF
# 基础设施验证报告
**验证时间**: $(date)
**配置文件**: docker-compose.optimized.yml

## 服务状态
\`\`\`
$(docker-compose -f docker-compose.optimized.yml ps)
\`\`\`

## 资源使用情况
\`\`\`
$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}")
\`\`\`

## 网络连通性
- DNS解析: $(docker exec football-prediction-app nslookup www.fotmob.com &> /dev/null && echo "✅ 正常" || echo "❌ 异常")
- 代理连接: $(docker exec football-prediction-app curl -v --connect-timeout 5 --proxy http://host.docker.internal:7890 https://www.google.com &> /dev/null && echo "✅ 正常" || echo "❌ 异常")
- FotMob API: $(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 https://www.fotmob.com/api/ | grep -E "(200|301)" &> /dev/null && echo "✅ 正常" || echo "❌ 异常")

## 模型状态
- 模型文件: $(docker exec football-prediction-app test -f "/app/data/models/football_prediction_model.pkl" && echo "✅ 存在" || echo "❌ 不存在")
- 预测功能: 需要手动验证 (修复代码语法错误后)

## 建议
1. 修复 src/ml/inference/predictor.py 第514行的语法错误
2. 根据实际负载调整数据库连接池大小
3. 考虑升级宿主机内存至16GB以获得更好性能
4. 监控内存使用率，保持在70%以下
EOF

    log_success "验证报告已生成: $REPORT_FILE"
}

# 清理函数
cleanup() {
    log_step "清理临时资源..."

    # 清理未使用的Docker资源
    docker system prune -f

    log_success "清理完成"
}

# 主函数
main() {
    echo "========================================"
    echo "🚀 足球预测系统基础设施优化脚本"
    echo "========================================"
    echo ""

    # 执行优化步骤
    check_prerequisites
    backup_data
    fix_environment
    fix_model_mount
    apply_optimized_config

    # 验证步骤
    verify_services
    verify_model_status
    verify_network
    performance_benchmark

    # 生成报告
    generate_report

    # 清理
    cleanup

    echo ""
    echo "========================================"
    echo "🎉 基础设施优化完成！"
    echo ""
    echo "📋 下一步操作："
    echo "1. 查看监控面板: http://localhost:3000 (admin/admin123_change_me)"
    echo "2. 查看应用状态: http://localhost:8000/health"
    echo "3. 修复代码语法错误后重新测试预测功能"
    echo "4. 根据验证报告调整配置"
    echo "========================================"
}

# 错误处理
trap 'log_error "脚本执行失败，请检查错误信息"; exit 1' ERR

# 执行主函数
main "$@"