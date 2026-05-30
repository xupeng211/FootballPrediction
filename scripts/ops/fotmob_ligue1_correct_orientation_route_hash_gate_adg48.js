#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG48 gate is superseded by authorized correct-orientation probe
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG48-GATE';
const A47 = 'docs/_manifests/fotmob_ligue1_adg47_ssr_probe_result_review.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_correct_orientation_route_hash_gate.adg48.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_CORRECT_ORIENTATION_ROUTE_HASH_GATE_ADG48.md';
function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a47 = rj(A47);
    const targets = [
        {
            target_match_id: '53_20252026_4830473',
            expected_home: 'Paris Saint-Germain', expected_away: 'Angers', expected_date: '2025-08-22', expected_competition: 'Ligue 1',
            current_status: 'known_route_hash_pair_confirmed_reverse',
            known_route_hash_pair: '2o4ahb#4830473', known_reverse: true,
            why_selected: 'Confirmed reverse fixture via ADG46 SSR probe. Same route_code 2o4ahb may serve both legs via different hash_ids (ADG40 model). Need to discover correct-orientation hash_id for PSG home vs Angers away.',
            future_probe_goal: 'discover_correct_orientation_route_hash_pair', max_request_count: 1, safe_summary_only: true, full_payload_saved: false, raw_write_ready: false,
        },
        {
            target_match_id: '53_20252026_4830472',
            expected_home: 'Nice', expected_away: 'Auxerre', expected_date: '2025-08-23', expected_competition: 'Ligue 1',
            current_status: 'route_hash_pair_unverified_needs_detail_verification',
            known_route_hash_pair: '2sy6tc#4830472',
            why_selected: 'One of 4 remaining unverified route_hash_pairs. Early season fixture. SSR safe summary can verify orientation against expected home/away.',
            future_probe_goal: 'verify_route_hash_pair_orientation', max_request_count: 1, safe_summary_only: true, full_payload_saved: false, raw_write_ready: false,
        },
        {
            target_match_id: '53_20252026_4830499',
            expected_home: 'Marseille', expected_away: 'Paris Saint-Germain', expected_date: null, expected_competition: 'Ligue 1',
            current_status: 'canonical_url_missing_needs_l1_discovery',
            known_route_hash_pair: null,
            why_selected: 'Highest-value missing canonical URL (Le Classique). SSR probe can search league schedule page for this fixture and discover canonical URL/route_hash_pair.',
            future_probe_goal: 'discover_canonical_url_pair', max_request_count: 1, safe_summary_only: true, full_payload_saved: false, raw_write_ready: false,
        },
    ];
    const allowedFields = ['target_match_id','request_url','http_status','redirect_summary','content_type','next_data_marker_present','pageprops_marker_present','hydration_marker_present','canonical_detail_url_found','route_code_found','hash_id_found','route_hash_pair_found','observed_home','observed_away','observed_date','observed_competition','identity_status','orientation_status','extraction_status','blocker_reason','full_payload_saved'];
    const forbiddenFields = ['full_html','full_next_data','full_pageprops','full_raw_data','full_source_body','cookies','sensitive_headers','session_tokens','api_keys'];
    return {
        schema_version: 'adg48_gate_v1', lifecycle: 'phase-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: [A47, CS],
        safety: { live_fetch_performed: false, network_request_performed: false, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false, full_html_saved: false, full_next_data_saved: false, full_pageprops_saved: false, re_acceptance_performed: false, suspension_reversal_performed: false, browser_bypass_performed: false },
        adg48_status: 'authorization_gate_prepared', authorization_gate_prepared: true, probe_not_executed: true,
        chosen_strategy: 'ssr_pageprops_correct_orientation_discovery',
        strategy_basis: ['ADG46 confirmed SSR viable (HTTP 200, __NEXT_DATA__ found)', 'ADG47 confirmed 2o4ahb#4830473 is reverse fixture', 'ADG40 model: same route_code serves both legs via different hash_ids'],
        requires_explicit_user_authorization: true,
        confirmed_reverse_count: 1, remaining_unverified_count: 4, canonical_url_missing_count: 27,
        future_probe_target_count: 3, max_targets: 3, max_requests_per_target: 1,
        probe_boundary: { public_match_page_only: true, ssr_pageprops_only: true, no_api_endpoint_guessing: true, no_browser_automation: true, no_proxy: true, no_bypass: true, no_retry_on_block: true, stop_on_403_or_block: true, stop_on_captcha: true, stop_on_first_identity_mismatch: true, stop_on_first_reverse_fixture: true, in_memory_parse_only: true, safe_summary_only: true, no_full_html_saved: true, no_full_next_data_saved: true, no_full_pageprops_saved: true, no_db_write: true, no_raw_write: true, raw_write_ready_count: 0 },
        allowed_safe_summary_fields: allowedFields, forbidden_fields_in_save: forbiddenFields,
        future_ssr_probe_targets: targets,
        raw_write_ready_count: 0,
        recommended_next_step: 'User must explicitly authorize ADG48 correct-orientation SSR probe; do NOT execute without authorization; do NOT raw write',
    };
}

function writeReport(data) {
    const lines = ['# ADG48 Correct-Orientation Route Hash Discovery Gate','',`- Phase: ${PH}`,`- chosen_strategy: ${data.chosen_strategy}`,`- future_probe_target_count: ${data.future_probe_target_count}`,`- max_targets: 3, max_requests_per_target: 1`,`- confirmed_reverse: 1, remaining_unverified: 4, canonical_url_missing: 27`,`- requires_explicit_user_authorization: true`,`- probe_not_executed: true`,`- raw_write_ready_count: 0`,'','## Strategy Basis',...data.strategy_basis.map(s => `- ${s}`),'','## Future Targets',''];
    for (const t of data.future_ssr_probe_targets) { lines.push(`### ${t.target_match_id}`,`- expected: ${t.expected_home} vs ${t.expected_away} | ${t.expected_date || 'date TBD'}`,`- status: ${t.current_status}`,`- known pair: ${t.known_route_hash_pair || 'missing'}`,`- goal: ${t.future_probe_goal}`,`- why: ${t.why_selected}`,''); }
    lines.push('## Safety Boundary','- SSR/pageProps only; public match pages; in-memory parse','- Stop: 403/block/captcha/identity mismatch/reverse fixture','- No full HTML/__NEXT_DATA__/pageProps saved','- No DB/raw write; raw_write_ready_count=0','','## Authorization Required','Probe requires separate explicit user authorization. This gate does NOT authorize execution.','','## Next','User explicit authorization required; do NOT execute probe; do NOT raw write');
    wt(RPT, lines.join('\n') + '\n');
}
if (require.main === module) { const d = build(); wj(OUT, d); writeReport(d); console.log(JSON.stringify({ adg48_status: d.adg48_status, strategy: d.chosen_strategy, targets: d.future_probe_target_count, raw_write_ready_count: 0 }, null, 2)); }
module.exports = { build };
