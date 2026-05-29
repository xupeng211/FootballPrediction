# ADG34 L2 URL Construction Fix

- Phase: Phase 5.21-ADG34
- total: 32
- constructed: 32
- slug_mismatch_detected: 19
- slug_blocked: 0
- adg32_4830473_fixed: true
- raw_write_ready: 0

## Key fix
- buildCorrectedFotmobDetailUrl() added to FotMobRouteIdentityReconciler
- Builds URLs from corrected_detail_id + expected home/away
- Does NOT use historical enriched source_page_url as primary
- 4830473: old slug angers-vs-psg → new slug paris-saint-germain-vs-angers

## Next
ADG35 bounded L2 detail-fetch using fixed URLs. Do not raw write.
