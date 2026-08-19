# Standings As-Of Runtime Source Normalization Contract

<!-- lifecycle: permanent -->

状态：`FROZEN`（`standings-asof-runtime-source-normalization/v1`）。这是一个新的
sibling handoff authority；它不修改 `canonical-runtime-capture/v1`、
`standings-asof-engine-input/v1` 或 `standings-asof-engine-consumer/v1` 的冻结语义。

## Authority placement

唯一 registry authority 是：

```text
config/model_feature_contracts.json
└── decision_boundaries.standings_asof_runtime_source_normalization
```

它引用以下既有 authority，但不替代它们：

```text
canonical-model-asof/v1
canonical-runtime-capture/v1
standings-asof-engine-input/v1
standings-asof-engine-consumer/v1
standings/premier-league-point-in-time/v1
```

既有 authority 的角色保持清晰：

```text
runtime capture authority       = capture manifest/integrity semantics
standings input authority       = normalized input semantics
standings consumer authority    = current engine consumer/boundary lifecycle
normalization authority         = capture-to-input handoff contract
ranking authority               = standings mathematics
```

本合同是 `NEW_SIBLING_NORMALIZATION_CONTRACT_V1`，不是 runtime-capture/v1、
standings-asof-engine-input/v1 或 standings-asof-engine-consumer/v1 的 hardening
或 readiness 改写。

## Proof-layer model

本合同冻结八层 proof 的不可替代关系：

```text
L1  CAPTURE_STRUCTURAL_AND_CONTENT_INTEGRITY
L2  CAPTURE_SELECTED_EVIDENCE_BINDING
L3  NORMALIZATION_ENVELOPE_STRUCTURAL_VALIDITY
L4  SOURCE_PAYLOAD_TO_DOMAIN_FACT_SEMANTIC_TRUTH
L5  SOURCE_AUTHORITY
L6  SOURCE_STREAM_CLOSURE
L7  STANDINGS_ASOF_INPUT_CONTRACT_VALIDITY
L8  RUNTIME_FEATURE_ELIGIBILITY
```

L1、L2、L3 都不蕴含 L4 或 L5；L4 不蕴含 L5；L5 不蕴含 L6；L7 不蕴含 L8。
digest match 也不蕴含 source truth。generic capture 和 generic normalization 都不
能从 `SOURCE_AUTHORITY_ID` 字符串、boolean、token、type identity、caller Git SHA 或
digest 生成 source authority。

因此正确链路是：

```text
canonical runtime capture
    ↓
normalization envelope identity / lineage binding
    ↓
future source-specific semantic normalizer + authority boundary
    ↓
standings-asof-engine-input/v1
    ↓
existing T-aware PointInTimeStandingsEngine consumer
```

当前 generic layer 的结果仍是：

```text
NORMALIZATION_ENVELOPE_STRUCTURAL_VALIDITY = PROVEN
CAPTURE_BINDING_VALIDITY                  = PROVEN
OUTPUT_INPUT_BINDING_VALIDITY             = PROVEN only after JS validates actual input
SOURCE_SEMANTIC_NORMALIZATION_VALIDITY    = NOT_PROVEN
SOURCE_AUTHORITY_VALIDITY                 = NOT_PROVEN
SOURCE_STREAM_COMPLETENESS                = NOT_PROVEN
RUNTIME_NUMERIC_ELIGIBILITY               = NO
```

`PROVEN` 的 capture/input binding 只表示身份、内容、结构和 lineage 相互一致，不表示
provider payload 的 domain interpretation 正确。

## Language-neutral envelope

`STANDINGS_ASOF_RUNTIME_SOURCE_NORMALIZATION_ENVELOPE_V1` 是严格字段集合：

```text
NORMALIZATION_CONTRACT_ID
NORMALIZATION_CONTRACT_VERSION
NORMALIZATION_INSTANCE_ID
NORMALIZATION_CONTENT_DIGEST
PREDICTION_CONTEXT
RUNTIME_CAPTURE_BINDING
STANDINGS_EVIDENCE_IDS
EVIDENCE_ATTESTATIONS
FACT_BINDINGS
OUTPUT_STANDINGS_INPUT_BINDING
STATUS
```

`NORMALIZATION_INSTANCE_ID` 是 envelope instance identity；
`NORMALIZATION_CONTENT_DIGEST` 是 self-excluding content identity，二者不可互换。
envelope 不保存 authorization header、cookie、bearer token、password、secret 或 raw
provider request metadata。

### Prediction context

必须绑定：

```text
PREDICTION_CONTEXT_ID
MODEL_ASOF_CONTRACT_ID / MODEL_ASOF_CONTRACT_VERSION
MODEL_DECISION_TIME_UTC = T
FEATURE_AS_OF_UTC       = T
TARGET_MATCH_ID
TARGET_KICKOFF_UTC
```

并满足 `T < TARGET_KICKOFF_UTC`。T 是 model knowledge boundary，真实 kickoff 是
target identity/schedule context；bridge 不允许二者 alias 或互换。

### Runtime capture binding

必须绑定：

```text
RUNTIME_CAPTURE_CONTRACT_ID      = canonical-runtime-capture/v1
RUNTIME_CAPTURE_CONTRACT_VERSION = v1
CAPTURE_INSTANCE_ID
CAPTURE_CONTENT_DIGEST
CAPTURE_SELECTED_EVIDENCE_IDS
```

capture binding validator 复用既有
`validate_runtime_capture_manifest_against_canonical_registry`。它不接受
`captureValidated=true`，也不实现第二个 capture validator。`CAPTURE_INSTANCE_ID` 必须
与 capture content digest distinct。

## Evidence subset and attestations

一个 runtime capture 可以包含多个 feature family 的 selected evidence；standings
bridge 只允许一个显式子集：

```text
STANDINGS_EVIDENCE_IDS ⊆ CAPTURE_SELECTED_EVIDENCE_IDS
```

未 selected evidence 不能进入 standings normalization；selected 但非-standings evidence
也不会自动成为 standings evidence。每个 standings evidence 需要完整 attestation，且
attestation 的 `EVIDENCE_ID`、source family、source record、payload digest/length、
event/effective/observed/captured timestamps、availability proof 和 provenance status
必须与已验证 capture entry exact match。bridge 不能在 capture 验证后重写这些值。

`SOURCE_PROVENANCE_STATUS=UNKNOWN` 是 generic V1 的唯一可消费 attestation 状态；
`EXTERNAL_CONTRACT_BOUND` 需要未来 source-specific authority，当前 fail closed。

## Fact binding taxonomy

`FACT_BINDINGS` 支持这些语义角色：

```text
FIXTURE_UNIVERSE
FIXTURE
FIXTURE_STATUS
RESULT
ADMIN_ADJUSTMENT
TARGET_IDENTITY
```

每个 binding 至少包含稳定 binding ID、semantic role、domain identity、source evidence
IDs、normalized fact digest，并在适用时绑定 canonical match、adjustment 和 primary
availability evidence identity。`SOURCE_ATTESTED` fact 必须有非空 source lineage；
只有明确允许的窄 derivation 才能使用 `CORE_DERIVED`。

允许的 core-derived facts 仅包括基于已验证 target/fixture/T 的：

```text
TARGET_FIXTURE_EXCLUDED
SCHEDULE_NOT_YET_REACHED_AT_T  (scheduledKickoffUtc >= T)
```

这些 derivation 不证明 fixture source authority。六个 source-dependent NO_TABLE reason
可以在 generic envelope 中被表示并绑定 lineage，但 generic layer 不证明其 semantic
truth、source authority 或 stream closure：

```text
PROVEN_POSTPONED_NOT_PLAYED_BY_T
PROVEN_NOT_FINAL_BY_T
PROVEN_NON_TABLE_ELIGIBLE_BY_T
PROVEN_ABANDONED_NON_TABLE_ELIGIBLE_BY_T
PROVEN_VOID_NON_TABLE_ELIGIBLE_BY_T
PROVEN_REPLAY_ORIGINAL_NON_ELIGIBLE_BY_T
```

## Lineage bridge

standings input 的 `sourceLineage.evidenceRefs` 必须使用 envelope 中 exact
`EVIDENCE_ID`。`sourceRecordRef` 的 deterministic bridge 是：

1. 单 evidence 且 `SOURCE_RECORD_ID` 非 null：exact source record identity；
2. 多 evidence 且存在 source record：由 ordered `(EVIDENCE_ID, SOURCE_RECORD_ID)` 集合
   计算 deterministic capture-record-set digest；
3. source record 全为 null：由 `CAPTURE_CONTENT_DIGEST + sorted EVIDENCE_ID set` 计算
   collision-resistant internal fallback。

fallback 只是 lineage identity，不证明 source authority。availability `proofRef` 必须
绑定 exact primary availability `EVIDENCE_ID`，不能是无法追溯的 opaque string。result
availability 不能只依赖 event time 或 captured-at；availability metadata 也不能由
normalizer invent 或 rewrite。

## Output-input binding

JS-side validator
`src/infrastructure/standings/StandingsAsOfRuntimeSourceNormalizationContract.js`
接收 envelope 和实际 raw candidate input，复用既有
`validateStandingsAsOfEngineInput`，不调用 `PointInTimeStandingsEngine`。它验证：

```text
standings-asof-engine-input/v1 + v1
standings/premier-league-point-in-time/v1 + v1
canonical input digest
T / feature-as-of / target / target kickoff
fixture universe reference ID
fixture state identity set
administrative adjustment identity set
lineage and proofRef compatibility
```

caller 提供的 `inputValid=true`、digest alone、`trusted=true` 或 source-authority boolean
不会绕过实际 validator。input binding proven 也不等于 source semantic normalization
proven，更不等于 runtime eligibility。

## Deterministic digest

normalization content digest 使用：

```text
SHA-256
STABLE_VALUE_SORTED_KEYS_COMPACT_UTF8_JSON
SELF_EXCLUDING_CANONICAL_NORMALIZATION_ENVELOPE
```

object keys 递归排序；timestamp 输入限定为 ISO-8601 UTC seconds、可选 1–6 位 fraction、
`Z` 或 `+00:00`，再 canonicalized 为 UTC millisecond form。以下数组是非
语义集合，输入可任意排列，digest 前 canonicalized：

```text
STANDINGS_EVIDENCE_IDS             lexical ascending
CAPTURE_SELECTED_EVIDENCE_IDS     lexical ascending
EVIDENCE_ATTESTATIONS              EVIDENCE_ID ascending
FACT_BINDINGS                      BINDING_ID ascending
SOURCE_EVIDENCE_IDS                lexical ascending
FIXTURE_STATE_IDS                  lexical ascending
ADMINISTRATIVE_ADJUSTMENT_IDS     lexical ascending
```

其他 carrying semantic order 的数组不排序。Python 与 JS 使用同一 canonical vectors；
当前要求为至少 20/20 digest equality，并包含 key/evidence/fact permutations、Unicode、
null source record IDs 和允许的 timestamp precision。

## Pure validators and current non-goals

Python capture-side validator：

```text
src/ml/inference/standings_asof_runtime_source_normalization_contract.py
```

JS input-side validator：

```text
src/infrastructure/standings/StandingsAsOfRuntimeSourceNormalizationContract.js
```

二者纯内存、确定性、无 wall-clock/network/DB/Git/filesystem dependency。当前没有：

- FotMob、Premier League、Football-Data 或任意 provider selection；
- source-specific payload parser；
- source-specific normalizer 或 authority contract；
- fixture universe/status/result/admin stream closure；
- capture storage/pipeline 或 runtime wiring；
- target identity authority；
- GD-A03/runtime/model serving/training/backtest/prediction integration。

允许状态：

```text
SOURCE_SPECIFIC_PAYLOAD_PARSER_COUNT = 0
RUNTIME_STANDINGS_PROVIDER_SELECTED  = NO
SOURCE_SPECIFIC_NORMALIZER_IMPLEMENTED = NO
SOURCE_SPECIFIC_AUTHORITY_CONTRACT_IMPLEMENTED = NO
RUNTIME_SOURCE_TO_STANDINGS_NORMALIZATION_PROVEN = NO
STANDINGS_RUNTIME_ELIGIBLE = NO
STANDINGS_TRAINING_ELIGIBLE = NO
```

未来 source-specific integration 若要升级 proof，必须另外冻结 source family、provider
authority identity、payload schema/version、normalizer implementation identity、semantic
mapping、availability interpretation、fixture/result/status/adjustment mapping 和适用的
stream-closure semantics；本 generic contract 不预先授予这些权限。
