# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🌟 快速开始（5分钟上手）

```bash
# 启动完整开发环境
make dev && make status

# 验证API可访问性
curl http://localhost:8000/health

# 运行核心测试验证环境
make test.fast

# 生成覆盖率报告
make coverage
```

## 语言偏好

**请使用简体中文回复用户** - 项目团队主要使用中文交流，除非特别要求，请使用简体中文回复。

## 项目质量基线

- **构建状态**: 稳定 (已建立绿色基线)
- **测试覆盖率**: 29.0% 基线 (持续改进中)
- **测试数量**: 385 个测试通过
- **代码质量**: A+ 等级 (ruff 检查)
- **Python版本**: 3.10/3.11/3.12 (推荐 3.11)

## 🏗️ 核心架构

### 架构模式
- **DDD (领域驱动设计)** - 清晰的领域边界和业务逻辑分离
- **CQRS (命令查询分离)** - 读写操作独立优化
- **事件驱动架构** - 组件间松耦合通信
- **异步优先** - 所有 I/O 操作使用 async/await

### 目录结构
```
src/
├── api/              # API 层 (83个文件) - CQRS 实现
├── domain/           # 领域层 (37个文件) - DDD 核心逻辑
├── database/         # 数据层 - 异步SQLAlchemy 2.0
├── ml/               # 机器学习模块 - XGBoost + LSTM
├── tasks/            # Celery 任务调度 - 7个专用队列
├── adapters/         # 外部数据源适配器
├── cqrs/            # CQRS 模式实现
├── cache/           # 缓存层
├── events/          # 事件系统
├── services/        # 业务服务层
├── utils/           # 工具函数
└── monitoring/      # 监控系统
```

### 关键技术栈

#### 后端核心
- **FastAPI** (v0.104.0+) - 现代异步Web框架
- **PostgreSQL 15** - 主数据库，异步SQLAlchemy 2.0+
- **Redis 7.0+** - 缓存和Celery消息队列
- **Pydantic v2+** - 数据验证和序列化

#### 机器学习
- **XGBoost 2.0+** - 梯度提升预测算法
- **TensorFlow 2.18.0** - 深度学习 (LSTM)
- **MLflow 2.22.2+** - 实验跟踪和模型管理
- **Optuna 4.6.0+** - 超参数优化

#### 开发工具
- **pytest 8.4.0+** - 测试框架，支持异步
- **Ruff 0.14+** - 代码检查和格式化 (A+等级)
- **Bandit 1.8.6+** - 安全扫描
- **Docker 27.0+** - 容器化部署

## 🚀 核心开发命令

### 环境管理
```bash
make dev              # 启动开发环境 (app + db + redis + nginx)
make dev-stop         # 停止开发环境
make status           # 检查所有服务状态
make rebuild          # 重新构建镜像
```

### 🔥 测试黄金法则
**永远不要直接运行 pytest 单个文件！** 始终使用 Makefile 命令：

```bash
make test.unit        # 单元测试 (278个测试文件)
make test.fast        # 快速核心测试 (仅API/Utils/Cache/Events)
make test.unit.ci     # CI最小化验证 (极致稳定方案)
make test.integration # 集成测试
make coverage         # 生成覆盖率报告
```

### ⚠️ 重要：单个测试文件运行方法
```bash
# 正确方法：使用容器环境
docker-compose exec app pytest tests/unit/api/test_predictions.py -v

# 或者进入容器后运行
make shell
pytest tests/unit/api/test_predictions.py -v
```

### 代码质量
```bash
make lint             # 代码检查
make fix-code         # 自动修复代码问题
make format           # 代码格式化
make security-check   # 安全扫描
make ci               # 完整CI验证
```

### 容器操作
```bash
make shell            # 进入后端容器
make db-shell         # 连接PostgreSQL数据库
make redis-shell      # 连接Redis
make logs             # 查看应用日志
make logs-db          # 查看数据库日志
```

### 数据库管理
```bash
make db-reset         # 重置数据库 (⚠️ 会删除所有数据)
make db-migrate       # 运行数据库迁移
```

## 🧪 测试策略

### 四层测试架构
- **单元测试 (85%)** - 快速隔离组件测试
- **集成测试 (12%)** - 数据库、缓存、外部API集成
- **端到端测试 (2%)** - 完整用户流程测试
- **性能测试 (1%)** - 负载和压力测试

### 关键测试原则
1. **环境一致性原则** - Always use Makefile commands
2. **测试隔离原则** - 每个测试独立运行
3. **异步测试原则** - 正确的异步测试模式
4. **外部API原则** - 单元测试Mock，集成测试使用真实API

### 测试标记示例
```python
@pytest.mark.unit           # 单元测试
@pytest.mark.integration    # 集成测试
@pytest.mark.api           # API测试
@pytest.mark.database      # 数据库测试
@pytest.mark.ml            # 机器学习测试
```

## 🔧 核心开发工作流

### 每日开发流程
```bash
# 1. 启动环境
make dev && make status

# 2. 运行测试确保环境正常
make test.fast

# 3. 开发过程中
make lint && make fix-code  # 代码质量检查和修复

# 4. 提交前验证（必须执行）
make test.unit.ci     # 最小化CI验证（最快）
make security-check   # 安全检查
```

### 提交前完整验证
```bash
make ci               # 完整CI验证（如时间允许）
```

## 🛠️ 架构指导原则

### 1. 异步编程
- **所有I/O操作必须使用 async/await**
- 数据库操作使用异步SQLAlchemy 2.0
- HTTP请求使用 httpx/aiohttp
- 避免阻塞操作

### 2. DDD分层
- **domain/** - 纯业务逻辑，不依赖外部框架
- **api/** - CQRS命令查询分离
- **database/** - 数据访问抽象
- **services/** - 应用服务编排

### 3. 类型安全
- 所有函数必须有完整类型注解
- 使用Pydantic进行数据验证
- MyPy类型检查（为CI稳定性暂时禁用）

### 4. 事件驱动
- 领域事件使用发布订阅模式
- 松耦合的组件通信
- 异步事件处理

## 🚨 故障排除快速参考

| 问题类型 | 解决方案 |
|---------|---------|
| **测试失败** | `make test.fast` 查看核心功能，避免ML模型加载 |
| **CI超时** | 使用 `make test.unit.ci` 替代完整测试套件 |
| **端口冲突** | 检查 8000、3000、5432、6379 端口可用性 |
| **数据库问题** | 运行 `make db-migrate`，检查PostgreSQL状态 |
| **Redis连接问题** | `make redis-shell` 测试连接 |
| **内存不足** | 使用 `make test.fast` 避免ML相关测试 |
| **类型错误** | 检查导入，添加缺失类型注解 |
| **依赖问题** | 运行 `make rebuild` 重新构建镜像 |

## 🤖 机器学习开发

### ML Pipeline结构
```python
# 特征工程
src/ml/enhanced_feature_engineering.py

# 模型训练
src/ml/enhanced_xgboost_trainer.py

# 预测管道
src/ml/football_prediction_pipeline.py

# 实验跟踪
src/ml/experiment_tracking.py
```

### 模型管理
- **MLflow** - 实验跟踪和版本控制
- **Optuna** - 超参数贝叶斯优化
- **模型注册** - 生产模型管理

## 📊 API访问地址

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **WebSocket**: ws://localhost:8000/api/v1/realtime/ws

## 🐳 容器架构

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Frontend  │  │  Backend    │  │  Database   │
│   (React)   │  │  (FastAPI)  │  │(PostgreSQL) │
│  Port:3000  │  │  Port:8000  │  │  Port:5432  │
└─────────────┘  └─────────────┘  └─────────────┘
       │                │                │
       │       ┌─────────────┐          │
       │       │    Redis    │          │
       │       │  Port:6379  │          │
       │       └─────────────┘          │
       │                │                │
       └────────────────┼────────────────┘
                        │
              ┌─────────────┐
              │   Worker    │
              │  (Celery)   │
              └─────────────┘
```

## 💡 重要提醒

1. **测试黄金法则** - 始终使用 Makefile 命令，永远不要直接运行pytest
2. **异步优先** - 所有I/O操作必须使用async/await模式
3. **架构完整性** - 严格遵循DDD+CQRS+事件驱动架构
4. **环境一致性** - 使用Docker确保本地与CI环境一致
5. **服务健康** - 开发前先运行 `make status` 检查所有服务

---

**💡 记住**: 这是一个AI优先维护的项目。优先考虑架构完整性、代码质量和全面测试。所有I/O操作必须是异步的，保持DDD层分离，并遵循既定模式。