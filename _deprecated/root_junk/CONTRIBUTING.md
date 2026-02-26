# FootballPrediction - 贡献指南

[Genesis.Hardening_Final] V1.0 - Golden Architecture Standards

---

## 目录

1. [黄金架构布局 (Golden Layout)](#黄金架构布局-golden-layout)
2. [单一真相源原则 (Single Source of Truth)](#单一真相源原则-single-source-of-truth)
3. [日志标准 (Logging Standards)](#日志标准-logging-standards)
4. [代码质量规范 (Code Quality)](#代码质量规范-code-quality)
5. [开发工作流 (Development Workflow)](#开发工作流-development-workflow)

---

## 黄金架构布局 (Golden Layout)

### [Genesis.Hardening_Final] V1.0 目录结构

```
FootballPrediction/
├── config/                          # 🔧 配置中心 (单一真相源)
│   ├── leagues.yaml                 # 联赛配置
│   ├── schema_map.yaml              # 数据源结构映射
│   ├── global_harvest_list.yaml     # 全球联赛注册表
│   └── titan_config.yaml            # 统一代理和联赛配置
│
├── src/                             # 📦 生产代码 (核心业务逻辑)
│   ├── api/                         # REST API 层
│   │   ├── collectors/              # 数据采集器
│   │   │   ├── base_extractor.py    # V141.0 Ghost Protocol 基类
│   │   │   ├── fotmob_core.py       # FotMob API 采集
│   │   │   └── odds_production_extractor.py  # 赔率提取
│   │   └── services/                # 业务服务层
│   │       └── harvester_service.py # V142.0 统一收割服务
│   │
│   ├── bridge/                      # 🌉 跨语言桥接层
│   │   ├── js_executor.py           # Python → Node.js 调用
│   │   └── protocols.py             # 数据交换协议
│   │
│   ├── collectors/                  # 数据采集器
│   │   ├── metadata_manager.py      # V20.0 动态联赛元数据管理器
│   │   ├── season_discoverer.py     # 赛季 ID 范围发现器
│   │   └── season_manifest_generator.py  # 赛季清单生成器
│   │
│   ├── config_unified.py            # ⚡ 统一配置管理 (SINGLE SOURCE OF TRUTH)
│   ├── logging_config.py            # 日志配置
│   │
│   ├── core/                        # 核心基础设施
│   │   ├── environment_detector.py  # V41.59 环境智能检测
│   │   ├── proxy_manager.py         # 代理管理器
│   │   └── redis_client.py          # Redis 客户端
│   │
│   ├── database/                    # 数据持久层
│   │   ├── db_pool.py               # 数据库连接池
│   │   ├── collector_repository.py  # [Genesis.Standardization] 采集器仓储
│   │   └── migrations/              # 数据库迁移脚本
│   │
│   ├── harvesters/                  # V41.832 工业级收割机 (蓝图阶段)
│   │   ├── oddsportal_archive.py    # 主收割机
│   │   └── database_inserter.py     # 数据库操作
│   │
│   ├── parsers/                     # 数据解析器
│   │   ├── match_parser.py          # 比赛数据解析
│   │   └── feature_parser.py        # 特征解析
│   │
│   ├── ml/                          # ML 引擎
│   │   ├── training/                # 训练引擎
│   │   │   └── v17_ml_engine.py     # V17 ML 训练引擎
│   │   ├── inference/               # 推理引擎
│   │   │   ├── model_dispatcher.py  # V26.8 模型分发器
│   │   │   └── predictor.py         # 预测器
│   │   └── feature_engine/          # 特征工程
│   │       └── processors/          # 特征处理器
│   │
│   ├── processors/                  # 特征提取处理器
│   │   ├── feature_factory.py       # V41.500+ 自动化特征工厂
│   │   ├── v41_380_golden_extractor.py  # V41.380 黄金特征提取
│   │   ├── path_resolver.py         # Schema-Agnostic 路径访问
│   │   └── integrity_guard.py       # 数据质量评级 (Golden Shield)
│   │
│   ├── scrapers/                    # 网页抓取器
│   │   └── offline_parser.py        # 离线解析器
│   │
│   └── utils/                       # 工具类
│       ├── team_normalizer.py       # V140.0 队名规范化
│       └── ...
│
├── scripts/                         # 🚀 运维脚本
│   ├── ops/                         # JavaScript 运维工具 (V48-V160 系列)
│   │   ├── temporal_sync_engine_v49.js  # V49.000 时间同步引擎
│   │   ├── v48_000_auto_task_pump.sh    # V48.000 任务调度器
│   │   └── v132_000_forensic_analyzer.js # V132.000 取证分析
│   ├── maintenance/                 # 维护脚本
│   └── run_checks.sh                # CI 质量门禁
│
├── tests/                           # 🧪 测试套件
│   ├── harvesters/                  # V41.832 收割机测试
│   ├── unit/                        # 单元测试 (80+ 测试文件)
│   ├── integration/                 # 集成测试
│   └── e2e/                         # 端到端测试
│
├── model_zoo/                       # 🤖 模型仓库
│   ├── v26_7_aligned_production.pkl  # V26.7 通用底座模型
│   └── backup/                      # 模型备份
│
├── config/                          # 配置文件目录
│   ├── .env                         # 环境变量配置
│   ├── leagues.yaml                 # 联赛配置
│   ├── schema_map.yaml              # Schema 韧性配置
│   └── global_harvest_list.yaml     # 全球联赛注册表
│
├── logs/                            # 日志目录
├── data/                            # 数据目录
│
├── main.py                          # V144.9 统一命令入口
├── Genesis_Ignition.py              # 系统点火验证脚本
│
├── requirements-prod.txt            # 生产依赖 (~60 核心库)
├── requirements-dev.txt             # 开发依赖 (~80 工具)
├── pyproject.toml                   # Poetry 配置
├── ruff.toml                        # V106.0 Ruff 配置 (line-length: 100)
│
├── Makefile                         # 统一命令入口
├── CLAUDE.md                        # 项目文档 (开发者指南)
└── CONTRIBUTING.md                  # 本文件 (贡献指南)
```

---

## 单一真相源原则 (Single Source of Truth)

### 核心配置中心

**[Genesis.Hardening_Final] 强制规定**: 所有配置必须通过 `src.config_unified.get_settings()` 获取。

#### ✅ 正确做法

```python
from src.config_unified import get_settings

settings = get_settings()

# 数据库配置
db_host = settings.database.host
db_name = settings.database.name  # 强制: football_db

# FotMob API
fotmob_url = settings.fotmob_base_url  # "https://www.fotmob.com/api"

# 代理配置
proxy_host = settings.proxy.host
proxy_port = settings.proxy.port
```

#### ❌ 禁止做法

```python
# ❌ 硬编码 URL
url = "https://www.fotmob.com/api/allLeagues"

# ❌ 硬编码 IP 地址
DB_HOST = "172.25.16.1"

# ❌ 魔法数字
MAX_RETRIES = 3
TIMEOUT = 30
```

### 配置文件层级 (优先级从高到低)

1. **环境变量 (`.env`)** - 生产环境覆盖
2. **YAML 配置 (`config/*.yaml`)** - 联赛/数据源配置
3. **默认值 (`config_unified.py`)** - 开发环境默认

### 0-Hardcoding 强制检查

在提交代码前，运行以下检查：

```bash
# 检查硬编码 URL
grep -r "https://www.fotmob.com/api" src/ --include="*.py"

# 检查硬编码 IP
grep -r "172\.25\.16\." src/ --include="*.py"

# 检查魔法数字
grep -r "TIMEOUT = [0-9]" src/ --include="*.py"
```

---

## 日志标准 (Logging Standards)

### [Genesis.Hardening_Final] 日志规范

**禁止使用 `print()` 语句** - 所有日志必须通过 `logging` 模块。

### 导入日志器

```python
import logging

logger = logging.getLogger(__name__)
```

### 日志级别使用指南

| 级别 | 用途 | 示例 |
|------|------|------|
| `DEBUG` | 调试信息 | `logger.debug(f"Processing match: {match_id}")` |
| `INFO` | 正常流程 | `logger.info(f"✅ 比赛数据已保存: {match_id}")` |
| `WARNING` | 警告信息 | `logger.warning(f"⚠️  代理连接失败，使用直连")` |
| `ERROR` | 错误信息 | `logger.error(f"❌ 数据库连接失败: {e}", exc_info=True)` |
| `CRITICAL` | 严重错误 | `logger.critical(f"🔥 系统崩溃: {e}", exc_info=True)` |

### 日志格式规范

#### 成功操作

```python
# ✅ 使用 emoji 前缀和简洁描述
logger.info("✅ 数据库连接测试成功")
logger.info(f"✅ 比赛数据已保存: {match_id}")
logger.info(f"✅ 特征提取完成: {len(features)} 维")
```

#### 错误处理

```python
# ✅ 错误日志必须包含堆栈信息 (exc_info=True)
try:
    await database.insert(data)
except Exception as e:
    logger.error(f"❌ 数据库插入失败: {e}", exc_info=True)
```

#### 警告信息

```python
# ✅ 警告用于可恢复的异常情况
logger.warning("⚠️  API 限流，进入冷却期")
logger.warning(f"⚠️  代理 {proxy} 响应缓慢 ({latency:.2f}s)")
```

### 结构化日志 (高级用法)

```python
from src.logging_config import log_execution_time, log_exceptions

@log_execution_time(logger)
def process_match(match_id: str):
    """自动记录执行时间"""
    ...

@log_exceptions(logger)
def risky_operation():
    """自动捕获并记录异常"""
    ...
```

### 禁止的日志模式

```python
# ❌ 禁止使用 print()
print(f"Processing {match_id}")

# ❌ 禁止使用 print() 输出错误
print(f"Error: {e}")

# ❌ 禁止无意义的日志
logger.info("OK")
logger.info("Done")

# ❌ 禁止中文+英文混合无 emoji
logger.info("成功: Database connection established")
```

---

## 代码质量规范 (Code Quality)

### Ruff 配置 (V106.0)

项目使用 **Ruff** 作为主代码质量工具：

```toml
# ruff.toml
line-length = 100
target-version = "py311"

[lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "C4", "DTZ", "T10",
          "EM", "ISC", "ICN", "G", "PIE", "T20", "PT", "Q", "RSE",
          "RET", "SIM", "TID", "TCH", "ARG", "PTH", "ERA", "PL",
          "TRY", "FLY", "PERF", "RUF"]
```

### 质量检查命令

```bash
# 快速验证 (本地开发)
make verify

# 完整质量门禁 (CI 环境)
./scripts/run_checks.sh

# 手动运行工具
ruff format src/ tests/      # 格式化
ruff check src/ tests/       # Lint 检查
mypy src/                    # 类型检查
bandit -r src/               # 安全扫描
```

### 提交前检查清单

- [ ] 运行 `make verify` 通过
- [ ] 无 `print()` 语句残留
- [ ] 无硬编码 URL/IP/端口
- [ ] 所有新函数有中文 docstring
- [ ] 单元测试覆盖率 > 80%

---

## 开发工作流 (Development Workflow)

### 标准提交流程

```bash
# 1. 确认分支
git status

# 2. 创建功能分支 (推荐)
git checkout -b feature/your-feature-name

# 3. 代码修改
# ... 编辑文件 ...

# 4. 提交前检查
make verify

# 5. 添加变更
git add src/path/to/your_file.py
git add tests/path/to/test_file.py

# 6. 提交
git commit -m "feat: 添加 XXX 功能

- 实现了 XXX 特性
- 添加了对应的单元测试
- 通过了 make verify 验证"

# 7. 推送
git push origin feature/your-feature-name
```

### 提交消息规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型 (type)**:
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具

**示例**:
```bash
git commit -m "feat(processors): 添加疲劳度特征计算"
git commit -m "fix(collectors): 修复 FotMob API 429 错误处理"
git commit -m "docs(claude): 更新 V41.832 蓝图状态说明"
```

### 核心文件优先级

修改功能时，按以下优先级选择：

| 优先级 | 文件类型 | 说明 | 示例 |
|--------|----------|------|------|
| **1** | 配置文件 | 优先修改配置 | `config/*.yaml` |
| **2** | 处理器 | 业务逻辑 | `src/processors/*.py` |
| **3** | 服务层 | 服务协调 | `src/api/services/*.py` |
| **4** | 采集器 | 数据采集 | `src/api/collectors/*.py` |
| **5** | 核心模块 | 基础设施 | `src/core/*.py` |

### 禁止操作

- ❌ 绕过 `FotMobCoreCollector.fetch_match_details()` 直接拼写 API URL
- ❌ 绕过 `technical_features` 字段存储数据
- ❌ 直接修改 `model_zoo/` 中的模型文件
- ❌ 在生产环境运行 `make db-reset`
- ❌ 跳过 `make verify` 直接提交
- ❌ 创建版本类文件 (`*_v2`, `*_new`, `*_backup`)

---

## 快速命令参考

### 常用命令

```bash
# 启动服务
make up

# 代码质量
make verify

# 数据采集
python main.py --source fotmob --mode single --limit 10

# 进入数据库
make db-shell

# 查看日志
make logs

# 运行测试
pytest tests/unit/ -v
```

### 系统验证

```bash
# 点火验证 (全链路测试)
python Genesis_Ignition.py

# 预期输出:
# [GENESIS.FIRSTFIRE] IGNITION SUCCESSFUL
# All systems nominal. 2279 Harvest Mission is GO.
```

---

**[Genesis.Hardening_Final] V1.0 - HARDENING COMPLETE**

Logs: Standardized. Hardcoding: ZERO. System ready for GitHub Push and Infinite Harvest.

---

*最后更新: 2026-01-31*
*维护者: [Genesis.Hardening_Final]*
