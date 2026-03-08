# FootballPrediction - AI 助手指令上下文

> **系统版本**: V4.45-stable | **最后更新**: 2026-03-08
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
| **L2 Harvest** | OddsPortal + 22 节点代理池 | 赔率数据采集（开盘/收盘/亚洲盘） |
| **L3 Smelt** | FeatureSmelter | 12061 维特征向量 |
| **ML Prediction** | XGBoost 3-Model Consensus | 67.2% 准确率，<100ms 响应 |

### 1.3 质量认证

- **零模拟数据**：所有数据来自真实 API
- **幂等收割**：支持重复执行，自动跳过已完成
- **架构纯净**：无冗余模块，无废弃代码

---

## 2. 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **运行时** | Node.js 18+ / Python 3.11+ | 双语言架构 |
| **数据库** | PostgreSQL 15 | 数据存储 |
| **缓存** | Redis | 分布式锁/缓存 |
| **容器化** | Docker / docker-compose | 环境隔离 |
| **浏览器** | Playwright | 页面自动化 |
| **模糊匹配** | RapidFuzz (C++) | 队名匹配 |
| **ML** | XGBoost 2.0+ | 预测模型 |
| **代理** | NetworkShield | 22 节点熔断保护 |

---

## 3. 系统架构

### 3.1 四层流水线架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  L1 Discovery   │───▶│  C++ Fuzzy      │───▶│  L2/L3 Harvest  │───▶│  ML Prediction  │
│  (Node.js)      │    │  Bridge (Python)│    │  (Node.js)      │    │  (Python)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 3.2 数据层级

| 层级 | 数据源 | 存储表 | 说明 |
|------|--------|--------|------|
| **L1** | FotMob API | `matches` | 比赛发现、基础信息 |
| **L2** | FotMob Details + OddsPortal | `raw_match_data`, `l2_match_data` | 赔率数据（开盘/收盘/1X2/亚洲盘） |
| **L3** | 特征工程 | `l3_features` | 12061 维特征向量 |
| **预测** | XGBoost 模型 | `predictions` | 预测结果 + EV 计算 |

### 3.3 核心资产地图

| 功能模块 | 唯一指定文件 | 入口脚本 |
|----------|-------------|---------|
| **L1 Discovery** | `src/infrastructure/FixtureSeeder.js` | `scripts/ops/seed_fixtures.js` |
| **L2 Harvest** | `src/infrastructure/harvesters/ProductionHarvester.js` | `scripts/ops/run_production.js` |
| **L3 Smelt** | `src/feature_engine/smelter/FeatureSmelter.js` | `scripts/ops/smelt_all.js` |
| **身份管理** | `src/infrastructure/network/SessionManager.js` | - |
| **代理池** | `src/infrastructure/network/NetworkShield.js` | - |
| **C++ 桥接** | `src/utils/cpp_bridge_radar.py` | - |

---

## 4. 项目结构

```
FootballPrediction/
├── config/                      # 配置中心
│   └── factory_config.js        # 工厂级配置（所有魔术数字归口）
├── scripts/
│   ├── ops/                     # 运维脚本
│   │   ├── run_production.js    # 生产收割主入口
│   │   ├── seed_fixtures.js     # L1 赛程种子
│   │   └── smelt_all.js         # L3 特征熔炼
│   └── maintenance/             # 维护工具
├── src/
│   ├── core/                    # 核心基础设施
│   ├── parsers/                 # 数据解析器
│   ├── feature_engine/          # Node.js 特征引擎
│   ├── infrastructure/          # 基础设施（收割器、网络、数据库）
│   ├── ml/                      # 机器学习
│   │   ├── inference/           # 模型推理
│   │   ├── training/            # 模型训练
│   │   └── backtest/            # 回测引擎
│   └── utils/                   # 工具函数
├── tests/                       # 测试文件
├── CLAUDE.md                    # AI 助手指南（详细命令）
├── COMMAND_CENTER.md            # 指挥中心（完整命令）
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
| `npm run smelt` | L3 特征熔炼 |
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

### 6.2 V4.45 架构规范

- **配置唯一源**: `src/config_unified.py`
- **数学能力**: `src/core/math/` (finance, evaluator)
- **动态能力**: `src/core/` (Math, Database, Types)
- **预测大脑**: `src/ml/`
- **基础设施**: `src/infrastructure/`

---

## 7. 常用开发命令

### 7.1 开发环境管理

```bash
# 启动开发环境
docker-compose -f docker-compose.dev.yml up -d

# 进入开发容器
docker-compose -f docker-compose.dev.yml exec dev bash

# 停止开发环境
docker-compose -f docker-compose.dev.yml down
```

### 7.2 核心收割流程

```bash
# L1: 赛程种子
docker-compose -f docker-compose.dev.yml exec dev npm run seed

# L2: 数据收割
docker-compose -f docker-compose.dev.yml exec dev npm start

# L3: 特征熔炼
docker-compose -f docker-compose.dev.yml exec dev npm run smelt
```

### 7.3 代码质量

```bash
# ESLint 检查
docker-compose -f docker-compose.dev.yml exec dev npm run lint

# ESLint 自动修复
docker-compose -f docker-compose.dev.yml exec dev npm run lint:fix

# Prettier 格式化
docker-compose -f docker-compose.dev.yml exec dev npm run format

# Python Ruff 检查
docker-compose -f docker-compose.dev.yml exec dev npm run lint:python

# 全量检查
docker-compose -f docker-compose.dev.yml exec dev npm run qa
```

### 7.4 测试

```bash
# Node.js 测试
docker-compose -f docker-compose.dev.yml exec dev npm test
docker-compose -f docker-compose.dev.yml exec dev npm run test:coverage

# Python 测试
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ -v
docker-compose -f docker-compose.dev.yml exec dev pytest tests/ml/ -v
```

### 7.5 数据库操作

```bash
# 进入 PostgreSQL Shell
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db

# Makefile 快捷方式
make db-shell
make db-backup
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
| `MAX_WORKERS` | Worker 数量 | `1` |
| `MIN_DELAY_MS` | 最小延时（ms） | `10000` |
| `MAX_DELAY_MS` | 最大延时（ms） | `15000` |
| `PROXY_HOST` | 代理服务器地址 | `172.25.16.1` |
| `LOG_LEVEL` | 日志级别 | `info` |

### 8.2 配置系统

所有配置集中在 `config/factory_config.js`，**严禁在业务代码中硬编码参数**。

```javascript
// 使用示例
const FactoryConfig = require('../../../config/factory_config');
const delay = FactoryConfig.getRandomDelay([FactoryConfig.TIMING.minDelayMs, FactoryConfig.TIMING.maxDelayMs]);
```

---

## 9. 故障排查

| 问题 | 诊断命令 | 解决方案 |
|------|---------|----------|
| **代理熔断** | `curl -x http://172.25.16.1:7891 https://httpbin.org/ip` | `docker-compose restart dev` |
| **数据库连接** | `docker-compose exec db pg_isready -U football_user` | `docker-compose restart db` |
| **浏览器崩溃** | `ps aux \| grep chromium` | `npx playwright install chromium --force` |
| **数据不一致** | `python scripts/maintenance/check_system_health.py` | 运行 `clean_corrupt_l2.py` |

---

## 10. 数据库表结构

| 表名 | 用途 | 数据层级 |
|------|------|----------|
| `matches` | 比赛基础信息 | L1 |
| `raw_match_data` | L2 原始数据（JSONB 赔率） | L2 |
| `l2_match_data` | L2 结构化数据 | L2 |
| `l3_features` | 特征向量（12061 维） | L3 |
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
```

---

## 11. 多模型共识

| 模型 | 特征维度 | 用途 |
|------|---------|------|
| Model A | 37 | 通用预测 |
| Model B | 6000+ | 联赛专项 |
| Model C | 19 | 赔率模型 |

**共识规则**: UNANIMOUS (3/3) > MAJORITY (2/3) > SPLIT（无共识）

---

## 12. 相关文档

| 文档 | 说明 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | AI 助手操作指南（工程铁律、配置系统、关键规则） |
| [COMMAND_CENTER.md](./COMMAND_CENTER.md) | 完整命令列表、环境变量、故障排查 |
| [AUDIT_REPORT_V3.2.md](./AUDIT_REPORT_V3.2.md) | V3.1-STABLE 穿透审计报告 |

---

## 13. 助手行为准则

### 13.1 代码修改原则

1. **先读后改**：从不修改未读过的代码
2. **最小变更**：只做必要的修改，不过度重构
3. **测试验证**：修改后运行相关测试
4. **中文优先**：所有注释、日志使用中文

### 13.2 安全守则

1. **绝不引入**：XSS、SQL 注入、命令注入等安全漏洞
2. **边界校验**：只在系统边界（用户输入、外部 API）做验证
3. **信任内部**：信任内部代码和框架保证

### 13.3 禁止行为

- 不在 `main` 分支直接开发
- 不在宿主机直接运行 Node/Python
- 不使用 `Math.random()` 伪造数据
- 不创建不必要的抽象和工具函数
- 不添加未请求的功能

---

**维护者**: V174 Engineering Team  
**许可证**: MIT License  
**最后更新**: 2026-03-08
