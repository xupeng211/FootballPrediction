# 🚀 FootballPrediction 生产部署指南

本文档提供FootballPrediction项目的完整生产环境部署指南。

---

## 📋 部署前检查清单

### ✅ 代码质量要求
- [ ] **零错误状态**: 确保代码质量检查通过 (`ruff check src/ tests/`)
- [ ] **基础语法**: 验证Python语法正确性 (`python3 -m py_compile src/**/*.py`)
- [ ] **核心功能**: 确保核心模块正常导入和运行
- [ ] **安全扫描**: 执行安全检查并修复高风险问题

### ✅ 环境准备
- [ ] **Docker环境**: 确保Docker和Docker Compose已安装
- [ ] **服务器资源**: 至少2GB RAM, 2 CPU cores
- [ ] **域名配置**: 准备好域名和SSL证书
- [ ] **数据库**: PostgreSQL数据库实例
- [ ] **缓存服务**: Redis缓存服务

### ✅ 安全配置
- [ ] **环境变量**: 准备所有必需的环境变量
- [ ] **SSL证书**: 配置HTTPS证书
- [ ] **防火墙**: 配置服务器防火墙规则
- [ ] **备份策略**: 建立数据库备份机制

---

## 🏗️ 部署架构

### 生产环境架构
```
Internet
    ↓
[Nginx Load Balancer] (端口 80/443)
    ↓
[Application Container] (FootballPrediction API)
    ↓
[PostgreSQL Database] (端口 5432)
    ↓
[Redis Cache] (端口 6379)
```

### 服务组件
- **Nginx**: 反向代理和负载均衡
- **Application**: FastAPI应用服务
- **PostgreSQL**: 主数据库
- **Redis**: 缓存和会话存储
- **Monitoring**: 监控和日志收集

---

## 🚀 部署步骤

### 1. 服务器环境准备

#### 安装Docker
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 配置防火墙
```bash
# 开放必要端口
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

### 2. 代码部署

#### 克隆代码
```bash
# 克隆生产代码
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 检出生产版本
git checkout v1.0.0-production
```

#### 构建镜像
```bash
# 构建生产镜像
docker build -t footballprediction:production .

# 或使用GitHub构建的镜像
docker pull footballprediction/production:latest
```

### 3. 环境配置

#### 创建环境变量文件
```bash
# 创建生产环境配置
cp .env.example .env.production
```

编辑 `.env.production`:
```bash
# 应用配置
NODE_ENV=production
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000

# 数据库配置
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=footballprediction_prod
DATABASE_USER=fp_user
DATABASE_PASSWORD=your_secure_password

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# 安全配置
SECRET_KEY=your_very_long_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# 监控配置
SENTRY_DSN=your_sentry_dsn_here
LOG_LEVEL=INFO

# CORS配置
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 4. 数据库设置

#### 创建数据库
```bash
# 连接到PostgreSQL
sudo -u postgres psql

# 创建数据库和用户
CREATE DATABASE footballprediction_prod;
CREATE USER fp_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE footballprediction_prod TO fp_user;
\q
```

#### 运行数据库迁移
```bash
# 使用Docker运行迁移
docker run --rm \
  --network host \
  -v $(pwd):/app \
  -w /app \
  footballprediction:production \
  python -m alembic upgrade head
```

### 5. 启动服务

#### 使用Docker Compose启动
```bash
# 创建生产环境docker-compose文件
cat > docker-compose.prod.yml << EOF
version: '3.8'

services:
  app:
    image: footballprediction/production:latest
    container_name: footballprediction-app
    restart: unless-stopped
    env_file:
      - .env.production
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    networks:
      - fp-network

  db:
    image: postgres:15
    container_name: footballprediction-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: footballprediction_prod
      POSTGRES_USER: fp_user
      POSTGRES_PASSWORD: your_secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - fp-network

  redis:
    image: redis:7-alpine
    container_name: footballprediction-redis
    restart: unless-stopped
    command: redis-server --requirepass your_redis_password
    volumes:
      - redis_data:/data
    networks:
      - fp-network

  nginx:
    image: nginx:alpine
    container_name: footballprediction-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - app
    networks:
      - fp-network

volumes:
  postgres_data:
  redis_data:

networks:
  fp-network:
    driver: bridge
EOF

# 启动服务
docker-compose -f docker-compose.prod.yml up -d
```

#### 配置Nginx
```bash
# 创建nginx配置目录
mkdir -p nginx

# 创建nginx配置
cat > nginx/nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    upstream footballprediction {
        server app:8000;
    }

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://\$server_name\$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            proxy_pass http://footballprediction;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        location /docs {
            proxy_pass http://footballprediction/docs;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }
}
EOF
```

---

## 🔍 部署验证

### 健康检查
```bash
# 检查服务状态
docker-compose -f docker-compose.prod.yml ps

# 检查应用日志
docker-compose -f docker-compose.prod.yml logs app

# 检查API健康状态
curl https://yourdomain.com/health

# 检查API文档
curl https://yourdomain.com/docs
```

### 功能测试
```bash
# 测试预测API
curl -X POST "https://yourdomain.com/predict" \
  -H "Content-Type: application/json" \
  -d '{"home_team": "Team A", "away_team": "Team B"}'

# 测试数据库连接
curl https://yourdomain.com/health/database

# 测试缓存连接
curl https://yourdomain.com/health/cache
```

---

## 📊 监控和维护

### 日志管理
```bash
# 查看应用日志
docker-compose -f docker-compose.prod.yml logs -f app

# 查看数据库日志
docker-compose -f docker-compose.prod.yml logs -f db

# 查看Nginx日志
docker-compose -f docker-compose.prod.yml logs -f nginx
```

### 性能监控
```bash
# 检查容器资源使用
docker stats

# 检查系统资源
top
htop

# 检查磁盘使用
df -h
```

### 数据库维护
```bash
# 备份数据库
docker exec footballprediction-db pg_dump -U fp_user footballprediction_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# 清理旧备份
find . -name "backup_*.sql" -mtime +7 -delete

# 数据库维护
docker exec footballprediction-db psql -U fp_user -d footballprediction_prod -c "VACUUM ANALYZE;"
```

---

## 🚨 故障处理

### 常见问题和解决方案

#### 1. 应用启动失败
```bash
# 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看详细错误日志
docker-compose -f docker-compose.prod.yml logs app

# 检查环境变量
docker-compose -f docker-compose.prod.yml exec app env | grep -E "(DATABASE|REDIS|SECRET)"
```

#### 2. 数据库连接失败
```bash
# 测试数据库连接
docker-compose -f docker-compose.prod.yml exec app python -c "
import os
from sqlalchemy import create_engine
url = f\"postgresql://{os.getenv('DATABASE_USER')}:{os.getenv('DATABASE_PASSWORD')}@{os.getenv('DATABASE_HOST')}/{os.getenv('DATABASE_NAME')}\"
engine = create_engine(url)
engine.connect()
print('✅ 数据库连接成功')
"
```

#### 3. Redis连接失败
```bash
# 测试Redis连接
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# 检查Redis配置
docker-compose -f docker-compose.prod.yml exec redis redis-cli config get requirepass
```

#### 4. 高负载处理
```bash
# 增加应用实例
docker-compose -f docker-compose.prod.yml up -d --scale app=3

# 检查负载均衡
curl -H "X-Forwarded-For: 1.2.3.4" https://yourdomain.com/health
```

### 紧急回滚
```bash
# 回滚到上一个版本
git checkout PREVIOUS_VERSION_TAG
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# 或者使用回滚脚本
./scripts/emergency_rollback.sh
```

---

## 🔄 更新部署

### 滚动更新
```bash
# 拉取最新代码
git fetch origin
git checkout NEW_VERSION_TAG

# 重新构建并部署
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# 运行数据库迁移
docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head
```

### 蓝绿部署
```bash
# 部署到绿色环境
docker-compose -f docker-compose.green.yml up -d

# 验证绿色环境
./scripts/verify_deployment.sh green

# 切换流量
./scripts/switch_traffic.sh green

# 清理蓝色环境
docker-compose -f docker-compose.blue.yml down
```

---

## 📞 联系支持

### 技术支持
- **GitHub Issues**: https://github.com/xupeng211/FootballPrediction/issues
- **项目文档**: https://docs.footballprediction.com
- **监控面板**: https://monitor.footballprediction.com

### 紧急联系
- **运维团队**: ops@footballprediction.com
- **技术负责人**: tech@footballprediction.com

---

## 📋 附录

### 环境变量参考
详见 `.env.example` 文件中的完整环境变量配置。

### 安全配置建议
1. 使用强密码和长密钥
2. 定期更新SSL证书
3. 配置备份策略
4. 设置访问日志监控
5. 实施网络分段

### 性能优化建议
1. 启用数据库连接池
2. 配置Redis集群
3. 使用CDN加速静态资源
4. 实施缓存策略
5. 监控和调优数据库查询

---

*文档版本: v1.0.0*
*最后更新: 2025-11-11*
*维护者: FootballPrediction运维团队*
