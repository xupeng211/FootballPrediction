# Docker 配置说明

## 使用方法

### 单一 docker-compose.yml

项目已将多个 docker-compose 文件整合为一个配置文件 `docker-compose.yml`，通过环境变量控制不同环境。

### 环境切换

#### 开发环境

```bash
# 使用开发配置
docker-compose --env-file .env.development up -d

# 或直接运行
make dev
```

#### 生产环境

```bash
# 使用生产配置
docker-compose --env-file .env.production up -d

# 启动所有服务包括nginx和mlflow
docker-compose --env-file .env.production --profile mlflow --profile production up -d

# 或直接运行
make prod
```

#### 测试环境

```bash
# 使用测试配置
docker-compose --env-file .env.test up -d

# 或直接运行
make test-env
```

### 启动特定服务

#### 仅启动基础服务（app, db, redis）

```bash
docker-compose up -d
```

#### 包含MLflow

```bash
docker-compose --profile mlflow up -d
```

#### 包含Celery任务队列

```bash
docker-compose --profile celery up -d
```

#### 完整生产环境

```bash
docker-compose --profile mlflow --profile celery --profile production up -d
```

### 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| ENVIRONMENT | 环境名称 | development |
| DEBUG | 调试模式 | false |
| LOG_LEVEL | 日志级别 | INFO |
| BUILD_TARGET | 构建目标 | development |
| API_PORT | API端口 | 8000 |
| DB_PORT | 数据库端口 | 5432 |
| REDIS_PORT | Redis端口 | 6379 |

### 旧的文件（已归档）

- `docker-compose.dev.yml` → 移至 `config/docker/`
- `docker-compose.prod.yml` → 移至 `config/docker/`
- `docker-compose.test.yml` → 移至 `config/docker/`
- `docker-compose.override.yml` → 移至 `config/docker/`

### 迁移说明

1. 新配置使用 YAML 锚点减少重复
2. 通过 profiles 控制可选服务
3. 环境变量外部化配置
4. 更清晰的服务依赖关系

### 故障排除

如果遇到端口冲突：

```bash
# 修改环境变量中的端口配置
export API_PORT=8001
export DB_PORT=5433
```
