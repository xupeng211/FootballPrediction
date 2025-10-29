# Football Prediction System 部署指南

## 概述
本文档提供了Football Prediction系统的完整部署指南，包括开发、测试和生产环境的部署步骤。

## 环境要求

### 系统要求
- CPU: 最少2核心，推荐4核心
- 内存: 最少4GB，推荐8GB
- 存储: 最少20GB可用空间
- 操作系统: Linux (Ubuntu 20.04+), macOS, Windows 10+

### 软件要求
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+ (用于本地开发)
- Git 2.30+

## 快速部署

### 1. 克隆仓库
```bash
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction
```

### 2. 环境配置
```bash
# 复制环境配置
cp .env.example .env

# 编辑环境变量
vim .env
```

### 3. 启动服务
```bash
# 开发环境
docker-compose up -d

# 生产环境
docker-compose -f docker-compose.prod.yml up -d
```

### 4. 验证部署
```bash
# 检查服务状态
docker-compose ps

# 健康检查
curl http://localhost:8000/health
```

## 生产环境部署

### 1. 环境准备
```bash
# 创建生产环境配置
cp environments/.env.production .env

# 设置必要的环境变量
export DB_PASSWORD="your-secure-password"
export SECRET_KEY="your-secret-key"
```

### 2. 启动生产服务
```bash
# 使用生产配置启动
docker-compose -f docker-compose.prod.yml up -d

# 初始化数据库
docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head
```

### 3. 配置反向代理
```bash
# 启动Nginx
docker-compose -f docker-compose.prod.yml up -d nginx
```

## 监控和维护

### 应用监控
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- AlertManager: http://localhost:9093

### 日志查看
```bash
# 查看应用日志
docker-compose logs -f app

# 查看所有服务日志
docker-compose logs -f
```

### 数据备份
```bash
# 数据库备份
docker-compose exec db pg_dump -U postgres football_prediction_prod > backup.sql

# 恢复数据库
docker-compose exec -T db psql -U postgres football_prediction_prod < backup.sql
```

## 故障排除

### 常见问题
1. **服务启动失败**: 检查端口占用和配置文件
2. **数据库连接失败**: 验证数据库服务状态和连接配置
3. **内存不足**: 调整Docker容器资源限制

### 健康检查
```bash
# 应用健康检查
curl -f http://localhost:8000/health

# 数据库连接检查
docker-compose exec db pg_isready -U postgres

# Redis连接检查
docker-compose exec redis redis-cli ping
```

---

*更新时间: 2025-10-30*
