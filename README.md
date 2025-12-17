# ⚽ FootballPrediction v2.0 - 足球预测系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=flat-square&logo=docker)](https://docker.com)
[![Coverage](https://img.shields.io/badge/Coverage-80%25+-brightgreen?style=flat-square)](https://github.com/xupeng211/FootballPrediction)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen?style=flat-square)](https://github.com/xupeng211/FootballPrediction)
[![Security](https://img.shields.io/badge/Security-Validated-green?style=flat-square)](https://github.com/xupeng211/FootballPrediction)
[![Version](https://img.shields.io/badge/Version-v2.0.0--Stable-brightgreen?style=flat-square)](https://github.com/xupeng211/FootballPrediction)

🎯 **现代化微服务架构的足球预测系统** - Service Layer + ML Inference + Docker容器化

> 🚀 **最新版本：v2.0.0-Stable** - 全新架构重构，生产就绪

---

## 🏗️ v2.0 架构概览

### 🔄 服务层架构 (Service Layer Architecture)

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Scripts    │    │   FastAPI Web    │    │   External API  │
│                 │    │     Interface    │    │    Clients      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Services Layer (v2.0)                         │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ InferenceServiceV2│ CollectionService│  ExplainabilityService     │
│                 │                 │                             │
│ • 比赛预测       │ • 数据收集        │ • 模型解释                   │
│ • 批量预测       │ • 任务管理        │ • SHAP分析                   │
│ • 缓存管理       │ • 并发执行        │ • 特征重要性                 │
└─────────────────┴─────────────────┴─────────────────────────────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ML Inference Layer (v2.0)                        │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  ModelLoader    │  MatchPredictor │  PredictionCache            │
│                 │                 │                             │
│ • 模型加载       │ • 预测逻辑       │ • LRU缓存                    │
│ • 版本管理       │ • 特征验证       │ • TTL管理                    │
│ • 内存缓存       │ • 统计信息       │ • 自动清理                   │
└─────────────────┴─────────────────┴─────────────────────────────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Layer                                     │
│  PostgreSQL  │    Redis    │  File System  │  External APIs    │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 🐳 一键启动 (推荐)

```bash
# 克隆项目
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 一键启动完整开发环境
./scripts/docker-manager.sh dev

# 🎉 服务已启动！
# 📱 Web应用: http://localhost:8000
# 📚 API文档: http://localhost:8000/docs
# 🗄️ 数据库管理: http://localhost:8080
# 📦 Redis管理: http://localhost:8081
```

### 📋 Docker 管理命令

```bash
# 构建和启动
./scripts/docker-manager.sh build
./scripts/docker-manager.sh up

# 查看状态和日志
./scripts/docker-manager.sh status
./scripts/docker-manager.sh logs -f app

# 健康检查
./scripts/docker-manager.sh health

# 开发环境特性
./scripts/docker-manager.sh dev --collectors    # 启动数据收集器
./scripts/docker-manager.sh test               # 运行测试套件
./scripts/docker-manager.sh quality            # 代码质量检查

# 清理和重置
./scripts/docker-manager.sh clean --all        # 清理所有资源
```

## ⚡ CLI 使用指南

### 🎯 预测比赛 (v2.0)

```bash
# 使用新的 v2.0 预测脚本
python scripts/predict_match_v2.py --home "Manchester United" --away "Arsenal"

# 批量预测
python scripts/predict_match_v2.py --batch matches.json

# 使用特定模型
python scripts/predict_match_v2.py --home "Chelsea" --away "Liverpool" --model xgboost_v2

# 输出示例
🏟️  比赛: Manchester United vs Arsenal
📅  日期: 2024-01-15

📊 预测概率:
主胜 (HOME) : 65.2% |███████████████████████████████████░░░|
平局 (DRAW) : 22.1% |███████████████░░░░░░░░░░░░░░░░░░░░░░|
客胜 (AWAY) : 12.7% |███████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░|

🎯 预测结果: HOME_WIN
💡 置信度: 65.2%
📈 模型版本: xgboost_v2
```

### 🗂️ 数据收集

```bash
# 收集 FotMob 数据
python scripts/collectors/enhanced_fotmob_collector.py --match-id 123456

# 收集赔率数据
python scripts/collectors/odds_collector.py --match-id 123456

# 处理离线特征
python scripts/process_offline_features_full.py
```

## 🔧 开发环境设置

### 📦 本地开发

```bash
# 安装依赖
make install

# 开发环境设置
make dev

# 运行测试
make test

# 代码质量检查
make quality

# 生成覆盖率报告
make coverage
```

### 🐳 Docker 开发环境

```bash
# 启动完整开发环境 (包含热重载和调试)
./scripts/docker-manager.sh dev

# 进入容器开发
./scripts/docker-manager.sh shell

# 查看实时日志
./scripts/docker-manager.sh logs -f app

# 重启服务
./scripts/docker-manager.sh restart
```

### 🧪 测试和质量保证

```bash
# 运行所有测试
./scripts/docker-manager.sh test

# 代码质量检查
./scripts/docker-manager.sh quality

# 安全扫描
make security

# 复杂度分析
make complexity
```

## 📚 API 文档

### 🌐 REST API 端点

```bash
# 启动服务后访问 API 文档
http://localhost:8000/docs
```

#### 主要端点：

- `GET /health` - 健康检查
- `GET /api/v1/predictions/{match_id}` - 获取预测结果
- `POST /api/v1/predictions/batch` - 批量预测
- `GET /api/v1/models` - 模型列表和状态
- `GET /api/v1/stats` - 服务统计信息

#### 示例请求：

```bash
# 单场比赛预测
curl -X GET "http://localhost:8000/api/v1/predictions/123456" \
  -H "accept: application/json"

# 批量预测
curl -X POST "http://localhost:8000/api/v1/predictions/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "matches": [
      {"home_team": "Man United", "away_team": "Arsenal"},
      {"home_team": "Chelsea", "away_team": "Liverpool"}
    ]
  }'
```

## 🏗️ 项目结构

```
FootballPrediction/
├── 📁 src/                          # 核心源代码
│   ├── 📁 api/                      # FastAPI 路由
│   │   ├── health.py                # 健康检查
│   │   ├── predictions/             # 预测API
│   │   └── monitoring.py            # 监控API
│   ├── 📁 services/                 # 服务层 (v2.0新增)
│   │   ├── inference_service_v2.py  # 推理服务
│   │   ├── collection_service.py    # 数据收集服务
│   │   └── explainability_service.py # 可解释性服务
│   ├── 📁 ml/                       # 机器学习
│   │   ├── 📁 inference/            # 推理层 (v2.0新增)
│   │   │   ├── model_loader.py      # 模型加载器
│   │   │   ├── predictor.py         # 预测器
│   │   │   └── cache_manager.py     # 缓存管理器
│   │   ├── 📁 models/                # ML模型
│   │   └── 📁 features/              # 特征工程
│   ├── 📁 database/                 # 数据库相关
│   └── main.py                       # FastAPI 应用入口
├── 📁 scripts/                      # 脚本工具
│   ├── predict_match_v2.py          # v2.0 预测CLI
│   ├── docker-manager.sh            # Docker管理脚本
│   └── 📁 collectors/               # 数据收集器
├── 📁 tests/                        # 测试套件
│   ├── unit/                        # 单元测试
│   ├── integration/                 # 集成测试
│   └── e2e/                         # 端到端测试
├── 📁 docker/                       # Docker配置
│   ├── entrypoint_v2.sh             # v2.0 容器入口
│   └── healthcheck_v2.py            # v2.0 健康检查
├── docker-compose.yml              # 生产环境
├── docker-compose.dev.yml           # 开发环境
├── Dockerfile                       # 容器镜像
├── Makefile                        # 构建工具
└── requirements.txt                # Python依赖
```

## 🔧 核心技术栈

### 🎯 后端架构
- **FastAPI 0.104+** - 现代高性能异步Web框架
- **SQLAlchemy 2.0+** - 现代ORM，支持异步操作
- **PostgreSQL 15+** - 主数据库，JSON支持
- **Redis 7+** - 缓存和消息队列
- **Pydantic V2** - 数据验证和序列化

### 🤖 机器学习
- **XGBoost 2.0+** - 梯度提升模型
- **SHAP 0.50+** - 模型可解释性
- **NumPy/Pandas** - 数据处理
- **Scikit-learn** - 特征工程

### 🐳 容器化和部署
- **Docker** - 容器化
- **Docker Compose** - 多服务编排
- **Multi-stage builds** - 优化的镜像构建
- **Health checks** - 服务健康监控

### 🔍 测试和质量
- **pytest 7.4+** - 测试框架
- **pytest-asyncio** - 异步测试
- **coverage** - 覆盖率报告
- **black/flake8/mypy** - 代码质量
- **bandit** - 安全扫描

## 📊 性能指标

### 🎯 预测性能
- **准确率目标**: 65%+ (从v1.1的58.69%提升)
- **特征维度**: 12维+ 专业特征
- **响应时间**: <100ms (单次预测)
- **缓存命中率**: >80%

### ⚡ 系统性能
- **并发处理**: 1000+ 请求/秒
- **内存使用**: <1GB (标准部署)
- **启动时间**: <30秒 (容器启动)
- **可用性**: 99.9% (生产环境)

## 🛡️ 安全性

### 🔒 安全措施
- ✅ **API认证** - JWT token认证
- ✅ **输入验证** - Pydantic严格验证
- ✅ **SQL注入防护** - SQLAlchemy参数化查询
- ✅ **依赖扫描** - 定期安全更新
- ✅ **HTTPS强制** - 生产环境TLS

### 🛡️ 安全扫描
```bash
# 运行安全扫描
make security

# 依赖漏洞检查
pip-audit

# 容器安全扫描
docker scan footballprediction-app
```

## 📈 监控和运维

### 📊 健康检查
- **应用健康**: `/health` 端点
- **数据库连接**: 连接池状态监控
- **缓存状态**: Redis连接检查
- **ML模型**: 模型加载状态

### 📝 日志管理
- **结构化日志**: JSON格式
- **日志级别**: DEBUG/INFO/WARNING/ERROR/CRITICAL
- **日志轮转**: 自动日志轮转和压缩
- **集中收集**: 支持ELK Stack集成

### 📊 指标监控
- **应用指标**: QPS、延迟、错误率
- **系统指标**: CPU、内存、磁盘、网络
- **业务指标**: 预测准确率、模型性能

## 🤝 贡献指南

### 🔧 开发流程
1. Fork 项目
2. 创建功能分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'Add amazing feature'`
4. 推送分支: `git push origin feature/amazing-feature`
5. 创建 Pull Request

### 📋 开发规范
- 遵循 PEP 8 代码风格
- 编写单元测试和集成测试
- 更新相关文档
- 通过所有质量检查

### 🧪 测试要求
```bash
# 运行完整测试套件
make ci

# 确保测试覆盖率 >80%
make coverage

# 代码质量检查
make quality
```

## 📝 更新日志

### 🎉 v2.0.0-Stable (2024-01-15)

#### 🏗️ 重大架构更新
- **服务层重构**: 全新的Service Layer架构
- **ML推理引擎**: 独立的ML Inference层
- **容器化升级**: 完整的Docker容器化方案
- **API现代化**: FastAPI异步Web框架

#### 🚀 新增功能
- **批量预测API**: 支持多场比赛同时预测
- **模型解释**: SHAP模型可解释性分析
- **缓存系统**: LRU预测结果缓存
- **健康检查**: 多层服务健康监控

#### 🔧 技术改进
- **异步架构**: 全栈异步支持，性能提升3x
- **类型安全**: 完整的Python类型注解
- **依赖升级**: Pydantic V2, SQLAlchemy 2.0等
- **安全增强**: JWT认证、输入验证、HTTPS

#### 🛠️ 开发体验
- **一键部署**: Docker管理脚本
- **热重载**: 开发环境热重载支持
- **调试工具**: 集成调试和性能分析
- **文档完善**: 自动生成API文档

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者和用户！

---

<div align="center">
  <p>⚽ <strong>FootballPrediction v2.0</strong> - 现代化足球预测系统</p>
  <p>🚀 <em>Powered by ML, Service Architecture & Docker</em></p>
</div>