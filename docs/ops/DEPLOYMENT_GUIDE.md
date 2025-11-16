# 足球预测系统部署指南

## 📋 概述

本文档提供足球预测系统的完整部署指南，包括开发环境、测试环境和生产环境的部署配置。

## 🏗️ 系统要求

### 最低硬件要求

| 环境 | CPU | 内存 | 存储 | 网络 |
|------|-----|------|------|------|
| 开发环境 | 2核 | 4GB | 20GB SSD | 10Mbps |
| 测试环境 | 4核 | 8GB | 50GB SSD | 50Mbps |
| 生产环境 | 8核 | 16GB | 100GB SSD | 100Mbps |

### 软件要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **Python**: 3.11+
- **Node.js**: 18+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

## 🐳 Docker部署 (推荐)

### 快速开始

#### 1. 克隆仓库
```bash
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction
```

#### 2. 环境配置
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

#### 3. 启动服务
```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

#### 4. 初始化数据库
```bash
# 运行数据库迁移
docker-compose exec app python -m alembic upgrade head

# 创建初始数据
docker-compose exec app python scripts/seed_data.py
```

### 环境变量配置

#### .env 文件示例
```bash
# 应用配置
APP_NAME=Football Prediction System
APP_VERSION=1.0.0
DEBUG=false
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# 数据库配置
DATABASE_URL=postgresql://postgres:password@db:5432/football_prediction
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis配置
REDIS_URL=redis://redis:6379/0
REDIS_CACHE_TTL=3600

# 外部API配置
ODDSPORTAL_API_KEY=your-oddsportal-api-key
FOOTBALL_API_KEY=your-football-api-key

# 安全配置
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 监控配置
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO

# 邮件配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Docker Compose配置

#### docker-compose.yml (开发环境)
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/football_prediction
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./src:/app/src
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: football_prediction
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
      - REACT_APP_WS_URL=ws://localhost:8000
    depends_on:
      - app
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - app
      - frontend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

#### docker-compose.prod.yml (生产环境)
```yaml
version: '3.8'

services:
  app:
    image: football-prediction:latest
    environment:
      - DEBUG=false
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
      - redis
    restart: always
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: always
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - static_files:/var/www/static
    depends_on:
      - app
    restart: always

volumes:
  postgres_data:
  redis_data:
  static_files:
```

## 🛠️ 手动部署

### 后端部署

#### 1. 环境准备
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev -y

# 安装系统依赖
sudo apt install postgresql postgresql-contrib redis-server nginx -y

# 安装Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

#### 2. 数据库配置
```bash
# 启动PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql << EOF
CREATE DATABASE football_prediction;
CREATE USER prediction_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE football_prediction TO prediction_user;
ALTER USER prediction_user CREATEDB;
\q
EOF
```

#### 3. 应用部署
```bash
# 创建应用用户
sudo useradd -m -s /bin/bash prediction

# 切换到应用用户
sudo su - prediction

# 克隆代码
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env

# 运行数据库迁移
python -m alembic upgrade head

# 创建systemd服务
sudo cp scripts/football-prediction.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable football-prediction
sudo systemctl start football-prediction
```

#### Systemd服务配置
```ini
# /etc/systemd/system/football-prediction.service
[Unit]
Description=Football Prediction System
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=prediction
Group=prediction
WorkingDirectory=/home/prediction/FootballPrediction
Environment=PATH=/home/prediction/FootballPrediction/venv/bin
ExecStart=/home/prediction/FootballPrediction/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 前端部署

#### 1. 构建前端
```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env.production
nano .env.production

# 构建生产版本
npm run build
```

#### 2. Nginx配置
```nginx
# /etc/nginx/sites-available/football-prediction
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/football-prediction.crt;
    ssl_certificate_key /etc/ssl/private/football-prediction.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    # 前端静态文件
    location / {
        root /home/prediction/FootballPrediction/frontend/build;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket代理
    location /realtime/ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 3. 启用站点
```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/football-prediction /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

## ☁️ 云平台部署

### AWS部署

#### 1. ECS部署
```yaml
# ecs-task-definition.json
{
  "family": "football-prediction",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "your-account.dkr.ecr.region.amazonaws.com/football-prediction:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://user:pass@rds-endpoint:5432/db"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/football-prediction",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### 2. RDS配置
```bash
# 创建RDS实例
aws rds create-db-instance \
  --db-instance-identifier football-prediction-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username postgres \
  --master-user-password securepassword \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-xxxxxxxxx \
  --db-subnet-group-name default
```

### Google Cloud Platform部署

#### 1. Cloud Run部署
```bash
# 构建并推送镜像
gcloud builds submit --tag gcr.io/PROJECT_ID/football-prediction

# 部署到Cloud Run
gcloud run deploy football-prediction \
  --image gcr.io/PROJECT_ID/football-prediction \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=postgresql://...
```

#### 2. Cloud SQL配置
```bash
# 创建Cloud SQL实例
gcloud sql instances create football-prediction-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# 创建数据库
gcloud sql databases create football_prediction \
  --instance=football-prediction-db
```

## 🔧 配置管理

### 环境分离

#### 开发环境 (.env.development)
```bash
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://postgres:password@localhost:5432/football_prediction_dev
REDIS_URL=redis://localhost:6379/0
```

#### 测试环境 (.env.test)
```bash
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql://postgres:password@test-db:5432/football_prediction_test
REDIS_URL=redis://test-redis:6379/0
```

#### 生产环境 (.env.production)
```bash
DEBUG=false
LOG_LEVEL=WARNING
DATABASE_URL=postgresql://user:securepassword@prod-db:5432/football_prediction
REDIS_URL=redis://prod-redis:6379/0
SECRET_KEY=${RANDOM_SECRET_KEY}
```

### 配置验证脚本
```python
# scripts/validate_config.py
import os
import sys
from typing import List, Dict, Any

class ConfigValidator:
    REQUIRED_VARS = [
        'SECRET_KEY',
        'DATABASE_URL',
        'REDIS_URL',
        'JWT_SECRET_KEY'
    ]

    def __init__(self, env_file: str = '.env'):
        self.env_file = env_file
        self.errors: List[str] = []

    def load_env(self) -> Dict[str, str]:
        env_vars = {}
        try:
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key] = value
        except FileNotFoundError:
            self.errors.append(f"环境文件 {self.env_file} 不存在")
        return env_vars

    def validate(self) -> bool:
        env_vars = self.load_env()

        # 检查必需变量
        for var in self.REQUIRED_VARS:
            if var not in env_vars:
                self.errors.append(f"缺少必需的环境变量: {var}")

        # 验证数据库URL
        if 'DATABASE_URL' in env_vars:
            db_url = env_vars['DATABASE_URL']
            if not db_url.startswith('postgresql://'):
                self.errors.append("DATABASE_URL 必须是PostgreSQL连接字符串")

        # 验证密钥强度
        if 'SECRET_KEY' in env_vars:
            secret_key = env_vars['SECRET_KEY']
            if len(secret_key) < 32:
                self.errors.append("SECRET_KEY 长度应至少32个字符")

        return len(self.errors) == 0

if __name__ == '__main__':
    validator = ConfigValidator()
    if validator.validate():
        print("✅ 配置验证通过")
        sys.exit(0)
    else:
        print("❌ 配置验证失败:")
        for error in validator.errors:
            print(f"  - {error}")
        sys.exit(1)
```

## 📊 监控和日志

### Prometheus监控配置

#### prometheus.yml
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'football-prediction'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
```

#### 应用指标
```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
prediction_requests = Counter('prediction_requests_total', 'Total prediction requests')
prediction_duration = Histogram('prediction_duration_seconds', 'Prediction processing time')
active_connections = Gauge('websocket_active_connections', 'Active WebSocket connections')

# 使用指标
@prediction_duration.time()
def create_prediction(match_id: int, strategy: str):
    prediction_requests.inc()
    # 预测逻辑
    pass
```

### 日志配置

#### 日志配置 (logging.yaml)
```yaml
version: 1
disable_existing_loggers: false

formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  json:
    format: '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: default
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: json
    filename: /app/logs/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  src:
    level: DEBUG
    handlers: [console, file]
    propagate: false

root:
  level: INFO
  handlers: [console, file]
```

## 🔒 安全配置

### SSL/TLS配置

#### 生成自签名证书 (开发环境)
```bash
# 创建证书目录
mkdir -p nginx/ssl

# 生成私钥
openssl genrsa -out nginx/ssl/football-prediction.key 2048

# 生成证书签名请求
openssl req -new -key nginx/ssl/football-prediction.key -out nginx/ssl/football-prediction.csr

# 生成自签名证书
openssl x509 -req -days 365 -in nginx/ssl/football-prediction.csr -signkey nginx/ssl/football-prediction.key -out nginx/ssl/football-prediction.crt
```

#### Let's Encrypt证书 (生产环境)
```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

### 防火墙配置

#### UFW配置
```bash
# 启用防火墙
sudo ufw enable

# 允许SSH
sudo ufw allow ssh

# 允许HTTP和HTTPS
sudo ufw allow 80
sudo ufw allow 443

# 限制数据库访问
sudo ufw allow from 10.0.0.0/8 to any port 5432
sudo ufw allow from 172.16.0.0/12 to any port 5432
sudo ufw allow from 192.168.0.0/16 to any port 5432

# 查看状态
sudo ufw status
```

## 🔄 备份和恢复

### 数据库备份

#### 自动备份脚本
```bash
#!/bin/bash
# scripts/backup_db.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="football_prediction"
DB_USER="postgres"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# 删除7天前的备份
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

echo "数据库备份完成: backup_$DATE.sql.gz"
```

#### 设置定时备份
```bash
# 添加到crontab
crontab -e

# 每天凌晨2点执行备份
0 2 * * * /home/prediction/FootballPrediction/scripts/backup_db.sh
```

### 数据恢复
```bash
# 恢复数据库
gunzip -c /backups/backup_20251029_020000.sql.gz | psql -U postgres -d football_prediction
```

## 🚀 性能优化

### 数据库优化

#### PostgreSQL配置优化
```sql
-- postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

#### 创建索引
```sql
-- 比赛表索引
CREATE INDEX idx_matches_date ON matches(match_date);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_league ON matches(league);

-- 预测表索引
CREATE INDEX idx_predictions_match_id ON predictions(match_id);
CREATE INDEX idx_predictions_created ON predictions(created_at);
CREATE INDEX idx_predictions_confidence ON predictions(confidence);
```

### 应用优化

#### 连接池配置
```python
# src/database/connection.py
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)
```

#### 缓存配置
```python
# src/cache/redis_cache.py
import redis.asyncio as redis

redis_client = redis.from_url(
    REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    max_connections=100,
    retry_on_timeout=True
)
```

## 🔧 故障排除

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查PostgreSQL状态
sudo systemctl status postgresql

# 检查连接
psql -U postgres -h localhost -d football_prediction

# 查看日志
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

#### 2. Redis连接失败
```bash
# 检查Redis状态
sudo systemctl status redis

# 测试连接
redis-cli ping

# 查看日志
sudo tail -f /var/log/redis/redis-server.log
```

#### 3. 应用启动失败
```bash
# 检查应用日志
docker-compose logs app

# 检查环境变量
docker-compose exec app env | grep DATABASE_URL

# 手动启动调试
docker-compose exec app python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 健康检查脚本
```bash
#!/bin/bash
# scripts/health_check.sh

# 检查API服务
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ $API_STATUS -ne 200 ]; then
    echo "API服务异常: HTTP $API_STATUS"
    exit 1
fi

# 检查数据库
DB_STATUS=$(docker-compose exec -T db pg_isready -U postgres)
if [[ $DB_STATUS != *"accepting connections"* ]]; then
    echo "数据库服务异常"
    exit 1
fi

# 检查Redis
REDIS_STATUS=$(docker-compose exec -T redis redis-cli ping)
if [ "$REDIS_STATUS" != "PONG" ]; then
    echo "Redis服务异常"
    exit 1
fi

echo "所有服务运行正常"
```

---

## 📞 技术支持

如有部署相关问题，请联系开发团队或查看相关技术文档。

**文档版本**: v1.0
**最后更新**: 2025-10-29
**维护团队**: Football Prediction Development Team
