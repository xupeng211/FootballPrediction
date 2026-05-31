#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG51 gate is superseded by ADG52 authorized probe
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG51-SEED-GATE';
const A50 = 'docs/_manifests/fotmob_ligue1_league_schedule_ssr_discovery_gate.adg50.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_league_schedule_url_seed_gate.adg51.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_LEAGUE_SCHEDULE_URL_SEED_GATE_ADG51.md';
function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function validateUrlSeed(url) {
    try {
        const u = new URL(url);
        const parts = u.pathname.split('/').filter(Boolean);
        const fixturesIdx = parts.indexOf('fixtures');
        return {
            ok: true,
            protocol: u.protocol.replace(':', ''),
            hostname: u.hostname,
            locale_path: parts[0] || null,
            path_segments: parts,
            league_segment_idx: parts.indexOf('leagues'),
            league_id: parts[parts.indexOf('leagues') + 1] || null,
            page_type: 'league_fixtures',
            league_slug: fixturesIdx >= 0 ? parts[fixturesIdx + 1] || null : null,
            tab: fixturesIdx >= 0 ? parts[fixturesIdx] : null,
            query_group: u.searchParams.get('group') || null,
            season_param_present: u.searchParams.has('season'),
        };
    } catch (_) { return { ok: false, reason: 'invalid_url' }; }
}

function build() {
    const v = validateUrlSeed('https://www.fotmob.com/zh-Hans/leagues/53/fixtures/ligue-1?group=by-date');

    const topLevelFields = ['source_url','http_status','content_type','redirect_summary','next_data_marker_present','pageprops_marker_present','hydration_marker_present','observed_competition','observed_league_id','observed_league_slug','observed_season','observed_tab_or_page_type','fixture_count_detected','candidate_target_matches_detected_count','target_match_ids_matched','route_code_candidates_count','hash_id_candidates_count','route_hash_pair_candidates_count','canonical_detail_url_candidates_count','extraction_status','blocker_reason','full_payload_saved'];
    const matchedFields = ['target_match_id','expected_home','expected_away','expected_date','candidate_home','candidate_away','candidate_date','candidate_route_code','candidate_hash_id','candidate_route_hash_pair','candidate_canonical_detail_url','orientation_status','confidence_reason'];
    const forbidden = ['full_html','full_next_data','full_pageprops','full_raw_json','full_source_body','cookies','sensitive_headers','session_tokens','api_keys'];

    return {
        schema_version: 'adg51_seed_gate_v1', lifecycle: 'phase-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: ['user_provided_url_seed', A50, CS],
        safety: { live_fetch_performed: false, network_request_performed: false, fotmob_request_performed: false, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false, full_html_saved: false, full_next_data_saved: false, full_pageprops_saved: false, re_acceptance_performed: false, suspension_reversal_performed: false, browser_bypass_performed: false },
        adg51_status: 'url_seed_recorded', url_seed_recorded: true, source_controlled_url_available: true, probe_not_executed: true,
        user_provided_url_seed: {
            url: 'https://www.fotmob.com/zh-Hans/leagues/53/fixtures/ligue-1?group=by-date',
            static_validation: v,
            browser_observed_competition: 'Ligue 1 / France',
            browser_observed_league_id: '53',
            browser_observed_season: '2025/2026',
            browser_tab: 'fixtures',
            season_param_present: false,
            current_season_url_without_explicit_season: true,
            season_param_note: 'User observed current-season page normally does not include explicit season param; historical seasons may include season=YYYY-YYYY',
            historical_season_param_example: 'season=2023-2024',
            source_type: 'league_fixtures_page_by_date',
        },
        future_adg52_probe_contract: {
            requires_explicit_user_authorization: true,
            source_url_must_equal: 'https://www.fotmob.com/zh-Hans/leagues/53/fixtures/ligue-1?group=by-date',
            max_sources: 1, max_requests_per_source: 1,
            public_league_schedule_page_only: true, ssr_pageprops_hydration_only: true,
            no_api_endpoint_guessing: true, no_browser_automation: true, no_proxy: true, no_bypass: true,
            stop_rules: {
                stop_on_403_or_block: true, stop_on_captcha: true, stop_on_season_mismatch: true,
                stop_on_wrong_competition: true, stop_on_unexpected_large_payload_if_cannot_summarize_safely: true,
                no_retry_on_block: true,
            },
            in_memory_parse_only: true, safe_summary_only: true,
            no_full_html_saved: true, no_full_next_data_saved: true, no_full_pageprops_saved: true, no_full_raw_json_saved: true,
            no_db_write: true, no_raw_write: true, no_raw_match_data_insert: true, raw_write_ready_count: 0,
            season_resolution_note: 'ADG52 probe must verify observed season from SSR safe summary. If safe summary indicates wrong season (not 2025/2026), stop and classify season_mismatch.',
        },
        allowed_safe_summary_fields_top: topLevelFields,
        allowed_matched_target_fields: matchedFields,
        forbidden_save_types: forbidden,
        confirmed_reverse_count: 2, still_unverified_count: 3, canonical_url_missing_count: 27,
        raw_write_ready_count: 0,
        recommended_next_step: 'User must explicitly authorize ADG52 bounded league schedule SSR probe using the recorded URL seed; do NOT execute without authorization',
    };
}

function writeReport(data) {
    const u = data.user_provided_url_seed; const v = u.static_validation;
    const lines = ['# ADG51 League Schedule URL Seed Gate', '', `- Phase: ${PH}`, '- url_seed_recorded: true', '- source_controlled_url_available: true', `- url: ${u.url}`, '', '## Static URL Validation',
        `- protocol: ${v.protocol}`, `- hostname: ${v.hostname}`, `- locale: ${v.locale_path}`, `- league_id: ${v.league_id}`, `- league_slug: ${v.league_slug}`, `- tab: ${v.tab}`, `- query_group: ${v.query_group}`, `- season_param_present: ${v.season_param_present}`, `- validation: ${v.ok ? 'PASS' : 'FAIL: ' + v.reason}`, '',
        '## Browser Observation', `- competition: ${u.browser_observed_competition}`, `- league_id: ${u.browser_observed_league_id}`, `- season: ${u.browser_observed_season}`, `- tab: ${u.browser_tab}`, `- season_param_present: ${u.season_param_present}`, `- note: ${u.season_param_note}`, '',
        '## Future ADG52 Probe Contract', `- source_url: ${data.future_adg52_probe_contract.source_url_must_equal}`, '- stop: 403/block/captcha/season_mismatch/wrong_competition', '- in-memory parse; safe summary only', '- no full HTML/__NEXT_DATA__/pageProps saved', '- no DB/raw write; raw_write_ready_count=0', '',
        '## Next', 'User must explicitly authorize ADG52 bounded league schedule SSR probe; do NOT execute without authorization'];
    wt(RPT, lines.join('\n') + '\n');
}

if (require.main === module) { const d = build(); wj(OUT, d); writeReport(d); console.log(JSON.stringify({ adg51_status: d.adg51_status, url_seed_recorded: true, url_valid: d.user_provided_url_seed.static_validation.ok, raw_write_ready_count: 0 }, null, 2)); }
module.exports = { build };
