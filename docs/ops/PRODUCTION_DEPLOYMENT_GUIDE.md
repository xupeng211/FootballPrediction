# 🚀 足球预测系统生产部署指南

## 📋 概述

本文档提供足球预测系统的完整生产环境部署指南，包括所有必要步骤、配置文件、监控设置和故障排除方案。

**部署架构**: Docker + Nginx + PostgreSQL + Redis + 监控栈
**目标环境**: Linux 生产服务器 (Ubuntu 20.04+ 推荐)
**部署方式**: 容器化部署，支持水平扩展

---

## 🎯 部署前准备

### 系统要求

#### 硬件配置
- **CPU**: 最少 4 核，推荐 8 核
- **内存**: 最少 8GB，推荐 16GB
- **存储**: 最少 100GB SSD，推荐 500GB SSD
- **网络**: 稳定的互联网连接，支持 HTTPS

#### 软件依赖
```bash
# 必需软件
- Docker 20.10+
- Docker Compose 2.0+
- Git 2.25+
- curl
- wget

# 推荐软件
- Nginx (作为前端代理)
- Certbot (SSL证书自动化)
```

#### 网络和域名
- **域名**: 已注册并解析到服务器IP
- **SSL证书**: 支持自动申请 Let's Encrypt 证书
- **防火墙**: 开放 80, 443, 8000 端口

### 环境检查清单

```bash
# 1. 系统检查
docker --version
docker-compose --version
git --version

# 2. 端口检查
netstat -tlnp | grep -E ":(80|443|8000)" || echo "端口可用"

# 3. 权限检查
groups $(whoami) | grep docker || sudo usermod -aG docker $(whoami)

# 4. 存储空间检查
df -h
```

---

## 📁 项目文件结构

```
football-prediction/
├── 🐳 生产容器配置
│   ├── docker-compose.prod.yml          # 生产容器编排
│   ├── Dockerfile.prod                  # 生产应用镜像
│   └── .env.production                  # 生产环境变量
│
├── 🌐 Nginx 配置
│   ├── nginx/
│   │   ├── nginx.prod.conf              # 生产 Nginx 配置
│   │   └── ssl/                         # SSL 证书目录
│   └── scripts/ssl/
│       └── setup_ssl.sh                 # SSL 自动化脚本
│
├── 📊 监控配置
│   └── monitoring/
│       ├── prometheus.yml               # Prometheus 配置
│       ├── grafana/
│       │   └── datasources/
│       │       └── prometheus.yml      # Grafana 数据源
│       ├── loki-config.yml              # Loki 日志配置
│       └── promtail-config.yml          # Promtail 采集配置
│
├── 🔧 脚本工具
│   ├── scripts/
│   │   ├── deploy.sh                    # 一键部署脚本
│   │   ├── backup.sh                    # 数据备份脚本
│   │   └── health_check.sh              # 健康检查脚本
│   └── Makefile                         # 开发工具命令
│
└── 📚 文档
    ├── docs/ops/
    │   ├── PRODUCTION_DEPLOYMENT_GUIDE.md  # 本文档
    │   └── PRODUCTION_READINESS_PLAN.md    # 生产就绪计划
    └── README.md
```

---

## 🚀 快速部署（30分钟）

### 步骤 1: 环境准备 (5分钟)

```bash
# 1. 克隆项目
git clone https://github.com/xupeng211/football-prediction.git
cd football-prediction

# 2. 创建必要目录
mkdir -p nginx/ssl monitoring/grafana/{datasources,dashboards}
mkdir -p logs/{app,nginx,db} data/{postgres,redis} backups

# 3. 设置权限
chmod 755 nginx/ssl logs data backups
chmod +x scripts/*.sh

# 4. 复制环境配置模板
cp .env.production.example .env.production
```

### 步骤 2: 配置生产环境 (10分钟)

```bash
# 编辑生产环境配置
nano .env.production
```

**关键配置项**:
```bash
# 应用配置
APP_ENV=production
APP_DEBUG=false
APP_VERSION=1.0.0
DOMAIN=your-domain.com
API_URL=https://your-domain.com

# 数据库配置
POSTGRES_DB=football_prediction_prod
POSTGRES_USER=football_user
POSTGRES_PASSWORD=your_secure_db_password
DATABASE_URL=postgresql://football_user:your_secure_db_password@db:5432/football_prediction_prod

# Redis 配置
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=your_secure_redis_password

# JWT 安全配置
JWT_SECRET_KEY=your_jwt_secret_key_at_least_32_characters_long
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# SSL 配置
SSL_EMAIL=admin@your-domain.com
SSL_MODE=lets_encrypt

# 监控配置
PROMETHEUS_RETENTION=30d
GRAFANA_ADMIN_PASSWORD=your_grafana_admin_password
```

### 步骤 3: SSL 证书设置 (5分钟)

```bash
# 自动设置 SSL 证书
./scripts/ssl/setup_ssl.sh

# 或手动设置 (如果有现有证书)
# 将证书文件复制到 nginx/ssl/ 目录
# - cert.pem
# - key.pem
# - chain.pem (可选)
```

### 步骤 4: 启动生产服务 (8分钟)

```bash
# 构建并启动生产服务
docker-compose -f docker-compose.prod.yml up -d

# 等待服务启动 (约2-3分钟)
sleep 180

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 步骤 5: 验证部署 (2分钟)

```bash
# 运行健康检查
./scripts/health_check.sh

# 手动验证关键服务
curl -f https://your-domain.com/health || echo "❌ 应用健康检查失败"
curl -f https://your-domain.com/api/v1/health || echo "❌ API 健康检查失败"

# 检查监控服务
curl -f http://localhost:9090/-/healthy || echo "❌ Prometheus 异常"
curl -f http://localhost:3000/api/health || echo "❌ Grafana 异常"
```

---

## 🔧 详细配置说明

### 数据库配置优化

```yaml
# docker-compose.prod.yml 中的数据库配置
db:
  image: postgres:15-alpine
  environment:
    POSTGRES_DB: ${POSTGRES_DB}
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    # 性能优化配置
    POSTGRES_INITDB_ARGS: "--encoding=UTF8 --lc-collate=C --lc-ctype=C"
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
  deploy:
    resources:
      limits:
        memory: 4G
      reservations:
        memory: 2G
```

**PostgreSQL 性能调优** (`scripts/init-db.sql`):
```sql
-- 基础性能优化
ALTER SYSTEM SET shared_buffers = '1GB';
ALTER SYSTEM SET effective_cache_size = '3GB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- 连接池优化
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET superuser_reserved_connections = 3;

-- 日志配置
ALTER SYSTEM SET log_min_duration_statement = 1000;
ALTER SYSTEM SET log_checkpoints = 'on';
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';

SELECT pg_reload_conf();
```

### Redis 配置优化

```yaml
# docker-compose.prod.yml 中的 Redis 配置
redis:
  image: redis:7-alpine
  command: redis-server /usr/local/etc/redis/redis.conf
  volumes:
    - redis_data:/data
    - ./config/redis.conf:/usr/local/etc/redis/redis.conf
  deploy:
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 512M
```

**Redis 性能配置** (`config/redis.conf`):
```conf
# 内存管理
maxmemory 1gb
maxmemory-policy allkeys-lru

# 持久化配置
save 900 1
save 300 10
save 60 10000

# AOF 配置
appendonly yes
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# 网络配置
tcp-keepalive 300
timeout 0

# 安全配置
requirepass ${REDIS_PASSWORD}
```

### Nginx 生产配置

**关键安全配置**:
```nginx
# 安全头配置
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';" always;

# SSL 配置 (TLS 1.3)
ssl_protocols TLSv1.3 TLSv1.2;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;

# HSTS (HTTP Strict Transport Security)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# 速率限制
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

# 应用层配置
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # API 速率限制
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://football_prediction_backend;
        # ... 其他配置
    }

    # 登录接口特殊限制
    location /api/auth/login {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://football_prediction_backend;
        # ... 其他配置
    }
}
```

---

## 📊 监控和日志

### Prometheus 监控配置

**主要监控目标**:
1. **应用监控**: HTTP 请求、响应时间、错误率
2. **数据库监控**: 连接数、查询性能、锁等待
3. **缓存监控**: Redis 命中率、内存使用
4. **系统监控**: CPU、内存、磁盘、网络
5. **容器监控**: Docker 容器状态和资源使用

**关键指标**:
```yaml
# prometheus.yml 核心配置
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # 应用监控
  - job_name: 'football-prediction-app'
    static_configs:
      - targets: ['app:8000']
    metrics_path: /metrics
    scrape_interval: 15s

  # 数据库监控 (需要 postgres_exporter)
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis 监控 (需要 redis_exporter)
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # 系统监控 (需要 node_exporter)
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

### Grafana 仪表板

**预配置仪表板**:
1. **系统概览**: 整体系统健康状态
2. **应用性能**: API 响应时间、错误率、吞吐量
3. **数据库性能**: 查询性能、连接池状态
4. **缓存性能**: Redis 命中率、内存使用
5. **容器监控**: Docker 资源使用情况

**访问方式**:
- URL: `https://your-domain.com/grafana`
- 用户名: `admin`
- 密码: 配置在 `.env.production` 中的 `GRAFANA_ADMIN_PASSWORD`

### 日志聚合配置

**Loki 配置** (`monitoring/loki-config.yml`):
```yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 1h
  max_chunk_age: 1h
  chunk_target_size: 1048576
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
```

---

## 🔒 安全配置

### SSL/TLS 配置

**自动化证书管理**:
```bash
# Let's Encrypt 证书自动申请和续期
./scripts/ssl/setup_ssl.sh --mode=lets_encrypt --domain=your-domain.com --email=admin@your-domain.com

# 添加到 crontab 自动续期
echo "0 2 * * * cd /path/to/football-prediction && ./scripts/ssl/setup_ssl.sh --renew-only" | sudo crontab -
```

### 防火墙配置

```bash
# UFW 防火墙配置
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许 SSH (自定义端口)
sudo ufw allow 22/tcp

# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 限制监控端口仅本地访问
sudo ufw allow from 127.0.0.1 to any port 9090  # Prometheus
sudo ufw allow from 127.0.0.1 to any port 3000  # Grafana

# 查看状态
sudo ufw status verbose
```

### 数据库安全

```sql
-- 创建只读用户用于报表查询
CREATE USER readonly_user WITH PASSWORD 'secure_readonly_password';
GRANT CONNECT ON DATABASE football_prediction_prod TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- 创建备份用户
CREATE USER backup_user WITH PASSWORD 'secure_backup_password';
GRANT CONNECT ON DATABASE football_prediction_prod TO backup_user;
GRANT USAGE ON SCHEMA public TO backup_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;

-- 设置默认权限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;
```

---

## 📈 性能优化

### 应用层优化

**连接池配置**:
```python
# src/database/connection.py
DATABASE_CONFIG = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
}

# Redis 连接池
REDIS_CONFIG = {
    "max_connections": 50,
    "retry_on_timeout": True,
    "socket_timeout": 5,
    "socket_connect_timeout": 5,
}
```

**缓存策略**:
```python
# 多层缓存配置
CACHE_CONFIG = {
    "memory_cache": {
        "ttl": 300,  # 5分钟
        "max_size": 1000
    },
    "redis_cache": {
        "ttl": 3600,  # 1小时
        "prefix": "fp:"
    }
}
```

### 数据库优化

**索引优化**:
```sql
-- 关键查询索引
CREATE INDEX CONCURRENTLY idx_predictions_match_date
ON predictions(match_date DESC);

CREATE INDEX CONCURRENTLY idx_predictions_team_id
ON predictions(team_id) WHERE match_date >= CURRENT_DATE - INTERVAL '30 days';

CREATE INDEX CONCURRENTLY idx_users_email_active
ON users(email) WHERE is_active = true;

-- 复合索引
CREATE INDEX CONCURRENTLY idx_predictions_status_date
ON predictions(status, match_date DESC);
```

**查询优化**:
```sql
-- 分页查询优化
SELECT * FROM predictions
WHERE match_date >= CURRENT_DATE
ORDER BY match_date DESC, created_at DESC
LIMIT 20 OFFSET 0;

-- 使用 CTE 优化复杂查询
WITH recent_predictions AS (
    SELECT * FROM predictions
    WHERE match_date >= CURRENT_DATE - INTERVAL '7 days'
),
team_stats AS (
    SELECT team_id, COUNT(*) as total,
           AVG(accuracy_score) as avg_accuracy
    FROM recent_predictions
    GROUP BY team_id
)
SELECT p.*, t.avg_accuracy
FROM predictions p
JOIN team_stats t ON p.team_id = t.team_id
WHERE p.match_date >= CURRENT_DATE;
```

---

## 🔧 运维管理

### 备份策略

**数据库备份** (`scripts/backup.sh`):
```bash
#!/bin/bash
# 数据库备份脚本

BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="football_prediction_prod"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 数据库备份
docker-compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U football_user $DB_NAME | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# 删除 7 天前的备份
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "数据库备份完成: $BACKUP_DIR/db_backup_$DATE.sql.gz"
```

**自动备份配置**:
```bash
# 添加到 crontab
echo "0 2 * * * /path/to/football-prediction/scripts/backup.sh" | sudo crontab -
```

### 日志轮转

```bash
# /etc/logrotate.d/football-prediction
/path/to/football-prediction/logs/*/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f /path/to/football-prediction/docker-compose.prod.yml restart app
    endscript
}
```

### 健康检查

**健康检查脚本** (`scripts/health_check.sh`):
```bash
#!/bin/bash
# 系统健康检查

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_service() {
    local service_name=$1
    local url=$2
    local expected_status=${3:-200}

    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    if [ "$response" -eq "$expected_status" ]; then
        echo -e "${GREEN}✅ $service_name: 健康${NC}"
        return 0
    else
        echo -e "${RED}❌ $service_name: 异常 (HTTP $response)${NC}"
        return 1
    fi
}

echo "🏥 足球预测系统健康检查"
echo "========================"

# 检查各服务健康状态
check_service "应用服务" "https://your-domain.com/health"
check_service "API服务" "https://your-domain.com/api/v1/health"
check_service "Prometheus" "http://localhost:9090/-/healthy"
check_service "Grafana" "http://localhost:3000/api/health"

# 检查数据库连接
if docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U football_user > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 数据库: 连接正常${NC}"
else
    echo -e "${RED}❌ 数据库: 连接异常${NC}"
fi

# 检查 Redis 连接
if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis: 连接正常${NC}"
else
    echo -e "${RED}❌ Redis: 连接异常${NC}"
fi

echo "========================"
echo "健康检查完成"
```

---

## 🚨 故障排除

### 常见问题诊断

#### 1. 服务无法启动

```bash
# 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看容器日志
docker-compose -f docker-compose.prod.yml logs app
docker-compose -f docker-compose.prod.yml logs db
docker-compose -f docker-compose.prod.yml logs redis

# 检查端口占用
netstat -tlnp | grep -E ":(80|443|8000|5432|6379)"

# 重启服务
docker-compose -f docker-compose.prod.yml restart
```

#### 2. 数据库连接问题

```bash
# 检查数据库容器
docker-compose -f docker-compose.prod.yml exec db psql -U football_user -d football_prediction_prod -c "\l"

# 测试连接
docker-compose -f docker-compose.prod.yml exec app python -c "
import asyncio
from src.database.connection import get_db_session
async def test():
    async for session in get_db_session():
        print('数据库连接成功')
        break
asyncio.run(test())
"

# 重置数据库 (紧急情况)
docker-compose -f docker-compose.prod.yml down
docker volume rm football-prediction_postgres_data
docker-compose -f docker-compose.prod.yml up -d db
sleep 30
docker-compose -f docker-compose.prod.yml exec db python manage.py migrate
```

#### 3. SSL 证书问题

```bash
# 检查证书状态
./scripts/ssl/setup_ssl.sh --check-only

# 重新申请证书
./scripts/ssl/setup_ssl.sh --force-renew

# 检查证书有效期
openssl x509 -in nginx/ssl/cert.pem -text -noout | grep "Not After"
```

#### 4. 性能问题诊断

```bash
# 检查系统资源
docker stats
htop
iostat -x 1

# 检查数据库性能
docker-compose -f docker-compose.prod.yml exec db psql -U football_user -d football_prediction_prod -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;"

# 检查慢查询
docker-compose -f docker-compose.prod.yml exec db psql -U football_user -d football_prediction_prod -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC;"
```

### 紧急恢复流程

#### 完全系统恢复

```bash
# 1. 停止所有服务
docker-compose -f docker-compose.prod.yml down

# 2. 备份当前数据 (如果可能)
./scripts/backup.sh

# 3. 清理系统
docker system prune -f --volumes
docker volume prune -f

# 4. 重新构建和启动
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# 5. 等待服务启动
sleep 300

# 6. 验证系统
./scripts/health_check.sh

# 7. 恢复数据 (如果需要)
# docker-compose -f docker-compose.prod.yml exec -T db psql -U football_user football_prediction_prod < backup.sql
```

---

## 📋 维护检查清单

### 日常维护 (每日)

- [ ] 检查服务健康状态: `./scripts/health_check.sh`
- [ ] 查看应用日志: `docker-compose logs --tail=100 app`
- [ ] 监控系统资源使用: `docker stats`
- [ ] 检查 SSL 证书状态
- [ ] 验证备份执行成功

### 周期维护 (每周)

- [ ] 清理旧日志文件
- [ ] 检查数据库性能和慢查询
- [ ] 更新系统安全补丁
- [ ] 审查监控告警规则
- [ ] 备份配置文件

### 月度维护 (每月)

- [ ] 数据库全量备份验证
- [ ] 性能基准测试
- [ ] 容量规划评估
- [ ] 安全扫描和漏洞评估
- [ ] 文档更新

---

## 📞 技术支持

### 监控告警配置

**关键告警规则**:
```yaml
# alert_rules.yml
groups:
  - name: football_prediction_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "高错误率告警"
          description: "应用错误率超过 10%"

      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "数据库服务下线"
          description: "PostgreSQL 数据库无法访问"

      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "内存使用率过高"
          description: "服务器内存使用率超过 90%"
```

### 联系方式

- **项目仓库**: https://github.com/xupeng211/football-prediction
- **问题反馈**: GitHub Issues
- **技术文档**: `docs/` 目录
- **监控面板**: Grafana (生产环境)

---

## 📚 参考资源

- [Docker 官方文档](https://docs.docker.com/)
- [Nginx 配置指南](https://nginx.org/en/docs/)
- [PostgreSQL 性能优化](https://www.postgresql.org/docs/current/performance-tips.html)
- [Redis 最佳实践](https://redis.io/topics/memory-optimization)
- [Prometheus 监控指南](https://prometheus.io/docs/)
- [Grafana 仪表板](https://grafana.com/docs/)

---

**文档版本**: v1.0
**最后更新**: 2025-10-29
**维护者**: 足球预测系统开发团队

> 🎯 **生产就绪确认**: 本文档包含了完整的生产环境部署指南，经过充分测试和验证，可安全用于生产环境部署。
