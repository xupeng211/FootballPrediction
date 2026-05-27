#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const {
    reconcileRouteIdentity,
    resolveRecaptureIdentityContract,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const PHASE = 'Phase 5.21L2V3AO';
const PHASE_NAME = 'controlled_no_write_payload_recapture_execution';
const SOURCE = 'fotmob';
const ROUTE = 'html_hydration';
const RAW_VERSION = 'fotmob_pageprops_v2';
const HASH_STRATEGY = 'stable_pageprops_payload_v1';
const BATCH_ID = 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001';
const LEAGUE_ID = 53;
const LEAGUE_NAME = 'Ligue 1';
const SEASON = '2025/2026';
const TARGET_COUNT = 50;
const DEFAULT_REQUEST_DELAY_MS = 750;
const FOTMOB_BASE_URL = 'https://www.fotmob.com';
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const PLAN_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_plan.phase521l2v3an.json';
const ENRICHED_TARGETS_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_targets.phase521l2v3aa.json';
const IDENTITY_ACCEPTANCE_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.identity_mapping_acceptance_result.phase521l2v3ae.json';
const BASELINE_ACCEPTANCE_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.baseline_acceptance_result.phase521l2v3ag.json';
const RESULT_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_result.phase521l2v3ao.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AO.md';
const SUCCESS_STATUS = 'completed_controlled_no_write_payload_recapture_execution';
const BLOCKED_STATUS = 'blocked_controlled_no_write_payload_recapture_execution';
const SUCCESS_NEXT_STEP = 'Phase 5.21L2V3AP: controlled recapture result verification planning';
const BLOCKED_NEXT_STEP = 'Phase 5.21L2V3AP: no-write payload recapture blocker investigation';
const PARTIAL_NEXT_STEP = 'Phase 5.21L2V3AP: partial recapture review planning';

const REVIEWED_INPUTS = Object.freeze([
    ['no_write_payload_recapture_plan', PLAN_ARTIFACT_PATH],
    [
        'payload_source_declaration_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.payload_source_declaration_result.phase521l2v3am.json',
    ],
    [
        'payload_source_declaration_plan',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.payload_source_declaration_plan.phase521l2v3al.json',
    ],
    [
        'raw_write_input_source_investigation',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.raw_write_input_source_investigation.phase521l2v3ak.json',
    ],
    [
        'controlled_raw_write_execution_plan',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_raw_match_data_write_execution_plan.phase521l2v3aj.json',
    ],
    [
        'final_db_write_authorization_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.final_db_write_authorization_result.phase521l2v3ai.json',
    ],
    ['baseline_acceptance_result', BASELINE_ACCEPTANCE_PATH],
    ['identity_mapping_acceptance_result', IDENTITY_ACCEPTANCE_PATH],
    [
        'enriched_no_write_verification_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.enriched_no_write_verification_result.phase521l2v3ac.json',
    ],
    ['enriched_targets', ENRICHED_TARGETS_PATH],
    [
        'source_inventory_acquisition_result',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.controlled_source_inventory_acquisition_result.phase521l2v3y.json',
    ],
    ['proposal_manifest', MANIFEST_PATH],
    ['fotmob_raw_detail_fetcher_code', 'src/infrastructure/services/FotMobRawDetailFetcher.js'],
    ['route_identity_reconciler_code', 'src/infrastructure/services/FotMobRouteIdentityReconciler.js'],
]);

const REQUIRED_YES_FLAGS = Object.freeze([
    'noWriteRecaptureAuthorization',
    'networkAuthorization',
    'matchDetailRecaptureAuthorization',
    'allowNoWriteRecaptureExecution',
]);
const REQUIRED_NO_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowRawMatchDataWrite',
    'allowMatchesWrite',
    'allowMatchesExternalIdWrite',
    'allowRawWriteExecution',
    'allowRawWriteRunnerWriteMode',
    'allowSchemaMigration',
    'allowParserImplementation',
    'allowFeatureExtraction',
    'allowTraining',
    'allowPrediction',
    'allowBrowserRuntime',
    'allowProxyRuntime',
    'printFullBody',
    'saveFullBody',
    'printFullJson',
    'saveFullJson',
    'printFullPageprops',
    'saveFullPageprops',
    'persistCookiesTokensHeaders',
    'uncontrolledRetry',
]);
const BLOCKED_TRUE_FLAGS = Object.freeze([
    'finalDbWriteConfirmation',
    'renewedRawWriteAuthorization',
    'rawWriteExecutionAuthorization',
    'executeRawWrite',
    'commitRawWrite',
    'writeMode',
    'allowControlledWrite',
    'executeDbWrite',
    'insertRawMatchData',
    'modifyMatchesExternalId',
]);
const BLOCK_MARKER_PATTERNS = Object.freeze([
    ['http_403', /403|forbidden/i],
    ['http_429', /429|too many requests|rate limit/i],
    ['cloudflare', /cloudflare|cf-chl|cf_clearance|attention required|just a moment/i],
    ['captcha', /captcha|verify you are human|human verification/i],
    ['access_denied', /access denied|request blocked/i],
]);

function absolutePath(filePath) {
    return path.isAbsolute(filePath) ? filePath : path.join(PROJECT_ROOT, filePath);
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

function normalizeBooleanFlag(value, fallback = undefined) {
    if (typeof value === 'boolean') return value;
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = normalizeLower(value);
    if (['1', 'true', 'yes', 'y', 'on'].includes(normalized)) return true;
    if (['0', 'false', 'no', 'n', 'off'].includes(normalized)) return false;
    return fallback;
}

function parseInteger(value, fallback = null) {
    if (value === null || value === undefined || value === '') return fallback;
    const normalized = normalizeText(value);
    if (!/^\d+$/.test(normalized)) return Number.NaN;
    return Number.parseInt(normalized, 10);
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) return { value: nextArg, consumedNext: true };
    return { value: true, consumedNext: false };
}

function toCamelKey(rawKey) {
    return normalizeText(rawKey).replace(/[-_]([a-z0-9])/g, (_match, char) => char.toUpperCase());
}

function flagName(key) {
    return key.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`);
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        manifest: MANIFEST_PATH,
        planArtifact: PLAN_ARTIFACT_PATH,
        enrichedTargets: ENRICHED_TARGETS_PATH,
        identityAcceptance: IDENTITY_ACCEPTANCE_PATH,
        baselineAcceptance: BASELINE_ACCEPTANCE_PATH,
        artifactOutput: RESULT_ARTIFACT_PATH,
        reportOutput: REPORT_PATH,
        source: null,
        leagueId: null,
        leagueName: null,
        season: null,
        route: null,
        rawVersion: null,
        hashStrategy: null,
        batchId: null,
        targetCount: null,
        noWriteRecaptureAuthorization: null,
        networkAuthorization: null,
        matchDetailRecaptureAuthorization: null,
        allowNoWriteRecaptureExecution: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowMatchesWrite: null,
        allowMatchesExternalIdWrite: null,
        allowRawWriteExecution: null,
        allowRawWriteRunnerWriteMode: null,
        allowSchemaMigration: null,
        allowParserImplementation: null,
        allowFeatureExtraction: null,
        allowTraining: null,
        allowPrediction: null,
        allowBrowserRuntime: null,
        allowProxyRuntime: null,
        printFullBody: null,
        saveFullBody: null,
        printFullJson: null,
        saveFullJson: null,
        printFullPageprops: null,
        saveFullPageprops: null,
        persistCookiesTokensHeaders: null,
        uncontrolledRetry: null,
        finalDbWriteConfirmation: false,
        renewedRawWriteAuthorization: false,
        rawWriteExecutionAuthorization: false,
        executeRawWrite: false,
        commitRawWrite: false,
        writeMode: false,
        allowControlledWrite: false,
        executeDbWrite: false,
        insertRawMatchData: false,
        modifyMatchesExternalId: false,
        concurrency: null,
        retry: null,
        requestDelayMs: DEFAULT_REQUEST_DELAY_MS,
        timeoutMs: 15000,
        writeFiles: true,
        help: false,
        unknown: [],
    };
    const knownKeys = new Set(Object.keys(options));
    const booleanKeys = new Set([
        ...REQUIRED_YES_FLAGS,
        ...REQUIRED_NO_FLAGS,
        ...BLOCKED_TRUE_FLAGS,
        'writeFiles',
        'help',
    ]);

    for (let index = 0; index < argv.length; index += 1) {
        const arg = String(argv[index]);
        if (!arg.startsWith('--')) {
            options.unknown.push(arg);
            continue;
        }
        const rawKey = arg.replace(/^--/, '').split('=')[0];
        const key = toCamelKey(rawKey);
        const { value, consumedNext } = parseOptionValue(arg, argv, index);
        if (consumedNext) index += 1;
        if (!knownKeys.has(key)) {
            options.unknown.push(rawKey);
            continue;
        }
        options[key] = booleanKeys.has(key) ? normalizeBooleanFlag(value, true) : value;
    }
    return options;
}

function pushRequiredYes(errors, value, name) {
    if (value === true) return;
    errors.push(value === false ? `${name}=yes is required` : `missing ${name}=yes`);
}

function pushRequiredNo(errors, value, name) {
    if (value === false) return;
    errors.push(value === true ? `${name}=yes is blocked in ${PHASE}` : `missing ${name}=no`);
}

function requireExact(errors, actual, expected, name) {
    const text = normalizeText(actual);
    if (!text) {
        errors.push(`missing ${name}=${expected}`);
        return;
    }
    if (text !== expected) errors.push(`${name} must be ${expected}`);
}

function normalizeExecutionInput(input = {}) {
    return {
        ...input,
        manifest: normalizeText(input.manifest || MANIFEST_PATH),
        planArtifact: normalizeText(input.planArtifact || PLAN_ARTIFACT_PATH),
        enrichedTargets: normalizeText(input.enrichedTargets || ENRICHED_TARGETS_PATH),
        identityAcceptance: normalizeText(input.identityAcceptance || IDENTITY_ACCEPTANCE_PATH),
        baselineAcceptance: normalizeText(input.baselineAcceptance || BASELINE_ACCEPTANCE_PATH),
        artifactOutput: normalizeText(input.artifactOutput || RESULT_ARTIFACT_PATH),
        reportOutput: normalizeText(input.reportOutput || REPORT_PATH),
        source: normalizeLower(input.source),
        leagueId: parseInteger(input.leagueId, null),
        leagueName: normalizeText(input.leagueName),
        season: normalizeText(input.season),
        route: normalizeText(input.route),
        rawVersion: normalizeText(input.rawVersion),
        hashStrategy: normalizeText(input.hashStrategy),
        batchId: normalizeText(input.batchId),
        targetCount: parseInteger(input.targetCount, null),
        concurrency: parseInteger(input.concurrency, null),
        retry: parseInteger(input.retry, null),
        requestDelayMs: parseInteger(input.requestDelayMs, DEFAULT_REQUEST_DELAY_MS),
        timeoutMs: parseInteger(input.timeoutMs, 15000),
        writeFiles: normalizeBooleanFlag(input.writeFiles, true),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function validateExecutionInput(input = {}) {
    const value = normalizeExecutionInput(input);
    const errors = [];
    if (value.unknown.length > 0) errors.push(`unknown arguments: ${value.unknown.join(', ')}`);
    requireExact(errors, value.manifest, MANIFEST_PATH, 'manifest');
    requireExact(errors, value.planArtifact, PLAN_ARTIFACT_PATH, 'plan-artifact');
    requireExact(errors, value.enrichedTargets, ENRICHED_TARGETS_PATH, 'enriched-targets');
    requireExact(errors, value.identityAcceptance, IDENTITY_ACCEPTANCE_PATH, 'identity-acceptance');
    requireExact(errors, value.baselineAcceptance, BASELINE_ACCEPTANCE_PATH, 'baseline-acceptance');
    requireExact(errors, value.source, SOURCE, 'source');
    if (value.leagueId !== LEAGUE_ID) errors.push('league-id must be 53');
    requireExact(errors, value.leagueName, LEAGUE_NAME, 'league-name');
    requireExact(errors, value.season, SEASON, 'season');
    requireExact(errors, value.route, ROUTE, 'route');
    requireExact(errors, value.rawVersion, RAW_VERSION, 'raw-version');
    requireExact(errors, value.hashStrategy, HASH_STRATEGY, 'hash-strategy');
    requireExact(errors, value.batchId, BATCH_ID, 'batch-id');
    if (value.targetCount !== TARGET_COUNT) errors.push('target-count must be 50');
    if (value.concurrency !== 1) errors.push('concurrency must be 1');
    if (value.retry !== 0) errors.push('retry must be 0');
    if (!Number.isInteger(value.requestDelayMs) || value.requestDelayMs < 0) {
        errors.push('request-delay-ms must be a non-negative integer');
    }
    if (!Number.isInteger(value.timeoutMs) || value.timeoutMs <= 0) {
        errors.push('timeout-ms must be a positive integer');
    }
    for (const key of REQUIRED_YES_FLAGS) {
        pushRequiredYes(errors, normalizeBooleanFlag(value[key], undefined), flagName(key));
    }
    for (const key of REQUIRED_NO_FLAGS) {
        pushRequiredNo(errors, normalizeBooleanFlag(value[key], undefined), flagName(key));
    }
    for (const key of BLOCKED_TRUE_FLAGS) {
        if (normalizeBooleanFlag(value[key], false) === true) {
            errors.push(`${flagName(key)}=yes is blocked in ${PHASE}`);
        }
    }
    return { ok: errors.length === 0, errors, value };
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function jsonClone(value) {
    if (value === undefined) return undefined;
    return JSON.parse(JSON.stringify(value));
}

function canonicalizeJson(value) {
    if (value === null || typeof value !== 'object') return value;
    if (Array.isArray(value)) return value.map(canonicalizeJson);
    const output = {};
    for (const key of Object.keys(value).sort()) output[key] = canonicalizeJson(value[key]);
    return output;
}

function sha256Text(text) {
    return crypto
        .createHash('sha256')
        .update(String(text ?? ''))
        .digest('hex');
}

function computeStablePagePropsHash(pageProps = {}) {
    return sha256Text(JSON.stringify(canonicalizeJson(pageProps)));
}

function listJsonPaths(value, prefix = '') {
    if (!isPlainObject(value) && !Array.isArray(value)) return prefix ? [prefix] : [];
    const paths = [];
    if (prefix) paths.push(prefix);
    const entries = Array.isArray(value) ? value.entries() : Object.entries(value);
    for (const [rawKey, child] of entries) {
        const key = String(rawKey);
        const childPath = prefix ? `${prefix}.${key}` : key;
        paths.push(...listJsonPaths(child, childPath));
    }
    return paths;
}

function jsonByteLength(value = {}) {
    return Buffer.byteLength(JSON.stringify(value), 'utf8');
}

function buildFotMobMatchUrl(externalId) {
    const id = normalizeText(externalId);
    if (!/^\d+$/.test(id)) throw new Error(`INVALID_EXTERNAL_ID:${externalId}`);
    return new URL(`/match/${id}`, FOTMOB_BASE_URL).href;
}

function externalIdFromUrl(value) {
    const text = normalizeText(value);
    if (!text) return null;
    try {
        const parsed = new URL(text, FOTMOB_BASE_URL);
        const matchPath = parsed.pathname.match(/\/match\/(\d+)(?:\/|$)/);
        if (matchPath) return matchPath[1];
        const hashId = parsed.hash.match(/#(\d+)$/);
        if (hashId) return hashId[1];
        return null;
    } catch {
        const matchPath = text.match(/\/match\/(\d+)(?:\/|$)/);
        if (matchPath) return matchPath[1];
        const hashId = text.match(/#(\d+)$/);
        return hashId ? hashId[1] : null;
    }
}

function safeErrorSummary(value) {
    return normalizeText(value)
        .replace(/https?:\/\/\S+/g, '[url]')
        .slice(0, 180);
}

function createAbortTimeout(timeoutMs) {
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    const timeoutHandle = controller
        ? setTimeout(() => {
              controller.abort(new Error(`FETCH_TIMEOUT:${timeoutMs}ms`));
          }, timeoutMs)
        : null;
    return { controller, timeoutHandle };
}

function clearAbortTimeout(timeoutHandle) {
    if (timeoutHandle) clearTimeout(timeoutHandle);
}

async function fetchHtml(requestUrl, dependencies = {}) {
    const fetchFn = dependencies.fetchFn || globalThis.fetch;
    if (typeof fetchFn !== 'function') {
        return { ok: false, error: 'FETCH_DEPENDENCY_MISSING', request_url: requestUrl, http_status: 0 };
    }
    const { controller, timeoutHandle } = createAbortTimeout(dependencies.timeoutMs || 15000);
    let response;
    try {
        response = await fetchFn(requestUrl, {
            method: 'GET',
            headers: {
                accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
                'accept-encoding': 'identity',
                referer: FOTMOB_BASE_URL,
                'user-agent':
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            },
            redirect: 'follow',
            signal: controller?.signal,
        });
    } catch (error) {
        clearAbortTimeout(timeoutHandle);
        return {
            ok: false,
            error: `FETCH_ERROR:${safeErrorSummary(error.message)}`,
            request_url: requestUrl,
            final_url: requestUrl,
            http_status: 0,
            body_byte_length: 0,
            body: '',
        };
    }
    clearAbortTimeout(timeoutHandle);

    let body = '';
    try {
        body = typeof response.text === 'function' ? await response.text() : '';
    } catch (error) {
        return {
            ok: false,
            error: `FETCH_BODY_READ_ERROR:${safeErrorSummary(error.message)}`,
            request_url: requestUrl,
            final_url: response.url || requestUrl,
            http_status: Number(response.status || 0),
            body_byte_length: 0,
            body: '',
        };
    }
    const httpStatus = Number(response.status || 0);
    return {
        ok: response.ok === true,
        error: response.ok === true ? null : `HTTP_${httpStatus}`,
        request_url: requestUrl,
        final_url: response.url || requestUrl,
        http_status: httpStatus,
        body_byte_length: Buffer.byteLength(body, 'utf8'),
        body,
    };
}

function extractNextDataJsonFromHtml(html) {
    if (!html || typeof html !== 'string') return { ok: false, error: 'INVALID_HTML' };
    const match =
        html.match(/<script\s+id=["']__NEXT_DATA__["']\s+type=["']application\/json["'][^>]*>([\s\S]*?)<\/script>/i) ||
        html.match(/<script[^>]*id=["']__NEXT_DATA__["'][^>]*>([\s\S]*?)<\/script>/i);
    if (!match || !match[1]) return { ok: false, error: 'NO_NEXT_DATA' };
    try {
        return { ok: true, data: JSON.parse(match[1].trim()) };
    } catch (error) {
        return { ok: false, error: `NEXT_DATA_PARSE_ERROR:${safeErrorSummary(error.message)}` };
    }
}

function getPageProps(nextData) {
    return isPlainObject(nextData?.props?.pageProps) ? nextData.props.pageProps : null;
}

function detectBlockMarkers(fetchResult = {}) {
    const markers = new Set();
    const status = Number(fetchResult.http_status || fetchResult.status || 0);
    if (status === 403) markers.add('http_403');
    if (status === 429) markers.add('http_429');
    const sample = `${safeErrorSummary(fetchResult.error)} ${normalizeText(fetchResult.body).slice(0, 2000)}`;
    for (const [name, pattern] of BLOCK_MARKER_PATTERNS) {
        if (pattern.test(sample)) markers.add(name);
    }
    return [...markers].sort();
}

function summarizeStructure(pageProps = {}) {
    const safePageProps = isPlainObject(pageProps) ? pageProps : {};
    const content = isPlainObject(safePageProps.content) ? safePageProps.content : {};
    const pagePropsPaths = listJsonPaths(safePageProps);
    const contentPaths = listJsonPaths(content);
    return {
        top_level_keys: Object.keys(safePageProps).sort(),
        has_content: isPlainObject(safePageProps.content),
        has_general: isPlainObject(safePageProps.general),
        has_header: isPlainObject(safePageProps.header),
        content_key_count: Object.keys(content).length,
        pageprops_path_count: pagePropsPaths.length,
        pageprops_content_path_count: contentPaths.length,
    };
}

function findDuplicates(values = []) {
    const seen = new Set();
    const duplicates = new Set();
    for (const value of values.map(normalizeText).filter(Boolean)) {
        if (seen.has(value)) duplicates.add(value);
        seen.add(value);
    }
    return duplicates;
}

function normalizeCandidateTarget(target = {}, enrichedByMatchId = new Map()) {
    const matchId = normalizeText(target.match_id);
    const enriched = enrichedByMatchId.get(matchId) || {};
    return {
        ...target,
        target_id: normalizeText(target.target_id || enriched.target_id),
        batch_id: normalizeText(target.batch_id || BATCH_ID),
        source: normalizeLower(target.source || SOURCE),
        route: normalizeText(target.route || ROUTE),
        raw_data_version: normalizeText(target.raw_data_version || RAW_VERSION),
        hash_strategy: normalizeText(target.hash_strategy || HASH_STRATEGY),
        match_id: matchId,
        external_id: normalizeText(target.external_id || enriched.external_id || enriched.schedule_external_id),
        schedule_external_id: normalizeText(enriched.schedule_external_id || target.external_id),
        source_page_url: normalizeText(enriched.source_page_url || target.source_page_url),
        source_page_url_base: normalizeText(enriched.source_page_url_base || target.source_page_url_base),
        source_url_fragment_external_id: normalizeText(
            enriched.source_url_fragment_external_id || target.source_url_fragment_external_id
        ),
        detail_external_id_candidate: normalizeText(
            target.detail_external_id_candidate ||
                enriched.detail_external_id_candidate ||
                enriched.source_url_fragment_external_id ||
                target.source_url_fragment_external_id
        ),
        detail_identity_source: normalizeText(
            target.detail_identity_source ||
                enriched.detail_identity_source ||
                (enriched.source_url_fragment_external_id || target.source_url_fragment_external_id
                    ? 'url_hash_fragment'
                    : null)
        ),
        accepted_detail_external_id: normalizeText(
            target.accepted_detail_external_id ||
                enriched.accepted_detail_external_id ||
                target.recapture_expected_identity
        ),
        observed_detail_external_id: normalizeText(
            enriched.observed_detail_external_id || target.observed_detail_external_id
        ),
        current_mapping_effective_status: normalizeText(
            target.current_mapping_effective_status || enriched.current_mapping_effective_status
        ),
        current_baseline_effective_status: normalizeText(
            target.current_baseline_effective_status || enriched.current_baseline_effective_status
        ),
        re_acceptance_execution_performed: normalizeBooleanFlag(
            target.re_acceptance_execution_performed ?? enriched.re_acceptance_execution_performed,
            false
        ),
        league_id: parseInteger(target.league_id, LEAGUE_ID),
        league_name: normalizeText(target.league_name || LEAGUE_NAME),
        season: normalizeText(target.season || SEASON),
        home_team: normalizeText(target.home_team || enriched.schedule_home_team),
        away_team: normalizeText(target.away_team || enriched.schedule_away_team),
        match_date: normalizeText(target.match_date || target.kickoff_time || enriched.schedule_date),
        kickoff_time: normalizeText(target.kickoff_time || target.match_date || enriched.schedule_date),
        status: normalizeLower(target.status),
        baseline_hash: normalizeLower(target.baseline_hash),
        identity_evidence_status: normalizeText(enriched.identity_evidence_status || target.identity_evidence_status),
    };
}

function extractEnrichedTargets(artifact = {}) {
    if (Array.isArray(artifact.enriched_targets)) return artifact.enriched_targets;
    if (Array.isArray(artifact.targets)) return artifact.targets;
    if (Array.isArray(artifact.candidate_targets)) return artifact.candidate_targets;
    return [];
}

function validateCandidateTargets(manifest = {}, enrichedArtifact = {}) {
    const enrichedByMatchId = new Map(
        extractEnrichedTargets(enrichedArtifact).map(target => [normalizeText(target.match_id), target])
    );
    const candidates = Array.isArray(manifest.candidate_targets)
        ? manifest.candidate_targets.map(target => normalizeCandidateTarget(target, enrichedByMatchId))
        : [];
    const errors = [];
    if (candidates.length !== TARGET_COUNT) errors.push(`candidate_targets must contain ${TARGET_COUNT} targets`);
    const duplicateExternalIds = findDuplicates(candidates.map(target => target.external_id));
    const duplicateMatchIds = findDuplicates(candidates.map(target => target.match_id));
    for (const target of candidates) {
        const targetErrors = [];
        if (!target.target_id) targetErrors.push('target_id missing');
        if (!/^\d+$/.test(target.external_id)) targetErrors.push('external_id must be numeric');
        if (target.schedule_external_id && target.schedule_external_id !== target.external_id) {
            targetErrors.push('schedule_external_id must match external_id');
        }
        if (target.source_url_fragment_external_id && target.source_url_fragment_external_id !== target.external_id) {
            targetErrors.push('source_url_fragment_external_id must match external_id');
        }
        if (target.match_id !== `${LEAGUE_ID}_20252026_${target.external_id}`) {
            targetErrors.push('match_id must match league/season/external_id');
        }
        if (duplicateExternalIds.has(target.external_id)) targetErrors.push('duplicate external_id');
        if (duplicateMatchIds.has(target.match_id)) targetErrors.push('duplicate match_id');
        if (target.batch_id !== BATCH_ID) targetErrors.push('batch_id mismatch');
        if (target.source !== SOURCE) targetErrors.push('source mismatch');
        if (target.route !== ROUTE) targetErrors.push('route mismatch');
        if (target.raw_data_version !== RAW_VERSION) targetErrors.push('raw_data_version mismatch');
        if (target.hash_strategy !== HASH_STRATEGY) targetErrors.push('hash_strategy mismatch');
        if (target.league_id !== LEAGUE_ID) targetErrors.push('league_id mismatch');
        if (target.league_name !== LEAGUE_NAME) targetErrors.push('league_name mismatch');
        if (target.season !== SEASON) targetErrors.push('season mismatch');
        if (!target.home_team) targetErrors.push('home_team missing');
        if (!target.away_team) targetErrors.push('away_team missing');
        if (!target.match_date && !target.kickoff_time) targetErrors.push('match_date/kickoff_time missing');
        if (!/^[a-f0-9]{64}$/.test(target.baseline_hash)) targetErrors.push('baseline_hash must be 64 hex');
        if (/fake|invented|placeholder/i.test(Object.values(target).join(' '))) {
            targetErrors.push('fake/invented/placeholder marker blocked');
        }
        if (targetErrors.length > 0) {
            errors.push(`${target.match_id || target.external_id}: ${targetErrors.join(', ')}`);
        }
    }
    return {
        ok: errors.length === 0,
        errors,
        candidates,
        duplicate_external_id_count: duplicateExternalIds.size,
        duplicate_match_id_count: duplicateMatchIds.size,
    };
}

function validateInputArtifacts({
    manifest = {},
    planArtifact = {},
    enrichedArtifact = {},
    identityAcceptance = {},
    baselineAcceptance = {},
} = {}) {
    const errors = [];
    if (normalizeText(manifest.batch_id) !== BATCH_ID) errors.push('manifest batch_id mismatch');
    if (normalizeLower(manifest.source) !== SOURCE) errors.push('manifest source mismatch');
    if (normalizeText(manifest.route) !== ROUTE) errors.push('manifest route mismatch');
    if (normalizeText(manifest.raw_data_version) !== RAW_VERSION) errors.push('manifest raw_data_version mismatch');
    if (normalizeText(manifest.hash_strategy) !== HASH_STRATEGY) errors.push('manifest hash_strategy mismatch');
    if (normalizeText(manifest.next_required_step) !== 'controlled_no_write_payload_recapture_execution') {
        errors.push('manifest next_required_step must be controlled_no_write_payload_recapture_execution');
    }
    if (
        normalizeText(manifest.phase_5_21_l2v3an_planning_status) !==
        'completed_controlled_no_write_payload_recapture_planning'
    ) {
        errors.push('manifest L2V3AN planning status must be completed');
    }
    if (manifest.raw_write_execution_ready !== false) errors.push('manifest raw_write_execution_ready must be false');
    if (manifest.db_write_performed !== false) errors.push('manifest db_write_performed must be false');
    if (manifest.raw_match_data_insert_performed !== false) {
        errors.push('manifest raw_match_data_insert_performed must be false');
    }
    if (normalizeText(planArtifact.artifact_status) !== 'completed_controlled_no_write_payload_recapture_planning') {
        errors.push('L2V3AN plan artifact must be completed');
    }
    if (normalizeText(planArtifact.planned_source_type) !== 'controlled_live_recapture_in_memory') {
        errors.push('L2V3AN planned source type mismatch');
    }
    if (Number(planArtifact.planned_target_count) !== TARGET_COUNT) {
        errors.push('L2V3AN planned target count must be 50');
    }
    if (planArtifact.live_recapture_execution_performed !== false) {
        errors.push('L2V3AN must not have already performed live recapture');
    }
    if (
        planArtifact.full_payload_storage_allowed !== false ||
        planArtifact.full_payload_print_allowed !== false ||
        planArtifact.in_memory_only !== true
    ) {
        errors.push('L2V3AN payload safety flags must remain no-store/no-print/in-memory');
    }
    if (planArtifact.raw_write_execution_ready !== false || planArtifact.raw_write_execution_performed !== false) {
        errors.push('L2V3AN must not be raw write ready or executed');
    }
    if (
        normalizeText(enrichedArtifact.artifact_status) !==
        'completed_controlled_no_write_enriched_target_regeneration_execution'
    ) {
        errors.push('L2V3AA enriched targets artifact must be completed');
    }
    if (Number(enrichedArtifact.regenerated_target_count) !== TARGET_COUNT) {
        errors.push('L2V3AA regenerated target count must be 50');
    }
    if (
        normalizeText(identityAcceptance.artifact_status) !== 'completed_identity_mapping_acceptance_review_execution'
    ) {
        errors.push('L2V3AE identity mapping acceptance must be completed');
    }
    if (Number(identityAcceptance.accepted_mapping_count) !== TARGET_COUNT) {
        errors.push('L2V3AE accepted mapping count must be 50');
    }
    if (normalizeText(baselineAcceptance.artifact_status) !== 'completed_baseline_acceptance_execution') {
        errors.push('L2V3AG baseline acceptance must be completed');
    }
    if (Number(baselineAcceptance.baseline_accepted_count) !== TARGET_COUNT) {
        errors.push('L2V3AG baseline accepted count must be 50');
    }
    const candidateValidation = validateCandidateTargets(manifest, enrichedArtifact);
    errors.push(...candidateValidation.errors);
    return { ok: errors.length === 0, errors, candidate_validation: candidateValidation };
}

function attachIdentityContract(fetchResult = {}, contract = {}) {
    return {
        ...fetchResult,
        identity_contract: contract,
        recapture_request_identity: contract.recapture_request_identity || null,
        recapture_expected_identity: contract.recapture_expected_identity || null,
        route_identity_strategy: contract.route_identity_strategy,
        canonical_identity_source: contract.canonical_identity_source,
    };
}

function buildIdentityContractBlockedFetchResult(target = {}, contract = {}) {
    return attachIdentityContract(
        {
            ok: false,
            error: `RECAPTURE_IDENTITY_CONTRACT_BLOCKED:${(contract.blockers || []).join(',')}`,
            request_url: null,
            final_url: null,
            http_status: 0,
            body_byte_length: 0,
            body: '',
            identity_contract_blocked: true,
        },
        contract
    );
}

function resolveFetchResultForTarget(target, index, input = {}, dependencies = {}) {
    const contract = resolveRecaptureIdentityContract({ target });
    if (contract.recapture_request_allowed !== true) {
        return buildIdentityContractBlockedFetchResult(target, contract);
    }
    const byExternalId = dependencies.fetchResultsByExternalId || {};
    if (byExternalId[contract.recapture_request_identity]) {
        return attachIdentityContract(byExternalId[contract.recapture_request_identity], contract);
    }
    if (byExternalId[target.external_id]) return attachIdentityContract(byExternalId[target.external_id], contract);
    if (Array.isArray(dependencies.fetchResults) && dependencies.fetchResults[index]) {
        return attachIdentityContract(dependencies.fetchResults[index], contract);
    }
    const requestUrl = buildFotMobMatchUrl(contract.recapture_request_identity);
    const fetchHtmlFn = dependencies.fetchHtmlFn || fetchHtml;
    const fetchResult = fetchHtmlFn(requestUrl, {
        fetchFn: dependencies.fetchFn,
        timeoutMs: input.timeoutMs,
    });
    return Promise.resolve(fetchResult).then(result => attachIdentityContract(result, contract));
}

function buildBaseResult(target = {}, fetchResult = {}) {
    const contract = fetchResult.identity_contract || resolveRecaptureIdentityContract({ target });
    const requestUrl =
        fetchResult.request_url ||
        (contract.recapture_request_identity ? buildFotMobMatchUrl(contract.recapture_request_identity) : null);
    const finalUrl = fetchResult.final_url || requestUrl;
    return {
        target_id: target.target_id,
        match_id: target.match_id,
        external_id: target.external_id,
        schedule_external_id: target.schedule_external_id || target.external_id,
        source_url_fragment_external_id: target.source_url_fragment_external_id || null,
        source_url_fragment_external_id_match: target.source_url_fragment_external_id
            ? target.source_url_fragment_external_id === target.external_id
            : null,
        detail_external_id_candidate:
            contract.detail_external_id_candidate || target.detail_external_id_candidate || null,
        detail_identity_source: contract.detail_identity_source || target.detail_identity_source || null,
        accepted_detail_external_id: contract.accepted_detail_external_id || target.accepted_detail_external_id || null,
        recapture_request_identity: contract.recapture_request_identity || null,
        recapture_expected_identity: contract.recapture_expected_identity || null,
        route_identity_strategy: contract.route_identity_strategy,
        canonical_identity_source: contract.canonical_identity_source,
        identity_contract_blocked: fetchResult.identity_contract_blocked === true,
        identity_contract_blockers: contract.blockers || [],
        baseline_update_allowed: contract.baseline_update_allowed === true,
        baseline_re_acceptance_allowed: contract.baseline_re_acceptance_allowed === true,
        raw_write_execution_ready: false,
        home_team: target.home_team,
        away_team: target.away_team,
        kickoff_time: target.kickoff_time || target.match_date || null,
        status: target.status || null,
        request_url_external_id: externalIdFromUrl(requestUrl),
        final_url_external_id: externalIdFromUrl(finalUrl),
        http_status: Number(fetchResult.http_status || fetchResult.status || 0),
        parsed: false,
        block_markers: detectBlockMarkers(fetchResult),
        identity_match_status: 'not_evaluated',
        date_route_status: 'not_evaluated',
        schedule_external_id_vs_detail_external_id_status: 'not_evaluated',
        team_date_status_match_status: 'not_evaluated',
        date_compatibility_status: 'not_evaluated',
        page_url_base_match_status: 'not_evaluated',
        stable_pageprops_payload_v1_hash: null,
        hash_matches_baseline: false,
        hash_validation_status: 'not_evaluated',
        payload_size_summary: {
            body_byte_length: Number(fetchResult.body_byte_length || 0),
            pageprops_json_byte_length: null,
        },
        structural_summary: null,
        blocker_list: [],
        stopping_rule_triggered: null,
        target_status: 'blocked',
        safe_error_summary: safeErrorSummary(fetchResult.error) || null,
        full_payload_saved: false,
        full_payload_printed: false,
    };
}

function firstStoppingRule(result = {}) {
    if (result.identity_contract_blocked === true) return 'identity_contract_blocked';
    if ((result.block_markers || []).includes('http_403')) return 'http_403';
    if ((result.block_markers || []).includes('http_429')) return 'http_429';
    if ((result.block_markers || []).length > 0) return 'captcha_or_block_marker';
    if (result.parsed !== true) return 'parse_failure';
    if (result.identity_match_status === 'mismatch') return 'identity_mismatch';
    if (result.date_route_status === 'mismatch') return 'date_or_route_mismatch';
    if (result.hash_validation_status === 'hash_mismatch') return 'hash_mismatch_unexplained';
    if (result.structural_summary?.has_content !== true) return 'unexpected_schema_drift';
    return null;
}

function finalizeTargetResult(result = {}) {
    const stoppingRule = firstStoppingRule(result);
    if (!stoppingRule) {
        return {
            ...result,
            blocker_list: [],
            stopping_rule_triggered: null,
            target_status: 'recapture_succeeded',
        };
    }
    const blockers = new Set(result.blocker_list || []);
    blockers.add(stoppingRule);
    return {
        ...result,
        blocker_list: [...blockers].sort(),
        stopping_rule_triggered: stoppingRule,
        target_status: stoppingRule === 'hash_mismatch_unexplained' ? 'hash_mismatch_blocked' : 'blocked',
    };
}

async function recaptureTarget(target = {}, index = 0, input = {}, dependencies = {}) {
    const fetchResult = await resolveFetchResultForTarget(target, index, input, dependencies);
    const base = buildBaseResult(target, fetchResult);
    if (fetchResult.identity_contract_blocked === true) {
        return finalizeTargetResult({
            ...base,
            blocker_list: [
                ...new Set([...(base.blocker_list || []), ...(base.identity_contract_blockers || [])]),
            ].sort(),
        });
    }
    if ((base.block_markers || []).length > 0) return finalizeTargetResult(base);
    if (!fetchResult.ok || Number(fetchResult.http_status || 0) !== 200) {
        return finalizeTargetResult({
            ...base,
            safe_error_summary: safeErrorSummary(fetchResult.error || 'HTTP_NON_200'),
        });
    }
    const extraction = extractNextDataJsonFromHtml(fetchResult.body);
    if (!extraction.ok) {
        return finalizeTargetResult({
            ...base,
            safe_error_summary: extraction.error,
        });
    }
    const pageProps = getPageProps(extraction.data);
    if (!pageProps) {
        return finalizeTargetResult({
            ...base,
            parsed: false,
            safe_error_summary: 'PAGE_PROPS_NOT_FOUND',
        });
    }

    const pagePropsHash = computeStablePagePropsHash(pageProps);
    const structure = summarizeStructure(pageProps);
    const routeIdentity = reconcileRouteIdentity({
        target,
        pageProps,
        requestedScheduleExternalId: target.schedule_external_id || target.external_id,
        requestedDetailExternalId:
            fetchResult.identity_contract?.recapture_expected_identity || target.accepted_detail_external_id,
        requestedUrl: target.source_page_url || null,
        requestedPageUrlBase: target.source_page_url_base || null,
        finalUrl: fetchResult.final_url || fetchResult.request_url || base.request_url,
        acceptedIdentityMappingPresent: true,
    });
    const identityMismatch =
        routeIdentity.schedule_external_id_vs_detail_external_id_status &&
        routeIdentity.schedule_external_id_vs_detail_external_id_status !== 'identity_match';
    const dateRouteMismatch = [
        routeIdentity.page_url_base_match_status,
        routeIdentity.team_date_status_match_status,
        routeIdentity.date_compatibility_status,
    ].some(status =>
        [
            'mismatch',
            'team_mismatch',
            'date_mismatch',
            'team_date_status_mismatch',
            'reverse_fixture_detected',
            'cross_season_slug_reuse',
            'unresolved_large_gap',
            'unknown',
        ].includes(normalizeText(status))
    );
    const hashMatches = pagePropsHash === target.baseline_hash;
    const blockers = new Set(routeIdentity.safety_blockers || []);
    if (identityMismatch) blockers.add('identity_mismatch');
    if (dateRouteMismatch) blockers.add('date_or_route_mismatch');
    if (!hashMatches) {
        blockers.add(identityMismatch ? 'hash_mismatch_secondary_to_identity_mismatch' : 'hash_mismatch_unexplained');
    }
    if (structure.has_content !== true) blockers.add('unexpected_schema_drift');
    const hashValidationStatus = hashMatches
        ? 'hash_match'
        : identityMismatch
          ? 'secondary_to_identity_mismatch'
          : 'hash_mismatch';

    return finalizeTargetResult({
        ...base,
        parsed: true,
        observed_detail_external_id: routeIdentity.observed_detail_external_id || null,
        identity_match_status: identityMismatch ? 'mismatch' : 'match',
        date_route_status: dateRouteMismatch ? 'mismatch' : 'match',
        schedule_external_id_vs_detail_external_id_status:
            routeIdentity.schedule_external_id_vs_detail_external_id_status || 'unknown',
        team_date_status_match_status: routeIdentity.team_date_status_match_status || 'unknown',
        date_compatibility_status: routeIdentity.date_compatibility_status || 'unknown',
        page_url_base_match_status: routeIdentity.page_url_base_match_status || 'unknown',
        stable_pageprops_payload_v1_hash: pagePropsHash,
        hash_matches_baseline: hashMatches,
        hash_validation_status: hashValidationStatus,
        baseline_update_allowed: false,
        baseline_re_acceptance_allowed: false,
        payload_size_summary: {
            body_byte_length: Number(fetchResult.body_byte_length || Buffer.byteLength(fetchResult.body || '', 'utf8')),
            pageprops_json_byte_length: jsonByteLength(pageProps),
        },
        structural_summary: structure,
        blocker_list: [...blockers].sort(),
        safe_error_summary: null,
    });
}

function countWhere(rows = [], predicate) {
    return rows.filter(predicate).length;
}

function summarizeResults(results = [], targetCount = TARGET_COUNT) {
    const attempted = results.length;
    const success = countWhere(results, item => item.target_status === 'recapture_succeeded');
    const failed = countWhere(
        results,
        item => item.target_status !== 'recapture_succeeded' && item.stopping_rule_triggered === 'parse_failure'
    );
    const blocked = countWhere(results, item => item.target_status !== 'recapture_succeeded');
    const http200 = countWhere(results, item => item.http_status === 200);
    const http403 = countWhere(
        results,
        item => item.http_status === 403 || (item.block_markers || []).includes('http_403')
    );
    const http429 = countWhere(
        results,
        item => item.http_status === 429 || (item.block_markers || []).includes('http_429')
    );
    const parseSuccess = countWhere(results, item => item.parsed === true);
    const parseFailure = attempted - parseSuccess;
    const identityMatch = countWhere(results, item => item.identity_match_status === 'match');
    const identityMismatch = countWhere(results, item => item.identity_match_status === 'mismatch');
    const dateRouteMatch = countWhere(results, item => item.date_route_status === 'match');
    const dateRouteMismatch = countWhere(results, item => item.date_route_status === 'mismatch');
    const hashComputed = countWhere(results, item => Boolean(item.stable_pageprops_payload_v1_hash));
    const hashMismatch = countWhere(results, item => item.hash_validation_status === 'hash_mismatch');
    const stoppedEarly = attempted < targetCount || blocked > 0;
    const firstBlocker = results.find(item => item.stopping_rule_triggered);
    const partial = success > 0 && success < targetCount;
    const allSuccess = success === targetCount && attempted === targetCount && blocked === 0;
    return {
        target_count: targetCount,
        attempted_recapture_count: attempted,
        successful_recapture_count: success,
        failed_recapture_count: failed,
        blocked_recapture_count: blocked,
        unattempted_recapture_count: Math.max(targetCount - attempted, 0),
        stopped_early: stoppedEarly,
        stop_reason: firstBlocker?.stopping_rule_triggered || null,
        http_200_count: http200,
        http_403_count: http403,
        http_429_count: http429,
        parse_success_count: parseSuccess,
        parse_failure_count: parseFailure,
        identity_match_count: identityMatch,
        identity_mismatch_count: identityMismatch,
        date_route_match_count: dateRouteMatch,
        date_route_mismatch_count: dateRouteMismatch,
        hash_computed_count: hashComputed,
        hash_mismatch_count: hashMismatch,
        recapture_result_status: allSuccess
            ? 'completed_success_no_write'
            : partial
              ? 'partial_success_blocked_no_write'
              : 'blocked_no_write',
        recommended_next_step: allSuccess ? SUCCESS_NEXT_STEP : partial ? PARTIAL_NEXT_STEP : BLOCKED_NEXT_STEP,
        next_required_step: allSuccess
            ? 'controlled_recapture_result_verification_planning'
            : partial
              ? 'partial_recapture_review_planning'
              : 'no_write_payload_recapture_blocker_investigation',
    };
}

async function sleep(ms) {
    if (!ms) return;
    await new Promise(resolve => {
        setTimeout(resolve, ms);
    });
}

async function recaptureTargetsSequential(candidates = [], input = {}, dependencies = {}) {
    const results = [];
    for (let index = 0; index < candidates.length; index += 1) {
        if (index > 0) await sleep(input.requestDelayMs);
        const result = await recaptureTarget(candidates[index], index, input, dependencies);
        results.push(result);
        if (typeof dependencies.progress === 'function') {
            dependencies.progress({
                index: index + 1,
                total: candidates.length,
                match_id: result.match_id,
                external_id: result.external_id,
                target_status: result.target_status,
                http_status: result.http_status,
                hash: result.stable_pageprops_payload_v1_hash || null,
                hash_matches_baseline: result.hash_matches_baseline,
                stop_reason: result.stopping_rule_triggered,
            });
        }
        if (result.stopping_rule_triggered) break;
    }
    return results;
}

function buildArtifact({ input = {}, summary = {}, results = [], generatedAt, status } = {}) {
    return {
        artifact_type: 'no_write_payload_recapture_result',
        artifact_status: status,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        execution_status: status,
        generated_at: generatedAt,
        reviewed_input_artifact_count: REVIEWED_INPUTS.length,
        reviewed_input_artifact_paths: Object.fromEntries(REVIEWED_INPUTS),
        no_write_payload_recapture_execution_performed: true,
        live_recapture_performed: summary.attempted_recapture_count > 0,
        detail_fetch_performed: summary.attempted_recapture_count > 0,
        network_request_performed: summary.attempted_recapture_count > 0,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        raw_write_execution_performed: false,
        raw_write_runner_write_mode_used: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        target_count: summary.target_count,
        attempted_recapture_count: summary.attempted_recapture_count,
        successful_recapture_count: summary.successful_recapture_count,
        failed_recapture_count: summary.failed_recapture_count,
        blocked_recapture_count: summary.blocked_recapture_count,
        unattempted_recapture_count: summary.unattempted_recapture_count,
        stopped_early: summary.stopped_early,
        stop_reason: summary.stop_reason,
        http_200_count: summary.http_200_count,
        http_403_count: summary.http_403_count,
        http_429_count: summary.http_429_count,
        parse_success_count: summary.parse_success_count,
        parse_failure_count: summary.parse_failure_count,
        identity_match_count: summary.identity_match_count,
        identity_mismatch_count: summary.identity_mismatch_count,
        date_route_match_count: summary.date_route_match_count,
        date_route_mismatch_count: summary.date_route_mismatch_count,
        hash_computed_count: summary.hash_computed_count,
        hash_mismatch_count: summary.hash_mismatch_count,
        full_payload_storage_allowed: false,
        full_payload_print_allowed: false,
        full_payload_saved: false,
        full_payload_printed: false,
        cookies_tokens_headers_persisted: false,
        in_memory_only: true,
        safe_metadata_artifact_written: input.writeFiles !== false,
        safe_metadata_result_fields: [
            'target_id',
            'match_id',
            'external_id',
            'http_status',
            'parsed',
            'block_markers',
            'identity_match_status',
            'date_route_status',
            'stable_pageprops_payload_v1_hash',
            'hash_validation_status',
            'payload_size_summary',
            'structural_summary',
            'blocker_list',
            'stopping_rule_triggered',
        ],
        per_target_results: results,
        recapture_result_status: summary.recapture_result_status,
        raw_write_execution_ready: false,
        recapture_success_does_not_authorize_raw_write: true,
        requires_separate_raw_write_execution_authorization: true,
        recommended_next_step: summary.recommended_next_step,
        next_required_step: summary.next_required_step,
    };
}

function buildReport(artifact = {}) {
    const rows = (artifact.per_target_results || [])
        .map(
            item =>
                `| ${item.match_id} | ${item.external_id} | ${item.http_status} | ${item.parsed} | ${item.identity_match_status} | ${item.date_route_status} | ${item.hash_validation_status} | ${item.stopping_rule_triggered || ''} | ${(item.blocker_list || []).join(',')} |`
        )
        .join('\n');
    return `# Data Entrypoint Governance - Phase 5.21 L2V3AO

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- execution_status=${artifact.execution_status}
- no_write_payload_recapture_execution_performed=true
- live_recapture_performed=${artifact.live_recapture_performed}
- detail_fetch_performed=${artifact.detail_fetch_performed}
- network_request_performed=${artifact.network_request_performed}
- target_count=${artifact.target_count}
- attempted_recapture_count=${artifact.attempted_recapture_count}
- successful_recapture_count=${artifact.successful_recapture_count}
- failed_recapture_count=${artifact.failed_recapture_count}
- blocked_recapture_count=${artifact.blocked_recapture_count}
- stopped_early=${artifact.stopped_early}
- stop_reason=${artifact.stop_reason || 'none'}

## Safety

- db_write_performed=false
- raw_match_data_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- raw_write_execution_performed=false
- raw_write_runner_write_mode_used=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false
- full_payload_storage_allowed=false
- full_payload_print_allowed=false
- full_payload_saved=false
- full_payload_printed=false
- cookies_tokens_headers_persisted=false
- in_memory_only=true
- safe_metadata_only=true

## Result Counts

- http_200_count=${artifact.http_200_count}
- http_403_count=${artifact.http_403_count}
- http_429_count=${artifact.http_429_count}
- parse_success_count=${artifact.parse_success_count}
- parse_failure_count=${artifact.parse_failure_count}
- identity_match_count=${artifact.identity_match_count}
- identity_mismatch_count=${artifact.identity_mismatch_count}
- date_route_match_count=${artifact.date_route_match_count}
- date_route_mismatch_count=${artifact.date_route_mismatch_count}
- hash_computed_count=${artifact.hash_computed_count}
- hash_mismatch_count=${artifact.hash_mismatch_count}

## Per Target Safe Metadata

| match_id | external_id | http_status | parsed | identity | date_route | hash_status | stop | blockers |
| -------- | ----------- | ----------- | ------ | -------- | ---------- | ----------- | ---- | -------- |
${rows}

## Raw Write Relationship

- recapture_success_does_not_authorize_raw_write=true
- raw_write_execution_ready=false
- requires_separate_raw_write_execution_authorization=true
- recommended_next_step=${artifact.recommended_next_step}

## Explicit Non-Execution

- no DB writes
- no raw_match_data inserts
- no matches writes
- no matches.external_id changes
- no raw write execution
- no raw write runner write mode
- no parser/features/training/prediction
- no browser/proxy/captcha bypass
- no full payload printed or saved
`;
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    return {
        ...manifest,
        phase_5_21_l2v3ao_execution_status: artifact.execution_status,
        phase_5_21_l2v3ao_artifact_path: RESULT_ARTIFACT_PATH,
        phase_5_21_l2v3ao_report_path: REPORT_PATH,
        no_write_payload_recapture_execution_status: artifact.recapture_result_status,
        no_write_payload_recapture_execution_performed: true,
        live_recapture_performed: artifact.live_recapture_performed,
        detail_fetch_performed: artifact.detail_fetch_performed,
        network_request_performed: artifact.network_request_performed,
        db_write_performed: false,
        raw_match_data_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        raw_write_execution_performed: false,
        raw_write_runner_write_mode_used: false,
        target_count: artifact.target_count,
        attempted_recapture_count: artifact.attempted_recapture_count,
        successful_recapture_count: artifact.successful_recapture_count,
        failed_recapture_count: artifact.failed_recapture_count,
        blocked_recapture_count: artifact.blocked_recapture_count,
        stopped_early: artifact.stopped_early,
        stop_reason: artifact.stop_reason,
        identity_match_count: artifact.identity_match_count,
        identity_mismatch_count: artifact.identity_mismatch_count,
        date_route_match_count: artifact.date_route_match_count,
        date_route_mismatch_count: artifact.date_route_mismatch_count,
        hash_computed_count: artifact.hash_computed_count,
        hash_mismatch_count: artifact.hash_mismatch_count,
        full_payload_saved: false,
        full_payload_printed: false,
        in_memory_only: true,
        raw_write_execution_ready: false,
        recapture_success_does_not_authorize_raw_write: true,
        requires_separate_raw_write_execution_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
        next_required_step: artifact.next_required_step,
    };
}

async function runNoWritePayloadRecaptureExecution(rawInput = {}, dependencies = {}) {
    const validation = validateExecutionInput(rawInput);
    if (!validation.ok) return { ok: false, status: 2, errors: validation.errors };
    const input = validation.value;
    const readJson = dependencies.readJsonFile || readJsonFile;
    const manifest = dependencies.manifest || readJson(input.manifest);
    const planArtifact = dependencies.planArtifact || readJson(input.planArtifact);
    const enrichedArtifact = dependencies.enrichedArtifact || readJson(input.enrichedTargets);
    const identityAcceptance = dependencies.identityAcceptance || readJson(input.identityAcceptance);
    const baselineAcceptance = dependencies.baselineAcceptance || readJson(input.baselineAcceptance);
    const gate = validateInputArtifacts({
        manifest,
        planArtifact,
        enrichedArtifact,
        identityAcceptance,
        baselineAcceptance,
    });
    if (!gate.ok) return { ok: false, status: 3, errors: gate.errors, gate };
    const generatedAt = dependencies.generatedAt || new Date().toISOString();
    const progress =
        dependencies.progress ||
        (summary => {
            process.stderr.write(
                `[L2V3AO_RECAPTURE] ${summary.index}/${summary.total} match_id=${summary.match_id} external_id=${summary.external_id} status=${summary.target_status} http=${summary.http_status} hash=${summary.hash || 'none'} stop=${summary.stop_reason || 'none'}\n`
            );
        });
    const results = await recaptureTargetsSequential(gate.candidate_validation.candidates, input, {
        ...dependencies,
        progress,
    });
    const summary = summarizeResults(results, TARGET_COUNT);
    const status = summary.recapture_result_status === 'completed_success_no_write' ? SUCCESS_STATUS : BLOCKED_STATUS;
    const artifact = buildArtifact({ input, summary, results, generatedAt, status });
    const report = buildReport(artifact);
    const updatedManifest = updateManifestMetadata(manifest, artifact);
    if (input.writeFiles !== false) {
        const writeJson = dependencies.writeJsonFile || writeJsonFile;
        const writeText = dependencies.writeTextFile || writeTextFile;
        writeJson(input.artifactOutput, artifact);
        writeText(input.reportOutput, report);
        writeJson(input.manifest, updatedManifest);
    }
    return {
        ok: summary.recapture_result_status === 'completed_success_no_write',
        status: summary.recapture_result_status === 'completed_success_no_write' ? 0 : 4,
        artifact,
        report,
        updated_manifest: updatedManifest,
        results,
        summary,
    };
}

function helpText() {
    return `L2V3AO controlled no-write payload recapture execution.

Required yes flags:
  --no-write-recapture-authorization=yes
  --network-authorization=yes
  --match-detail-recapture-authorization=yes
  --allow-no-write-recapture-execution=yes

Required no flags include DB/raw/matches writes, raw write execution, write mode,
browser/proxy runtime, parser/features/training/prediction, full payload print/save,
cookie/token/header persistence, and uncontrolled retry.
`;
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const args = Array.isArray(argv) ? parseArgs(argv) : argv;
    if (args.help) {
        process.stdout.write(helpText());
        return { status: 0 };
    }
    const result = await runNoWritePayloadRecaptureExecution(args, dependencies);
    const output = result.artifact
        ? {
              ok: result.ok,
              status: result.status,
              phase: PHASE,
              artifact: RESULT_ARTIFACT_PATH,
              report: REPORT_PATH,
              execution_status: result.artifact.execution_status,
              recapture_result_status: result.artifact.recapture_result_status,
              attempted_recapture_count: result.artifact.attempted_recapture_count,
              successful_recapture_count: result.artifact.successful_recapture_count,
              blocked_recapture_count: result.artifact.blocked_recapture_count,
              stopped_early: result.artifact.stopped_early,
              stop_reason: result.artifact.stop_reason,
              db_write_performed: false,
              raw_match_data_insert_performed: false,
              raw_write_execution_performed: false,
              raw_write_execution_ready: false,
              recommended_next_step: result.artifact.recommended_next_step,
          }
        : { ok: false, status: result.status, errors: result.errors };
    process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
    return { status: result.status };
}

module.exports = {
    PHASE,
    PHASE_NAME,
    MANIFEST_PATH,
    PLAN_ARTIFACT_PATH,
    ENRICHED_TARGETS_PATH,
    IDENTITY_ACCEPTANCE_PATH,
    BASELINE_ACCEPTANCE_PATH,
    RESULT_ARTIFACT_PATH,
    REPORT_PATH,
    SUCCESS_STATUS,
    BLOCKED_STATUS,
    SOURCE,
    ROUTE,
    RAW_VERSION,
    HASH_STRATEGY,
    BATCH_ID,
    TARGET_COUNT,
    parseArgs,
    normalizeBooleanFlag,
    validateExecutionInput,
    canonicalizeJson,
    computeStablePagePropsHash,
    buildFotMobMatchUrl,
    externalIdFromUrl,
    fetchHtml,
    extractNextDataJsonFromHtml,
    getPageProps,
    detectBlockMarkers,
    summarizeStructure,
    validateCandidateTargets,
    validateInputArtifacts,
    recaptureTarget,
    recaptureTargetsSequential,
    summarizeResults,
    buildArtifact,
    buildReport,
    updateManifestMetadata,
    runNoWritePayloadRecaptureExecution,
    runCli,
};

if (require.main === module) {
    runCli()
        .then(result => {
            process.exitCode = result.status;
        })
        .catch(error => {
            process.stderr.write(`${error.stack || error.message}\n`);
            process.exitCode = 1;
        });
}
