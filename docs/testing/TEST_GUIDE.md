# 📚 测试指南

本指南说明足球预测项目的三层测试架构、运行命令和依赖准备步骤。

## 📑 目录

1. [测试架构概览](#测试架构概览)
2. [单元测试 (Unit Tests)](#单元测试-unit-tests)
3. [集成测试 (Integration Tests)](#集成测试-integration-tests)
4. [Legacy 测试](legacy-测试)
5. [测试标记说明](#测试标记说明)
6. [覆盖率报告](#覆盖率报告)
7. [CI/CD 集成](#cicd-集成)
8. [故障排除](#故障排除)

## 测试架构概览

项目采用三层测试架构：

```
tests/
├── unit/           # 单元测试（主要）
│   ├── api/        # API 层测试（Mock）
│   ├── services/   # 服务层测试（Mock + 内存数据库）
│   ├── database/   # 数据库层测试（SQLite 内存）
│   └── models/     # 模型层测试（Mock）
├── integration/    # 集成测试（重建中）
├── e2e/           # 端到端测试
└── legacy/        # 真实服务测试
```

### 测试策略

- **单元测试**：使用 Mock，快速执行，覆盖率 ≥ 40%
- **集成测试**：使用真实服务，完整验证
- **Legacy 测试**：保留的真实依赖测试，逐步迁移

## 单元测试 (Unit Tests)

单元测试是项目的主要测试类型，使用 Mock 架构，执行速度快。

### 运行命令

```bash
# 运行所有单元测试
make test

# 或
pytest tests/unit -v

# 运行特定模块测试
pytest tests/unit/api -v
pytest tests/unit/services -v
pytest tests/unit/database -v

# 运行全量测试并生成覆盖率报告
make test-full

# 或
python scripts/run_full_coverage.py
```

### Mock 架构说明

单元测试使用统一的 Mock 架构，所有外部依赖都被 Mock：

- **Redis**: `MockRedis` (tests/helpers/redis.py)
- **MLflow**: `MockMlflow` (tests/helpers/mlflow.py)
- **Kafka**: `MockKafka` (tests/helpers/kafka.py)
- **HTTP 客户端**: `MockHTTPResponse` (tests/helpers/http.py)
- **数据库**: SQLite 内存数据库 (tests/helpers/database.py)

### 编写新的单元测试

```python
"""示例单元测试"""

import pytest
from tests.helpers import MockRedis, create_sqlite_sessionmaker

class TestNewService:
    @pytest.fixture
    async def db_session(self):
        """内存数据库会话"""
        engine = create_sqlite_memory_engine()
        sessionmaker = create_sqlite_sessionmaker(engine)
        async with sessionmaker() as session:
            yield session
        engine.dispose()

    @pytest.fixture
    def mock_redis(self):
        """模拟 Redis 客户端"""
        redis_mock = MockRedis()
        redis_mock.set("__ping__", "ok")
        return redis_mock

    @pytest.fixture
    def service(self, db_session, mock_redis):
        """创建服务实例"""
        from src.services.new_service import NewService
        return NewService(db=db_session, redis=mock_redis)

    @pytest.mark.asyncio
    async def test_service_method(self, service):
        """测试服务方法"""
        # 准备
        service.redis.get.return_value = b'{"cached": true}'

        # 执行
        result = await service.get_data("test_key")

        # 验证
        assert result is not None
        service.redis.get.assert_called_once_with("test_key")
```

## 集成测试 (Integration Tests)

集成测试目前处于重建阶段，将测试组件间的交互。

### 状态：重建中

集成测试正在从 Legacy 测试中提取并重构，目标：

- 测试多个组件协作
- 使用轻量级真实服务
- 保持执行效率

## Legacy 测试

Legacy 测试使用真实的外部服务，用于验证真实环境下的集成。

### 运行条件

1. **启动服务**：

```bash
# 使用 Docker Compose
cd tests/legacy
docker-compose up -d

# 检查服务状态
docker-compose ps
```

2. **设置环境变量**：

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

# 运行特定测试
pytest tests/legacy/test_integration.py::TestRealDatabaseIntegration -v

# 跳过慢速测试
pytest tests/legacy/ -m "not slow" -v
```

### CI 自动运行

Legacy 测试通过 GitHub Actions 自动运行：

- **每日运行**：UTC 02:00（北京时间 10:00）
- **手动触发**：可在 Actions 页面手动运行
- **PR 触发**：当修改相关文件时自动运行

## 测试标记说明

项目使用 pytest 标记来分类测试：

- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.e2e` - 端到端测试
- `@pytest.mark.legacy` - 需要真实服务的遗留测试
- `@pytest.mark.slow` - 慢速测试（执行时间 > 1分钟）

### 使用标记

```python
@pytest.mark.slow
@pytest.mark.integration
def test_slow_integration(self):
    """慢速集成测试"""
    pass
```

### 按标记运行

```bash
# 只运行单元测试
pytest -m unit

# 跳过 legacy 测试
pytest -m "not legacy"

# 运行慢速测试
pytest -m slow
```

## 覆盖率报告

### 生成覆盖率报告

```bash
# 生成完整报告
make coverage

# 生成 HTML 报告
make cov.html

# 查看覆盖率趋势
make coverage-trends
```

### 覆盖率阈值

- **当前状态**：22.32%（Phase 3 实际）
- **当前目标**：稳定在22%基础上，逐步提升
- **Phase 4 目标**：40%
- **最终目标**：80%（生产标准）
- **CI 检查**：必须达到当前阈值 (22%) 才能通过

### 覆盖率报告位置

- **终端输出**：运行时实时显示
- **HTML 报告**：`htmlcov/index.html`
- **XML 报告**：`coverage.xml`
- **JSON 报告**：`coverage.json`
- **存档报告**：`docs/_reports/COVERAGE_REPORT.json`

## CI/CD 集成

### GitHub Actions 工作流

1. **CI Pipeline** (`.github/workflows/ci-pipeline.yml`)
   - 代码质量检查
   - 单元测试 + 覆盖率
   - 镜像构建

2. **Legacy Tests** (`.github/workflows/legacy-tests.yml`)
   - 真实服务集成测试
   - 每日自动运行
   - 矩阵测试（不同组件）

### 本地预检查

提交前运行：

```bash
# 完整预检查
make prepush

# 或分步执行
make fmt      # 代码格式化
make lint     # 代码检查
make test-quick  # 快速测试
make coverage-fast  # 覆盖率检查

# 质量门禁检查 (Phase 3新增)
python scripts/quality_gate.py --quick-mode  # 快速检查
python scripts/quality_gate.py               # 完整检查

# 环境健康检查
make env-check
```

## 故障排除

### 常见问题

#### 1. 测试无法导入模块

```bash
# 确保虚拟环境激活
source .venv/bin/activate

# 安装依赖
make install

# 检查 PYTHONPATH
export PYTHONPATH=$(pwd)
```

#### 2. Redis/MLflow 连接失败

```bash
# 检查服务状态
docker ps | grep redis
docker ps | grep mlflow

# 查看日志
docker logs test-redis
docker logs test-mlflow
```

#### 3. 数据库连接问题

```bash
# 检查 PostgreSQL
docker exec -it test-postgres psql -U postgres -d football_test -c "SELECT 1;"

# 重置数据库
make db-reset
```

#### 4. 覆盖率低

```bash
# 查看未覆盖的行
make coverage

# 查看具体报告
open htmlcov/index.html

# 生成覆盖率趋势
make coverage-dashboard
```

### 调试技巧

1. **运行单个测试**：

```bash
pytest tests/unit/test_example.py::TestClass::test_method -v -s
```

2. **显示输出**：

```bash
pytest -s  # 不捕获输出
```

3. **进入调试**：

```python
import pdb; pdb.set_trace()  # 在测试中添加断点
```

4. **详细错误**：

```bash
pytest --tb=long  # 显示完整错误堆栈
```

## 测试最佳实践

### 1. 命名规范

- 测试文件：`test_*.py`
- 测试类：`Test*`
- 测试方法：`test_*`

### 2. 测试结构

使用 Given-When-Then 模式：

```python
def test_prediction_creation(self, service):
    # Given - 准备数据
    prediction_data = {"match_id": 123, "home_score": 2}

    # When - 执行操作
    result = service.create_prediction(prediction_data)

    # Then - 验证结果
    assert result["status"] == "success"
    assert result["match_id"] == 123
```

### 3. 测试隔离

每个测试应该独立，不依赖其他测试：

```python
@pytest.fixture
def clean_db(self, db_session):
    """清理数据库"""
    yield
    # 测试后清理
    db_session.execute(text("DELETE FROM test_table"))
```

### 4. 测试数据管理

使用工厂模式创建测试数据：

```python
@pytest.fixture
def sample_match_data(self):
    """示例比赛数据"""
    return {
        "home_team": "Team A",
        "away_team": "Team B",
        "match_date": datetime.now()
    }
```

## 质量门禁系统详解 (Phase 3新增)

### 系统概述

项目引入了企业级质量门禁系统，自动化检查代码质量、测试覆盖率和安全性标准。

### 核心组件

1. **质量门禁脚本**: `scripts/quality_gate.py`
2. **配置文件**: `quality_config.json`
3. **报告生成**: `quality-report.json`
4. **CI集成**: GitHub Actions 工作流

### 使用方法

```bash
# 开发时快速检查
python scripts/quality_gate.py --quick-mode

# 提交前完整检查
python scripts/quality_gate.py

# 检查特定模块
python scripts/quality_gate.py --module api

# 跳过某些检查
python scripts/quality_gate.py --skip-security

# 详细输出模式
python scripts/quality_gate.py --verbose

# 帮助信息
python scripts/quality_gate.py --help
```

### 检查项目

| 检查项目 | 权重 | 通过标准 | 当前状态 |
|---------|------|----------|----------|
| 测试覆盖率 | 30% | ≥22% | ✅ 通过 |
| 测试通过率 | 25% | ≥85% | ✅ 通过 |
| 代码质量 | 20% | Ruff + MyPy 通过 | ✅ 通过 |
| 安全性检查 | 15% | Bandit 通过 | ✅ 通过 |
| 依赖安全 | 10% | pip-audit 通过 | ✅ 通过 |

### 质量报告解读

```json
{
  "overall_score": 8.5,
  "status": "PASSED",
  "checks": {
    "test_coverage": {
      "score": 7.0,
      "status": "PASSED",
      "details": "Coverage: 22.32% (threshold: 22%)"
    }
  }
}
```

### 与CI集成

质量门禁已集成到CI流程中：

1. **Pull Request**: 自动运行完整检查
2. **Push**: 运行快速检查
3. **手动触发**: 可在GitHub Actions页面手动运行

### 故障排除

#### 质量检查失败

```bash
# 查看详细失败原因
python scripts/quality_gate.py --verbose

# 只运行失败的检查项
python scripts/quality_gate.py --check coverage

# 生成修复建议
python scripts/quality_gate.py --suggest-fixes
```

#### 覆盖率不足

```bash
# 查看哪些文件缺少测试
make coverage-targeted MODULE=src/api

# 生成覆盖率提升建议
python scripts/quality_gate.py --coverage-suggestions
```

### 最佳实践

1. **开发过程中**: 使用 `--quick-mode` 快速反馈
2. **提交前**: 运行完整质量门禁检查
3. **修复问题**: 根据详细报告针对性修复
4. **持续改进**: 定期检查质量趋势报告

## Phase 3 测试策略总结

### 当前状态
- ✅ **质量门禁系统**: 已部署并正常运行
- ✅ **测试基础设施**: 完整的Mock和辅助工具
- ✅ **覆盖率稳定**: 22.32%，基础架构完善
- 🔄 **持续优化**: 正在进行的改进项目

### 下一阶段目标 (Phase 4)
- 🎯 **覆盖率目标**: 提升至40%以上
- 🎯 **测试质量**: 减少Flaky测试
- 🎯 **性能优化**: 加快测试执行速度
- 🎯 **集成测试**: 完善多组件协作测试

## 相关文档

- [API 参考](../reference/API_REFERENCE.md)
- [数据库架构](../reference/DATABASE_SCHEMA.md)
- [开发指南](../reference/DEVELOPMENT_GUIDE.md)
- [故障排除](../../CLAUDE_TROUBLESHOOTING.md)
- [质量门禁配置](../reference/QUALITY_GATE.md)

---

*最后更新：2025-01-21 (Phase 3 更新)*
