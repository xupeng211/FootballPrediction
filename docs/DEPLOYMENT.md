# FootballPrediction 系统部署指南

## 目录

1. [环境准备](#环境准备)
2. [依赖要求](#依赖要求)
3. [配置说明](#配置说明)
4. [部署方式](#部署方式)
5. [环境变量](#环境变量)
6. [SSL证书配置](#ssl证书配置)
7. [数据库设置](#数据库设置)
8. [Redis配置](#redis配置)
9. [监控系统](#监控系统)
10. [故障排除](#故障排除)

## 环境准备

### 系统要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Amazon Linux 2
- **Python**: 3.11+
- **内存**: 最低 2GB，推荐 4GB+
- **存储**: 最低 20GB，推荐 50GB+
- **网络**: 稳定的互联网连接

### 端口要求

- **API服务**: 8000 (HTTP) / 8443 (HTTPS)
- **PostgreSQL**: 5432
- **Redis**: 6379
- **Prometheus**: 9090
- **Grafana**: 3000
- **Nginx**: 80, 443

## 依赖要求

### 系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip nginx postgresql redis-server

# CentOS/RHEL
sudo yum update
sudo yum install -y python3.11 python3-pip nginx postgresql-server redis
```

### Docker依赖（可选）

```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## 配置说明

### 1. 克隆代码

```bash
git clone https://github.com/your-org/FootballPrediction.git
cd FootballPrediction
```

### 2. 创建虚拟环境

```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 3. 安装依赖

```bash
make install-locked
```

### 4. 环境配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

## 部署方式

### 方式一：直接部署（开发/测试环境）

```bash
# 1. 设置环境变量
export ENVIRONMENT=development
export DATABASE_URL=postgresql://user:password@localhost:5432/football_prediction
export REDIS_URL=redis://localhost:6379/0

# 2. 初始化数据库
make db-init

# 3. 运行数据库迁移
make db-upgrade

# 4. 启动应用
make serve
```

### 方式二：Docker部署（推荐）

```bash
# 1. 构建镜像
docker build -t football-prediction:latest .

# 2. 使用Docker Compose启动
docker-compose up -d

# 3. 查看日志
docker-compose logs -f
```

### 方式三：生产环境部署（蓝绿部署）

```bash
# 1. 使用部署脚本
python scripts/deploy.py \
    --environment production \
    --version v1.0.0 \
    --blue-green

# 2. 检查部署状态
curl -f https://api.footballprediction.com/api/v1/health

# 3. 如需回滚
python scripts/deploy.py \
    --action rollback \
    --environment production
```

## 环境变量

### 必需变量

```bash
# 环境
ENVIRONMENT=production  # development, staging, production

# 数据库
DATABASE_URL=postgresql://user:password@host:5432/database

# Redis
REDIS_URL=redis://host:6379/0

# JWT密钥
JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-chars
```

### 可选变量

```bash
# API密钥
FOOTBALL_API_KEY=your-football-api-key

# 监控
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# 缓存
CACHE_TTL=3600
CACHE_MAX_SIZE=1000

# 日志
LOG_LEVEL=INFO
LOG_FORMAT=json

# SSL
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

## SSL证书配置

### Let's Encrypt（推荐）

```bash
# 1. 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 2. 获取证书
sudo certbot --nginx -d api.footballprediction.com

# 3. 设置自动续期
sudo crontab -e
# 添加：0 12 * * * /usr/bin/certbot renew --quiet
```

### 自签名证书（开发环境）

```bash
# 1. 生成证书
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# 2. 配置Nginx
sudo cp cert.pem /etc/ssl/certs/
sudo cp key.pem /etc/ssl/private/
sudo chmod 600 /etc/ssl/private/key.pem
```

### 使用SSL配置脚本

```bash
# 自动配置SSL
sudo bash scripts/setup_ssl.sh \
    --domain api.footballprediction.com \
    --email admin@footballprediction.com \
    --method letsencrypt
```

## 数据库设置

### PostgreSQL安装与配置

```bash
# 1. 安装PostgreSQL
sudo apt install postgresql postgresql-contrib

# 2. 创建数据库和用户
sudo -u postgres psql
CREATE DATABASE football_prediction;
CREATE USER fp_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE football_prediction TO fp_user;
\q

# 3. 配置PostgreSQL
sudo nano /etc/postgresql/14/main/postgresql.conf
# 修改：listen_addresses = 'localhost'

# 4. 重启PostgreSQL
sudo systemctl restart postgresql
```

### 数据库迁移

```bash
# 初始化迁移
make db-init

# 运行迁移
make db-upgrade

# 创建迁移文件
make db-revision message="添加新功能"

# 回滚迁移
make db-downgrade
```

### 数据库备份

```bash
# 手动备份
pg_dump -h localhost -U fp_user football_prediction > backup.sql

# 使用备份脚本
python scripts/backup_database.py \
    --output-dir /backup \
    --compress \
    --encrypt
```

## Redis配置

### Redis安装与配置

```bash
# 1. 安装Redis
sudo apt install redis-server

# 2. 配置Redis
sudo nano /etc/redis/redis.conf
# 重要配置：
# bind 127.0.0.1
# requirepass your_redis_password
# maxmemory 256mb
# maxmemory-policy allkeys-lru

# 3. 重启Redis
sudo systemctl restart redis-server

# 4. 测试连接
redis-cli ping
```

### Redis集群（生产环境）

```bash
# 1. 创建Redis集群配置
mkdir -p /etc/redis/cluster
cp scripts/redis-cluster.conf /etc/redis/cluster/

# 2. 启动集群节点
for port in 7000 7001 7002; do
    redis-server /etc/redis/cluster/redis-${port}.conf &
done

# 3. 创建集群
redis-cli --cluster create \
    127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 \
    --cluster-replicas 0
```

## 监控系统

### Prometheus配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'football-prediction'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
```

### Grafana仪表板

```bash
# 1. 启动Grafana
docker run -d \
  --name=grafana \
  -p 3000:3000 \
  -v grafana-storage:/var/lib/grafana \
  grafana/grafana-enterprise

# 2. 导入预配置仪表板
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @monitoring/grafana/dashboards/football-prediction.json
```

### 日志聚合（ELK Stack）

```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./monitoring/logstash/pipeline:/usr/share/logstash/pipeline
    ports:
      - "5044:5044"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
```

## 故障排除

### 常见问题

#### 1. 应用无法启动

```bash
# 检查日志
docker-compose logs app
# 或
journalctl -u football-prediction -f

# 检查端口占用
netstat -tlnp | grep :8000

# 检查环境变量
printenv | grep -E "(DATABASE|REDIS|JWT)"
```

#### 2. 数据库连接失败

```bash
# 测试数据库连接
psql -h localhost -U fp_user -d football_prediction

# 检查PostgreSQL状态
sudo systemctl status postgresql

# 查看数据库日志
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

#### 3. Redis连接问题

```bash
# 测试Redis连接
redis-cli -h localhost -p 6379 ping

# 检查Redis状态
sudo systemctl status redis-server

# 监控Redis
redis-cli --latency-history -i 1
```

#### 4. SSL证书问题

```bash
# 验证证书
openssl x509 -in /path/to/cert.pem -text -noout

# 检查证书有效期
openssl x509 -in /path/to/cert.pem -noout -dates

# 测试HTTPS连接
curl -v https://api.footballprediction.com
```

#### 5. 高CPU/内存使用

```bash
# 查看进程资源使用
htop

# 查看Python进程详情
ps aux | grep python

# 分析内存使用
memory_profiler python -m memory_profiler src/api/app.py

# 生成性能报告
make benchmark-full
```

### 性能优化

#### 1. 数据库优化

```sql
-- 创建索引
CREATE INDEX CONCURRENTLY idx_matches_date ON matches(date);
CREATE INDEX CONCURRENTLY idx_predictions_user_id ON predictions(user_id);

-- 分析慢查询
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- 更新表统计信息
ANALYZE;
```

#### 2. Redis优化

```bash
# 监控Redis性能
redis-cli --latency
redis-cli info memory
redis-cli info stats

# 优化内存使用
redis-cli MEMORY USAGE key
redis-cli --bigkeys
```

#### 3. 应用优化

```python
# 使用连接池
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30

# 配置缓存
CACHE_CONFIG = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            }
        }
    }
}
```

### 应急响应

#### 1. 服务中断

```bash
# 快速健康检查
curl -f http://localhost:8000/api/v1/health || echo "Service down"

# 快速重启
docker-compose restart app
# 或
sudo systemctl restart football-prediction

# 回滚到上一个版本
python scripts/deploy.py --action rollback --environment production
```

#### 2. 数据库问题

```bash
# 紧急备份
pg_dump -h localhost -U fp_user football_prediction > emergency_backup.sql

# 恢复备份
psql -h localhost -U fp_user football_prediction < backup.sql

# 进入紧急模式
export EMERGENCY_MODE=true
make serve
```

#### 3. 安全事件

```bash
# 检查异常登录
sudo tail -f /var/log/auth.log | grep -i "failed\|invalid"

# 检查应用日志
grep -i "error\|exception\|failed" /var/log/football-prediction/app.log

# 立即撤销所有会话
redis-cli FLUSHDB

# 强制重新认证
export FORCE_REAUTH=true
```

## 部署检查清单

### 部署前检查

- [ ] 代码已通过所有测试
- [ ] 安全扫描通过
- [ ] 性能测试通过
- [ ] 数据库备份已完成
- [ ] SSL证书已配置
- [ ] 监控系统已启用
- [ ] 日志系统正常
- [ ] 环境变量已设置
- [ ] 依赖已安装
- [ ] 防火墙规则已配置

### 部署后验证

- [ ] 应用正常启动
- [ ] 健康检查通过
- [ ] API端点响应正常
- [ ] 数据库连接正常
- [ ] Redis缓存正常
- [ ] 监控指标正常
- [ ] 日志无错误
- [ ] SSL证书有效
- [ ] 性能指标正常
- [ ] 备份计划已设置

### 联系信息

- **技术负责人**: [姓名] <email@example.com>
- **运维团队**: <ops@example.com>
- **紧急联系**: <emergency@example.com>

---

更新时间: 2025-01-14
版本: v1.0.0
