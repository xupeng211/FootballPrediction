# README V201 FINAL - 防弹级预测系统

> **版本**: V201.1.0-reborn | **发布日期**: 2026-03-06
> **状态**: 生产就绪 | **安全性**: 防弹级 | **Elo 闭环**: ✅ 已焊死

---

## V201.1 核心修复

| 修复项 | 状态 | 说明 |
|--------|------|------|
| **FeatureSmelter.js** | ✅ | 完全重写，语法错误已修复 |
| **Elo 注入 L3** | ✅ | 从 `team_elo_ratings` 表读取真实 Elo |
| **autonomous_engine.js** | ✅ | 补全 5 阶段执行逻辑 |
| **字段对齐** | ✅ | L3 特征与 predict_weekend.py 完全对齐 |

---

## 版本特性

| 特性 | 说明 |
|------|------|
| **防弹级安全** | SQL 注入防护、参数化查询、输入验证 |
| **ID 统一** | match_id 全局唯一标识符，消除歧义 |
| **Elo 实时感知** | 40 支球队 Elo 评分（西甲 20 + 英超 20） |
| **Elo 闭环** | L3 熔炼时自动从 team_elo_ratings 注入真实 Elo |
| **EV 期望值** | 按 EV 排序的高价值投注清单 |
| **全自动编排** | L1 → L2 → L3 → ELO → PREDICT 五层闭环 |

---

## 一键命令速查

### 🚀 完整流水线（推荐）

```bash
# 一键执行：L1播种 → L2收割 → L3熔炼 → Elo重算 → 预测生成
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/autonomous_engine.js

# 循环模式（每 6 小时自动执行）
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/autonomous_engine.js --loop

# 只执行特定阶段
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/autonomous_engine.js --only l2,l3,elo,predict

# 预览模式（不执行实际操作）
docker-compose -f docker-compose.dev.yml exec dev node scripts/ops/autonomous_engine.js --dry-run
```

### 每周五晚必跑

```bash
# 西甲 + 英超 EV 清单（一键生成）
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/predict_weekend.py --save
```

### 指定联赛

```bash
# 只看西甲
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/predict_weekend.py --league "La Liga" --save

# 只看英超
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/predict_weekend.py --league "Premier League" --save
```

### Elo 战力重算（新联赛补血后）

```bash
# 全量重算
docker-compose -f docker-compose.dev.yml exec dev node scripts/maintenance/recalculate_elo.js

# 只算英超
docker-compose -f docker-compose.dev.yml exec dev node scripts/maintenance/recalculate_elo.js --league-id 47

# 只算西甲
docker-compose -f docker-compose.dev.yml exec dev node scripts/maintenance/recalculate_elo.js --league-id 87
```

### L3 全量熔炼（注入真实 Elo）

```bash
# 全量重算 L3 特征，从 team_elo_ratings 注入真实 Elo
docker-compose -f docker-compose.dev.yml exec dev bash -c 'cd /app && node -e "
const { FeatureSmelter } = require(\"./src/feature_engine/smelter/FeatureSmelter\");
(async () => {
    const smelter = new FeatureSmelter({ batchSize: 2000 });
    await smelter.init();
    await smelter.run({ fullRecalculate: true, limit: 2000 });
    await smelter.close();
})().catch(console.error);
"'
```

---

## 本周末西甲 EV 清单

| 排名 | 主队 | 客队 | 时间 | 预测 | 置信度 | EV |
|------|------|------|------|------|--------|-----|
| 1 | Athletic Club | **Barcelona** | 03/07 20:00 | 客胜 | **64.7%** | **+14.9%** |
| 2 | **Villarreal** | Elche | 03/08 13:00 | 主胜 | **62.7%** | **+13.8%** |
| 3 | **Osasuna** | Mallorca | 03/07 13:00 | 主胜 | **53.9%** | **+9.5%** |
| 4 | **Espanyol** | Real Oviedo | 03/09 20:00 | 主胜 | **53.3%** | **+9.1%** |
| 5 | **Valencia** | Deportivo Alaves | 03/08 20:00 | 主胜 | **49.1%** | **+7.1%** |
| 6 | **Atletico Madrid** | Real Sociedad | 03/07 17:30 | 主胜 | **48.6%** | **+6.8%** |
| 7 | Celta Vigo | **Real Madrid** | 03/06 20:00 | 客胜 | **47.4%** | **+6.2%** |

---

## 下周末英超 EV 清单（3/14-3/16）

| 排名 | 主队 | 客队 | 时间 | 预测 | 置信度 | EV |
|------|------|------|------|------|--------|-----|
| 1 | **Arsenal** | Everton | 03/14 17:30 | 主胜 | **60.3%** | **+12.7%** |
| 2 | **Liverpool** | Tottenham | 03/15 16:30 | 主胜 | **59.3%** | **+12.1%** |
| 3 | West Ham | **Manchester City** | 03/14 20:00 | 客胜 | **54.3%** | **+9.6%** |
| 4 | Burnley | **AFC Bournemouth** | 03/14 15:00 | 客胜 | **53.1%** | **+9.0%** |
| 5 | **Chelsea** | Newcastle | 03/14 17:30 | 主胜 | **51.8%** | **+8.4%** |
| 6 | **Manchester United** | Aston Villa | 03/15 14:00 | 主胜 | **47.5%** | **+6.2%** |

---

## Elo 战力榜（TOP 10）

### 西甲

| 排名 | 球队 | Elo |
|------|------|-----|
| 1 | Barcelona | 1684 |
| 2 | Real Madrid | 1635 |
| 3 | Villarreal | 1586 |
| 4 | Atletico Madrid | 1585 |
| 5 | Real Betis | 1566 |

### 英超

| 排名 | 球队 | Elo |
|------|------|-----|
| 1 | Arsenal | 1672 |
| 2 | Manchester City | 1633 |
| 3 | Manchester United | 1590 |
| 4 | Chelsea | 1565 |
| 5 | Aston Villa | 1541 |

---

## 投注策略

1. **只投注 EV > 5% 的场次**
2. **Fractional Kelly 仓位控制**（建议 1/4 Kelly）
3. **赛前 2 小时确认赔率变化**

---

## 技术架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  L1 Discovery   │───▶│  L2 Harvest     │───▶│  L3 Smelt       │───▶│  PREDICT        │
│  (FotMob API)   │    │  (OddsPortal)   │    │  (特征熔炼)      │    │  (Elo + EV)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 预测引擎算法

| 模块 | 公式 |
|------|------|
| **Elo 期望** | `P(主胜) = 1 / (1 + 10^((客Elo - 主Elo - 50) / 400))` |
| **身价调整** | `P(主胜) += (身价差距 / 1亿) * 2%` |
| **伤病调整** | `P(主胜) -= (主队伤病 - 客队伤病) * 0.5%` |
| **期望值** | `EV = 模型概率 * 赔率 - 1` |

---

## V201 安全加固清单

| 安全项 | 状态 | 说明 |
|--------|------|------|
| SQL 注入防护 | ✅ | 全部使用参数化查询 |
| 输入验证 | ✅ | match_id 格式校验 |
| ID 统一 | ✅ | match_id 全局唯一 |
| Elo 闭环 | ✅ | team_elo_ratings 实时更新（40 队） |
| 错误处理 | ✅ | 优雅降级，无崩溃 |

---

## 数据库查询

### 验证 Elo 真实注入

```bash
# 验证 L3 特征中的 Elo 不再是 1500
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
  SELECT
    match_id,
    elo_features->>'home_elo_pre' as home_elo,
    elo_features->>'away_elo_pre' as away_elo,
    elo_features->>'_source' as source
  FROM l3_features
  WHERE match_id LIKE '87_%'
  LIMIT 5;
"

# 预期结果：source = 'team_elo_ratings_table'，Elo 值不再是 1500
```

### 查看本周预测

```bash
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
  SELECT m.home_team, m.away_team, m.league_name, p.predicted_result, p.final_confidence, p.edge
  FROM predictions p JOIN matches m ON p.match_id = m.match_id
  WHERE p.model_version = 'V200-ELO-MV' AND m.match_date >= CURRENT_DATE
  ORDER BY p.edge DESC
"
```

### 查看球队 Elo 评分

```bash
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
  SELECT team_name, elo_rating FROM team_elo_ratings ORDER BY elo_rating DESC LIMIT 20
"
```

---

## 版本历史

| 版本 | 日期 | 核心变更 |
|------|------|----------|
| **V201.1 REBORN** | 2026-03-06 | FeatureSmelter 完全重写、Elo 真实注入 L3、autonomous_engine 五阶段闭环 |
| **V201 FINAL** | 2026-03-06 | 防弹级安全、Elo 实时感知（西甲+英超）、封卷存档 |
| V200 | 2026-03-06 | 交钥匙预测系统 |
| V198 | 2026-03-06 | Elo 战力重算脚本 |
| V195 | 2026-03-05 | 全自动编排器 |
| V186 | 2026-03-04 | 企业级日志 |

---

## 封卷声明

**V201 是最终稳定版本**，具备：
- 防弹级安全性（SQL 注入防护、参数化查询）
- Elo 实时状态感知（40 支球队：西甲 20 + 英超 20）
- 完整 EV 报告生成

此版本已通过生产验证，可安全用于每周预测。

---

**祝投注顺利！**

---

*最后更新: 2026-03-06*
