<!-- markdownlint-disable MD013 -->

# FotMob Ligue 1 ADG60 Payload Acquisition Authorization Gate

- lifecycle: phase-artifact
- phase: ADG60-PAYLOAD-ACQUISITION-AUTHORIZATION-GATE
- scope: authorization gate only
- user authorization quote: “我明确授权”
- authorization interpreted as: authorization to proceed to authorization-gated payload acquisition preparation, not DB write, not raw write, not acquisition execution in this PR
- target_count: 32
- current blocker: blocked_missing_payload=32
- no live fetch
- no network fetch
- no browser automation
- no payload save
- no DB write
- no raw write
- no raw_match_data insert
- no schema migration
- no ADG60 write

## Exact Target Scope

- exactly 32 ADG59B accepted Ligue 1 targets
- no scope expansion
- no target discovery
- no extra leagues
- no extra seasons
- no extra matches

## Allowed Actions In This PR

- create authorization manifest
- create authorization report
- create pre-execution checklist
- create future execution requirements
- create safety boundary
- create storage policy decision matrix
- create batch/rate-limit recommendation

## Forbidden Actions In This PR

- live fetch
- network fetch
- browser automation
- payload save
- raw payload acquisition execution
- DB write
- raw write
- raw_match_data insert
- schema migration
- ADG60 write

## Future Acquisition Execution Prerequisites

- whether live/network fetch is allowed
- whether browser automation is allowed
- whether payload persistence is allowed
- exact storage location
- batch size
- rate limit / delay
- payload minimization policy
- hash policy
- cleanup policy
- no DB write unless separately authorized
- no raw_match_data insert unless separately authorized

## Storage Policy Requirements

- default to metadata/hash-only source-controlled outputs
- do not commit full raw payload, full HTML, __NEXT_DATA__, pageProps, or source body
- require explicit storage location before any future payload persistence
- require gitignore or external storage review before any future local payload persistence
- document cleanup policy before any future dry-run writes files

## Batch And Rate-Limit Requirements

- future dry-run must declare max batch size before any request-capable code is run
- future dry-run must declare delay/rate-limit policy before any request-capable code is run
- future dry-run must stop on identity mismatch, route/hash drift, or unexpected payload shape
- future dry-run must stay no-DB-write and no-raw_match_data-insert unless separately authorized

## Risk Controls

- anti-bot risk remains blocked until explicit live/network authorization
- wrong target risk controlled by exact 32-target scope and identity re-check
- payload persistence risk controlled by metadata/hash-only default
- DB write risk controlled by keeping write authorization separate
- dangerous script risk controlled by not executing historical recapture/write/backfill scripts

## Recommended Next Phase

- recommended next phase: ADG60-PAYLOAD-ACQUISITION-DRY-RUN-NO-WRITE
- Next phase may prepare an executable dry-run, but still must not write DB or raw_match_data.
