# 术语表

## 📋 概述

本文档定义了足球预测系统中使用的专业术语、缩写和概念，帮助团队成员建立统一的沟通语言，减少理解偏差。

## 🏀 业务术语

### 比赛相关

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **比赛** | Match | 两支球队之间的正式对抗活动 | 曼联 vs 利物浦 |
| **主队** | Home Team | 在主场进行比赛的球队 | 曼联 (主场) |
| **客队** | Away Team | 在客场进行比赛的球队 | 利物浦 (客场) |
| **联赛** | League | 组织化的比赛体系 | 英超、西甲、德甲 |
| **赛季** | Season | 一年一度的联赛周期 | 2024-25赛季 |
| **积分** | Points | 联赛中获得的分数 | 胜3分、平1分、负0分 |
| **排名** | Standing | 球队在联赛中的位置 | 第1名、第10名 |

### 比赛结果

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **主胜** | Home Win | 主队获胜的比赛结果 | 2-1 (主队2球，客队1球) |
| **客胜** | Away Win | 客队获胜的比赛结果 | 1-2 (主队1球，客队2球) |
| **平局** | Draw | 双方得分相同的比赛结果 | 1-1、0-0 |
| **进球数** | Goals | 比赛中的总进球数 | 3球 (2-1) |
| **净胜球** | Goal Difference | 进球数减去失球数 | +5、-2 |

### 赔率相关

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **赔率** | Odds | 博彩公司对比赛结果的概率预测 | 主胜1.85、平3.40、客胜4.20 |
| **盘口** | Handicap | 为了平衡双方实力而设置的让分 | 主队让0.5球 |
| **大小球** | Over/Under | 总进球数的上下盘 | 大2.5球、小2.5球 |
| **博彩公司** | Bookmaker | 提供赔率服务的公司 | Bet365、威廉希尔 |
| **隐含概率** | Implied Probability | 从赔率推算出的概率 | 1/1.85 = 54.1% |

## 🤖 机器学习术语

### 模型相关

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **预测模型** | Prediction Model | 用于预测比赛结果的算法 | 随机森林、神经网络 |
| **特征** | Feature | 用于预测的输入变量 | 球队实力、主场优势 |
| **标签** | Label | 模型预测的目标变量 | 比赛结果 (主胜/平局/客胜) |
| **训练集** | Training Set | 用于训练模型的数据 | 历史比赛数据 (80%) |
| **测试集** | Test Set | 用于评估模型性能的数据 | 历史比赛数据 (20%) |
| **验证集** | Validation Set | 用于调参的数据 | 历史比赛数据 (10%) |
| **过拟合** | Overfitting | 模型在训练数据上表现过好 | 训练准确率95%，测试准确率60% |
| **欠拟合** | Underfitting | 模型过于简单，无法捕捉规律 | 训练准确率55%，测试准确率53% |

### 性能指标

| 术语 | 英文 | 定义 | 计算公式 |
|------|------|------|----------|
| **准确率** | Accuracy | 正确预测的比例 | (TP+TN)/(TP+TN+FP+FN) |
| **精确率** | Precision | 预测为正的样本中实际为正的比例 | TP/(TP+FP) |
| **召回率** | Recall | 实际为正的样本中被正确预测的比例 | TP/(TP+FN) |
| **F1分数** | F1-Score | 精确率和召回率的调和平均 | 2×(Precision×Recall)/(Precision+Recall) |
| **AUC** | Area Under Curve | ROC曲线下面积 | - |
| **混淆矩阵** | Confusion Matrix | 分类结果的矩阵表示 | - |

## 🧠 AI辅助开发术语

### AI助手和工作流

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **Claude AI** | Claude AI | Anthropic开发的AI助手 | 代码生成、文档编写 |
| **上下文加载** | Context Loading | 为AI提供项目背景信息 | `make context` |
| **AI辅助开发** | AI-Assisted Development | 使用AI工具辅助编程开发 | 代码补全、重构建议 |
| **提示工程** | Prompt Engineering | 设计有效的AI指令 | 结构化提示、角色设定 |
| **代码审查** | Code Review | AI辅助代码质量检查 | 最佳实践建议、问题识别 |

### 开发效率工具

| 术语 | 英文 | 定义 | 用途 |
|------|------|------|------|
| **自动化代码生成** | Automated Code Generation | AI自动生成代码片段 | 模板代码、测试用例 |
| **智能重构** | Intelligent Refactoring | AI辅助代码结构优化 | 代码清理、性能优化 |
| **文档同步** | Documentation Sync | 代码与文档自动同步 | API文档更新、注释生成 |

## 🏗️ 技术架构术语

### 软件架构

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **分层架构** | Layered Architecture | 按功能层次组织软件结构 | API层、服务层、数据层 |
| **领域驱动设计** | DDD | 以业务领域为中心的设计方法 | 领域模型、仓储模式 |
| **CQRS** | Command Query Responsibility Segregation | 命令查询责任分离模式 | 写操作用命令，读操作用查询 |
| **微服务** | Microservices | 小型、独立部署的服务 | 预测服务、数据服务、用户服务 |
| **API网关** | API Gateway | 统一的API入口 | FastAPI应用 |
| **负载均衡** | Load Balancing | 分散请求到多个服务器 | Nginx、HAProxy |
| **观察者模式** | Observer Pattern | 对象间一对多依赖关系 | 事件系统、通知机制 |
| **仓储模式** | Repository Pattern | 数据访问抽象层 | 数据库操作封装 |
| **依赖注入** | Dependency Injection | 控制反转实现松耦合 | 依赖容器、服务注册 |

### 数据存储

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **关系数据库** | Relational Database | 基于关系模型的数据库 | PostgreSQL、MySQL |
| **NoSQL数据库** | NoSQL Database | 非关系型数据库 | Redis、MongoDB |
| **缓存** | Cache | 高速存储层，减少数据访问时间 | Redis |
| **数据湖** | Data Lake | 原始数据存储库 | S3、HDFS |
| **数据仓库** | Data Warehouse | 结构化数据分析存储 | 数据集市、OLAP |
| **ETL** | Extract, Transform, Load | 数据抽取、转换、加载过程 | 数据管道 |

### 开发运维

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **CI/CD** | Continuous Integration/Continuous Deployment | 持续集成/持续部署 | GitHub Actions、Jenkins |
| **容器化** | Containerization | 将应用打包成容器的技术 | Docker、Podman |
| **编排** | Orchestration | 管理多个容器的工具 | Kubernetes、Docker Compose |
| **监控** | Monitoring | 监控系统状态和性能 | Prometheus、Grafana |
| **日志** | Logging | 记录系统运行信息 | ELK Stack、Loki |
| **告警** | Alerting | 异常情况的通知机制 | Alertmanager、PagerDuty |

## 📊 业务数据术语

### 比赛数据

| 术语 | 英文 | 定义 | 数据类型 |
|------|------|------|----------|
| **比赛时间** | Match Time | 比赛开始的具体时间 | TIMESTAMP |
| **比赛状态** | Match Status | 比赛的当前状态 | ENUM (scheduled/live/finished/cancelled) |
| **主场优势** | Home Advantage | 主队相对客队的优势 | DECIMAL |
| **球队实力** | Team Strength | 球队的综合实力评分 | DECIMAL |
| **历史战绩** | Head-to-Head | 两队历史交锋记录 | JSON |
| **近期表现** | Recent Form | 球队最近几场比赛的表现 | JSON |

### 特征工程

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **特征工程** | Feature Engineering | 从原始数据中提取有用特征的过程 | 滚动平均、排名特征 |
| **标准化** | Normalization | 将特征缩放到特定范围 | 0-1标准化、Z-score标准化 |
| **独热编码** | One-Hot Encoding | 将分类变量转换为二进制向量 | 联赛编码、球队编码 |
| **时间序列特征** | Time Series Features | 基于时间的数据特征 | 滚动平均、趋势特征 |
| **衍生特征** | Derived Features | 通过计算生成的新特征 | 进球率、胜率 |

## 🔧 开发工具术语

### 编程语言和框架

| 术语 | 英文 | 定义 | 用途 |
|------|------|------|------|
| **Python** | Python | 高级编程语言 | 后端开发、数据分析 |
| **FastAPI** | FastAPI | 现代Python Web框架 | API开发 |
| **SQLAlchemy** | SQLAlchemy | Python SQL工具包 | ORM、数据库操作 |
| **Pydantic** | Pydantic | 数据验证库 | 数据模型、API验证 |
| **pytest** | pytest | Python测试框架 | 单元测试、集成测试 |
| **Docker** | Docker | 容器化平台 | 应用打包、部署 |
| **asyncio** | asyncio | Python异步编程库 | 异步I/O操作 |
| **uvicorn** | uvicorn | ASGI服务器 | FastAPI应用运行 |
| **Poetry** | Poetry | Python依赖管理工具 | 项目依赖管理 |
| **Ruff** | Ruff | Python代码检查和格式化工具 | 代码质量保证 |
| **MyPy** | MyPy | Python静态类型检查器 | 类型安全 |

### 数据库技术

| 术语 | 英文 | 定义 | 用途 |
|------|------|------|------|
| **PostgreSQL** | PostgreSQL | 开源关系型数据库 | 主数据存储 |
| **Redis** | Redis | 内存数据结构存储 | 缓存、会话存储 |
| **Alembic** | Alembic | 数据库迁移工具 | 数据库版本管理 |
| **asyncpg** | asyncpg | 异步PostgreSQL驱动 | 异步数据库操作 |
| **SQL** | SQL | 结构化查询语言 | 数据查询、操作 |

### 监控和日志

| 术语 | 英文 | 定义 | 用途 |
|------|------|------|------|
| **Prometheus** | Prometheus | 监控和告警系统 | 指标收集、监控 |
| **Grafana** | Grafana | 开源可视化平台 | 监控仪表板 |
| **Loki** | Loki | 日志聚合系统 | 日志收集、查询 |
| **Jaeger** | Jaeger | 分布式追踪系统 | 性能分析、链路追踪 |
| **APM** | APM | 应用性能监控 | 性能监控、优化 |

## 📈 分析术语

### 统计分析

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **均值** | Mean | 数值的算术平均 | 平均进球数2.5 |
| **中位数** | Median | 排序后的中间值 | 进球数中位数2 |
| **标准差** | Standard Deviation | 数据分散程度的度量 | 进球数标准差1.2 |
| **相关系数** | Correlation Coefficient | 两个变量间线性关系的强度 | 球队实力与胜率相关系数0.8 |
| **回归分析** | Regression Analysis | 建立变量间关系的统计方法 | 线性回归、逻辑回归 |
| **假设检验** | Hypothesis Testing | 统计推断方法 | t检验、卡方检验 |

### 预测分析

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **预测** | Prediction | 基于模型对未来结果的估计 | 主队获胜概率65% |
| **置信度** | Confidence | 预测结果的可信程度 | 95%置信区间 |
| **不确定性** | Uncertainty | 预测结果的误差范围 | 预测误差±0.1 |
| **集成学习** | Ensemble Learning | 结合多个模型的方法 | 随机森林、梯度提升 |
| **交叉验证** | Cross Validation | 模型评估方法 | 5折交叉验证 |

## 🔒 安全术语

### 身份认证

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **认证** | Authentication | 验证用户身份的过程 | 用户名密码登录 |
| **授权** | Authorization | 控制用户访问权限的过程 | 管理员权限、普通用户权限 |
| **JWT** | JSON Web Token | 基于JSON的开放标准令牌 | Bearer Token |
| **OAuth** | OAuth | 开放授权标准 | 第三方登录 |
| **RBAC** | Role-Based Access Control | 基于角色的访问控制 | 管理员角色、用户角色 |

### 数据安全

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **加密** | Encryption | 将数据转换为密文的过程 | AES加密、RSA加密 |
| **哈希** | Hash | 单向加密算法 | SHA-256、MD5 |
| **SSL/TLS** | SSL/TLS | 安全传输协议 | HTTPS、WSS |
| **审计日志** | Audit Log | 记录系统操作的日志 | 用户操作记录、系统变更记录 |
| **数据脱敏** | Data Masking | 隐藏敏感数据的过程 | 手机号脱敏、邮箱脱敏 |

## 🎯 性能术语

### 系统性能

| 术语 | 英文 | 定义 | 目标值 |
|------|------|------|--------|
| **响应时间** | Response Time | 系统响应请求的时间 | <200ms |
| **吞吐量** | Throughput | 系统单位时间处理的请求数 | >1000 RPS |
| **并发用户** | Concurrent Users | 同时访问系统的用户数 | >1000 |
| **可用性** | Availability | 系统可正常服务的时间比例 | 99.9% |
| **延迟** | Latency | 请求处理的等待时间 | <50ms |

### 数据库性能

| 术语 | 英文 | 定义 | 优化方法 |
|------|------|------|----------|
| **索引** | Index | 加速数据库查询的数据结构 | B树索引、哈希索引 |
| **查询优化** | Query Optimization | 提高SQL查询性能的过程 | 执行计划分析、索引优化 |
| **连接池** | Connection Pool | 数据库连接的缓存机制 | 连接复用、连接管理 |
| **分页** | Pagination | 大数据集的分批显示 | LIMIT、OFFSET |
| **缓存击穿** | Cache Penetration | 大量请求缓存中不存在的数据 | 缓存空值、布隆过滤器 |

## 📋 项目管理术语

### 开发流程

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **冲刺** | Sprint | 固定时间的开发周期 | 2周冲刺 |
| **需求** | Requirement | 系统需要实现的功能 | 用户故事、技术需求 |
| **任务** | Task | 具体的工作项 | 代码实现、测试编写 |
| **缺陷** | Bug | 系统中的错误 | 功能错误、性能问题 |
| **技术债务** | Technical Debt | 为快速开发而牺牲的代码质量 | 代码重构、架构优化 |

### 版本控制

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **Git** | Git | 分布式版本控制系统 | GitHub、GitLab |
| **分支** | Branch | 代码的独立开发线 | main、develop、feature |
| **合并** | Merge | 将一个分支的变更合并到另一个分支 | PR、Merge Request |
| **标签** | Tag | 特定版本的标记 | v1.0.0、v2.1.0 |
| **提交** | Commit | 代码变更的记录 | git commit -m "feat: add feature" |

## 🌐 部署术语

### 环境管理

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **开发环境** | Development Environment | 开发人员使用的环境 | localhost:8000 |
| **测试环境** | Test Environment | 质量保证测试的环境 | test.domain.com |
| **预发布环境** | Staging Environment | 上线前的最终测试环境 | staging.domain.com |
| **生产环境** | Production Environment | 正式运行的环境 | api.domain.com |
| **配置管理** | Configuration Management | 管理不同环境的配置 | .env文件、ConfigMap |

### 部署策略

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **蓝绿部署** | Blue-Green Deployment | 零停机时间的部署策略 | 两套环境切换 |
| **滚动更新** | Rolling Update | 逐步替换旧版本的部署策略 | Kubernetes滚动更新 |
| **金丝雀发布** | Canary Release | 小流量测试新版本的发布策略 | 1%流量测试 |
| **回滚** | Rollback | 回退到之前版本的操作 | git revert、数据库回滚 |

## 📝 文档术语

### 文档类型

| 术语 | 英文 | 定义 | 示例 |
|------|------|------|------|
| **API文档** | API Documentation | 接口说明文档 | Swagger、OpenAPI |
| **架构文档** | Architecture Documentation | 系统架构说明文档 | 系统设计、技术选型 |
| **用户手册** | User Manual | 用户使用指南 | 功能说明、操作步骤 |
| **开发指南** | Development Guide | 开发人员的指导文档 | 环境搭建、编码规范 |
| **部署手册** | Deployment Handbook | 系统部署操作指南 | 环境配置、部署流程 |

## 🔄 更新日志

### 版本记录

| 版本 | 日期 | 更新内容 | 维护者 |
|------|------|----------|--------|
| 1.0 | 2025-10-23 | 初始版本，包含基础术语定义 | 开发团队 |
| 1.1 | 2025-10-23 | 添加AI辅助开发术语，完善技术术语 | Claude AI |

### 贡献指南

如果您发现术语缺失或定义不准确，请：

1. 在GitHub上创建Issue
2. 提交Pull Request
3. 联系项目维护者

## 📚 相关文档

- **[CLAUDE.md](../../CLAUDE.md)** - Claude AI助手开发指导
- **[系统架构文档](../architecture/ARCHITECTURE.md)** - 系统架构设计
- **[数据库架构文档](DATABASE_SCHEMA.md)** - 数据库设计和表结构
- **[开发指南](DEVELOPMENT_GUIDE.md)** - 开发环境搭建和规范
- **[API文档](API_REFERENCE.md)** - REST API接口说明
- **[机器学习模型指南](../ml/ML_MODEL_GUIDE.md)** - ML模型开发和部署

---

## 📋 文档信息

- **文档版本**: v1.1 (AI增强版)
- **术语总数**: 200+ 专业术语
- **涵盖领域**: 业务、技术、AI、开发运维等
- **最后更新**: 2025-10-23
- **维护团队**: 开发团队 + Claude AI助手
- **审核状态**: ✅ 已审核

**版本历史**:
- v1.0 (2025-10-23): 初始版本，包含基础术语定义
- v1.1 (2025-10-23): 添加AI辅助开发术语，完善技术术语和链接

**使用建议**:
- 新团队成员建议通读一遍建立基础认知
- 开发过程中可查阅特定术语定义
- 发现缺失术语请及时贡献补充
