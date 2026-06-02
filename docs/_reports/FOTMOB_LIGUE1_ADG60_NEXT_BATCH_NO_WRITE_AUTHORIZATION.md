<!-- markdownlint-disable MD013 -->

# FotMob Ligue 1 ADG60 Next Batch No Write Authorization

- lifecycle: phase-artifact
- phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE-AUTHORIZATION
- scope: authorization only
- source review: PR #1411
- source three-target result: PR #1410
- source authorization: PR #1409
- no live fetch
- no network fetch
- no browser automation
- no payload save
- no DB write
- no raw write
- no raw_match_data insert
- no schema migration
- no ADG60 write

This PR authorizes a future bounded next-batch (5-target) live fetch no-write phase. It does not execute any fetch.

## Why Next Authorization Is Justified

Previous evidence shows all 4 tested targets (1 from #1407 + 3 from #1410) are accessible via FotMob SSR detail pages:

- All HTTP 200
- All have `__NEXT_DATA__` and pageProps markers
- All are payload-like
- No blocking signals (403/429/captcha/anti-bot) detected
- All safety constraints were upheld

The three-target review (#1411) confirmed accessibility=PASS, payload shape=PASS, safety=PASS, with evidence quality sufficient for a next authorization phase.

## Authorization Scope

### Target Scope

- max future targets: **5**
- target source: existing ADG60 dry-run matrix (source-controlled)
- candidate target indices: **[5, 6, 7, 8, 9]**

| Target Index | Match ID | Match | Date | Route Hash Pair |
|---|---|---|---|---|
| 5 | `53_20252026_4830478` | Lens vs Brest | 2025-08-29 | `2f5cib#4830478` |
| 6 | `53_20252026_4830479` | Lorient vs Lille | 2025-08-30 | `2he6a1#4830479` |
| 7 | `53_20252026_4830476` | Angers vs Rennes | 2025-08-31 | `2o5ty5#4830476` |
| 8 | `53_20252026_4830477` | Le Havre vs Nice | 2025-08-31 | `363pdo#4830477` |
| 9 | `53_20252026_4830480` | Lyon vs Marseille | 2025-08-31 | `2s51f2#4830480` |

- no target discovery
- no extra leagues/seasons/matches
- no automatic 32-target run
- no fallback to extra targets
- stop if any target missing route/hash before network

### Candidate Target Policy

Candidates are sequential from the dry-run matrix, contiguous with already-fetched targets [1,2,3,4]. All candidates have:

- accepted_suspension_resolved identity status
- corrected_hash_id
- corrected_route_hash_pair
- expected_home/away/date/competition

### Future Execution Policy

- max network requests: **5**
- exactly one request per target
- sequential only, no parallel fetch, no retry
- delay: 20-60s between requests
- timeout: <= 20s per request
- redirect: manual
- stop on: 403/429/captcha/anti-bot/redirect/identity-mismatch/route-hash-mismatch/body-persistence/DB-write/raw_match_data-insert
- stop on any target missing required route/hash before network
- no automatic continuation to remaining 32 targets

### Payload / Write / Browser Policy

- **Payload**: metadata/hash/status/size/content_type/minimal schema flags only in git; body persistence requires separate authorization
- **Write**: DB/raw/raw_match_data writes remain prohibited; ADG60 write blocked
- **Browser**: prohibited; requires separate explicit authorization PR

### Review Policy

- review required after next batch (5 targets)
- no automatic next batch
- no automatic 32-target run
- any failure blocks expansion

## Stop Conditions

- target identity mismatch
- home/away orientation mismatch
- expected date mismatch
- competition mismatch
- missing corrected_hash_id
- missing route hash
- duplicate raw_match_data row already exists
- output directory not clean
- payload would be saved to git-tracked path
- full HTML would be saved
- full pageProps would be saved
- DB write attempted
- raw_match_data insert attempted
- unexpected network route
- unexpected redirect
- 403 / 429 / captcha / anti-bot / blocked response
- unexpected schema / payload structure
- payload too large (> 5 MB per target)
- more targets than authorized batch (max=5)
- any automatic retry loop
- parallel fetch attempted
- browser automation attempted

## Readiness Decision

- ready: **true**
- current phase is authorization only, execution deferred
- raw_write_ready remains false
- DB write remains prohibited

## Safety

- live_fetch_performed: false
- network_fetch_performed: false
- browser_automation_performed: false
- payload_saved: false
- db_write_performed: false
- raw_write_performed: false
- raw_match_data_insert_performed: false
- adg60_write_performed: false
- raw_write_ready_marked: false

## Recommended Next Phase

```
ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE
```

Next phase will execute live fetch for at most 5 targets with all the guards defined in this authorization.
