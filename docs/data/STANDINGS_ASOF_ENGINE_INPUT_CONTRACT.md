# Standings As-Of Engine Input Contract

<!-- lifecycle: permanent -->

状态：`FROZEN`（`standings-asof-engine-input/v1`）。本文档冻结进入现有
`PointInTimeStandingsEngine` 消费边界所需的 normalized as-of input shape、时间语义、
fixture state 分类和确定性 digest；本阶段不实现 engine consumer、provider 或 runtime
source。

## Canonical authority

唯一 registry authority 是：

```text
config/model_feature_contracts.json
└── decision_boundaries.standings_asof_engine_input
```

它与同一 registry 中的以下合同保持显式引用关系：

```text
STANDINGS_CONTRACT_ID         = standings/premier-league-point-in-time/v1
MODEL_ASOF_CONTRACT_ID        = canonical-model-asof/v1
RUNTIME_CAPTURE_CONTRACT_ID   = canonical-runtime-capture/v1
ENGINE_IMPLEMENTATION_FAMILY  = PointInTimeStandingsEngine
```

`standings/premier-league-point-in-time/v1` 仍是 3/1/0、points → goal difference →
goals scored、shared positions、异常比赛和行政调整规则的唯一 standings semantic
authority。本合同不复制或改写这些排名规则。`PointInTimeStandingsEngine` 的 identity
也不包含 caller-supplied Git SHA；repository provenance 属于外部审计边界。

## Purpose and non-purpose

对目标比赛 `M` 和 decision time `T`，本合同回答：哪一个完整、显式、normalized 的
fixture state 可以传给既有 standings engine consumer，以及如何把“在 T 尚未到达”与
“在 T 应有证据但缺失”分开。

本合同不是：

- 新的 standings ranking engine 或第二套 ranking authority；
- provider、Premier League/FotMob/PulseLive runtime adapter；
- runtime capture storage 或 source-specific normalization proof；
- target identity authority、DB/raw writer、training/backtest/prediction contract。

## T and target kickoff

每个 input 必须同时保存：

```text
MODEL_DECISION_TIME_UTC = T
FEATURE_AS_OF_UTC       = T
TARGET_KICKOFF_UTC      = target.targetKickoffUtc（真实目标 kickoff）
```

并满足：

```text
FEATURE_AS_OF_UTC = MODEL_DECISION_TIME_UTC
MODEL_DECISION_TIME_UTC < TARGET_KICKOFF_UTC
TARGET_KICKOFF_UTC_IS_EVALUATION_BOUNDARY = NO
MODEL_DECISION_TIME_UTC_IS_ASOF_EVALUATION_BOUNDARY = YES
```

validator 不把 `targetKickoffUtc` 改成 T；目标 fixture 的 identity、schedule 和排除状态
必须仍然绑定真实 kickoff。只在调用前删除 T 后不可用记录，也不能证明 as-of 兼容性：它
会丢失“not yet eligible”和“required evidence missing”的区别。

## Normalized input shape

`src/infrastructure/standings/StandingsAsOfEngineInputContract.js` 是纯内存 validator/
canonicalizer。它接收显式的 registry boundary、已有 branded standings binding、T、target、
fixture universe、fixture states 和 administrative-adjustment states；不读取文件、DB、
环境、网络、Git 或墙钟，也不调用 `PointInTimeStandingsEngine`。

输入的顶层边界是严格集合：

```text
contractBoundary
standingsContractBinding
modelDecisionTimeUtc
featureAsOfUtc
target
fixtureUniverse
fixtureStates
administrativeAdjustments
```

### Fixture universe

`fixtureUniverse.reference` 必须包含稳定 reference id/version、reference SHA-256 和完整
`fixtureIds` 集合；`fixtureUniverse.fixtures` 必须逐条提供同一 competition/season 的
canonical match identity、双方 team、scheduled kickoff 和 lineage。reference 的 ID 集合
与 fixture rows 必须完全相等，不能靠省略不方便的 fixture 让表格看起来完整。

validator 能证明：

```text
FIXTURE_UNIVERSE_REFERENCE_MATCH = STRUCTURALLY_VALID
FULL_FIXTURE_STATE_COVERAGE     = EXACTLY_ONE_STATE_PER_FIXTURE
```

validator 不能证明：

```text
CANONICAL_FIXTURE_UNIVERSE_AUTHORITY_PROVEN = NOT_PROVEN
```

真实 canonical schedule/source authority 仍需未来受控 integration。

### Structural reference vs source-stream closure

合同把四类 closure 分开保存，避免“输入 rows 自洽”被误报成“来源完整”：

```text
FIXTURE_UNIVERSE_REFERENCE_MATCH = STRUCTURALLY_VALID
FIXTURE_UNIVERSE_CLOSURE         = NOT_PROVEN
FIXTURE_STATUS_EVIDENCE_CLOSURE  = NOT_PROVEN
RESULT_EVIDENCE_CLOSURE           = NOT_PROVEN
ADMIN_ADJUSTMENT_STREAM_CLOSURE  = NOT_PROVEN
```

reference 的 fixture ID 集合与传入 rows 相等，只能证明 caller input 的结构一致；它不能
证明 caller 没有遗漏 fixture，也不能证明 status/result/administrative-adjustment stream
已经被真实 canonical source 完整收闭。absence of evidence 仍不能升级为
`NO_TABLE_RESULT_AT_T`。

### Fixture as-of states

每个 fixture 必须恰好有一个 state；重复、遗漏、未知 identity 或未知 state 都 fail closed。
每个 state 必须有显式 `basis.reasonCode` 与非空 `basis.evidenceRefs`，不接受裸的
`eligible=true`、`known=true`、`not_required=true` 或 `proven=true`。

| State                            | 语义                                                             |                                               是否 blocker |
| -------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------: |
| `RESULT_AVAILABLE_AT_T`          | final、table-eligible result 及其 T 前 availability proof 已绑定 |                否（仅结构有效；source authority 仍未证明） |
| `NO_TABLE_RESULT_AT_T`           | T 时刻不应有结果进入 standings，且有明确 reason/reference        | 否（结构层；source-dependent temporal proof 仍可能未证明） |
| `REQUIRED_EVIDENCE_MISSING_AT_T` | 对 T 前的 prior obligation 无法诚实证明 result 或 no-table 状态  |                                                         是 |
| `ASOF_STATE_AMBIGUOUS`           | 状态/时间/来源冲突无法在 T 解析                                  |                                                         是 |
| `TARGET_FIXTURE_EXCLUDED`        | 唯一目标 fixture 明确排除，不得贡献自身 prematch result          |                                                         否 |

`NO_TABLE_RESULT_AT_T` 只接受下列冻结 reason taxonomy：

```text
SCHEDULE_NOT_YET_REACHED_AT_T
PROVEN_POSTPONED_NOT_PLAYED_BY_T
PROVEN_NOT_FINAL_BY_T
PROVEN_NON_TABLE_ELIGIBLE_BY_T
PROVEN_ABANDONED_NON_TABLE_ELIGIBLE_BY_T
PROVEN_VOID_NON_TABLE_ELIGIBLE_BY_T
PROVEN_REPLAY_ORIGINAL_NON_ELIGIBLE_BY_T
```

其中 `SCHEDULE_NOT_YET_REACHED_AT_T` 是唯一由 generic core 直接推导的 temporal relation：
它要求 supplied canonical fixture row 的 scheduled kickoff 不早于 T；prior fixture 不能用
此 reason 掩盖缺失数据。

其余 `PROVEN_*` reason 都依赖未来受信任的 status/source integration。generic core 只验证
reason taxonomy、fixture timing 不矛盾、reference 字符串的结构和确定性 lineage；它不证明
reference 对应的 evidence object 存在、不证明 status truth，也不证明该 status 在 T 前可用。
因此 non-empty `evidenceRefs` 不是 external truth proof，`PROVEN_*` 名称也不是 core proof。
source-dependent no-table state 可以保持 `semanticStatus=STRUCTURALLY_VALID`，但它的
`TEMPORAL_ELIGIBILITY_VALIDITY=NOT_PROVEN`、`SOURCE_DEPENDENT_NO_TABLE_STATUS_PROOF=
NOT_PROVEN_BY_CORE`、`RUNTIME_NUMERIC_ELIGIBILITY=NO`。这明确表示：
`STRUCTURALLY_VALID != ENGINE_CONSUMPTION_ELIGIBLE`。

`REQUIRED_EVIDENCE_MISSING_AT_T` 与 `ASOF_STATE_AMBIGUOUS` 都保留在 normalized input 中，
并继续使 engine-compatible semantic status 为 `BLOCKED`。generic core 不证明
`CANONICAL_FIXTURE_UNIVERSE_AUTHORITY_PROVEN`、fixture/status/result stream closure 或
source authority。

未来 engine consumer 必须同时满足：

```text
ENGINE_CONSUMPTION_REQUIRES_TEMPORAL_ELIGIBILITY_PROVEN = YES
ENGINE_CONSUMPTION_REQUIRES_SOURCE_DEPENDENCY_GATES    = YES
```

本任务不实现该 consumer 或任何 status/source authority。

### Result availability by T

`RESULT_AVAILABLE_AT_T` 至少要求：canonical match/team identity、final score、
`tableEligibility=ELIGIBLE`、`finalityStatus=FINAL`、disposition、actual eligible event
time、result lineage，以及 availability proof reference。

availability proof 复用 `canonical-model-asof/v1` 的三种形式：

```text
EXACT_OBSERVATION_TIMESTAMP
EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF
BOUNDED_INTERVAL_ENTIRELY_BEFORE_T
```

`SOURCE_EVENT_TIME_UTC` 不能单独证明可用；`SOURCE_CAPTURED_AT_UTC` 不能替代
`SOURCE_OBSERVED_AT_UTC`；观察或证明在 T 之后的 evidence 被拒绝；与 T 重叠的 interval
fail closed。event/result time 与 availability time 永不别名。

### Administrative adjustment as-of states

每个 adjustment 必须有唯一 `adjustmentId`、delta、effective-time evidence、lineage 和
availability proof，并归入：

```text
EFFECTIVE_AND_AVAILABLE_AT_T
KNOWN_NOT_EFFECTIVE_AT_T
ASOF_ADJUSTMENT_AMBIGUOUS
```

exact effective time 在 T 前（含 T）且可用时才可进入第一类；未来生效但已在 T 前被知道
的 adjustment 可进入第二类；effective interval 在 T 上重叠时进入第三类并阻塞。未来才
观察到的 adjustment 不能用于较早 T。空 adjustment array 也不证明 adjustment stream
complete。

## Trust and readiness separation

validator 分开返回以下状态：

```text
ENGINE_INPUT_STRUCTURAL_VALIDITY = PROVEN / rejected
FIXTURE_STATE_COVERAGE_VALIDITY  = PROVEN / rejected
NO_TABLE_STATE_REFERENCE_VALIDITY = STRUCTURALLY_VALID
TEMPORAL_ELIGIBILITY_VALIDITY   = PROVEN / NOT_PROVEN
SOURCE_DEPENDENT_NO_TABLE_STATUS_PROOF = NOT_PROVEN_BY_CORE
SOURCE_AUTHORITY_VALIDITY        = NOT_PROVEN
SOURCE_STREAM_COMPLETENESS       = NOT_PROVEN
RUNTIME_NUMERIC_ELIGIBILITY     = NO
```

generic core 不接受 caller 自报的 source closure、fixture-universe authority、fixture
status authority、result stream completeness、admin stream completeness 或 Git SHA
provenance。`canonical-runtime-capture/v1` 的存在只定义未来边界，不证明 Python capture
已经跨语言来源到此 JS object；当前 `RUNTIME_CAPTURE_TO_JS_PROVEN=NOT_PROVEN`。
`STRUCTURALLY_VALID` 只表示输入 shape、identity、coverage 和允许的 reference 结构通过；
它不等同于 temporal proof 或 runtime/engine eligibility。

因此当前准确状态为：

```text
STANDINGS_ASOF_ENGINE_INPUT_CONTRACT_FROZEN=YES
STANDINGS_ASOF_INPUT_STRUCTURAL_VALIDATOR_IMPLEMENTED=YES
POINT_IN_TIME_STANDINGS_ENGINE_ASOF_CONSUMER_IMPLEMENTED=NO
STANDINGS_ENGINE_ASOF_COMPATIBILITY=VERSIONED_ASOF_ENGINE_INPUT_CONTRACT_FROZEN_CONSUMER_NOT_IMPLEMENTED
RUNTIME_SOURCE_TO_STANDINGS_NORMALIZATION_PROVEN=NO
STANDINGS_SOURCE_CLOSURE_PROVEN=NO
STANDINGS_RUNTIME_ELIGIBLE=NO
STANDINGS_TRAINING_ELIGIBLE=NO
```

## Deterministic digest

canonical digest 使用既有 `StableValue.stableStringify`（sorted object keys、compact
UTF-8 JSON）和 `sha256Text`。digest 绑定 contract/versions、T、target identity/kickoff、
competition/season、fixture-universe reference、全部 fixture rows、全部 fixture states、
result facts、reason codes、evidence/lineage refs 和全部 adjustment states。

语义集合按以下规则排序后再 digest：

```text
fixture rows/states → canonicalMatchId ascending
administrative adjustments → adjustmentId ascending
evidenceRefs → lexicographic ascending
```

因此 fixture-state 或 adjustment-state permutation 不改变 digest；T、target、reason、
evidence、score、contract version 或 referenced contract tamper 会改变 digest 或直接被
拒绝。digest 不包含 wall-clock telemetry，也不包含自排除的 digest 字段。

## Historical and runtime boundary

既有 `standings/premier-league-point-in-time/v1`、`KICKOFF_EXCLUSIVE_POINT_IN_TIME`、
`SOURCE_EVENT_TIME_LT_TARGET_KICKOFF`、887/888 historical coverage 与 888/888
engine↔GD-A03 parity 均保持不变。`47_20232024_4193789` 仍因
`ADMIN_ADJUSTMENT_EFFECTIVE_TIME_AMBIGUOUS` unavailable。

历史 rows 仍是 `KICKOFF_EXCLUSIVE_REFERENCE_PROJECTION`：不 rebuild、不 relabel 为 T-aware
rows，也没有 arbitrary-T numeric parity proof。本 PR 不修改 PointInTimeStandingsEngine
的 computation semantics，不创建第二 engine，不启动 provider、capture storage、source
normalization、GD-A04、odds、training、backtest 或 prediction。

## Validation surface

行为覆盖位于：

```text
tests/unit/standings_asof_engine_input_contract.test.js
tests/unit/ml/test_standings_asof_engine_input_contract.py
```

前者当前覆盖 73 个 semantic/tamper cases，其中包含 15 个 NO_TABLE source-proof regression cases；后者验证同一 singular registry 的 frozen boundary
与 drift fail-closed。后续 engine consumer 必须复用此 normalized shape 和 digest，不得把
T 转译为 target kickoff，也不得另建 standings engine 或第二 temporal registry。
