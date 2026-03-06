# FootballPrediction V3.0-PRO

> **工业级足球预测平台** - XGBoost 3-Model Consensus + 12061 维特征

[![Version](https://img.shields.io/badge/version-3.0.0--PRO-blue.svg)](https://github.com/xupeng211/FootballPrediction)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Node](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen.svg)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Audit](https://img.shields.io/badge/audit-V3.1--STABLE-brightgreen.svg)](AUDIT_REPORT_V3.2.md)

---

## 项目简介

FootballPrediction 是一个**工业级足球预测平台**，采用双语言 (Node.js + Python) 四层架构，通过多源数据采集、C++ 模糊匹配和 XGBoost 多模型共识，实现高精度的比赛预测。

### 核心能力

| 模块 | 技术实现 | 说明 |
|------|----------|------|
| **L1 Discovery** | FotMob API | 自动发现未来 7 天比赛 |
| **L2 Harvest** | OddsPortal + 22 节点代理池 | 赔率数据采集 (开盘/收盘/亚洲盘) |
| **L3 Smelt** | FeatureSmelter | 12061 维特征向量 |
| **ML Prediction** | XGBoost 3-Model Consensus | 67.2% 准确率, <100ms 响应 |

### 质量认证

> **本项目通过 V3.1-STABLE 穿透审计** - 详见 [AUDIT_REPORT_V3.2.md](./AUDIT_REPORT_V3.2.md)

- 零模拟数据：所有数据来自真实 API
- 幂等收割：支持重复执行，自动跳过已完成
- 架构纯净：无冗余模块，无废弃代码

---

## 快速启动

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

### 核心命令

| 命令 | 描述 |
|------|------|
| `npm start` | 生产收割器 (L2/L3) |
| `npm run seed` | L1 赛程种子 |
| `npm run smelt` | L3 特征熔炼 |
| `npm test` | 运行单元测试 |
| `npm run qa` | 全量检查 (lint + test) |

> **完整命令列表请参考 [COMMAND_CENTER.md](./COMMAND_CENTER.md)**

---

## 技术栈

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

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  L1 Discovery   │───▶│  C++ Fuzzy      │───▶│  L2/L3 Harvest  │───▶│  ML Prediction  │
│  (Node.js)      │    │  Bridge (Python)│    │  (Node.js)      │    │  (Python)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
        │                      │                      │                      │
        ▼                      ▼                      ▼                      ▼
    matches 表            URL 匹配             l2_match_data            predictions
                                               l3_features
```

### 数据层级

| 层级 | 数据源 | 存储表 | 说明 |
|------|--------|--------|------|
| **L1** | FotMob API | `matches` | 比赛发现、基础信息 |
| **L2** | OddsPortal | `l2_match_data` | 赔率数据 (开盘/收盘/1X2/亚洲盘) |
| **L3** | 特征工程 | `l3_features` | 12061 维特征向量 |

---

## 项目结构

```
FootballPrediction/
├── config/                      # 配置中心
│   └── factory_config.js        # 工厂级配置 (所有魔术数字归口)
├── scripts/
│   ├── ops/                     # 运维脚本
│   │   ├── run_production.js    # 生产收割主入口
│   │   ├── seed_fixtures.js     # L1 赛程种子
│   │   └── smelt_all.js         # L3 特征熔炼
│   ├── maintenance/             # 维护工具
│   └── tools/                   # 诊断工具
├── src/
│   ├── infrastructure/          # 基础设施
│   │   ├── harvesters/          # ProductionHarvester (V186)
│   │   ├── network/             # NetworkShield + SessionManager
│   │   └── database/            # PostgresClient
│   ├── feature_engine/          # Node.js 特征引擎
│   │   ├── smelter/             # FeatureSmelter
│   │   └── extractors/          # GoldenFeature, EloRating, etc.
│   ├── ml/                      # 机器学习
│   │   ├── inference/           # 预测器 + 多模型验证
│   │   ├── training/            # 模型训练
│   │   └── backtest/            # 回测引擎
│   └── utils/                   # 工具函数
│       └── cpp_bridge_radar.py  # C++ 模糊匹配桥接
├── tests/                       # 测试文件
├── CLAUDE.md                    # AI 助手指南 (详细命令)
├── COMMAND_CENTER.md            # 指挥中心 (完整命令)
└── AUDIT_REPORT_V3.2.md         # 穿透审计报告
```

---

## 故障排查

| 问题 | 诊断命令 | 解决方案 |
|------|---------|---------|
| **代理熔断** | `curl -x http://172.25.16.1:7891 https://httpbin.org/ip` | `docker-compose restart dev` |
| **数据库连接** | `docker-compose exec db pg_isready` | `docker-compose restart db` |
| **浏览器崩溃** | `ps aux \| grep chromium` | `npx playwright install chromium --force` |
| **数据不一致** | `python scripts/maintenance/check_system_health.py` | 运行 `clean_corrupt_l2.py` |

---

## 文档

| 文档 | 说明 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | AI 助手操作指南 (工程铁律、配置系统、关键规则) |
| [COMMAND_CENTER.md](./COMMAND_CENTER.md) | 完整命令列表、环境变量、故障排查 |
| [AUDIT_REPORT_V3.2.md](./AUDIT_REPORT_V3.2.md) | V3.1-STABLE 穿透审计报告 |

---

## 许可证

[MIT License](LICENSE)

---

<p align="center">
  V3.0-PRO Truth Edition | Enterprise Logging + Database Integrity Verified
</p>
