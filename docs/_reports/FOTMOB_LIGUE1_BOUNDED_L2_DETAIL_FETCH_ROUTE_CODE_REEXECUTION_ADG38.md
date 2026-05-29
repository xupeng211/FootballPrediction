# ADG38 Route Code Fix Verification

- Phase: Phase 5.21-ADG38
- planned: 3
- attempted: 3
- success: 0
- validation_failed: 1
- route_code_fix_verified: false
- 4830473_orientation: unknown
- rw: 0

## Results
| id | status | observed | orientation |
| --- | --- | --- | --- |
| 4830473 | hydration_identity_missing | ? vs ? | ? |
| 4830487 | validation_failed | Toulouse vs Lille | reversed |
| 4830507 | hydration_identity_missing | ? vs ? | ? |

## Safety notes
- attempted=3: script continued past 4830473 hydration_identity_missing (stop rule only triggered on validation_failed, not hydration_missing — script bug noted)
- all 3 requests within bounded scope (3 planned, 3 attempted, 0 beyond 3)
- no raw write, no DB write, no full payload, no browser/proxy

## Next
ADG39: investigate canonical detail URLs / alternate route codes from L1 artifacts. Do not raw write. Do not expand fetch.
