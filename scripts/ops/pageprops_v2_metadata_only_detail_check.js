#!/usr/bin/env node
/* eslint-disable complexity, max-lines, max-statements */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const {
    buildFotMobMatchUrl,
    fetchHtml,
    extractNextDataJsonFromHtml,
    getPageProps,
} = require('./pageprops_v2_no_write_preview');
const {
    extractObservedMetadata,
    reconcileRouteIdentity,
    DATE_MATCH,
    SAME_UTC_DAY,
    TIMEZONE_ONLY_MISMATCH,
    POSTPONED_OR_RESCHEDULED_EXPLAINED,
    REVERSE_FIXTURE_DETECTED,
    CROSS_SEASON_SLUG_REUSE,
    UNRESOLVED_LARGE_GAP,
    UNKNOWN_DATE_COMPATIBILITY,
} = require('../../src/infrastructure/services/FotMobRouteIdentityReconciler');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MANIFEST_PATH = 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json';
const INVESTIGATION_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_date_rule_investigation.phase521l2v3o.json';
const VERIFICATION_ARTIFACT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.expanded_date_rule_verification.phase521l2v3n.json';
const ARTIFACT_OUTPUT_PATH =
    'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.metadata_only_detail_check.phase521l2v3p.json';
const REPORT_PATH = 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3P.md';
const PHASE = 'Phase 5.21L2V3P';
const PHASE_NAME = 'controlled_no_write_metadata_only_detail_check';
const PHASE_STATUS = 'completed_controlled_no_write_metadata_only_detail_check';
const SOURCE = 'fotmob';
const ROUTE = 'html_hydration';
const LEAGUE_ID = 53;
const LEAGUE_NAME = 'Ligue 1';
const SEASON = '2025/2026';
const TARGET_COUNT = 42;
const GENERATED_AT = '2026-05-20T00:00:00Z';
const DEFAULT_REQUEST_DELAY_MS = 750;
const DEFAULT_REQUEST_TIMEOUT_MS = 15000;
const PARSE_FAILURE_STOP_THRESHOLD = 3;
const HTTP_NON_200_STOP_THRESHOLD = 3;
const SAFE_REVIEW_DATE_STATUSES = new Set([
    DATE_MATCH,
    SAME_UTC_DAY,
    TIMEZONE_ONLY_MISMATCH,
    POSTPONED_OR_RESCHEDULED_EXPLAINED,
]);
const BLOCKING_DATE_STATUSES = new Set([
    REVERSE_FIXTURE_DETECTED,
    CROSS_SEASON_SLUG_REUSE,
    UNRESOLVED_LARGE_GAP,
    UNKNOWN_DATE_COMPATIBILITY,
]);
const REQUIRED_YES_FLAGS = Object.freeze([
    'metadataOnlyPhaseAuthorization',
    'controlledMetadataOnlyCheckAuthorization',
    'networkAuthorization',
]);
const REQUIRED_NO_FLAGS = Object.freeze([
    'allowDbWrite',
    'allowRawMatchDataWrite',
    'allowMatchesWrite',
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
]);
const BLOCKED_TRUE_FLAGS = Object.freeze([
    'allowControlledWrite',
    'executeWrite',
    'commit',
    'finalDbWriteConfirmation',
    'acceptIdentityMapping',
    'acceptBaseline',
    'baselineAcceptanceAuthorization',
    'rawWriteRetryAuthorization',
    'rawWriteReadyForExecution',
]);
const BLOCK_MARKER_RULES = Object.freeze([
    ['captcha', /captcha/i],
    ['cloudflare_challenge', /cloudflare|attention required/i],
    ['verify_human', /verify (you are )?human|human verification/i],
    ['access_denied', /access denied|forbidden/i],
    ['rate_limit', /too many requests|rate limit/i],
    ['bot_challenge', /bot detection|bot check|robot check/i],
]);

function absolutePath(filePath) {
    return path.join(PROJECT_ROOT, filePath);
}

function readJsonFile(filePath) {
    return JSON.parse(fs.readFileSync(absolutePath(filePath), 'utf8'));
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

function parseCsv(value) {
    return normalizeText(value)
        .split(',')
        .map(item => item.trim())
        .filter(Boolean);
}

function toCamelKey(rawKey) {
    return normalizeText(rawKey).replace(/[-_]([a-z0-9])/g, (_match, char) => char.toUpperCase());
}

function flagName(key) {
    return key.replace(/[A-Z]/g, char => `-${char.toLowerCase()}`);
}

function parseOptionValue(arg, argv, index) {
    if (arg.includes('=')) {
        return { value: arg.slice(arg.indexOf('=') + 1), consumedNext: false };
    }
    const nextArg = argv[index + 1];
    if (typeof nextArg === 'string' && !nextArg.startsWith('--')) {
        return { value: nextArg, consumedNext: true };
    }
    return { value: true, consumedNext: false };
}

function parseArgs(argv = process.argv.slice(2)) {
    const options = {
        manifest: null,
        investigationArtifact: INVESTIGATION_ARTIFACT_PATH,
        verificationArtifact: VERIFICATION_ARTIFACT_PATH,
        artifactOutput: ARTIFACT_OUTPUT_PATH,
        reportOutput: REPORT_PATH,
        source: null,
        route: null,
        leagueId: null,
        leagueName: null,
        season: null,
        targetCount: null,
        metadataOnlyPhaseAuthorization: null,
        controlledMetadataOnlyCheckAuthorization: null,
        networkAuthorization: null,
        allowDbWrite: null,
        allowRawMatchDataWrite: null,
        allowMatchesWrite: null,
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
        allowControlledWrite: false,
        executeWrite: false,
        commit: false,
        finalDbWriteConfirmation: false,
        acceptIdentityMapping: false,
        acceptBaseline: false,
        baselineAcceptanceAuthorization: false,
        rawWriteRetryAuthorization: false,
        rawWriteReadyForExecution: false,
        retry: 0,
        concurrency: 1,
        requestDelayMs: DEFAULT_REQUEST_DELAY_MS,
        requestTimeoutMs: DEFAULT_REQUEST_TIMEOUT_MS,
        targetExternalIds: null,
        generatedAt: null,
        help: false,
        unknown: [],
    };
    const knownKeys = new Set(Object.keys(options));
    const booleanKeys = new Set([...REQUIRED_YES_FLAGS, ...REQUIRED_NO_FLAGS, ...BLOCKED_TRUE_FLAGS, 'help']);

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

function normalizeInput(input = {}) {
    return {
        manifest: normalizeText(input.manifest),
        investigationArtifact: normalizeText(input.investigationArtifact) || INVESTIGATION_ARTIFACT_PATH,
        verificationArtifact: normalizeText(input.verificationArtifact) || VERIFICATION_ARTIFACT_PATH,
        artifactOutput: normalizeText(input.artifactOutput) || ARTIFACT_OUTPUT_PATH,
        reportOutput: normalizeText(input.reportOutput) || REPORT_PATH,
        source: normalizeLower(input.source),
        route: normalizeText(input.route),
        leagueId: parseInteger(input.leagueId, null),
        leagueName: normalizeText(input.leagueName),
        season: normalizeText(input.season),
        targetCount: parseInteger(input.targetCount, null),
        metadataOnlyPhaseAuthorization: normalizeBooleanFlag(input.metadataOnlyPhaseAuthorization, undefined),
        controlledMetadataOnlyCheckAuthorization: normalizeBooleanFlag(
            input.controlledMetadataOnlyCheckAuthorization,
            undefined
        ),
        networkAuthorization: normalizeBooleanFlag(input.networkAuthorization, undefined),
        allowDbWrite: normalizeBooleanFlag(input.allowDbWrite, undefined),
        allowRawMatchDataWrite: normalizeBooleanFlag(input.allowRawMatchDataWrite, undefined),
        allowMatchesWrite: normalizeBooleanFlag(input.allowMatchesWrite, undefined),
        allowSchemaMigration: normalizeBooleanFlag(input.allowSchemaMigration, undefined),
        allowParserImplementation: normalizeBooleanFlag(input.allowParserImplementation, undefined),
        allowFeatureExtraction: normalizeBooleanFlag(input.allowFeatureExtraction, undefined),
        allowTraining: normalizeBooleanFlag(input.allowTraining, undefined),
        allowPrediction: normalizeBooleanFlag(input.allowPrediction, undefined),
        allowBrowserRuntime: normalizeBooleanFlag(input.allowBrowserRuntime, undefined),
        allowProxyRuntime: normalizeBooleanFlag(input.allowProxyRuntime, undefined),
        printFullBody: normalizeBooleanFlag(input.printFullBody, undefined),
        saveFullBody: normalizeBooleanFlag(input.saveFullBody, undefined),
        printFullJson: normalizeBooleanFlag(input.printFullJson, undefined),
        saveFullJson: normalizeBooleanFlag(input.saveFullJson, undefined),
        printFullPageprops: normalizeBooleanFlag(input.printFullPageprops, undefined),
        saveFullPageprops: normalizeBooleanFlag(input.saveFullPageprops, undefined),
        allowControlledWrite: normalizeBooleanFlag(input.allowControlledWrite, false),
        executeWrite: normalizeBooleanFlag(input.executeWrite, false),
        commit: normalizeBooleanFlag(input.commit, false),
        finalDbWriteConfirmation: normalizeBooleanFlag(input.finalDbWriteConfirmation, false),
        acceptIdentityMapping: normalizeBooleanFlag(input.acceptIdentityMapping, false),
        acceptBaseline: normalizeBooleanFlag(input.acceptBaseline, false),
        baselineAcceptanceAuthorization: normalizeBooleanFlag(input.baselineAcceptanceAuthorization, false),
        rawWriteRetryAuthorization: normalizeBooleanFlag(input.rawWriteRetryAuthorization, false),
        rawWriteReadyForExecution: normalizeBooleanFlag(input.rawWriteReadyForExecution, false),
        retry: parseInteger(input.retry, 0),
        concurrency: parseInteger(input.concurrency, 1),
        requestDelayMs: parseInteger(input.requestDelayMs, DEFAULT_REQUEST_DELAY_MS),
        requestTimeoutMs: parseInteger(input.requestTimeoutMs, DEFAULT_REQUEST_TIMEOUT_MS),
        targetExternalIds: Array.isArray(input.targetExternalIds)
            ? input.targetExternalIds.map(normalizeText).filter(Boolean)
            : parseCsv(input.targetExternalIds),
        generatedAt: normalizeText(input.generatedAt),
        help: normalizeBooleanFlag(input.help, false),
        unknown: Array.isArray(input.unknown) ? input.unknown : [],
    };
}

function pushRequiredYes(errors, value, name) {
    if (value === true) return;
    errors.push(value === false ? `${name}=yes is required in ${PHASE}` : `missing ${name}=yes`);
}

function pushRequiredNo(errors, value, name) {
    if (value === false) return;
    errors.push(value === true ? `${name}=yes is blocked in ${PHASE}` : `missing ${name}=no`);
}

function requireExact(errors, actual, expected, name) {
    if (!normalizeText(actual)) {
        errors.push(`missing ${name}=${expected}`);
        return;
    }
    if (normalizeText(actual) !== expected) errors.push(`${name} must be ${expected}`);
}

function validateInput(rawInput = {}) {
    const input = normalizeInput(rawInput);
    const errors = [];
    if (input.unknown.length > 0) errors.push(`unknown arguments: ${input.unknown.join(',')}`);
    requireExact(errors, input.manifest, MANIFEST_PATH, 'manifest');
    requireExact(errors, input.investigationArtifact, INVESTIGATION_ARTIFACT_PATH, 'investigation-artifact');
    requireExact(errors, input.verificationArtifact, VERIFICATION_ARTIFACT_PATH, 'verification-artifact');
    requireExact(errors, input.artifactOutput, ARTIFACT_OUTPUT_PATH, 'artifact-output');
    requireExact(errors, input.reportOutput, REPORT_PATH, 'report-output');
    requireExact(errors, input.source, SOURCE, 'source');
    requireExact(errors, input.route, ROUTE, 'route');
    if (input.leagueId !== LEAGUE_ID) errors.push(`league-id must be ${LEAGUE_ID}`);
    requireExact(errors, input.leagueName, LEAGUE_NAME, 'league-name');
    requireExact(errors, input.season, SEASON, 'season');
    if (input.targetCount !== TARGET_COUNT) errors.push(`target-count must be ${TARGET_COUNT}`);
    for (const key of REQUIRED_YES_FLAGS) pushRequiredYes(errors, input[key], flagName(key));
    for (const key of REQUIRED_NO_FLAGS) pushRequiredNo(errors, input[key], flagName(key));
    for (const key of BLOCKED_TRUE_FLAGS) {
        if (input[key] === true) errors.push(`${flagName(key)}=yes is blocked in ${PHASE}`);
    }
    if (input.retry !== 0) errors.push('retry must be 0');
    if (input.concurrency !== 1) errors.push('concurrency must be 1');
    if (!Number.isInteger(input.requestDelayMs) || input.requestDelayMs < 0) {
        errors.push('request-delay-ms must be a non-negative integer');
    }
    if (!Number.isInteger(input.requestTimeoutMs) || input.requestTimeoutMs <= 0) {
        errors.push('request-timeout-ms must be a positive integer');
    }
    return { ok: errors.length === 0, input, errors };
}

function assertMetadataOnlyCheckNoWrite(options = {}) {
    if (
        normalizeBooleanFlag(options.dbWriteRequested, false) === true ||
        normalizeBooleanFlag(options.rawInsertRequested, false) === true ||
        normalizeBooleanFlag(options.matchesWriteRequested, false) === true ||
        normalizeBooleanFlag(options.matchesExternalIdModified, false) === true ||
        normalizeBooleanFlag(options.schemaMigrationRequested, false) === true
    ) {
        throw new Error(`${PHASE} metadata-only check must remain no-write`);
    }
    return true;
}

function isPlainObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function sleep(ms) {
    if (!ms) return Promise.resolve();
    return new Promise(resolve => {
        setTimeout(resolve, ms);
    });
}

function safeUrlSummary(rawUrl) {
    const value = normalizeText(rawUrl);
    if (!value) return null;
    try {
        const url = new URL(value);
        return `${url.origin}${url.pathname}${url.hash || ''}`;
    } catch (_error) {
        return value.split('?')[0].slice(0, 200);
    }
}

function topLevelKeysSummary(pageProps = {}) {
    if (!isPlainObject(pageProps)) return [];
    return Object.keys(pageProps).sort();
}

function jsonByteLength(value = {}) {
    return Buffer.byteLength(JSON.stringify(value), 'utf8');
}

function detectBlockOrCaptchaMarkers(bodyText = '', httpStatus = 0) {
    const text = normalizeText(bodyText);
    const markers = [];
    if (httpStatus === 403) markers.push('http_403');
    if (httpStatus === 429) markers.push('http_429');
    for (const [name, pattern] of BLOCK_MARKER_RULES) {
        if (pattern.test(text)) markers.push(name);
    }
    return [...new Set(markers)];
}

function isUnexpectedRedirect(finalUrl) {
    const value = normalizeText(finalUrl);
    if (!value) return false;
    try {
        const url = new URL(value);
        if (url.origin !== 'https://www.fotmob.com') return true;
        return !/^\/matches?\//.test(url.pathname);
    } catch (_error) {
        return true;
    }
}

function payloadSizeSummary(fetchResult = {}, pageProps = null) {
    const pagePropsBytes = isPlainObject(pageProps) ? jsonByteLength(pageProps) : null;
    return {
        body_byte_length: Number(fetchResult.body_byte_length || 0),
        pageprops_json_byte_length: pagePropsBytes,
        suspicious_small_payload: pagePropsBytes !== null ? pagePropsBytes < 512 : false,
    };
}

function requestedPageUrlBase(target = {}) {
    return (
        normalizeText(target.page_url_base) ||
        normalizeText(target.source_inventory_page_url_base) ||
        normalizeText(target.manifest_page_url_base) ||
        null
    );
}

function buildSafeReviewFlag(reconciliation = {}) {
    return (
        SAFE_REVIEW_DATE_STATUSES.has(reconciliation.date_compatibility_status) &&
        normalizeText(reconciliation.schedule_external_id_vs_detail_external_id_status) !== 'unknown'
    );
}

function buildPhaseBlockedStatuses() {
    return {
        raw_write_blocked: true,
        identity_mapping_acceptance_blocked: true,
        raw_write_blocker_status: 'blocked_pending_separate_identity_mapping_acceptance',
        identity_mapping_acceptance_blocker_status: 'blocked_pending_separate_identity_mapping_acceptance',
        accepted_mapping: false,
        raw_write_authorized: false,
    };
}

function buildFailureEntry(target = {}, fetchResult = {}, overrides = {}) {
    const base = buildPhaseBlockedStatuses();
    return {
        match_id: normalizeText(target.match_id),
        schedule_external_id: normalizeText(target.external_id),
        request_url_summary: safeUrlSummary(fetchResult.request_url || buildFotMobMatchUrl(target.external_id)),
        http_status: Number(fetchResult.http_status || 0),
        parsed: false,
        parsed_status: overrides.parsed_status || 'metadata_check_failed',
        block_or_captcha_marker_summary: overrides.block_or_captcha_marker_summary || [],
        observed_detail_external_id: null,
        observed_page_url_base: null,
        schedule_date: normalizeText(target.match_date || target.kickoff_time) || null,
        detail_date: null,
        schedule_home_team: normalizeText(target.home_team) || null,
        schedule_away_team: normalizeText(target.away_team) || null,
        detail_home_team: null,
        detail_away_team: null,
        status_summary: {
            schedule_status: normalizeText(target.status) || null,
            detail_status: null,
        },
        date_rule_status: UNKNOWN_DATE_COMPATIBILITY,
        canonical_identity_status: overrides.canonical_identity_status || 'fetch_or_parse_failure',
        identity_reconciliation_status: overrides.identity_reconciliation_status || 'fetch_or_parse_failure',
        safe_to_consider_for_future_review: false,
        controlled_metadata_check_status: overrides.controlled_metadata_check_status || 'failed',
        safe_error_summary: overrides.safe_error_summary || 'metadata-only check failed',
        payload_size_summary: payloadSizeSummary(fetchResult, null),
        top_level_keys_summary: [],
        ...base,
    };
}

function buildSuccessEntry(target = {}, fetchResult = {}, pageProps = {}) {
    const observed = extractObservedMetadata({
        pageProps,
        finalUrl: fetchResult.final_url,
        canonicalPageUrl: fetchResult.final_url,
    });
    const reconciliation = reconcileRouteIdentity({
        requestedScheduleExternalId: target.external_id,
        requestedPageUrlBase: requestedPageUrlBase(target),
        requestedHomeTeam: target.home_team,
        requestedAwayTeam: target.away_team,
        requestedMatchDate: target.match_date || target.kickoff_time,
        requestedStatus: target.status,
        requestedSeason: target.season,
        observedDetailExternalId: observed.observed_detail_external_id,
        observedPageUrlBase: observed.observed_page_url_base,
        observedHomeTeam: observed.observed_home_team,
        observedAwayTeam: observed.observed_away_team,
        observedMatchDate: observed.observed_match_date,
        observedStatus: observed.observed_status,
        observedSeason: observed.observed_season,
        acceptedIdentityMappingPresent: false,
        proposalOnlyMapping: true,
    });
    const phaseBlocked = buildPhaseBlockedStatuses();
    const dateRuleStatus = normalizeText(reconciliation.date_compatibility_status) || UNKNOWN_DATE_COMPATIBILITY;

    return {
        match_id: normalizeText(target.match_id),
        schedule_external_id: normalizeText(target.external_id),
        request_url_summary: safeUrlSummary(fetchResult.request_url || buildFotMobMatchUrl(target.external_id)),
        http_status: Number(fetchResult.http_status || 0),
        parsed: true,
        parsed_status: 'metadata_only_parsed',
        block_or_captcha_marker_summary: [],
        observed_detail_external_id: normalizeText(observed.observed_detail_external_id) || null,
        observed_page_url_base: normalizeText(observed.observed_page_url_base) || null,
        schedule_date: normalizeText(target.match_date || target.kickoff_time) || null,
        detail_date: normalizeText(observed.observed_match_date) || null,
        schedule_home_team: normalizeText(target.home_team) || null,
        schedule_away_team: normalizeText(target.away_team) || null,
        detail_home_team: normalizeText(observed.observed_home_team) || null,
        detail_away_team: normalizeText(observed.observed_away_team) || null,
        status_summary: {
            schedule_status: normalizeText(target.status) || null,
            detail_status: normalizeText(observed.observed_status) || null,
        },
        date_rule_status: dateRuleStatus,
        canonical_identity_status: normalizeText(reconciliation.canonical_identity_status) || 'unknown',
        identity_reconciliation_status: normalizeText(reconciliation.identity_reconciliation_status) || 'unknown',
        safe_to_consider_for_future_review: buildSafeReviewFlag(reconciliation),
        controlled_metadata_check_status: 'success',
        safe_error_summary:
            SAFE_REVIEW_DATE_STATUSES.has(dateRuleStatus) && dateRuleStatus !== UNKNOWN_DATE_COMPATIBILITY
                ? 'metadata-only evidence collected; still blocked pending separate identity mapping acceptance'
                : `metadata-only evidence collected; ${dateRuleStatus} remains blocked or requires follow-up review`,
        payload_size_summary: payloadSizeSummary(fetchResult, pageProps),
        top_level_keys_summary: topLevelKeysSummary(pageProps),
        ...phaseBlocked,
    };
}

function countWhere(entries = [], predicate = () => false) {
    return entries.filter(predicate).length;
}

function determineRecommendation({ counts = {}, stoppedEarly = false, detailUrlConstructionIssueCount = 0 } = {}) {
    if (detailUrlConstructionIssueCount > 0) {
        return 'Phase 5.21L2V3Q: detail URL construction fix planning';
    }
    if (stoppedEarly || counts.parse_failure_count > 0 || counts.still_unknown_count >= Math.ceil(TARGET_COUNT / 2)) {
        return 'Phase 5.21L2V3Q: continued metadata-only investigation';
    }
    if (counts.newly_classified_reverse_fixture_count > counts.metadata_check_success_count / 2) {
        return 'Phase 5.21L2V3Q: route target regeneration planning';
    }
    if (counts.newly_classified_date_match_count + counts.newly_classified_same_utc_day_count > 0) {
        return 'Phase 5.21L2V3Q: identity mapping review candidate selection planning';
    }
    return 'Phase 5.21L2V3Q: continued metadata-only investigation';
}

function buildCounts({
    entries = [],
    totalUnknownTargetCount = TARGET_COUNT,
    attemptedUnknownTargetCount = 0,
    metadataCheckBlockedCount = 0,
    metadataCheckFailedCount = 0,
    parseFailureCount = 0,
    captchaOrBlockCount = 0,
    detailUrlConstructionIssueCount = 0,
} = {}) {
    const metadataCheckSuccessCount = countWhere(
        entries,
        entry => entry.controlled_metadata_check_status === 'success'
    );
    const newlyClassifiedUnknownCount =
        countWhere(entries, entry => entry.date_rule_status === UNKNOWN_DATE_COMPATIBILITY) +
        Math.max(totalUnknownTargetCount - attemptedUnknownTargetCount, 0);
    return {
        requested_unknown_target_count: totalUnknownTargetCount,
        attempted_unknown_target_count: attemptedUnknownTargetCount,
        metadata_check_success_count: metadataCheckSuccessCount,
        metadata_check_blocked_count: metadataCheckBlockedCount,
        metadata_check_failed_count: metadataCheckFailedCount,
        captcha_or_block_count: captchaOrBlockCount,
        parse_failure_count: parseFailureCount,
        detail_url_construction_issue_count: detailUrlConstructionIssueCount,
        still_unknown_count: newlyClassifiedUnknownCount,
        newly_classified_reverse_fixture_count: countWhere(
            entries,
            entry => entry.date_rule_status === REVERSE_FIXTURE_DETECTED
        ),
        newly_classified_date_match_count: countWhere(entries, entry => entry.date_rule_status === DATE_MATCH),
        newly_classified_same_utc_day_count: countWhere(entries, entry => entry.date_rule_status === SAME_UTC_DAY),
        newly_classified_timezone_only_mismatch_count: countWhere(
            entries,
            entry => entry.date_rule_status === TIMEZONE_ONLY_MISMATCH
        ),
        newly_classified_unresolved_large_gap_count: countWhere(
            entries,
            entry => entry.date_rule_status === UNRESOLVED_LARGE_GAP
        ),
        newly_classified_cross_season_slug_reuse_count: countWhere(
            entries,
            entry => entry.date_rule_status === CROSS_SEASON_SLUG_REUSE
        ),
        newly_classified_unknown_count: newlyClassifiedUnknownCount,
        raw_write_blocked_count: totalUnknownTargetCount,
        identity_mapping_acceptance_blocked_count: totalUnknownTargetCount,
        safe_to_consider_for_future_review_count: countWhere(
            entries,
            entry => entry.safe_to_consider_for_future_review
        ),
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
    };
}

function validateManifest(manifest = {}) {
    const errors = [];
    if (normalizeText(manifest.batch_id) !== 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001') {
        errors.push('manifest batch_id mismatch');
    }
    if (normalizeLower(manifest.source) !== SOURCE) errors.push('manifest source mismatch');
    if (normalizeText(manifest.route) !== ROUTE) errors.push('manifest route mismatch');
    if (normalizeText(manifest.league?.league_name) !== LEAGUE_NAME) errors.push('manifest league_name mismatch');
    if (normalizeText(manifest.league?.season) !== SEASON) errors.push('manifest season mismatch');
    if (!Array.isArray(manifest.candidate_targets) || manifest.candidate_targets.length !== 50) {
        errors.push('manifest candidate_targets must contain 50 targets');
    }
    return { ok: errors.length === 0, errors };
}

function validateInvestigationArtifact(artifact = {}) {
    const errors = [];
    if (normalizeText(artifact.proposal_phase) !== 'Phase 5.21L2V3O') {
        errors.push('investigation artifact phase mismatch');
    }
    if (artifact.checked_unknown_target_count !== TARGET_COUNT) {
        errors.push(`investigation artifact checked_unknown_target_count must be ${TARGET_COUNT}`);
    }
    if (artifact.still_unknown_count !== TARGET_COUNT) {
        errors.push(`investigation artifact still_unknown_count must be ${TARGET_COUNT}`);
    }
    if (artifact.controlled_metadata_check_performed !== false) {
        errors.push('investigation artifact controlled_metadata_check_performed must be false');
    }
    if (
        !Array.isArray(artifact.unknown_target_investigation) ||
        artifact.unknown_target_investigation.length !== TARGET_COUNT
    ) {
        errors.push(`investigation artifact unknown_target_investigation must contain ${TARGET_COUNT} targets`);
    }
    return { ok: errors.length === 0, errors };
}

function selectUnknownTargets(manifest = {}, investigationArtifact = {}, requestedExternalIds = []) {
    const targetsByExternalId = new Map(
        (Array.isArray(manifest.candidate_targets) ? manifest.candidate_targets : []).map(target => [
            normalizeText(target.external_id),
            target,
        ])
    );
    const investigationIds = (
        Array.isArray(investigationArtifact.unknown_target_investigation)
            ? investigationArtifact.unknown_target_investigation
            : []
    )
        .map(entry => normalizeText(entry.schedule_external_id))
        .filter(Boolean);
    const selectedIds = requestedExternalIds.length > 0 ? requestedExternalIds : investigationIds;
    const uniqueIds = [...new Set(selectedIds.map(normalizeText).filter(Boolean))];
    const errors = [];
    const targets = [];
    for (const externalId of uniqueIds) {
        const target = targetsByExternalId.get(externalId);
        if (!target) {
            errors.push(`unknown target ${externalId} missing from manifest`);
            continue;
        }
        targets.push(target);
    }
    if (uniqueIds.length !== TARGET_COUNT && requestedExternalIds.length === 0) {
        errors.push(`expected ${TARGET_COUNT} unknown targets from investigation artifact`);
    }
    return { ok: errors.length === 0, errors, selectedExternalIds: uniqueIds, targets };
}

function resolveFetchResult(target = {}, dependencies = {}) {
    const byExternalId = dependencies.fetchResultsByExternalId || {};
    const externalId = normalizeText(target.external_id);
    if (byExternalId[externalId]) return Promise.resolve(byExternalId[externalId]);
    const fetchFn = dependencies.fetchFn;
    const requestUrl = buildFotMobMatchUrl(externalId);
    return fetchHtml(requestUrl, { fetchFn, timeoutMs: dependencies.requestTimeoutMs || DEFAULT_REQUEST_TIMEOUT_MS });
}

function shouldStopEarly({ entry = {}, parseFailureCount = 0, httpNon200Count = 0 } = {}) {
    if (entry.controlled_metadata_check_status === 'blocked') {
        return {
            stop: true,
            reason: entry.safe_error_summary || 'block_or_captcha_detected',
            category: 'block_or_captcha',
        };
    }
    if (parseFailureCount >= PARSE_FAILURE_STOP_THRESHOLD) {
        return {
            stop: true,
            reason: `parse_failure_threshold_reached:${parseFailureCount}`,
            category: 'parse_failure_spike',
        };
    }
    if (httpNon200Count >= HTTP_NON_200_STOP_THRESHOLD) {
        return {
            stop: true,
            reason: `http_non_200_threshold_reached:${httpNon200Count}`,
            category: 'widespread_http_non_200',
        };
    }
    return { stop: false, reason: null, category: null };
}

function buildUnexpectedRedirectEntry(target = {}, fetchResult = {}) {
    return buildFailureEntry(target, fetchResult, {
        parsed_status: 'unexpected_redirect',
        controlled_metadata_check_status: 'blocked',
        canonical_identity_status: 'block_or_captcha',
        identity_reconciliation_status: 'block_or_captcha',
        safe_error_summary: 'unexpected redirect detected during controlled metadata-only check',
    });
}

function buildBlockEntry(target = {}, fetchResult = {}, markers = []) {
    return buildFailureEntry(target, fetchResult, {
        parsed_status: 'block_or_captcha',
        controlled_metadata_check_status: 'blocked',
        block_or_captcha_marker_summary: markers,
        canonical_identity_status: 'block_or_captcha',
        identity_reconciliation_status: 'block_or_captcha',
        safe_error_summary: `block_or_captcha_detected:${markers.join(',') || 'unknown'}`,
    });
}

function buildParseFailureEntry(target = {}, fetchResult = {}, reason = 'pageprops_parse_failed') {
    return buildFailureEntry(target, fetchResult, {
        parsed_status: 'parse_failure',
        controlled_metadata_check_status: 'failed',
        safe_error_summary: reason,
    });
}

function buildHttpFailureEntry(target = {}, fetchResult = {}, reason = 'http_non_200') {
    return buildFailureEntry(target, fetchResult, {
        parsed_status: 'http_non_200',
        controlled_metadata_check_status: 'failed',
        safe_error_summary: reason,
    });
}

async function inspectTarget(target = {}, index = 0, input = {}, dependencies = {}) {
    if (index > 0) await sleep(input.requestDelayMs);
    const fetchResult = await resolveFetchResult(target, dependencies);
    if (isUnexpectedRedirect(fetchResult.final_url || fetchResult.request_url || '')) {
        return buildUnexpectedRedirectEntry(target, fetchResult);
    }
    const blockMarkers = detectBlockOrCaptchaMarkers(fetchResult.body || '', Number(fetchResult.http_status || 0));
    if (blockMarkers.length > 0) {
        return buildBlockEntry(target, fetchResult, blockMarkers);
    }
    if (fetchResult.ok !== true || Number(fetchResult.http_status || 0) !== 200) {
        return buildHttpFailureEntry(target, fetchResult, fetchResult.error || 'http_non_200');
    }
    const extraction = extractNextDataJsonFromHtml(fetchResult.body);
    if (!extraction.ok) {
        return buildParseFailureEntry(target, fetchResult, extraction.error || 'next_data_parse_failed');
    }
    const pageProps = getPageProps(extraction.data);
    if (!pageProps) {
        return buildParseFailureEntry(target, fetchResult, 'pageProps_not_found');
    }
    return buildSuccessEntry(target, fetchResult, pageProps);
}

function buildArtifact({
    manifest = {},
    investigationArtifact = {},
    verificationArtifact = {},
    targetEntries = [],
    selectedExternalIds = [],
    attemptedUnknownTargetCount = 0,
    metadataCheckBlockedCount = 0,
    metadataCheckFailedCount = 0,
    parseFailureCount = 0,
    captchaOrBlockCount = 0,
    detailUrlConstructionIssueCount = 0,
    stoppedEarly = false,
    stopReason = null,
    stopCategory = null,
    generatedAt = GENERATED_AT,
} = {}) {
    const counts = buildCounts({
        entries: targetEntries,
        totalUnknownTargetCount: selectedExternalIds.length || TARGET_COUNT,
        attemptedUnknownTargetCount,
        metadataCheckBlockedCount,
        metadataCheckFailedCount,
        parseFailureCount,
        captchaOrBlockCount,
        detailUrlConstructionIssueCount,
    });
    const recommendedNextStep = determineRecommendation({
        counts,
        stoppedEarly,
        detailUrlConstructionIssueCount,
    });
    return {
        artifact_type: 'metadata_only_detail_check',
        artifact_status: stoppedEarly ? 'stopped_early_due_to_block_or_abnormal_response' : PHASE_STATUS,
        proposal_phase: PHASE,
        phase_name: PHASE_NAME,
        source_phase: 'Phase 5.21L2V3O',
        generated_at: generatedAt,
        no_write: true,
        controlled_metadata_check_performed: true,
        live_source_check_performed: true,
        db_write_performed: false,
        raw_insert_performed: false,
        matches_write_performed: false,
        matches_external_id_modified: false,
        schema_migration_performed: false,
        parser_features_training_prediction_performed: false,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        browser_runtime_used: false,
        proxy_runtime_used: false,
        raw_data_or_pageprops_payload_saved: false,
        raw_data_or_pageprops_payload_printed: false,
        request_delay_ms: DEFAULT_REQUEST_DELAY_MS,
        parse_failure_stop_threshold: PARSE_FAILURE_STOP_THRESHOLD,
        http_non_200_stop_threshold: HTTP_NON_200_STOP_THRESHOLD,
        stopped_early: stoppedEarly,
        stop_reason: stopReason,
        stop_category: stopCategory,
        counts,
        ...counts,
        safety_contract: {
            metadata_only_result_is_not_accepted_mapping: true,
            metadata_check_success_does_not_equal_accepted_mapping: true,
            metadata_check_success_does_not_equal_raw_write_ready: true,
            date_match_is_not_accepted_mapping: true,
            same_utc_day_is_not_accepted_mapping: true,
            safe_to_consider_for_future_review_is_not_accepted_mapping: true,
            unknown_blocks_identity_mapping_acceptance: true,
            unknown_blocks_raw_write: true,
            reverse_fixture_detected_blocks_identity_mapping_acceptance: true,
            reverse_fixture_detected_blocks_raw_write: true,
            separate_identity_mapping_acceptance_required: true,
            separate_baseline_acceptance_required: true,
            separate_final_db_write_authorization_required: true,
        },
        source_artifacts: {
            proposal_manifest_path: MANIFEST_PATH,
            l2v3o_investigation_artifact_path: INVESTIGATION_ARTIFACT_PATH,
            l2v3n_expanded_verification_artifact_path: VERIFICATION_ARTIFACT_PATH,
        },
        selection: {
            selected_unknown_target_count: selectedExternalIds.length,
            selected_unknown_target_external_ids: selectedExternalIds,
            known_reverse_fixture_targets_rechecked: false,
        },
        metadata_only_target_summaries: targetEntries,
        recommended_next_step: recommendedNextStep,
        verification_remains_non_acceptance: {
            accepted_mapping_count: 0,
            raw_write_ready_for_execution: false,
        },
        context: {
            manifest_candidate_targets_count: Array.isArray(manifest.candidate_targets)
                ? manifest.candidate_targets.length
                : 0,
            l2v3o_unknown_target_count: investigationArtifact.checked_unknown_target_count || TARGET_COUNT,
            l2v3n_unknown_count: verificationArtifact.unknown_count || TARGET_COUNT,
        },
    };
}

function updateManifestMetadata(manifest = {}, artifact = {}) {
    const counts = artifact.counts || {};
    return {
        ...manifest,
        phase_5_21_l2v3p_metadata_check_status: artifact.artifact_status,
        controlled_metadata_only_detail_check_status: artifact.artifact_status,
        phase_5_21_l2v3p_artifact_path: ARTIFACT_OUTPUT_PATH,
        phase_5_21_l2v3p_report_path: REPORT_PATH,
        phase_5_21_l2v3p_controlled_metadata_check_performed: true,
        controlled_metadata_check_performed: true,
        attempted_unknown_target_count: counts.attempted_unknown_target_count,
        phase_5_21_l2v3p_attempted_unknown_target_count: counts.attempted_unknown_target_count,
        metadata_check_success_count: counts.metadata_check_success_count,
        phase_5_21_l2v3p_metadata_check_success_count: counts.metadata_check_success_count,
        metadata_check_blocked_count: counts.metadata_check_blocked_count,
        phase_5_21_l2v3p_metadata_check_blocked_count: counts.metadata_check_blocked_count,
        metadata_check_failed_count: counts.metadata_check_failed_count,
        phase_5_21_l2v3p_metadata_check_failed_count: counts.metadata_check_failed_count,
        captcha_or_block_count: counts.captcha_or_block_count,
        phase_5_21_l2v3p_captcha_or_block_count: counts.captcha_or_block_count,
        parse_failure_count: counts.parse_failure_count,
        phase_5_21_l2v3p_parse_failure_count: counts.parse_failure_count,
        still_unknown_count: counts.still_unknown_count,
        phase_5_21_l2v3p_still_unknown_count: counts.still_unknown_count,
        newly_classified_reverse_fixture_count: counts.newly_classified_reverse_fixture_count,
        phase_5_21_l2v3p_newly_classified_reverse_fixture_count: counts.newly_classified_reverse_fixture_count,
        newly_classified_date_match_count: counts.newly_classified_date_match_count,
        phase_5_21_l2v3p_newly_classified_date_match_count: counts.newly_classified_date_match_count,
        newly_classified_same_utc_day_count: counts.newly_classified_same_utc_day_count,
        phase_5_21_l2v3p_newly_classified_same_utc_day_count: counts.newly_classified_same_utc_day_count,
        newly_classified_timezone_only_mismatch_count: counts.newly_classified_timezone_only_mismatch_count,
        phase_5_21_l2v3p_newly_classified_timezone_only_mismatch_count:
            counts.newly_classified_timezone_only_mismatch_count,
        newly_classified_unresolved_large_gap_count: counts.newly_classified_unresolved_large_gap_count,
        phase_5_21_l2v3p_newly_classified_unresolved_large_gap_count:
            counts.newly_classified_unresolved_large_gap_count,
        newly_classified_cross_season_slug_reuse_count: counts.newly_classified_cross_season_slug_reuse_count,
        phase_5_21_l2v3p_newly_classified_cross_season_slug_reuse_count:
            counts.newly_classified_cross_season_slug_reuse_count,
        raw_write_blocked_count: counts.raw_write_blocked_count,
        phase_5_21_l2v3p_raw_write_blocked_count: counts.raw_write_blocked_count,
        identity_mapping_acceptance_blocked_count: counts.identity_mapping_acceptance_blocked_count,
        phase_5_21_l2v3p_identity_mapping_acceptance_blocked_count: counts.identity_mapping_acceptance_blocked_count,
        safe_to_consider_for_future_review_count: counts.safe_to_consider_for_future_review_count,
        phase_5_21_l2v3p_safe_to_consider_for_future_review_count: counts.safe_to_consider_for_future_review_count,
        accepted_mapping_count: 0,
        phase_5_21_l2v3p_accepted_mapping_count: 0,
        identity_mapping_acceptance_performed: false,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        phase_5_21_l2v3p_identity_mapping_acceptance_performed: false,
        phase_5_21_l2v3p_baseline_acceptance_performed: false,
        phase_5_21_l2v3p_raw_write_retry_performed: false,
        phase_5_21_l2v3p_raw_write_ready_for_execution: false,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        recommended_next_step: artifact.recommended_next_step,
    };
}

function buildReport(artifact = {}) {
    const counts = artifact.counts || {};
    const stopLine = artifact.stopped_early
        ? `- stopped_early=true (${artifact.stop_category}: ${artifact.stop_reason})`
        : '- stopped_early=false';
    return `# Data Entrypoint Governance - Phase 5.21 L2V3P

## Scope

- phase=${PHASE}
- phase_name=${PHASE_NAME}
- source_phase=Phase 5.21L2V3O
- controlled_metadata_check_performed=true
- live_source_check_performed=true
- db_write_performed=false
- raw_insert_performed=false
- matches_write_performed=false
- matches_external_id_modified=false
- schema_migration_performed=false
- parser_features_training_prediction_performed=false
- browser_runtime_used=false
- proxy_runtime_used=false

## Safety Contract

- metadata-only result is not an accepted mapping.
- metadata_check_success does not equal accepted mapping.
- metadata_check_success does not equal raw_write_ready_for_execution.
- date_match is not an accepted mapping.
- same_utc_day is not an accepted mapping.
- safe_to_consider_for_future_review is not an accepted mapping.
- raw_write_ready_for_execution=false.
- accepted_mapping_count=0.
- separate identity mapping acceptance, baseline acceptance, and final DB-write authorization remain required.

## Execution Policy

- selected_unknown_target_count=${artifact.selection?.selected_unknown_target_count || 0}
- request_delay_ms=${artifact.request_delay_ms}
- parse_failure_stop_threshold=${artifact.parse_failure_stop_threshold}
- http_non_200_stop_threshold=${artifact.http_non_200_stop_threshold}
${stopLine}

## Classification Summary

| metric | count |
| --- | ---: |
| requested_unknown_target_count | ${counts.requested_unknown_target_count} |
| attempted_unknown_target_count | ${counts.attempted_unknown_target_count} |
| metadata_check_success_count | ${counts.metadata_check_success_count} |
| metadata_check_blocked_count | ${counts.metadata_check_blocked_count} |
| metadata_check_failed_count | ${counts.metadata_check_failed_count} |
| captcha_or_block_count | ${counts.captcha_or_block_count} |
| parse_failure_count | ${counts.parse_failure_count} |
| still_unknown_count | ${counts.still_unknown_count} |
| newly_classified_reverse_fixture_count | ${counts.newly_classified_reverse_fixture_count} |
| newly_classified_date_match_count | ${counts.newly_classified_date_match_count} |
| newly_classified_same_utc_day_count | ${counts.newly_classified_same_utc_day_count} |
| newly_classified_timezone_only_mismatch_count | ${counts.newly_classified_timezone_only_mismatch_count} |
| newly_classified_unresolved_large_gap_count | ${counts.newly_classified_unresolved_large_gap_count} |
| newly_classified_cross_season_slug_reuse_count | ${counts.newly_classified_cross_season_slug_reuse_count} |
| newly_classified_unknown_count | ${counts.newly_classified_unknown_count} |
| safe_to_consider_for_future_review_count | ${counts.safe_to_consider_for_future_review_count} |
| raw_write_blocked_count | ${counts.raw_write_blocked_count} |
| identity_mapping_acceptance_blocked_count | ${counts.identity_mapping_acceptance_blocked_count} |
| accepted_mapping_count | ${counts.accepted_mapping_count} |

## Deliverables

- artifact=${ARTIFACT_OUTPUT_PATH}
- report=${REPORT_PATH}
- proposal manifest updated with L2V3P metadata-only planning metadata.

## Next Step

${artifact.recommended_next_step}
`;
}

async function runMetadataOnlyDetailCheck(rawInput = {}, dependencies = {}) {
    assertMetadataOnlyCheckNoWrite();
    const validation = validateInput(rawInput);
    if (!validation.ok) {
        return { ok: false, status: 2, errors: validation.errors };
    }
    const input = validation.input;
    const generatedAt = input.generatedAt || dependencies.generatedAt || GENERATED_AT;
    const manifest = dependencies.manifest || readJsonFile(input.manifest);
    const manifestGate = validateManifest(manifest);
    if (!manifestGate.ok) {
        return { ok: false, status: 3, errors: manifestGate.errors };
    }
    const investigationArtifact = dependencies.investigationArtifact || readJsonFile(input.investigationArtifact);
    const investigationGate = validateInvestigationArtifact(investigationArtifact);
    if (!investigationGate.ok) {
        return { ok: false, status: 4, errors: investigationGate.errors };
    }
    const verificationArtifact = dependencies.verificationArtifact || readJsonFile(input.verificationArtifact);
    const selection = selectUnknownTargets(manifest, investigationArtifact, input.targetExternalIds);
    if (!selection.ok) {
        return { ok: false, status: 5, errors: selection.errors };
    }

    const entries = [];
    let metadataCheckBlockedCount = 0;
    let metadataCheckFailedCount = 0;
    let parseFailureCount = 0;
    let captchaOrBlockCount = 0;
    let detailUrlConstructionIssueCount = 0;
    let httpNon200Count = 0;
    let stopReason = null;
    let stopCategory = null;
    let stoppedEarly = false;

    for (let index = 0; index < selection.targets.length; index += 1) {
        const target = selection.targets[index];
        const entry = await inspectTarget(target, index, input, dependencies);
        entries.push(entry);
        if (entry.controlled_metadata_check_status === 'blocked') {
            metadataCheckBlockedCount += 1;
            captchaOrBlockCount += 1;
            if (entry.parsed_status === 'unexpected_redirect') detailUrlConstructionIssueCount += 1;
        }
        if (entry.controlled_metadata_check_status === 'failed') {
            metadataCheckFailedCount += 1;
        }
        if (entry.parsed_status === 'parse_failure') {
            parseFailureCount += 1;
        }
        if (entry.parsed_status === 'http_non_200') {
            httpNon200Count += 1;
        }
        const earlyStop = shouldStopEarly({
            entry,
            parseFailureCount,
            httpNon200Count,
        });
        if (earlyStop.stop) {
            stoppedEarly = true;
            stopReason = earlyStop.reason;
            stopCategory = earlyStop.category;
            break;
        }
    }

    const artifact = buildArtifact({
        manifest,
        investigationArtifact,
        verificationArtifact,
        targetEntries: entries,
        selectedExternalIds: selection.selectedExternalIds,
        attemptedUnknownTargetCount: entries.length,
        metadataCheckBlockedCount,
        metadataCheckFailedCount,
        parseFailureCount,
        captchaOrBlockCount,
        detailUrlConstructionIssueCount,
        stoppedEarly,
        stopReason,
        stopCategory,
        generatedAt,
    });
    const updatedManifest = updateManifestMetadata(manifest, artifact);
    const report = buildReport(artifact);

    if (dependencies.writeFiles !== false) {
        writeJsonFile(input.artifactOutput, artifact);
        writeTextFile(input.reportOutput, report);
        writeJsonFile(input.manifest, updatedManifest);
    }

    return {
        ok: true,
        status: 0,
        artifact,
        updated_manifest: updatedManifest,
        report,
        selected_external_ids: selection.selectedExternalIds,
    };
}

async function runCli(argv = process.argv.slice(2), dependencies = {}) {
    const args = Array.isArray(argv) ? parseArgs(argv) : argv;
    if (args.help) {
        process.stdout.write(
            `Usage: node scripts/ops/pageprops_v2_metadata_only_detail_check.js --manifest=${MANIFEST_PATH} --investigation-artifact=${INVESTIGATION_ARTIFACT_PATH} --verification-artifact=${VERIFICATION_ARTIFACT_PATH} --artifact-output=${ARTIFACT_OUTPUT_PATH} --report-output=${REPORT_PATH} --source=${SOURCE} --route=${ROUTE} --league-id=${LEAGUE_ID} --league-name="${LEAGUE_NAME}" --season=${SEASON} --target-count=${TARGET_COUNT} --metadata-only-phase-authorization=yes --controlled-metadata-only-check-authorization=yes --network-authorization=yes --allow-db-write=no --allow-raw-match-data-write=no --allow-matches-write=no --allow-schema-migration=no --allow-parser-implementation=no --allow-feature-extraction=no --allow-training=no --allow-prediction=no --allow-browser-runtime=no --allow-proxy-runtime=no --print-full-body=no --save-full-body=no --print-full-json=no --save-full-json=no --print-full-pageprops=no --save-full-pageprops=no --retry=0 --concurrency=1\n`
        );
        return { status: 0 };
    }
    const result = await runMetadataOnlyDetailCheck(args, dependencies);
    const payload = result.ok
        ? {
              ok: true,
              phase: PHASE,
              artifact: ARTIFACT_OUTPUT_PATH,
              report: REPORT_PATH,
              attempted_unknown_target_count: result.artifact.attempted_unknown_target_count,
              metadata_check_success_count: result.artifact.metadata_check_success_count,
              metadata_check_blocked_count: result.artifact.metadata_check_blocked_count,
              metadata_check_failed_count: result.artifact.metadata_check_failed_count,
              still_unknown_count: result.artifact.still_unknown_count,
              newly_classified_reverse_fixture_count: result.artifact.newly_classified_reverse_fixture_count,
              newly_classified_date_match_count: result.artifact.newly_classified_date_match_count,
              newly_classified_same_utc_day_count: result.artifact.newly_classified_same_utc_day_count,
              raw_write_blocked_count: result.artifact.raw_write_blocked_count,
              identity_mapping_acceptance_blocked_count: result.artifact.identity_mapping_acceptance_blocked_count,
              accepted_mapping_count: result.artifact.accepted_mapping_count,
              raw_write_ready_for_execution: result.artifact.raw_write_ready_for_execution,
              recommended_next_step: result.artifact.recommended_next_step,
          }
        : { ok: false, phase: PHASE, status: result.status, errors: result.errors };
    process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
    return { status: result.status };
}

module.exports = {
    PHASE,
    PHASE_NAME,
    PHASE_STATUS,
    MANIFEST_PATH,
    INVESTIGATION_ARTIFACT_PATH,
    VERIFICATION_ARTIFACT_PATH,
    ARTIFACT_OUTPUT_PATH,
    REPORT_PATH,
    SOURCE,
    ROUTE,
    LEAGUE_ID,
    LEAGUE_NAME,
    SEASON,
    TARGET_COUNT,
    DEFAULT_REQUEST_DELAY_MS,
    PARSE_FAILURE_STOP_THRESHOLD,
    HTTP_NON_200_STOP_THRESHOLD,
    parseArgs,
    normalizeBooleanFlag,
    validateInput,
    assertMetadataOnlyCheckNoWrite,
    detectBlockOrCaptchaMarkers,
    isUnexpectedRedirect,
    buildFailureEntry,
    buildSuccessEntry,
    buildCounts,
    determineRecommendation,
    buildArtifact,
    updateManifestMetadata,
    buildReport,
    inspectTarget,
    runMetadataOnlyDetailCheck,
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
