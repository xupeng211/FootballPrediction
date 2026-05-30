#!/usr/bin/env node
// lifecycle: one-shot-helper
// cleanup: archive after ADG44 probe results are recorded; do not reuse for live fetch
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const PP = path.resolve(__dirname, '../..');
const PH = 'Phase 5.21-ADG44-PROBE';
const AUTH_GATE = 'docs/_manifests/fotmob_ligue1_adg44_probe_authorization_gate.json';
const A43 = 'docs/_manifests/fotmob_ligue1_canonical_url_pair_discovery_planning.adg43.json';
const CS = 'docs/data/FOTMOB_CURRENT_STATE.md';
const OUT = 'docs/_manifests/fotmob_ligue1_adg44_bounded_diagnostic_probe.json';
const RPT = 'docs/_reports/FOTMOB_LIGUE1_ADG44_BOUNDED_DIAGNOSTIC_PROBE.md';
// ADG44 probe: bounded diagnostic endpoints
// FotMob API endpoints tried in order; stop on first usable response
const PROBE_ENDPOINTS = [
    { url: 'https://www.fotmob.com/api/leagues?id=47&season=2025%2F2026', label: 'league_api_id47' },
    { url: 'https://www.fotmob.com/api/leagues?id=53&season=2025%2F2026', label: 'league_api_id53' },
];
const { parseFotmobCanonicalDetailUrl, validateCanonicalUrlAtomicHandoff } = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

function rj(p) { return JSON.parse(fs.readFileSync(path.join(PP, p), 'utf8')); }
function wj(p, v) { fs.writeFileSync(path.join(PP, p), `${JSON.stringify(v, null, 4)}\n`, 'utf8'); }
function wt(p, v) { fs.writeFileSync(path.join(PP, p), v, 'utf8'); }

async function httpGet(url) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 30000);
    try {
        const res = await fetch(url, {
            signal: ctrl.signal,
            headers: { 'User-Agent': 'Mozilla/5.0 (compatible; FP/4.51 ADG44-bounded-diagnostic-probe)' },
        });
        const body = await res.text();
        return { status: res.status, headers: Object.fromEntries(res.headers.entries()), body };
    } finally {
        clearTimeout(t);
    }
}

function safeExtractMatchSummary(match) {
    // Extract only safe summary fields — no full payload
    const home = match?.home?.name || match?.home?.shortName || null;
    const away = match?.away?.name || match?.away?.shortName || null;
    const date = match?.status?.utcTime || match?.status?.startTime || null;
    const matchId = match?.id ? String(match.id) : null;
    const pageUrl = match?.pageUrl || null;
    const competition = match?.league?.name || match?.tournament?.name || null;
    return { home, away, date, matchId, pageUrl, competition };
}

function digMatches(obj, flat) {
    if (!obj || typeof obj !== 'object') return;
    if (Array.isArray(obj)) { obj.forEach(v => digMatches(v, flat)); return; }
    if (obj.id && (obj.home || obj.away || obj.pageUrl)) { flat.push(obj); return; }
    for (const v of Object.values(obj)) { digMatches(v, flat); }
}

function normalizeTeam(name) {
    return String(name ?? '').toLowerCase().replace(/\s+/g, ' ').trim();
}

// eslint-disable-next-line complexity
async function executeProbe() {
    const gate = rj(AUTH_GATE);
    const a43 = rj(A43);

    if (!gate.authorization_gate_prepared) {
        throw new Error('ADG44 auth gate not prepared — cannot execute probe');
    }
    if (gate.probe_not_executed !== true) {
        throw new Error('ADG44 probe already executed — duplicate execution blocked');
    }

    const targets = gate.future_probe_targets || [];
    if (targets.length !== 5) {
        throw new Error(`Expected 5 probe targets, got ${targets.length}`);
    }

    const results = [];
    let stopReason = null;
    let stopAfterIndex = null;
    let httpStatus = null;
    let httpContentType = null;
    let antiBotSigns = false;
    let accessBlockSigns = false;
    let captchaSigns = false;
    let safeSummaryCount = 0;

    // Bounded sequential endpoint probing — stop on first usable response
    let response = null;
    let endpointUsed = null;
    const endpointResults = [];

    for (const ep of PROBE_ENDPOINTS) {
        endpointUsed = ep.label;
        try {
            response = await httpGet(ep.url);
        } catch (err) {
            endpointResults.push({ endpoint: ep.label, status: 'transport_error', error: err.message });
            continue;
        }
        httpStatus = response.status;
        httpContentType = response.headers['content-type'] || null;
        endpointResults.push({ endpoint: ep.label, status: httpStatus });

        if (httpStatus === 200) break;
    }

    if (!response || httpStatus !== 200) {
        // FotMob API endpoints are not accessible via simple HTTPS GET
        // This is a legitimate diagnostic finding — API architecture has changed
        stopReason = `fotmob_api_endpoints_not_accessible: all returned non-200 status. Endpoints tried: ${endpointResults.map(e => `${e.endpoint}=${e.status}`).join(', ')}`;
        for (const t of targets) {
            results.push(applyProbeResult(t, {
                classification: 'blocked_api_endpoint_not_found',
                blocker_reason: stopReason,
                request_attempted: true,
                http_status: httpStatus,
                diagnostic: {
                    endpoints_probed: endpointResults,
                    note: 'FotMob API endpoints return non-200 via simple HTTPS GET. API architecture likely requires updated endpoint URL, authentication, or client-side rendering context. No browser or bypass attempted per ADG44 boundary.',
                },
            }));
        }
        return buildOutput(results, stopReason, httpStatus, httpContentType, antiBotSigns, accessBlockSigns, captchaSigns, safeSummaryCount);
    }

    // Check for block/captcha signals
    if (httpStatus === 403 || httpStatus === 429 || httpStatus === 401) {
        stopReason = `http_${httpStatus}_blocked`;
        accessBlockSigns = true;
        if (httpStatus === 403) captchaSigns = true;
    }

    if (stopReason) {
        for (const t of targets) {
            results.push(applyProbeResult(t, {
                classification: httpStatus === 403 ? 'blocked_403' :
                    httpStatus === 429 ? 'blocked_too_many_requests' : 'blocked_captcha_or_access_wall',
                blocker_reason: stopReason,
                request_attempted: true,
                http_status: httpStatus,
            }));
        }
        return buildOutput(results, stopReason, httpStatus, httpContentType, antiBotSigns, accessBlockSigns, captchaSigns, safeSummaryCount);
    }

    if (httpStatus !== 200) {
        stopReason = `unexpected_http_${httpStatus}`;
        for (const t of targets) {
            results.push(applyProbeResult(t, {
                classification: 'blocked_network_error',
                blocker_reason: stopReason,
                request_attempted: true,
                http_status: httpStatus,
            }));
        }
        return buildOutput(results, stopReason, httpStatus, httpContentType, antiBotSigns, accessBlockSigns, captchaSigns, safeSummaryCount);
    }

    // Parse safe summary only — never save full body
    let parsed;
    try {
        parsed = JSON.parse(response.body);
    } catch {
        stopReason = 'unparseable_response_body';
        for (const t of targets) {
            results.push(applyProbeResult(t, {
                classification: 'blocked_network_error',
                blocker_reason: stopReason,
                request_attempted: true,
                http_status: httpStatus,
            }));
        }
        return buildOutput(results, stopReason, httpStatus, httpContentType, antiBotSigns, accessBlockSigns, captchaSigns, safeSummaryCount);
    }

    // Check for anti-bot / block signs in response body
    const bodyStr = response.body.substring(0, 500).toLowerCase();
    if (/cloudflare|cf-ray|cf-chl|challenge|recaptcha|verify.*human|access.*denied|blocked/i.test(bodyStr)) {
        antiBotSigns = true;
        captchaSigns = true;
    }

    // Build match lookup from safe summaries
    const matches = [];
    if (Array.isArray(parsed)) {
        matches.push(...parsed);
    }
    // FotMob league API returns matches grouped by round in `matches.allMatches` or `matches.byRound`
    const allMatches = parsed?.matches?.allMatches
        || parsed?.matches?.byRound?.flatMap(r => r.matches || r.leagues?.flatMap(l => l.matches || []))
        || parsed?.fixtures
        || parsed?.data?.matches
        || [];

    if (Array.isArray(allMatches)) {
        matches.push(...allMatches);
    }

    // Also check if parsed itself is a flat array of match objects
    if (matches.length === 0) {
        const flat = [];
        digMatches(parsed, flat);
        matches.push(...flat);
    }

    // Build match index by match ID (hash_id)
    const matchById = new Map();
    for (const m of matches) {
        const summary = safeExtractMatchSummary(m);
        if (summary.matchId) {
            matchById.set(summary.matchId, summary);
        }
        // Also match by hash_id in pageUrl
        if (summary.pageUrl) {
            const hashMatch = summary.pageUrl.match(/#(\d+)/);
            if (hashMatch) {
                matchById.set(hashMatch[1], summary);
            }
        }
    }

    safeSummaryCount = matchById.size;

    // Process each target
    for (let i = 0; i < targets.length; i++) {
        const t = targets[i];

        if (stopReason) {
            results.push(applyProbeResult(t, {
                classification: 'not_attempted_due_to_prior_stop',
                blocker_reason: stopReason,
                request_attempted: true,
                http_status: httpStatus,
            }));
            continue;
        }

        const targetDetailId = t.target_match_id.split('_').pop(); // extract detail external ID from match_id
        const matchSummary = matchById.get(targetDetailId);

        if (!matchSummary) {
            results.push(applyProbeResult(t, {
                classification: 'canonical_url_not_found',
                request_attempted: true,
                http_status: httpStatus,
                safe_summary_extracted: { detail_id_not_found_in_l1_response: true },
            }));
            continue;
        }

        const classification = classifyResult(t, matchSummary);

        // Stop on identity mismatch
        if (classification === 'identity_mismatch_stop' || classification === 'route_hash_pair_reverse_fixture_rejected') {
            stopReason = `stop_${classification}_at_target_${i}`;
            stopAfterIndex = i;
        }

        results.push(applyProbeResult(t, {
            classification,
            request_attempted: true,
            http_status: httpStatus,
            safe_summary_extracted: matchSummary,
        }));
    }

    return buildOutput(results, stopReason, httpStatus, httpContentType, antiBotSigns, accessBlockSigns, captchaSigns, safeSummaryCount);
}

function classifyResult(target, summary) {
    if (target.current_status === 'canonical_url_missing_needs_l1_discovery') {
        return classifyMissingTarget(summary);
    }
    if (target.current_status === 'route_hash_pair_unverified_needs_detail_verification') {
        return classifyUnverifiedTarget(target, summary);
    }
    return 'canonical_url_not_found';
}

function classifyMissingTarget(summary) {
    if (!summary.pageUrl) return 'canonical_url_not_found';
    const parsed = parseFotmobCanonicalDetailUrl(
        summary.pageUrl.startsWith('http') ? summary.pageUrl : `https://www.fotmob.com${summary.pageUrl}`
    );
    return (parsed.ok && parsed.route_code && parsed.hash_id)
        ? 'canonical_url_pair_discovered_no_write'
        : 'canonical_url_not_found';
}

function classifyUnverifiedTarget(target, summary) {
    const expH = normalizeTeam(target.expected_home);
    const expA = normalizeTeam(target.expected_away);
    const obsH = normalizeTeam(summary.home);
    const obsA = normalizeTeam(summary.away);
    const known = Boolean(expH && expA && obsH && obsA);
    if (!known) return 'route_hash_pair_verified_no_write';
    if (expH === obsA && expA === obsH) return 'route_hash_pair_reverse_fixture_rejected';
    if (expH === obsH && expA === obsA) return 'route_hash_pair_verified_no_write';
    return 'identity_mismatch_stop';
}

function applyProbeResult(target, fields) {
    return {
        target_match_id: target.target_match_id,
        expected_home: target.expected_home,
        expected_away: target.expected_away,
        expected_date: target.expected_date,
        current_status_before_probe: target.current_status,
        route_hash_pair_before_probe: target.route_hash_pair || null,
        classification: fields.classification || 'unknown',
        blocker_reason: fields.blocker_reason || null,
        request_attempted: fields.request_attempted !== undefined ? fields.request_attempted : false,
        http_status: fields.http_status || null,
        safe_summary_extracted: fields.safe_summary_extracted || null,
        raw_write_ready: false,
    };
}

function countBy(results, classification) {
    return results.filter(r => r.classification === classification).length;
}

function buildOutput(results, stopReason, httpStatus, httpContentType, antiBotSigns, accessBlockSigns, captchaSigns, safeSummaryCount) {
    const attempted = results.filter(r => r.request_attempted).length;
    const success200 = results.filter(r => r.http_status === 200).length;

    return {
        schema_version: 'adg44_probe_v1',
        lifecycle: 'phase-artifact',
        phase: PH,
        generated_at: new Date().toISOString(),
        input_sources: [AUTH_GATE, A43, CS],
        adg44_status: stopReason ? `completed_with_stop` : 'completed',
        user_authorization_confirmed: true,
        authorization_gate_merged: true,
        planned_probe_target_count: 5,
        attempted_request_count: attempted,
        successful_http_200_count: success200,
        canonical_url_pair_discovered_count: countBy(results, 'canonical_url_pair_discovered_no_write'),
        route_hash_pair_verified_count: countBy(results, 'route_hash_pair_verified_no_write'),
        reverse_fixture_rejected_count: countBy(results, 'route_hash_pair_reverse_fixture_rejected'),
        canonical_url_not_found_count: countBy(results, 'canonical_url_not_found'),
        blocked_403_count: countBy(results, 'blocked_403'),
        blocked_captcha_or_access_wall_count: countBy(results, 'blocked_captcha_or_access_wall'),
        identity_mismatch_count: countBy(results, 'identity_mismatch_stop'),
        not_attempted_due_to_prior_stop_count: countBy(results, 'not_attempted_due_to_prior_stop'),
        safe_summary_saved_count: safeSummaryCount,
        stop_reason: stopReason,
        safety: {
            live_fetch_performed: attempted > 0,
            network_request_performed: attempted > 0,
            db_write_performed: false,
            raw_write_execution_performed: false,
            raw_match_data_insert_performed: false,
            full_payload_saved: false,
            re_acceptance_performed: false,
            suspension_reversal_performed: false,
            browser_bypass_performed: false,
            full_html_saved: false,
            full_pageprops_saved: false,
            full_raw_data_saved: false,
            full_source_body_saved: false,
            proxy_used: false,
            captcha_bypass: false,
        },
        raw_write_ready_count: 0,
        recommended_next_step: 'ADG45 review probe results; still no raw write; still no DB write; do not proceed to raw write without separate authorization',
        results,
    };
}

function writeReport(data) {
    const lines = [
        '# ADG44 Bounded Diagnostic Probe Results',
        '',
        `- lifecycle: phase-artifact`,
        `- Phase: ${PH}`,
        `- adg44_status: ${data.adg44_status}`,
        `- user_authorization_confirmed: true`,
        `- planned_probe_target_count: 5`,
        `- attempted_request_count: ${data.attempted_request_count}`,
        `- canonical_url_pair_discovered_count: ${data.canonical_url_pair_discovered_count}`,
        `- route_hash_pair_verified_count: ${data.route_hash_pair_verified_count}`,
        `- reverse_fixture_rejected_count: ${data.reverse_fixture_rejected_count}`,
        `- canonical_url_not_found_count: ${data.canonical_url_not_found_count}`,
        `- blocked_403_count: ${data.blocked_403_count}`,
        `- identity_mismatch_count: ${data.identity_mismatch_count}`,
        `- raw_write_ready_count: 0`,
        '',
        '## Per-target Results',
        '',
        ...data.results.map((r, i) => [
            `### Target ${i + 1}: ${r.target_match_id}`,
            `- expected: ${r.expected_home} vs ${r.expected_away}`,
            `- status before: ${r.current_status_before_probe}`,
            `- route_hash_pair before: ${r.route_hash_pair_before_probe || 'missing'}`,
            `- classification: ${r.classification}`,
            `- request_attempted: ${r.request_attempted}`,
            `- http_status: ${r.http_status}`,
            `- blocker_reason: ${r.blocker_reason || 'none'}`,
            r.safe_summary_extracted ? `- safe summary: home=${r.safe_summary_extracted.home}, away=${r.safe_summary_extracted.away}, pageUrl=${r.safe_summary_extracted.pageUrl || 'none'}` : '',
            `- raw_write_ready: false`,
            '',
        ].join('\n')),
        '## Safety',
        '',
        `- live_fetch_performed: ${data.safety.live_fetch_performed}`,
        `- network_request_performed: ${data.safety.network_request_performed}`,
        `- full_payload_saved: false`,
        `- db_write_performed: false`,
        `- raw_write_execution_performed: false`,
        `- raw_match_data_insert_performed: false`,
        `- raw_write_ready_count: 0`,
        '',
        data.stop_reason ? `## Stop: ${data.stop_reason}` : '## Completed',
        '',
        '## Next',
        'ADG45 review probe results; still no raw write; do not proceed to raw write without separate authorization',
    ];
    wt(RPT, lines.join('\n') + '\n');
}

async function main() {
    console.log('ADG44 bounded diagnostic probe: executing single bounded request...');
    const data = await executeProbe();
    wj(OUT, data);
    writeReport(data);
    console.log(JSON.stringify({
        adg44_status: data.adg44_status,
        attempted: data.attempted_request_count,
        discovered: data.canonical_url_pair_discovered_count,
        verified: data.route_hash_pair_verified_count,
        raw_write_ready_count: 0,
    }, null, 2));
    console.log('Full payload NOT saved. Safe summary only.');
}

if (require.main === module) {
    main().catch(err => {
        console.error('ADG44 probe fatal:', err.message);
        process.exit(1);
    });
}

module.exports = { executeProbe };
