# GD-A03 Point-in-Time Prior-State Feature View Contract

<!-- lifecycle: permanent -->

状态：GD-A03 V1 implementation contract。本文档是当前的数值 lineage 边界；历史
`docs/_reports` 只能作为背景证据，不能覆盖本文档或 runtime contract。

## 目标与边界

GD-A03 回答：对目标比赛 `M`，在 `M` 开球前，哪些数值可以只从严格早于
`M` 的 canonical schedule 与 GD-A02 factual evidence 可重复推导？

V1 的唯一 cutoff 是：

```text
FEATURE_CUTOFF_POLICY=TARGET_KICKOFF_EXCLUSIVE
source_match_kickoff < target_match_kickoff
```

这里的 source time 是 source match 的 kickoff/event time。它证明的是历史比赛
顺序和 current-match leakage 边界，不证明 T-24H、T-1H、bookmaker decision time，
也不把 `captured_at` 当成 `feature_observed_at`。因此：

```text
STRICT_DECISION_TIME_VALUE_EVALUATION=NOT_READY
```

### System-wide model-as-of boundary

`canonical-model-asof/v1` 已在同一 `config/model_feature_contracts.json` registry
中冻结为系统级 temporal policy。它要求未来每个 prediction context 显式提供
`MODEL_DECISION_TIME_UTC=T`，并令 `FEATURE_AS_OF_UTC=T`；`TARGET_KICKOFF_UTC` 仍是
独立的 target scheduling field。它不会改写本 GD-A03 的历史语义，也不会把既有
kickoff-exclusive rows 自动重标为 decision-time rows。完整定义见
`docs/data/MODEL_ASOF_CONTRACT.md`。

因此本文件下述 V1 cutoff 仍只回答“目标 kickoff 前的历史状态”，不回答某个更早
prediction decision time 可知什么。`standings-asof-engine-input/v1` 现已在同一
canonical registry 中冻结 T-aware standings normalized input、source availability proof
和 fixture-state taxonomy；但其 engine consumer、source-specific normalization 与
replayable runtime capture 仍未实现。本文件的历史 rows 不因此被重建或重标为 T-aware rows。

GD-A02 的 `score`、`result`、`xG`、shots、possession、events、shotmap、player
stats、match stats 是同场 `POSTMATCH_ONLY` facts。它们禁止进入同场 feature；前一
场的合格 facts 可以作为后一场的历史输入。

## Authority separation

- 特征名称和顺序：`config/model_feature_contracts.json` 的
  `v26_7_aligned/v1`，并与 `V26_6_PreMatchAdapter.V26_6_FEATURES` 对账。
- GD-A03 numeric semantics：`src/infrastructure/golden_dataset/GdA03PriorStateContract.js`
  与本文 feature matrix；不是 `SchemaManager` 的兼容实现。
- 目标 identity/spine：GD-A01 artifact。
- historical factual truth：GD-A02 artifact；其事实时序固定为 `POSTMATCH_ONLY`。
- history closure：canonical candidate/schedule identity artifact（现行三赛季
  Premier League master scope 为 380 场/season）。GD-A03 CLI 另外验证每季 20
  个 team、每队 38 场且主客各 19 场；它证明哪些 official fixture 存在，不把
  GD-A02 的 888 target subset 当成完整 schedule/result history。
- `l3_features`、PostgreSQL runtime tables、`SchemaManager` proxy/default 不是
  GD-A03 的 input authority。

GD-A03 CLI 只接受显式 repository-external immutable input files，输出 artifact 和
receipt 也必须在仓库外。它不联网、不连接 DB、不写 DB/raw/L3，不训练、不 backtest、
不预测。

## Versioned V-next contract freeze

截至 2026-08-16，`config/model_feature_contracts.json` 已升级为同一注册表内的
版本化权威（`model-feature-contract-registry/v2`）。这不是第二套 feature
authority：V1 和 V-next、V1→V-next migration map、逐 feature readiness status
以及 activation/decision boundaries 都由该注册表共同校验；decision-boundary 的
关键值也必须 fail-closed，不能只校验 section 名称。SOT inventory 的证据链引用
OSD-V1 final decision memo SHA256 `21eab8eedb31688488850d47833b2f86a2b765abadc49562050a81ebeaf78e2f`。

### Current historical/default contract: V1

`contract_id=v26_7_aligned/v1`、`feature_contract_version=v26_6_pre_match/v1`、
20 个 feature 的名称、顺序和既有数值语义保持冻结。它仍是当前历史 artifact、
canonical training producer 与 runtime adapter 所使用的默认绑定。V1 artifact 不得
被重新解释为 V-next。

### Next contract: V-next

`contract_id=canonical_prematch/vnext-v1`、`feature_contract_version=canonical_prematch/vnext/v1`
固定为 17 个 feature，且 `activation_status=DEFINED_NOT_ACTIVATED`。V-next 删除：

- `rolling_team_rating_home`
- `rolling_team_rating_away`
- `adjusted_elo_gap`

没有为保持 20 维而虚构替代 feature；`table_position_diff`、`points_diff` 和
`fatigue_diff` 仍保留。SOT、possession 和 raw ELO 仍保持 pending；standings
的语义合同已冻结，但不把“仍在 contract 中”升级为可训练、可运行或已物化数值。
V1→V-next 的 20 条迁移记录必须对每个 V1 feature 恰好覆盖一次。
同时，所有 17 个保留目标 feature 必须恰好获得一个非空迁移目标；迁移源或目标
覆盖不完整都会 fail-closed。逐 feature 状态矩阵的值（包括 proven family 的
runtime/readiness 状态）也是冻结边界，不是仅校验字段形状。

### Frozen V-next standings semantic contract

V-next 的三个 standings features 共同绑定同一个、且仅一个语义合同：

```text
STANDINGS_CONTRACT_ID=standings/premier-league-point-in-time/v1
STANDINGS_CONTRACT_VERSION=v1
COMPETITION_SCOPE=Premier League / league_id 47
FROZEN_SEASONS=2022/2023,2023/2024,2024/2025
STANDINGS_SEMANTIC_CONTRACT_STATUS=FROZEN
STANDINGS_HISTORY_EVIDENCE_STATUS=EVIDENCE_CLOSED_FOR_FROZEN_SCOPE
```

`rule_history_closure_required` 是“当前 rule-history closure 是否仍未完成”的
state flag；frozen scope 下值为 `NO`，表示 official rule-history closure 已完成，
不是对未来所有 standings contract 都永久声明 prerequisite。

合同位于同一 `config/model_feature_contracts.json` 的
`decision_boundaries.standings.contract`，不是第二个 registry。它冻结
points → goal difference → goals scored、competition ranking shared positions
with gaps（`1,1,3`）、严格 `SOURCE_EVENT_TIME_LT_TARGET_KICKOFF`、排除相同
kickoff、postponed 使用 actual played event time、异常比赛官方状态处理、
行政扣分有效时间区间与 fail-closed reason codes。证据 memo SHA256 为
`e09a80735f26d3fe3f949fcc115c853354c3f449dcf1ca6e9da7954846dbb357`，覆盖
`887/888`，其中 `47_20232024_4193789` 必须因
`ADMIN_ADJUSTMENT_EFFECTIVE_TIME_AMBIGUOUS` 保持 unavailable。

这不会改写 V1 的 20-feature numeric lineage matrix，也不会使 runtime、training
或 feature frame ready。V1 matrix 中 standings 行仍保留其既有未实现数值边界；
本阶段新增的历史能力只属于 V-next 的显式、未激活 projection path。

当前边界不变：

```text
V_NEXT_DEFAULT_ACTIVATED=NO
TRAINING_DEFAULT_SWITCHED=NO
RUNTIME_DEFAULT_SWITCHED=NO
MODEL_SCHEMA_SWITCHED=NO
FEATURE_FRAME_READINESS=NOT_READY
REAL_TRAINING_READINESS=NOT_READY
TRAIN_INFERENCE_NUMERIC_PARITY=NOT_PROVEN
GOLDEN_DATASET_COMPLETE=NO
```

Raw ELO 只冻结 `BOUNDED_START` 方向；E1–E11 数值与历史行为参数仍需 Owner
单独批准。Standings 已完成官方规则历史/例外闭合并冻结严格
`source_kickoff < target_kickoff`、排除相同 kickoff 的语义合同；Phase B 的
`PremierLeagueFrozenEvidenceAdapter` 先证明每季 380 场、20 队、每队 38 场且主客
各 19 场，再调用已合并的 `PointInTimeStandingsEngine`，由
`GdA03StandingsIntegration` 生成显式 V-next 历史 audit projection。冻结证据验证为
887/888，唯一 unavailable 行仍由行政有效时间区间重叠产生。该 projection 不是 V1
artifact、canonical training frame 或 runtime cache。SOT 只完成了对既有
冻结资产的只读库存：812 个 formal payload 均有 shotmap、`isOnTarget` 和
`isOwnGoal` 布尔字段，但独立观测的主客 team-ID pair 为 0，因此现有资产不足以
闭合 canonical SOT；不得在本任务中采集新足球数据。Possession 仍保留但历史与运行时
source 均为 unavailable，禁止任何比例、均值、插值或估算 fallback。

当前 standings integration 仍保持不联网、不查 provider、不查 DB、不写 DB、无兼容
proxy/default；历史 adapter 只接收 frozen evidence，runtime source adapter 尚未
开始。V1 `npm run gd:a03` 入口和 assembler 行为保持不变，V-next 仍为
`DEFINED_NOT_ACTIVATED`。

## V1 canonical 20-feature numeric lineage matrix

下表中的每行都必须在 artifact 中出现，且必须包含：
`FEATURE_NAME`、`INTENDED_SEMANTICS`、`SOURCE_AUTHORITY`、`SOURCE_FIELDS`、
`HISTORY_SCOPE`、`LOOKBACK_RULE`、`DERIVATION`、`CUTOFF_RULE`、
`MISSING_HISTORY_POLICY`、`COLD_START_POLICY`、`PROVENANCE_REQUIREMENTS`、
`SEMANTICS_STATUS`。

| Feature                        | Intended semantics                                                 | Source / derivation                                                                                                                     | History and missing policy                                                                                                              | Semantics status     |
| ------------------------------ | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| `rolling_xg_home`              | target home team previous-five mean xG                             | GD-A02 `facts.xg.<side>.value`, side must be `COMPLETE`; arithmetic mean                                                                | exact five actual same-season prior fixtures; any missing fact => null, no skip                                                         | `PROVEN_DERIVED`     |
| `rolling_xg_away`              | target away team previous-five mean xG                             | GD-A02 `facts.xg.<side>.value`, side must be `COMPLETE`; arithmetic mean                                                                | exact five actual same-season prior fixtures; any missing fact => null, no skip                                                         | `PROVEN_DERIVED`     |
| `rolling_shots_on_target_home` | target home team previous-five mean shots on target                | GD-A02 v2 `facts.shots_on_target.home.value`, from normalized shotmap `isOnTarget` by team ID plus independent observed team-ID binding | exact five actual same-season prior fixtures; missing binding/fact, invalid own-goal flag, or own-goal ambiguity => null; no goal proxy | `SEMANTICS_UNPROVEN` |
| `rolling_shots_on_target_away` | target away team previous-five mean shots on target                | GD-A02 v2 `facts.shots_on_target.away.value`, from normalized shotmap `isOnTarget` by team ID plus independent observed team-ID binding | exact five actual same-season prior fixtures; missing binding/fact, invalid own-goal flag, or own-goal ambiguity => null; no goal proxy | `SEMANTICS_UNPROVEN` |
| `rolling_possession_home`      | target home team previous-five mean possession                     | no accepted numeric field in GD-A02 projection                                                                                          | null; no 50/55/45 proxy                                                                                                                 | `UNAVAILABLE`        |
| `rolling_possession_away`      | target away team previous-five mean possession                     | no accepted numeric field in GD-A02 projection                                                                                          | null; no 50/55/45 proxy                                                                                                                 | `UNAVAILABLE`        |
| `rolling_team_rating_home`     | target home team prior rolling rating                              | no frozen rating formula; current weighted proxy is compatibility behavior                                                              | null; no replacement algorithm invented                                                                                                 | `SEMANTICS_UNPROVEN` |
| `rolling_team_rating_away`     | target away team prior rolling rating                              | no frozen rating formula; current weighted proxy is compatibility behavior                                                              | null; no replacement algorithm invented                                                                                                 | `SEMANTICS_UNPROVEN` |
| `home_table_position`          | exact league position before kickoff                               | requires complete prior league results and reproducible official tie-break                                                              | null on history gap or tie-break ambiguity; estimated rank forbidden                                                                    | `SEMANTICS_UNPROVEN` |
| `away_table_position`          | exact league position before kickoff                               | requires complete prior league results and reproducible official tie-break                                                              | null on history gap or tie-break ambiguity; estimated rank forbidden                                                                    | `SEMANTICS_UNPROVEN` |
| `table_position_diff`          | home position minus away position                                  | derived only from both proven positions                                                                                                 | null if either dependency unavailable                                                                                                   | `SEMANTICS_UNPROVEN` |
| `home_points`                  | target home team points from all prior fixtures                    | GD-A02 result: win=3/draw=1/loss=0                                                                                                      | all actual prior team fixtures must have result facts; empty closed history => proven 0                                                 | `PROVEN_DERIVED`     |
| `away_points`                  | target away team points from all prior fixtures                    | GD-A02 result: win=3/draw=1/loss=0                                                                                                      | all actual prior team fixtures must have result facts; empty closed history => proven 0                                                 | `PROVEN_DERIVED`     |
| `points_diff`                  | home points minus away points                                      | derived from both point lineages                                                                                                        | null if either dependency unavailable                                                                                                   | `PROVEN_DERIVED`     |
| `home_recent_form_points`      | target home team points in exact previous-five fixtures            | GD-A02 result: win=3/draw=1/loss=0                                                                                                      | fewer than five or any missing previous fixture => null; no older sixth match substitution                                              | `PROVEN_DERIVED`     |
| `raw_elo_gap`                  | home minus away historical ELO                                     | no proven complete universe, initialization, season, K, or home treatment contract                                                      | null; 1500 is not silently treated as observed historical ELO                                                                           | `SEMANTICS_UNPROVEN` |
| `adjusted_elo_gap`             | proven transformation of raw ELO gap                               | no value while raw ELO and adjustment formula are unproven; current `*0.1` is not promoted                                              | null on dependency/semantic gap                                                                                                         | `SEMANTICS_UNPROVEN` |
| `home_fatigue_index`           | scheduled prior fixtures in `[cutoff-7d, cutoff)` / 7, capped at 1 | canonical complete schedule identity; no target facts required                                                                          | null only if schedule closure is not proven; empty closed window => 0                                                                   | `PROVEN_DERIVED`     |
| `away_fatigue_index`           | scheduled prior fixtures in `[cutoff-7d, cutoff)` / 7, capped at 1 | canonical complete schedule identity; no target facts required                                                                          | null only if schedule closure is not proven; empty closed window => 0                                                                   | `PROVEN_DERIVED`     |
| `fatigue_diff`                 | home fatigue minus away fatigue                                    | derived from both fatigue lineages                                                                                                      | null if either dependency unavailable                                                                                                   | `PROVEN_DERIVED`     |

Every rolling feature records the exact actual previous-five canonical IDs even when
one required fact is absent. The assembler never changes `A B C D E` into `A B D E F`.

## Artifact and population contract

The file-first artifact schema is:

```text
golden-dataset-v1-gd-a03-prior-state-features-artifact/v4
```

FSC-V1 advances the numeric lineage contract to
`gd-a03-numeric-lineage/v2`; feature names and order remain the unchanged
canonical 20-feature identity.

Each target row contains:

- `canonical_match_id`, `target_kickoff`, home/away identity;
- `feature_cutoff_policy`, `feature_cutoff_time`;
- the canonical feature contract and ordered feature object;
- each feature value or `null`, `availability_status`, exact source IDs and identities,
  latest source kickoff, derivation contract, cutoff proof, and provenance digest;
- `feature_availability` and deterministic `unavailable_reason_counts` for all 20 features;
- `feature_vector_eligibility` (`YES`/`NO`) with reason codes;
- an isolated `target_label` with `role=TRAINING_LABEL_POSTMATCH`.
- the isolated label identifies the target with `canonical_match_id`; it is not a provider `source_match_id`.
- the isolated label includes `source_fact_binding`, which binds its canonical ID,
  GD-A02 artifact hashes, `fact_presence`, and (when admitted) a deterministic
  result/provenance binding. A missing fact also carries a deterministic
  `fact_rejection_binding` over the canonical ID, source ID, rejection reason,
  error code, and reason text.

The target label is created after feature derivation and is never an input to it.

The population invariant is:

```text
TARGET_IDS = FEATURE_ELIGIBLE_IDS ∪ FEATURE_UNAVAILABLE_IDS
intersection(TARGET_IDS) = empty
duplicate = 0
extra = 0
unaccounted = 0
```

The schedule authority is fail-closed for the current canonical Premier League
inventory: each season must contain 20 distinct teams, 380 fixtures, and every
team must have exactly 38 fixtures (19 home and 19 away). The artifact retains
the per-season/per-team counts and validates them against the schedule rows;
the GD-A03 assembler does not accept a declared closure that is not reconciled
to those rows.

`population_authority` is a required GD-A01-bound object. Its
`target_id_set_sha256` and `target_population_count` must equal the admitted ID
set hash and admitted row count in `gd_a01_receipt`; the artifact verifier does
not accept a self-declared smaller population.

`population_accounting.target_id_set_sha256` and
`population_accounting.accounted_id_set_sha256` are required hashes of the
sorted canonical target IDs. The artifact verifier recomputes both hashes from
the rows and compares the result to `population_authority`, so population
accounting cannot be made green by changing counts alone.

Each `target_label` is independently bound to its row identity and to the
postmatch result projection. GD-A02 validates that an available outcome is
derived from its final home/away scores. GD-A03 retains the result and source
provenance in `provenance_input`, recomputes both the display digest and the
fact-result binding for admitted facts, and verifies the admitted/rejected/
accounted ID sets against the validated GD-A02 artifact binding. A GD-A02
rejection is retained as a target row with `fact_presence=MISSING`, explicit
rejection provenance, a null result, and no synthetic fact-result binding; its
dependent historical features remain unavailable. The GD-A02 source binding
also carries the sorted aggregate hash and count of rejected-fact bindings,
and each missing target label carries its corresponding binding. Identity,
projection, source binding, or provenance tampering therefore fails closed,
without shrinking the GD-A01 target population. Target labels remain
postmatch-only and are never inputs to feature computation.

The GD-A02 coverage binding in `source_bindings.gd_a02_artifact` records the
SHA-256 ID-set hash and row count for admitted facts, rejected facts, and their
union, plus the admitted fact-result binding aggregate and rejected-fact
binding aggregate. GD-A03 requires both binding aggregates to match the
validated GD-A02 rows and the union to equal the GD-A01 admitted population. A
missing rejection record is therefore a population/provenance error, not an
invitation to use older history or an estimated value.

`FULL_20_VECTOR_ELIGIBLE=YES` requires all 20 values to be finite, semantically proven,
strictly prior, fully closed, and individually hash/provenance bound. No null is replaced
by zero, neutral, a proxy, or a cold-start default.

The receipt uses `gd-a03-prior-state-feature-view-receipt/v4` and carries
`receipt_content_sha256`, a stable hash over every other receipt field. Receipt provenance
tampering therefore fails closed even when the artifact bytes are unchanged.

## Fail-closed and determinism requirements

The contract rejects:

- target/future/equal kickoff source IDs;
- home/away or kickoff identity mismatch between GD-A01, GD-A02 and schedule;
- duplicate or reordered source IDs that change the business projection;
- missing required actual history that is hidden by a longer lookback;
- artifact/receipt/source hash mismatch;
- non-finite values, unavailable lines carrying values, or available lines carrying null;
- population shrink, unaccounted rows, or target labels used in feature inputs.

For identical immutable input bytes and code revision, builds must have equal business
projection, row ordering, availability, values, lineage, source ID sets and business hash.

## Runtime numeric parity boundary

GD-A03 keeps these statuses explicit:

```text
CANONICAL_20_NAME_ORDER_PARITY=YES
TRAIN_GD_A03_NUMERIC_SEMANTICS_PROVEN=PARTIAL
RUNTIME_NUMERIC_SEMANTICS_PROVEN=NO
TRAIN_INFERENCE_NUMERIC_PARITY=NOT_PROVEN
```

The current `SchemaManager` implementation uses goals as xG, estimated shots-on-target,
fixed possession, estimated position, default/cold-start values, and a compatibility
rating formula. Those values are not silently copied into GD-A03. FSC-V1 extends the
existing capture/staging contract to retain response-derived team IDs when the source
response exposes them, and the GD-A02 projection accepts SOT only when that independent
binding is present. Current frozen payloads do not retain the independent pair, so their
SOT projection remains unavailable rather than accepting an ID-only side reversal. A
source shot marked `isOwnGoal=true` (or carrying a missing/invalid own-goal flag) is
also fail-closed because the frozen authority does not prove whether it belongs in the
canonical team SOT statistic; therefore the two SOT rolling features remain
`SEMANTICS_UNPROVEN` at the global contract level and are only a partial closure.
The canonical runtime adapter still fails closed because it has no runtime source with
the same historical lineage; non-strict compatibility behavior is not numeric authority.
Consequently this does not authorize training and does not upgrade
`REAL_TRAINING_READINESS`.

```text
FEATURE_FRAME_READINESS=NOT_READY
TRAINING_EXECUTION_AUTHORIZED=NO
GOLDEN_DATASET_COMPLETE=NO
```

The receipt also records `DB_CONNECTIONS=0` alongside the other offline safety counters.
