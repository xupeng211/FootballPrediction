检查慢查询
docker-compose logs app | grep -i "slow\|query.*ms"
```

#### 🛠️ 应急解决方案

```bash#
#=============================================================================
=============================================================================#
#1. 模型重新加载
1. 模型重新加载#
#=============================================================================

cat > reload_model.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Model Reload Script ==="

=============================================================================

cat > reload_model.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Model Reload Script ==="
#
#重启MLflow服务
echo "Restarting MLflow..."
docker-compose restart mlflow

重启MLflow服务
echo "Restarting MLflow..."
docker-compose restart mlflow
#
#等待MLflow就绪
sleep 20

等待MLflow就绪
sleep 20
#
#清理应用缓存
echo "Clearing application cache..."
docker exec football_prediction_app rm -rf /tmp/model_cache/*

清理应用缓存
echo "Clearing application cache..."
docker exec football_prediction_app rm -rf /tmp/model_cache/*
#
#重启应用服务
echo "Restarting application..."
docker-compose restart app

重启应用服务
echo "Restarting application..."
docker-compose restart app
#
#等待应用启动
sleep 15

等待应用启动
sleep 15
#
#验证模型加载
echo "Verifying model loading..."
curl -f http://localhost:8000/health

echo "Model reload completed"
EOF

chmod +x reload_model.sh

验证模型加载
echo "Verifying model loading..."
curl -f http://localhost:8000/health

echo "Model reload completed"
EOF

chmod +x reload_model.sh
#
#=============================================================================
=============================================================================#
#2. 缓存重置
2. 缓存重置#
#=============================================================================

cat > reset_cache.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Cache Reset Script ==="

=============================================================================

cat > reset_cache.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Cache Reset Script ==="
#
#重启Redis服务
echo "Restarting Redis..."
docker-compose restart redis

重启Redis服务
echo "Restarting Redis..."
docker-compose restart redis
#
#等待Redis就绪
sleep 10

等待Redis就绪
sleep 10
#
#清理应用缓存连接
echo "Clearing application cache..."
docker-compose restart app

清理应用缓存连接
echo "Clearing application cache..."
docker-compose restart app
#
#验证缓存连接
echo "Verifying cache connection..."
docker exec football_prediction_redis redis-cli ping

echo "Cache reset completed"
EOF

chmod +x reset_cache.sh

验证缓存连接
echo "Verifying cache connection..."
docker exec football_prediction_redis redis-cli ping

echo "Cache reset completed"
EOF

chmod +x reset_cache.sh
#
#=============================================================================
=============================================================================#
#3. 数据库连接池重置
3. 数据库连接池重置#
#=============================================================================

cat > reset_db_pool.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Database Pool Reset Script ==="

=============================================================================

cat > reset_db_pool.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Database Pool Reset Script ==="
#
#重启数据库服务
echo "Restarting database..."
docker-compose restart db

重启数据库服务
echo "Restarting database..."
docker-compose restart db
#
#等待数据库就绪
timeout 60 bash -c 'until docker exec football_prediction_db pg_isready -U football_user; do sleep 2; done'

等待数据库就绪
timeout 60 bash -c 'until docker exec football_prediction_db pg_isready -U football_user; do sleep 2; done'
#
#重启应用服务
echo "Restarting application..."
docker-compose restart app

重启应用服务
echo "Restarting application..."
docker-compose restart app
#
#验证数据库连接
echo "Verifying database connection..."
curl -f http://localhost:8000/health

echo "Database pool reset completed"
EOF

chmod +x reset_db_pool.sh
```

验证数据库连接
echo "Verifying database connection..."
curl -f http://localhost:8000/health

echo "Database pool reset completed"
EOF

chmod +x reset_db_pool.sh
```
###
###3. 消息队列阻塞

#### 🔍 问题诊断步骤

```bash
3. 消息队列阻塞

#### 🔍 问题诊断步骤

```bash#
#=============================================================================
=============================================================================#
#1. 检查Kafka状态
1. 检查Kafka状态#
#=============================================================================

=============================================================================
#
#检查Kafka服务状态
docker-compose ps kafka

检查Kafka服务状态
docker-compose ps kafka
#
#检查Kafka日志
docker-compose logs kafka | tail -20

检查Kafka日志
docker-compose logs kafka | tail -20
#
#检查Kafka主题
docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --list

检查Kafka主题
docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --list
#
#检查主题状态
docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --describe

检查主题状态
docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --describe
#
#=============================================================================
=============================================================================#
#2. 检查Celery状态
2. 检查Celery状态#
#=============================================================================

=============================================================================
#
#检查Celery工作进程
docker-compose ps celery-worker

检查Celery工作进程
docker-compose ps celery-worker
#
#检查Celery日志
docker-compose logs celery-worker | tail -20

检查Celery日志
docker-compose logs celery-worker | tail -20
#
#检查Celery任务状态
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect active
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect scheduled
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect stats

检查Celery任务状态
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect active
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect scheduled
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect stats
#
#=============================================================================
=============================================================================#
#3. 检查消息积压
3. 检查消息积压#
#=============================================================================

=============================================================================
#
#检查队列长度
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect queued

检查队列长度
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect queued
#
#检查消费者延迟
docker-compose logs celery-worker | grep -i "delay\|latency"

检查消费者延迟
docker-compose logs celery-worker | grep -i "delay\|latency"
#
#检查ZooKeeper状态
docker exec football_prediction_zookeeper echo "ruok" | nc localhost 2181
```

#### 🛠️ 应急解决方案

```bash
检查ZooKeeper状态
docker exec football_prediction_zookeeper echo "ruok" | nc localhost 2181
```

#### 🛠️ 应急解决方案

```bash#
#=============================================================================
=============================================================================#
#1. 消息队列重置
1. 消息队列重置#
#=============================================================================

cat > reset_message_queue.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Message Queue Reset Script ==="

=============================================================================

cat > reset_message_queue.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Message Queue Reset Script ==="
#
#停止消息队列服务
echo "Stopping message queue services..."
docker-compose stop kafka zookeeper celery-worker celery-beat

停止消息队列服务
echo "Stopping message queue services..."
docker-compose stop kafka zookeeper celery-worker celery-beat
#
#清理Kafka数据
echo "Cleaning Kafka data..."
docker volume rm football_prediction_kafka_data
docker volume create football_prediction_kafka_data

清理Kafka数据
echo "Cleaning Kafka data..."
docker volume rm football_prediction_kafka_data
docker volume create football_prediction_kafka_data
#
#重启ZooKeeper
echo "Restarting ZooKeeper..."
docker-compose up -d zookeeper

重启ZooKeeper
echo "Restarting ZooKeeper..."
docker-compose up -d zookeeper
#
#等待ZooKeeper就绪
sleep 20

等待ZooKeeper就绪
sleep 20
#
#重启Kafka
echo "Restarting Kafka..."
docker-compose up -d kafka

重启Kafka
echo "Restarting Kafka..."
docker-compose up -d kafka
#
#等待Kafka就绪
timeout 60 bash -c 'until docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --list; do sleep 5; done'

等待Kafka就绪
timeout 60 bash -c 'until docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --list; do sleep 5; done'
#
#重建主题
echo "Recreating topics..."
docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --topic football-predictions --partitions 3 --replication-factor 1

重建主题
echo "Recreating topics..."
docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --topic football-predictions --partitions 3 --replication-factor 1
#
#重启Celery服务
echo "Restarting Celery services..."
docker-compose up -d celery-worker celery-beat

重启Celery服务
echo "Restarting Celery services..."
docker-compose up -d celery-worker celery-beat
#
#验证服务状态
echo "Verifying services..."
docker-compose ps celery-worker celery-beat kafka
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect stats

echo "Message queue reset completed"
EOF

chmod +x reset_message_queue.sh

验证服务状态
echo "Verifying services..."
docker-compose ps celery-worker celery-beat kafka
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect stats

echo "Message queue reset completed"
EOF

chmod +x reset_message_queue.sh
#
#=============================================================================
=============================================================================#
#2. Celery任务清理
2. Celery任务清理#
#=============================================================================

cat > clear_celery_tasks.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Celery Tasks Cleanup Script ==="

=============================================================================

cat > clear_celery_tasks.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Celery Tasks Cleanup Script ==="
#
#停止Celery工作进程
echo "Stopping Celery workers..."
docker-compose stop celery-worker celery-beat

停止Celery工作进程
echo "Stopping Celery workers..."
docker-compose stop celery-worker celery-beat
#
#清理Redis中的任务数据
echo "Clearing Redis task data..."
docker exec football_prediction_redis redis-cli flushdb

清理Redis中的任务数据
echo "Clearing Redis task data..."
docker exec football_prediction_redis redis-cli flushdb
#
#重启Celery服务
echo "Restarting Celery services..."
docker-compose up -d celery-worker celery-beat

重启Celery服务
echo "Restarting Celery services..."
docker-compose up -d celery-worker celery-beat
#
#等待服务启动
sleep 10

等待服务启动
sleep 10
#
#验证Celery状态
echo "Verifying Celery status..."
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect stats

echo "Celery tasks cleanup completed"
EOF

chmod +x clear_celery_tasks.sh
```

验证Celery状态
echo "Verifying Celery status..."
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect stats

echo "Celery tasks cleanup completed"
EOF

chmod +x clear_celery_tasks.sh
```
###
###4. 告警风暴

#### 🔍 问题诊断步骤

```bash
4. 告警风暴

#### 🔍 问题诊断步骤

```bash#
#=============================================================================
=============================================================================#
#1. 检查告警状态
1. 检查告警状态#
#=============================================================================

=============================================================================
#
#检查当前告警
curl -s http://localhost:9093/api/v1/alerts | jq '.data.alerts[] | {name, state, labels}'

检查当前告警
curl -s http://localhost:9093/api/v1/alerts | jq '.data.alerts[] | {name, state, labels}'
#
#检查告警规则状态
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | {name, health, lastError}'

检查告警规则状态
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | {name, health, lastError}'
#
#检查Prometheus目标状态
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {health, labels}'

检查Prometheus目标状态
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {health, labels}'
#
#=============================================================================
=============================================================================#
#2. 检查系统资源
2. 检查系统资源#
#=============================================================================

=============================================================================
#
#检查CPU使用率
docker stats football_prediction_app --no-stream --format '{{.CPUPerc}}'

检查CPU使用率
docker stats football_prediction_app --no-stream --format '{{.CPUPerc}}'
#
#检查内存使用率
docker stats football_prediction_app --no-stream --format '{{.MemUsage}}'

检查内存使用率
docker stats football_prediction_app --no-stream --format '{{.MemUsage}}'
#
#检查磁盘使用
df -h

检查磁盘使用
df -h
#
#检查网络连接
netstat -an | grep :8000 | wc -l

检查网络连接
netstat -an | grep :8000 | wc -l
#
#=============================================================================
=============================================================================#
#3. 检查业务指标
3. 检查业务指标#
#=============================================================================

=============================================================================
#
#检查API错误率
curl -s http://localhost:8000/metrics | grep "http_requests_total{status=\"5..\"}"

检查API错误率
curl -s http://localhost:8000/metrics | grep "http_requests_total{status=\"5..\"}"
#
#检查响应时间
curl -s http://localhost:8000/metrics | grep "football_prediction_latency_seconds"

检查响应时间
curl -s http://localhost:8000/metrics | grep "football_prediction_latency_seconds"
#
#检查数据库连接数
curl -s http://localhost:9187/metrics | grep "pg_stat_database_numbackends"
```

#### 🛠️ 应急解决方案

```bash
检查数据库连接数
curl -s http://localhost:9187/metrics | grep "pg_stat_database_numbackends"
```

#### 🛠️ 应急解决方案

```bash#
#=============================================================================
=============================================================================#
#1. 告警静默脚本
1. 告警静默脚本#
#=============================================================================

cat > silence_alerts.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Alert Silence Script ==="

=============================================================================

cat > silence_alerts.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Alert Silence Script ==="
#
#静默所有告警
curl -X POST http://localhost:9093/api/v1/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {
        "name": "severity",
        "value": ".*",
        "isRegex": true
      }
    ],
    "startsAt": "'$(date -Iseconds)'",
    "endsAt": "'$(date -d '+1 hour' -Iseconds)'",
    "comment": "Emergency silence during incident",
    "createdBy": "emergency_script"
  }'

echo "All alerts silenced for 1 hour"
EOF

chmod +x silence_alerts.sh

静默所有告警
curl -X POST http://localhost:9093/api/v1/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {
        "name": "severity",
        "value": ".*",
        "isRegex": true
      }
    ],
    "startsAt": "'$(date -Iseconds)'",
    "endsAt": "'$(date -d '+1 hour' -Iseconds)'",
    "comment": "Emergency silence during incident",
    "createdBy": "emergency_script"
  }'

echo "All alerts silenced for 1 hour"
EOF

chmod +x silence_alerts.sh
#
#=============================================================================
=============================================================================#
#2. 告警阈值调整
2. 告警阈值调整#
#=============================================================================

cat > adjust_alert_thresholds.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Alert Threshold Adjustment Script ==="

=============================================================================

cat > adjust_alert_thresholds.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Alert Threshold Adjustment Script ==="
#
#备份当前告警规则
cp configs/prometheus/alert_rules.yml configs/prometheus/alert_rules.yml.backup_$(date +%Y%m%d_%H%M%S)

备份当前告警规则
cp configs/prometheus/alert_rules.yml configs/prometheus/alert_rules.yml.backup_$(date +%Y%m%d_%H%M%S)
#
#调整告警阈值（提高阈值以减少告警）
sed -i 's/> 0.01/> 0.05/g' configs/prometheus/alert_rules.yml
sed -i 's/> 1/> 5/g' configs/prometheus/alert_rules.yml
sed -i 's/> 80/> 90/g' configs/prometheus/alert_rules.yml
sed -i 's/> 90/> 95/g' configs/prometheus/alert_rules.yml

调整告警阈值（提高阈值以减少告警）
sed -i 's/> 0.01/> 0.05/g' configs/prometheus/alert_rules.yml
sed -i 's/> 1/> 5/g' configs/prometheus/alert_rules.yml
sed -i 's/> 80/> 90/g' configs/prometheus/alert_rules.yml
sed -i 's/> 90/> 95/g' configs/prometheus/alert_rules.yml
#
#重新加载Prometheus配置
curl -X POST http://localhost:9090/-/reload

echo "Alert thresholds adjusted and Prometheus reloaded"
EOF

chmod +x adjust_alert_thresholds.sh

重新加载Prometheus配置
curl -X POST http://localhost:9090/-/reload

echo "Alert thresholds adjusted and Prometheus reloaded"
EOF

chmod +x adjust_alert_thresholds.sh
#
#=============================================================================
=============================================================================#
#3. 系统资源优化
3. 系统资源优化#
#=============================================================================

cat > optimize_resources.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Resource Optimization Script ==="

=============================================================================

cat > optimize_resources.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Resource Optimization Script ==="
#
#重启高内存使用服务
echo "Restarting high-memory services..."
docker-compose restart app celery-worker

重启高内存使用服务
echo "Restarting high-memory services..."
docker-compose restart app celery-worker
#
#清理Docker资源
echo "Cleaning Docker resources..."
docker system prune -f
docker volume prune -f

清理Docker资源
echo "Cleaning Docker resources..."
docker system prune -f
docker volume prune -f
#
#优化数据库连接池
echo "Optimizing database connection pool..."
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();
"

优化数据库连接池
echo "Optimizing database connection pool..."
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();
"
#
#重启数据库
echo "Restarting database..."
docker-compose restart db

echo "Resource optimization completed"
EOF

chmod +x optimize_resources.sh
```

---

重启数据库
echo "Restarting database..."
docker-compose restart db

echo "Resource optimization completed"
EOF

chmod +x optimize_resources.sh
```

---
##
##📋 附录

📋 附录
###
###A. 部署命令示例

#### 🐳 Docker Compose 部署命令

```bash
A. 部署命令示例

#### 🐳 Docker Compose 部署命令

```bash#
#=============================================================================
=============================================================================#
#基础部署命令
基础部署命令#
#=============================================================================

=============================================================================
#
#完整部署
docker-compose up -d

完整部署
docker-compose up -d
#
#分步部署
docker-compose up -d db redis
docker-compose up -d zookeeper kafka
docker-compose up -d minio mlflow
docker-compose up -d prometheus grafana
docker-compose up -d app celery-worker celery-beat
docker-compose up -d nginx

分步部署
docker-compose up -d db redis
docker-compose up -d zookeeper kafka
docker-compose up -d minio mlflow
docker-compose up -d prometheus grafana
docker-compose up -d app celery-worker celery-beat
docker-compose up -d nginx
#
#特定服务部署
docker-compose up -d app
docker-compose up -d db
docker-compose up -d redis

特定服务部署
docker-compose up -d app
docker-compose up -d db
docker-compose up -d redis
#
#=============================================================================
=============================================================================#
#服务管理命令
服务管理命令#
#=============================================================================

=============================================================================
#
#启动服务
docker-compose up -d

启动服务
docker-compose up -d
#
#停止服务
docker-compose down

停止服务
docker-compose down
#
#重启服务
docker-compose restart app

重启服务
docker-compose restart app
#
#查看日志
docker-compose logs -f app

查看日志
docker-compose logs -f app
#
#查看服务状态
docker-compose ps

查看服务状态
docker-compose ps
#
#=============================================================================
=============================================================================#
#清理命令
清理命令#
#=============================================================================

=============================================================================
#
#停止并删除容器
docker-compose down

停止并删除容器
docker-compose down
#
#停止并删除容器和网络
docker-compose down --rmi all

停止并删除容器和网络
docker-compose down --rmi all
#
#停止并删除容器、网络、卷
docker-compose down -v

停止并删除容器、网络、卷
docker-compose down -v
#
#清理未使用的资源
docker system prune -a
docker volume prune
```

#### ☸️ Kubernetes 部署命令

```bash
清理未使用的资源
docker system prune -a
docker volume prune
```

#### ☸️ Kubernetes 部署命令

```bash#
#=============================================================================
=============================================================================#
#基础部署命令
基础部署命令#
#=============================================================================

=============================================================================
#
#应用所有配置
kubectl apply -f k8s/

应用所有配置
kubectl apply -f k8s/
#
#分步应用
kubectl apply -f k8s/storage/
kubectl apply -f k8s/database/
kubectl apply -f k8s/cache/
kubectl apply -f k8s/messaging/
kubectl apply -f k8s/ml/
kubectl apply -f k8s/monitoring/
kubectl apply -f k8s/app/
kubectl apply -f k8s/ingress/

分步应用
kubectl apply -f k8s/storage/
kubectl apply -f k8s/database/
kubectl apply -f k8s/cache/
kubectl apply -f k8s/messaging/
kubectl apply -f k8s/ml/
kubectl apply -f k8s/monitoring/
kubectl apply -f k8s/app/
kubectl apply -f k8s/ingress/
#
#=============================================================================
=============================================================================#
#服务管理命令
服务管理命令#
#=============================================================================

=============================================================================
#
#查看Pod状态
kubectl get pods -o wide

查看Pod状态
kubectl get pods -o wide
#
#查看服务状态
kubectl get services

查看服务状态
kubectl get services
#
#查看Ingress状态
kubectl get ingress

查看Ingress状态
kubectl get ingress
#
#查看部署状态
kubectl get deployments

查看部署状态
kubectl get deployments
#
#=============================================================================
=============================================================================#
#故障排查命令
故障排查命令#
#=============================================================================

=============================================================================
#
#查看Pod日志
kubectl logs -f deployment/football-prediction

查看Pod日志
kubectl logs -f deployment/football-prediction
#
#查看特定Pod日志
kubectl logs -f <pod-name>

查看特定Pod日志
kubectl logs -f <pod-name>
#
#进入Pod调试
kubectl exec -it <pod-name> -- /bin/bash

进入Pod调试
kubectl exec -it <pod-name> -- /bin/bash
#
#描述Pod详细信息
kubectl describe pod <pod-name>

描述Pod详细信息
kubectl describe pod <pod-name>
#
#=============================================================================
=============================================================================#
#扩缩容命令
扩缩容命令#
#=============================================================================

=============================================================================
#
#扩容应用
kubectl scale deployment football-prediction --replicas=3

扩容应用
kubectl scale deployment football-prediction --replicas=3
#
#扩容工作节点
kubectl scale deployment celery-worker --replicas=2

扩容工作节点
kubectl scale deployment celery-worker --replicas=2
#
#=============================================================================
=============================================================================#
#更新命令
更新命令#
#=============================================================================

=============================================================================
#
#滚动更新
kubectl rollout restart deployment football-prediction

滚动更新
kubectl rollout restart deployment football-prediction
#
#回滚到上一个版本
kubectl rollout undo deployment football-prediction

回滚到上一个版本
kubectl rollout undo deployment football-prediction
#
#查看更新状态
kubectl rollout status deployment football-prediction
```

查看更新状态
kubectl rollout status deployment football-prediction
```
###
###B. 常用运维命令

#### 📊 日志和状态命令

```bash
B. 常用运维命令

#### 📊 日志和状态命令

```bash#
#=============================================================================
=============================================================================#
#应用日志
应用日志#
#=============================================================================

=============================================================================
#
#实时查看应用日志
docker-compose logs -f app

实时查看应用日志
docker-compose logs -f app
#
#查看最近的100行日志
docker-compose logs --tail=100 app

查看最近的100行日志
docker-compose logs --tail=100 app
#
#查看特定时间段的日志
docker-compose logs --since=1h app

查看特定时间段的日志
docker-compose logs --since=1h app
#
#查看错误日志
docker-compose logs app | grep ERROR

查看错误日志
docker-compose logs app | grep ERROR
#
#=============================================================================
=============================================================================#
#系统状态
系统状态#
#=============================================================================

=============================================================================
#
#查看所有容器状态
docker ps -a

查看所有容器状态
docker ps -a
#
#查看资源使用情况
docker stats

查看资源使用情况
docker stats
#
#查看网络状态
docker network ls
docker network inspect football-network

查看网络状态
docker network ls
docker network inspect football-network
#
#查看卷状态
docker volume ls
docker volume inspect football_prediction_db_data

查看卷状态
docker volume ls
docker volume inspect football_prediction_db_data
#
#=============================================================================
=============================================================================#
#数据库操作
数据库操作#
#=============================================================================

=============================================================================
#
#连接到数据库
docker exec -it football_prediction_db psql -U football_user -d football_prediction_dev

连接到数据库
docker exec -it football_prediction_db psql -U football_user -d football_prediction_dev
#
#数据库备份
docker exec football_prediction_db pg_dump -U football_user -d football_prediction_dev > backup.sql

数据库备份
docker exec football_prediction_db pg_dump -U football_user -d football_prediction_dev > backup.sql
#
#数据库恢复
docker exec -i football_prediction_db psql -U football_user -d football_prediction_dev < backup.sql

数据库恢复
docker exec -i football_prediction_db psql -U football_user -d football_prediction_dev < backup.sql
#
#=============================================================================
