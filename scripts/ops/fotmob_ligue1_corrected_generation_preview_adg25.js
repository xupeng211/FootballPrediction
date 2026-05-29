#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG25
/* eslint-disable complexity */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG25';
const ADG22 = 'docs/_manifests/fotmob_ligue1_corrected_source_validation.adg22.json';
const ADG24 = 'docs/_manifests/fotmob_ligue1_remaining_corrected_source_validation.adg24.json';
const ADG20 = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory_generation.adg20.json';
const CURRENT_STATE = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_corrected_generation_preview.adg25.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_CORRECTED_GENERATION_PREVIEW_ADG25.md';

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const d22 = rj(ADG22); const d24 = rj(ADG24); const d20 = rj(ADG20);
    // Collect all validated corrected candidates
    const validated = [];
    for (const t of d22.validation_results || []) {
        if (t.validation_status === 'corrected_candidate_validated_no_write') {validated.push({
            external_id: t.external_id, expH: t.expH, expA: t.expA, expD: t.expD, selected_id: t.selected_id,
            selected_home: t.selected_home, selected_away: t.selected_away, phase: 'ADG22' });}
    }
    for (const t of d24.validation_results || []) {
        if (t.validation_status === 'corrected_candidate_validated_no_write') {validated.push({
            external_id: t.external_id, expH: t.expH, expA: t.expA, expD: t.expD, selected_id: t.selected_id,
            selected_home: t.selected_home, selected_away: t.selected_away, phase: 'ADG24' });}
    }
    // Collect wrong-leg rejected
    const wrongLeg = new Map();
    for (const t of d20.generation_results || []) {
        if (t.generation_status === 'rejected_current_reverse_fixture_record') wrongLeg.set(t.external_id, t);
    }

    const results = [];
    for (const v of validated) {
        const isWrongLeg = wrongLeg.has(v.external_id);
        results.push({
            external_id: v.external_id, match_id: v.match_id || null,
            expected_home: v.expH, expected_away: v.expA, expected_date: v.expD,
            corrected_detail_id: v.selected_id, corrected_home: v.selected_home, corrected_away: v.selected_away,
            validation_phase: v.phase, validation_status: 'validated_corrected_candidate',
            proposed_source_action: 'proposed_corrected_source_inventory_record',
            proposed_candidate_action: isWrongLeg ? 'supersede_current_wrong_leg_candidate_no_write' : 'proposed_corrected_candidate_record',
            supersedes_wrong_leg: isWrongLeg,
            correction_type: isWrongLeg ? 'supersede_with_corrected_candidate' : 'new_corrected_candidate',
            raw_write_ready: false, re_acceptance_candidate: false,
            recommended_next_action: 'no_write_pending_authorization'
        });
    }
    // Controls
    results.push({ external_id: '4813735', generation_status: 'positive_control_preserved', raw_write_ready: false });
    results.push({ external_id: '4830466', generation_status: 'suspended_still_blocked', raw_write_ready: false });
    // Suspended from ADG20
    for (const t of d20.generation_results || []) {
        if (t.generation_status === 'preserved_suspended_blocked')
            {results.push({ external_id: t.external_id, generation_status: 'suspended_still_blocked', raw_write_ready: false });}
    }
    return { validated, wrong_leg_count: wrongLeg.size, results };
}

function cnt(l, p) { return l.filter(p).length; }
function build() {
    const g = new Date().toISOString(); const r = run();
    const previews = r.results.filter(t => t.validation_status === 'validated_corrected_candidate');
    const s = {
        validated_count: r.validated.length,
        proposed_source_inventory: cnt(previews, t => t.proposed_source_action === 'proposed_corrected_source_inventory_record'),
        proposed_candidate: cnt(previews, t => t.proposed_candidate_action?.includes('proposed_corrected')),
        supersede_wrong_leg: cnt(previews, t => t.supersedes_wrong_leg),
        wrong_leg_total: r.wrong_leg_count,
        positive_preserved: cnt(r.results, t => t.generation_status === 'positive_control_preserved'),
        suspended_blocked: cnt(r.results, t => t.generation_status === 'suspended_still_blocked'),
        raw_write_ready: 0, re_acceptance: 0,
    };
    const rec = 'corrected generation preview complete for 32 validated candidates; recommend ADG26 controlled correction implementation planning; do not raw write';
    return { schema_version: 'adg25_v1', phase: PH, generated_at: g, adg25_status: 'completed_generation_preview',
        generation_preview_performed: true, no_network: true, no_db_write: true, no_raw_write: true, no_mutation: true,
        full_payload_saved: false, ...s, recommended_next_step: rec, generation_results: r.results };
}

function report(a) {
    const l = ['# ADG25 Corrected Generation Preview', '', `- Phase: ${a.phase}`,
        `- validated_candidates: ${a.validated_count}`,
        `- proposed_source_inventory: ${a.proposed_source_inventory}`,
        `- proposed_candidate: ${a.proposed_candidate}`,
        `- supersede_wrong_leg: ${a.supersede_wrong_leg}`,
        `- wrong_leg_total: ${a.wrong_leg_total}`,
        `- suspended_blocked: ${a.suspended_blocked}`,
        `- raw_write_ready: ${a.raw_write_ready}`, '',
        '## Preview (first 10 of 32)', '| id | action | correction |', '| --- | --- | --- |'];
    for (const t of a.generation_results.filter(t => t.validation_status).slice(0, 10))
        {l.push(`| ${t.external_id} | ${t.proposed_candidate_action} | ${t.correction_type} |`);}
    l.push(`| ... | ... (${a.validated_count - 10} more) | ... |`);
    l.push('', '## Safety', '- no network / DB write / raw write / mutation', '- raw_write_ready=0', '- all generation_preview only', '', '## Next', '', a.recommended_next_step);
    return `${l.join('\n')}\n`;
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CURRENT_STATE), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG25 corrected generation preview';
        return line;
    });
    fs.writeFileSync(path.join(PP, CURRENT_STATE), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ validated: a.validated_count, source: a.proposed_source_inventory, candidate: a.proposed_candidate, supersede: a.supersede_wrong_leg, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
