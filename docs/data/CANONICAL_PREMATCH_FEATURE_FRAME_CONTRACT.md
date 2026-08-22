# Canonical Prematch Training Feature Frame Contract

<!-- lifecycle: permanent -->

本文档定义第一版离线 training feature frame 的业务边界。它是 GD-A03
`TARGET_KICKOFF_EXCLUSIVE` prior-state foundation 的一个版本化投影，不改变
V1 默认模型 contract，不激活 V-next，也不把历史 kickoff 顺序冒充为真实
model decision time。

## Authority and entrypoint

特征名称、顺序、历史/runtime readiness 与训练决策仍只有一个 authority：

```text
config/model_feature_contracts.json
  contracts[canonical_prematch/vnext-v1]
```

frame artifact schema 是 `canonical-prematch-training-feature-frame/v1`，这是
输出/receipt schema，不是第二套 feature registry。入口为：

```bash
npm run feature:frame -- build \
  --gd-a03-artifact <absolute repository-external artifact> \
  --gd-a03-receipt <absolute repository-external receipt> \
  --output <absolute repository-external frame> \
  --receipt <absolute repository-external frame-receipt> \
  --code-revision <full 40-hex Git SHA>

npm run feature:frame -- validate \
  --artifact <absolute repository-external frame> \
  --receipt <absolute repository-external frame-receipt>
```

Build 先重新验证 GD-A03 artifact/receipt，然后只投影 selected features。它不
抓取数据、不连接数据库、不写 raw/L3、不训练、不预测、不 backtest、不激活模型。

## First training decision matrix

V-next 的 17 个定义按当前证据被严格分成三类：

| Feature | Final decision | Reason |
|---|---|---|
| `rolling_xg_home` | `ACCEPTED_FOR_TRAINING` | GD-A03 exact previous-five historical xG lineage；typed-context runtime formula 与 deterministic fixture numeric parity 已证明 |
| `rolling_xg_away` | `ACCEPTED_FOR_TRAINING` | 同上，team identity 按每场 home/away side 解析 |
| `home_points` | `ACCEPTED_FOR_TRAINING` | prior result `3/1/0` 累加；empty closed history 可证明为 0 |
| `away_points` | `ACCEPTED_FOR_TRAINING` | 同上 |
| `points_diff` | `ACCEPTED_FOR_TRAINING` | `home_points - away_points` |
| `home_recent_form_points` | `ACCEPTED_FOR_TRAINING` | exact previous-five result points；不足五场为 unavailable |
| `home_fatigue_index` | `ACCEPTED_FOR_TRAINING` | prior scheduled matches in `[cutoff-7d, cutoff)` / 7, capped at 1 |
| `away_fatigue_index` | `ACCEPTED_FOR_TRAINING` | 同上 |
| `fatigue_diff` | `ACCEPTED_FOR_TRAINING` | `home_fatigue_index - away_fatigue_index` |
| `rolling_possession_home` | `EXCLUDED_FROM_TRAINING` | 当前没有 accepted numeric historical + runtime source；禁止比例、均值和 proxy |
| `rolling_possession_away` | `EXCLUDED_FROM_TRAINING` | 同上 |
| `rolling_shots_on_target_home` | `BLOCKED_PENDING_EVIDENCE` | frozen source 没有独立可靠 team identity/own-goal closure；不得用 goals 或 total shots |
| `rolling_shots_on_target_away` | `BLOCKED_PENDING_EVIDENCE` | 同上 |
| `home_table_position` | `BLOCKED_PENDING_EVIDENCE` | historical semantic contract 已冻结，但当前 runtime numeric materialization/parity 未证明 |
| `away_table_position` | `BLOCKED_PENDING_EVIDENCE` | 同上 |
| `table_position_diff` | `BLOCKED_PENDING_EVIDENCE` | 依赖两侧 standings runtime parity |
| `raw_elo_gap` | `BLOCKED_PENDING_EVIDENCE` | initialization、season transition、K、home treatment 与 update order 未形成 Owner-approved complete contract |

因此第一版 frame 的 feature order 是 registry 原顺序中过滤后的 9 个名字，绝不
为了维度保留 proxy、默认值或 0 fill。其余 8 个仍保留在 decision matrix，便于
未来有独立证据时按 registry 演化，而不创建 parallel feature authority。

## Point-in-time policy

每行至少绑定：

```text
canonical_match_id
target_match_identity
target_kickoff_utc
feature_contract_id/version
feature_as_of_utc
feature_as_of_status
model_decision_time_utc
model_decision_time_status
每个 feature 的 value/availability/source IDs/source identities/provenance
postmatch-only target_label
```

当前 frame 的唯一可证明关系是：

```text
FEATURE_CUTOFF_POLICY=TARGET_KICKOFF_EXCLUSIVE
source_match_kickoff < target_match_kickoff
FEATURE_AS_OF_STATUS=KICKOFF_REFERENCE_ONLY
MODEL_DECISION_TIME_UTC=null
MODEL_DECISION_TIME_STATUS=NOT_PROVEN_KICKOFF_REFERENCE_ONLY
```

这不声称 T-24H、T-1H、source observed time、capture time 或实际 bookmaker
decision-time availability。未来明确的 decision-time context 必须令
`FEATURE_AS_OF_UTC == MODEL_DECISION_TIME_UTC < TARGET_KICKOFF_UTC`，并为 source
facts 提供不晚于该时间的 availability proof；否则 fail closed。

## Eligibility and population conservation

`ROW_ACCOUNTED` 与 `ROW_TRAINING_ELIGIBLE` 分开。feature history 不足的行仍保留，
但列为 `INELIGIBLE`，并记录具体 unavailable feature；不做 mean/median/zero/
forward/league-average/synthetic imputation。

真实 frozen validation 使用现有 repository-external GD-A03 A artifact：

```text
GD-A03 artifact business hash = 2a21672302563c3ecf30e0a3f1962adefad1d5f719c2dd3897ac136f442dde53
TARGET_POPULATION=888
ROWS_ACCOUNTED=888
TRAINING_ELIGIBLE=545
TRAINING_INELIGIBLE=343
UNACCOUNTED=0
DUPLICATE=0
EXTRA=0
```

这 888 行没有因为 early-history gap 被静默丢弃。每个 frame receipt 都重新绑定
target/accounted ID-set hash，并要求 population conservation。

## Leakage, labels, provenance, and determinism

- 所有 selected source identities 必须严格早于 target kickoff；source IDs 不得包含 target ID。
- target label 只作为 `TRAINING_LABEL_POSTMATCH` 独立字段；修改 target score/result/xG/shots/shotmap/player stats 不得改变 prematch feature lines。
- 每条投影 line 带 `source_line_sha256`，并保留 GD-A03 source IDs、identities、cutoff proof、derivation、provenance digest。
- frame business hash 覆盖 contract decision、rows、values、availability、provenance、population 和 readiness；receipt 另绑定 artifact bytes、source bindings 与 code revision。
- 对相同冻结输入和相同 code revision，BUILD_A/BUILD_B 要求 artifact/receipt 字节、business hash、row set、values、availability 与 provenance 完全一致。

## Runtime parity boundary

`src/ml/inference/canonical_prematch_feature_engine.py` 是纯 typed-context semantic
engine，不是 provider/capture adapter，也没有接管 production runtime。它复用 registry
accepted order，使用与 GD-A03 相同的 xG、points/form、fatigue 公式；在 deterministic
fixture 上逐 feature 验证 historical kickoff-reference path 与 runtime typed-context
path 的数值和 unavailable reason 一致。

因此：

```text
TYPED_CONTEXT_SEMANTIC_PARITY=PROVEN
REAL_DECISION_TIME_PROVIDER_AVAILABILITY=NOT_PROVEN
V1_DEFAULT_RUNTIME_SWITCH=NO
MODEL_SCHEMA_SWITCH=NO
```

这足以闭合第一版 kickoff-exclusive offline frame，但不等于真实线上 provider
已接通，也不允许在本任务中启动训练或预测。

## Readiness boundary

本 frame 可以报告：

```text
FEATURE_FRAME_READINESS=READY
REAL_TRAINING_READINESS=READY_FOR_OFFLINE_CANDIDATE_INPUT
TRAINING_EXECUTION_AUTHORIZED=NO
STRICT_DECISION_TIME_VALUE_EVALUATION=NOT_READY
GOLDEN_DATASET_COMPLETE=NO
```

这里的 `REAL_TRAINING_READINESS` 仅表示已经有可信的 offline candidate input；它
不是训练已执行、不是 metrics 已生成，也不是 model artifact 已激活。后续
`CANONICAL_TRAINING_CANDIDATE_PRODUCTION` 需要 Owner 单独授权。
