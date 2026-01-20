# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

---

## 🚨 语言要求（最高优先级）

**请务必使用中文回复用户！**

---

## 📖 项目简介

**FootballPrediction** - 基于 XGBoost 3.0+ 的专业足球比赛预测系统

**项目愿景**: 以年化 25% 的真实收益率为北极星指标，构建可验证、可复制、可持续的体育预测系统

**当前状态**: ✅ Production Ready (V51.0 Industrial Grade Ready)

**基线准确率**: 56% (真赛前) | **推理延迟**: <100ms

---

## 🎯 5 分钟快速开始

```bash
# 1. 启动核心服务
make up

# 2. 验证环境
python main.py --test-proxy

# 3. 测试采集（干跑）
python main.py --source fotmob --mode single --limit 1 --dry-run

# 4. 质量检查
make verify
```

---

## 📋 核心命令速查

### 环境管理
```bash
make help                # 显示所有可用命令
make up                  # 启动核心服务 (db + redis)
make up-pipeline         # 启动核心服务 + 数据流水线
make up-api              # 启动核心服务 + API
make up-dev              # 启动开发环境 (包含管理工具)
make up-all              # 启动所有服务
make verify              # 代码质量检查（lint + test-unit + security）
make ps                  # 查看容器状态
make down                # 停止服务
make restart             # 重启核心服务
make logs                # 查看核心服务日志
make logs-api            # 查看 API 日志
make logs-all            # 查看所有服务日志
make health              # 检查服务健康状态
```

### 数据采集（main.py - V144.7 Command Center）
```bash
# FotMob 数据源
python main.py --source fotmob --mode single --limit 10
python main.py --source fotmob --mode cruise                 # 24h 巡航

# OddsPortal 数据源
python main.py --source oddsportal --mode single --limit 10

# 测试代理
python main.py --test-proxy

# V41.44: 哈希对齐服务
python main.py --action align-hashes --season "23/24"
```

### V41.230+ 生产级赔率同步
```bash
# 单场采集
python run_odds_sync.py --url "https://www.oddsportal.com/.../"

# 自动发现与批量采集 (V41.239)
python scripts/ops/auto_odds_discover.py --concurrent 3
python scripts/ops/auto_odds_discover.py --hours 72
```

### V41.15x 生态系统（运维工具）
```bash
python scripts/ops/v41_155_joint_auditor.py     # V41.155 联合对账审计
python scripts/ops/v41_156_ghost_capture.py    # V41.156 代理池健康检查
python scripts/ops/v41_157_proxy_census.py     # V41.157 代理普查
python scripts/ops/v41_158_stress_test.py      # V41.158 压力测试
python scripts/ops/v41_159_eco_master.py       # V41.159 生态主控
```

### V41.16x-V41.18x 反爬虫对抗工具
```bash
python scripts/ops/v41_164_titan_patch.py      # V41.164 泰坦补丁（链接大扫荡）
python scripts/ops/v41_177_shield_breaker.py   # V41.177 盾牌突破（TLS 绕过）
python scripts/ops/v41_178_hybrid_harvester.py # V41.178 混合收割器
python scripts/ops/v41_179_dual_tower.py       # V41.179 双塔收割器
python scripts/ops/v41_180_memory_hook.py      # V41.180 内存钩子
```

### 测试与质量
```bash
make test-unit           # 运行核心单元测试
make test                # 运行全量测试（7 步质量门禁）
make lint                # Lint 检查
make format              # 格式化代码
make security            # 安全扫描
make verify              # 完整验证（lint + test-unit + security）
./scripts/run_checks.sh  # 完整 CI 质量门禁（7 步）
```

### 数据库操作
```bash
make db-shell            # 进入 PostgreSQL Shell
make db-backup           # 备份数据库
make db-reset            # 重置数据库（危险操作！）
make redis-shell         # 进入 Redis CLI
```

### 清理命令
```bash
make clean               # 清理垃圾文件、缓存和僵尸资产
make clean-csv           # 清理临时测试生成的 CSV 文件
make clean-logs          # 清理超过 7 天的日志文件
make clean-docker        # 清理 Docker 资源
make clean-all           # 完全清理（包括临时文件和日志）
```

### 部署命令
```bash
make deploy              # 部署到生产环境
make build               # 构建生产镜像
make dashboard           # 启动战神仪表盘
```

---

## 🏗️ 系统架构

### 三层流水线架构

```
┌─────────────────────────────────────────────────────────────────┐
│  数据采集层 (Data Collection Layer)                              │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │  FotMob API      │         │  OddsPortal RPA  │              │
│  │  (V144.5)        │         │  (V144.2)        │              │
│  └──────────────────┘         └──────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  数据处理层 (Data Processing Layer)                               │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │  Ghost Protocol  │ ←────── │  HarvesterService │              │
│  │  (V141.0 反爬)   │         │  (V142.0 队列)    │              │
│  └──────────────────┘         └──────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  数据存储层 (Data Storage Layer) - V41.153+ 架构重构              │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │  matches         │         │  matches_mapping │              │
│  │  (Source_F 数据) │         │  (Source_O 数据) │              │
│  └──────────────────┘         └──────────────────┘              │
│                              ↓                                  │
│  ┌──────────────────┐         ┌──────────────────┐              │
│  │  MatchSchema     │         │  storage/        │              │
│  │  (统一数据模型)   │         │  html_vault/     │              │
│  └──────────────────┘         └──────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

### V56.3 三层生产级架构

```
┌─────────────────────────────────────────────────────────────────┐
│  Master 调度层 → Production 提取层 → Database 持久层             │
│  scripts/production_harvester.py                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  • 跨赛季/跨联赛编排: 21/22, 22/23, 23/24                 │ │
│  │  • 智能跳过检测: 自动跳过已有 opening_time 的比赛          │ │
│  │  • 反封禁机制: 每 30 场休息 60 秒                          │ │
│  │  • IP 健康监控: 连续 3 次连接错误 → 5 分钟冷却            │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 版本 | 职责 |
|------|------|------|
| **Command Center** | V144.7 | 多数据源路由（FotMob/OddsPortal） |
| **HarvesterService** | V142.0 | 队列驱动收割服务 |
| **Ghost Protocol** | V141.0 | 反爬检测保护（UA 轮换、熔断器） |
| **ModelDispatcher** | V26.8 | 联赛专项模型分发 |
| **MatchSchema** | V41.155 | 统一比赛数据模型（Source_F + Source_O） |
| **ProxyManager** | V41.156 | 代理池管理器（"幽灵网络"） |

### 数据流向

1. **采集**: `main.py` → `HarvesterService` → `BaseExtractor` → 调用 API
2. **解析**: API 响应 → `technical_features` 解析 → JSONB 存储
3. **入库**: PostgreSQL `matches` 表（Source_F）+ `matches_mapping` 表（Source_O）
4. **建模** (V41.155+): `MatchSchema` 整合双源数据 → 计算 `Fusion_Score` → 质量评级
5. **存储** (V41.153+): `storage/html_vault/` 离线 HTML 存储 + `storage/injection_queue/` 任务队列

---

## 📁 核心目录结构

```
FootballPrediction/
├── src/                          # 生产代码
│   ├── api/collectors/           # 数据采集器
│   ├── ml/                       # ML 引擎
│   ├── processors/               # 特征提取
│   ├── models/                   # V41.155 数据模型 (MatchSchema)
│   ├── core/scrapers/            # V41.156 代理管理器
│   ├── services/                 # 业务服务层
│   └── config_unified.py         # 统一配置
├── scripts/                      # 运维脚本
│   ├── ops/                      # 运维脚本 (V41.x 系列)
│   ├── maintenance/              # 维护脚本
│   └── run_checks.sh             # CI 质量门禁
├── storage/                      # V41.153 存储层
│   ├── html_vault/               # HTML 存储库 (离线解析)
│   └── injection_queue/          # 注入队列 (待处理任务)
├── config/                       # 配置文件
│   └── titan_config.yaml         # V41.151 统一代理和联赛配置
├── tests/                        # 测试套件
├── main.py                       # ⭐ V144.7 命令入口
├── run_odds_sync.py              # ⭐ V41.230 生产级赔率同步入口
├── Makefile                      # ⭐ 快捷命令
└── CLAUDE.md                     # ⭐ 本文档
```

---

## 🔧 开发指南

### 配置管理

```python
from src.config_unified import get_settings

settings = get_settings()
db_host = settings.database.host
```

**环境差异**:
| 环境 | DB_HOST |
|------|---------|
| Docker | `db` |
| 本地 | `localhost` |
| WSL2 | `172.25.16.1` |

### 数据库连接标准

**标准模式**（推荐）:
```python
from src.config_unified import get_settings
import psycopg2

settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value(),
)
cursor = conn.cursor()
```

**快速模式**（使用内置函数）:
```python
from src.config_unified import get_database_url
import psycopg2

conn = psycopg2.connect(get_database_url())
```

**带字典结果**（返回字段名）:
```python
from src.config_unified import get_settings
from psycopg2.extras import RealDictCursor

settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value(),
    cursor_factory=RealDictCursor  # 返回字典而非元组
)
```

### V41.156 代理管理器

```python
from src.core.scrapers.proxy_manager import ProxyManager, ProxyConfig

config = ProxyConfig(
    hosts=["172.25.16.1"],
    ports=[7890, 7892, 7893, 7894, 7895, 7896,  # 原 7 个端口
          7897, 7898, 7899, 7900, 7901, 7902,  # V41.164 新增 6 个端口
          7903, 7904, 7905, 7907, 7908, 7909],  # V41.164 新增 5 个端口
    rotation_strategy="random",
    ban_duration_seconds=1800,  # 30 分钟
    max_failures=10
)
manager = ProxyManager(config)

# 获取可用代理（自动剔除脏 IP）
proxy = manager.get_proxy()

# 记录成功/失败（自动管理代理健康状态）
manager.record_success(proxy)
manager.record_failure(proxy, status_code=403)  # 自动标记为脏 IP，禁封 30 分钟
```

### 核心数据库表

**matches 表** - 比赛基础信息 (Source_F)
```sql
match_id VARCHAR(50) PRIMARY KEY
league_name VARCHAR(255)
season VARCHAR(20)
home_team VARCHAR(255)
away_team VARCHAR(255)
match_time TIMESTAMP
technical_features JSONB      -- 152 维技术特征
l2_raw_json JSONB            -- FotMob L2 原始数据
```

**matches_mapping 表** - 哈希对齐 (Source_O)
```sql
fotmob_id VARCHAR(50) REFERENCES matches(match_id)
oddsportal_hash VARCHAR(8)
oddsportal_url TEXT
match_date TIMESTAMP
mapping_method VARCHAR(50)
confidence FLOAT
review_status VARCHAR(20)
```

**metrics_multi_source_data 表** - 赔率数据
```sql
match_id VARCHAR(50) REFERENCES matches(match_id)
source_name VARCHAR(50)      -- Entity_P (Pinnacle)
init_h/d/a FLOAT             -- 开盘赔率
final_h/d/a FLOAT            -- 终盘赔率
integrity_score FLOAT        -- 完整性分数
```

### 代码质量规范

**提交前必须运行**:
```bash
make verify  # lint + test-unit + security
```

**推荐工作流**:
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

**类型注解要求**: 所有函数必须包含类型注解
```python
# ✅ 正确
def predict_match(home_team: str, away_team: str) -> dict[str, float]:
    ...

# ❌ 错误
def predict_match(home_team, away_team):
    ...
```

### CI/CD 质量门禁

项目包含完整的 CI/CD 流水线 (`.github/workflows/`)，包含 7 步质量门禁：

1. **导入排序检查** (isort)
2. **代码格式化检查** (ruff format/black)
3. **Lint 检查** (ruff check/flake8)
4. **类型检查** (mypy)
5. **单元测试** (pytest)
6. **模型性能回归测试** (baseline accuracy gate)
7. **安全扫描** (bandit)

**本地运行完整门禁**:
```bash
./scripts/run_checks.sh
```

---

## 🐛 常见错误速查表

| 错误信息 | 快速解决方案 |
|---------|-------------|
| `database does not exist` | `make up` + 创建数据库 |
| `Connection refused` | `make up` 启动服务 |
| `HTTP 429/403` | 等待 6-24h 冷却或检查代理 |
| `Module import error` | `pip install -r requirements.txt` |
| `Model file not found` | 运行训练脚本或恢复备份 |
| `KeyError: 'rolling_xg_home'` | 检查历史数据是否充足 |

### 调试流程
```bash
make ps                    # 1. 检查服务状态
make logs                  # 2. 查看日志
pytest tests/ -v -k "test_name"  # 3. 运行测试
```

---

## 🧬 核心模块快速参考

### main.py - V144.7 Multi-Source Command Center

```bash
# V144.7: 多数据源支持
python main.py --source fotmob --mode single --limit 10      # FotMob API 数据源
python main.py --source oddsportal --mode single --limit 10  # OddsPortal RPA 数据源
python main.py --source fotmob --mode cruise                 # FotMob 24h 巡航模式

# 单次收割模式 - 指定联赛和赛季
python main.py --mode single --league "Premier League" --season "23/24"

# 24h 全自动巡航模式
python main.py --mode cruise

# V41.44: 哈希对齐服务（扫描缺失哈希并自动采集）
python main.py --action align-hashes --season "23/24"
python main.py --action align-hashes --league "Premier League"

# 禁用 Ghost Protocol (调试用)
python main.py --mode single --no-ghost

# 限制处理数量
python main.py --mode single --limit 50

# 干跑模式 (不实际采集)
python main.py --mode single --dry-run
```

### run_odds_sync.py - V41.230 Production Entry

```bash
# 单场采集
python run_odds_sync.py --url "https://www.oddsportal.com/.../"

# 指定模式
python run_odds_sync.py --url "..." --patterns "Opening" "Closing"

# 禁用无头模式（调试）
python run_odds_sync.py --url "..." --no-headless

# 指定代理端口
python run_odds_sync.py --url "..." --proxy-port 7893

# 仅提取数据（不存储）
python run_odds_sync.py --url "..." --extract-only
```

### V41.239 自动发现与批量采集

```bash
# 扫描并分发（干跑模式）
python scripts/ops/auto_odds_discover.py --dry-run

# 执行采集
python scripts/ops/auto_odds_discover.py --concurrent 3

# 指定时间窗口（小时）
python scripts/ops/auto_odds_discover.py --hours 72
```

**核心功能**:
- A. 待办池提取 - 从数据库筛选未来 48 小时且无赔率记录的比赛
- B. 智能 URL 生成 - 基于队名和日期动态生成 OddsPortal 搜索 URL
- C. 批量作业分发 - 生产者-消费者模式调用 bin/odds_sync

### HarvesterService - V142.0 收割服务

```python
from src.api.services.harvester_service import HarvesterService

service = HarvesterService(mode="single", enable_ghost_protocol=True)
await service.run()
```

### ModelDispatcher - V26.8 模型分发

```python
from src.ml.engine import ModelDispatcher

dispatcher = ModelDispatcher()
prediction = dispatcher.predict(
    home_team="Arsenal",
    away_team="Chelsea",
    league_name="Premier League"
)
```

### V41.106 架构标准化 - FotMob 采集唯一标准入口

**重要**: V41.106 确立了 FotMob 数据采集的**唯一标准入口**，废除所有临时补丁脚本。

**标准采集方式** - 使用 `FotMobCoreCollector`:
```python
from src.api.collectors.fotmob_core import FotMobCoreCollector

# 创建采集器实例
collector = FotMobCoreCollector()

# 采集比赛数据（标准入口）
match_data = collector.fetch_match_details(match_id=3428850)

# 解析 152 维技术特征
technical_features = collector._parse_technical_features(match_data)

# 存储到数据库
UPDATE matches SET technical_features = %s WHERE match_id = %s
```

**V41.106 核心规范**:
- ✅ **API 端点**: `/matchDetails?matchId={id}` (唯一正确端点)
- ✅ **特征解析**: `_parse_technical_features()` 提取 152 维技术特征
- ✅ **数据存储**: `matches.technical_features` (JSONB 字段)

**禁止操作**:
- ❌ **禁止使用** `/leagueMatchStats` 端点（返回 404）
- ❌ **禁止直接拼写 API URL**（绕过 `FotMobCoreCollector`）
- ❌ **禁止绕过 technical_features 字段**（存储到其他位置）

### V41.121 精准回补引擎

**功能**: 使用现有 match_id 直接回补缺失的 technical_features，无需重新采集。

```python
from src.api.collectors.fotmob_core import FotMobCoreCollector

collector = FotMobCoreCollector()
result = collector.backfill_missing_features(
    match_ids=["match1", "match2", ...],
    concurrent_workers=5
)
# 输出: 成功: 99, 失败: 1 (99.0%)
```

### V41.108/V41.109 审计与架构合龙

**V41.108 地基贯通审计**:
```bash
python scripts/ops/v41_108_integrity_check.py
```
- 五大联赛覆盖率: 53.0% (5,733/10,808)

**V41.109 架构合龙**:
```bash
# 回炉重造引擎（从 l2_raw_json 提取 technical_features）
python scripts/ops/v41_109_reforge_engine.py --limit 100

# 标准化 ID 采集器（德甲/意甲定向采集）
python scripts/ops/v41_109_standardized_harvester.py --league-id 78 --seasons 2020 2021 2022
```

---

## 🛡️ V41.15x 生态系统 - 新一代运维工具集

### V41.155 联合对账审计 (Joint Auditor)

```bash
# 运行双源数据一致性审计
python scripts/ops/v41_155_joint_auditor.py
```

**核心功能**:
- **孤儿记录检测**: 统计有基础数据但缺失哈希URL，或反之的记录
- **时空一致性校验**: 比对 Source_F 和 Source_O 的 match_time，偏差 >15 分钟标记警报
- **数据完整性评级**: 为每场比赛计算 Fusion_Score (0-100)
- **审计报告生成**: Markdown 格式，包含按联赛分布统计和行动建议

**数据模型** (V41.155):
```python
from src.models.match_schema import MatchSchema, MatchQuality

# 从数据库行创建统一数据模型
schema = MatchSchema.from_database_row(row)

# 访问融合分数和质量评级
print(f"Fusion Score: {schema.fusion_score}")  # 0-100
print(f"Quality: {schema.quality_rating}")     # Excellent/Good/Fair/Poor
```

### V41.156 幽灵捕获 (Ghost Capture)

```bash
# 代理池健康检查
python scripts/ops/v41_156_ghost_capture.py
```

**核心功能**:
- **代理健康度追踪**: 实时监控每个代理端点的状态
- **"脏 IP" 自动剔除**: 403/429 禁封自动标记为 dirty，禁封 30 分钟
- **并发安全设计**: threading.Lock 保证多线程环境安全
- **多种轮换策略**: random（默认）, round_robin, weighted

### V41.157 代理普查 / V41.158 压力测试 / V41.159 生态主控

```bash
python scripts/ops/v41_157_proxy_census.py     # 全链路连通性测试
python scripts/ops/v41_158_stress_test.py      # 系统负载测试
python scripts/ops/v41_159_eco_master.py       # 自动化调度
```

---

## 🛡️ V41.16x-V41.18x 反爬虫对抗工具集

| 工具 | 核心技术 | 适用场景 |
|------|----------|----------|
| **V41.164 Titan Patch** | Mg30 + Response Interceptor | 链接大扫荡 |
| **V41.166 Mg30 Stealth** | WebGL + Navigator 伪装 | 浏览器指纹混淆 |
| **V41.177 Shield Breaker** | curl_cffi TLS 绕过 | 指纹封锁突破 |
| **V41.178 Hybrid Harvester** | JSON API + DOM 回退 | 数据采集 |
| **V41.179 Dual Tower** | 双管齐下策略 | 高可靠性采集 |
| **V41.180 Memory Hook** | 内存直接读取 | 零网络请求 |

**推荐使用顺序**:
1. **V41.178 Hybrid Harvester**（首选）- JSON API 优先，速度快
2. **V41.179 Dual Tower**（备选）- 双管齐下，可靠性高
3. **V41.164 Titan Patch**（扫荡）- 批量提取链接
4. **V41.180 Memory Hook**（终极）- 绕过所有网络检测

---

## 📊 V41.153+ 数据模型架构

### Source_F 和 Source_O 双源数据模型

```
┌─────────────────────────────────────────────────────────────────┐
│                    MatchSchema (V41.155)                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Source_F (FotMob 基础元数据)                            │ │
│  │  - match_id, home_team, away_team                        │ │
│  │  - match_time, league_name, season                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Source_O (OddsPortal 市场数据)                          │ │
│  │  - oddsportal_hash, oddsportal_url                       │ │
│  │  - init_h/d/a, final_h/d/a                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Fusion_Score (0-100)                                     │ │
│  │  - 基础信息全 (50%): ID, 队名, 时间, 联赛              │ │
│  │  - 哈希对齐 (50%): oddsportal_hash 非空                  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🌿 Git 工作流

### 分支策略
```bash
main                    # 生产环境（稳定）
feature/新功能名称       # 功能开发
fix/问题描述            # Bug 修复
hotfix/紧急修复         # 生产紧急修复
```

### 提交规范
```bash
feat(collectors): 添加 FotMob L3 采集器支持
fix(database): 修复 l3_features 索引缺失问题
refactor(harvester): 重构 HarvesterService 队列逻辑
```

### 提交前检查清单
- [ ] 运行 `make verify` 通过
- [ ] 新功能有对应测试
- [ ] 更新了相关文档
- [ ] 无遗留调试代码

---

## ⚠️ 重要警告

### V41.106 架构标准化（最高优先级）

**唯一标准入口 - FotMob 采集与解析**:
```
采集与解析的唯一标准入口为 FotMobCoreCollector.fetch_match_details
位置: src/api/collectors/fotmob_core.py
```

**禁止操作**:
- ❌ **禁止直接拼写 API URL** - 必须通过 `FotMobCoreCollector.fetch_match_details()`
- ❌ **禁止绕过 technical_features 字段** - 152 维技术特征必须存储在 `matches.technical_features` (JSONB)
- ❌ **禁止使用错误的 API 端点** - `/matchDetails` 是唯一正确端点（`/leagueMatchStats` 返回 404）
- ❌ **禁止直接修改 `model_zoo/`** 中的模型文件
- ❌ **禁止在生产环境运行** `make db-reset`
- ❌ **禁止跳过 `make verify`** 直接提交
- ❌ **禁止使用硬编码的数据库密码**
- ❌ **禁止创建版本类文件** (`*_v2`, `*_new`, `*_backup`)

**必须操作**:
- ✅ **所有 FotMob 采集必须使用** `FotMobCoreCollector.fetch_match_details(match_id)`
- ✅ **152 维技术特征必须存储在** `matches.technical_features` 字段
- ✅ **修改代码前运行** `git status` 确认分支
- ✅ **提交前运行** `make verify` 确保质量
- ✅ **修改核心模块前完成影响分析**
- ✅ **数据库变更前备份** (`make db-backup`)

### 核心模块保护级别
| 模块 | 保护级别 |
|------|----------|
| `src/ml/inference/` | P0 严格冻结 |
| `src/ml/data/postgres_loader.py` | P1 审批冻结 |
| `scripts/ml/extract_features_v1.py` | P1 审批冻结 |

---

## 📝 测试指南

### 测试目录结构
```
tests/
├── unit/              # 单元测试
│   ├── test_backtest_engine.py
│   ├── test_signal_generator.py
│   └── test_config.py
├── integration/       # 集成测试
└── ops/               # 运维测试
```

### 运行测试
```bash
# 本地开发快速反馈（仅运行核心单元测试）
make test-unit

# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定测试文件
pytest tests/unit/test_config.py -v

# 提交前完整验证
./scripts/run_checks.sh

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

---

## 🔗 快速链接

### 新手入门
- [快速开始](#-5-分钟快速开始) - 5 分钟上手指南
- [核心命令速查](#-核心命令速查) - 常用命令
- [常见错误速查表](#-常见错误速查表) - 快速问题解决

### 核心概念
- [系统架构](#-系统架构) - 三层流水线架构
- [核心数据库表](#核心数据库表) - 数据库结构说明
- [开发指南](#-开发指南) - 配置、数据库连接、代码质量

### 重要规范
- [V41.106 架构标准化](#v41106-架构标准化---fotmob-采集唯一标准入口) - FotMob 采集规范
- [核心模块保护级别](#核心模块保护级别) - 模块修改限制
- [禁止操作](#禁止操作) - 必须避免的操作

### 详细文档
- [docs/onboarding.md](docs/onboarding.md) - 新开发者 30 分钟上手指南
- [docs/troubleshooting.md](docs/troubleshooting.md) - 故障排除指南
- [docs/CHANGELOG.md](docs/CHANGELOG.md) - 版本历史与升级指南
- [docs/module_reference.md](docs/module_reference.md) - 核心模块详细说明

---

## 🔒 永久保留条款

### 语言要求
**请务必使用中文回复用户！**

这一要求具有最高优先级，必须始终保留在文件的显眼位置。

---

**🚨 CRITICAL**: This is a production system support document.

**🧬 当前版本**: V51.0 (Industrial Grade Ready)
**核心模型**: V26.8 (联赛专项)
**数据采集**: V151.3 (并发收割器) + V144.5 (FotMob) + V41.164-V41.180 (反爬虫对抗工具集)
**数据同步**: V36.3 (auto_sync_and_alchemy_v2.sh) + V41.230 (run_odds_sync.py) + V41.239 (auto_odds_discover.py)
**特征引擎**: V29.1 (多格式解析)
**架构重构**: V41.153 (铁军合龙) + V56.3 (三层生产级架构)
**反爬虫**: V41.16x-V41.18x (Mg30 隐身 + Response Interceptor + 混合收割器)
**代理配置**: 18 路代理并发 (V41.164 升级)
**Docker 版本**: V51.0 (Industrial Grade Ready)
**最后更新**: 2026-01-19
**基线准确率**: 56% (真赛前)
**生产状态**: Production Ready
**Python 版本**: 3.11+
