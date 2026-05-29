#!/usr/bin/env node
/* eslint-disable complexity */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG20';

const ADG19_IN = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory_preview.adg19.json';
const ADG8 = 'docs/_manifests/fotmob_identity_mapping_source_inventory_audit_result.adg8.json';
const ADG12 = 'docs/_manifests/fotmob_observed_identity_evidence_acquisition_result.adg12.json';
const ADG16 = 'docs/_manifests/fotmob_observed_identity_evidence_acquisition_batch_b.adg16.json';
const ENRICHED = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const OUT = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory_generation.adg20.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_CORRECTED_SOURCE_INVENTORY_GENERATION_ADG20.md';

const { selectOrientedFixtureRecord, FIXTURE_IDENTITY_GUARD_PASSED, FIXTURE_IDENTITY_GUARD_BLOCKED } =
    require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function abs(p) { return path.isAbsolute(p) ? p : path.join(PP, p); }
function rj(p) { return JSON.parse(fs.readFileSync(abs(p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(abs(p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(abs(p), v, 'utf8'); }

function buildAllObserved() {
    const m = new Map();
    for (const src of [rj(ADG8), rj(ADG12), rj(ADG16)]) {
        for (const r of (src.audit_results || src.batch_results || [])) {
            if (r.schedule_external_id && r.observed_detail_id) {
                const eid = r.schedule_external_id;
                if (!m.has(eid) || r.observed_detail_id !== r.expected_detail_external_id_candidate)
                    {m.set(eid, { oh: r.observed_home_team, oa: r.observed_away_team, od: r.observed_detail_id, omd: r.observed_match_date });}
            }
        }
    }
    return m;
}

function run() {
    const preview = rj(ADG19_IN);
    const observed = buildAllObserved();
    const enrichedMap = new Map();
    for (const t of rj(ENRICHED).enriched_targets || []) { if (t.schedule_external_id) enrichedMap.set(t.schedule_external_id, t); }

    const results = [];
    for (const t of preview.preview_results || []) {
        if (t.is_pc) { results.push({ ...t, generation_status: 'preserved_positive_control_no_write', raw_write_ready: false }); continue; }
        if (t.is_suspended) { results.push({ ...t, generation_status: 'preserved_suspended_blocked', raw_write_ready: false }); continue; }

        const obs = observed.get(t.external_id);
        const enr = enrichedMap.get(t.external_id) || {};
        const base = { external_id: t.external_id, expH: t.expH, expA: t.expA, expD: t.expD, match_id: t.match_id,
            current_source_url: enr.source_page_url || null,
            current_candidate: enr.source_url_fragment_external_id || null,
            current_status: t.classification, prev_action: t.recommended_action };

        if (obs) {
            // Has observed evidence — check if oriented selection is possible
            const sel = selectOrientedFixtureRecord({ expectedHome: base.expH, expectedAway: base.expA, expectedDate: base.expD,
                candidates: [{ home_team: obs.oh, away_team: obs.oa, match_date: obs.omd, external_id: obs.od }] });

            if (sel.status === 'rejected_reverse_fixture_mapping') {
                // Confirmed: only reverse fixture is available. Cannot correct from source-controlled data.
                results.push({ ...base, generation_status: 'rejected_current_reverse_fixture_record',
                    observed_id: obs.od, observed_home: obs.oh, observed_away: obs.oa,
                    proposed_source_url: null, proposed_detail: null,
                    correction_action: 'requires_external_discovery_or_evidence_acquisition',
                    evidence_source: 'adg12_adg16_adg8', raw_write_ready: false,
                    reason: 'only reverse fixture observed; corrected oriented source inventory record must be acquired from external source (FotMob API/league overview) or public page-route discovery' });
            } else {
                results.push({ ...base, generation_status: 'proposed_corrected_source_inventory_record',
                    observed_id: obs.od, observed_home: obs.oh, observed_away: obs.oa,
                    proposed_detail: sel.selected?.external_id || obs.od,
                    correction_action: 'proposed_record_requires_no_write_validation',
                    evidence_source: 'adg12_adg16_adg8', raw_write_ready: false });
            }
        } else {
            // No observed evidence — require external discovery
            results.push({ ...base, generation_status: 'requires_external_discovery_or_evidence_acquisition',
                observed_id: null, observed_home: null, observed_away: null,
                proposed_source_url: null, proposed_detail: null,
                correction_action: 'acquire_oriented_source_inventory_record_from_external_source',
                evidence_source: 'none_source_controlled', raw_write_ready: false,
                reason: 'no observed identity evidence available from source-controlled artifacts; must acquire corrected source inventory record from FotMob L1 API league overview or public page-route discovery' });
        }
    }
    return results;
}

function cnt(l, p) { return l.filter(p).length; }

function build() {
    const g = new Date().toISOString(); const r = run();
    const s = { total: r.length,
        positive_control: cnt(r, t => t.is_pc),
        proposed_corrected: cnt(r, t => t.generation_status === 'proposed_corrected_source_inventory_record'),
        rejected_current_reverse: cnt(r, t => t.generation_status === 'rejected_current_reverse_fixture_record'),
        requires_external_discovery: cnt(r, t => t.generation_status === 'requires_external_discovery_or_evidence_acquisition'),
        suspended_blocked: cnt(r, t => t.generation_status === 'preserved_suspended_blocked'),
        raw_write_ready: 0, re_acceptance_candidate: 0 };

    const has_rejects = s.rejected_current_reverse > 0;
    const rec = has_rejects
        ? `${s.rejected_current_reverse} targets have reverse-only evidence — confirmed from source-controlled data. ${s.requires_external_discovery} additional targets lack any observed evidence. Recommend ADG21: bounded corrected-source discovery using FotMob L1 API league overview or oriented public page-route acquisition. Do NOT raw write.`
        : 'corrected generation preview complete; do not raw write';

    return { schema_version: 'adg20_v1', phase: PH, generated_at: g, adg20_status: 'completed_corrected_generation_preview',
        corrected_generation_performed: true, total_requires_new_record: cnt(r, t => !t.is_pc && !t.is_suspended),
        no_live_fetch: true, no_network: true, no_db_write: true, no_raw_write: true,
        source_inventory_mutation_performed: false, candidate_mutation_performed: false,
        full_payload_saved: false, ...s, recommended_next_step: rec, generation_results: r };
}

function report(a) {
    const l = ['# ADG20 Corrected Source Inventory Generation', '', `- Phase: ${a.phase}`,
        `- proposed_corrected: ${a.proposed_corrected}`, `- rejected_current_reverse: ${a.rejected_current_reverse}`,
        `- requires_external_discovery: ${a.requires_external_discovery}`, `- suspended_blocked: ${a.suspended_blocked}`,
        `- raw_write_ready: ${a.raw_write_ready}`, '',
        '## Key Finding',
        'From source-controlled artifacts alone, corrected source inventory records cannot be generated for reverse-mapped Ligue 1 targets.',
        'The current source inventory returns the WRONG leg for all double round-robin fixtures.',
        'Corrected records must be acquired from external FotMob L1 API league overview or public page-route discovery.',
        '',
        '## Results', '| id | generation_status | correction_action |', '| --- | --- | --- |'];
    for (const t of a.generation_results || []) l.push(`| ${t.external_id} | ${t.generation_status} | ${t.correction_action || 'n/a'} |`);
    l.push('', '## Safety', '- no live fetch / DB write / raw write / production mutation', '', '## Next', '', a.recommended_next_step);
    return `${l.join('\n')}\n`;
}

function main() { const a = build(); wj(OUT, a); wt(RPT, report(a)); process.stdout.write(JSON.stringify({ proposed: a.proposed_corrected, rejected: a.rejected_current_reverse, need_external: a.requires_external_discovery, suspended: a.suspended_blocked, rw: a.raw_write_ready }, null, 2) + '\n'); return { status: 0 }; }
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
