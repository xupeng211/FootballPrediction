# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**重要提醒：请始终使用简体中文回复用户，用户看不懂英文。**

---

## 📑 快速导航

- [🎯 核心必知](#-核心必知) - 首次打开必读
- [🏗️ 架构概览](#️-架构概览) - 技术栈和结构
- [🧪 测试策略](#-测试策略) - Smart Tests体系
- [🔧 质量工具](#-质量工具) - 代码质量保证
- [🚨 问题解决](#-问题解决) - 按优先级分类
- [🐳 部署指南](#-部署指南) - Docker和CI/CD
- [📚 扩展阅读](#-扩展阅读) - 详细文档链接

---

## 🎯 核心必知

### 🔥 首次打开项目必做（3步启动）

```bash
# 1️⃣ 环境准备
make install && make env-check

# 2️⃣ 智能修复（解决80%常见问题）
python3 scripts/smart_quality_fixer.py

# 3️⃣ 快速验证
make test.smart
```

### ⚡ 7个必会命令

```bash
make install          # 安装项目依赖
make test.smart       # 快速测试验证（<2分钟）
make fix-code         # 一键修复代码质量问题
make coverage         # 查看测试覆盖率报告
make ci-check         # CI/CD质量检查
make prepush          # 提交前完整验证
make context          # 加载项目上下文（AI开发必用）
```

### 🔍 单个测试执行

```bash
# 运行特定测试文件
pytest tests/unit/api/test_predictions.py::test_prediction_simple -v

# 按标记运行测试
pytest -m "unit and api" -v          # 单元+API测试
pytest -m "critical" --maxfail=5     # 关键功能测试
pytest -m "not slow"                 # 排除慢速测试

# 覆盖率相关
make cov.html                         # HTML覆盖率报告
pytest --cov=src --cov-report=term-missing  # 查看覆盖详情
```

### ⚠️ 关键规则

- **永远不要**对单个文件使用 `--cov-fail-under`
- **优先使用** Makefile命令而非直接调用工具
- **覆盖率阈值**: 40%（当前实际29%，渐进式提升）
- **测试危机**: 使用 `make solve-test-crisis` 解决大量测试失败

---

## 🏗️ 架构概览

### 💻 技术栈
- **后端**: FastAPI + SQLAlchemy 2.0 + Redis + PostgreSQL
- **架构**: DDD + CQRS + 策略工厂 + 依赖注入 + 事件驱动
- **测试**: 完整测试体系，47个标准化标记
- **工具**: 智能修复工具 + 自动化脚本 + CI/CD

### 📁 核心模块结构

```
src/
├── domain/           # 业务实体和领域逻辑
│   ├── entities.py      # 核心业务实体（Match、Team、Prediction）
│   ├── models/          # 领域模型
│   ├── strategies/      # 预测策略模式实现
│   ├── services/        # 领域服务
│   └── events/          # 领域事件定义和总线
├── api/             # FastAPI路由和接口层
├── services/        # 应用服务和数据处理
├── database/        # 数据访问层和仓储模式
├── cache/           # Redis缓存管理和装饰器
├── core/            # 核心基础设施
│   ├── di.py            # 依赖注入容器
│   ├── exceptions.py    # 异常处理
│   └── config/          # 配置管理
├── cqrs/            # CQRS模式实现
├── adapters/        # 适配器模式实现
├── config/          # FastAPI和安全配置
├── ml/              # 机器学习模型
├── features/        # 特征工程
├── monitoring/      # 性能监控和指标
└── utils/           # 工具函数
```

### 🔧 关键设计模式

**策略工厂模式** - `src/domain/strategies/factory.py:15`
```python
from src.domain.strategies.factory import PredictionStrategyFactory
from src.domain.services.prediction_service import PredictionService

# 创建策略工厂
factory = PredictionStrategyFactory()

# 动态选择策略类型
strategy = await factory.create_strategy("ml_model", "enhanced_ml_model")
service = PredictionService(strategy)

# 执行预测
prediction_data = {"match_id": 123, "home_team": "Team A", "away_team": "Team B"}
prediction = await service.create_prediction(prediction_data)
```

**依赖注入容器** - `src/core/di.py:75`
```python
from src.core.di import DIContainer, ServiceCollection, ServiceLifetime
from src.database.manager import DatabaseManager
from src.database.unit_of_work import UnitOfWork

# 配置服务容器
container = ServiceCollection()
container.add_singleton(DatabaseManager)           # 单例模式
container.add_scoped(UnitOfWork)                   # 作用域模式
container.add_transient(PredictionService)         # 瞬时模式

# 构建容器并解析服务
di_container = container.build_container()
db_manager = di_container.resolve(DatabaseManager)
```

**CQRS模式** - `src/cqrs/bus.py:25`
```python
from src.cqrs.bus import CommandBus, QueryBus
from src.cqrs.commands import CreatePredictionCommand
from src.cqrs.queries import GetPredictionQuery

# 命令总线处理写操作
command_bus = CommandBus()
create_cmd = CreatePredictionCommand(
    match_id=123,
    predicted_home_score=2,
    predicted_away_score=1,
    confidence=0.75
)
result = await command_bus.execute(create_cmd)

# 查询总线处理读操作
query_bus = QueryBus()
prediction = await query_bus.execute(GetPredictionQuery(prediction_id=result.id))
```

### ⚠️ 项目结构说明
- **历史冗余**: 存在一些历史遗留的重复路径，应使用标准结构
- **核心功能**: 主要业务逻辑位于 `src/domain/`、`src/api/`、`src/services/`
- **测试分布**: 单元测试在 `tests/unit/`，集成测试在 `tests/integration/`

---

## 🧪 测试策略

### 📊 测试类型分布
- `unit`: 单元测试 (85%) - 单个函数/类测试
- `integration`: 集成测试 (12%) - 多组件交互测试
- `e2e`: 端到端测试 (2%) - 完整用户流程测试
- `performance`: 性能测试 (1%) - 基准和性能分析

### 🎯 Smart Tests配置

**核心稳定测试模块（执行时间<2分钟）**
```bash
tests/unit/utils      # 工具类测试 - 最稳定
tests/unit/cache      # 缓存测试 - 依赖少
tests/unit/core       # 核心模块测试 - 基础功能
```

**47个标准化测试标记**
```bash
# 核心类型标记
pytest -m "unit"          # 单元测试
pytest -m "integration"   # 集成测试
pytest -m "critical"      # 关键功能测试
pytest -m "smoke"         # 冒烟测试

# 依赖环境标记
pytest -m "docker"        # 需要Docker环境
pytest -m "network"       # 需要网络连接
pytest -m "slow"          # 慢速测试 (>30s)
```

**按功能域执行**
```bash
pytest -m "api and critical"     # API关键功能测试
pytest -m "domain or services"   # 业务逻辑测试
pytest -m "ml"                   # 机器学习模块测试
pytest -m "database"             # 数据库相关测试
pytest -m "cache"                # 缓存相关测试
```

### 📋 关键配置文件

**项目配置**
- `pyproject.toml`: 项目元数据、依赖管理、工具配置（Ruff、MyPy、coverage）
- `pytest.ini`: 测试配置、47个标记定义、40%覆盖率设置、Smart Tests优化
- `Makefile`: 613行，完整开发工作流支持，涵盖环境、测试、部署

**环境配置**
- `.env`: 本地开发环境变量（从 `.env.example` 创建）
- `.env.ci`: CI/CD环境变量配置
- `requirements.txt`: 生产依赖
- `requirements-dev.txt`: 开发依赖

**Docker配置**
- `docker-compose.yml`: 开发环境容器编排
- `docker-compose.prod.yml`: 生产环境配置
- `Dockerfile`: 应用容器构建

**智能修复脚本**
- `scripts/smart_quality_fixer.py`: 核心智能修复工具
- `scripts/smart_quality_fixer_enhanced.py`: 增强版修复工具

---

## 🔧 质量工具

### 🤖 智能修复工具（核心）

```bash
# 智能自动修复（解决80%代码质量问题）
python3 scripts/smart_quality_fixer.py

# 一键修复组合
make fix-code              # 格式化 + 基础修复
make ci-auto-fix          # CI/CD自动修复流程
make solve-test-crisis    # 完整测试危机解决方案
```

### 📊 质量检查命令

```bash
make check-quality     # 完整质量检查
make lint             # 运行代码检查
make fmt              # 使用ruff格式化
make syntax-check     # 语法错误检查
make ci-check         # CI/CD质量检查
```

### 🛠️ 现代化工具链

```bash
# Ruff - 统一代码检查和格式化（主要工具）
ruff check src/ tests/       # 代码检查
ruff format src/ tests/      # 代码格式化
ruff check src/ tests/ --fix # 自动修复

# 类型检查和安全
mypy src/ --ignore-missing-imports  # MyPy类型检查
bandit -r src/                     # 安全检查
```

---

## 🚨 问题解决

### 🔥 按优先级分类的解决方案

**1级：紧急修复（测试大量失败 >30%）**
```bash
make solve-test-crisis               # 完整测试危机解决方案
python3 scripts/smart_quality_fixer.py  # 智能自动修复
make test.unit                      # 验证修复效果
```

**2级：智能修复（代码质量问题）**
```bash
make fix-code                        # 格式化 + 基础修复
make ci-auto-fix                     # CI/CD自动修复流程
make check-quality                   # 检查修复结果
```

**3级：环境配置问题**
```bash
make env-check                       # 检查环境健康状态
make create-env                      # 创建环境文件
make check-deps                      # 验证依赖安装
```

**4级：覆盖率优化**
```bash
make coverage                        # 生成覆盖率报告
make test-enhanced-coverage          # 增强覆盖率分析
make cov.html                        # 查看HTML覆盖率详情
```

### 🐳 Docker相关问题

```bash
# 容器化环境修复
make down && make up                 # 重启所有服务
docker-compose exec app make test.unit  # 容器中运行测试
make devops-validate                 # 验证部署环境
```

### 📊 质量监控

```bash
# 实时质量监控
make quality-monitor      # 启动质量监控面板

# 快速状态检查
ruff check src/ --output-format=concise | grep "error" | wc -l     # 错误数量
pytest tests/unit/utils/ tests/unit/core/ --maxfail=5 -x --tb=no   # 核心测试
```

---

## 🔧 高级优化指南

### 🚀 性能调优建议

**数据库优化**
```python
# 连接池优化配置 - src/core/config/database.py
SQLALCHEMY_DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,           # 连接池大小
    max_overflow=30,        # 最大溢出连接
    pool_timeout=30,        # 连接超时
    pool_recycle=3600,      # 连接回收时间
    echo=False              # 生产环境关闭SQL日志
)
```

**缓存优化**
```python
# Redis缓存配置 - src/cache/redis_client.py
import redis
from redis.asyncio import ConnectionPool

# 高性能连接池
pool = ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,     # 最大连接数
    retry_on_timeout=True,  # 超时重试
    socket_timeout=5,       # Socket超时
    socket_connect_timeout=5
)

redis_client = redis.Redis(connection_pool=pool)
```

**API性能优化**
```python
# 异步批处理 - src/api/endpoints/predictions.py
from fastapi import FastAPI, BackgroundTasks
import asyncio

@app.post("/predictions/batch")
async def create_batch_predictions(
    predictions: List[PredictionCreate],
    background_tasks: BackgroundTasks
):
    # 异步批量处理，避免阻塞
    batch_size = 50
    for i in range(0, len(predictions), batch_size):
        batch = predictions[i:i + batch_size]
        background_tasks.add_task(process_prediction_batch, batch)

    return {"message": "Batch processing started"}
```

### 🛠️ 常见故障排除

**依赖冲突解决**
```bash
# 1. 清理虚拟环境
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate

# 2. 重新安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 3. 验证关键依赖
python -c "import fastapi, sqlalchemy, redis; print('✓ Core dependencies OK')"
```

**测试失败排查**
```bash
# 诊断测试问题
pytest --collect-only 2>&1 | grep "error\|failed" | head -10

# 单独运行问题测试
pytest tests/unit/core/test_di.py -v -s --tb=long

# 检查导入问题
python -c "from src.core.di import DIContainer; print('✓ Import OK')"
```

**Docker环境问题**
```bash
# 完全重置Docker环境
make down
docker system prune -f
docker volume prune -f

# 重新构建启动
make up

# 检查容器健康
docker-compose ps
docker-compose logs app | tail -50
```

**内存和性能监控**
```bash
# 监控Python进程内存
ps aux | grep python | grep -v grep

# 使用memory_profiler分析代码
pip install memory-profiler
python -m memory_profiler src/main.py

# 性能基准测试
python -m pytest tests/performance/ --benchmark-only
```

### 📈 智能修复工具进阶用法

**自定义修复规则**
```bash
# 运行增强版智能修复
python3 scripts/smart_quality_fixer_enhanced.py \
  --target=imports \
  --fix-level=aggressive \
  --backup-original

# 仅修复特定模块
python3 scripts/smart_quality_fixer.py \
  --modules=src/api,src/services \
  --dry-run  # 预览修复内容
```

**批量代码重构**
```bash
# 统一导入风格
ruff check src/ --select=I --fix

# 移除未使用的导入
ruff check src/ --select=F401 --fix

# 类型注解修复
mypy src/ --ignore-missing-imports --disallow-untyped-defs
```

---

## 🐳 部署指南

### 🌐 完整服务栈

```bash
make up              # 启动所有服务（app + db + redis + nginx）
make down            # 停止所有服务
make deploy          # 构建并部署容器
make rollback TAG=<sha>  # 回滚到指定版本
docker-compose exec app make test.unit  # 容器中运行测试
```

### 📋 环境配置

**必需的环境变量**
```bash
# 数据库连接
DATABASE_URL=postgresql://user:pass@localhost:5432/football_prediction

# Redis缓存
REDIS_URL=redis://localhost:6379/0

# 应用安全
SECRET_KEY=your-secret-key-here-alphanumeric-32-chars-min

# 运行环境
ENVIRONMENT=development
LOG_LEVEL=INFO
```

**可选的环境变量**
```bash
# 服务配置
API_HOSTNAME=localhost
API_PORT=8000
API_WORKERS=4

# 数据库池配置
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30

# 缓存配置
CACHE_TTL=3600
CACHE_MAX_SIZE=10000

# ML模型配置
ML_MODEL_PATH=/app/models/
ML_PREDICTION_THRESHOLD=0.6
```

**环境管理**
```bash
make create-env      # 从 .env.example 创建 .env
make env-check       # 检查环境健康状态
make check-deps      # 验证依赖安装
```

**环境验证步骤**
1. 创建环境文件：`make create-env`
2. 验证数据库连接：`psql $DATABASE_URL -c "SELECT 1;"`
3. 验证Redis连接：`redis-cli -u $REDIS_URL ping`
4. 检查应用健康：`curl http://localhost:8000/health`

### 🔍 服务访问地址
- **API文档**: http://localhost:8000/docs
- **应用服务**: http://localhost:8000
- **健康检查**: http://localhost:8000/health
- **数据库**: localhost:5432
- **Redis**: localhost:6379
- **Nginx代理**: http://localhost:80 (Docker环境)

### 🚀 CI/CD集成

```bash
make github-actions-test     # 测试GitHub Actions
make ci-full-workflow       # 完整CI流水线验证
make devops-validate        # DevOps环境验证
```

---

## 📚 扩展阅读

### 📋 详细子文档
- [完整架构说明](docs/claude/architecture.md) - 深入了解DDD+CQRS架构
- [测试体系详解](docs/claude/testing.md) - 完整的47标记测试体系
- [部署和CI/CD](docs/claude/deployment.md) - Docker部署和持续集成
- [故障排除指南](docs/claude/troubleshooting.md) - 详细问题解决方案

### 🎯 开发最佳实践
- **架构设计**: 使用依赖注入容器管理组件生命周期，遵循仓储模式
- **异步编程**: 对I/O操作使用async/await实现异步架构
- **测试策略**: 编写全面的单元测试和集成测试，使用Smart Tests优化
- **渐进式改进**: 优先保证测试通过，再逐步提升质量
- **智能工具**: 充分利用自动化工具提升开发效率

### 📊 项目规模指标
- **代码文件**: 253个Python源文件（src/目录）
- **测试文件**: 242个测试文件
- **架构模式**: DDD + CQRS + 策略工厂 + 依赖注入 + 事件驱动
- **工具链**: Ruff + MyPy + Bandit + pytest + Docker
- **覆盖率**: 40%目标阈值，当前实际29%

### 📋 提交前检查清单
- [ ] `make test.smart` 快速验证通过
- [ ] `make test.unit` 完整单元测试通过
- [ ] `make ci-check` 无严重问题
- [ ] `make coverage` 达到40%阈值
- [ ] `make prepush` 完整验证通过
- [ ] 核心功能验证正常

---

## 🏆 项目状态

- **🏗️ 架构**: DDD + CQRS + 策略工厂 + 依赖注入 + 事件驱动（已验证）
- **📏 规模**: 253个源文件，242个测试文件，企业级代码库
- **🧪 测试**: 完整测试体系，47个标准化标记，覆盖率40%（当前29%）
- **🛡️ 质量**: 现代化工具链（Ruff + MyPy + bandit + 安全扫描）
- **🤖 工具**: 智能修复工具 + 自动化脚本，完整CI/CD工作流
- **🎯 方法**: 本地开发环境，渐进式改进策略，Docker容器化部署

### 🚀 核心竞争优势
- **智能修复**: 一键解决80%的代码质量问题
- **渐进式改进**: 不破坏现有功能的持续优化方法
- **完整工具链**: 从开发到部署的全流程自动化
- **企业级就绪**: 完整的CI/CD、监控、安全和质量保证体系

---

## 🔧 高级优化指南

### 🚀 性能调优建议

**数据库优化**
```python
# 连接池优化配置 - src/core/config/database.py
SQLALCHEMY_DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,           # 连接池大小
    max_overflow=30,        # 最大溢出连接
    pool_timeout=30,        # 连接超时
    pool_recycle=3600,      # 连接回收时间
    echo=False              # 生产环境关闭SQL日志
)
```

**缓存优化**
```python
# Redis缓存配置 - src/cache/redis_client.py
import redis
from redis.asyncio import ConnectionPool

# 高性能连接池
pool = ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,     # 最大连接数
    retry_on_timeout=True,  # 超时重试
    socket_timeout=5,       # Socket超时
    socket_connect_timeout=5
)

redis_client = redis.Redis(connection_pool=pool)
```

**API性能优化**
```python
# 异步批处理 - src/api/endpoints/predictions.py
from fastapi import FastAPI, BackgroundTasks
import asyncio

@app.post("/predictions/batch")
async def create_batch_predictions(
    predictions: List[PredictionCreate],
    background_tasks: BackgroundTasks
):
    # 异步批量处理，避免阻塞
    batch_size = 50
    for i in range(0, len(predictions), batch_size):
        batch = predictions[i:i + batch_size]
        background_tasks.add_task(process_prediction_batch, batch)

    return {"message": "Batch processing started"}
```

### 🛠️ 常见故障排除

**依赖冲突解决**
```bash
# 1. 清理虚拟环境
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate

# 2. 重新安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 3. 验证关键依赖
python -c "import fastapi, sqlalchemy, redis; print('✓ Core dependencies OK')"
```

**测试失败排查**
```bash
# 诊断测试问题
pytest --collect-only 2>&1 | grep "error\|failed" | head -10

# 单独运行问题测试
pytest tests/unit/core/test_di.py -v -s --tb=long

# 检查导入问题
python -c "from src.core.di import DIContainer; print('✓ Import OK')"
```

**Docker环境问题**
```bash
# 完全重置Docker环境
make down
docker system prune -f
docker volume prune -f

# 重新构建启动
make up

# 检查容器健康
docker-compose ps
docker-compose logs app | tail -50
```

**内存和性能监控**
```bash
# 监控Python进程内存
ps aux | grep python | grep -v grep

# 使用memory_profiler分析代码
pip install memory-profiler
python -m memory_profiler src/main.py

# 性能基准测试
python -m pytest tests/performance/ --benchmark-only
```

### 📈 智能修复工具进阶用法

**自定义修复规则**
```bash
# 运行增强版智能修复
python3 scripts/smart_quality_fixer_enhanced.py \
  --target=imports \
  --fix-level=aggressive \
  --backup-original

# 仅修复特定模块
python3 scripts/smart_quality_fixer.py \
  --modules=src/api,src/services \
  --dry-run  # 预览修复内容
```

**批量代码重构**
```bash
# 统一导入风格
ruff check src/ --select=I --fix

# 移除未使用的导入
ruff check src/ --select=F401 --fix

# 类型注解修复
mypy src/ --ignore-missing-imports --disallow-untyped-defs
```

---

*文档版本: v20.0 (增强优化版) | 维护者: Claude Code | 更新时间: 2025-11-16*

## 🔄 版本更新说明 (v20.0)

### 架构代码示例增强
- **策略工厂模式**: 添加完整的预测服务使用示例
- **依赖注入容器**: 增加服务生命周期管理示例
- **CQRS模式**: 补充命令查询分离的具体使用场景

### 配置文件路径明确化
- **项目配置**: 详细说明pyproject.toml、pytest.ini、Makefile的作用
- **环境配置**: 区分必需和可选环境变量，添加验证步骤
- **Docker配置**: 明确容器编排文件的用途
- **智能修复脚本**: 标注核心修复工具位置

### 环境配置完善
- **必需变量**: 详细的数据库、Redis、安全配置
- **可选变量**: 服务、连接池、缓存、ML模型高级配置
- **环境验证**: 提供完整的健康检查流程

### 性能调优和故障排除
- **数据库优化**: SQLAlchemy连接池配置建议
- **缓存优化**: Redis高性能连接池设置
- **API优化**: 异步批处理和后台任务示例
- **故障排除**: 依赖冲突、测试失败、Docker问题的解决方案
- **性能监控**: 内存分析、基准测试工具使用方法
