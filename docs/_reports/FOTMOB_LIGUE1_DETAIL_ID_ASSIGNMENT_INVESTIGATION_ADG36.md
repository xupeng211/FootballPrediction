# ADG36 Detail ID Assignment Investigation

- Phase: Phase 5.21-ADG36
- total: 32
- route_code_reused: 0
- route_code_mismatch: 0
- lineage_verified: 32

## Root cause
ADG34 builder reuses historical route code from wrong-leg enriched URL
FotMob server serves detail page content based on route code path segment, not hash ID alone
4830473: old route code 2o4ahb from wrong-leg URL reused in corrected URL

## Fix
do NOT reuse route code when slug mismatch detected; use detail ID as fallback route code

## Next
ADG37: fix route code construction — use detail ID instead of historical route code when slug mismatch; do not raw write
