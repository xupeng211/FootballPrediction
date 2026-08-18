# Canonical Model As-Of Contract

<!-- lifecycle: permanent -->

状态：`FROZEN`（`canonical-model-asof/v1`）。本文档解释同一
`config/model_feature_contracts.json` 注册表中的 canonical temporal boundary；不
实现 runtime source、capture、feature rebuild 或 training。

## Authority and scope

唯一 registry authority 是 `config/model_feature_contracts.json` 的
`model-feature-contract-registry/v2`，校验入口是
`src/ml/inference/feature_contract_registry.py` 与
`src/ml/inference/model_asof_contract.py`（由
`src/ml/inference/feature_contract_boundary_validator.py` 复用其 registry 校验入口）。不得建立第二套通用
temporal/feature registry，也不得由 provider、`l3_features`、`SchemaManager` 或
当前表格结果暗中覆盖本合同。

本合同来自 Owner 选择的 `EXPLICIT_PER_PREDICTION_AS_OF`。它是系统级政策，适用于
standings、ELO、form、fatigue、SOT、possession、availability、lineups 以及未来
market-linked inputs；各 feature family 仍须分别完成 source、capture、replay 和
numeric parity 证明。

## Canonical information boundary

每一个 prematch prediction/value-decision context 必须绑定不可变的：

```text
MODEL_ASOF_CONTRACT_ID      = canonical-model-asof/v1
MODEL_ASOF_CONTRACT_VERSION = v1
MODEL_DECISION_TIME_UTC     = T
FEATURE_AS_OF_UTC           = T
```

`T` 是模型允许使用的最新逻辑信息边界，必须是绝对 UTC timestamp，并在 canonical
feature eligibility 解析前确定。对 prematch context：

```text
MODEL_DECISION_TIME_UTC < TARGET_KICKOFF_UTC
FEATURE_AS_OF_UTC       = MODEL_DECISION_TIME_UTC
```

缺失、非法、相等或晚于 kickoff 的 T 都 fail closed。重复预测同一 target 但使用新
的 T 是新的 prediction context；不得把已有 context 从 T1 原地改写成 T2。

`TARGET_KICKOFF_UTC` 是目标比赛的 scheduling/identity context，不是 model knowledge
boundary。它与 T 分开保存，并且在正常预测中预期不相等。

## Timestamp taxonomy

| 字段                            | 语义                                                | 能否单独证明 T 前可用                          |
| ------------------------------- | --------------------------------------------------- | ---------------------------------------------- |
| `SOURCE_EVENT_TIME_UTC`         | 事件发生的时间                                      | 否；event time 不是 availability time          |
| `SOURCE_EFFECTIVE_TIME_UTC`     | 事实/处置生效的时间（适用时）                       | 否；还需 source observation proof              |
| `SOURCE_OBSERVED_AT_UTC`        | source 观察、发布或系统可知事实的时间               | 在 source contract 明确且 `<= T` 时可以        |
| `SOURCE_CAPTURED_AT_UTC`        | 本系统捕获/保存 source record 的时间                | 默认不能替代 observed-at                       |
| `MODEL_DECISION_TIME_UTC`       | 模型逻辑信息边界 T                                  | 是 canonical boundary，不是 source observation |
| `FEATURE_AS_OF_UTC`             | feature family 共用的 T                             | 必须等于 model decision time                   |
| `PREDICTION_GENERATED_AT_UTC`   | 输出执行 telemetry                                  | 不是 feature authority；若存在必须 `>= T`      |
| `TARGET_KICKOFF_UTC`            | 目标比赛 kickoff                                    | 不是 T                                         |
| `ODDS_SNAPSHOT_OBSERVED_AT_UTC` | 实际用于 value decision 的 market snapshot 观察时间 | 未来 strict value context 中必须证明 `<= T`    |

`SOURCE_CAPTURED_AT_UTC != SOURCE_OBSERVED_AT_UTC` by default。只有另一个已冻结
的 source/capture contract 明确证明两者关系时，才可以使用该证明。不能用 event time
或 capture time 事后推断 model 已经知道事实。

## Availability proof and fail-closed rules

动态事实只有在 `INFORMATION_AVAILABLE_BY_MODEL_DECISION=YES` 可被诚实证明时才能
进入 canonical feature context。允许的 proof form 是：

- exact observation timestamp 且不晚于 T；
- exact effective timestamp 且有 source observation proof；
- 由 source contract 证明整个 bounded interval 严格早于 T；
- 其他未来明确冻结且可审计的 source-contract proof 需要后续版本化 source/capture
  contract；`canonical-model-asof/v1` 不接受未绑定的自报 proof flag。

unknown 保持 unknown。观察时间晚于 T 直接拒绝。时间精度不足导致 availability
interval 与 T overlap 时，不能猜测先后，必须以
`SOURCE_TIME_PRECISION_AMBIGUOUS` fail closed。未来信息依赖数量必须为零，包含较晚
的比赛结果、行政决定、伤停/首发更新、provider correction、较晚观察到的旧事件以及
较晚 odds。

当前 pure validator 不读取墙钟、DB、环境、网络或 Git，也不负责持久化 context
immutability。这个持久化/replay boundary 已由独立的
`canonical-runtime-capture/v1` contract freeze 定义（见
`docs/data/RUNTIME_CAPTURE_CONTRACT.md`），但 storage、provider capture 和
source-specific normalization 仍未实现。

## Historical standings preservation

既有 standings contract `standings/premier-league-point-in-time/v1` 仍是：

```text
SOURCE_EVENT_TIME_UTC < TARGET_KICKOFF_UTC
```

它是 `KICKOFF_EXCLUSIVE_POINT_IN_TIME` 的正确实现，历史覆盖 `887/888`，engine 与
GD-A03 parity 为 `888/888`；`47_20232024_4193789` 仍因
`ADMIN_ADJUSTMENT_EFFECTIVE_TIME_AMBIGUOUS` unavailable。

这批数值保留为 `KICKOFF_EXCLUSIVE_REFERENCE_PROJECTION`，可用于历史语义和 engine
校验，但不自动变成 Option-C 的 as-of training rows，也不能通过改标签绕过新的
availability proof。对更早的 T，standings 可能需要在未来由 T-aware adapter 重建。

当前 `PointInTimeStandingsEngine` 仍以 target kickoff 解释 prior result/event 和
行政 adjustment eligibility，输入也没有 model T 或 source observation proof。因此本
合同冻结的架构结论是：未来可继续复用同一个 engine core，但需要
`REQUIRES_VERSIONED_ENGINE_INPUT_CONTRACT`；不能声称仅把 evidence 在调用前过滤就已
证明 Option-C numeric parity，也不能创建第二个 standings engine。

## Odds and strict value evaluation

既有赔率事实保持：provider-defined closing 可用，但 exact closing timestamp 和 strict
decision-time evidence 均未证明。provider-defined closing 不能被重命名成 T 时刻的
snapshot。

未来 strict decision-time value evaluation 必须在同一 decision context T 下同时满足：

```text
all feature information <= T
used odds snapshot observed <= T
```

odds snapshot 不要求时间戳恰好等于 T，但必须是该 decision 实际使用的、时间已证明的
snapshot；freshness/staleness policy 留待未来合同或 Owner 决策。本阶段状态仍为
`STRICT_DECISION_TIME_VALUE_EVALUATION=NOT_READY`，因此当前 v1 validator 拒绝所有
odds evidence；provider-defined closing 或 caller 自报的 exactness flag 都不能绕过该
状态。未来 odds temporal contract 需先绑定 exact observation authority 后再扩展。

## Version/readiness boundary

- V1 保持 20 features、原顺序、原公式、`ACTIVE_DEFAULT`；points semantics 未改变。
- V-next 保持 17 features、原顺序、`DEFINED_NOT_ACTIVATED`；不因本合同冻结而激活。
- runtime capture contract、provider adapter、standings runtime、historical
  rebuild、training、backtest 和 model activation 均未开始。
- `STANDINGS_RUNTIME_ELIGIBLE=NO`、`STANDINGS_TRAINING_ELIGIBLE=NO`、
  `FEATURE_FRAME_READINESS=NOT_READY`、`REAL_TRAINING_READINESS=NOT_READY`。

本合同是 temporal semantic authority 的 freeze，不是 source readiness 或 training
readiness 的升级。
