# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**重要提醒：请始终使用简体中文回复用户，用户看不懂英文。**

---

## 🎯 Claude Code 使用指南 (重要)

### 📋 首次打开此项目时

**必须首先执行**：
```bash
# 1. 阅读改进策略文档
cat CLAUDE_IMPROVEMENT_STRATEGY.md

# 2. 运行改进启动器
python3 scripts/start_progressive_improvement.py

# 3. 评估当前状态
source .venv/bin/activate && ruff check src/ --output-format=concise | head -10
```

### 🚀 渐进式改进策略

**核心策略**：避免大规模变更，采用四阶段流程
1. **语法修复** → 2. **功能重建** → 3. **测试验证** → 4. **成果提交**
- ✅ **测试驱动**：以测试通过作为成功标准
- ✅ **数据驱动**：基于质量报告制定策略

### 📊 快速状态检查

```bash
# 检查语法错误数量
source .venv/bin/activate && ruff check src/ --output-format=concise | grep "invalid-syntax" | wc -l

# 检查测试通过数量
pytest tests/unit/utils/ tests/unit/core/ --maxfail=5 -x --tb=no | grep -E "(PASSED|FAILED)" | wc -l

# 验证核心功能
source .venv/bin/activate && python3 -c "
import src.utils.date_utils as du
import src.cache.decorators as cd
print(f'✅ 核心功能: {hasattr(du.DateUtils, \"get_month_start\")} && {hasattr(cd, \"CacheDecorator\")}')
"
```

### 🎯 改进工作流程

1. **启动阶段** - 运行 `python3 scripts/start_progressive_improvement.py`
2. **修复阶段** - 按照四阶段流程执行改进
3. **验证阶段** - 确保测试通过和功能正常
4. **记录阶段** - 创建改进报告并提交成果

### ⚠️ 重要提醒

- **必须**先阅读 `CLAUDE_IMPROVEMENT_STRATEGY.md`
- **必须**使用渐进式方法，避免一次性大改
- **必须**以测试通过作为成功标准
- **必须**创建改进报告记录成果

---

## 📊 项目概述

**足球预测系统** - 基于现代Python技术栈的Web应用，采用DDD + CQRS架构模式。

**🎯 核心特性：**
- **现代化架构**: FastAPI + SQLAlchemy 2.0 + Redis + PostgreSQL 全异步设计
- **分层架构**: DDD设计 + CQRS模式 + 依赖注入容器 + 事件驱动
- **完整测试**: 195个测试文件，25+种标准化标记，覆盖率30%（渐进式改进）
- **智能工具**: 113个自动化脚本，辅助质量修复和危机处理
- **容器化**: Docker支持，完整CI/CD配置

**🛠️ 技术栈**: Python 3.11+, 异步架构, 容器化部署, 多环境支持

---

## 🚀 快速开始

### 🎯 推荐流程（本地环境）
```bash
# 1️⃣ 环境准备
make install                    # 安装依赖并创建虚拟环境
make env-check                  # 验证环境健康状态

# 2️⃣ 质量修复（首次运行必需）
python3 scripts/smart_quality_fixer.py    # 智能自动修复（解决80%问题）

# 3️⃣ 验证运行
make test.unit                   # 运行单元测试（385个测试用例）
make coverage                    # 生成覆盖率报告
```

### 🐳 Docker环境
```bash
make up                          # 启动完整服务栈
make down                        # 停止所有服务
docker-compose exec app make test.unit  # 容器中运行测试
```

### ⚡ 快速修复
```bash
python3 scripts/fix_test_crisis.py           # 测试危机修复
python3 scripts/quality_guardian.py --check-only  # 全面质量检查
```

---

## 🔧 开发指南

### 📋 环境要求
- **Python**: 3.11+
- **数据库**: PostgreSQL 13+
- **缓存**: Redis 6+
- **容器**: Docker & Docker Compose (可选)

### 🗄️ 数据库设置
```bash
# 创建数据库
createdb football_prediction

# 运行迁移
alembic upgrade head

# 填充种子数据（可选）
python scripts/seed_data.py
```

### 📚 API文档访问
- **本地开发**: http://localhost:8000/docs
- **生产环境**: https://your-domain.com/docs

### 🔧 核心开发命令

### ⭐ 必做命令（开发流程）
```bash
make install          # 安装项目依赖
make env-check        # 环境健康检查
make test.unit        # 仅单元测试（标记为'unit'）
make test.int         # 集成测试（标记为'integration'）
make test.e2e         # 端到端测试（标记为'e2e'）
make coverage         # 覆盖率报告（HTML和终端输出）
make prepush          # 提交前完整验证
make ci               # CI/CD流水线验证
```

### 🧪 测试执行

**🎯 核心测试命令（基于Makefile）**
```bash
make test                    # 运行pytest单元测试（-v --maxfail=5）
make coverage               # 运行覆盖率测试（阈值80%，仅unit标记）
make coverage-fast          # 快速覆盖率（unit and not slow）
make coverage-unit          # 单元测试覆盖率（生成HTML报告）
make test-crisis-fix        # 测试危机紧急修复
make test-m2-toolchain      # M2完整工具链测试
make syntax-check           # 语法错误检查
make syntax-fix             # 自动修复语法错误
```

**📊 M2增强测试工具链**
```bash
make test-enhanced-coverage     # 增强覆盖率分析
make test-enhanced-full         # 完整增强测试分析
make test-report-generate       # 生成综合测试报告
make test-report-html           # 生成HTML测试报告
make test-ci-integration        # CI/CD测试集成
make test-coverage-monitor      # 监控覆盖率趋势
```

**🎯 精准测试（基于pytest标记）**
```bash
# 按测试类型
pytest -m "unit"                    # 仅单元测试（85%）
pytest -m "integration"             # 仅集成测试（12%）
pytest -m "e2e"                     # 端到端测试（2%）
pytest -m "performance"             # 性能测试（1%）

# 按功能域
pytest -m "api and critical"        # API关键功能测试
pytest -m "domain or services"      # 业务逻辑测试
pytest -m "database"                # 数据库相关测试
pytest -m "cache"                   # 缓存相关测试
pytest -m "auth"                    # 认证相关测试
pytest -m "ml"                      # 机器学习模块测试

# 按执行特征
pytest -m "unit and not slow"       # 单元测试（排除慢速）
pytest -m "critical"                # 关键功能测试
pytest -m "smoke"                   # 冒烟测试
pytest -m "regression"              # 回归测试
pytest -m "issue94"                 # 特定Issue相关测试

# 调试和特殊情况
pytest tests/unit/api/test_predictions.py::test_prediction_simple -v  # 调试特定测试
pytest -m "unit and api" -v        # 功能域测试
pytest -m "not slow" --maxfail=3   # 快速反馈测试
pytest --cov=src --cov-report=term-missing  # 查看具体覆盖情况
```

### 🛠️ 代码质量

**🎯 核心质量命令（基于Makefile）**
```bash
make fix-code                # 一键修复代码格式和语法问题
make fix-syntax              # 修复语法和格式问题
make fix-imports             # 修复导入语句和排序
make check-quality           # 检查代码质量（不修复）
make lint                    # 运行flake8和mypy检查
make fmt                     # 使用black和isort格式化
make quality                 # 完整质量检查（lint + format + test）
make check                   # quality命令的别名
```

**🔧 现代化工具链**
```bash
ruff check src/ tests/       # Ruff代码检查（替代flake8）
ruff format src/ tests/      # Ruff格式化（替代black + isort）
ruff check src/ tests/ --fix # Ruff自动修复
mypy src/ --ignore-missing-imports  # MyPy类型检查
black src/ tests/            # Black格式化
isort src/ tests/            # 导入排序
```

**🤖 智能修复工具体系**
```bash
python3 scripts/smart_quality_fixer.py      # 智能自动修复（核心工具）
python3 scripts/quality_guardian.py --check-only  # 全面质量检查
python3 scripts/fix_test_crisis.py         # 测试危机修复
python3 scripts/emergency_quality_fixer.py  # 紧急质量修复
```

**⚠️ 重要规则：**
- **优先使用Makefile命令**而非直接pytest或工具
- **永远不要对单个文件使用 `--cov-fail-under`**（项目采用渐进式覆盖率改进）
- **覆盖率阈值设置为30%**（pytest.ini配置），采用渐进式改进策略
- **智能修复工具可解决80%的常见问题**
- 推荐使用本地开发环境，虚拟环境确保依赖隔离

---

## 🏗️ 系统架构

### 🎯 DDD + CQRS 核心架构

**分层架构设计**
- **🏛️ 领域层** (`src/domain/`, `src/domain_simple/`): 业务实体、策略模式、事件系统
- **⚡ 应用层** (`src/api/`): FastAPI路由、CQRS实现、依赖注入、健康检查
- **🔧 基础设施层** (`src/database/`, `src/cache/`): PostgreSQL、Redis、仓储模式
- **🔄 服务层** (`src/services/`): 数据处理、缓存、ML模型服务、预测引擎
- **📊 数据层** (`src/data/`): 数据收集、存储、处理和质量控制
- **🎯 核心层** (`src/core/`): 配置、认证、验证、缓存、指标
- **🧪 任务系统** (`src/tasks/`): 数据收集、备份、定时任务
- **📡 流处理** (`src/streaming/`): Kafka消费者、消息处理、数据处理器
- **🔍 监控系统** (`src/monitoring/`): 指标收集、性能监控
- **🤖 ML模块** (`src/ml/`): 机器学习模型训练和预测

### 🧩 核心设计模式

**策略工厂模式**
```python
# 动态创建预测策略
strategy = StrategyFactory.create_strategy("ml_model")
service = PredictionService(strategy)
prediction = await service.create_prediction(data)
```

**CQRS模式**
```python
# 命令侧 - 写操作
await command_bus.handle(CreatePredictionCommand(...))

# 查询侧 - 读操作
predictions = await query_bus.handle(GetPredictionsQuery(...))
```

**依赖注入容器**
```python
container = Container()
container.register_singleton(DatabaseManager)
service = container.resolve(PredictionService)
```

### 🛠️ 技术栈
- **Web框架**: FastAPI + Pydantic + 自动文档
- **数据层**: SQLAlchemy 2.0 异步ORM + Redis缓存
- **基础设施**: PostgreSQL + Alembic迁移 + 仓储模式
- **监控**: WebSocket + Prometheus + 健康检查

### 📱 应用入口
- **`src/main.py`** - 生产环境完整应用（包含生命周期管理、中间件、监控系统）
- **`src/main_simple.py`** - 调试测试简化版

### 🔄 事件驱动架构
```python
# 事件系统初始化
from src.core.event_application import initialize_event_system, shutdown_event_system
from src.observers import ObserverManager

# 在应用生命周期中管理事件
@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_event_system()
    # ... 应用启动逻辑
    await shutdown_event_system()
```

### 🎯 中间件系统
- **I18nMiddleware** (`src/middleware/i18n.py`): 国际化支持
- **PerformanceMonitoringMiddleware** (`src/performance/middleware.py`): 性能监控

---

## 🧪 测试体系详解

### 🎯 25+种标准化测试标记

**📊 核心测试类型**
- `unit`: 单元测试 (85%) - 单个函数或类测试
- `integration`: 集成测试 (12%) - 多组件交互测试
- `e2e`: 端到端测试 (2%) - 完整用户流程测试
- `performance`: 性能测试 (1%) - 基准和性能分析

**🏗️ 功能域标记**
- `api`, `domain`, `services` - 业务逻辑层
- `database`, `cache` - 数据存储层
- `auth`, `monitoring` - 系统服务层
- `utils`, `core`, `decorators` - 基础设施层

**⚡ 执行特征标记**
- `critical`: 关键功能测试 (必须通过)
- `slow`: 慢速测试 (>30秒，可选择性执行)
- `smoke`: 冒烟测试 (基本功能验证)
- `regression`: 回归测试 (防止问题重现)

### 🚀 测试执行示例

**按类型执行**
```bash
pytest -m "unit"                    # 仅单元测试
pytest -m "integration"             # 仅集成测试
pytest -m "not slow"                # 排除慢速测试
```

**按功能域执行**
```bash
pytest -m "api and critical"        # API关键功能测试
pytest -m "domain or services"      # 业务逻辑测试
pytest -m "ml"                      # 机器学习模块测试
```

**组合条件执行**
```bash
pytest -m "(unit or integration) and critical"  # 关键功能测试
pytest -m "unit and not slow"                    # 快速单元测试
```

---

## 📦 配置文件说明

### 🎯 核心配置文件
- **pytest.ini**: 25+种标准化测试标记，覆盖率阈值30%，异步测试配置，警告过滤
- **pyproject.toml**: 项目构建配置，包含Ruff、MyPy、pytest等工具配置（注意：存在大量TODO注释需要清理）
- **requirements.txt**: 锁定的依赖版本，确保环境一致性
- **.ruffignore**: Ruff忽略规则，排除有问题的脚本文件

### 🚀 Makefile开发工具链
- **规模**: 1062行，600+个开发命令
- **功能**: 完整的CI/CD自动化、质量检查、测试执行、部署管理
- **特色**: M2测试工具链、危机修复、渐进式改进支持

### 🤖 自动化脚本体系 (scripts/**)
**总计113个脚本，涵盖全开发流程：**

**🎯 核心修复工具**
- `smart_quality_fixer.py` - 智能自动修复（核心脚本）
- `quality_guardian.py` - 全面质量检查
- `fix_test_crisis.py` - 测试危机修复
- `emergency_quality_fixer.py` - 紧急质量修复

**📊 覆盖率专项工具**
- `phase35_ai_coverage_master.py` - 覆盖率优化
- `coverage_improvement_executor.py` - 覆盖率执行器
- `enhanced_coverage_analysis.py` - 增强覆盖率分析
- `coverage_dashboard.py` - 覆盖率监控面板

**🔧 问题诊断修复**
- `comprehensive_mypy_fix.py` - MyPy问题修复
- `precise_error_fixer.py` - 精确错误修复
- `fix_b904_exceptions.py` - B904异常修复
- `fix_syntax_errors.py` - 语法错误修复

**🚨 危机处理工具**
- `emergency-response.sh` - 紧急响应脚本
- `continuous_improvement_engine.py` - 持续改进引擎
- `start_progressive_improvement.py` - 渐进式改进启动器

**📈 测试和CI工具**
- `ci_test_integration.py` - CI测试集成
- `generate_test_report.py` - 测试报告生成
- `test_framework_builder.py` - 测试框架构建
- `sync_github_issues.py` - GitHub问题同步

---

## ⚡ 快速故障排除

### 常见问题解决方案
```bash
# 环境问题修复
make install && make env-check           # 完整环境安装和检查

# 依赖缺失问题
source .venv/bin/activate
pip install pandas numpy aiohttp psutil scikit-learn  # 安装核心依赖

# 代码质量问题
ruff check src/ tests/                   # Ruff代码检查
python3 scripts/smart_quality_fixer.py   # 智能自动修复（核心工具）

# 测试问题
make test.unit                           # 运行单元测试
python3 scripts/coverage_improvement_executor.py  # 覆盖率改进

# 完全环境重置
make clean && make install && make test.unit
```

### 关键提醒
- **推荐使用本地开发环境**，虚拟环境确保依赖隔离
- **优先使用Makefile命令**而非直接pytest
- **智能修复工具**可解决80%的常见问题
- **核心脚本**: `smart_quality_fixer.py` 是主要的智能修复工具

---

## 🎯 开发最佳实践

### 核心原则
- 使用依赖注入容器管理组件生命周期
- 遵循仓储模式进行数据访问抽象
- 对I/O操作使用async/await实现异步架构
- 编写全面的单元测试和集成测试
- **关键规则**: 永远不要对单个文件使用 `--cov-fail-under`

### 智能开发工作流
```bash
# 推荐的开发流程
make install                          # 安装依赖
python3 scripts/smart_quality_fixer.py # 智能质量修复
make test.unit                        # 运行单元测试
make prepush                          # 提交前验证
```

### 🚨 危机处理流程
```bash
# 当测试大量失败时的应急流程
python3 scripts/fix_test_crisis.py        # 1. 测试危机修复
python3 scripts/smart_quality_fixer.py    # 2. 智能质量修复
make test.unit                           # 3. 验证修复结果
```

### 🎯 项目状态
- **🏗️ 架构**: DDD + CQRS + 依赖注入 + 异步架构
- **🧪 测试**: 195个测试文件，25+种标准化标记，覆盖率30%
- **🛡️ 质量**: 完整的代码质量工具链（Ruff + MyPy + bandit）
- **🤖 工具**: 113个自动化脚本，辅助开发和质量修复
- **📏 规模**: Makefile 1062行，600+个开发命令
- **🎯 方法**: 本地开发环境，渐进式改进方法

---

## 🛠️ 智能修复工具体系详解

### 🎯 核心使用工作流

**📝 日常开发流程**
```bash
# 1. 首次打开项目时的必做流程
python3 scripts/start_progressive_improvement.py    # 运行改进启动器
source .venv/bin/activate && ruff check src/ --output-format=concise | head -10  # 评估状态

# 2. 开发过程中的一键修复
python3 scripts/smart_quality_fixer.py              # 智能自动修复（解决80%问题）
make test                                           # 验证修复结果
```

**🧪 测试危机处理流程**
```bash
# 当测试大量失败时的应急流程
python3 scripts/fix_test_crisis.py                  # 1. 测试危机修复
python3 scripts/smart_quality_fixer.py              # 2. 智能质量修复
make test.unit                                       # 3. 验证修复结果
```

**📊 覆盖率优化流程**
```bash
# 渐进式覆盖率提升
python3 scripts/enhanced_coverage_analysis.py       # 1. 覆盖率分析
python3 scripts/phase35_ai_coverage_master.py       # 2. AI覆盖率优化
make test-enhanced-coverage                          # 3. 验证优化效果
python3 scripts/coverage_dashboard.py               # 4. 监控覆盖率趋势
```

### 🤖 工具选择决策树

**根据问题类型选择工具：**
- **代码质量问题** → `smart_quality_fixer.py` → `quality_guardian.py --check-only`
- **测试失败危机** → `fix_test_crisis.py` → `emergency_quality_fixer.py`
- **覆盖率不足** → `enhanced_coverage_analysis.py` → `phase35_ai_coverage_master.py`
- **类型检查错误** → `comprehensive_mypy_fix.py`
- **语法错误** → `fix_syntax_errors.py` → `precise_error_fixer.py`
- **CI/CD问题** → `ci_test_integration.py` → `generate_test_report.py`

### 💡 高级功能特性

**🔄 持续改进引擎**
```bash
python3 scripts/continuous_improvement_engine.py   # 持续监控和优化
```

**📈 智能质量监控**
```bash
python3 scripts/intelligent_quality_monitor.py     # 实时质量监控
```

**🚨 紧急响应系统**
```bash
./scripts/emergency-response.sh                     # 一键紧急恢复
```

### 🎯 工具集成最佳实践

1. **开发前**: `start_progressive_improvement.py` → 评估状态
2. **开发中**: `smart_quality_fixer.py` → 实时修复
3. **测试前**: `check-quality` → 质量检查
4. **提交前**: `make prepush` → 完整验证
5. **危机时**: `fix_test_crisis.py` → 紧急修复

---

---

## 🎯 Claude Code 特别提醒

### ✅ 开发工作流程
1. **使用中文回复** - 用户看不懂英文，始终用简体中文
2. **优先Makefile命令** - 避免直接使用pytest，优先使用make命令
3. **渐进式改进** - 避免大规模变更，采用四阶段流程
4. **测试驱动** - 以测试通过作为成功标准
5. **善用智能工具** - 113个脚本解决80%的常见问题

### ⚠️ 关键约束
- 永远不要对单个文件使用 `--cov-fail-under`
- 覆盖率阈值30%，采用渐进式改进策略
- 推荐本地开发环境，确保依赖隔离
- 必须先运行 `start_progressive_improvement.py` 评估状态

### 🎯 成功标准
- 测试通过：385个测试用例正常运行
- 覆盖率达标：当前30%，渐进式提升
- 代码质量：通过Ruff + MyPy检查
- 功能正常：核心模块导入和基础功能验证

---

*文档版本: v12.0 (全面优化版) | 维护者: Claude Code | 更新时间: 2025-11-05*

**基于实际代码分析生成，包含600+个Makefile命令和113个自动化脚本的详细使用指南**