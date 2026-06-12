# FotMob Retain 50 Raw Parser Validation

lifecycle: phase-artifact

- Date: `2026-06-13`
- Branch: `data/fotmob-retain-50-raw-validation-batch`
- Base main commit: `4fc9c531646384c4e74a89ce5080e08415cb3319`
- Scope: bounded live FotMob raw retention expansion + full retained-sample parser dry-run
- Safety: only `raw_match_data` INSERT/UPSERT; no `matches`/`features`/`odds` write; no parser/test/feature/model change; no full raw/pageProps/HTML saved or printed

## Execution Summary

- Original retained `fotmob_live_v1` rows: `24`
- Target additional raw: `<=50`
- Initial non-retained candidate pool found: `36`
- First blocked candidate: `900002` (`47_20242025_900002`, Burgos vs Oviedo) returned `HTTP 404` with `TRANSFORM_FAILED: no structured match data`
- Bounded continuation scope: remaining `34` `Ligue 1` `2025/2026` candidates
- Actual additional raw retained: `34`
- Final retained `fotmob_live_v1` rows: `58`
- Writes performed: `raw_match_data=yes`, `matches=no`, `features=no`, `odds=no`
- Parser/test/features/model changed: `no`
- Feature generation / model training run: `no`

## Added External IDs

`4830458`, `4830459`, `4830460`, `4830462`, `4830463`, `4830465`, `4830467`, `4830468`,
`4830469`, `4830470`, `4830471`, `4830472`, `4830473`, `4830474`, `4830475`, `4830476`,
`4830477`, `4830478`, `4830479`, `4830480`, `4830481`, `4830482`, `4830483`, `4830484`,
`4830485`, `4830486`, `4830487`, `4830488`, `4830489`, `4830490`, `4830491`, `4830492`,
`4830493`, `4830498`

## Structural Validation

- New rows present in `raw_match_data`: `34/34`
- `raw_data` is valid JSON object: `34/34`
- top-level `_meta`: `34/34`
- top-level `matchId`: `34/34`
- top-level `general`: `34/34`
- top-level `header`: `34/34`
- top-level `content`: `34/34`
- `_meta.source` present: `34/34` (`fotmob`)
- `data_version='fotmob_live_v1'`: `34/34`
- `external_id` retained: `34/34`
- `data_hash` retained: `34/34`

## Parser Dry-run Result

- Parser dry-run sample: `58` retained `fotmob_live_v1` rows
- Parse success: `58/58`
- Parse failure: `0/58`
- Events parity: `58/58` rows; raw timeline events `1106/1106` preserved
- `Substitution` `synthetic_event_key`: `493/493`; duplicate-key rows: `0`
- `AddedTime` `marker_event`: `111/111`
- `Half` `marker_event`: `114/114`
- New null-id `real_event` types: `none`
- Note: observed null-id `Substitution` rows remained fully covered by synthetic keys; no new uncovered null-id real-event blocker appeared
- New parser blocker: `none`

## New Raw Summary

| external_id | match_id | matchup | date | hash12 | bytes | events | Sub | AT | Half |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| `4830458` | `53_20252026_4830458` | Angers vs Paris FC | `2025-08-17` | `f35855b36c62` | 226544 | 15 | `10/10` | `1/1` | `2/2` |
| `4830459` | `53_20252026_4830459` | Auxerre vs Lorient | `2025-08-17` | `de7cdef3a6d2` | 268020 | 19 | `6/6` | `3/3` | `2/2` |
| `4830460` | `53_20252026_4830460` | Brest vs Lille | `2025-08-17` | `1916829cafd6` | 288766 | 14 | `7/7` | `1/1` | `2/2` |
| `4830462` | `53_20252026_4830462` | Metz vs Strasbourg | `2025-08-17` | `702f48d58643` | 263232 | 21 | `9/9` | `2/2` | `2/2` |
| `4830463` | `53_20252026_4830463` | Monaco vs Le Havre | `2025-08-16` | `57e986606a68` | 234524 | 16 | `9/9` | `2/2` | `2/2` |
| `4830465` | `53_20252026_4830465` | Nice vs Toulouse | `2025-08-16` | `cca8c02f1e48` | 336635 | 23 | `10/10` | `2/2` | `2/2` |
| `4830467` | `53_20252026_4830467` | Le Havre vs Lens | `2025-08-24` | `54bfaede327f` | 276241 | 18 | `9/9` | `2/2` | `2/2` |
| `4830468` | `53_20252026_4830468` | Lille vs Monaco | `2025-08-24` | `3d981291df0a` | 246087 | 20 | `10/10` | `2/2` | `2/2` |
| `4830469` | `53_20252026_4830469` | Lorient vs Rennes | `2025-08-24` | `2b4f3a311a0b` | 286742 | 17 | `9/9` | `2/2` | `2/2` |
| `4830470` | `53_20252026_4830470` | Lyon vs Metz | `2025-08-23` | `dd9641a818d5` | 296264 | 21 | `9/9` | `2/2` | `2/2` |
| `4830471` | `53_20252026_4830471` | Marseille vs Paris FC | `2025-08-23` | `47bc986e90da` | 287611 | 23 | `10/10` | `2/2` | `2/2` |
| `4830472` | `53_20252026_4830472` | Nice vs Auxerre | `2025-08-23` | `b8df190def39` | 258006 | 17 | `9/9` | `2/2` | `2/2` |
| `4830473` | `53_20252026_4830473` | Paris Saint-Germain vs Angers | `2025-08-22` | `6a331623bd0c` | 286573 | 19 | `10/10` | `2/2` | `2/2` |
| `4830474` | `53_20252026_4830474` | Strasbourg vs Nantes | `2025-08-24` | `5fc09ba3a674` | 284131 | 23 | `8/8` | `2/2` | `2/2` |
| `4830475` | `53_20252026_4830475` | Toulouse vs Brest | `2025-08-24` | `0e70ec9fc32a` | 247690 | 16 | `5/5` | `2/2` | `2/2` |
| `4830476` | `53_20252026_4830476` | Angers vs Rennes | `2025-08-31` | `59a1b8f758fb` | 266796 | 18 | `9/9` | `1/1` | `2/2` |
| `4830477` | `53_20252026_4830477` | Le Havre vs Nice | `2025-08-31` | `29295507546b` | 267154 | 16 | `8/8` | `2/2` | `2/2` |
| `4830478` | `53_20252026_4830478` | Lens vs Brest | `2025-08-29` | `42e73ee9839d` | 309576 | 25 | `9/9` | `2/2` | `2/2` |
| `4830479` | `53_20252026_4830479` | Lorient vs Lille | `2025-08-30` | `993558d89c1d` | 264820 | 21 | `10/10` | `2/2` | `2/2` |
| `4830480` | `53_20252026_4830480` | Lyon vs Marseille | `2025-08-31` | `dc7abc9b1a31` | 313803 | 21 | `7/7` | `2/2` | `2/2` |
| `4830481` | `53_20252026_4830481` | Monaco vs Strasbourg | `2025-08-31` | `7b6f307545ce` | 326074 | 23 | `7/7` | `2/2` | `2/2` |
| `4830482` | `53_20252026_4830482` | Nantes vs Auxerre | `2025-08-30` | `24a490db992f` | 232503 | 15 | `7/7` | `2/2` | `2/2` |
| `4830483` | `53_20252026_4830483` | Paris FC vs Metz | `2025-08-31` | `9c162400b475` | 286939 | 23 | `10/10` | `2/2` | `2/2` |
| `4830484` | `53_20252026_4830484` | Toulouse vs Paris Saint-Germain | `2025-08-30` | `e11116f4deb0` | 281284 | 17 | `8/8` | `2/2` | `2/2` |
| `4830485` | `53_20252026_4830485` | Auxerre vs Monaco | `2025-09-13` | `97f7425e874a` | 276483 | 21 | `8/8` | `2/2` | `2/2` |
| `4830486` | `53_20252026_4830486` | Brest vs Paris FC | `2025-09-14` | `f5b94b22c782` | 284308 | 21 | `10/10` | `2/2` | `2/2` |
| `4830487` | `53_20252026_4830487` | Lille vs Toulouse | `2025-09-14` | `630fb5ee54fb` | 278952 | 22 | `10/10` | `2/2` | `2/2` |
| `4830488` | `53_20252026_4830488` | Marseille vs Lorient | `2025-09-12` | `0e19c243bfad` | 283220 | 18 | `9/9` | `2/2` | `2/2` |
| `4830489` | `53_20252026_4830489` | Metz vs Angers | `2025-09-14` | `194f95daad3d` | 260220 | 21 | `10/10` | `2/2` | `2/2` |
| `4830490` | `53_20252026_4830490` | Nice vs Nantes | `2025-09-13` | `e159bd5c3766` | 289537 | 21 | `7/7` | `2/2` | `2/2` |
| `4830491` | `53_20252026_4830491` | Paris Saint-Germain vs Lens | `2025-09-14` | `2ce99dee6fbb` | 314721 | 17 | `10/10` | `2/2` | `2/2` |
| `4830492` | `53_20252026_4830492` | Rennes vs Lyon | `2025-09-14` | `4a743bf0da8b` | 291602 | 23 | `10/10` | `2/2` | `2/2` |
| `4830493` | `53_20252026_4830493` | Strasbourg vs Le Havre | `2025-09-14` | `921d04bdab7e` | 267677 | 19 | `8/8` | `2/2` | `2/2` |
| `4830498` | `53_20252026_4830498` | Lyon vs Angers | `2025-09-19` | `2e10ffd452ce` | 240148 | 16 | `9/9` | `2/2` | `2/2` |

## Blockers

- Acquisition blocker encountered: `900002` (`47_20242025_900002`) returned `HTTP 404` and `TRANSFORM_FAILED: no structured match data`; no DB row was written for that target
- Remaining non-retained targets after this bounded round: `900002`, `4837496`
- No parser blocker was introduced on the retained `58`-row sample

## Conclusion

- This bounded round increased retained `fotmob_live_v1` raw rows from `24` to `58` by adding `34` real match detail raws
- Full retained-sample parser dry-run stayed green on `58/58` rows with `1106/1106` events parity
- No `matches` / `features` / `odds` writes were performed
- No feature engineering, model training, or next-stage design work was performed
- Do not start the next task automatically
