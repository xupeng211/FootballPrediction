# 足球预测系统运维手册
# Football Prediction System Operations Manual

## 目录
- [概述](#概述)
- [系统架构](#系统架构)
- [环境管理](#环境管理)
- [部署指南](#部署指南)
- [监控和告警](#监控和告警)
- [备份和恢复](#备份和恢复)
- [故障排除](#故障排除)
- [性能优化](#性能优化)
- [安全管理](#安全管理)
- [维护计划](#维护计划)

## 概述

本运维手册提供足球预测系统的完整运维指南，包括部署、监控、故障排除、维护等各个方面。

### 系统组件

- **应用服务**: FastAPI应用 (Python 3.11+)
- **数据库**: PostgreSQL 14+
- **缓存**: Redis 6+
- **消息队列**: Celery + Redis
- **监控**: Prometheus + Grafana + AlertManager
- **负载均衡**: Nginx
- **容器化**: Docker + Docker Compose

### 关键特性

- 多租户架构支持
- 机器学习预测模型
- 实时数据处理
- 高可用性设计
- 自动化监控告警

## 系统架构

### 架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   用户界面       │    │   移动应用       │    │   第三方集成     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      负载均衡器 (Nginx)    │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │     API网关 + 应用层       │
                    │   (FastAPI + 多租户)      │
                    └─────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────┴───────┐    ┌─────────┴───────┐    ┌─────────┴───────┐
│   PostgreSQL    │    │     Redis       │    │   消息队列        │
│   (主数据库)     │    │    (缓存)       │    │   (Celery)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      监控系统              │
                    │ Prometheus + Grafana     │
                    │   + AlertManager         │
                    └───────────────────────────┘
```

### 数据流

1. **用户请求** → Nginx负载均衡 → FastAPI应用
2. **API请求** → 业务逻辑处理 → 数据库查询/缓存访问
3. **异步任务** → Celery队列 → Redis → 后台处理
4. **监控数据** → Prometheus指标收集 → Grafana可视化
5. **告警触发** → AlertManager → 通知渠道

## 环境管理

### 环境分类

| 环境 | 用途 | 域名 | 数据库 | 监控 |
|------|------|------|--------|------|
| 开发环境 | 功能开发测试 | dev.football-prediction.com | 独立实例 | 基础监控 |
| 测试环境 | 集成测试验证 | test.football-prediction.com | 独立实例 | 完整监控 |
| 预生产环境 | 生产前验证 | staging.football-prediction.com | 生产级实例 | 完整监控 |
| 生产环境 | 正式服务运行 | api.football-prediction.com | 高可用集群 | 全面监控 |

### 环境配置

#### 开发环境

```bash
# 环境变量
ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

# 数据库配置
DATABASE_URL=postgresql://dev_user:dev_pass@localhost:5432/football_prediction_dev

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 安全配置
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=dev-jwt-secret

# 监控配置
PROMETHEUS_ENABLED=true
METRICS_PORT=8000
```

#### 生产环境

```bash
# 环境变量
ENV=production
DEBUG=false
LOG_LEVEL=INFO

# 数据库配置 (主从配置)
DATABASE_URL=postgresql://prod_user:secure_pass@db-master:5432/football_prediction
DATABASE_READ_URL=postgresql://prod_user:secure_pass@db-slave:5432/football_prediction

# Redis配置 (集群模式)
REDIS_URL=redis://redis-cluster:6379/0
REDIS_CLUSTER_NODES=redis-node1:6379,redis-node2:6379,redis-node3:6379

# 安全配置
SECRET_KEY=${SECRET_KEY_FROM_VAULT}
JWT_SECRET_KEY=${JWT_SECRET_FROM_VAULT}
ALLOWED_HOSTS=api.football-prediction.com,*.football-prediction.com

# SSL/TLS配置
SSL_CERT_PATH=/etc/ssl/certs/football-prediction.com.crt
SSL_KEY_PATH=/etc/ssl/private/football-prediction.com.key

# 监控配置
PROMETHEUS_ENABLED=true
METRICS_PORT=8000
SENTRY_DSN=${SENTRY_DSN_FROM_VAULT}
```

## 部署指南

### 快速部署

```bash
# 1. 克隆代码
git clone https://github.com/your-org/football-prediction.git
cd football-prediction

# 2. 安装依赖
make install

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置必要的环境变量

# 4. 启动数据库
make up-db

# 5. 运行数据库迁移
make db-migrate

# 6. 启动应用
make up

# 7. 验证部署
make health-check
```

### 生产环境部署

#### 1. 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 创建应用用户
sudo useradd -m -s /bin/bash football
sudo usermod -aG docker football
```

#### 2. 部署应用

```bash
# 切换到应用用户
sudo su - football

# 克隆代码
git clone https://github.com/your-org/football-prediction.git
cd football-prediction

# 配置环境变量
cp .env.production .env
# 配置生产环境变量

# 构建和启动
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 运行数据库迁移
docker-compose exec app alembic upgrade head

# 创建管理员用户
docker-compose exec app python scripts/create_admin.py
```

#### 3. 配置SSL证书

```bash
# 使用Let's Encrypt
sudo apt install certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d api.football-prediction.com

# 设置自动续期
sudo crontab -e
# 添加以下行：
# 0 12 * * * /usr/bin/certbot renew --quiet
```

#### 4. 配置监控

```bash
# 启动监控系统
cd monitoring
chmod +x ../scripts/start_monitoring.sh
./start_monitoring.sh

# 配置Grafana
# 访问 http://your-server:3000
# 默认用户名/密码: admin/admin123
# 导入仪表板配置
```

### 蓝绿部署

```bash
# 蓝环境部署
docker-compose -f docker-compose.blue.yml up -d

# 验证蓝环境
curl -H "Host: api.football-prediction.com" http://blue-server/health

# 切换流量
# 更新DNS或负载均衡器配置，指向蓝环境

# 绿环境部署
docker-compose -f docker-compose.green.yml up -d

# 验证绿环境
curl -H "Host: api.football-prediction.com" http://green-server/health

# 切换流量到绿环境
# 更新DNS或负载均衡器配置

# 清理旧环境
docker-compose -f docker-compose.blue.yml down
```

## 监控和告警

### 监控架构

```
应用服务 → Prometheus指标收集 → Grafana可视化
    ↓
AlertManager告警路由 → 邮件/Slack/钉钉通知
```

### 关键指标

#### 应用层指标

- **请求量**: QPS、并发用户数
- **响应时间**: 平均、P95、P99响应时间
- **错误率**: 4xx、5xx错误率
- **业务指标**: 预测准确率、用户活跃度

#### 系统层指标

- **CPU使用率**: 应用和数据库服务器
- **内存使用率**: 应用和缓存服务器
- **磁盘使用率**: 日志、数据、临时文件
- **网络I/O**: 带宽使用、连接数

#### 数据库指标

- **连接池**: 活跃连接、空闲连接、等待连接
- **查询性能**: 慢查询、查询频率
- **存储**: 表大小、索引使用率
- **复制延迟**: 主从同步延迟

#### 业务指标

- **预测准确率**: 模型预测成功率
- **用户活跃度**: DAU、MAU、留存率
- **租户使用情况**: 配额使用、API调用量
- **数据质量**: 数据完整性、时效性

### 告警规则

#### 关键告警

```yaml
# 系统宕机
- alert: SystemDown
  expr: up{job="football-prediction"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "系统服务不可用"

# 高错误率
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "API错误率过高"

# 响应时间过长
- alert: HighResponseTime
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.0
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "API响应时间过高"
```

#### 业务告警

```yaml
# 预测准确率下降
- alert: LowPredictionAccuracy
  expr: prediction_accuracy < 0.6
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "预测准确率下降"

# 租户配额超限
- alert: TenantQuotaExceeded
  expr: tenant_quota_usage / tenant_quota_limit > 0.9
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "租户配额即将超限"
```

### 监控面板

#### 系统概览面板
- 系统健康状态
- 请求量趋势
- 错误率趋势
- 响应时间分布

#### 业务指标面板
- 预测准确率趋势
- 用户活跃度统计
- 租户使用情况
- 数据质量指标

#### 基础设施面板
- 服务器资源使用
- 数据库性能
- 缓存命中率
- 网络流量统计

## 备份和恢复

### 备份策略

#### 数据库备份

```bash
#!/bin/bash
# 每日全量备份脚本
BACKUP_DIR="/backup/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="football_prediction"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
pg_dump -h db-master -U postgres -d $DB_NAME | gzip > $BACKUP_DIR/football_prediction_$DATE.sql.gz

# 保留30天备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

# 上传到云存储
aws s3 cp $BACKUP_DIR/football_prediction_$DATE.sql.gz s3://football-prediction-backups/postgres/
```

#### Redis备份

```bash
#!/bin/bash
# Redis备份脚本
BACKUP_DIR="/backup/redis"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
redis-cli --rdb $BACKUP_DIR/redis_$DATE.rdb

# 压缩备份
gzip $BACKUP_DIR/redis_$DATE.rdb

# 保留7天备份
find $BACKUP_DIR -name "*.rdb.gz" -mtime +7 -delete
```

#### 应用数据备份

```bash
#!/bin/bash
# 应用数据备份脚本
BACKUP_DIR="/backup/application"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份上传文件
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /app/uploads

# 备份配置文件
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /app/config

# 备份日志文件
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /app/logs
```

### 恢复流程

#### 数据库恢复

```bash
#!/bin/bash
# 数据库恢复脚本
BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# 停止应用
docker-compose stop app

# 恢复数据库
gunzip -c $BACKUP_FILE | psql -h db-master -U postgres -d football_prediction

# 启动应用
docker-compose start app

# 验证恢复
docker-compose exec app python scripts/verify_data.py
```

#### 完整系统恢复

```bash
#!/bin/bash
# 完整系统恢复脚本
RESTORE_DATE=$1

if [ -z "$RESTORE_DATE" ]; then
    echo "Usage: $0 <YYYYMMDD>"
    exit 1
fi

# 停止所有服务
docker-compose down

# 恢复数据库
gunzip -c /backup/postgres/football_prediction_${RESTORE_DATE}*.sql.gz | psql -h db-master -U postgres

# 恢复Redis
redis-cli --rdb /backup/redis/redis_${RESTORE_DATE}*.rdb

# 恢复应用数据
tar -xzf /backup/application/uploads_${RESTORE_DATE}.tar.gz -C /
tar -xzf /backup/application/config_${RESTORE_DATE}.tar.gz -C /

# 启动服务
docker-compose up -d

# 验证系统
./scripts/health_check.sh
```

### 备份验证

```bash
#!/bin/bash
# 备份验证脚本
BACKUP_FILE=$1

# 检查备份文件完整性
if ! gzip -t $BACKUP_FILE; then
    echo "备份文件损坏: $BACKUP_FILE"
    exit 1
fi

# 恢复到测试环境
echo "恢复备份到测试环境..."
createdb test_restore
gunzip -c $BACKUP_FILE | psql -h test-db -U postgres -d test_restore

# 验证数据完整性
python scripts/verify_backup_integrity.py --db test_restore

# 清理测试环境
dropdb test_restore

echo "备份验证完成"
```

## 故障排除

### 常见问题

#### 应用无法启动

**症状**: 应用容器启动失败或退出

**排查步骤**:
1. 检查容器日志: `docker-compose logs app`
2. 检查环境变量配置: `docker-compose exec app env`
3. 检查数据库连接: `docker-compose exec app python scripts/check_db.py`
4. 检查端口占用: `netstat -tlnp | grep 8000`

**解决方案**:
```bash
# 重启应用
docker-compose restart app

# 重新构建镜像
docker-compose build --no-cache app

# 检查配置文件
docker-compose exec app cat /app/.env
```

#### 数据库连接问题

**症状**: 数据库连接超时或失败

**排查步骤**:
1. 检查数据库状态: `docker-compose exec postgres pg_isready`
2. 检查连接池: `docker-compose exec app python scripts/check_pool.py`
3. 检查网络连接: `docker network ls`
4. 检查数据库日志: `docker-compose logs postgres`

**解决方案**:
```bash
# 重启数据库
docker-compose restart postgres

# 检查数据库配置
docker-compose exec postgres cat /var/lib/postgresql/data/postgresql.conf

# 增加连接池大小
# 更新环境变量 DB_POOL_SIZE=20
```

#### 高内存使用

**症状**: 系统内存使用率过高

**排查步骤**:
1. 检查进程内存使用: `docker stats`
2. 检查应用内存泄漏: `docker-compose exec app python scripts/memory_profiler.py`
3. 检查数据库内存: `docker-compose exec postgres psql -c "SELECT * FROM pg_stat_activity;"`
4. 检查缓存使用: `redis-cli info memory`

**解决方案**:
```bash
# 重启应用释放内存
docker-compose restart app

# 清理Redis缓存
redis-cli FLUSHDB

# 优化数据库查询
# 分析慢查询日志
docker-compose exec postgres psql -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

#### 高CPU使用

**症状**: 系统CPU使用率过高

**排查步骤**:
1. 检查进程CPU使用: `docker stats --no-stream`
2. 检查应用性能: `docker-compose exec app python scripts/cpu_profiler.py`
3. 检查数据库查询: `docker-compose exec postgres psql -c "SELECT * FROM pg_stat_activity;"`
4. 检查系统负载: `uptime`

**解决方案**:
```bash
# 扩展应用实例
docker-compose up -d --scale app=3

# 优化慢查询
# 使用EXPLAIN分析查询计划

# 增加缓存
# 检查Redis命中率
```

### 故障响应流程

#### P1故障 (严重)

1. **响应时间**: 5分钟内
2. **处理流程**:
   - 立即通知运维团队
   - 启动应急响应程序
   - 执行快速回滚或切换
   - 持续监控修复情况
3. **升级条件**: 15分钟内未解决

#### P2故障 (重要)

1. **响应时间**: 15分钟内
2. **处理流程**:
   - 通知相关开发和运维人员
   - 分析故障原因
   - 制定修复方案
   - 实施修复并验证

#### P3故障 (一般)

1. **响应时间**: 1小时内
2. **处理流程**:
   - 记录故障详情
   - 安排在下一个维护窗口修复
   - 更新文档和流程

## 性能优化

### 应用层优化

#### 数据库查询优化

```python
# 使用连接池
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)

# 使用索引优化查询
class Prediction(Base):
    __table_args__ = (
        Index('idx_prediction_user_created', 'user_id', 'created_at'),
        Index('idx_prediction_match_status', 'match_id', 'status'),
    )

# 批量操作
def create_predictions_bulk(predictions_data):
    with Session(engine) as session:
        session.bulk_insert_mappings(Prediction, predictions_data)
        session.commit()
```

#### 缓存策略

```python
import redis
from functools import wraps

redis_client = redis.Redis(host='redis', port=6379, db=0)

def cache_result(expire_time=300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 尝试从缓存获取
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)

            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, expire_time, json.dumps(result))

            return result
        return wrapper
    return decorator

@cache_result(expire_time=600)
async def get_prediction_statistics(match_id: int):
    # 复杂的统计查询
    pass
```

### 数据库优化

#### 索引优化

```sql
-- 创建复合索引
CREATE INDEX CONCURRENTLY idx_predictions_composite
ON predictions(user_id, match_id, created_at DESC);

-- 创建部分索引
CREATE INDEX CONCURRENTLY idx_predictions_active
ON predictions(match_id, created_at)
WHERE status = 'pending';

-- 分析索引使用情况
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

#### 查询优化

```sql
-- 使用EXPLAIN分析查询
EXPLAIN (ANALYZE, BUFFERS)
SELECT p.*, m.home_team_id, m.away_team_id
FROM predictions p
JOIN matches m ON p.match_id = m.id
WHERE p.user_id = 1 AND p.created_at >= '2025-10-01'
ORDER BY p.created_at DESC
LIMIT 20;

-- 优化后的查询
SELECT p.*, m.home_team_id, m.away_team_id
FROM predictions p
USE INDEX (idx_prediction_user_created)
JOIN matches m ON p.match_id = m.id
WHERE p.user_id = 1 AND p.created_at >= '2025-10-01'
ORDER BY p.created_at DESC
LIMIT 20;
```

### 系统级优化

#### Nginx配置优化

```nginx
# nginx.conf
worker_processes auto;
worker_connections 1024;

http {
    # 启用gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain application/json application/javascript text/css;

    # 缓存配置
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g
                     inactive=60m use_temp_path=off;

    upstream football_prediction {
        least_conn;
        server app1:8000 max_fails=3 fail_timeout=30s;
        server app2:8000 max_fails=3 fail_timeout=30s;
        server app3:8000 max_fails=3 fail_timeout=30s;
    }

    server {
        listen 80;
        server_name api.football-prediction.com;

        # 静态文件缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # API代理配置
        location /api/ {
            proxy_pass http://football_prediction;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 启用缓存
            proxy_cache api_cache;
            proxy_cache_valid 200 5m;
            proxy_cache_key "$scheme$request_method$host$request_uri";

            # 超时设置
            proxy_connect_timeout 5s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
}
```

## 安全管理

### 访问控制

#### 网络安全

```bash
# 防火墙配置
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许必要端口
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# 限制数据库访问
sudo ufw allow from 10.0.0.0/8 to any port 5432
sudo ufw allow from 172.16.0.0/12 to any port 5432
```

#### 应用安全

```python
# 输入验证
from pydantic import BaseModel, validator

class PredictionCreate(BaseModel):
    match_id: int
    confidence: float

    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('置信度必须在0-1之间')
        return v

# SQL注入防护
from sqlalchemy import text

# 错误方式 - 容易SQL注入
# query = f"SELECT * FROM predictions WHERE user_id = {user_id}"

# 正确方式 - 使用参数化查询
query = text("SELECT * FROM predictions WHERE user_id = :user_id")
result = session.execute(query, {"user_id": user_id})

# XSS防护
from markupsafe import escape

def sanitize_user_input(user_input: str) -> str:
    return escape(user_input)
```

### 数据加密

#### 传输加密

```yaml
# SSL/TLS配置
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

#### 存储加密

```python
# 敏感数据加密
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self, key: str):
        self.cipher = Fernet(key.encode())

    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# 使用示例
encryption = DataEncryption(ENCRYPTION_KEY)
encrypted_password = encryption.encrypt(user_password)
```

### 安全审计

#### 日志审计

```python
import logging
from datetime import datetime

# 安全日志配置
security_logger = logging.getLogger('security')
handler = logging.FileHandler('/var/log/football-prediction/security.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
security_logger.addHandler(handler)

def log_security_event(event_type: str, user_id: int, details: dict):
    security_logger.info(f"SECURITY_EVENT: {event_type} - USER: {user_id} - DETAILS: {details}")

# 使用示例
log_security_event("LOGIN_SUCCESS", user.id, {"ip": request.client.host})
```

#### 访问日志分析

```bash
# 分析访问日志
#!/bin/bash
# 分析可疑IP访问
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -nr | head -20

# 分析错误日志
grep "ERROR" /var/log/football-prediction/app.log | tail -50

# 检测暴力破解
grep "LOGIN_FAILED" /var/log/football-prediction/security.log | awk '{print $6}' | sort | uniq -c | sort -nr | head -10
```

## 维护计划

### 日常维护

#### 每日检查清单

- [ ] 检查系统健康状态
- [ ] 查看错误日志
- [ ] 监控系统资源使用
- [ ] 检查备份完成状态
- [ ] 验证关键业务指标

#### 每周维护任务

- [ ] 清理过期日志文件
- [ ] 更新系统补丁
- [ ] 分析性能趋势
- [ ] 检查安全告警
- [ ] 审查用户权限

#### 每月维护任务

- [ ] 数据库性能优化
- [ ] 清理过期数据
- [ ] 更新依赖包
- [ ] 安全漏洞扫描
- [ ] 容量规划评估

### 维护脚本

#### 系统健康检查

```bash
#!/bin/bash
# health_check.sh

echo "=== 系统健康检查 ==="
echo "时间: $(date)"

# 检查服务状态
echo -e "\n1. 服务状态:"
docker-compose ps

# 检查系统资源
echo -e "\n2. 系统资源:"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')"
echo "内存: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "磁盘: $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')"

# 检查应用健康
echo -e "\n3. 应用健康:"
curl -s -o /dev/null -w "HTTP状态码: %{http_code}, 响应时间: %{time_total}s\n" http://localhost:8000/health

# 检查数据库连接
echo -e "\n4. 数据库连接:"
docker-compose exec -T postgres pg_isready

# 检查Redis连接
echo -e "\n5. Redis连接:"
docker-compose exec -T redis redis-cli ping

echo -e "\n=== 检查完成 ==="
```

#### 日志清理

```bash
#!/bin/bash
# cleanup_logs.sh

LOG_DIR="/var/log/football-prediction"
RETENTION_DAYS=30

echo "开始清理日志文件..."
echo "保留天数: $RETENTION_DAYS"

# 清理应用日志
find $LOG_DIR -name "*.log" -mtime +$RETENTION_DAYS -delete
echo "应用日志清理完成"

# 清理Nginx日志
find /var/log/nginx -name "*.log.*" -mtime +$RETENTION_DAYS -delete
echo "Nginx日志清理完成"

# 清理Docker日志
docker system prune -f
echo "Docker日志清理完成"

echo "日志清理完成"
```

#### 数据库维护

```bash
#!/bin/bash
# db_maintenance.sh

echo "开始数据库维护..."

# 更新统计信息
docker-compose exec postgres psql -U postgres -d football_prediction -c "ANALYZE;"

# 重建索引（如果需要）
docker-compose exec postgres psql -U postgres -d football_prediction -c "REINDEX DATABASE football_prediction;"

# 清理死元组
docker-compose exec postgres psql -U postgres -d football_prediction -c "VACUUM ANALYZE;"

# 检查数据库大小
docker-compose exec postgres psql -U postgres -d football_prediction -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;"

echo "数据库维护完成"
```

### 应急响应

#### 故障应急响应流程

```mermaid
flowchart TD
    A[故障发生] --> B{严重程度评估}
    B -->|P1-严重| C[立即通知运维团队]
    B -->|P2-重要| D[通知相关人员]
    B -->|P3-一般| E[记录并安排处理]

    C --> F[启动应急响应]
    F --> G[执行快速修复]
    G --> H[验证修复效果]
    H --> I[持续监控]

    D --> J[分析故障原因]
    J --> K[制定修复方案]
    K --> L[实施修复]
    L --> M[验证修复]

    E --> N[记录故障详情]
    N --> O[安排维护窗口]
```

#### 应急联系方式

| 角色 | 联系人 | 电话 | 邮箱 |
|------|--------|------|------|
| 运维负责人 | 张三 | 138-xxxx-xxxx | zhang.san@football-prediction.com |
| 开发负责人 | 李四 | 139-xxxx-xxxx | li.si@football-prediction.com |
| 数据库DBA | 王五 | 137-xxxx-xxxx | wang.wu@football-prediction.com |
| 安全负责人 | 赵六 | 136-xxxx-xxxx | zhao.liu@football-prediction.com |

---

*文档版本: v1.0*
*最后更新: 2025-10-30*
*维护者: 运维团队*