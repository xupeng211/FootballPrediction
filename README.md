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
| **单元测试** | Jest | 43+ Pass | `npm test` |
| **代码覆盖** | Jest | 80%+ | `npm run test:coverage` |
| **文档规范** | JSDoc | Required | `npm run lint` |
| **代码格式** | Prettier | Enforced | `npm run format:check` |

### Pre-Commit Hook

所有提交必须通过本地质检门禁：

```bash
# .git/hooks/pre-commit 自动执行：
1. ESLint 检查 (src/, scripts/)
2. Jest 单元测试 (43+ tests)
3. 覆盖率验证 (≥80%)
```

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
npm run test          # 单元测试
npm run test:coverage # 覆盖率报告
npm run format:check  # 格式检查
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
├── docs/                      # 文档中心
├── data/                      # 数据存储
└── models/                    # ML模型仓库
```

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
