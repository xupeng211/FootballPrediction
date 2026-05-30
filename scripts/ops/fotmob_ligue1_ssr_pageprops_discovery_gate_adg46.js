#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG46 gate is superseded by authorized SSR probe execution
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG46-SSR-GATE';
const A45 = 'docs/_manifests/fotmob_ligue1_adg45_probe_result_review.json';
const A44 = 'docs/_manifests/fotmob_ligue1_adg44_bounded_diagnostic_probe.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_ssr_pageprops_discovery_gate.adg46.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_SSR_PAGEPROPS_DISCOVERY_GATE_ADG46.md';

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a45 = rj(A45);
    const a44 = rj(A44);

    // Select exactly 2 future SSR/pageProps probe targets
    const futureTargets = [
        {
            target_match_id: '53_20252026_4830473',
            expected_home: 'Paris Saint-Germain',
            expected_away: 'Angers',
            expected_date: '2025-08-22T18:45:00.000Z',
            expected_competition: 'Ligue 1',
            current_status: 'route_hash_pair_unverified_needs_detail_verification',
            route_hash_pair_known: '2o4ahb#4830473',
            why_selected: 'Known reversed slug in L1 API URL; high diagnostic value for SSR pageProps orientation verification',
            expected_page_url: 'https://www.fotmob.com/matches/angers-vs-paris-saint-germain/2o4ahb#4830473',
            expected_probe_method: 'Single GET to FotMob match page URL; in-memory parse of __NEXT_DATA__ script tag; extract safe summary only',
            max_request_count: 1,
            safe_summary_only: true,
            full_payload_saved: false,
            raw_write_ready: false,
        },
        {
            target_match_id: '53_20252026_4830499',
            expected_home: 'Marseille',
            expected_away: 'Paris Saint-Germain',
            expected_date: null,
            expected_competition: 'Ligue 1',
            current_status: 'canonical_url_missing_needs_l1_discovery',
            route_hash_pair_known: null,
            why_selected: 'High-value missing canonical URL (Le Classique); SSR probe may discover route_code + hash_id from page',
            expected_page_url: null,
            expected_probe_method: 'SSR page discovery via league page listing or match search; extract match pageUrl from pageProps',
            max_request_count: 1,
            safe_summary_only: true,
            full_payload_saved: false,
            raw_write_ready: false,
        },
    ];

    // Allowed safe summary fields
    const allowedSafeSummaryFields = [
        'target_match_id',
        'request_url',
        'http_status',
        'redirect_summary',
        'content_type',
        'next_data_marker_present',
        'pageprops_marker_present',
        'hydration_marker_present',
        'canonical_detail_url_found',
        'route_code_found',
        'hash_id_found',
        'route_hash_pair_found',
        'observed_home',
        'observed_away',
        'observed_date',
        'observed_competition',
        'identity_status',
        'orientation_status',
        'extraction_status',
        'blocker_reason',
    ];

    const forbiddenFieldsInSave = [
        'full_html',
        'full_next_data',
        'full_pageprops',
        'full_raw_data',
        'full_source_body',
        'cookies',
        'sensitive_headers',
        'session_tokens',
        'api_keys',
    ];

    return {
        schema_version: 'adg46_ssr_gate_v1',
        lifecycle: 'phase-artifact',
        phase: PH,
        generated_at: new Date().toISOString(),
        input_sources: [A45, A44, CS],
        safety: {
            live_fetch_performed: false,
            network_request_performed: false,
            db_write_performed: false,
            raw_write_execution_performed: false,
            raw_match_data_insert_performed: false,
            full_payload_saved: false,
            full_html_saved: false,
            full_pageprops_saved: false,
            re_acceptance_performed: false,
            suspension_reversal_performed: false,
            browser_bypass_performed: false,
            proxy_used: false,
            captcha_bypass: false,
        },
        adg46_status: 'authorization_gate_prepared',
        authorization_gate_prepared: true,
        ssr_probe_not_executed: true,

        // Chosen strategy
        chosen_strategy: 'fotmob_ssr_pageprops',
        chosen_reason: [
            'Public FotMob match pages use Next.js SSR with __NEXT_DATA__ inline script',
            'No authentication required for public match pages',
            'No API key needed',
            'No browser automation needed — simple HTTPS GET with SSR-friendly User-Agent',
            'pageProps contains match identity fields extractable as safe summary',
            'Aligned with ADG40 model: route_code + hash_id are embedded in page data',
        ],

        requires_explicit_user_authorization: true,
        authorization_scope: 'ADG46 SSR/pageProps bounded diagnostic probe execution only; does NOT authorize raw write, DB write, re-acceptance, suspension reversal, or full payload save',

        future_probe_target_count: 2,
        max_targets: 2,
        max_requests_per_target: 1,

        probe_boundary: {
            public_match_page_only: true,
            no_api_endpoint_guessing: true,
            no_authenticated_api: true,
            no_browser_automation: true,
            no_proxy: true,
            no_bypass: true,
            no_retry_on_block: true,
            stop_on_403_or_block: true,
            stop_on_captcha: true,
            stop_on_first_identity_mismatch: true,
            in_memory_parse_only: true,
            safe_summary_only: true,
            no_full_html_saved: true,
            no_full_pageprops_saved: true,
            no_full_next_data_saved: true,
            no_full_raw_json_saved: true,
            no_db_write: true,
            no_raw_write: true,
            no_raw_match_data_insert: true,
            raw_write_ready_count: 0,
        },

        allowed_safe_summary_fields: allowedSafeSummaryFields,
        forbidden_fields_in_save: forbiddenFieldsInSave,

        future_ssr_probe_targets: futureTargets,

        recommended_next_step: 'User must explicitly authorize ADG46 SSR/pageProps bounded diagnostic probe execution; do NOT execute without authorization; do NOT raw write',
    };
}

function writeReport(data) {
    const lines = [
        '# ADG46 SSR pageProps Discovery Authorization Gate',
        '',
        `- lifecycle: phase-artifact`,
        `- Phase: ${PH}`,
        `- chosen_strategy: ${data.chosen_strategy}`,
        `- future_probe_target_count: ${data.future_probe_target_count}`,
        `- max_targets: ${data.max_targets}`,
        `- max_requests_per_target: ${data.max_requests_per_target}`,
        `- requires_explicit_user_authorization: true`,
        `- ssr_probe_not_executed: true`,
        `- raw_write_ready_count: 0`,
        '',
        '## Chosen Strategy: fotmob_ssr_pageprops',
        '',
        'Why this strategy:',
        ...data.chosen_reason.map(r => `- ${r}`),
        '',
        '## Selected Future SSR Probe Targets',
        '',
        ...data.future_ssr_probe_targets.map((t, i) => [
            `### Target ${i + 1}: ${t.target_match_id}`,
            `- expected: ${t.expected_home} vs ${t.expected_away} | ${t.expected_date || 'date TBD'}`,
            `- status: ${t.current_status}`,
            `- route_hash_pair_known: ${t.route_hash_pair_known || 'missing'}`,
            `- why selected: ${t.why_selected}`,
            `- expected page URL: ${t.expected_page_url || 'to be discovered via league page search'}`,
            `- probe method: ${t.expected_probe_method}`,
            `- max requests: ${t.max_request_count}`,
            '',
        ].join('\n')),
        '## SSR pageProps Extraction Contract',
        '',
        '### Allowed safe summary fields (22 fields)',
        ...data.allowed_safe_summary_fields.map(f => `- \`${f}\``),
        '',
        '### Forbidden in save',
        ...data.forbidden_fields_in_save.map(f => `- \`${f}\``),
        '',
        '### Extraction process',
        '1. GET match page URL with SSR-friendly User-Agent',
        '2. Search response for `id="__NEXT_DATA__"` script tag',
        '3. Parse JSON in-memory; extract only allowed fields',
        '4. Discard full HTML, full __NEXT_DATA__, full pageProps immediately',
        '5. Save only safe summary fields to manifest',
        '',
        '## Probe Safety Boundary',
        '',
        '- Stop on 403 / block / captcha / first identity mismatch',
        '- No retry on any block signal',
        '- No browser, no proxy, no bypass',
        '- In-memory parse only; no full payload saved',
        '- No DB write, no raw write, no raw_match_data insert',
        '- No re-acceptance, no suspension reversal',
        '- raw_write_ready_count=0',
        '',
        '## Authorization Required',
        '',
        'SSR/pageProps probe execution requires explicit user authorization.',
        'This gate document records the boundary; it does NOT authorize execution.',
        '',
        '## Not Executed',
        '',
        '- No live fetch performed',
        '- No network request performed',
        '- No page fetched',
        '- No HTML saved',
        '',
        '## Next',
        'User explicit authorization required; do NOT execute SSR probe without it; do NOT raw write',
    ];
    wt(RPT, lines.join('\n') + '\n');
}

if (require.main === module) {
    const data = build();
    wj(OUT, data);
    writeReport(data);
    console.log(JSON.stringify({
        adg46_status: data.adg46_status,
        authorization_gate_prepared: true,
        ssr_probe_not_executed: true,
        strategy: data.chosen_strategy,
        future_target_count: data.future_probe_target_count,
        raw_write_ready_count: 0,
    }, null, 2));
}

module.exports = { build };
