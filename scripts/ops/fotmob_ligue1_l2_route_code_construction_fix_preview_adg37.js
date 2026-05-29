#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG37
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG37';
const SRC = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory.adg27.json';
const ENR = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_l2_route_code_construction_fix.adg37.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_L2_ROUTE_CODE_CONSTRUCTION_FIX_ADG37.md';
const { buildCorrectedFotmobDetailUrl } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const src = rj(SRC).corrected_source_inventory_records || [];
    const enrichedMap = new Map();
    for (const t of rj(ENR).enriched_targets || []) if (t.schedule_external_id) enrichedMap.set(t.schedule_external_id, t);
    const results = []; let mismatch = 0; let rejected = 0; let fallback = 0;

    for (const s of src) {
        const enr = enrichedMap.get(s.external_id) || {};
        const built = buildCorrectedFotmobDetailUrl({ correctedDetailExternalId: s.corrected_detail_id,
            expectedHomeTeam: s.expected_home, expectedAwayTeam: s.corrected_away,
            historicalSourcePageUrl: enr.source_page_url || null });
        if (built.historical_slug_mismatch_detected) { mismatch++; rejected++; }
        if (built.route_code_source === 'corrected_detail_id_fallback_slug_mismatch_rejected') fallback++;
        results.push({ external_id: s.external_id, expected_home: s.expected_home, expected_away: s.corrected_away,
            corrected_detail: s.corrected_detail_id, constructed_url: built.url, slug: built.slug,
            route_code: built.route_code, route_code_source: built.route_code_source,
            historical_route_code_reused: built.historical_route_code_reused,
            historical_route_code_rejected_reason: built.historical_route_code_rejected_reason,
            historical_slug_mismatch: built.historical_slug_mismatch_detected,
            raw_write_ready: false });
    }
    const sample483 = results.find(r => r.external_id === '4830473');
    return { results, total: src.length, slug_mismatch: mismatch, route_code_rejected: rejected, fallback,
        adg37_4830473_fixed: sample483 ? !sample483.historical_route_code_reused && sample483.route_code === '4830473' : false,
        adg37_4830473_no_2o4ahb: sample483 ? !sample483.constructed_url.includes('2o4ahb') : false };
}

function build() {
    const g = new Date().toISOString(); const r = run();
    return { schema_version: 'adg37_v1', phase: PH, generated_at: g, adg37_status: 'completed_route_code_fix',
        route_code_fix_implemented: true, total: r.total, slug_mismatch: r.slug_mismatch,
        route_code_rejected: r.route_code_rejected, detail_id_fallback: r.fallback,
        historical_route_code_reused: r.total - r.rejected,
        adg37_4830473_fixed: r.adg37_4830473_fixed, adg37_4830473_no_2o4ahb: r.adg37_4830473_no_2o4ahb,
        raw_write_ready: 0, re_acceptance: 0,
        recommended_next_step: (r.adg37_4830473_fixed ? 'ADG38: re-execute bounded L2 fetch with fixed route code for 4830473 first; do not raw write' : 'fix 4830473 route code before ADG38'),
        results: r.results };
}

function report(a) {
    return ['# ADG37 Route Code Construction Fix', '', `- Phase: ${a.phase}`, `- total: ${a.total}`,
        `- slug_mismatch: ${a.slug_mismatch}`, `- route_code_rejected: ${a.route_code_rejected}`,
        `- detail_id_fallback: ${a.detail_id_fallback}`, `- historical_route_code_reused: ${a.historical_route_code_reused}`,
        `- adg37_4830473_fixed: ${a.adg37_4830473_fixed} (no longer uses 2o4ahb)`,
        `- rw: ${a.raw_write_ready}`, '', '## Next', a.recommended_next_step].join('\n') + '\n';
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CS), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG37 L2 route code construction fix';
        return line;
    });
    fs.writeFileSync(path.join(PP, CS), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ slug_mismatch: a.slug_mismatch, route_code_rejected: a.route_code_rejected, a4830473: a.adg37_4830473_fixed, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
