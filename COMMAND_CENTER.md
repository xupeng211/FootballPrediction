# FootballPrediction 数字化指挥中心操作手册

**版本**: V3.1-STABLE | **生效日期**: 2026-03-06 | **密级**: 内部绝密

---

## 指挥官必读 (Commander's Brief)

本手册是 FootballPrediction 系统的**唯一权威操作指南**。系统经过 V3.0-PRO 工业级重构，现已具备：

- **配置中心**：所有业务常量集中管理（`src/config/constants.js`）
- **结构化日志**：JSON 格式输出，ELK 友好
- **身价数据校准**：所有身价单位统一为**欧元**（EUR）
- **数学正确的 EV 算法**：`EV = P × Odds - 1`，封装为独立工具类
- **完整测试套件**：覆盖身价转换、回退逻辑、纯函数特性

> ⚠️ **铁律**：本系统不产生"必胜推荐"，只提供数学上有正期望值的投注机会。如果系统输出"无高价值投注"，那才是真实的市场信号——**拒绝投注也是一种胜利**。

---

## 第一章：系统架构概览

### 1.1 五阶段自动化流水线

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  L1         │    │  L2         │    │  L3         │    │  ELO        │    │  PREDICT    │
│  Discovery  │───▶│  Harvest    │───▶│  Smelt      │───▶│  Rating     │───▶│  Output     │
│  (赛程发现) │    │  (数据收割) │    │  (特征熔炼) │    │  (动态评分) │    │  (预测报告) │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     FotMob           FotMob Details     4 Extractors        K-Factor           EV 排序
     API              + Odds 辅助        12061 维特征        递归更新           3-Model
                      22 代理节点
```

| 阶段 | 功能 | 入口脚本 | 输出表 |
|------|------|----------|--------|
| **L1 Discovery** | 从 FotMob API 发现比赛赛程 | `npm run seed` | `matches` |
| **L2 Harvest** | 收割 FotMob 比赛详情（身价/阵容/xG/评分）及赔率 | `npm start` | `raw_match_data`, `l2_match_data` |
| **L3 Smelt** | 提取 12061 维特征向量 | `npm run smelt` | `l3_features` |
| **Elo Rating** | 计算球队动态实力评分 | 自动触发 | `team_elo_ratings` |
| **Predict** | 生成 EV 排序的预测报告 | `predict_weekend.py` | `predictions` |

> ⚠️ **数据源说明**：`raw_match_data` 表存储的是 **FotMob Match Details API** 的原始 JSON 响应，包含身价（`marketValue`）、阵容（`starters`/`subs`）、xG、球员评分等核心特征。OddsPortal 仅作为赔率数据的辅助来源。

### 1.2 V201.13 核心突破

#### 突破一：身价单位校准

**问题**：FotMob API 返回的 `marketValue` 单位是**百万欧元**（如 1.5 = 1.5M = 150万欧元），原代码直接使用导致缩水 100 万倍。

**修复**：
```javascript
// GoldenFeatureExtractor.js:98
const MARKET_VALUE_MULTIPLIER = 1e6;  // 百万欧元 -> 欧元

// 所有提取的身价乘以 1e6
const convertedValue = totalMarketValue * MARKET_VALUE_MULTIPLIER;
```

> ⚠️ **关键提醒**：身价数据基于 **FotMob JSON 数据结构**提取，路径为 `content.lineup.{team}Team.totalStarterMarketValue` 或 `starters[].marketValue`。如果 FotMob 接口结构发生变动（字段重命名、路径变更），需立即更新 `GoldenFeatureExtractor.js` 中的提取逻辑，否则将导致身价数据归零。

**效果验证**：
| 球队 | 修复前 | 修复后 |
|------|--------|--------|
| Real Madrid | ~3 (错误) | ~900,000,000 欧元 |
| 身价差示例 | 0.153 (153) | 153,000,000 欧元 (1.53亿) |

#### 突破二：数学正确的 EV 算法

**问题**：原代码的条件分支从低到高排序，导致所有概率 >40% 都匹配第一个分支，产生虚假正 EV。

**修复**：
```python
# predict_weekend.py - EV 计算（条件从高到低）
EV = P * Odds - 1  # 有赔率时

# 无赔率时的保守估算（条件从高到低！）
if p > 0.70:    ev = min(0.10, theoretical_ev + 0.05)
elif p > 0.60:  ev = min(0.05, theoretical_ev + 0.02)
elif p > 0.50:  ev = min(0.03, theoretical_ev)
elif p > 0.40:  ev = max(-0.05, theoretical_ev - 0.02)
else:           ev = max(-0.10, theoretical_ev - 0.05)
```

**数学验证**：
```
P = 64.7%, Odds = 1.47
EV = 0.647 × 1.47 - 1 = 0.951 - 1 = -4.9%  (负值，不推荐投注)
```

---

## 第二章：每周作战常规指令

### 2.1 第一步：数据库体检与清理

**执行时机**：每周五 18:00 或开战前 2 小时

```bash
# 进入开发容器
docker-compose -f docker-compose.dev.yml exec dev bash

# 执行数据库清理（删除损坏的 L3 特征）
psql -h db -U football_user -d football_db << 'EOF'
-- 清理 7 天前的损坏特征
DELETE FROM l3_features
WHERE computed_at < NOW() - INTERVAL '7 days'
  AND (
    golden_features IS NULL
    OR golden_features->>'market_value_gap' IS NULL
    OR (golden_features->>'home_market_value_total')::float = 0
  );

-- 查看待收割比赛数量
SELECT
    COUNT(*) FILTER (WHERE l2_harvested = false) as pending_l2,
    COUNT(*) FILTER (WHERE l2_harvested = true) as completed_l2
FROM matches
WHERE match_date >= NOW()
  AND match_date < NOW() + INTERVAL '4 days';
EOF
```

### 2.2 第二步：全自动引擎启动

**执行时机**：每周五 18:30 - 21:00

```bash
# 阶段 1: 赛程种子 (约 2 分钟)
docker-compose -f docker-compose.dev.yml exec dev npm run seed

# 阶段 2: L2 数据收割 (约 1-3 小时，取决于比赛数量)
# ⚠️ 此步骤需要代理池运行正常
docker-compose -f docker-compose.dev.yml exec dev npm start

# 阶段 3: L3 特征熔炼 (约 5-10 分钟)
docker-compose -f docker-compose.dev.yml exec dev npm run smelt
```

**监控要点**：
```bash
# 实时查看收割日志
tail -f /app/logs/harvester.log

# 检查代理池状态
curl -x http://172.25.16.1:7890 https://httpbin.org/ip --connect-timeout 5
```

### 2.3 第三步：独立预测报告生成

**执行时机**：每周六 10:00（开战前 6 小时）

```bash
# 生成西甲预测报告（不保存到数据库，仅预览）
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/predict_weekend.py --league "La Liga"

# 确认无误后，保存到数据库
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/predict_weekend.py --league "La Liga" --save

# 生成所有联赛预测（可选）
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/predict_weekend.py --days 3 --save
```

---

## 第三章：指挥官监控指标 (Critical KPI)

### 3.1 健康数据识别标准

**日志中的健康信号**：

| 指标 | 健康值 | 检查位置 |
|------|--------|----------|
| 身价差 | **亿级** (如 +1.53亿) | `market_value_gap` |
| 身价单位 | 显示"欧元"后缀 | `format_value()` 输出 |
| L3 成功率 | **100%** | `FeatureSmelter` 日志 |
| EV 分布 | 有正有负 | `_print_report()` |
| 数据来源 | `totalStarterMarketValue` 或 `starters` | `market_value_source` |

**健康日志示例**：
```
[V201.13] Real Madrid vs Barcelona
   身价差: +1.53亿欧元 | 伤病差: -2 人
   概率: 主 45.2% | 平 28.0% | 客 26.8%
   EV: 主 -2.1% | 平 +1.2% | 客 -5.3%
   建议: 平局 @ 3.20 (EV: +1.2%)
```

### 3.2 幻觉报警识别

**立即停止并排查的信号**：

| 幻觉类型 | 异常表现 | 根因 |
|----------|----------|------|
| **身价归零** | `market_value_gap: 0` | FotMob 数据源失效或单位转换失败 |
| **EV 全正** | 所有 EV > 0 | 条件分支顺序错误（已修复） |
| **EV 过高** | 单个 EV > 15% | 模型过拟合或赔率数据异常 |
| **置信度 100%** | 任何 `confidence: 100%` | 数据缺失导致默认值 |
| **身价缩水** | 身价差显示"万"而非"亿" | 单位转换未生效 |

**幻觉报警日志示例**：
```
❌ 错误示例（V201.10 Bug）：
   身价差: 0.153万   ← 缩水 100 万倍！
   EV: 主 +14.85%    ← 数学错误！64.7% × 1.47 应为 -4.9%

✅ 正确示例（V201.13）：
   身价差: +1.53亿欧元
   EV: 主 -2.1%      ← 数学正确
```

### 3.3 数据完整性检查 SQL

```sql
-- 检查 L3 特征完整性
SELECT
    COUNT(*) as total_matches,
    COUNT(*) FILTER (WHERE golden_features IS NOT NULL) as has_golden,
    COUNT(*) FILTER (WHERE golden_features->>'home_market_value_total' IS NOT NULL) as has_mv,
    COUNT(*) FILTER (WHERE (golden_features->>'home_market_value_total')::float > 1e6) as mv_reasonable
FROM l3_features
WHERE computed_at > NOW() - INTERVAL '24 hours';

-- 检查 Elo 评分覆盖率
SELECT
    COUNT(DISTINCT m.home_team) as unique_teams,
    COUNT(DISTINCT e.team_name) as teams_with_elo
FROM matches m
LEFT JOIN team_elo_ratings e ON m.home_team = e.team_name
WHERE m.match_date >= NOW();
```

---

## 第四章：数据血缘与修复

### 4.1 核心数据表血缘图

```
matches (L1)
    │
    ├── match_id ──────────────────────────────────────────┐
    │                                                       │
    ▼                                                       ▼
raw_match_data (L2 原始)                         l2_match_data (L2 结构化)
    │                                                       │
    │ raw_data (JSONB)                                      │
    │   ├── content.lineup.homeTeam.totalStarterMarketValue │
    │   ├── content.lineup.homeTeam.starters[].marketValue  │
    │   └── odds.1x2.closing                                │
    │                                                       │
    └───────────────────────┬───────────────────────────────┘
                            │
                            ▼
                    l3_features (L3 特征)
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
  golden_features      tactical_features   computed_features
  (JSONB)              (JSONB)             (JSONB)
        │
        ├── home_market_value_total (欧元)
        ├── away_market_value_total (欧元)
        ├── market_value_gap (主队 - 客队)
        ├── home_injury_count
        └── home_rating_avg
                            │
                            ▼
                    team_elo_ratings
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
    home_elo           draw_base           away_elo
                            │
                            ▼
                    predictions (输出)
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
  confidence_home    confidence_draw    confidence_away
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                      edge (EV)
```

### 4.2 L3 Features 关键字段

| 字段名 | 类型 | 说明 | 示例值 |
|--------|------|------|--------|
| `match_id` | VARCHAR(50) | 比赛唯一标识 | `fotmob_1234567` |
| `computed_at` | TIMESTAMP | 特征计算时间 | `2026-03-06 18:30:00` |
| `golden_features` | JSONB | 黄金特征（身价/伤病/评分） | 见下表 |
| `tactical_features` | JSONB | 战术特征 | `{...}` |
| `external_id` | VARCHAR(50) | 外部系统 ID | 可选 |

**golden_features JSONB 结构**：

```json
{
  "home_market_value_total": 850000000,    // 主队总身价（欧元）
  "away_market_value_total": 750000000,    // 客队总身价（欧元）
  "market_value_gap": 100000000,           // 身价差（主队 - 客队）
  "market_value_ratio": 1.133,             // 身价比率
  "home_injury_count": 2,                  // 主队伤病人数
  "away_injury_count": 4,                  // 客队伤病人数
  "injury_count_gap": -2,                  // 伤病差（主队 - 客队）
  "home_rating_avg": 6.85,                 // 主队平均评分
  "away_rating_avg": 6.72,                 // 客队平均评分
  "home_market_value_source": "totalStarterMarketValue",  // 数据来源
  "_version": "V201.13.0-TRUTH"            // 提取器版本
}
```

### 4.3 GoldenFeatureExtractor 四层回退逻辑

```
┌─────────────────────────────────────────────────────────────────┐
│                    身价提取策略 (V201.13)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  策略 1: totalStarterMarketValue                                │
│  ├─ 路径: content.lineup.{team}Team.totalStarterMarketValue     │
│  ├─ 可靠性: ★★★★★ (最可靠)                                      │
│  └─ 单位转换: × 1e6                                              │
│                                                                 │
│  策略 2: starters 数组求和                                       │
│  ├─ 路径: content.lineup.{team}Team.starters[].marketValue      │
│  ├─ 可靠性: ★★★★☆                                               │
│  └─ 单位转换: 每个 player.marketValue × 1e6 后求和               │
│                                                                 │
│  策略 3: subs 数组求和                                           │
│  ├─ 路径: content.lineup.{team}Team.subs[].marketValue          │
│  ├─ 可靠性: ★★★☆☆ (替补阵容)                                     │
│  └─ 单位转换: 每个 player.marketValue × 1e6 后求和               │
│                                                                 │
│  策略 4: 深度搜索 (新增)                                         │
│  ├─ 路径 A: content.table.all[].marketValue                     │
│  ├─ 路径 B: content.players[].marketValue                       │
│  ├─ 路径 C: content.details.stats.* (含 market/value 关键字)     │
│  ├─ 路径 D: header.homeMarketValue/awayMarketValue              │
│  ├─ 路径 E: 递归搜索所有 marketValue 字段                        │
│  └─ 可靠性: ★★☆☆☆ (兜底)                                        │
│                                                                 │
│  策略 5: 数据缺失                                                │
│  ├─ 输出: market_value_total = 0                                │
│  └─ 标记: market_value_source = 'not_found'                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4 常见数据修复操作

```bash
# 修复损坏的 L2 数据
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/clean_corrupt_l2.py

# 重新计算 Elo 评分
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/recalculate_elo.py

# 历史数据回填
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/fotmob_historical_backfill.py --days 30

# 系统健康检查
docker-compose -f docker-compose.dev.yml exec dev python scripts/maintenance/check_system_health.py
```

---

## 第五章：投注纪律 (The Quant Rule)

### 5.1 核心原则

> **"我们不是在赌博，我们是在执行数学公式。"**

1. **只投注 EV > 5% 的场次** - 低于此阈值的市场噪音太大
2. **使用 Fractional Kelly 控制仓位** - 推荐 1/4 Kelly，避免单场过重
3. **赛前 2 小时确认赔率** - 赔率变动可能使 EV 归零
4. **接受"无投注"结果** - 系统拒绝投注 = 避免负 EV 损失

### 5.2 EV 阈值决策矩阵

| EV 范围 | 决策 | 仓位建议 |
|---------|------|----------|
| **EV > 10%** | 强烈推荐 | 1/2 Kelly |
| **5% < EV < 10%** | 推荐 | 1/4 Kelly |
| **0% < EV < 5%** | 边缘 | 1/8 Kelly 或跳过 |
| **EV < 0%** | **拒绝** | 0 (负期望值) |

### 5.3 Fractional Kelly 计算公式

```
Kelly% = (P × Odds - 1) / (Odds - 1)
实际仓位 = Kelly% × 分数系数 (推荐 0.25)

示例:
P = 55%, Odds = 2.10, EV = 15.5%
Kelly% = (0.55 × 2.10 - 1) / (2.10 - 1) = 0.155 / 1.10 = 14.1%
实际仓位 = 14.1% × 0.25 = 3.5% (总资金的 3.5%)
```

### 5.4 为什么"系统拒绝投注"也是一种胜利

```
假设某周末 10 场比赛：
├── 7 场 EV < 0%  → 系统拒绝 → 节省潜在损失
├── 2 场 0% < EV < 5% → 系统边缘 → 跳过
└── 1 场 EV = 8% → 系统推荐 → 投注

如果盲目投注全部 10 场:
  期望收益 = 7×(-5%) + 2×(+2%) + 1×(+8%) = -35% + 4% + 8% = -23%

系统筛选后只投注 1 场:
  期望收益 = 1×(+8%) = +8%

结论: 拒绝 9 场 = 避免 31% 的损失 = 系统价值
```

### 5.5 投注记录与复盘

**每次投注后记录**：
```sql
INSERT INTO bet_records (
    match_id, bet_type, odds, stake, ev_at_bet,
    result, profit, lesson_learned
) VALUES (
    'fotmob_1234567', 'home', 2.10, 100, 0.08,
    'win', 110, 'Elo 差距 +50 时的主胜值得信赖'
);
```

**每周复盘 SQL**：
```sql
SELECT
    DATE_TRUNC('week', bet_time) as week,
    COUNT(*) as bets,
    SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
    ROUND(AVG(ev_at_bet)::numeric, 3) as avg_ev,
    SUM(profit) as total_profit
FROM bet_records
GROUP BY DATE_TRUNC('week', bet_time)
ORDER BY week DESC;
```

---

## 第六章：故障排查速查表

### 6.1 常见问题与解决方案

| 问题 | 诊断命令 | 解决方案 |
|------|---------|----------|
| **代理熔断** | `curl -x http://172.25.16.1:7890 https://httpbin.org/ip` | `docker-compose restart dev` |
| **数据库连接失败** | `docker-compose exec db pg_isready -U football_user` | `docker-compose restart db` |
| **浏览器崩溃** | `ps aux \| grep chromium` | `npx playwright install chromium --force` |
| **身价全为 0** | 检查 `golden_features->>'home_market_value_source'` | 确认 V201.13 版本已生效 |
| **EV 异常高** | 检查条件分支顺序 | 确认 V201.13 版本已生效 |
| **Turnstile 拦截** | 检查 `/app/data/sessions/` | 宿主机运行 `node scripts/capture_auth.js` |

### 6.2 紧急恢复流程

```bash
# 1. 停止所有服务
docker-compose -f docker-compose.dev.yml down

# 2. 清理损坏数据
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
DELETE FROM l3_features WHERE computed_at < NOW() - INTERVAL '1 day';
"

# 3. 重启服务
docker-compose -f docker-compose.dev.yml up -d

# 4. 重新熔炼
docker-compose -f docker-compose.dev.yml exec dev npm run smelt
```

---

## 附录 A：命令速查卡

```bash
# === 日常作战 ===
npm run seed                    # L1: 赛程种子
npm start                       # L2: 数据收割
npm run smelt                   # L3: 特征熔炼
python scripts/ops/predict_weekend.py --league "La Liga"  # 预测

# === 系统维护 ===
npm run lint                    # 代码检查
npm test                        # 运行测试
python scripts/maintenance/check_system_health.py  # 健康检查

# === 数据库 ===
make db-shell                   # 进入数据库
make db-backup                  # 备份数据库

# === 日志查看 ===
tail -f /app/logs/harvester.log # 收割日志
docker-compose logs -f dev      # 容器日志
```

---

## 附录 B：版本历史

| 版本 | 日期 | 核心变更 |
|------|------|----------|
| **V3.1-STABLE** | 2026-03-06 | ✅ 穿透审计完成：修复 external_id 字段，100% 合规 | | 2026-03-06 | 工业级重构：配置中心 + 结构化日志 + EV 工具类 + 测试套件 |
| V201.14-FIX | 2026-03-06 | 修正文档：L2 数据源归属（FotMob Details 为主，Odds 辅助） |
| V201.13-TRUTH | 2026-03-06 | 身价单位校准 + EV 算法修复 |
| V201.10-RESTORE | 2026-03-05 | 多路径回退策略 |
| V200 | 2026-03-04 | 交钥匙预测系统 |
| V186-ENTERPRISE | 2026-03-04 | 企业级日志 + 优雅停机 |

---

**文档维护**: 本手册随系统版本同步更新。如有疑问，请查阅 `CLAUDE.md` 或联系系统架构师。

**最后更新**: 2026-03-06 | **下次审核**: 2026-03-13

---

*"在数字的战场上，纪律就是利润。"*
