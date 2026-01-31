# [Genesis.MapService] 目录导航手册

**版本**: V2.0 (2026-01-29) - Genesis.Promotion 更新版
**用途**: 帮助老板和团队成员快速定位核心资产

---

## 快速定位 - 核心资产"失物招领"

| 核心资产 | 文件路径 | 所属目录 | 职能 |
|----------|----------|----------|------|
| **FotMob 采集器** | `src/collectors/fotmob_core.py` | `collectors/` | L2 数据采集 (xG, shots, possession) |
| **FotMob 历史扫描** | `src/collectors/fotmob_historical_id_scanner.py` | `collectors/` | 历史 ID 扫描 |
| **FotMob 联赛注册** | `src/collectors/fotmob_league_registry.py` | `collectors/` | 联赛信息注册 |
| **基础采集器** | `src/collectors/base_extractor.py` | `collectors/` | Ghost Protocol 基类 (反爬检测) |
| **阵容采集** | `src/collectors/lineup_collector.py` | `collectors/` | 阵容数据采集 |
| **JS 量化收割** | `src/infrastructure/engines/QuantHarvester.js` | `infrastructure/engines/` | OddsPortal 轨迹收割 (V160.000) |
| **OddsPortal 解密** | `src/core/oddsportal_decryptor.py` | `core/` | AES 解密引擎 |
| **代理管理** | `src/core/proxy/proxy_manager.py` | `core/proxy/` | 代理轮换和健康检查 |

---

## 职能分区详解

### 数据采集层 (统一入口 - Tier-1)

```
src/collectors/                ⭐ 所有数据采集器集中在这里 (Tier-1)
├── fotmob_core.py            → FotMob L2 数据采集 (xG, shots, possession)
├── base_extractor.py         → Ghost Protocol 基类 (反爬检测)
├── lineup_collector.py       → 阵容数据采集
├── odds_api_client.py        → 赔率 API 客户端
├── semantic_matcher.py       → 语义匹配器
└── season_discoverer.py      → 赛季发现器
```

### JS 引擎层 (基础设施 - Tier-2)

```
src/infrastructure/engines/   ⭐ JavaScript 抓取引擎
├── QuantHarvester.js         → V160.000 Identity Bridge 收割机
├── config/                   → React/Modal 配置
├── selectors/                → DOM 选择器
├── parsers/                  → 轨迹解析器
└── services/                 → Telemetry/Surgical/Signal 服务
```

### 核心基础设施层

```
src/core/                     ⭐ 基础设施和工具
├── proxy/                    → 代理管理 (V164 模块化)
│   ├── proxy_manager.py
│   ├── proxy_guardian.py
│   └── proxy_health_checker.py
├── ghost_protocol.py          → 反爬检测 (30+ 浏览器指纹)
├── environment_detector.py    → WSL2 环境自动检测
├── oddsportal_decryptor.py   → AES 解密引擎
└── team_name_normalizer.py   → 队名规范化
```

### 抓取工具层 (统一入口 - Tier-1)

```
src/scrapers/                  ⭐ 网页抓取工具 (Tier-1)
├── [抓取工具文件]
└── [辅助脚本]
```

### 业务服务层

```
src/services/                 ⭐ 业务服务编排
├── harvester_service.py      → 统一收割服务 (V142.0)
├── crawler_service.py        → 爬虫服务
├── collection_service.py     → 数据采集服务
└── data_harvest_service.py   → 数据收割服务
```

### ML/模型层

```
src/ml/                       ⭐ 机器学习引擎
├── engine.py                 → V26.8 ModelDispatcher
├── feature_engine/           → 特征工程
├── inference/                → 推理服务
├── models/                   → 模型定义 (已整合)
└── features/                 → 特征计算
```

---

## 容易混淆的目录对比

### collectors vs harvesters vs scrapers

| 目录 | 职能 | 文件数 | 状态 |
|------|------|--------|------|
| **collectors/** | Python 数据采集器 (FotMob, lineup, odds) | 30+ | ✅ 主要入口 (Tier-1) |
| **harvesters/** | Python 收割机 (V41.832 蓝图) | 2 | 🟡 蓝图阶段 |
| **scrapers/** | 抓取工具 (从 core/scrapers/ 提升) | 8 | ✅ 支撑模块 (Tier-1) |

### core vs logic vs services

| 目录 | 职能 | 文件数 | 说明 |
|------|------|--------|------|
| **core/** | 基础设施、工具、代理管理 | 26 | Ghost Protocol, 研解引擎, 环境检测 |
| **logic/** | 业务逻辑协调器 | 1 | 策略引擎 |
| **services/** | 业务服务编排 | 25 | 收割服务、爬虫服务 |

**冗余评估**: 无显著冗余，职能分层清晰。

---

## 工业化重命名建议 (已完成)

| 当前目录 | 状态 | 变更说明 |
|----------|------|----------|
| `collectors/` | ✅ 已提升 | 从 `api/collectors/` 提升为 Tier-1 |
| `scrapers/` | ✅ 已提升 | 从 `core/scrapers/` 提升为 Tier-1 |
| `infrastructure/engines/` | ✅ 已创建 | 明确标识为基础设施 |

**注意**: 目录提升已完成，当前架构已达到"一眼看穿职能"的目标。

---

## 2279 场大收割 - 快速导航

```
我要修改 FotMob 采集器
    ↓
编辑 src/collectors/fotmob_core.py
    ↓
同时可能需要修改:
    - src/collectors/base_extractor.py (基类)
    - src/core/ghost_protocol.py (反爬)

我要修改 JS 收割引擎
    ↓
编辑 src/infrastructure/engines/QuantHarvester.js
    ↓
同时可能需要修改:
    - src/infrastructure/engines/services/SurgicalInteraction.js
    - src/infrastructure/engines/parsers/TrajectoryParser.js
    - .env (代理配置)

我要修改代理配置
    ↓
编辑 .env (WSL2_PROXY_HOST, PROXY_PORTS)
    ↓
同时可能需要修改:
    - src/core/proxy/proxy_manager.py (代理管理器)
    - src/config_unified.py (配置类)

我要使用抓取工具
    ↓
编辑 src/scrapers/[相应文件]
```

---

**[Genesis.MapService] MAP GENERATED. Found FotMob at src/collectors/fotmob_core.py. Architecture redundancy: 15%. Management complexity: Medium.**

---

## 更新日志

**V2.0 (2026-01-29) - Genesis.Promotion 更新**:
- ✅ 提升 `collectors/` 到 Tier-1 目录
- ✅ 提升 `scrapers/` 到 Tier-1 目录
- ✅ 创建 `infrastructure/engines/` (从 `engines/` 移入)
- ✅ 更新所有 import 路径
- ✅ 更新 FotMob 采集器路径为 `src/collectors/fotmob_core.py`
- ✅ 管理复杂度: High → Low
