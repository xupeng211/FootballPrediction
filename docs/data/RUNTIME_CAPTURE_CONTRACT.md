# Canonical Runtime Capture Contract

<!-- lifecycle: permanent -->

状态：`FROZEN`（`canonical-runtime-capture/v1`）。本文档定义如何为一个
Option-C prediction context 记录并验证“实际绑定到该决策的证据集合”。它不实现
provider、source adapter、capture storage、数据库 schema、feature generator 或
runtime pipeline。

## Authority and relationship to model-as-of

唯一 registry authority 是：

```text
config/model_feature_contracts.json
└── decision_boundaries.runtime_capture
```

`canonical-model-asof/v1` 仍是时间语义 authority：它定义允许知道信息的时刻
`MODEL_DECISION_TIME_UTC = T`，并要求 `FEATURE_AS_OF_UTC = T` 且 prematch
`T < TARGET_KICKOFF_UTC`。本合同只定义怎样把一个已绑定的 context、selected
evidence identity 和精确 payload content 记录下来；它没有第二套 T 逻辑。

feature contract binding 由 `feature_contract_registry.py` 在读取并验证 canonical
registry 后签发不可变的 `ValidatedFeatureContractBinding`。纯 validator 接收这个
typed binding，而不是任意 `Mapping[str, str]`；因此
`FEATURE_CONTRACT_REFERENCE_MATCHED` 与
`CANONICAL_FEATURE_CONTRACT_AUTHORITY_PROVEN` 是两个有明确 trust boundary 的结果。
caller 自建 mapping、boolean 或字符串不能建立 canonical feature authority。

## Capture manifest

一个 manifest 的顶层字段是严格集合：

```text
RUNTIME_CAPTURE_CONTRACT_ID
RUNTIME_CAPTURE_CONTRACT_VERSION
CAPTURE_INSTANCE_ID
CAPTURE_CONTENT_DIGEST
MANIFEST_FINALIZED_AT_UTC
PREDICTION_CONTEXT
PROVENANCE
EVIDENCE
SELECTED_EVIDENCE_IDS
STATUS
```

`CAPTURE_INSTANCE_ID` 是一次 capture package 的不透明 immutable identity；
`CAPTURE_CONTENT_DIGEST` 是 manifest metadata 的 canonical content identity。二者
不可互换。manifest digest 是对删除自身 `CAPTURE_CONTENT_DIGEST` 字段后的
canonical manifest 做 SHA-256，不是 manifest 文件的 raw-file SHA-256。

`PREDICTION_CONTEXT` 必须精确绑定：

```text
PREDICTION_CONTEXT_ID
MODEL_ASOF_CONTRACT_ID / MODEL_ASOF_CONTRACT_VERSION
MODEL_DECISION_TIME_UTC
FEATURE_AS_OF_UTC
TARGET_MATCH_ID
TARGET_KICKOFF_UTC
FEATURE_CONTRACT_ID / FEATURE_CONTRACT_VERSION
PREDICTION_GENERATED_AT_UTC      # 可为 null；只是 output telemetry
POST_DECISION_INFORMATION_DEPENDENCY_COUNT = 0
```

同一个 context 不得从 `T1` 原地改成 `T2`；同一 target 的另一个决策时刻必须
使用新的 `PREDICTION_CONTEXT_ID`。

## Evidence and selected decision set

`EVIDENCE` 是 package 中可验证的 captured evidence entries；它不等于模型实际
使用的输入。`SELECTED_EVIDENCE_IDS` 是显式、不可省略的 decision evidence set。
只在 selected set 中的 evidence 才能成为该 context 的模型输入；未 selected 的
额外 entry 不会自动升级为输入。

每个 evidence entry 必须绑定：

```text
EVIDENCE_ID
SOURCE_FAMILY
SOURCE_AUTHORITY_ID       # 可为 null；capture 不创造 authority
SOURCE_RECORD_ID           # 可为 null；适用时用于稳定 identity
PAYLOAD_KIND
PAYLOAD_CONTENT_DIGEST
PAYLOAD_BYTE_LENGTH
SOURCE_EVENT_TIME_UTC      # 可为 null
SOURCE_EFFECTIVE_TIME_UTC  # 可为 null
SOURCE_OBSERVED_AT_UTC     # 可为 null，取决于 proof kind
SOURCE_CAPTURED_AT_UTC     # required
AVAILABILITY_PROOF_KIND
AVAILABILITY_PROOF_DATA
SOURCE_PROVENANCE_STATUS
```

`SOURCE_EVENT_TIME_UTC` 只证明事件发生时间，不能证明系统在 T 前知道它。
`SOURCE_CAPTURED_AT_UTC` 只证明本系统捕获/保存时间，默认不能替代
`SOURCE_OBSERVED_AT_UTC`。source authority 必须来自另一个 source-specific
contract；generic capture validator 只保存 binding，不能把 `UNKNOWN` 改成
verified。当前 V1 尚无 canonical external source-authority resolver，因此
`SOURCE_AUTHORITY_ID`、`EXTERNAL_CONTRACT_BOUND` 或
`PROVEN_BY_SOURCE_CONTRACT` 的 caller-authored positive claim 都 fail closed；
正向证明必须由未来经批准的 source-specific authority boundary 提供。capture
本身不建立 source authority。

允许的 availability proof 与 model-as-of/v1 相同：

1. `EXACT_OBSERVATION_TIMESTAMP`；
2. `EXACT_EFFECTIVE_TIMESTAMP_WITH_SOURCE_OBSERVATION_PROOF`；
3. `BOUNDED_INTERVAL_ENTIRELY_BEFORE_T`，且 interval end 必须严格早于 T。

unknown、post-T、overlap/precision 不足均 fail closed。selected evidence 的
`SOURCE_CAPTURED_AT_UTC` 也必须 `<= T`。因此本 v1 采用：

```text
CAPTURE_TIME_RELATION_TO_T=CAPTURE_MUST_BE_LTE_T
```

`MANIFEST_FINALIZED_AT_UTC` 是 package telemetry；它可以在 T 之后，不能使
post-T evidence 变成 eligible，也不能替代 selected evidence 的 capture 或
observation proof。

## Content integrity and deterministic replay

payload validator 接收外部显式提供的 `bytes`，不读文件、不访问网络、不访问 DB。
每个 payload 必须满足 SHA-256 与 `PAYLOAD_BYTE_LENGTH`。manifest canonicalization
与已有 `StableValue.stableStringify` 约定一致：递归排序 object keys、保留数组的
语义顺序、compact UTF-8 JSON。evidence entries 按 `EVIDENCE_ID` 排序，selected
IDs 按字典序排序；因此非语义的 manifest permutation 产生相同
`CAPTURE_CONTENT_DIGEST`。

validator fail closed on：

- duplicate `EVIDENCE_ID` 或 duplicate/conflicting `SOURCE_RECORD_ID`；
- missing selected evidence / missing payload / unbound payload；
- payload byte、length 或 digest mismatch；
- manifest unknown fields、contract/version drift 或 self-excluding digest mismatch；
- secret-bearing metadata（authorization、token、cookie、session、password、API key 等）；
- caller-supplied Git SHA 被当作 repository provenance。

`STATUS` 分开表达：

```text
STRUCTURAL_CAPTURE_VALIDITY
SOURCE_AUTHORITY_VALIDITY
TEMPORAL_ELIGIBILITY_VALIDITY
FEATURE_DEPENDENCY_COMPLETENESS
```

结构和 payload integrity 通过，不代表 source authority 或 feature dependency
complete。generic v1 validator 没有 source-specific authority 或 feature-dependency
证明输入，因此当前不会接受 `PROVEN_BY_SOURCE_CONTRACT` 或
`SOURCE_PROVENANCE_STATUS=EXTERNAL_CONTRACT_BOUND`，也不会接受
`FEATURE_DEPENDENCY_COMPLETENESS=PROVEN`。当前
generic contract 的 source normalization、feature numeric replay、train/inference
replay 都保持 `NOT_PROVEN`。

## Replay boundary

冻结的未来离线链路是：

```text
CAPTURE_PACKAGE
  → pure manifest/context validation
  → exact selected evidence identities
  → exact payload digest verification
  → future source-specific normalization
  → future feature/engine input
```

本合同已覆盖 generic structural/content-integrity boundary；它没有实现 storage
pipeline、provider replay、standings T-aware engine input、feature numeric replay
或 training replay。不存在 wall-clock authority，validator 不调用 `now()`、
`time()`、network 或 Git。

## Security and readiness

capture metadata 默认禁止保存 authorization headers、bearer tokens、API keys、
cookies、session IDs、passwords、signed credentials 以及不必要的 request dump；
只保留 identity、authority binding、temporal proof、integrity 与 replay 所需字段。

现有 truth 不变：

```text
ODDS_PROVIDER_DEFINED_CLOSING_AVAILABLE=YES
ODDS_EXACT_CLOSING_TIMESTAMP_PROVEN=NO
ODDS_STRICT_DECISION_TIME_AVAILABLE=NO
STRICT_DECISION_TIME_VALUE_EVALUATION=NOT_READY

HISTORICAL_STANDINGS_COVERAGE=887/888
HISTORICAL_ENGINE_GD_A03_PARITY=888/888
CURRENT_KICKOFF_EXCLUSIVE_ROWS_RELABELED=NO
```

V1 仍为 20 features / `ACTIVE_DEFAULT`；V-next 仍为 17 features /
`DEFINED_NOT_ACTIVATED`。本合同冻结不实现 runtime storage、provider、standings
runtime、training、backtest、prediction 或 model activation。
