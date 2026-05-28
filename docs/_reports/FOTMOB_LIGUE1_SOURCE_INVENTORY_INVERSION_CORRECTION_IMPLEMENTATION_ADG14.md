# Ligue 1 Source Inventory Inversion Correction Implementation ADG14

- Phase: Phase 5.21-ADG14
- Status: completed_runtime_correction_implementation
- runtime_code_changed=true

## Runtime Changes

### 1. FotMobRouteIdentityReconciler.js
Added `classifyDetailCandidateIdentity()` — classifies detail identity candidates at generation time using source-controlled evidence. Returns `detail_identity_candidate_status` (accepted_validated/rejected_home_away_inversion/rejected_reverse_fixture_mapping/requires_new_source_inventory_record/unknown_insufficient_evidence).

### 2. FotMobSourceInventoryAdapter.js
Updated `buildDetailIdentityFields()` and `buildSourceEvidenceFields()` to call `classifyDetailCandidateIdentity()` during candidate generation. Adds `detail_identity_candidate_status`, `fixture_identity_guard_status`, `correction_needed` fields to manifest candidate seeds. Source inventory candidates are now classified at generation time, not just at validation time.

## Behavior

- Positive control #4813735: accepted_validated / guard passed
- Seven reverse samples (4830458-4830471): rejected_reverse_fixture_mapping / guard blocked / correction_needed=true
- URL hash alone: unknown_insufficient_evidence / not accepted
- Same team pair wrong date: blocked
- All: raw_write_execution_ready=false

## Validation

- 55/55 regression tests pass (ADG14 9 + Adapter 14 + Reconciler 12 + ADG9 11 + ADG12 9)
- No DB write, no raw write, no live fetch, no network
