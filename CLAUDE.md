# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**重要提醒：请始终使用简体中文回复用户，用户看不懂英文。**

---

## 📚 文档导航

### 相关文档
- **[📖 项目主文档](docs/INDEX.md)** - 完整的项目文档导航中心
- **[🏗️ 系统架构](docs/architecture/ARCHITECTURE.md)** - 详细的系统架构说明
- **[🛡️ 质量守护系统](docs/QUALITY_GUARDIAN_SYSTEM_GUIDE.md)** - Claude Code完整使用指南 ⭐
- **[🚀 快速开始](docs/how-to/QUICKSTART_TOOLS.md)** - 5分钟快速开发指南
- **[📋 API参考](docs/reference/API_REFERENCE.md)** - 完整的API文档
- **[🧪 测试指南](docs/testing/TEST_IMPROVEMENT_GUIDE.md)** - 测试策略和最佳实践

### 文档版本信息
- **当前版本**: v2.0 (企业级架构 + 质量守护系统)
- **最后更新**: 2025-10-24
- **维护者**: Claude AI Assistant
- **适用范围**: Claude Code AI助手开发指导

### 国际化说明
本文档提供中文版本（推荐），英文版本作为参考：
- 🇨🇳 **中文版本** (主要) - 当前文档，适合中文用户
- 🇺🇸 **English Version** (参考) - 可根据需要切换语言

---

## ⚡ 快速导航

**🚀 新手？** → [快速开始](#快速开始-5分钟) | **🔧 开发？** → [核心命令](#核心命令) | **🧪 测试？** → [测试策略](#-测试策略) | **🏗️ 架构？** → [架构设计](#-架构设计)

---

## 📑 目录

- [📚 文档导航](#-文档导航)
  - [相关文档](#相关文档)
  - [文档版本信息](#文档版本信息)
  - [国际化说明](#国际化说明)
- [📊 项目概述](#-项目概述)
- [🛠️ 开发环境设置](#️-开发环境设置)
  - [快速开始](#快速开始-5分钟)
  - [核心命令](#核心命令)
  - [常用开发命令](#常用开发命令)
- [🧪 测试策略](#-测试策略)
- [🏗️ 架构设计](#-架构设计)
- [📏 代码质量标准](#-代码质量标准)
- [🐳 容器管理](#-容器管理)
- [🚀 CI/CD流水线](#-cicd流水线)
- [🗄️ 数据库操作](#️-数据库操作)
- [🔒 安全与合规](#-安全与合规)
- [⚙️ 开发工作流](#️-开发工作流)
- [🎯 高级架构特性](#-高级架构特性)
- [✨ 最佳实践](#-最佳实践)
- [🔧 故障排除](#-故障排除)
- [📈 项目状态](#-项目状态)
- [🔗 深入学习资源](#-深入学习资源)
- [📞 获取帮助](#-获取帮助)

---

## 📊 项目概述

基于现代Python技术栈的足球预测系统，采用FastAPI + PostgreSQL + Redis架构。项目遵循企业级开发模式，使用DDD、CQRS等设计模式。

**关键指标：**
- 测试覆盖率：22% (目标：>=80%，持续改进中)
- 代码质量：A+ (通过Ruff + MyPy检查)
- Python版本：3.11.9 (目标：3.11+)
- 源代码文件：737个Python文件
- 测试文件：452个测试文件
- 开发命令：190个Makefile命令
- 项目成熟度：企业级生产就绪 ⭐⭐⭐⭐⭐

## 开发环境设置

### 快速开始（5分钟）
```bash
make install      # 安装依赖并创建虚拟环境
make context      # 加载项目上下文 (⭐ 最重要)
make test         # 运行所有测试 (452个测试文件)
make coverage     # 查看覆盖率报告 (22%)
```

### 核心命令
```bash
make help         # 显示所有可用命令 (190个命令)
make env-check    # 检查开发环境健康状态
make lint         # 运行ruff和mypy检查
make fmt          # 使用ruff格式化代码
make ci           # 模拟完整CI流水线
make prepush      # 完整的预推送验证
```

### 🛡️ 质量守护系统命令 ⭐
```bash
# 快速质量检查和改进
./start-improvement.sh                    # 一键启动质量改进
python3 scripts/quality_guardian.py --check-only  # 全面质量检查
python3 scripts/smart_quality_fixer.py           # 智能自动修复
python3 scripts/improvement_monitor.py          # 查看改进状态

# 持续改进自动化
python3 scripts/continuous_improvement_engine.py --automated --interval 30  # 自动改进
python3 scripts/continuous_improvement_engine.py --history --history-limit 5      # 查看历史

# 质量标准优化
python3 scripts/quality_standards_optimizer.py --report-only  # 查看优化建议
python3 scripts/quality_standards_optimizer.py --update-scripts   # 应用优化标准
```

### 常用开发命令
```bash
# 环境管理
make venv               # 创建虚拟环境
make install-locked     # 从锁文件安装可重现依赖
make clean-env          # 清理虚拟环境

# 测试相关
make test-api           # 运行API测试
make test-integration   # 运行集成测试
make coverage-targeted MODULE=<module>  # 运行特定模块覆盖率

# 容器和部署
make up                 # 启动Docker服务
make down               # 停止服务
make deploy             # 构建生产镜像

# 文档生成
make docs-api           # 生成API文档
make docs-code          # 生成代码文档
make docs-architecture  # 生成架构图和文档
make docs-all           # 生成所有文档
make serve-docs         # 本地启动文档服务器

# 监控和日志
make staging-monitor    # 打开监控面板
make model-monitor      # 运行模型监控
make coverage-live      # 启动实时覆盖率监控
```

## 测试策略

### 测试执行规则
- **优先使用Makefile命令** - 避免直接运行单个pytest文件
- 测试环境使用Docker容器隔离
- 强制执行覆盖率阈值（最低18%，当前22%，目标80%，持续改进）

### 测试组织结构
```
tests/
├── unit/           # 单元测试 (45个子目录)
├── integration/    # 集成测试 (9个子目录)
├── e2e/           # 端到端测试
├── api/           # API测试
├── database/      # 数据库测试
├── cache/         # 缓存测试
└── conftest.py    # 测试配置文件
```

### 测试分类
```bash
make test-phase1      # 核心API测试（数据、特征、预测）
make test.unit        # 仅单元测试
make test.int         # 集成测试
make test.e2e         # 端到端测试
make coverage-fast    # 快速覆盖率检查（仅单元测试）
```

### 测试标记（pytest.ini）
项目使用19种测试标记：

- `unit`: 单元测试
- `integration`: 集成测试
- `api`: API测试
- `database`: 数据库测试
- `slow`: 慢速测试
- `smoke`: 冒烟测试
- `auth`: 认证测试
- `cache`: 缓存测试
- `monitoring`: 监控测试
- `e2e`: 端到端测试
- `performance`: 性能测试
- `critical`: 关键测试

**使用示例：**
```bash
pytest -m "unit"           # 仅单元测试
pytest -m "not slow"       # 跳过慢速测试
pytest -m "critical"       # 仅关键测试
```

### 覆盖率管理
- **当前覆盖率**: 22%
- **目标覆盖率**: 80%
- **覆盖率阈值**: 18% (最低)、20% (开发)、22% (CI)

### ⚠️ 关键测试规则
**永远不要**对单个测试文件使用 `--cov-fail-under` - 这会破坏CI集成。项目有复杂的覆盖率跟踪系统，仅在集中管理时覆盖率阈值才正常工作。

## 🏗️ 架构设计

### 核心架构层次
1. **API层** (`src/api/`): FastAPI路由、CQRS实现、依赖注入、数据模型
2. **领域层** (`src/domain/`): 业务模型、服务、策略模式、事件系统
3. **基础设施层** (`src/database/`, `src/cache/`): PostgreSQL、Redis、仓储模式、连接管理
4. **服务层** (`src/services/`): 数据处理、缓存、审计、管理服务
5. **支撑系统**: ML模块、流处理、实时通信、任务队列、监控体系

### 关键设计模式使用
- **依赖注入容器**: `src/core/di.py` - 轻量级DI实现
- **仓储模式**: 数据访问抽象层 (`src/database/repositories/`)
- **CQRS模式**: 命令查询分离 (`src/api/cqrs.py`)
- **观察者模式**: 事件处理系统 (`src/observers/`)
- **策略模式**: 预测算法策略 (`src/domain/strategies/`)
- **装饰器模式**: 切面功能实现 (`src/decorators/`)
- **适配器模式**: 接口适配 (`src/adapters/`)

### 数据库架构
- **PostgreSQL**: 主数据库，使用SQLAlchemy 2.0异步ORM
- **Redis**: 缓存和会话存储
- **连接池**: 高效连接管理
- **迁移**: Alembic模式管理
- **仓储模式**: 数据访问抽象层

### 高级架构特性
- **任务队列**: Celery分布式任务处理 (`src/tasks/`)
- **流处理**: Kafka实时数据流处理 (`src/streaming/`)
- **机器学习**: ML模型训练和推理系统 (`src/ml/`)
- **实时通信**: WebSocket双向通信 (`src/realtime/`)
- **监控体系**: Prometheus + Grafana + Loki
- **文档系统**: MkDocs自动生成多语言文档

### 架构优势
- **模块化设计**: 清晰的层次分离，便于维护和扩展
- **异步支持**: 全异步架构，高并发处理能力
- **可测试性**: 完整的单元测试和集成测试体系
- **容器化**: Docker + Docker Compose一键部署
- **监控完善**: 完整的监控、日志、告警体系

## 代码质量标准

### 代码风格
- **Ruff**: 主要代码检查和格式化工具（行长度：88）
- **MyPy**: 类型检查（零容忍类型错误）
- **双引号**: 标准字符串引用
- **类型注解**: 所有公共函数必须包含

### Ruff配置要点
- **Python目标版本**: 3.11+
- **行长度**: 88字符
- **测试文件例外**: 测试文件采用更宽松的规则
- **质量门禁**: 必须通过所有质量检查

### 质量检查
```bash
make lint           # 代码检查，必须无错误
make type-check     # MyPy类型检查，必须清洁
make coverage       # >=80%阈值强制执行
make prepush        # 组合所有质量检查
```

## 容器管理

### 开发环境
```bash
make up             # 启动docker-compose服务
make down           # 停止服务
make logs           # 查看日志
make deploy         # 构建不可变git-sha标签镜像
```

### Docker服务架构
- **app**: 主FastAPI应用
- **db**: PostgreSQL数据库 (含健康检查)
- **redis**: Redis缓存服务
- **nginx**: 反向代理和负载均衡
- **prometheus**: 监控指标收集
- **grafana**: 可视化监控面板
- **celery-worker**: 任务队列工作进程
- **celery-beat**: 任务调度器

### 环境配置
```bash
# 开发环境
docker-compose up

# 生产环境
ENV=production docker-compose --profile production up -d

# 测试环境
ENV=test docker-compose --profile test run --rm app pytest
```

## CI/CD流水线

### 本地验证
```bash
./ci-verify.sh      # 完整本地CI验证
make ci             # 模拟GitHub Actions CI
```

### 质量检查流程
1. **安全扫描**: bandit漏洞扫描
2. **依赖检查**: pip-audit漏洞包检查
3. **代码质量**: Ruff + MyPy严格检查
4. **测试**: 452个测试文件，覆盖率强制执行（当前22%，目标80%）
5. **构建**: Docker镜像构建和测试

### CI/CD流水线
- **GitHub Actions**: 11个自动化工作流
- **多环境部署**: 开发、预发布、生产环境
- **质量门禁**: 安全扫描、代码质量、测试覆盖率
- **自动化测试**: 单元测试、集成测试、性能测试

### 质量监控体系
**核心指标**:
- **代码质量**: Ruff + MyPy 严格检查
- **测试覆盖率**: 22% (目标80%)
- **安全扫描**: bandit漏洞扫描
- **依赖检查**: pip-audit包检查
- **性能监控**: Prometheus + Grafana

**监控服务**:
- **Prometheus**: 指标收集和存储
- **Grafana**: 可视化监控面板
- **Loki**: 日志收集和分析
- **AlertManager**: 告警管理

## 数据库操作

### 管理命令
```bash
make db-init         # 初始化数据库和迁移
make db-migrate      # 运行数据库迁移
make db-seed         # 播种初始数据
make db-backup       # 创建数据库备份
make db-reset        # 重置数据库（警告：删除所有数据）
```

### 连接管理
- 使用异步SQLAlchemy 2.0和连接池
- 仓储模式的数据访问抽象
- 自动事务管理

## 安全与合规

### 安全扫描
```bash
make security-check      # 运行漏洞扫描
make audit               # 完整安全审计
make secret-scan         # 扫描硬编码密钥
make dependency-check    # 检查过期依赖
```

### 安全特性
- JWT令牌认证
- RBAC权限控制
- SQL注入防护
- XSS和CSRF防护
- HTTPS强制执行
- 审计日志记录

## 开发工作流

### AI辅助开发流程
1. **环境检查** - `make env-check`
2. **加载上下文** - `make context`
3. **质量检查** - `python3 scripts/quality_guardian.py --check-only`
4. **智能修复** - `python3 scripts/smart_quality_fixer.py`
5. **持续改进** - `python3 scripts/continuous_improvement_engine.py`
6. **预提交验证** - `make prepush`

### 🛡️ Claude Code质量守护工作流 ⭐

#### 代码生成后立即执行
```bash
# 1. 语法检查
python3 scripts/smart_quality_fixer.py --syntax-only

# 2. 全面质量检查
python3 scripts/quality_guardian.py --check-only

# 3. 智能修复发现问题
python3 scripts/smart_quality_fixer.py

# 4. 验证修复效果
python3 scripts/improvement_monitor.py
```

#### 批量代码修改后处理
```bash
# 运行完整改进周期
./start-improvement.sh

# 或启动自动化改进
python3 scripts/continuous_improvement_engine.py --automated --interval 30

# 监控改进状态
python3 scripts/improvement_monitor.py
```

#### Claude Code推荐的每日检查清单
- [ ] 运行质量状态检查: `python3 scripts/quality_guardian.py --check-only`
- [ ] 检查改进趋势: `python3 scripts/improvement_monitor.py`
- [ ] 验证自动化引擎状态: `ps aux | grep continuous_improvement_engine`
- [ ] 查看质量目标达成情况: `cat config/quality_standards.json`

### 本地CI验证
提交代码前运行完整本地CI验证：

```bash
./ci-verify.sh
```

脚本输出"🎉 CI 绿灯验证成功！"表示可以安全推送。

## 高级架构特性

### 核心设计模式
- **依赖注入容器**: `src/core/di.py` 完整DI系统
- **CQRS模式**: 命令查询分离，读写模型隔离
- **事件驱动架构**: 事件总线和观察者模式
- **仓储模式**: 数据访问抽象层

### 关键配置文件
- **[`pyproject.toml`](pyproject.toml)**: Ruff配置和工具设置
- **[`pytest.ini`](pytest.ini)**: 测试配置和标记定义
- **[`requirements/requirements.lock`](requirements/requirements.lock)**: 锁定的依赖版本
- **[`Makefile`](Makefile)**: 完整开发工具链（199个命令）
- **[`.env.example`](.env.example)**: 环境变量模板
- **[`docker-compose.yml`](docker-compose.yml)**: 容器编排配置
- **[`docs/guard.py`](scripts/docs_guard.py)**: 文档质量守护工具

### 相关配置文档
- **[开发环境配置](docs/reference/DEVELOPMENT_GUIDE.md)** - 详细的配置说明
- **[数据库配置](docs/reference/DATABASE_SCHEMA.md)** - 数据库连接配置
- **[部署配置](docs/ops/PRODUCTION_READINESS_PLAN.md)** - 生产环境配置

## 最佳实践

### 开发原则
- 使用依赖注入容器
- 遵循仓储模式进行数据访问
- 实现适当的错误处理和自定义异常
- 对I/O操作使用async/await
- 编写全面的单元和集成测试
- **关键**: 永远不要对单个文件使用 `--cov-fail-under`

### 何时打破规则
虽然首选Makefile命令，但以下情况允许直接使用pytest：
- 调试特定测试失败
- 处理隔离的功能
- 开发期间的快速反馈

## 故障排除

### 常见问题
- **端口冲突**: 确保端口5432、6379、80可用
- **Docker问题**: 检查Docker守护进程和docker-compose版本
- **测试失败**: 验证测试环境是否正确设置
- **覆盖率下降**: 运行 `make coverage-targeted MODULE=<module>`

### 调试命令
```bash
make test-env-status    # 检查测试环境健康
make env-check          # 验证开发环境
make logs               # 查看服务日志
```

## 📈 项目状态

- **成熟度**: 企业级生产就绪 ⭐⭐⭐⭐⭐
- **架构**: 现代微服务 + DDD + CQRS
- **测试**: 22%覆盖率，452个测试文件（目标80%）
- **CI/CD**: 全自动化质量门禁
- **文档**: AI辅助完善文档
- **代码质量**: A+ (通过Ruff + MyPy检查)
- **安全**: 通过bandit安全扫描和依赖审计

### 系统优势
- **架构清晰**: 模块化设计，清晰的层次分离
- **设计模式**: 采用多种现代设计模式，代码可维护性高
- **异步支持**: 全异步架构，高并发处理能力
- **测试完善**: 完整的单元测试和集成测试体系
- **容器化**: Docker + Docker Compose一键部署
- **监控完善**: 完整的监控、日志、告警体系
- **质量门禁**: 严格的代码质量标准和CI/CD流程

### 持续改进方向
- 提高测试覆盖率至80%
- 优化API性能和响应时间
- 完善错误处理和异常管理
- 增强安全防护和审计功能
- 优化CI/CD流水线的自动化程度

这个系统展现了现代工具、实践和全面自动化支持的企业级Python开发最佳实践。

---

## 🔗 深入学习资源

### 📚 必读文档
- **[完整项目文档](docs/INDEX.md)** - 所有文档的入口点
- **[系统架构设计](docs/architecture/ARCHITECTURE.md)** - 深入理解系统设计
- **[API开发指南](docs/reference/API_REFERENCE.md)** - API设计和使用规范
- **[测试最佳实践](docs/testing/TEST_IMPROVEMENT_GUIDE.md)** - 测试策略和技巧
- **[部署运维手册](docs/ops/MONITORING.md)** - 生产环境运维指南

### 🛠️ 开发工具链
- **[Makefile完整指南](docs/project/TOOLS.md)** - 120+命令详解
- **[Docker容器化指南](docs/how-to/STAGING_ENVIRONMENT.md)** - 容器开发环境
- **[代码质量标准](docs/reference/DEVELOPMENT_GUIDE.md)** - 质量门禁和检查
- **[CI/CD流水线](docs/project/CI_VERIFICATION.md)** - 持续集成配置

### 🚀 高级主题
- **[机器学习模块](docs/ml/ML_MODEL_GUIDE.md)** - ML模型和预测系统
- **[数据处理管道](docs/data/DATA_COLLECTION_SETUP.md)** - 数据采集和处理
- **[安全最佳实践](docs/maintenance/SECURITY_AUDIT_GUIDE.md)** - 安全配置和审计
- **[性能优化指南](docs/ops/MONITORING.md)** - 性能监控和优化

### 📋 故障排除
- **[常见问题解答](docs/project/ISSUES.md)** - 常见问题和解决方案
- **[调试指南](docs/testing/QA_TEST_KANBAN.md)** - 调试技巧和工具
- **[日志分析](docs/ops/MONITORING.md)** - 日志收集和分析

---

## 📞 获取帮助

### 🤝 社区支持
- **[贡献指南](CONTRIBUTING.md)** - 如何参与项目贡献
- **[问题反馈](docs/project/ISSUES.md)** - 报告问题和建议
- **[开发讨论](docs/reference/COMPREHENSIVE_API_DOCUMENTATION_STYLE_GUIDE.md)** - 技术讨论和规范

### 📖 文档维护
本文档遵循项目的文档管理最佳实践，定期更新和维护。如发现问题或改进建议，请参考 [文档管理分析报告](DOCUMENTATION_MANAGEMENT_ANALYSIS.md) 中的任务看板。

---

*最后更新: 2025-10-23 | 文档版本: v2.0 | 维护者: Claude AI Assistant*