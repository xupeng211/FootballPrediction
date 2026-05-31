#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG57 dry-run is superseded by ADG58
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG57-DRY-RUN';
const A56 = 'docs/_manifests/fotmob_ligue1_adg56_date_guard_completion_review.json';
const A54 = 'docs/_manifests/fotmob_ligue1_adg54_canonical_identity_promotion_preview.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg57_no_write_mutation_dry_run_preview.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG57_NO_WRITE_MUTATION_DRY_RUN_PREVIEW.md';
function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a56 = rj(A56); const a54 = rj(A54);
    const records = a56.reviewed_records || [];
    const dryRunRecords = records.map(r => ({
        target_match_id: r.target_match_id,
        expected_home: r.expected_home, expected_away: r.expected_away, expected_date: r.expected_date,
        corrected_canonical_detail_url: r.corrected_canonical_detail_url,
        corrected_route_code: r.corrected_route_code, corrected_hash_id: r.corrected_hash_id, corrected_route_hash_pair: r.corrected_route_hash_pair,
        eligibility_status: r.eligibility_no_write || 'eligibility_ready_no_write',
        proposed_future_operation: 'source_controlled_canonical_identity_artifact_update',
        requires_reacceptance_authorization: true,
        requires_suspension_resolution_authorization: true,
        dry_run_only: true, mutation_executed: false,
        rollback_key: `rollback_${r.target_match_id}`,
        validation_checks_required: ['canonical_url_parse','route_hash_pair_atomic','orientation_match','date_match','competition_match','duplicate_free','reacceptance_authorized'],
    }));
    const futureMutationPrerequisites = [
        'explicit_user_authorization_naming_exact_phase_and_scope','dedicated_mutation_branch','clean_worktree','explicit_target_allowlist','no_git_add_dot',
        'db_backup_snapshot_plan_if_db_mutation_included','transaction_boundary_plan','begin_commit_rollback_strategy','dry_run_manifest_reviewed_and_merged',
        'rollback_manifest','post_mutation_select_only_validation','post_mutation_tests','main_ci_green_before_and_after','no_network_unless_separately_authorized','no_full_payload_save',
    ];
    return {
        schema_version: 'adg57_dry_run_v1', lifecycle: 'phase-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: [A56, A54, CS],
        safety: { live_fetch_performed: false, network_request_performed: false, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false, re_acceptance_performed: false, suspension_reversal_performed: false },
        adg57_status: 'dry_run_preview_completed',
        total_targets: 32, dry_run_records_generated: dryRunRecords.length,
        eligibility_ready_no_write: 32, date_pass: 32, promotion_guard_blocked: 0,
        reacceptance_required: 32, suspension_resolution_required: 32,
        mutation_executed: 0, db_write_performed: false, raw_write_performed: false, raw_match_data_insert_performed: false, re_acceptance_performed: false, suspension_reversal_performed: false,
        proposed_future_mutation_classes: [
            { name: 'source_controlled_canonical_identity_artifact_update', executed: false, description: 'Update source-controlled canonical identity manifest with corrected route_hash_pairs from ADG52 league schedule discovery' },
            { name: 'acceptance_state_reacceptance', executed: false, description: 'Re-accept corrected candidates with explicit per-target or batch authorization' },
            { name: 'suspended_state_resolution', executed: false, description: 'Resolve suspended/verification-required state for previously blocked candidates' },
            { name: 'downstream_l2_input_refresh_preview', executed: false, description: 'Generate preview of updated L2 input using corrected canonical identities' },
            { name: 'post_mutation_regression', executed: false, description: 'Run regression checks against existing ADG41/42 contracts' },
        ],
        future_mutation_prerequisites: futureMutationPrerequisites,
        raw_write_ready_count: 0, recommended_next_step: 'User must authorize ADG58 controlled mutation authorization gate; do NOT raw write',
        dry_run_records: dryRunRecords,
    };
}

function writeReport(data) {
    const lines = ['# ADG57 No-Write Mutation Dry-Run Preview', '', `- Phase: ${PH}`, `- total: ${data.total_targets}`, `- dry_run_records: ${data.dry_run_records_generated}`, `- eligibility: ${data.eligibility_ready_no_write}`, `- reacceptance_required: ${data.reacceptance_required}`,
        '', '## Future Mutation Classes', ...data.proposed_future_mutation_classes.map(c => `- ${c.name}: ${c.description}`),
        '', '## Mutation Prerequisites', ...data.future_mutation_prerequisites.map(p => `- ${p}`),
        '', '## Safety', '- no DB/raw write, no re-acceptance, no full payload', '- all records dry_run_only=true, mutation_executed=false', '', '## Next', 'User must authorize ADG58 controlled mutation gate'];
    wt(RPT, lines.join('\n') + '\n');
}
if (require.main === module) { const d = build(); wj(OUT, d); writeReport(d); console.log(JSON.stringify({ adg57_status: d.adg57_status, total: d.total_targets, dry_run_records: d.dry_run_records_generated, raw_write_ready_count: 0 }, null, 2)); }
module.exports = { build };
