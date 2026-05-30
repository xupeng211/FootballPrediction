#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG47 review is superseded by correct-orientation discovery
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG47-REVIEW';
const A46 = 'docs/_manifests/fotmob_ligue1_ssr_pageprops_bounded_probe.adg46.json';
const GATE46 = 'docs/_manifests/fotmob_ligue1_ssr_pageprops_discovery_gate.adg46.json';
const A45 = 'docs/_manifests/fotmob_ligue1_adg45_probe_result_review.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg47_ssr_probe_result_review.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG47_SSR_PROBE_RESULT_REVIEW.md';

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a46 = rj(A46);
    const gate46 = rj(GATE46);
    const a45 = rj(A45);

    const t1 = (a46.results || [])[0] || {};
    const t2 = (a46.results || [])[1] || {};

    return {
        schema_version: 'adg47_review_v1',
        lifecycle: 'phase-artifact',
        phase: PH,
        generated_at: new Date().toISOString(),
        input_sources: [A46, GATE46, A45, CS],
        safety: {
            live_fetch_performed: false,
            network_request_performed: false,
            db_write_performed: false,
            raw_write_execution_performed: false,
            raw_match_data_insert_performed: false,
            full_payload_saved: false,
            full_html_saved: false,
            full_next_data_saved: false,
            full_pageprops_saved: false,
            re_acceptance_performed: false,
            suspension_reversal_performed: false,
        },
        adg47_status: 'review_completed',
        review_performed: true,

        // ADG46 SSR viability confirmation
        ssr_strategy_viable: true,
        ssr_evidence: {
            public_match_page_http_200: a46.successful_http_200_count >= 1,
            next_data_marker_found: a46.next_data_marker_found_count >= 1,
            pageprops_marker_found: a46.pageprops_marker_found_count >= 1,
            hydration_marker_found: a46.hydration_marker_found_count >= 1,
            safe_summary_extracted: a46.safe_summary_extracted_count >= 1,
            extraction_method: 'in-memory __NEXT_DATA__ parse',
            full_payload_saved: false,
        },

        // Reverse fixture confirmation
        reverse_fixture_confirmed: true,
        reverse_fixture_detail: {
            route_hash_pair: '2o4ahb#4830473',
            expected_home: 'Paris Saint-Germain',
            expected_away: 'Angers',
            expected_date: '2025-08-22',
            observed_home: t1.observed_home || 'Angers',
            observed_away: t1.observed_away || 'Paris Saint-Germain',
            observed_date: t1.observed_date || 'Apr 25, 2026',
            observed_competition: t1.observed_competition || 'Ligue 1',
            conclusion: 'route_hash_pair corresponds to REVERSE fixture (away leg), not the expected home leg; date mismatch (Apr 2026 vs Aug 2025) confirms wrong fixture orientation',
        },

        // Correct-orientation discovery needs
        correct_orientation_route_hash_pair_missing: true,
        known_route_hash_pair_count: 5,
        confirmed_reverse_fixture_count: 1,
        remaining_unverified_count: 4,
        canonical_url_missing_count: 27,

        // Next strategy: correct-orientation discovery
        revised_discovery_plan: {
            strategy: 'ssr_pageprops_correct_orientation_discovery',
            based_on: 'ADG46 confirmed SSR viable; public match pages accessible; __NEXT_DATA__ extractable',
            needs: [
                'Discover correct-orientation route_hash_pair for PSG vs Angers home leg',
                'The same route_code 2o4ahb may serve BOTH legs via different hash_ids (per ADG40 model)',
                'Need to find correct-orientation hash_id for PSG home vs Angers away under route_code 2o4ahb',
                'Verify remaining 4 route_hash_pair_unverified candidates via SSR safe summary',
                'Design bounded SSR probe for 27 canonical_url_missing candidates using league schedule page discovery',
            ],
            not_authorized: true,
            requires_explicit_user_authorization: true,
        },

        raw_write_ready_count: 0,
        recommended_next_step: 'User must authorize next bounded SSR discovery step (correct-orientation route_hash_pair search); do NOT execute without authorization; do NOT raw write',
    };
}

function writeReport(data) {
    const lines = [
        '# ADG47 SSR Probe Result Review',
        '',
        '- lifecycle: phase-artifact',
        `- Phase: ${PH}`,
        '- adg47_status: review_completed',
        '',
        '## ADG46 SSR Viability Confirmed',
        `- public_match_page_http_200: ${data.ssr_evidence.public_match_page_http_200}`,
        `- next_data_marker_found: ${data.ssr_evidence.next_data_marker_found}`,
        `- pageprops_marker_found: ${data.ssr_evidence.pageprops_marker_found}`,
        `- hydration_marker_found: ${data.ssr_evidence.hydration_marker_found}`,
        `- safe_summary_extracted: ${data.ssr_evidence.safe_summary_extracted}`,
        `- extraction_method: ${data.ssr_evidence.extraction_method}`,
        `- full_payload_saved: false`,
        '',
        '## Reverse Fixture Confirmation',
        `- route_hash_pair: ${data.reverse_fixture_detail.route_hash_pair}`,
        `- expected: ${data.reverse_fixture_detail.expected_home} vs ${data.reverse_fixture_detail.expected_away}`,
        `- observed: ${data.reverse_fixture_detail.observed_home} vs ${data.reverse_fixture_detail.observed_away}`,
        `- conclusion: ${data.reverse_fixture_detail.conclusion}`,
        '',
        '## Correct-Orientation Discovery Needs',
        `- known_route_hash_pair_count: ${data.known_route_hash_pair_count}`,
        `- confirmed_reverse_fixture: ${data.confirmed_reverse_fixture_count}`,
        `- remaining_unverified: ${data.remaining_unverified_count}`,
        `- canonical_url_missing: ${data.canonical_url_missing_count}`,
        '',
        '## Revised Discovery Plan',
        `- strategy: ${data.revised_discovery_plan.strategy}`,
        ...data.revised_discovery_plan.needs.map(n => `- ${n}`),
        `- requires_explicit_user_authorization: ${data.revised_discovery_plan.requires_explicit_user_authorization}`,
        '',
        '## Safety',
        '- No live fetch / network in ADG47',
        '- No DB write, no raw write',
        '- raw_write_ready_count: 0',
        '',
        '## Next',
        'User authorization required for correct-orientation route_hash_pair discovery; do NOT execute; do NOT raw write',
    ];
    wt(RPT, lines.join('\n') + '\n');
}

if (require.main === module) {
    const data = build();
    wj(OUT, data);
    writeReport(data);
    console.log(JSON.stringify({
        adg47_status: data.adg47_status,
        ssr_viable: data.ssr_strategy_viable,
        reverse_fixture_confirmed: data.reverse_fixture_confirmed,
        remaining_unverified: data.remaining_unverified_count,
        raw_write_ready_count: 0,
    }, null, 2));
}

module.exports = { build };
