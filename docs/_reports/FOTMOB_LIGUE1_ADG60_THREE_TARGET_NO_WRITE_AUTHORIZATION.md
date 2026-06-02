<!-- markdownlint-disable MD013 -->

# FotMob Ligue 1 ADG60 Three Target No Write Authorization

- lifecycle: phase-artifact
- phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE-AUTHORIZATION
- scope: authorization only
- source review: PR #1408
- source one-target result: PR #1407
- no live fetch
- no network fetch
- no browser automation
- no payload save
- no DB write
- no raw write
- no raw_match_data insert
- no schema migration
- no ADG60 write

This PR authorizes a future bounded three-target live fetch no-write phase. It does not execute any fetch.

## Why Next Authorization Is Justified

The one-target review confirmed:

- **Accessibility**: pass — FotMob detail page is accessible
- **Payload shape**: pass — `__NEXT_DATA__` and pageProps confirmed
- **Safety**: pass — constraints held
- **Evidence quality**: sufficient_for_next_authorization_phase_only

## Authorization Scope

### Target Scope

- max future targets: **3**
- target source: existing ADG60 dry-run matrix (source-controlled)
- candidate target indices: **[2, 3, 4]**

| Target Index | Match ID | Match |
|---|---|---|
| 2 | `53_20252026_4830472` | Nice vs Auxerre |
| 3 | `53_20252026_4830474` | Strasbourg vs Nantes |
| 4 | `53_20252026_4830475` | Toulouse vs Brest |

- no target discovery
- no extra leagues/seasons/matches
- no automatic 32-target run

### Future Execution Policy

- max network requests: **3**
- sequential only, no parallel fetch, no retry
- delay: 20-60s
- timeout: <= 20s
- redirect: manual
- stop on: 403/429/captcha/anti-bot/redirect/identity-mismatch/body-persistence/DB-write

### Payload / Write / Browser Policy

- **Payload**: metadata/hash only in git; body persistence requires separate authorization
- **Write**: DB/raw/raw_match_data writes remain prohibited; ADG60 write blocked
- **Browser**: prohibited; requires separate explicit authorization PR

### Review Policy

- review required after 3 targets
- no automatic next batch or 32-target run
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
- more targets than authorized batch (max=3)
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
ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE
```

Next phase will execute live fetch for at most 3 targets with all the guards defined in this authorization.
