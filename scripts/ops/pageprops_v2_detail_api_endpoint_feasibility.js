#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3S';
const PHASE_NAME = 'detail_api_endpoint_feasibility_verification';
const ARTIFACT_STATUS = 'completed_no_write_detail_api_endpoint_feasibility_verification';
const GENERATED_AT = '2026-05-21T00:00:00Z';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const L2V3R_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.detail_url_construction_fix_plan.phase521l2v3r.json';
const L2V3Q_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_metadata_investigation.phase521l2v3q.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.detail_api_endpoint_feasibility.phase521l2v3s.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3S.md';
const NEXT_REQUIRED_STEP = 'continued_detail_endpoint_investigation';
const NEXT_RECOMMENDED_STEP = 'Phase 5.21L2V3T: continued detail endpoint investigation';
const PRECISE_IMPLEMENTATION_STEP = 'precise_detail_request_strategy_implementation';
const PRECISE_IMPLEMENTATION_RECOMMENDATION = 'Phase 5.21L2V3T: precise detail request strategy implementation';
const DIRECT_API_ENDPOINT = 'https://www.fotmob.com/api/data/matchDetails';
const MAX_CONTROLLED_TARGETS = 3;
const BLOCK_SIGNAL_PATTERNS = Object.freeze([
    /captcha/i,
    /cloudflare/i,
    /cf-challenge/i,
    /access denied/i,
    /too many requests/i,
    /rate limit/i,
    /forbidden/i,
]);

const SOURCE_FILES = Object.freeze([
    {
        key: 'fotmob_raw_detail_fetcher',
        path: 'src/infrastructure/services/FotMobRawDetailFetcher.js',
        patterns: ['buildFotMobMatchUrl', 'unsupported route: only html_hydration is supported'],
    },
    {
        key: 'fotmob_api_client',
        path: 'src/infrastructure/network/FotMobApiClient.js',
        patterns: ['/api/data/matchDetails', 'fetchMatchDetails'],
    },
    {
        key: 'l2_raw_detail_preview',
        path: 'scripts/ops/l2_raw_detail_preview.js',
        patterns: ['api/data/matchDetails', 'api_match_details', 'alternate_route'],
    },
    {
        key: 'marathon_service',
        path: 'src/infrastructure/services/MarathonService.js',
        patterns: ['_buildMatchDetailsApiUrls', 'api/data/matchDetails', 'api/matchDetails'],
    },
    {
        key: 'fotmob_strategy',
        path: 'src/infrastructure/harvesters/strategies/FotMobStrategy.js',
        patterns: ['fetchMatchDetails', 'api/data/matchDetails', '_fetchMatchDetailsWithSession'],
    },
    {
        key: 'source_inventory_preflight',
        path: 'scripts/ops/l1_discovery_safe_preview.js',
        patterns: ['api/data/leagues'],
    },
]);

function absolutePath(filePath) {
    if (path.isAbsolute(filePath)) return filePath;
    return path.join(PROJECT_ROOT, filePath);
}

function readTextFile(filePath) {
    return fs.readFileSync(absolutePath(filePath), 'utf8');
}

function readJsonFile(filePath) {
    return JSON.parse(readTextFile(filePath));
}

function writeJsonFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), `${JSON.stringify(value, null, 4)}\n`, 'utf8');
}

function writeTextFile(filePath, value) {
    fs.writeFileSync(absolutePath(filePath), value, 'utf8');
}

function normalizeText(value) {
    return String(value ?? '').trim();
}

function normalizeLower(value) {
    return normalizeText(value).toLowerCase();
}

function normalizeBooleanFlag(value, fallback = false) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const text = normalizeLower(value);
    if (['1', 'true', 'yes', 'y', 'on'].includes(text)) return true;
    if (['0', 'false', 'no', 'n', 'off'].includes(text)) return false;
    return fallback;
}

function parseInteger(value, fallback = null) {
    if (value === null || value === undefined || value === '') return fallback;
    const text = normalizeText(value);
    if (!/^\d+$/.test(text)) return Number.NaN;
    return Number.parseInt(text, 10);
}

function safeNumber(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function getByPath(value, pathExpression) {
    return pathExpression.split('.').reduce((current, key) => {
        if (!isPlainObject(current) && !Array.isArray(current)) return undefined;
        return current[key];
    }, value);
}

function firstText(...values) {
    for (const value of values) {
        const text = normalizeText(value);
        if (text) return text;
    }
    return null;
}

function firstNumericText(...values) {
    const text = firstText(...values);
    return text && /^\d+$/.test(text) ? text : null;
}

function extractTeamName(value) {
    if (isPlainObject(value)) {
        return firstText(value.name, value.shortName, value.fullName, value.longName);
    }
    return firstText(value);
}

function normalizeDateOnly(value) {
    const text = normalizeText(value);
    if (!text) return null;
    const parsed = new Date(text);
    if (!Number.isNaN(parsed.getTime())) return parsed.toISOString().slice(0, 10);
    return text.match(/\d{4}-\d{2}-\d{2}/)?.[0] || null;
}

function buildDetailApiUrl(externalId) {
    const id = normalizeText(externalId);
    if (!/^\d+$/.test(id)) {
        throw new Error(`INVALID_EXTERNAL_ID:${externalId}`);
    }
    const url = new URL(DIRECT_API_ENDPOINT);
    url.searchParams.set('matchId', id);
    return url.href;
}

function buildDetailApiRequest(target = {}) {
    const externalId = normalizeText(target.external_id || target.schedule_external_id);
    const requestUrl = buildDetailApiUrl(externalId);
    return {
        route: 'api_match_details',
        method: 'GET',
        url: requestUrl,
        endpoint_path: '/api/data/matchDetails?matchId={externalId}',
        headers: {
            accept: 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'identity',
            referer: `https://www.fotmob.com/match/${externalId}`,
            'user-agent':
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        },
    };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        controlledLiveCheck: false,
        networkAuthorization: false,
        maxTargets: MAX_CONTROLLED_TARGETS,
        writeFiles: true,
        help: false,
        unknown: [],
    };
    const keyMap = {
        'controlled-live-check': 'controlledLiveCheck',
        controlled_live_check: 'controlledLiveCheck',
        'network-authorization': 'networkAuthorization',
        network_authorization: 'networkAuthorization',
        'max-targets': 'maxTargets',
        max_targets: 'maxTargets',
        'write-files': 'writeFiles',
        write_files: 'writeFiles',
        help: 'help',
        h: 'help',
    };

    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }
        const key = arg.replace(/^--/, '').split('=')[0];
        const mapped = keyMap[key];
        if (!mapped) {
            options.unknown.push(key);
            continue;
        }
        const value = arg.includes('=')
            ? arg.slice(arg.indexOf('=') + 1)
            : argv[index + 1] && !String(argv[index + 1]).startsWith('--')
              ? argv[++index]
              : true;
        if (['controlledLiveCheck', 'networkAuthorization', 'writeFiles', 'help'].includes(mapped)) {
            options[mapped] = normalizeBooleanFlag(value, true);
        } else {
            options[mapped] = parseInteger(value, options[mapped]);
        }
    }

    return options;
}

function validateCliOptions(options = {}) {
    const errors = [];
    if (Array.isArray(options.unknown) && options.unknown.length > 0) {
        errors.push(`unknown arguments: ${options.unknown.join(', ')}`);
    }
    if (options.controlledLiveCheck === true && options.networkAuthorization !== true) {
        errors.push('network-authorization=yes is required for controlled live endpoint check');
    }
    if (
        !Number.isInteger(options.maxTargets) ||
        options.maxTargets < 0 ||
        options.maxTargets > MAX_CONTROLLED_TARGETS
    ) {
        errors.push(`max-targets must be between 0 and ${MAX_CONTROLLED_TARGETS}`);
    }
    return { ok: errors.length === 0, errors };
}

function sourceTextFor(item, dependencies = {}) {
    if (
        dependencies.sourceTextByPath &&
        Object.prototype.hasOwnProperty.call(dependencies.sourceTextByPath, item.path)
    ) {
        return dependencies.sourceTextByPath[item.path];
    }
    return readTextFile(item.path);
}

function analyzeSourceFiles(sourceFiles = SOURCE_FILES, dependencies = {}) {
    return sourceFiles.map(item => {
        const text = sourceTextFor(item, dependencies);
        const matched_patterns = item.patterns.filter(pattern => text.includes(pattern));
        return {
            key: item.key,
            path: item.path,
            matched_patterns,
            matched_pattern_count: matched_patterns.length,
            evidence_found: matched_patterns.length === item.patterns.length,
        };
    });
}

function buildEndpointInventory(sourceFileAnalysis = []) {
    const hasEvidence = key => sourceFileAnalysis.some(item => item.key === key && item.evidence_found === true);
    return [
        {
            endpoint_key: 'league_schedule_source_inventory',
            route_candidate: '/api/data/leagues?id={leagueId}&season={season}',
            endpoint_type: 'schedule_inventory',
            code_evidence_found: hasEvidence('source_inventory_preflight'),
            precise_detail_candidate: false,
            current_pageprops_detail_usage: false,
            safe_conclusion: 'available_for_target_inventory_not_detail_payload_identity',
        },
        {
            endpoint_key: 'html_match_external_id_route',
            route_candidate: '/match/{externalId}',
            endpoint_type: 'html_detail_route',
            code_evidence_found: hasEvidence('fotmob_raw_detail_fetcher'),
            precise_detail_candidate: false,
            current_pageprops_detail_usage: true,
            safe_conclusion: 'current_strategy_but_slug_reuse_risk_remains_blocked',
        },
        {
            endpoint_key: 'source_inventory_slug_fragment_route',
            route_candidate: '/matches/{slug}#{externalId}',
            endpoint_type: 'html_slug_fragment_route',
            code_evidence_found: true,
            precise_detail_candidate: false,
            current_pageprops_detail_usage: false,
            fragment_reaches_server: false,
            safe_conclusion: 'fragment_cannot_be_assumed_to_select_server_payload',
        },
        {
            endpoint_key: 'api_data_match_details',
            route_candidate: '/api/data/matchDetails?matchId={externalId}',
            endpoint_type: 'json_detail_api',
            code_evidence_found:
                hasEvidence('fotmob_api_client') ||
                hasEvidence('l2_raw_detail_preview') ||
                hasEvidence('fotmob_strategy'),
            precise_detail_candidate: true,
            current_pageprops_detail_usage: false,
            safe_conclusion: 'candidate_requires_controlled_no_write_feasibility_and_identity_guard',
        },
        {
            endpoint_key: 'api_match_details_alternate',
            route_candidate: '/api/matchDetails?matchId={externalId}',
            endpoint_type: 'json_detail_api_legacy_or_alternate',
            code_evidence_found: hasEvidence('marathon_service') || hasEvidence('l2_raw_detail_preview'),
            precise_detail_candidate: true,
            current_pageprops_detail_usage: false,
            plan_only: true,
            safe_conclusion: 'alternate_route_not_adopted_without_future_authorization',
        },
    ];
}

function validateInputs(manifest = {}, l2v3rArtifact = {}) {
    const errors = [];
    const nextRequiredStep = normalizeText(manifest.next_required_step);
    const alreadyCompleted =
        nextRequiredStep === NEXT_REQUIRED_STEP &&
        normalizeText(manifest.phase_5_21_l2v3s_feasibility_status) === ARTIFACT_STATUS;
    if (nextRequiredStep !== 'detail_api_endpoint_feasibility_verification' && !alreadyCompleted) {
        errors.push(
            'manifest next_required_step must be detail_api_endpoint_feasibility_verification or completed L2V3S output'
        );
    }
    if (manifest.raw_write_ready_for_execution !== false) {
        errors.push('manifest raw_write_ready_for_execution must remain false');
    }
    if (Number(manifest.accepted_mapping_count || 0) !== 0) {
        errors.push('manifest accepted_mapping_count must remain 0');
    }
    if (normalizeText(l2v3rArtifact.current_url_strategy) !== 'fotmob_match_external_id_route') {
        errors.push('L2V3R current_url_strategy must remain fotmob_match_external_id_route');
    }
    if (l2v3rArtifact.uses_match_external_id_route !== true) {
        errors.push('L2V3R must record uses_match_external_id_route=true');
    }
    if (l2v3rArtifact.uses_source_inventory_page_url !== false) {
        errors.push('L2V3R must record uses_source_inventory_page_url=false');
    }
    if (l2v3rArtifact.fragment_reaches_server !== false) {
        errors.push('L2V3R must record fragment_reaches_server=false');
    }
    if (l2v3rArtifact.slug_reuse_risk !== true) {
        errors.push('L2V3R slug_reuse_risk must remain true');
    }
    if (normalizeText(l2v3rArtifact.precise_detail_endpoint_found) !== 'unknown') {
        errors.push('L2V3R precise_detail_endpoint_found must remain unknown');
    }
    if (Number(l2v3rArtifact.detail_url_construction_suspect_count || 0) !== 42) {
        errors.push('L2V3R detail_url_construction_suspect_count must be 42');
    }
    if (l2v3rArtifact.raw_write_ready_for_execution !== false) {
        errors.push('L2V3R raw_write_ready_for_execution must remain false');
    }
    if (Number(l2v3rArtifact.accepted_mapping_count || 0) !== 0) {
        errors.push('L2V3R accepted_mapping_count must remain 0');
    }
    return { ok: errors.length === 0, errors };
}

function normalizeTargetFromManifest(target = {}, category = 'known_good_control') {
    return {
        target_category: category,
        match_id: normalizeText(target.match_id),
        requested_schedule_external_id: normalizeText(target.external_id),
        requested_home_team: normalizeText(target.home_team),
        requested_away_team: normalizeText(target.away_team),
        requested_match_date: normalizeText(target.match_date || target.kickoff_time),
        requested_status: normalizeText(target.status),
    };
}

function normalizeTargetFromInvestigation(target = {}, category) {
    return {
        target_category: category,
        match_id: normalizeText(target.match_id),
        requested_schedule_external_id: normalizeText(target.schedule_external_id),
        requested_home_team: normalizeText(target.schedule_home_team),
        requested_away_team: normalizeText(target.schedule_away_team),
        requested_match_date: normalizeText(target.schedule_date),
        requested_status: normalizeText(target.schedule_status),
        prior_observed_detail_external_id: normalizeText(target.observed_detail_external_id) || null,
        prior_detail_url_construction_suspect: target.detail_url_construction_suspect === true,
        prior_likely_reverse_fixture_or_slug_reuse: target.likely_reverse_fixture_or_slug_reuse === true,
    };
}

function dedupeTargets(targets = []) {
    const seen = new Set();
    return targets.filter(target => {
        const id = target.requested_schedule_external_id;
        if (!id || seen.has(id)) return false;
        seen.add(id);
        return true;
    });
}

function selectControlledLiveTargets(manifest = {}, l2v3qArtifact = {}, maxTargets = MAX_CONTROLLED_TARGETS) {
    const investigationTargets = Array.isArray(l2v3qArtifact.analyzed_targets) ? l2v3qArtifact.analyzed_targets : [];
    const completedTargets = Array.isArray(manifest.known_completed_targets) ? manifest.known_completed_targets : [];
    const selected = [];
    if (investigationTargets[0]) {
        selected.push(normalizeTargetFromInvestigation(investigationTargets[0], 'known_reverse_fixture_or_slug_reuse'));
    }
    if (investigationTargets[1]) {
        selected.push(normalizeTargetFromInvestigation(investigationTargets[1], 'unresolved_large_gap'));
    }
    if (completedTargets[0]) {
        selected.push(normalizeTargetFromManifest(completedTargets[0], 'known_good_seeded_v2_control'));
    }
    return dedupeTargets(selected).slice(0, maxTargets);
}

function summarizeTopLevelKeys(value) {
    return isPlainObject(value) ? Object.keys(value).sort().slice(0, 25) : [];
}

function detectBlockSignals(bodyText, httpStatus) {
    const signals = [];
    if ([403, 429].includes(Number(httpStatus))) signals.push(`HTTP_${httpStatus}`);
    for (const pattern of BLOCK_SIGNAL_PATTERNS) {
        if (pattern.test(bodyText)) signals.push(pattern.source.replace(/\\/g, ''));
    }
    return [...new Set(signals)].sort();
}

function parseSafeJson(bodyText) {
    try {
        const value = JSON.parse(String(bodyText || ''));
        return { ok: true, value, error: null };
    } catch (error) {
        return { ok: false, value: null, error: error.message };
    }
}

function extractObservedSafeMetadata(payload = {}) {
    const general = isPlainObject(payload.general) ? payload.general : {};
    const header = isPlainObject(payload.header) ? payload.header : {};
    const teams = Array.isArray(header.teams) ? header.teams : [];
    return {
        observed_detail_external_id: firstNumericText(
            getByPath(payload, 'general.matchId'),
            getByPath(payload, 'general.matchID'),
            payload.matchId,
            payload.match_id,
            getByPath(payload, 'content.matchFacts.matchId')
        ),
        observed_home_team: firstText(
            extractTeamName(general.homeTeam),
            extractTeamName(header.homeTeam),
            extractTeamName(teams[0])
        ),
        observed_away_team: firstText(
            extractTeamName(general.awayTeam),
            extractTeamName(header.awayTeam),
            extractTeamName(teams[1])
        ),
        observed_match_date: firstText(
            general.matchTimeUTC,
            general.matchDate,
            getByPath(header, 'status.utcTime'),
            header.utcTime
        ),
        observed_status: firstText(getByPath(general, 'status.type'), general.status, getByPath(header, 'status.type')),
    };
}

function compareDateRule(target = {}, observed = {}) {
    const requestedDate = normalizeDateOnly(target.requested_match_date);
    const observedDate = normalizeDateOnly(observed.observed_match_date);
    if (!requestedDate || !observedDate) return 'unknown';
    return requestedDate === observedDate ? 'date_match' : 'date_mismatch';
}

function compareTeams(target = {}, observed = {}) {
    const requestedHome = normalizeLower(target.requested_home_team);
    const requestedAway = normalizeLower(target.requested_away_team);
    const observedHome = normalizeLower(observed.observed_home_team);
    const observedAway = normalizeLower(observed.observed_away_team);
    if (!requestedHome || !requestedAway || !observedHome || !observedAway) return 'unknown';
    if (requestedHome === observedHome && requestedAway === observedAway) return 'same_order';
    if (requestedHome === observedAway && requestedAway === observedHome) return 'reversed_order';
    return 'mismatch';
}

function buildSafeEndpointSummary({ target, request, response = {}, bodyText = '', error = null }) {
    const httpStatus = safeNumber(response.status || response.statusCode, 0);
    const contentType =
        response.headers && typeof response.headers.get === 'function'
            ? normalizeText(response.headers.get('content-type'))
            : normalizeText(response.headers?.['content-type']);
    const blockSignals = detectBlockSignals(bodyText, httpStatus);
    const parsed = parseSafeJson(bodyText);
    const observed = parsed.ok ? extractObservedSafeMetadata(parsed.value) : {};
    const requestedId = normalizeText(target.requested_schedule_external_id);
    const observedId = normalizeText(observed.observed_detail_external_id);
    const identityMatch = Boolean(requestedId && observedId && requestedId === observedId);
    const teamStatus = parsed.ok ? compareTeams(target, observed) : 'unknown';
    const dateRuleStatus = parsed.ok ? compareDateRule(target, observed) : 'unknown';
    const endpointAvoidsSlugReuse =
        parsed.ok && identityMatch && teamStatus === 'same_order' && dateRuleStatus === 'date_match' ? true : 'unknown';
    const safeErrorSummary = error
        ? `FETCH_ERROR:${normalizeText(error.message || error).slice(0, 160)}`
        : blockSignals.length > 0
          ? `CONTROLLED_BLOCK_SIGNAL:${blockSignals.join(',')}`
          : parsed.ok
            ? null
            : `JSON_PARSE_FAILED:${normalizeText(parsed.error).slice(0, 120)}`;

    return {
        target_category: target.target_category,
        requested_schedule_external_id: requestedId,
        match_id: target.match_id,
        endpoint_path: request.endpoint_path,
        request_url_summary: request.url.replace(requestedId, '{externalId}'),
        http_status: httpStatus,
        parsed: parsed.ok,
        observed_detail_external_id: observedId || null,
        schedule_detail_date_safe_summary: {
            requested_date: normalizeDateOnly(target.requested_match_date),
            observed_date: normalizeDateOnly(observed.observed_match_date),
        },
        team_safe_summary: {
            requested: `${target.requested_home_team || ''}-${target.requested_away_team || ''}`,
            observed: `${observed.observed_home_team || ''}-${observed.observed_away_team || ''}`,
            status: teamStatus,
        },
        status_safe_summary: {
            requested_status: target.requested_status || null,
            observed_status: observed.observed_status || null,
        },
        identity_match: identityMatch,
        date_rule_status: dateRuleStatus,
        whether_endpoint_avoids_slug_reuse: endpointAvoidsSlugReuse,
        safe_error_summary: safeErrorSummary,
        payload_size_summary: {
            body_byte_length: Buffer.byteLength(String(bodyText || ''), 'utf8'),
            content_type: contentType || null,
        },
        top_level_keys_summary: parsed.ok ? summarizeTopLevelKeys(parsed.value) : [],
        block_signals: blockSignals,
        full_payload_saved: false,
        full_payload_printed: false,
        db_write_performed: false,
        raw_insert_performed: false,
    };
}

async function executeEndpointCheck(target = {}, dependencies = {}) {
    const fetchFn = dependencies.fetchFn || global.fetch;
    if (typeof fetchFn !== 'function') {
        throw new Error('FETCH_DEPENDENCY_MISSING');
    }
    const request = buildDetailApiRequest({ external_id: target.requested_schedule_external_id });
    let response;
    let bodyText = '';
    try {
        response = await fetchFn(request.url, {
            method: request.method,
            headers: request.headers,
            redirect: 'follow',
        });
        bodyText = typeof response.text === 'function' ? await response.text() : '';
        return buildSafeEndpointSummary({ target, request, response, bodyText });
    } catch (error) {
        return buildSafeEndpointSummary({ target, request, response: { status: 0 }, bodyText, error });
    }
}

function shouldStopAfterSummary(summary = {}) {
    if ((summary.block_signals || []).length > 0) return true;
    const status = Number(summary.http_status || 0);
    if (status < 200 || status >= 300) return true;
    if (summary.parsed !== true) return true;
    return false;
}

async function runControlledLiveChecks(targets = [], dependencies = {}) {
    const checked = [];
    let stoppedEarly = false;
    let stopReason = null;
    for (const target of targets) {
        const summary = await executeEndpointCheck(target, dependencies);
        checked.push(summary);
        if (shouldStopAfterSummary(summary)) {
            stoppedEarly = true;
            stopReason =
                summary.safe_error_summary ||
                `STOP_AFTER_HTTP_STATUS_${summary.http_status || 'unknown'}_OR_PARSE_FAILURE`;
            break;
        }
    }
    return { checked_targets: checked, stopped_early: stoppedEarly, stop_reason: stopReason };
}

function summarizeControlledChecks(result = {}, controlledLiveCheckPerformed = false) {
    const targets = Array.isArray(result.checked_targets) ? result.checked_targets : [];
    const identityMatchCount = targets.filter(target => target.identity_match === true).length;
    const parsedCount = targets.filter(target => target.parsed === true).length;
    const blockCount = targets.filter(target => (target.block_signals || []).length > 0).length;
    const mismatchCount = targets.filter(
        target => target.parsed === true && target.observed_detail_external_id && target.identity_match !== true
    ).length;
    const reverseStillDetectedCount = targets.filter(
        target =>
            target.team_safe_summary?.status === 'reversed_order' || (target.target_category || '').includes('reverse')
    ).length;
    const unresolvedStillDetectedCount = targets.filter(target => target.identity_match !== true).length;
    const allParsedMatches =
        targets.length > 0 &&
        parsedCount === targets.length &&
        identityMatchCount === targets.length &&
        targets.every(target => target.team_safe_summary?.status === 'same_order');

    return {
        controlled_live_check_performed: controlledLiveCheckPerformed,
        checked_target_count: targets.length,
        requested_observed_identity_match_count: identityMatchCount,
        requested_observed_identity_mismatch_count: mismatchCount,
        reverse_fixture_still_detected_count: reverseStillDetectedCount,
        unresolved_large_gap_still_detected_count: unresolvedStillDetectedCount,
        parse_failure_count: targets.filter(target => target.parsed !== true).length,
        block_or_captcha_count: blockCount,
        endpoint_avoids_slug_reuse: allParsedMatches ? true : 'unknown',
        precise_detail_endpoint_found: allParsedMatches ? true : 'unknown',
        stopped_early: result.stopped_early === true,
        stop_reason: result.stop_reason || null,
        targets,
    };
}

function buildRecommendedStrategy(checkSummary = {}) {
    if (checkSummary.precise_detail_endpoint_found === true && checkSummary.endpoint_avoids_slug_reuse === true) {
        return {
            recommended_precise_detail_strategy:
                'implement_guarded_api_match_details_request_with_requested_observed_id_date_team_status_no_go_checks',
            strategy_confidence: 'medium',
            requires_followup_implementation: true,
            recommended_next_step: PRECISE_IMPLEMENTATION_RECOMMENDATION,
            next_required_step: PRECISE_IMPLEMENTATION_STEP,
        };
    }
    return {
        recommended_precise_detail_strategy:
            'do_not_adopt_api_match_details_until_controlled_no_write_check_parses_safe_metadata_and_requested_observed_id_matches',
        strategy_confidence: 'low',
        requires_followup_implementation: false,
        recommended_next_step: NEXT_RECOMMENDED_STEP,
        next_required_step: NEXT_REQUIRED_STEP,
    };
}

function buildArtifact({
    manifest,
    l2v3rArtifact,
    l2v3qArtifact,
    sourceFileAnalysis,
    endpointInventory,
    controlledCheckSummary,
    generatedAt = GENERATED_AT,
} = {}) {
    const strategy = buildRecommendedStrategy(controlledCheckSummary);
    const analyzedEndpointCount = endpointInventory.length;
    return {
        artifact_type: 'detail_api_endpoint_feasibility',
        artifact_status: ARTIFACT_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3R',
        generated_at: generatedAt,
        no_write: true,
        live_source_check_performed: controlledCheckSummary.controlled_live_check_performed,
        controlled_live_check_performed: controlledCheckSummary.controlled_live_check_performed,
        network_request_performed: controlledCheckSummary.controlled_live_check_performed,
        db_write_performed: false,
        raw_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        browser_proxy_captcha_bypass_performed: false,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        analyzed_endpoint_count: analyzedEndpointCount,
        checked_target_count: controlledCheckSummary.checked_target_count,
        precise_detail_endpoint_found: controlledCheckSummary.precise_detail_endpoint_found,
        endpoint_avoids_slug_reuse: controlledCheckSummary.endpoint_avoids_slug_reuse,
        requested_observed_identity_match_count: controlledCheckSummary.requested_observed_identity_match_count,
        requested_observed_identity_mismatch_count: controlledCheckSummary.requested_observed_identity_mismatch_count,
        reverse_fixture_still_detected_count: controlledCheckSummary.reverse_fixture_still_detected_count,
        unresolved_large_gap_still_detected_count: controlledCheckSummary.unresolved_large_gap_still_detected_count,
        parse_failure_count: controlledCheckSummary.parse_failure_count,
        block_or_captcha_count: controlledCheckSummary.block_or_captcha_count,
        ...strategy,
        source_code_evidence: {
            analyzed_source_file_count: sourceFileAnalysis.length,
            source_files: sourceFileAnalysis,
        },
        endpoint_inventory: endpointInventory,
        controlled_endpoint_check: {
            max_allowed_targets: MAX_CONTROLLED_TARGETS,
            stopped_early: controlledCheckSummary.stopped_early,
            stop_reason: controlledCheckSummary.stop_reason,
            checked_targets: controlledCheckSummary.targets,
        },
        upstream_context: {
            l2v3r_current_url_strategy: l2v3rArtifact.current_url_strategy,
            l2v3r_uses_match_external_id_route: l2v3rArtifact.uses_match_external_id_route,
            l2v3r_uses_source_inventory_page_url: l2v3rArtifact.uses_source_inventory_page_url,
            l2v3r_fragment_reaches_server: l2v3rArtifact.fragment_reaches_server,
            l2v3r_slug_reuse_risk: l2v3rArtifact.slug_reuse_risk,
            l2v3r_detail_url_construction_suspect_count: l2v3rArtifact.detail_url_construction_suspect_count,
            l2v3q_analyzed_target_count:
                l2v3qArtifact.analyzed_target_count || l2v3qArtifact.counts?.analyzed_target_count,
            l2v3q_still_blocked_count: l2v3qArtifact.still_blocked_count || l2v3qArtifact.counts?.still_blocked_count,
        },
        safety_contract: {
            endpoint_feasibility_result_is_not_accepted_mapping: true,
            endpoint_feasibility_result_is_not_raw_write_authorization: true,
            precise_detail_endpoint_found_does_not_imply_raw_write_ready: true,
            requested_observed_mismatch_remains_blocked: true,
            slug_reuse_risk_blocks_raw_write_until_future_guarded_strategy: true,
            full_payload_saved: false,
            full_payload_printed: false,
            db_write_performed: false,
            raw_match_data_insert_performed: false,
            matches_write_performed: false,
            separate_identity_mapping_acceptance_required: true,
            separate_baseline_acceptance_required: true,
            separate_final_db_write_authorization_required: true,
        },
        recommended_next_step: strategy.recommended_next_step,
        next_required_step: strategy.next_required_step,
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3s_feasibility_status: artifact.artifact_status,
        detail_api_endpoint_feasibility_status: artifact.artifact_status,
        phase_5_21_l2v3s_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3s_report_path: REPORT_PATH,
        analyzed_endpoint_count: artifact.analyzed_endpoint_count,
        phase_5_21_l2v3s_analyzed_endpoint_count: artifact.analyzed_endpoint_count,
        controlled_live_check_performed: artifact.controlled_live_check_performed,
        phase_5_21_l2v3s_controlled_live_check_performed: artifact.controlled_live_check_performed,
        checked_target_count: artifact.checked_target_count,
        phase_5_21_l2v3s_checked_target_count: artifact.checked_target_count,
        precise_detail_endpoint_found: artifact.precise_detail_endpoint_found,
        phase_5_21_l2v3s_precise_detail_endpoint_found: artifact.precise_detail_endpoint_found,
        endpoint_avoids_slug_reuse: artifact.endpoint_avoids_slug_reuse,
        phase_5_21_l2v3s_endpoint_avoids_slug_reuse: artifact.endpoint_avoids_slug_reuse,
        recommended_precise_detail_strategy: artifact.recommended_precise_detail_strategy,
        phase_5_21_l2v3s_recommended_precise_detail_strategy: artifact.recommended_precise_detail_strategy,
        strategy_confidence: artifact.strategy_confidence,
        phase_5_21_l2v3s_strategy_confidence: artifact.strategy_confidence,
        requires_followup_implementation: artifact.requires_followup_implementation,
        phase_5_21_l2v3s_requires_followup_implementation: artifact.requires_followup_implementation,
        accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        phase_5_21_l2v3s_accepted_mapping_count: 0,
        phase_5_21_l2v3s_identity_mapping_acceptance_performed: false,
        phase_5_21_l2v3s_baseline_acceptance_performed: false,
        phase_5_21_l2v3s_raw_write_retry_performed: false,
        phase_5_21_l2v3s_raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

function buildReport(artifact = {}) {
    return `# Data Entrypoint Governance - Phase 5.21 L2V3S

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- source_phase=Phase 5.21L2V3R
- no_write=true
- controlled_live_check_performed=${artifact.controlled_live_check_performed}
- network_request_performed=${artifact.network_request_performed}
- db_write_performed=false
- raw_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false
- browser_proxy_captcha_bypass_performed=false

## Safety Contract

- endpoint feasibility result is not an accepted mapping.
- endpoint feasibility result is not raw write authorization.
- precise_detail_endpoint_found does not imply raw_write_ready_for_execution.
- accepted_mapping_count=0.
- raw_write_ready_for_execution=false.
- full API payload saved=false.
- full API payload printed=false.
- separate identity mapping acceptance, baseline acceptance, and final DB-write authorization remain required.

## Endpoint Feasibility Summary

- analyzed_endpoint_count=${artifact.analyzed_endpoint_count}
- controlled_live_check_performed=${artifact.controlled_live_check_performed}
- checked_target_count=${artifact.checked_target_count}
- precise_detail_endpoint_found=${artifact.precise_detail_endpoint_found}
- endpoint_avoids_slug_reuse=${artifact.endpoint_avoids_slug_reuse}
- requested_observed_identity_match_count=${artifact.requested_observed_identity_match_count}
- requested_observed_identity_mismatch_count=${artifact.requested_observed_identity_mismatch_count}
- reverse_fixture_still_detected_count=${artifact.reverse_fixture_still_detected_count}
- unresolved_large_gap_still_detected_count=${artifact.unresolved_large_gap_still_detected_count}
- parse_failure_count=${artifact.parse_failure_count}
- block_or_captcha_count=${artifact.block_or_captcha_count}

## Existing Endpoint Evidence

The repository already contains code references to /api/data/matchDetails?matchId={externalId}, the alternate /api/matchDetails?matchId={externalId}, the current /match/{externalId} HTML route, and the league source inventory endpoint. Current pageProps v2 acquisition paths still use html_hydration and do not adopt api_match_details for raw write.

## Controlled Check Conclusion

- recommended_precise_detail_strategy=${artifact.recommended_precise_detail_strategy}
- strategy_confidence=${artifact.strategy_confidence}
- requires_followup_implementation=${artifact.requires_followup_implementation}
- stop_reason=${artifact.controlled_endpoint_check?.stop_reason || 'none'}

This phase does not accept any identity mapping or baseline. A future implementation must keep requested_schedule_external_id as primary identity and must fail closed unless observed_detail_external_id, date, team, and status metadata are compatible.

## Next Step

${artifact.recommended_next_step}
`;
}

async function runDetailApiEndpointFeasibility(dependencies = {}) {
    const options = {
        controlledLiveCheck: dependencies.controlledLiveCheck === true,
        networkAuthorization: dependencies.networkAuthorization === true,
        maxTargets:
            dependencies.maxTargets === undefined
                ? MAX_CONTROLLED_TARGETS
                : parseInteger(dependencies.maxTargets, MAX_CONTROLLED_TARGETS),
    };
    const optionGate = validateCliOptions({ ...options, unknown: [] });
    if (!optionGate.ok) return { ok: false, status: 2, errors: optionGate.errors };

    const manifest = dependencies.manifest || readJsonFile(MANIFEST_PATH);
    const l2v3rArtifact = dependencies.l2v3rArtifact || readJsonFile(L2V3R_ARTIFACT_PATH);
    const l2v3qArtifact = dependencies.l2v3qArtifact || readJsonFile(L2V3Q_ARTIFACT_PATH);
    const inputGate = validateInputs(manifest, l2v3rArtifact);
    if (!inputGate.ok) return { ok: false, status: 2, errors: inputGate.errors };

    const sourceFileAnalysis = analyzeSourceFiles(SOURCE_FILES, dependencies);
    const endpointInventory = buildEndpointInventory(sourceFileAnalysis);
    const selectedTargets = selectControlledLiveTargets(manifest, l2v3qArtifact, options.maxTargets);
    const controlledResult =
        options.controlledLiveCheck === true
            ? await runControlledLiveChecks(selectedTargets, dependencies)
            : { checked_targets: [], stopped_early: false, stop_reason: null };
    const controlledCheckSummary = summarizeControlledChecks(controlledResult, options.controlledLiveCheck === true);
    const artifact = buildArtifact({
        manifest,
        l2v3rArtifact,
        l2v3qArtifact,
        sourceFileAnalysis,
        endpointInventory,
        controlledCheckSummary,
        generatedAt: dependencies.generatedAt || GENERATED_AT,
    });
    const updatedManifest = updateManifestMetadata(manifest, artifact);
    const report = buildReport(artifact);

    if (dependencies.writeFiles !== false) {
        writeJsonFile(dependencies.artifactOutputPath || ARTIFACT_OUTPUT_PATH, artifact);
        writeTextFile(dependencies.reportOutputPath || REPORT_PATH, report);
        writeJsonFile(dependencies.manifestOutputPath || MANIFEST_PATH, updatedManifest);
    }

    return {
        ok: true,
        status: 0,
        artifact,
        updated_manifest: updatedManifest,
        report,
    };
}

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/pageprops_v2_detail_api_endpoint_feasibility.js --controlled-live-check=no --network-authorization=no --max-targets=0',
        '  node scripts/ops/pageprops_v2_detail_api_endpoint_feasibility.js --controlled-live-check=yes --network-authorization=yes --max-targets=3',
        '',
        'Safety:',
        '  L2V3S is no-write endpoint feasibility only. It never saves or prints full API payloads and never writes DB/raw/matches.',
    ].join('\n');
}

async function runCli(argv = process.argv.slice(2), streams = {}) {
    const stdout = streams.stdout || (text => process.stdout.write(text));
    const options = parseArgs(argv);
    if (options.help) {
        stdout(`${usage()}\n`);
        return 0;
    }
    const optionGate = validateCliOptions(options);
    if (!optionGate.ok) {
        stdout(`${JSON.stringify({ ok: false, phase: PHASE, errors: optionGate.errors }, null, 2)}\n`);
        return 2;
    }
    const result = await runDetailApiEndpointFeasibility({
        controlledLiveCheck: options.controlledLiveCheck,
        networkAuthorization: options.networkAuthorization,
        maxTargets: options.maxTargets,
        writeFiles: options.writeFiles,
    });
    if (!result.ok) {
        stdout(`${JSON.stringify({ ok: false, phase: PHASE, errors: result.errors }, null, 2)}\n`);
        return result.status;
    }
    stdout(
        `${JSON.stringify(
            {
                ok: true,
                phase: PHASE,
                artifact: ARTIFACT_OUTPUT_PATH,
                report: REPORT_PATH,
                analyzed_endpoint_count: result.artifact.analyzed_endpoint_count,
                controlled_live_check_performed: result.artifact.controlled_live_check_performed,
                checked_target_count: result.artifact.checked_target_count,
                precise_detail_endpoint_found: result.artifact.precise_detail_endpoint_found,
                endpoint_avoids_slug_reuse: result.artifact.endpoint_avoids_slug_reuse,
                requested_observed_identity_match_count: result.artifact.requested_observed_identity_match_count,
                requested_observed_identity_mismatch_count: result.artifact.requested_observed_identity_mismatch_count,
                parse_failure_count: result.artifact.parse_failure_count,
                block_or_captcha_count: result.artifact.block_or_captcha_count,
                recommended_precise_detail_strategy: result.artifact.recommended_precise_detail_strategy,
                strategy_confidence: result.artifact.strategy_confidence,
                raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
                accepted_mapping_count: result.artifact.accepted_mapping_count,
                recommended_next_step: result.artifact.recommended_next_step,
            },
            null,
            2
        )}\n`
    );
    return result.status;
}

module.exports = {
    PHASE,
    PHASE_NAME,
    ARTIFACT_STATUS,
    MANIFEST_PATH,
    L2V3R_ARTIFACT_PATH,
    L2V3Q_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    NEXT_REQUIRED_STEP,
    NEXT_RECOMMENDED_STEP,
    buildDetailApiUrl,
    buildDetailApiRequest,
    parseArgs,
    validateCliOptions,
    analyzeSourceFiles,
    buildEndpointInventory,
    validateInputs,
    selectControlledLiveTargets,
    extractObservedSafeMetadata,
    buildSafeEndpointSummary,
    executeEndpointCheck,
    runControlledLiveChecks,
    summarizeControlledChecks,
    buildRecommendedStrategy,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    runDetailApiEndpointFeasibility,
    runCli,
};

if (require.main === module) {
    runCli()
        .then(status => {
            process.exitCode = status;
        })
        .catch(error => {
            process.stdout.write(`${JSON.stringify({ ok: false, phase: PHASE, error: error.message }, null, 2)}\n`);
            process.exitCode = 1;
        });
}
