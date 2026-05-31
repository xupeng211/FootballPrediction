#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG50 gate is superseded by authorized league schedule SSR probe
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG50-GATE';
const A49 = 'docs/_manifests/fotmob_ligue1_adg49_correct_orientation_strategy_review.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_league_schedule_ssr_discovery_gate.adg50.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_LEAGUE_SCHEDULE_SSR_DISCOVERY_GATE_ADG50.md';
function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a49 = rj(A49);
    const allowedFields = ['source_url','http_status','content_type','redirect_summary','next_data_marker_present','pageprops_marker_present','hydration_marker_present','fixture_count_detected','candidate_target_matches_detected_count','target_match_ids_matched','route_code_candidates_count','hash_id_candidates_count','route_hash_pair_candidates_count','canonical_detail_url_candidates_count','extraction_status','blocker_reason','full_payload_saved'];
    const forbiddenFields = ['full_html','full_next_data','full_pageprops','full_raw_json','full_source_body','cookies','sensitive_headers','session_tokens','api_keys'];
    const matchedTargetSummary = ['target_match_id','expected_home','expected_away','expected_date','candidate_home','candidate_away','candidate_date','candidate_route_code','candidate_hash_id','candidate_route_hash_pair','candidate_canonical_detail_url','orientation_status'];

    const futureSource = {
        source_type: 'league_schedule_ssr_page',
        competition: 'Ligue 1',
        season: '2025/2026',
        expected_scope: 'season fixtures / match list / schedule hydration data',
        goal: 'enumerate fixture-level canonical identities (route_code, hash_id, route_hash_pair, canonical_detail_url, home/away orientation)',
        source_controlled_url_available: false,
        source_controlled_url: null,
        source_url_note: 'No source-controlled league schedule page URL found in committed artifacts. ADG50 gate records need for URL seed. Future probe must not guess URL; must use source-controlled URL from authorized discovery.',
        max_request_count: 1,
        safe_summary_only: true,
        full_payload_saved: false,
        raw_write_ready: false,
    };

    return {
        schema_version: 'adg50_gate_v1', lifecycle: 'phase-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: [A49, CS],
        safety: { live_fetch_performed: false, network_request_performed: false, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false, full_html_saved: false, full_next_data_saved: false, full_pageprops_saved: false, re_acceptance_performed: false, suspension_reversal_performed: false, browser_bypass_performed: false },
        adg50_status: 'authorization_gate_prepared', authorization_gate_prepared: true, probe_not_executed: true,
        chosen_strategy: 'league_schedule_ssr_discovery',
        strategy_basis: [
            'ADG46 confirmed SSR viable (HTTP 200, __NEXT_DATA__ extractable)',
            'ADG48 confirmed 2 known route_hash_pairs are reverse fixtures',
            'ADG48 confirmed single match page pageProps does not expose alternate hash_ids',
            'ADG49 recommended league_schedule_ssr_discovery as next strategy',
            'League schedule page likely contains full season fixture list with all route/hash pairs',
        ],
        requires_explicit_user_authorization: true,
        future_probe_source_count: 1, max_sources: 1, max_requests_per_source: 1,
        confirmed_reverse_count: 2, still_unverified_count: 3, canonical_url_missing_count: 27,
        future_probe_source: futureSource,
        probe_boundary: {
            public_league_schedule_page_only: true, ssr_pageprops_hydration_only: true,
            no_api_endpoint_guessing: true, no_authenticated_api: true, no_browser_automation: true, no_proxy: true, no_bypass: true,
            no_retry_on_block: true, stop_on_403_or_block: true, stop_on_captcha: true, stop_on_unexpected_large_payload_if_cannot_summarize_safely: true,
            in_memory_parse_only: true, safe_summary_only: true, no_full_html_saved: true, no_full_next_data_saved: true, no_full_pageprops_saved: true, no_full_raw_json_saved: true,
            no_db_write: true, no_raw_write: true, no_raw_match_data_insert: true, raw_write_ready_count: 0,
        },
        allowed_safe_summary_fields: allowedFields, matched_targets_summary_schema: matchedTargetSummary, forbidden_fields_in_save: forbiddenFields,
        raw_write_ready_count: 0,
        recommended_next_step: 'User must provide source-controlled league schedule page URL seed OR explicitly authorize a bounded URL discovery step; do NOT guess URL; do NOT raw write; do NOT execute probe without authorization',
    };
}

function writeReport(data) {
    const src = data.future_probe_source;
    const lines = ['# ADG50 League Schedule SSR Discovery Gate', '', `- Phase: ${PH}`, `- chosen_strategy: ${data.chosen_strategy}`, `- future_probe_source_count: ${data.future_probe_source_count}`, `- max_requests_per_source: 1`, `- source_controlled_url_available: ${src.source_controlled_url_available}`, `- confirmed_reverse: ${data.confirmed_reverse_count}, still_unverified: ${data.still_unverified_count}, canonical_url_missing: ${data.canonical_url_missing_count}`, `- requires_explicit_user_authorization: true`, `- probe_not_executed: true`, `- raw_write_ready_count: 0`, '',
        '## Strategy Basis', ...data.strategy_basis.map(s => `- ${s}`), '',
        '## Future Probe Source', `- type: ${src.source_type}`, `- competition: ${src.competition}`, `- season: ${src.season}`, `- scope: ${src.expected_scope}`, `- goal: ${src.goal}`, `- source_controlled_url_available: ${src.source_controlled_url_available}`, `- note: ${src.source_url_note}`, '',
        '## Probe Boundary', '- public league schedule page only; SSR/hydration only', '- stop: 403/block/captcha/unexpected large payload', '- in-memory parse; no full HTML/__NEXT_DATA__/pageProps saved', '- no DB/raw write; raw_write_ready_count=0', '',
        '## Allowed Safe Summary (aggregate/bounded)', `- ${data.allowed_safe_summary_fields.length} top-level fields`, `- matched_targets_summary: ${data.matched_targets_summary_schema.length} fields per target`, `- ${data.forbidden_fields_in_save.length} forbidden save types`, '',
        '## Authorization Required', 'Probe requires explicit user authorization + source-controlled URL seed. This gate does NOT authorize execution.', '',
        '## Next', 'User must provide league schedule URL seed or authorize URL discovery; do NOT guess; do NOT raw write'];
    wt(RPT, lines.join('\n') + '\n');
}

if (require.main === module) { const d = build(); wj(OUT, d); writeReport(d); console.log(JSON.stringify({ adg50_status: d.adg50_status, strategy: d.chosen_strategy, source_url_available: d.future_probe_source.source_controlled_url_available, raw_write_ready_count: 0 }, null, 2)); }
module.exports = { build };
