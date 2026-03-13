# FootballPrediction - AI 助手指令上下文

> **系统版本**: V4.51.2-TOTAL-WAR | **最后更新**: 2026-03-13
>
> 本文档为 AI 助手提供项目背景、架构理解和操作指南，用于快速上手和高效协作。

---

## 1. 项目概述

### 1.1 项目定位

**FootballPrediction** 是一个工业级足球预测平台，采用双语言（Node.js + Python）四层架构，通过多源数据采集、C++ 模糊匹配和 XGBoost 多模型共识，实现高精度的比赛预测。

### 1.2 核心能力

| 模块 | 技术实现 | 说明 |
|------|----------|------|
| **L1 Discovery** | FotMob API | 自动发现未来 7 天比赛 |
| **L2 Harvest** | FotMob Details + 22 节点代理池 | 赔率数据采集（开盘/收盘/亚洲盘） |
| **L3 Smelt** | FeatureSmelter | 11维纯净战斗特征向量 |
| **ML Prediction** | XGBoost TITAN 模型 | 65.31% 准确率，<100ms 响应 |
| **OddsFluxDetector** | V5.0 赔率背离算法 | 实时监测赔率异常波动 |
| **Swarm Harvest** | Hyper Swarm 引擎 | 多 Worker 并发收割 |
| **Sentinel** | 哨兵监控系统 | 自动停机与熔断保护 |

### 1.3 质量认证

- **零模拟数据**：所有数据来自真实 API
- **幂等收割**：支持重复执行，自动跳过已完成
- **架构纯净**：无冗余模块，无废弃代码
- **黄金准则**：80% 测试覆盖率熔断 + 0 Error 静态质量

---

## 2. 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **运行时** | Node.js 20+ / Python 3.11+ | 双语言架构 |
| **数据库** | PostgreSQL 15 | 数据存储 |
| **缓存** | Redis | 分布式锁/缓存 |
| **容器化** | Docker / docker-compose | 环境隔离 |
| **浏览器** | Playwright + Stealth | 页面自动化与反检测 |
| **模糊匹配** | RapidFuzz (C++) | 队名匹配 |
| **ML** | XGBoost 2.0+ / scikit-learn | 预测模型 |
| **代理** | NetworkShield | 22 节点熔断保护 |
| **监控** | Prometheus + Grafana | 指标采集与可视化 |

---

## 3. 系统架构

### 3.1 五阶段自动化流水线

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  L1         │    │  L2         │    │  L3         │    │  ELO        │    │  PREDICT    │
│  Discovery  │───▶│  Harvest    │───▶│  Smelt      │───▶│  Rating     │───▶│  Output     │
│  (赛程发现) │    │  (数据收割) │    │  (特征熔炼) │    │  (动态评分) │    │  (预测报告) │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     FotMob           FotMob Details     11维特征          K-Factor           EV 排序
     API              + Odds 辅助        (Elo+身价+H2H)    递归更新           TITAN 模型
                      22 代理节点                                               3-Model 共识
```

### 3.2 数据层级

| 层级 | 数据源 | 存储表 | 说明 |
|------|--------|--------|------|
| **L1** | FotMob API | `matches` | 比赛发现、基础信息 |
| **L2** | FotMob Details + OddsPortal | `raw_match_data`, `l2_match_data` | 赔率数据（开盘/收盘/1X2/亚洲盘） |
| **L3** | 特征工程 | `l3_features` | 11维纯净特征向量 |
| **ELO** | 历史比赛结果 | `team_elo_ratings` | 球队动态实力评分 |
| **预测** | XGBoost 模型 | `predictions` | 预测结果 + EV 计算 |

### 3.3 核心资产地图

| 功能模块 | 唯一指定文件 | 入口脚本 |
|----------|-------------|---------|
| **L1 Discovery** | `src/infrastructure/FixtureSeeder.js` | `npm run seed` |
| **L2 Harvest** | `src/infrastructure/harvesters/ProductionHarvester.js` | `npm start` |
| **Swarm Harvest** | `src/infrastructure/harvesters/SwarmEngine.js` | `npm run harvest:swarm` |
| **L3 Smelt** | `src/feature_engine/smelter/FeatureSmelter.js` | `npm run smelt` |
| **Sentinel** | `src/infrastructure/monitoring/Sentinel.js` | `npm run titan:watch` |
| **OddsFluxDetector** | `src/analysis/OddsFluxDetector.js` | V5.0 算法模块 |
| **身份管理** | `src/infrastructure/network/SessionManager.js` | - |
| **代理池** | `src/infrastructure/network/NetworkShield.js` | - |
| **TITAN 模型** | `src/ml/inference/predictor.py` | `npm run predict` |
| **统一配置** | `src/config_unified.py` | - |

---

## 4. 项目结构

```
FootballPrediction/
├── config/                      # 配置中心
│   ├── factory_config.js        # 工厂级配置（所有魔术数字归口）
│   ├── constants.js             # 业务常量
│   └── leagues.json             # 联赛配置
├── scripts/
│   ├── ops/                     # 运维脚本
│   │   ├── run_production.js    # 生产收割主入口
│   │   ├── seed_fixtures.js     # L1 赛程种子
│   │   ├── smelt_all.js         # L3 特征熔炼
│   │   ├── swarm_test.js        # Swarm 蜂群收割
│   │   ├── sentinel_watch.js    # 哨兵监控
│   │   ├── hyper_swarm.js       # 超 Swarm 引擎
│   │   ├── check_health.js      # 健康检查
│   │   ├── train_model.py       # 模型训练
│   │   ├── predict_pipeline.py  # 预测管道
│   │   └── titan_daily_ops.sh   # 一键运维脚本
│   └── maintenance/             # 维护工具
│       ├── integrity_guard.py   # 数据完整性守护
│       ├── recalculate_elo.js   # ELO 重新计算
│       └── check_system_health.py
├── src/
│   ├── core/                    # 核心基础设施（Math, Database, Types）
│   ├── parsers/                 # 数据解析器
│   ├── feature_engine/          # Node.js 特征引擎
│   ├── analysis/                # V5.0 分析算法（OddsFluxDetector）
│   ├── strategy/                # 策略模块（Kelly准则、Tuner）
│   ├── infrastructure/          # 基础设施（收割器、网络、数据库）
│   │   ├── harvesters/          # 收割引擎
│   │   ├── network/             # 网络与代理
│   │   ├── monitoring/          # 监控与哨兵
│   │   └── browser/             # 浏览器自动化
│   ├── ml/                      # 机器学习
│   │   ├── inference/           # 模型推理
│   │   ├── models/              # 模型定义
│   │   ├── data/                # 数据处理
│   │   └── feature_engine/      # Python 特征工程
│   ├── database/                # 数据库模型（唯一真理源）
│   ├── schemas/                 # Pydantic Schema
│   ├── services/                # 业务服务层
│   ├── config/                  # 配置模块
│   ├── constants/               # 常量定义
│   ├── api/                     # API 接口
│   ├── data/                    # 数据层
│   └── utils/                   # 工具函数
├── tests/                       # 测试文件
│   ├── unit/                    # 单元测试
│   ├── integration/             # 集成测试
│   └── fixtures/                # 测试数据
├── models/                      # 生产模型文件
│   └── titan_v4466_real_combat.joblib
├── docs/                        # 文档中心
├── CLAUDE.md                    # AI 助手详细操作指南
├── COMMAND_CENTER.md            # 数字化指挥中心
└── AGENTS.md                    # 本文件
```

---

## 5. 开发环境搭建

### 5.1 快速启动

```bash
# 1. 克隆项目
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 设置 DB_PASSWORD

# 3. 启动开发环境
docker-compose -f docker-compose.dev.yml up -d

# 4. 进入容器
docker-compose -f docker-compose.dev.yml exec dev bash

# 5. 运行生产收割
npm start
```

### 5.2 核心命令

| 命令 | 描述 |
|------|------|
| `npm start` | 生产收割器（L2/L3） |
| `npm run seed` | L1 赛程种子 |
| `npm run seed:all` | L1 全量赛程种子 |
| `npm run smelt` | L3 特征熔炼 |
| `npm run harvest:swarm` | Swarm 蜂群收割 |
| `npm run titan:start` | TITAN 完整工作流 |
| `npm run titan:watch` | 启动哨兵监控 |
| `npm run titan:check` | 健康检查 |
| `npm run predict` | 生成预测报告 |
| `npm run train` | 训练 TITAN 模型 |
| `npm test` | 运行单元测试 |
| `npm run qa` | 全量检查（lint + test） |

---

## 6. 工程铁律

### 6.1 五大核心规则

1. **沟通协议**：所有回复、注释、日志必须使用**中文**
2. **容器化优先**：**禁止**在宿主机直接运行 Node/Python，所有操作在 Docker 容器内执行
3. **分支管理**：严禁在 `main` 分支开发，分支命名：`feat/<功能>` / `lab/<实验>` / `fix/<修复>`
4. **数据完整性**：**零模拟原则**，严禁使用 `Math.random()` 伪造数据
5. **幂等性**：所有收割任务支持重复执行，已存在的完整数据应跳过

### 6.2 V4.51 架构规范

- **配置唯一源**: `src/config_unified.py` / `config/factory_config.js`
- **数学能力**: `src/core/math/` (finance, evaluator)
- **动态能力**: `src/core/` (Math, Database, Types)
- **预测大脑**: `src/ml/`
- **分析算法**: `src/analysis/` (V5.0 新增)
- **策略模块**: `src/strategy/` (Kelly准则等)
- **基础设施**: `src/infrastructure/`
- **唯一数据**: `src/database/`

### 6.3 黄金准则（V4.51.2+）

- **测试覆盖率**: 80% 熔断阈值
- **静态质量**: 0 Error 容忍
- **文档规范**: JSDoc 完整注释

---

## 7. 常用开发命令

### 7.1 开发环境管理

```bash
# 启动开发环境
docker-compose -f docker-compose.dev.yml up -d
make dev-up

# 进入开发容器
docker-compose -f docker-compose.dev.yml exec dev bash
make dev-shell

# 停止开发环境
docker-compose -f docker-compose.dev.yml down
make dev-down
```

### 7.2 核心收割流程

```bash
# L1: 赛程种子
docker-compose -f docker-compose.dev.yml exec dev npm run seed

# L2: 数据收割
docker-compose -f docker-compose.dev.yml exec dev npm start

# Swarm 蜂群收割（推荐，多 Worker 并发）
docker-compose -f docker-compose.dev.yml exec dev npm run harvest:swarm

# L3: 特征熔炼
docker-compose -f docker-compose.dev.yml exec dev npm run smelt

# TITAN 完整工作流（高阶）
npm run titan:start
```

### 7.3 代码质量

```bash
# ESLint 检查
npm run lint

# ESLint 自动修复
npm run lint:fix

# Prettier 格式化
npm run format

# Python Ruff 检查
npm run lint:python

# Python 格式化
npm run format:python

# Markdown 检查
npm run lint:md

# 全量检查
npm run qa
make verify
```

### 7.4 测试

```bash
# Node.js 单元测试
npm test
npm run test:unit

# 指定测试文件
npm run test:l1

# 集成测试
npm run test:integration

# 覆盖率测试
npm run test:coverage

# Python 测试
pytest tests/ -v
pytest tests/ml/ -v
```

### 7.5 数据库操作

```bash
# 进入 PostgreSQL Shell
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db
make db-shell

# 数据库备份
make db-backup

# 查看数据层级状态
npm run status:db
```

### 7.6 监控与运维

```bash
# 启动监控栈（Prometheus + Grafana）
npm run monitor:up

# 停止监控
npm run monitor:down

# 启动哨兵监控
npm run titan:watch

# 健康检查
npm run titan:check
npm run status:health
make health
```

### 7.7 模型操作

```bash
# 训练模型
npm run train

# 快速训练（参数减少）
npm run train:fast

# 深度训练（参数增加）
npm run train:deep

# 生成预测
npm run predict

# 试运行模式（不写入数据库）
npm run predict:dry

# JSON 格式输出
npm run predict:json
```

### 7.8 ELO 评分操作

```bash
# 重新计算 ELO（完整）
npm run elo:recalc

# 试运行模式
npm run elo:recalc:dry

# 增量更新
npm run elo:incremental
```

---

## 8. 关键配置

### 8.1 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_PASSWORD` | 数据库密码（**必填**） | - |
| `DB_HOST` | 数据库主机 | `host.docker.internal` |
| `DB_PORT` | 数据库端口 | `5432` |
| `DB_NAME` | 数据库名称 | `football_db` |
| `DB_USER` | 数据库用户 | `football_user` |
| `REDIS_HOST` | Redis 主机 | `host.docker.internal` |
| `REDIS_PORT` | Redis 端口 | `6379` |
| `MAX_WORKERS` | Worker 数量 | `1` |
| `MIN_DELAY_MS` | 最小延时（ms） | `10000` |
| `MAX_DELAY_MS` | 最大延时（ms） | `15000` |
| `PROXY_HOST` | 代理服务器地址 | `172.25.16.1` |
| `LOG_LEVEL` | 日志级别 | `info` |
| `SWARM_CONCURRENCY` | Swarm 并发数 | `3` |

### 8.2 配置系统

所有配置集中在 `config/factory_config.js` 和 `src/config_unified.py`，**严禁在业务代码中硬编码参数**。

```javascript
// Node.js 使用示例
const FactoryConfig = require('../../../config/factory_config');
const delay = FactoryConfig.getRandomDelay([FactoryConfig.TIMING.minDelayMs, FactoryConfig.TIMING.maxDelayMs]);
```

```python
# Python 使用示例
from src.config_unified import settings
from src.config_unified import DatabaseConfig
```

---

## 9. 故障排查

| 问题 | 诊断命令 | 解决方案 |
|------|---------|----------|
| **代理熔断** | `curl -x http://172.25.16.1:7890 https://httpbin.org/ip` | `docker-compose restart dev` |
| **数据库连接** | `docker-compose exec db pg_isready -U football_user` | `docker-compose restart db` |
| **浏览器崩溃** | `ps aux \| grep chromium` | `npx playwright install chromium --force` |
| **数据不一致** | `python scripts/maintenance/check_system_health.py` | 运行 `clean_corrupt_l2.py` |
| **Redis 连接** | `docker-compose exec redis redis-cli ping` | `docker-compose restart redis` |
| **Swarm 挂起** | `npm run titan:check` | 检查 `sentinel_watch.js` 日志 |

---

## 10. 数据库表结构

| 表名 | 用途 | 数据层级 |
|------|------|----------|
| `matches` | 比赛基础信息 | L1 |
| `raw_match_data` | L2 原始数据（JSONB 赔率） | L2 |
| `l2_match_data` | L2 结构化数据 | L2 |
| `l3_features` | 特征向量（11维纯净特征） | L3 |
| `predictions` | 预测结果 | - |
| `team_elo_ratings` | 球队 Elo 评分 | - |

**常用查询：**

```sql
-- 查看待收割比赛
SELECT match_id, home_team, away_team, match_time
FROM matches
WHERE l2_harvested = false;

-- 查看高置信度预测
SELECT * FROM predictions
WHERE final_confidence > 0.65
ORDER BY match_time;

-- 查看数据层级统计
SELECT
    COUNT(*) FILTER (WHERE l2_harvested = false) as pending_l2,
    COUNT(*) FILTER (WHERE l2_harvested = true) as completed_l2
FROM matches
WHERE match_date >= NOW()
  AND match_date < NOW() + INTERVAL '4 days';
```

---

## 11. TITAN 模型系统

### 11.1 模型架构

| 组件 | 描述 |
|------|------|
| **核心模型** | XGBoost 分类器 |
| **特征维度** | 11维纯净特征（Elo + 身价 + H2H） |
| **准确率** | 65.31%（测试集）/ 67.94%（5折交叉验证） |
| **F1 Score** | 0.6371 |
| **Log Loss** | 0.9834 |

### 11.2 11维特征组成

| 类别 | 特征 | 说明 |
|------|------|------|
| **Elo特征 (5维)** | `home_elo_pre`, `away_elo_pre`, `elo_diff`, `expected_home_win`, `expected_away_win` | 球队实力核心指标 |
| **身价特征 (3维)** | `log_home_squad_value`, `log_away_squad_value`, `home_mv_share` | 阵容价值量化 |
| **H2H特征 (3维)** | `h2h_home_win_ratio`, `h2h_draw_ratio`, `h2h_avg_goal_diff` | 历史对战优势 |

### 11.3 特征重要性

| 排名 | 特征 | 重要性 |
|------|------|--------|
| 1 | elo_diff | 64.66% |
| 2 | away_score | 14.27% |
| 3 | home_score | 13.72% |
| 4 | total_goals | 7.36% |

### 11.4 EV 计算算法

```
EV = P × Odds - 1

# 无赔率时的保守估算
if p > 0.70:    ev = min(0.10, theoretical_ev + 0.05)
elif p > 0.60:  ev = min(0.05, theoretical_ev + 0.02)
elif p > 0.50:  ev = min(0.03, theoretical_ev)
elif p > 0.40:  ev = max(-0.05, theoretical_ev - 0.02)
else:           ev = max(-0.10, theoretical_ev - 0.05)
```

---

## 12. V5.0 新功能

### 12.1 OddsFluxDetector - 赔率背离监测器

**文件**: `src/analysis/OddsFluxDetector.js`

TITAN V5.0 首个预测算法模块，用于实时监测赔率异常波动和市场背离信号。

**核心功能**:
- 赔率偏差检测（deviation detection）
- 市场信号分析（market signals）
- 凯利准则建议（Kelly criterion）
- 价值投注识别（value bets）

**使用示例**:
```javascript
const { OddsFluxDetector } = require('./src/analysis/OddsFluxDetector');

const detector = new OddsFluxDetector({
  deviationThreshold: 0.15,  // 偏差阈值 15%
  minOdds: 1.5,
  maxOdds: 10.0
});

const result = detector.analyze({
  modelProbability: 0.65,
  marketOdds: 2.1,
  homeTeam: '曼城',
  awayTeam: '利物浦'
});
```

---

## 13. 相关文档

| 文档 | 说明 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | AI 助手操作指南（工程铁律、配置系统、关键规则） |
| [COMMAND_CENTER.md](./COMMAND_CENTER.md) | 数字化指挥中心（完整命令、作战常规） |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 系统架构详述 |
| [docs/OPERATIONS_MANUAL.md](./docs/OPERATIONS_MANUAL.md) | 运维手册 |
| [docs/TESTING_GUIDE.md](./docs/TESTING_GUIDE.md) | 测试指南 |
| [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) | 故障排查 |
| [docs/xgboost_optimization_guide.md](./docs/xgboost_optimization_guide.md) | XGBoost 优化指南 |
| [docs/MODEL_V4_ANATOMY.md](./docs/MODEL_V4_ANATOMY.md) | V4 模型解剖学报告（11维特征详解） |
| [AUDIT_REPORT_V3.2.md](./AUDIT_REPORT_V3.2.md) | V3.1-STABLE 穿透审计报告 |

---

## 14. 助手行为准则

### 14.1 代码修改原则

1. **先读后改**：从不修改未读过的代码
2. **最小变更**：只做必要的修改，不过度重构
3. **测试验证**：修改后运行相关测试
4. **中文优先**：所有注释、日志使用中文

### 14.2 安全守则

1. **绝不引入**：XSS、SQL 注入、命令注入等安全漏洞
2. **边界校验**：只在系统边界（用户输入、外部 API）做验证
3. **信任内部**：信任内部代码和框架保证

### 14.3 禁止行为

- 不在 `main` 分支直接开发
- 不在宿主机直接运行 Node/Python
- 不使用 `Math.random()` 伪造数据
- 不创建不必要的抽象和工具函数
- 不添加未请求的功能
- 不硬编码配置参数

### 14.4 Skills 约束体系

项目已配置 12 个专用 Skills，详见 `.claude/README.md`。核心约束：

| 约束等级 | Skill | 用途 |
|----------|-------|------|
| 🔴 RED | `minimal_change` | 最小修改策略 |
| 🔴 RED | `architecture_boundary` | 架构边界保护 |
| 🔴 RED | `test_guard` | 测试质量保护 |
| 🔴 RED | `context_lock` | 核心模块冻结 |
| 🔴 RED | `change_impact` | 变更影响分析 |

---

## 15. MCP 服务器权限

| MCP 服务器 | 权限 | 允许行为 |
|-----------|------|----------|
| **postgres** | READ-ONLY | SELECT / DESCRIBE / EXPLAIN |
| **filesystem** | PROJECT ROOT | 读 / diff / 受控写 |
| **git** | READ-ONLY | commit history / diff / blame |
| **pytest** | RESTRICTED | 运行 pytest / 列出测试 |

> ⚠️ **MCP 不拥有生产环境控制权**，禁止任何不可逆或高风险自动化操作。

---

**维护者**: V174 Engineering Team  
**许可证**: MIT License  
**最后更新**: 2026-03-13