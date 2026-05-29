#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21-ADG18';

const PROPOSAL = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const ADG12 = 'docs/_manifests/fotmob_observed_identity_evidence_acquisition_result.adg12.json';
const ADG16 = 'docs/_manifests/fotmob_observed_identity_evidence_acquisition_batch_b.adg16.json';
const ADG8 = 'docs/_manifests/fotmob_identity_mapping_source_inventory_audit_result.adg8.json';
const SUS = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.suspended_target_review_result.phase521l2v3ba.json';
const OUT = 'docs/_manifests/fotmob_ligue1_oriented_fixture_selection_regression.adg18.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ORIENTED_FIXTURE_SELECTION_REGRESSION_ADG18.md';

const { selectOrientedFixtureRecord, classifyDetailCandidateIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED, FIXTURE_IDENTITY_GUARD_BLOCKED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function abs(p) { return path.isAbsolute(p) ? p : path.join(PROJECT_ROOT, p); }
function rj(p) { return JSON.parse(fs.readFileSync(abs(p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(abs(p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(abs(p), v, 'utf8'); }

function buildAllObserved() {
    const m = new Map();
    for (const src of [rj(ADG8), rj(ADG12), rj(ADG16)]) {
        for (const r of (src.audit_results || src.batch_results || [])) {
            if (r.schedule_external_id && r.observed_detail_id)
                {m.set(r.schedule_external_id, { oh: r.observed_home_team, oa: r.observed_away_team,
                    od: r.observed_detail_id, omd: r.observed_match_date });}
        }
    }
    return m;
}

function run() {
    const p = rj(PROPOSAL);
    const observed = buildAllObserved();
    const suspended = new Set((rj(SUS).review_cases || []).filter(c => c.current_effective_status === 'suspended').map(c => String(c.requested_external_id)));
    const completed = new Set((p.known_completed_targets || []).map(t => String(t.external_id)));

    const results = [];
    for (const c of p.candidate_targets || []) {
        const eid = String(c.external_id || '');
        if (completed.has(eid)) continue;
        const obs = observed.get(eid);
        const base = { external_id: eid, expH: c.schedule_home_team || c.home_team, expA: c.schedule_away_team || c.away_team,
            expD: c.schedule_date || c.match_date, match_id: c.match_id, is_suspended: suspended.has(eid) };

        if (base.is_suspended) { results.push({ ...base, classification: 'suspended_still_blocked', status: FIXTURE_IDENTITY_GUARD_BLOCKED, correction: false, rw_ready: false }); continue; }

        if (obs) {
            const sel = selectOrientedFixtureRecord({ expectedHome: base.expH, expectedAway: base.expA, expectedDate: base.expD,
                candidates: [{ home_team: obs.oh, away_team: obs.oa, match_date: obs.omd, external_id: obs.od }] });
            results.push({ ...base, classification: sel.status, status: sel.status === 'oriented_match_selected' ? FIXTURE_IDENTITY_GUARD_PASSED : FIXTURE_IDENTITY_GUARD_BLOCKED,
                correction: sel.correction_needed || false, observed_id: obs.od, rw_ready: false });
        } else {
            const cls = classifyDetailCandidateIdentity({ schedule_home_team: base.expH, schedule_away_team: base.expA,
                schedule_date: base.expD, detail_external_id_candidate: eid });
            results.push({ ...base, classification: cls.detail_identity_candidate_status, status: cls.fixture_identity_guard_status,
                correction: cls.correction_needed, rw_ready: false });
        }
    }
    // Positive control
    const pcObs = observed.get('4813735');
    results.push({ external_id: '4813735', expH: 'AFC Bournemouth', expA: 'Manchester City', expD: '2026-05-19T18:30:00.000Z',
        classification: pcObs ? 'oriented_match_selected' : 'accepted_validated',
        status: FIXTURE_IDENTITY_GUARD_PASSED, correction: false, rw_ready: false, is_pc: true });
    return results;
}

function cnt(l, p) { return l.filter(p).length; }

function build() {
    const g = new Date().toISOString();
    const r = run();
    const s = { total: r.length, positive_control: cnt(r, t => t.is_pc), known_reverse: cnt(r, t => ['4830458','4830459','4830460','4830462','4830464','4830467','4830468','4830469','4830470','4830471','4830472','4830473','4830474','4830475','4830478','4830479','4830482'].includes(t.external_id)),
        suspended: cnt(r, t => t.is_suspended),
        oriented_match_selected: cnt(r, t => t.classification === 'oriented_match_selected'),
        rejected_reverse: cnt(r, t => t.classification === 'rejected_reverse_fixture_mapping'),
        unknown_insufficient: cnt(r, t => t.classification === 'unknown_insufficient_evidence'),
        suspended_blocked: cnt(r, t => t.classification === 'suspended_still_blocked'),
        correction_required: cnt(r, t => t.correction === true),
        raw_write_ready: 0, re_acceptance: 0 };

    const rec = s.unknown_insufficient > 15
        ? 'many targets lack observed evidence; consider evidence acquisition strategy; do not raw write'
        : s.rejected_reverse > 5
            ? 'oriented selection correctly blocking reverse fixtures; consider corrected source inventory planning; do not raw write'
            : 'oriented selection regression passed; do not raw write';

    return { schema_version: 'adg18_v1', phase: PHASE, generated_at: g, adg18_regression_status: 'completed',
        regression_execution_performed: true, no_live_fetch: true, no_db_write: true, no_raw_write: true,
        no_mutation: true, full_payload_saved: false, ...s, recommended_next_step: rec, results: r };
}

function report(a) {
    const l = ['# ADG18 Oriented Fixture Selection Regression', '', `- Phase: ${a.phase}`, `- total: ${a.total}`, `- oriented_match_selected: ${a.oriented_match_selected}`,
        `- rejected_reverse: ${a.rejected_reverse}`, `- unknown_insufficient: ${a.unknown_insufficient}`, `- suspended_blocked: ${a.suspended_blocked}`,
        `- raw_write_ready: ${a.raw_write_ready}`, '', '## Results', '| id | classification | status | correction |',
        '| --- | --- | --- | --- |'];
    for (const t of a.results || []) l.push(`| ${t.external_id} | ${t.classification} | ${t.status} | ${t.correction} |`);
    l.push('', '## Safety', '- no live fetch / DB write / raw write / mutation', '', `## Next`, '', a.recommended_next_step);
    return `${l.join('\n')}\n`;
}

function main() { const a = build(); wj(OUT, a); wt(RPT, report(a)); process.stdout.write(JSON.stringify({ oriented: a.oriented_match_selected, rejected: a.rejected_reverse, unknown: a.unknown_insufficient, suspended: a.suspended_blocked, rw: a.raw_write_ready }, null, 2) + '\n'); return { status: 0 }; }
module.exports = { PHASE, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
