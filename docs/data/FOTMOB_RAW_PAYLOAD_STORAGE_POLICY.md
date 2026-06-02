<!-- markdownlint-disable MD013 -->

# FotMob Raw Payload Storage Policy

- lifecycle: permanent / governance
- phase: ADG60-RAW-PAYLOAD-STORAGE-FOUNDATION
- version: 1.0.0

## 1. Storage Goal

Store FotMob match detail raw payloads locally for long-term stable acquisition. Each match is one file. Payloads are gitignored — never committed to git. Only metadata manifests and reports are source-controlled.

## 2. Storage Location

```
data/raw/fotmob/match_detail/{match_id}.payload.html
```

All paths under `data/raw/` are gitignored. Raw payload files exist on the capturing machine only and are portable via manifest references.

## 3. Manifest Location

Manifests are committed to git and live under:

```
docs/_manifests/fotmob_raw_payload_capture_adg60_manifest.json
```

A manifest records per-match metadata only — never the raw payload body:

- `match_id`
- `target_index`, `expected_home`, `expected_away`, `expected_date`, `competition`
- `route_hash_pair`, `corrected_hash_id`
- `raw_payload_relative_path`
- `sha256`, `byte_size`, `content_type`, `captured_at`
- `has_next_data_marker`, `has_page_props_marker`
- `extractor_flags`
- `body_committed: false`
- `db_write: false`
- `raw_match_data_insert: false`

Prohibited in manifest:
- full HTML body
- raw `__NEXT_DATA__` JSON
- full `pageProps` object
- source response body

## 4. File Naming Rules

- Deterministic: `{match_id}.payload.html` (e.g., `53_20252026_4830473.payload.html`)
- No random filenames
- Default: no overwrite unless `--allow-overwrite` explicitly passed

## 5. Validation Rules

Every captured raw payload must record:
- sha256 checksum
- byte_size
- content_type
- capture timestamp
- route/hash identity
- presence of `__NEXT_DATA__` and `pageProps` markers

## 6. Safety Rules

- Raw payload files must remain gitignored
- No DB write
- No raw_match_data insert
- No ADG60 write
- `raw_write_ready` remains `false` until raw payload storage review passes
- Raw payload storage success does NOT equal DB write authorization

## 7. Long-Term Acquisition Rules

- One match = one raw file
- Idempotent capture (manifest-driven, skip existing unless overwrite)
- Resumable (manifest records what was captured)
- Stop on block (403/429/captcha/anti-bot)
- No parallel by default
- No retry storm
- Per-league / per-season batching
- Raw storage review required before parser/write stages

## 8. Gitignore Confirmation

The following paths must be gitignored:

```
data/raw/
```

All raw payloads write to paths under `data/raw/fotmob/` which MUST be gitignored. Verify with `git check-ignore`.
