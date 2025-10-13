#=============================================================================

cat > partial_config_rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Partial Configuration Rollback ==="

=============================================================================

cat > partial_config_rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Partial Configuration Rollback ==="
#
#备份当前特定配置
echo "Backing up specific configurations..."
cp .env.production .env.production.backup_$(date +%Y%m%d_%H%M%S)

备份当前特定配置
echo "Backing up specific configurations..."
cp .env.production .env.production.backup_$(date +%Y%m%d_%H%M%S)
#
#选择回滚项目
echo "Available configuration items to rollback:"
echo "1. Database passwords"
echo "2. Redis configuration"
echo "3. API endpoints"
echo "4. Monitoring settings"
echo "5. Model settings"

read -p "Enter item number to rollback (1-5): " ITEM_NUMBER

case $ITEM_NUMBER in
    1)
        echo "Rolling back database passwords..."
        # 从备份恢复数据库密码
        sed -i 's/DB_PASSWORD=.*/DB_PASSWORD=previous_password_here/' .env.production
        sed -i 's/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=previous_postgres_password_here/' .env.production
        ;;
    2)
        echo "Rolling back Redis configuration..."
        sed -i 's/REDIS_PASSWORD=.*/REDIS_PASSWORD=previous_redis_password_here/' .env.production
        sed -i 's/REDIS_URL=.*/REDIS_URL=redis://:previous_redis_password_here@redis:6379\/0/' .env.production
        ;;
    3)
        echo "Rolling back API endpoints..."
        sed -i 's/API_HOST=.*/API_HOST=0.0.0.0/' .env.production
        sed -i 's/API_PORT=.*/API_PORT=8000/' .env.production
        ;;
    4)
        echo "Rolling back monitoring settings..."
        sed -i 's/GRAFANA_ADMIN_PASSWORD=.*/GRAFANA_ADMIN_PASSWORD=previous_grafana_password/' .env.production
        ;;
    5)
        echo "Rolling back model settings..."
        sed -i 's/MODEL_CACHE_TTL_HOURS=.*/MODEL_CACHE_TTL_HOURS=1/' .env.production
        sed -i 's/PRODUCTION_MODEL_VERSION=.*/PRODUCTION_MODEL_VERSION=previous_version/' .env.production
        ;;
    *)
        echo "Invalid item number"
        exit 1
        ;;
esac

选择回滚项目
echo "Available configuration items to rollback:"
echo "1. Database passwords"
echo "2. Redis configuration"
echo "3. API endpoints"
echo "4. Monitoring settings"
echo "5. Model settings"

read -p "Enter item number to rollback (1-5): " ITEM_NUMBER

case $ITEM_NUMBER in
    1)
        echo "Rolling back database passwords..."
        # 从备份恢复数据库密码
        sed -i 's/DB_PASSWORD=.*/DB_PASSWORD=previous_password_here/' .env.production
        sed -i 's/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=previous_postgres_password_here/' .env.production
        ;;
    2)
        echo "Rolling back Redis configuration..."
        sed -i 's/REDIS_PASSWORD=.*/REDIS_PASSWORD=previous_redis_password_here/' .env.production
        sed -i 's/REDIS_URL=.*/REDIS_URL=redis://:previous_redis_password_here@redis:6379\/0/' .env.production
        ;;
    3)
        echo "Rolling back API endpoints..."
        sed -i 's/API_HOST=.*/API_HOST=0.0.0.0/' .env.production
        sed -i 's/API_PORT=.*/API_PORT=8000/' .env.production
        ;;
    4)
        echo "Rolling back monitoring settings..."
        sed -i 's/GRAFANA_ADMIN_PASSWORD=.*/GRAFANA_ADMIN_PASSWORD=previous_grafana_password/' .env.production
        ;;
    5)
        echo "Rolling back model settings..."
        sed -i 's/MODEL_CACHE_TTL_HOURS=.*/MODEL_CACHE_TTL_HOURS=1/' .env.production
        sed -i 's/PRODUCTION_MODEL_VERSION=.*/PRODUCTION_MODEL_VERSION=previous_version/' .env.production
        ;;
    *)
        echo "Invalid item number"
        exit 1
        ;;
esac
#
#重启相关服务
echo "Restarting affected services..."
docker-compose restart app celery-worker celery-beat

重启相关服务
echo "Restarting affected services..."
docker-compose restart app celery-worker celery-beat
#
#验证更改
echo "Verifying configuration changes..."
curl -f http://localhost:8000/health

echo "✅ Partial configuration rollback completed"
EOF

chmod +x partial_config_rollback.sh
```

验证更改
echo "Verifying configuration changes..."
curl -f http://localhost:8000/health

echo "✅ Partial configuration rollback completed"
EOF

chmod +x partial_config_rollback.sh
```
###
###4. 验证回滚成功的检查步骤

#### ✅ 检查清单：回滚验证

- [ ] **服务状态**: 所有服务正常运行
- [ ] **数据一致性**: 数据回滚后一致性验证
- [ ] **功能验证**: 核心功能正常工作
- [ ] **性能指标**: 性能指标恢复到正常范围
- [ ] **监控告警**: 监控系统正常工作
- [ ] **日志检查**: 错误日志在正常范围内

#### 🧪 回滚后验证脚本

```bash
4. 验证回滚成功的检查步骤

#### ✅ 检查清单：回滚验证

- [ ] **服务状态**: 所有服务正常运行
- [ ] **数据一致性**: 数据回滚后一致性验证
- [ ] **功能验证**: 核心功能正常工作
- [ ] **性能指标**: 性能指标恢复到正常范围
- [ ] **监控告警**: 监控系统正常工作
- [ ] **日志检查**: 错误日志在正常范围内

#### 🧪 回滚后验证脚本

```bash#
#=============================================================================
=============================================================================#
#1. 综合回滚验证脚本
1. 综合回滚验证脚本#
#=============================================================================

cat > verify_rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Rollback Verification Script ==="
echo "Verification started at $(date)"

=============================================================================

cat > verify_rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Rollback Verification Script ==="
echo "Verification started at $(date)"
#
#创建验证报告文件
REPORT_FILE="rollback_verification_$(date +%Y%m%d_%H%M%S).txt"
echo "Rollback Verification Report" > $REPORT_FILE
echo "Timestamp: $(date)" >> $REPORT_FILE
echo "================================" >> $REPORT_FILE

创建验证报告文件
REPORT_FILE="rollback_verification_$(date +%Y%m%d_%H%M%S).txt"
echo "Rollback Verification Report" > $REPORT_FILE
echo "Timestamp: $(date)" >> $REPORT_FILE
echo "================================" >> $REPORT_FILE
#
#初始化验证计数器
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

初始化验证计数器
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
#
#验证函数
verify() {
    local check_name="$1"
    local check_command="$2"

    echo "Verifying: $check_name"
    echo "Checking: $check_name" >> $REPORT_FILE

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if eval "$check_command" >> $REPORT_FILE 2>&1; then
        echo "✅ PASSED: $check_name"
        echo "Status: PASSED" >> $REPORT_FILE
        echo "" >> $REPORT_FILE
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "❌ FAILED: $check_name"
        echo "Status: FAILED" >> $REPORT_FILE
        echo "" >> $REPORT_FILE
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

验证函数
verify() {
    local check_name="$1"
    local check_command="$2"

    echo "Verifying: $check_name"
    echo "Checking: $check_name" >> $REPORT_FILE

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if eval "$check_command" >> $REPORT_FILE 2>&1; then
        echo "✅ PASSED: $check_name"
        echo "Status: PASSED" >> $REPORT_FILE
        echo "" >> $REPORT_FILE
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "❌ FAILED: $check_name"
        echo "Status: FAILED" >> $REPORT_FILE
        echo "" >> $REPORT_FILE
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}
#
#=============================================================================
=============================================================================#
#1. 服务状态验证
1. 服务状态验证#
#=============================================================================

verify "Docker services status" "docker-compose ps | grep -q 'Up'"
verify "Application service health" "curl -f http://localhost:8000/health"
verify "Database connectivity" "docker exec football_prediction_db pg_isready -U football_user"
verify "Redis connectivity" "docker exec football_prediction_redis redis-cli ping"
verify "MLflow service" "curl -f http://localhost:5002/health"
verify "Grafana service" "curl -f http://localhost:3000/api/health"

=============================================================================

verify "Docker services status" "docker-compose ps | grep -q 'Up'"
verify "Application service health" "curl -f http://localhost:8000/health"
verify "Database connectivity" "docker exec football_prediction_db pg_isready -U football_user"
verify "Redis connectivity" "docker exec football_prediction_redis redis-cli ping"
verify "MLflow service" "curl -f http://localhost:5002/health"
verify "Grafana service" "curl -f http://localhost:3000/api/health"
#
#=============================================================================
=============================================================================#
#2. 数据一致性验证
2. 数据一致性验证#
#=============================================================================

verify "Database tables exist" "docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c 'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '\\\"public\\\";' | grep -q '[0-9]'"

verify "Essential data present" "
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c 'SELECT COUNT(*) FROM leagues;' | grep -q '[0-9]'
"

verify "No data corruption" "
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c 'SELECT COUNT(*) FROM matches WHERE match_date > now() + interval '1 year';' | grep -q '^0$'
"

=============================================================================

verify "Database tables exist" "docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c 'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '\\\"public\\\";' | grep -q '[0-9]'"

verify "Essential data present" "
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c 'SELECT COUNT(*) FROM leagues;' | grep -q '[0-9]'
"

verify "No data corruption" "
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c 'SELECT COUNT(*) FROM matches WHERE match_date > now() + interval '1 year';' | grep -q '^0$'
"
#
#=============================================================================
=============================================================================#
#3. 功能验证
3. 功能验证#
#=============================================================================

verify "API endpoints accessible" "curl -f http://localhost:8000/docs"
verify "Prediction API functional" "
curl -X POST http://localhost:8000/api/v1/predictions/ \
  -H 'Content-Type: application/json' \
  -d '{\"match_id\": \"rollback_test\", \"home_team_id\": 1, \"away_team_id\": 2, \"league_id\": 1, \"match_date\": \"2025-09-25T15:00:00Z\"}' | grep -q 'prediction_id'
"

verify "Data retrieval working" "curl -f http://localhost:8000/api/v1/data/teams?limit=5"
verify "Feature access working" "curl -f http://localhost:8000/api/v1/features/"

=============================================================================

verify "API endpoints accessible" "curl -f http://localhost:8000/docs"
verify "Prediction API functional" "
curl -X POST http://localhost:8000/api/v1/predictions/ \
  -H 'Content-Type: application/json' \
  -d '{\"match_id\": \"rollback_test\", \"home_team_id\": 1, \"away_team_id\": 2, \"league_id\": 1, \"match_date\": \"2025-09-25T15:00:00Z\"}' | grep -q 'prediction_id'
"

verify "Data retrieval working" "curl -f http://localhost:8000/api/v1/data/teams?limit=5"
verify "Feature access working" "curl -f http://localhost:8000/api/v1/features/"
#
#=============================================================================
=============================================================================#
#4. 性能验证
4. 性能验证#
#=============================================================================

verify "Response time acceptable" "
response_time=\$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/health)
echo \"Response time: \$response_time seconds\"
if (( \$(echo \"\$response_time < 0.5\" | bc -l) )); then
    exit 0
else
    exit 1
fi
"

verify "Memory usage normal" "
memory_usage=\$(docker stats football_prediction_app --no-stream --format '{{.MemUsage}}' | head -1 | cut -d'%' -f1 | tr -d ' ')
echo \"Memory usage: \$memory_usage%\"
if [ \"\$memory_usage\" -lt 80 ]; then
    exit 0
else
    exit 1
fi
"

verify "CPU usage normal" "
cpu_usage=\$(docker stats football_prediction_app --no-stream --format '{{.CPUPerc}}' | head -1 | tr -d '%')
echo \"CPU usage: \$cpu_usage%\"
if (( \$(echo \"\$cpu_usage < 80\" | bc -l) )); then
    exit 0
else
    exit 1
fi
"

=============================================================================

verify "Response time acceptable" "
response_time=\$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/health)
echo \"Response time: \$response_time seconds\"
if (( \$(echo \"\$response_time < 0.5\" | bc -l) )); then
    exit 0
else
    exit 1
fi
"

verify "Memory usage normal" "
memory_usage=\$(docker stats football_prediction_app --no-stream --format '{{.MemUsage}}' | head -1 | cut -d'%' -f1 | tr -d ' ')
echo \"Memory usage: \$memory_usage%\"
if [ \"\$memory_usage\" -lt 80 ]; then
    exit 0
else
    exit 1
fi
"

verify "CPU usage normal" "
cpu_usage=\$(docker stats football_prediction_app --no-stream --format '{{.CPUPerc}}' | head -1 | tr -d '%')
echo \"CPU usage: \$cpu_usage%\"
if (( \$(echo \"\$cpu_usage < 80\" | bc -l) )); then
    exit 0
else
    exit 1
fi
"
#
#=============================================================================
=============================================================================#
#5. 监控验证
5. 监控验证#
#=============================================================================

verify "Prometheus metrics available" "curl -f http://localhost:8000/metrics | grep -q 'football_predictions_total'"
verify "Grafana accessible" "curl -f http://localhost:3000/api/health"
verify "AlertManager functioning" "curl -f http://localhost:9093/-/ready"

=============================================================================

verify "Prometheus metrics available" "curl -f http://localhost:8000/metrics | grep -q 'football_predictions_total'"
verify "Grafana accessible" "curl -f http://localhost:3000/api/health"
verify "AlertManager functioning" "curl -f http://localhost:9093/-/ready"
#
#=============================================================================
=============================================================================#
#6. 日志验证
6. 日志验证#
#=============================================================================

verify "No critical errors in logs" "
! docker-compose logs app | tail -100 | grep -E '(ERROR|CRITICAL|Exception)' | grep -v 'test'
"

verify "Database connection stable" "
! docker-compose logs app | tail -100 | grep -E '(Connection refused|Database.*failed|authentication.*failed)'
"

=============================================================================

verify "No critical errors in logs" "
! docker-compose logs app | tail -100 | grep -E '(ERROR|CRITICAL|Exception)' | grep -v 'test'
"

verify "Database connection stable" "
! docker-compose logs app | tail -100 | grep -E '(Connection refused|Database.*failed|authentication.*failed)'
"
#
#=============================================================================
=============================================================================#
#7. 生成验证报告
7. 生成验证报告#
#=============================================================================

echo "================================" >> $REPORT_FILE
echo "Verification Summary" >> $REPORT_FILE
echo "Total checks: $TOTAL_CHECKS" >> $REPORT_FILE
echo "Passed: $PASSED_CHECKS" >> $REPORT_FILE
echo "Failed: $FAILED_CHECKS" >> $REPORT_FILE
echo "Success rate: $(( PASSED_CHECKS * 100 / TOTAL_CHECKS ))%" >> $REPORT_FILE
echo "Verification completed at $(date)" >> $REPORT_FILE

=============================================================================

echo "================================" >> $REPORT_FILE
echo "Verification Summary" >> $REPORT_FILE
echo "Total checks: $TOTAL_CHECKS" >> $REPORT_FILE
echo "Passed: $PASSED_CHECKS" >> $REPORT_FILE
echo "Failed: $FAILED_CHECKS" >> $REPORT_FILE
echo "Success rate: $(( PASSED_CHECKS * 100 / TOTAL_CHECKS ))%" >> $REPORT_FILE
echo "Verification completed at $(date)" >> $REPORT_FILE
#
#显示结果
echo ""
echo "=== Rollback Verification Summary ==="
echo "Total checks: $TOTAL_CHECKS"
echo "Passed: $PASSED_CHECKS"
echo "Failed: $FAILED_CHECKS"
echo "Success rate: $(( PASSED_CHECKS * 100 / TOTAL_CHECKS ))%"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo "✅ All checks passed! Rollback successful."
    exit 0
else
    echo "❌ $FAILED_CHECKS checks failed. Manual intervention required."
    echo "Detailed report saved to: $REPORT_FILE"
    exit 1
fi
EOF

chmod +x verify_rollback.sh

显示结果
echo ""
echo "=== Rollback Verification Summary ==="
echo "Total checks: $TOTAL_CHECKS"
echo "Passed: $PASSED_CHECKS"
echo "Failed: $FAILED_CHECKS"
echo "Success rate: $(( PASSED_CHECKS * 100 / TOTAL_CHECKS ))%"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo "✅ All checks passed! Rollback successful."
    exit 0
else
    echo "❌ $FAILED_CHECKS checks failed. Manual intervention required."
    echo "Detailed report saved to: $REPORT_FILE"
    exit 1
fi
EOF

chmod +x verify_rollback.sh
#
#=============================================================================
=============================================================================#
#2. 执行验证
2. 执行验证#
#=============================================================================

=============================================================================
#
#注意：在执行回滚后运行此脚本
注意：在执行回滚后运行此脚本#
#./verify_rollback.sh
```

---

./verify_rollback.sh
```

---
##
##🚨 常见问题与应急预案

🚨 常见问题与应急预案
###
###1. 服务无法启动

#### 🔍 问题诊断步骤

```bash
1. 服务无法启动

#### 🔍 问题诊断步骤

```bash#
#=============================================================================
=============================================================================#
#1. 检查服务状态
1. 检查服务状态#
#=============================================================================

=============================================================================
#
#查看所有服务状态
docker-compose ps

查看所有服务状态
docker-compose ps
#
#检查特定服务状态
docker-compose ps app

检查特定服务状态
docker-compose ps app
#
#查看服务日志
docker-compose logs app
docker-compose logs --tail=50 app

查看服务日志
docker-compose logs app
docker-compose logs --tail=50 app
#
#=============================================================================
=============================================================================#
#2. 检查依赖服务
2. 检查依赖服务#
#=============================================================================

=============================================================================
#
#检查数据库连接
docker exec football_prediction_db pg_isready -U football_user

检查数据库连接
docker exec football_prediction_db pg_isready -U football_user
#
#检查Redis连接
docker exec football_prediction_redis redis-cli ping

检查Redis连接
docker exec football_prediction_redis redis-cli ping
#
#检查网络连接
docker network ls
docker network inspect football-network

检查网络连接
docker network ls
docker network inspect football-network
#
#=============================================================================
=============================================================================#
#3. 检查资源使用
3. 检查资源使用#
#=============================================================================

=============================================================================
#
#检查内存使用
docker stats football_prediction_app

检查内存使用
docker stats football_prediction_app
#
#检查磁盘空间
df -h

检查磁盘空间
df -h
#
#检查端口占用
netstat -tulpn | grep :8000

检查端口占用
netstat -tulpn | grep :8000
#
#=============================================================================
=============================================================================#
#4. 常见启动问题解决
4. 常见启动问题解决#
#=============================================================================

=============================================================================
#
#问题1: 数据库连接失败
if docker-compose logs app | grep -q "Connection refused"; then
    echo "解决方案: 检查数据库服务状态和网络配置"
    docker-compose restart db
    sleep 10
    docker-compose restart app
fi

问题1: 数据库连接失败
if docker-compose logs app | grep -q "Connection refused"; then
    echo "解决方案: 检查数据库服务状态和网络配置"
    docker-compose restart db
    sleep 10
    docker-compose restart app
fi
#
#问题2: Redis连接失败
if docker-compose logs app | grep -q "Redis connection"; then
    echo "解决方案: 检查Redis服务状态和密码配置"
    docker-compose restart redis
    sleep 5
    docker-compose restart app
fi

问题2: Redis连接失败
if docker-compose logs app | grep -q "Redis connection"; then
    echo "解决方案: 检查Redis服务状态和密码配置"
    docker-compose restart redis
    sleep 5
    docker-compose restart app
fi
#
#问题3: 端口冲突
if docker-compose logs app | grep -q "Address already in use"; then
    echo "解决方案: 检查端口占用情况"
    lsof -i :8000
    # 杀死占用端口的进程
    # kill -9 <PID>
fi

问题3: 端口冲突
if docker-compose logs app | grep -q "Address already in use"; then
    echo "解决方案: 检查端口占用情况"
    lsof -i :8000
    # 杀死占用端口的进程
    # kill -9 <PID>
fi
#
#问题4: 权限问题
if docker-compose logs app | grep -q "Permission denied"; then
    echo "解决方案: 检查文件权限和环境变量"
    chown -R 999:999 data/
    docker-compose restart app
fi
```

#### 🛠️ 应急解决方案

```bash
问题4: 权限问题
if docker-compose logs app | grep -q "Permission denied"; then
    echo "解决方案: 检查文件权限和环境变量"
    chown -R 999:999 data/
    docker-compose restart app
fi
```

#### 🛠️ 应急解决方案

```bash#
#=============================================================================
=============================================================================#
#1. 紧急重启脚本
1. 紧急重启脚本#
#=============================================================================

cat > emergency_restart.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Emergency Service Restart ==="

=============================================================================

cat > emergency_restart.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Emergency Service Restart ==="
#
#记录当前状态
echo "Current service status:" > emergency_restart.log
docker-compose ps >> emergency_restart.log

记录当前状态
echo "Current service status:" > emergency_restart.log
docker-compose ps >> emergency_restart.log
#
#停止所有服务
echo "Stopping all services..."
docker-compose down

停止所有服务
echo "Stopping all services..."
docker-compose down
#
#清理资源
echo "Cleaning up resources..."
docker system prune -f
docker volume prune -f

清理资源
echo "Cleaning up resources..."
docker system prune -f
docker volume prune -f
#
#重新启动基础设施
echo "Starting infrastructure services..."
docker-compose up -d db redis

重新启动基础设施
echo "Starting infrastructure services..."
docker-compose up -d db redis
#
#等待基础设施就绪
echo "Waiting for infrastructure..."
timeout 60 bash -c 'until docker exec football_prediction_db pg_isready -U football_user; do sleep 2; done'
timeout 30 bash -c 'until docker exec football_prediction_redis redis-cli ping; do sleep 2; done'

等待基础设施就绪
echo "Waiting for infrastructure..."
timeout 60 bash -c 'until docker exec football_prediction_db pg_isready -U football_user; do sleep 2; done'
timeout 30 bash -c 'until docker exec football_prediction_redis redis-cli ping; do sleep 2; done'
#
#启动应用服务
echo "Starting application services..."
docker-compose up -d app

启动应用服务
echo "Starting application services..."
docker-compose up -d app
#
#等待应用启动
echo "Waiting for application..."
sleep 30

等待应用启动
echo "Waiting for application..."
sleep 30
#
#验证服务状态
echo "Verifying service status..."
docker-compose ps >> emergency_restart.log
curl -f http://localhost:8000/health >> emergency_restart.log 2>&1

echo "Emergency restart completed"
echo "Log saved to emergency_restart.log"
EOF

chmod +x emergency_restart.sh

验证服务状态
echo "Verifying service status..."
docker-compose ps >> emergency_restart.log
curl -f http://localhost:8000/health >> emergency_restart.log 2>&1

echo "Emergency restart completed"
echo "Log saved to emergency_restart.log"
EOF

chmod +x emergency_restart.sh
#
#=============================================================================
=============================================================================#
#2. 单独服务重启
2. 单独服务重启#
#=============================================================================

=============================================================================
#
#重启特定服务
docker-compose restart app
docker-compose restart db
docker-compose restart redis

重启特定服务
docker-compose restart app
docker-compose restart db
docker-compose restart redis
#
#强制重启
docker-compose restart --timeout 60 app

强制重启
docker-compose restart --timeout 60 app
#
#=============================================================================
=============================================================================#
#3. 配置重置
3. 配置重置#
#=============================================================================

=============================================================================
#
#重置到默认配置
cp .env.production.example .env.production
docker-compose down
docker-compose up -d
```

重置到默认配置
cp .env.production.example .env.production
docker-compose down
docker-compose up -d
```
###
###2. API 请求 500

#### 🔍 问题诊断步骤

```bash
2. API 请求 500

#### 🔍 问题诊断步骤

```bash#
#=============================================================================
=============================================================================#
#1. 检查错误日志
1. 检查错误日志#
#=============================================================================

=============================================================================
#
#查看应用错误日志
docker-compose logs app | grep -E "(500|ERROR|Exception|Traceback)" | tail -20

查看应用错误日志
docker-compose logs app | grep -E "(500|ERROR|Exception|Traceback)" | tail -20
#
#查看最新错误
docker-compose logs --tail=100 app | grep -A 5 -B 5 "ERROR"

查看最新错误
docker-compose logs --tail=100 app | grep -A 5 -B 5 "ERROR"
#
#=============================================================================
=============================================================================#
#2. 检查模型文件
2. 检查模型文件#
#=============================================================================

=============================================================================
#
#检查MLflow模型注册
curl -s http://localhost:5002/api/2.0/registered-models/get?name=football-match-predictor | jq '.latest_versions[]'

检查MLflow模型注册
curl -s http://localhost:5002/api/2.0/registered-models/get?name=football-match-predictor | jq '.latest_versions[]'
#
#检查模型文件存在
docker exec football_prediction_mlflow ls -la /mlflow-artifacts/

检查模型文件存在
docker exec football_prediction_mlflow ls -la /mlflow-artifacts/
#
#检查模型加载日志
docker-compose logs app | grep -i "model\|mlflow"

检查模型加载日志
docker-compose logs app | grep -i "model\|mlflow"
#
#=============================================================================
=============================================================================#
#3. 检查缓存状态
3. 检查缓存状态#
#=============================================================================

=============================================================================
#
#检查Redis连接
docker exec football_prediction_redis redis-cli ping

检查Redis连接
docker exec football_prediction_redis redis-cli ping
#
#检查缓存命中率
docker exec football_prediction_redis redis-cli info | grep keyspace

检查缓存命中率
docker exec football_prediction_redis redis-cli info | grep keyspace
#
#检查缓存键
docker exec football_prediction_redis redis-cli keys "model:*" | head -10

检查缓存键
docker exec football_prediction_redis redis-cli keys "model:*" | head -10
#
#=============================================================================
=============================================================================#
#4. 检查数据库连接
4. 检查数据库连接#
#=============================================================================

=============================================================================
#
#测试数据库连接
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "SELECT 1;"

测试数据库连接
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "SELECT 1;"
#
#检查数据库连接池
docker-compose logs app | grep -i "connection\|pool"

检查数据库连接池
docker-compose logs app | grep -i "connection\|pool"
#
#检查慢查询
docker-compose logs app | grep -i "slow\|query.*ms"
```

#### 🛠️ 应急解决方案

```bash
