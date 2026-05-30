# ADG42 Corrected Artifacts Canonical Contract

- lifecycle: phase-artifact
- Phase: Phase 5.21-ADG42
- total_corrected_candidates: 32
- canonical_url_atomic_identity_valid_count: 5
- canonical_url_missing_count: 27
- route_hash_pair_missing_count: 27
- route_hash_pair_unverified_count: 5
- historical_url_only_count: 27
- detail_page_verification_required_count: 32
- raw_write_ready_count: 0

## Boundary
- no live fetch / network / DB write / raw write / raw_match_data insert
- historical enriched URLs are historical_evidence_only, not L2 primary
- missing canonical URLs remain blocked; no fallback construction

## Next
ADG43 design L1 canonical URL pair discovery for missing candidates; do not fetch in ADG42
