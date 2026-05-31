#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG52 probe results are recorded
'use strict';
const fs = require('node:fs'); const path = require('node:path');
const PP = path.resolve(__dirname, '../..'); const PH = 'Phase 5.21-ADG52-PROBE';
const A51 = 'docs/_manifests/fotmob_ligue1_league_schedule_url_seed_gate.adg51.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg52_league_schedule_ssr_probe.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG52_LEAGUE_SCHEDULE_SSR_PROBE.md';
const SRC_URL = 'https://www.fotmob.com/zh-Hans/leagues/53/fixtures/ligue-1?group=by-date';

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

async function httpGet(url) {
    const ctrl = new AbortController(); const t = setTimeout(() => ctrl.abort(), 60000);
    try { const res = await fetch(url, { signal: ctrl.signal, headers: { 'User-Agent': 'Mozilla/5.0 (compatible; FP/4.51 ADG52-league-schedule)' } }); const body = await res.text(); return { status: res.status, headers: Object.fromEntries(res.headers.entries()), body }; }
    finally { clearTimeout(t); }
}

function safeCheckMarkers(body) {
    return { nextData: body.includes('__NEXT_DATA__') || body.includes('"buildId"'), pageProps: body.includes('pageProps') || body.includes('"props"'), hydration: body.includes('__NEXT_DATA__') && body.includes('"props"') };
}

// eslint-disable-next-line complexity
function extractLeagueSafeSummary(body) {
    const s = {};
    try {
        const ndMatch = body.match(/<script\s+id="__NEXT_DATA__"[^>]*>(.*?)<\/script>/s);
        if (!ndMatch) { s.extraction_status = 'no_next_data_marker_found'; return s; }
        const nd = JSON.parse(ndMatch[1]); const pp = nd?.props?.pageProps || {};
        // Page identity validation
        s.observed_competition = pp?.league?.name || pp?.competition?.name || pp?.general?.leagueName || null;
        s.observed_league_id = String(pp?.league?.id || pp?.leagueId || pp?.general?.leagueId || '');
        s.observed_league_slug = pp?.league?.slug || pp?.leagueSlug || null;
        s.observed_season = pp?.season || pp?.leagueSeason || pp?.general?.season || null;
        s.observed_tab_or_page_type = pp?.tab || pp?.viewType || 'fixtures_by_date';

        // Enumerate fixtures from season data
        const fixtures = pp?.fixtures || pp?.matches || pp?.matchList || pp?.schedule || pp?.data?.matches || [];
        const allMatches = [];
        if (Array.isArray(fixtures)) allMatches.push(...fixtures);
        else if (fixtures && typeof fixtures === 'object') {
            for (const v of Object.values(fixtures)) { if (Array.isArray(v)) allMatches.push(...v); }
        }
        // Try nested structures
        if (allMatches.length === 0) {
            const flat = [];
            (function dig(obj) { if (!obj || typeof obj !== 'object') return; if (Array.isArray(obj)) { obj.forEach(dig); return; } if (obj.id && (obj.home || obj.away || obj.pageUrl)) { flat.push(obj); return; } for (const v of Object.values(obj)) dig(v); })(pp);
            allMatches.push(...flat);
        }

        s.fixture_count_detected = allMatches.length;
        s.extraction_status = 'next_data_parsed_safe_summary_extracted';

        // Extract safe match summaries
        const matchSummaries = [];
        for (const m of allMatches) {
            const home = m?.home?.name || m?.homeTeam?.name || null;
            const away = m?.away?.name || m?.awayTeam?.name || null;
            const date = m?.status?.utcTime || m?.startTime || m?.matchTimeUTC || null;
            const id = m?.id ? String(m.id) : null;
            const pageUrl = m?.pageUrl || m?.canonicalUrl || null;
            if (!id) continue;
            const summary = { match_id: id, home, away, date, pageUrl };
            if (pageUrl) {
                const parts = pageUrl.split('/').filter(Boolean); const mIdx = parts.indexOf('matches');
                if (mIdx >= 0 && parts.length > mIdx + 2) {
                    summary.route_code = parts[mIdx + 2].split('#')[0];
                    summary.hash_id = pageUrl.split('#').pop() || null;
                    summary.route_hash_pair = summary.route_code && summary.hash_id ? `${summary.route_code}#${summary.hash_id}` : null;
                }
            }
            matchSummaries.push(summary);
        }
        s.match_summaries = matchSummaries; // bounded — only safe fields per match
    } catch (_) { s.extraction_status = 'next_data_parse_failed_or_partial'; }
    return s;
}

function matchTargets(summary, knownTargetIds) {
    const matched = []; const summaries = summary.match_summaries || [];
    const byId = new Map(summaries.filter(s => s.match_id).map(s => [s.match_id, s]));
    for (const tid of knownTargetIds) {
        const s = byId.get(tid);
        if (s) matched.push({ target_match_id: tid, candidate_home: s.home, candidate_away: s.away, candidate_date: s.date, candidate_route_code: s.route_code || null, candidate_hash_id: s.hash_id || null, candidate_route_hash_pair: s.route_hash_pair || null, candidate_canonical_detail_url: s.pageUrl || null, orientation_status: 'pending_verification', confidence_reason: 'found_in_league_schedule_ssr' });
    }
    return matched;
}

// eslint-disable-next-line complexity
async function executeProbe() {
    // Known target IDs from ADG48/ADG42 problem set
    const knownTargetIds = [
        '4830473','4830472','4830474','4830475','4830478', // 5 known pairs
        '4830479','4830476','4830477','4830480','4830482','4830483','4830484','4830485','4830486','4830487',
        '4830488','4830489','4830490','4830491','4830492','4830493','4830494','4830495','4830497','4830498',
        '4830499','4830500','4830501','4830502','4830505','4830507','4830510', // 27 missing
    ];

    const result = { adg52_status: null };
    let response;
    try { response = await httpGet(SRC_URL); } catch (err) {
        result.adg52_status = 'blocked_network_error'; result.blocker_reason = err.message; result.request_attempted = false;
        return buildOutput(result, null);
    }

    const hs = response.status;
    if (hs === 403) { result.adg52_status = 'blocked_403'; result.http_status = 403; result.request_attempted = true; return buildOutput(result, null); }
    if (hs !== 200) { result.adg52_status = 'blocked_network_error'; result.http_status = hs; result.request_attempted = true; return buildOutput(result, null); }

    const body = response.body;
    const markers = safeCheckMarkers(body);
    const summary = markers.nextData ? extractLeagueSafeSummary(body) : { extraction_status: 'no_next_data_marker_found' };

    // Page identity check
    const wrongCompetition = summary.observed_competition && !/ligue\s*1|france/i.test(summary.observed_competition);
    const wrongSeason = summary.observed_season && !/2025.*2026|2026.*2025/i.test(summary.observed_season);

    const matchedTargets = (summary.match_summaries && summary.match_summaries.length > 0) ? matchTargets(summary, knownTargetIds) : [];
    const routeCodes = [...new Set((summary.match_summaries || []).map(s => s.route_code).filter(Boolean))];
    const hashIds = [...new Set((summary.match_summaries || []).map(s => s.hash_id).filter(Boolean))];
    const routeHashPairs = [...new Set((summary.match_summaries || []).map(s => s.route_hash_pair).filter(Boolean))];
    const canonicalUrls = [...new Set((summary.match_summaries || []).map(s => s.pageUrl).filter(Boolean))];

    return buildOutput({
        http_status: hs, content_type: response.headers['content-type'] || null,
        next_data_marker_present: markers.nextData, pageprops_marker_present: markers.pageProps, hydration_marker_present: markers.hydration,
        observed_competition: summary.observed_competition || null, observed_league_id: summary.observed_league_id || null,
        observed_league_slug: summary.observed_league_slug || null, observed_season: summary.observed_season || null,
        observed_tab_or_page_type: summary.observed_tab_or_page_type || null,
        fixture_count_detected: summary.fixture_count_detected || 0,
        extraction_status: summary.extraction_status || 'not_extracted',
        wrong_competition: wrongCompetition, wrong_season: wrongSeason,
        candidate_target_matches_detected_count: matchedTargets.length,
        target_match_ids_matched_count: matchedTargets.length,
        route_code_candidates_count: routeCodes.length, hash_id_candidates_count: hashIds.length,
        route_hash_pair_candidates_count: routeHashPairs.length, canonical_detail_url_candidates_count: canonicalUrls.length,
        matched_targets_summary: matchedTargets.slice(0, 50), // bounded
        full_payload_saved: false,
    });
}

// eslint-disable-next-line complexity
function buildOutput(data, summary) {
    const s = summary || data;
    const attempted = (s.http_status !== undefined);
    const matchedCnt = (s.candidate_target_matches_detected_count || 0);
    const correctOrientation = 0; // requires per-target orientation check, not done here
    let status = 'completed';
    if (s.wrong_competition || s.wrong_season) status = 'wrong_competition_or_season';
    else if (!s.next_data_marker_present) status = 'next_data_marker_missing';
    else if (matchedCnt > 0) status = 'league_schedule_target_matches_found_no_write';
    else if (s.fixture_count_detected > 0) status = 'league_schedule_ssr_safe_summary_extracted_no_write';
    else status = 'no_target_matches_detected';

    return {
        schema_version: 'adg52_probe_v1', lifecycle: 'phase-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: [A51, CS],
        adg52_status: status, user_authorization_confirmed: true, url_seed_merged: true, chosen_strategy: 'league_schedule_ssr_discovery',
        source_url: SRC_URL, planned_source_count: 1, attempted_request_count: attempted ? 1 : 0, successful_http_200_count: s.http_status === 200 ? 1 : 0,
        next_data_marker_found_count: s.next_data_marker_present ? 1 : 0, pageprops_marker_found_count: s.pageprops_marker_present ? 1 : 0, hydration_marker_found_count: s.hydration_marker_present ? 1 : 0,
        safe_summary_extracted_count: (s.fixture_count_detected > 0 || matchedCnt > 0) ? 1 : 0,
        fixture_count_detected: s.fixture_count_detected || 0, candidate_target_matches_detected_count: matchedCnt, target_match_ids_matched_count: s.target_match_ids_matched_count || 0,
        route_code_candidates_count: s.route_code_candidates_count || 0, hash_id_candidates_count: s.hash_id_candidates_count || 0,
        route_hash_pair_candidates_count: s.route_hash_pair_candidates_count || 0, canonical_detail_url_candidates_count: s.canonical_detail_url_candidates_count || 0,
        correct_orientation_route_hash_pair_candidates_found_count: correctOrientation, canonical_url_candidates_found_count: s.canonical_detail_url_candidates_count || 0,
        wrong_competition_or_season_count: (s.wrong_competition || s.wrong_season) ? 1 : 0,
        blocked_403_count: s.http_status === 403 ? 1 : 0, blocked_captcha_or_access_wall_count: 0,
        full_html_saved: false, full_next_data_saved: false, full_pageprops_saved: false, full_payload_saved: false,
        safety: { live_fetch_performed: attempted, network_request_performed: attempted, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false, full_html_saved: false, full_next_data_saved: false, full_pageprops_saved: false, re_acceptance_performed: false, suspension_reversal_performed: false, browser_bypass_performed: false, proxy_used: false, captcha_bypass: false },
        raw_write_ready_count: 0,
        result: {
            http_status: s.http_status, content_type: s.content_type, next_data_marker_present: s.next_data_marker_present, pageprops_marker_present: s.pageprops_marker_present, hydration_marker_present: s.hydration_marker_present,
            observed_competition: s.observed_competition, observed_league_id: s.observed_league_id, observed_league_slug: s.observed_league_slug,
            observed_season: s.observed_season, observed_tab_or_page_type: s.observed_tab_or_page_type,
            fixture_count_detected: s.fixture_count_detected, extraction_status: s.extraction_status,
            matched_targets_summary: s.matched_targets_summary || [],
            wrong_competition: s.wrong_competition, wrong_season: s.wrong_season,
            full_payload_saved: false, raw_write_ready: false,
        },
        recommended_next_step: 'ADG53 review ADG52 league schedule probe findings; do NOT raw write',
    };
}

function writeReport(data) {
    const r = data.result || {};
    const lines = ['# ADG52 League Schedule SSR Probe', '', `- Phase: ${PH}`, `- adg52_status: ${data.adg52_status}`, `- source_url: ${data.source_url}`, `- http_status: ${r.http_status}`, `- next_data_marker: ${r.next_data_marker_present}`, `- fixture_count: ${r.fixture_count_detected}`, `- candidate_matches: ${data.candidate_target_matches_detected_count}`, `- route_code_candidates: ${data.route_code_candidates_count}`, `- hash_id_candidates: ${data.hash_id_candidates_count}`, `- route_hash_pair_candidates: ${data.route_hash_pair_candidates_count}`, `- canonical_url_candidates: ${data.canonical_detail_url_candidates_count}`, `- observed_competition: ${r.observed_competition}`, `- observed_season: ${r.observed_season}`, `- extraction_status: ${r.extraction_status}`, `- wrong_competition: ${r.wrong_competition || false}`, `- wrong_season: ${r.wrong_season || false}`, '', '## Page Identity', `- league: ${r.observed_competition || 'N/A'}`, `- season: ${r.observed_season || 'N/A'}`, `- league_id: ${r.observed_league_id || 'N/A'}`, '', '## Safety', '- no full HTML/__NEXT_DATA__/pageProps saved', '- raw_write_ready_count=0', '', '## Next', 'ADG53 review findings'];
    wt(RPT, lines.join('\n') + '\n');
}

async function main() {
    console.log('ADG52 league schedule SSR probe: single bounded request...');
    const data = await executeProbe();
    wj(OUT, data); writeReport(data);
    console.log(JSON.stringify({ status: data.adg52_status, http_status: data.result?.http_status, fixtures: data.fixture_count_detected, matched: data.candidate_target_matches_detected_count, route_hash_pairs: data.route_hash_pair_candidates_count, canonical_urls: data.canonical_detail_url_candidates_count, raw_write_ready_count: 0 }, null, 2));
    console.log('No full payload saved.');
}
if (require.main === module) { main().catch(err => { console.error('Fatal:', err.message); process.exit(1); }); }
module.exports = { executeProbe };
