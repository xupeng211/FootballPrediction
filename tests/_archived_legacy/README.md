# Legacy 测试说明

本目录包含依赖真实服务的遗留测试。这些测试需要真实的外部服务运行。

## 📋 目录结构

```
tests/legacy/
├── README.md              # 本文件
├── conftest.py            # Legacy 测试配置
├── test_integration.py    # 集成测试（使用真实服务）
└── docker-compose.yml     # 测试所需的服务
```

## 🚀 运行条件

运行这些测试前，需要启动以下服务：

### 1. 使用 Docker Compose
```bash
# 启动所有服务
docker-compose -f tests/legacy/docker-compose.yml up -d

# 检查服务状态
docker-compose -f tests/legacy/docker-compose.yml ps
```

### 2. 单独启动服务
```bash
# PostgreSQL
docker run -d --name test-postgres \
  -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=football_test \
  -p 5432:5432 postgres:15

# Redis
docker run -d --name test-redis \
  -p 6379:6379 redis:7-alpine

# MLflow
docker run -d --name test-mlflow \
  -p 5000:5000 python:3.11 \
  bash -c "pip install mlflow && mlflow server --host 0.0.0.0"

# Kafka
docker-compose -f tests/legacy/docker-compose.yml up kafka -d
```

## 🧪 运行测试

### 环境变量设置
```bash
export DATABASE_URL=postgresql://postgres:testpass@localhost:5432/football_test
export REDIS_URL=redis://localhost:6379
export MLFLOW_TRACKING_URI=http://localhost:5000
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### 运行命令
```bash
# 运行所有 legacy 测试
pytest tests/legacy/ -v

# 运行特定的 legacy 测试
pytest tests/legacy/test_integration.py::TestRealIntegration -v

# 运行并显示输出
pytest tests/legacy/ -v -s
```

## ⚠️ 注意事项

1. **资源消耗**：这些测试会消耗更多资源，因为需要启动真实服务
2. **执行时间**：执行时间较长，通常 2-5 分钟
3. **数据清理**：测试会自动清理数据，但建议使用独立的测试数据库
4. **网络依赖**：需要网络连接来拉取 Docker 镜像
5. **端口冲突**：确保 5432、6379、5000、9092 端口未被占用

## 📊 测试覆盖范围

- ✅ 真实数据库连接和事务
- ✅ Redis 缓存操作
- ✅ MLflow 模型跟踪
- ✅ Kafka 消息队列
- ✅ HTTP 客户端请求
- ✅ 文件系统操作

## 🔄 迁移策略

这些测试应该逐步迁移到使用 Mock 架构：

1. 分析测试的真实依赖
2. 创建对应的 Mock 类
3. 将测试移动到 `tests/unit/` 目录
4. 使用 Mock 替换真实依赖
5. 保留关键集成测试在此目录

## 🚨 故障排除

### PostgreSQL 连接失败
```bash
# 检查服务是否运行
docker ps | grep postgres

# 查看日志
docker logs test-postgres
```

### Redis 连接失败
```bash
# 测试连接
redis-cli -h localhost -p 6379 ping
```

### MLflow 不可用
```bash
# 检查服务
curl http://localhost:5000/health
```

### Kafka 连接问题
```bash
# 查看 Kafka 日志
docker logs test-kafka
```