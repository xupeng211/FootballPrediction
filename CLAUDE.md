# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📋 目录

1. [快速上手](#快速上手)
2. [核心架构](#核心架构)
3. [开发命令](#开发命令)
4. [测试策略](#测试策略)
5. [技术栈](#技术栈)
6. [重要提醒](#重要提醒)

## 语言偏好

**请使用简体中文回复用户** - 项目团队主要使用中文交流，除非特别要求，请使用简体中文回复。

## 项目质量基线

- **构建状态**: 稳定 (已建立绿色基线)
- **测试覆盖率**: 29.0% 基线 (持续改进中)
- **测试数量**: 385 个测试通过
- **安全性**: Bandit 验证，依赖漏洞已修复
- **代码质量**: A+ 等级 (ruff, mypy 检查)
- **Python版本**: 支持 3.10/3.11/3.12 (推荐 3.11)

## 快速上手

### 5分钟快速启动
```bash
make dev && make status && make test.unit && make coverage
```

### 项目启动验证
```bash
# 1. 启动环境
make dev

# 2. 检查服务状态
make status

# 3. 验证API可访问性
curl http://localhost:8000/health

# 4. 运行核心测试
make test.fast

# 5. 查看项目状态
make logs
```

### 常用命令速查
| 任务 | 命令 | 说明 |
|------|------|------|
| 环境管理 | `make dev` / `make dev-stop` | 启动/停止开发环境 |
| 测试 | `make test.unit` / `make test.fast` / `make coverage` | 单元测试/快速核心测试/覆盖率 |
| CI验证 | `make test.unit.ci` / `make ci` | CI最小化验证/完整CI验证 |
| 代码质量 | `make lint && make fix-code` | 检查并自动修复 |
| 容器操作 | `make shell` / `make logs` / `make status` | 进入容器/查看日志/服务状态 |
| 数据库 | `make db-shell` / `make db-reset` / `make db-migrate` | 数据库操作/重置/迁移 |
| Redis | `make redis-shell` | 连接Redis缓存 |
| 监控 | `make logs-db` / `make logs-redis` | 查看数据库/Redis日志 |
| 维护命令 | `make rebuild` / `make clean` | 重新构建/清理资源 |

## 项目概述

这是一个基于 Python FastAPI 构建的企业级足球预测系统，采用领域驱动设计（DDD）、CQRS 和事件驱动架构模式。系统全面使用现代 async/await 模式，具备机器学习比赛预测能力。

**项目规模**:
- **大型 Python 项目** - 企业级应用架构
- **完整测试体系** - 四层测试架构 (单元: 85%, 集成: 12%, 端到端: 2%, 性能: 1%)
- **自动化工作流** - 完整的 Makefile 开发命令
- **API 接口** - 40+ 端点，支持 v1 和 v2 版本
- **任务调度** - 7 个专用队列的 Celery 分布式任务调度

## 核心架构

### 架构模式
- **DDD (领域驱动设计)** - 清晰的领域边界和业务逻辑分离
- **CQRS (命令查询分离)** - 读写操作独立优化
- **事件驱动架构** - 组件间松耦合通信
- **异步优先** - 所有 I/O 操作使用 async/await

### 目录结构
```
src/
├── api/              # API 层 (CQRS 实现)
├── domain/           # 领域层 (DDD 核心逻辑)
├── adapters/         # 外部数据源适配器
├── cqrs/            # CQRS 模式实现
├── core/            # 核心基础设施
├── database/        # 数据层
├── cache/           # 缓存层
├── ml/              # 机器学习模块
├── tasks/           # Celery 任务调度
├── events/          # 事件系统
├── services/        # 业务服务层
├── utils/           # 工具函数
└── monitoring/      # 监控系统
```

### 关键架构组件

#### 1. 数据库层 (`src/database/`)
- **异步 SQLAlchemy 2.0** - 现代异步ORM
- **连接池管理** - 智能连接池和健康检查
- **迁移管理** - Alembic 数据库版本控制
- **多租户支持** - 租户隔离和数据管理

#### 2. 领域层 (`src/domain/`)
- **实体模型** - Match, Team, League, Prediction 等核心业务实体
- **领域服务** - 业务逻辑和规则引擎
- **事件系统** - 领域事件和事件处理器
- **策略模式** - 多种预测策略的统一接口

#### 3. 应用层 (`src/api/`)
- **RESTful API** - FastAPI 构建，支持 OpenAPI 3.0
- **版本控制** - v1 和 v2 API 版本管理
- **中间件系统** - 认证、缓存、性能监控
- **WebSocket** - 实时数据推送

#### 4. 机器学习层 (`src/ml/`)
- **XGBoost 模型** - 梯度提升预测算法
- **LSTM 深度学习** - 时间序列预测
- **特征工程** - 自动化特征提取和转换
- **模型管理** - MLflow 实验跟踪和版本控制

#### 5. 任务调度 (`src/tasks/`)
- **Celery 分布式任务** - 7个专用队列 (fixtures, odds, scores, maintenance等)
- **定时任务** - Celery Beat 调度器
- **数据收集** - 多源数据自动采集和处理
- **智能重试** - 指数退避和错误阈值管理

#### 6. 适配器系统 (`src/adapters/`)
- **外部数据源适配** - 统一的第三方API接口适配层
- **适配器工厂模式** - 动态创建和管理数据源适配器
- **注册机制** - 可插拔的适配器注册和发现系统

## 开发命令

### 环境管理
```bash
# 开发环境
make dev              # 启动开发环境
make dev-stop         # 停止开发环境
make status           # 检查服务状态

# 生产环境
make prod             # 启动生产环境

# 维护命令
make clean            # 清理资源
make rebuild          # 重新构建
```

### 代码质量与测试
```bash
# 🏆 测试黄金法则：始终使用 Makefile 命令，不要直接运行 pytest
make test.unit        # 单元测试
make test.fast        # 快速核心测试 (仅API/Utils/Cache/Events模块)
make test.unit.ci     # CI最小化验证 (极致稳定方案)
make test.integration # 集成测试
make test.all         # 所有测试
make coverage         # 覆盖率报告

# 代码质量
make lint             # 代码检查
make fix-code         # 自动修复
make security-check   # 安全扫描
make ci               # 完整 CI 验证
```

### 容器操作
```bash
# 容器访问
make shell            # 进入应用容器
make db-shell         # 连接数据库
make redis-shell      # 连接 Redis

# 日志和监控
make logs             # 应用日志
make monitor          # 容器资源监控
```

### 数据库管理
```bash
make db-reset         # 重置数据库 (⚠️ 会删除数据)
make db-migrate       # 运行迁移
```

### Celery 任务管理
```bash
# 基础服务
celery -A src.tasks.celery_app worker --loglevel=info    # 启动 Worker
celery -A src.tasks.celery_app beat --loglevel=info      # 启动调度器
celery -A src.tasks.celery_app flower                    # 启动 Flower UI

# 任务监控
docker-compose exec app celery -A src.tasks.celery_app inspect active    # 活动任务
docker-compose exec app celery -A src.tasks.celery_app inspect stats     # 任务统计
docker-compose exec app celery -A src.tasks.celery_app purge             # 清空队列
```

## 测试策略

### 四层测试架构
- **单元测试 (85%)** - 快速隔离组件测试
- **集成测试 (12%)** - 数据库、缓存、外部API集成
- **端到端测试 (2%)** - 完整用户流程测试
- **性能测试 (1%)** - 负载和压力测试

### 关键测试原则 🏆
1. **环境一致性原则** - Always use Makefile commands
2. **测试隔离原则** - 每个测试独立运行
3. **异步测试原则** - 正确的异步测试模式
4. **外部API原则** - 单元测试Mock，集成测试使用真实API

### ⚠️ 重要：如何运行单个测试文件
**永远不要直接运行 `pytest tests/unit/specific_file.py`**，这会导致环境和依赖问题。

正确的方法：
```bash
# 使用容器环境运行单个测试文件
docker-compose exec app pytest tests/unit/api/test_predictions.py -v

# 或者使用Makefile命令进入容器后运行
make shell
pytest tests/unit/api/test_predictions.py -v
```

### 测试标记
```python
@pytest.mark.unit           # 单元测试
@pytest.mark.integration    # 集成测试
@pytest.mark.api           # API测试
@pytest.mark.database      # 数据库测试
@pytest.mark.ml            # 机器学习测试
@pytest.mark.security      # 安全测试
```

### 测试环境配置
- **技术债务管理** - 自动跳过已知不稳定的测试模块
- **Mock数据库** - 测试环境使用内存SQLite和Mock对象
- **并行测试** - 支持pytest-xdist并行执行
- **超时保护** - 300秒测试超时限制

## 技术栈

### 后端核心
- **FastAPI** (v0.104.0+) - 现代异步Web框架
- **PostgreSQL 15** - 主数据库，异步SQLAlchemy 2.0+
- **Redis 7.0+** - 缓存和Celery消息队列
- **Pydantic v2+** - 数据验证和序列化
- **httpx/aiohttp** - 异步HTTP客户端

### 机器学习
- **XGBoost 2.0+** - 梯度提升框架
- **scikit-learn 1.3+** - 传统机器学习
- **TensorFlow 2.18.0** - 深度学习 (LSTM)
- **MLflow 2.22.2+** - 实验跟踪和模型管理 (版本<3.0.0)
- **Optuna 4.6.0+** - 超参数优化

### 开发工具
- **pytest 8.4.0+** - 测试框架，支持异步
- **Ruff 0.14+** - 代码检查和格式化 (A+等级)
- **Bandit 1.8.6+** - 安全扫描
- **MyPy 1.18+** - 类型检查 (为CI稳定性暂时禁用)
- **Docker 27.0+** - 容器化部署
- **Pre-commit 4.0.1+** - Git钩子管理
- **pip-audit 2.6.0+** - 依赖安全审计

### 前端技术
- **React 19.2.0** + **TypeScript 4.9.5**
- **Ant Design 5.27+** - UI组件库
- **Vite 6.0.1** - 构建工具
- **Redux Toolkit** - 状态管理

### 容器架构
- **app**: FastAPI应用 (8000端口) - 支持热重载
- **db**: PostgreSQL 15 (5432端口) - 带健康检查
- **redis**: Redis 7.0 (6379端口) - 缓存和消息队列
- **frontend**: React应用 (3000端口) - 前端服务
- **nginx**: 反向代理 (80端口) - 统一入口
- **worker**: Celery异步任务处理器 - 8个专用队列
- **beat**: Celery定时任务调度器

### 数据库与缓存
- **数据库**: PostgreSQL 15 + 异步SQLAlchemy 2.0
- **连接池**: 异步连接池 + 健康检查
- **缓存**: Redis 7.0多级缓存 + 智能失效
- **迁移**: Alembic数据库架构管理

## 重要提醒

### 🔥 核心开发原则

1. **测试黄金法则** - 始终使用 `make test.unit` 等Makefile命令，永远不要直接运行pytest单个文件
2. **异步优先** - 所有I/O操作必须使用async/await模式
3. **类型安全** - 所有函数必须有完整类型注解
4. **架构完整性** - 严格遵循DDD+CQRS+事件驱动架构

### 🚨 关键注意事项

- **环境一致性**: 使用Docker Compose确保本地与CI环境一致
- **CI验证**: 提交前运行 `make lint && make test && make security-check`
- **服务健康**: 开发前先运行 `make status` 检查所有服务
- **数据安全**: `make db-reset` 会删除所有数据，谨慎使用
- **语言偏好**: **请使用简体中文回复用户** - 项目团队主要使用中文交流

### 🛠️ 开发工作流

```bash
# 每日开发流程
make dev              # 启动开发环境
make status           # 确认所有服务健康
make test.unit        # 运行单元测试
make coverage         # 检查覆盖率
make lint && make fix-code  # 代码质量检查和修复

# 提交前验证（必须执行）
make test.unit.ci     # 最小化CI验证（最快）
make ci               # 完整CI验证（如时间允许）
make security-check   # 安全检查
make type-check       # 类型检查
```

### 📋 GitHub 工作流集成
- **CI 管道**: `.github/workflows/ci_pipeline_v2.yml` - 主要的持续集成管道
- **智能修复**: `.github/workflows/smart-fixer-ci.yml` - 自动修复常见问题
- **问题同步**: 自动化的 GitHub Issues 与项目看板同步
- **覆盖率监控**: 实时测试覆盖率跟踪和报告

### 🔧 故障排除

| 问题 | 解决方案 |
|------|---------|
| 测试失败 | `make test` 查看详细错误信息 |
| CI验证失败 | 运行 `make test.unit.ci` 进行最小化验证，检查核心功能 |
| 内存不足 | 使用 `make test.fast` 运行快速核心测试，避免ML模型加载 |
| 类型错误 | 检查导入，添加缺失类型注解 |
| 数据库问题 | 验证连接字符串，检查PostgreSQL状态，运行 `make db-migrate` |
| Redis问题 | 检查Redis服务状态和连接 |
| 端口冲突 | 检查8000、3000、5432、6379端口是否可用 |
| 性能问题 | 使用 `make monitor` 监控容器资源消耗 |
| 依赖问题 | 运行 `make rebuild` 重新构建镜像 |
| CI超时 | 使用 `make test.unit.ci` 替代完整测试套件 |

### 📊 API 访问地址

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **WebSocket**: ws://localhost:8000/api/v1/realtime/ws

---

**💡 记住**: 这是一个AI优先维护的项目。优先考虑架构完整性、代码质量和全面测试。所有I/O操作必须是异步的，保持DDD层分离，并遵循既定模式。

---

## 特色功能

### 智能冷启动系统
- **数据库状态检测** - 自动检测数据表记录数量和时间戳
- **自适应收集策略** - 空数据库→完整收集，陈旧数据→增量更新
- **故障恢复机制** - 智能降级和重试机制

### 机器学习管道 (`src/ml/`)
- **预测引擎** - XGBoost 2.0+ + LSTM深度学习支持
- **特征工程** - 自动化特征提取和转换
- **模型管理** - MLflow实验跟踪和版本控制
- **超参数优化** - Optuna贝叶斯优化

### 任务调度系统 (`src/tasks/`)
- **7个专用队列** - fixtures, odds, scores, maintenance等
- **智能调度** - Celery Beat定时任务 + 间隔任务
- **高级重试** - 指数退避、抖动和错误阈值