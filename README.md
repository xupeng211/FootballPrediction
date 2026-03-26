# TITAN Football Prediction Platform

> 工业级足球数据采集与预测平台 | Production-Ready Data Harvesting System
>
> **Version**: V4.51.2-TOTAL-WAR | **Status**: Production-Ready | **Coverage**: 80%+ Threshold

---

## 📐 Architecture

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TITAN 四层流水线架构                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │   L1 Discovery   │────▶│  C++ Fuzzy Match │────▶│  L2/L3 Harvest   │    │
│  │   (Node.js)      │     │  Bridge (Python) │     │  (Node.js)       │    │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘    │
│         │                                                   │               │
│         ▼                                                   ▼               │
│  ┌──────────────────┐                              ┌──────────────────┐    │
│  │   FotMob API     │                              │   ML Prediction  │    │
│  │   Match Seeding  │                              │   (Python)       │    │
│  └──────────────────┘                              └──────────────────┘    │
│                                                             │               │
│                                                             ▼               │
│                                                    ┌──────────────────┐    │
│                                                    │   XGBoost 3-Model │    │
│                                                    │   Consensus       │    │
│                                                    └──────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 技术栈 | 职责 |
|------|--------|------|
| **L1 Discovery** | Node.js + Playwright | 自动发现未来7天比赛 |
| **L2 Harvest** | Node.js + 22节点代理池 | 赔率数据采集（开盘/收盘/亚洲盘） |
| **L3 Smelt** | FeatureSmelter | 12061维特征向量生成 |
| **ML Engine** | Python + XGBoost | 3-Model共识预测（67.2%准确率） |
| **Network Shield** | Custom Proxy Pool | 熔断保护与会话管理 |

### V11.0 Clean Sweep 架构 (Recon 侦察引擎)

V11.0 引入了工业级 Recon 侦察系统，实现从 OddsPortal 高效采集历史数据：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      V11.0 RECON 侦察引擎架构                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │  ReconNavigator  │────▶│   ReconParser    │────▶│  ReconStitcher   │    │
│  │   (页面导航)      │     │   (数据解析)      │     │   (数据缝合)      │    │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘    │
│           │                       │                       │                 │
│           ▼                       ▼                       ▼                 │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │ReconDistributed  │     │ ReconResilience  │     │  ReconMetrics    │    │
│  │    (分布式锁)     │     │   (错误恢复)      │     │   (指标监控)      │    │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### V11.0 核心特性

| 特性 | 实现 | 说明 |
|------|------|------|
| **TraceID 追踪** | 每笔请求唯一编号 | 全链路可观测性 |
| **全局异常捕获** | 单点失败不影响整体 | 任务级容错 |
| **协议解密** | ReconDecryptor | 自动处理加密响应 |
| **熔断保护** | ReconCircuitBreaker | 连续失败自动熔断 |
| **配置解耦** | `config/recon_config.json` | Recon 配置唯一源 |
| **真事务映射保存** | `FixtureRepository` 单 Client 事务 | 避免批量写入伪事务 |
| **Fallback 加固** | `smartScan()` + DOM fallback | API 失败后不再因赛季变量缺失崩溃 |

#### V11.0 Release Note

**新特性**

- Recon TraceID 已从扫描入口显式贯穿到 Navigator、Engine、Parser、Repository
- 新增 Recon 鲁棒性回归测试，覆盖 API 失败后自动进入 fallback 链路

**Bug 修复**

- 修复 `smartScan()` fallback 路径 `dbSeason` 未定义崩溃
- 修复 `FixtureRepository` 批量映射保存的伪事务问题，改为单 `client` 真事务
- 修复 ajax / raw / nested 赔率结构解析回归

**破坏性变更**

- 真实网络与浏览器型验证用例迁移至 `tests/integration/`，`npm test` 仅保留单元测试基线

**已知技术债**

- `AbstractHarvester.js` 当前仍为高耦合大类，已登记到根目录 `TECH_DEBT.md`，计划在 V12.0 或全量收割完成后重构

#### V11.0 启动指令

```bash
# 启动 Recon 扫描器 (单赛季单联赛)
docker-compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/recon_scanner.js --season 2025-2026 --league BUNDESLIGA

# 启动 DOM Surgical Harvest (按月分段清缴)
docker-compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/dom_surgical_harvest.js

# 启动 L1 发现引擎
docker-compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/seed_fixtures.js --season 2025/2026 --league 54
```

---

### 🧩 模块化架构 (V4.52+)

TITAN V4.52 引入了三大高内聚组件，实现真正的模块化设计：

```
┌─────────────────────────────────────────────────────────────────┐
│                    ProductionHarvester                          │
│                    (轻量级调度中心 ~547行)                        │
└──────────────┬─────────────────┬────────────────┬───────────────┘
               │                 │                │
       ┌───────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
       │ Dispatcher   │  │Persistence  │  │ErrorHandler │
       │ 任务分派器    │  │数据持久化器  │  │错误审计器   │
       │ 231行 100%   │  │219行 核心   │  │289行 100%   │
       └──────────────┘  └─────────────┘  └─────────────┘
```

#### 组件职责

| 组件 | 行数 | 覆盖率 | 核心功能 |
|------|------|--------|----------|
| **Dispatcher** | 231 | 100% | Worker ID计算、统计报告、CLI解析、批次调度 |
| **Persistence** | 219 | 60%+ | 数据库保存、文件保存、双保险模式、错误分类 |
| **ErrorHandler** | 289 | 100% | 错误分类、可重试性判断、审计报告、模式匹配 |

#### 使用示例

```javascript
// Dispatcher - 任务分派
const workerId = this.dispatcher.calculateWorkerId(index);
const delay = this.dispatcher.calculateDelay(isRetry, minDelay, maxDelay);
this.dispatcher.printReport();

// Persistence - 数据持久化
await this.persistence.dualSave(pool, matchId, rawData, metadata);
await this.persistence.saveToFile(matchId, rawData, metadata);

// ErrorHandler - 错误审计
const type = this.errorHandler.classify(error);
const retryable = this.errorHandler.isRetryable(error, attempt);
this.errorHandler.audit(error, { matchId, workerId });
```

### 数据流向

```
FotMob API → matches (L1) → raw_match_data (L2) → l3_features (L3) → predictions
     │              │                │                   │                │
     ▼              ▼                ▼                   ▼                ▼
  比赛发现      基础信息        赔率数据(JSONB)      12061维特征      预测结果+EV
```

---

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose

### Installation

```bash
# 克隆项目
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 配置环境变量
cp config/.env.example config/.env
# 编辑 config/.env 填入 DB_PASSWORD 和其他配置

# 启动基础设施
docker-compose -f docker-compose.dev.yml up -d

# 验证安装
npm run titan:check
```

### Start Harvesting

```bash
# 方式1: 哨兵自动监控模式（推荐）
npm run titan:start  # 终端1: 启动收割
npm run titan:watch  # 终端2: 启动哨兵

# 方式2: 手动模式
docker-compose -f docker-compose.dev.yml exec dev \
  node scripts/ops/run_production.js --workers 12 --limit 12000
```

---

## 🛡️ Quality Gate

### 三位一体质检门禁

```
┌─────────────────────────────────────────────────────────────┐
│                    TITAN QUALITY GATE                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   ESLint     │  │    Jest      │  │  Coverage    │      │
│  │   0 Error    │  │   43+ Tests  │  │    80%+      │      │
│  │   Policy     │  │   Pass       │  │  Threshold   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                │                │
│         ▼                 ▼                ▼                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              JSDoc Documentation                      │  │
│  │         (Code as Documentation)                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 质量标准

| 检查项 | 工具 | 阈值 | 命令 |
|--------|------|------|------|
| **静态分析** | ESLint | 0 Error | `npm run lint` |
| **单元测试** | Node.js --test | 100+ Pass | `node --test` |
| **代码覆盖** | c8 | 80%+ | `npx c8 --reporter=text node --test` |
| **文档规范** | JSDoc | Required | `npm run lint` |
| **代码格式** | Prettier | Enforced | `npm run format:check` |

### Pre-Commit Hook

所有提交必须通过本地质检门禁：

```bash
# .git/hooks/pre-commit 自动执行：
1. ESLint 检查 (src/, scripts/)
2. Node.js 单元测试 (100+ tests)
3. Line Coverage 验证 (≥80%)
4. Branch Coverage 验证 (≥80%)
5. components/ 目录扫描
```

**覆盖率阈值**:
- Line Coverage: **≥80%** (阻断)
- Branch Coverage: **≥80%** (阻断)

**执行结果：**

- ✅ 通过：准予提交
- ❌ 失败：阻断提交，需修复后重试

### 运行质检

```bash
# 全量质检流程
npm run qa

# 分项检查
npm run lint          # ESLint 检查
npm run lint:fix      # 自动修复
npm run test          # 单元测试 (Jest)
npm run test:coverage # 覆盖率报告
npm run format:check  # 格式检查

# Mini测试 (Node.js 内置测试，推荐)
node --max-old-space-size=256 tests/unit/Dispatcher.test.js
node --max-old-space-size=256 tests/unit/ErrorHandler.test.js
node --max-old-space-size=256 tests/unit/Persistence.test.js
```

---

## 📦 Deployment

### Docker 部署

```bash
# 开发环境
docker-compose -f docker-compose.dev.yml up -d

# 生产环境
docker-compose -f docker-compose.yml up -d

# 查看状态
docker-compose ps
```

### 环境配置

#### 数据库 (config/.env)

| 变量 | 默认值 | 必填 | 说明 |
|------|--------|------|------|
| `DB_HOST` | `host.docker.internal` | ✅ | 数据库主机 |
| `DB_PORT` | `5432` | ✅ | 数据库端口 |
| `DB_NAME` | `football_db` | ✅ | 数据库名 |
| `DB_USER` | `football_user` | ✅ | 数据库用户 |
| `DB_PASSWORD` | - | **必填** | 数据库密码 |

#### 收割配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MAX_WORKERS` | `12` | 并发Worker数量 |
| `MIN_DELAY_MS` | `10000` | 最小请求延迟 |
| `MAX_DELAY_MS` | `15000` | 最大请求延迟 |
| `PROXY_HOST` | `172.25.16.1` | 代理服务器 |
| `PROXY_PORT_RANGE` | `7891-7912` | 22节点代理池 |

#### 末端韧性模式 (Endgame)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RETRY_MAX_ATTEMPTS` | `5` | NO_DATA最大重试 |
| `CIRCUIT_THRESHOLD` | `10` | 熔断阈值 |
| `ENDGAME_SLOWDOWN` | `true` | 末端降速模式 |

### 运维指令集

| 指令 | 功能 | 场景 |
|------|------|------|
| `npm run titan:check` | 环境健康检查 | 启动前验证 |
| `npm run titan:start` | 启动12路收割 | 全量收割 |
| `npm run titan:watch` | 启动哨兵监控 | 无人值守 |
| `npm run titan:sync` | 存量数据同步 | 数据整理 |
| `npm run titan:audit` | 数据资产审计 | 质量检查 |
| `npm run status:db` | 查看数据库状态 | 监控 |

---

## 📊 Data Dictionary

### 数据库表结构

#### L1: matches (比赛发现层)

| 字段 | 类型 | 说明 |
|------|------|------|
| `match_id` | VARCHAR(50) PK | FotMob比赛ID |
| `home_team` | VARCHAR(100) | 主队名称 |
| `away_team` | VARCHAR(100) | 客队名称 |
| `match_time` | TIMESTAMP | 比赛时间 |
| `l2_harvested` | BOOLEAN | L2收割状态 |
| `is_finished` | BOOLEAN | 是否已完成 |

#### L2: raw_match_data (原始数据层)

| 字段 | 类型 | 说明 |
|------|------|------|
| `match_id` | VARCHAR(50) PK | 比赛ID |
| `collected_at` | TIMESTAMP | 采集时间 |
| `odds_data` | JSONB | 赔率数据(开盘/收盘/1X2/亚洲盘) |
| `xg_data` | JSONB | xG预期进球数据 |
| `source` | VARCHAR(50) | 数据来源 |

#### L3: l3_features (特征向量层)

| 字段 | 类型 | 说明 |
|------|------|------|
| `match_id` | VARCHAR(50) PK | 比赛ID |
| `feature_vector` | FLOAT[] | 12061维特征向量 |
| `feature_names` | TEXT[] | 特征名称列表 |
| `created_at` | TIMESTAMP | 生成时间 |

#### predictions (预测结果层)

| 字段 | 类型 | 说明 |
|------|------|------|
| `match_id` | VARCHAR(50) PK | 比赛ID |
| `home_win_prob` | FLOAT | 主胜概率 |
| `draw_prob` | FLOAT | 平局概率 |
| `away_win_prob` | FLOAT | 客胜概率 |
| `final_confidence` | FLOAT | 最终置信度 |
| `ev_value` | FLOAT | 期望值 |

### 物理文件结构

```
data/
├── matches/           # L2 JSON数据文件
│   ├── 12345.json
│   └── ...
├── sessions/          # 浏览器会话
│   └── manual_session.json
├── registry/          # 代理注册表
│   └── active_registry.json
└── debug/            # 调试输出
    └── screenshots/
```

### 数据质量指标

| 指标 | 目标 | 当前 |
|------|------|------|
| **L1覆盖率** | 100% | 12,000+/12,000 |
| **L2完整率** | ≥95% | 11,907/12,000 (99.2%) |
| **L3特征率** | ≥90% | 待处理 |
| **预测准确率** | ≥65% | 67.2% |

---

## 📁 Project Structure

```
FootballPrediction/
├── config/                    # 配置中心
│   ├── .env.example          # 环境变量模板
│   ├── factory_config.js     # 工厂级配置
│   └── database.js           # 数据库配置
├── scripts/                   # 运维脚本
│   ├── ops/                  # 核心操作
│   │   ├── run_production.js    # 生产收割
│   │   ├── check_health.js      # 健康检查
│   │   ├── sentinel_watch.js    # 哨兵监控
│   │   └── archive_legacy.sh    # 归档脚本
│   └── maintenance/          # 维护工具
├── src/                       # 源代码
│   ├── core/                 # 核心基础设施
│   ├── infrastructure/       # 基础设施层
│   │   ├── harvesters/      # 收割机系统
│   │   ├── network/         # 网络代理
│   │   └── browser/         # 浏览器工厂
│   ├── feature_engine/      # 特征工程
│   ├── ml/                  # 机器学习
│   └── parsers/             # 数据解析器
├── tests/                     # 测试套件
│   └── unit/                 # 单元测试
│       ├── Dispatcher.test.js      # 任务分派器测试 (38用例)
│       ├── ErrorHandler.test.js    # 错误审计器测试 (45用例)
│       ├── Persistence.test.js     # 持久化器测试 (17用例)
│       └── *_Mini.test.js          # 旧版Mini测试 (见下方)
├── docs/                      # 文档中心
├── data/                      # 数据存储
└── models/                    # ML模型仓库
```

---

## 🧪 Mini测试详解

TITAN 使用 Node.js 内置测试框架 (`node --test`) 进行单元测试，相比 Jest 更轻量、更快。

### 7个核心Mini测试

| 测试文件 | 测试目标 | 用例数 | 覆盖率 |
|----------|----------|--------|--------|
| `Dispatcher.test.js` | 任务分派器 | 38 | 100% |
| `ErrorHandler.test.js` | 错误审计器 | 45 | 100% |
| `Persistence.test.js` | 数据持久化器 | 17 | 60%+ |
| `ZK_Mini.test.js` | ZombieKiller | 3 | 核心 |
| `AA_Mini.test.js` | AutoAuthManager | 3 | 核心 |
| `DB_Mini.test.js` | PostgresClient | 5 | 85%+ |
| `FM_Mini.test.js` | FotMobStrategy | 5 | 核心 |

### 运行Mini测试

```bash
# 内存限制模式 (推荐，256MB)
node --max-old-space-size=256 tests/unit/Dispatcher.test.js
node --max-old-space-size=256 tests/unit/ErrorHandler.test.js
node --max-old-space-size=256 tests/unit/Persistence.test.js

# 批量运行
for f in tests/unit/*_Mini.test.js; do
  node --max-old-space-size=256 "$f"
done
```

### 测试覆盖重点

- **Dispatcher**: Worker ID计算、延迟计算、统计报告、CLI解析
- **ErrorHandler**: 8种错误类型分类、可重试性判断、审计报告
- **Persistence**: 数据库/文件错误分类、双保险保存模式

---

## 🔐 Authentication

### Cookie 更新

```bash
# 方法1: 手动导入
node scripts/import_manual_cookies.js

# 方法2: 自动采集
node scripts/capture_auth_v3.js
```

---

## 📈 Monitoring

### 实时监控

```bash
# 查看收割日志
docker-compose logs -f dev

# 数据库状态
npm run status:db

# 哨兵日志
tail -f logs/sentinel.log
```

### 胜利庆典

当 12,000 场目标达成时，哨兵系统将自动展示 ASCII Art 胜利庆典并安全停机。

---

## 🛠️ Troubleshooting

### 常见问题

| 问题 | 诊断 | 解决 |
|------|------|------|
| 代理熔断 | `curl -x http://proxy:port https://httpbin.org/ip` | 重启 docker-compose |
| 数据库连接失败 | `docker-compose exec db pg_isready` | 重启 db 服务 |
| NO_DATA 错误 | 检查 Cookie 是否过期 | 更新 manual_session.json |

### 故障排查手册

- 详见 `docs/TROUBLESHOOTING.md`
- 运维 SOP: `docs/OPERATIONS_SOP.md`

---

## 📋 Version Information

- **Version**: V4.51.2-TOTAL-WAR
- **Node.js**: 18+
- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Coverage**: 80%+ Threshold
- **License**: MIT
- **Last Updated**: 2026-03-13

---

## 🏆 Quality Badges

```
┌────────────────────────────────────────┐
│  ESLint    │  0 Error     │    ✅      │
├────────────────────────────────────────┤
│  Jest      │  43+ Pass    │    ✅      │
├────────────────────────────────────────┤
│  Coverage  │  80%+        │    ✅      │
├────────────────────────────────────────┤
│  JSDoc     │  Required    │    ✅      │
└────────────────────────────────────────┘
```

---

## 🆘 Support

- **Issues**: GitHub Issues
- **Docs**: `docs/` 目录
- **Team**: V174 Engineering Team

---

<p align="center">
  <strong>TITAN —— 工业级足球预测平台</strong><br>
  <em>Production-Ready. Zero Compromise.</em>
</p>
