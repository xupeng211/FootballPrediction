# 🚀 Football Prediction System - 部署指南

## 📋 目录

- [部署概览](#部署概览)
- [环境准备](#环境准备)
- [Docker部署](#docker部署)
- [Kubernetes部署](#kubernetes部署)
- [云平台部署](#云平台部署)
- [监控和日志](#监控和日志)
- [安全配置](#安全配置)
- [性能优化](#性能优化)
- [备份和恢复](#备份和恢复)
- [故障排除](#故障排除)

---

## 🎯 部署概览

### 支持的部署方式
- **Docker Compose**: 开发和小规模生产环境
- **Kubernetes**: 企业级生产环境
- **云服务**: AWS, Azure, GCP托管部署
- **传统部署**: 物理机/虚拟机直接部署

### 系统架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   负载均衡器     │    │   API网关       │    │   应用服务      │
│   (Nginx/HAProxy)│◄──►│   (Kong/Traefik)│◄──►│   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   静态资源      │    │   缓存层        │    │   数据库        │
│   (CDN)         │    │   (Redis)       │    │   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 资源要求

#### 最小配置
- **CPU**: 2核心
- **内存**: 4GB RAM
- **存储**: 20GB SSD
- **网络**: 100Mbps

#### 推荐配置
- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 100GB SSD
- **网络**: 1Gbps

#### 生产配置
- **CPU**: 8核心+
- **内存**: 16GB+ RAM
- **存储**: 500GB+ SSD
- **网络**: 10Gbps

---

## 🛠️ 环境准备

### 系统要求
- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 2.30+

### 服务器初始化

#### Ubuntu/Debian
```bash
#!/bin/bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y curl wget git htop vim

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 创建应用目录
sudo mkdir -p /opt/football-prediction
sudo chown $USER:$USER /opt/football-prediction

# 配置防火墙
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw --force enable
```

#### CentOS/RHEL
```bash
#!/bin/bash
# 更新系统
sudo yum update -y

# 安装基础工具
sudo yum install -y curl wget git htop vim

# 安装Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 创建应用目录
sudo mkdir -p /opt/football-prediction
sudo chown $USER:$USER /opt/football-prediction

# 配置防火墙
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### SSL证书准备

#### Let's Encrypt自动证书
```bash
# 安装certbot
sudo apt install certbot python3-certbot-nginx  # Ubuntu/Debian
# 或
sudo yum install certbot python3-certbot-nginx   # CentOS/RHEL

# 获取证书（需要域名已解析到服务器）
sudo certbot certonly --nginx -d yourdomain.com -d api.yourdomain.com

# 设置自动续期
sudo crontab -e
# 添加以下行：
# 0 12 * * * /usr/bin/certbot renew --quiet
```

#### 自签名证书（开发环境）
```bash
# 创建证书目录
sudo mkdir -p /etc/ssl/private

# 生成私钥
sudo openssl genrsa -out /etc/ssl/private/football-prediction.key 2048

# 生成证书
sudo openssl req -new -x509 -key /etc/ssl/private/football-prediction.key -out /etc/ssl/certs/football-prediction.crt -days 365
```

---

## 🐳 Docker部署

### 开发环境部署

#### 1. 项目克隆和配置
```bash
# 进入项目目录
cd /opt/football-prediction

# 克隆项目
git clone https://github.com/your-org/football-prediction.git .

# 复制环境配置
cp .env.example .env

# 编辑配置文件
vim .env
```

#### 2. 开发环境配置
```bash
# .env
COMPOSE_PROJECT_NAME=football-prediction-dev
ENVIRONMENT=development
DEBUG=true

# 数据库配置
POSTGRES_DB=football_pred_dev
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=dev_password
DATABASE_URL=postgresql://dev_user:dev_password@postgres:5432/football_pred_dev

# Redis配置
REDIS_URL=redis://redis:6379

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# 安全配置
SECRET_KEY=dev-secret-key-change-in-production
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

#### 3. 启动开发环境
```bash
# 构建和启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app

# 初始化数据库
docker-compose exec app alembic upgrade head
docker-compose exec app python scripts/seed_data.py
```

### 生产环境部署

#### 1. 生产环境配置
```bash
# .env.production
COMPOSE_PROJECT_NAME=football-prediction-prod
ENVIRONMENT=production
DEBUG=false

# 数据库配置（使用强密码）
POSTGRES_DB=football_pred
POSTGRES_USER=prod_user
POSTGRES_PASSWORD=$(openssl rand -base64 32)
DATABASE_URL=postgresql://prod_user:${POSTGRES_PASSWORD}@postgres:5432/football_pred

# Redis配置
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=$(openssl rand -base64 32)

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# 安全配置
SECRET_KEY=$(openssl rand -base64 64)
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com

# SSL配置
SSL_CERT_PATH=/etc/ssl/certs/football-prediction.crt
SSL_KEY_PATH=/etc/ssl/private/football-prediction.key

# 监控配置
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 16)
```

#### 2. 生产Docker Compose
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    restart: unless-stopped
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
    volumes:
      - ./ssl:/etc/ssl:ro
      - ./logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - app-network
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - app
    networks:
      - app-network

  postgres:
    image: postgres:15
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - app-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  prometheus:
    image: prom/prometheus:latest
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    networks:
      - app-network

  grafana:
    image: grafana/grafana:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    networks:
      - app-network

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  app-network:
    driver: bridge
```

#### 3. 生产Dockerfile
```dockerfile
# Dockerfile.prod
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["gunicorn", "src.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

#### 4. Nginx配置
```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    # HTTP重定向到HTTPS
    server {
        listen 80;
        server_name yourdomain.com api.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS配置
    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        # SSL配置
        ssl_certificate /etc/ssl/football-prediction.crt;
        ssl_certificate_key /etc/ssl/football-prediction.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # 安全头
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

        # 静态文件
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # API代理
        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 超时设置
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }

    # API子域名
    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;

        # SSL配置（同上）
        ssl_certificate /etc/ssl/football-prediction.crt;
        ssl_certificate_key /etc/ssl/football-prediction.key;
        ssl_protocols TLSv1.2 TLSv1.3;

        # API代理
        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

#### 5. 部署脚本
```bash
#!/bin/bash
# deploy.sh

set -e

echo "🚀 开始部署Football Prediction System..."

# 检查环境
if [ ! -f ".env.production" ]; then
    echo "❌ .env.production文件不存在"
    exit 1
fi

# 拉取最新代码
echo "📥 拉取最新代码..."
git pull origin main

# 构建镜像
echo "🔨 构建Docker镜像..."
docker-compose -f docker-compose.prod.yml build --no-cache

# 停止旧服务
echo "⏹️ 停止旧服务..."
docker-compose -f docker-compose.prod.yml down

# 启动新服务
echo "▶️ 启动新服务..."
docker-compose -f docker-compose.prod.yml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 数据库迁移
echo "🗄️ 执行数据库迁移..."
docker-compose -f docker-compose.prod.yml exec -T app alembic upgrade head

# 健康检查
echo "🏥 执行健康检查..."
if curl -f http://localhost/health; then
    echo "✅ 部署成功！"
else
    echo "❌ 健康检查失败"
    docker-compose -f docker-compose.prod.yml logs app
    exit 1
fi

echo "🎉 Football Prediction System部署完成！"
echo "📊 监控面板: http://yourdomain.com:3000"
echo "📈 Prometheus: http://yourdomain.com:9090"
```

---

## ☸️ Kubernetes部署

### 集群准备

#### 1. 节点要求
- **Master节点**: 2CPU, 4GB RAM, 20GB存储
- **Worker节点**: 4CPU, 8GB RAM, 100GB存储
- **网络**: Calico/Flannel CNI

#### 2. 安装依赖
```bash
# 安装kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# 安装Helm
curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
sudo mv linux-amd64/helm /usr/local/bin/

# 添加Helm仓库
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 应用部署

#### 1. 命名空间和配置
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: football-prediction
  labels:
    name: football-prediction

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: football-prediction
data:
  ENVIRONMENT: "production"
  DEBUG: "false"
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  CORS_ORIGINS: "https://yourdomain.com"
  ALLOWED_HOSTS: "yourdomain.com"

---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: football-prediction
type: Opaque
data:
  DATABASE_URL: <base64-encoded-database-url>
  REDIS_URL: <base64-encoded-redis-url>
  SECRET_KEY: <base64-encoded-secret-key>
  SSL_CERT_PATH: <base64-encoded-ssl-cert-path>
  SSL_KEY_PATH: <base64-encoded-ssl-key-path>
```

#### 2. 数据库部署
```yaml
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: football-prediction
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_DB
          value: "football_pred"
        - name: POSTGRES_USER
          value: "postgres"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 20Gi

---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: football-prediction
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
```

#### 3. Redis部署
```yaml
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: football-prediction
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command: ["redis-server", "--requirepass", "$(REDIS_PASSWORD)", "--appendonly", "yes"]
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: password
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: football-prediction
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: football-prediction
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

#### 4. 应用部署
```yaml
# k8s/app.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: football-prediction-api
  namespace: football-prediction
spec:
  replicas: 3
  selector:
    matchLabels:
      app: football-prediction-api
  template:
    metadata:
      labels:
        app: football-prediction-api
    spec:
      containers:
      - name: api
        image: football-prediction:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3

---
apiVersion: v1
kind: Service
metadata:
  name: football-prediction-api
  namespace: football-prediction
spec:
  selector:
    app: football-prediction-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: football-prediction-api-hpa
  namespace: football-prediction
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: football-prediction-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### 5. Ingress配置
```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: football-prediction-ingress
  namespace: football-prediction
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  tls:
  - hosts:
    - yourdomain.com
    - api.yourdomain.com
    secretName: football-prediction-tls
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: football-prediction-api
            port:
              number: 80
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: football-prediction-api
            port:
              number: 80
```

#### 6. 部署脚本
```bash
#!/bin/bash
# k8s-deploy.sh

set -e

echo "🚀 开始Kubernetes部署..."

# 应用配置
echo "📝 应用配置..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 部署数据库
echo "🗄️ 部署数据库..."
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml

# 等待数据库就绪
echo "⏳ 等待数据库就绪..."
kubectl wait --for=condition=ready pod -l app=postgres -n football-prediction --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n football-prediction --timeout=300s

# 部署应用
echo "🚀 部署应用..."
kubectl apply -f k8s/app.yaml

# 等待应用就绪
echo "⏳ 等待应用就绪..."
kubectl wait --for=condition=ready pod -l app=football-prediction-api -n football-prediction --timeout=300s

# 配置Ingress
echo "🌐 配置Ingress..."
kubectl apply -f k8s/ingress.yaml

# 数据库迁移
echo "🗄️ 执行数据库迁移..."
kubectl exec -n football-prediction deployment/football-prediction-api -- alembic upgrade head

# 验证部署
echo "✅ 验证部署..."
kubectl get pods -n football-prediction
kubectl get services -n football-prediction
kubectl get ingress -n football-prediction

echo "🎉 Kubernetes部署完成！"
```

---

## ☁️ 云平台部署

### AWS部署

#### 1. ECS部署
```yaml
# aws/ecs-task-definition.json
{
  "family": "football-prediction",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "football-prediction-api",
      "image": "your-account.dkr.ecr.region.amazonaws.com/football-prediction:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:football-prediction/db-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/football-prediction",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

#### 2. AWS CDK部署
```typescript
// aws/lib/football-prediction-stack.ts
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';

export class FootballPredictionStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // VPC
    const vpc = new ec2.Vpc(this, 'FootballPredictionVPC', {
      maxAzs: 2,
      natGateways: 1,
    });

    // ECS Cluster
    const cluster = new ecs.Cluster(this, 'FootballPredictionCluster', {
      vpc,
      clusterName: 'football-prediction',
    });

    // RDS PostgreSQL
    const database = new rds.DatabaseInstance(this, 'FootballPredictionDB', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_15,
      }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
      vpc,
      databaseName: 'football_pred',
      allocatedStorage: 20,
      storageType: rds.StorageType.GP2,
      backupRetention: cdk.Duration.days(7),
      deletionProtection: false,
    });

    // ElastiCache Redis
    const redis = new elasticache.CfnCacheCluster(this, 'FootballPredictionRedis', {
      cacheNodeType: 'cache.t3.micro',
      engine: 'redis',
      numCacheNodes: 1,
      vpcSecurityGroupIds: [vpc.vpcDefaultSecurityGroup],
    });

    // Fargate Task Definition
    const taskDefinition = new ecs.FargateTaskDefinition(this, 'FootballPredictionTask', {
      memoryLimitMiB: 1024,
      cpu: 512,
    });

    const container = taskDefinition.addContainer('football-prediction-api', {
      image: ecs.ContainerImage.fromRegistry('your-account.dkr.ecr.region.amazonaws.com/football-prediction:latest'),
      portMappings: [{ containerPort: 8000 }],
      logging: new ecs.AwsLogDriver({
        streamPrefix: 'football-prediction',
      }),
    });

    container.addEnvironment('DATABASE_URL', database.instanceEndpoint.socketAddress);
    container.addEnvironment('REDIS_URL', `redis://${redis.attrRedisEndpoint.address}:${redis.attrRedisEndpoint.port}`);

    // Fargate Service
    const service = new ecs.FargateService(this, 'FootballPredictionService', {
      cluster,
      taskDefinition,
      desiredCount: 2,
      assignPublicIp: false,
    });
  }
}
```

### Azure部署

#### 1. Azure Container Instances
```bash
#!/bin/bash
# azure/deploy-aci.sh

# 变量定义
RESOURCE_GROUP="football-prediction-rg"
LOCATION="eastus"
CONTAINER_NAME="football-prediction-api"
IMAGE="yourregistry.azurecr.io/football-prediction:latest"

# 创建资源组
az group create --name $RESOURCE_GROUP --location $LOCATION

# 部署容器实例
az container create \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_NAME \
  --image $IMAGE \
  --cpu 1 \
  --memory 2 \
  --ports 8000 \
  --environment-variables \
    ENVIRONMENT=production \
    DATABASE_URL=$DATABASE_URL \
    REDIS_URL=$REDIS_URL \
    SECRET_KEY=$SECRET_KEY \
  --dns-name-label football-prediction-$RANDOM

# 获取FQDN
FQDN=$(az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query "ipAddress.fqdn" --output tsv)

echo "🌐 应用已部署: https://$FQDN:8000"
```

### GCP部署

#### 1. Cloud Run部署
```bash
#!/bin/bash
# gcp/deploy-cloudrun.sh

# 变量定义
PROJECT_ID="your-project-id"
REGION="us-central1"
SERVICE_NAME="football-prediction-api"
IMAGE_NAME="football-prediction"

# 构建和推送镜像
gcloud builds submit --tag gcr.io/$PROJECT_ID/$IMAGE_NAME

# 部署到Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets DATABASE_URL=football-prediction-db-url:latest \
  --set-secrets REDIS_URL=football-prediction-redis-url:latest \
  --set-secrets SECRET_KEY=football-prediction-secret-key:latest

# 获取服务URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)")

echo "🌐 应用已部署: $SERVICE_URL"
```

---

## 📊 监控和日志

### Prometheus配置

#### 1. Prometheus配置文件
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'football-prediction-api'
    static_configs:
      - targets: ['app:8000']
    metrics_path: /metrics
    scrape_interval: 15s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

#### 2. 告警规则
```yaml
# monitoring/alert_rules.yml
groups:
  - name: football-prediction
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }} seconds"

      - alert: DatabaseConnectionFailure
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failure"
          description: "PostgreSQL database is down"

      - alert: RedisConnectionFailure
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis connection failure"
          description: "Redis cache is down"

      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value }}%"
```

### Grafana仪表板

#### 1. Grafana配置
```json
{
  "dashboard": {
    "title": "Football Prediction System",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{status}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"4..\"}[5m])",
            "legendFormat": "4xx errors"
          },
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends",
            "legendFormat": "Active connections"
          }
        ]
      },
      {
        "title": "Redis Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "redis_memory_used_bytes",
            "legendFormat": "Memory used"
          }
        ]
      }
    ]
  }
}
```

### 日志聚合

#### 1. ELK Stack配置
```yaml
# logging/elasticsearch.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    ports:
      - "5044:5044"
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

#### 2. Logstash配置
```ruby
# logstash/pipeline/logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "football-prediction" {
    json {
      source => "message"
    }

    date {
      match => [ "timestamp", "ISO8601" ]
    }

    if [level] == "ERROR" {
      mutate {
        add_tag => [ "error" ]
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "football-prediction-%{+YYYY.MM.dd}"
  }

  if "error" in [tags] {
    email {
      to => "admin@yourdomain.com"
      subject => "Football Prediction Error Alert"
      body => "Error occurred: %{message}"
    }
  }
}
```

---

## 🔒 安全配置

### 应用安全

#### 1. 环境变量加密
```bash
# 使用Docker secrets或Kubernetes secrets
# 不要在环境变量中存储敏感信息

# 加密敏感配置
echo "your-secret-key" | openssl enc -aes-256-cbc -base64 -salt > secret.key

# 解密配置
openssl enc -aes-256-cbc -d -base64 -in secret.key -out secret.decrypted
```

#### 2. API安全配置
```python
# src/security/middleware.py
from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
import time

# 限流配置
limiter = Limiter(key_func=get_remote_address)

# 安全中间件
async def security_middleware(request: Request, call_next):
    # 添加安全头
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"

    return response

# 请求验证
async def validate_request(request: Request):
    # 验证User-Agent
    user_agent = request.headers.get("User-Agent", "")
    if not user_agent or len(user_agent) < 10:
        raise HTTPException(status_code=400, detail="Invalid User-Agent")

    # 验证Content-Length
    content_length = request.headers.get("Content-Length")
    if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=413, detail="Payload too large")
```

#### 3. 数据库安全
```sql
-- 创建专用数据库用户
CREATE USER api_user WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE football_pred TO api_user;
GRANT USAGE ON SCHEMA public TO api_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO api_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO api_user;

-- 行级安全策略
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_predictions ON predictions
    FOR ALL TO api_user
    USING (user_id = current_setting('app.current_user_id')::uuid);

-- 审计日志
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id UUID,
    action VARCHAR(50),
    table_name VARCHAR(50),
    record_id UUID,
    old_values JSONB,
    new_values JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, old_values, new_values)
    VALUES (
        current_setting('app.current_user_id')::uuid,
        TG_OP,
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW) ELSE NULL END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
```

### 网络安全

#### 1. 防火墙配置
```bash
# UFW配置
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许SSH
sudo ufw allow 22/tcp

# 允许HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 限制数据库访问
sudo ufw allow from 10.0.0.0/8 to any port 5432
sudo ufw allow from 10.0.0.0/8 to any port 6379

# 启用防火墙
sudo ufw enable
```

#### 2. Fail2ban配置
```bash
# /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
port = http,https
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10
findtime = 600
```

---

## ⚡ 性能优化

### 应用优化

#### 1. 连接池优化
```python
# src/config/database.py
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,          # 连接池大小
    max_overflow=30,       # 最大溢出连接数
    pool_pre_ping=True,    # 连接前ping检查
    pool_recycle=3600,     # 连接回收时间
    echo=settings.debug
)
```

#### 2. 缓存策略
```python
# src/cache/strategy.py
from typing import Optional
import redis.asyncio as redis
import json
import hashlib

class CacheManager:
    def __init__(self):
        self.redis = redis.from_url(settings.redis_url)

    async def get_or_set(
        self,
        key: str,
        func,
        expire: int = 3600,
        cache_null: bool = False
    ):
        """获取缓存或设置新值"""
        # 尝试从缓存获取
        cached = await self.redis.get(key)
        if cached is not None:
            return json.loads(cached)

        # 执行函数获取数据
        result = await func()

        # 缓存结果（包括null值如果需要）
        if result is not None or cache_null:
            await self.redis.setex(
                key,
                expire,
                json.dumps(result, default=str)
            )

        return result

    async def invalidate_pattern(self, pattern: str):
        """按模式批量删除缓存"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

# 使用装饰器
def cache_result(expire: int = 3600, key_prefix: str = ""):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()}"

            # 获取或设置缓存
            return await cache_manager.get_or_set(
                cache_key,
                lambda: func(*args, **kwargs),
                expire
            )
        return wrapper
    return decorator
```

#### 3. 异步优化
```python
# src/utils/async_utils.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Callable, Any

class AsyncTaskManager:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def gather_with_concurrency(
        self,
        tasks: List[Callable],
        max_concurrency: int = 10
    ) -> List[Any]:
        """并发执行任务，限制并发数"""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def limited_task(task):
            async with semaphore:
                if asyncio.iscoroutinefunction(task):
                    return await task()
                else:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(self.executor, task)

        return await asyncio.gather(*(limited_task(task) for task in tasks))

    async def batch_process(
        self,
        items: List[Any],
        processor: Callable,
        batch_size: int = 100
    ) -> List[Any]:
        """批量处理数据"""
        results = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await self.gather_with_concurrency([
                lambda item=item: processor(item) for item in batch
            ])
            results.extend(batch_results)

        return results

# 使用示例
async def process_predictions_batch(predictions: List[PredictionRequest]):
    task_manager = AsyncTaskManager()

    # 批量处理预测请求
    results = await task_manager.batch_process(
        predictions,
        process_single_prediction,
        batch_size=50
    )

    return results
```

### 数据库优化

#### 1. 索引优化
```sql
-- 创建复合索引
CREATE INDEX CONCURRENTLY idx_predictions_user_created
ON predictions(user_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_matches_status_date
ON matches(status, match_date)
WHERE status IN ('scheduled', 'live');

-- 部分索引
CREATE INDEX CONCURRENTLY idx_active_users
ON users(id)
WHERE subscription_plan != 'free';

-- 表达式索引
CREATE INDEX CONCURRENTLY idx_predictions_date_trunc
ON predictions(date_trunc('day', created_at));

-- 自动分析表统计信息
CREATE OR REPLACE FUNCTION auto_analyze_tables()
RETURNS void AS $$
BEGIN
    ANALYZE predictions;
    ANALYZE matches;
    ANALYZE users;
END;
$$ LANGUAGE plpgsql;

-- 设置定时任务
SELECT cron.schedule('auto-analyze', '0 2 * * *', 'SELECT auto_analyze_tables();');
```

#### 2. 查询优化
```python
# src/repositories/optimized_queries.py
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload, joinedload

class OptimizedPredictionRepository:
    async def get_user_predictions_paginated(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20
    ):
        """分页获取用户预测（优化版）"""
        offset = (page - 1) * page_size

        # 使用窗口函数优化分页
        query = select(
            Prediction,
            func.count().over().label('total_count')
        ).where(
            Prediction.user_id == user_id
        ).order_by(
            Prediction.created_at.desc()
        ).offset(offset).limit(page_size)

        result = await self.session.execute(query)
        rows = result.all()

        if not rows:
            return [], 0

        total_count = rows[0].total_count
        predictions = [row.Prediction for row in rows]

        return predictions, total_count

    async def get_popular_predictions(
        self,
        limit: int = 10,
        time_range_days: int = 7
    ):
        """获取热门预测（优化版）"""
        cutoff_date = datetime.now() - timedelta(days=time_range_days)

        # 使用CTE优化复杂查询
        cte = select(
            Prediction.match_id,
            func.count().label('prediction_count')
        ).where(
            and_(
                Prediction.created_at >= cutoff_date,
                Prediction.predicted_winner.isnot(None)
            )
        ).group_by(
            Prediction.match_id
        ).order_by(
            func.count().desc()
        ).limit(limit).cte('popular_predictions')

        query = select(
            Match,
            cte.c.prediction_count
        ).join(
            cte, Match.id == cte.c.match_id
        ).options(
            selectinload(Match.home_team),
            selectinload(Match.away_team)
        )

        result = await self.session.execute(query)
        return result.all()
```

---

## 💾 备份和恢复

### 数据库备份

#### 1. 自动备份脚本
```bash
#!/bin/bash
# scripts/backup_database.sh

set -e

# 配置
BACKUP_DIR="/backups/postgresql"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="football_pred_backup_${TIMESTAMP}.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
echo "📦 开始数据库备份..."
pg_dump -h localhost -U postgres -d football_pred | gzip > "${BACKUP_DIR}/${BACKUP_FILE}.gz"

# 验证备份文件
if [ -f "${BACKUP_DIR}/${BACKUP_FILE}.gz" ]; then
    echo "✅ 备份成功: ${BACKUP_FILE}.gz"
else
    echo "❌ 备份失败"
    exit 1
fi

# 清理旧备份
echo "🧹 清理${RETENTION_DAYS}天前的备份..."
find $BACKUP_DIR -name "*.gz" -mtime +$RETENTION_DAYS -delete

# 上传到云存储（可选）
if [ ! -z "$AWS_S3_BUCKET" ]; then
    echo "☁️ 上传备份到S3..."
    aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}.gz" "s3://${AWS_S3_BUCKET}/backups/"
fi

echo "🎉 数据库备份完成！"
```

#### 2. 增量备份
```bash
#!/bin/bash
# scripts/incremental_backup.sh

WAL_ARCHIVE_DIR="/backups/wal_archive"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建WAL归档目录
mkdir -p $WAL_ARCHIVE_DIR

# 配置PostgreSQL WAL归档
echo "archive_command = 'cp %p ${WAL_ARCHIVE_DIR}/%f'" >> /var/lib/postgresql/data/postgresql.conf

# 重启PostgreSQL以应用配置
docker-compose restart postgres

# 创建基础备份
pg_basebackup -h localhost -U postgres -D "${WAL_ARCHIVE_DIR}/base_backup_${TIMESTAMP}" -Ft -z -P

echo "✅ 增量备份配置完成"
```

### 数据恢复

#### 1. 完整恢复
```bash
#!/bin/bash
# scripts/restore_database.sh

set -e

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ 请提供备份文件路径"
    echo "用法: $0 <backup_file>"
    exit 1
fi

echo "🔄 开始数据库恢复..."

# 停止应用服务
docker-compose stop app

# 删除现有数据库
echo "🗑️ 删除现有数据库..."
docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS football_pred;"

# 创建新数据库
echo "📝 创建新数据库..."
docker-compose exec postgres psql -U postgres -c "CREATE DATABASE football_pred;"

# 恢复数据
echo "📥 恢复数据..."
if [[ $BACKUP_FILE == *.gz ]]; then
    gunzip -c $BACKUP_FILE | docker-compose exec -T postgres psql -U postgres -d football_pred
else
    docker-compose exec -T postgres psql -U postgres -d football_pred < $BACKUP_FILE
fi

# 重启应用服务
docker-compose start app

echo "✅ 数据库恢复完成！"
```

#### 2. 时间点恢复
```bash
#!/bin/bash
# scripts/point_in_time_recovery.sh

TARGET_TIME=$1  # 格式: "2025-11-10 15:30:00"

if [ -z "$TARGET_TIME" ]; then
    echo "❌ 请提供目标时间"
    echo "用法: $0 \"YYYY-MM-DD HH:MM:SS\""
    exit 1
fi

echo "🕒 开始时间点恢复到: $TARGET_TIME"

# 停止PostgreSQL
docker-compose stop postgres

# 创建恢复配置
cat > /var/lib/postgresql/data/recovery.conf << EOF
restore_command = 'cp ${WAL_ARCHIVE_DIR}/%f %p'
recovery_target_time = '$TARGET_TIME'
EOF

# 启动PostgreSQL（恢复模式）
docker-compose start postgres

# 监控恢复进程
echo "⏳ 等待恢复完成..."
while docker-compose exec postgres pg_isready -q; do
    sleep 5
    echo "恢复中..."
done

echo "✅ 时间点恢复完成！"
```

---

## 🔧 故障排除

### 常见问题诊断

#### 1. 服务健康检查
```bash
#!/bin/bash
# scripts/health_check.sh

echo "🏥 Football Prediction System 健康检查"

# 检查Docker服务
echo "📋 Docker服务状态:"
docker-compose ps

# 检查API健康状态
echo "🌐 API健康状态:"
curl -f http://localhost:8000/health || echo "❌ API服务异常"

# 检查数据库连接
echo "🗄️ 数据库连接:"
docker-compose exec postgres pg_isready || echo "❌ 数据库连接失败"

# 检查Redis连接
echo "💾 Redis连接:"
docker-compose exec redis redis-cli ping || echo "❌ Redis连接失败"

# 检查磁盘空间
echo "💽 磁盘使用情况:"
df -h

# 检查内存使用
echo "🧠 内存使用情况:"
free -h

# 检查网络连接
echo "🌐 网络连接:"
netstat -tlnp | grep -E ':(80|443|8000|5432|6379)'

# 查看最近的错误日志
echo "📋 最近的错误日志:"
docker-compose logs --tail=50 app | grep -i error || echo "✅ 无错误日志"
```

#### 2. 性能诊断
```bash
#!/bin/bash
# scripts/performance_diagnosis.sh

echo "📊 性能诊断报告"

# 检查CPU使用率
echo "🔥 CPU使用率:"
top -bn1 | grep "Cpu(s)" | awk '{print "CPU使用率:", $2}'

# 检查内存使用
echo "🧠 内存使用:"
free -h

# 检查数据库性能
echo "🗄️ 数据库性能:"
docker-compose exec postgres psql -U postgres -d football_pred -c "
SELECT
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC
LIMIT 10;"

# 检查慢查询
echo "🐌 慢查询:"
docker-compose exec postgres psql -U postgres -d football_pred -c "
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 5;"

# 检查Redis性能
echo "💾 Redis性能:"
docker-compose exec redis redis-cli info memory | grep used_memory_human
docker-compose exec redis redis-cli info stats | grep keyspace

# 检查API响应时间
echo "🌐 API响应时间:"
curl -w "响应时间: %{time_total}s\n" -o /dev/null -s http://localhost:8000/health
```

#### 3. 日志分析
```bash
#!/bin/bash
# scripts/log_analysis.sh

LOG_DIR="./logs"
TODAY=$(date +%Y-%m-%d)

echo "📋 日志分析报告 - $TODAY"

# API访问统计
echo "📊 API访问统计:"
if [ -f "$LOG_DIR/access.log" ]; then
    awk '{print $1}' "$LOG_DIR/access.log" | sort | uniq -c | sort -nr | head -10
fi

# 错误统计
echo "❌ 错误统计:"
if [ -f "$LOG_DIR/error.log" ]; then
    grep -c "ERROR" "$LOG_DIR/error.log" || echo "无错误记录"
fi

# 数据库慢查询
echo "🐌 数据库慢查询:"
if [ -f "$LOG_DIR/postgresql.log" ]; then
    grep "slow query" "$LOG_DIR/postgresql.log" | tail -5
fi

# 应用异常
echo "⚠️ 应用异常:"
if [ -f "$LOG_DIR/app.log" ]; then
    grep -i "exception\|error" "$LOG_DIR/app.log" | tail -10
fi
```

### 紧急恢复程序

#### 1. 服务重启脚本
```bash
#!/bin/bash
# scripts/emergency_restart.sh

set -e

echo "🚨 紧急重启程序"

# 记录重启时间
echo "重启时间: $(date)" >> /var/log/football-prediction-restarts.log

# 停止所有服务
echo "⏹️ 停止所有服务..."
docker-compose down

# 清理系统资源
echo "🧹 清理系统资源..."
docker system prune -f

# 重新启动服务
echo "▶️ 重新启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 执行健康检查
echo "🏥 执行健康检查..."
./scripts/health_check.sh

echo "✅ 紧急重启完成！"
```

#### 2. 数据库修复
```bash
#!/bin/bash
# scripts/repair_database.sh

echo "🔧 数据库修复程序"

# 检查数据库一致性
echo "🔍 检查数据库一致性..."
docker-compose exec postgres psql -U postgres -d football_pred -c "
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;"

# 重建索引
echo "🔨 重建索引..."
docker-compose exec postgres psql -U postgres -d football_pred -c "
REINDEX DATABASE football_pred;"

# 更新表统计信息
echo "📊 更新统计信息..."
docker-compose exec postgres psql -U postgres -d football_pred -c "
ANALYZE;"

# 检查数据完整性
echo "✅ 检查数据完整性..."
docker-compose exec postgres psql -U postgres -d football_pred -c "
SELECT
    conname,
    conrelid::regclass as table_name,
    conkey
FROM pg_constraint
WHERE contype = 'f'
AND convalidated = false;"

echo "✅ 数据库修复完成！"
```

---

## 📞 支持和维护

### 监控告警
- **Slack集成**: 错误通知发送到Slack频道
- **邮件通知**: 关键错误发送邮件告警
- **短信通知**: 紧急故障发送短信提醒

### 定期维护
- **每日**: 备份数据库，清理日志文件
- **每周**: 分析性能指标，更新统计信息
- **每月**: 安全更新，性能调优
- **每季度**: 容量规划，架构优化

### 联系支持
- **技术支持**: support@football-prediction.com
- **紧急响应**: emergency@football-prediction.com
- **文档**: https://docs.football-prediction.com

---

**部署指南版本**: v1.0.0
**最后更新**: 2025-11-10
**适用于**: Football Prediction System v1.0+
