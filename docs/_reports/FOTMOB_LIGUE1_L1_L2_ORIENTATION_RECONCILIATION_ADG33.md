# ADG33 L1/L2 Orientation Reconciliation

- Phase: Phase 5.21-ADG33
- targets_checked: 32
- slug_mismatch: 15
- root_cause: enriched_source_page_url_contains_wrong_leg_slug

## Key finding
L1 league API orientation IS correct. The issue is in L2 URL construction.
ADG32 used enriched source_page_url directly, but those URLs contain wrong-leg slugs
from the original (pre-correction) source inventory.

## Impact
15 targets have source_page_url slugs that encode the reverse orientation.
32 corrected candidates marked as detail_page_verification_required.
ADG21-ADG27 conclusion remains valid: L1 orientation data IS correct.
Only L2 URL construction needs fixing.

## Next
ADG34: fix L2 URL construction. Do NOT raw write.
