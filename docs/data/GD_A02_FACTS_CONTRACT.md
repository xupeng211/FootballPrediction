<!-- lifecycle: permanent -->

# GD-A02 facts contract

GD-A02 is the file-first FotMob facts projection that follows the GD-A01
spine. It does not complete the Golden Dataset and does not create prematch
features, a training frame, a model, a backtest, or a value-evaluation path.

## Authority and boundary

- GD-A01 `artifact` and `receipt` are the upstream population and identity
  authority. GD-A02 does not recalculate the population, odds linkage, or
  canonical identity.
- FotMob capture payload/manifest validation is delegated to
  `FotMobDetailCaptureContract`; the five-section staging contract is
  delegated to `FotMobDetailStagingContract`.
- Match identity remains the exact GD-A01 linkage (`matchLinker.js` authority
  as embedded in each admitted GD-A01 row). No fuzzy or positional matching is
  permitted.
- Build and validation are offline and file-first. Inputs and outputs are
  explicit repository-external files. The implementation performs zero live
  network requests, database writes, raw mutations, training, backtesting, or
  model activation.

## Inputs and output

The build surface is `npm run gd:a02 -- build` with explicit paths for:

1. GD-A01 artifact and receipt;
2. the frozen FotMob freeze document and JSONL manifest;
3. a GD-A02 source index that binds each admitted canonical ID to one staging
   artifact, capture payload, and capture manifest plus their physical SHA-256
   hashes;
4. the current full Git revision and two new output paths.

The artifact schema is
`golden-dataset-v1-gd-a02-facts-artifact/v1`; its deterministic rows contain:

- GD-A01 canonical identity and exact source linkage;
- frozen, staging, and capture provenance/hash bindings;
- five staging section audits: `events`, `lineup`, `player_stats`, `shotmap`,
  and `stats`, each with `present`, contract `version`, the existing staging
  `coverage`, and a deterministic `schema_fingerprint`. The section JSON is
  validated from the canonical staging/capture pair but is not copied into
  the GD-A02 artifact;
- `match_result`, derived only from the normalized final home/away scores;
- `xg`, derived only from normalized shotmap values by exact home/away team
  ID. A side is `null` when its evidence is incomplete; missing xG is never
  replaced with zero. Finite source numbers are summed as parsed without an
  additional decimal truncation or rounding step. Own-goal shots are not
  silently treated as ordinary xG shots;
- an explicit `admission` value. Invalid evidence is represented by a
  `rejected_rows` entry with its canonical ID, error code, and reason rather
  than being silently dropped.

The receipt binds output bytes, business hash, admitted/accounted ID-set
hashes, population counts, source bindings, code revision, scope, and status.

## Population and identity invariants

For every build:

```text
GD-A01_INPUT_IDS = ADMITTED_FACT_IDS ∪ REJECTED_OR_QUARANTINED_IDS
intersection = empty
duplicate IDs = 0
extra IDs = 0
unaccounted IDs = 0
```

The expected population is read from the validated upstream/frozen artifacts;
`888` is evidence from the current frozen snapshot, not a code-level expected
count. A build must fail closed on an upstream identity/hash mismatch, missing
source evidence, duplicate/extra IDs, malformed capture/staging contract, or
reversed home/away identity.

## Temporal semantics

Every GD-A02 fact is explicitly:

```text
role=MATCH_FACT
timing_class=POSTMATCH_ONLY
prematch_available=false
decision_time_eligible=false
```

Final score, xG, shots, events, lineup, player statistics, shotmap, and match
statistics are factual truth/audit material. They are not prematch-known
features. Therefore GD-A02 does not prove strict decision-time readiness or
real training readiness. GD-A01/M3 odds semantics remain unchanged:
provider-defined closing is proven; exact closing, opening, and capture
timestamps remain unproven; strict decision-time value evaluation is not ready.

## Determinism and revalidation

Rows and rejected rows are sorted by `canonical_match_id`. The business hash
excludes only its own self field; physical output SHA-256 is bound by the
receipt. Rebuilding with the same exact input bytes and code revision must
produce equal business projections, business hashes, ID sets, fact values, and
ordering. `validate` rechecks the full contract and receipt bindings.
