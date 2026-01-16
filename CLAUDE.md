# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

---

## 🚨 语言要求（最高优先级）

**请务必使用中文回复用户！**

---

## 📚 文档导航

### 核心文档
- **本文档** (CLAUDE.md) - 核心开发指南（精简版）
- [docs/onboarding.md](docs/onboarding.md) - 新开发者快速上手（30分钟）
- [docs/troubleshooting.md](docs/troubleshooting.md) - 故障排除指南
- [docs/CHANGELOG.md](docs/CHANGELOG.md) - 版本历史与升级指南
- [docs/V41.108_INTEGRITY_AUDIT_REPORT.md](docs/V41.108_INTEGRITY_AUDIT_REPORT.md) - V41.108 地基贯通审计报告

### 详细参考
- [docs/module_reference.md](docs/module_reference.md) - 核心模块详细说明
- [docs/deployment.md](docs/deployment.md) - Docker 部署完整指南
- [docs/system_architecture.md](docs/system_architecture.md) - 系统架构详解

### 按角色阅读
- **新开发者**: onboarding.md → 本文档（快速开始）
- **数据采集工程师**: module_reference.md（采集器章节）
- **机器学习工程师**: module_reference.md（ML 引擎章节）
- **运维工程师**: deployment.md + troubleshooting.md

---

## 🎯 快速参考（10个核心命令）

```bash
# 环境管理
make up                  # 启动核心服务 (db + redis)
make verify              # 代码质量检查（提交前必需）
make ps                  # 查看容器状态

# 数据采集
python main.py --source fotmob --mode single --limit 10    # FotMob 采集
python main.py --source oddsportal --mode single --limit 10 # OddsPortal 采集
python main.py --mode cruise                                # 24h 巡航
python main.py --test-proxy                                 # 测试代理

# 开发测试
make test-unit           # 运行单元测试
make db-shell            # 进入 PostgreSQL Shell
make logs                # 查看核心服务日志
```

---

## 📋 项目概览

**FootballPrediction** - 基于 XGBoost 3.0+ 的专业足球比赛预测系统

### 当前状态
| 属性 | 值 |
|------|-----|
| **状态** | ✅ Production Ready |
| **生产版本** | V36.1 (Final Guard) |
| **命令中心** | V144.7 (Multi-Source) |
| **核心模型** | V26.8 (联赛专项) |
| **数据采集** | V151.3 (8 Workers) + V41.60 (全能之眼) |
| **哈希对齐服务** | V41.60 (TDD 驱动的代理配置修复) |
| **数据库优化** | V41.49 (连接池优化) |
| **基线准确率** | 56% |
| **推理延迟** | <100ms |
| **五大联赛覆盖率** | 53.0% (5,733/10,808) - V41.108 审计结果 |

### 核心技术栈
- **ML**: XGBoost 3.0+, scikit-learn
- **Backend**: Python 3.11+, FastAPI, PostgreSQL 15, Redis 7
- **Automation**: Playwright, Docker, GitHub Actions
- **Quality**: Ruff, MyPy, Bandit, pytest

---

## ⚡ 快速开始

### 5 分钟上手

```bash
# 1. 启动服务
make up

# 2. 验证环境
python main.py --test-proxy

# 3. 测试采集（干跑）
python main.py --source fotmob --mode single --limit 1 --dry-run

# 4. 质量检查
make verify

# 5. V41.108 完整性审计（可选）
python scripts/ops/v41_108_integrity_check.py
```

### 环境要求
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15

---

## 🏗️ 系统架构（高层概览）

```
main.py (V144.7 统一入口)
    ↓
HarvesterService (V142.0 收割服务)
    ↓
BaseExtractor (V141.0 Ghost Protocol)
    ↓
PostgreSQL (matches + metrics_multi_source_data)
```

**核心组件**:
- **V144.7 Command Center**: 多数据源路由（FotMob/OddsPortal）
- **V142.0 HarvesterService**: 队列驱动收割
- **V141.0 Ghost Protocol**: 反爬检测保护
- **V26.8 ModelDispatcher**: 联赛专项模型

> 详细架构说明请参阅 [docs/system_architecture.md](docs/system_architecture.md)

---

## 📁 核心目录结构

```
FootballPrediction/
├── src/                          # 生产代码
│   ├── api/collectors/           # 数据采集器
│   ├── ml/                       # ML 引擎
│   ├── processors/               # 特征提取
│   └── config_unified.py         # 统一配置
├── scripts/                      # 运维脚本
│   ├── ops/                      # 运维脚本
│   ├── maintenance/              # 维护脚本
│   └── ml/                       # ML 训练脚本
├── tests/                        # 测试套件
├── model_zoo/                    # 模型仓库
├── main.py                       # ⭐ 命令入口
├── Makefile                      # ⭐ 快捷命令
└── CLAUDE.md                     # ⭐ 本文档
```

---

## ⚙️ MCP 和 Skills 配置

### MCP 工具配置
- ✅ **当前可用**: Git log (read-only) - `.claude/mcp_servers/git_server.py`
- ℹ️ **状态**: 配置已简化 (2026-01-08)

### Skills 配置
- 📖 **参考文档**: `.claude/skills/` 包含 15+ 个技能定义文档
- ℹ️ **用途**: 作为项目功能参考和架构理解
- 🔧 **状态**: 自动加载机制已禁用 (2026-01-08)

### 可用技能文档参考

| 类别 | 技能文档 | 功能 |
|------|----------|------|
| **核心业务** | `football-prediction` | XGBoost 2.0+ 预测 |
| | `machine-learning-engineering` | XGBoost 调优, SHAP |
| | `feature-engineering` | V25.1 自适应特征提取 |
| | `data-collection` | FotMob API 数据采集 |
| | `v26-harvest` | V26.1 生产级收割流水线 |
| **开发工具** | `code-quality` | Ruff, MyPy, Bandit, pytest |
| | `fastapi-development` | FastAPI 开发 |
| | `api-testing` | API 单元/集成/性能测试 |
| **运维支撑** | `deployment-management` | Docker 部署 |
| | `deployment-operations` | Docker 容器管理、故障诊断 |
| | `database-operations` | PostgreSQL 优化 |
| | `performance-monitoring` | Prometheus + Grafana |
| | `data-engineering` | ETL 流程设计 |

> **注意**: 技能文档仅供参考，自动加载机制已禁用。开发时请使用本文档中明确的标准命令。

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
```python
from src.config_unified import get_settings
from psycopg2.extras import RealDictCursor

settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value(),
    cursor_factory=RealDictCursor
)
```

### V41.49 数据库连接池配置优化

**连接池参数**（V41.49 优化）:
```python
class DatabaseConfig:
    pool_size: int = 15           # V41.49: 原 10 → 15 (基础连接数)
    max_overflow: int = 20        # 保持 20 (最大溢出数，理论最大 35)
    pool_timeout: int = 10        # V41.49: 原 30 → 10 (降低超时，防止无限阻塞)
    pool_recycle: int = 600       # V41.49: 原 3600 → 600 (10分钟回收，避免长连接问题)
```

**优化说明**:
- ✅ **提升并发能力**: pool_size 从 10 提升到 15，支持更高并发
- ✅ **降低阻塞风险**: pool_timeout 从 30s 降低到 10s，避免长时间等待
- ✅ **避免长连接问题**: pool_recycle 从 1 小时降低到 10 分钟，定期回收连接

**适用场景**:
- 高并发数据采集（8 Workers 并发收割）
- 批量特征提取（1000+ 场比赛）
- API 服务（多用户并发请求）

### V41.121 统一代理配置 - 零硬编码架构

**核心特性**:
- ✅ **配置中心化**: 所有代理配置通过 `src.config_unified.ProxyConfig` 统一管理
- ✅ **零配置启动**: 支持环境变量 `PROXY_PORTS` 和 `PROXY_WSL2_HOST` 动态配置
- ✅ **WSL2 自动检测**: 自动识别 WSL2 环境并使用正确的代理主机地址
- ✅ **类型安全**: 完整的类型注解和 Pydantic 验证

**标准访问方式**:
```python
from src.config_unified import get_config

config = get_config()
proxy_config = config.proxy

# 获取代理端口列表
proxy_ports = proxy_config.proxy_ports  # [7892, 7893, 7894, 7895, 7896, 7898, 7899]

# 获取 WSL2 代理主机
wsl2_host = proxy_config.wsl2_bridge_host  # "172.25.16.1"

# 获取健康检查配置
timeout = proxy_config.health_check_timeout  # 2.0
circuit_breaker = proxy_config.circuit_breaker_threshold  # 5
```

**环境变量配置**:
```bash
# .env 文件
PROXY_PORTS=7892,7893,7894,7895,7896,7898,7899
PROXY_WSL2_HOST=172.25.16.1
```

**各模块 Getter 方法**:
```python
# HashAlignmentService
from src.services.hash_alignment_service import HashAlignmentService
ports = HashAlignmentService.get_proxy_ports()
host = HashAlignmentService.get_wsl2_proxy_host()

# AntiScrapingConfig
from src.services.harvest_config import AntiScrapingConfig
ports = AntiScrapingConfig.get_proxy_ports()
```

**架构改进** (V41.121):
| 模块 | 修改前 | 修改后 |
|------|--------|--------|
| `hash_alignment_service.py` | 硬编码 `PROXY_PORTS` 类变量 | `get_proxy_ports()` 读取统一配置 |
| `harvest_config.py` | 硬编码端口列表 | `get_proxy_ports()` 类方法 |
| `crawler_service.py` | 硬编码 `WSL2_PROXY_HOST` | `_get_proxy_host()` 使用统一配置 |
| `base_extractor.py` | 直接访问 `AntiScrapingConfig.PROXY_PORTS` | 调用 `AntiScrapingConfig.get_proxy_ports()` |
| `fotmob_core.py` | `backfill_missing_features()` 内部硬编码 | 通过 `get_config().proxy` 获取配置 |

### 核心数据库表

**matches 表** - 比赛基础信息
```sql
match_id VARCHAR(50) PRIMARY KEY
league_name VARCHAR(255)
season VARCHAR(20)
home_team VARCHAR(255)
away_team VARCHAR(255)
match_time TIMESTAMP
l2_raw_json JSONB       -- FotMob L2 原始数据
l3_features JSONB       -- V25.1 特征向量
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

### Makefile 常用命令
```bash
# 服务管理
make up                # 启动核心服务
make down              # 停止服务
make restart           # 重启服务
make ps                # 查看状态

# 代码质量
make verify            # 完整验证
make test-unit         # 单元测试
make lint              # Lint 检查
make format            # 格式化代码

# 数据库
make db-shell          # PostgreSQL Shell
make db-backup         # 备份数据库

# 日志
make logs              # 核心服务日志
make logs-all          # 所有服务日志
```

---

## 🐛 常见错误速查表

> 💡 **详细故障排除**: 请查看 [docs/troubleshooting.md](docs/troubleshooting.md)

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
python scripts/health_check.py  # 3. 健康检查
pytest tests/ -v -k "test_name"  # 4. 运行测试
```

---

## 🧬 核心模块快速参考

### main.py - V144.7 命令中心
```bash
python main.py --source fotmob --mode single --limit 10
python main.py --source oddsportal --mode single --limit 10
python main.py --mode cruise
python main.py --test-proxy
```

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

### V151.3 并发收割器
```bash
python scripts/ops/harvest_pinnacle_concurrent.py --workers 3 --limit 100
```

### V40 DOM 收割器（历史数据）
```bash
python scripts/ops/v40_22_improved_harvester.py --leagues "La Liga"
python scripts/ops/v40_24_import_fixed.py --source logs/v40_22_results.json
```

### V41.60 全能之眼 - DOM 提取与代理配置修复
```bash
# V41.60 诊断工具（DOM 结构深度采样）
python scripts/ops/v41_60_dom_diagnostic.py --league "Premier League"

# V41.60 代理诊断（代理环境隔离诊断）
python scripts/ops/v41_60_proxy_diagnostic.py

# V41.60 增强诊断（完整收割流程模拟）
python scripts/ops/v41_60_enhanced_diagnostic.py --league "Premier League"
```

**V41.60 核心特性**:
- ✅ **TDD 驱动的代理配置修复** - 使用 Playwright `proxy` 参数替代 `--proxy-server`
- ✅ **浏览器指纹增强** - 添加 locale 和 timezone_id 使浏览器更像真实用户
- ✅ **URL 遍历模式翻页** - 直接构造分页 URL，更可靠
- ✅ **内容验证** - 检查新页面是否有 hash 链接，智能检测最后一页
- ✅ **双重回退** - URL 失败时回退到点击翻页

**V41.60 适用场景**:
- ✅ 多联赛 DOM 兼容性问题（已解决英超、德甲、意甲提取失败）
- ✅ 代理配置不稳定问题（已修复为 Playwright 原生参数）
- ✅ 翻页逻辑可靠性问题（已升级为 URL 遍历模式）

### V41.61 五大联赛 100% 满绿收官总攻
```bash
# V41.61 自动化收割脚本（按序收割五大联赛）
python scripts/ops/v41_61_grand_finale_harvest.py --limit 100

# V41.61 支持的参数
python scripts/ops/v41_61_grand_finale_harvest.py --leagues "Premier League" "La Liga" --max-retries 3
```

**V41.61 核心特性**:
- ✅ **按序收割五大联赛** - 自动按顺序收割所有联赛
- ✅ **动态重试机制** - 失败自动重试 3 次
- ✅ **实时覆盖率统计** - 追踪收割进度
- ✅ **最终战报生成** - 自动生成收割报告

**注意**: V41.61 收割可能触发 OddsPortal 反爬保护，建议间隔 6-24 小时后重试。

### V41.63 代理连通性检查
```bash
# V41.63 全链路连通性测试（验证 6 个代理端口）
python scripts/ops/v41_63_proxy_check.py

# 检查指定代理端口
python scripts/ops/v41_63_proxy_check.py --ports 7891 7892 7893
```

**V41.63 核心特性**:
- ✅ **6 个代理端口连通性测试** - 验证 7891-7896 端口状态
- ✅ **IP 唯一性验证** - 确保每个代理端口使用不同 IP
- ✅ **并发测试** - 多线程并发测试提高效率
- ✅ **详细报告** - 生成连通性和 IP 分配报告

### V41.108 地基贯通审计 - 完整性审计

```bash
# V41.108 完整性审计（4 项任务）
python scripts/ops/v41_108_integrity_check.py
```

**V41.108 核心功能**:
- ✅ **采集姿势审计** - 检查 API 端点、参数化、代理适配
- ✅ **入口与入库对齐** - 验证 technical_features 初始化和版本追踪
- ✅ **五大联赛完整性暴力测试** - 对比官方场数 vs 数据库场数
- ✅ **回炉重造收益评估** - 统计低精度数据量和 CPU 成本

**V41.108 审计结果** (2026-01-16):
- 五大联赛覆盖率: 53.0% (5,733/10,808)
- 德甲/意甲完全缺失: 0% 覆盖率
- 待回炉重造: 8,813 场 (预计 14.7 分钟)

### V41.109 架构合龙 - 回炉重造引擎与标准化采集器

```bash
# V41.109 回炉重造引擎（从 l2_raw_json 提取 technical_features）
python scripts/ops/v41_109_reforge_engine.py --limit 100

# V41.109 标准化 ID 采集器（德甲/意甲定向采集）
python scripts/ops/v41_109_standardized_harvester.py --league-id 78 --seasons 2020 2021 2022  # 德甲
python scripts/ops/v41_109_standardized_harvester.py --league-id 126 --seasons 2020 2021 2022  # 意甲
```

**V41.109 核心功能**:
- ✅ **回炉重造引擎** - 从 l2_raw_json 中提取 technical_features（零网络成本）
- ✅ **标准化 ID 采集器** - 参数化赛季支持 (--season)、代理池轮换
- ✅ **入库对齐** - technical_features 字段显式包含
- ✅ **德甲/意甲支持** - League ID 78 (Bundesliga)、126 (Serie A)

**V41.109 回炉重造特性**:
- ✅ 零 API 额度消耗（本地离线处理）
- ✅ 零代理流量消耗
- ✅ 批量处理，支持断点续传
- ✅ 实时进度监控

**V41.109 标准化采集器特性**:
- ✅ V41.106 标准入口 (FotMobCoreCollector)
- ✅ 代理池轮换 (19 端口)
- ✅ 批量入库优化
- ✅ 种子球队池配置（五大联赛）

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
- ✅ **黄金收割**: `scripts/ops/v41_103_golden_harvest.py` (标准脚本)

**禁止操作**:
- ❌ **禁止使用** `/leagueMatchStats` 端点（返回 404）
- ❌ **禁止直接拼写 API URL**（绕过 `FotMobCoreCollector`）
- ❌ **禁止绕过 technical_features 字段**（存储到其他位置）

**已归档的临时脚本** (V41.98-V41.105):
- `v41_102_api_sniff_test.py` → `scripts/archive/`
- `v41_103_smoke_test.py` → `scripts/archive/`

### V41.121 精准回补引擎 - FotMobCoreCollector.backfill_missing_features()

**V41.121 新增方法**: 使用现有 match_id 直接回补缺失的 technical_features，无需重新采集。

**核心特性**:
- ✅ **V41.120 验证方法**: 使用现有 match_id 直接查询 FotMob API（无需搜索）
- ✅ **正确解析**: 修复 `header.teams[]` 数组解析，避免 `home.id` 错误
- ✅ **双层回补**: 同时更新基础索引字段和 `technical_features`（152维）
- ✅ **并发处理**: ThreadPoolExecutor + 代理轮换
- ✅ **零硬编码**: 通过 `get_config().proxy` 获取代理配置
- ✅ **JSON 序列化**: 自动转换 PostgreSQL Decimal 为 float

**使用方式**:
```python
from src.api.collectors.fotmob_core import FotMobCoreCollector

# 查询缺失 technical_features 的比赛
import psycopg2
conn = psycopg2.connect(...)
cur = conn.cursor()
cur.execute("""
    SELECT match_id FROM matches
    WHERE technical_features IS NULL
    LIMIT 100
""")
match_ids = [row[0] for row in cur.fetchall()]

# 创建采集器并执行回补
collector = FotMobCoreCollector()
result = collector.backfill_missing_features(
    match_ids=match_ids,
    concurrent_workers=5,
    dry_run=False
)

# 查看结果
print(f"成功: {result['successful']}, 失败: {result['failed']}")
# 输出: 成功: 99, 失败: 1 (99.0%)
```

**V41.120 关键修复**:
| 问题 | 旧方法 | V41.120 修复 |
|------|--------|-------------|
| 队伍 ID 解析 | `match_data['home']['id']` | `match_data['header']['teams'][0]['id']` |
| Match ID 来源 | 搜索 API 获取 | 直接使用数据库现有 match_id |
| 数据库操作 | UPSERT（可能创建重复） | UPDATE（仅更新现有记录） |

**适用场景**:
- 批量回补缺失的 `technical_features` 字段
- 修复 `home_team_id` / `away_team_id` 索引字段
- 数据迁移后的完整性修复

**152 维技术特征分类**:
| 类别 | 数量 | 占比 | 示例 |
|------|------|------|------|
| **黄金信号** | 48 | 31.6% | `home_xg`, `shots_on_target`, `possession` |
| **统计噪音** | 72 | 47.4% | `ratio_*` 冗余特征 |
| **元数据** | 3 | 2.0% | `_meta.total_metrics` |
| **缺失数据** | 29 | 19.1% | 需要修复映射 |

### V41.108 五大联赛完整性统计

```bash
# 五大联赛覆盖率监控 SQL
docker-compose exec db psql -U football_user -d football_db -c "
SELECT
    m.league_name,
    COUNT(*) as total_matches,
    COUNT(m.technical_features->>'home_xg') as with_xg,
    ROUND(COUNT(m.technical_features->>'home_xg') * 100.0 / COUNT(*), 2) as xg_coverage
FROM matches m
WHERE m.league_name IN ('Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1')
  AND m.season IN ('2019', '2020', '2021', '2022', '2023', '2024')
GROUP BY m.league_name
ORDER BY xg_coverage DESC;
"
```

**V41.108 审计结果** (2026-01-16):
| 联赛 | 官方总计 | 数据库 | 覆盖率 | 状态 |
|------|----------|--------|--------|------|
| 英超 | 2,280 | 2,081 | 91.3% | ✅ 优秀 |
| 西甲 | 2,280 | 1,900 | 83.3% | ✅ 良好 |
| 德甲 | 1,836 | 0 | 0.0% | ❌ 完全缺失 |
| 意甲 | 2,280 | 0 | 0.0% | ❌ 完全缺失 |
| 法甲 | 2,132 | 1,752 | 82.2% | ✅ 良好 |
| **总计** | **10,808** | **5,733** | **53.0%** | ⚠️ 待改进 |

> 详细模块说明请参阅 [docs/module_reference.md](docs/module_reference.md)

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

### pytest 标记
```bash
pytest -m unit                    # 单元测试
pytest -m integration             # 集成测试
pytest -m "not network"           # 排除网络测试
```

### 运行单个测试
```bash
pytest tests/unit/test_config.py -v
pytest tests/unit/test_config.py::TestConfig::test_database_config -v
pytest -k "test_database" -v
```

### 测试场景
```bash
# 本地开发快速反馈
make test-unit

# 提交前完整验证
./scripts/run_checks.sh

# 全量测试
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

---

## 🔒 永久保留条款

### 语言要求
**请务必使用中文回复用户！**

这一要求具有最高优先级，必须始终保留在文件的显眼位置。

---

**🚨 CRITICAL**: This is a production system support document.

**🧬 当前版本**: V41.109 (架构合龙 - 回炉重造引擎与标准化采集器)
**命令中心**: V144.7 (Multi-Source Command Center)
**数据采集**: V41.109 (标准化 ID 采集器) + V151.3 (并发收割器)
**哈希对齐服务**: V41.60 (TDD 驱动的代理配置修复)
**最后更新**: 2026-01-16
**基线准确率**: 56% (真赛前)
**生产状态**: Production Ready
**Python 版本**: 3.11+
