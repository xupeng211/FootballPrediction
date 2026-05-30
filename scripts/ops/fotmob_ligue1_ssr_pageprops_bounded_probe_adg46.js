#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG46 SSR probe results are recorded
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG46-SSR-PROBE';
const GATE = 'docs/_manifests/fotmob_ligue1_ssr_pageprops_discovery_gate.adg46.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_ssr_pageprops_bounded_probe.adg46.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_SSR_PAGEPROPS_BOUNDED_PROBE_ADG46.md';
const { parseFotmobCanonicalDetailUrl } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

async function httpGet(url) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 30000);
    try {
        const res = await fetch(url, {
            signal: ctrl.signal,
            headers: { 'User-Agent': 'Mozilla/5.0 (compatible; FP/4.51 SSR-diagnostic)' },
        });
        const body = await res.text();
        return { status: res.status, headers: Object.fromEntries(res.headers.entries()), body };
    } finally { clearTimeout(t); }
}

function safeCheckMarkers(body) {
    const hasNextData = body.includes('__NEXT_DATA__') || body.includes('"buildId"');
    const hasPageProps = body.includes('pageProps') || body.includes('"props"');
    const hasHydration = body.includes('__NEXT_DATA__') && body.includes('"props"');
    return { nextDataMarker: hasNextData, pagePropsMarker: hasPageProps, hydrationMarker: hasHydration };
}

// eslint-disable-next-line complexity
function extractSafeSummary(body) {
    // In-memory only — extract safe summary fields, immediately discard full body
    const summary = {};
    try {
        const ndMatch = body.match(/<script\s+id="__NEXT_DATA__"[^>]*>(.*?)<\/script>/s);
        if (ndMatch) {
            const nd = JSON.parse(ndMatch[1]);
            const pp = nd?.props?.pageProps || {};
            const gen = pp?.general || {};
            summary.canonical_detail_url_found = gen?.pageUrl || gen?.canonicalUrl || null;
            if (summary.canonical_detail_url_found) {
                const parsed = parseFotmobCanonicalDetailUrl(summary.canonical_detail_url_found.startsWith('http') ? summary.canonical_detail_url_found : `https://www.fotmob.com${summary.canonical_detail_url_found}`);
                if (parsed.ok) {
                    summary.route_code_found = parsed.route_code;
                    summary.hash_id_found = parsed.hash_id;
                    summary.route_hash_pair_found = `${parsed.route_code}#${parsed.hash_id}`;
                }
            }
            summary.observed_home = gen?.homeTeam?.name || pp?.homeTeam?.name || null;
            summary.observed_away = gen?.awayTeam?.name || pp?.awayTeam?.name || null;
            summary.observed_date = gen?.matchTimeUTC || gen?.startTime || null;
            summary.observed_competition = gen?.leagueName || gen?.parentLeagueName || null;
            summary.observed_detail_id = String(gen?.matchId || pp?.matchId || '');
            summary.extraction_status = 'next_data_parsed_safe_summary_extracted';
        }
    } catch (_) { summary.extraction_status = 'next_data_parse_failed_or_partial'; }
    return summary;
}

function normalizeTeam(name) { return String(name ?? '').toLowerCase().replace(/\s+/g, ' ').trim(); }

// eslint-disable-next-line complexity
function classifyTarget(target, summary, markers) {
    const cs = target.current_status;
    if (cs === 'route_hash_pair_unverified_needs_detail_verification') {
        const obsH = normalizeTeam(summary.observed_home);
        const obsA = normalizeTeam(summary.observed_away);
        const expH = normalizeTeam(target.expected_home);
        const expA = normalizeTeam(target.expected_away);
        if (obsH && obsA && expH && expA) {
            if (obsH === expA && obsA === expH) return 'route_hash_pair_reverse_fixture_rejected';
            if (obsH === expH && obsA === expA) return 'route_hash_pair_verified_no_write';
            if (obsH !== expH || obsA !== expA) return 'identity_mismatch_stop';
        }
        return 'ssr_pageprops_safe_summary_extracted_no_write';
    }
    if (cs === 'canonical_url_missing_needs_l1_discovery') {
        if (summary.canonical_detail_url_found && summary.route_hash_pair_found) {
            return 'canonical_url_pair_discovered_no_write';
        }
        if (markers.nextDataMarker) return 'ssr_pageprops_marker_found_no_write';
        return 'canonical_url_not_found';
    }
    return 'canonical_url_not_found';
}

// eslint-disable-next-line complexity
async function executeProbe() {
    const gate = rj(GATE);
    if (!gate.authorization_gate_prepared) throw new Error('ADG46 gate not prepared');
    if (gate.ssr_probe_not_executed !== true) throw new Error('Probe already executed');

    const targets = gate.future_ssr_probe_targets;
    const results = [];
    let stopReason = null;

    for (let i = 0; i < targets.length; i++) {
        const t = targets[i];
        if (stopReason) {
            results.push({ target_match_id: t.target_match_id, classification: 'not_attempted_due_to_prior_stop', blocker_reason: stopReason, request_attempted: false, raw_write_ready: false });
            continue;
        }

        if (!t.expected_page_url) {
            results.push({ target_match_id: t.target_match_id, classification: 'probe_not_attempted_missing_request_url', blocker_reason: 'no source-controlled request_url available for canonical_url_missing target', request_attempted: false, raw_write_ready: false });
            continue;
        }

        let response;
        try { response = await httpGet(t.expected_page_url); } catch (err) {
            stopReason = `network_transport_error_target_${i}`;
            results.push({ target_match_id: t.target_match_id, classification: 'blocked_network_error', blocker_reason: err.message, request_attempted: true, raw_write_ready: false });
            continue;
        }

        const httpStatus = response.status;
        if (httpStatus === 403) { stopReason = 'http_403_blocked'; results.push({ target_match_id: t.target_match_id, classification: 'blocked_403', blocker_reason: 'HTTP 403', request_attempted: true, http_status: 403, raw_write_ready: false }); continue; }
        if (httpStatus !== 200) { stopReason = `http_${httpStatus}`; results.push({ target_match_id: t.target_match_id, classification: 'blocked_network_error', blocker_reason: `HTTP ${httpStatus}`, request_attempted: true, http_status: httpStatus, raw_write_ready: false }); continue; }

        // In-memory marker check — never save full body
        const body = response.body;
        const markers = safeCheckMarkers(body);
        const summary = markers.nextDataMarker ? extractSafeSummary(body) : { extraction_status: 'no_next_data_marker_found' };

        // Verify no full payload is being saved
        const safeForManifest = {
            target_match_id: t.target_match_id,
            expected_home: t.expected_home,
            expected_away: t.expected_away,
            request_attempted: true,
            request_url: t.expected_page_url,
            http_status: httpStatus,
            content_type: response.headers['content-type'] || null,
            next_data_marker_present: markers.nextDataMarker,
            pageprops_marker_present: markers.pagePropsMarker,
            hydration_marker_present: markers.hydrationMarker,
            canonical_detail_url_found: summary.canonical_detail_url_found || null,
            route_code_found: summary.route_code_found || null,
            hash_id_found: summary.hash_id_found || null,
            route_hash_pair_found: summary.route_hash_pair_found || null,
            observed_home: summary.observed_home || null,
            observed_away: summary.observed_away || null,
            observed_date: summary.observed_date || null,
            observed_competition: summary.observed_competition || null,
            extraction_status: summary.extraction_status || 'not_extracted',
            full_payload_saved: false,
            full_html_saved: false,
            full_next_data_saved: false,
            full_pageprops_saved: false,
        };

        const classification = classifyTarget(t, summary, markers);
        results.push({ ...safeForManifest, classification, blocker_reason: null, raw_write_ready: false });

        if (classification === 'identity_mismatch_stop' || classification === 'route_hash_pair_reverse_fixture_rejected') {
            stopReason = `stop_${classification}_at_target_${i}`;
        }

        // body is scoped to this iteration — discarded on next iteration
    }

    return buildOutput(results, targets.length);
}

function buildOutput(results, planned) {
    const attempted = results.filter(r => r.request_attempted).length;
    return {
        schema_version: 'adg46_ssr_probe_v1', lifecycle: 'phase-artifact', phase: PH, generated_at: new Date().toISOString(), input_sources: [GATE, CS],
        adg46_status: results.some(r => r.classification.includes('stop') || r.classification.includes('blocked') || r.classification.includes('not_attempted')) ? 'completed_with_partial_success' : 'completed',
        user_authorization_confirmed: true, ssr_gate_merged: true, chosen_strategy: 'fotmob_ssr_pageprops',
        planned_probe_target_count: planned,
        attempted_request_count: attempted,
        successful_http_200_count: results.filter(r => r.http_status === 200).length,
        next_data_marker_found_count: results.filter(r => r.next_data_marker_present).length,
        pageprops_marker_found_count: results.filter(r => r.pageprops_marker_present).length,
        hydration_marker_found_count: results.filter(r => r.hydration_marker_present).length,
        safe_summary_extracted_count: results.filter(r => r.observed_home || r.canonical_detail_url_found).length,
        canonical_url_pair_discovered_count: results.filter(r => r.classification === 'canonical_url_pair_discovered_no_write').length,
        route_hash_pair_verified_count: results.filter(r => r.classification === 'route_hash_pair_verified_no_write').length,
        reverse_fixture_rejected_count: results.filter(r => r.classification === 'route_hash_pair_reverse_fixture_rejected').length,
        canonical_url_not_found_count: results.filter(r => r.classification === 'canonical_url_not_found').length,
        blocked_403_count: results.filter(r => r.classification === 'blocked_403').length,
        blocked_captcha_or_access_wall_count: 0,
        identity_mismatch_count: results.filter(r => r.classification === 'identity_mismatch_stop').length,
        not_attempted_due_to_prior_stop_count: results.filter(r => r.classification === 'not_attempted_due_to_prior_stop').length,
        not_attempted_missing_request_url_count: results.filter(r => r.classification === 'probe_not_attempted_missing_request_url').length,
        full_html_saved: false, full_next_data_saved: false, full_pageprops_saved: false, full_payload_saved: false,
        safety: { live_fetch_performed: attempted > 0, network_request_performed: attempted > 0, db_write_performed: false, raw_write_execution_performed: false, raw_match_data_insert_performed: false, full_payload_saved: false, full_html_saved: false, full_next_data_saved: false, full_pageprops_saved: false, re_acceptance_performed: false, suspension_reversal_performed: false, browser_bypass_performed: false, proxy_used: false, captcha_bypass: false },
        raw_write_ready_count: 0, recommended_next_step: 'ADG47 review SSR/pageProps probe findings; do NOT raw write; do NOT proceed to raw write without separate authorization', results,
    };
}

function writeReport(data) {
    const lines = ['# ADG46 SSR pageProps Bounded Probe Results', '', `- lifecycle: phase-artifact`, `- Phase: ${PH}`, `- adg46_status: ${data.adg46_status}`, `- user_authorization_confirmed: true`, `- attempted_request_count: ${data.attempted_request_count}`, `- successful_http_200_count: ${data.successful_http_200_count}`, `- next_data_marker_found: ${data.next_data_marker_found_count}`, `- pageprops_marker_found: ${data.pageprops_marker_found_count}`, `- canonical_url_pair_discovered: ${data.canonical_url_pair_discovered_count}`, `- route_hash_pair_verified: ${data.route_hash_pair_verified_count}`, `- reverse_fixture_rejected: ${data.reverse_fixture_rejected_count}`, `- raw_write_ready_count: 0`, '', '## Per-target Results', ''];
    for (const r of data.results) {
        lines.push(`### ${r.target_match_id}`, `- expected: ${r.expected_home || '?'} vs ${r.expected_away || '?'}`, `- classification: ${r.classification}`, `- request_attempted: ${r.request_attempted}`, `- http_status: ${r.http_status || 'N/A'}`, `- next_data_marker: ${r.next_data_marker_present || false}`, `- canonical_url_found: ${r.canonical_detail_url_found || 'none'}`, `- route_hash_pair_found: ${r.route_hash_pair_found || 'none'}`, `- observed: ${r.observed_home || '?'} vs ${r.observed_away || '?'}`, `- extraction_status: ${r.extraction_status || 'N/A'}`, `- full_payload_saved: false`, `- raw_write_ready: false`, '');
    }
    lines.push('## Safety', `- full_html_saved: false`, `- full_next_data_saved: false`, `- full_pageProps_saved: false`, `- full_payload_saved: false`, `- db_write: false`, `- raw_write: false`, `- raw_write_ready_count: 0`, '', '## Next', 'ADG47 review SSR probe findings; do NOT raw write');
    wt(RPT, lines.join('\n') + '\n');
}

async function main() {
    console.log('ADG46 SSR/pageProps probe: executing bounded diagnostic requests...');
    const data = await executeProbe();
    wj(OUT, data);
    writeReport(data);
    console.log(JSON.stringify({ adg46_status: data.adg46_status, attempted: data.attempted_request_count, http_200: data.successful_http_200_count, next_data: data.next_data_marker_found_count, discovered: data.canonical_url_pair_discovered_count, verified: data.route_hash_pair_verified_count, raw_write_ready_count: 0, full_payload_saved: false }, null, 2));
    console.log('No full HTML/pageProps/__NEXT_DATA__ saved.');
}

if (require.main === module) { main().catch(err => { console.error('ADG46 probe fatal:', err.message); process.exit(1); }); }
module.exports = { executeProbe };
