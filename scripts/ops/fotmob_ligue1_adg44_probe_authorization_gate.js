#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG44 probe is either executed or superseded
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG44-AUTH-GATE';
const A43 = 'docs/_manifests/fotmob_ligue1_canonical_url_pair_discovery_planning.adg43.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg44_probe_authorization_gate.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG44_PROBE_AUTHORIZATION_GATE.md';

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a43 = rj(A43);

    // Select up to 5 future probe targets
    const missing = a43.target_groups.missing_canonical_url_targets || [];
    const unverified = a43.target_groups.unverified_route_hash_pair_targets || [];

    // Selection criteria:
    // - 2 high-value missing: Marseille-PSG and Lyon-Marseille
    // - 2 unverified with clear reverse risk: PSG-Angers, Lens-Brest
    // - 1 additional reverse-risk: Strasbourg-Nantes
    const selectedIds = new Set([
        '53_20252026_4830499', // Marseille vs PSG (Le Classique)
        '53_20252026_4830480', // Lyon vs Marseille
        '53_20252026_4830473', // PSG vs Angers
        '53_20252026_4830478', // Lens vs Brest
        '53_20252026_4830474', // Strasbourg vs Nantes
    ]);

    const selectedMissing = missing.filter(t => selectedIds.has(t.target_match_id));
    const selectedUnverified = unverified.filter(t => selectedIds.has(t.target_match_id));

    const probeTargets = [
        ...selectedMissing.map(t => ({
            target_match_id: t.target_match_id,
            expected_home: t.expected_home,
            expected_away: t.expected_away,
            expected_date: t.expected_match_date,
            current_status: 'canonical_url_missing_needs_l1_discovery',
            why_selected: t.target_match_id.includes('4830499')
                ? 'highest_value_missing_le_classique_marseille_vs_psg'
                : 'high_value_missing_lyon_vs_marseille',
            expected_probe_source: 'GET L1 league API overview for league_id=53 season=2025/2026',
            max_request_count: 1,
            safe_summary_only: true,
            raw_write_ready: false,
        })),
        ...selectedUnverified.map(t => ({
            target_match_id: t.target_match_id,
            expected_home: t.expected_home,
            expected_away: t.expected_away,
            expected_date: t.expected_match_date,
            route_hash_pair: t.route_hash_pair,
            canonical_detail_url: t.canonical_detail_url,
            current_status: 'route_hash_pair_unverified_needs_detail_verification',
            why_selected: t.slug_orientation_reversed
                ? `reverse_slug_risk_verification_${t.expected_home.toLowerCase().replace(/\s+/g, '_')}_vs_${t.expected_away.toLowerCase().replace(/\s+/g, '_')}`
                : 'detail_page_verification_required',
            expected_probe_source: 'detail page safe summary extraction (no full payload)',
            max_request_count: 1,
            safe_summary_only: true,
            raw_write_ready: false,
        })),
    ];

    return {
        schema_version: 'adg44_auth_gate_v1',
        lifecycle: 'phase-artifact',
        phase: PH,
        generated_at: new Date().toISOString(),
        input_sources: [A43, CS],
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
        adg44_auth_gate_status: 'authorization_required',
        authorization_gate_prepared: true,
        probe_not_executed: true,

        requires_explicit_user_authorization: true,
        authorization_scope: 'ADG44 bounded diagnostic probe execution only; does NOT authorize raw write, DB write, re-acceptance, or suspension reversal',

        future_probe_target_count: probeTargets.length,
        max_targets: 5,
        max_requests_per_target: 1,
        total_max_requests: 5,

        probe_boundary: {
            stop_on_403_or_block: true,
            stop_on_captcha: true,
            stop_on_first_identity_mismatch: true,
            stop_on_first_access_blocker: true,
            no_retry_on_block: true,
            no_browser: true,
            no_proxy: true,
            no_bypass: true,
            no_full_payload: true,
            safe_summary_only: true,
            allowed_summary_fields: [
                'observed_home_team',
                'observed_away_team',
                'observed_match_date',
                'observed_competition',
                'observed_detail_external_id',
                'identity_match_status',
            ],
            no_db_write: true,
            no_raw_write: true,
            no_raw_match_data_insert: true,
            no_re_acceptance: true,
            no_suspension_reversal: true,
            raw_write_ready_count: 0,
        },

        future_probe_targets: probeTargets,

        recommended_next_step: 'User must explicitly authorize ADG44 probe execution; do NOT proceed without authorization; do not raw write',
    };
}

function writeReport(data) {
    const lines = [
        '# ADG44 Bounded Diagnostic Probe Authorization Gate',
        '',
        `- lifecycle: phase-artifact`,
        `- Phase: ${PH}`,
        `- future_probe_target_count: ${data.future_probe_target_count}`,
        `- max_targets: ${data.max_targets}`,
        `- max_requests_per_target: ${data.max_requests_per_target}`,
        `- requires_explicit_user_authorization: true`,
        `- probe_not_executed: true`,
        `- raw_write_ready_count: 0`,
        '',
        '## Selected Future Probe Targets',
        '',
        ...data.future_probe_targets.map((t, i) => [
            `### Target ${i + 1}: ${t.target_match_id}`,
            `- expected: ${t.expected_home} vs ${t.expected_away} | ${t.expected_date || 'date TBD'}`,
            `- status: ${t.current_status}`,
            `- why selected: ${t.why_selected}`,
            `- probe source: ${t.expected_probe_source}`,
            `- max requests: ${t.max_request_count}`,
            `- current route_hash_pair: ${t.route_hash_pair || 'missing'}`,
            '',
        ].join('\n')),
        '## Probe Safety Boundary',
        '',
        '- Stop on 403 / block / captcha',
        '- Stop on first identity mismatch / access blocker',
        '- No retry on any block signal',
        '- No browser, no proxy, no bypass',
        '- Safe summary fields only (home, away, date, competition, identity status)',
        '- No full payload (no pageProps, no raw_data, no source body)',
        '- No DB write, no raw write, no raw_match_data insert',
        '- No re-acceptance, no suspension reversal',
        '- raw_write_ready_count=0',
        '',
        '## Authorization Required',
        '',
        'ADG44 probe execution requires explicit user authorization.',
        'This gate document records the boundary; it does NOT authorize execution.',
        'The user must issue a separate, explicit authorization to proceed.',
        '',
        '## Not Executed',
        '',
        '- No live fetch performed',
        '- No network request performed',
        '- ADG44 probe NOT executed in this phase',
        '',
        '## Next',
        'User explicit authorization required before any ADG44 probe execution; do not raw write',
    ];
    wt(RPT, lines.join('\n') + '\n');
}

if (require.main === module) {
    const data = build();
    wj(OUT, data);
    writeReport(data);
    console.log(JSON.stringify({
        adg44_auth_gate_status: data.adg44_auth_gate_status,
        authorization_gate_prepared: true,
        probe_not_executed: true,
        raw_write_ready_count: 0,
    }, null, 2));
}

module.exports = { build };
