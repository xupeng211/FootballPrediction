#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG40
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG40';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_canonical_url_identity_model.adg40.json';
const RPT = 'docs/_reports/FOTMOB_CANONICAL_URL_IDENTITY_MODEL_ADG40.md';

function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function run() {
    const observation = { url_a: 'https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735',
        page_a: 'AFC Bournemouth 1-1 Manchester City, venue: Vitality Stadium',
        url_b: 'https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813470',
        page_b: 'Manchester City 3-1 AFC Bournemouth, venue: Etihad Stadium',
        implication: 'same slug + same route code + different hash ID = different fixtures with different home/away' };

    const model = {
        slug: 'display/SEO only — not authoritative for home/away orientation',
        route_code: 'matchup route / team-pair entry point — NOT unique fixture identity',
        hash_id: 'fixture selector within the route — determines which concrete fixture is displayed',
        canonical_identity: 'atomic tuple = {route_code, hash_id} — must be preserved as unit',
    };

    const l2_prohibitions = [
        'rewrite slug based on expected home/away',
        'replace route_code with detail_id',
        'treat route_code alone as unique fixture identity',
        'treat hash_id alone as unique fixture identity',
        'use historical enriched URL as primary L2 URL source',
        'guess route_code when L1 has not provided one',
    ];

    const contract = {
        l1_must_deliver: ['canonical_detail_url', 'route_code', 'hash_id', 'route_hash_pair',
            'expected_home', 'expected_away', 'expected_date', 'expected_competition'],
        l2_must_consume: 'canonical_detail_url as atomic unit; do not decompose and rewrite components',
        l2_must_validate: 'observed home/away/date after fetch; do not assume orientation from URL',
    };

    // Check existing builder behavior against model
    const builderAssessment = {
        issue_1: 'detail ID as route code fallback — violates model (route_code ≠ detail_id)',
        issue_2: 'slug rewriting based on expected home/away — violates model (slug not authoritative)',
        issue_3: 'route_code guessing when historical URL unavailable — violates model',
        recommendation: 'deprecate buildCorrectedFotmobDetailUrl() for primary L2 use; use only when no L1 canonical URL exists AND mark as provisional',
    };

    return { observation, model, l2_prohibitions, contract, builder_assessment: builderAssessment,
        route_code_not_unique: true, hash_id_fixture_selector: true, slug_not_authoritative: true,
        route_hash_pair_required: true, existing_builder_requires_change: true,
        l2_url_rewriting_blocked: true, detail_id_as_route_code_blocked: true,
        alternate_hash_discovery_required: true, canonical_url_probe_required: true,
        adg32_38_explained: 'L1 API provided route_code + hash_id for reverse fixture; correct-orientation hash_id was not discovered', };
}

function build() {
    const g = new Date().toISOString(); const r = run();
    return { schema_version: 'adg40_v1', phase: PH, generated_at: g, adg40_status: 'completed_identity_model',
        investigation_performed: true, manual_observation_recorded: true, no_network: true, no_db_write: true,
        no_raw_write: true, full_payload_saved: false, ...r, raw_write_ready: 0,
        recommended_next_step: 'ADG41: implement canonical URL atomic handoff contract; block L2 URL rewriting; do not raw write' };
}

function report(a) {
    return ['# ADG40 Canonical URL Identity Model', '', `- Phase: ${a.phase}`,
        '', '## User-provided observation',
        `URL A: ${a.observation.url_a} → ${a.observation.page_a}`,
        `URL B: ${a.observation.url_b} → ${a.observation.page_b}`,
        `Same route_code 2feiv3, different hash IDs (4813735 vs 4813470), different fixtures.`,
        '', '## FotMob URL component model',
        `- slug: ${a.model.slug}`, `- route_code: ${a.model.route_code}`,
        `- hash_id: ${a.model.hash_id}`, `- canonical identity: ${a.model.canonical_identity}`,
        '', '## L2 URL rewriting blocked', ...a.l2_prohibitions.map(r => `- ${r}`),
        '', '## ADG32-38 retrospective',
        a.adg32_38_explained, '', '## Next', a.recommended_next_step].join('\n') + '\n';
}

function main() {
    const a = build(); wj(OUT, a); wt(RPT, report(a));
    const cs = fs.readFileSync(path.join(PP, CS), 'utf8').split('\n').map(line => {
        if (line.startsWith('- latest completed phase:')) return '- latest completed phase: ADG40 canonical URL identity model';
        return line;
    });
    fs.writeFileSync(path.join(PP, CS), cs.join('\n'), 'utf8');
    process.stdout.write(JSON.stringify({ route_code_not_unique: a.route_code_not_unique, hash_selector: a.hash_id_fixture_selector, rewrite_blocked: a.l2_url_rewriting_blocked, rw: a.raw_write_ready }, null, 2) + '\n');
    return { status: 0 };
}
module.exports = { PH, run, build, report, main };
if (require.main === module) { try { process.exitCode = main().status; } catch (e) { process.stderr.write(e.stack + '\n'); process.exitCode = 1; } }
