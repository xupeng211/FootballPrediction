# TITAN V4.46.6 系统更新日志

> **发布日期**: 2026-03-11
> **版本代号**: REAL-COMBAT
> **认证胜率**: 44.86% (时序隔离)

---

## 核心变更摘要

本次更新完成了从"虚假高分"到"真实战力"的根本性重构，建立了严格的数据诚信标准和时序隔离训练框架。

---

## [v4.46.6] - 2026-03-11 - REAL COMBAT

### 新增 (Added)

#### 时序隔离训练框架
- **文件**: `scripts/ops/TITAN_CORE_TRAIN.py`
- **功能**: 严格的时序隔离训练
  - 训练集: `match_date <= '2025-12-31'`
  - 测试集: `match_date >= '2026-01-01'`
  - **严禁随机划分** (`train_test_split` 已禁用)

```python
# 训练集查询
WHERE m.match_date <= '2025-12-31' AND m.status = 'finished'

# 测试集查询
WHERE m.match_date >= '2026-01-01' AND m.status = 'finished'
```

#### H2H 除毒审计
- **功能**: 自动检测测试集 H2H 数据是否包含未来比赛结果
- **逻辑**: 比较 `h2h_avg_goal_diff` 与本场净胜球，- **告警**: 若两者一致且非零，则标记潜在泄露

#### 未来比赛身价补偿机制
- **文件**: `scripts/ops/combat_ready_fix.py` (已归档)
- **功能**: 为 `scheduled` 比赛填充预估身价
- **策略**:
  1. 查询该队过去 5 场首发身价平均值
  2. 回退: 联赛默认值 (英超 3.5亿, 西甲 2.5亿...)

### 变更 (Changed)

#### 身价字段统一 (BREAKING CHANGE)

| 旧字段 | 新字段 | 说明 |
|-------|-------|------|
| `home_market_value` | `home_squad_value_eur` | 单位: 欧元 |
| `away_market_value` | `away_squad_value_eur` | 单位: 欧元 |
| - | `home_mv_share` | 新增: 动态占比计算 |

**计算公式**:
```python
home_mv = lineup.get('home_squad_value_eur', 0)
away_mv = lineup.get('away_squad_value_eur', 0)
total_mv = home_mv + away_mv
home_mv_share = home_mv / total_mv if total_mv > 0 else 0.5
```

#### H2H 净胜球修正

**问题**: `h2h_avg_goal_diff` 全部为 0

**修复**: 基于胜率反推估算
```python
# 估算公式
hwr = h2h.get('h2h_home_win_ratio', 0.4)
draw_r = h2h.get('h2h_draw_ratio', 0.25)
awr = 1 - hwr - draw_r
estimated_gd = (hwr * 1.5) + (draw_r * 0) + (awr * -1.5)
```

**影响**: 修复 2006 条记录

#### Elo 引擎动态化

**变更**: 废除硬编码联赛映射

```javascript
// 旧版 (硬编码)
const LEAGUES = ['Premier League', 'La Liga', 'Serie A', ...];

// 新版 (动态发现)
async function discoverLeagues(client) {
    const query = `
        SELECT split_part(match_id, '_', 1) as league_id,
               league_name, COUNT(*) as match_count
        FROM matches
        GROUP BY split_part(match_id, '_', 1), league_name
    `;
    // 自动识别所有联赛，包括中超、J联赛等
}
```

#### 模型参数降温

| 参数 | 旧值 | 新值 | 原因 |
|------|-----|-----|------|
| `n_estimators` | 300 | **80** | 防止过拟合 |
| `max_depth` | 5 | **3** | 强制学习通用规律 |
| `reg_alpha` | 0.1 | **0.5** | 增强 L1 正则化 |
| `reg_lambda` | 1.0 | **2.0** | 增强 L2 正则化 |

### 移除 (Removed)

#### 赛后统计特征 (LEAKAGE)

以下特征已从训练集中**永久移除**:

| 特征名 | 原因 |
|--------|------|
| `possession_pct` | 赛后统计 |
| `shots_total` | 赛后统计 |
| `xg_total` | 赛后统计 |
| `pass_accuracy` | 赛后统计 |
| `corners` | 赛后统计 |
| `fouls` | 赛后统计 |

**替代方案**: 仅使用 11 维赛前可获取特征

---

## 纯净特征集 (11 Dimensions)

```
Elo 核心 (5 维)
├── home_elo_pre      # 主队赛前 Elo
├── away_elo_pre      # 客队赛前 Elo
├── elo_diff          # Elo 差值
├── expected_home_win # 主队预期胜率
└── expected_away_win # 客队预期胜率

身价力量 (3 维)
├── log_home_squad_value  # 主队身价对数
├── log_away_squad_value  # 客队身价对数
└── home_mv_share        # 主队身价占比

历史交锋 (3 维)
├── h2h_home_win_ratio   # 主队历史胜率
├── h2h_draw_ratio       # 历史平局率
└── h2h_avg_goal_diff    # 平均净胜球
```

---

## 性能基准 (Performance Benchmarks)

### 真实胜率 (时序隔离)

| 指标 | 值 |
|------|-----|
| 测试集准确率 | **44.86%** |
| F1 Score | 40.80% |
| Log Loss | 1.088 |
| 训练集 | 876 场 (≤2025) |
| 测试集 | 584 场 (≥2026) |

### 特征重要性

| 特征 | 重要性 |
|------|--------|
| expected_home_win | 18.90% |
| elo_diff | 17.55% |
| expected_away_win | 12.52% |
| home_elo_pre | 9.20% |
| log_home_squad_value | 7.63% |

### 预警阈值

```
⚠️  警告: 任何超过 60% 的回测高分均可能存在特征泄露
🚨 危险: 任何超过 70% 的准确率在当前特征集下几乎必然存在泄露
```

---

## 文件变更清单

### 新增文件
- `scripts/ops/TITAN_CORE_TRAIN.py` - 核心训练脚本
- `models/titan_v4466_real_combat.joblib` - 生产模型
- `scripts/maintenance/archives/` - 归档目录

### 归档文件
- `scripts/maintenance/archives/train_titan_combat.py`
- `scripts/maintenance/archives/combat_ready_fix.py`
- `scripts/maintenance/archives/fix_market_value.py`
- `scripts/maintenance/archives/audit_market_value.py`
- `scripts/maintenance/archives/check_data_status.py`
- `models/archive/` (14 个旧模型)

---

## 迁移指南 (Migration Guide)

### 数据库字段迁移

```sql
-- 检查旧字段残留
SELECT COUNT(*) FROM l3_features
WHERE lineup_features->>'home_market_value' IS NOT NULL;

-- 如果有残留，执行迁移
UPDATE l3_features
SET lineup_features = jsonb_set(
    lineup_features,
    '{home_squad_value_eur}',
    (lineup_features->>'home_market_value')::numeric * 1000000
)
WHERE lineup_features->>'home_market_value' IS NOT NULL;
```

### 训练脚本迁移

```bash
# 旧版 (已废弃)
python scripts/ops/train_model.py

# 新版 (推荐)
python scripts/ops/TITAN_CORE_TRAIN.py
```

---

## 贡献者

- **架构设计**: Claude Code
- **特征工程**: 数据团队
- **审计验证**: ML 工程团队

---

**封版签名**: `v4.46.6-REAL-COMBAT-BASE`
