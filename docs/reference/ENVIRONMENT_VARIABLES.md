# 环境变量文档

本文档描述了足球预测系统使用的所有环境变量。

## 📋 目录

- [必需环境变量](#必需环境变量)
- [数据库配置](#数据库配置)
- [Redis配置](#redis配置)
- [API配置](#api配置)
- [安全配置](#安全配置)
- [缓存配置](#缓存配置)
- [监控配置](#监控配置)
- [日志配置](#日志配置)
- [性能配置](#性能配置)
- [第三方服务配置](#第三方服务配置)

## 🔑 必需环境变量

| 变量名 | 类型 | 默认值 | 描述 | 示例 |
|--------|------|--------|------|------|
| `ENVIRONMENT` | string | `development` | 运行环境 | `production`, `staging`, `development` |
| `DATABASE_URL` | string | - | 数据库连接URL | `postgresql://user:pass@localhost/db` |
| `JWT_SECRET_KEY` | string | - | JWT签名密钥（至少32字符） | `your-secret-key-here` |
| `SECRET_KEY` | string | - | 应用密钥（至少32字符） | `your-app-secret-here` |

## 🗄️ 数据库配置

| 变量名 | 类型 | 默认值 | 描述 | 示例 |
|--------|------|--------|------|------|
| `DB_POOL_SIZE` | int | `10` | 数据库连接池大小 | `20` |
| `DB_MAX_OVERFLOW` | int | `20` | 连接池最大溢出数 | `30` |
| `DB_POOL_TIMEOUT` | int | `30` | 获取连接超时时间（秒） | `60` |
| `DB_POOL_RECYCLE` | int | `3600` | 连接回收时间（秒） | `7200` |
| `DB_ECHO` | bool | `false` | 是否打印SQL语句 | `true` |

**数据库URL格式**：
- PostgreSQL: `postgresql://username:password@host:port/database`
- SQLite: `sqlite:///path/to/database.db`

## 📦 Redis配置

| 变量名 | 类型 | 默认值 | 描述 | 示例 |
|--------|------|--------|------|------|
| `REDIS_URL` | string | - | Redis连接URL（覆盖其他Redis配置） | `redis://localhost:6379/0` |
| `REDIS_HOST` | string | `localhost` | Redis服务器地址 | `redis.example.com` |
| `REDIS_PORT` | int | `6379` | Redis服务器端口 | `6380` |
| `REDIS_DB` | int | `0` | Redis数据库编号 | `1` |
| `REDIS_PASSWORD` | string | - | Redis认证密码 | `your-redis-password` |
| `REDIS_MAX_CONNECTIONS` | int | `10` | Redis连接池大小 | `20` |
| `REDIS_SOCKET_TIMEOUT` | int | `5` | Redis套接字超时（秒） | `10` |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | int | `5` | Redis连接超时（秒） | `10` |

## 🌐 API配置

| 变量名 | 类型 | 默认值 | 描述 | 示例 |
|--------|------|--------|------|------|
| `API_HOST` | string | `0.0.0.0` | API服务器监听地址 | `127.0.0.1` |
| `API_PORT` | int | `8000` | API服务器端口 | `8080` |
| `API_WORKERS` | int | `1` | Uvicorn工作进程数 | `4` |
| `API_RELOAD` | bool | `false` | 开发模式热重载 | `true` |
| `API_LOG_LEVEL` | string | `info` | 日志级别 | `debug`, `info`, `warning` |
| `CORS_ORIGINS` | string | - | 允许的CORS源（逗号分隔） | `https://example.com,https://app.com` |
| `API_PREFIX` | string | `/api/v1` | API路径前缀 | `/api/v2` |
| `API_DOCS_URL` | string | `/docs` | API文档路径 | `/api/docs` |
| `MINIMAL_API_MODE` | bool | `false` | 最小API模式（仅健康检查） | `true` |

## 🔒 安全配置

| 变量名 | 类型 | 默认值 | 描述 | 示例 |
|--------|------|--------|------|------|
| `JWT_SECRET_KEY` | string | - | JWT签名密钥（必须） | `super-secret-jwt-key-32-chars` |
| `SECRET_KEY` | string | - | 应用密钥（必须） | `super-secret-app-key-32-chars` |
| `JWT_ALGORITHM` | string | `HS256` | JWT签名算法 | `HS256`, `RS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `30` | 访问令牌过期时间（分钟） | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | int | `7` | 刷新令牌过期时间（天） | `30` |
| `BCRYPT_ROUNDS` | int | `12` | bcrypt加密轮数 | `14` |
| `RATE_LIMIT_ENABLED` | bool | `true` | 是否启用限流 | `false` |
| `MAX_REQUESTS_PER_MINUTE` | int | `60` | 每分钟最大请求数 | `100` |
| `TRUSTED_PROXIES` | string | - | 信任的代理IP（逗号分隔） | `10.0.0.0/8,172.16.0.0/12` |

## ⚡ 缓存配置

| 变量名 | 类型 | 默认值 | 描述 | 示例 |
|--------|------|--------|------|------|
| `CACHE_ENABLED` | bool | `true` | 是否启用缓存 | `false` |
| `CACHE_DEFAULT_TTL` | int | `300` | 默认缓存TTL（秒） | `600` |
| `CACHE_TYPE` | string | `redis` | 缓存类型 | `memory`, `redis` |
| `MEMORY_CACHE_SIZE` | int | `1000` | 内存缓存最大条目数 | `2000` |
| `MEMORY_CACHE_TTL` | int | `300` | 内存缓存TTL（秒） | `600` |
| `L2_CACHE_TTL` | int | `1800` | L2缓存TTL（秒） | `3600` |
| `L2_MAX_MEMORY` | string | `100mb` | L2缓存最大内存 | `200mb` |
| `CACHE_PRELOAD_ENABLED` | bool | `true` | 是否启用缓存预热 | `false` |
| `CACHE_PRELOAD_BATCH_SIZE` | int | `100` | 预热批次大小 | `200` |
| `CACHE_METRICS_ENABLED` | bool | `true` | 是否启用缓存指标 | `false` |
| `CACHE_STATS_INTERVAL` | int | `60` | 统计信息更新间隔（秒） | `120` |

## 📊 监控配置

| 变量名 | 类型 | 默认值 | 描述 | 示例 |
|--------|------|--------|------|------|
| `METRICS_ENABLED` | bool | `true` | 是否启用指标收集 | `false` |
| `METRICS_PORT` | int | `9090` | 指标服务端口 | `9091` |
| `METRICS_PATH` | string | `/metrics` | 指标端点路径 | `/api/metrics` |
| `SENTRY_DSN` | string | - | Sentry错误追踪DSN | `https://xxx@sentry.io/xxx` |
| `SENTRY_ENVIRONMENT` | string | `production` | Sentry环境名称 | `staging` |
| `SENTRY_SAMPLE_RATE` | float | `0.1` | Sentry采样率 | `0.5` |
| `PROMETHEUS_GATEWAY_URL` | string | - | Prometheus Pushgateway URL | `http://gateway:9091` |
| `HEALTH_CHECK_INTERVAL` | int | `30` | 健康检查间隔（秒） | `60` |

## 📝 日志配置

| 变量名 | 类型 | 默认值 | 描述 | 示例 |
|--------|------|--------|------|------|
| `LOG_LEVEL` | string | `INFO` | 日志级别 | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | string | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | 日志格式 | `%(message)s` |
| `LOG_FILE` | string | - | 日志文件路径 | `/var/log/app.log` |
| `LOG_MAX_SIZE` | string | `100MB` | 日志文件最大大小 | `500MB` |
| `LOG_BACKUP_COUNT` | int | `5` | 日志备份数量 | `10` |
| `STRUCTURED_LOGGING` | bool | `false` | 是否使用结构化日志 | `true` |
| `LOG_CORRELATION_ID` | bool | `true` | 是否添加关联ID | `false` |

## ⚡ 性能配置

| 变量名 | 类型 | 默认值 | 描述 | 示例 |
|--------|------|--------|------|------|
| `PERF_SLOW_QUERY_THRESHOLD` | float | `1.0` | 慢查询阈值（秒） | `0.5` |
| `PERF_ENABLE_COMPRESSION` | bool | `true` | 是否启用响应压缩 | `false` |
| `PERF_COMPRESSION_THRESHOLD` | int | `1024` | 压缩阈值（字节） | `2048` |
| `PERF_BATCH_SIZE_LIMIT` | int | `100` | 批处理最大大小 | `200` |
| `PERF_CONNECTION_TIMEOUT` | int | `30` | 连接超时（秒） | `60` |
| `PERF_READ_TIMEOUT` | int | `60` | 读取超时（秒） | `120` |
| `PERF_WRITE_TIMEOUT` | int | `60` | 写入超时（秒） | `120` |
| `PERF_KEEP_ALIVE_TIMEOUT` | int | `5` | Keep-alive超时（秒） | `30` |

## 🔌 第三方服务配置

### Celery任务队列

| 变量名 | 类型 | 默认值 | 描述 | 示例 |
|--------|------|--------|------|------|
| `CELERY_BROKER_URL` | string | - | Celery代理URL | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | string | - | Celery结果后端 | `redis://localhost:6379/2` |
| `CELERY_TASK_SERIALIZER` | string | `json` | 任务序列化器 | `pickle`, `json` |
| `CELERY_RESULT_SERIALIZER` | string | `json` | 结果序列化器 | `pickle`, `json` |
| `CELERY_TIMEZONE` | string | `UTC` | 时区 | `Asia/Shanghai` |
| `CELERY_ENABLE_UTC` | bool | `true` | 是否使用UTC | `false` |

### 机器学习配置

| 变量名 | 类型 | 默认值 | 描述 | 示例 |
|--------|------|--------|------|------|
| `ML_MODEL_PATH` | string | `./models` | 模型存储路径 | `/app/models` |
| `ML_MODEL_VERSION` | string | `latest` | 模型版本 | `v1.2.0` |
| `ML_BATCH_SIZE` | int | `32` | 批处理大小 | `64` |
| `ML_FEATURE_CACHE_TTL` | int | `3600` | 特征缓存TTL（秒） | `7200` |
| `ML_PREDICTION_TIMEOUT` | int | `5` | 预测超时（秒） | `10` |

### 外部API配置

| 变量名 | 类型 | 默认值 | 描述 | 示例 |
|--------|------|--------|------|------|
| `FOOTBALL_API_KEY` | string | - | 足球数据API密钥 | `your-api-key-here` |
| `FOOTBALL_API_URL` | string | - | 足球数据API URL | `https://api.football-data.org` |
| `FOOTBALL_API_TIMEOUT` | int | `30` | API请求超时（秒） | `60` |
| `FOOTBALL_API_RETRY_ATTEMPTS` | int | `3` | 重试次数 | `5` |
| `WEATHER_API_KEY` | string | - | 天气API密钥 | `your-weather-key-here` |
| `WEATHER_API_URL` | string | - | 天气API URL | `https://api.openweathermap.org` |

## 📋 环境特定配置

### 开发环境 (.env.development)

```bash
# 基础配置
ENVIRONMENT=development
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
API_LOG_LEVEL=debug

# 数据库
DATABASE_URL=sqlite:///./football_dev.db
DB_ECHO=true

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 缓存
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=60

# 日志
LOG_LEVEL=DEBUG
STRUCTURED_LOGGING=false

# 安全（开发用密钥，生产必须更换）
JWT_SECRET_KEY=dev-secret-key-change-in-production-32
SECRET_KEY=dev-app-secret-key-change-in-production-32
```

### 测试环境 (.env.testing)

```bash
# 基础配置
ENVIRONMENT=testing
API_HOST=127.0.0.1
API_PORT=8001
API_LOG_LEVEL=warning

# 数据库（使用内存SQLite）
DATABASE_URL=sqlite:///:memory:

# Redis（使用测试数据库）
REDIS_DB=15

# 缓存（禁用以确保测试一致性）
CACHE_ENABLED=false

# 日志
LOG_LEVEL=WARNING

# 安全（测试固定密钥）
JWT_SECRET_KEY=test-secret-key-32-chars-long-value
SECRET_KEY=test-app-secret-key-32-chars-long-value
```

### 生产环境 (.env.production)

```bash
# 基础配置
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_LOG_LEVEL=info

# 数据库
DATABASE_URL=postgresql://user:pass@db.example.com:5432/football_prod
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30

# Redis
REDIS_URL=redis://redis.example.com:6379/0
REDIS_PASSWORD=your-redis-password
REDIS_MAX_CONNECTIONS=20

# 缓存
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=1800
L2_CACHE_TTL=3600

# 安全（生产必须使用强密钥）
JWT_SECRET_KEY=your-super-secret-jwt-key-32-chars
SECRET_KEY=your-super-secret-app-key-32-chars

# 监控
METRICS_ENABLED=true
SENTRY_DSN=https://xxx@sentry.io/xxx

# 性能
PERF_SLOW_QUERY_THRESHOLD=0.5
PERF_ENABLE_COMPRESSION=true
```

## 🔧 配置验证

使用提供的配置验证脚本：

```bash
# 验证当前环境配置
python scripts/validate_config.py

# 验证特定文件
python scripts/validate_config.py --file .env.production

# 保存验证报告
python scripts/validate_config.py --output config_report.txt
```

## 🔐 配置加密

使用配置加密工具保护敏感信息：

```bash
# 加密.env文件
python scripts/config_crypto.py encrypt-env --input .env.production --output .env.production.enc --password

# 解密配置
python scripts/config_crypto.py decrypt-env --input .env.production.enc --output .env.production --password

# 创建加密备份
python scripts/backup_config.py backup --config env --password
```

## 📝 最佳实践

1. **永远不要**在代码中硬编码敏感信息
2. **永远不要**将.env文件提交到版本控制
3. **使用**强随机生成的密钥
4. **区分**不同环境的配置
5. **定期**轮换密钥和密码
6. **使用**配置验证脚本检查完整性
7. **加密**存储敏感配置文件
8. **备份**重要的配置文件

## 🚨 安全注意事项

- 所有密钥必须至少32个字符
- 生产环境必须使用HTTPS
- 定期检查密钥泄露
- 使用最小权限原则配置数据库访问
- 限制CORS源到可信域名
- 启用请求限流防止滥用

## 📚 相关文档

- [API文档](./API_REFERENCE.md)
- [部署指南](../deployment/DEPLOYMENT_GUIDE.md)
- [安全指南](../security/SECURITY_GUIDE.md)