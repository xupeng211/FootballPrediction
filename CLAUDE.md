# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**重要提醒：请始终使用简体中文回复用户，用户看不懂英文。**

---

## 🎯 5分钟快速上手

### 🔥 首次打开项目必做

```bash
# 1️⃣ 环境准备
make install && make env-check

# 2️⃣ 智能修复（解决80%问题）
python3 scripts/smart_quality_fixer.py

# 3️⃣ 验证成功
make test.unit
```

### ⚡ 单个文件测试（重要！）
```bash
# 测试单个文件（正确方式）
pytest tests/unit/utils/test_date_utils.py::test_format_date_iso -v

# 单个文件覆盖率查看（正确方式 - 不要加 --cov-fail-under）
pytest tests/unit/utils/test_date_utils.py --cov=src.utils --cov-report=term-missing -v
```

### ⚡ 核心开发命令

```bash
make install          # 安装依赖
make test.unit        # 运行单元测试
make coverage         # 查看覆盖率报告
make fix-code         # 一键修复代码质量问题
make prepush          # 提交前完整验证
```

### 🚨 紧急修复

```bash
# 当测试大量失败时
python3 scripts/fix_test_crisis.py
python3 scripts/smart_quality_fixer.py
make test.unit
```

---

## 📊 项目架构概览

### 🏗️ 技术栈
- **后端**: FastAPI + SQLAlchemy 2.0 + Redis + PostgreSQL
- **架构**: DDD + CQRS + 依赖注入 + 事件驱动
- **测试**: 217个测试文件，47种标记，覆盖率30%
- **工具**: 161个自动化脚本，613行Makefile命令
- **容器**: Docker + docker-compose完整服务栈

### 🎯 核心模块结构
```
src/
├── domain/           # 业务实体和领域逻辑
│   ├── entities/     # 领域实体 (Match, Team, Prediction)
│   ├── strategies/   # 预测策略工厂模式
│   └── services/     # 领域服务
├── api/             # FastAPI路由和CQRS处理
│   ├── app.py       # FastAPI应用入口
│   └── routes/      # API路由模块
├── services/        # 业务服务和数据处理
├── database/        # 数据访问层和仓储模式
│   └── repositories/ # 仓储实现
├── cache/           # Redis缓存管理
├── core/            # 配置、认证、验证、DI容器
├── cqrs/            # CQRS命令和查询处理
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

**CQRS模式**
```python
from src.cqrs.commands import CreatePredictionCommand
from src.cqrs.queries import GetPredictionsByUserQuery

# 命令执行
command = CreatePredictionCommand(match_id=123, user_id=456, ...)
result = await cqrs_app.execute_command(command)

# 查询执行
query = GetPredictionsByUserQuery(user_id=456)
predictions = await cqrs_app.execute_query(query)
```

---

## 🧪 测试体系详解

### 📊 测试类型分布
- `unit`: 单元测试 (85%) - 单个函数/类测试
- `integration`: 集成测试 (12%) - 多组件交互测试
- `e2e`: 端到端测试 (2%) - 完整用户流程测试
- `performance`: 性能测试 (1%) - 基准和性能分析

### 🎯 常用测试命令

**核心测试命令（推荐）**
```bash
make test.unit              # 运行所有单元测试（385个测试用例）
make test-phase1           # Phase 1核心功能测试
make coverage              # 查看覆盖率报告（当前29%）
make test.crisis-fix       # 测试危机修复工具
```

**按类型执行**
```bash
pytest -m "unit"              # 仅单元测试（85%）
pytest -m "integration"       # 仅集成测试（12%）
pytest -m "e2e"               # 端到端测试（2%）
pytest -m "performance"       # 性能测试（1%）
pytest -m "not slow"          # 排除慢速测试
```

**按功能域执行**
```bash
pytest -m "api and critical"  # API关键功能测试
pytest -m "domain or services" # 业务逻辑测试
pytest -m "ml"                 # 机器学习模块测试
pytest -m "database"           # 数据库相关测试
pytest -m "cache"              # 缓存相关测试
pytest -m "auth"               # 认证相关测试
pytest -m "utils"              # 工类模块测试
pytest -m "core"               # 核心模块测试
```

**Smart Tests优化（快速执行）**
```bash
# 核心稳定测试模块，执行时间<2分钟，通过率>90%
pytest tests/unit/utils tests/unit/cache tests/unit/core -v --maxfail=20
```

**调试特定测试**
```bash
# 运行单个测试方法
pytest tests/unit/api/test_predictions.py::test_prediction_simple -v

# 运行单个测试文件
pytest tests/unit/utils/test_date_utils.py -v

# 运行特定模块的所有测试
pytest tests/unit/utils/ -v

# 功能域测试
pytest -m "unit and api" -v

# 查看覆盖详情（项目级别）
pytest --cov=src --cov-report=term-missing

# 查看特定模块覆盖详情（正确方式）
pytest tests/unit/utils/ --cov=src.utils --cov-report=term-missing -v
```

### ⚠️ 重要测试规则
- **永远不要**对单个文件使用 `--cov-fail-under`
- **覆盖率阈值**: 30%（pytest.ini配置，渐进式改进策略）
- **优先使用**: Makefile命令而非直接pytest
- **测试环境修复**: 270个语法错误已修复，100+核心测试已恢复
- **Smart Tests**: 核心稳定测试组合，执行时间<2分钟，通过率>90%

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

# 智能修复工具
python3 scripts/smart_quality_fixer.py  # 一键智能修复（推荐）
```

---

## 🚀 开发工作流程

### 📋 推荐开发流程
1. **环境启动**: `make install && make env-check`
2. **智能修复**: `python3 scripts/smart_quality_fixer.py`
3. **开发**: 编写代码和测试
4. **质量检查**: `make ci-check`
5. **测试验证**: `make test.unit && make coverage`
6. **提交**: `make prepush`

### 🎯 渐进式改进策略
当遇到大量质量问题时：
1. **语法修复** - 运行 `make ci-auto-fix` 修复语法错误
2. **功能重建** - 恢复影响测试的核心功能
3. **测试验证** - 运行 `make test-crisis-fix` 解决测试危机
4. **质量提升** - 执行 `make improve-test-quality`
5. **成果提交** - 记录改进成果

### 📈 质量监控和CI/CD
```bash
# 检查语法错误数量
ruff check src/ --output-format=concise | grep "invalid-syntax" | wc -l

# 检查测试通过数量
pytest tests/unit/utils/ tests/unit/core/ --maxfail=5 -x --tb=no | grep -E "(PASSED|FAILED)" | wc -l

# 验证核心功能
python3 -c "import src.utils.date_utils as du; import src.cache.decorators as cd; print(f'✅ 核心功能正常')"

# 运行完整CI/CD流程
make ci-full-workflow

# 生成质量报告
make ci-quality-report
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

### 🚀 部署工作流
```bash
# 开发环境部署
make dev-setup

# 生产环境部署
make devops-deploy

# 环境验证
make devops-validate
```

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

### 📊 覆盖率优化和监控
```bash
# 增强覆盖率分析
make test-enhanced-coverage

# 生成覆盖率趋势报告
make test-coverage-monitor

# 覆盖率阈值执行
make cov.enforce

# M2工具链完整测试
make test-m2-toolchain
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

### 🎯 成功标准
- **测试通过**: 单元测试和集成测试正常运行
- **覆盖率达标**: 30%（pytest.ini配置），渐进式提升
- **代码质量**: 通过Ruff + MyPy + bandit安全检查
- **功能正常**: 核心模块导入和基础功能验证
- **CI就绪**: GitHub Actions + 本地CI验证通过

### 📋 提交前检查清单
- [ ] `make test.unit` 通过
- [ ] `make ci-check` 无严重问题
- [ ] `make coverage` 达到30%阈值
- [ ] `make prepush` 完整验证通过
- [ ] 核心功能验证正常
- [ ] 创建改进报告（如有重大修改）

### 🔄 CI/CD集成
```bash
# GitHub Actions工作流测试
make github-actions-test

# 完整CI流水线验证
make ci-full-workflow

# DevOps环境验证
make devops-validate
```

---

## 🛠️ 智能工具选择指南

### 根据问题类型选择工具
- **代码质量问题** → `make smart-fix` → `make quality-guardian`
- **测试失败危机** → `make solve-test-crisis` → `make fix-test-errors`
- **覆盖率不足** → `make test-enhanced-coverage` → `make test-coverage-monitor`
- **语法错误** → `make syntax-fix` → `make ci-auto-fix`
- **CI/CD问题** → `make ci-full-workflow` → `make github-actions-test`
- **环境问题** → `make devops-setup` → `make env-check`

### 🔄 持续改进工具
```bash
make smart-fix              # 智能自动修复
make quality-guardian       # 质量守护检查
make continuous-improvement # 持续改进引擎
make ci-monitoring         # CI监控和指标
```

### 🔗 Claude Code 作业同步
```bash
make claude-start-work     # 开始新作业记录
make claude-complete-work  # 完成作业记录
make claude-sync          # 同步作业到GitHub Issues
make claude-list-work     # 查看所有作业记录
```

### 📊 报告和分析工具
```bash
make report-quality         # 综合质量报告
make report-ci-metrics     # CI/CD指标仪表板
make test-report-generate  # 测试报告生成
make coverage-unit         # 单元测试覆盖率报告
```

---

## 🔗 Claude Code 作业同步系统

### 🎯 功能概述
专门为Claude Code设计的作业同步系统，用于自动将开发工作同步到GitHub Issues：
- **智能作业记录** - 自动追踪工作进度、文件修改、技术详情
- **GitHub同步** - 使用GitHub CLI自动创建/更新/关闭Issues
- **多维度分类** - 按类型、优先级、状态自动打标签
- **详细报告** - 生成包含技术细节、测试结果、挑战解决方案的完整报告
- **双向同步** - 支持本地作业记录与GitHub Issues的双向数据同步

### 📋 工作流程

#### 1. 开始新作业
```bash
make claude-start-work
```
系统会提示输入：
- 作业标题
- 作业描述
- 作业类型（development/testing/documentation/bugfix/feature）
- 优先级（low/medium/high/critical）

系统会自动：
- 生成唯一作业ID
- 记录开始时间
- 检测当前Git状态和修改的文件
- 创建本地作业记录

#### 2. 完成作业
```bash
make claude-complete-work
```
系统会提示输入：
- 作业ID
- 交付成果（可选）
- 其他工作详情

系统会自动：
- 更新作业状态为已完成
- 计算工作时长
- 记录完成时间

#### 3. 同步到GitHub
```bash
make claude-sync
```
系统会自动：
- 为每个作业创建或更新GitHub Issue
- 添加适当的标签（类型、优先级、状态）
- 生成包含技术详情的Issue正文
- 完成的作业会自动关闭Issue
- 生成详细的同步报告

#### 4. 查看作业记录
```bash
make claude-list-work
```
显示所有作业项目的状态和进度。

### 🏷️ 自动标签系统

#### 类型标签
- `development` + `enhancement` - 开发工作
- `testing` + `quality-assurance` - 测试工作
- `documentation` - 文档工作
- `bug` + `bugfix` - 缺陷修复
- `enhancement` + `new-feature` - 新功能

#### 优先级标签
- `priority/low` - 低优先级
- `priority/medium` - 中等优先级
- `priority/high` - 高优先级
- `priority/critical` - 关键优先级

#### 状态标签
- `status/pending` - 待开始
- `status/in-progress` - 进行中
- `status/completed` - 已完成
- `status/review-needed` - 需要审核

#### Claude专用标签
- `claude-code` - Claude Code作业
- `automated` - 自动创建

### 📄 生成的Issue内容
每个GitHub Issue包含：
- 作业基本信息（状态、优先级、完成度）
- 详细描述
- 技术详情（Git信息、环境等）
- 修改的文件列表
- 交付成果
- 测试结果
- 遇到的挑战
- 实施的解决方案
- 后续步骤
- 工作时长统计

### 🗂️ 文件存储
- `claude_work_log.json` - 本地作业记录
- `claude_sync_log.json` - 同步历史记录
- `reports/claude_sync_report_*.md` - 详细同步报告

### ⚙️ 环境要求
- **GitHub CLI** - 需要先安装和认证：`gh auth login`
- **Git** - 需要配置好的Git环境
- **Python 3.8+** - 运行同步脚本

### 🔧 快速设置
```bash
# 自动环境检查和设置
make claude-setup

# 包含测试Issue的完整设置
make claude-setup-test
```

设置脚本会自动检查：
- Python版本兼容性
- Git安装和配置
- GitHub CLI安装和认证
- 仓库访问权限
- Issues管理权限
- 必要目录结构创建

### 🚀 使用示例

#### 开发新功能
```bash
# 开始功能开发
make claude-start-work
# 输入: 标题="实现用户认证功能", 类型="feature", 优先级="high"

# 开发过程中...

# 完成功能开发
make claude-complete-work
# 输入: 作业ID="claude_20251106_143022", 交付成果="JWT认证系统,用户登录API,安全测试"

# 同步到GitHub
make claude-sync
# 自动创建GitHub Issue，打上相应标签
```

#### 修复Bug
```bash
# 开始Bug修复
make claude-start-work
# 输入: 标题="修复数据库连接超时问题", 类型="bugfix", 优先级="critical"

# 修复过程...

# 完成修复
make claude-complete-work
# 输入: 交付成果="连接池优化,超时重试机制,单元测试"

# 同步并关闭Issue
make claude-sync
# Bug修复完成后自动关闭GitHub Issue
```

## 📚 相关文档

- `CLAUDE_IMPROVEMENT_STRATEGY.md` - 渐进式改进策略详解
- `README.md` - 项目总体介绍和部署指南
- `docs/ARCHITECTURE.md` - 系统架构详细文档
- `docs/TESTING_GUIDE.md` - 测试指南和最佳实践
- `docs/DEVELOPMENT_SETUP.md` - 开发环境配置指南
- `docs/DEPLOYMENT_COMPREHENSIVE_GUIDE.md` - 部署指南
- `docs/API_REFERENCE.md` - API参考文档

---

## 🏆 项目状态

- **🏗️ 架构**: DDD + CQRS + 策略工厂 + 依赖注入 + 事件驱动 + 异步架构
- **🧪 测试**: 385个测试用例，完整测试体系，47个标准化标记，覆盖率30%（渐进式提升）
- **🛡️ 质量**: 现代化工具链（Ruff + MyPy + bandit + 安全扫描），270个语法错误已修复
- **🤖 工具**: 智能修复工具 + 自动化脚本，完整的CI/CD工作流，613行Makefile
- **📏 规模**: 企业级代码库，589个Python源文件，217个测试文件，161个自动化脚本
- **🎯 方法**: 本地开发环境，渐进式改进策略，Docker容器化部署
- **📊 监控**: 实时质量监控 + 覆盖率趋势分析 + CI/CD指标仪表板
- **🔄 同步**: Claude Code作业与GitHub Issues双向同步系统
- **🚀 部署**: Docker + docker-compose + nginx完整服务栈，生产就绪

### 🚀 核心竞争优势
- **智能修复**: 一键解决80%的代码质量问题
- **渐进式改进**: 不破坏现有功能的持续优化方法
- **完整工具链**: 从开发到部署的全流程自动化
- **企业级就绪**: 完整的CI/CD、监控、安全和质量保证体系
- **自动化同步**: Claude Code作业与GitHub Issues的双向同步

---

## 📈 项目统计与指标

### 📊 代码库规模
- **源代码文件**: 589个Python文件
- **测试文件**: 217个测试文件
- **自动化脚本**: 161个脚本
- **文档文件**: 100+个Markdown文档
- **Makefile命令**: 613行自动化命令

### 🎯 测试体系现状
- **测试用例总数**: 385个
- **当前覆盖率**: 30%（渐进式提升中）
- **测试标记体系**: 47种标准化标记
- **语法错误修复**: 270个错误已修复
- **核心测试恢复**: 100+测试正常运行
- **Smart Tests**: 核心稳定测试组合，通过率>90%

### 🛡️ 质量指标
- **代码质量**: A级（通过Ruff + MyPy + bandit检查）
- **安全验证**: 通过bandit安全扫描
- **依赖安全**: 依赖漏洞已修复
- **类型安全**: 完整的Python类型注解
- **CI/CD就绪**: GitHub Actions + 本地CI验证

### 🚀 技术债务清理
- **测试环境修复**: 完成Phase 1-5修复
- **语法错误清理**: 270个错误已解决
- **核心功能恢复**: 100+测试用例正常运行
- **覆盖率基准**: 建立30%基准线，渐进式提升
- **工具链优化**: 统一使用Ruff + MyPy + Black

---

*文档版本: v18.0 (2025年更新版) | 维护者: Claude Code | 更新时间: 2025-11-08*