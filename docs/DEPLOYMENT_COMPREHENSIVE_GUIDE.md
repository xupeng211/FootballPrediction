# 足球比赛结果预测系统 - 综合部署手册

## 📋 文档信息

| 项目 | 足球比赛结果预测系统部署指南 |
|------|------------------------------------|
| 版本 | v1.0 |
| 创建日期 | 2025-11-06 |
| 最后更新 | 2025-11-06 |
| 作者 | Claude Code |
| 状态 | Phase 4: 文档完善 |

---

## 🎯 部署概述

### 系统架构
本系统采用现代化的微服务架构，基于以下技术栈：
- **后端**: Python 3.11+ + FastAPI
- **数据库**: PostgreSQL 13+
- **缓存**: Redis 6+
- **队列**: 自研FIFO队列系统
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx (可选)

### 部署环境
- **开发环境**: 本地开发和测试
- **测试环境**: 自动化测试和集成测试
- **生产环境**: 生产环境部署

---

## 🛠️ 环境要求

### 最低系统要求

#### CPU
- **开发环境**: 2核心
- **测试环境**: 4核心
- **生产环境**: 8核心

#### 内存
- **开发环境**: 4GB RAM
- **测试环境**: 8GB RAM
- **生产环境**: 16GB RAM

#### 存储
- **开发环境**: 20GB可用空间
- **测试环境**: 50GB可用空间
- **生产环境**: 100GB可用空间

#### 网络
- 稳定的互联网连接
- 支持HTTPS (生产环境)
- 端口8000可用 (或可配置)

### 软件要求

#### 必需软件
- **操作系统**: Linux (Ubuntu 20.04+, CentOS 8+, 或其他Linux发行版)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 2.25+

#### 推荐软件
- **Make**: GNU Make 4.2+
- **Python**: 3.11+ (如果不使用Docker)
- **PostgreSQL**: 13+ (如果不使用Docker)
- **Redis**: 6+ (如果不使用Docker)

---

## 📦 快速部署 (Docker Compose)

### 1. 克隆项目

```bash
# 克隆代码仓库
git clone https://github.com/your-username/FootballPrediction.git
cd FootballPrediction

# 检出部署分支
git checkout main
```

### 2. 环境配置

```bash
# 复制环境配置文件
cp .env.example .env
cp .env.production.example .env.production

# 编辑配置文件
nano .env
```

#### 环境配置文件示例

```bash
# .env 文件示例
# 应用配置
APP_NAME=Football Prediction System
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=production

# 数据库配置
DATABASE_URL=postgresql://football_user:secure_password@postgres:5432/football_prediction
POSTGRES_DB=football_prediction
POSTGRES_USER=football_user
POSTGRES_PASSWORD=secure_password_here

# Redis配置
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=redis_password_here

# 安全配置
SECRET_KEY=your-super-secret-key-here-64-chars-minimum
JWT_SECRET_KEY=your-jwt-secret-key-here-64-chars-minimum
ENCRYPTION_KEY=your-encryption-key-here-32-chars

# API配置
API_V1_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json

# 性能配置
MAX_WORKERS=4
QUEUE_MAX_SIZE=10000
CACHE_TTL=3600
```

### 3. 构建和启动服务

```bash
# 构建Docker镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
docker-compose exec app alembic upgrade head

# 填充基础数据 (可选)
docker-compose exec app python scripts/seed_data.py
```

### 5. 验证部署

```bash
# 检查健康状态
curl http://localhost:8000/health

# 检查API文档
curl http://localhost:8000/docs

# 运行基础测试
docker-compose exec app python -m pytest tests/unit/ -v --tb=short
```

---

## 🔧 本地开发部署

### 1. 环境准备

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-pip -y

# 安装系统依赖
sudo apt install postgresql postgresql-contrib redis-server -y

# 安装开发工具
sudo apt install git make -y
```

### 2. 创建虚拟环境

```bash
# 创建项目目录
mkdir -p ~/projects
cd ~/projects

# 克隆项目
git clone https://github.com/your-username/FootballPrediction.git
cd FootballPrediction

# 创建虚拟环境
python3.11 -m venv .venv
source .venv/bin/activate

# 升级pip
pip install --upgrade pip
```

### 3. 安装依赖

```bash
# 安装项目依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 4. 数据库设置

```bash
# 启动PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql << EOF
CREATE DATABASE football_prediction;
CREATE USER football_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE football_prediction TO football_user;
ALTER USER football_user CREATEDB;
\q
EOF

# 启动Redis
sudo systemctl start redis
sudo systemctl enable redis
```

### 5. 配置环境变量

```bash
# 创建环境配置文件
cat > .env << EOF
APP_NAME=Football Prediction System
DEBUG=true
ENVIRONMENT=development

DATABASE_URL=postgresql://football_user:secure_password@localhost:5432/football_prediction
REDIS_URL=redis://localhost:6379/0

SECRET_KEY=dev-secret-key-for-testing-only
JWT_SECRET_KEY=dev-jwt-secret-key-for-testing-only
EOF
```

### 6. 运行应用

```bash
# 运行数据库迁移
alembic upgrade head

# 启动应用
python src/main.py

# 或使用make命令
make run
```

---

## 🏗️ 生产环境部署

### 1. 服务器准备

#### 系统配置
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要软件
sudo apt install -y \
    docker.io \
    docker-compose \
    nginx \
    ufw \
    certbot \
    python3-certbot-nginx

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 添加用户到docker组
sudo usermod -aG docker $USER
```

#### 安全配置
```bash
# 配置防火墙
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw deny 5432  # 禁止外部数据库访问

# SSH安全配置
sudo nano /etc/ssh/sshd_config
# 禁用root登录，更改默认端口等

# 配置fail2ban
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
```

### 2. SSL证书配置

#### 使用Let's Encrypt
```bash
# 获取SSL证书
sudo certbot --nginx certonly -d yourdomain.com

# 配置自动续期
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

#### 自签名证书 (开发环境)
```bash
# 创建自签名证书
sudo mkdir -p /etc/ssl/private
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/nginx-selfsigned.key \
    -out /etc/ssl/certs/nginx-selfsigned.crt
```

### 3. Nginx配置

#### 创建Nginx配置文件
```bash
sudo nano /etc/nginx/sites-available/football-prediction
```

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 静态文件服务
    location /static/ {
        alias /home/user/projects/FootballPrediction/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API文档
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
}
```

#### 启用配置
```bash
sudo ln -s /etc/nginx/sites-available/football-prediction /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. 数据库配置

#### PostgreSQL生产配置
```bash
# 修改PostgreSQL配置
sudo nano /etc/postgresql/13/main/postgresql.conf
```

```ini
# 连接设置
listen_addresses = 'localhost, *'
port = 5432
max_connections = 200

# 内存设置
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# WAL设置
wal_buffers = 16MB
checkpoint_completion_target = 0.9
wal_writer_delay = 200ms

# 日志设置
logging_collector = stderr
log_line_prefix = 'postgresql'
log_min_messages = warning
```

```bash
# 重启PostgreSQL
sudo systemctl restart postgresql
```

#### Redis生产配置
```bash
sudo nano /etc/redis/redis.conf
```

```ini
# 内存配置
maxmemory 512mb
maxmemory-policy allkeys-lru

# 持久化配置
save 900 1
save 300 10
save 60 10000

# 安全配置
requirepass your_redis_password_here
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command KEYS ""
rename-command CONFIG ""
```

```bash
# 重启Redis
sudo systemctl restart redis
```

### 5. 应用部署

#### 生产环境配置
```bash
# 创建生产配置
cp .env.production.example .env.production
nano .env.production
```

```bash
# 生产环境配置示例
APP_NAME=Football Prediction System
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=production

DATABASE_URL=postgresql://football_user:SECURE_PASSWORD@localhost:5432/football_prediction
REDIS_URL=redis://localhost:6379/0

SECRET_KEY=YOUR_SUPER_SECRET_KEY_64_CHARS_MINIMUM
JWT_SECRET_KEY=YOUR_JWT_SECRET_KEY_64_CHARS_MINIMUM
ENCRYPTION_KEY=YOUR_ENCRYPTION_KEY_32_CHARS

# 生产安全设置
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 性能配置
MAX_WORKERS=8
QUEUE_MAX_SIZE=50000
CACHE_TTL=7200

# 监控配置
SENTRY_DSN=your_sentry_dsn_here
LOG_LEVEL=WARNING
```

#### 部署服务
```bash
# 创建生产目录
sudo mkdir -p /opt/football-prediction
sudo chown $USER:$USER /opt/football-prediction

# 复制应用代码
cp -r /home/user/projects/FootballPrediction/* /opt/football-prediction/
cd /opt/football-prediction

# 构建和启动服务
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 配置systemd服务 (可选)
sudo tee /etc/systemd/system/football-prediction.service > /dev/null <<EOF
[Unit]
Description=Football Prediction System
After=docker.service
Requires=docker-compose-prod.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/football-prediction
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable football-prediction
```

---

## 🔍 监控和维护

### 1. 健康检查

#### 应用健康检查
```bash
# 检查应用状态
curl http://localhost:8000/health

# 检查系统状态
curl http://localhost:8000/health/system

# 检查数据库状态
curl http://localhost:8000/health/database
```

#### 系统监控脚本
```bash
#!/bin/bash
# monitor.sh - 系统监控脚本

# 检查服务状态
services=("docker" "nginx" "postgresql" "redis")
for service in "${services[@]}"; do
    if systemctl is-active --quiet $service; then
        echo "✅ $service is running"
    else
        echo "❌ $service is not running"
        # 发送告警通知
        # send_alert "$service is down"
    fi
done

# 检查磁盘空间
disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $disk_usage -gt 80 ]; then
    echo "⚠️  Disk usage is high: ${disk_usage}%"
    # send_alert "Disk usage is ${disk_usage}%"
fi

# 检查内存使用
memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ $memory_usage -gt 80 ]; then
    echo "⚠️  Memory usage is high: ${memory_usage}%"
    # send_alert "Memory usage is ${memory_usage}%"
fi
```

### 2. 日志管理

#### 日志配置
```yaml
# docker-compose.yml 日志配置
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
    volumes:
      - ./logs:/app/logs
```

#### 日志轮转
```bash
#!/bin/bash
# logrotate.sh - 日志轮转脚本

sudo tee /etc/logrotate.d/football-prediction > /dev/null <<EOF
/opt/football-prediction/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f /opt/football-prediction/docker-compose.prod.yml exec app kill -USR1
    endscript
}
EOF

sudo logrotate -f /etc/logrotate.d/football-prediction
```

### 3. 备份策略

#### 数据库备份
```bash
#!/bin/bash
# backup.sh - 数据库备份脚本

BACKUP_DIR="/opt/backups/football-prediction"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="football_prediction_${DATE}.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
docker-compose exec -T postgres pg_dump -U football_user football_prediction > $BACKUP_DIR/$BACKUP_FILE

# 压缩备份文件
gzip $BACKUP_DIR/$BACKUP_FILE

# 清理旧备份（保留30天）
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

#### 应用数据备份
```bash
#!/bin/bash
# app_backup.sh - 应用数据备份脚本

BACKUP_DIR="/opt/backups/football-prediction"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份配置文件
tar -czf $BACKUP_DIR/config_${DATE}.tar.gz \
    .env* \
    docker-compose*.yml \
    nginx/ \
    scripts/

# 备份静态文件
tar -czf $BACKUP_DIR/static_${DATE}.tar.gz \
    static/ \
    media/ \
    uploads/

echo "Application backup completed"
```

### 4. 自动化部署

#### CI/CD Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: |
          python -m pytest tests/ -v --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3

      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/football-prediction
            git pull origin main
            docker-compose -f docker-compose.prod.yml down
            docker-compose -f docker-compose.prod.yml build
            docker-compose -f docker-compose.prod.yml up -d
```

---

## 🚨 故障排除

### 常见问题

#### 1. 服务无法启动

**问题**: Docker容器启动失败

**解决步骤**:
```bash
# 检查容器状态
docker-compose ps

# 查看容器日志
docker-compose logs app

# 检查配置文件
cat .env

# 重新构建
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### 2. 数据库连接失败

**问题**: 应用无法连接到数据库

**解决步骤**:
```bash
# 检查数据库状态
sudo systemctl status postgresql

# 测试数据库连接
docker-compose exec app python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://football_user:secure_password@localhost:5432/football_prediction')
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"

# 检查网络连接
docker-compose exec app ping postgres
```

#### 3. Redis连接失败

**问题**: Redis连接超时

**解决步骤**:
```bash
# 检查Redis状态
sudo systemctl status redis

# 测试Redis连接
docker-compose exec app python -c "
import redis
try:
    r = redis.Redis(host='redis', port=6379, db=0)
    r.ping()
    print('Redis connection successful')
except Exception as e:
    print(f'Redis connection failed: {e}')
"

# 检查Redis配置
docker-compose exec app redis-cli ping
```

#### 4. 内存不足

**问题**: 应用内存不足导致OOM

**解决步骤**:
```bash
# 检查内存使用
free -h
docker stats

# 调整容器内存限制
nano docker-compose.yml
# 修改memory限制

# 重启服务
docker-compose restart app
```

### 性能优化

#### 1. 数据库优化
```sql
-- 添加索引
CREATE INDEX CONCURRENTLY idx_matches_date ON matches(date);
CREATE INDEX CONCURRENTLY idx_predictions_status ON predictions(status);

-- 分析查询性能
EXPLAIN ANALYZE SELECT * FROM matches WHERE date >= '2025-01-01';

-- 优化慢查询
REINDEX TABLE matches;
VACUUM ANALYZE matches;
```

#### 2. Redis优化
```bash
# 监控Redis性能
docker-compose exec redis redis-cli info stats
docker-compose exec redis redis-cli info memory

# 优化Redis配置
# 编辑 redis.conf
maxmemory 1gb
maxmemory-policy allkeys-lru
```

#### 3. 应用优化
```python
# 优化FastAPI配置
# 使用uvicorn而不是内置服务器
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# 数据库连接池配置
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
```

---

## 📋 部署检查清单

### 部署前检查

- [ ] 系统要求满足最低配置
- [ ] 所有必需软件已安装
- [ ] 防火墙和安全配置完成
- [ ] SSL证书已配置
- [ ] 数据库已创建和配置
- [ ] Redis服务正常运行

### 部署过程检查

- [ ] 代码已克隆到目标服务器
- [ ] 环境配置文件已创建
- [ ] Docker镜像构建成功
- [ ] 服务启动正常
- [ ] 数据库迁移完成
- [ ] 基础数据已填充
- [ ] 健康检查通过

### 部署后验证

- [ ] 应用健康检查通过
- [ ] 所有API端点正常响应
- [ ] 数据库连接正常
- [ ] Redis缓存正常工作
- [ ] 日志记录正常
- [ ] 监控系统配置完成
- [ ] 备份策略已实施
- [ ] SSL证书配置正确

### 性能验证

- [ ] API响应时间 <500ms
- [ ] 页面加载时间 <2秒
- [ ] 系统资源使用正常
- [ ] 数据库查询性能良好
- [ ] 队列系统运行正常

### 安全验证

- [ ] HTTPS正常工作
- [ ] 敏感数据已加密
- [ ] 访问控制已配置
- [ ] 安全头已设置
- [ ] 日志中无敏感信息
- [ ] 备份数据已加密

---

## 📞 维护计划

### 日常维护

#### 每日任务
- [ ] 检查系统健康状态
- [ ] 监控资源使用情况
- [ ] 检查日志文件
- [ ] 备份增量数据

#### 每周任务
- [ ] 运行完整备份
- [ ] 更新系统补丁
- [ ] 清理旧日志文件
- [ ] 检查备份完整性
- [ ] 性能分析和优化

#### 每月任务
- [ ] 安全漏洞扫描
- [ ] 系统性能评估
- [ ] 容量规划调整
- [ ] 文档更新
- [ ] 灾难恢复演练

### 监控指标

#### 系统指标
- CPU使用率
- 内存使用率
- 磁盘使用率
- 网络流量
- 服务可用性

#### 应用指标
- API响应时间
- 错误率
- 队列处理速度
- 数据库性能
- 缓存命中率

#### 业务指标
- 预测准确率
- 用户访问量
- 数据更新频率
- 系统负载

---

## 📚 参考文档

### 项目文档
- [SRS需求规格说明书](../SRS_FOOTBALL_PREDICTION_SYSTEM.md)
- [系统架构文档](../architecture/UPDATED_ARCHITECTURE_V2.md)
- [API文档](../API_COMPREHENSIVE_GUIDE.md)

### 技术文档
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [PostgreSQL文档](https://www.postgresql.org/docs/)
- [Redis文档](https://redis.io/documentation/)
- [Docker文档](https://docs.docker.com/)
- [Nginx文档](https://nginx.org/en/docs/)

---

## 📝 更新日志

### v1.0.0 (2025-11-06)
- ✅ 初始部署文档创建
- ✅ Docker Compose部署指南
- ✅ 本地开发环境部署
- ✅ 生产环境部署
- ✅ Nginx反向代理配置
- ✅ SSL证书配置
- ✅ 监控和维护指南
- ✅ 故障排除指南

### 未来版本计划
- v1.1.0: Kubernetes部署指南
- v1.2.0: 高可用架构
- v1.3.0: 多区域部署
- v2.0.0: 云原生架构

---

**文档版本**: v1.0
**最后更新**: 2025-11-06
**状态**: Phase 4: 文档完善
**维护者**: Claude Code