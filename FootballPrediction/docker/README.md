# Docker配置说明

## 概述

本项目使用统一的Docker配置，支持多环境部署。通过环境变量和Docker Compose profiles实现灵活的服务编排。

## 目录结构

```
docker/
├── Dockerfile                   # 统一Dockerfile（多阶段构建）
├── docker-compose.yml           # 基础服务配置
├── docker-compose.override.yml  # 开发环境覆盖配置
├── entrypoint.sh               # 容器入口脚本
├── environments/               # 环境变量配置
│   ├── .env.development       # 开发环境
│   ├── .env.staging          # 预发布环境
│   ├── .env.production       # 生产环境
│   └── .env.test             # 测试环境
└── README.md                  # 本文档
```

## 快速开始

### 开发环境

```bash
# 启动开发环境（自动加载override配置）
docker-compose up

# 启动特定服务
docker-compose up -d db redis
docker-compose up app

# 查看日志
docker-compose logs -f app
```

### 生产环境

```bash
# 设置环境变量
export ENV=production

# 启动生产环境（包含Nginx、监控等）
docker-compose --profile production up -d

# 仅启动核心服务
docker-compose --profile production up app db redis
```

### 测试环境

```bash
# 运行测试
ENV=test docker-compose --profile test up --rm app

# 或使用测试数据库
docker-compose --profile test --profile tools up -d
docker-compose run --rm app pytest
```

## 服务配置

### 核心服务

- **app**: 主应用服务
- **db**: PostgreSQL数据库
- **redis**: Redis缓存

### 可选服务（通过profiles控制）

- **nginx**: 反向代理（production、staging）
- **prometheus**: 监控（monitoring、production）
- **grafana**: 监控面板（monitoring、production）
- **loki**: 日志收集（logging、production）
- **celery-worker**: Celery工作进程（celery、production）
- **celery-beat**: Celery定时任务（celery、production）

### 开发工具（tools profile）

- **adminer**: 数据库管理工具 (http://localhost:8080)
- **redis-commander**: Redis管理工具 (http://localhost:8081)
- **mailhog**: 邮件模拟器 (http://localhost:8025)
- **pyroscope**: 性能分析 (http://localhost:4040)

## 环境变量说明

### 通用配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| ENV | 环境名称 | development |
| LOG_LEVEL | 日志级别 | INFO |
| DEBUG | 调试模式 | false |

### 数据库配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| DATABASE_URL | 完整数据库URL | postgresql+asyncpg://user:pass@host:5432/db |
| DB_HOST | 数据库主机 | db |
| DB_PORT | 数据库端口 | 5432 |
| DB_NAME | 数据库名称 | football_prediction |
| DB_USER | 数据库用户 | postgres |
| DB_PASSWORD | 数据库密码 | password |

### Redis配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| REDIS_URL | 完整Redis URL | redis://:password@host:6379/0 |
| REDIS_HOST | Redis主机 | redis |
| REDIS_PORT | Redis端口 | 6379 |
| REDIS_PASSWORD | Redis密码 | - |

## 常用命令

### 构建镜像

```bash
# 开发环境构建
docker-compose build app

# 生产环境构建
docker-compose -f docker/docker-compose.yml build \
  --build-arg APP_VERSION=v1.0.0 \
  --build-arg GIT_COMMIT=$(git rev-parse HEAD) \
  app

# 多平台构建
docker buildx build --platform linux/amd64,linux/arm64 -t myapp:latest .
```

### 数据库操作

```bash
# 进入数据库
docker-compose exec db psql -U postgres -d football_prediction

# 备份数据库
docker-compose exec db pg_dump -U postgres football_prediction > backup.sql

# 恢复数据库
docker-compose exec -T db psql -U postgres football_prediction < backup.sql

# 运行迁移
docker-compose exec app alembic upgrade head

# 创建新迁移
docker-compose exec app alembic revision --autogenerate -m "描述"
```

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs -f app

# 查看最近的日志
docker-compose logs --tail=100 app

# 实时跟踪日志
docker-compose logs -f --tail=10 app
```

### 性能监控

```bash
# 查看资源使用情况
docker stats

# 查看容器详情
docker-compose ps

# 进入容器调试
docker-compose exec app bash

# 查看容器内进程
docker-compose exec app ps aux
```

## 最佳实践

### 开发环境

1. 使用 `docker-compose.override.yml` 配置开发特定需求
2. 启用热重载和调试端口
3. 使用 volumes 挂载源代码
4. 启用开发工具 profile

```bash
# 启动完整开发环境
docker-compose --profile tools up -d
```

### 生产环境

1. 始终使用特定的镜像标签
2. 不要挂载源代码（使用COPY）
3. 启用健康检查
4. 配置资源限制
5. 使用 secrets 管理敏感信息

```yaml
# 示例：生产环境资源限制
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 测试环境

1. 使用独立的测试数据库
2. 禁用外部服务调用
3. 使用内存队列替代Redis
4. 启用覆盖率收集

```bash
# 运行完整测试套件
docker-compose --profile test run --rm app \
  pytest -v --cov=src --cov-report=html
```

## 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   lsof -i :8000

   # 修改端口配置
   export API_PORT=8001
   ```

2. **权限问题**
   ```bash
   # 修复文件权限
   sudo chown -R 1001:1001 .
   ```

3. **网络问题**
   ```bash
   # 重建网络
   docker-compose down
   docker network prune
   docker-compose up -d
   ```

4. **缓存问题**
   ```bash
   # 清理Docker缓存
   docker system prune -a

   # 重新构建镜像
   docker-compose build --no-cache
   ```

### 调试技巧

1. **查看容器启动日志**
   ```bash
   docker-compose logs app
   ```

2. **进入运行中的容器**
   ```bash
   docker-compose exec app bash
   ```

3. **检查环境变量**
   ```bash
   docker-compose exec app env | grep -E "(DB|REDIS)"
   ```

4. **测试服务连通性**
   ```bash
   docker-compose exec app nc -z db 5432
   docker-compose exec app nc -z redis 6379
   ```

## 更新与维护

### 更新依赖

```bash
# 重新构建并更新
docker-compose build --pull
docker-compose up -d
```

### 备份与恢复

```bash
# 备份所有数据
docker-compose run --rm app python scripts/backup.py

# 仅备份数据库
docker-compose exec db pg_dump -U postgres football_prediction > backup.sql
```

### 滚动更新

```bash
# 零停机更新
docker-compose up -d --no-deps app
```

## 更多资源

- [Docker Compose官方文档](https://docs.docker.com/compose/)
- [Dockerfile最佳实践](https://docs.docker.com/develop/dev-best-practices/)
- [Docker多阶段构建](https://docs.docker.com/build/building/multi-stage/)
