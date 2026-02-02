# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 🚨 语言要求（最高优先级）

**请务必使用中文回复用户！**

---

## 📑 快速导航

### 🆕 新开发者快速通道

**5 分钟快速上手**（推荐路径）：

```mermaid
graph LR
    A[克隆项目] --> B[安装依赖]
    B --> C[启动服务 make up]
    C --> D[运行测试 main.py --test-proxy]
    D --> E[开始开发]

    style A fill:#e1f5ff
    style B fill:#fff3e0
    style C fill:#e8f5e9
    style D fill:#fce4ec
    style E fill:#f3e5f5
```

### 按角色查找

| 角色 | 推荐阅读 | 预计时间 |
|------|----------|----------|
| **新开发者** | [docs/onboarding.md](docs/onboarding.md) → [快速开始](#-快速开始) | 30 分钟 |
| **数据采集工程师** | [数据采集系统](#-数据采集系统) + [Ghost Protocol](#核心模块) | 45 分钟 |
| **机器学习工程师** | [ML 引擎](#核心模块) + [特征工程](#核心模块) | 60 分钟 |
| **运维工程师** | [Docker 部署](#docker-容器化部署) + [故障排除](#-常见错误速查表) | 30 分钟 |
| **JavaScript 工具** | [JavaScript 运维工具文档](docs/CLAUDE_JS_TOOLS.md) | 45 分钟 |

### 按任务查找

| 我想... | 使用命令 |
|--------|----------|
| 🚀 启动开发环境 | `make up` |
| 🧪 运行代码质量检查 | `make verify` |
| 📊 采集单场比赛数据 | `python main.py --source fotmob --mode single --limit 1` |
| 🔄 24h 全自动巡航 | `python main.py --mode cruise` |
| 🔍 检查代理连通性 | `python main.py --test-proxy` |
| 🗄️ 进入数据库 | `make db-shell` |
| 📈 查看系统日志 | `make logs` |

---

## ⚡ 超快速索引（10 个核心命令）

```bash
# 环境管理
make up                  # 启动核心服务 (db + redis)
make verify              # 运行代码质量检查
make ps                  # 查看容器状态

# 数据采集
python main.py --source fotmob --mode single --limit 10    # FotMob API
python main.py --source oddsportal --mode single --limit 10  # OddsPortal RPA
python main.py --mode cruise                                # 24h 巡航
python main.py --test-proxy                                 # 测试代理

# 开发和测试
make test-unit           # 单元测试
make db-shell            # PostgreSQL Shell
make logs                # 系统日志
```

---

## 📋 项目概览

**FootballPrediction** - 基于 XGBoost 3.0+ 的专业足球比赛预测系统

**项目愿景**: 以年化 25% 的真实收益率为北极星指标，构建可验证、可复制、可持续的体育预测系统

### 当前系统状态

| 属性 | 值 |
|------|-----|
| **状态** | ✅ Production Ready |
| **生产版本** | **V160.0** (Identity Bridge) |
| **命令中心** | **V144.9** (Multi-Source Command Center) |
| **核心模型** | **V26.8** (联赛专项) |
| **特征提取** | **V41.380** (GoldenExtractor) |
| **代码质量** | **V106.0** (Ruff - line-length: 100) |
| **基线准确率** | 56% (真赛前) |
| **推理延迟** | <100ms |
| **最后更新** | 2026-01-31 |

### 版本兼容性矩阵

| Python 版本 | 支持状态 | 推荐用途 |
|-------------|----------|----------|
| **3.11** | ✅ 完全支持 | 生产环境 |
| **3.12** | ✅ 完全支持 | 最新特性 |
| **3.10** | ⚠️ 兼容 | 最低版本 |
| **3.13** | 🔄 测试中 | 实验性 |

| Node.js 版本 | 支持状态 | 用途 |
|--------------|----------|------|
| **18.x** | ✅ 完全支持 | JavaScript 运维工具 |
| **20.x** | ✅ 完全支持 | 推荐 |

---

## ⚡ 快速开始

### 3 分钟上手（4 步）

```bash
# 1. 验证 Git 分支（开发前检查）
git status

# 2. 启动核心服务
make up

# 3. 验证环境并采集测试数据
python main.py --source fotmob --mode single --limit 1

# 4. 检查代码质量（提交前必需）
make verify
```

### 环境要求

| 软件 | 版本 | 检查命令 |
|------|------|----------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| Docker | 24+ | `docker --version` |
| Git | 最新 | `git --version` |

---

## 🏗️ 系统架构

### 简化数据流图

```
┌─────────────────────────────────────────────────────────────────┐
│  数据采集层                                                      │
│  FotMob API (L2数据) + OddsPortal RPA (赔率数据)              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  特征工程层                                                      │
│  GoldenExtractor (V41.380) + Feature Factory (V41.500+)        │
│  → 市场价值/缺阵/评分/疲劳度等 6000+ 维特征                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  数据持久层                                                      │
│  PostgreSQL (matches + metrics_multi_source_data)             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  预测引擎层                                                      │
│  ModelDispatcher (V26.8) → XGBoost 预测                        │
└─────────────────────────────────────────────────────────────────┘
```

### 核心目录结构（简化版）

```
FootballPrediction/
├── src/                              # 生产代码
│   ├── api/collectors/               # 数据采集器
│   │   ├── base_extractor.py         # V141.0 Ghost Protocol
│   │   ├── fotmob_core.py            # FotMob API 采集
│   │   └── odds_production_extractor.py  # 赔率提取
│   ├── api/services/                 # 业务服务层
│   │   └── harvester_service.py      # V142.0 统一收割服务
│   ├── ml/engine.py                  # V26.8 ModelDispatcher
│   ├── processors/                   # V25.1 特征提取
│   ├── infrastructure/engines/       # QuantHarvester (V160.000)
│   └── config_unified.py             # V26.0 统一配置
├── scripts/ops/                      # V41.x 运维工具 ⭐
├── config/                           # 配置文件
├── tests/                            # 测试套件
│   ├── unit/                         # 单元测试 (80+ 文件)
│   └── harvesters/                   # V41.832 收割机测试
├── main.py                           # V144.7 统一命令入口 ⭐
├── Makefile                          # 统一命令入口
└── CLAUDE.md                         # 本文件
```

---

## 🔧 开发指南

### 🚨 核心约束（必读）

| 约束 | 说明 | 违规后果 |
|------|------|----------|
| **单数据库准则** | `DB_NAME` 必须为 `football_db` | 异常 |
| **禁止绕过 FotMobCoreCollector** | 所有 FotMob 采集必须使用指定方法 | 数据不一致 |
| **禁止直接修改 model_zoo/** | 模型文件只能通过重新训练更新 | 模型损坏 |
| **禁止创建版本类文件** | 不创建 `*_v2.py`, `*_new.py`, `*_backup.py` | 代码库混乱 |

### 核心文件优先级

| 优先级 | 文件类型 | 说明 | 示例 |
|--------|----------|------|------|
| **1** | 配置文件 | 优先修改配置 | `config/schema_map.yaml` |
| **2** | 处理器 | 特征提取业务逻辑 | `src/processors/*.py` |
| **3** | 服务层 | 业务服务协调 | `src/api/services/*.py` |
| **4** | 采集器 | 数据采集逻辑 | `src/api/collectors/*.py` |
| **5** | 核心模块 | 基础设施（修改需谨慎） | `src/core/*.py` |

### 代码质量规范

**提交前必须运行**:
```bash
make verify  # 快速验证 (lint + test-unit + security)
```

**配置优先级**:
1. **`ruff.toml`** (最高优先级) - `line-length`: **100 字符**
2. **`pyproject.toml`** (备用配置) - `line-length`: 120 字符

**推荐的代码质量工作流**：
```bash
# 1. 格式化代码
ruff format src/ tests/

# 2. Lint 检查
ruff check src/ tests/

# 3. 类型检查
mypy src/

# 4. 安全扫描
bandit -r src/
```

### Git 工作流

```bash
# 1. 确认当前分支
git status

# 2. 创建功能分支
git checkout -b feature/your-feature-name

# 3. 提交前质量检查
make verify

# 4. 提交变更
git add src/path/to/your_file.py
git commit -m "feat: 添加 XXX 功能"

# 5. 推送到远程
git push origin feature/your-feature-name
```

**提交消息规范**:
```
<type>(<scope>): <subject>

类型: feat | fix | docs | style | refactor | test | chore
```

---

## 🧬 核心模块

### main.py - V144.7 统一命令入口

```bash
# V144.7: 多数据源支持
python main.py --source fotmob --mode single --limit 10
python main.py --source oddsportal --mode single --limit 10
python main.py --mode cruise

# 测试代理
python main.py --test-proxy

# 干跑模式
python main.py --mode single --dry-run
```

### HarvesterService - V142.0 统一收割服务

```python
from src.api.services.harvester_service import HarvesterService

service = HarvesterService(
    mode="single",              # single / cruise
    enable_ghost_protocol=True,
    enable_queue=True,
    limit=None,
)
await service.run()
```

### BaseExtractor - V141.0 Ghost Protocol

**反爬检测基础能力**:
- 30+ 浏览器指纹池
- 人类行为模拟
- 深度拦截检测
- WSL2 自动代理发现

### ModelDispatcher (V26.8)

```python
from src.ml.engine import ModelDispatcher

dispatcher = ModelDispatcher()
prediction = dispatcher.predict(
    home_team="Arsenal",
    away_team="Chelsea",
    league_name="Premier League"  # 自动选择 EPL 专项模型
)
```

### V41.380 GoldenExtractor - 特征深度提取

**三大黄金特征**:
- **市场价值特征**: 球队总身价、身价差值
- **缺阵特征**: 伤停球员、身价影响
- **评分特征**: 球队评分、球员评分

### V41.500+ 自动化特征工厂

**Schema 韧性配置**:
- 数据源 API 结构变化时，只需更新 `config/schema_map.yaml`
- 无需修改代码即可适配

---

## 📊 系统性能基准

| 指标 | 基准值 | 实际测试值 |
|------|--------|-----------|
| **推理延迟** | <100ms | 平均 45ms |
| **吞吐量** | >100 QPS | 150 QPS |
| **模型准确率** | 56% | 56.3% |
| **特征维度** | 6000+ | 6142 维 |
| **FotMob API** | ~2s/match | 1.8s/match |
| **OddsPortal RPA** | ~5s/match | 4.7s/match |

---

## 🛠️ 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **语言** | Python | 3.11+ | 核心开发 |
| **语言** | Node.js | 18+ | JavaScript 运维工具 |
| **数据库** | PostgreSQL | 15 | 数据存储 |
| **缓存** | Redis | 7 | 分布式缓存 |
| **浏览器自动化** | Playwright | 1.57+ | 网页自动化 |
| **ML 框架** | XGBoost | 3.0+ | 预测模型 |
| **Web** | FastAPI | 0.124+ | REST API |
| **测试** | Pytest | 9.0+ | 单元测试 |
| **代码质量** | Ruff | 0.8+ | 格式化 + Lint |

---

## 🧪 测试指南

### 测试场景选择

| 场景 | 推荐命令 | 说明 |
|------|----------|------|
| **本地开发快速反馈** | `make test-unit` | 2 个文件 |
| **单元测试验证** | `pytest tests/unit/ -v` | 80+ 文件 |
| **JavaScript 测试** | `cd scripts/ops && npm test` | V87.203 Jest |
| **提交前完整验证** | `./scripts/run_checks.sh` | 7 步检查 |
| **快速验证** | `make verify` | lint + test-unit |
| **全量测试** | `pytest tests/ -v` | 所有测试 |
| **性能测试** | `pytest -m performance -v --benchmark-only` | 需要插件 |

### 测试标记

```bash
pytest -m unit -v              # 只运行单元测试
pytest -m integration -v       # 只运行集成测试
pytest -m "not network" -v      # 排除网络测试
pytest -m performance -v        # 运行性能测试
```

---

## 🐛 常见错误速查表

> 💡 **详细故障排除**: 查看 [docs/troubleshooting.md](docs/troubleshooting.md)

| 错误信息 | 可能原因 | 快速解决方案 |
|---------|---------|-------------|
| `database "football_db" does not exist` | 数据库未初始化 | `make up` 后创建数据库 |
| `Timeout 30000ms exceeded` | 网络慢或页面加载慢 | 检查代理配置 |
| `HTTP 429 Too Many Requests` | API 限流 | 等待 6-24 小时 |
| `HTTP 403 Forbidden` | IP 被封禁 | 启用 Ghost Protocol |
| `ConnectionRefusedError: 5432` | 数据库未启动 | `make up` |
| `ModuleNotFoundError: No module named 'src'` | Python 路径问题 | 在项目根目录运行 |
| `KeyError: 'rolling_xg_home'` | 特征提取失败 | 检查历史数据 |

---

## 🐚 Docker 容器化部署

### Makefile 命令参考

```bash
# 服务管理
make up                  # 启动核心服务 (db + redis)
make up-pipeline         # 启动 + 数据流水线
make up-api              # 启动 + API 服务
make up-dev              # 启动 + 开发工具
make down                # 停止所有服务
make ps                  # 查看状态

# 代码质量
make verify              # lint + test-unit + security
make lint                # Lint 检查
make format              # 格式化代码
make security            # 安全扫描

# 数据库
make db-shell            # PostgreSQL Shell
make db-backup           # 备份数据库
make redis-shell         # Redis CLI

# 日志和监控
make logs                # 核心服务日志
make logs-api            # API 日志
make health              # 健康检查

# 清理
make clean               # 清理缓存
make clean-all           # 完全清理

# 部署
make deploy              # 部署到生产
```

---

## 🌐 版本号体系

本项目采用**多版本号体系**，各组件独立演进：

| 版本前缀 | 组件范围 | 当前版本 |
|----------|----------|----------|
| `V26.x` | ML 特征引擎和模型 | V26.8 |
| `V41.x` | 数据采集运维工具 | V41.832 |
| `V48/V49.x` | JavaScript 时间同步引擎 | V49.000 |
| `V69.x` | Pipeline 编排器 | V69.000 |
| `V84/V85.x` | JavaScript 视觉提取 | V85.000 |
| `V86/V87.x` | Master Pipeline | V87.203 |
| `V132-V160.x` | QuantHarvester 系列 | V160.000 |
| `V144.x` | 多数据源命令中心 | V144.9 |

> **注意**: 项目版本 (`V26.7.0`) 与组件版本独立。

---

## 📚 延伸阅读

### 核心文档

| 文档 | 内容 |
|------|------|
| [docs/onboarding.md](docs/onboarding.md) | 新开发者快速上手（30分钟） |
| [docs/troubleshooting.md](docs/troubleshooting.md) | 故障排除指南 |
| [docs/CLAUDE_JS_TOOLS.md](docs/CLAUDE_JS_TOOLS.md) | JavaScript 运维工具完整参考 |

### JavaScript 运维工具

**V132-V160 系列**完整文档请查看：
📖 **[docs/CLAUDE_JS_TOOLS.md](docs/CLAUDE_JS_TOOLS.md)**

包含：
- V132.000 Forensic Analyzer - 取证分析工具
- V160.000 Identity Bridge - 身份桥接
- V49.000 Full-Spectrum Temporal Sync Engine
- V84/V85 诊断和测试工具集
- V86/V87 Master Pipeline 系列

### 版本发布说明

详细版本变更记录位于 `docs/V*.md` 文件中。

---

## 🔒 永久保留条款

### 语言要求
**请务必使用中文回复用户！**

这一要求具有最高优先级，必须始终保留在文件的显眼位置。

---

**🚨 CRITICAL**: This is a production system support document.

**🧬 当前版本**: V160.000 (Identity Bridge)
**命令中心**: V144.9 (Multi-Source Command Center)
**特征提取**: V41.380 (GoldenExtractor)
**收割引擎**: V142.0 (HarvesterService)
**QuantHarvester**: V160.000 (Identity Bridge + Modular Refactoring)
**代码质量**: V106.0 (Ruff - line-length: 100)
**最后更新**: 2026-01-31
**基线准确率**: 56% (真赛前)
**生产状态**: Production Ready
**Python 版本**: 3.11+
**Node.js 版本**: 18+ (JavaScript 运维工具)
