# Ligue 1 Source Inventory Inversion Correction Plan ADG13

- Phase: Phase 5.21-ADG13
- Status: completed_source_inventory_inversion_correction_planning
- Type: correction-planning / governance-only

## Evidence

ADG12 Batch A: 7/9 samples (7/7 with observed identity) = reverse_fixture_mapping_error

| Sample | Expected | Observed | Delta |
|--------|----------|----------|-------|
| 4830467 | Le Havre vs Lens | Lens vs Le Havre | 159d |
| 4830468 | Lille vs Monaco | Monaco vs Lille | 259d |
| 4830469 | Lorient vs Rennes | Rennes vs Lorient | 153d |
| 4830470 | Lyon vs Metz | Metz vs Lyon | 155d |
| 4830471 | Marseille vs Paris FC | Paris FC vs Marseille | 161d |
| 4830458 | Angers vs Paris FC | Paris FC vs Angers | 161d |
| 4830464 | Nantes vs PSG | PSG vs Nantes | 248d |

## Root Cause

Ligue 1 double round-robin format: each team pair has TWO fixtures (home leg + away leg).
The source inventory uses team-pair key (e.g. "angers|paris fc") which matches BOTH legs.
When the FotMob L1 API returns the reverse leg's page URL for a given team pair,
the detail_external_id_candidate is extracted from the wrong leg's URL hash.
Without home/away orientation validation, the inverted candidate enters the pipeline.

## Correction Strategy

**Reject/supersede inverted candidates during generation, not just at validation.**

### Runtime paths to correct

1. `FotMobSourceInventoryAdapter.toManifestCandidateSeed()`:
   - Add home/away orientation check
   - Mark inverted candidates with status=blocked_home_away_inversion

2. `pageprops_v2_source_inventory_enrichment_apply.js`:
   - Inline call to validateStrictFixtureIdentity() during enrichment
   - Block reverse_fixture candidates

3. `pageprops_v2_enriched_target_regeneration_execute.js`:
   - Add strict_guard_classification to regenerated targets
   - Set regeneration_blockers for reverse_fixture targets

### New candidate statuses

- rejected_home_away_inversion
- rejected_reverse_fixture_mapping
- requires_new_source_inventory_record

### Preservation
- Positive control #4813735 must still pass
- Suspended targets must stay blocked
- URL hash = evidence, not acceptance
- raw_write_execution_ready=false always

## ADG14 Implementation Scope

3-4 runtime files changed. No live fetch, no DB write, no raw write.

## Recommendation on 37 Remaining Targets

Stop Batch B/C/D expansion. 7/7 Ligue 1 samples are reverse errors.
Implement correction guard first (ADG14), then rerun regression (ADG15).

## Safety

No execution performed. No live fetch, network, DB write, raw write, re-acceptance, suspension reversal.

## Next Step

ADG14: runtime source inventory/candidate generation home/away inversion correction implementation.
Do not raw write. Do not Batch B/C/D.
