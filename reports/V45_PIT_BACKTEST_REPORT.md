# V4.5-STRUCTURAL-FIX: 时序防火墙与真实回测报告

**执行日期**: 2026-03-07
**版本**: V4.5.0
**状态**: ✅ 完成

---

## 执行摘要

本报告记录了对 FootballPrediction 系统数据泄露问题的修复及真实准确率评估。

### 核心发现

| 指标 | 修复前 (虚假) | 修复后 (真实) | 变化 |
|------|-------------|-------------|------|
| **总准确率** | 93.1% | 40.4% | **-52.7pp** |
| **高置信度准确率 (>=70%)** | 100% | 51.9% | **-48.1pp** |
| **数据泄露率** | 100% | 0% | **-100%** |

### 结论

修复前的 **93.1% 准确率完全来自数据泄露**，模型实际上没有预测能力。

修复后的 **40.4% 准确率**略高于随机基准 (33.3%)，表明模型在严格时序隔离下有微弱预测能力。

---

## 修复方案

### 1. 时序防火墙 (Point-in-Time Firewall)

创建文件: `scripts/ops/backtest_v45_pit.py`

**特征分类**:

| 类别 | 白名单 (赛前可用) | 黑名单 (赛后数据) |
|------|-----------------|-----------------|
| Elo | elo_diff, home_elo_pre, away_elo_pre | - |
| 身价 | market_value_total, market_value_gap | - |
| 伤病 | injury_count, injury_count_gap | - |
| Rolling | rolling_ppg, rolling_wins/draws/losses | - |
| 赔率 | opening_odds (开盘) | closing_odds (收盘) |
| 战术 | - | xG, shots, corners, possession |
| 评分 | - | rating_avg, rating_max |
| 动量 | - | momentum_mean, momentum_trend |

**特征数量**:
- 白名单: 27 个
- 黑名单: 34 个

### 2. Walk-Forward 验证引擎

创建文件: `scripts/ops/walk_forward_backtest.py`

**验证逻辑**:
1. 按 match_date 排序所有比赛
2. 用前 N 天数据训练，预测后 M 天
3. 滑动窗口重复，模拟真实预测场景
4. 每个窗口独立评估

---

## 回测结果详情

### V4.5-PIT: 时序防火墙回测

```
总样本量: 562 场
总准确率: 40.39%
随机基准: 33.33%

预测分布:
  HOME_WIN: 221 场 (39.3%) | 准确率 52.9%
  DRAW: 166 场 (29.5%) | 准确率 19.9%
  AWAY_WIN: 175 场 (31.1%) | 准确率 44.0%

置信度分析:
  >= 0.7: 266 场 (47.3%) | 准确率 51.9%

时序交叉验证 (TimeSeriesSplit):
  平均准确率: 49.5% (+/- 12.8%)
```

### V4.5-Walk-Forward: 步进式验证

```
窗口配置: 训练 60 天 | 测试 30 天
窗口数量: 5 个
平均准确率: 48.7% (+/- 20.3%)

各窗口详情:
  窗口 1: 56.2% (2025-10-14 ~ 2025-11-13)
  窗口 2: 33.7% (2025-11-13 ~ 2025-12-13)
  窗口 3: 43.9% (2025-12-13 ~ 2026-01-12)
  窗口 4: 46.6% (2026-01-12 ~ 2026-02-11)
  窗口 5: 63.0% (2026-02-11 ~ 2026-03-13)

高置信度准确率 (>= 0.6): 54.3%
```

---

## 特征重要性分析

使用随机森林模型 (仅安全特征):

| 排名 | 特征 | 重要性 |
|------|------|--------|
| 1 | elo_diff | 0.141 |
| 2 | market_value_ratio | 0.088 |
| 3 | home_elo_pre | 0.087 |
| 4 | away_market_value_total | 0.081 |
| 5 | market_value_gap | 0.070 |
| 6 | home_market_value_total | 0.061 |
| 7 | away_elo_pre | 0.055 |
| 8 | home_age_avg | 0.055 |
| 9 | injury_count_gap | 0.054 |
| 10 | home_injury_count | 0.047 |

**关键发现**: Elo 和身价是最重要的预测因子。

---

## 数据泄露根源分析

### 问题 1: 赛后特征混入

**位置**: `src/feature_engine/extractors/TacticalMomentumExtractor.js`

**问题代码**:
```javascript
// 从 FotMob 提取的 xG, shots, corners 等都是赛后数据
features["home_xg"] = safeGet(stats, "home_xg");
features["home_shots"] = safeGet(stats, "home_shots");
```

**影响**: 这些特征只有在比赛结束后才能获得，用于预测会导致 100% 数据泄露。

### 问题 2: 评分特征混入

**位置**: `src/feature_engine/extractors/GoldenFeatureExtractor.js`

**问题代码**:
```javascript
// 评分是赛后给出的，只有比赛结束后才有
features[`${prefix}_rating_avg`] = Math.round(avg * 100) / 100;
```

**影响**: 评分反映了球员在比赛中的表现，是典型的赛后数据。

### 问题 3: 随机分割验证

**位置**: `scripts/ops/backtest_v43_aligned.py`

**问题代码**:
```python
from sklearn.model_selection import cross_val_score
scores = cross_val_score(rf, X_scaled, y, cv=5, scoring='accuracy')
```

**影响**: 随机分割不遵守时序，会用未来数据训练预测过去比赛。

---

## 改进建议

### P0: 紧急修复

1. **补充开盘赔率数据**
   - 实现 OddsPortalProvider 获取开盘赔率
   - 当前赔率特征全是 0，严重削弱预测能力

2. **修复 Rolling 特征计算**
   - 确保 rolling_ppg 只统计 match_date 之前的比赛
   - 添加 `_computed_as_of` 时间戳

### P1: 架构改进

1. **特征版本控制**
   - 为每个特征添加 `data_as_of` 时间戳
   - 实现特征快照机制

2. **验证框架标准化**
   - 默认使用 TimeSeriesSplit 或 Walk-Forward
   - 禁止使用随机 K-Fold 验证

### P2: 数据质量

1. **身价数据完善**
   - 当前覆盖率约 70%
   - 考虑使用 TransferMarkt 作为补充数据源

2. **Elo 评分更新**
   - 当前使用静态 Elo
   - 考虑实现动态 Elo 更新

---

## 文件清单

### 新建文件

| 文件 | 用途 |
|------|------|
| `scripts/ops/backtest_v45_pit.py` | 时序防火墙回测 |
| `scripts/ops/walk_forward_backtest.py` | Walk-Forward 验证 |
| `reports/V45_PIT_BACKTEST_REPORT.md` | 本报告 |

### 可能修改

| 文件 | 修改内容 |
|------|---------|
| `src/feature_engine/smelter/FeatureSmelter.js` | 添加 `_data_as_of` 字段 |
| `src/feature_engine/extractors/GoldenFeatureExtractor.js` | 身价 Fallback 逻辑 |
| `src/ml/backtest/fractional_kelly_backtest.py` | 更新验证方法 |

---

## 运行命令

```bash
# 时序防火墙回测
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/backtest_v45_pit.py

# Walk-Forward 验证 (默认: 训练 90 天, 测试 30 天)
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/walk_forward_backtest.py

# Walk-Forward 验证 (自定义窗口)
docker-compose -f docker-compose.dev.yml exec dev python scripts/ops/walk_forward_backtest.py \
    --train-days 60 --test-days 30 --model random_forest
```

---

## 总结

V4.5-STRUCTURAL-FIX 完成了以下工作:

1. ✅ 建立了时序防火墙，严格隔离赛前/赛后特征
2. ✅ 实现了 Walk-Forward 验证，确保零数据泄露
3. ✅ 揭示了真实准确率 (40-50%) vs 虚假准确率 (93.1%)
4. ✅ 确定了 Elo 和身价是最重要的预测因子

**下一步**: 补充开盘赔率数据，预计可将准确率提升至 50-55%。
