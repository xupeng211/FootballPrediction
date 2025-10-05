# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📑 目录

- [语言设置](#语言设置)
- [快速开始](#快速开始)
- [核心命令](#核心命令)
- [开发原则](#开发原则)
- [项目架构](#项目架构)
- [重要文档](#重要文档)
- [故障排除](#故障排除)

## 🌏 语言设置

**请始终使用中文回复！**

- 语言偏好: 中文 (简体)
- 回复语言: 中文
- 注释语言: 中文
- 文档语言: 中文

## 🚀 快速开始

### 🤖 AI工具快速检查清单

**首次进入项目必须执行**：
```bash
make install      # 安装依赖
make context      # 加载项目上下文 ⭐最重要
make env-check    # 验证环境健康
make test-phase1  # 验证测试环境（71个测试）
```

**每次代码修改后**：
```bash
make test-quick   # 快速测试验证
make fmt && make lint  # 代码格式化和质量检查
make prepush      # 完整提交前检查
```

**如果添加了新依赖**：
```bash
make smart-deps   # 智能依赖检查和指导
```

### 日常开发

```bash
make env-check    # 检查环境
make test-quick   # 快速测试
make fmt && make lint  # 代码格式化和检查
make prepush      # 提交前检查
```

## 📋 核心命令

### 必须知道的命令

| 命令 | 说明 | 何时使用 |
|------|------|----------|
| `make help` | 查看所有命令 | 不确定时 |
| `make context` | 加载项目上下文 | 开始工作前 |
| `make install` | 安装依赖 | 首次使用 |
| `make test-quick` | 快速测试（不包含coverage） | 开发中 |
| `make test.unit` | 只运行单元测试 | 主要测试方式 |
| `make coverage` | 运行覆盖率测试（80%阈值） | CI要求 |
| `make ci` | 完整CI检查 | 推送前 |
| `./ci-verify.sh` | Docker CI验证 | 发布前 |
| `make prepush` | 提交前检查 | 必须运行 |
| `make fmt` | 代码格式化 | 提交前 |
| `make lint` | 代码质量检查 | 提交前 |
| `make type-check` | 类型检查 | 提交前 |
| `make lock-deps` | 锁定依赖版本 | 依赖更新后 |
| `make verify-deps` | 验证依赖一致性 | 环境检查 |
| `make smart-deps` | 智能依赖检查（带AI提醒） | 依赖变更后 |
| `make ai-deps-reminder` | 显示依赖管理提醒 | 需要指导时 |
| `make env-check` | 检查开发环境 | 环境问题排查 |
| `make coverage-local` | 本地覆盖率检查（60%阈值） | 日常开发 |
| `make coverage-ci` | CI覆盖率检查（80%阈值） | 提交前验证 |

### 快速参考

- 完整命令列表：[CLAUDE_QUICK_REFERENCE.md](./CLAUDE_QUICK_REFERENCE.md)
- 故障排除：[CLAUDE_TROUBLESHOOTING.md](./CLAUDE_TROUBLESHOOTING.md)

### 🔍 重要提醒

- **CI验证**: 推送前必须运行 `./ci-verify.sh` 模拟完整CI环境
- **Docker服务**: 集成测试需要 `docker-compose up -d postgres redis`
- **Phase 1测试**: 使用 `make test-phase1`（不是 `make test.phase1`）

## 🤖 AI开发原则

### 核心原则

1. **文档优先**：修改代码前先更新文档
   - API变更 → 更新 `docs/reference/API_REFERENCE.md`
   - 数据库变更 → 更新 `docs/reference/DATABASE_SCHEMA.md`
   - 完成功能 → 生成完成报告
2. **使用Makefile**：保持命令一致性
3. **测试驱动**：确保测试覆盖率（目标≥80%）
4. **修改优于创建**：优先修改现有文件

### ⚠️ 测试运行重要提醒

**AI编程工具特别注意**：

1. **不要对单个测试文件使用 `--cov=src`** - 这会显示误导性的0%覆盖率
2. **Phase 1 测试已完成**：
   - data.py: 17个测试，90%覆盖率
   - features.py: 27个测试，88%覆盖率
   - predictions.py: 27个测试，88%覆盖率
   - **总计**：71个测试用例
3. **使用正确的命令**：
   ```bash
   make test-phase1    # Phase 1核心测试
   make test-quick     # 快速测试
   make coverage       # 完整覆盖率
   ```

### 文档自动化规则

根据 `docs/AI_DEVELOPMENT_DOCUMENTATION_RULES.md`：

- **API变更** → 更新 `docs/reference/API_REFERENCE.md`
- **数据库变更** → 更新 `docs/reference/DATABASE_SCHEMA.md`
- **完成阶段** → 生成完成报告
- **修复Bug** → 创建bugfix报告

## 🏗️ 项目架构

### 技术栈

- **Python版本**: 3.11+ （项目要求）
- **框架**: FastAPI + SQLAlchemy 2.0
- **数据库**: PostgreSQL (生产) + SQLite (测试)
- **缓存**: Redis
- **任务队列**: Celery
- **MLOps**: MLflow + Feast
- **监控**: Prometheus/Grafana
- **测试**: pytest (96.35%覆盖率)
- **代码质量**: black, flake8, mypy, bandit

### 项目结构

```
src/
├── api/           # FastAPI路由和端点
├── cache/         # Redis缓存管理
├── config/        # 配置管理（环境变量、设置）
├── core/          # 核心业务逻辑
├── data/          # 数据处理和ETL
├── database/      # SQLAlchemy模型和数据库连接
├── features/      # 特征工程
├── lineage/       # 数据血缘追踪
├── locales/       # 国际化支持
├── middleware/    # FastAPI中间件（认证、CORS等）
├── models/        # 预测模型
├── monitoring/    # 监控和指标
├── scheduler/     # 任务调度
├── services/      # 业务服务层
├── streaming/     # 实时数据流
├── stubs/         # 类型存根
├── tasks/         # 异步任务
└── utils/         # 通用工具函数

tests/ (96.35%覆盖率)
├── unit/          # 单元测试 ⭐主要使用
│   ├── api/       # API单元测试
│   ├── database/  # 数据库测试
│   ├── services/  # 服务测试
│   └── utils/     # 工具测试
├── integration/   # 集成测试
├── e2e/          # 端到端测试
├── factories/    # 测试数据工厂
├── fixtures/     # 测试夹具
├── helpers/      # 测试辅助函数
└── legacy/       # 遗留测试（默认排除）

scripts/          # 辅助脚本（自动化工具）
├── dependency/   # 依赖管理（lock、verify、audit）
├── testing/      # 测试工具（performance、optimization）
├── security/     # 安全工具（漏洞扫描、审计）
├── welcome.sh    # 新开发者自动引导
└── check-test-usage.sh  # 测试命令检查
```

### 核心模块说明

- **api/**: FastAPI路由和端点定义
  - `data.py` - 数据API端点（17个测试）
  - `features.py` - 特征工程API（27个测试）
  - `predictions.py` - 预测API（27个测试）
  - `health.py` - 健康检查端点

- **config/**: 配置管理，包括环境变量和设置
  - 使用Pydantic进行配置验证
  - 支持多环境配置（dev/prod/ci）

- **database/**: SQLAlchemy模型、数据库连接和会话管理
  - 使用PostgreSQL（生产）和SQLite（测试）
  - 支持数据库迁移

- **utils/**: 通用工具函数（国际化、字典操作等）
  - `time_utils.py` - 时间处理工具
  - `crypto_utils.py` - 加密工具
  - `dict_utils.py` - 字典操作工具

- **middleware/**: FastAPI中间件（认证、CORS、日志等）
  - 认证中间件
  - CORS中间件
  - 请求日志中间件

### 🏃‍♂️ 5分钟架构理解

AI工具需要快速理解项目架构时：

1. **入口点**: `src/main.py` - FastAPI应用启动
2. **路由注册**: `src/api/` - 所有API端点
3. **数据层**: `src/database/models/` - SQLAlchemy模型
4. **业务逻辑**: `src/services/` - 核心业务服务
5. **配置中心**: `src/core/config.py` - 环境配置

**数据流向**:
```
Request → API路由 → 业务服务 → 数据库 → 响应
    ↓
   日志/监控
```

## 📚 重要文档

### 文档索引

- [文档首页](docs/INDEX.md) - 完整文档列表
- [AI开发规则](docs/AI_DEVELOPMENT_DOCUMENTATION_RULES.md) - 必读
- [测试指南](docs/testing/) - 测试策略
- [架构文档](docs/architecture/) - 系统设计
- [运维手册](docs/ops/) - 部署运维

### API和参考

- [API文档](docs/reference/API_REFERENCE.md)
- [数据库架构](docs/reference/DATABASE_SCHEMA.md)
- [开发指南](docs/reference/DEVELOPMENT_GUIDE.md)

## 🔧 开发工作流

### 新功能开发

1. `make context` - 了解项目状态
2. 更新相关文档（重要！）
3. 编写代码
4. `make test-quick` - 测试
5. `make fmt && make lint` - 代码规范
6. `make coverage-local` - 本地覆盖率检查
7. `make prepush` - 提交前检查（触发CI）

### 运行单个测试

⚠️ **重要警告**：不要对单个文件使用 `--cov=src`，这会显示误导性的0%覆盖率！

```bash
# ✅ 正确：运行特定测试文件（不含覆盖率）
pytest tests/unit/api/test_health.py -v

# ✅ 正确：运行特定测试函数
pytest tests/unit/api/test_health.py::test_health_endpoint -v

# ✅ 正确：运行带标记的测试
pytest -m "unit and not slow" --cov=src

# ❌ 错误：单个文件 + 覆盖率（会显示0%！）
# pytest tests/unit/api/test_health.py --cov=src  # 不要这样做！

# 调试模式运行测试
pytest tests/unit/api/test_health.py -v -s --tb=long

# 只运行上次失败的测试
pytest --lf

# 并行运行测试（需要pytest-xdist）
pytest tests/ -n auto

# 生成HTML覆盖率报告
make cov.html
# 查看报告：open htmlcov/index.html
```

### Bug修复

1. 查看Issue Tracker的Issue
2. 理解失败原因
3. 修复代码
4. 添加测试
5. 推送修复（CI自动运行）

## ⚠️ 重要注意事项

### 测试策略

- **主要使用单元测试**：`tests/unit/` 目录包含96.35%覆盖率的测试
- **测试标记系统**：
  - `unit` - 单元测试（主要）
  - `integration` - 集成测试（待重建）
  - `e2e` - 端到端测试
  - `slow` - 慢速测试
  - `legacy` - 遗留测试（默认排除）
- **覆盖率要求**：CI要求80%，本地开发20-60%即可

### 环境管理

#### 虚拟环境
- **目录**：`.venv/`（通过Makefile自动管理）
- **Python版本**：3.11+
- **激活方式**：`source .venv/bin/activate` 或使用Makefile命令自动激活

#### 服务依赖
```bash
# 核心服务（必须启动）
docker-compose up -d postgres redis  # 数据库和缓存

# 可选服务（按需启动）
docker-compose --profile mlflow up    # MLflow模型管理
docker-compose --profile celery up    # Celery任务队列
docker-compose up nginx               # Nginx反向代理（无profile）
```

#### 环境配置
- **开发环境**：`.env`（包含调试和开发设置）
- **生产环境**：`.env.production`（安全设置）
- **CI环境**：`.env.ci`（CI特定配置）
- **示例配置**：`.env.example`（模板文件）

#### 环境检查命令
```bash
make env-check      # 完整环境健康检查
make check-services # 检查Docker服务状态
make check-ports    # 检查端口占用情况
```

### 数据库操作

```bash
# 启动数据库服务
docker-compose up -d postgres redis

# 检查服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f

# 停止服务
docker-compose down

# 使用profiles启动额外服务
docker-compose --profile mlflow up   # 启动MLflow
docker-compose --profile celery up   # 启动Celery任务队列
```

### 依赖管理

采用**分层依赖管理**方案，确保环境隔离和生产稳定性：

#### 依赖层次结构

```
requirements/
├── base.in/.lock      # Python基础版本（3.11+）
├── core.txt           # 核心运行时依赖（FastAPI、SQLAlchemy等）
├── ml.txt             # 机器学习依赖（scikit-learn、pandas等）
├── api.txt            # API服务依赖（uvicorn、pydantic等）
├── dev.in/.lock       # 开发工具依赖（pytest、black、mypy等）
├── production.txt     # 生产环境（core + ml + api）
├── development.txt     # 开发环境（production + dev）
└── requirements.lock  # 完整锁定文件（所有依赖）
```

#### 核心命令

```bash
# 安装依赖（首次使用）
make install           # 从requirements.lock安装

# 锁定依赖版本（依赖变更后）
make lock-deps         # 生成所有.lock文件

# 验证依赖一致性
make verify-deps       # 检查当前环境与lock文件是否一致

# 重现性构建
make install-locked    # 强制从lock文件重新安装

# 依赖分析和审计
make audit-deps        # 扫描安全漏洞
make analyze-deps      # 分析依赖冲突
```

#### 环境管理原则

1. **开发环境**：包含所有依赖（dev + test + lint）
2. **生产环境**：只包含运行时依赖（core + ml + api）
3. **版本锁定**：所有依赖版本精确锁定
4. **安全审计**：定期扫描依赖漏洞

## 🔄 CI/CD系统

### 必须遵守的规则

```bash
# 提交前必须运行
make prepush
# 或
./ci-verify.sh
```

### Docker CI验证

- **推送前必须**：执行 `./ci-verify.sh` 验证CI兼容性
- **环境一致性**：与GitHub Actions CI环境完全一致
- **依赖验证**：确保 `requirements.lock` 在CI环境中正常工作
- **服务测试**：在PostgreSQL和Redis服务下运行完整测试

### CI失败处理

- Issue Tracker会自动创建Issue
- Issue包含详细错误信息
- 修复后自动关闭Issue

## 🆘 故障排除

### 快速诊断

```bash
# 环境问题
make env-check

# 查看所有命令
make help

# 测试失败
cat htmlcov/index.html  # 查看覆盖率报告

# CI问题
./ci-verify.sh  # 本地验证

# 检查mypy错误
make type-check  # 或 mypy src --ignore-missing-imports

# 查看Docker服务状态
docker-compose ps

# 检查端口占用
netstat -tulpn | grep :5432  # PostgreSQL
netstat -tulpn | grep :6379  # Redis
netstat -tulpn | grep :8000  # FastAPI应用
```

### 常见问题

- **测试失败**：查看 [故障排除指南](CLAUDE_TROUBLESHOOTING.md)
- **命令不工作**：运行 `make help`
- **环境问题**：运行 `make env-check`
- **依赖问题**：检查 `requirements.lock.txt` 或运行 `make verify-deps`
- **Docker问题**：确保 `docker-compose up -d`
- **覆盖率不足**：运行 `make cov.html` 查看详细报告
- **类型检查失败**：运行 `make type-check` 查看具体错误
- **代码格式问题**：运行 `make fmt` 自动修复
- **CI失败**：查看GitHub Actions日志，本地运行 `./ci-verify.sh`
- **端口冲突**：修改 `.env` 文件中的端口配置

## 🤖 AI工具使用技巧

### 🎯 高效工作流

1. **开始工作前**：
   ```bash
   make context      # 加载项目上下文
   make env-check    # 验证环境健康
   ```

2. **测试策略**：
   - 使用 `make test-phase1` 而不是单个文件测试
   - 运行单个测试时**不要**添加 `--cov=src`
   - 优先使用 `make test-quick` 进行快速验证

3. **代码生成前**：
   - 先查看现有代码模式
   - 使用相同的imports和结构
   - 遵循已有的命名规范

4. **依赖操作**：
   - 永远不要直接修改 `.lock` 文件
   - **推荐使用**：`python scripts/dependency/add_dependency.py <package>`
   - 手动操作：编辑 `.in` 文件后运行 `make lock-deps`
   - 使用 `make verify-deps` 验证一致性
   - **绝对不要**：直接运行 `pip install <package>`

   > 💡 **AI工具特别提醒**：引入新依赖后，运行 `make smart-deps` 获取智能指导

### ⚡ 常见模式识别

1. **测试文件模式**：
   ```python
   # 正确的导入模式
   from unittest.mock import Mock, patch
   import pytest
   from src.api.module import function_to_test

   class TestModuleName:
       @pytest.mark.unit
       def test_function_name(self, mock_fixture):
           # 测试逻辑
           pass
   ```

2. **API路由模式**：
   ```python
   # FastAPI路由标准模式
   from fastapi import APIRouter, Depends
   from src.core.logger import logger

   router = APIRouter(prefix="/api/v1", tags=["module"])

   @router.get("/endpoint")
   async def get_endpoint():
       logger.info("Getting endpoint")
       return {"status": "ok"}
   ```

3. **数据库操作模式**：
   ```python
   # SQLAlchemy标准模式
   from sqlalchemy.orm import Session
   from src.database.models import Model

   def get_items(db: Session):
       return db.query(Model).all()
   ```

### 🔍 快速诊断命令

```bash
# 检查为什么测试失败
pytest tests/unit/api/test_xxx.py -v -s --tb=long

# 查看哪些代码缺少测试
make cov.html && open htmlcov/index.html

# 检查类型错误
make type-check

# 验证所有环境配置
make env-check
```

### 📋 提交前清单

在推送代码前，AI工具应该：
1. ✅ 运行 `make test-quick` 验证测试
2. ✅ 运行 `make fmt` 格式化代码
3. ✅ 运行 `make lint` 检查质量
4. ✅ 运行 `make type-check` 类型检查
5. ✅ 运行 `make verify-deps` 验证依赖
6. ✅ 运行 `make prepush` 完整检查

### 💡 性能提示

- 使用 `pytest -x` 在第一个失败时停止
- 使用 `pytest --lf` 只运行上次失败的测试
- 使用 `pytest -k "keyword"` 过滤测试
- 避免在CI中运行慢速测试（使用 `-m "not slow"`）

## 📞 支持

- 快速参考：[CLAUDE_QUICK_REFERENCE.md](./CLAUDE_QUICK_REFERENCE.md)
- 故障排除：[CLAUDE_TROUBLESHOOTING.md](./CLAUDE_TROUBLESHOOTING.md)
- 完整文档：[docs/](docs/)

---

# 重要指令提醒

Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files unless explicitly requested.
