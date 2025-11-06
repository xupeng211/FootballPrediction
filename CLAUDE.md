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

### ⚡ 核心开发命令

```bash
make install          # 安装依赖
make test.unit        # 运行单元测试（385个测试）
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
- **测试**: 195个测试文件，25+种标记，覆盖率30%
- **工具**: 113个自动化脚本，600+个Makefile命令

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
strategy = StrategyFactory.create_strategy("ml_model")
service = PredictionService(strategy)
prediction = await service.create_prediction(data)
```

**CQRS模式 - 命令查询分离**
```python
# 写操作
await command_bus.handle(CreatePredictionCommand(...))
# 读操作
predictions = await query_bus.handle(GetPredictionsQuery(...))
```

**依赖注入容器**
```python
container = Container()
container.register_singleton(DatabaseManager)
service = container.resolve(PredictionService)
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
pytest -m "unit"              # 仅单元测试
pytest -m "integration"       # 仅集成测试
pytest -m "not slow"          # 排除慢速测试
```

**按功能域执行**
```bash
pytest -m "api and critical"  # API关键功能测试
pytest -m "domain or services" # 业务逻辑测试
pytest -m "ml"                 # 机器学习模块测试
```

**调试特定测试**
```bash
pytest tests/unit/api/test_predictions.py::test_prediction_simple -v
pytest -m "unit and api" -v   # 功能域测试
pytest --cov=src --cov-report=term-missing  # 查看覆盖详情
```

### ⚠️ 重要测试规则
- **永远不要**对单个文件使用 `--cov-fail-under`
- **覆盖率阈值**: 30%（渐进式改进策略）
- **优先使用**: Makefile命令而非直接pytest

---

## 🔧 代码质量工具链

### 🎯 一键修复工具
```bash
python3 scripts/smart_quality_fixer.py      # 智能自动修复（核心工具）
python3 scripts/quality_guardian.py --check-only  # 全面质量检查
make fix-code                               # 一键修复格式和语法
```

### 📊 质量检查命令
```bash
make check-quality     # 完整质量检查
make lint             # 运行flake8和mypy
make fmt              # 使用black和isort格式化
make syntax-check     # 语法错误检查
```

### 🛠️ 现代化工具
```bash
ruff check src/ tests/       # Ruff代码检查（替代flake8）
ruff format src/ tests/      # Ruff格式化（替代black + isort）
ruff check src/ tests/ --fix # Ruff自动修复
mypy src/ --ignore-missing-imports  # MyPy类型检查
```

---

## 🚀 开发工作流程

### 📋 推荐开发流程
1. **启动**: `make install && make env-check`
2. **修复**: `python3 scripts/smart_quality_fixer.py`
3. **开发**: 编写代码和测试
4. **验证**: `make test.unit && make coverage`
5. **提交**: `make prepush`

### 🎯 渐进式改进策略
当遇到大量质量问题时：
1. **语法修复** - 修复invalid-syntax错误
2. **功能重建** - 恢复影响测试的核心功能
3. **测试验证** - 确保测试通过
4. **成果提交** - 记录改进成果

### 📈 质量监控
```bash
# 检查语法错误数量
ruff check src/ --output-format=concise | grep "invalid-syntax" | wc -l

# 检查测试通过数量
pytest tests/unit/utils/ tests/unit/core/ --maxfail=5 -x --tb=no | grep -E "(PASSED|FAILED)" | wc -l

# 验证核心功能
python3 -c "import src.utils.date_utils as du; import src.cache.decorators as cd; print(f'✅ 核心功能正常')"
```

---

## 🐳 Docker和部署

### 🌐 完整服务栈
```bash
make up              # 启动所有服务（app + db + redis + nginx）
make down            # 停止所有服务
docker-compose exec app make test.unit  # 容器中运行测试
```

### 📋 环境配置
- **本地开发**: `.env` + PostgreSQL + Redis
- **Docker环境**: `docker-compose.yml` + 完整服务栈
- **CI环境**: `.env.ci` + 容器化验证

### 🔍 访问地址
- **API文档**: http://localhost:8000/docs
- **监控面板**: http://localhost:3000（Grafana）
- **数据库**: localhost:5432

---

## ⚡ 常见问题解决

### 🚨 测试失败处理
```bash
# 1. 测试危机修复
python3 scripts/fix_test_crisis.py

# 2. 智能质量修复
python3 scripts/smart_quality_fixer.py

# 3. 验证修复结果
make test.unit
```

### 🔧 环境问题修复
```bash
# 完全环境重置
make clean && make install && make test.unit

# 依赖缺失问题
source .venv/bin/activate
pip install pandas numpy aiohttp psutil scikit-learn
```

### 📊 覆盖率优化
```bash
python3 scripts/enhanced_coverage_analysis.py   # 覆盖率分析
python3 scripts/phase35_ai_coverage_master.py   # AI覆盖率优化
make test-enhanced-coverage                     # 验证优化效果
```

---

## 🎯 最佳实践

### ✅ 开发原则
- 使用依赖注入容器管理组件生命周期
- 遵循仓储模式进行数据访问抽象
- 对I/O操作使用async/await实现异步架构
- 编写全面的单元测试和集成测试
- **关键规则**: 永远不要对单个文件使用 `--cov-fail-under`

### 🎯 成功标准
- **测试通过**: 385个测试用例正常运行
- **覆盖率达标**: 当前30%，渐进式提升
- **代码质量**: 通过Ruff + MyPy检查
- **功能正常**: 核心模块导入和基础功能验证

### 📋 提交前检查清单
- [ ] `make test.unit` 通过
- [ ] `make check-quality` 无严重问题
- [ ] `make coverage` 达到阈值
- [ ] 核心功能验证正常
- [ ] 创建改进报告（如有重大修改）

---

## 🛠️ 智能工具选择指南

### 根据问题类型选择工具
- **代码质量问题** → `smart_quality_fixer.py` → `quality_guardian.py --check-only`
- **测试失败危机** → `fix_test_crisis.py` → `emergency_quality_fixer.py`
- **覆盖率不足** → `enhanced_coverage_analysis.py` → `phase35_ai_coverage_master.py`
- **类型检查错误** → `comprehensive_mypy_fix.py`
- **语法错误** → `fix_syntax_errors.py` → `precise_error_fixer.py`
- **CI/CD问题** → `ci_test_integration.py` → `generate_test_report.py`

### 🔄 持续改进工具
```bash
python3 scripts/continuous_improvement_engine.py   # 持续监控和优化
python3 scripts/intelligent_quality_monitor.py     # 实时质量监控
./scripts/emergency-response.sh                     # 一键紧急恢复
```

---

## 📚 相关文档

- `CLAUDE_IMPROVEMENT_STRATEGY.md` - 渐进式改进策略详解
- `README.md` - 项目总体介绍和部署指南
- `TOOLS.md` - 113个自动化脚本详细说明
- `docs/TEST_IMPROVEMENT_GUIDE.md` - 测试改进机制指南

---

## 🏆 项目状态

- **🏗️ 架构**: DDD + CQRS + 依赖注入 + 异步架构
- **🧪 测试**: 195个测试文件，25+种标准化标记，覆盖率30%
- **🛡️ 质量**: 完整的代码质量工具链（Ruff + MyPy + bandit）
- **🤖 工具**: 113个自动化脚本，辅助开发和质量修复
- **📏 规模**: Makefile 1062行，600+个开发命令
- **🎯 方法**: 本地开发环境，渐进式改进方法

---

*文档版本: v13.0 (优化精简版) | 维护者: Claude Code | 更新时间: 2025-11-06*