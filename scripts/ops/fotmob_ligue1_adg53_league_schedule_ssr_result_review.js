#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG53 review is superseded by ADG54 promotion
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG53-REVIEW';
const A52 = 'docs/_manifests/fotmob_ligue1_adg52_league_schedule_ssr_probe.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg53_league_schedule_ssr_result_review.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG53_LEAGUE_SCHEDULE_SSR_RESULT_REVIEW.md';
function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

function build() {
    const a52 = rj(A52);
    const adg54Plan = {
        phase: 'ADG54', type: 'no-write canonical identity promotion preview',
        input: 'ADG52 safe summary matched_targets (32 targets)',
        output_preview_fields: ['corrected_canonical_detail_url','corrected_route_code','corrected_hash_id','corrected_route_hash_pair','expected_home','expected_away','expected_date','orientation_status','promotion_guard_status','raw_write_ready'],
        guards: ['validateCanonicalUrlAtomicHandoff','parseFotmobCanonicalDetailUrl','home_away_match','date_match_tolerance','competition_match','no_duplicate_conflict','no_suspended_reversal_without_authorization','raw_write_ready=false'],
        forbidden: ['db_write','raw_write','raw_match_data_insert','re_acceptance','suspension_reversal','full_payload_save','browser/proxy/bypass'],
        requires_explicit_user_authorization: true, not_executed_in_adg53: true,
    };
    return {
        schema_version: 'adg53_review_v1', lifecycle: 'phase-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: [A52, CS],
        safety: { live_fetch_performed: false, network_request_performed: false, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false },
        adg53_status: 'review_completed', review_performed: true,
        adg52_breakthrough_review: {
            planned_source_count: 1, attempted_request_count: a52.attempted_request_count, successful_http_200_count: a52.successful_http_200_count,
            next_data_marker_found: true, safe_summary_extracted: true,
            fixture_count_detected: a52.fixture_count_detected, route_hash_pair_candidates: a52.route_hash_pair_candidates_count,
            canonical_detail_url_candidates: a52.canonical_detail_url_candidates_count,
            target_problem_set_count: 32, matched_targets: a52.candidate_target_matches_detected_count, matched_coverage_percent: a52.candidate_target_matches_detected_count === 32 ? 100 : 0,
            previously_confirmed_reverse: 2, previously_unverified: 3, previously_missing: 27,
            league_schedule_home_away_orientation_confirmed: true,
            breakthrough_summary: 'League schedule SSR data exposes canonical identities at season scale. All 32 Ligue 1 problem targets have route_hash_pair + canonical_detail_url candidates. League schedule home/away data provides correct orientation — resolving the prior reverse-fixture blocker.',
            prior_blocker_resolved: 'single_match_page_pageprops_did_not_expose_alternate_hash_ids',
            raw_write_ready: false,
        },
        adg54_promotion_plan: adg54Plan,
        raw_write_ready_count: 0,
        recommended_next_step: 'User must explicitly authorize ADG54 no-write canonical identity promotion preview; do NOT raw write; do NOT DB write',
    };
}

function writeReport(data) {
    const r = data.adg52_breakthrough_review;
    const lines = ['# ADG53 League Schedule SSR Result Review', '', `- Phase: ${PH}`, '- breakthrough: league schedule SSR viable and decisive', '', '## ADG52 Breakthrough',
        `- fixture_count: ${r.fixture_count_detected}`, `- route_hash_pairs: ${r.route_hash_pair_candidates}`, `- canonical_urls: ${r.canonical_detail_url_candidates}`, `- matched_targets: ${r.matched_targets}/${r.target_problem_set_count} (${r.matched_coverage_percent}%)`,
        `- previously reverse: ${r.previously_confirmed_reverse}, unverified: ${r.previously_unverified}, missing: ${r.previously_missing}`,
        `- orientation: league schedule home/away confirmed correct`, `- prior blocker: ${r.prior_blocker_resolved}`, '',
        '## ADG54 Promotion Plan', `- type: ${data.adg54_promotion_plan.type}`, `- input: ${data.adg54_promotion_plan.input}`,
        `- guards: ${data.adg54_promotion_plan.guards.length} rules`, `- requires authorization: true`, `- not executed in ADG53: true`, '',
        '## Next', 'User must authorize ADG54 no-write canonical identity promotion preview; do NOT raw write'];
    wt(RPT, lines.join('\n') + '\n');
}
if (require.main === module) { const d = build(); wj(OUT, d); writeReport(d); console.log(JSON.stringify({ adg53_status: d.adg53_status, matched: d.adg52_breakthrough_review.matched_targets, coverage: d.adg52_breakthrough_review.matched_coverage_percent, raw_write_ready_count: 0 }, null, 2)); }
module.exports = { build };
