# README V200 - 交钥匙预测系统

> **版本**: V200.0.0-stable | **发布日期**: 2026-03-06

## 概述

V200 是 FootballPrediction 项目的**交钥匙版本**，实现了从数据采集到预测输出的完整自动化流水线。

### 核心能力

| 能力 | 说明 |
|------|------|
| **Elo 预测引擎** | 基于 team_elo_ratings 表的 20 支西甲球队 Elo 评分 |
| **身价调整** | 根据市场价值差距调整预测概率 |
| **伤病影响** | 实时伤病数据影响预测 |
| **EV 计算** | 期望值计算，筛选高价值投注 |
| **自动编排** | L1 → L2 → L3 → PREDICT 四层流水线自动执行 |

---

## 一键启动

### 完整流水线（推荐）

```bash
# 进入开发容器
make dev-shell

# 执行完整流水线：L1播种 → L2收割 → L3熔炼 → 预测生成
node scripts/ops/autonomous_engine.js
```

### 只执行预测

```bash
# 只运行预测阶段（基于现有数据）
node scripts/ops/autonomous_engine.js --only predict

# 或直接调用 Python 预测脚本
python scripts/ops/predict_weekend.py --save
```

### 循环模式（每日自动巡检）

```bash
# 每 6 小时自动执行一次
node scripts/ops/autonomous_engine.js --loop

# 自定义间隔（每 1 小时）
node scripts/ops/autonomous_engine.js --loop --interval 3600000
```

---

## 本周末高价值投注清单

基于 V200 Elo + 身价 + 伤病预测引擎，以下场次具有正期望值：

| 排名 | 比赛 | 时间 | 预测 | 置信度 | EV |
|------|------|------|------|--------|-----|
| 1 | Athletic Club vs **Barcelona** | 03/07 20:00 | 客胜 | 64.7% | **+14.9%** |
| 2 | **Villarreal** vs Elche | 03/08 13:00 | 主胜 | 62.7% | **+13.8%** |
| 3 | **Osasuna** vs Mallorca | 03/07 13:00 | 主胜 | 53.9% | **+9.5%** |
| 4 | **Espanyol** vs Real Oviedo | 03/09 20:00 | 主胜 | 53.3% | **+9.1%** |
| 5 | **Valencia** vs Deportivo Alaves | 03/08 20:00 | 主胜 | 49.1% | **+7.1%** |
| 6 | **Atletico Madrid** vs Real Sociedad | 03/07 17:30 | 主胜 | 48.6% | **+6.8%** |
| 7 | Celta Vigo vs **Real Madrid** | 03/06 20:00 | 客胜 | 47.4% | **+6.2%** |

### 投注建议

1. **只投注 EV > 5% 的场次**（上述 7 场）
2. **使用 Fractional Kelly 控制仓位**（建议 1/4 Kelly）
3. **赛前 2 小时确认赔率变化**

---

## 预测算法

### Elo 期望公式

```
P(主胜) = 1 / (1 + 10^((客队Elo - 主队Elo - 50) / 400))
```

- 50 = 主场优势 Elo 加成

### 身价调整

```
P(主胜) += (身价差距 / 1亿欧元) * 2%
```

### 伤病调整

```
P(主胜) -= (主队伤病 - 客队伤病) * 0.5%
```

### 期望值计算

```
EV = 模型概率 * 赔率 - 1
```

无赔率时使用理论 EV：高置信度预测 = 潜在价值

---

## 数据依赖

| 数据源 | 表名 | 用途 |
|--------|------|------|
| Elo 评分 | `team_elo_ratings` | 球队战力评估 |
| L3 特征 | `l3_features` | 身价、伤病等基本面 |
| 赔率数据 | `raw_match_data` | 开盘/收盘赔率 |

---

## 文件结构

```
scripts/ops/
├── autonomous_engine.js    # V200 四层编排器
├── predict_pipeline.js     # 预测流水线模块
├── predict_weekend.py      # Python 预测脚本
├── predict_laliga.py       # 西甲专项预测
└── run_production.js       # L2 收割入口

src/ml/inference/
├── predictor.py            # ML 预测器
├── model_dispatcher.py     # 模型路由
└── multi_model_validator.py # 多模型共识
```

---

## 命令速查

```bash
# === 完整流水线 ===
node scripts/ops/autonomous_engine.js                    # 单次执行
node scripts/ops/autonomous_engine.js --loop             # 循环模式
node scripts/ops/autonomous_engine.js --only predict     # 只预测
node scripts/ops/autonomous_engine.js --dry-run          # 干跑测试

# === Python 预测 ===
python scripts/ops/predict_weekend.py                    # 显示预测
python scripts/ops/predict_weekend.py --save             # 保存到数据库
python scripts/ops/predict_weekend.py --league "La Liga" # 指定联赛
python scripts/ops/predict_weekend.py --days 7           # 预测未来 7 天

# === 数据查询 ===
docker-compose -f docker-compose.dev.yml exec db psql -U football_user -d football_db -c "
  SELECT m.home_team, m.away_team, p.predicted_result, p.edge
  FROM predictions p JOIN matches m ON p.match_id = m.match_id
  WHERE p.model_version = 'V200-ELO-MV' ORDER BY p.edge DESC
"
```

---

## 版本历史

| 版本 | 日期 | 核心变更 |
|------|------|----------|
| V200 | 2026-03-06 | 交钥匙预测系统，Elo + 身价 + 伤病 + EV |
| V195 | 2026-03-05 | 全自动编排器，L1→L2→L3 闭环 |
| V186 | 2026-03-04 | 企业级日志、优雅停机 |
| V179 | 2026-03-03 | 无人值守身份管理 |

---

**祝投注顺利！**
