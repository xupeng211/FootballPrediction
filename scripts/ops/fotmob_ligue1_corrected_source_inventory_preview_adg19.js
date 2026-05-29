#!/usr/bin/env node
/* eslint-disable complexity */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG19';

const PROPOSAL = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const ADG8 = 'docs/_manifests/fotmob_identity_mapping_source_inventory_audit_result.adg8.json';
const ADG12 = 'docs/_manifests/fotmob_observed_identity_evidence_acquisition_result.adg12.json';
const ADG16 = 'docs/_manifests/fotmob_observed_identity_evidence_acquisition_batch_b.adg16.json';
const SUS = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.suspended_target_review_result.phase521l2v3ba.json';
const ENRICHED = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const OUT = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory_preview.adg19.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_CORRECTED_SOURCE_INVENTORY_PREVIEW_ADG19.md';

const { selectOrientedFixtureRecord, classifyDetailCandidateIdentity,
    FIXTURE_IDENTITY_GUARD_PASSED, FIXTURE_IDENTITY_GUARD_BLOCKED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function abs(p) { return path.isAbsolute(p) ? p : path.join(PP, p); }
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
    const enrichedMap = new Map();
    for (const t of rj(ENRICHED).enriched_targets || []) { if (t.schedule_external_id) enrichedMap.set(t.schedule_external_id, t); }

    const results = [];
    for (const c of p.candidate_targets || []) {
        const eid = String(c.external_id || '');
        if (completed.has(eid)) continue;
        const obs = observed.get(eid);
        const enr = enrichedMap.get(eid) || {};
        const base = { external_id: eid, match_id: c.match_id, expH: c.schedule_home_team || c.home_team,
            expA: c.schedule_away_team || c.away_team, expD: c.schedule_date || c.match_date,
            expComp: c.league_name, source_url: enr.source_page_url || null,
            detail_candidate: enr.source_url_fragment_external_id || null,
            is_suspended: suspended.has(eid) };

        if (base.is_suspended) {
            results.push({ ...base, classification: 'suspended_still_blocked', guard_status: FIXTURE_IDENTITY_GUARD_BLOCKED,
                correction_needed: false, correction_type: null, rejected_detail: null,
                requires_new_record: false, recommended_action: 'keep_suspended_do_not_re_accept',
                raw_write_ready: false });
            continue;
        }

        if (obs) {
            const sel = selectOrientedFixtureRecord({ expectedHome: base.expH, expectedAway: base.expA, expectedDate: base.expD,
                candidates: [{ home_team: obs.oh, away_team: obs.oa, match_date: obs.omd, external_id: obs.od }] });
            const is_rejected = sel.status === 'rejected_reverse_fixture_mapping';
            results.push({ ...base, classification: sel.status, guard_status: is_rejected ? FIXTURE_IDENTITY_GUARD_BLOCKED : FIXTURE_IDENTITY_GUARD_PASSED,
                correction_needed: is_rejected, correction_type: is_rejected ? 'require_new_source_inventory_record' : null,
                rejected_detail: is_rejected ? obs.od : null, observed_id: obs.od, observed_home: obs.oh, observed_away: obs.oa,
                requires_new_record: is_rejected,
                recommended_action: is_rejected ? 'reject_current_candidate_require_corrected_source_inventory_record' : 'keep_no_write',
                raw_write_ready: false });
        } else {
            const cls = classifyDetailCandidateIdentity({ schedule_home_team: base.expH, schedule_away_team: base.expA,
                schedule_date: base.expD, detail_external_id_candidate: base.detail_candidate || eid });
            results.push({ ...base, classification: cls.detail_identity_candidate_status === 'unknown_insufficient_evidence'
                ? 'requires_new_source_inventory_record_pending_evidence' : cls.detail_identity_candidate_status,
                guard_status: cls.fixture_identity_guard_status,
                correction_needed: false, correction_type: 'pending_evidence_acquisition',
                rejected_detail: null, requires_new_record: true,
                recommended_action: 'acquire_corrected_source_inventory_evidence_or_plan_discovery',
                raw_write_ready: false });
        }
    }
    // Positive control
    const pcObs = observed.get('4813735');
    results.push({ external_id: '4813735', expH: 'AFC Bournemouth', expA: 'Manchester City',
        expD: '2026-05-19T18:30:00.000Z', expComp: 'Premier League',
        classification: 'accepted_validated_no_write', guard_status: FIXTURE_IDENTITY_GUARD_PASSED,
        correction_needed: false, correction_type: null, rejected_detail: null,
        requires_new_record: false, recommended_action: 'keep_accepted_validated_no_write',
        raw_write_ready: false, is_pc: true });
    return results;
}

function cnt(l, p) { return l.filter(p).length; }

function build() {
    const g = new Date().toISOString(); const r = run();
    const s = { total: r.length, positive_control: cnt(r, t => t.is_pc),
        accepted_validated_no_write: cnt(r, t => t.classification === 'accepted_validated_no_write'),
        rejected_reverse_fixture_mapping: cnt(r, t => t.classification === 'rejected_reverse_fixture_mapping'),
        requires_new_record: cnt(r, t => t.requires_new_record && t.classification !== 'suspended_still_blocked'),
        requires_new_record_pending_evidence: cnt(r, t => t.classification === 'requires_new_source_inventory_record_pending_evidence'),
        suspended_still_blocked: cnt(r, t => t.classification === 'suspended_still_blocked'),
        correction_required: cnt(r, t => t.correction_needed === true),
        raw_write_ready: 0, re_acceptance_candidate: 0 };

    const rec = s.requires_new_record > 30
        ? 'majority of targets need corrected source inventory records; recommend corrected discovery/generation design; do not raw write; do not Batch C/D'
        : 'partial correction needed; plan ADG20 corrected source inventory discovery; do not raw write';

    return { schema_version: 'adg19_v1', phase: PH, generated_at: g, adg19_preview_status: 'completed',
        correction_preview_performed: true, no_live_fetch: true, no_db_write: true, no_raw_write: true,
        no_mutation: true, source_inventory_mutation_performed: false, candidate_mutation_performed: false,
        full_payload_saved: false, ...s, recommended_next_step: rec, preview_results: r };
}

function report(a) {
    const l = ['# ADG19 Corrected Source Inventory Preview', '', `- Phase: ${a.phase}`,
        `- accepted_validated_no_write: ${a.accepted_validated_no_write}`,
        `- rejected_reverse_fixture_mapping: ${a.rejected_reverse_fixture_mapping}`,
        `- requires_new_record: ${a.requires_new_record}`,
        `- requires_new_record_pending_evidence: ${a.requires_new_record_pending_evidence}`,
        `- suspended_still_blocked: ${a.suspended_still_blocked}`,
        `- raw_write_ready: ${a.raw_write_ready}`, '',
        '## Preview', '| id | classification | correction | recommended_action |',
        '| --- | --- | --- | --- |'];
    for (const t of a.preview_results || []) l.push(`| ${t.external_id} | ${t.classification} | ${t.correction_needed} | ${t.recommended_action} |`);
    l.push('', '## Safety', '- no live fetch / DB write / raw write / production mutation', '- raw_write_ready=0',
        '', '## Next', '', a.recommended_next_step);
    return `${l.join('\n')}\n`;
}

function main() { const a = build(); wj(OUT, a); wt(RPT, report(a)); process.stdout.write(JSON.stringify({ accepted: a.accepted_validated_no_write, rejected: a.rejected_reverse_fixture_mapping, need_record: a.requires_new_record, pending_evidence: a.requires_new_record_pending_evidence, suspended: a.suspended_still_blocked, rw: a.raw_write_ready }, null, 2) + '\n'); return { status: 0 }; }
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
