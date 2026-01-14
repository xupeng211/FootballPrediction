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
| **五大联赛覆盖率** | 78.0% (1366/1752) |

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

### 禁止操作
- ❌ 不要直接修改 `model_zoo/` 中的模型文件
- ❌ 不要在生产环境运行 `make db-reset`
- ❌ 不要跳过 `make verify` 直接提交
- ❌ 不要使用硬编码的数据库密码
- ❌ 不要创建版本类文件 (`*_v2`, `*_new`, `*_backup`)

### 必须操作
- ✅ 修改代码前运行 `git status` 确认分支
- ✅ 提交前运行 `make verify` 确保质量
- ✅ 修改核心模块前完成影响分析
- ✅ 数据库变更前备份 (`make db-backup`)

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

**🧬 当前版本**: V41.60 (全能之眼 - 代理配置修复与翻页逻辑升级)
**命令中心**: V144.7 (Multi-Source Command Center)
**数据采集**: V41.60 (DOM 提取 + URL 遍历翻页)
**哈希对齐服务**: V41.60 (TDD 驱动的代理配置修复)
**最后更新**: 2026-01-14
**基线准确率**: 56% (真赛前)
**生产状态**: Production Ready
**Python 版本**: 3.11+
