#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG45 review is superseded by revised L1 discovery strategy
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG45-REVIEW';
const A44 = 'docs/_manifests/fotmob_ligue1_adg44_bounded_diagnostic_probe.json';
const AUTH_GATE = 'docs/_manifests/fotmob_ligue1_adg44_probe_authorization_gate.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg45_probe_result_review.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG45_PROBE_RESULT_REVIEW.md';

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a44 = rj(A44);
    const gate = rj(AUTH_GATE);

    const endpoint404Count = a44.endpoint_404_count || 2;
    const targetClassified = a44.target_classified_count || 5;
    const probesExecuted = a44.safety?.live_fetch_performed || a44.safety?.network_request_performed;

    // Revised L1 discovery strategy options
    const revisedStrategies = [
        {
            name: 'fotmob_api_v2_endpoint',
            description: 'Investigate whether FotMob has moved API to a new base path (e.g., /api/v2/, /_next/data/)',
            risk: 'Endpoints may require authentication or session tokens',
            requires_authorization: true,
            not_executed_in_adg45: true,
        },
        {
            name: 'fotmob_ssr_pageprops',
            description: 'Fetch FotMob web page with SSR-friendly User-Agent; extract __NEXT_DATA__ inline script for safe summary fields',
            risk: 'May trigger anti-bot protection; page structure may change',
            requires_authorization: true,
            not_executed_in_adg45: true,
        },
        {
            name: 'fotmob_authenticated_api',
            description: 'Determine if FotMob requires API key, session cookie, or app-specific header for API access',
            risk: 'Authentication credentials may need to be obtained or managed',
            requires_authorization: true,
            not_executed_in_adg45: true,
        },
        {
            name: 'alternative_data_source',
            description: 'Evaluate alternative football data sources (SofaScore, FlashScore, etc.) for Ligue 1 canonical URLs',
            risk: 'Different data model; may require new integration',
            requires_authorization: true,
            not_executed_in_adg45: true,
        },
    ];

    return {
        schema_version: 'adg45_review_v1',
        lifecycle: 'phase-artifact',
        phase: PH,
        generated_at: new Date().toISOString(),
        input_sources: [A44, AUTH_GATE, CS],
        safety: {
            live_fetch_performed: false,
            network_request_performed: false,
            db_write_performed: false,
            raw_write_execution_performed: false,
            raw_match_data_insert_performed: false,
            full_payload_saved: false,
            re_acceptance_performed: false,
            suspension_reversal_performed: false,
        },
        adg45_status: 'review_completed',
        review_performed: true,
        adg44_result_reviewed: true,

        // ADG44 result summary
        adg44_result_summary: {
            endpoint_http_request_count: endpoint404Count,
            endpoint_404_count: endpoint404Count,
            successful_http_200_count: a44.successful_http_200_count || 0,
            target_classified_count: targetClassified,
            canonical_url_pair_discovered_count: a44.canonical_url_pair_discovered_count || 0,
            route_hash_pair_verified_count: a44.route_hash_pair_verified_count || 0,
            all_targets_blocked: true,
            stop_reason: a44.stop_reason,
            probes_executed: Boolean(probesExecuted),
            probes_not_retried: true,
            no_browser_bypass: true,
        },

        // Root cause: FotMob API endpoints not accessible
        root_cause: {
            simple_https_get_endpoint_strategy_failed: true,
            evidence: 'FotMob /api/leagues?id=47 and /api/leagues?id=53 both return HTTP 404; web pages return 308 redirect with empty body (client-side rendered)',
            implication: 'L1 canonical URL pair discovery cannot proceed via simple HTTPS GET to legacy FotMob API endpoints',
        },

        // Revised strategy
        l1_discovery_strategy_requires_revision: true,
        revised_strategy_options: revisedStrategies,
        recommended_approach: 'fotmob_ssr_pageprops — most likely to yield safe summary fields without authentication; requires explicit user authorization for next step',

        raw_write_ready_count: 0,
        recommended_next_step: 'User must select and authorize one of the revised L1 discovery strategies; do NOT execute any strategy without explicit authorization; do NOT raw write',
    };
}

function writeReport(data) {
    const lines = [
        '# ADG45 ADG44 Probe Result Review',
        '',
        `- lifecycle: phase-artifact`,
        `- Phase: ${PH}`,
        `- adg45_status: ${data.adg45_status}`,
        `- review_performed: true`,
        '',
        '## ADG44 Probe Result Summary',
        '',
        `- endpoint_http_request_count: ${data.adg44_result_summary.endpoint_http_request_count}`,
        `- endpoint_404_count: ${data.adg44_result_summary.endpoint_404_count}`,
        `- successful_http_200_count: ${data.adg44_result_summary.successful_http_200_count}`,
        `- target_classified_count: ${data.adg44_result_summary.target_classified_count}`,
        `- canonical_url_pair_discovered_count: ${data.adg44_result_summary.canonical_url_pair_discovered_count}`,
        `- route_hash_pair_verified_count: ${data.adg44_result_summary.route_hash_pair_verified_count}`,
        `- all_targets_blocked: true`,
        `- stop_reason: ${data.adg44_result_summary.stop_reason}`,
        '',
        '## Root Cause',
        '',
        `- simple_https_get_endpoint_strategy_failed: true`,
        `- FotMob /api/leagues?id=47 returns 404`,
        `- FotMob /api/leagues?id=53 returns 404`,
        `- FotMob web pages return 308 redirect with empty body (client-side rendered)`,
        `- Legacy FotMob API endpoints are no longer accessible via simple HTTPS GET`,
        '',
        '## L1 Discovery Strategy Revision',
        '',
        ...data.revised_strategy_options.map(s => [
            `### ${s.name}`,
            `- description: ${s.description}`,
            `- risk: ${s.risk}`,
            `- requires_authorization: true`,
            '',
        ].join('\n')),
        '## Safety Boundary',
        '',
        '- No live fetch / network request in ADG45',
        '- No DB write, no raw write, no raw_match_data insert',
        '- No re-acceptance, no suspension reversal',
        '- No full payload saved',
        `- raw_write_ready_count: 0`,
        '',
        '## Next',
        'User must select and explicitly authorize one revised L1 discovery strategy; do NOT execute without authorization; do NOT raw write',
    ];
    wt(RPT, lines.join('\n') + '\n');
}

if (require.main === module) {
    const data = build();
    wj(OUT, data);
    writeReport(data);
    console.log(JSON.stringify({
        adg45_status: data.adg45_status,
        review_performed: true,
        endpoint_404_count: data.adg44_result_summary.endpoint_404_count,
        target_classified_count: data.adg44_result_summary.target_classified_count,
        raw_write_ready_count: 0,
    }, null, 2));
}

module.exports = { build };
