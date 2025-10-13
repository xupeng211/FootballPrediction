# 🧱 集成测试运行手册（Integration Test Runbook）

**目标：**
验证模块间交互逻辑（API ↔ DB ↔ Kafka ↔ Redis）是否正常。

**测试范围：**
- `tests/integration/` 目录下所有测试文件。
- 重点模块：
  - `src/api/`
  - `src/services/`
  - `src/data/`
  - `src/streaming/`

## 📋 运行前准备

### 1. 环境要求
- Python 3.11+
- Docker & Docker Compose
- 至少 8GB 可用内存

### 2. 依赖服务配置

#### 2.1 启动测试基础设施
```bash
# 使用测试专用的 Docker Compose
docker compose -f docker-compose.test.yml up -d

# 检查服务状态
docker compose -f docker-compose.test.yml ps
```

#### 2.2 服务列表
| 服务 | 端口 | 描述 | 测试数据库 |
|------|------|------|------------|
| PostgreSQL | 5432 | 主数据库 | football_test |
| Redis | 6379 | 缓存/会话 | test_redis |
| Kafka | 9092 | 消息队列 | test_topics |
| MLflow | 5000 | 模型跟踪 | mlflow_test |
| Zookeeper | 2181 | Kafka协调 | - |

#### 2.3 环境变量配置
```bash
# 复制测试环境配置
cp .env.example .env.test

# 编辑测试环境变量
cat > .env.test << EOF
# 测试环境配置
TEST_ENV=integration
TESTING=true

# 数据库配置
DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/football_test
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_test
DB_USER=test_user
DB_PASSWORD=test_pass

# Redis配置
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Kafka配置
KAFKA_BROKER=localhost:9092
KAFKA_TOPIC_PREFIX=test_
KAFKA_GROUP_ID=test_group

# MLflow配置
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=test_experiment

# 日志配置
LOG_LEVEL=DEBUG
LOG_FORMAT=json

# 其他配置
SECRET_KEY=test-secret-key-for-integration-only
ALLOWED_HOSTS=localhost,127.0.0.1
EOF

# 加载环境变量
export $(cat .env.test | xargs)
```

### 3. 数据库初始化
```bash
# 创建测试数据库
docker exec -it football-pg-test psql -U postgres -c "CREATE DATABASE football_test;"

# 运行数据库迁移
docker exec -it football-app-test alembic upgrade head

# 加载测试数据
python scripts/load_test_data.py --env=test
```

## 🚀 执行测试

### 1. 运行所有集成测试
```bash
# 运行完整集成测试套件
pytest tests/integration/ \
  --maxfail=5 \
  --disable-warnings \
  --cov-append \
  --cov-report=term \
  --cov-report=html \
  --junit-xml=reports/integration-results.xml \
  -v

# 生成覆盖率报告
open htmlcov/index.html
```

### 2. 运行特定模块测试
```bash
# API集成测试
pytest tests/integration/api/ \
  -v \
  --disable-warnings \
  --maxfail=3

# 服务层集成测试
pytest tests/integration/services/ \
  -v \
  --disable-warnings \
  --maxfail=3

# 数据库集成测试
pytest tests/integration/database/ \
  -v \
  --disable-warnings \
  --maxfail=3

# 流处理集成测试
pytest tests/integration/streaming/ \
  -v \
  --disable-warnings \
  --maxfail=3
```

### 3. 运行性能相关的集成测试
```bash
# 包含性能基准的集成测试
pytest tests/integration/ -m "performance" \
  --benchmark-only \
  --benchmark-json=reports/integration-benchmark.json \
  -v

# 压力测试
pytest tests/integration/stress/ \
  --maxfail=1 \
  -v
```

## 📊 测试类别

### 1. API集成测试 (`tests/integration/api/`)
```python
# 典型测试示例
class TestAPIIntegration:
    """API集成测试"""

    async def test_prediction_api_workflow(self):
        """测试预测API完整流程"""
        # 1. 创建预测请求
        response = await client.post("/api/v1/predictions", json={
            "match_id": 12345,
            "home_team": "Team A",
            "away_team": "Team B",
            "prediction": "HOME_WIN"
        })
        assert response.status_code == 201

        # 2. 验证数据库保存
        prediction = await db.get_prediction(12345)
        assert prediction is not None
        assert prediction.result == "HOME_WIN"

        # 3. 验证Kafka消息发送
        message = await kafka.consume("predictions")
        assert message["match_id"] == 12345

        # 4. 验证缓存更新
        cached = await redis.get(f"prediction:{12345}")
        assert cached is not None
```

### 2. 数据库集成测试 (`tests/integration/database/`)
```python
# 测试数据库事务、连接池、查询优化
class TestDatabaseIntegration:
    """数据库集成测试"""

    async def test_transaction_rollback(self):
        """测试事务回滚"""
        async with db.transaction():
            # 插入数据
            await db.insert_prediction(data)
            # 故意抛出异常
            raise Exception("Rollback")

        # 验证数据未保存
        count = await db.count_predictions()
        assert count == initial_count
```

### 3. 流处理集成测试 (`tests/integration/streaming/`)
```python
# 测试Kafka消费者、生产者
class TestStreamingIntegration:
    """流处理集成测试"""

    async def test_kafka_message_flow(self):
        """测试Kafka消息完整流程"""
        # 1. 生产消息
        await kafka.produce("predictions", test_message)

        # 2. 消费消息
        consumed = await kafka.consume("predictions", timeout=5)
        assert consumed["match_id"] == test_message["match_id"]

        # 3. 验证处理结果
        result = await db.get_processed_prediction(test_message["match_id"])
        assert result is not None
```

## 🔍 故障排查

### 常见问题及解决方案

#### 1. 数据库连接失败
```bash
# 检查PostgreSQL状态
docker logs football-pg-test

# 重启服务
docker restart football-pg-test

# 检查连接
docker exec -it football-pg-test psql -U test_user -d football_test
```

#### 2. Kafka无法连接
```bash
# 检查Kafka状态
docker logs football-kafka-test

# 检查主题列表
docker exec -it football-kafka kafka-topics --bootstrap-server localhost:9092 --list

# 创建测试主题
docker exec -it football-kafka kafka-topics --bootstrap-server localhost:9092 --create --topic test_predictions
```

#### 3. Redis连接超时
```bash
# 检查Redis状态
docker logs football-redis-test

# 测试连接
docker exec -it football-redis redis-cli ping

# 清空测试数据
docker exec -it football-redis redis-cli flushall
```

### 测试失败处理

#### 1. 查看详细错误
```bash
# 显示完整错误堆栈
pytest tests/integration/ -v --tb=long

# 只看失败测试
pytest tests/integration/ --lf -v

# 查看前3个失败
pytest tests/integration/ --maxfail=3 -v
```

#### 2. 调试模式
```bash
# 进入调试模式
pytest tests/integration/test_api.py::TestAPIIntegration::test_prediction_api_workflow -s

# 使用pdb调试
pytest --pdb tests/integration/test_api.py::TestAPIIntegration::test_prediction_api_workflow
```

## 📈 报告输出

### 1. 报告生成
```bash
# 运行测试并生成报告
pytest tests/integration/ \
  --junit-xml=reports/integration-results.xml \
  --html=reports/integration-report.html \
  --self-contained-html

# 生成Markdown报告
pytest tests/integration/ --json-report --json-report-file=reports/integration.json
python scripts/generate_integration_report.py reports/integration.json
```

### 2. 报告内容结构
```markdown
# 集成测试报告 - 2025-01-13

## 📊 测试概览
- 总测试数：42
- 通过：38 (90.5%)
- 失败：4 (9.5%)
- 耗时：3分24秒

## 🔧 模块状态
### API集成
- ✅ 通过：12/15
- ❌ 失败：3
- 平均响应时间：125ms

### 数据库集成
- ✅ 通过：15/15
- 平均查询时间：45ms

### 流处理集成
- ✅ 通过：11/12
- 平均延迟：78ms

## 🚨 失败详情
1. test_api_timeout_error - 响应时间 > 5s
2. test_kafka_consumer_error - 消费超时
...

## 📈 性能指标
- 90分位响应时间：450ms
- 数据库连接池使用率：65%
- Kafka消息吞吐量：1200 msg/s
```

## 🤖 AI 协同规则

### 1. 自动检测规则
- Claude Code 自动读取 `INTEGRATION_RESULT_<date>.md`
- 检测连续失败模式
- 自动标注在 `TEST_ACTIVATION_KANBAN.md`

### 2. 优先修复建议
```markdown
### 修复优先级
1. 🔴 高优先级：数据库写入失败、Kafka阻塞
2. 🟡 中优先级：API响应慢、缓存未命中
3. 🟢 低优先级：日志格式、性能警告
```

### 3. 自动化建议
```python
# Claude Code 可以执行的自动修复建议
if integration_failures > 3:
    # 建议创建修复脚本
    create_fix_script(failure_pattern)

if performance_issues:
    # 建议优化
    suggest_performance_optimizations()
```

## 🏷️ 标签系统

使用 pytest 标记来分类测试：
```python
@pytest.mark.integration
@pytest.mark.database
@pytest.mark.kafka
@pytest.mark.redis
@pytest.mark.performance
@pytest.mark.slow  # > 1秒
```

运行特定标签：
```bash
# 只运行数据库集成测试
pytest tests/integration/ -m "database"

# 排除性能测试
pytest tests/integration/ -m "not performance"

# 运行快速测试
pytest tests/integration/ -m "not slow" -x
```

## 📅 定期执行建议

### 1. CI/CD集成
```yaml
# .github/workflows/integration-test.yml
name: Integration Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 2 * * *"  # 每天凌晨2点

jobs:
  integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - name: Start test services
        run: docker-compose -f docker-compose.test.yml up -d
      - name: Wait for services
        run: sleep 30
      - name: Run integration tests
        run: |
          pytest tests/integration/ \
            --junit-xml=integration-results.xml \
            --cov=src \
            --cov-report=xml
      - name: Stop test services
        run: docker-compose -f docker-compose.test.yml down
```

### 2. 本地开发流程
```bash
# 每日开始
make test-integration

# 提交前
make test-integration-quick

# 完整测试
make test-all
```

## 📝 测试清单

### 执行前检查
- [ ] Docker服务已启动
- [ ] 环境变量已配置
- [ ] 数据库已初始化
- [ ] 测试数据已加载

### 执行后验证
- [ ] 所有测试通过
- [ ] 报告已生成
- [ ] 覆盖率达标
- [ ] 无阻塞问题

## 🔄 清理操作

```bash
# 停止所有服务
docker compose -f docker-compose.test.yml down

# 清理测试数据
docker volume rm football_postgres_test_data

# 清理缓存
pytest --cache-clear

# 清理报告
rm -rf reports/* htmlcov/
```

---

**维护说明：**
- 每次测试后更新此文档
- 新增集成测试时更新范围说明
- 保持环境变量同步更新
