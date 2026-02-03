# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

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
| **数据采集工程师** | [数据采集系统](#-数据采集系统) + [QuantHarvester](#-quantharvester-v170000) + [NetworkShield](#-networkshield-v110-工业级代理管理) | 60 分钟 |
| **机器学习工程师** | [ML 引擎](#核心模块) + [特征工程](#核心模块) | 60 分钟 |
| **运维工程师** | [Docker 部署](#docker-容器化部署) + [环境检测](#️-环境检测系统) | 30 分钟 |
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
| 🌐 JavaScript 收割 | `node src/infrastructure/engines/QuantHarvester.js` |

---

## ⚡ 超快速索引（10 个核心命令）

```bash
# 环境管理
make up                  # 启动核心服务 (db + redis)
make verify              # 运行代码质量检查
make ps                  # 查看容器状态

# 数据采集（Python）
python main.py --source fotmob --mode single --limit 10    # FotMob API
python main.py --source oddsportal --mode single --limit 10  # OddsPortal RPA
python main.py --mode cruise                                # 24h 巡航
python main.py --test-proxy                                 # 测试代理

# 数据采集（JavaScript）
node src/infrastructure/engines/QuantHarvester.js           # V170.000 收割
python -c "from src.infrastructure.network import get_network_shield; import asyncio; shield = asyncio.run(get_network_shield()); print(shield.getStatus())"  # NetworkShield 状态

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
| **QuantHarvester** | **V170.000** (Genesis.NetworkShield) |
| **NetworkShield** | **V1.1.0** (工业级代理管理) |
| **命令中心** | **V144.9** (Multi-Source Command Center) |
| **核心模型** | **V26.8** (联赛专项) |
| **特征提取** | **V41.380** (GoldenExtractor) |
| **代码质量** | **V106.0** (Ruff - line-length: 100) |
| **基线准确率** | 56% (真赛前) |
| **推理延迟** | <100ms |
| **最后更新** | 2026-02-03 |

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

# 2. 启动核心服务（自动检测环境）
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

## 🌐 环境检测系统

### V26.0 智能环境检测

项目内置**智能环境检测系统**，自动识别运行环境并配置最优参数：

```
┌─────────────────────────────────────────────────────────────────┐
│                    V26.0 智能环境检测                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  环境类型检测                                             │ │
│  │  • Docker Environment (DOCKER_ENV=true)                   │ │
│  │  • WSL2 Environment (/proc/version 包含 "microsoft")      │ │
│  │  • Local Environment (默认)                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  自动配置响应                                             │ │
│  │  • Docker: DB_HOST=db, REDIS_HOST=redis                 │ │
│  │  • WSL2: DB_HOST=172.25.16.1 (最优主机检测)              │ │
│  │  • Local: DB_HOST=localhost                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  代理自动发现                                             │ │
│  │  • 环境变量 (HTTPS_PROXY/HTTP_PROXY)                     │ │
│  │  • WSL2 自动探测 (宿主机代理)                            │ │
│  │  • 直连模式 (无代理)                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 环境配置示例

| 环境类型 | DB_HOST | 代理配置 | 启动方式 |
|----------|---------|----------|----------|
| **Docker** | `db` | 环境变量 | `make up` |
| **WSL2** | `172.25.16.1` | 自动探测 | `make up` |
| **本地** | `localhost` | 手动配置 | `make up` |

### 禁用自动检测

如需手动配置，可设置环境变量：
```bash
export DB_HOST=custom_host
export DB_NAME=football_db  # 必须为 football_db
```

---

## 🏗️ 系统架构

### 简化数据流图

```
┌─────────────────────────────────────────────────────────────────┐
│  数据采集层                                                      │
│  FotMob API (L2数据) + OddsPortal RPA (赔率数据)              │
│  QuantHarvester V170.000 (JavaScript 双模提取)                │
│  NetworkShield V1.1.0 (22节点工业级代理管理)                   │
│  Match Engine (Python 基础收割引擎)                           │
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
│   ├── api/                          # API 层
│   │   ├── collectors/                # 数据采集器
│   │   │   ├── base_extractor.py      # V141.0 Ghost Protocol
│   │   │   ├── fotmob_core.py         # FotMob API 采集
│   │   │   └── odds_production_extractor.py  # 赔率提取
│   │   ├── models/                   # ✨ 数据模型 (新增)
│   │   │   └── odds_models.py         # 赔率数据模型
│   │   ├── monitoring/               # ✨ 监控模块 (新增)
│   │   │   └── prometheus_metrics.py  # Prometheus 指标
│   │   └── services/                 # 业务服务层
│   │       └── harvester_service.py  # V142.0 统一收割服务
│   ├── infrastructure/               # 基础设施层
│   │   ├── engines/                  # 引擎系统
│   │   │   ├── QuantHarvester.js      # V170.000 主收割机
│   │   │   ├── match_engine/         # ✨ Python 基础收割引擎 (新增)
│   │   │   │   ├── base/              # 基础引擎抽象类
│   │   │   │   │   └── base_harvest_engine.py  # V1.0.0
│   │   │   │   ├── shared/            # 共享组件
│   │   │   │   │   ├── network_guardian.py  # NetworkShield 适配器
│   │   │   │   │   └── circuit_breaker.py    # 统一熔断器
│   │   │   │   ├── fotmob/            # FotMob 引擎
│   │   │   │   │   └── fotmob_engine.py      # V145.0
│   │   │   │   └── discovery/         # 发现引擎
│   │   │   │       └── dynamic_discovery_engine.py  # ✨ 动态发现引擎
│   │   │   ├── services/             # 模块化服务
│   │   │   │   ├── SignalRadar.js     # 网络雷达
│   │   │   │   └── SurgicalInteraction.js  # 精确交互
│   │   │   ├── parsers/              # 解析器
│   │   │   ├── selectors/            # ✨ 选择器 (新增)
│   │   │   │   └── js_templates.py
│   │   │   └── config/               # 引擎配置
│   │   ├── merger/                   # ✨ 数据融合层 (新增)
│   │   │   └── GoldenDataMerger.py   # V1.0.0 黄金数据缝合器
│   │   └── network/                 # NetworkShield 代理管理
│   │       ├── NetworkShield.js      # V1.1.0 中央代理管理器
│   │       ├── core/                 # 核心组件
│   │       │   ├── CircuitBreaker.js
│   │       │   ├── LRUSessionManager.js
│   │       │   └── RegistryManager.js
│   │       └── health/               # 健康检查
│   ├── config/                       # ✨ 配置模块 (新增)
│   │   └── league/                   # 联赛配置
│   │       ├── fotmob_league_registry.py
│   │       ├── metadata_manager.py
│   │       └── season_manifest_generator.py
│   ├── ml/                          # 机器学习
│   │   ├── engine.py                 # V26.8 ModelDispatcher
│   │   └── processors/               # V25.1 特征提取
│   ├── utils/                       # ✨ 工具函数 (新增)
│   │   ├── semantic_matcher.py      # 语义匹配
│   │   ├── semantic_refiner.py       # 语义校准
│   │   └── levenshtein_matcher.py   # 编辑距离匹配
│   └── config_unified.py            # V26.0 统一配置
├── scripts/ops/                   # V41.x 运维工具 ⭐
├── config/                        # 配置文件
│   ├── active_proxies.json        # V169.300 代理池配置
│   ├── active_registry.json       # V1.1.0 NetworkShield 节点注册表
│   └── schema_map.yaml            # V41.500+ Schema 韧性配置
├── archive/legacy/               # ✨ 遗留代码归档 (新增)
│   └── src/                      # 已归档的遗留文件
├── docs/                         # 文档
│   └── TECHNICAL_DEBT.md         # ✨ 技术债务追踪 (新增)
├── tests/                        # 测试套件
│   ├── unit/                      # 单元测试 (80+ 文件)
│   └── harvesters/                # V41.832 收割机测试
├── production_fire.py            # ✨ 一键数据采集入口 (新增)
├── main.py                       # V144.7 统一命令入口 ⭐
├── Makefile                      # 统一命令入口
└── CLAUDE.md                     # 本文件
```

**目录结构变更说明 (V169.300 → V170.000)**:
- ✨ `src/api/models/`: 赔率数据模型
- ✨ `src/api/monitoring/`: Prometheus 监控模块
- ✨ `src/infrastructure/merger/`: 黄金数据缝合器
- ✨ `src/infrastructure/engines/match_engine/`: Python 基础收割引擎
- ✨ `src/config/league/`: 联赛配置专用目录
- ✨ `src/utils/`: 匹配器工具函数
- ✨ `archive/legacy/`: 遗留代码归档
- ✨ `docs/TECHNICAL_DEBT.md`: 技术债务追踪
- ✨ `production_fire.py`: 一键数据采集入口

---

## 🧬 QuantHarvester V170.000 - Genesis.NetworkShield

### 概述

**QuantHarvester V170.000** 是最新的 JavaScript 数据收割引擎，集成 **NetworkShield V1.1.0** 工业级代理管理系统，实现了**双模提取**和**跨语言代理管理**，专门用于从 OddsPortal 采集高价值赔率数据。

### 核心特性

| 特性 | 说明 |
|------|------|
| **双模提取** | 20秒快速回退到 DOM 抓取 |
| **NetworkShield 集成** | 22节点工业级代理管理 |
| **Session 绑定** | 一个会话 = 一个 IP |
| **跨语言同步** | Python + Node.js 状态共享 |
| **人类脉冲延迟** | 2000-5000ms 随机延迟 |
| **并发上限锁定** | 5 个并发浏览器（硬锁定） |
| **自动愈合** | 失败自动重试逻辑 |

### 核心架构

```
┌─────────────────────────────────────────────────────────────────┐
│  QuantHarvester V170.000                                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  NetworkShieldAdapter - NetworkShield 适配器               │ │
│  │  • Session 绑定 (一个会话 = 一个 IP)                      │ │
│  │  • 跨语言状态同步 (Python + Node.js)                       │ │
│  │  • 兼容原有 ProxyPoolManager 接口                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  SignalRadar - 网络雷达调度中心 (V168.002)                │ │
│  │  • NetworkInterceptor - 网络拦截                          │ │
│  │  • TextSurgicalExtractor - 文本提取                       │ │
│  │  • RadarLogger - 结构化日志                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  SurgicalInteraction - 精确交互服务 (V165.000)            │ │
│  │  • DOMNavigator - DOM 导航                                │ │
│  │  • EventSimulator - 事件模拟                              │ │
│  │  • AntiFingerprint - 反指纹检测                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  TrajectoryParser - 轨迹解析器                            │ │
│  │  • 处理深度 L3 数据                                       │ │
│  │  • 轨迹模拟 (Gap Filling)                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    PostgreSQL (metrics_multi_source_data)
```

### 使用方式

```bash
# 基本用法（自动使用 NetworkShield）
node src/infrastructure/engines/QuantHarvester.js

# 禁用代理
PROXY_ENABLED=false node src/infrastructure/engines/QuantHarvester.js

# 查看代理池统计
# 日志输出: [NetworkShield] Status: 22/22 nodes available, Proxy: ENABLED
```

### 模块化组件

V170.000 采用**模块化架构**，各组件职责清晰：

| 组件 | 文件路径 | 功能 |
|------|----------|------|
| **NetworkShieldAdapter** | `QuantHarvester.js` | NetworkShield 适配器 |
| **SignalRadar** | `services/SignalRadar.js` | 网络雷达调度中心 |
| **SurgicalInteraction** | `services/SurgicalInteraction.js` | 精确交互服务 |
| **TrajectoryParser** | `parsers/TrajectoryParser.js` | 轨迹解析器 |
| **NetworkInterceptor** | `services/intercept/NetworkInterceptor.js` | 网络拦截 |
| **TextSurgicalExtractor** | `services/extractors/TextSurgicalExtractor.js` | 文本提取 |
| **RadarLogger** | `services/logging/RadarLogger.js` | 结构化日志 |

### 双模提取机制

V170.000 继承了 V169.300 的**智能回退机制**：

```
┌─────────────────────────────────────────────────────────────────┐
│  模式一: 网络拦截提取（首选）                                   │
│  • 监听 /match-event/*.dat 请求                                │
│  • Base64 → atob() → JXG.decompress → JSON                    │
│  • 超时: 15秒 (renderTimeout)                                 │
└─────────────────────────────────────────────────────────────────┘
         ↓ 15秒超时或失败
┌─────────────────────────────────────────────────────────────────┐
│  模式二: DOM 抓取（回退）                                      │
│  • 直接从页面 DOM 提取数据                                    │
│  • 悬停取证 + 视觉定位                                       │
│  • 优雅降级确保数据完整性                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 数据写入

所有采集数据写入 `metrics_multi_source_data` 表：

```sql
-- 数据表结构
match_id              VARCHAR(50)      -- 比赛ID
source_name           VARCHAR(50)      -- Entity_P, Entity_B365, etc.
init_h/d/a            FLOAT           -- 开盘赔率
final_h/d/a           FLOAT           -- 终盘赔率
odds_history          JSONB           -- 赔率历史曲线
provider_internal_id  INTEGER         -- 提供商ID
integrity_score       FLOAT           -- 完整性分数 (1.05 = good)
data_timestamp        TIMESTAMP       -- 采集时间
```

---

## 🛡️ NetworkShield V1.1.0 - 工业级代理管理

### 概述

**NetworkShield V1.1.0** 是中央代理管理系统，统一管理 Python (L2) 和 Node.js (L3) 的网络出口，深度对接 Windows 端的 Clash Verge (22个节点)。

### 核心特性

| 特性 | 说明 |
|------|------|
| **解耦设计** | 模块化架构，独立组件可替换 |
| **中央注册制** | 统一节点注册和状态管理 |
| **自适应健康检查** | 自动检测节点可用性 |
| **智能轮换** | Session 绑定确保一致性 |
| **自愈熔断** | 连续失败自动屏蔽节点 |
| **跨语言同步** | Python + Node.js 状态共享 |
| **LRU 会话管理** | 防止长时间运行的内存泄漏 |
| **错误码标准化** | 统一的异常处理机制 |

### 核心架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    NetworkShield V1.1.0                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  RegistryManager - 中央注册管理器                          │ │
│  │  • 节点注册 (22 个 Clash Verge 节点)                      │ │
│  │  • 状态持久化 (active_registry.json)                      │ │
│  │  • 原子锁保护 (防止并发冲突)                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  BatchHealthChecker - 批量健康检查器                       │ │
│  │  • 并发健康检查 (最多 22 个节点)                          │ │
│  │  • 延迟统计 (avg/min/max)                                 │ │
│  │  • 状态更新 (active/circuited/cooldown)                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  CircuitBreakerRegistry - 熔断器注册表                     │ │
│  │  • 连续失败计数 (maxConsecutiveFailures=2)                │ │
│  │  • 自动熔断 (连续 2 次失败后屏蔽)                         │ │
│  │  • 冷却恢复 (15 分钟后自动尝试恢复)                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  LRUSessionManager - LRU 会话管理器                        │ │
│  │  • Session 绑定 (一个会话 = 一个 IP)                      │ │
│  │  • LRU 淘汰 (超过 500 个会话自动清理)                      │ │
│  │  • 超时清理 (30 分钟不活跃自动清理)                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    跨语言状态同步 (Python + Node.js)
```

### 配置文件

节点配置位于 `config/active_registry.json`：

```json
{
  "nodes": [
    {
      "id": "NODE-7891",
      "port": 7891,
      "status": "active",
      "last_check": "2026-02-03T10:00:00Z",
      "avg_latency_ms": 150,
      "consecutive_failures": 0
    }
  ],
  "metadata": {
    "total_nodes": 22,
    "active_nodes": 22,
    "circuited_nodes": 0,
    "cooldown_nodes": 0
  }
}
```

### 使用方式

**Python (L2 数据采集)**:
```python
from src.infrastructure.network import get_network_shield

# 初始化 NetworkShield
shield = get_network_shield(log_level='info')
await shield.initialize()

# 获取健康代理
proxy = await shield.get_next_healthy_proxy(session_id='my-session')
print(f"Using proxy: {proxy.url}")

# 上报成功/失败
await shield.report_success(proxy.port)
await shield.report_failure(proxy.port)

# 获取状态
status = shield.get_status()
print(f"Active nodes: {status.nodes.active}/{status.nodes.total}")
```

**Node.js (L3 数据采集)**:
```javascript
const { getNetworkShield } = require('./NetworkShield');

// 初始化 NetworkShield
const shield = getNetworkShield({ logLevel: 'info' });
await shield.initialize();

// 获取健康代理
const proxy = await shield.getNextHealthyProxy('my-session');
console.log(`Using proxy: ${proxy.url}`);

// 上报成功/失败
await shield.reportSuccess(proxy.port);
await shield.reportFailure(proxy.port);
```

### 熔断器机制

NetworkShield 实现了**自愈熔断**机制：

| 状态 | 触发条件 | 恢复条件 |
|------|----------|----------|
| **active** | 默认状态 | - |
| **circuited** | 连续失败 2 次 | 15 分钟冷却后尝试恢复 |
| **cooldown** | 手动设置冷却 | 冷却时间结束后恢复 |

### Session 绑定

Session 绑定确保**一个浏览器会话始终使用同一 IP**：

```python
# 创建会话
session_id = f"MATCH-{match_id}"
proxy = await shield.get_next_healthy_proxy(session_id)

# 同一会话多次请求返回相同代理
proxy1 = await shield.get_next_healthy_proxy(session_id)
proxy2 = await shield.get_next_healthy_proxy(session_id)
# proxy1.port == proxy2.port  # True
```

---

## ⚙️ Match Engine - Python 基础收割引擎

### 概述

**Match Engine** 是 Python 基础收割引擎架构，提供统一的数据采集基础框架。

### 核心架构

```
src/infrastructure/engines/match_engine/
├── base/
│   └── base_harvest_engine.py    # 基础收割引擎抽象类
├── shared/
│   ├── circuit_breaker.py        # 熔断器
│   └── network_guardian.py       # 网络守护者
├── discovery/
│   └── discovery_engine.py       # 发现引擎
└── fotmob/
    └── fotmob_engine.py          # FotMob 采集引擎
```

### 核心组件

| 组件 | 文件路径 | 功能 |
|------|----------|------|
| **BaseHarvestEngine** | `base/base_harvest_engine.py` | 基础收割引擎抽象类 |
| **CircuitBreaker** | `shared/circuit_breaker.py` | 熔断器模式实现 |
| **NetworkGuardian** | `shared/network_guardian.py` | 网络状态监控 |
| **DynamicDiscoveryEngine** | `discovery/dynamic_discovery_engine.py` | 动态比赛发现引擎（新增） |
| **FotMobEngine** | `fotmob/fotmob_engine.py` | FotMob 数据采集 |

### 使用方式

```python
from src.infrastructure.engines.match_engine.fotmob import FotMobEngine

# 初始化引擎
engine = FotMobEngine()

# 发现比赛
matches = await engine.discover_matches(league_id=47, season="2324")

# 采集数据
for match in matches:
    data = await engine.harvest_match(match_id)
    print(f"Harvested: {data}")
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
1. **`ruff.toml`** (最高优先级) - `line-length`: **100 字符** - 这是项目标准
2. **`pyproject.toml`** (备用配置) - `line-length`: 120 字符 - 仅当 ruff.toml 不存在时使用
3. **注意**: Black 和 isort 在 pyproject.toml 中配置为 120 字符，但项目使用 Ruff 作为主要格式化工具，遵循 ruff.toml 的 100 字符限制

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

### 配置文件说明

**重要配置文件及其作用**：

| 配置文件 | 作用 | 优先级/说明 |
|----------|------|-------------|
| `ruff.toml` | Ruff 代码质量配置 | **最高优先级** - line-length: 100 |
| `.env` | 环境变量 | 数据库、Redis 连接等（不提交到版本控制） |
| `config/active_registry.json` | NetworkShield 节点配置 | 22 个代理节点配置 |
| `config/schema_map.yaml` | Schema 韧性配置 | 数据源 API 路径映射 |
| `pyproject.toml` | 项目元数据和依赖 | 备用代码质量配置 (line-length: 120) |

**配置文件冲突解决**：
- 当 `ruff.toml` 存在时，Ruff 优先使用该配置（100 字符限制）
- `pyproject.toml` 中的 Ruff 配置仅在 `ruff.toml` 不存在时使用
- Black 和 isort 配置为 120 字符，但项目使用 Ruff 作为主要格式化工具

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
| **QuantHarvester** | ~20s/match | V170.000 双模提取 (NetworkShield 集成) |

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
| **本地开发快速反馈** | `make test-unit` | 仅运行 2 个核心测试文件 (backtest_engine + signal_generator) |
| **单元测试验证** | `pytest tests/unit/ -v` | 80+ 文件完整单元测试 |
| **JavaScript 测试** | `cd scripts/ops && npm test` | V87.203 Jest |
| **提交前完整验证** | `./scripts/run_checks.sh` | 7 步检查 |
| **快速验证** | `make verify` | lint + test-unit (2 个文件) + security |
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
| `ProxyPool: No available proxies` | 所有代理被屏蔽 | 检查 `config/active_registry.json` |
| `NetworkShield: No healthy nodes` | 所有节点不可用 | 运行健康检查 `python -c "from src.infrastructure.network import get_network_shield; import asyncio; asyncio.run(get_network_shield().health_check())"` |

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
| `V132-V169.x` | QuantHarvester 系列 | V169.300 |
| `V170.x` | QuantHarvester + NetworkShield | **V170.000** |
| `V144.x` | 多数据源命令中心 | V144.9 |
| `V1.x` | NetworkShield 代理管理 | **V1.1.0** |

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

**完整文档请查看**: 📖 **[docs/CLAUDE_JS_TOOLS.md](docs/CLAUDE_JS_TOOLS.md)**

包含以下系列：
- V132-V169 QuantHarvester 系列（数据收割）
- V170.x QuantHarvester + NetworkShield 系列（工业级代理管理）
- V48/V49 时间同步引擎
- V69 Pipeline 编排器
- V84/V85 诊断和测试工具集
- V86/V87 Master Pipeline 系列

---

## 🔒 永久保留条款

### 语言要求
**请务必使用中文回复用户！**

这一要求具有最高优先级，必须始终保留在文件的显眼位置。

---

**🚨 CRITICAL**: This is a production system support document.

**🧬 当前版本**: V170.000 (Genesis.NetworkShield)
**命令中心**: V144.9 (Multi-Source Command Center)
**特征提取**: V41.380 (GoldenExtractor)
**收割引擎**: V142.0 (HarvesterService)
**QuantHarvester**: V170.000 (双模提取 + NetworkShield)
**NetworkShield**: V1.1.0 (22节点工业级代理管理)
**Match Engine**: Python 基础收割引擎（新增动态发现引擎）
**代码质量**: V106.0 (Ruff - line-length: 100，pyproject.toml 备用为 120)
**最后更新**: 2026-02-03
**基线准确率**: 56% (真赛前)
**生产状态**: Production Ready
**Python 版本**: 3.11+
**Node.js 版本**: 18+ (JavaScript 运维工具)
