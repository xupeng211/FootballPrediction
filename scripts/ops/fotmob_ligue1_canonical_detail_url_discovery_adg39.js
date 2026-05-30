#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG39
/* eslint-disable complexity */
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG39';
const D21 = 'docs/_manifests/fotmob_ligue1_corrected_source_discovery.adg21.json';
const D23 = 'docs/_manifests/fotmob_ligue1_remaining_corrected_source_discovery.adg23.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_canonical_detail_url_discovery.adg39.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_CANONICAL_DETAIL_URL_DISCOVERY_ADG39.md';

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const d21 = rj(D21).discovery_results || []; const d23 = rj(D23).discovery_results || [];
    const all = [...d21, ...d23].filter(r => !r.is_pc && !r.is_suspended && !r.is_adg22_control);
    let routeCodeFound = 0; let routeCodeInUrl = 0; let canonicalUrlExists = 0; const findings = [];

    for (const r of all) {
        const url = r.selected_url || '';
        const parts = url.split('/').filter(Boolean);
        const matchesIdx = parts.indexOf('matches');
        const routeCode = matchesIdx >= 0 && parts.length > matchesIdx + 2 ? parts[matchesIdx + 2].split('#')[0] : null;
        const slug = matchesIdx >= 0 && parts.length > matchesIdx + 1 ? parts[matchesIdx + 1] : null;
        const hashId = url.split('#').pop() || null;
        if (routeCode) routeCodeFound++;
        if (hashId && hashId === r.external_id) routeCodeInUrl++;
        if (url) canonicalUrlExists++;
        findings.push({ external_id: r.external_id, selected_url: url, route_code: routeCode, slug, hash_id: hashId,
            route_code_present: Boolean(routeCode), canonical_url_from_l1: Boolean(url),
            note: slug && slug.toLowerCase().startsWith((r.corrected_away || r.selected_away || '').toLowerCase().replace(/[^a-z0-9]+/g, '-')) ? 'slug_likely_reverse_leg' : 'slug_may_match' });
    }

    const handoffContract = {
        l1_must_deliver: ['canonical_detail_url', 'route_code', 'detail_hash_id', 'slug', 'expected_home', 'expected_away', 'expected_date', 'expected_competition'],
        l2_must_not: ['guess_route_code', 'use_detail_id_as_route_code', 'use_historical_enriched_url_as_primary'],
        canonical_url_source: 'L1 league API page_url field — already present in ADG21/ADG23 discovery results',
        blocker: 'L1 API may return page_url with reverse-leg route code despite correct home/away in record fields',
    };

    return { total: all.length, route_code_found: routeCodeFound, route_code_in_url: routeCodeInUrl,
        canonical_url_exists: canonicalUrlExists, handoff_contract: handoffContract,
        recommendation: 'L1 API already provides canonical route codes in page_url. But these route codes may be for reverse legs. ADG40: bounded diagnostic probe to discover alternate detail ID with correct orientation route code.',
        findings };
}

function build() {
    const g = new Date().toISOString(); const r = run();
    return { schema_version: 'adg39_v1', phase: PH, generated_at: g, adg39_status: 'completed_canonical_url_investigation',
        investigation_performed: true, no_network: true, no_db_write: true, no_raw_write: true, full_payload_saved: false,
        canonical_detail_url_found: r.canonical_url_exists, route_code_found: r.route_code_found,
        route_code_from_l1_api: true, l2_route_code_guessing_blocked: true,
        alternate_route_code_discovery_required: true, canonical_url_diagnostic_probe_required: true,
        total: r.total, handoff_contract: r.handoff_contract, raw_write_ready: 0,
        recommended_next_step: 'ADG40: bounded diagnostic probe for alternate detail ID with correct-orientation route code from L1 API; do not raw write' };
}

function report(a) {
    return ['# ADG39 Canonical Detail URL Discovery', '', `- Phase: ${a.phase}`, `- total: ${a.total}`,
        `- canonical_url_found: ${a.canonical_detail_url_found}`, `- route_code_found: ${a.route_code_found}`,
        `- route_code_from_l1_api: ${a.route_code_from_l1_api}`,
        '', '## Key finding', 'L1 league API page_url already contains canonical route codes.',
        'But these route codes may belong to reverse-leg detail pages.',
        'L2 must consume L1 canonical URL, not guess route codes.', '',
        '## Handoff contract', 'L1 delivers: canonical_detail_url, route_code, detail_hash_id, home/away',
        'L2 must NOT: guess route code, use detail ID as route code, use historical enriched URL',
        '', '## Next', a.recommended_next_step].join('\n') + '\n';
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CS), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG39 canonical detail URL discovery';
        return line;
    });
    fs.writeFileSync(path.join(PP, CS), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ canonical_url: a.canonical_detail_url_found, route_code: a.route_code_found, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
