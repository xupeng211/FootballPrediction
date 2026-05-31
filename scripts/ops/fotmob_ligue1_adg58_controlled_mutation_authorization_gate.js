#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG58 gate is superseded by ADG59A
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG58-GATE';
const A57 = 'docs/_manifests/fotmob_ligue1_adg57_no_write_mutation_dry_run_preview.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg58_controlled_mutation_authorization_gate.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG58_CONTROLLED_MUTATION_AUTHORIZATION_GATE.md';
function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a57 = rj(A57);
    const records = a57.dry_run_records || [];
    const allowlist = records.map(r => ({
        target_match_id: r.target_match_id,
        expected_home: r.expected_home, expected_away: r.expected_away, expected_date: r.expected_date,
        corrected_canonical_detail_url: r.corrected_canonical_detail_url,
        corrected_route_code: r.corrected_route_code, corrected_hash_id: r.corrected_hash_id, corrected_route_hash_pair: r.corrected_route_hash_pair,
        eligibility_status: 'eligible_no_write',
        future_scope_a_allowed: true, future_scope_b_requires_explicit_authorization: true, future_scope_c_planned: true,
        rollback_key: `rollback_${r.target_match_id}`,
        validation_checks: ['canonical_url_parse','route_hash_pair_atomic','orientation_match','date_match','competition_match','duplicate_free','reacceptance_authorized'],
    }));
    return {
        schema_version: 'adg58_gate_v1', lifecycle: 'phase-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: [A57, CS],
        safety: { live_fetch_performed: false, network_request_performed: false, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false, re_acceptance_performed: false, suspension_reversal_performed: false },
        adg58_status: 'authorization_gate_prepared', mutation_not_executed: true,
        total_targets: 32, authorization_gate_records: allowlist.length,
        scope_a_allowed: 32, scope_b_requires_explicit_authorization: 32, scope_c_planned: 32,
        mutation_executed: 0, raw_write_ready_count: 0,
        future_mutation_scopes: {
            scope_a: { name: 'source_controlled_canonical_identity_artifact_promotion', future_phase: 'ADG59A', description: 'Mutates source-controlled artifacts only. No DB write. No raw write. Requires explicit authorization.', db_write_required: false, raw_write_required: false, requires_explicit_authorization: true },
            scope_b: { name: 'acceptance_suspension_state_mutation', future_phase: 'ADG59B', description: 'May require DB mutation. Must have DB backup/transaction/rollback. Must not be combined with Scope A unless separately authorized. Requires explicit authorization naming exact target scope. Still no raw_match_data insert unless separately authorized.', db_write_required: true, raw_write_required: false, requires_explicit_authorization: true },
            scope_c: { name: 'downstream_l2_input_refresh_preview', future_phase: 'ADG60', description: 'No network unless separately authorized. Based on accepted canonical identity artifacts.', db_write_required: false, raw_write_required: false, requires_explicit_authorization: true },
        },
        authorization_phrases: { scope_a: '我授权执行 ADG59A source-controlled canonical identity artifact promotion for exactly 32 Ligue 1 targets, no DB write, no raw write.', scope_b: '我授权执行 ADG59B acceptance/suspension state mutation for exactly approved targets with DB backup and rollback plan.', note: 'If user only says 继续 or 执行下一步, do NOT enter mutation.' },
        rollback_plan: { source_artifact: 'Restore prior manifest from git history', db: 'ROLLBACK or restore from backup snapshot', manifest: 'Rollback manifest with pre/post counts', post_mutation: 'SELECT-only verification + CI regression', no_force_push: true, no_history_rewrite: true },
        validation_plan: ['preflight_main_ci_green','clean_worktree','hidden_bidi_scan','explicit_file_allowlist','target_allowlist_check','canonical_url_parser_check','route_hash_pair_atomic_check','orientation_date_competition_guard_check','duplicate_conflict_check','db_select_only_preflight_before_db_write','post_mutation_select_only_verification','tests_lint','main_ci_green_after_merge'],
        recommended_next_step: 'User must explicitly authorize ADG59A source-controlled artifact promotion using the defined authorization phrase; do NOT enter mutation without it',
        target_allowlist: allowlist,
    };
}

function writeReport(data) {
    const lines = ['# ADG58 Controlled Mutation Authorization Gate', '', `- Phase: ${PH}`, `- total: ${data.total_targets}`, `- allowlist: ${data.authorization_gate_records}`, `- scope_a_allowed: ${data.scope_a_allowed}`, `- scope_b_requires_auth: ${data.scope_b_requires_explicit_authorization}`, `- mutation_executed: ${data.mutation_executed}`, `- raw_write_ready_count: 0`,
        '', '## Future Mutation Scopes', '### Scope A: Artifact Promotion', `- phase: ${data.future_mutation_scopes.scope_a.future_phase}`, `- DB write: ${data.future_mutation_scopes.scope_a.db_write_required}`, `- raw write: ${data.future_mutation_scopes.scope_a.raw_write_required}`,
        '### Scope B: Acceptance/Suspension Mutation', `- phase: ${data.future_mutation_scopes.scope_b.future_phase}`, `- DB write: ${data.future_mutation_scopes.scope_b.db_write_required}`,
        '### Scope C: L2 Input Preview', `- phase: ${data.future_mutation_scopes.scope_c.future_phase}`,
        '', '## Authorization Required', `- Scope A: ${data.authorization_phrases.scope_a}`, `- Scope B: ${data.authorization_phrases.scope_b}`, `- ${data.authorization_phrases.note}`,
        '', '## Rollback & Validation', `- Rollback: ${data.rollback_plan.source_artifact}, ${data.rollback_plan.db}`, `- Validation: ${data.validation_plan.length} steps`,
        '', '## Next', 'User must explicitly authorize ADG59A using the defined phrase'];
    wt(RPT, lines.join('\n') + '\n');
}
if (require.main === module) { const d = build(); wj(OUT, d); writeReport(d); console.log(JSON.stringify({ adg58_status: d.adg58_status, total: d.total_targets, scope_a: d.scope_a_allowed, raw_write_ready_count: 0 }, null, 2)); }
module.exports = { build };
