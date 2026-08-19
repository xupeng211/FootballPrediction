# Standings As-Of Engine Consumer

<!-- lifecycle: permanent -->

状态：`FROZEN`（`standings-asof-engine-consumer/v1`）。这是现有
`PointInTimeStandingsEngine` 的 consumer/integration boundary，不是新的 standings
engine、ranking contract、provider 或 source authority。

## 两个 authority 的边界

同一 canonical registry 中的两个 sibling boundary 各自负责不同事实：

```text
config/model_feature_contracts.json
├── decision_boundaries.standings_asof_engine_input
│   └── standings-asof-engine-input/v1
└── decision_boundaries.standings_asof_engine_consumer
    └── standings-asof-engine-consumer/v1
```

`standings-asof-engine-input/v1` 是不可变的 input semantics authority。其既有
`readiness.engine_consumer_implemented=NO` 字段属于冻结的 V1 input boundary，本任务
没有修改它。`standings-asof-engine-consumer/v1` 是当前 consumer implementation 和
boundary policy 的 lifecycle authority；它引用 input、
`standings/premier-league-point-in-time/v1`、`canonical-model-asof/v1`、
`canonical-runtime-capture/v1` 以及现有 `PointInTimeStandingsEngine` binding。

因此：input authority = input semantics；consumer authority = current consumer
implementation/boundary。后者不会升级 source authority 或 runtime readiness。

## One engine, two explicit policies

排名数学只有一个内部 kernel：`applyResult`、3/1/0、W/D/L、GF/GA/GD、行政积分、official
points、strict ordering 和 shared positions 均只实现一次。engine 内部仅有两个 evaluation
boundary policy：

| Path                                 | Evaluation context                    | Result                      | Administrative adjustment   |
| ------------------------------------ | ------------------------------------- | --------------------------- | --------------------------- |
| legacy `computeStandingsSnapshot(s)` | `targetKickoffUtc`                    | strict `< targetKickoffUtc` | strict `< targetKickoffUtc` |
| as-of `computeStandingsAsOfSnapshot` | validated `MODEL_DECISION_TIME_UTC=T` | inclusive `<= T`            | inclusive `<= T`            |

legacy exact-kickoff result 继续排除，legacy exact-kickoff adjustment 继续不生效；as-of
exact-`T` result 在 final、table-eligible、availability proof valid 时可以进入，exact-`T`
adjustment 也可以生效。`T` 永远不被重标为 target kickoff，target kickoff 也永远不被
当作 T。

## Raw input and fail-closed gates

`computeStandingsAsOfSnapshot(rawInput)` 只接受 raw
`standings-asof-engine-input/v1` shape，并在函数内部直接调用
`validateStandingsAsOfEngineInput`。调用者不能通过 `validatedInput`、
`consumerEligible`、`evaluationBoundaryUtc`、`trusted` 或 source-authority boolean
自报验证/eligibility；没有 generic `computeStandingsAtTime(input, callerTime)` 或
`computeWithBoundary(input, options)` 导出。没有 private token/type identity 作为安全边界。

验证和 consumer gate 在 transformation 与 ranking kernel 之前完成：

- malformed/tampered contract、T、target、fixture coverage、result availability 或
  unknown state/reason 直接 reject；
- `REQUIRED_EVIDENCE_MISSING_AT_T`、`ASOF_STATE_AMBIGUOUS`、
  `ADMIN_ADJUSTMENT_ASOF_AMBIGUOUS` 返回 deterministic `UNAVAILABLE`，positions 为
  `null`，`engine_computation_status=NOT_EXECUTED`；
- 六个 source-dependent `NO_TABLE_RESULT_AT_T` reason 即使结构上有效，也因
  `TEMPORAL_ELIGIBILITY_VALIDITY=NOT_PROVEN` 返回
  `STANDINGS_SOURCE_CLOSURE_UNPROVEN`，不得进入 numeric kernel；
- `SCHEDULE_NOT_YET_REACHED_AT_T` 由 core 证明 scheduled kickoff `>= T` 时可消费；它
  不会被当成 prior missing evidence；
- state 不得先被删除、过滤或重标后再获取 eligibility；`STRUCTURALLY_VALID` 不等于
  consumer-eligible。

## Output and provenance

executed output 保留 standings positions、table diff、diagnostic table state、source
event IDs 和 applied adjustment IDs，并增加：

```text
consumer_contract_id/version/status
input_contract_id/version
model_decision_time_utc
feature_as_of_utc
target_kickoff_utc
evaluation_boundary_policy
asof_input_digest
ranking_contract_id/version
engine_implementation_id/identity_digest
ranking_projection_input_digest
ranking_projection_provenance_digest
consumer_provenance_digest
engine_computation_status
runtime_numeric_eligibility
source_authority_validity
```

`consumer_provenance_digest` 使用 `StableValue.stableStringify` + SHA-256，至少绑定
consumer/input/ranking contract identities、input canonical digest、T、feature as-of、
target kickoff、policy、existing engine identity、numeric projection、source event IDs、
applied adjustment IDs 和 outcome status。它是独立于 legacy `provenance_digest` 的
as-of provenance；legacy digest 不单独证明 T。即使两个 T 产生相同 numeric positions，
T 仍在 digest 中，因而 provenance 必须不同。

对语义有效但不可消费的 input，输出不隐藏 fabricated table：positions 为 `null`、
`engine_computation_status=NOT_EXECUTED`、reason codes 非空。对可消费 input，kernel
可以产生 contract-semantic numeric projection，但 `runtime_numeric_eligibility=NO`、
`source_authority_validity=NOT_PROVEN` 保持不变。

## Integration and readiness boundary

本 consumer 不接入 `GdA03StandingsIntegration`、GD-A03 assembler、prediction/feature
runtime、provider pipeline、training 或 model serving。GD-A03 继续调用 legacy
kickoff-exclusive API，历史 `887/888` coverage、`888/888` engine parity、唯一
unavailable target `47_20232024_4193789` 和原有 legacy digests 保持不变；历史 rows 不
rebuild、不 relabel。

本实现只证明 T-aware contract-semantic consumer computation：

```text
STANDINGS_ASOF_ENGINE_CONSUMER_IMPLEMENTED = YES
CONSUMER_SEMANTIC_NUMERIC_COMPUTATION     = YES
SOURCE_AUTHORITY_VALIDITY                 = NOT_PROVEN
SOURCE_STREAM_COMPLETENESS                = NOT_PROVEN
RUNTIME_SOURCE_TO_STANDINGS_NORMALIZATION = NO
TARGET_IDENTITY_AUTHORITY                 = NO
STANDINGS_RUNTIME_ELIGIBLE                = NO
STANDINGS_TRAINING_ELIGIBLE               = NO
RUNTIME_CAPTURE_STORAGE/PIPELINE          = NO
```

因此它不是 live standings-as-of proof、runtime provider、capture implementation、
training readiness 或 strict decision-time value evaluation。

## Runtime-source normalization boundary

`standings-asof-runtime-source-normalization/v1` 是 consumer 之前的独立 handoff
authority。它只绑定已验证 runtime capture、standings evidence subset、fact lineage 和
candidate `standings-asof-engine-input/v1`；它不修改本 consumer 的 frozen subtree，也不
把 envelope/input binding validity 升级为 source semantic normalization、source authority
或 runtime eligibility。

该 validator 不调用 `PointInTimeStandingsEngine`，也不接入 GD-A03、prediction/runtime、
provider、capture storage 或 training。consumer 仍只接受自身 raw input validator 的
结果；normalization envelope 不能通过 caller boolean、digest、token 或 type identity
绕过 consumer gates。
