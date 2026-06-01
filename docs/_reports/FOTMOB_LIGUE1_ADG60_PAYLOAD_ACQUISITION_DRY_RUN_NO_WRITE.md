<!-- markdownlint-disable MD013 -->

# FotMob Ligue 1 ADG60 Payload Acquisition Dry Run No Write

- lifecycle: phase-artifact
- phase: ADG60-PAYLOAD-ACQUISITION-DRY-RUN-NO-WRITE
- scope: dry-run planning only
- based_on: ADG60 preflight no-write; ADG60 raw payload source inventory; ADG60 payload acquisition plan; ADG60 authorization gate
- target_count: 32
- current blocker: blocked_missing_payload=32
- raw_write_ready_count: 0
- no live fetch
- no network fetch
- no browser automation
- no payload save
- no acquisition execution
- no DB write
- no raw write
- no raw_match_data insert
- no schema migration
- no ADG60 write

## Dry-Run Target Matrix Summary

- dry-run matrix count: 32
- target scope: exactly 32 ADG59B accepted Ligue 1 targets
- raw_payload_status: missing for 32/32 targets
- raw_match_data_status: not_present for 32/32 targets
- dry_run_action: planned_only for 32/32 targets
- canonical_detail_route_or_url_if_available: not source-controlled for all targets; no URL probing performed

## Future Command Preview

- command_preview_only: true
- command_executed: false
- command preview is non-executable documentation in this PR
- preview command: `docker compose -f docker-compose.dev.yml exec -T dev node scripts/ops/future_adg60_payload_acquisition_authorized_execute.js --target-manifest docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write.json --output-dir data/raw_external/fotmob/adg60_ligue1_payloads --max-batch-size 4 --delay-seconds 10 --stop-on-first-mismatch --stop-on-duplicate-raw-row --stop-on-unexpected-redirect --stop-on-orientation-mismatch --stop-on-payload-schema-mismatch --stop-on-payload-too-large --stop-on-anti-bot-or-captcha --stop-on-any-write-attempt`
- required parameters: target manifest path, output directory, max batch size, delay seconds
- required guards: stop on first mismatch, duplicate raw row, unexpected redirect, orientation mismatch, payload schema mismatch, payload too large, anti-bot/captcha/block, or any write attempt

## Output Policy

- full source payloads must not be committed to git
- HTML, __NEXT_DATA__, and full pageProps must not be committed to git
- source-controlled manifests may store only metadata, hash, size, timestamp, target identity, and status
- payload retention, if separately authorized later, must use a gitignored external raw storage path
- gitignore coverage must be verified before any future payload retention path is used
- cleanup policy must be documented before any future local file output
- payload minimization must be selected before any future acquisition
- stable hash policy must be selected before any future acquisition

## Stop Conditions

- target identity mismatch
- home/away orientation mismatch
- expected date mismatch
- competition mismatch
- missing corrected_hash_id
- missing route hash
- duplicate raw row already exists
- output directory not clean
- payload would be written to a git-tracked path
- full HTML would be persisted
- full pageProps would be persisted
- db write attempted
- raw_match_data insert attempted
- network attempt in this PR
- browser automation attempted in this PR
- anti-bot/captcha/block detected in future execution
- unexpected schema or payload structure

## Recommended Next Phase

- recommended next phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-AUTHORIZATION
- next phase must separately authorize live/network fetch before any external request
- even if fetch is later authorized, DB write and raw_match_data insert remain blocked unless separately authorized
