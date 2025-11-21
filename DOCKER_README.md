# 🐳 足球预测系统 Docker 部署指南

## 快速开始 (一键启动)

### 前置要求
- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

### 一键启动
```bash
# 启动所有服务
./start-docker.sh
```

### 一键停止
```bash
# 停止所有服务
./stop-docker.sh

# 停止并清理镜像
./stop-docker.sh --clean-images
```

## 🚀 服务访问地址

启动成功后，您可以通过以下地址访问各个服务：

| 服务 | 地址 | 描述 |
|------|------|------|
| 🌐 前端应用 | http://localhost:3000 | React 前端界面 |
| 🔧 后端API | http://localhost:8000 | FastAPI 后端服务 |
| 📖 API文档 | http://localhost:8000/docs | 交互式 API 文档 |
| ❤️ 健康检查 | http://localhost:8000/health | 后端健康状态 |

## 🏗️ 架构组件

### 服务架构
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Frontend  │    │   Backend   │    │  Database   │
│  (Nginx)    │────│ (FastAPI)   │──── │(PostgreSQL) │
│   :80       │    │   :8000     │    │   :5432     │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                   ┌─────────────┐
                   │    Redis    │
                   │    Cache    │
                   │   :6379    │
                   └─────────────┘
```

### 容器详情

#### 1. Frontend (frontend)
- **镜像**: 自定义构建 (Node.js + Nginx)
- **端口**: 3000:80
- **功能**: React 应用，通过 Nginx 提供静态文件服务
- **特性**:
  - 多阶段构建优化镜像大小
  - Gzip 压缩
  - API 代理到后端
  - React Router 支持

#### 2. Backend (backend)
- **镜像**: 自定义构建 (Python 3.11)
- **端口**: 8000:8000
- **功能**: FastAPI 应用，提供 REST API
- **特性**:
  - 基于 Python 3.11-slim
  - 健康检查
  - 非root用户运行
  - 完整依赖安装

#### 3. Database (db)
- **镜像**: postgres:15
- **端口**: 5432:5432
- **功能**: PostgreSQL 数据库
- **配置**:
  - 数据库名: `football_prediction`
  - 用户名: `postgres`
  - 密码: `football_prediction_2024`

#### 4. Cache (redis)
- **镜像**: redis:7-alpine
- **端口**: 6379:6379
- **功能**: Redis 缓存服务
- **特性**: 数据持久化

## ⚙️ 配置说明

### 环境变量
主要配置在 `.env.docker` 文件中：

```bash
# 数据库配置
DATABASE_URL=postgresql://postgres:football_prediction_2024@db:5432/football_prediction

# Redis 配置
REDIS_URL=redis://redis:6379/0

# 应用配置
SECRET_KEY=football_prediction_secret_key_2024
ENVIRONMENT=production
```

### 端口映射
- **前端**: 3000 → 80 (Nginx)
- **后端**: 8000 → 8000 (FastAPI)
- **数据库**: 5432 → 5432 (PostgreSQL)
- **缓存**: 6379 → 6379 (Redis)

## 🔧 管理命令

### 查看服务状态
```bash
docker-compose -f docker-compose.simple.yml ps
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose -f docker-compose.simple.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.simple.yml logs -f backend
docker-compose -f docker-compose.simple.yml logs -f frontend
docker-compose -f docker-compose.simple.yml logs -f db
```

### 重启服务
```bash
# 重启所有服务
docker-compose -f docker-compose.simple.yml restart

# 重启特定服务
docker-compose -f docker-compose.simple.yml restart backend
```

### 进入容器
```bash
# 进入后端容器
docker exec -it football_prediction_backend bash

# 进入数据库容器
docker exec -it football_prediction_db psql -U postgres -d football_prediction

# 进入 Redis 容器
docker exec -it football_prediction_redis redis-cli
```

## 🔍 故障排除

### 常见问题

#### 1. 端口冲突
```bash
# 检查端口占用
netstat -tulpn | grep :3000
netstat -tulpn | grep :8000

# 解决方案：停止占用端口的服务或修改 docker-compose.yml 中的端口映射
```

#### 2. 容器启动失败
```bash
# 查看容器状态
docker-compose -f docker-compose.simple.yml ps

# 查看错误日志
docker-compose -f docker-compose.simple.yml logs [service_name]
```

#### 3. 数据库连接问题
```bash
# 检查数据库是否运行
docker exec football_prediction_db pg_isready -U postgres

# 重置数据库数据
docker-compose -f docker-compose.simple.yml down -v
docker-compose -f docker-compose.simple.yml up -d db
```

#### 4. 内存不足
```bash
# 检查系统资源
docker stats

# 清理未使用的资源
docker system prune -a
```

### 性能优化

#### 1. 生产环境调优
- 增加数据库连接池大小
- 调整 Redis 内存限制
- 启用 Nginx 缓存
- 配置日志轮转

#### 2. 监控
```bash
# 实时监控容器资源使用
docker stats

# 监控磁盘使用
docker system df
```

## 🔐 安全说明

### 生产环境建议
1. **更改默认密码**: 修改 `.env.docker` 中的数据库密码
2. **使用 HTTPS**: 在生产环境中配置 SSL 证书
3. **网络安全**: 使用防火墙限制访问端口
4. **定期更新**: 定期更新 Docker 镜像和依赖

### 数据备份
```bash
# 备份数据库
docker exec football_prediction_db pg_dump -U postgres football_prediction > backup.sql

# 恢复数据库
docker exec -i football_prediction_db psql -U postgres football_prediction < backup.sql
```

## 📝 开发指南

### 自定义构建
```bash
# 仅构建后端
docker-compose -f docker-compose.simple.yml build backend

# 仅构建前端
docker-compose -f docker-compose.simple.yml build frontend

# 重新构建（无缓存）
docker-compose -f docker-compose.simple.yml build --no-cache
```

### 调试模式
```bash
# 启用调试日志
export LOG_LEVEL=DEBUG
./start-docker.sh

# 或者修改 docker-compose.simple.yml 中的环境变量
```

---

**注意**: 这是生产就绪的 Docker 配置。如需开发环境的热重载功能，请使用项目原有的 `docker-compose.yml` 文件。