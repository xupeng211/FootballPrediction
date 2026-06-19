# Training Dataset Construction & Feature Leakage Dry-Run
- lifecycle: phase-artifact
- scope: read-only training dataset construction & feature leakage policy audit
- date: 2026-06-19
- branch: `data/training-dataset-leakage-dry-run`

## 结论

这是 **dry-run，不是真实训练**。没有 DB write / migration / schema change / live fetch / raw payload output / model training / model output。本次只做只读审计，分析 58 条已 `is_training_eligible=true` 的 Ligue 1 样本，确认标签完整性，区分安全特征与泄漏特征。

## 训练样本状态

| 指标 | 数值 |
| --- | ---: |
| `is_training_eligible=true` | 58 |
| `actual_result` 非空 | 58 |
| `actual_result` 合法值 | 58/58 |
| 2 条 no-raw excluded 进入训练 | 0（不在此范围） |

### Label 分布

| 编码 | 数量 |
| --- | ---: |
| `home_win` | 23 |
| `draw` | 17 |
| `away_win` | 18 |

58/58 标签完整，全部在 `{home_win, draw, away_win}` 集合内。

## 字段分类（32 个 matches 列全覆盖）

### Label（1 个）

| 字段 | 说明 |
| --- | --- |
| `actual_result` | 预测目标。编码：home_win / draw / away_win |

### 赛前安全特征（7 个）— 可用于训练

| 字段 | 说明 | 编码注意事项 |
| --- | --- | --- |
| `league_name` | 联赛标识 | One-hot 或 label encode |
| `season` | 赛季标识 | 可衍生赛季阶段/轮次 |
| `home_team` | 主队 | 球队强度特征必须时间门控 |
| `away_team` | 客队 | 同主队要求 |
| `match_date` | 比赛日期 | 可衍生：周几、月份、时间、赛季天数 |
| `venue` | 比赛场地 | 主场优势特征 |
| `referee` | 裁判 | 裁判严格度指标须时间门控。边际特征 |

### 赛后泄漏字段（10 个）— 严禁作为特征

| 字段 | 原因 |
| --- | --- |
| `home_score` | 终场比分 — 直接泄漏标签 |
| `away_score` | 终场比分 — 直接泄漏标签 |
| `home_corners` | 赛后统计 |
| `away_corners` | 赛后统计 |
| `home_yellow_cards` | 赛后纪律记录 |
| `away_yellow_cards` | 赛后纪律记录 |
| `home_red_cards` | 赛后纪律记录 |
| `away_red_cards` | 赛后纪律记录 |
| `status` | 赛后状态（finished） |
| `is_finished` | 赛后布尔标记 |

### 管理/治理字段（14 个）— 不作为特征

`external_id`, `match_id`, `collection_date`, `created_at`, `updated_at`, `data_version`, `data_source`, `pipeline_status`, `source_type`, `evidence_level`, `is_production_scope`, `is_reconciliation_eligible`, `is_training_eligible`, `pipeline_status_reason`

### 不确定字段（0 个）

所有 32 列全部分类完毕，无待确认。

## 重要风险点

1. **样本量不足**：58 条只适合 smoke/integration dataset，不适合正式模型训练。需要扩展到 500+ 条多联赛多赛季数据。
2. **时间门控未实施**：当前 repo 没有时间门控基础设施。所有从历史数据派生的球队特征（ELO、近期状态、历史交锋等）必须保证特征数据时间 < 当前比赛 `match_date`。
3. **raw_match_data 泄漏风险**：FotMob raw 数据包含 xG、射门、控球、传球等 100+ 字段，全部是赛后泄漏。如果未来从 raw 数据提取特征，每个字段都必须审计。
4. **collection_date 解释**：这是数据采集时间戳，不是比赛时间。如果误用会导致跨时间泄漏。
5. **跨联赛泛化未测试**：58 条仅来自 Ligue 1。扩展到其他联赛前需要验证联赛特定特征。

## 建议

1. 58 条当前样本定位为 smoke/integration dataset
2. 赛前特征仅限 7 个已确认安全字段
3. 严禁将任何 match statistics（score/corners/cards）作为特征
4. 从 raw_match_data 提取的任何特征必须先通过泄漏审计
5. 在扩展到正式训练前，实施显式的时间截止策略
6. 定义特征时间点 T：特征必须仅使用 `match_date[T]` 之前可用的数据

## 安全确认

| 项目 | 状态 |
| --- | --- |
| 无 migration | ✅ |
| 无 schema change | ✅ |
| 无 DB write | ✅ |
| 无 live fetch | ✅ |
| 无 raw payload 输出 | ✅ |
| 无 model training | ✅ |
| 无 model output | ✅ |
| 只读事务 | ✅ |

## 下一步

必须用户确认后才能进入正式训练 pipeline 构建：
1. 确认 58 条 smoke dataset 用途
2. 确认 7 个安全特征列表
3. 确认时间门控策略
4. 确认是否需要扩展到多联赛多赛季训练数据
5. 确认正式模型训练目标和评估标准
