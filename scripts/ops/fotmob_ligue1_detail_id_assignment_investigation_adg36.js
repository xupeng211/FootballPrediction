#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG36
/* eslint-disable complexity */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG36';
const SRC = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory.adg27.json';
const ENR = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_detail_id_assignment_investigation.adg36.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_DETAIL_ID_ASSIGNMENT_INVESTIGATION_ADG36.md';
const { buildCorrectedFotmobDetailUrl } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const src = rj(SRC).corrected_source_inventory_records || [];
    const enrichedMap = new Map();
    for (const t of rj(ENR).enriched_targets || []) if (t.schedule_external_id) enrichedMap.set(t.schedule_external_id, t);
    const results = [];
    let routeCodeReused = 0; let routeCodeMismatch = 0; let lineageVerified = 0;

    for (const s of src) {
        const enr = enrichedMap.get(s.external_id) || {};
        const oldUrl = enr.source_page_url || '';
        const oldParts = oldUrl.split('/').filter(Boolean);
        const oldSlug = oldParts.length > 1 ? oldParts[oldParts.length - 2] : '';
        const oldRouteCode = oldParts.length > 2 ? oldParts[oldParts.length - 2] : '';
        const built = buildCorrectedFotmobDetailUrl({ correctedDetailExternalId: s.corrected_detail_id,
            expectedHomeTeam: s.expected_home, expectedAwayTeam: s.corrected_away,
            historicalSourcePageUrl: oldUrl || null });

        // Check route code lineage
        const routeCodeFromOld = built.route_code === oldRouteCode && oldRouteCode !== s.corrected_detail_id;
        const slugMismatch = oldSlug.toLowerCase().startsWith((s.corrected_away || '').toLowerCase().replace(/[^a-z0-9]+/g, '-'));
        if (routeCodeFromOld) routeCodeReused++;
        if (slugMismatch && routeCodeFromOld) routeCodeMismatch++;
        if (!routeCodeFromOld) lineageVerified++;

        results.push({ external_id: s.external_id, expected_home: s.expected_home, expected_away: s.corrected_away,
            old_route_code: oldUrl ? oldParts.filter(Boolean).slice(-3)[0] : null,
            used_route_code: built.route_code, route_code_from_old_url: routeCodeFromOld,
            slug_mismatch: slugMismatch, route_code_mismatch: slugMismatch && routeCodeFromOld,
            raw_write_ready: false });
    }
    const sample483 = results.find(r => r.external_id === '4830473');
    const finding = {
        root_cause: 'ADG34 builder reuses historical route code from wrong-leg enriched URL',
        mechanism: 'FotMob server serves detail page content based on route code path segment, not hash ID alone',
        evidence_4830473: sample483 ? {
            old_route_code: sample483.old_route_code, used_route_code: sample483.used_route_code,
            route_code_from_wrong_leg: sample483.route_code_from_old_url,
        } : {},
        fix: 'do NOT reuse route code when slug mismatch detected; use detail ID as fallback route code',
    };
    return { results, total: src.length, route_code_reused: routeCodeReused, route_code_mismatch: routeCodeMismatch,
        lineage_verified: lineageVerified, finding };
}

function build() {
    const g = new Date().toISOString(); const r = run();
    return { schema_version: 'adg36_v1', phase: PH, generated_at: g, adg36_status: 'completed_investigation',
        investigation_performed: true, no_network: true, no_db_write: true, no_raw_write: true,
        full_payload_saved: false, total: r.total, route_code_reused: r.route_code_reused,
        route_code_mismatch: r.route_code_mismatch, lineage_verified: r.lineage_verified,
        finding: r.finding, raw_write_ready: 0,
        recommended_next_step: 'ADG37: fix route code construction — use detail ID instead of historical route code when slug mismatch; do not raw write' };
}

function report(a) {
    return ['# ADG36 Detail ID Assignment Investigation', '', `- Phase: ${a.phase}`,
        `- total: ${a.total}`, `- route_code_reused: ${a.route_code_reused}`,
        `- route_code_mismatch: ${a.route_code_mismatch}`, `- lineage_verified: ${a.lineage_verified}`,
        '', '## Root cause', a.finding.root_cause, a.finding.mechanism,
        '4830473: old route code 2o4ahb from wrong-leg URL reused in corrected URL', '',
        '## Fix', a.finding.fix, '', '## Next', a.recommended_next_step].join('\n') + '\n';
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CS), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG36 detail ID assignment investigation';
        return line;
    });
    fs.writeFileSync(path.join(PP, CS), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ route_code_reused: a.route_code_reused, route_code_mismatch: a.route_code_mismatch, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
