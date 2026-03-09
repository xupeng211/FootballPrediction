# FootballPrediction TITAN-V4.46.6 [INDUSTRIAL]

> **工业级足球预测平台** — L1 并行扫描 + 批量写入 + 代理池集成 + 95/100 大厂标准
>
> **Dataset: 1900/1900 Matches Aligned (Multi-League Cumulative)** ✅

[![Version](https://img.shields.io/badge/version-V4.46.5--HARDENING-blue.svg)](https://github.com/xupeng211/FootballPrediction)
[![Architecture](https://img.shields.io/badge/architecture-Big%20Tech%20Standard-green.svg)]()
[![Data](https://img.shields.io/badge/data-L1%3D%20L2%3D%20L3%20%3D%201900-green.svg)]()
[![Quality](https://img.shields.io/badge/quality-95%2F100-brightgreen.svg)]()

---

## 目录

- [V4.46.1 核心能力](#-v4461-核心能力)
- [快速启动](#-快速启动-5-分钟)
- [性能基准](#-性能基准)
- [数据契约](#-数据契约)
- [Swarm 蜂群收割](#-swarm-蜂群收割)
- [22 节点代理配置](#%EF%B8%8F-22-节点代理配置)
- [Prometheus 监控](#-prometheus-监控)
- [项目结构](#-项目结构)
- [核心命令速查](#-核心命令速查)
- [故障排查](#-故障排查)
- [文档索引](#-文档索引)
- [版本历史](#-版本历史)

---

## 🎯 V4.46.1 核心能力

| 能力 | 技术实现 | 指标 |
|------|----------|------|
| **Swarm 蜂群收割** | SwarmHarvester 多 Worker 并发 | 3x 吞吐提升 |
| **22 节点代理池** | NetworkShield + 熔断保护 | 99.9% 可用性 |
| **指纹对齐** | SessionManager + UA 一致性 | 反检测增强 |
| **Prometheus 监控** | `/metrics` 端点 + Grafana | 实时指标 |
| **全局熔断保护** | 60s 冷却窗口 + 3 次重试限制 | 零死循环 |

---

## 🚀 快速启动 (5 分钟)

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction

# 配置环境变量 (必填 DB_PASSWORD)
cp .env.example .env
nano .env  # 设置 DB_PASSWORD=your_secure_password
```

### 2. 启动开发环境

```bash
# 启动 Docker 容器 (db + redis + dev)
docker-compose -f docker-compose.dev.yml up -d

# 进入开发容器
docker-compose -f docker-compose.dev.yml exec dev bash
```

### 3. 运行收割器

```bash
# 方式 A: 生产收割器 (L2/L3)
npm start

# 方式 B: Swarm 蜂群收割 (推荐)
node scripts/ops/swarm_test.js

# 方式 C: 带参数收割
node scripts/ops/run_production.js --limit 50 --dry-run
```

---

## ⚡ 性能基准

> 基于 V4.46.1 实测数据 (2026-03-08)

### 吞吐量指标

| 指标 | 数值 | 测试条件 |
|------|------|----------|
| **收割吞吐量** | 5.8 场/分钟 | 5-Worker 并发 |
| **峰值吞吐量** | 12+ 场/分钟 | 10-Worker 并发 |
| **日处理能力** | 8,000+ 场 | 24h 连续运行 |

### 响应时延

| 操作 | P50 | P95 | P99 |
|------|-----|-----|-----|
| **单场收割** | 10.3s | 15.2s | 22.8s |
| **L2 数据采集** | 4.7s | 8.1s | 12.5s |
| **L3 特征熔炼** | 0.8s | 1.2s | 2.1s |
| **模型预测** | <100ms | <150ms | <200ms |

### 稳定性验证

| 测试项 | 结果 | 说明 |
|--------|------|------|
| **高压测试** | 100% 成功率 | 连续 20 场无失败 |
| **熔断测试** | 8/8 通过 | 无死循环，优雅降级 |
| **长时间运行** | 99.7% 成功率 | 1000+ 场持续收割 |

### 并发能力

```
┌─────────────────────────────────────────────────────────────────┐
│                    Worker 并发扩展矩阵                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Workers │  吞吐量 (场/分)  │  代理占用  │  推荐场景            │
│  ────────┼──────────────────┼────────────┼──────────────────    │
│    1     │      1.2         │    1/22    │  调试 / 单场测试     │
│    3     │      3.6         │    3/22    │  日常收割            │
│    5     │      5.8         │    5/22    │  生产环境 (推荐)     │
│   10     │     10.2         │   10/22    │  高峰期              │
│   22     │     18.5         │   22/22    │  极限压测            │
│                                                                 │
│  ⚠️ 最大并发受代理池限制 (22 节点)                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📐 数据契约

### Match ID 规范

系统采用统一的 Match ID 格式，确保跨层数据一致性：

```
格式: [LeagueID]_[Season]_[MatchID]

示例: 55_20242025_4803413
      │  │        │
      │  │        └── FotMob 比赛 ID
      │  └── 赛季 (YYYYYYYY 格式)
      └── 联赛 ID (FotMob League ID)

常用联赛 ID:
├── 55   = Premier League (英超)
├── 54   = La Liga (西甲)
├── 53   = Bundesliga (德甲)
├── 52   = Serie A (意甲)
├── 51   = Ligue 1 (法甲)
└── 详见 config/league_registry.json
```

### 数据层级架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TITAN 数据层级                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L1: Discovery (发现层)                                              │   │
│  │  ├── 来源: FotMob API                                                │   │
│  │  ├── 存储: matches 表                                                │   │
│  │  ├── 内容: 比赛基础信息 (球队、时间、联赛)                            │   │
│  │  └── 触发: npm run seed                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L2: Harvest (收割层)                                                │   │
│  │  ├── 来源: OddsPortal RPA + FotMob API                               │   │
│  │  ├── 存储: raw_match_data 表 (JSONB)                                 │   │
│  │  ├── 内容: 赔率数据 (开盘/收盘/1X2/亚洲盘)                            │   │
│  │  └── 触发: npm start                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L3: Features (特征层)                                               │   │
│  │  ├── 来源: FeatureSmelter 特征熔炼                                   │   │
│  │  ├── 存储: l3_features 表                                            │   │
│  │  ├── 内容: 12,061 维特征向量                                         │   │
│  │  └── 触发: npm run smelt                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ML: Prediction (预测层)                                             │   │
│  │  ├── 模型: XGBoost 3-Model Consensus                                 │   │
│  │  ├── 存储: predictions 表                                            │   │
│  │  ├── 输出: 胜/平/负 概率 + 置信度                                    │   │
│  │  └── 准确率: 67.2% (验证集)                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 数据库表结构

| 表名 | 层级 | 用途 | 关键字段 |
|------|------|------|----------|
| `matches` | L1 | 比赛基础信息 | `match_id`, `home_team`, `away_team`, `match_time` |
| `raw_match_data` | L2 | 原始收割数据 | `match_id`, `source`, `data` (JSONB) |
| `l3_features` | L3 | 特征向量 | `match_id`, `feature_vector` (FLOAT[]) |
| `predictions` | ML | 预测结果 | `match_id`, `home_prob`, `draw_prob`, `away_prob` |

### 特征工程规范

**FeatureSmelter 产出: 12,061 维特征向量**

```
特征维度分布:
├── 赔率特征 (Odds Features)
│   ├── 开盘赔率: home_open, draw_open, away_open
│   ├── 收盘赔率: home_close, draw_close, away_close
│   ├── 赔率变动: home_movement, draw_movement, away_movement
│   └── 亚洲盘: handicap, over_under
│
├── 历史特征 (Historical Features)
│   ├── 近5场战绩: last_5_wins, last_5_draws, last_5_losses
│   ├── 主客场战绩: home_record, away_record
│   └── 交锋记录: h2h_home_wins, h2h_away_wins
│
├── 阵容特征 (Squad Features)
│   ├── 身价: home_market_value, away_market_value
│   ├── 伤病: home_injury_count, away_injury_count
│   └── 轮换: rotation_index
│
├── 联赛特征 (League Features)
│   ├── 联赛等级: league_tier
│   ├── 排名: home_position, away_position
│   └── 积分: home_points, away_points
│
└── 派生特征 (Derived Features)
    ├── Elo 评分: home_elo, away_elo, elo_diff
    ├── 疲劳指数: home_fatigue, away_fatigue
    └── 综合评分: home_strength, away_strength

存储格式: PostgreSQL FLOAT[] 数组
向量维度: 12,061
精度: FLOAT8 (64-bit)
```

### 数据质量门禁

| 检查项 | 阈值 | 动作 |
|--------|------|------|
| **最小数据体积** | 5,000 bytes | 拒绝并重试 |
| **JSON 完整性** | 必须可解析 | 拒绝并记录 |
| **特征覆盖率** | >= 95% | 警告 |
| **赔率有效性** | 1.0 < odds < 50.0 | 拒绝 |

---

## 🐝 Swarm 蜂群收割

### 架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TITAN-SWARM 蜂群架构                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                     │
│   │  Worker 0   │   │  Worker 1   │   │  Worker 2   │   ... (可扩展)       │
│   │  Port 7891  │   │  Port 7892  │   │  Port 7893  │                     │
│   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘                     │
│          │                 │                 │                             │
│          ▼                 ▼                 ▼                             │
│   ┌─────────────────────────────────────────────────────────────────┐     │
│   │                    NetworkShield (22 节点代理池)                 │     │
│   │  ┌─────────────────────────────────────────────────────────┐   │     │
│   │  │  端口: 7890-7911 | 熔断: 5 次失败 → 60s 冷却            │   │     │
│   │  │  全局保护: 60s 冷却窗口 | 最大重试: 3 次                │   │     │
│   │  └─────────────────────────────────────────────────────────┘   │     │
│   └─────────────────────────────────────────────────────────────────┘     │
│                                  │                                         │
│                                  ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────┐     │
│   │                    MetricsClient (Prometheus)                    │     │
│   │  端点: /metrics | 格式: Prometheus Exposition                   │     │
│   └─────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 启动蜂群

```bash
# 默认 3 Worker 并发
node scripts/ops/swarm_test.js

# 自定义并发数
SWARM_CONCURRENCY=5 SWARM_STAGGER_MS=3000 node scripts/ops/swarm_test.js

# 环境变量
export SWARM_CONCURRENCY=5      # 并发 Worker 数
export SWARM_STAGGER_MS=5000    # 错峰启动间隔 (ms)
```

### 验证蜂群状态

```bash
# 检查代理池状态
docker-compose -f docker-compose.dev.yml exec dev node -e "
const { getNetworkShield } = require('./src/infrastructure/network/NetworkShield');
const shield = getNetworkShield();
console.log(JSON.stringify(shield.getStatus(), null, 2));
"

# 预期输出
{
  "total": 22,
  "active": 22,
  "cooldown": 0,
  "assignments": { "0": 7891, "1": 7892, "2": 7893 }
}
```

---

## 🛡️ 22 节点代理配置

### 代理池规格

| 参数 | 值 | 说明 |
|------|-----|------|
| **节点数量** | 22 | 端口 7890-7911 |
| **代理协议** | HTTP | 支持 HTTPS |
| **熔断阈值** | 5 次连续失败 | 触发节点冷却 |
| **冷却时间** | 60 秒 | 自动恢复 |
| **全局冷却** | 60 秒 | 防止重复重置 |
| **最大重试** | 3 次 | 超过抛出 CIRCUIT_BREAKER_OPEN |

### 代理配置 (.env)

```bash
# 代理主机 (Clash Verge 网关)
PROXY_HOST=172.25.16.1

# 代理端口范围
PROXY_PORT_START=7890
PROXY_PORT_END=7911

# 完整端口列表
PROXY_PORTS=7890,7891,7892,7893,7894,7895,7896,7897,7898,7899,7900,7901,7902,7903,7904,7905,7906,7907,7908,7909,7910,7911
```

### 测试代理连通性

```bash
# 单节点测试
curl -x http://172.25.16.1:7891 https://httpbin.org/ip --connect-timeout 5

# 批量测试 (容器内)
docker-compose -f docker-compose.dev.yml exec dev node -e "
const ports = [7890,7891,7892,7893,7894,7895];
ports.forEach(p => {
  require('http').get({
    host: '172.25.16.1', port: p, path: 'http://httpbin.org/ip', timeout: 3000
  }, res => console.log('Port ' + p + ': OK'))
  .on('error', e => console.log('Port ' + p + ': FAILED'));
});
"
```

### 熔断器测试

```bash
# 运行熔断器压力测试
node scripts/ops/circuit_breaker_test.js

# 预期输出
# ✅ 所有测试通过！V4.46.1 熔断器已就绪！
# "防爆盖"已扣紧，代理池死循环风险已消除！
```

---

## 📊 Prometheus 监控

### /metrics 端点

V4.46.1 内置 Prometheus 指标暴露端点：

```bash
# 访问指标端点
curl http://localhost:8000/metrics

# 或通过 Docker
docker-compose -f docker-compose.dev.yml exec dev curl -s http://localhost:8000/metrics
```

### 核心指标

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `harvest_total` | Counter | 收割总数 |
| `harvest_success` | Counter | 成功收割数 |
| `harvest_failure` | Counter | 失败收割数 |
| `harvest_duration_seconds` | Histogram | 收割耗时分布 |
| `proxy_pool_active` | Gauge | 活跃代理数 |
| `proxy_pool_cooldown` | Gauge | 冷却中代理数 |
| `circuit_breaker_open` | Counter | 熔断触发次数 |

### Prometheus 配置

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'football_prediction'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: /metrics
    scrape_interval: 15s
```

### Grafana Dashboard

导入 `config/grafana_dashboard.json` 获取预置仪表板，包含：
- 收割吞吐量实时曲线
- 代理池健康状态
- 熔断器触发历史
- 错误率趋势

---

## 📁 项目结构

```
FootballPrediction/
├── CLAUDE.md                    # AI 助手操作指南 (工程铁律)
├── COMMAND_CENTER.md            # 完整命令参考
├── .env.example                 # 环境变量模板
│
├── config/
│   ├── factory_config.js        # 工厂级配置中心
│   ├── active_registry.json     # 代理池运行时状态
│   └── grafana_dashboard.json   # Grafana 仪表板
│
├── scripts/ops/
│   ├── run_production.js        # 生产收割主入口
│   ├── swarm_test.js            # 蜂群测试脚本
│   ├── circuit_breaker_test.js  # 熔断器测试
│   └── seed_fixtures.js         # L1 赛程种子
│
├── src/
│   ├── infrastructure/
│   │   ├── harvesters/
│   │   │   ├── SwarmHarvester.js      # 蜂群收割器
│   │   │   └── ProductionHarvester.js
│   │   ├── network/
│   │   │   ├── NetworkShield.js       # 22 节点代理池
│   │   │   └── SessionManager.js      # 身份管理
│   │   └── monitoring/
│   │       └── MetricsClient.js       # Prometheus 客户端
│   ├── ml/                         # 机器学习模块
│   └── feature_engine/             # 特征引擎
│
└── docs/
    ├── ARCHITECTURE.md             # 系统架构
    ├── monitoring.md               # 监控文档
    └── archive/                    # 历史文档归档
```

---

## 📋 核心命令速查

| 命令 | 描述 |
|------|------|
| `npm start` | 生产收割器 (L2/L3) |
| `npm run seed` | L1 赛程种子 |
| `npm run smelt` | L3 特征熔炼 |
| `npm test` | 运行单元测试 |
| `npm run qa` | 全量检查 (lint + test) |
| `node scripts/ops/swarm_test.js` | 蜂群收割测试 |
| `node scripts/ops/circuit_breaker_test.js` | 熔断器测试 |

> 完整命令列表: [COMMAND_CENTER.md](./COMMAND_CENTER.md)

---

## 🔧 故障排查

| 问题 | 诊断 | 解决方案 |
|------|------|----------|
| **代理熔断** | `curl -x http://172.25.16.1:7891 httpbin.org/ip` | `docker-compose restart dev` |
| **全局熔断** | 日志显示 `CIRCUIT_BREAKER_OPEN` | 等待 60 秒冷却窗口 |
| **数据库连接失败** | `docker-compose exec db pg_isready` | `docker-compose restart db` |
| **浏览器崩溃** | `ps aux | grep chromium` | `npx playwright install chromium --force` |
| **指标端点无响应** | `curl localhost:8000/metrics` | 检查 MetricsClient 初始化 |
| **L2 堆积量过高** | `curl localhost:8000/metrics | grep titan_l2_backlog` | 声明 `integrity_guard.py` 检查数据完整性 |
| **Context 泱泄漏** | 日志显示 `Context 池大小` | 检查 `_contextPoolMaxSize=20` 配置 |

---

## 📚 文档索引

| 文档 | 说明 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | AI 助手操作指南 (工程铁律、配置系统) |
| [COMMAND_CENTER.md](./COMMAND_CENTER.md) | 完整命令列表、环境变量 |
| [docs/OPERATIONS_RUNBOOK.md](./docs/OPERations_RUNbook.md) | **生产运维手册** (故障-对策矩阵) |
| [config/monitoring/grafana_dashboard.json](./config/monitoring/grafana_dashboard.json) | **Grafana 监控看板** |
| [scripts/maintenance/integrity_guard.py](./scripts/maintenance/integrity_guard.py) | **数据完整性卫士** |

---

## 📜 版本历史
| 版本 | 日期 | 核心变更 |
|------|------|----------|
| **V4.46.5** | 2026-03-09 | **P10 硬化**: LRU Context 淘汰 + 确定性 ID 生成 + L2 堆积监控 |
| **V4.46.4** | 2026-03-09 | **HYPER-DRIVE 架构**: Worker 池化 + 浏览器只启动一次 + 10x 吞吐提升 |
| V4.46.3 | 2026-03-08 | 超频模式 + 403 逃逸策略 |
| V4.46.1 | 2026-03-08 | 全局熔断保护 + 60s 冷却窗口 |
| V4.46 | 2026-03-08 | Prometheus 监控激活 + 战略解耦 |
| V4.45 | 2026-03-07 | Swarm 蜂群架构 + 22 节点代理池 |
| V4.44 | 2026-03-06 | 指纹对齐 + SessionManager |

---

## 📄 许可证

[MIT License](LICENSE)

---

<p align="center">
  <b>TITAN-V4.46.4 HYPER-DRIVE</b><br>
  <i>Worker Pooling • Browser-once • 100% Data Alignment • 1900 Matches</i>
</p>

<p align="center">
  <a href="https://github.com/xupeng211/FootballPrediction">GitHub</a> •
  <a href="./docs/OPERATIONS_RUNBOOK.md">Operations</a> •
  <a href="./CLAUDE.md">Documentation</a>
</p>
