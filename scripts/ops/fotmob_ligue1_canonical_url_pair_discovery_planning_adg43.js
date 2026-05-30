#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG43 once L1 canonical URL pair discovery planning is superseded by ADG44
/* eslint-disable complexity */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG43';
const A42 = 'docs/_manifests/fotmob_ligue1_corrected_artifacts_canonical_contract.adg42.json';
const A27 = 'docs/_manifests/fotmob_ligue1_corrected_candidates.adg27.json';
const A22 = 'docs/_manifests/fotmob_ligue1_corrected_source_validation.adg22.json';
const A24 = 'docs/_manifests/fotmob_ligue1_remaining_corrected_source_validation.adg24.json';
const A39 = 'docs/_manifests/fotmob_ligue1_canonical_detail_url_discovery.adg39.json';
const A33 = 'docs/_manifests/fotmob_ligue1_l1_l2_orientation_reconciliation.adg33.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_canonical_url_pair_discovery_planning.adg43.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_CANONICAL_URL_PAIR_DISCOVERY_PLANNING_ADG43.md';

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a42 = rj(A42);
    const a27 = rj(A27);
    const a22 = rj(A22);
    const a24 = rj(A24);
    const a39 = rj(A39);
    const a33 = rj(A33);

    const candidates = a42.candidates || [];
    const valid = candidates.filter(c => c.atomic_handoff_status === 'canonical_url_atomic_identity_valid');
    const missing = candidates.filter(c => c.atomic_handoff_status === 'canonical_url_missing');

    // Build discovery targets
    const missingTargets = missing.map(c => ({
        target_match_id: c.target_match_id,
        corrected_detail_external_id: c.corrected_detail_external_id,
        expected_home: c.expected_home,
        expected_away: c.expected_away,
        expected_match_date: c.expected_match_date,
        expected_competition: c.expected_competition,
        classification: 'canonical_url_missing_needs_l1_discovery',
        l1_league_api_url_available: false,
        l2_guessing_blocked: true,
        raw_write_blocked: true,
        canonical_pair_probe_required: true,
    }));

    const unverifiedTargets = valid.map(c => ({
        target_match_id: c.target_match_id,
        route_code: c.route_code,
        hash_id: c.hash_id,
        route_hash_pair: c.route_hash_pair,
        canonical_detail_url: c.canonical_detail_url,
        canonical_url_source: c.canonical_url_source,
        expected_home: c.expected_home,
        expected_away: c.expected_away,
        expected_match_date: c.expected_match_date,
        expected_competition: c.expected_competition,
        classification: 'route_hash_pair_unverified_needs_detail_verification',
        slug_orientation_reversed: true,
        reverse_fixture_risk: true,
        detail_page_verification_required: true,
        raw_write_blocked: true,
    }));

    // Alternate hash discovery assessment
    const alternateHashRequired = unverifiedTargets.length > 0;

    return {
        schema_version: 'adg43_v1',
        lifecycle: 'phase-artifact',
        phase: PH,
        generated_at: new Date().toISOString(),
        input_sources: [A42, A27, A22, A24, A39, A33, CS],
        safety: {
            live_fetch_performed: false,
            network_request_performed: false,
            db_write_performed: false,
            raw_write_execution_performed: false,
            raw_match_data_insert_performed: false,
            full_payload_saved: false,
            re_acceptance_performed: false,
            suspension_reversal_performed: false,
            browser_bypass_performed: false,
        },
        adg43_status: 'planning_completed',
        planning_performed: true,
        total_corrected_candidates: 32,
        missing_canonical_url_targets: missingTargets.length,
        unverified_route_hash_pair_targets: unverifiedTargets.length,
        alternate_hash_id_discovery_required_count: alternateHashRequired ? 5 : 0,
        canonical_pair_probe_required_count: missingTargets.length,
        l2_guessing_blocked_count: 32,
        reverse_fixture_risk_count: unverifiedTargets.length,
        raw_write_ready_count: 0,

        // Discovery strategy
        discovery_strategy: {
            name: 'l1_canonical_url_pair_discovery',
            description: 'Use L1 FotMob league API source-controlled data to discover canonical_detail_url for 27 missing candidates and verify 5 unverified route_hash_pairs',
            blocked_approaches: [
                'l2_route_code_guessing',
                'detail_id_as_route_code',
                'historical_enriched_url_as_primary',
                'slug_rewriting',
                'fallback_url_construction',
            ],
        },

        // Target groups
        target_groups: {
            missing_canonical_url_targets: missingTargets,
            unverified_route_hash_pair_targets: unverifiedTargets,
        },

        // ADG44 bounded diagnostic probe design (not executed)
        adg44_probe_design: {
            description: 'Bounded diagnostic probe for candidates still missing canonical URLs after L1 source-controlled search',
            max_target_count: 5,
            max_request_count: 5,
            allowed_endpoint: 'GET https://www.fotmob.com/api/leagues?id=53&season=2025/2026',
            safe_summary_fields: ['pageUrl', 'home.name', 'away.name', 'status.utcTime', 'id'],
            no_full_payload: true,
            stop_on_403_or_block: true,
            stop_on_captcha: true,
            stop_on_first_identity_mismatch: true,
            no_browser: true,
            no_proxy: true,
            no_bypass: true,
            explicit_user_authorization_required: true,
            not_executed_in_adg43: true,
        },

        recommended_next_step: 'ADG44 bounded diagnostic probe execution (requires explicit user authorization); do not raw write; do not skip to raw write',
    };
}

function writeReport(data) {
    const lines = [
        '# ADG43 L1 Canonical URL Pair Discovery Planning',
        '',
        `- lifecycle: phase-artifact`,
        `- Phase: ${PH}`,
        `- total_corrected_candidates: 32`,
        `- missing_canonical_url_targets: ${data.missing_canonical_url_targets}`,
        `- unverified_route_hash_pair_targets: ${data.unverified_route_hash_pair_targets}`,
        `- alternate_hash_id_discovery_required_count: ${data.alternate_hash_id_discovery_required_count}`,
        `- canonical_pair_probe_required_count: ${data.canonical_pair_probe_required_count}`,
        `- l2_guessing_blocked_count: 32`,
        `- raw_write_ready_count: 0`,
        '',
        '## Discovery Strategy',
        '',
        '### For 27 missing canonical URLs',
        '- Primary source: L1 FotMob league API source-controlled data (league_api_overview)',
        '- Each match in L1 API response has pageUrl with route_code + hash_id',
        '- Hash fragment in pageUrl === corrected_detail_external_id for correct match',
        '- Search L1 response for matching hash_id per candidate',
        '- Extract complete canonical_detail_url, route_code, hash_id, route_hash_pair',
        '- Candidates NOT found in L1 source-controlled data → ADG44 probe required',
        '',
        '### For 5 unverified route_hash_pairs',
        '- All 5 have route_hash_pair from L1 but with reversed slug orientation',
        '- route_code + hash_id may correspond to reverse-leg fixture',
        '- Detail-page verification required: compare observed home/away/date/competition against expected',
        '- Safe summary fields only (no full payload, no pageProps save)',
        '- Alternate hash_id may exist for correct-orientation fixture under same route_code',
        '',
        '### Alternate hash discovery',
        '- Same route_code can serve different fixtures via different hash_ids',
        '- Man City vs Bournemouth example: 2feiv3#4813735 (reverse) vs 2feiv3#4813470 (correct)',
        '- L1 API typically returns one hash_id per fixture (the primary/featured one)',
        '- Correct-orientation hash_id may differ from L1-returned hash_id',
        '- Discovery method: L1 API may contain both home/away legs under same route_code',
        '- Selection: prefer hash_id matching corrected_detail_external_id with correct home/away orientation',
        '',
        '### ADG44 bounded diagnostic probe (NOT executed in ADG43)',
        '- Max 5 targets for diagnostic only',
        '- Single GET to L1 league API per target set',
        '- Safe summary fields only; no full payload',
        '- Stop on 403 / block / captcha / first identity mismatch',
        '- No browser, proxy, or bypass',
        '- Requires explicit user authorization',
        '',
        '## Boundary',
        '- No live fetch, no network, no DB write, no raw write',
        '- No raw_match_data insert, no re-acceptance, no suspension reversal',
        '- No full payload saved, no browser/proxy/captcha bypass',
        '- L2 route-code guessing permanently blocked',
        '- Detail ID as route code permanently blocked',
        '- raw_write_ready_count=0',
        '',
        '## Next',
        'ADG44 bounded diagnostic probe for remaining missing canonical URLs; requires explicit user authorization; do not raw write',
    ];
    wt(RPT, lines.join('\n') + '\n');
}

if (require.main === module) {
    const data = build();
    wj(OUT, data);
    writeReport(data);
    console.log(JSON.stringify({ adg43_status: data.adg43_status, planning_performed: true, raw_write_ready_count: 0 }, null, 2));
}

module.exports = { build };
