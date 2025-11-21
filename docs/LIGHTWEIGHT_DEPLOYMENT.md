# 🚀 轻量级部署快速启动指南

## 📋 概述

本指南帮助您快速部署足球预测系统的轻量级版本，包含前端、后端、数据库和缓存的完整全栈应用。

### 🎯 适用场景
- 开发环境快速搭建
- 演示和原型验证
- 小团队内部使用
- 资源受限的部署环境

## ⚡ 快速启动 (5分钟搞定)

### 前置要求
- Docker 20.0+
- Docker Compose 2.0+
- 至少 2GB 可用内存
- 至少 2GB 可用磁盘空间

### 一键启动
```bash
# 克隆项目
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 启动轻量级全栈环境
docker-compose -f docker-compose.lightweight.yml up -d

# 等待服务启动完成 (约2-3分钟)
docker-compose -f docker-compose.lightweight.yml logs -f
```

### 🌐 访问地址
启动成功后，可以通过以下地址访问：

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **API文档(ReDoc)**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## 🔧 使用Makefile命令

如果您更喜欢使用Makefile，我们也提供了便捷的命令：

```bash
# 启动轻量级环境
make docker.up.lightweight

# 查看服务日志
make docker.logs.lightweight

# 停止服务
make docker.down.lightweight

# 重启服务
make docker.restart.lightweight
```

## 📊 服务架构

### 服务组件
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │  PostgreSQL     │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   Database      │
│   Port: 3000    │    │   Port: 8000    │    │   Port: 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │     Redis       │
                       │     Cache       │
                       │   Port: 6379    │
                       └─────────────────┘
```

### 服务特性
- **前端**: React 19.2.0 + TypeScript + Ant Design
- **后端**: FastAPI + 轻量级Python依赖
- **数据库**: PostgreSQL 15 (性能优化配置)
- **缓存**: Redis 7 (内存优化配置)

## 🛠️ 高级配置

### 环境变量自定义
创建 `.env.lightweight` 文件来自定义配置：

```bash
# 数据库配置
POSTGRES_DB=football_prediction
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password

# 后端配置
SECRET_KEY=your_secret_key_here
ENVIRONMENT=production
LOG_LEVEL=INFO

# Redis配置
REDIS_PASSWORD=your_redis_password  # 可选
```

### 资源限制调整
编辑 `docker-compose.lightweight.yml` 中的资源限制：

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 512M    # 最大内存
          cpus: '0.5'     # 最大CPU核心数
```

### 端口映射修改
如果需要修改默认端口：

```yaml
services:
  frontend:
    ports:
      - "3001:80"  # 修改前端端口为3001

  backend:
    ports:
      - "8001:8000"  # 修改后端端口为8001
```

## 📈 性能优化

### 数据库优化
轻量级配置已包含以下PostgreSQL优化：
- 连接池优化 (max_connections: 200)
- 缓存优化 (shared_buffers: 256MB)
- 查询优化 (effective_cache_size: 1GB)

### Redis优化
缓存配置优化：
- 内存限制: 200MB
- 淘汰策略: allkeys-lru
- 持久化: AOF + RDB

### 应用优化
后端服务优化：
- 资源限制: 内存512MB, CPU 0.5核心
- 健康检查: 30秒间隔
- 重启策略: unless-stopped

## 🔍 监控和调试

### 查看服务状态
```bash
# 检查所有服务状态
docker-compose -f docker-compose.lightweight.yml ps

# 查看详细状态
docker-compose -f docker-compose.lightweight.yml ps --services

# 查看资源使用情况
docker stats
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose -f docker-compose.lightweight.yml logs

# 查看特定服务日志
docker-compose -f docker-compose.lightweight.yml logs backend
docker-compose -f docker-compose.lightweight.yml logs frontend
docker-compose -f docker-compose.lightweight.yml logs db
docker-compose -f docker-compose.lightweight.yml logs redis

# 实时跟踪日志
docker-compose -f docker-compose.lightweight.yml logs -f
```

### 健康检查
```bash
# 检查后端健康状态
curl http://localhost:8000/health

# 检查前端状态
curl http://localhost:3000/health

# 检查数据库连接
docker-compose -f docker-compose.lightweight.yml exec db pg_isready -U postgres

# 检查Redis连接
docker-compose -f docker-compose.lightweight.yml exec redis redis-cli ping
```

## 🛡️ 安全配置

### 基础安全
- 更改默认密码
- 使用环境变量管理敏感信息
- 定期更新依赖

### 网络安全
- 仅暴露必要端口
- 使用Docker网络隔离
- 配置防火墙规则

### 生产环境安全
```bash
# 1. 设置强密码
POSTGRES_PASSWORD=your_strong_password
SECRET_KEY=your_very_long_secret_key

# 2. 启用Redis认证
# 编辑 config/redis.conf 取消注释:
# requirepass your_redis_password

# 3. 使用HTTPS (生产环境)
# 配置反向代理 (Nginx/Apache) 处理SSL
```

## 🔄 数据管理

### 数据备份
```bash
# 备份PostgreSQL数据库
docker-compose -f docker-compose.lightweight.yml exec db pg_dump -U postgres football_prediction > backup.sql

# 备份Redis数据
docker-compose -f docker-compose.lightweight.yml exec redis redis-cli BGSAVE
docker cp $(docker-compose -f docker-compose.lightweight.yml ps -q redis):/data/dump.rdb ./redis_backup.rdb
```

### 数据恢复
```bash
# 恢复PostgreSQL数据库
docker-compose -f docker-compose.lightweight.yml exec -T db psql -U postgres football_prediction < backup.sql

# 恢复Redis数据
docker cp ./redis_backup.rdb $(docker-compose -f docker-compose.lightweight.yml ps -q redis):/data/dump.rdb
docker-compose -f docker-compose.lightweight.yml restart redis
```

## 🔧 故障排除

### 常见问题

#### 1. 端口冲突
```bash
# 错误: Port already in use
# 解决: 修改 docker-compose.lightweight.yml 中的端口映射
```

#### 2. 内存不足
```bash
# 错误: Container killed due to memory limit
# 解决: 增加 Docker 内存限制或调整服务内存配置
```

#### 3. 数据库连接失败
```bash
# 检查数据库状态
docker-compose -f docker-compose.lightweight.yml logs db

# 重启数据库服务
docker-compose -f docker-compose.lightweight.yml restart db
```

#### 4. 前端构建失败
```bash
# 清理并重新构建前端
docker-compose -f docker-compose.lightweight.yml exec frontend npm install
docker-compose -f docker-compose.lightweight.yml up --build frontend
```

### 日志分析
```bash
# 查看错误日志
docker-compose -f docker-compose.lightweight.yml logs --tail=50

# 查看特定时间范围的日志
docker-compose -f docker-compose.lightweight.yml logs --since="2023-01-01T00:00:00"
```

## 📚 进阶用法

### 开发模式
```bash
# 开发模式启动 (挂载源码卷，支持热重载)
docker-compose -f docker-compose.yml -f docker-compose.lightweight.yml up
```

### 生产部署
```bash
# 使用生产配置
docker-compose -f docker-compose.lightweight.yml -f docker-compose.prod.yml up -d
```

### 扩展服务
```bash
# 扩展后端服务实例
docker-compose -f docker-compose.lightweight.yml up -d --scale backend=3
```

## 📞 支持和帮助

### 获取帮助
```bash
# 查看所有可用命令
make help

# 查看项目文档
cat docs/LIGHTWEIGHT_DEPLOYMENT.md

# 查看Docker日志
docker-compose -f docker-compose.lightweight.yml logs
```

### 报告问题
如果遇到问题，请提供以下信息：
- Docker和Docker Compose版本
- 错误日志
- 系统资源使用情况
- 使用的配置文件

### 社区支持
- GitHub Issues: [项目Issues页面]
- 文档: [项目Wiki页面]
- 讨论: [GitHub Discussions]

---

**注意**: 轻量级部署适用于开发和演示环境。生产环境请使用完整的生产配置。

**更新时间**: 2025-11-22
**版本**: 1.0