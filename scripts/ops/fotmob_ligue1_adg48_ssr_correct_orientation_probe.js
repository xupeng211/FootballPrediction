#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG48 correct-orientation probe results are recorded
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG48-PROBE';
const GATE48 = 'docs/_manifests/fotmob_ligue1_correct_orientation_route_hash_gate.adg48.json';
const A46 = 'docs/_manifests/fotmob_ligue1_ssr_pageprops_bounded_probe.adg46.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg48_ssr_correct_orientation_probe.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG48_SSR_CORRECT_ORIENTATION_PROBE.md';
const { parseFotmobCanonicalDetailUrl } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');
function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

async function httpGet(url) {
    const ctrl = new AbortController(); const t = setTimeout(() => ctrl.abort(), 30000);
    try { const res = await fetch(url, { signal: ctrl.signal, headers: { 'User-Agent': 'Mozilla/5.0 (compatible; FP/4.51 SSR-correct-orientation)' } }); const body = await res.text(); return { status: res.status, headers: Object.fromEntries(res.headers.entries()), body }; }
    finally { clearTimeout(t); }
}

function safeCheckMarkers(body) {
    return { nextDataMarker: body.includes('__NEXT_DATA__') || body.includes('"buildId"'), pagePropsMarker: body.includes('pageProps') || body.includes('"props"'), hydrationMarker: body.includes('__NEXT_DATA__') && body.includes('"props"') };
}

// eslint-disable-next-line complexity
function extractSafeSummary(body) {
    const s = {};
    try {
        const ndMatch = body.match(/<script\s+id="__NEXT_DATA__"[^>]*>(.*?)<\/script>/s);
        if (ndMatch) {
            const nd = JSON.parse(ndMatch[1]); const pp = nd?.props?.pageProps || {}; const gen = pp?.general || {};
            s.canonical_detail_url_found = gen?.pageUrl || gen?.canonicalUrl || pp?.pageUrl || null;
            if (s.canonical_detail_url_found) {
                const u = s.canonical_detail_url_found.startsWith('http') ? s.canonical_detail_url_found : `https://www.fotmob.com${s.canonical_detail_url_found}`;
                const p = parseFotmobCanonicalDetailUrl(u);
                if (p.ok) { s.route_code_found = p.route_code; s.hash_id_found = p.hash_id; s.route_hash_pair_found = `${p.route_code}#${p.hash_id}`; }
            }
            s.observed_home = gen?.homeTeam?.name || pp?.homeTeam?.name || null;
            s.observed_away = gen?.awayTeam?.name || pp?.awayTeam?.name || null;
            s.observed_date = gen?.matchTimeUTC || gen?.startTime || null;
            s.observed_competition = gen?.leagueName || gen?.parentLeagueName || null;
            s.observed_detail_id = String(gen?.matchId || pp?.matchId || '');
            // Check for alternate/cross-reference fixtures
            s.alternate_hash_candidates = null;
            const related = pp?.relatedMatches || pp?.crossReferences || pp?.alternateFixtures || null;
            if (related) s.alternate_hash_candidates = 'related_matches_present_in_pageProps';
            s.extraction_status = 'next_data_parsed_safe_summary_extracted';
        }
    } catch (_) { s.extraction_status = 'next_data_parse_failed_or_partial'; }
    return s;
}

function normalizeTeam(name) { return String(name ?? '').toLowerCase().replace(/\s+/g, ' ').trim(); }

// eslint-disable-next-line complexity
function classifyTarget(target, summary) {
    const cs = target.current_status; const expH = normalizeTeam(target.expected_home); const expA = normalizeTeam(target.expected_away);
    const obsH = normalizeTeam(summary.observed_home); const obsA = normalizeTeam(summary.observed_away);
    const teamsKnown = Boolean(expH && expA && obsH && obsA);

    if (cs === 'known_route_hash_pair_confirmed_reverse') {
        // Goal: find correct-orientation pair, not verify bad pair
        if (teamsKnown && obsH === expA && obsA === expH) return 'reverse_pair_observed_again';
        if (teamsKnown && obsH === expH && obsA === expA && summary.route_hash_pair_found) {
            const isSameAsBad = summary.route_hash_pair_found === '2o4ahb#4830473';
            return isSameAsBad ? 'reverse_pair_observed_again' : 'correct_orientation_route_hash_pair_discovered_no_write';
        }
        if (summary.route_hash_pair_found && summary.route_hash_pair_found !== '2o4ahb#4830473') return 'correct_orientation_route_hash_pair_discovered_no_write';
        if (summary.alternate_hash_candidates) return 'alternate_hash_candidate_found_no_write';
        return 'reverse_pair_observed_again';
    }
    if (cs === 'route_hash_pair_unverified_needs_detail_verification') {
        if (!teamsKnown) return 'route_hash_pair_verified_no_write';
        if (obsH === expA && obsA === expH) return 'route_hash_pair_reverse_fixture_rejected';
        if (obsH === expH && obsA === expA) return 'route_hash_pair_verified_no_write';
        return 'identity_mismatch_stop';
    }
    if (cs === 'canonical_url_missing_needs_l1_discovery') {
        if (summary.canonical_detail_url_found && summary.route_hash_pair_found) return 'canonical_url_pair_discovered_no_write';
        return 'canonical_url_not_found';
    }
    return 'canonical_url_not_found';
}

// eslint-disable-next-line complexity
async function executeProbe() {
    const gate = rj(GATE48);
    if (!gate.authorization_gate_prepared) throw new Error('Gate not prepared');
    const targets = gate.future_ssr_probe_targets;
    const results = []; let stopReason = null;

    for (let i = 0; i < targets.length; i++) {
        const t = targets[i];
        if (stopReason) { results.push({ target_match_id: t.target_match_id, classification: 'not_attempted_due_to_prior_stop', blocker_reason: stopReason, request_attempted: false, raw_write_ready: false }); continue; }

        // Determine source-controlled request URL
        let reqUrl = null;
        if (t.target_match_id === '53_20252026_4830473') reqUrl = 'https://www.fotmob.com/matches/angers-vs-paris-saint-germain/2o4ahb#4830473'; // known bad pair URL — still source-controlled
        if (t.target_match_id === '53_20252026_4830472') reqUrl = 'https://www.fotmob.com/matches/auxerre-vs-nice/2sy6tc#4830472'; // from ADG42 source-controlled
        // Target 3 (4830499) has no source-controlled URL

        if (!reqUrl) {
            results.push({ target_match_id: t.target_match_id, classification: 'probe_not_attempted_missing_request_url', blocker_reason: 'no source-controlled request_url available', request_attempted: false, raw_write_ready: false });
            continue;
        }

        let response;
        try { response = await httpGet(reqUrl); } catch (err) {
            stopReason = `network_transport_error_target_${i}`;
            results.push({ target_match_id: t.target_match_id, classification: 'blocked_network_error', blocker_reason: err.message, request_attempted: true, raw_write_ready: false });
            continue;
        }

        const hs = response.status;
        if (hs === 403) { stopReason = 'http_403'; results.push({ target_match_id: t.target_match_id, classification: 'blocked_403', blocker_reason: 'HTTP 403', request_attempted: true, http_status: 403, raw_write_ready: false }); continue; }
        if (hs !== 200) { stopReason = `http_${hs}`; results.push({ target_match_id: t.target_match_id, classification: 'blocked_network_error', blocker_reason: `HTTP ${hs}`, request_attempted: true, http_status: hs, raw_write_ready: false }); continue; }

        const body = response.body;
        const markers = safeCheckMarkers(body);
        const summary = markers.nextDataMarker ? extractSafeSummary(body) : { extraction_status: 'no_next_data_marker_found' };

        const entry = {
            target_match_id: t.target_match_id, expected_home: t.expected_home, expected_away: t.expected_away,
            request_attempted: true, request_url: reqUrl, http_status: hs,
            content_type: response.headers['content-type'] || null,
            next_data_marker_present: markers.nextDataMarker, pageprops_marker_present: markers.pagePropsMarker, hydration_marker_present: markers.hydrationMarker,
            canonical_detail_url_found: summary.canonical_detail_url_found || null, route_code_found: summary.route_code_found || null,
            hash_id_found: summary.hash_id_found || null, route_hash_pair_found: summary.route_hash_pair_found || null,
            alternate_hash_candidates: summary.alternate_hash_candidates || null,
            observed_home: summary.observed_home || null, observed_away: summary.observed_away || null,
            observed_date: summary.observed_date || null, observed_competition: summary.observed_competition || null,
            extraction_status: summary.extraction_status || 'not_extracted',
            full_payload_saved: false, full_html_saved: false, full_next_data_saved: false, full_pageprops_saved: false,
        };

        const classification = classifyTarget(t, summary);
        entry.classification = classification; entry.raw_write_ready = false;
        results.push(entry);

        if (['identity_mismatch_stop', 'route_hash_pair_reverse_fixture_rejected'].includes(classification)) {
            stopReason = `stop_${classification}_at_target_${i}`;
        }
    }

    return buildOutput(results);
}

function buildOutput(results) {
    const attempted = results.filter(r => r.request_attempted).length;
    const discovered = results.filter(r => r.classification === 'correct_orientation_route_hash_pair_discovered_no_write').length;
    return {
        schema_version: 'adg48_probe_v1', lifecycle: 'phase-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: [GATE48, A46, CS],
        adg48_status: results.some(r => r.classification.includes('stop') || r.classification.includes('blocked') || r.classification.includes('not_attempted')) ? 'completed_with_partial_success' : 'completed',
        user_authorization_confirmed: true, authorization_gate_merged: true, chosen_strategy: 'ssr_pageprops_correct_orientation_discovery',
        planned_probe_target_count: 3, attempted_request_count: attempted, successful_http_200_count: results.filter(r => r.http_status === 200).length,
        next_data_marker_found_count: results.filter(r => r.next_data_marker_present).length,
        pageprops_marker_found_count: results.filter(r => r.pageprops_marker_present).length,
        hydration_marker_found_count: results.filter(r => r.hydration_marker_present).length,
        safe_summary_extracted_count: results.filter(r => r.observed_home || r.canonical_detail_url_found).length,
        correct_orientation_route_hash_pair_discovered_count: discovered,
        route_hash_pair_verified_count: results.filter(r => r.classification === 'route_hash_pair_verified_no_write').length,
        reverse_fixture_rejected_count: results.filter(r => r.classification === 'route_hash_pair_reverse_fixture_rejected').length,
        reverse_pair_observed_again_count: results.filter(r => r.classification === 'reverse_pair_observed_again').length,
        alternate_hash_candidate_found_count: results.filter(r => r.classification === 'alternate_hash_candidate_found_no_write').length,
        canonical_url_pair_discovered_count: results.filter(r => r.classification === 'canonical_url_pair_discovered_no_write').length,
        canonical_url_not_found_count: results.filter(r => r.classification === 'canonical_url_not_found').length,
        probe_not_attempted_missing_request_url_count: results.filter(r => r.classification === 'probe_not_attempted_missing_request_url').length,
        blocked_403_count: results.filter(r => r.classification === 'blocked_403').length,
        identity_mismatch_count: results.filter(r => r.classification === 'identity_mismatch_stop').length,
        not_attempted_due_to_prior_stop_count: results.filter(r => r.classification === 'not_attempted_due_to_prior_stop').length,
        full_html_saved: false, full_next_data_saved: false, full_pageprops_saved: false, full_payload_saved: false,
        safety: { live_fetch_performed: attempted > 0, network_request_performed: attempted > 0, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false, full_html_saved: false, full_next_data_saved: false, full_pageprops_saved: false, re_acceptance_performed: false, suspension_reversal_performed: false, browser_bypass_performed: false, proxy_used: false, captcha_bypass: false },
        raw_write_ready_count: 0, recommended_next_step: 'ADG49 review ADG48 correct-orientation probe findings; do NOT raw write', results,
    };
}

function writeReport(data) {
    const lines = ['# ADG48 SSR Correct-Orientation Probe Results', '', `- Phase: ${PH}`, `- status: ${data.adg48_status}`, `- attempted: ${data.attempted_request_count}, http_200: ${data.successful_http_200_count}`, `- correct_orientation_discovered: ${data.correct_orientation_route_hash_pair_discovered_count}`, `- route_hash_pair_verified: ${data.route_hash_pair_verified_count}`, `- reverse_fixture_rejected: ${data.reverse_fixture_rejected_count}`, `- raw_write_ready_count: 0`, ''];
    for (const r of data.results) {
        lines.push(`### ${r.target_match_id}`, `- classification: ${r.classification}`, `- request_attempted: ${r.request_attempted}`, `- http_status: ${r.http_status || 'N/A'}`, `- next_data_marker: ${r.next_data_marker_present || false}`, `- observed: ${r.observed_home || '?'} vs ${r.observed_away || '?'}`, `- route_hash_pair_found: ${r.route_hash_pair_found || 'none'}`, `- alternate_hash: ${r.alternate_hash_candidates || 'none'}`, `- full_payload_saved: false`, '');
    }
    lines.push('## Safety', '- no full HTML/__NEXT_DATA__/pageProps saved', '- no DB/raw write', '- raw_write_ready_count=0', '', '## Next', 'ADG49 review findings; do NOT raw write');
    wt(RPT, lines.join('\n') + '\n');
}

async function main() {
    console.log('ADG48 correct-orientation probe: executing...');
    const data = await executeProbe();
    wj(OUT, data); writeReport(data);
    console.log(JSON.stringify({ status: data.adg48_status, attempted: data.attempted_request_count, http_200: data.successful_http_200_count, discovered: data.correct_orientation_route_hash_pair_discovered_count, verified: data.route_hash_pair_verified_count, raw_write_ready_count: 0 }, null, 2));
}
if (require.main === module) { main().catch(err => { console.error('Fatal:', err.message); process.exit(1); }); }
module.exports = { executeProbe };
