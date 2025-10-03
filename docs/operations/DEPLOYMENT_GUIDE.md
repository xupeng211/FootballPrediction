# Football Prediction System - 生产环境部署指南

## 概述

本指南详细说明如何在生产环境中部署Football Prediction System。

## 系统要求

### 最低配置

- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 100GB SSD
- **网络**: 1Gbps带宽

### 推荐配置

- **CPU**: 8核心
- **内存**: 16GB RAM
- **存储**: 200GB SSD
- **网络**: 10Gbps带宽

### 软件依赖

- Ubuntu 20.04 LTS / CentOS 8 / RHEL 8
- Docker 20.10+
- Docker Compose 2.0+
- Kubernetes 1.24+ (可选)
- Python 3.11

## 部署架构

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx/HAProxy]
    end

    subgraph "Application Layer"
        APP1[App Instance 1]
        APP2[App Instance 2]
        APP3[App Instance 3]
    end

    subgraph "Cache Layer"
        REDIS[Redis Cluster]
    end

    subgraph "Database Layer"
        DB_MASTER[(PostgreSQL Master)]
        DB_SLAVE[(PostgreSQL Slave)]
    end

    subgraph "Monitoring"
        PROM[Prometheus]
        GRAF[Grafana]
        ALERT[AlertManager]
    end

    LB --> APP1
    LB --> APP2
    LB --> APP3

    APP1 --> REDIS
    APP2 --> REDIS
    APP3 --> REDIS

    APP1 --> DB_MASTER
    APP2 --> DB_MASTER
    APP3 --> DB_MASTER

    DB_MASTER --> DB_SLAVE

    APP1 --> PROM
    APP2 --> PROM
    APP3 --> PROM

    PROM --> GRAF
    PROM --> ALERT
```

## 部署步骤

### 1. 环境准备

#### 1.1 系统更新

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

#### 1.2 安装Docker

```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 添加用户到docker组
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 1.3 创建部署目录

```bash
sudo mkdir -p /opt/football-prediction
sudo chown $USER:$USER /opt/football-prediction
cd /opt/football-prediction
```

### 2. 获取代码

```bash
# 克隆代码仓库
git clone https://github.com/your-org/football-prediction.git .

# 切换到生产分支
git checkout production

# 验证标签
git tag -v v1.0.0
```

### 3. 配置环境变量

#### 3.1 创建生产环境文件

```bash
cp .env.example .env.production
```

#### 3.2 编辑环境变量

```bash
nano .env.production
```

关键配置项：

```bash
# 环境
ENVIRONMENT=production
DEBUG=false

# 数据库配置
DATABASE_URL=postgresql://user:password@db-master:5432/football_prod
DATABASE_REPLICA_URL=postgresql://user:password@db-slave:5432/football_prod

# Redis配置
REDIS_URL=redis://redis-cluster:6379/0
REDIS_PASSWORD=your-redis-password

# 安全密钥
SECRET_KEY=your-256-bit-secret-key
JWT_SECRET_KEY=your-jwt-secret-key

# API配置
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://app.football-prediction.com

# 监控配置
METRICS_ENABLED=true
METRICS_PORT=9090

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json

# 性能配置
WORKERS=4
WORKER_CONNECTIONS=1000
KEEPALIVE_TIMEOUT=65

# 缓存配置
CACHE_DEFAULT_TTL=300
MEMORY_CACHE_SIZE=10000

# 限流配置
RATE_LIMIT_PER_MINUTE=1000
RATE_LIMIT_BURST=100
```

### 4. Docker部署

#### 4.1 创建生产Dockerfile

```dockerfile
# Dockerfile.production
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.lock .
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.lock

# 复制应用代码
COPY src/ ./src/
COPY scripts/ ./scripts/

# 创建非root用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["gunicorn", "src.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

#### 4.2 创建Docker Compose文件

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.production
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    depends_on:
      - db-master
      - redis-cluster
    volumes:
      - ./logs:/app/logs
    networks:
      - football-network
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G

  db-master:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: football_prod
      POSTGRES_USER: football
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - db-master-data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - football-network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  db-slave:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: football_prod
      POSTGRES_USER: football
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      PGUSER: postgres
      POSTGRES_MASTER_SERVICE: db-master
    volumes:
      - db-slave-data:/var/lib/postgresql/data
    networks:
      - football-network
    depends_on:
      - db-master

  redis-cluster:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    networks:
      - football-network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - app
    networks:
      - football-network

  prometheus:
    image: prom/prometheus:latest
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    networks:
      - football-network

  grafana:
    image: grafana/grafana:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    networks:
      - football-network

volumes:
  db-master-data:
  db-slave-data:
  redis-data:
  prometheus-data:
  grafana-data:

networks:
  football-network:
    driver: bridge
```

#### 4.3 启动服务

```bash
# 构建镜像
docker-compose -f docker-compose.production.yml build

# 启动服务
docker-compose -f docker-compose.production.yml up -d

# 查看状态
docker-compose -f docker-compose.production.yml ps

# 查看日志
docker-compose -f docker-compose.production.yml logs -f app
```

### 5. Kubernetes部署

#### 5.1 创建命名空间

```bash
kubectl create namespace football-prediction
```

#### 5.2 创建ConfigMap

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: football-config
  namespace: football-prediction
data:
  ENVIRONMENT: "production"
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  REDIS_URL: "redis://redis-service:6379/0"
  DATABASE_URL: "postgresql://football:password@postgres-service:5432/football_prod"
```

#### 5.3 创建Secret

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: football-secret
  namespace: football-prediction
type: Opaque
data:
  SECRET_KEY: <base64-encoded-secret>
  JWT_SECRET_KEY: <base64-encoded-jwt-secret>
  DB_PASSWORD: <base64-encoded-db-password>
  REDIS_PASSWORD: <base64-encoded-redis-password>
```

#### 5.4 创建Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: football-api
  namespace: football-prediction
spec:
  replicas: 3
  selector:
    matchLabels:
      app: football-api
  template:
    metadata:
      labels:
        app: football-api
    spec:
      containers:
      - name: api
        image: football-prediction:production
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: football-config
        - secretRef:
            name: football-secret
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 40
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 20
          periodSeconds: 10
```

#### 5.5 创建Service

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: football-api-service
  namespace: football-prediction
spec:
  selector:
    app: football-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

#### 5.6 创建Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: football-api-ingress
  namespace: football-prediction
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "1000"
spec:
  tls:
  - hosts:
    - api.football-prediction.com
    secretName: football-api-tls
  rules:
  - host: api.football-prediction.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: football-api-service
            port:
              number: 80
```

#### 5.7 应用K8s配置

```bash
kubectl apply -f k8s/
```

### 6. 数据库初始化

#### 6.1 运行迁移

```bash
# Docker部署
docker-compose exec app python -m alembic upgrade head

# Kubernetes部署
kubectl exec -it deployment/football-api -- python -m alembic upgrade head
```

#### 6.2 加载初始数据

```bash
# Docker部署
docker-compose exec app python scripts/seed_database.py

# Kubernetes部署
kubectl exec -it deployment/football-api -- python scripts/seed_database.py
```

### 7. 监控配置

#### 7.1 Prometheus配置

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'football-api'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-cluster:6379']

  - job_name: 'postgres'
    static_configs:
      - targets: ['db-master:5432']
```

#### 7.2 Grafana仪表板

导入预配置的仪表板：
- API性能仪表板
- 数据库性能仪表板
- 系统资源仪表板
- 业务指标仪表板

### 8. 备份策略

#### 8.1 数据库备份

```bash
# 创建备份脚本
cat > scripts/backup-db.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"
mkdir -p $BACKUP_DIR

# 数据库备份
docker-compose exec -T db-master pg_dump -U football football_prod | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# 保留30天
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete
EOF

# 添加到crontab
0 2 * * * /opt/football-prediction/scripts/backup-db.sh
```

#### 8.2 Redis备份

```bash
# Redis配置中启用AOF
echo "appendonly yes" >> redis.conf
```

### 9. 安全配置

#### 9.1 SSL/TLS配置

```nginx
# nginx/nginx.conf
server {
    listen 443 ssl http2;
    server_name api.football-prediction.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 9.2 防火墙规则

```bash
# Ubuntu UFW
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# CentOS firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## 验证部署

### 1. 健康检查

```bash
# 检查API健康状态
curl https://api.football-prediction.com/health

# 检查详细健康状态
curl https://api.football-prediction.com/health/detailed
```

### 2. 功能测试

```bash
# 测试认证
curl -X POST https://api.football-prediction.com/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&username=test&password=test"

# 测试预测
curl -H "Authorization: Bearer <token>" \
  https://api.football-prediction.com/v1/predictions/matches/12345
```

### 3. 性能测试

```bash
# 使用Apache Bench
ab -n 1000 -c 100 https://api.football-prediction.com/health

# 使用wrk
wrk -t12 -c400 -d30s https://api.football-prediction.com/health
```

## 运维操作

### 滚动更新

```bash
# Docker Compose
docker-compose -f docker-compose.production.yml pull
docker-compose -f docker-compose.production.yml up -d --no-deps app

# Kubernetes
kubectl set image deployment/football-api api=football-prediction:v1.1.0
kubectl rollout status deployment/football-api
```

### 扩容缩容

```bash
# Docker Compose
docker-compose -f docker-compose.production.yml up -d --scale app=5

# Kubernetes
kubectl scale deployment football-api --replicas=5
```

### 故障恢复

```bash
# 重启服务
docker-compose -f docker-compose.production.yml restart app

# Kubernetes
kubectl rollout restart deployment/football-api
```

## 故障排查

### 常见问题

1. **服务无法启动**
   - 检查环境变量配置
   - 查看容器日志
   - 验证数据库连接

2. **数据库连接失败**
   - 检查数据库服务状态
   - 验证连接字符串
   - 检查防火墙规则

3. **高延迟**
   - 检查数据库索引
   - 监控缓存命中率
   - 分析慢查询日志

### 日志查看

```bash
# Docker Compose
docker-compose -f docker-compose.production.yml logs -f app

# Kubernetes
kubectl logs -f deployment/football-api -n football-prediction
```

## 联系支持

- **技术支持**: support@football-prediction.com
- **紧急响应**: emergency@football-prediction.com
- **文档**: https://docs.football-prediction.com

---

最后更新: 2025-01-02
版本: 1.0.0