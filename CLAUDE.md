# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**重要提醒：请始终使用简体中文回复用户，用户看不懂英文。**

---

## 🎯 项目概览

**足球预测系统** - 基于现代Python技术栈的企业级Web应用，采用DDD + CQRS架构模式。

**🏗️ 核心架构：**
- **Web框架**: FastAPI + SQLAlchemy 2.0 + Redis + PostgreSQL 全异步设计
- **架构模式**: DDD + CQRS + 依赖注入容器 + 事件驱动
- **测试体系**: 195个测试文件，25+种标准化标记，覆盖率30%
- **智能工具**: 113个自动化脚本，辅助开发和质量修复
- **部署**: Docker + 完整CI/CD配置

**🛠️ 技术栈**: Python 3.11+, 异步架构, 容器化部署

---

## 🚀 快速开始

### 📋 首次使用（必须执行）

```bash
# 1️⃣ 环境准备
make install                    # 安装依赖并创建虚拟环境
make env-check                  # 验证环境健康状态

# 2️⃣ 质量修复（解决80%常见问题）
python3 scripts/smart_quality_fixer.py

# 3️⃣ 验证运行
make test.unit                   # 运行单元测试
make coverage                    # 生成覆盖率报告
```

### 🐳 Docker环境

```bash
make up                          # 启动完整服务栈
make down                        # 停止所有服务
docker-compose exec app make test.unit  # 容器中运行测试
```

---

## 🏗️ 系统架构

### 📁 核心目录结构

```
src/
├── api/             # FastAPI应用层 - 路由、中间件、CQRS实现
├── domain/          # 领域层 - 业务实体、策略模式、事件系统
├── database/        # 数据层 - PostgreSQL、SQLAlchemy、仓储模式
├── cache/           # 缓存层 - Redis、分布式缓存、智能预热
├── services/        # 服务层 - 业务逻辑、数据处理、ML模型服务
└── utils/           # 工具模块 - 日期工具、缓存装饰器、通用函数

tests/
├── unit/            # 单元测试 (85%) - 按功能域组织
├── integration/     # 集成测试 (12%) - 组件交互测试
├── e2e/             # 端到端测试 (2%) - 完整用户流程
└── performance/     # 性能测试 (1%) - 基准测试

scripts/             # 113个自动化脚本 - 质量修复、测试、部署工具
```

### 🎯 核心设计模式

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

### 📱 应用入口

- **`src/main.py`** - 生产环境完整应用
- **`src/main_simple.py`** - 调试测试简化版

---

## 🧪 测试体系

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

### 🚀 测试执行命令

```bash
# 按类型执行
pytest -m "unit"                    # 仅单元测试
pytest -m "integration"             # 仅集成测试
pytest -m "not slow"                # 排除慢速测试

# 按功能域执行
pytest -m "api and critical"        # API关键功能测试
pytest -m "domain or services"      # 业务逻辑测试
pytest -m "ml"                      # 机器学习模块测试

# 组合条件执行
pytest -m "(unit or integration) and critical"  # 关键功能测试
pytest -m "unit and not slow"                    # 快速单元测试
```

---

## 🔧 核心开发命令

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

### 🛠️ 代码质量

```bash
ruff check src/ tests/     # 代码检查（替代make lint）
ruff format src/ tests/    # 代码格式化（替代make fmt）

# 智能修复工具
python3 scripts/smart_quality_fixer.py      # 智能自动修复（核心工具）
python3 scripts/quality_guardian.py --check-only  # 全面质量检查
python3 scripts/fix_test_crisis.py         # 测试危机修复
```

### ⚠️ 重要规则

- 优先使用Makefile命令而非直接pytest
- 永远不要对单个文件使用 `--cov-fail-under`（项目采用渐进式覆盖率改进）
- 推荐使用本地开发环境
- 使用`ruff check`替代`make lint`（项目已迁移到ruff）
- **覆盖率阈值设置为30%**（pytest.ini配置），采用渐进式改进策略
- **智能修复工具可解决80%的常见问题**

---

## 🚨 故障排除

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

### 🚨 危机处理流程

```bash
# 当测试大量失败时的应急流程
python3 scripts/fix_test_crisis.py        # 1. 测试危机修复
python3 scripts/smart_quality_fixer.py    # 2. 智能质量修复
make test.unit                           # 3. 验证修复结果
```

---

## 🛠️ 智能修复工具体系

### 🤖 核心修复工具

```bash
python3 scripts/smart_quality_fixer.py      # 自动质量修复（核心脚本）
python3 scripts/quality_guardian.py --check-only  # 全面质量检查
python3 scripts/fix_test_crisis.py         # 测试危机修复
```

### ⚡ 高级修复工具集

```bash
# 📊 覆盖率专项提升
python3 scripts/phase35_ai_coverage_master.py     # 覆盖率优化
python3 scripts/coverage_improvement_executor.py  # 覆盖率执行器

# 🔧 问题诊断和修复
python3 scripts/comprehensive_mypy_fix.py        # MyPy问题修复
python3 scripts/f821_undefined_name_fixer.py     # F821错误修复
python3 scripts/precise_error_fixer.py           # 精确错误修复

# 🚨 危机处理工具
python3 scripts/emergency-response.sh            # 紧急响应脚本
python3 scripts/continuous_improvement_engine.py # 持续改进引擎
```

### 💡 工具选择指南

| 场景 | 推荐工具 | 说明 |
|------|----------|------|
| 📝 日常开发 | `smart_quality_fixer.py` | 自动修复常见问题 |
| 🧪 测试失败 | `fix_test_crisis.py` | 测试危机处理 |
| 📊 覆盖率提升 | `phase35_ai_coverage_master.py` | 覆盖率优化 |
| 🚨 紧急情况 | `emergency-response.sh` | 紧急响应和恢复 |
| 🔍 全面检查 | `quality_guardian.py --check-only` | 完整质量分析 |

---

## 📦 配置文件说明

- **pytest.ini**: 25+种标准化测试标记，覆盖率阈值30%，并行测试配置
- **pyproject.toml**: 项目构建配置，包含Ruff、MyPy、pytest等工具配置
- **.ruffignore**: Ruff忽略规则，排除有问题的脚本文件
- **Makefile**: 1062行，600+个命令，完整开发工具链，包含CI/CD自动化
- **scripts/**: 113个自动化脚本，涵盖修复、测试、部署等全流程
- **requirements.txt**: 锁定的依赖版本，确保环境一致性

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

### 🎯 项目状态
- **🏗️ 架构**: DDD + CQRS + 依赖注入 + 异步架构
- **🧪 测试**: 195个测试文件，25+种标准化标记，覆盖率30%
- **🛡️ 质量**: 完整的代码质量工具链（Ruff + MyPy + bandit）
- **🤖 工具**: 113个自动化脚本，辅助开发和质量修复
- **📏 规模**: Makefile 1062行，600+个开发命令
- **🎯 方法**: 本地开发环境，渐进式改进方法

---

## 📚 API文档访问

- **本地开发**: http://localhost:8000/docs
- **生产环境**: https://your-domain.com/docs

---

*文档版本: v12.0 (优化版) | 维护者: Claude Code | 更新时间: 2025-11-08*