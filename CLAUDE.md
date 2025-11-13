# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**重要提醒：请始终使用简体中文回复用户，用户看不懂英文。**

---

## 🎯 AI开发者快速指南

### ⚡ 首次打开项目必做

```bash
# 1️⃣ 环境准备
make install && make env-check

# 2️⃣ 智能修复（解决80%问题）
python3 scripts/smart_quality_fixer.py

# 3️⃣ 加载上下文（AI开发必备）
make context

# 4️⃣ 验证成功
make test.unit
```

### 🔥 常用开发命令

```bash
make test.unit        # 运行单元测试
make coverage         # 查看覆盖率报告
make fix-code         # 一键修复代码质量问题
make ci-check         # CI/CD质量检查
make solve-test-crisis # 测试危机解决方案
make context          # 加载项目上下文
```

---

## 📊 项目架构概览

### 🏗️ 核心架构模式
- **DDD (领域驱动设计)**: 严格的分层架构，domain/包含业务核心逻辑
- **CQRS (命令查询职责分离)**: src/cqrs/目录实现读写分离
- **事件驱动架构**: src/events/和src/domain/events/实现异步处理
- **依赖注入容器**: 轻量级DI实现，管理组件生命周期
- **策略工厂模式**: src/domain/strategies/动态创建预测策略

### 🏗️ 技术栈
- **后端**: FastAPI + SQLAlchemy 2.0 + Redis + PostgreSQL
- **架构**: DDD + CQRS + 依赖注入 + 事件驱动
- **测试**: 完整测试体系，47个标准化标记，覆盖率40%（pytest.ini配置）
- **工具**: 智能修复工具 + 自动化脚本，完整的CI/CD工作流

### 🎯 核心模块结构
```
src/
├── domain/           # 业务实体和领域逻辑
├── api/             # FastAPI路由和CQRS处理
├── services/        # 业务服务和数据处理
├── database/        # 数据访问层和仓储模式
├── cache/           # Redis缓存管理
├── core/            # 配置、认证、验证
├── data/            # 数据收集和处理
├── features/        # 特征工程
├── ml/              # 机器学习模型
├── tasks/           # 异步任务和定时作业
└── monitoring/      # 性能监控和指标
```

### 🔧 关键设计模式

**策略工厂模式 - 动态创建预测策略**
```python
from src.domain.strategies.factory import PredictionStrategyFactory

factory = PredictionStrategyFactory()
strategy = await factory.create_strategy("ml_predictor", "ml_model")
service = PredictionService(strategy)
prediction = await service.create_prediction(data)
```

**依赖注入容器 - 轻量级DI实现**
```python
from src.core.di import DIContainer, ServiceCollection

# 创建容器
container = ServiceCollection()
container.add_singleton(DatabaseManager)
container.add_transient(PredictionService)
di_container = container.build_container()

# 解析服务
service = di_container.resolve(PredictionService)
```

**事件驱动架构**
```python
from src.core.event_application import initialize_event_system
from src.domain.events.prediction_events import PredictionCreatedEvent

# 初始化事件系统
await initialize_event_system()

# 发布事件
event = PredictionCreatedEvent(prediction_id="123", match_data=data)
await event_bus.publish(event)
```

**CQRS模式 - 命令查询分离**
```python
# 命令端（写操作）
from src.cqrs.commands import CreatePredictionCommand
command = CreatePredictionCommand(match_data=data)
result = await command_bus.execute(command)

# 查询端（读操作）
from src.cqrs.queries import GetPredictionQuery
query = GetPredictionQuery(prediction_id="123")
prediction = await query_bus.execute(query)
```

---

## 🧪 测试体系详解

### 📊 测试类型分布
- `unit`: 单元测试 (85%) - 单个函数/类测试
- `integration`: 集成测试 (12%) - 多组件交互测试
- `e2e`: 端到端测试 (2%) - 完整用户流程测试
- `performance`: 性能测试 (1%) - 基准和性能分析

### 🎯 常用测试命令

**按类型执行**
```bash
make test.unit          # 仅单元测试
make test.int           # 仅集成测试
pytest -m "not slow"    # 排除慢速测试
make test.smart         # 优化的Smart Tests组合
```

**按功能域执行**
```bash
pytest -m "api and critical"     # API关键功能测试
pytest -m "domain or services"   # 业务逻辑测试
pytest -m "ml"                   # 机器学习模块测试
pytest -m "database"             # 数据库相关测试
pytest -m "cache"                # 缓存相关测试
```

**调试特定测试**
```bash
pytest tests/unit/api/test_predictions.py::test_prediction_simple -v
pytest -m "unit and api" -v      # 功能域测试
pytest --cov=src --cov-report=term-missing  # 查看覆盖详情
make coverage-unit               # 单元测试覆盖率
make cov.html                    # 生成HTML覆盖率报告
```

### ⚠️ 重要测试规则
- **永远不要**对单个文件使用 `--cov-fail-under`
- **覆盖率阈值**: 40%（pytest.ini配置，渐进式改进策略）
- **优先使用**: Makefile命令而非直接pytest
- **测试危机**: 使用 `make solve-test-crisis` 解决大量测试失败
- **智能修复**: 使用 `python3 scripts/smart_quality_fixer.py` 自动修复

---

## 🔧 代码质量工具链

### 🎯 一键修复工具
```bash
python3 scripts/smart_quality_fixer.py      # 智能自动修复（核心工具）
make fix-code                               # 一键修复格式和语法
make ci-auto-fix                            # CI/CD自动修复流程
```

### 📊 质量检查命令
```bash
make check-quality     # 完整质量检查
make lint             # 运行代码检查
make fmt              # 使用black和isort格式化
make syntax-check     # 语法错误检查
make ci-check         # CI/CD质量检查
```

### 🛠️ 现代化工具
```bash
# Ruff - 统一代码检查和格式化（主要工具）
ruff check src/ tests/       # 代码检查
ruff format src/ tests/      # 代码格式化
ruff check src/ tests/ --fix # 自动修复

# 类型检查和安全
mypy src/ --ignore-missing-imports  # MyPy类型检查
bandit -r src/                     # 安全检查

# 传统工具链（备用）
black src/ tests/            # Black格式化
isort src/ tests/            # 导入排序
flake8 src/ tests/           # 代码检查
```

---

## 🚀 开发工作流程

### 📋 推荐开发流程
1. **环境启动**: `make install && make env-check`
2. **加载上下文**: `make context` (AI开发必备)
3. **智能修复**: `python3 scripts/smart_quality_fixer.py`
4. **开发**: 编写代码和测试
5. **质量检查**: `make ci-check`
6. **测试验证**: `make test.unit && make coverage`
7. **提交**: `make prepush`

### 🎯 渐进式改进策略
当遇到大量质量问题时：
1. **语法修复** - 运行 `make ci-auto-fix` 修复语法错误
2. **功能重建** - 恢复影响测试的核心功能
3. **测试危机解决** - 运行 `make solve-test-crisis` 完整解决方案
4. **质量提升** - 执行 `make improve-test-quality`
5. **成果提交** - 记录改进成果

### 🚨 问题解决优先级
```bash
# 1级: 紧急修复 (测试大量失败)
make solve-test-crisis

# 2级: 智能修复 (代码质量问题)
make smart-fix

# 3级: 质量检查 (验证修复效果)
make ci-check

# 4级: 渐进式改进 (持续优化)
make continuous-improvement
```

---

## 🐳 Docker和部署

### 🌐 完整服务栈
```bash
make up              # 启动所有服务（app + db + redis + nginx）
make down            # 停止所有服务
make deploy          # 构建并部署容器
make rollback TAG=<sha>  # 回滚到指定版本
docker-compose exec app make test.unit  # 容器中运行测试
```

### 📋 环境配置
- **本地开发**: `.env` + PostgreSQL + Redis
- **Docker环境**: `docker-compose.yml` + 完整服务栈
- **CI环境**: `.env.ci` + 容器化验证

### 🔍 访问地址
- **API文档**: http://localhost:8000/docs
- **应用服务**: http://localhost:8000
- **数据库**: localhost:5432
- **Redis**: localhost:6379
- **Nginx代理**: http://localhost:80

---

## ⚡ 常见问题解决

### 🚨 测试失败处理
```bash
# 1. 测试危机修复（首选）
make solve-test-crisis

# 2. 智能质量修复
python3 scripts/smart_quality_fixer.py

# 3. 验证修复结果
make test.unit

# 4. 生成状态报告
make test-status-report
```

### 🔧 环境问题修复
```bash
# 完全环境重置
make clean && make install && make test.unit

# 依赖缺失问题
make check-deps

# 环境变量检查
make check-env

# 创建环境文件
make create-env
```

---

## 🎯 最佳实践

### ✅ 开发原则
- 使用依赖注入容器管理组件生命周期
- 遵循仓储模式进行数据访问抽象
- 对I/O操作使用async/await实现异步架构
- 编写全面的单元测试和集成测试
- **关键规则**: 永远不要对单个文件使用 `--cov-fail-under`
- 使用Makefile命令而非直接调用工具
- 优先使用 `make ci-check` 进行质量验证
- **AI开发**: 始终以 `make context` 开始，获取项目上下文
- **渐进式改进**: 优先保证测试通过，再逐步提升质量
- **智能工具**: 充分利用 `scripts/smart_quality_fixer.py` 等自动化工具
- **Docker开发**: 使用 `docker-compose up` 启动完整服务栈
- **测试策略**: 按标记运行测试（如 `-m "unit and api"`）而非直接指定文件路径

### 🎯 成功标准
- **测试通过**: 单元测试和集成测试正常运行
- **覆盖率达标**: 当前40%（pytest.ini配置），渐进式提升
- **代码质量**: 通过Ruff + MyPy + 安全检查
- **功能正常**: 核心模块导入和基础功能验证
- **CI就绪**: `make ci` 模拟通过

### 📋 提交前检查清单
- [ ] `make test.unit` 通过
- [ ] `make ci-check` 无严重问题
- [ ] `make coverage` 达到40%阈值
- [ ] `make prepush` 完整验证通过
- [ ] 核心功能验证正常
- [ ] 创建改进报告（如有重大修改）

---

## 🏆 项目状态

- **🏗️ 架构**: DDD + CQRS + 策略工厂 + 依赖注入 + 事件驱动 + 异步架构
- **🧪 测试**: 完整测试体系，47个标准化标记，覆盖率40%（渐进式提升）
- **🛡️ 质量**: 现代化工具链（Ruff + MyPy + bandit + 安全扫描）
- **🤖 工具**: 智能修复工具 + 自动化脚本，完整的CI/CD工作流
- **📏 规模**: 企业级代码库，完整的Makefile命令体系
- **🎯 方法**: 本地开发环境，渐进式改进策略，Docker容器化部署
- **📊 监控**: 实时质量监控 + 覆盖率趋势分析 + CI/CD指标仪表板

### 🚀 核心竞争优势
- **智能修复**: 一键解决80%的代码质量问题
- **渐进式改进**: 不破坏现有功能的持续优化方法
- **完整工具链**: 从开发到部署的全流程自动化
- **企业级就绪**: 完整的CI/CD、监控、安全和质量保证体系

### 🔍 关键架构洞察
这个足球预测系统展现了现代企业级Python应用的最佳实践：

1. **分层架构**: 严格的DDD分层，确保业务逻辑与技术实现分离
2. **异步优先**: 全面采用async/await，支持高并发处理
3. **测试驱动**: 47个标准化测试标记，支持精准的测试执行
4. **质量内建**: 智能修复工具链，自动化质量保证流程
5. **容器就绪**: Docker + docker-compose完整服务栈配置

### 💡 AI开发要点
- **始终以 `make context` 开始**：获取完整的项目上下文
- **使用标记而非文件路径**：如 `pytest -m "unit and api"`
- **遵循渐进式改进**：先保证功能正常，再提升质量
- **利用智能工具**：`scripts/smart_quality_fixer.py` 等
- **Docker优先**：使用 `docker-compose up` 确保环境一致性

---

*文档版本: v20.0 (Claude Code 2025架构优化版) | 维护者: Claude Code | 更新时间: 2025-11-13*