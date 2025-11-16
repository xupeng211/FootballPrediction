# 📚 FootballPrediction 运维手册

本文档提供生产环境的日常运维、监控和故障处理指南。

---

## 🎯 运维目标

### 核心指标
- **可用性**: 99.9%+
- **响应时间**: <200ms (P95)
- **错误率**: <0.1%
- **数据一致性**: 100%

### 服务等级协议 (SLA)
- **关键功能**: 99.9%可用性
- **API响应**: <200ms (95%请求)
- **故障恢复**: <5分钟
- **数据备份**: 每日备份

---

## 📊 监控体系

### 关键监控指标

#### 应用层监控
```bash
# API响应时间监控
curl -w "@curl-format.txt" https://api.footballprediction.com/health

# 错误率监控
tail -f /var/log/nginx/access.log | grep -E " (4[0-9]{2}|5[0-9]{2}) "

# 请求量监控
tail -f /var/log/nginx/access.log | wc -l
```

#### 系统层监控
```bash
# CPU使用率
top -b -n 1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1

# 内存使用率
free | grep Mem | awk '{printf("%.2f%%"), $3/$2 * 100.0}'

# 磁盘使用率
df -h | grep -vE '^Filesystem|tmpfs|cdrom' | awk '{print $5 " " $1}'

# 网络连接数
netstat -an | grep :8000 | wc -l
```

#### 数据库监控
```bash
# 数据库连接数
docker exec footballprediction-db psql -U fp_user -d footballprediction_prod -c "SELECT count(*) FROM pg_stat_activity;"

# 数据库大小
docker exec footballprediction-db psql -U fp_user -d footballprediction_prod -c "SELECT pg_size_pretty(pg_database_size('footballprediction_prod'));"

# 慢查询
docker exec footballprediction-db psql -U fp_user -d footballprediction_prod -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

### 监控工具配置

#### Prometheus配置
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'footballprediction'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['localhost:9187']

  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['localhost:9121']
```

#### Grafana仪表板
- **应用性能**: API响应时间、错误率、请求量
- **系统资源**: CPU、内存、磁盘、网络
- **数据库**: 连接数、查询性能、锁等待
- **缓存**: Redis命中率、内存使用

---

## 🚨 告警配置

### 关键告警规则

#### 应用告警
```yaml
# 应用不可用
- alert: ApplicationDown
  expr: up{job="footballprediction"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "FootballPrediction应用不可用"

# 响应时间过长
- alert: HighResponseTime
  expr: http_request_duration_seconds{quantile="0.95"} > 0.5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "API响应时间超过500ms"

# 错误率过高
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "API错误率超过1%"
```

#### 系统告警
```yaml
# CPU使用率过高
- alert: HighCPUUsage
  expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "CPU使用率超过80%"

# 内存使用率过高
- alert: HighMemoryUsage
  expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "内存使用率超过85%"

# 磁盘空间不足
- alert: LowDiskSpace
  expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 10
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "磁盘空间不足10%"
```

### 告警通知配置
```yaml
# AlertManager配置
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@footballprediction.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  email_configs:
  - to: 'ops@footballprediction.com'
    subject: '[FootballPrediction Alert] {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      告警: {{ .Annotations.summary }}
      详情: {{ .Annotations.description }}
      时间: {{ .StartsAt }}
      {{ end }}
```

---

## 🔧 日常维护

### 每日检查清单

#### 系统健康检查
```bash
#!/bin/bash
# daily_health_check.sh

echo "🔍 执行每日健康检查..."

# 1. 检查应用状态
echo "1. 检查应用状态..."
curl -f https://api.footballprediction.com/health || {
    echo "❌ 应用健康检查失败"
    exit 1
}

# 2. 检查API响应时间
echo "2. 检查API响应时间..."
RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' https://api.footballprediction.com/health)
if (( $(echo "$RESPONSE_TIME > 0.2" | bc -l) )); then
    echo "⚠️ API响应时间过长: ${RESPONSE_TIME}s"
else
    echo "✅ API响应时间正常: ${RESPONSE_TIME}s"
fi

# 3. 检查数据库连接
echo "3. 检查数据库连接..."
docker exec footballprediction-db pg_isready -U fp_user || {
    echo "❌ 数据库连接失败"
    exit 1
}

# 4. 检查Redis连接
echo "4. 检查Redis连接..."
docker exec footballprediction-redis redis-cli ping || {
    echo "❌ Redis连接失败"
    exit 1
}

# 5. 检查磁盘空间
echo "5. 检查磁盘空间..."
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "⚠️ 磁盘使用率过高: ${DISK_USAGE}%"
else
    echo "✅ 磁盘使用率正常: ${DISK_USAGE}%"
fi

echo "✅ 每日健康检查完成"
```

#### 日志检查
```bash
#!/bin/bash
# check_logs.sh

echo "📋 检查错误日志..."

# 检查Nginx错误日志
NGINX_ERRORS=$(tail -100 /var/log/nginx/error.log | grep -E "(error|crit)" | wc -l)
if [ $NGINX_ERRORS -gt 0 ]; then
    echo "⚠️ 发现 $NGINX_ERRORS 个Nginx错误"
    tail -10 /var/log/nginx/error.log
fi

# 检查应用错误日志
APP_ERRORS=$(docker-compose -f docker-compose.prod.yml logs --tail=100 app | grep -E "(ERROR|CRITICAL)" | wc -l)
if [ $APP_ERRORS -gt 0 ]; then
    echo "⚠️ 发现 $APP_ERRORS 个应用错误"
    docker-compose -f docker-compose.prod.yml logs --tail=10 app | grep -E "(ERROR|CRITICAL)"
fi

echo "✅ 日志检查完成"
```

### 每周维护任务

#### 数据库维护
```bash
#!/bin/bash
# weekly_db_maintenance.sh

echo "🗄️ 执行数据库维护..."

# 1. 数据库备份
echo "1. 创建数据库备份..."
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
docker exec footballprediction-db pg_dump -U fp_user footballprediction_prod > "/backups/$BACKUP_FILE"

# 2. 数据库优化
echo "2. 优化数据库..."
docker exec footballprediction-db psql -U fp_user -d footballprediction_prod -c "VACUUM ANALYZE;"

# 3. 更新统计信息
echo "3. 更新统计信息..."
docker exec footballprediction-db psql -U fp_user -d footballprediction_prod -c "ANALYZE;"

# 4. 清理旧备份（保留7天）
echo "4. 清理旧备份..."
find /backups -name "backup_*.sql" -mtime +7 -delete

echo "✅ 数据库维护完成"
```

#### 系统更新
```bash
#!/bin/bash
# weekly_system_update.sh

echo "🔄 执行系统更新..."

# 1. 更新系统包
sudo apt update && sudo apt upgrade -y

# 2. 更新Docker
sudo apt-get install docker-ce docker-ce-cli containerd.io -y

# 3. 清理未使用的Docker镜像
docker system prune -f

# 4. 重启必要的服务
docker-compose -f docker-compose.prod.yml restart

echo "✅ 系统更新完成"
```

---

## 🚨 故障处理

### 故障分级

#### P0 - 关键故障
- **影响**: 服务完全不可用
- **响应时间**: 5分钟内
- **解决时间**: 30分钟内
- **通知**: 立即通知所有相关人员

#### P1 - 高优先级故障
- **影响**: 核心功能不可用
- **响应时间**: 15分钟内
- **解决时间**: 2小时内
- **通知**: 立即通知技术负责人

#### P2 - 中优先级故障
- **影响**: 部分功能受影响
- **响应时间**: 1小时内
- **解决时间**: 8小时内
- **通知**: 下一工作日处理

#### P3 - 低优先级故障
- **影响**: 非核心功能问题
- **响应时间**: 1个工作日内
- **解决时间**: 5个工作日内

### 常见故障处理流程

#### 应用服务不可用
```bash
# 1. 快速诊断
#!/bin/bash
echo "🚨 应用服务不可用 - 快速诊断"

# 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 检查应用日志
docker-compose -f docker-compose.prod.yml logs --tail=50 app

# 检查端口监听
netstat -tlnp | grep :8000

# 检查进程
ps aux | grep footballprediction

# 2. 常见解决方案
# 重启应用
docker-compose -f docker-compose.prod.yml restart app

# 重建容器
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# 回滚到上一版本
./scripts/emergency_rollback.sh
```

#### 数据库连接问题
```bash
# 数据库故障诊断
#!/bin/bash
echo "🗄️ 数据库连接问题诊断"

# 检查数据库服务
docker-compose -f docker-compose.prod.yml ps db

# 测试数据库连接
docker exec footballprediction-db pg_isready -U fp_user

# 检查数据库日志
docker-compose -f docker-compose.prod.yml logs --tail=50 db

# 检查连接数
docker exec footballprediction-db psql -U fp_user -d footballprediction_prod -c "SELECT count(*) FROM pg_stat_activity;"

# 解决方案
# 重启数据库
docker-compose -f docker-compose.prod.yml restart db

# 扩展连接池
# 修改数据库配置文件
```

#### 高负载处理
```bash
# 高负载处理脚本
#!/bin/bash
echo "📈 处理高负载情况"

# 1. 快速扩展
# 增加应用实例
docker-compose -f docker-compose.prod.yml up -d --scale app=3

# 2. 诊断负载原因
# 检查CPU使用
top -b -n 1 | head -10

# 检查内存使用
free -h

# 检查网络连接
netstat -an | grep :8000 | wc -l

# 3. 优化措施
# 清理缓存
docker-compose -f docker-compose.prod.yml exec app python -c "
from src.cache.redis_client import redis_client
redis_client.flushdb()
print('✅ 缓存已清理')
"

# 重启服务
docker-compose -f docker-compose.prod.yml restart
```

### 紧急响应流程

#### 1. 故障发现和评估
```bash
# 故障检测脚本
#!/bin/bash
# detect_issues.sh

ISSUES_FOUND=false

# 检查应用可用性
if ! curl -f https://api.footballprediction.com/health > /dev/null 2>&1; then
    echo "🚨 P0: 应用服务不可用"
    ISSUES_FOUND=true
fi

# 检查响应时间
RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' https://api.footballprediction.com/health)
if (( $(echo "$RESPONSE_TIME > 1.0" | bc -l) )); then
    echo "⚠️ P1: API响应时间过长: ${RESPONSE_TIME}s"
    ISSUES_FOUND=true
fi

# 检查错误率
ERROR_RATE=$(tail -1000 /var/log/nginx/access.log | awk '{print $9}' | grep -E "^[45][0-9]{2}" | wc -l)
if [ $ERROR_RATE -gt 10 ]; then
    echo "⚠️ P1: 错误率过高: $ERROR_RATE/1000"
    ISSUES_FOUND=true
fi

if [ "$ISSUES_FOUND" = true ]; then
    # 发送告警
    curl -X POST "https://api.slack.com/webhooks/..." \
      -H 'Content-type: application/json' \
      --data '{"text":"🚨 FootballPrediction服务异常，请立即处理！"}'
fi
```

#### 2. 快速恢复
```bash
# 快速恢复脚本
#!/bin/bash
# quick_recovery.sh

echo "🚀 执行快速恢复..."

# 1. 重启所有服务
docker-compose -f docker-compose.prod.yml restart

# 2. 检查服务状态
sleep 10
docker-compose -f docker-compose.prod.yml ps

# 3. 验证服务可用性
if curl -f https://api.footballprediction.com/health > /dev/null 2>&1; then
    echo "✅ 服务已恢复"
else
    echo "❌ 服务仍未恢复，需要手动介入"
    # 通知团队
    curl -X POST "https://api.slack.com/webhooks/..." \
      -H 'Content-type: application/json' \
      --data '{"text":"🚨 快速恢复失败，需要立即手动介入！"}'
fi
```

---

## 📊 性能优化

### 应用层优化

#### 数据库优化
```sql
-- 优化数据库配置
-- postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

-- 创建必要的索引
CREATE INDEX CONCURRENTLY idx_matches_date ON matches(date);
CREATE INDEX CONCURRENTLY idx_predictions_created_at ON predictions(created_at);
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);

-- 分析查询性能
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

#### 缓存优化
```python
# Redis缓存配置
CACHE_CONFIG = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
        },
        'KEY_PREFIX': 'footballprediction',
        'TIMEOUT': 300,  # 5分钟
    }
}

# 缓存使用示例
from django.core.cache import cache

def get_predictions(match_id):
    cache_key = f'predictions:{match_id}'
    predictions = cache.get(cache_key)
    if predictions is None:
        predictions = fetch_predictions_from_db(match_id)
        cache.set(cache_key, predictions, timeout=300)
    return predictions
```

### 系统层优化

#### Nginx优化
```nginx
# nginx.conf 优化配置
worker_processes auto;
worker_connections 1024;

http {
    # 启用gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript;

    # 连接池优化
    upstream footballprediction {
        server app:8000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    # 缓存配置
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m inactive=60m;

    server {
        listen 443 ssl http2;
        server_name api.footballprediction.com;

        # SSL优化
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
        ssl_prefer_server_ciphers off;

        # 性能优化
        client_max_body_size 10M;
        client_body_timeout 60s;
        client_header_timeout 60s;

        location / {
            proxy_pass http://footballprediction;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }
    }
}
```

---

## 📞 联系方式

### 运维团队
- **值班电话**: +86-xxx-xxxx-xxxx
- **运维邮箱**: ops@footballprediction.com
- **紧急联系**: emergency@footballprediction.com

### 相关链接
- **监控面板**: https://monitor.footballprediction.com
- **日志系统**: https://logs.footballprediction.com
- **文档中心**: https://docs.footballprediction.com

---

*手册版本: v1.0.0*
*最后更新: 2025-11-11*
*维护者: FootballPrediction运维团队*
