#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG49 review is superseded by revised strategy execution
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG49-REVIEW';
const A48 = 'docs/_manifests/fotmob_ligue1_adg48_ssr_correct_orientation_probe.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg49_correct_orientation_strategy_review.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG49_CORRECT_ORIENTATION_STRATEGY_REVIEW.md';
function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a48 = rj(A48);
    const revPairs = [
        { route_hash_pair: '2o4ahb#4830473', expected: 'PSG vs Angers', observed: 'Angers vs PSG, Apr 2026' },
        { route_hash_pair: '2sy6tc#4830472', expected: 'Nice vs Auxerre', observed: 'Auxerre vs Nice, May 2026' },
    ];
    const revisedOptions = [
        { name: 'league_schedule_ssr_discovery', desc: 'Probe FotMob league schedule/matchday page (SSR) to enumerate all fixtures and discover correct-orientation route_hash_pairs from full-season data', risk: 'Requires authorized probe; league page may be large but safe summary extraction works', requires_auth: true, not_executed: true },
        { name: 'matchup_route_page_discovery', desc: 'Use same route_code matchup page to see if it lists both legs (home/away) with different hash_ids', risk: 'May not expose both legs on single page', requires_auth: true, not_executed: true },
        { name: 'season_schedule_hydration_data', desc: 'Look for season-level __NEXT_DATA__ that contains all fixtures with full route/hash pairs', risk: 'Requires finding correct league season page URL', requires_auth: true, not_executed: true },
        { name: 'manual_canonical_seed', desc: 'Accept user-provided browser-observed canonical URL examples as manual evidence only, not automated source', risk: 'Manual process; may still yield reverse fixtures', requires_auth: true, not_executed: true },
        { name: 'alternate_public_source', desc: 'Evaluate other public football data sources if FotMob cannot expose correct pairs safely', risk: 'Different data model; integration cost', requires_auth: true, not_executed: true },
    ];
    return {
        schema_version: 'adg49_review_v1', lifecycle: 'phase-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: [A48, CS],
        safety: { live_fetch_performed: false, network_request_performed: false, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false },
        adg49_status: 'review_completed', review_performed: true,
        ssr_strategy_still_viable: true,
        adg48_result_summary: {
            planned_probe_target_count: 3, attempted_request_count: a48.attempted_request_count, successful_http_200_count: a48.successful_http_200_count,
            next_data_marker_found_count: a48.next_data_marker_found_count, safe_summary_extracted_count: a48.safe_summary_extracted_count,
            correct_orientation_discovered: 0, route_hash_pair_verified: 0, reverse_fixture_confirmed: 2, alternate_hash_found: 0,
        },
        confirmed_reverse_pairs: revPairs,
        remaining_problem: { known_route_hash_pairs: 5, confirmed_reverse: 2, still_unverified: 3, canonical_url_missing: 27, correct_orientation_route_hash_pair_missing: true, ssr_alternate_hash_not_exposed: true },
        revised_strategy_options: revisedOptions,
        recommended_approach: 'league_schedule_ssr_discovery',
        strategy_revision_required: true,
        raw_write_ready_count: 0,
        recommended_next_step: 'User must select and authorize revised discovery strategy; league_schedule_ssr_discovery recommended; do NOT raw write',
    };
}

function writeReport(data) {
    const lines = ['# ADG49 Correct-Orientation Strategy Review', '', `- Phase: ${PH}`, '- ssr_strategy_still_viable: true', '', '## ADG48 Probe Summary',
        `- attempted: ${data.adg48_result_summary.attempted_request_count}, http_200: ${data.adg48_result_summary.successful_http_200_count}`, `- correct_orientation_discovered: 0, route_hash_pair_verified: 0, reverse_fixture_confirmed: 2`, '',
        '## Confirmed Reverse Pairs', ...data.confirmed_reverse_pairs.map(p => `- ${p.route_hash_pair}: expected ${p.expected}, observed ${p.observed}`), '',
        '## Remaining Problem', `- 5 known pairs: 2 reverse, 3 unverified, 27 missing`, '- correct-orientation still missing', '- pageProps no alternate hash_ids', '',
        '## Revised Strategy Options', ...data.revised_strategy_options.map(o => `### ${o.name}\n- ${o.desc}\n- risk: ${o.risk}\n- requires_auth: ${o.requires_auth}\n- not_executed: ${o.not_executed}\n`),
        '## Next', 'User must select and authorize revised strategy; recommended: league_schedule_ssr_discovery; do NOT raw write'];
    wt(RPT, lines.join('\n') + '\n');
}

if (require.main === module) { const d = build(); wj(OUT, d); writeReport(d); console.log(JSON.stringify({ adg49_status: d.adg49_status, reverse_confirmed: d.adg48_result_summary.reverse_fixture_confirmed, remaining_unverified: d.remaining_problem.still_unverified, raw_write_ready_count: 0 }, null, 2)); }
module.exports = { build };
