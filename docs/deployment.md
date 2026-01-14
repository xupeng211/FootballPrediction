# Docker 部署完整指南

本文档提供 FootballPrediction 项目的 Docker 容器化部署完整指南。

---

## 📋 目录

- [V106.0 Docker 架构](#v1060-docker-架构)
- [快速部署](#快速部署)
- [Docker Compose 配置](#docker-compose-配置)
- [服务配置说明](#服务配置说明)
- [容器日志查看](#容器日志查看)
- [生产环境部署](#生产环境部署)
- [常见问题](#常见问题)

---

## V106.0 Docker 架构

### Dockerfile 特性

V106.0 采用**多阶段生产级 Docker 构建**：

- **Builder 阶段**: 构建依赖和预编译字节码
- **Runtime 阶段**: 最小化运行时镜像
- **非特权用户**: `appuser` 用户运行容器
- **健康检查**: `/health` 端点健康监控

### 构建镜像

```bash
# 构建生产镜像
docker-compose build

# 无缓存构建
docker-compose build --no-cache

# 构建测试镜像
docker build --target test -f Dockerfile -t footballprediction:test .
```

---

## 快速部署

### 启动核心服务

```bash
# 启动核心服务 (db + redis)
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### Profile 部署选项

```bash
# 启动核心服务 + 数据流水线
docker-compose --profile pipeline up -d

# 启动核心服务 + API 服务
docker-compose --profile api up -d

# 启动核心服务 + 自动化调度
docker-compose --profile automation up -d

# 启动开发环境 (含管理工具: pgadmin, redis-commander)
docker-compose --profile dev up -d

# 启动所有服务
docker-compose --profile all up -d
```

---

## Docker Compose 配置

### 服务配置说明

| 服务 | 功能 | 端口 | 资源限制 |
|------|------|------|----------|
| `db` | PostgreSQL 15 数据库 | 5432 | 2 CPU / 2G 内存 |
| `redis` | Redis 7 缓存服务 | 6379 | 0.5 CPU / 512M 内存 |
| `pipeline_worker` | V25.1 数据流水线 | - | 2 CPU / 2G 内存 |
| `predictor_api` | FastAPI 预测服务 | 8000 | 1 CPU / 1G 内存 |
| `dashboard` | 战神仪表盘 | - | 0.5 CPU / 512M 内存 |
| `db_backup` | 数据库自动备份 | - | 0.25 CPU / 256M 内存 |
| `odds_scraper` | 赔率数据采集 | - | 1 CPU / 1G 内存 |
| `production_cron` | 生产自动化调度 | - | 1 CPU / 1G 内存 |

### 开发工具（仅 dev profile）

| 服务 | 功能 | 端口 |
|------|------|------|
| `pgadmin` | PostgreSQL 管理 | 5050 |
| `redis-commander` | Redis 管理 | 8081 |

### Docker 环境变量

```bash
# .env 文件配置
DOCKER_ENV=true           # Docker 环境标识
DB_HOST=db                # Docker 内使用服务名
REDIS_HOST=redis          # Docker 内使用服务名
API_WORKERS=2             # API 工作进程数
```

---

## 服务配置说明

### 数据库服务 (db)

```yaml
db:
  image: postgres:15
  environment:
    POSTGRES_DB: football_db
    POSTGRES_USER: football_user
    POSTGRES_PASSWORD: ${DB_PASSWORD}
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

### Redis 服务

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

### API 服务 (predictor_api)

```yaml
predictor_api:
  build:
    context: .
    dockerfile: Dockerfile
    target: runtime
  environment:
    DB_HOST: db
    REDIS_HOST: redis
    API_WORKERS: 2
  ports:
    - "8000:8000"
  depends_on:
    - db
    - redis
```

---

## 容器日志查看

### 查看核心服务日志

```bash
# 查看核心服务日志
docker-compose logs -f pipeline_worker

# 查看 API 日志
docker-compose logs -f predictor_api

# 查看所有服务日志
docker-compose logs -f
```

### 日志位置

| 日志类型 | 路径 |
|----------|------|
| 应用日志 | `logs/app.log` |
| 错误日志 | `logs/error.log` |
| 采集器日志 | `logs/auto_harvest.log` |

---

## 生产环境部署

### 部署前检查清单

- [ ] 确认 `.env` 文件已配置（包含数据库密码等）
- [ ] 确认 Docker 镜像已构建（`docker-compose build`）
- [ ] 确认数据库备份已完成（`make db-backup`）
- [ ] 确认代码质量检查通过（`make verify`）

### 部署步骤

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 备份数据库
make db-backup

# 3. 构建镜像
docker-compose build --no-cache

# 4. 启动服务
docker-compose --profile pipeline up -d

# 5. 检查服务状态
docker-compose ps

# 6. 查看日志确认启动成功
docker-compose logs -f
```

### 健康检查

```bash
# 运行健康检查脚本
python scripts/health_check.py

# 或使用 Make 命令
make health
```

---

## 常见问题

### 容器无法启动

**诊断步骤**:
```bash
# 1. 查看容器状态
docker-compose ps

# 2. 查看容器日志
docker-compose logs --tail=100

# 3. 检查 Docker 资源
docker system df
```

**解决方案**:
```bash
# 1. 清理 Docker 资源
make clean-docker

# 2. 重建容器
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### 容器内无法访问宿主机服务

**原因**: Docker 网络配置问题

**解决方案**:
```bash
# Docker Desktop (Mac/Windows)
# 使用 host.docker.internal
export DB_HOST=host.docker.internal

# Linux Docker
# 使用宿主机 IP (需要获取)
export DB_HOST=$(ip route | awk '/docker0/ {print $NF}')
```

### 数据库连接问题

**症状**: 容器内应用无法连接数据库

**解决方案**:
```bash
# 确认服务名称正确
# Docker 内使用服务名 'db'，而非 'localhost'
export DB_HOST=db

# 确认数据库已启动
docker-compose ps db

# 查看数据库日志
docker-compose logs db
```

---

## Docker 资源管理

### 清理 Docker 资源

```bash
# 清理垃圾文件和缓存
make clean

# 清理 Docker 资源
make clean-docker

# 完全清理 (所有清理操作)
make clean-all
```

### 查看资源使用

```bash
# 查看 Docker 资源使用情况
docker system df

# 查看容器资源使用
docker stats
```

---

## 生产环境建议

### 资源限制配置

在 `docker-compose.yml` 中为每个服务配置资源限制：

```yaml
services:
  predictor_api:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 健康检查配置

```yaml
services:
  predictor_api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 日志轮转配置

```yaml
services:
  predictor_api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 部署命令快捷方式

### Makefile 部署命令

```bash
# 服务管理
make help              # 显示所有可用命令
make up                # 启动核心服务
make up-pipeline       # 启动核心服务 + 数据流水线
make up-api            # 启动核心服务 + API
make up-dev            # 启动开发环境 (含管理工具)
make up-all            # 启动所有服务
make down              # 停止所有服务
make restart           # 重启核心服务

# 部署
make deploy            # 部署到生产环境
```

---

**最后更新**: 2026-01-14
