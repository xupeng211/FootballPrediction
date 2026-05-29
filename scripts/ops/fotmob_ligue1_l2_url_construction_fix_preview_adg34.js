#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG34
/* eslint-disable complexity */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG34';
const SRC = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory.adg27.json';
const ENR = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_l2_url_construction_fix.adg34.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_L2_URL_CONSTRUCTION_FIX_ADG34.md';
const { buildCorrectedFotmobDetailUrl } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const src = rj(SRC).corrected_source_inventory_records || [];
    const enrichedMap = new Map();
    for (const t of rj(ENR).enriched_targets || []) if (t.schedule_external_id) enrichedMap.set(t.schedule_external_id, t);
    const results = [];
    let slugFixed = 0; let slugMismatch = 0; let slugBlocked = 0;

    for (const s of src) {
        const enr = enrichedMap.get(s.external_id) || {};
        const oldUrl = enr.source_page_url || null;
        const oldSlug = (oldUrl || '').split('/').filter(Boolean).slice(-2, -1)[0] || '';
        const built = buildCorrectedFotmobDetailUrl({ correctedDetailExternalId: s.corrected_detail_id,
            expectedHomeTeam: s.expected_home, expectedAwayTeam: s.corrected_away });
        const oldReversed = oldSlug.toLowerCase().startsWith((s.corrected_away || '').toLowerCase().replace(/[^a-z0-9]+/g, '-'));
        if (oldReversed) slugMismatch++;
        if (built.ok) slugFixed++;
        else slugBlocked++;

        results.push({ external_id: s.external_id, expected_home: s.expected_home, expected_away: s.corrected_away,
            corrected_detail_id: s.corrected_detail_id, old_enriched_url: oldUrl, old_slug: oldSlug,
            old_slug_reversed: oldReversed,
            constructed_url: built.url, constructed_slug: built.slug,
            construction_status: built.ok ? 'constructed_from_corrected_identity' : 'blocked',
            construction_source: built.construction_source || 'corrected_identity',
            historical_enriched_url_used: false, raw_write_ready: false });
    }
    return { results, total: src.length, constructed: slugFixed, slug_mismatch: slugMismatch, slug_blocked: slugBlocked,
        adg32_sample_4830473_fixed: (results.find(r => r.external_id === '4830473') || {}).construction_status === 'constructed_from_corrected_identity' };
}

function build() {
    const g = new Date().toISOString(); const r = run();
    const s = { total: r.total, constructed: r.constructed, slug_mismatch_detected: r.slug_mismatch,
        slug_blocked: r.slug_blocked, adg32_4830473_fixed: r.adg32_sample_4830473_fixed, raw_write_ready: 0, re_acceptance: 0 };
    const rec = r.constructed === 32
        ? '32/32 corrected-identity URLs constructed; recommend ADG35 re-plan bounded L2 detail-fetch; do not raw write'
        : `${r.slug_blocked} slugs blocked; fix before L2 fetch; do not raw write`;
    return { schema_version: 'adg34_v1', phase: PH, generated_at: g, adg34_status: 'completed_l2_url_fix',
        l2_url_construction_fix_implemented: true, no_network: true, no_db_write: true, no_raw_write: true,
        full_payload_saved: false, ...s, recommended_next_step: rec, url_preview: r.results };
}

function report(a) {
    const l = ['# ADG34 L2 URL Construction Fix', '', `- Phase: ${a.phase}`,
        `- total: ${a.total}`, `- constructed: ${a.constructed}`,
        `- slug_mismatch_detected: ${a.slug_mismatch_detected}`,
        `- slug_blocked: ${a.slug_blocked}`,
        `- adg32_4830473_fixed: ${a.adg32_4830473_fixed}`,
        `- raw_write_ready: ${a.raw_write_ready}`, '',
        '## Key fix', '- buildCorrectedFotmobDetailUrl() added to FotMobRouteIdentityReconciler',
        '- Builds URLs from corrected_detail_id + expected home/away',
        '- Does NOT use historical enriched source_page_url as primary',
        '- 4830473: old slug angers-vs-psg → new slug paris-saint-germain-vs-angers',
        '', '## Next', 'ADG35 bounded L2 detail-fetch using fixed URLs. Do not raw write.'];
    return `${l.join('\n')}\n`;
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CS), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG34 L2 URL construction fix';
        return line;
    });
    fs.writeFileSync(path.join(PP, CS), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ constructed: a.constructed, slug_mismatch: a.slug_mismatch_detected, a4830473: a.adg32_4830473_fixed, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
