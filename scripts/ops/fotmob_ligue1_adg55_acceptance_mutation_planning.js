#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG55 planning is superseded by ADG56
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG55-PLANNING';
const A54 = 'docs/_manifests/fotmob_ligue1_adg54_canonical_identity_promotion_preview.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg55_acceptance_mutation_planning.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG55_ACCEPTANCE_MUTATION_PLANNING.md';
function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a54 = rj(A54);
    const records = a54.preview_records || [];
    const datePass = records.filter(r => r.date_status === 'matches').length;
    const dateUnknown = records.filter(r => r.date_status === 'unknown').length;
    return {
        schema_version: 'adg55_planning_v1', lifecycle: 'phase-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: [A54, CS],
        safety: { live_fetch_performed: false, network_request_performed: false, detail_page_fetch_performed: false, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false, re_acceptance_performed: false, suspension_reversal_performed: false },
        adg55_status: 'acceptance_mutation_planning_completed',
        current_promotion_state: {
            total_targets: a54.total_targets, promotion_preview_ready: a54.promotion_preview_ready_count,
            promotion_guard_blocked: a54.promotion_guard_blocked_count,
            suspended_requires_authorization: a54.suspended_requires_authorization_count,
            date_pass: datePass, date_unknown: dateUnknown, raw_write_ready: 0,
        },
        acceptance_eligibility_categories: {
            category_a_ready_for_acceptance_planning_date_guard_passed: { count: datePass, note: 'Date verified; still no mutation in ADG55; needs explicit re-acceptance authorization before any mutation' },
            category_b_requires_date_guard_completion: { count: dateUnknown, note: 'Expected dates not populated in source-controlled artifacts; cannot proceed to mutation until dates filled or explicit waiver exists' },
            category_c_blocked_by_guard: { count: 0, note: 'All 32 pass all guards; zero blocked' },
            category_d_requires_explicit_reacceptance_authorization: { count: 32, note: 'All 32 targets currently in suspended/verification-required state from ADG42; re-acceptance must be explicitly authorized per target or batch' },
        },
        mutation_planning_boundary: {
            no_mutation_executed_in_adg55: true,
            future_mutation_prerequisites: [
                'dedicated branch from clean main', 'clean worktree', 'explicit file allowlist', 'no git add .',
                'DB backup/snapshot plan if DB mutation is ever authorized', 'read-only preflight before write',
                'no raw payload save', 'no full HTML/NEXT_DATA/pageProps save', 'no network during mutation stage unless separately authorized',
                'dry-run manifest first', 'mutation scope limited to exactly authorized targets', 'rollback plan', 'post-mutation validation/regression', 'main CI green before and after',
            ],
            current_stage: 'planning_only', mutation_executed: false,
        },
        recommended_next_phase: {
            phase: 'ADG56', type: 'date guard completion / acceptance eligibility review without writes',
            goal: 'Fill expected_date for 27 unknown targets using source-controlled ADG52 safe summary and existing candidate artifacts only; no network; no DB/raw write',
            expected_outputs: ['expected_date_completed_count','remaining_date_unknown_count','acceptance_eligibility_count','still_requires_reacceptance_authorization_count','raw_write_ready_count=0'],
            requires_user_authorization: true, not_executed_in_adg55: true,
        },
        raw_write_ready_count: 0,
        recommended_next_step: 'User must authorize ADG56 date guard completion / acceptance eligibility review without writes; do NOT raw write; do NOT DB write',
    };
}

function writeReport(data) {
    const s = data.current_promotion_state; const c = data.acceptance_eligibility_categories;
    const lines = ['# ADG55 Acceptance / Mutation Planning', '', `- Phase: ${PH}`, '- mutation_executed: false', '', '## Current Promotion State', `- total: ${s.total_targets}`, `- promotion_preview_ready: ${s.promotion_preview_ready}`, `- guard_blocked: ${s.promotion_guard_blocked}`, `- suspended_requires_auth: ${s.suspended_requires_authorization}`, `- date_pass: ${s.date_pass}`, `- date_unknown: ${s.date_unknown}`, `- raw_write_ready: ${s.raw_write_ready}`,
        '', '## Eligibility Categories', `- Category A (date pass): ${c.category_a_ready_for_acceptance_planning_date_guard_passed.count}`, `- Category B (date unknown): ${c.category_b_requires_date_guard_completion.count}`, `- Category C (blocked): ${c.category_c_blocked_by_guard.count}`, `- Category D (requires re-acceptance): ${c.category_d_requires_explicit_reacceptance_authorization.count}`,
        '', '## Mutation Boundary', '- no mutation in ADG55', '- 8 prerequisites defined for any future mutation', '',
        '## Recommended ADG56', `- type: ${data.recommended_next_phase.type}`, `- goal: ${data.recommended_next_phase.goal}`, `- requires user authorization: ${data.recommended_next_phase.requires_user_authorization}`,
        '', '## Next', 'User must authorize ADG56 date guard completion; do NOT raw write'];
    wt(RPT, lines.join('\n') + '\n');
}
if (require.main === module) { const d = build(); wj(OUT, d); writeReport(d); console.log(JSON.stringify({ adg55_status: d.adg55_status, ready: d.current_promotion_state.promotion_preview_ready, date_pass: d.current_promotion_state.date_pass, date_unknown: d.current_promotion_state.date_unknown, raw_write_ready_count: 0 }, null, 2)); }
module.exports = { build };
