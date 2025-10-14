# 运维手册

## 目录

1. [日常运维](#日常运维)
2. [监控管理](#监控管理)
3. [日志管理](#日志管理)
4. [备份管理](#备份管理)
5. [性能优化](#性能优化)
6. [安全管理](#安全管理)
7. [故障处理](#故障处理)
8. [维护计划](#维护计划)

## 日常运维

### 每日检查清单

#### 系统健康检查

```bash
#!/bin/bash
# daily_health_check.sh

echo "=== 系统健康检查 $(date) ==="

# 1. 检查服务状态
echo "1. 检查服务状态..."
docker-compose ps

# 2. 检查磁盘空间
echo "2. 检查磁盘空间..."
df -h

# 3. 检查内存使用
echo "3. 检查内存使用..."
free -h

# 4. 检查负载
echo "4. 检查系统负载..."
uptime

# 5. 检查网络连接
echo "5. 检查网络连接..."
netstat -tuln | grep LISTEN

# 6. 检查日志错误
echo "6. 检查错误日志..."
tail -n 100 logs/api/*.log | grep ERROR

# 7. 检查备份
echo "7. 检查备份状态..."
ls -la backups/database/ | grep "$(date +%Y%m%d)"

echo "=== 检查完成 ==="
```

#### 应用健康检查

```bash
# API健康检查
curl -f http://localhost:8000/api/health || echo "API服务异常"

# 数据库连接检查
docker-compose exec -T api python -c "
import asyncio
from src.database.base import get_db_session
asyncio.run(get_db_session())
echo '数据库连接正常'
"

# Redis连接检查
redis-cli -a $REDIS_PASSWORD ping || echo "Redis连接异常"
```

### 每周维护任务

#### 1. 日志清理

```bash
#!/bin/bash
# weekly_cleanup.sh

# 清理应用日志（保留7天）
find logs/ -name "*.log" -mtime +7 -delete

# 清理Docker日志
docker system prune -f

# 清理临时文件
find /tmp -name "football_*" -mtime +1 -delete

# 清理Nginx日志
sudo logrotate -f /etc/logrotate.d/nginx
```

#### 2. 性能分析

```bash
# 分析数据库性能
python scripts/analyze-db-performance.py

# 分析API性能
python scripts/analyze-api-performance.py

# 生成性能报告
python scripts/generate-performance-report.py
```

#### 3. 安全检查

```bash
#!/bin/bash
# security_check.sh

# 检查系统更新
sudo apt list --upgradable

# 检查开放端口
nmap -sT -O localhost

# 检查失败的登录尝试
sudo grep "Failed password" /var/log/auth.log | tail -20

# 检查SSL证书有效期
openssl x509 -in config/ssl/server.crt -noout -dates
```

### 每月维护任务

#### 1. 系统更新

```bash
#!/bin/bash
# monthly_update.sh

# 更新系统包
sudo apt update && sudo apt upgrade -y

# 更新Docker镜像
docker-compose pull

# 重启服务（如需要）
docker-compose up -d
```

#### 2. 容量规划

```bash
# 检查存储趋势
df -h | grep -E "(Filesystem|/dev/)"

# 检查数据库增长
docker-compose exec postgres psql -U postgres -d football_prediction -c "
SELECT pg_size_pretty(pg_database_size('football_prediction'));
"

# 检查用户增长
docker-compose exec api python -c "
from src.database.repositories.user import UserRepository
repo = UserRepository()
count = asyncio.run(repo.count())
print(f'用户数: {count}')
"
```

## 监控管理

### Prometheus监控

#### 查询常用指标

```bash
# 查看API请求率
curl -G "http://localhost:9090/api/v1/query" \
  --data-urlencode 'query=rate(http_requests_total[5m])'

# 查看API响应时间
curl -G "http://localhost:9090/api/v1/query" \
  --data-urlencode 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))'

# 查看错误率
curl -G "http://localhost:9090/api/v1/query" \
  --data-urlencode 'query=rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])'

# 查看数据库连接数
curl -G "http://localhost:9090/api/v1/query" \
  --data-urlencode 'query=pg_stat_database_numbackends'
```

#### 添加自定义监控指标

```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active database connections')

# 使用示例
@REQUEST_DURATION.time()
def handle_request():
    REQUEST_COUNT.labels(method='GET', endpoint='/api/health', status='200').inc()
    return "OK"
```

### Grafana仪表板

#### 导入预配置仪表板

```bash
# 使用Grafana API导入仪表板
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @monitoring/grafana/dashboards/football-prediction-overview.json
```

#### 自定义告警规则

```yaml
# monitoring/prometheus/rules/custom-alerts.yml
groups:
  - name: custom-alerts
    rules:
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is above 90% for more than 5 minutes"
```

### 日志管理

### Loki日志查询

```bash
# 查询最近的错误日志
curl -G "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={level="ERROR"}' \
  --data-urlencode 'start=2024-03-15T00:00:00Z' \
  --data-urlencode 'end=2024-03-15T23:59:59Z'

# 查询特定服务的日志
curl -G "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="football-prediction"}' \
  --data-urlencode 'limit=100'
```

### 日志分析脚本

```python
# scripts/analyze_logs.py
import json
import re
from collections import defaultdict
from datetime import datetime

def analyze_api_logs(log_file):
    """分析API访问日志"""
    stats = {
        'total_requests': 0,
        'error_count': 0,
        'slow_requests': 0,
        'endpoints': defaultdict(int),
        'status_codes': defaultdict(int)
    }

    with open(log_file) as f:
        for line in f:
            try:
                log_entry = json.loads(line)

                stats['total_requests'] += 1

                # 统计端点
                endpoint = log_entry.get('path', 'unknown')
                stats['endpoints'][endpoint] += 1

                # 统计状态码
                status = log_entry.get('status_code', 0)
                stats['status_codes'][status] += 1

                # 统计错误
                if status >= 400:
                    stats['error_count'] += 1

                # 统计慢请求
                duration = log_entry.get('duration', 0)
                if duration > 1.0:
                    stats['slow_requests'] += 1

            except json.JSONDecodeError:
                continue

    return stats

if __name__ == "__main__":
    stats = analyze_api_logs("logs/api/app.log")
    print(json.dumps(stats, indent=2))
```

## 备份管理

### 备份脚本执行

```bash
# 执行数据库备份
python scripts/backup-database.py backup --type full --compress --encrypt

# 查看备份列表
python scripts/backup-database.py list

# 验证备份
python scripts/backup-database.py verify --file backups/database/full_20240315_020000.sql

# 恢复测试（在测试环境）
python scripts/backup-database.py restore --file backups/database/full_20240315_020000.sql --test
```

### 自动备份配置

```bash
# 添加到crontab
crontab -e

# 每天凌晨2点全量备份
0 2 * * * cd /opt/football-prediction && python scripts/backup-database.py backup --type full --compress --encrypt

# 每6小时增量备份
0 */6 * * * cd /opt/football-prediction && python scripts/backup-database.py backup --type incremental

# 每周日凌晨3点清理旧备份
0 3 * * 0 cd /opt/football-prediction && python scripts/backup-database.py cleanup
```

### 备份验证

```bash
#!/bin/bash
# verify_backups.sh

# 验证最近的备份
LATEST_BACKUP=$(ls -t backups/database/*.sql | head -1)

echo "验证备份: $LATEST_BACKUP"

# 1. 检查文件大小
if [ $(stat -c%s "$LATEST_BACKUP") -lt 1000000 ]; then
    echo "警告: 备份文件过小"
fi

# 2. 验证备份完整性
python scripts/backup-database.py verify --file "$LATEST_BACKUP"

# 3. 测试恢复（到测试数据库）
echo "测试恢复到测试数据库..."
TEST_DB="football_prediction_test"
createdb $TEST_DB
pg_restore -d $TEST_DB "$LATEST_BACKUP"
dropdb $TEST_DB

echo "备份验证完成"
```

## 性能优化

### 数据库优化

```bash
# 运行数据库优化
python scripts/optimize-database.py

# 更新表统计信息
docker-compose exec postgres psql -U postgres -d football_prediction -c "ANALYZE;"

# 重建索引
docker-compose exec postgres psql -U postgres -d football_prediction -c "REINDEX DATABASE football_prediction;"

# 查看慢查询
docker-compose exec postgres psql -U postgres -d football_prediction -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"
```

### Redis优化

```bash
# 监控Redis性能
redis-cli -a $REDIS_PASSWORD info stats

# 查看内存使用
redis-cli -a $REDIS_PASSWORD info memory

# 清理过期键
redis-cli -a $REDIS_PASSWORD --scan --pattern "*:EXPIRED*" | xargs redis-cli -a $REDIS_PASSWORD del

# 优化内存使用
python scripts/optimize-redis.py
```

### API性能优化

```bash
# 运行性能测试
./scripts/run-performance-tests.sh basic

# 分析慢端点
python scripts/analyze-slow-endpoints.py

# 优化缓存配置
python scripts/optimize-cache.py
```

## 安全管理

### 证书管理

```bash
# 检查证书有效期
openssl x509 -in config/ssl/server.crt -noout -dates

# 自动续期Let's Encrypt证书
echo "0 2 1 * * certbot renew --quiet" | sudo crontab -

# 生成新证书
openssl req -x509 -newkey rsa:4096 -keyout config/ssl/server.key -out config/ssl/server.crt -days 365 -nodes
```

### 密钥轮换

```bash
#!/bin/bash
# rotate_secrets.sh

# 生成新的JWT密钥
NEW_JWT_SECRET=$(openssl rand -base64 32)
echo "JWT_SECRET_KEY=$NEW_JWT_SECRET" >> .env.new

# 生成新的数据库密码
NEW_DB_PASSWORD=$(openssl rand -base64 16)
echo "DB_PASSWORD=$NEW_DB_PASSWORD" >> .env.new

# 更新应用配置
docker-compose down
mv .env .env.old
mv .env.new .env
docker-compose up -d

# 更新数据库密码
docker-compose exec postgres psql -U postgres -c "ALTER USER postgres PASSWORD '$NEW_DB_PASSWORD';"
```

### 安全审计

```bash
#!/bin/bash
# security_audit.sh

# 1. 检查开放端口
echo "=== 开放端口 ==="
nmap -sT -O localhost

# 2. 检查用户权限
echo "=== 用户权限 ==="
sudo -l

# 3. 检查文件权限
echo "=== 敏感文件权限 ==="
ls -la config/ssl/
ls -la .env*

# 4. 检查Docker安全配置
echo "=== Docker安全 ==="
docker system info | grep -i security
```

## 故障处理

### 常见故障处理流程

#### 1. API服务无响应

```bash
# 检查服务状态
docker-compose ps api

# 查看日志
docker-compose logs api

# 重启服务
docker-compose restart api

# 检查端口占用
netstat -tulpn | grep 8000

# 检查系统资源
top
```

#### 2. 数据库连接失败

```bash
# 检查数据库状态
docker-compose exec postgres pg_isready

# 查看连接数
docker-compose exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# 检查慢查询
docker-compose exec postgres psql -U postgres -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
"

# 终止长时间运行的查询
docker-compose exec postgres psql -U postgres -c "SELECT pg_terminate_backend(pid);"
```

#### 3. Redis连接失败

```bash
# 检查Redis状态
redis-cli -a $REDIS_PASSWORD ping

# 查看Redis日志
docker-compose logs redis

# 检查内存使用
redis-cli -a $REDIS_PASSWORD info memory

# 清理Redis
redis-cli -a $REDIS_PASSWORD flushdb
```

#### 4. 高CPU使用率

```bash
# 查看CPU使用情况
top -p $(pgrep -f "football-prediction")

# 查看进程详情
ps aux | grep football

# 分析CPU热点
perf top -p $(pgrep -f "uvicorn")

# 重启服务
docker-compose restart api
```

### 故障恢复脚本

```bash
#!/bin/bash
# emergency_recovery.sh

echo "=== 紧急故障恢复程序 ==="

# 1. 停止所有服务
echo "停止服务..."
docker-compose down

# 2. 备份当前状态
echo "备份当前状态..."
mkdir -p emergency_backup/$(date +%Y%m%d_%H%M%S)
cp -r logs/ emergency_backup/$(date +%Y%m%d_%H%M%S)/
docker-compose logs --no-color > emergency_backup/$(date +%Y%m%d_%H%M%S)/docker_logs.log

# 3. 恢复到最后已知良好状态
echo "恢复服务..."
docker-compose up -d

# 4. 等待服务启动
sleep 30

# 5. 健康检查
echo "健康检查..."
if curl -f http://localhost:8000/api/health; then
    echo "✓ 服务恢复成功"
else
    echo "✗ 服务恢复失败，需要人工干预"
    exit 1
fi

echo "=== 恢复完成 ==="
```

## 维护计划

### 维护窗口管理

```bash
#!/bin/bash
# maintenance_mode.sh

# 启用维护模式
enable_maintenance() {
    echo "启用维护模式..."

    # 1. 更新Nginx配置返回503
    sudo cp config/nginx/maintenance.conf /etc/nginx/sites-available/football-prediction
    sudo nginx -s reload

    # 2. 停止应用服务（保留数据库和缓存）
    docker-compose stop api celery-worker celery-beat

    # 3. 通知用户
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🔧 系统维护中，预计30分钟"}' \
        $SLACK_WEBHOOK
}

# 禁用维护模式
disable_maintenance() {
    echo "禁用维护模式..."

    # 1. 启动应用服务
    docker-compose start api celery-worker celery-beat

    # 2. 恢复Nginx配置
    sudo cp config/nginx/nginx.conf /etc/nginx/sites-available/football-prediction
    sudo nginx -s reload

    # 3. 等待服务就绪
    sleep 10

    # 4. 健康检查
    if curl -f http://localhost:8000/api/health; then
        curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"✅ 系统维护完成"}' \
            $SLACK_WEBHOOK
    fi
}

case "$1" in
    enable)
        enable_maintenance
        ;;
    disable)
        disable_maintenance
        ;;
    *)
        echo "Usage: $0 {enable|disable}"
        exit 1
        ;;
esac
```

### 定期维护任务

```yaml
# .github/workflows/maintenance.yml
name: Scheduled Maintenance

on:
  schedule:
    - cron: '0 3 * * 0'  # 每周日凌晨3点
  workflow_dispatch:

jobs:
  maintenance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run maintenance tasks
        run: |
          # 系统清理
          docker system prune -f

          # 日志轮转
          ./scripts/rotate-logs.sh

          # 备份验证
          ./scripts/verify-backups.sh

          # 性能报告
          ./scripts/generate-performance-report.py
```

---

**更新时间**: 2024-03-15
**版本**: 1.0.0
**维护者**: Football Prediction DevOps Team
