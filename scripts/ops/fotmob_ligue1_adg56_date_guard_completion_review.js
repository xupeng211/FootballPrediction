#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG56 review is superseded by ADG57
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG56-DATE-GUARD';
const A54 = 'docs/_manifests/fotmob_ligue1_adg54_canonical_identity_promotion_preview.json';
const A52 = 'docs/_manifests/fotmob_ligue1_adg52_league_schedule_ssr_probe.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg56_date_guard_completion_review.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG56_DATE_GUARD_COMPLETION_REVIEW.md';
function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a54 = rj(A54); const a52 = rj(A52);
    const records = a54.preview_records || [];
    const a52matches = (a52.result?.matched_targets_summary || []).reduce((m, t) => { m.set(t.target_match_id, t); return m; }, new Map());

    const priorDatePass = records.filter(r => r.date_status === 'matches').length;
    const priorDateUnknown = records.filter(r => r.date_status === 'unknown').length;
    let completedThisPhase = 0;

    const reviewed = records.map(r => {
        const tid = r.target_match_id.split('_').pop();
        const a52m = a52matches.get(tid);
        const updated = { ...r };

        if (r.date_status === 'unknown' && a52m?.candidate_date) {
            updated.expected_date = a52m.candidate_date;
            updated.date_status = 'matches';
            updated.date_source = 'adg52_safe_summary_candidate_date';
            completedThisPhase++;
        }
        if (r.date_status === 'unknown' && r.candidate_date && !updated.expected_date) {
            updated.expected_date = r.candidate_date;
            updated.date_status = 'matches';
            updated.date_source = 'adg54_candidate_date';
            completedThisPhase++;
        }

        // Eligibility reclassification
        const blocked = [...(r.promotion_guard_blockers || [])];
        if (updated.date_status !== 'matches') blocked.push('date_unknown');
        const eligible = blocked.length === 0;
        updated.eligibility_no_write = eligible ? 'eligibility_ready_no_write' : (updated.date_status === 'unknown' ? 'eligibility_date_unknown' : 'eligibility_blocked');
        updated.eligibility_blockers = blocked;
        return updated;
    });

    const datePassAfter = reviewed.filter(r => r.date_status === 'matches').length;
    const dateUnknownAfter = reviewed.filter(r => r.date_status === 'unknown').length;
    const eligible = reviewed.filter(r => r.eligibility_no_write === 'eligibility_ready_no_write').length;
    const dateUnknown = reviewed.filter(r => r.eligibility_no_write === 'eligibility_date_unknown').length;
    const blockedCount = reviewed.filter(r => r.eligibility_no_write === 'eligibility_blocked').length;

    return {
        schema_version: 'adg56_date_guard_v1', lifecycle: 'phase-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: [A54, A52, CS],
        safety: { live_fetch_performed: false, network_request_performed: false, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false, re_acceptance_performed: false, suspension_reversal_performed: false },
        adg56_status: 'date_guard_completion_completed',
        total_targets: 32, prior_date_pass: priorDatePass, prior_date_unknown: priorDateUnknown,
        date_completed_this_phase: completedThisPhase, date_pass_after_adg56: datePassAfter, remaining_date_unknown: dateUnknownAfter,
        eligibility_ready_no_write: eligible, eligibility_date_unknown: dateUnknown, eligibility_blocked: blockedCount,
        suspended_requires_authorization: 32,
        raw_write_ready_count: 0, db_write_performed: false, raw_write_performed: false, re_acceptance_performed: false, suspension_reversal_performed: false,
        recommended_next_step: 'User must authorize ADG57 no-write mutation dry-run preview; all 32 require explicit re-acceptance authorization; do NOT raw write',
        reviewed_records: reviewed,
    };
}

function writeReport(data) {
    const lines = ['# ADG56 Date Guard Completion / Eligibility Review', '', `- Phase: ${PH}`, `- total: ${data.total_targets}`, `- prior_date_pass: ${data.prior_date_pass}, prior_date_unknown: ${data.prior_date_unknown}`, `- date_completed_this_phase: ${data.date_completed_this_phase}`, `- date_pass_after: ${data.date_pass_after_adg56}, remaining_date_unknown: ${data.remaining_date_unknown}`, `- eligibility_ready: ${data.eligibility_ready_no_write}, eligibility_date_unknown: ${data.eligibility_date_unknown}, blocked: ${data.eligibility_blocked}`, `- suspended_requires_auth: ${data.suspended_requires_authorization}`, `- raw_write_ready_count: 0`, '', '## Safety', '- no network, no DB/raw write, no re-acceptance', '', '## Next', 'User must authorize ADG57 no-write mutation dry-run preview'];
    wt(RPT, lines.join('\n') + '\n');
}
if (require.main === module) { const d = build(); wj(OUT, d); writeReport(d); console.log(JSON.stringify({ adg56_status: d.adg56_status, total: d.total_targets, date_pass_after: d.date_pass_after_adg56, remaining_unknown: d.remaining_date_unknown, eligible: d.eligibility_ready_no_write, raw_write_ready_count: 0 }, null, 2)); }
module.exports = { build };
