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

## Canonical 20-feature numeric lineage matrix

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
golden-dataset-v1-gd-a03-prior-state-features-artifact/v3
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
  result/provenance binding.

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
dependent historical features remain unavailable. Identity, projection, source
binding, or provenance tampering therefore fails closed, without shrinking the
GD-A01 target population. Target labels remain postmatch-only and are never
inputs to feature computation.

The GD-A02 coverage binding in `source_bindings.gd_a02_artifact` records the
SHA-256 ID-set hash and row count for admitted facts, rejected facts, and their
union, plus the admitted fact-result binding aggregate. GD-A03 requires the
union to equal the GD-A01 admitted population. A missing rejection record is
therefore a population/provenance error, not an invitation to use older history
or an estimated value.

`FULL_20_VECTOR_ELIGIBLE=YES` requires all 20 values to be finite, semantically proven,
strictly prior, fully closed, and individually hash/provenance bound. No null is replaced
by zero, neutral, a proxy, or a cold-start default.

The receipt uses `gd-a03-prior-state-feature-view-receipt/v3` and carries
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
